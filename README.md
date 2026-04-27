# Agent Infrastructure

**Your self-hosted agent infrastructure.** Built on Claude Code with optional Google Workspace integration (Gmail, Calendar, Drive, Docs). Ships with curated routines, a live cockpit dashboard you can use yourself or show clients, and a customization framework. Specialize it for any vertical — runs entirely on your machine, no SaaS.

Three layers, all in one repo:

- **Routines** — copy-to-clipboard skill cards that fire `claude -p '<prompt>'` commands. Curated for personal-assistant work out of the box; customizable for any niche in 5 minutes.
- **Cockpit dashboard** — a live, read-only view of your Claude Code usage (rate-limit gauges, activity chart, forecast), your MCP connections, your vault's recent activity, and your routine catalog. Use it yourself or share the screen with clients.
- **Customization framework** — small, explicit code (~1,200 lines total) you can extend. Add gauges, swap palette, wire new data sources, or specialize the whole surface for a niche.

```
~/.claude/projects/        →  GAUGES + ACTIVITY CHART
config.py SKILLS  ←──── click ──→  copies `claude -p '<prompt>'` to clipboard
~/.claude/.credentials      →  Sonnet / Claude Design utilization
your vault folder           →  VAULT PULSE
.cache/mcp_list.json        →  CONNECTIONS strip
```

The dashboard is a **passive monitor** — it reads files; it doesn't run Claude. You stay in your terminal where Claude Code is meant to live, and the cockpit gives you the bird's-eye view alongside it.

## What the dashboard shows you

- **Status strip** — five mini-rings: 5-hour window, 7-day window, today's routines, Sonnet-only utilization, Claude Design utilization. The first three are computed locally from your real transcripts; the last two come from Anthropic's OAuth usage endpoint when your plan exposes them.
- **Skills & workflows** — a grouped grid of every routine in your `config.py`. Click → command copies to clipboard. Cards with a `{input}` pill expect a placeholder fill.
- **Connections** — pills for every MCP server in your local cache. A `↻ refresh` button shells out to `claude mcp list` on demand (slow, ~5–10s).
- **Dispatches** — today's dashboard runs (if you keep `dashboard-runs/` in your vault).
- **Vault Pulse** — last 8 files touched in your vault, with verb (created / appended / linked / updated) and folder.
- **The Long View** — Forecast (5-hour window projection with NOW marker), Last 7 days (vertical bars), Cumulative activity (30-day line chart).
- Light / dark theme toggle in the masthead.

Built with FastAPI + Jinja templates + a single CSS file. ~1,200 lines of code total. No build step, no JS framework, no database.

## Prerequisites

Two things you install once, before doing anything else with this repo. Both have official installers — follow their docs.

| | Required | How to verify |
|---|---|---|
| **Python** ≥ 3.10 | yes — the dashboard is Python | `python --version` |
| **Claude Code CLI** | yes — Claude runs the setup AND populates the gauges | `claude --version` |

Optional, only if you want the matching feature:

