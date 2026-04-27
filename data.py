"""
Data layer for the Agent Infrastructure Dashboard.

Pure-Python data readers — no web framework imports. Reads from the user's
~/.claude/ folder, the local vault, and disk caches. Used by server.py.

Everything here is read-only and side-effect-free except for disk-cache
writes and the routines ledger (both file-based, no network).
"""
from __future__ import annotations

import base64
import json
import re
import threading
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from config import (
    CLAUDE_CLI,
    DRAFTS_AWAITING,
    LIMITS,
    RUNS_DIR,
    SESSION_META_DIR,
    VAULT_NAME,
    VAULT_PATH,
)

# ───────────────────────────────────────────────────────────────
# Paths & cache
# ───────────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / ".cache"
MCP_CACHE = CACHE_DIR / "mcp.json"
RATE_CACHE = CACHE_DIR / "rate_limits.json"
USAGE_DISK_CACHE = CACHE_DIR / "anthropic_usage.json"
MCP_DISK_CACHE = CACHE_DIR / "mcp_list.json"
ROUTINES_LEDGER = CACHE_DIR / "routines.json"
DISK_CACHE_TTL = 300  # 5 min fresh, 4× stale-OK

CACHE_DIR.mkdir(parents=True, exist_ok=True)

_BG_REFRESH_LOCK = threading.Lock()
_BG_REFRESHING: dict[str, bool] = {}

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


# ───────────────────────────────────────────────────────────────
# Formatters
# ───────────────────────────────────────────────────────────────


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def fmt_cost(c: float) -> str:
    if c >= 100:
        return f"${c:.0f}"
    if c >= 10:
        return f"${c:.1f}"
    return f"${c:.2f}"


def fmt_ago(sec: int) -> str:
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m"
    if sec < 86400:
        return f"{sec // 3600}h"
    return f"{sec // 86400}d"


def fmt_time_until(ts: int) -> str:
    if not ts:
        return "—"
    delta = int(ts - time.time())
    if delta <= 0:
        return "now"
    h = delta // 3600
    m = (delta % 3600) // 60
    if h > 24:
        d = h // 24
        h = h % 24
        return f"{d}d {h}h"
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def fmt_clock_short(dt: datetime) -> str:
    s = dt.strftime("%I:%M%p").lower()
    return s[1:] if s.startswith("0") else s


def iso_to_ts(iso_str):
    """Parse Anthropic's ISO 8601 reset timestamps to Unix epoch seconds."""
    if not iso_str:
        return None
    try:
        s = iso_str.replace("Z", "+00:00") if iso_str.endswith("Z") else iso_str
        return int(datetime.fromisoformat(s).timestamp())
    except (ValueError, TypeError):
        return None


def compute_delta(current: float, prior: float, threshold_pct: float = 5.0):
    """Returns (arrow, pct, klass)."""
    if prior <= 0 and current <= 0:
        return ("·", 0.0, "neutral")
    if prior <= 0:
        return ("↑", 100.0, "up")
    pct = (current - prior) / prior * 100.0
    if abs(pct) < threshold_pct:
        return ("·", pct, "neutral")
    return ("↑", pct, "up") if pct > 0 else ("↓", pct, "down")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "untitled"


def obsidian_uri(vault_path: Path) -> str:
    try:
        rel = vault_path.relative_to(VAULT_PATH).as_posix()
    except ValueError:
        rel = vault_path.name
    return f"obsidian://open?vault={VAULT_NAME}&file={rel}"


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def asset_data_url(filename: str) -> str:
    p = Path(__file__).parent / "assets" / filename
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ───────────────────────────────────────────────────────────────
# Disk cache
# ───────────────────────────────────────────────────────────────


def _disk_cache_read(path: Path, fresh_ttl: int = DISK_CACHE_TTL):
    if not path.exists():
        return None
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return None
    if age > fresh_ttl * 4:
        return None
    try:
        return {
            "data": json.loads(path.read_text(encoding="utf-8")),
            "fresh": age <= fresh_ttl,
        }
    except Exception:
        return None


