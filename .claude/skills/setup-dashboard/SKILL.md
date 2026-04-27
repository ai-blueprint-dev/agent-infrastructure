---
name: setup-dashboard
description: "End-to-end setup for the Agent Infrastructure project. Conversational, plain-English walkthrough that handles everything: checks prerequisites (Python, Node.js if needed), installs Python deps, writes config.py, copies bundled skills into the user's vault, sets up the vault CLAUDE.md, and optionally walks the user through the full Google Workspace CLI setup (Google Cloud project, OAuth consent screen, OAuth client, gws install, gws auth login, Model Armor). The user never touches a Python file or types a setup command — they just answer questions."
metadata:
  version: 2.0.0
---

# Agent Infrastructure — Full Setup

Run this skill when the user has just cloned the agent-infrastructure repo and wants the whole thing working. **This skill assumes the user is non-technical.** Talk them through it in plain English. Don't explain what `pip` or `npm` does — just run the commands and tell them what's happening.

The skill has three phases. Run them in order. **After each phase, tell the user what just happened in one short sentence.**

- **Phase 1 — Prerequisites check** (Python, Node.js if they want GWS, vault folder)
- **Phase 2 — Dashboard configuration** (config.py, skills, vault CLAUDE.md)
- **Phase 3 — Google Workspace setup** (optional, opt-in)

At the very end, tell them how to launch.

---

## Preflight

Before you say anything to the user, silently verify:

1. The current working directory contains `server.py` and `config.example.py`. If not, tell the user: *"Please open Claude Code from inside the agent-infrastructure folder and try again."* and stop.
2. Read `README.md` and `GWS_SETUP.md` so you have full context on what this project is and how the GWS flow works. You'll reference GWS_SETUP.md during Phase 3 instead of duplicating its instructions here.

Once preflight passes, greet the user:

> "Hey — I'll set up the Agent Infrastructure for you. This takes about 5 minutes if you only want the dashboard, or about 30 minutes if you also want the Google Workspace skills (Morning Brief, Inbox Snapshot, etc.) working. I'll walk you through every step. Ready?"

Wait for confirmation.

---

## Phase 1 — Prerequisites

### 1.1 Python

Run `python --version`. If exit code is 0 and version ≥ 3.10, tell them: *"Python ✓"* and continue.

If missing or older:

> "I need Python 3.10 or newer to run the dashboard. You don't have it (or your version is too old). Download it from https://python.org and run the installer. **Important — on Windows, tick the 'Add Python to PATH' box during install.** Tell me when you're done and I'll re-check."

Wait for them to confirm. Re-run `python --version`. If still failing, give specific debugging steps based on the error.

### 1.2 Claude Code

Already installed by definition (the user is talking to you through it). Skip.

### 1.3 Ask about Google Workspace

Before checking Node.js, ask the user:

> "Do you want the example Google Workspace skills (Morning Brief, Inbox Snapshot, Today's Agenda, Meeting Prep, Weekly Digest) to actually work? They need a Google account and about 30 minutes of setup. (y/n)"

Save their answer as `wants_gws`. If yes, continue with Node.js check. If no, skip to 1.5.

### 1.4 Node.js (only if `wants_gws == true`)

Run `node --version`. If exit code 0 and version ≥ 20, tell them: *"Node.js ✓"* and continue.

If missing:

> "The Google Workspace CLI runs on Node.js, which you don't have yet. Download Node.js v20 or newer from https://nodejs.org (the LTS version is fine). Tell me when you're done."

Wait for confirmation. Re-run `node --version`.

### 1.5 Vault folder

Ask:

> "Where do you want your 'vault' folder to live? This is where Claude does its work — your daily notes, research dumps, generated content, etc. If you use Obsidian, point me at your Obsidian vault. Otherwise just pick any folder. Default: `~/Documents/agent-infrastructure-vault`. Press Enter to accept the default, or paste a path."

Resolve `~` to their home directory. Make the path absolute. If it doesn't exist, create it with `mkdir -p`. Save as `vault_path`.

---

## Phase 2 — Dashboard configuration

### 2.1 Confirm what comes next

> "Now I'll set up the dashboard itself. This is fast — about 30 seconds."

### 2.2 Anthropic plan

Ask:

> "What's your Anthropic plan? Type one: `pro`, `max_5x`, `max_20x`, `team`, or `enterprise`. (This sets the ceilings on the rate-limit gauges. If you don't know, type `pro`.)"

Validate. If invalid, default to `pro` and tell them.

### 2.3 Auto-detect `claude`

Run `which claude` (Mac/Linux) or `where claude` (Windows). Save the path. If not found, tell them you need them to find it manually with `Get-Command claude` (PowerShell) or `which claude`. Don't ask them to guess.

### 2.4 Install Python dependencies

```bash
pip install -q -r requirements.txt
```

Tell them: *"Installing Python dependencies… done."*

### 2.5 Write `config.py`

If `config.py` already exists, tell them: *"You already have a config.py — leaving it alone. If you want to redo this, delete config.py and run me again."* and skip to 2.6.

Otherwise: read `config.example.py`. Replace these lines with the user's values:

