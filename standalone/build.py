#!/usr/bin/env python3
"""把獨立 skill 打包成根目錄有 SKILL.md 的 zip（給 Agensi 等平台上傳）
  python3 standalone/build.py            打包 standalone/ 底下所有 skill → dist/<名字>/ 與 dist/<名字>.zip

每個 skill 的 SKILL.md 放在 standalone/<名字>/；腳本從外掛的 scripts/ 複製，並把錯誤訊息裡的設定提示換成這個 skill 的。
"""
import re, shutil, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "plugins" / "zotero-llm-wiki" / "scripts"
DIST = ROOT / "dist"

# skill 名字 → 要帶的腳本、設定提示
SKILLS = {
    "zotero-ask": {
        "scripts": ["litcommon.py", "zot.py", "zotann.py"],
        "setup_hint": 'ask Claude to "set up zotero-ask"',
    },
}

def build(name, conf):
    out = DIST / name
    shutil.rmtree(out, ignore_errors=True)
    (out / "scripts").mkdir(parents=True)
    shutil.copy2(ROOT / "standalone" / name / "SKILL.md", out / "SKILL.md")
    for f in conf["scripts"]:
        s = (SRC / f).read_text(encoding="utf-8")
        s = re.sub(r'^SETUP_HINT = .*$',f'SETUP_HINT = {conf["setup_hint"]!r}', s, flags=re.M)
        s = s.replace('created by lit-setup — tell Claude "set up zotero-llm-wiki"', f'created by {name} setup — tell Claude "set up {name}"')
        s = s.replace("; rules in skills/lit-library/規則.md §5.2", "")
        s = s.replace('"""zotero-llm-wiki shared settings', f'"""{name} shared settings')
        (out / "scripts" / f).write_text(s, encoding="utf-8")
    left = [f for f in conf["scripts"] if re.search(r"lit-setup|lit-library|zotero-llm-wiki", (out / "scripts" / f).read_text(encoding="utf-8"))]
    if left: raise SystemExit(f"⚠️ {name}：{left} 還提到外掛的 skill，請更新 build.py 的替換規則")
    z = DIST / f"{name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                zf.write(p, p.relative_to(out))       # SKILL.md 在 zip 根目錄
    print(f"✅ {z.relative_to(ROOT)}")

for name, conf in SKILLS.items():
    build(name, conf)