def _disk_cache_write(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def _bg_refresh(key: str, fetch_fn, write_path: Path) -> None:
    with _BG_REFRESH_LOCK:
        if _BG_REFRESHING.get(key):
            return
        _BG_REFRESHING[key] = True

    def _worker():
        try:
            result = fetch_fn()
            if result is not None:
                _disk_cache_write(write_path, result)
        except Exception:
            pass
        finally:
            with _BG_REFRESH_LOCK:
                _BG_REFRESHING[key] = False

    threading.Thread(target=_worker, daemon=True).start()


# ───────────────────────────────────────────────────────────────
# Vault scanners
# ───────────────────────────────────────────────────────────────


def _parse_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:2500]
    except OSError:
        return {"file": path.name, "path": str(path)}
    meta = {"file": path.name, "path": str(path)}
    m = _FRONTMATTER_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
    return meta


def scan_runs(days: int = 30) -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    out = []
    for day_dir in RUNS_DIR.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            d = date.fromisoformat(day_dir.name)
        except ValueError:
            continue
        if d < cutoff:
            continue
        for f in day_dir.glob("*.md"):
            meta = _parse_frontmatter(f)
            meta["date"] = d.isoformat()
            out.append(meta)
    return out


def list_awaiting_approvals():
    if not DRAFTS_AWAITING.exists():
        return []
    return sorted(DRAFTS_AWAITING.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


_DASHBOARD_DIR = Path(__file__).parent.resolve()


def list_vault_pulse(limit: int = 6) -> list[dict]:
    if not VAULT_PATH.exists():
        return []
    # Folder-name-agnostic skip list. We always skip the dashboard's own
    # folder via its __file__ path (so users can rename the repo without
    # having to edit anything here), plus the standard hidden + dependency
    # folders that show up inside vaults.
    skip_parts = {".obsidian", ".trash", "node_modules", ".git", ".claude"}
    files = []
    for p in VAULT_PATH.rglob("*.md"):
        if any(part in skip_parts for part in p.parts):
            continue
        try:
            if p.resolve().is_relative_to(_DASHBOARD_DIR):
                continue
        except (OSError, ValueError):
            pass
        try:
            st_ = p.stat()
        except OSError:
            continue
        files.append((p, st_))
    files.sort(key=lambda t: t[1].st_mtime, reverse=True)
    files = files[:limit]

    now = time.time()
    out = []
    for p, st_ in files:
        age = now - st_.st_mtime
        created_delta = abs(st_.st_mtime - st_.st_ctime)
        has_wikilink = False
        if age < 900:
            try:
                has_wikilink = "[[" in p.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                pass
        if created_delta < 120:
            verb = "created"
        elif has_wikilink and age < 300:
            verb = "linked"
        elif age < 600:
            verb = "appended"
        else:
            verb = "updated"
        try:
            rel = p.relative_to(VAULT_PATH).as_posix()
        except ValueError:
            rel = p.name
        directory = str(Path(rel).parent).replace("\\", "/")
        if directory == ".":
            directory = "vault"
        out.append({
            "verb": verb,
            "name": p.stem,
            "dir": directory,
            "age_sec": int(age),
            "age": fmt_ago(int(age)),
            "path": p,
            "uri": obsidian_uri(p),
        })
    return out


# ───────────────────────────────────────────────────────────────
# Session-meta / transcripts (per-message token usage)
# ───────────────────────────────────────────────────────────────


def _read_session_metas() -> list[dict]:
    """Per-message Claude Code token usage across ALL sessions.

    Primary source: ~/.claude/projects/<slug>/<session-id>.jsonl files.
    Returns dicts with start_time / input_tokens / output_tokens.
    Total input includes cache_creation + cache_read tokens so the 5h
    gauge reflects real rate-limit-window consumption.
    """
    out: list[dict] = []
    cutoff = time.time() - 30 * 86400

    projects_dir = Path.home() / ".claude" / "projects"
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for f in project_dir.glob("*.jsonl"):
                try:
                    if f.stat().st_mtime < cutoff:
                        continue
                    with open(f, encoding="utf-8", errors="replace") as fh:
                        for line in fh:
                            if '"usage"' not in line:
                                continue
                            try:
                                d = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            msg = d.get("message")
                            if not isinstance(msg, dict):
                                continue
                            usage = msg.get("usage")
                            ts = d.get("timestamp")
                            if not isinstance(usage, dict) or not ts:
                                continue
                            out.append({
                                "start_time": ts,
                                "input_tokens": (
                                    int(usage.get("input_tokens") or 0)
                                    + int(usage.get("cache_creation_input_tokens") or 0)
                                    + int(usage.get("cache_read_input_tokens") or 0)
                                ),
                                "output_tokens": int(usage.get("output_tokens") or 0),
                            })
                except OSError:
                    continue
        if out:
            return out

    # Fallback: legacy session-meta JSONs
    if SESSION_META_DIR.exists():
        for f in SESSION_META_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
                if "start_time" in d and ("input_tokens" in d or "output_tokens" in d):
                    out.append(d)
            except Exception:
                continue
        if out:
            return out

    # Last resort: dashboard-runs
    for r in scan_runs(30):
        t = r.get("time")
        if not t:
            continue
        out.append({
            "start_time": t,
            "input_tokens": _to_int(r.get("tokens_in")),
            "output_tokens": _to_int(r.get("tokens_out")),
        })
    return out


def _parse_session_time(d: dict):
    t = d.get("start_time")
    if not t:
        return None
    try:
        if t.endswith("Z"):
            t = t.replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        return dt.replace(tzinfo=None)
    except Exception:
        return None


def _read_cwd_basename(transcript_path: Path):
    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 4096))
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(tail.strip().split("\n")):
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        cwd = d.get("cwd")
        if cwd:
            return Path(cwd).name
    return None


