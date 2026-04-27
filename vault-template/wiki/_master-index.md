# Wiki — Master Index

This is the entry point for your knowledge base. Claude (acting as your "librarian") maintains it.

Each topic lives in its own subfolder under `wiki/` with its own `_index.md` listing the articles in that topic. As you compile material from `/raw/`, this index updates with one-line descriptions of each topic.

## Topics

_(empty — add notes to `/raw/` and run the **Compile Vault** skill to populate this)_

---

## How this works

- Drop notes, research, brain dumps, emails into `/raw/` (use the **Capture** or **Research Topic** skill cards).
- Run **Compile Vault** when you want Claude to organize what's in `/raw/` into proper wiki articles.
- Run **Ask Wiki** to query your knowledge base — Claude reads this index first, navigates to the right topic, and synthesizes an answer with `[[wiki links]]` to cite sources.

The full rules for how Claude maintains the wiki are in your vault's `CLAUDE.md` file (in the vault root).