| Find | Replace with |
|---|---|
| `Path(r"C:\Users\YourName\Documents\my-vault")` | `Path(r"<vault_path>")` |
| `VAULT_NAME = "my-vault"` | `VAULT_NAME = "<basename of vault_path>"` |
| `Path(r"C:\Users\YourName\.local\bin\claude.exe")` | `Path(r"<auto-detected claude path>")` |
| `CLAUDE_PLAN = "pro"` | `CLAUDE_PLAN = "<their plan>"` |

Write the result to `config.py`. Tell them: *"Configuration written ✓"*

### 2.6 Copy bundled skills into the vault

The repo's `skills/` folder contains 17 Claude Code skill folders. Copy each one into `<vault_path>/.claude/skills/`. Skip any that already exist (don't overwrite).

```bash
mkdir -p "<vault_path>/.claude/skills"
# then copy each skill subfolder; you can use cp -r or shutil.copytree
```

Tell them: *"Installed N skills into your vault."*

### 2.7 Copy the vault CLAUDE.md template

If `<vault_path>/CLAUDE.md` exists, leave it alone and tell them.

Otherwise: read `VAULT_CLAUDE_TEMPLATE.md`. Extract the markdown code block (between `` ```markdown `` and the closing `` ``` ``). Write that block to `<vault_path>/CLAUDE.md`.

Tell them: *"Created a starter CLAUDE.md in your vault. Edit the 'About Me' section anytime to teach Claude about you."*

---

## Phase 3 — Google Workspace setup (only if `wants_gws == true`)

If the user said no in 1.3, skip this entire phase and go to "Done."

This phase mirrors `GWS_SETUP.md` but turns it into a conversation. **Read `GWS_SETUP.md` thoroughly before starting** — it has every detail you need. Don't deviate from it; just translate it into "here's what to do, do it, tell me when you're back."

Walk them through these in order, one at a time, waiting for confirmation between each:

### 3.1 Path choice — Sandbox vs Full Access

Quote them this exactly:

> "Quick choice: do you want me to set this up against your **main Google account** (simpler, but Claude can read all your real Gmail / Drive / Calendar) or against a **separate sandbox Google account** you create just for this (safer, but you have to make and maintain a second account)?
>
> Most people start with their main account. We can switch to a sandbox later if you want. Type `main` or `sandbox`."

Save as `gws_mode`. If `sandbox`, tell them to create a new Gmail account now and confirm when they're signed into it.

### 3.2 Install the gws CLI

```bash
npm install -g @googleworkspace/cli
gws --version
```

If install fails on permissions, tell them to retry with `sudo npm install -g @googleworkspace/cli` (Mac/Linux) or run their terminal as administrator (Windows).

### 3.3 Walk through Google Cloud Console

Open https://console.cloud.google.com in their browser (use the Bash tool with `start` on Windows or `open` on Mac).

Now walk them through, **one tiny step at a time**:

1. **"Sign in with the account you chose."** Wait for confirmation.
2. **"Create a new project. Click the project dropdown at the top, then 'New Project'. Name it whatever — 'AI Assistant CLI' is fine. Click Create."** Wait. Then ask: *"What's the Project ID? It's in the project dropdown — looks like `ai-assistant-cli-438219`. Paste it."* Save as `gcp_project_id`.
3. **OAuth consent screen.** Walk them through `GWS_SETUP.md` Step 4 verbatim, including the External vs Internal nuance. **Critical reminder:** if External, they MUST publish the app or tokens die every 7 days.
4. **Create OAuth client.** `GWS_SETUP.md` Step 5. They download `client_secret_*.json`. You then tell them: *"Rename that file to exactly `client_secret.json` and move it to `~/.config/gws/client_secret.json`. Tell me when done."* Help them with the exact `mkdir` and `mv` commands for their OS.
5. **Enable billing.** `GWS_SETUP.md` Step 6 — link a billing account before enabling APIs.
6. **Enable APIs.** Walk through the list (Gmail, Drive, Calendar, Docs, Sheets, Model Armor). Tell them: *"For each one: search, click into it, click Enable, go back. Tell me when you've done all six."*

### 3.4 First sign-in

```bash
gws auth login
```

Their browser opens. Walk them through:
- Pick the Google account
- Approve the scopes
- See "Google hasn't verified this app" — tell them: *"Click Advanced → Go to (unsafe). It's your own app on your own account, totally normal."*
- Wait for "Authentication successful" in their terminal

Smoke test:

```bash
# Mac/Linux
gws gmail users messages list --params '{"userId": "me", "maxResults": 5}'
# Windows
gws gmail users messages list --params '{\"userId\": \"me\", \"maxResults\": 5}'
```

If they see emails, tell them: *"Google Workspace is wired up ✓"*. If they get a decryption error, run `npm install -g @googleworkspace/cli@latest` and re-try `gws auth login` — that bug was fixed in 0.10.0.

### 3.5 Sandbox sharing (only if `gws_mode == "sandbox"`)

Walk them through `GWS_SETUP.md` Step 8 — share calendar, Drive folder, optional email forwarding. One at a time.

### 3.6 Model Armor (recommended)

Ask:

