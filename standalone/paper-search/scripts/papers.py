#!/usr/bin/env python3
"""Paper search tools: bibliographic data always comes from OpenAlex, never from memory.
  papers.py status                          show setup: Zotero library, log folder, OpenAlex key
  papers.py search "query" [--from YEAR] [--to YEAR] [--n 25] [--abs]
                                            OpenAlex keyword search
  papers.py cites <DOI> refs|citedby [--n 50] [--abs]
                                            citation tracking: refs = what it cites, citedby = what cites it
  papers.py fetch <DOI or OpenAlex ID>      full record: authors, venue, citations, abstract, free full text
  papers.py save <JSON string or .json file>
                                            add or update papers in <folder>/papers.csv (needs a log folder)
  papers.py folder <path>                   set the log folder ("" to stop logging)
  papers.py ris -o <file.ris> [--status candidate,to-read] [DOI ...]
                                            export for Zotero import (File → Import); DOIs given → those papers, else the log;
                                            papers already in Zotero are skipped

Marks in results: ★ already in your Zotero library, ✗ excluded before (in papers.csv), • in papers.csv.
papers.csv is plain CSV: open it in Excel/Numbers/Google Sheets. Changing a row's status to "excluded"
there works the same as telling Claude.
"""
import sys, re, csv, json, sqlite3, unicodedata, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from datetime import date

from litcommon import ZDB, ZDIR, SSL_CTX, CACHE, read_key, settings, save_setting

TODAY = date.today().isoformat()
OACACHE = CACHE / "openalex"
COLS = ["status", "title", "authors", "year", "venue", "doi", "openalex", "cited_by", "contribution",
        "basis", "reason", "query", "date", "free_full_text"]
STATUSES = ["candidate", "to-read", "excluded"]
BASES = ["full text", "abstract", "secondary", "metadata only"]

# ───────── helpers ─────────
def norm_doi(s):
    s = (s or "").strip()
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", s, flags=re.I).lower()

def is_oa_id(s):
    return bool(re.fullmatch(r"(https://openalex\.org/)?W\d+", (s or "").strip(), re.I))

def simple(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t.lower())

def excluded(status):
    s = (status or "").strip().lower()
    return s.startswith("excl") or s.startswith("reject")

# ───────── OpenAlex ─────────
OA_FIELDS = ("id,doi,title,publication_year,type,cited_by_count,open_access,best_oa_location,"
             "primary_location,authorships,abstract_inverted_index,referenced_works")

