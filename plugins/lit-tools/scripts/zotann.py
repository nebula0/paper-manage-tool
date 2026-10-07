#!/usr/bin/env python3
"""Claude 的 Zotero 標註工具（AI 標註一律灰色 + AI/ 分類 tag，規範見 skills/lit-library/規則.md §5.2）
  zotann.py add <附件代號> <標註.json> [--send]   依 JSON 找句子位置、組成 Zotero 標註；預設只預覽，加 --send 才寫入
  zotann.py list <附件代號>                      列出這個 PDF 上的 AI 灰色標註（讀本機資料庫）
  zotann.py delete <標註代號>... [--send]        刪除 AI 標註；只刪得掉灰色的，預設只預覽

標註.json 格式（list）：
  [{"page": 6, "text": "PDF 裡的原句", "tag": "論點", "comment": "為什麼標", "task": "perspective"}]
  page 是 PDF 第幾頁（從 1 起算）；tag 必須是 論點／質疑／方法／數據／待查／本研究；task 可省略。

寫入走 Zotero 網路 API，金鑰讀 ~/.config/zotero/api_key；不直接改 zotero.sqlite。
Zotero 帳號編號第一次用時由金鑰查出，存在 ~/.config/lit-tools/config.json。
"""
import sys, json, sqlite3, urllib.request, urllib.error
from litcommon import ZDB, SSL_CTX, storage_file, read_key, settings, save_setting

AI_COLOR = "#aaaaaa"
TAGS = {"論點", "質疑", "方法", "數據", "待查", "本研究"}

def db():
    return sqlite3.connect(ZDB, uri=True)

def pdf_path(att):
    r = db().execute("""select a.path from items i join itemAttachments a on a.itemID=i.itemID
                        where i.key=? and a.contentType='application/pdf'""", (att,)).fetchone()
    if not r: sys.exit(f"找不到 PDF 附件 {att}")
    return str(storage_file(att, r[0]))

def api_key():
    k = read_key("zotero")
    if not k: sys.exit("找不到 Zotero API 金鑰 ~/.config/zotero/api_key，請先執行 lit-setup（跟 Claude 說「設定 lit-tools」）")
    return k

def user_id():
    """Zotero 帳號編號：設定檔有就用，沒有就用金鑰向 Zotero 查一次並存起來"""
    uid = settings().get("zotero_user_id")
    if uid: return str(uid)
    req = urllib.request.Request("https://api.zotero.org/keys/current",
                                 headers={"Zotero-API-Key": api_key(), "Zotero-API-Version": "3"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as r:
            uid = str(json.load(r)["userID"])
    except urllib.error.HTTPError as e:
        sys.exit(f"Zotero 金鑰無效（{e.code}），請重新執行 lit-setup（跟 Claude 說「設定 lit-tools」）")
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
        sys.exit(f"Zotero API {method} {path} 失敗：{e.code} {e.read().decode()[:300]}")

def _norm(w):
    import unicodedata
    return unicodedata.normalize("NFKC", w).strip(".,;:()[]\"'“”‘’").lower()

def find_rects(pg, text):
    """先精確搜尋；找不到就逐字比對，處理行尾斷字（experimen- tally）。回傳 (每行一個框, 起始字元位置)"""
    import pymupdf
    hits = pg.search_for(text)
    if hits:
        return hits, max(0, pg.get_text().find(text.split()[0]))
    words = pg.get_text("words")                      # (x0, y0, x1, y1, 字, block, line, 序)
    toks, i = [], 0                                   # 每個 token：(可接受的寫法, 用到的字索引)
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
            print(f"⚠️ tag「{tag}」不在 {sorted(TAGS)}，略過：{s['text'][:40]}"); bad += 1; continue
        pi = int(s["page"]) - 1
        pg = doc[pi]
        rects, offset = find_rects(pg, s["text"])
        if not rects:
            print(f"⚠️ p.{pi+1} 找不到：{s['text'][:60]}"); bad += 1; continue
        m = ~pg.transformation_matrix          # MuPDF 座標（左上原點）→ PDF 座標（左下原點）
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
        print(f"✅ p.{pi+1} [AI/{tag}] {len(rects)} 段框線：{s['text'][:50]}")
    return out, bad

def add(att, spec_file, send):
    synced = db().execute("select synced from items where key=?", (att,)).fetchone()
    if synced is None: sys.exit(f"找不到附件 {att}")
    if not synced[0]: print("⚠️ 這個附件在本機顯示尚未同步到 zotero.org，網路 API 可能找不到它")
    items, bad = build(att, json.load(open(spec_file, encoding="utf-8")))
    print(f"— 共 {len(items)} 則可寫入，{bad} 則有問題")
    if not send:
        print("（預覽模式，未寫入。確認無誤後加 --send）"); return
    for i in range(0, len(items), 50):
        _, res = api("POST", "/items", items[i:i + 50])
        for k, v in (res.get("successful") or {}).items():
            print(f"已寫入 {v['key']}")
        for k, v in (res.get("failed") or {}).items():
            print(f"❌ 第 {int(k) + i + 1} 則失敗：{v.get('message')}")
    print("寫入完成；Zotero 桌面版同步後就會看到灰色標註。")

def list_ai(att):
    rows = db().execute("""select ai.key, a.pageLabel, a.text, a.comment,
                             (select group_concat(t.name) from itemTags it join tags t using(tagID) where it.itemID=a.itemID)
                           from itemAnnotations a join items ai on ai.itemID=a.itemID
                           join items p on p.itemID=a.parentItemID
                           where p.key=? and lower(a.color)=? order by a.sortIndex""", (att, AI_COLOR)).fetchall()
    if not rows: print("這個 PDF 目前沒有 AI 標註")
    for key, pl, text, com, tags in rows:
        print(f"{key}  p.{pl} [{tags or '無 tag'}] {(text or '')[:60]}\n        註：{com or ''}")

def delete(keys, send):
    for k in keys:
        _, it = api("GET", f"/items/{k}")
        d = it["data"]
        if d.get("itemType") != "annotation" or (d.get("annotationColor") or "").lower() != AI_COLOR:
            print(f"⛔ {k} 不是 AI 灰色標註，不刪"); continue
        print(f"{'刪除' if send else '將刪除'} {k}：{d.get('annotationText', '')[:50]}")
        if send:
            api("DELETE", f"/items/{k}", headers={"If-Unmodified-Since-Version": str(it["version"])})
    if not send: print("（預覽模式，未刪除。確認無誤後加 --send）")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--send"]
    send = "--send" in sys.argv
    cmd, *a = args or ["-h"]
    if cmd == "add" and len(a) == 2: add(a[0], a[1], send)
    elif cmd == "list" and len(a) == 1: list_ai(a[0])
    elif cmd == "delete" and a: delete(a, send)
    else: print(__doc__)
