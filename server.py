"""
Agent Infrastructure Dashboard — FastAPI server.

Run with:  uvicorn server:app --reload --host 127.0.0.1 --port 8501

A single server-rendered page that reads from your local ~/.claude/ folder
and the vault. No Streamlit, no run engine — the dashboard is a passive
monitor. Skills are copy-to-clipboard cards.
"""
from __future__ import annotations

from datetime import date
from itertools import groupby
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import data
from config import (
    CLAUDE_PLAN,
    PERMISSION_MODE,
    SKILLS,
    VAULT_NAME,
)

BASE_DIR = Path(__file__).parent
app = FastAPI(title="Agent Infrastructure")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

templates.env.filters["fmt_tokens"] = data.fmt_tokens
templates.env.filters["fmt_cost"] = data.fmt_cost
templates.env.filters["fmt_ago"] = data.fmt_ago


# ── Routes ──


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Status strip cells (5h, weekly, routines, sonnet, claude design)
    cells = data.status_strip_data()
    cells_html = []
    for c in cells:
        cells_html.append(
            '<div class="ss-cell">'
            f'{data.mini_ring_svg(c["pct"])}'
            f'<div class="ss-pct">{c["value_str"]}</div>'
            f'<div class="ss-cell-label">{c["label"]}</div>'
            f'<div class="ss-cell-reset">{c["reset_str"]}</div>'
            '</div>'
        )
    status_strip_html = (
        '<div class="status-strip">' + "".join(cells_html) + '</div>'
        '<div class="anthropic-link-row">'
        '<a href="https://claude.com/settings/usage" target="_blank">'
        'view exact usage on anthropic ↗</a>'
        '</div>'
    )

    # Activity chart (cumulative 30-day, line chart)
    activity_rows = data.activity_cumulative(days=30)
    cum_total = sum(r["day_count"] for r in activity_rows)
    activity_svg = data.build_activity_svg(activity_rows)

    # 7-day bar chart
    bar7_svg, bar7_total = data.bar_chart_7day_svg(activity_rows)

    # Forecast
    forecast = data.forecast_data()
    fc_used_w = max(0.0, min(100.0, forecast["used_pct"]))
    fc_proj_w = max(0.0, min(100.0, forecast["proj_pct"]))
    fc_proj_extra = max(0.0, fc_proj_w - fc_used_w)

    # MCP servers + connections strip data
    mcp_servers = data.fetch_mcp_servers()
    for m in mcp_servers:
        m["status_norm"] = (m.get("status") or "unknown").lower().replace("-", "_")
        m["display_name"] = (m.get("name") or "?").replace("claude.ai ", "").replace("plugin:", "")
    mcp_ready_count = sum(
        1 for m in mcp_servers
        if m["status_norm"] in ("ready", "connected")
    )

    # Vault Pulse
    pulse = data.list_vault_pulse(limit=8)

    # Dispatches (today's dashboard runs)
    dispatches = data.list_dispatches(limit=8)

    # Active state
    active_state = data.claude_code_active_state()

    # Skills, grouped by category — preserved order daily → vault → tools
    cat_order = {"daily": 0, "vault": 1, "tools": 2}
    cat_label = {"daily": "Daily routines", "vault": "Content & studies", "tools": "Tools"}
    skills_sorted = sorted(SKILLS, key=lambda s: cat_order.get(s.get("category", "other"), 99))
    skill_groups = []
    for category, group in groupby(skills_sorted, key=lambda s: s.get("category", "other")):
        entries = []
        for s in group:
            tmpl = s.get("prompt_template") or ""
            entries.append({
                "label": s.get("label", "skill"),
                "description": s.get("description", ""),
                "prompt": tmpl,
                "placeholder": s.get("input_placeholder"),
                "needs_input": "{input}" in tmpl,
                "icon": (s.get("label", "·").strip()[:1] or "·").upper(),
                "is_routine": category == "daily",
            })
        skill_groups.append({
            "id": category,
            "label": cat_label.get(category, category.title()),
            "entries": entries,
        })

    # Masthead bits
    today_dt = date.today()
    today_str = today_dt.strftime("%A, %B ") + str(today_dt.day)
    vault_uri_masthead = f"obsidian://open?vault={quote(VAULT_NAME)}"

    return templates.TemplateResponse(request, "index.html", {
        "vault_name": VAULT_NAME,
        "plan": CLAUDE_PLAN,
        "permission_mode": PERMISSION_MODE,
        "today_str": today_str,
        "vault_uri": vault_uri_masthead,
        "status_strip_html": status_strip_html,
        "activity_svg": activity_svg,
        "cum_total": cum_total,
        "bar7_svg": bar7_svg,
        "bar7_total": bar7_total,
        "forecast": forecast,
        "fc_used_w": fc_used_w,
        "fc_proj_extra": fc_proj_extra,
        "mcp_servers": mcp_servers,
        "mcp_ready_count": mcp_ready_count,
        "pulse": pulse,
        "dispatches": dispatches,
        "active": active_state,
        "skill_groups": skill_groups,
    })


@app.post("/api/refresh-mcp")
def refresh_mcp() -> JSONResponse:
    servers = data.refresh_mcp_servers_blocking()
    return JSONResponse({"servers": servers, "count": len(servers)})


@app.get("/healthz")
def healthz() -> Response:
    return Response("ok", media_type="text/plain")