def oa_get(path, **params):
    key = read_key("openalex")                                        # works without a key, with a lower daily quota
    q = urllib.parse.urlencode({**params, "select": OA_FIELDS, **({"api_key": key} if key else {})})
    try:
        with urllib.request.urlopen(f"https://api.openalex.org/{path}?{q}", context=SSL_CTX, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            sys.exit(f"OpenAlex refused the request (HTTP {e.code}): daily quota used up or key invalid. "
                     "A free key from https://openalex.org/settings/api raises the quota; "
                     'ask Claude to "set up paper-search" to save it.')
        raise
    except urllib.error.URLError as e:
        sys.exit(f"Can't reach OpenAlex ({e.reason}). Check the internet connection.")

def oa_trim(w):
    src = ((w.get("primary_location") or {}).get("source") or {})
    best, oa = w.get("best_oa_location") or {}, w.get("open_access") or {}
    inv = w.get("abstract_inverted_index") or {}
    pos = sorted((i, word) for word, ii in inv.items() for i in ii)
    return {"id": (w.get("id") or "").rsplit("/", 1)[-1], "doi": norm_doi(w.get("doi")),
            "title": w.get("title") or "", "year": w.get("publication_year"), "type": w.get("type"),
            "venue": src.get("display_name") or "",
            "authors": [a["author"]["display_name"] for a in w.get("authorships") or []],
            "cited_by": w.get("cited_by_count"),
            "oa_url": best.get("pdf_url") or best.get("landing_page_url") or oa.get("oa_url") or "",
            "abstract": " ".join(word for _, word in pos) or None,
            "refs": [r.rsplit("/", 1)[-1] for r in w.get("referenced_works") or []]}

def record(ident):
    """One paper by DOI or OpenAlex ID; cached. Exits if OpenAlex doesn't have it."""
    ident = ident.strip()
    oid = ident.rsplit("/", 1)[-1].upper() if is_oa_id(ident) else None
    key = oid or norm_doi(ident)
    p = OACACHE / (urllib.parse.quote(key, safe="") + ".json")
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    path = f"works/{oid}" if oid else f"works/doi:{urllib.parse.quote(key, safe='/')}"
    try:
        rec = oa_trim(oa_get(path))
    except urllib.error.HTTPError as e:
        if e.code == 404: sys.exit(f"OpenAlex has no record for {ident}. Don't fill in its details from memory.")
        raise
    OACACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    return rec

# ───────── Zotero (read-only) ─────────
def zotero_index():
    """DOIs and normalized titles in the Zotero library; empty if Zotero isn't found"""
    if not (ZDIR / "zotero.sqlite").exists(): return set(), set()
    try:
        con = sqlite3.connect(ZDB, uri=True)
        rows = con.execute("""select f.fieldName, v.value from itemData d
                              join fields f on f.fieldID=d.fieldID join itemDataValues v on v.valueID=d.valueID
                              where f.fieldName in ('DOI','title','extra')
                                and d.itemID not in (select itemID from deletedItems)""").fetchall()
    except sqlite3.Error:
        return set(), set()
    dois, titles = set(), set()
    for f, v in rows:
        if f == "DOI": dois.add(norm_doi(v))
        elif f == "title": titles.add(simple(v))
        else: dois.update(norm_doi(m) for m in re.findall(r"^DOI:\s*(\S+)", v or "", re.M | re.I))
    titles.discard("")
    return dois, titles

# ───────── log (papers.csv) ─────────
def log_dir():
    f = settings().get("paper_search_folder")
    return Path(f).expanduser() if f else None

def log_file():
    d = log_dir()
    return d / "papers.csv" if d else None

def read_log():
    p = log_file()
    if not p or not p.exists(): return [], list(COLS)
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or COLS)
        rows = list(rd)
    return rows, cols + [c for c in COLS if c not in cols]           # keep columns the user added

def write_log(rows, cols):
    p = log_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:     # BOM so Excel reads non-English text correctly
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    try:
        tmp.replace(p)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        sys.exit(f"Can't write {p}: it's probably open in Excel or another program. Close it and try again.")

def row_key(r):
    return norm_doi(r.get("doi")) or (r.get("openalex") or "").upper()

def log_index():
    return {row_key(r): r for r in read_log()[0] if row_key(r)}

# ───────── commands ─────────
def mark(r, zdois, ztitles, logged):
    lr = logged.get(r["doi"]) or logged.get(r["id"].upper())
    if lr and excluded(lr.get("status")):
        return f"  ✗ excluded {lr.get('date', '')}: {lr.get('reason') or 'no reason given'}"
    m = ""
    if (r["doi"] and r["doi"] in zdois) or simple(r["title"]) in ztitles: m += "  ★ in Zotero"
    if lr: m += f"  • logged as {lr.get('status') or '?'}"
    return m

def show_hits(works, total, abstracts):
    zdois, ztitles = zotero_index()
    logged = log_index()
    print(f"{total} results, showing {len(works)}")
    for n, w in enumerate(works, 1):
        r = oa_trim(w)
        au = (r["authors"][0].split()[-1] + (" et al." if len(r["authors"]) > 1 else "")) if r["authors"] else "?"
        print(f"[{n}] {r['year']} {au} — {r['title']} — {r['venue'] or '?'} — cited {r['cited_by']} — "
              f"{r['doi'] or r['id']}{mark(r, zdois, ztitles, logged)}")
        if abstracts:
            print(f"     {(r['abstract'] or '(no abstract)')[:400]}")
    notes = []
    if not zdois and not ztitles: notes.append("Zotero library not found, so no ★ marks")
    if not log_file(): notes.append("no log folder, so no ✗ marks")
    if notes: print(f"\n({'; '.join(notes)})")

