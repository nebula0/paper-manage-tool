# lit-tools：讓 Claude 幫你讀論文、整理文獻

[English](README.md) ｜ **繁體中文**

這是給 Claude Code 用的外掛。裝好之後，你可以在 Obsidian 裡直接跟 Claude 說「幫我找 ○○ 的文獻」、「這篇的實驗怎麼做的？」，Claude 會去搜尋、讀你 Zotero 裡的 PDF，把結果整理成一個會自動更新的文獻庫（在 Obsidian 裡看）。

---

## 它解決什麼問題

| 以前 | 用了之後 |
|---|---|
| 每次請 AI 找文獻都重新搜一次，格式每次不同，還會重複推薦 | 搜過的查詢、收過的文章都有紀錄，再搜時已在庫內的標 ★、排除過的標 ✗ |
| AI 給的 DOI、年份、期刊有時是編的 | 書目一律從 OpenAlex 資料庫抓，程式會擋掉沒有來源的資料 |
| 看過的、下載過的、還沒看的文章混在一起 | 一篇一頁，表格裡看得到「AI 讀到哪」、「你讀到哪」（依你在 Zotero 的畫記自動判斷）、有沒有 PDF |
| 問 AI 論文內容，不知道它是讀了原文還是在猜 | 回答附頁碼與原句，並在 PDF 上畫灰色標註，你在 Zotero 裡就能對照原文 |
| 和 AI 討論過的內容散在對話裡，下次就找不到 | 每篇論文有一份 AI 筆記，問答會一直累積在裡面 |
| 不記得當初為什麼收這篇 | 每篇都記錄「為何收錄」、「主要貢獻」，以及判斷依據是全文、摘要還是只有書目 |

## 它長什麼樣

```
你：在 Zotero 存文章、畫重點          你：跟 Claude 說話
        │                                     │
        ▼                                     ▼
   Zotero（PDF＋畫記）  ◀── 讀取、寫灰色標註 ──  Claude Code ＋ lit-tools
        │                                     │
        └──────────────┬──────────────────────┘
                       ▼  自動重建
           Obsidian 文獻庫（一篇一頁＋表格）
           ├─ 文章頁：書目、主要貢獻、為何收錄、你和 AI 的閱讀程度
           ├─ 任務頁：每次搜尋找了什麼、收了什麼、排除了什麼與理由
           └─ AI 筆記：Claude 讀每篇論文的問答紀錄（附頁碼）
```

你平常只會打開兩個軟體：
- **Zotero**：存 PDF、畫重點（你本來可能就在用）
- **Obsidian**：看整理好的文獻庫，也在這裡跟 Claude 對話（透過 Claudian 外掛，畫面右側會多一個聊天面板）

---

## 安裝（Windows，約 30 分鐘）

### 需要的東西

- Claude 付費訂閱（Pro 或 Max）
- Zotero 帳號（免費），用來同步 AI 標註

### 每個軟體是做什麼的

| 軟體 | 做什麼 | 你會直接用到嗎 |
|---|---|---|
| **Zotero** | 文獻管理軟體：存 PDF 和書目、在 PDF 上畫重點、寫筆記。所有論文都放這裡 | ✅ 每天用：讀論文、畫重點 |
| **Zotero Connector** | 瀏覽器外掛：在期刊網頁按一下，就把書目和 PDF 存進 Zotero | ✅ 存新文章時用 |
| **Better BibTeX** | Zotero 的外掛：給每篇文章一個固定代碼（例如 `smithThermalTuning2023`），檔名和連結都用它；寫 LaTeX 時也能用來引用 | ❌ 裝好就不用管 |
| **Obsidian** | 筆記軟體：用來看整理好的文獻庫（表格、卡片牆、文章頁），也可以寫自己的筆記 | ✅ 每天用 |
| **Claudian** | Obsidian 的外掛：在 Obsidian 右側開一個聊天面板，讓你在這裡跟 Claude 說話 | ✅ 每天用：跟 Claude 說話 |
| **Claude Code** | Claude 的 AI 助理程式，真正做事的是它：搜尋、讀 PDF、寫筆記、整理文獻庫。Claudian 會在背景呼叫它 | ❌ 只在安裝時用一次 PowerShell 登入，之後不用打開 |
| **Python** | 程式語言：外掛的工具程式（讀 Zotero、重建文獻庫、畫標註）是用 Python 寫的 | ❌ Claude 會自己執行，你不用學 |
| **Git for Windows** | Claude Code 在 Windows 上執行指令需要它 | ❌ 裝好就不用管 |

### 第 1 步：安裝軟體

照順序安裝，已經裝過的就跳過：