> "Do you want to set up Model Armor? It scans data before Claude reads it, catching prompt-injection attacks. Free for typical use. (y/n)"

If yes, walk them through `GWS_SETUP.md` Step 10:
1. Create the template:
   ```bash
   gws modelarmor +create-template --project <gcp_project_id> --location us-central1 --template-id workspace-safety --preset jailbreak
   ```
2. Add the env vars to their shell profile (use the OS-specific commands from `GWS_SETUP.md`).
3. Tell them: *"Starting in `warn` mode for now. Once you've used it for a few days and trust it, ask me to flip to `block` mode."*

---

## Phase 4 — Launch the dashboard

### 4.1 Start the server in the background

Run the dashboard as a background process **using the Bash tool with `run_in_background: true`** so it survives this Claude Code session ending.

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8501
```

Wait 3 seconds, then verify it started by running `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501/`. If you don't get `200`, retry once. If still failing, tell the user the exact error from the server log.

### 4.2 Open the browser

Open the dashboard URL in their default browser:

- **Windows:** `start "" http://127.0.0.1:8501`
- **Mac:** `open http://127.0.0.1:8501`
- **Linux:** `xdg-open http://127.0.0.1:8501`

### 4.3 Confirm it's live

> "Your dashboard is live at http://127.0.0.1:8501 — I just opened it for you. Take a look."

### 4.4 Optional — auto-start on login

Ask:

> "Do you want this dashboard to launch automatically every time you log into your computer? That way it's always there at http://127.0.0.1:8501, no setup or click needed. (recommended — y/n)"

If yes, walk them through the OS-specific auto-start:

**Windows (Task Scheduler):**
1. Create a `.vbs` launcher next to `start.bat` that runs the bat hidden:
   ```vbscript
   CreateObject("Wscript.Shell").Run "<full path to start.bat>", 0, False
   ```
2. Create a Task Scheduler entry: Trigger = "At log on", Action = "Start a program" → the `.vbs` file. Run task as the current user.
3. Run the task once to confirm it works.

**Mac (launchd):**
1. Create `~/Library/LaunchAgents/com.aiblueprint.agent-infrastructure.plist` with:
   ```xml
   <plist><dict>
     <key>Label</key><string>com.aiblueprint.agent-infrastructure</string>
     <key>ProgramArguments</key><array>
       <string>/bin/bash</string>
       <string>-c</string>
       <string>cd <repo path> && ./start.sh</string>
     </array>
     <key>RunAtLoad</key><true/>
     <key>KeepAlive</key><true/>
   </dict></plist>
   ```
2. Run `launchctl load ~/Library/LaunchAgents/com.aiblueprint.agent-infrastructure.plist`.

**Linux (systemd user service):**
1. Create `~/.config/systemd/user/agent-infrastructure.service`:
   ```ini
   [Unit]
   Description=Agent Infrastructure dashboard
   [Service]
   WorkingDirectory=<repo path>
   ExecStart=/usr/bin/env python -m uvicorn server:app --host 127.0.0.1 --port 8501
   Restart=always
   [Install]
   WantedBy=default.target
   ```
2. Run `systemctl --user enable --now agent-infrastructure.service`.

After setting up auto-start, tell them:

> "Done — your dashboard will now start automatically every time you log in. If you ever want to undo this, just ask me to remove the auto-start."

If they say no, tell them:

> "OK — to relaunch the dashboard later (after a reboot, or if you've closed it), you can either:
> - Double-click `start.bat` (Windows) or `start.sh` (Mac/Linux), OR
> - Run `claude` here and ask me to start it again."

## Done

> "All set up. Your dashboard is running at http://127.0.0.1:8501.
>
> A few things you can do anytime:
> - Edit `<vault_path>/CLAUDE.md` to describe yourself — Claude reads it every time you click a skill button.
> - Add or remove skill buttons by asking me (I'll edit `config.py` for you).
> - Toggle the dashboard between light and dark mode using the link in the masthead.
>
> Anything else you want me to set up or customize?"

---

## Notes for you (Claude)

- **Plain English everywhere.** Don't say "shell command" — say "I'll run something for you." Don't say "Python module" — say "the dashboard." The user is non-technical; assume they don't know what `npm` or `pip` is.
- **One step at a time during the GWS browser walkthrough.** Do not give them a wall of "do all of this." They will get lost. Wait for confirmation between every navigation click.
- **Show progress as you go.** After each command runs successfully, print one short line: *"Installed dependencies ✓"* / *"Wrote config.py ✓"* etc. Builds confidence.
- **If anything fails**, stop and tell the user the specific error in plain English plus what to try next. Don't keep going with broken state.
- **Idempotent.** If they re-run this skill (because something went wrong, or they want to redo GWS), gracefully skip parts that are already done.
- **Don't suggest they run `python setup.py`** — that file was deleted. You ARE the setup.
- **Refer to `README.md` and `GWS_SETUP.md`** as authoritative references — read them at the start so you have full context, but don't dump them at the user.
- **Be encouraging when GWS gets long.** OAuth is genuinely 30 minutes of clicking. Acknowledge that, tell them they're 60% / 80% / done as you go.
