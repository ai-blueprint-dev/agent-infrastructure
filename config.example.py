"""
Agent Infrastructure — user config template.

STEP 1: Copy this file to `config.py` in the same folder.
STEP 2: Edit the paths, plan, and SKILLS list below to match your setup.
STEP 3: Run the dashboard:
            Windows:    start.bat
            Mac/Linux:  ./start.sh
        Or run uvicorn directly:
            python -m uvicorn server:app --host 127.0.0.1 --port 8501

`config.py` is gitignored — your edits stay local and never get pushed.
"""

from pathlib import Path

# ───────────────────────────────────────────────────────────────
# PATHS — edit these to point at your own folders
# ───────────────────────────────────────────────────────────────

# Where Claude Code should run (its working directory) and where the
# dashboard scans for vault activity. Usually your Obsidian vault, a
# project folder, or wherever your skills expect to operate.
# Windows example: Path(r"C:\Users\YourName\Documents\my-vault")
# Mac / Linux:     Path("/Users/yourname/Documents/my-vault")
VAULT_PATH = Path(r"C:\Users\YourName\Documents\my-vault")

# Display name for the vault — shown in the masthead header.
# Also used to build Obsidian deep-links, so it must match your Obsidian
# vault name exactly if you want vault links to open in Obsidian.
VAULT_NAME = "my-vault"

# Full path to the `claude` executable.
# Find it with:
#   Windows:  where claude
#   Mac/Linux: which claude
# Windows example: Path(r"C:\Users\YourName\.local\bin\claude.exe")
# Mac / Linux:     Path("/usr/local/bin/claude")
CLAUDE_CLI = Path(r"C:\Users\YourName\.local\bin\claude.exe")

# Where skill runs get logged. Defaults below assume VAULT_PATH has these
# subfolders — change if you organize differently.
DAILY_NOTES_DIR = VAULT_PATH / "daily-notes"
RUNS_DIR = VAULT_PATH / "dashboard-runs"
DRAFTS_AWAITING = VAULT_PATH / "drafts" / "awaiting"

# ───────────────────────────────────────────────────────────────
# YOUR CLAUDE PLAN — single source of truth for gauge ceilings
# ───────────────────────────────────────────────────────────────
# Options: "pro" | "max_5x" | "max_20x" | "team" | "enterprise"
#   "max" is a legacy alias for "max_5x".
CLAUDE_PLAN = "pro"

# Per-plan rate-limit caps (best-effort estimates of Anthropic's quotas).
# Cache reads count at full weight in the 5h and weekly token totals.
PLAN_LIMITS = {
    "pro":        {"five_hour_tokens":   5_000_000, "weekly_tokens":   50_000_000, "daily_routine_runs":  5},
    "max_5x":     {"five_hour_tokens":  25_000_000, "weekly_tokens":  880_000_000, "daily_routine_runs": 15},
    "max_20x":    {"five_hour_tokens": 100_000_000, "weekly_tokens": 3_500_000_000, "daily_routine_runs": 25},
    "team":       {"five_hour_tokens":  25_000_000, "weekly_tokens":  880_000_000, "daily_routine_runs": 25},
    "enterprise": {"five_hour_tokens": 100_000_000, "weekly_tokens": 3_500_000_000, "daily_routine_runs": 25},
    "max":        {"five_hour_tokens":  25_000_000, "weekly_tokens":  880_000_000, "daily_routine_runs": 15},  # legacy alias
}

LIMITS = PLAN_LIMITS.get(CLAUDE_PLAN, PLAN_LIMITS["pro"])

# How long to let a skill run before killing it (seconds).
RUN_TIMEOUT_SEC = 900

# Claude Code permission mode. Options:
#   "bypassPermissions" → no prompts, Claude runs freely (convenient, riskier)
#   "default"           → Claude prompts for each tool use (safer, slower)
PERMISSION_MODE = "bypassPermissions"

# Path to Claude Code's per-session usage data. /usage reads from here too.
# You should NOT need to change this unless Claude Code moved its data dir.
SESSION_META_DIR = Path.home() / ".claude" / "usage-data" / "session-meta"


# ───────────────────────────────────────────────────────────────
# SKILLS — the buttons on the dashboard
# ───────────────────────────────────────────────────────────────
#
# Each entry becomes a clickable button that runs `claude -p "<prompt>"`.
#
# Fields per skill:
#   label             — button text
#   prompt_template   — the prompt sent to Claude. Use `{input}` as a
#                       placeholder for any user-typed input; omit it for
#                       no-input skills.
#   description       — subtitle shown under the label
#   category          — "daily" or "content" (groups buttons visually)
#   input_placeholder — (optional) hint text for input box, only if the
#                       prompt_template contains `{input}`
#
# Pattern to keep things autonomous (no mid-run prompts):
#   "Act autonomously. Do not ask for confirmation. Do not use
#    AskUserQuestion. Run the /your-skill skill"
#
# Replace the examples below with your own Claude Code skills (or /commands).
# Delete any you don't use.
# ───────────────────────────────────────────────────────────────

