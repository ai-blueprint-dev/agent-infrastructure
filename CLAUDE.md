# Agent Infrastructure — Project Context for Claude Code

This file is auto-loaded when the user runs `claude` in this folder. It exists so you (Claude Code) immediately know what this project is, how to set it up for the user, and how to extend it without the user having to re-explain anything.

## If the user is setting up for the first time

If the user has just cloned this repo and says anything like *"set me up"*, *"install this"*, *"get this working"*, or runs the dashboard skill explicitly — **invoke the `setup-dashboard` skill**. That skill walks them through a short conversational setup (3 questions) and handles everything: installs Python deps, writes `config.py`, copies bundled skills into their vault, and copies the vault `CLAUDE.md` template.

The skill is at `.claude/skills/setup-dashboard/SKILL.md` and is auto-loaded into your context.

**Do not** suggest the user run a Python script themselves. There is no `setup.py` — you ARE the setup.

## If the user is asking how to extend or customize the dashboard

If the user pastes something like *"specialize this for real estate"* or *"add a fourth gauge"* or *"make the dispatches column show GitHub PRs instead"*, you have everything you need below.

---

## What this project is

A **local-first, single-user FastAPI dashboard** that monitors the user's Claude Code activity. It reads from `~/.claude/projects/` (transcripts), `~/.claude/.credentials.json` (OAuth token for Anthropic's usage endpoint), the user's vault folder, and a few local disk caches. It does not run Claude — it watches what the user runs themselves.

Skills shown in the UI are **copy-to-clipboard cards**. Clicking one copies a `claude -p '<prompt>'` command, which the user pastes into a terminal. The dashboard never spawns subprocesses for skill execution.

Tech stack: FastAPI · Jinja2 · vanilla CSS + JS · Python ≥ 3.10. No build step. No database. Three runtime dependencies: `fastapi`, `uvicorn`, `jinja2`.

---

## File map (full)

```
agent-infrastructure/
├─ server.py            FastAPI routes. ~160 lines. Thin shell over data.py.
├─ data.py              Pure data layer. ~700 lines. No web imports. Where
│                       you add new readers / sections / aggregations.
├─ config.py            User config (gitignored). VAULT_PATH, VAULT_NAME,
│                       CLAUDE_CLI, CLAUDE_PLAN, PERMISSION_MODE, SKILLS.
├─ config.example.py    Template for users to copy.
├─ templates/
│   └─ index.html       Single page, all sections inline. ~180 lines.
├─ static/
│   ├─ css/main.css     Atrium / Terracotta palette. CSS variables drive
│   │                   light + dark. ~750 lines.
│   └─ js/main.js       Copy-to-clipboard, theme toggle, MCP refresh. ~90 lines.
├─ requirements.txt
├─ start.bat / start.sh  Launchers (open browser + run uvicorn).
├─ README.md            Human onboarding + GWS deep dive + customization story.
└─ CLAUDE.md            (this file)
```

## Sections rendered on the page

In order, top to bottom:

1. **Masthead** — `cpt-masthead` div. Title + date + plan + permission mode + obsidian + theme toggle + (optional) active session pill.
2. **Status strip** — `status-strip` div with up to 5 cells. Always 3 (5h, weekly, routines). Plus 2 conditional (Sonnet, Claude Design — only if Anthropic API returns them).
3. **`<hr class="chapter">`** divider.
4. **Skills & workflows** — `console-h2` + `console-explainer` (collapsible) + per-category `atrium-skill-grid` blocks.
5. **Connections** — `conn-strip` with MCP pills + refresh button.
6. **Dispatches** — `section-band` with today's dashboard runs (legacy data source; mostly empty for new users).
7. **Vault Pulse** — `section-band` with last 8 vault file changes.
8. **The Long View** — `long-view-eyebrow` + 2-col grid (Forecast left, 7-day bars right) + full-width Cumulative chart.

---

## Data flow

Every page render is on-demand. There is no background job, no cache invalidation logic beyond a 5-minute disk cache for the slow Anthropic OAuth call.

```
~/.claude/projects/<sess>.jsonl  ──┐
~/.claude/.credentials.json      ──┤
config.py SKILLS, LIMITS         ──┤──►  data.py  ──►  server.py.index()  ──►  index.html
VAULT_PATH (rglob *.md)          ──┤      (pure         (compose context     (Jinja render)
.cache/mcp_list.json             ──┘       readers)      dict)
```

## Module responsibilities

### `data.py`

Pure-Python module. **Never import `fastapi` or `streamlit` here.** All side effects are limited to:
- Reading files from `~/.claude/`, the vault, and `.cache/`
- Writing to `.cache/` for the disk-cache layer
- Spawning a subprocess for `claude mcp list` (only via `refresh_mcp_servers_blocking()`)

Key functions, grouped:

