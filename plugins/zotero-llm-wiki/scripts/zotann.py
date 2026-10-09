#!/usr/bin/env python3
"""Claude's Zotero annotation tool (AI annotations are always grey + an AI/ category tag; rules in skills/lit-library/規則.md §5.2)
  zotann.py add <key> <annotations.json> [--send]   locate the sentences from the JSON and build Zotero annotations; previews by default, writes only with --send
  zotann.py list <key>                              list the grey AI annotations on this PDF (reads the local database)
  zotann.py delete <annotation key>... [--send]     delete AI annotations; only grey ones can be deleted; previews by default

annotations.json format (a list):
  [{"page": 6, "text": "sentence from the PDF", "tag": "claim", "comment": "why it is highlighted", "task": "perspective"}]
  page is the PDF page index starting at 1; tag must be claim/critique/method/data/todo/relevance
  (Chinese: 論點/質疑/方法/數據/待查/本研究); task is optional.

Writes go through the Zotero web API with the key in ~/.config/zotero/api_key; zotero.sqlite is never modified directly.
The Zotero user ID is looked up with the key on first use and saved in ~/.config/lit-tools/config.json.
"""
import sys, json, sqlite3, urllib.request, urllib.error
from litcommon import ZDB, SSL_CTX, SETUP_HINT, storage_file, read_key, settings, save_setting

AI_COLOR = "#aaaaaa"
TAGS = {"論點", "質疑", "方法", "數據", "待查", "本研究",                       # Chinese
        "claim", "critique", "method", "data", "todo", "relevance"}         # English, same order as above

def db():
    return sqlite3.connect(ZDB, uri=True)

def pdf_path(att):
    r = db().execute("""select a.path from items i join itemAttachments a on a.itemID=i.itemID
                        where i.key=? and a.contentType='application/pdf'""", (att,)).fetchone()
    if not r: sys.exit(f"PDF attachment {att} not found")
    return str(storage_file(att, r[0]))

def api_key():
    k = read_key("zotero")
    if not k: sys.exit(f"No Zotero API key at ~/.config/zotero/api_key; {SETUP_HINT}")
    return k