SKILLS = [
    # ─── DAILY ROUTINES (Google Workspace flavour — see GWS_SETUP.md) ───
    {
        "label": "Morning Brief",
        "prompt_template": (
            "Run gws-workflow-standup-report to get today's calendar and open tasks, then "
            "gws-gmail-triage --max 10 for the latest unread emails. Synthesize into a single "
            "morning brief with sections: Today's Schedule, Open Tasks, Inbox Highlights "
            "(grouped urgent/today/can-wait). Save the result to daily-notes/<today's date>.md "
            "(append if the file already exists today)."
        ),
        "description": "Calendar + tasks + inbox → daily-notes/",
        "category": "daily",
    },
    {
        "label": "Inbox Snapshot",
        "prompt_template": (
            "Run gws-gmail-triage --max 10. Group the results by priority "
            "(urgent / today / can wait). For each: sender, subject, one-line summary, "
            "suggested action. Don't save — just show in chat."
        ),
        "description": "Triage latest 10 unread emails",
        "category": "daily",
    },
    {
        "label": "Today's Agenda",
        "prompt_template": (
            "Run gws-calendar-agenda for today and tomorrow. Format as a clean timeline with "
            "times, titles, locations, attendees. Don't save — just show in chat."
        ),
        "description": "Calendar — today and tomorrow",
        "category": "daily",
    },
    {
        "label": "Meeting Prep",
        "prompt_template": (
            "Run gws-workflow-meeting-prep to get the next upcoming meeting. Show: meeting "
            "time, attendees, description, linked docs. If there are recent emails with the "
            "attendees or relevant Drive docs in scope, surface those too. Save the brief to "
            "daily-notes/<today's date>.md under a 'Meeting Prep' heading."
        ),
        "description": "Brief for your next meeting → daily-notes/",
        "category": "daily",
    },
    {
        "label": "Weekly Digest",
        "prompt_template": (
            "Run gws-workflow-weekly-digest. Reformat as a digest with: total meeting count "
            "and rough hours, unread email count, key deadlines or decisions surfaced. Save "
            "the result to daily-notes/week-<today's ISO week>.md."
        ),
        "description": "This week's meetings + email rollup",
        "category": "daily",
    },

    # ─── VAULT / RESEARCH (Wiki System pattern — see VAULT_CLAUDE_TEMPLATE.md) ───
    {
        "label": "Capture",
        "prompt_template": (
            "Take this input: {input}\n\n"
            "Save it to raw/YYYY-MM-DD-<short-kebab-slug>.md. At the top, add YAML frontmatter "
            "with: capture date, 3-5 auto-tags based on content, and a 1-2 sentence summary. "
            "Then the original input verbatim below. Confirm where you saved it."
        ),
        "description": "Quick brain dump → raw/",
        "category": "vault",
        "input_placeholder": "anything — note, idea, observation",
    },
    {
        "label": "Research Topic",
        "prompt_template": (
            "Research the topic: {input}\n\n"
            "Use web search to find recent (last 12 months) information from multiple sources. "
            "Save findings to raw/YYYY-MM-DD-<topic-slug>.md with sections: Key Findings, "
            "Sources (with links), Contradictions/Gaps. Don't compile to wiki yet — that's a "
            "separate step."
        ),
        "description": "Multi-source web research → raw/",
        "category": "vault",
        "input_placeholder": "topic to research",
    },
    {
        "label": "Compile Vault",
        "prompt_template": (
            "Per the Wiki System rules in CLAUDE.md, read each file in raw/ that hasn't been "
            "compiled yet. Decide its topic, write or update the wiki article with key "
            "takeaways and [[wiki links]], update the topic's _index.md, and update "
            "wiki/_master-index.md. After compiling each raw file, append a "
            "'compiled-on: <date>' line to its frontmatter so it isn't reprocessed. "
            "Report what you compiled."
        ),
        "description": "raw/ → wiki/ via the librarian",
        "category": "vault",
    },
    {
        "label": "Ask Wiki",
        "prompt_template": (
            "Question: {input}\n\n"
            "Per CLAUDE.md, read wiki/_master-index.md first, navigate to the right topic's "
            "_index.md, then read the specific articles. Synthesize an answer with [[wiki links]] "
            "to cite sources. If the wiki doesn't have the info, say so clearly — don't make "
            "anything up."
        ),
        "description": "Query your knowledge base",
        "category": "vault",
        "input_placeholder": "what do you want to know?",
    },

    # ─── TOOLS (free-form) ───
    {
        "label": "Quick Prompt",
        "prompt_template": "{input}",
        "description": "Free-form prompt — Claude figures out the rest",
        "category": "tools",
        "input_placeholder": "type any prompt",
    },
]
