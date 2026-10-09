---
name: zotero-ask
description: Ask Claude about papers in your Zotero library. It finds the PDF, answers with page numbers and quotes, and can leave grey AI highlights in Zotero. No web search, no database. Use when the user asks about a paper's content (methods, data, claims, figures, what a passage means), wants papers in their Zotero summarized or compared, or wants highlights on a PDF. Also use when the user says "set up zotero-ask". 問 Zotero 裡的論文內容、整理或比較文獻、在 PDF 上畫記時使用。
---

# zotero-ask: ask about papers in Zotero

Answer questions by reading the PDFs in the user's Zotero library. **No web search, no database.** Answers go in the chat; when an API key is set up, also leave grey highlights on the PDF; save a note only when asked.

**Language:** reply in the user's language. Highlight comments, highlight tags, notes and the summary line follow the same language; the English templates below only show the structure.

The tools are in `scripts/` inside this skill's folder (the base directory shown when this skill loads, written `<skill>` below). Use `python` on Windows and `python3` on macOS/Linux (written `PY` below):
- `Z` = `PY "<skill>/scripts/zot.py"` (reads Zotero PDFs, read-only)
- `A` = `PY "<skill>/scripts/zotann.py"` (writes grey highlights, needs an API key)

Write out each command in full; don't store a command in a shell variable (`Z=…; $Z find` fails in zsh).

If the first run fails (no Python, no `pymupdf`, no `zotero.sqlite`), go through **Setup** at the end first.

## 1. Find the paper

0. **Every time, start with `Z status`.** It shows whether the API key is set (decides section 4) and whether `zotero_ask_notes` is set (decides section 5).
1. `Z find "author keyword"` → **attachment key** (the PDF attachment's key, not the parent item's), title, authors.
2. Several matches: list them and ask the user to pick. None: say it isn't in Zotero and ask the user to add the PDF or give other keywords. **Stop there: don't search the web, and don't answer about the paper's content from memory**, even with a disclaimer.
3. Supplementary material is usually a separate attachment; `Z find` lists it too.

## 2. Read

- Locate first, then read: `Z grep <key> "regex"` finds the relevant pages, `Z page <key> <page>` prints a page. Read every page only when the user asks for a close reading or a full summary.
- To show the user the original: `Z open <key> <page>` opens that page in the Zotero reader.
- `Z notes <key>` lists the user's own highlights; use it when they ask "what did I highlight".

## 3. Answer (in the chat)

- Conclusion first, then evidence. Cite key sentences with **page and quote**: `p.5 "…original sentence…"`.
- Keep three things apart: **what the paper says**, **your inference** (label it "inference"), and **what the paper doesn't say** (say so; don't fill the gap).
- Comparing papers: find and cite each one separately, then sum up the differences in a table or list.
- End with one short line on what you did, e.g. `Read p.1–2, 5–7 | 3 grey highlights (p.5, p.7)`.

## 4. Grey highlights (when a key is set up; do it after answering, without asking)

No key (`Z status` says `not set`): skip this, and at the end of the first answer mention once that saying "set up zotero-ask" lets Claude highlight the PDF automatically. **Never work around a missing key**: don't draw on the PDF with other tools.

**Never write to the Zotero data folder**: no changes to files in `storage/`, to the PDFs or to `zotero.sqlite`. Highlights go only through `A add`, which uses the Zotero web API.

- Highlight the passages the answer relied on. **Whole passages**: context + claim + the authors' reasoning or caveats, usually 2–5 sentences; never across pages, never overlapping a neighbouring highlight. Only highlight what is genuinely useful.
- Always grey. The tag must be one of `claim`, `critique`, `method`, `data`, `todo`, `relevance` (the script adds the `AI/` prefix). For Chinese-speaking users use `論點`, `質疑`, `方法`, `數據`, `待查`, `本研究` instead.
- The comment says in a sentence or two why it was highlighted, starting with `[Q: short version of the question]`.
- Run `A list <key>` first to avoid duplicates. Only touch your own grey highlights, never the user's coloured ones.