| | Optional for | Notes |
|---|---|---|
| Node.js + [Google Workspace CLI](https://github.com/googleworkspace/cli) | The example Gmail / Calendar / Drive skills | Walkthrough in [GWS_SETUP.md](GWS_SETUP.md). About 30 minutes. |
| [Obsidian](https://obsidian.md) | Vault-link clicks opening notes natively | Without it, links still display — they just don't open anything. |
| MCP servers (set up via Claude Code) | A populated Connections strip | `claude mcp list` shows what you have. |

You don't need an Anthropic API key — Claude Code is the intelligence layer and authenticates separately.

## Quickstart — let Claude do everything

You don't have to know anything technical. After installing Python and Claude Code (one-time, links below), the entire setup is a conversation:

```bash
git clone https://github.com/ai-blueprint-dev/agent-infrastructure.git
cd agent-infrastructure
claude
```

Then in the Claude Code session that opens, say:

> *"set up this dashboard"*

Claude takes over from there. It:

- Checks you have everything you need (Python, optionally Node.js for Google Workspace)
- Asks where your vault should live
- Asks your Anthropic plan
- Asks if you want the Google Workspace skills working
- **If yes**, walks you through the full Google Cloud setup step-by-step (project creation, OAuth, billing, APIs, gws install, sign-in, optional Model Armor) — about 30 minutes of clicking, but Claude tells you exactly what to click at every step.
- **If no**, finishes the dashboard config in 30 seconds.
- Writes all the config files for you. Copies the bundled skills into your vault. Drops a starter `CLAUDE.md` into your vault root.

**You never type a Python command, edit a file, open a `.py` extension, or read a setup script.** Plain English the whole way through.

When setup finishes, **Claude launches the dashboard for you and opens it in your browser** at `http://127.0.0.1:8501`. No double-click needed.

Claude also asks if you want the dashboard to **auto-start every time you log in** — if you say yes, it sets up Task Scheduler (Windows), launchd (Mac), or systemd (Linux) for you. After that, the dashboard is always live at `http://127.0.0.1:8501` without you ever touching anything.

If you didn't pick auto-start: relaunch later by double-clicking `start.bat` (Windows) or `start.sh` (Mac/Linux), or by opening Claude Code in this folder and saying *"start the dashboard."* The dashboard auto-refreshes every 60 seconds.

### What if I want to know exactly what Claude is doing?

Everything Claude runs during setup is documented in plain English:

- Dashboard config + skill bundling: see the `.claude/skills/setup-dashboard/SKILL.md` file in this repo (it's the script Claude follows)
- Google Workspace setup: see [GWS_SETUP.md](GWS_SETUP.md) (the same content, but written for humans to read directly)

Both contain the same instructions — Claude just runs them as a conversation instead of leaving you to follow a manual.

### Localhost-only by default

The dashboard binds to `127.0.0.1`. That's the localhost address — only your machine can reach it. Other devices on your wifi cannot. To expose to your LAN, change `--host` to `0.0.0.0`. **Don't do this on public wifi**: the dashboard reads from `~/.claude/` and there is no auth.

## Architecture map

```
agent-infrastructure/
│
├─ server.py              FastAPI entry. One route (/), one POST endpoint
│                         (/api/refresh-mcp), Jinja template renderer.
│                         ≈ 160 lines. The thinnest layer in the app.
│
├─ data.py                All file-reading and transformation logic.
│                         No web framework imports. Pure functions you
│                         can unit-test directly.
│                         ≈ 700 lines. Where you'll add new sections.
│
├─ config.py              YOUR machine config (gitignored). Paths, plan
│                         tier, and the SKILLS list.
├─ config.example.py      Template. Users copy → edit.
│
├─ templates/
│   └─ index.html         The whole page. One file, no build step.
│
├─ static/
│   ├─ css/main.css       Atrium / Terracotta palette + every component
│   │                     style. CSS variables drive light & dark mode.
│   └─ js/main.js         Copy-to-clipboard, theme toggle, MCP refresh.
│                         ≈ 90 lines, no framework.
│
├─ requirements.txt       fastapi, uvicorn, jinja2. That's it.
├─ start.bat / start.sh   One-click launchers (open browser + run server)
│
├─ README.md              You are here.
└─ CLAUDE.md              Auto-loaded by Claude Code. Architectural map +
                          extension recipes for when users say things like
                          "specialize this for real estate" or "add a
                          fourth gauge."
```

### Data flow

```
   ~/.claude/projects/<sess>.jsonl    config.py (SKILLS, LIMITS)
          │                                   │
          │  read transcripts                 │ static
          ▼                                   ▼
       data.py  ────────────────────────►  server.py
       (gauges, dispatches,                (route handler)
        vault pulse, forecast)                   │
                                                 ▼
                                          templates/index.html
                                                 │
                                                 ▼
                                            HTML to browser
```

Every read is on-demand at request time. There is no background worker, no queue, no database. If something looks wrong on the dashboard it's because the underlying file changed — fix the file, refresh the page.

## Wire up Claude Code

Without Claude Code, the dashboard renders but every gauge sits at 0 — there's nothing to read.

1. Install Claude Code: see the [official install guide](https://docs.claude.com/claude-code).
2. Sign in: `claude` then follow the OAuth flow. Once.
3. Run any session: open `claude` in any folder, ask it anything, exit. This populates `~/.claude/projects/` with your first transcript.
4. Refresh the dashboard. Gauges fill in.

Set `CLAUDE_PLAN` in `config.py` to your tier so the gauge ceilings are accurate (`pro`, `max_5x`, `max_20x`, `team`, `enterprise`).

## Wire up GWS CLI (for the example Google Workspace skills)

The example `config.py` ships with five Google-Workspace-flavored skills (Morning Brief, Inbox Snapshot, Today's Agenda, Meeting Prep, Weekly Digest) that run through Google's official [Google Workspace CLI](https://github.com/googleworkspace/cli) — `gws`. They give Claude Code direct access to your Gmail, Calendar, Drive, Docs, and Sheets.

**This is optional.** If you don't use Google Workspace, replace those skills in `config.py` with prompts that match your stack — the dashboard's framework doesn't care what the prompts do.

If you do want them working, the setup takes about 30 minutes end-to-end and is documented in detail in **[GWS_SETUP.md](GWS_SETUP.md)**. The short version:

1. Install the CLI: `npm install -g @googleworkspace/cli`
2. Create a Google Cloud project, enable the APIs (Gmail, Calendar, Drive, Docs, Sheets, Model Armor).
3. Configure the OAuth consent screen (**External** for `@gmail.com`, **Internal** for Google Workspace domains — *External users must publish the app to avoid 7-day token expiry*).
4. Create a Desktop OAuth client, download the JSON, rename to `client_secret.json`, save to `~/.config/gws/client_secret.json`.
5. `gws auth login`
6. Install the recommended skill set inside your `VAULT_PATH/.claude/skills/` — *not all 100+, that exceeds Claude Code's skill budget*.
7. *(Recommended)* Set up Model Armor for prompt-injection protection — free for typical personal use.

### Sandbox vs Full Access

You can connect either your main Google account (Full Access — simplest) or a separate sandbox Google account that you share specific calendars / Drive folders / forwarded emails into (Sandbox — significantly safer). Both paths use identical setup steps; the only difference is which Google account you sign in with. **GWS_SETUP.md** walks through both.

### Vault-level CLAUDE.md (required for Compile Vault / Ask Wiki)

Two of the example skills — **Compile Vault** and **Ask Wiki** — reference a `CLAUDE.md` file in your `VAULT_PATH` that defines your vault's "Wiki System" conventions (how to organize `raw/`, `wiki/`, `outputs/`, etc.). Copy [VAULT_CLAUDE_TEMPLATE.md](VAULT_CLAUDE_TEMPLATE.md) into `<VAULT_PATH>/CLAUDE.md`, fill in the `## About Me` block, and you're set. Without this file, those two skills won't know what structure to maintain.

### More skills

The Google Workspace CLI ships 100+ skills total — the dashboard's defaults use ~13 of them. You can browse the rest at [github.com/googleworkspace/cli/tree/main/skills](https://github.com/googleworkspace/cli/tree/main/skills).

For curated dashboard-flavored skill bundles (vertical-specific packs, premium routines, community-built extensions), see the **Skills module** in the [AI Blueprint Skool community](https://www.skool.com/theaiblueprint). New packs are published there as they ship.

## Wire up Obsidian (optional)

Obsidian is only used to make vault links *clickable*. If you don't have Obsidian installed, every other part of the dashboard works fine — the links just won't navigate.

If you do:
1. Install [Obsidian](https://obsidian.md).
2. Open your vault inside Obsidian once, so it registers with the OS URI handler.
3. Set `VAULT_NAME` in `config.py` to **exactly** the name Obsidian shows for the vault. Case sensitive.
4. The Vault Pulse and Dispatches sections now have `obsidian://open?vault=<VAULT_NAME>&file=<path>` links. Click → Obsidian opens the note.

## Customizing the cockpit

This is where the project gets interesting. The dashboard is built as a starter, not a finished product. Two axes of customization: **vertical** (specialize the surface for a specific niche) and **horizontal** (extend the framework with new capabilities).

### Vertical — specialize for your niche

The 10 example skills are personal-assistant-flavored. **None of that is hardcoded.** `config.py` is just a Python list of dicts. Replace the entries and the dashboard transforms into a niche-specific cockpit without changing a single line of design or framework code.

You're not confined to the categories below — they're meant to spark ideas about *where* this can go:

- **Real estate** — listing-research, comp-analysis, neighborhood-deep-dive, client-followup-drafter, weekly-pipeline-summary.
- **Consulting** — prospect-research, meeting-prep, proposal-drafter, weekly-status-roundup, post-mortem-synthesizer.
- **Course creator / educator** — lesson-outline, module-summary, FAQ-batch, content-calendar, student-feedback-rollup.
- **SaaS founder** — competitor-scan, customer-quote-roundup, churn-investigation, weekly-metrics-pull, support-ticket-triage.
- **Developer / agency** — pr-summary, dependency-audit, error-log-triager, weekly-deliverable-rollup, infra-status-check.
- **Knowledge worker / writer** — daily-research-digest, source-fact-checker, draft-outliner, citation-roundup, brain-dump-organizer.

Anything you'd otherwise prompt-and-paste into Claude Code repeatedly is a candidate. Each skill is a label + description + prompt template. Five minutes of editing `config.py` is enough to flip the dashboard from one niche to another.

**Pre-built skill packs.** The [AI Blueprint Skool community](https://www.skool.com/theaiblueprint) Skills module publishes curated skill packs you can drop straight into your `config.py` (and the matching `gws-*` or other CLI skills into `<VAULT_PATH>/.claude/skills/`). Niche packs ship as they're built — that's the place to grab vertical-specific bundles instead of authoring everything yourself.

### Horizontal — extend the framework

If you want the dashboard to *do more* (more sections, more gauges, more behaviors), the codebase is intentionally small and explicit so you can extend with an LLM coding assistant. Every extension point lives in a single, predictable place:

| You want to | Edit | Roughly |
|---|---|---|
| Change a skill | `config.py` SKILLS list | one dict |
| Change the palette / fonts | `static/css/main.css` `:root` and `[data-theme="dark"]` | CSS variables only |
| Change the masthead text | `templates/index.html` `.cpt-masthead` block | one block |
| Add a new section | new function in `data.py` + new block in `index.html` + matching styles | three small edits |
| Add a new gauge to the status strip | add a new dict to `data.status_strip_data()` returns | one block |
| Wire up a new data source | new reader function in `data.py`, called from `server.py:index()` | mostly `data.py` |
| Add live streaming back | new SSE endpoint in `server.py`, JS `EventSource` in `main.js` | server + 30 lines JS |
| Multi-user / hosted | swap localhost binding, add login layer (FastAPI middleware), per-user `~/.claude` paths | larger project |

The dashboard ships read-only and single-user on purpose — that's the hardest mode to *break*. Everything beyond that is opt-in, and CLAUDE.md walks Claude Code through each one when you ask.

## Theme

Light by default. Toggle in the masthead (`☾ dark`). Choice persists in localStorage. Honors `prefers-reduced-motion` for users who disable animations at the OS level.

## Refreshing the MCP connections list

The Connections pills read from `.cache/mcp_list.json`. The `↻ refresh` button next to the section runs `claude mcp list` in the background and writes the result back to the cache (5–10 seconds). The page reloads when it's done.

If the strip stays empty after refresh, run `claude mcp list` in a terminal — if you get errors there, the dashboard is correctly reflecting reality (you have no connections set up). The dashboard doesn't *make* MCP servers work; Claude Code does.

## Troubleshooting

**Page loads but gauges are zero**
Your `~/.claude/projects/` folder has no transcripts yet. Run any Claude Code session, then refresh. If you've been using Claude Code for a while and it's still zero, your transcripts may live elsewhere — check `SESSION_META_DIR` in `config.py`.

**`uvicorn: command not found`**
Use `python -m uvicorn server:app --host 127.0.0.1 --port 8501` instead. Same effect.

**Sonnet-only / Claude Design cells missing from the status strip**
Your plan tier doesn't expose those sub-windows in the OAuth usage endpoint, or your `~/.claude/.credentials.json` is stale. Run `claude` once to refresh the credential.

**Browser keeps requesting `/_stcore/health` URLs**
You have an old Streamlit tab open. Close it. The previous version of this app was built on Streamlit; the new one is FastAPI.

**Port 8501 already in use**
Something else is on that port. Pick another: `--port 8502`. Update `start.bat` / `start.sh` to match if you use the launcher.

**Connections strip is empty after clicking refresh**
You don't have any MCP servers configured. Run `claude mcp list` in a terminal — same output. The dashboard mirrors reality.

**`claude -p` commands fail when pasted**
Most likely your shell isn't bash/zsh/PowerShell-with-bash. The shell-escaped quoting (`'\''` runs) needs a POSIX-style shell. On Windows, paste into Git Bash, WSL, or PowerShell — not classic `cmd.exe`.

## What is `claude -p`?

`-p` is short for `--print`. It runs Claude Code in **non-interactive mode**: takes the prompt, runs it once autonomously, prints the result, exits. Same engine as a regular interactive session — just one-shot.

That's why the skill cards copy a command rather than running anything: you stay in control. Paste the command into your terminal, watch it run, and the full transcript stays right there for you to scroll through.

The dashboard itself includes an expandable "What is `claude -p`?" panel with a plain-English explanation of when to use `claude -p` vs the interactive REPL vs the VS Code extension.

## License

MIT. Fork it, ship it, sell it built on top.
