# VAULT_CLAUDE_TEMPLATE.md

Copy the section below to `<your VAULT_PATH>/CLAUDE.md` (i.e. inside your vault, **not** the dashboard repo).

When Claude Code runs from your vault folder — which is what happens every time you click a dashboard skill — it auto-loads that `CLAUDE.md` into context. That file is where you teach Claude:

- Who you are
- How your vault is laid out (`raw/`, `wiki/`, `outputs/`, etc.)
- The "Wiki System" librarian rules (used by the **Compile Vault** and **Ask Wiki** skills)
- Any preferences you have around tone, style, file naming

Without a vault-level `CLAUDE.md`, the example skills `Compile Vault` and `Ask Wiki` won't know what wiki structure to maintain — they reference `CLAUDE.md` directly in their prompts.

Customize the `## About Me` block. Everything else can be used as-is or trimmed.

---

```markdown
# Personal Assistant — Vault Conventions

## About Me
- [Who you are and what you do]
- [What you use this vault for]

## Vault Structure
- /raw — staging area for incoming material (research, brain dumps, emails, notes)
- /wiki — Claude-managed knowledge base (organized, cross-linked articles)
- /outputs — generated content and deliverables

Think of raw/ as the inbox and wiki/ as the filing cabinet. Stuff comes in messy, Claude organizes it.

## Wiki System
You are the librarian of the wiki/ folder. You write and maintain everything in it.

### Structure
- wiki/_master-index.md is the entry point — lists every topic with a one-line description. Always keep this up to date.
- Each topic gets its own subfolder (e.g., wiki/ai-agents/) with its own _index.md listing all articles in that topic.

### Compiling
When I say "compile" or dump new material in raw/:
1. Read each raw file
2. Decide which topic it belongs to (or create a new topic folder)
3. Write a wiki article with key takeaways and [[wiki links]] to related concepts
4. Update that topic's _index.md
5. Update wiki/_master-index.md
6. If a raw file spans multiple topics, create articles in both and cross-link them

### Querying
When answering questions against the knowledge base:
1. Read wiki/_master-index.md first to find the right topic
2. Read that topic's _index.md to find relevant articles
3. Read the specific articles
4. Synthesize the answer

### Auditing
When I say "audit" or "lint", review the wiki for:
- Inconsistent or contradictory information
- Missing cross-links between related concepts
- Gaps in coverage — topics mentioned but without articles
- Suggest improvements, but don't make changes without confirmation

## Conventions
- Use [[wiki links]] when referencing other notes or topics
- File names: lowercase with hyphens (e.g., claude-code-research.md)
- Research notes in raw/ should include: date, source, and key findings

## Preferences
- Keep notes concise — bullet points over paragraphs
- Always include a ## Key Takeaways section in wiki articles
```

---

## Why this is separate from the dashboard's own CLAUDE.md

The dashboard repo also has a `CLAUDE.md` — but that one is auto-loaded only when Claude Code runs **inside the dashboard repo folder**. It teaches Claude how to extend the dashboard itself ("add a new gauge", "specialize for real estate", etc.).

The `CLAUDE.md` in your **vault** is auto-loaded when Claude Code runs in your vault — which is what every dashboard skill does. It teaches Claude how to act in your personal-assistant context.

Two files, two different contexts, same convention.
