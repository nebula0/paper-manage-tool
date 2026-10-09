#!/usr/bin/env python3
"""Zotero PDF tools (read-only; never modifies the Zotero database)
  zot.py status                     show setup: Zotero data folder, API key, saved settings
  zot.py find "keywords"            find papers by title/author → attachment key, title, authors
  zot.py grep <key> "regex"         search a paper, listing page numbers and context
  zot.py page <key> <page>          print the full text of one page
  zot.py open <key> <page>          open the Zotero reader at that page
  zot.py notes <key>                list the annotations in Zotero
  zot.py hl <key> <page> "sentence 1[::comment]" ["sentence 2"...]
                                    highlight a copy of the PDF and open it with the default app (the original is untouched)
"""
import sys, re, json, sqlite3
from litcommon import ZDIR, ZDB, CACHE, CONF, storage_file, open_path, settings

PDFCACHE = CACHE / "pdftext"

def db():
    return sqlite3.connect(ZDB, uri=True)

def pdf_path(att):
    r = db().execute("""select a.path from items i join itemAttachments a on a.itemID=i.itemID
                        where i.key=? and a.contentType='application/pdf'""", (att,)).fetchone()
    if not r: sys.exit(f"PDF attachment {att} not found")
    return storage_file(att, r[0])

def pages(att):
    """Text of each page; cached after the first read"""
    PDFCACHE.mkdir(parents=True, exist_ok=True)
    cache = PDFCACHE / f"{att}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    import pymupdf
    txt = [pg.get_text() for pg in pymupdf.open(pdf_path(att))]
    cache.write_text(json.dumps(txt, ensure_ascii=False), encoding="utf-8")
    return txt

def status():
    ok = (ZDIR / "zotero.sqlite").exists()
    print(f"Zotero data folder: {ZDIR} ({'ok' if ok else 'zotero.sqlite NOT FOUND'})")
    print(f"Zotero API key: {'set' if (CONF / 'zotero' / 'api_key').exists() else 'not set'}")
    for k, v in settings().items():
        print(f"setting {k}: {v}")

def find(q):
    sql = """select a.key, coalesce(tv.value,''), a2.path,
               (select group_concat(c.lastName, ', ') from itemCreators ic join creators c
                  on c.creatorID=ic.creatorID where ic.itemID=p.itemID)
             from items a join itemAttachments a2 on a2.itemID=a.itemID
             left join items p on p.itemID=a2.parentItemID
             left join itemData td on td.itemID=p.itemID and td.fieldID=(select fieldID from fields where fieldName='title')
             left join itemDataValues tv on tv.valueID=td.valueID
             where a2.contentType='application/pdf'
               and a.itemID not in (select itemID from deletedItems)
               and (p.itemID is null or p.itemID not in (select itemID from deletedItems))"""
    ql = q.lower()
    for key, title, path, au in db().execute(sql):
        hay = f"{title} {au} {path}".lower()
        if all(w in hay for w in ql.split()):
            print(f"{key}\t{title}\t[{au}]")

def grep(att, pat, ctx=150):
    rx = re.compile(pat, re.I)
    for n, pg in enumerate(pages(att), 1):
        flat = re.sub(r"\s+", " ", pg)
        for m in rx.finditer(flat):
            s = max(0, m.start()-ctx); e = min(len(flat), m.end()+ctx)
            print(f"p.{n}: …{flat[s:e]}…\n")

def notes(att):
    iid = db().execute("select itemID from items where key=?", (att,)).fetchone()[0]
    for pos, text, com, color in db().execute("""select pageLabel, text, comment, color from itemAnnotations
                                                 where parentItemID=? order by sortIndex""", (iid,)):
        print(f"p.{pos} {color} | {text or ''} | comment: {com or ''}")

def hl(att, page, snippets):
    import pymupdf
    out_dir = CACHE / "hl"; out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{att}.pdf"
    doc = pymupdf.open(pdf_path(att)); pg = doc[int(page)-1]
    for snip in snippets:
        snip, _, note = snip.partition("::")
        quads = pg.search_for(snip, quads=True)
        if not quads:
            print(f"⚠️ p.{page} not found: {snip}"); continue
        a = pg.add_highlight_annot(quads); a.set_colors(stroke=(0.55, 0.85, 1.0))
        if note: a.set_info(content=note, title="Claude")
        a.update()
        print(f"✅ highlighted: {snip[:50]}")
    doc.save(out)
    print(f"saved {out}, highlights on page {page}")
    open_path(out)

cmd, *a = sys.argv[1:] or ["-h"]
if cmd == "status": status()
elif cmd == "find": find(" ".join(a))
elif cmd == "grep": grep(a[0], a[1])
elif cmd == "page": print(pages(a[0])[int(a[1])-1])
elif cmd == "open": open_path(f"zotero://open-pdf/library/items/{a[0]}?page={a[1]}")
elif cmd == "notes": notes(a[0])
elif cmd == "hl": hl(a[0], a[1], a[2:])
else: print(__doc__)