def search(query, frm=None, to=None, n=25, abstracts=False):
    flt = [f"from_publication_date:{frm}-01-01"] if frm else []
    if to: flt.append(f"to_publication_date:{to}-12-31")
    params = {"search": query, "per_page": n}
    if flt: params["filter"] = ",".join(flt)
    d = oa_get("works", **params)
    show_hits(d.get("results", []), d.get("meta", {}).get("count"), abstracts)

def cites(ident, direction, n=50, abstracts=False):
    r = record(ident)
    if direction == "refs":
        refs, works = r.get("refs", []), []
        for i in range(0, len(refs), 50):
            works += oa_get("works", filter="openalex:" + "|".join(refs[i:i + 50]), per_page=50).get("results", [])
        works.sort(key=lambda w: -(w.get("cited_by_count") or 0))
        show_hits(works[:n], len(refs), abstracts)
    elif direction == "citedby":
        d = oa_get("works", filter=f"cites:{r['id']}", sort="cited_by_count:desc", per_page=n)
        show_hits(d.get("results", []), d.get("meta", {}).get("count"), abstracts)
    else:
        sys.exit("direction must be refs or citedby")

def fetch(ident):
    r = record(ident)
    zdois, ztitles = zotero_index()
    au = ", ".join(r["authors"][:6]) + (" et al." if len(r["authors"]) > 6 else "")
    print(f"{r['title']}\n{au} · {r['venue'] or '?'} · {r['year']} · {r['type']}")
    print(f"DOI {r['doi'] or '—'} | OpenAlex {r['id']} | cited {r['cited_by']}{mark(r, zdois, ztitles, log_index())}")
    print(f"Free full text: {r['oa_url'] or 'none found'}")
    print(f"\nAbstract: {r['abstract'] or '(OpenAlex has no abstract)'}")

def save(arg):
    if not log_file():
        sys.exit('No log folder set. Ask the user where to keep the log, then run: papers.py folder "<path>"')
    s = arg.strip()
    recs = json.loads(Path(s).read_text(encoding="utf-8-sig") if s.endswith(".json") and Path(s).exists() else s)
    if isinstance(recs, dict): recs = [recs]
    rows, cols = read_log()
    index = {row_key(r): r for r in rows if row_key(r)}
    errors, updates = [], []
    for i, rec in enumerate(recs, 1):
        ident = rec.get("doi") or rec.get("openalex")
        if not ident: errors.append(f"#{i}: needs a doi or openalex ID"); continue
        st = (rec.get("status") or "").strip().lower()
        if st and st not in STATUSES: errors.append(f"#{i}: status must be one of {STATUSES}")
        if rec.get("basis") and rec["basis"] not in BASES: errors.append(f"#{i}: basis must be one of {BASES}")
        if st == "excluded" and not rec.get("reason"): errors.append(f"#{i}: excluded papers need a reason")
        updates.append((ident, rec))
    if errors: sys.exit("Nothing saved:\n" + "\n".join(errors))
    added = changed = 0
    for ident, rec in updates:
        oa = record(ident)                                           # bibliographic data from OpenAlex only
        key = oa["doi"] or oa["id"].upper()
        row = index.get(key)
        if row is None:
            row = {c: "" for c in cols}; rows.append(row); index[key] = row; added += 1
        else:
            changed += 1
        row.update({"title": oa["title"], "authors": "; ".join(oa["authors"]), "year": oa["year"] or "",
                    "venue": oa["venue"], "doi": oa["doi"], "openalex": oa["id"], "cited_by": oa["cited_by"],
                    "free_full_text": oa["oa_url"], "date": TODAY})
        for k in ("status", "contribution", "basis", "reason", "query"):
            if rec.get(k): row[k] = rec[k].strip().lower() if k == "status" else rec[k]
        if not row.get("status"): row["status"] = "candidate"
    write_log(rows, cols)
    print(f"✅ {added} added, {changed} updated → {log_file()} ({len(rows)} papers)")

