---
name: lit-setup
description: zotero-llm-wiki（舊名 lit-tools）第一次使用的設定精靈：檢查 Python／Zotero／Better BibTeX、存放金鑰、建立文獻庫資料夾、填研究主題與標籤詞表。使用者說「設定 zotero-llm-wiki」「設定 lit-tools」「第一次使用」「安裝文獻工具」，或 lit-library／lit-reading 發現還沒設定時使用。
---

# zotero-llm-wiki 設定精靈

帶使用者一步一步完成設定。每一步先檢查，已經好的就跳過、簡短回報；缺的才請使用者動手，**一次只給一個動作**，等使用者回覆再繼續。用繁體中文、口語、步驟編號。最後給一份「✅／❌」總表。

外掛位置：`${CLAUDE_PLUGIN_ROOT}`（腳本在 `scripts/`，範本在 `starter-vault/`）。如果這段文字沒有被換成實際路徑，外掛位置就是載入本 skill 時顯示的 base directory 往上兩層；下面所有 `${CLAUDE_PLUGIN_ROOT}` 都換成那個路徑。

使用者可能是在 Obsidian 的 Claudian 面板裡跟你對話（這時目前資料夾就是他的 vault），也可能在終端機或 VS Code。給操作說明時以 Obsidian 和 PowerShell 為主，不要假設他熟悉終端機。

**金鑰等於密碼：絕對不要請使用者把金鑰貼進對話**，也不要印出金鑰內容；只檢查檔案存在與格式。

## 1. 作業系統與 Python

1. 判斷作業系統（Windows／macOS／Linux）。之後的指令依系統給。
2. 找 Python 指令：依序試 `python --version`、`python3 --version`、`py --version`，記下能用且版本 ≥ 3.9 的（下面寫成 `PY`）。
   - 都沒有：Windows 請使用者到 https://www.python.org/downloads/ 下載安裝，**安裝第一個畫面要勾「Add python.exe to PATH」**；裝完要重開 Claude Code。macOS 請他裝 python.org 版或 `brew install python`。
3. 安裝 PDF 套件：`PY -m pip install --upgrade pymupdf`，再用 `PY -c "import pymupdf; print(pymupdf.__version__)"` 確認。

## 2. Zotero

1. 找 Zotero 資料夾：預設在家目錄的 `Zotero/`（Windows 是 `C:\Users\<名字>\Zotero`），裡面要有 `zotero.sqlite`。
   - 找不到：請使用者打開 Zotero →「編輯」（macOS 是「Zotero」選單）→「設定」→「進階」→「檔案與資料夾」→「資料目錄位置」，把路徑告訴你。然後存起來：
     `PY -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/scripts'); import litcommon; litcommon.save_setting('zotero_dir', r'<路徑>')"`
   - 完全沒有：請他到 https://www.zotero.org/download/ 安裝 Zotero 7 和瀏覽器的 Zotero Connector。
2. **Better BibTeX**（產生 citekey）：檢查 Zotero 資料夾裡有沒有 `better-bibtex` 開頭的檔案。
   - 沒有：請他到 https://retorque.re/zotero-better-bibtex/installation/ 下載 `.xpi` → Zotero「工具」→「外掛程式」→ 右上齒輪「從檔案安裝外掛」→ 選 `.xpi` → 重開 Zotero。
   - 裝好後請他到 Zotero「設定」→「Better BibTeX」→「Citation keys」，把 citation key formula 改成 `auth.lower + shorttitle(3,3) + year`（和本系統的暫定代碼同公式）。
3. **同步**：AI 灰色標註是透過 zotero.org 寫回去的，所以要有 Zotero 帳號並開啟同步。請他確認 Zotero「設定」→「同步」已登入。（只同步資料就夠，PDF 檔不用同步。）
4. 用 `PY "${CLAUDE_PLUGIN_ROOT}/scripts/zot.py" find a` 測試讀得到 Zotero（沒有任何文獻也沒關係，不報錯就好）。

## 3. 金鑰

### Zotero API 金鑰（必要，用來寫 AI 灰色標註）

1. 在使用者的瀏覽器打開圖解說明：`PY -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/scripts'); import litcommon; litcommon.open_path('https://github.com/nebula0/zotero-llm-wiki/blob/main/docs/zotero-api-key.md')"`，並在對話裡附上同一個連結（瀏覽器沒打開時用）。重點：到 https://www.zotero.org/settings/keys →「Create new private key」，Personal Library 勾 **Allow library access**、**Allow notes access**、**Allow write access** → Save Key。
2. 給他存金鑰的指令，並說明順序：**先把指令貼到終端機、先不要按 Enter → 回網頁複製金鑰 → 再回終端機按 Enter**（指令在按 Enter 那一刻才讀剪貼簿）。
   - Windows（開「PowerShell」，不是這個對話）：
     ```
     New-Item -ItemType Directory -Force "$HOME\.config\zotero" | Out-Null; (Get-Clipboard).Trim() | Set-Content -NoNewline -Encoding ascii "$HOME\.config\zotero\api_key"
     ```
   - macOS（開「終端機」）：
     ```
     mkdir -p ~/.config/zotero && pbpaste > ~/.config/zotero/api_key && chmod 600 ~/.config/zotero/api_key
     ```