- **Formatters:** `fmt_tokens`, `fmt_cost`, `fmt_ago`, `fmt_time_until`, `fmt_clock_short`, `slugify`, `iso_to_ts`, `obsidian_uri`
- **Disk cache:** `_disk_cache_read`, `_disk_cache_write`, `_bg_refresh`
- **Vault scanners:** `scan_runs`, `list_vault_pulse`, `list_dispatches`, `list_awaiting_approvals`
- **Session metadata:** `_read_session_metas`, `_parse_session_time`, `claude_code_active_state`, `_window_oldest_reset`
- **Aggregations:** `calc_usage_windows`, `compute_delta`, `activity_cumulative`
- **Composite shapers (called directly by `server.py`):** `status_strip_data`, `forecast_data`, `bar_chart_7day_svg`, `build_activity_svg`, `mini_ring_svg`
- **MCP / Anthropic API:** `fetch_mcp_servers`, `refresh_mcp_servers_blocking`, `fetch_anthropic_usage`

### `server.py`

Thin FastAPI shell. Two routes:

- `GET /` → calls a handful of `data.py` functions, builds a context dict, renders `index.html`.
- `POST /api/refresh-mcp` → blocks on `data.refresh_mcp_servers_blocking()`, returns JSON. Triggered from `main.js` via `fetch()`.
- `GET /healthz` → trivial OK.

If you're adding new server-side logic, prefer to put data-fetching code in `data.py` and keep `server.py` to "call data, build context, render."

### `templates/index.html`

One file. No partials beyond what's already inline. Each section is a discrete `<div class="...">` block. Order matches the README's "Sections rendered" list.

### `static/css/main.css`

CSS-variable driven. Two roots:
- `:root { ... }` — light-mode palette
- `html[data-theme="dark"] { ... }` — dark-mode overrides

Adding new components: don't hardcode colors; use the variables. Hardcoded whites need explicit `html[data-theme="dark"]` overrides further down (see existing patterns for `.conn-pill`, `.atrium-skill`).

### `static/js/main.js`

Three behaviors. All vanilla JS, no framework:
- **Skill cards** — `.atrium-skill` click handler that copies `"claude -p " + shellEscape(prompt)` to clipboard.
- **Theme toggle** — flips `data-theme` on `<html>`, persists in `localStorage` under key `ai-theme`. Initial value is set by an inline script in `<head>` *before* first paint to avoid flash.
- **MCP refresh** — `fetch("/api/refresh-mcp", {method: "POST"})`, then `location.reload()` after toast.

---

## Recipes for common requests

### Recipe: "Specialize this for [niche]"

The user wants the dashboard to feel like it was built for their specific job (real estate, consulting, course creation, SaaS, dev work, etc.).

**What to change:** only `config.py`'s `SKILLS` list. Nothing else. The framework doesn't care what the prompts say.

**Steps:**
1. Read the user's `config.py` to see the current SKILLS.
2. Ask the user 1–2 questions if you don't already know:
   - "What are the 5–8 things you do in [niche] over and over that you'd want a one-click prompt for?"
   - "Which of these need input from you each time (a topic, a question), and which run on a fixed prompt?"
3. Write replacement skill entries. Each entry needs `label`, `prompt_template`, `description`, `category`, optional `input_placeholder`.
4. Categories are visual groupings only. Use `daily` for routine-style skills (gets a `routine` pill), `vault` for content/research, `tools` for utilities. You can add new categories — they'll auto-render with the category name as the heading.
5. Show the user the diff. Don't replace skills they've explicitly customized unless asked.

**Important:** keep the `"Act autonomously. Do not ask for confirmation. Do not use AskUserQuestion."` preamble in any prompt that you'd want to fire as a scheduled routine. Without it, Claude Code may pause mid-run waiting for input.

### Recipe: "Add a fourth/fifth gauge"

The user wants a new metric at the top of the page (e.g., GitHub commits today, Pomodoros done, weekly word count).

**Steps:**
1. In `data.py`, add a function that returns `{pct, value_str, label, reset_str}` for the new metric.
2. Add a new dict to the list returned by `data.status_strip_data()`.
3. Done. The status strip auto-renders all cells via `mini_ring_svg(c["pct"])`. CSS handles up to 5+ cells via `grid-template-columns: repeat(auto-fit, minmax(150px, 1fr))`.

If the data lives in an external service (GitHub API, RescueTime, etc.), follow the existing `fetch_anthropic_usage` pattern — disk-cache with stale-while-revalidate so you don't slow the page render with a network call.

### Recipe: "Add a new section"

The user wants a new band (e.g., "GitHub PRs", "Linear tickets", "Daily journal entries").

**Steps:**
1. **`data.py`** — write a new reader function. Return a list of dicts with whatever fields you need.
2. **`server.py:index()`** — call your new function, add the result to the template context dict.
3. **`templates/index.html`** — add a new block. Most sections use the `section-band` pattern (top border, eyebrow, sub, list). Copy the Vault Pulse block as a template.
4. **`static/css/main.css`** — only needed if your section needs styles beyond what's already there. Reuse `.aside-dispatch` rows for list items; reuse `.dispatches-full-eyebrow` for the section heading.