1. **Git for Windows**：https://git-scm.com/downloads/win（安裝選項全部用預設）
2. **Python**：https://www.python.org/downloads/
   ⚠️ 安裝第一個畫面**一定要勾「Add python.exe to PATH」**
3. **Zotero 7**＋瀏覽器的 **Zotero Connector**：https://www.zotero.org/download/
4. **Better BibTeX**：
   到 https://retorque.re/zotero-better-bibtex/installation/ 下載 `.xpi` 檔 → Zotero「工具」→「外掛程式」→ 右上角齒輪 →「從檔案安裝外掛」
5. **Obsidian**：https://obsidian.md/download
6. **Claude Code**（要用 PowerShell 的地方只有這裡，和第 4 步存金鑰時貼一行指令）：
   1. 按開始鍵，搜尋「PowerShell」並打開。
   2. 貼上下面這行，按 Enter，等它裝完：
      ```
      irm https://claude.ai/install.ps1 | iex
      ```
   3. 輸入 `claude` 按 Enter，照畫面登入你的 Claude 帳號。
   4. 看到可以輸入的畫面就代表登入成功，輸入 `/exit` 離開，關掉 PowerShell。之後都不用再開。

### 第 2 步：建立筆記庫並裝 Claudian

1. 在「文件」裡建一個資料夾當研究筆記庫，例如 `研究筆記`。
2. 打開 Obsidian →「開啟資料夾作為 vault」→ 選這個資料夾。
3. Obsidian 左下角齒輪「設定」→「第三方外掛」→ 關閉「限制模式」→「瀏覽」→ 搜尋 **Claudian** → 安裝 → 啟用。
   （搜不到的話，照 Claudian 的 GitHub 頁面說明手動安裝：https://github.com/YishenTu）
4. 點左側欄的 Claudian 圖示，打開聊天面板，打一句「你好」測試。Claude 有回應就成功了。

### 第 3 步：請 Claude 安裝外掛

1. 在 Claudian 面板裡說：
   > 幫我安裝 Claude Code 外掛：執行 `claude plugin marketplace add nebula0/paper-manage-tool`，再執行 `claude plugin install lit-tools@lit-tools-market`
2. Claude 說安裝成功後，**完全關掉 Obsidian 再重開**，讓外掛生效。

<details>
<summary>不能連 GitHub？用壓縮檔安裝</summary>

在本頁右上角「Code」→「Download ZIP」下載，解壓縮放在固定的地方（例如 `C:\Users\你的名字\lit-tools`，之後不要移動），把上面指令裡的 `nebula0/paper-manage-tool` 換成這個資料夾路徑（前後加引號）。
</details>

### 第 4 步：跑設定精靈

在 Claudian 面板裡說：

> 設定 lit-tools

Claude 會一步一步帶你完成：檢查 Python 和 Zotero、存 Zotero 金鑰、建立資料夾、填你的研究主題與分類標籤、設定 Obsidian。中間會請你重開一次 Obsidian，重開後打開 Claudian 說「繼續設定 lit-tools」。

> 🔑 **金鑰等於密碼**：設定時 Claude 會給你一行指令，讓你在 PowerShell 把金鑰直接存進電腦。**不要把金鑰貼進對話。**

---

## 日常怎麼用

**打開 Obsidian，在右側的 Claudian 面板跟 Claude 說話。** 直接用中文說就好，不用記指令。

### 找文獻

> 幫我找「○○」的文獻，這是新主題，先找綜述

Claude 會先讀幾篇綜述、整理出這個領域有哪些做法，再一個方向一個方向搜。每篇找到的文章都先讀過摘要才收，排除的也會列出理由。搜完它會給你一個「待匯入」頁面，**你看過、說哪些要，才會正式加進文獻庫**。

### 問論文內容

> 我 Zotero 裡那篇 Smith 2023，它的樣品怎麼做的？

Claude 會讀 PDF 回答，附上頁碼和原句，同時：
- 在 PDF 上把引用的段落畫成**灰色**（評論開頭寫 `〔問：…〕`）
- 把這次問答存進這篇的 AI 筆記

### 改文章狀態

> 這篇排除，跟我的題目無關
> Chen 2024 我引言要引用

### 更新文獻庫

在 Zotero 存了新文章或畫了重點之後：

> 重建文獻庫

Claude 會更新文章頁，並幫新文章讀摘要、寫主要貢獻、分類。

---

## 在 Zotero 裡畫重點

照這個顏色畫，系統會依顏色統計，Obsidian 閱讀卡也會依顏色分區：

