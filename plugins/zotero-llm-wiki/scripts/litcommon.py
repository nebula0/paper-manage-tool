"""zotero-llm-wiki shared settings: paths, API keys, cross-platform (Windows/macOS/Linux) handling. The other scripts import this file.

Settings file ~/.config/lit-tools/config.json (created by lit-setup — tell Claude "set up zotero-llm-wiki"; every field is optional):
  {"zotero_dir": "C:/Users/me/Zotero", "zotero_user_id": "1234567", "vault": "C:/Users/me/Documents/research"}
API keys: ~/.config/zotero/api_key, ~/.config/openalex/api_key (one line of plain text).
"""
import sys, os, json, ssl, subprocess
from pathlib import Path

# The Windows console doesn't default to UTF-8, so printing CJK text and emoji fails
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
ZDB = (ZDIR / "zotero.sqlite").as_uri() + "?immutable=1"          # read-only; works while Zotero is open
CACHE = HOME / ".cache" / "lit-tools"
SETUP_HINT = 'run lit-setup first (tell Claude "set up zotero-llm-wiki")'   # tells the user how to set up, in error messages

def storage_file(att_key, path):
    """Zotero attachment path: storage:filename → the actual file; linked files (outside storage) are returned as is"""
    path = path or ""
    return ZDIR / "storage" / att_key / path.removeprefix("storage:") if path.startswith("storage:") else Path(path)

def read_key(name):
    p = CONF / name / "api_key"
    return p.read_text(encoding="utf-8-sig").strip() if p.exists() else None

# python.org Python on macOS may have no certificates installed, so use the system bundle; Windows uses the system store
SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if os.path.exists("/etc/ssl/cert.pem") else None

def find_vault():
    """Vault root: LIT_VAULT env var > settings file > nearest parent with 2_paper/文獻庫資料 or .obsidian > current folder"""
    v = os.environ.get("LIT_VAULT") or settings().get("vault")
    if v: return Path(v)
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        if (d / "2_paper" / "文獻庫資料").is_dir(): return d
    for d in [cwd, *cwd.parents]:
        if (d / ".obsidian").is_dir(): return d
    return cwd

def open_path(target):
    """Open a file or URL (including zotero://) with the system default app"""
    target = str(target)
    if sys.platform.startswith("win"): os.startfile(target)
    elif sys.platform == "darwin": subprocess.run(["open", target])
    else: subprocess.run(["xdg-open", target])
