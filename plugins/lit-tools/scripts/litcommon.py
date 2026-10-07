"""lit-tools 共用設定：路徑、金鑰、跨平台（Windows／macOS／Linux）處理。其他腳本 import 這個檔。

設定檔 ~/.config/lit-tools/config.json（由 lit-setup（跟 Claude 說「設定 lit-tools」） 建立，全部選填）：
  {"zotero_dir": "C:/Users/me/Zotero", "zotero_user_id": "1234567", "vault": "C:/Users/me/Documents/research"}
金鑰：~/.config/zotero/api_key、~/.config/openalex/api_key（純文字一行）。
"""
import sys, os, json, ssl, subprocess
from pathlib import Path

# Windows 終端機預設編碼不是 UTF-8，印中文與 emoji 會出錯
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass

HOME = Path.home()
CONF = HOME / ".config"
SETTINGS = CONF / "lit-tools" / "config.json"

def settings():
    try: return json.loads(SETTINGS.read_text(encoding="utf-8-sig"))
    except Exception: return {}

def save_setting(k, v):
    s = settings(); s[k] = v
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

ZDIR = Path(os.environ.get("LIT_ZOTERO_DIR") or settings().get("zotero_dir") or HOME / "Zotero")
ZDB = (ZDIR / "zotero.sqlite").as_uri() + "?immutable=1"          # 唯讀；Zotero 開著也能讀
CACHE = HOME / ".cache" / "lit-tools"

def storage_file(att_key, path):
    """Zotero 附件路徑：storage:檔名 → 實際檔案；連結檔（不在 storage）原樣回傳"""
    path = path or ""
    return ZDIR / "storage" / att_key / path.removeprefix("storage:") if path.startswith("storage:") else Path(path)

def read_key(name):
    p = CONF / name / "api_key"
    return p.read_text(encoding="utf-8-sig").strip() if p.exists() else None

# python.org 版 Python（macOS）沒裝憑證時會連線失敗，改用系統的憑證檔；Windows 用系統憑證庫
SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") else None

def find_vault():
    """vault 根目錄：環境變數 LIT_VAULT > 設定檔 > 從目前資料夾往上找有 2_paper/文獻庫資料 或 .obsidian 的 > 目前資料夾"""
    v = os.environ.get("LIT_VAULT") or settings().get("vault")
    if v: return Path(v)
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        if (d / "2_paper" / "文獻庫資料").is_dir(): return d
    for d in [cwd, *cwd.parents]:
        if (d / ".obsidian").is_dir(): return d
    return cwd

def open_path(target):
    """用系統預設程式開檔案或網址（含 zotero://）"""
    target = str(target)
    if sys.platform.startswith("win"): os.startfile(target)
    elif sys.platform == "darwin": subprocess.run(["open", target])
    else: subprocess.run(["xdg-open", target])