def claude_code_active_state(threshold_sec: int = 120):
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None
    cutoff = time.time() - threshold_sec
    most_recent_path = None
    most_recent_mtime = 0.0
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        try:
            for f in project_dir.glob("*.jsonl"):
                try:
                    m = f.stat().st_mtime
                except OSError:
                    continue
                if m > cutoff and m > most_recent_mtime:
                    most_recent_path = f
                    most_recent_mtime = m
        except OSError:
            continue
    if most_recent_path is None:
        return None
    project_name = _read_cwd_basename(most_recent_path) or most_recent_path.parent.name
    return {"project": project_name}


def _window_oldest_reset(metas: list[dict], hours: int):
    cutoff = datetime.now() - timedelta(hours=hours)
    oldest = None
    for m in metas:
        t = _parse_session_time(m)
        if t is None or t < cutoff:
            continue
        if oldest is None or t < oldest:
            oldest = t
    if oldest is None:
        return None
    return int((oldest + timedelta(hours=hours)).timestamp())


# ───────────────────────────────────────────────────────────────
# Usage windows + activity chart data
# ───────────────────────────────────────────────────────────────


def calc_usage_windows() -> dict:
    now = datetime.now()
    five_h_ago = now - timedelta(hours=5)
    seven_d_ago = now - timedelta(days=7)
    today_start = datetime.combine(date.today(), datetime.min.time())

    metas = _read_session_metas()

    def agg(since):
        in_tok = out_tok = sessions = 0
        for m in metas:
            t = _parse_session_time(m)
            if t is None or t < since:
                continue
            in_tok += int(m.get("input_tokens") or 0)
            out_tok += int(m.get("output_tokens") or 0)
            sessions += 1
        return {
            "input": in_tok,
            "output": out_tok,
            "total": in_tok + out_tok,
            "sessions": sessions,
        }

    five_hour = agg(five_h_ago)
    weekly = agg(seven_d_ago)
    today_data = agg(today_start)

    # Reset times
    five_hour["reset_ts"] = _window_oldest_reset(metas, 5)
    weekly["reset_ts"] = _window_oldest_reset(metas, 7 * 24)

    # Today extras
    runs_today = [r for r in scan_runs(2) if r.get("date") == date.today().isoformat()]
    today_data["routines"] = count_routines_today()
    today_data["cost"] = sum(_to_float(r.get("cost_usd")) for r in runs_today)
    today_data["runs"] = len(runs_today)

    return {
        "five_hour": five_hour,
        "weekly": weekly,
        "today": today_data,
    }


def activity_cumulative(days: int = 30) -> list[dict]:
    """Daily cumulative request count for the activity chart.

    Returns list of {date: 'YYYY-MM-DD', day_count: int, cumulative: int}.
    """
    today = date.today()
    per_day = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for m in _read_session_metas():
        t = _parse_session_time(m)
        if t is None:
            continue
        k = t.date().isoformat()
        if k in per_day:
            per_day[k] += 1

    out = []
    cumulative = 0
    for k, v in per_day.items():
        cumulative += v
        out.append({"date": k, "day_count": v, "cumulative": cumulative})
    return out