def folder(path):
    if not path.strip():
        save_setting("paper_search_folder", ""); print("Logging stopped (papers.csv is kept)."); return
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    save_setting("paper_search_folder", str(p))
    print(f"✅ Log folder: {p}\n   Papers go to {p / 'papers.csv'}")

RIS_TYPES = {"article": "JOUR", "review": "JOUR", "book": "BOOK", "book-chapter": "CHAP",
             "dissertation": "THES", "preprint": "UNPB", "report": "RPRT", "dataset": "DATA"}

def ris(out, idents, statuses):
    if not idents:
        rows = read_log()[0]
        if not rows: sys.exit("Nothing to export: give DOIs, or save papers to the log first.")
        idents = [r.get("doi") or r.get("openalex") for r in rows
                  if (r.get("status") or "").strip().lower() in statuses and (r.get("doi") or r.get("openalex"))]
        if not idents: sys.exit(f"No papers in the log with status {', '.join(statuses)}.")
    zdois, ztitles = zotero_index()
    lines, skipped = [], 0
    for ident in idents:
        r = record(ident)
        if (r["doi"] and r["doi"] in zdois) or simple(r["title"]) in ztitles:
            skipped += 1; continue                                    # already in Zotero; importing would duplicate it
        lines.append(f"TY  - {RIS_TYPES.get(r['type'], 'GEN')}")
        lines.append(f"TI  - {r['title']}")
        lines += [f"AU  - {a}" for a in r["authors"]]
        if r["year"]: lines.append(f"PY  - {r['year']}")
        if r["venue"]: lines.append(f"T2  - {r['venue']}")
        if r["doi"]: lines.append(f"DO  - {r['doi']}")
        if r["oa_url"]: lines.append(f"UR  - {r['oa_url']}")
        if r["abstract"]: lines.append(f"AB  - {r['abstract']}")
        lines += ["ER  - ", ""]
    if skipped: print(f"Skipped {skipped} already in Zotero.")
    if not lines: sys.exit("Nothing left to export.")
    p = Path(out).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ {len(idents) - skipped} papers → {p}\n   In Zotero: File → Import… → choose this file.")

def status():
    zok = (ZDIR / "zotero.sqlite").exists()
    print(f"Zotero library: {ZDIR} ({'found, ★ marks on' if zok else 'not found, no ★ marks (optional)'})")
    lf = log_file()
    print(f"Log folder: {log_dir() or 'not set (optional; needed for ✗ marks and saving)'}"
          + (f" ({len(read_log()[0])} papers)" if lf and lf.exists() else ""))
    print(f"OpenAlex key: {'set' if read_key('openalex') else 'not set (optional; raises the daily quota)'}")

def opt(args, name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default

def flag(args, name):
    if name in args: args.remove(name); return True
    return False

cmd, *a = sys.argv[1:] or ["-h"]
if cmd == "status": status()
elif cmd == "search":
    frm, to, n, ab = opt(a, "--from"), opt(a, "--to"), int(opt(a, "--n", 25)), flag(a, "--abs")
    search(" ".join(a), frm, to, n, ab)
elif cmd == "cites":
    n, ab = int(opt(a, "--n", 50)), flag(a, "--abs")
    cites(a[0], a[1], n, ab)
elif cmd == "fetch": fetch(a[0])
elif cmd == "save": save(" ".join(a))
elif cmd == "folder": folder(a[0] if a else "")
elif cmd == "ris":
    out = opt(a, "-o") or sys.exit("ris needs -o <file.ris>")
    st = [s.strip() for s in opt(a, "--status", "candidate,to-read").split(",")]
    ris(out, a, st)
else: print(__doc__)