Steps:
1. Write a JSON file to a temp location. `page` is the PDF page index starting at 1, not the printed page number. Copy sentences exactly from the PDF; write hyphenated line-break words in full, the script handles them.
   ```json
   [{"page": 5, "text": "sentence from the PDF", "tag": "data", "comment": "[Q: absorption rate] source of the 0.95 absorption figure"}]
   ```
2. Preview: `A add <key> <json>`; fix until nothing is reported as not found.
3. Write: same command with `--send`.
4. If the user wants them removed: `A delete <annotation key>... --send` (the script can only delete grey ones).

The attachment must be synced to zotero.org for the web API to find it; if the script warns it isn't synced, ask the user to sync Zotero and retry.

## 5. Save as a note (optional)

**Don't save by default.** Write the Q&A to Markdown only when:
- the user asks this time ("save this as a note", "write it to a md file"), or
- `Z status` shows `setting zotero_ask_notes: <folder>` with a non-empty folder; then save every answer there without asking. When the user says "always save notes to X", store it with `PY -c "import sys; sys.path.insert(0, r'<skill>/scripts'); import litcommon; litcommon.save_setting('zotero_ask_notes', r'<folder>')"`; when they say to stop, set it to an empty string.

No folder given: ask once where to save. One file per paper, named `FirstAuthor Year Short title.md`. Append new Q&As at the end of the same file; never rewrite old ones.

```markdown
# FirstAuthor Year Short title

> PDF attachment XXXXXXXX | Open in Zotero: zotero://open-pdf/library/items/XXXXXXXX

## Q&A

### YYYY-MM-DD Q: the user's question
- **Answer**: concise conclusion (a few sentences).
- **Evidence**: p.5 "quote"; p.7 Fig. 3.
- **Inference**: (if any)
- **Read**: p.1–2, 5–7
- **Highlights**: TMMF4ZKK, UB3PAREQ
```

## Setup (first use, or when the user says "set up zotero-ask")

Go one step at a time: check each step first and skip it if it's already done; when something is missing, give the user one action at a time. **An API key is a password: never ask the user to paste it into the chat**, and never print it.

1. **Python**: try `python --version`, `python3 --version`, `py --version` in order and use one that is ≥ 3.9. None: install from https://www.python.org/downloads/ (on Windows tick "Add python.exe to PATH" on the first screen, then restart Claude Code).
2. **PDF library**: `PY -m pip install --upgrade pymupdf`.
3. **Zotero data folder**: by default `Zotero/` in the home folder, containing `zotero.sqlite`. If it's elsewhere, ask the user to check Zotero Settings → Advanced → Files and Folders → Data Directory Location, then save it:
   `PY -c "import sys; sys.path.insert(0, r'<skill>/scripts'); import litcommon; litcommon.save_setting('zotero_dir', r'<path>')"`
   Test with `Z find a`; no error means it works.
4. **Zotero API key (optional, only needed for grey highlights)**:
   1. Check that Zotero Settings → Sync is signed in (syncing data is enough; files don't need to sync).
   2. Open the illustrated guide in the user's browser: `PY -c "import sys; sys.path.insert(0, r'<skill>/scripts'); import litcommon; litcommon.open_path('https://github.com/nebula0/zotero-llm-wiki/blob/main/docs/zotero-api-key.md')"`, and also give the link in the chat in case the browser doesn't open. Sum it up: go to https://www.zotero.org/settings/keys → "Create new private key", under Personal Library tick **Allow library access**, **Allow notes access** and **Allow write access** → Save Key.
   3. Save the key: **paste the command into a terminal without pressing Enter → copy the key from the web page → go back and press Enter** (the command reads the clipboard when Enter is pressed).
      - Windows (PowerShell): `New-Item -ItemType Directory -Force "$HOME\.config\zotero" | Out-Null; (Get-Clipboard).Trim() | Set-Content -NoNewline -Encoding ascii "$HOME\.config\zotero\api_key"`
      - macOS (Terminal): `mkdir -p ~/.config/zotero && pbpaste > ~/.config/zotero/api_key && chmod 600 ~/.config/zotero/api_key`
   4. Check: `PY -c "import sys; sys.path.insert(0, r'<skill>/scripts'); import zotann; print('Zotero user ID', zotann.user_id())"`; printing an ID means it worked.

Finish with a ✅/❌ checklist.