| 顏色 | 意思 |
|---|---|
| 🟡 黃 | 核心論述、要引用的句子 |
| 🔴 紅 | 懷疑、不同意 |
| 🟢 綠 | 方法值得參考 |
| 🔵 藍 | 關鍵數據 |
| 🟣 紫 | 還需要查資料（＝待辦） |
| ⚪ 灰 | **只有 Claude 用**，你不要用灰色 |

**看到灰色的 AI 標註：**
- 同意 → 改成你的顏色（＝採納）
- 不同意 → 直接刪掉
- 不處理也可以

**Zotero 筆記第一行寫一句主張**（例如「本文證明了 X」），會變成閱讀卡上的一句話摘要。

**閱讀程度不用自己填**：系統依你畫了幾頁判斷。判斷錯的話，在 Zotero 對那篇打 tag：`閱讀/沒看`、`閱讀/看過摘要`、`閱讀/略讀`、`閱讀/精讀`。

---

## 在 Obsidian 裡看

打開 `2_paper/文獻庫.base`，左上角可以切換檢視：

| 檢視 | 看什麼 |
|---|---|
| 總表 | 全部文章 |
| 最近新增 | 最新收錄的在最上面 |
| 卡片牆 | 有封面圖的卡片（自動從 PDF 截圖；想換就在 Zotero 用「選擇區域」框一張圖，評論打 `cover`） |
| 你還沒讀 | AI 讀得越深的排越上面，適合挑下一篇讀什麼 |
| 需要你下載 | 不在 Zotero 或沒有 PDF 的 |
| 有待查項 | 有紫色畫記的 |
| 候選與排除 | Claude 找到但還沒決定、或已排除的 |
| 本團隊 | 作者有你的指導教授或合作對象的 |

把 Zotero 畫記匯成閱讀卡：Obsidian 按 `Ctrl+P` →「Zotero Integration: 文獻卡片」→ 選文章。

⚠️ **`2_paper/文獻庫/` 和 `2_paper/任務/` 裡的頁面不要手動編輯**，它們是程式產生的，下次重建會被覆蓋。想改什麼跟 Claude 說；自己的想法寫在 Zotero 筆記或閱讀卡。

---

## 資料夾說明

```
研究筆記/
├─ 2_paper/
│  ├─ 文獻庫/          文章頁（自動產生，不要改）
│  ├─ 任務/            每次搜尋的紀錄頁（自動產生，不要改）
│  ├─ AI筆記/          Claude 讀每篇論文的筆記
│  ├─ notes/           你的閱讀卡（從 Zotero 匯入）
│  ├─ 文獻庫資料/       所有紀錄與設定（設定.json：研究主題、標籤、本團隊名單）
│  └─ 文獻庫.base       表格檢視
├─ 1_attachment/封面/  卡片牆的封面圖
└─ 筆記/               其他筆記（例如 Claude 整理的領域地圖）
```

建議用 Git 或雲端硬碟備份 `研究筆記` 資料夾；`文獻庫資料/` 是唯一無法重建的部分。

---

## 常見問題

**Q：Claudian 說找不到 Claude Code。**
Claudian 找不到 Claude Code 程式的位置。打開 PowerShell 輸入 `where.exe claude`，把顯示的路徑複製起來，貼到 Obsidian「設定」→「Claudian」裡的 Claude CLI 路徑欄位。

**Q：Claude 說找不到 Python。**
安裝 Python 時沒勾「Add python.exe to PATH」。重新執行安裝程式選「Modify」補勾，或解除安裝後重裝，然後重開 Obsidian。

**Q：灰色標註寫不進去，說找不到附件。**
那篇的 PDF 附件還沒同步到 zotero.org。在 Zotero 按右上角的同步按鈕，等它同步完再試。

**Q：文章頁出現「沒有正式 citekey」的警告。**
Better BibTeX 沒裝好，或那篇還沒產生代碼。在 Zotero 對那篇按右鍵 →「Better BibTeX」→「Refresh BibTeX key」。

**Q：想改分類標籤。**
跟 Claude 說「標籤詞表加一個 topic/xxx，意思是……」，它會更新 `設定.json`。

**Q：外掛有新版本。**
在 Claudian 說「幫我更新 lit-tools 外掛：執行 `claude plugin marketplace update lit-tools-market`，再執行 `claude plugin update lit-tools@lit-tools-market`」，然後重開 Obsidian。（用壓縮檔安裝的，先用新下載的資料夾取代舊的。）

**Q：會不會很貴？**
用的是你自己 Claude 訂閱的額度，沒有額外費用。精讀整篇論文比較耗額度，平常問特定段落就好。

---

## 授權

MIT License，見 [LICENSE](LICENSE)。歡迎改成適合你自己研究的版本。
