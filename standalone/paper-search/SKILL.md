---
name: paper-search
description: Find research papers with bibliographic data checked against OpenAlex, never made up. Checks your Zotero library first, marks papers you already have (★) and ones you excluded before (✗); can add papers straight into Zotero (with the open-access PDF when available) and keep a CSV log. Use when the user asks to find, search for or recommend papers or literature on a topic, wants a literature review starting point, wants to check a citation or DOI, or wants citation tracking (what a paper cites / what cites it). Also use when the user says "set up paper-search".
---

# paper-search: find papers you can trust

Search for papers, check every bibliographic detail against OpenAlex, and answer **in the chat**. Writing is optional: papers go into Zotero when the user asks, and into a CSV log when they set a folder.

**Language:** always reply in the language the user writes in, including tips, notices and the closing summary line. The English sentences in this file are examples of the content, not text to copy; translate them. Paper titles, venues and DOIs stay as published. The CSV columns and status values stay in English (`candidate`, `to-read`, `excluded`); `contribution` and `reason` follow the user's language.

The tool is `scripts/papers.py` inside this skill's folder (the base directory shown when this skill loads, written `<skill>` below). Use `python` on Windows and `python3` on macOS/Linux. Below, `P` = `python3 "<skill>/scripts/papers.py"`.

If the first run fails (no Python, no internet), go through **Setup** at the end first.

## Rules

1. **Bibliographic data comes from OpenAlex** (`P fetch`, `P search`, `P cites`), never from memory or search-engine snippets. If OpenAlex has no record of a paper, say so; don't fill in a DOI, year or venue yourself.
2. **Every paper you recommend gets one sentence on its main contribution**, followed by the basis for that judgment: `full text`, `abstract`, `secondary` (someone else's description, a search snippet) or `metadata only`. Papers with `metadata only` are candidates at most; don't call them must-cite.
3. **List the papers you excluded too**, each with a one-line reason.
4. **Respect the marks**: ★ = already in the user's Zotero, don't present it as new; ✗ = the user excluded it before, skip it unless asked (mention how many you skipped).
5. **Say how to get each paper's full text.** `P fetch` shows a free full-text link when one exists; give it. When there's none (`Free full text: none found`), the paper is most likely paywalled: tell the user plainly that they need to download it themselves through their institution's access (library website, campus network or VPN, or signing in on the publisher's site with their institution), and that Claude can't do this for them. Say this once, listing which papers it applies to, not after every paper.
6. **Don't download PDFs yourself** (no curl, no browser tools). The only download is `P add`, which attaches open-access PDFs when the user asks to add papers to Zotero.

## Searching

1. **Check the user's Zotero first** (skip if `P status` says Zotero isn't found): `P library "keywords"`, trying 2–3 keyword variants (synonyms, singular/plural, e.g. `metasurface` as well as `metamaterial`; every word must match, so use 1–2 words per query). What they already collected tells you:
   - which papers to show as "already in your Zotero" instead of recommending them as new;
   - which angle of the topic they actually work on (e.g. nonlinear metasurfaces *for optical neural networks*, not mechanical metamaterials). Aim the search at that angle;
   - good seeds for citation tracking (step 4).
2. **Understand the goal.** If the request is still vague after looking at their library, ask one question about what it's for (a thesis intro, a specific method, a review). Skip this when the goal is clear.
3. **New topic: start from reviews.** Find 2–4 highly cited reviews first; their sections tell you which sub-topics to search and their references are good seeds.
4. **Search one sub-topic per query**, look at the results, then decide the next query. Don't cram several ideas into one query.
   - Discovery: use web search with the field's own terms, then check each hit with `P fetch <DOI>`.
   - `P search "query" [--from YEAR] [--to YEAR] [--abs]` for OpenAlex keyword search, when you need result counts or a year range. Broad queries get flooded by general reviews; be specific.
   - Citation tracking from 1–2 core papers (from their Zotero when possible): `P cites <DOI> refs --abs` (what it cites) and `P cites <DOI> citedby --abs` (what cites it, most cited first). `citedby` on a paper they already have is the best way to find newer work in their exact niche.
5. **Read the abstract before judging** (`P fetch <DOI>`). No abstract anywhere: basis is `metadata only`, still list it as a candidate; don't drop it just for that.
6. **Answer in the chat:**
   - **Already in your Zotero** (when relevant ones exist): a short list, one line each, so the user sees what they have. Don't re-recommend them below.
   - New papers worth reading, most useful first: `Author et al. (Year). Title. Venue. DOI` + contribution (basis) + why it fits the user's goal. Mark ★ ones as already in Zotero.
   - Excluded papers, one line each with the reason.
   - Which 2–3 to read first, the free full-text links, and the paywall notice from rule 5 for those without one.
   - One closing line on what you did, e.g. `4 queries, 2 citation tracks | 9 kept, 5 excluded, 3 already in Zotero`.

Web search ranking is opaque and not reproducible; don't present results as a systematic review.