3. 他說存好後檢查：`PY -c "import sys; sys.path.insert(0, r'${CLAUDE_PLUGIN_ROOT}/scripts'); import zotann; print('Zotero 帳號編號', zotann.user_id())"`。成功會印出編號並自動存進設定；失敗（金鑰無效、存成指令本身）就請他重新複製金鑰、按 ↑ 叫回指令再按 Enter。

### OpenAlex API 金鑰（選用）

沒有也能搜尋，只是每日額度較低。想要的話：到 https://openalex.org 註冊免費帳號，在帳號設定頁找 API key，用同樣方式存到 `~/.config/openalex/api_key`（把上面指令裡的 `zotero` 換成 `openalex`）。

## 4. 建立文獻庫資料夾（Obsidian vault）

1. 問使用者要用哪個資料夾當 vault：
   - 目前資料夾已經是 Obsidian vault（有 `.obsidian/`，在 Claudian 裡對話時一定是）→ 直接用。
   - 否則請他給一個路徑（例如 `文件\研究筆記`），之後要在 Obsidian「開啟資料夾作為 vault」選它，並建議改用 Claudian 在 Obsidian 裡跟 Claude 對話。
2. 複製範本（不覆蓋已存在的檔案）並建立資料夾：
   ```
   PY -c "import shutil, pathlib, sys; src = pathlib.Path(r'${CLAUDE_PLUGIN_ROOT}/starter-vault'); dst = pathlib.Path(sys.argv[1]); [((dst / f.relative_to(src)).parent.mkdir(parents=True, exist_ok=True), shutil.copy2(f, dst / f.relative_to(src))) for f in src.rglob('*') if f.is_file() and not (dst / f.relative_to(src)).exists()]; [(dst / d).mkdir(parents=True, exist_ok=True) for d in ['2_paper/文獻庫', '2_paper/任務', '2_paper/notes', '2_paper/AI筆記', '1_attachment/封面', '筆記']]; print('完成')" "<vault 路徑>"
   ```
   如果目的地已經有 `.obsidian/appearance.json`，範本的不會複製過去；這時讀它、把 `"litlib"` 加進 `enabledCssSnippets` 再寫回。

## 5. 研究主題與標籤詞表

打開 `<vault>/2_paper/文獻庫資料/設定.json`，跟使用者一起填：

1. **研究主題**：請他用 2–3 句話描述研究題目。Claude 判斷文獻相關性、標 `AI/本研究` 都靠這段。
2. **本團隊**（選填）：指導教授、合作對象的姓名（姓、名的英文拼法）。他們的文章會自動標 `our-lab`。
3. **標籤詞表**：依研究主題提議 5–8 個 `topic/…`（英文小寫、用連字號，附中文說明），`type/…` 保留範本的 4 個。請他確認或修改後寫入。範本裡的 `topic/example-…` 要刪掉。

## 6. Obsidian

1. 請使用者用 Obsidian 開啟 vault，到「設定」→「第三方外掛」→ 關閉限制模式 →「瀏覽」，安裝並啟用：
   - **Zotero Integration**（把 Zotero 畫記匯成閱讀卡；需要 Better BibTeX）
   - **Claudian**（如果還沒裝）：在 Obsidian 裡直接跟 Claude 對話，用的是電腦上已登入的 Claude Code。
2. 他裝好 Zotero Integration 後，把 `${CLAUDE_PLUGIN_ROOT}/zotero-integration-settings.json` 合併進 `<vault>/.obsidian/plugins/obsidian-zotero-desktop-connector/data.json`：已有的欄位保留，`exportFormats`、`citeFormats` 沒有同名項目才加入；然後請他重開 Obsidian。
3. 確認「設定」→「外觀」→「CSS 片段」裡的 `litlib` 是開啟的。
4. 如果你們是在 Claudian 裡對話，重開 Obsidian 之後要重新打開 Claudian 面板，從下一步繼續。

## 7. 測試

1. 在 vault 根目錄執行 `PY "${CLAUDE_PLUGIN_ROOT}/scripts/litlib.py" rebuild`。Zotero 裡有幾篇，就會產生幾頁文章頁；列出 📝 是正常的（還沒寫主要貢獻）。
2. 請他在 Obsidian 打開 `2_paper/文獻庫.base`，應該看得到表格。
3. 給總表（✅／❌），沒完成的項目附下一步。最後告訴他可以開始用了，舉兩個例子：
   - 「幫我找 ○○ 的文獻，先找綜述」
   - 「我 Zotero 裡那篇 ○○ 2023，它的實驗怎麼做的？」
   並提醒：有新文章存進 Zotero 或畫了重點，跟 Claude 說「重建文獻庫」就會更新。