If the section is async (loading from an API), prefer rendering on the server and letting the page auto-refresh handle freshness. There is no client-side data fetching pattern in this codebase — keep it that way unless the user explicitly asks for live updates.

### Recipe: "Make a skill that takes input"

Already supported. Add `{input}` anywhere in the `prompt_template`, and add an `input_placeholder` field. The card renders an `{input}` pill, and clicking copies the command verbatim with `{input}` still in it — the user replaces it in their terminal before running. **Do not bring back the `window.prompt()` flow** — the user explicitly asked us to remove it.

### Recipe: "Change the color palette"

Only edit `:root` (light) and `html[data-theme="dark"]` (dark) blocks at the top and bottom of `main.css`. Don't touch the per-component rules. The variables (`--bg`, `--fg`, `--accent`, `--accent-soft`, `--ring-soft`, `--ring-mid`, etc.) propagate everywhere.

If the user wants a non-Atrium aesthetic, the design system is small enough to overhaul in one pass: change the CSS variables, swap the fonts in `templates/index.html` `<link>`, optionally adjust the masthead `border-bottom` thickness, and you're 80% done.

### Recipe: "Bring back live in-browser runs"

The dashboard used to run skills via subprocess and stream output to the browser. We removed it because Streamlit was making it fragile. To re-add:

1. New `data.py` runner module that spawns `subprocess.Popen` and reads `stdout`.
2. New `server.py` route `GET /api/run/{skill_id}` that returns a `StreamingResponse` (Server-Sent Events).
3. New `main.js` `EventSource` connection that updates a "running" panel.
4. Resist any temptation to put the output inside the existing skill cards — keep it in a dedicated panel so the layout stays stable.

Estimate: ~150 lines of new code total. Ask the user before doing this — it adds significant complexity and the current copy-to-clipboard model has been deliberately preferred.

### Recipe: "Add a new MCP-data source"

The connections strip just shows `claude mcp list` output. To pull richer info from a specific MCP server (e.g. show the user's open issues from a Linear MCP server), you'd:

1. Use `ListMcpResourcesTool` and `ReadMcpResourceTool` to query that specific server during a Claude Code session and confirm what data is available.
2. Decide if it's worth adding a new section for it (most cases) or augmenting the existing connection pill (rare — only for status info).
3. Follow the "Add a new section" recipe with a reader that calls the MCP server.

---

## Things to NOT do

- **Don't introduce a JavaScript framework** (React, Vue, htmx, etc.). The whole point is "no build step." Vanilla JS only.
- **Don't add a database.** Everything is files; that's the design. If you need persistence, use a JSON or SQLite file in `.cache/`.
- **Don't add Streamlit, Gradio, or any other web UI framework.** This project was specifically migrated *off* Streamlit.
- **Don't import `data.py` functions into `templates/index.html` via Jinja imports** — pass everything through `server.py`'s context dict. Keeps the data layer testable.
- **Don't pre-fetch data on a background thread** unless the user explicitly asks. Page-render-on-demand is the model.
- **Don't add authentication or multi-user logic** unless the user explicitly asks. Single-user, localhost-only is the design.
- **Don't change `127.0.0.1` to `0.0.0.0` in the launchers** — leave LAN exposure as a manual edit so users do it consciously.
- **Don't bring back the mascot.** It was removed deliberately.
- **Don't touch `config.py` directly** unless asked. It's the user's personal config; modify `config.example.py` if you're updating the template, and tell the user to copy.

---

## Coding conventions in this repo

- **Python:** Python 3.10+, type hints on public functions, `from __future__ import annotations`, no third-party deps beyond what's in `requirements.txt`.
- **HTML:** Semantic where possible. `<details>`/`<summary>` for disclosures. `<button>` for interactive elements (not styled `<div>`s). One template file.
- **CSS:** All colors are CSS variables. Class selectors over tag selectors. No inline styles in templates except for SVG-driven dynamic widths/dasharrays.
- **JS:** No transpiler. ES2020 features OK (arrow funcs, async/await, template literals, optional chaining, nullish coalescing). No bundler.
- **Comments:** prefer self-documenting names. Add comments for *why*, not *what* (e.g., "we cache because the call takes 5–10s cold," not "this is a cache").
- **Don't add unrelated changes.** If the user asks to add a gauge, just add the gauge. Don't reformat unrelated CSS, don't bump dependency versions, don't refactor adjacent code "while you're here."

---

## What to verify before reporting "done"

1. The dashboard still loads — `curl http://127.0.0.1:8501/` returns 200.
2. Whatever you changed renders — count the relevant DOM elements (`grep -c "<div class=\"my-new-thing\""`) and confirm.
3. Both light and dark mode look right — toggle the masthead theme link.
4. No console errors — JS-heavy changes only.

If the dashboard is already running with `--reload`, file edits hot-reload automatically. If not, restart with `python -m uvicorn server:app --host 127.0.0.1 --port 8501 --reload`.