## Remembering (optional log)

`P status` shows whether a log folder is set.

**No folder set:** at the end of the **first** search in a conversation, add one line (in the user's language), then don't repeat it:
> Want me to remember these? Say "save my searches to <folder>" and next time I'll mark papers you've already seen or excluded.

Also offer it when the user rejects a paper ("not this one", "that's off topic"): ask once whether to remember it so it's skipped next time.

**Setting the folder:** when the user names one, run `P folder "<path>"`. To stop: `P folder ""`.

**Folder set:** after each search, save what you listed without asking:
1. Write a JSON file to a temp location (bibliographic fields are filled in from OpenAlex automatically, don't include them):
   ```json
   [{"doi": "10.1016/j.coco.2018.05.001", "status": "candidate", "contribution": "Review of porous sound absorbers by material type", "basis": "abstract", "query": "porous sound absorption review"},
    {"doi": "10.1016/j.apacoust.2020.107845", "status": "excluded", "reason": "Sponge composite, outside the user's scope", "basis": "abstract"}]
   ```
   No DOI: use `"openalex": "W123..."` instead.
2. `P save <file>`. It refuses the whole batch if anything is invalid; fix and rerun.
3. When the user says "I'll read this one" → `status: to-read`; "drop this one" → `status: excluded` with their reason. Only the fields you give are updated.

The log is `<folder>/papers.csv`, one row per paper. Tell the user they can open it in Excel/Numbers/Google Sheets, and that changing a row's `status` to `excluded` there works the same as telling you. If saving fails because the file is open in Excel, ask them to close it.

## Adding to Zotero

Only when the user asks ("add these to Zotero", "save #1 and #3"); never add on your own.

1. `P add <DOI> <DOI>...`, or with no DOIs to add the log's `candidate` and `to-read` papers (`--status to-read` for just those). Bibliographic data comes from OpenAlex; papers already in Zotero are skipped.
2. Zotero must be open. The papers go into **whichever collection is selected in Zotero** at that moment; the output names it. If the user wants a specific collection, ask them to click it in Zotero first, then run the command.
3. PDFs: for open-access papers `P add` tries every free copy OpenAlex knows (arXiv and university repositories first) and attaches the first real PDF. Many publisher sites block scripts; then the item gets the link only. `--no-pdf` skips this if the user doesn't want files.
4. Tell the user, per paper, what happened, using the output: PDF attached; free version exists but the site blocked the download (they can open the link saved in the item's URL field in their browser, or select the item in Zotero → right-click → **Find Available PDF**); or paywalled (they need their institution's access, rule 5). Mention when the attached PDF is an open-access copy (e.g. arXiv), since it may differ slightly from the published version.
5. If Zotero isn't running: ask the user to open it and retry. If that doesn't work (very old Zotero), fall back to a file: `P ris -o "<Downloads>/papers-<date>.ris" <DOI>...` and tell them Zotero → File → Import… → choose the file.

## Setup (first use, or when the user says "set up paper-search")

Go one step at a time: check each step first and skip it if it's already done; when something is missing, give the user one action at a time. **An API key is a password: never ask the user to paste it into the chat**, and never print it.

1. **Python**: try `python --version`, `python3 --version`, `py --version` in order and use one that is ≥ 3.9. None: install from https://www.python.org/downloads/ (on Windows tick "Add python.exe to PATH" on the first screen, then restart Claude Code). No extra packages are needed.
2. **Check**: `P status`, then `P search "test" --n 1`. A result means it works.
3. **Zotero (optional, for checking what they already have, ★ marks and adding papers)**: `P status` finds the Zotero library in the default place (`Zotero/` in the home folder). If the user has Zotero but it shows "not found", ask them to check Zotero Settings → Advanced → Files and Folders → Data Directory Location, then save it:
   `python3 -c "import sys; sys.path.insert(0, r'<skill>/scripts'); import litcommon; litcommon.save_setting('zotero_dir', r'<path>')"`
   Nothing is ever written to Zotero; it's read-only.
4. **Log folder (optional)**: ask whether they want searches remembered; if yes, `P folder "<path>"`.
5. **OpenAlex key (optional, only if they search a lot or hit a quota error)**: a free key gives 10× the keyless daily quota. Create a free account at https://openalex.org, open https://openalex.org/settings/api, then save the key: **paste the command into a terminal without pressing Enter → copy the key from the web page → go back and press Enter** (the command reads the clipboard when Enter is pressed).
   - Windows (PowerShell): `New-Item -ItemType Directory -Force "$HOME\.config\openalex" | Out-Null; (Get-Clipboard).Trim() | Set-Content -NoNewline -Encoding ascii "$HOME\.config\openalex\api_key"`
   - macOS (Terminal): `mkdir -p ~/.config/openalex && pbpaste > ~/.config/openalex/api_key && chmod 600 ~/.config/openalex/api_key`

Finish with a ✅/❌ checklist.