def build_activity_svg(rows: list[dict]) -> str:
    """Inline SVG for the cumulative-activity chart, terracotta palette."""
    if not rows:
        return (
            '<div class="activity-chart-wrap" style="height:170px;'
            'display:flex;align-items:center;justify-content:center;'
            'color:var(--fg-mute);font:italic 400 12px \'Source Serif 4\',Georgia,serif;">'
            'no activity yet</div>'
        )

    vals = [r["cumulative"] for r in rows]
    n = len(vals)
    vmax = max(vals) if vals else 0
    if vmax <= 0:
        vmax = 1

    W, H = 1000, 170
    pad_l, pad_r, pad_t, pad_b = 6, 6, 8, 6

    def x_for(i):
        if n <= 1:
            return pad_l
        return pad_l + (W - pad_l - pad_r) * (i / (n - 1))

    def y_for(v):
        return pad_t + (H - pad_t - pad_b) * (1 - v / vmax)

    if n == 1:
        line_d = f"M {x_for(0):.2f},{y_for(vals[0]):.2f}"
        area_d = (
            f"M {x_for(0):.2f},{H - pad_b:.2f} "
            f"L {x_for(0):.2f},{y_for(vals[0]):.2f} "
            f"L {x_for(0):.2f},{H - pad_b:.2f} Z"
        )
    else:
        pts = [f"{x_for(i):.2f},{y_for(v):.2f}" for i, v in enumerate(vals)]
        line_d = "M " + " L ".join(pts)
        area_d = (
            f"M {x_for(0):.2f},{H - pad_b:.2f} "
            "L " + " L ".join(pts) + " "
            f"L {x_for(n - 1):.2f},{H - pad_b:.2f} Z"
        )

    def lbl(date_str):
        try:
            return datetime.fromisoformat(date_str).strftime("%b %d").upper()
        except Exception:
            return ""

    first_lbl = lbl(rows[0]["date"])
    mid_lbl = lbl(rows[n // 2]["date"]) if n >= 3 else ""
    last_lbl = lbl(rows[-1]["date"])

    svg = (
        f'<svg class="activity-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="none">'
        '<defs>'
        '<linearGradient id="actGrad" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset="0%" stop-color="#d97757" stop-opacity="0.28"/>'
        '<stop offset="100%" stop-color="#d97757" stop-opacity="0.02"/>'
        '</linearGradient>'
        '</defs>'
        f'<path d="{area_d}" fill="url(#actGrad)" stroke="none"/>'
        f'<path d="{line_d}" fill="none" stroke="#d97757" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )

    return (
        '<div class="activity-chart-wrap">'
        f'{svg}'
        '<div class="activity-axis">'
        f'<span>{first_lbl}</span>'
        f'<span>{mid_lbl}</span>'
        f'<span>{last_lbl}</span>'
        '</div>'
        '</div>'
    )


# ───────────────────────────────────────────────────────────────
# MCP servers (disk cache only — refreshed manually or via /refresh-mcp)
# ───────────────────────────────────────────────────────────────


def save_mcp_state(servers: list):
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        MCP_CACHE.write_text(json.dumps(servers), encoding="utf-8")
    except Exception:
        pass


def load_mcp_state() -> list:
    if MCP_CACHE.exists():
        try:
            return json.loads(MCP_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def fetch_mcp_servers() -> list[dict]:
    """Read MCP server list from disk cache. Cheap (no subprocess)."""
    cached = _disk_cache_read(MCP_DISK_CACHE)
    if cached is not None:
        return cached["data"] or []
    return load_mcp_state() or []


def refresh_mcp_servers_blocking() -> list[dict]:
    """Manually invoke `claude mcp list` and write to disk. Slow (5-10s)."""
    import subprocess
    try:
        result = subprocess.run(
            [str(CLAUDE_CLI), "mcp", "list"],
            capture_output=True, text=True, timeout=15,
        )
        out = result.stdout
    except Exception:
        return load_mcp_state()

    servers = []
    for raw in out.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("checking"):
            continue
        if ":" not in line or " - " not in line:
            continue
        try:
            name_part, rest = line.split(":", 1)
            url_part, status_part = rest.rsplit(" - ", 1)
        except ValueError:
            continue
        sp = status_part.strip().lower()
        if "connected" in sp:
            status = "connected"
        elif "needs authentication" in sp or "needs auth" in sp:
            status = "needs_auth"
        elif "failed" in sp or "✗" in status_part:
            status = "failed"
        else:
            status = "unknown"
        servers.append({
            "name": name_part.strip(),
            "url": url_part.strip(),
            "status": status,
        })

    if servers:
        save_mcp_state(servers)
        _disk_cache_write(MCP_DISK_CACHE, servers)
    return servers


# ───────────────────────────────────────────────────────────────
# Anthropic OAuth usage (for the gauges)
# ───────────────────────────────────────────────────────────────


def _fetch_anthropic_usage_network():
    try:
        creds_path = Path.home() / ".claude" / ".credentials.json"
        creds = json.loads(creds_path.read_text(encoding="utf-8"))
        token = creds.get("claudeAiOauth", {}).get("accessToken")
        if not token:
            return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_anthropic_usage():
    """Stale-while-revalidate Anthropic usage fetch."""
    cached = _disk_cache_read(USAGE_DISK_CACHE)
    if cached is not None:
        if not cached["fresh"]:
            _bg_refresh("anthropic_usage", _fetch_anthropic_usage_network, USAGE_DISK_CACHE)
        return cached["data"]
    data = _fetch_anthropic_usage_network()
    if data is not None:
        _disk_cache_write(USAGE_DISK_CACHE, data)
    return data


# ───────────────────────────────────────────────────────────────
# Rate-limit cache (legacy; kept so existing data files still parse)
# ───────────────────────────────────────────────────────────────


def load_rate_limits() -> dict:
    if RATE_CACHE.exists():
        try:
            return json.loads(RATE_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# ───────────────────────────────────────────────────────────────
# Routines ledger
# ───────────────────────────────────────────────────────────────


def _load_routines_ledger() -> dict:
    if ROUTINES_LEDGER.exists():
        try:
            return json.loads(ROUTINES_LEDGER.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def count_routines_today() -> int:
    today_str = date.today().isoformat()
    return int(_load_routines_ledger().get(today_str, 0))


# ───────────────────────────────────────────────────────────────
# Composite reads — what server.py needs in one call
# ───────────────────────────────────────────────────────────────


def status_strip_data() -> list[dict]:
    """The horizontal status strip cells.

    Always includes: 5-hour window, weekly, routines today.
    Additionally includes Sonnet only + Claude Design IF Anthropic's OAuth
    usage endpoint returns those sub-windows.

    Each cell: {pct, value_str, label, reset_str}
    """
    from datetime import timedelta as _td
    w = calc_usage_windows()
    five_h_total = w["five_hour"]["total"]
    week_total = w["weekly"]["total"]
    routines_today = w["today"]["routines"]

    anth = fetch_anthropic_usage() or {}
    five_h_pct_real = (anth.get("five_hour") or {}).get("utilization")
    wk_pct_real = (anth.get("seven_day") or {}).get("utilization")
    sonnet = anth.get("seven_day_sonnet")
    omelette = anth.get("seven_day_omelette")  # = Claude Design tier

    # Reset times: prefer Anthropic, fall back to local.
    five_h_reset = (
        iso_to_ts((anth.get("five_hour") or {}).get("resets_at"))
        or w["five_hour"]["reset_ts"]
    )
    week_reset = (
        iso_to_ts((anth.get("seven_day") or {}).get("resets_at"))
        or w["weekly"]["reset_ts"]
    )

    # Percentages
    if five_h_pct_real is not None:
        ss_5h_pct = float(five_h_pct_real)
    else:
        ss_5h_pct = 100.0 * five_h_total / LIMITS["five_hour_tokens"] if LIMITS["five_hour_tokens"] else 0.0

    if wk_pct_real is not None:
        ss_wk_pct = float(wk_pct_real)
    else:
        ss_wk_pct = 100.0 * week_total / LIMITS["weekly_tokens"] if LIMITS["weekly_tokens"] else 0.0

    routines_total = LIMITS["daily_routine_runs"]
    ss_rt_pct = 100.0 * routines_today / routines_total if routines_total else 0.0

    cells = [
        {
            "pct": ss_5h_pct,
            "value_str": f"{ss_5h_pct:.0f}%",
            "label": "5-hour window",
            "reset_str": "resets " + (fmt_time_until(five_h_reset) if five_h_reset else "—"),
        },
        {
            "pct": ss_wk_pct,
            "value_str": f"{ss_wk_pct:.0f}%",
            "label": "weekly",
            "reset_str": "resets " + (fmt_time_until(week_reset) if week_reset else "—"),
        },
        {
            "pct": ss_rt_pct,
            "value_str": f"{routines_today}/{routines_total}",
            "label": "routines today",
            "reset_str": "resets midnight",
        },
    ]

    if sonnet and sonnet.get("utilization") is not None:
        s_pct = float(sonnet["utilization"])
        s_reset = iso_to_ts(sonnet.get("resets_at"))
        cells.append({
            "pct": s_pct,
            "value_str": f"{s_pct:.0f}%",
            "label": "sonnet only",
            "reset_str": "resets " + (fmt_time_until(s_reset) if s_reset else "—"),
        })
    if omelette and omelette.get("utilization") is not None:
        d_pct = float(omelette["utilization"])
        d_reset = iso_to_ts(omelette.get("resets_at"))
        cells.append({
            "pct": d_pct,
            "value_str": f"{d_pct:.0f}%",
            "label": "claude design",
            "reset_str": "resets " + (fmt_time_until(d_reset) if d_reset else "—"),
        })
    return cells


def mini_ring_svg(pct: float, size: int = 56) -> str:
    """Inline SVG ring, terracotta-tinted, used in each status-strip cell."""
    import math
    pct = max(0.0, min(100.0, float(pct)))
    r = size / 2 - 4
    c = 2 * math.pi * r
    off = c * (1 - pct / 100.0)
    cx = cy = size / 2
    if pct >= 90:
        stroke = "var(--danger)"
    elif pct >= 70:
        stroke = "var(--warn)"
    else:
        stroke = "var(--accent)"
    return (
        f'<svg class="ss-ring" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
        f'stroke="var(--ring-soft)" stroke-width="4"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{stroke}" '
        f'stroke-width="4" stroke-linecap="round" '
        f'stroke-dasharray="{c:.2f}" stroke-dashoffset="{off:.2f}" '
        f'transform="rotate(-90 {cx} {cy})" '
        f'style="transition: stroke-dashoffset 0.6s ease"/>'
        f'</svg>'
    )


def forecast_data() -> dict:
    """Compute Forecast card values for The Long View.

    Returns: {used_pct, proj_pct, burn_str, cap_str, reset_str}
    """
    anth = fetch_anthropic_usage() or {}
    five_h_pct_real = (anth.get("five_hour") or {}).get("utilization")
    five_h_reset = (
        iso_to_ts((anth.get("five_hour") or {}).get("resets_at"))
        or _window_oldest_reset(_read_session_metas(), 5)
    )

    used_pct = float(five_h_pct_real) if five_h_pct_real is not None else 0.0
    if five_h_pct_real is None:
        # local fallback
        w = calc_usage_windows()
        five_h_total = w["five_hour"]["total"]
        used_pct = (
            100.0 * five_h_total / LIMITS["five_hour_tokens"]
            if LIMITS["five_hour_tokens"] else 0.0
        )

    proj_pct = used_pct
    burn_str = "idle"
    cap_str = "under cap this window"
    reset_str = fmt_time_until(five_h_reset) if five_h_reset else "—"

    try:
        if five_h_reset:
            reset_in_sec = max(0, int(five_h_reset - time.time()))
            reset_in_min = reset_in_sec / 60.0
            elapsed_min = max(0.0, 300.0 - reset_in_min)
            if five_h_pct_real is not None:
                used_tokens = LIMITS["five_hour_tokens"] * (five_h_pct_real / 100.0)
            else:
                w = calc_usage_windows()
                used_tokens = float(w["five_hour"]["total"])
            if elapsed_min > 0 and used_tokens > 0:
                bpm = used_tokens / elapsed_min
                burn_str = f"{fmt_tokens(int(bpm))}/min"
                remaining = max(0.0, LIMITS["five_hour_tokens"] - used_tokens)
                proj_tokens_at_reset = used_tokens + bpm * reset_in_min
                proj_pct = min(150.0, 100.0 * proj_tokens_at_reset / LIMITS["five_hour_tokens"])
                if bpm > 0:
                    exhaust_min = remaining / bpm
                    if exhaust_min < reset_in_min:
                        cap_time = datetime.now() + timedelta(minutes=exhaust_min)
                        cap_str = f"cap projected at {fmt_clock_short(cap_time)}"
    except Exception:
        pass

    return {
        "used_pct": used_pct,
        "proj_pct": proj_pct,
        "burn_str": burn_str,
        "cap_str": cap_str,
        "reset_str": reset_str,
    }


def bar_chart_7day_svg(rows: list[dict]) -> tuple[str, int]:
    """Last-7-days vertical bar chart SVG. Returns (svg_html, total_sessions)."""
    last7 = rows[-7:] if len(rows) >= 7 else rows[:]
    if not last7:
        return ("", 0)
    vals = [r["day_count"] for r in last7]
    dates = [datetime.fromisoformat(r["date"]) for r in last7]
    bar_max = max(vals) if vals else 0
    if bar_max <= 0:
        bar_max = 1
    total = sum(vals)

    BW, BH = 720, 130
    pad_l, pad_r, pad_t, pad_b = 6, 6, 8, 6
    n = len(vals)
    slot = (BW - pad_l - pad_r) / max(n, 1)
    bar_w = slot * 0.62

    bars_svg = ""
    for i, v in enumerate(vals):
        bx = pad_l + slot * i + (slot - bar_w) / 2
        bh = (BH - pad_t - pad_b) * (v / bar_max)
        by = BH - pad_b - bh
        bars_svg += (
            f'<rect x="{bx:.2f}" y="{by:.2f}" width="{bar_w:.2f}" '
            f'height="{bh:.2f}" fill="#d97757" rx="2"/>'
        )
    axis_html = "".join(f'<span>{d.strftime("%a").upper()}</span>' for d in dates)
    svg = (
        f'<svg class="bar-chart-svg" viewBox="0 0 {BW} {BH}" preserveAspectRatio="none">'
        f'{bars_svg}'
        '</svg>'
        f'<div class="bar-chart-axis">{axis_html}</div>'
    )
    return (svg, total)


def list_dispatches(limit: int = 8) -> list[dict]:
    """Recent dashboard runs from today, oldest first.

    Reads dashboard-runs/<today>/*.md. Each entry: {time, label, topic, cost,
    duration, uri}. Will be empty for new users since the dashboard no longer
    fires runs in-browser — kept so existing data still surfaces.
    """
    today_runs_dir = RUNS_DIR / date.today().isoformat() if RUNS_DIR.exists() else None
    if not today_runs_dir or not today_runs_dir.exists():
        return []
    files = sorted(today_runs_dir.glob("*.md"), key=lambda p: p.stat().st_mtime)
    files = files[:limit]
    out = []
    for r in files:
        meta = _parse_frontmatter(r)
        mtime = datetime.fromtimestamp(r.stat().st_mtime)
        time_str = meta.get("time") or mtime.strftime("%H:%M")
        stem_parts = r.stem.split("-", 2)
        if len(stem_parts) >= 3 and stem_parts[0].isdigit():
            label = stem_parts[-1].replace("-", " ")
        else:
            label = r.stem.replace("-", " ")
        topic = meta.get("topic") or ""
        if not topic and meta.get("prompt"):
            p = meta["prompt"].strip().strip('"').strip("'")
            topic = (p[:60] + "…") if len(p) > 60 else p
        cost_raw = meta.get("cost_usd") or ""
        try:
            cost_str = f"${float(cost_raw):.4f}"
        except (TypeError, ValueError):
            cost_str = ""
        dur_raw = meta.get("duration_sec") or meta.get("duration") or ""
        if dur_raw:
            try:
                ds = int(float(dur_raw))
                dur_str = f"{ds}s" if ds < 60 else f"{ds // 60}m {ds % 60}s"
            except (TypeError, ValueError):
                dur_str = str(dur_raw)
        else:
            dur_str = ""
        meta_line = " · ".join(p for p in (dur_str, cost_str) if p)
        out.append({
            "time": time_str,
            "label": label,
            "topic": topic,
            "meta_line": meta_line,
            "uri": obsidian_uri(r),
        })
    return out