def user_id():
    """Zotero user ID: from the settings file if present, otherwise looked up once with the key and saved"""
    uid = settings().get("zotero_user_id")
    if uid: return str(uid)
    req = urllib.request.Request("https://api.zotero.org/keys/current",
                                 headers={"Zotero-API-Key": api_key(), "Zotero-API-Version": "3"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as r:
            uid = str(json.load(r)["userID"])
    except urllib.error.HTTPError as e:
        sys.exit(f"Invalid Zotero API key ({e.code}); {SETUP_HINT}")
    save_setting("zotero_user_id", uid)
    return uid

def api(method, path, body=None, headers=None):
    h = {"Zotero-API-Key": api_key(), "Zotero-API-Version": "3",
         "Content-Type": "application/json", **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"https://api.zotero.org/users/{user_id()}" + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        sys.exit(f"Zotero API {method} {path} failed: {e.code} {e.read().decode()[:300]}")

def _norm(w):
    import unicodedata
    return unicodedata.normalize("NFKC", w).strip(".,;:()[]\"'“”‘’").lower()

def find_rects(pg, text):
    """Exact search first; if that fails, match word by word to handle line-end hyphenation (experimen- tally). Returns (one rect per line, start character offset)"""
    import pymupdf
    hits = pg.search_for(text)
    if hits:
        return hits, max(0, pg.get_text().find(text.split()[0]))
    words = pg.get_text("words")                      # (x0, y0, x1, y1, word, block, line, index)
    toks, i = [], 0                                   # each token: (accepted spellings, word indices used)
    while i < len(words):
        w = words[i][4]
        if w.endswith("-") and i + 1 < len(words) and words[i + 1][5:7] != words[i][5:7]:
            nxt = words[i + 1][4]
            toks.append(({_norm(w[:-1] + nxt), _norm(w + nxt)}, [i, i + 1])); i += 2
        else:
            toks.append(({_norm(w)}, [i])); i += 1
    q = [_norm(w) for w in text.split() if _norm(w)]
    for s in range(len(toks) - len(q) + 1):
        if all(q[k] in toks[s + k][0] for k in range(len(q))):
            idx = [j for t in toks[s:s + len(q)] for j in t[1]]
            lines = {}
            for j in idx:
                x0, y0, x1, y1, _, b, l, _ = words[j]
                r = lines.setdefault((b, l), pymupdf.Rect(x0, y0, x1, y1))
                r.include_rect(pymupdf.Rect(x0, y0, x1, y1))
            offset = sum(len(words[j][4]) + 1 for j in range(idx[0]))
            return list(lines.values()), offset
    return [], 0

def build(att, spec):
    import pymupdf
    doc = pymupdf.open(pdf_path(att))
    out, bad = [], 0
    for s in spec:
        tag = s.get("tag", "")
        if tag not in TAGS:
            print(f"⚠️ tag \"{tag}\" not in {sorted(TAGS)}, skipped: {s['text'][:40]}"); bad += 1; continue
        pi = int(s["page"]) - 1
        pg = doc[pi]
        rects, offset = find_rects(pg, s["text"])
        if not rects:
            print(f"⚠️ p.{pi+1} not found: {s['text'][:60]}"); bad += 1; continue
        m = ~pg.transformation_matrix          # MuPDF coordinates (top-left origin) → PDF coordinates (bottom-left origin)
        pdf_rects = []
        for r in rects:
            q = r * m
            pdf_rects.append([round(min(q.x0, q.x1), 3), round(min(q.y0, q.y1), 3),
                              round(max(q.x0, q.x1), 3), round(max(q.y0, q.y1), 3)])
        top = int(min(r.y0 for r in rects))
        comment = s.get("comment", "")
        if s.get("task"): comment += f"〔任務：{s['task']}〕"
        out.append({
            "itemType": "annotation", "parentItem": att, "annotationType": "highlight",
            "annotationText": s["text"], "annotationComment": comment,
            "annotationColor": AI_COLOR, "annotationPageLabel": pg.get_label() or str(pi + 1),
            "annotationSortIndex": f"{pi:05d}|{offset:06d}|{top:05d}",
            "annotationPosition": json.dumps({"pageIndex": pi, "rects": pdf_rects}),
            "tags": [{"tag": f"AI/{tag}"}],
        })
        print(f"✅ p.{pi+1} [AI/{tag}] {len(rects)} line box(es): {s['text'][:50]}")
    return out, bad

def add(att, spec_file, send):
    synced = db().execute("select synced from items where key=?", (att,)).fetchone()
    if synced is None: sys.exit(f"Attachment {att} not found")
    if not synced[0]: print("⚠️ This attachment is not synced to zotero.org yet; the web API may not find it")
    items, bad = build(att, json.load(open(spec_file, encoding="utf-8")))
    print(f"— {len(items)} ready to write, {bad} with problems")
    if not send:
        print("(Preview only, nothing written. Add --send once it looks right)"); return
    for i in range(0, len(items), 50):
        _, res = api("POST", "/items", items[i:i + 50])
        for k, v in (res.get("successful") or {}).items():
            print(f"written {v['key']}")
        for k, v in (res.get("failed") or {}).items():
            print(f"❌ #{int(k) + i + 1} failed: {v.get('message')}")
    print("Done; the grey annotations appear after Zotero desktop syncs.")

def list_ai(att):
    rows = db().execute("""select ai.key, a.pageLabel, a.text, a.comment,
                             (select group_concat(t.name) from itemTags it join tags t using(tagID) where it.itemID=a.itemID)
                           from itemAnnotations a join items ai on ai.itemID=a.itemID
                           join items p on p.itemID=a.parentItemID
                           where p.key=? and lower(a.color)=? order by a.sortIndex""", (att, AI_COLOR)).fetchall()
    if not rows: print("No AI annotations on this PDF yet")
    for key, pl, text, com, tags in rows:
        print(f"{key}  p.{pl} [{tags or 'no tag'}] {(text or '')[:60]}\n        comment: {com or ''}")

def delete(keys, send):
    for k in keys:
        _, it = api("GET", f"/items/{k}")
        d = it["data"]
        if d.get("itemType") != "annotation" or (d.get("annotationColor") or "").lower() != AI_COLOR:
            print(f"⛔ {k} is not a grey AI annotation, not deleting"); continue
        print(f"{'deleted' if send else 'would delete'} {k}: {d.get('annotationText', '')[:50]}")
        if send:
            api("DELETE", f"/items/{k}", headers={"If-Unmodified-Since-Version": str(it["version"])})
    if not send: print("(Preview only, nothing deleted. Add --send once it looks right)")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--send"]
    send = "--send" in sys.argv
    cmd, *a = args or ["-h"]
    if cmd == "add" and len(a) == 2: add(a[0], a[1], send)
    elif cmd == "list" and len(a) == 1: list_ai(a[0])
    elif cmd == "delete" and a: delete(a, send)
    else: print(__doc__)
