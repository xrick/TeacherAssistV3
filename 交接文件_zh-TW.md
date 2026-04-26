# TXT2PPTX — 專案交接手冊

**本文件撰寫者：** 離職開發者（完成交接）
**最後修訂：** 2026-04-25
**閱讀對象：** 接手此程式碼庫的下一位開發者
**預估閱讀時間：** 第一次仔細閱讀約需 30 分鐘

---

## 0. 摘要 — 請先閱讀此節

你接手的是一個可正常運作的 FastAPI 網頁應用程式，功能是透過 LLM 生成的大綱，將純文字轉換為 PowerPoint 簡報。程式碼庫規模不大（約 2,000 行 Python，前端無需建置步驟），大部分內容都相當直觀。**在動任何程式碼之前，你必須理解的唯一非trivial設計主題，是 `txt2pptx/backend/templates/` 中的模板策略系統（Template Strategy System）** — 這個系統在最後這次交接週期中被重寫，以解決反覆出現的「每加入新模板就會破壞版面」問題。

第一天請做三件事：

1. 閱讀 **§4 架構總覽**（10 分鐘）和 **§5 模板策略系統**（15 分鐘）。
2. 端對端執行測試流程（`§7 如何執行／開發`）。若未通過，請先修好環境再寫程式碼。
3. 瀏覽 **§9 已知問題與注意事項**，避免在已被發現的問題上浪費整天時間。

其他內容依需要查閱即可。

---

## 1. 專案概況

| 屬性 | 值 |
|---|---|
| **名稱** | TXT2PPTX（UI 中有時稱為「TeacherAssist」） |
| **目標** | 將中／英文文字轉換為專業的 `.pptx` 簡報 |
| **技術棧** | Python 3.10+、FastAPI、Uvicorn、python-pptx、Pydantic v2、Ollama（LLM）、原生 HTML/CSS/JS |
| **UI 語言** | 繁體中文（zh-TW），部分英文備援 |
| **LLM** | Ollama，OpenAI 相容端點（預設模型 `gpt-oss:20b`） |
| **狀態** | 可正常運作。支援 8 個模板。任意使用者模板的上傳與導入工作流程已接線完成，但需要手動新增程式碼（設計上如此——見 §5.4）。 |
| **測試框架** | 尚未設定。驗證透過 `txt2pptx/utils/` 中的專用 CLI 腳本進行。 |

### 與 gamma.app 的成熟度比較

前任開發者聲稱本專案涵蓋 gamma.app 文字轉簡報核心功能的約 30–40%。在策略重構（§5）之後，**模板處理已相當穩固**，但 gamma.app 的多項功能仍未實作——見 §10 路線圖。

---

## 2. 快速名詞對照表

| 術語 | 說明 |
|---|---|
| **Outline（大綱）** | 中間結構化表示層。一個由 `SlideData` 項目組成的 `PresentationOutline`（Pydantic 模型）。由 LLM 產生，由生成器消費。 |
| **SlideLayout（投影片版面）** | 9 種版面類型的列舉（`title_slide`、`section_header`、`bullets`、`two_column`、`image_left`、`image_right`、`key_stats`、`comparison`、`conclusion`）。每個 `SlideData` 聲明其中一種。 |
| **Template（模板）** | 位於 `txt2pptx/templates/` 中提供視覺外觀的 `.pptx` 檔案。 |
| **Strategy（策略）** | 位於 `txt2pptx/backend/templates/` 中的 Python 類別（`TemplateStrategy` 的子類別），封裝特定模板的重新計算參數——使用哪些投影片版面索引、哪個佔位符 idx 是標題／內文、字體縮放比例等。 |
| **Code-drawn 模式** | 完全跳過模板，透過 Inches 座標繪製所有形狀的替代路徑（`pptx_generator.py`）。保留以維持向後相容性。 |
| **Demo 備援模式** | 當 Ollama 無法連線時，LLM 呼叫會退回至啟發式文字分割器（`llm_service.py` 中的 `generate_outline_demo`）。產生結構上有效但外觀較差的大綱。 |

---

## 3. 儲存庫結構

```
TeacherAssistV3/
├── CLAUDE.md                       # ≪ Claude/AI 工具的專案說明
├── claudedocs/                     # 人工 + AI 撰寫的文件
│   ├── HANDOVER.md                 # ◀ 本文件
│   ├── dev_diary/                  # 日期標記的工作日誌
│   ├── how_to/                     # 特定任務指南
│   └── … 較舊的分析文件
├── pptxenv/                        # Python 虛擬環境（理想上應加入 gitignore）
├── refData/                        # 參考文獻／規格（唯讀）
└── txt2pptx/                       # ◀ 所有程式碼在此
    ├── backend/
    │   ├── main.py                 # FastAPI 進入點
    │   ├── models.py               # Pydantic 模型——資料結構的唯一來源
    │   ├── llm_service.py          # Ollama 客戶端 + demo 備援
    │   ├── pptx_generator.py       # code-drawn 生成器（無模板）
    │   ├── pptx_generator_template.py  # 舊版模板生成器（保留作備援）
    │   └── templates/              # ◀ 新策略套件（§5）
    │       ├── __init__.py         # STRATEGIES 登錄表
    │       ├── base.py             # TemplateStrategy ABC
    │       ├── ocean_gradient.py   # 正式基準策略
    │       ├── college_elegance.py # 每個支援模板一個策略
    │       ├── data_centric.py
    │       ├── high_contrast.py
    │       ├── minimalist_corporate.py
    │       ├── modernist.py
    │       ├── startup_edge.py
    │       └── zen_serenity.py
    ├── frontend/                   # 原生 HTML/CSS/JS，無建置步驟
    │   ├── index.html
    │   ├── app.js
    │   └── style.css
    ├── generated/                  # 輸出的 PPTX 檔案（自動建立）
    ├── templates/                  # .pptx 模板檔案本身
    │   ├── ocean_gradient.pptx
    │   ├── College_Elegance.pptx
    │   ├── … 另外 6 個
    │   └── MyCustom.pptx           # ⚠ 上傳流程測試的殘留檔案，見 §11
    ├── utils/                      # ◀ 新工具（§5.4）
    │   ├── __init__.py
    │   ├── inspect_template.py     # 內省任何 .pptx 檔案
    │   ├── scaffold_template_class.py  # 自動產生策略類別骨架
    │   └── validate_template_class.py  # 端對端驗證器
    ├── start.sh / stop.sh          # PID 管理的 Uvicorn 生命週期
    └── server.log                  # 執行期日誌（理想上應加入 gitignore）
```

---

## 4. 架構總覽

### 4.1 三階段流水線

```
┌──────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ 使用者文字   │ ──> │ LLM 大綱服務          │ ──> │ PPTX 生成器          │ ──> .pptx
│（前端）      │     │ llm_service.py        │     │ TemplateStrategy +   │
└──────────────┘     │（Ollama 或 demo）     │     │ python-pptx          │
                     └──────────────────────┘     └──────────────────────┘
                              │                              │
                              ▼                              ▼
                   PresentationOutline             ocean_gradient.pptx,
                   （已驗證的 Pydantic）           College_Elegance.pptx, …
```

第一階段隔離良好：LLM 被要求回傳符合 `PresentationOutline` 格式的嚴格 JSON。系統提示（位於 `llm_service.py:SYSTEM_PROMPT`，約 50 行中文）承擔了大部分工作。重試機制（`LLM_MAX_RETRIES`，預設 3 次）包裝了整個呼叫。

第二階段是本次交接週期的工作重心。`main.py` 中的分派器根據 `request.template` 選擇三條路徑之一：

| `request.template` | 路徑 |
|---|---|
| `"code_drawn"` | `pptx_generator.generate_pptx()` — 程式化繪製形狀，不使用模板檔案 |
| 任何存在於 `STRATEGIES` 中的值（目前 8 個） | `STRATEGIES[id]().generate(outline)` — 策略類別填入對應 `.pptx` 的佔位符 |
| 其他任何值 | `pptx_generator_template.generate_pptx()` — 舊版單一腳本生成器（保留作安全網） |

### 4.2 `PresentationOutline` 契約

這是兩端都必須遵守的資料格式。見 `backend/models.py`：

- `PresentationOutline` 包含 `title`、`subtitle`、`theme`、`slides: list[SlideData]`。
- `SlideData` 包含所有版面類型的每個可能欄位。每種版面使用其中的子集（例如 `BULLETS` 使用 `title` + `bullets`；`KEY_STATS` 使用 `title` + `stats: list[StatItem]`；`TWO_COLUMN` 使用 `left_title/left_column/right_title/right_column`）。
- `speaker_notes: str` 有 Pydantic 約束 `min_length=50, max_length=200`。**這個約束已讓 demo 備援踩過兩次坑——見 §9.1。** 任何構建 `SlideData` 且傳入非空但短於 50 字元 `speaker_notes` 的程式碼都會引發 `ValidationError`。

### 4.3 前端一覽

`frontend/` 刻意保持低技術含量：三個檔案，無打包工具，無 React。`app.js` 約 300 行，使用輕量選取器輔助函式（`els.foo()`）。UI 呼叫四個端點：

- `POST /api/generate` — 主要流程
- `GET /api/templates` — 填入模板下拉選單
- `GET /api/download/{filename}` — 下載產生的 PPTX
- `POST /api/upload-template` — 本週期新增（§5.5）

---

## 5. 模板策略系統

**這是需要仔細閱讀的章節。**

### 5.1 我們要解決的問題

在本週期之前，`pptx_generator_template.py` 有一個**硬編碼的單一 `LAYOUT_MAP` 和 `placeholder_map`**，所有模板都被假設遵守這個格式：

```python
LAYOUT_MAP = {
    SlideLayout.TITLE: 0, SlideLayout.SECTION: 1, SlideLayout.BULLETS: 2, …
}
PH_TITLE = 0; PH_BODY = 1; PH_PICTURE = 10; PH_SLIDE_NUM = 12
```

這個方式對 `ocean_gradient.pptx` 有效，是因為它曾經透過 `utils/fix_for_pptx_format.py` 手動調整以匹配那些數值。其他 7 個模板「支援」只是因為載入器不會崩潰——佔位符索引往往是錯的，內容會悄悄跑到錯誤的形狀（或直接消失）。

前任負責人在 `CLAUDE.md` 中將此識別為專案的核心技術難題（「套用不同參考 pptx 模板時，新模板的所有參數都需要重新計算」）。

### 5.2 選定的解決方案：策略模式 + 腳手架工具

我們拒絕採用 gamma.app 風格的「任何使用者模板，完全自動化」方式。原因：

1. 真實模板有任意的版面數量、任意的佔位符索引和不同的長寬比。沒有任何啟發式方法能持續產生良好輸出。
2. 即使是 gamma.app 在使用者上傳的主題上也會出現明顯的品質下降。
3. 支援的模板集很小（8 個），增長緩慢。手動調整是可管理的。

我們改為建立：

- **`TemplateStrategy` 抽象基底類別**，封裝一個模板的重新計算參數，並暴露統一的 `generate(outline) -> bytes` API。
- **每個支援模板對應一個具體子類別**，包含硬編碼的 `layout_map`、`placeholder_map`、`font_scale`、`aspect_ratio`。子類別可以覆寫任何 `fill_*` 方法，當預設行為不夠用時使用。
- **5 步驟導入工作流程**，用於新增下一個模板：80% 的工作由 `inspect_template.py` 和 `scaffold_template_class.py` 自動完成；剩餘 20% 是人工解決 `TODO` 註解並驗證輸出。
- **上傳 UI**，讓非開發者可以將 `.pptx` 檔案拖入系統。若該檔名已有對應的策略，則立即可用。否則 UI 會在對話框中顯示 5 步驟說明，並將該選項停用，直到開發者完成註冊。

### 5.3 `TemplateStrategy` 契約

檔案：`backend/templates/base.py`。每個具體策略都繼承自此類別。子類別**必須設定或接受預設值**的類別屬性：

| 屬性 | 類型 | 用途 |
|---|---|---|
| `template_file` | `str` | `txt2pptx/templates/` 中的檔名（例如 `"ocean_gradient.pptx"`） |
| `layout_map` | `dict[SlideLayout, int]` | 將 9 種 SlideLayout 各自對應至 .pptx 中的投影片版面索引 |
| `placeholder_map` | `dict[str, int]` | 語義名稱 → 佔位符 idx。必要鍵：`title`、`body`。選用：`body_right`、`body_col2`、`body_col3`、`picture`、`slide_num` |
| `font_scale` | `float` | 套用至硬編碼字體大小的乘數（例如 `0.85`）；以 `ocean_gradient`（= 1.0）為校準基準 |
| `aspect_ratio` | `tuple[float, float]` | 投影片尺寸，單位為英吋 |

預設的 `fill_*` 方法（每種 `SlideLayout` 各一個）處理將文字放入具名佔位符的常見情況。只有當版面需要特殊處理時才需覆寫（目前 8 個策略均未覆寫任何方法——預設值已足夠）。

此類別在 `_layout_index` 中還有一條備援鏈，若策略未對應（例如）`IMAGE_LEFT`，則該版面類型的請求會退回至 `BULLETS`。實務上腳手架工具會填滿每個槽位，因此很少觸發此備援。

### 5.4 5 步驟導入工作流程（交付成果）

當有新的 `.pptx` 模板加入時：

```bash
# 1. 內省模板——查看其版面、佔位符、主題
python -m txt2pptx.utils.inspect_template MyTemplate.pptx

# 2. 產生策略類別骨架
python -m txt2pptx.utils.scaffold_template_class MyTemplate.pptx
#  → 寫入 backend/templates/my_template.py，包含 TODO 待辦事項

# 3. 手動編輯 my_template.py
#    - 解決所有 TODO 註解
#    - 驗證自動偵測的 layout_map 對應是否符合設計意圖
#    - 若渲染的文字看起來太大／太小，調整 font_scale

# 4. 驗證
python -m txt2pptx.utils.validate_template_class MyTemplateStrategy
#  → 寫入 /tmp/validation/validation_MyTemplateStrategy.pptx
#    在 PowerPoint 或 LibreOffice 中開啟並目視檢查

# 5. 在 backend/templates/__init__.py 中進行登錄
#    新增 import 陳述式 + STRATEGIES 條目，約 1-2 行。
```

步驟 1、2、4 是工具化的部分。步驟 3 是人工判斷。步驟 5 是機械性操作。

腳手架工具使用三輪處理，確保每個 `SlideLayout` 都獲得版面指派：

1. **關鍵字比對**版面名稱——多語言表格（`LAYOUT_KEYWORDS`）能辨識英文、中文和德文版面名稱。
2. **自動填充剩餘槽位**，使用任何有真實內容佔位符的未使用版面（跳過純空白／僅含頁尾的版面——這個 bug 曾讓我們踩過坑，見 §9.2）。
3. **最後備援**至 BULLETS 版面，處理仍未對應的槽位。

這就是為什麼所有 8 個當前模板都能通過驗證器的「每張投影片都有可見文字」檢查：腳手架工具不會留下任何未對應的 `SlideLayout`。

### 5.5 上傳流程（面向使用者的 UX）

```
┌────────────────────────────────────────────────────────────────────┐
│ 使用者點擊「上傳自訂模板 (.pptx)」                                  │
│      │                                                             │
│      ▼                                                             │
│ POST /api/upload-template（multipart）                             │
│      │                                                             │
│      ├── 儲存至 txt2pptx/templates/<n>.pptx                       │
│      ├── 以 python-pptx 驗證（拒絕格式錯誤的檔案）                 │
│      └── 檢查 STRATEGIES 字典                                      │
│           │                                                        │
│      ┌────┴────┐                                                   │
│      ▼         ▼                                                   │
│  已登錄        未登錄                                              │
│  (200 OK)      (202 Accepted)                                      │
│      │         │                                                   │
│      │         └─→ 回傳導入酬載：                                  │
│      │             { steps: [{cmd, desc} × 5] }                   │
│      │             前端顯示包含 5 個編號步驟的對話框               │
│      │                                                             │
│      ▼                                                             │
│  重新整理 /api/templates 下拉選單，選取新模板                       │
└────────────────────────────────────────────────────────────────────┘
```

注意事項：

- 端點永遠都會儲存檔案。這讓開發者的工作更輕鬆（.pptx 已在 `templates/` 中，隨時可用 `inspect_template`）。
- 未登錄的模板在下拉選單中顯示為 `<n> ⚠ 未註冊`，並在完成登錄後的下次伺服器重啟前保持停用狀態。
- `/api/templates` 每個模板都暴露 `is_registered: bool`；前端使用此欄位將不支援的選項變灰。

### 5.6 此系統**無法**解決的問題

請誠實面對自己和你的利害關係人：

- **自動調整文字以適應任意佔位符尺寸** — `font_scale` 是單一的全域乘數，不是逐形狀的重新計算。在空間緊湊的模板中，較長的條列項目可能會溢出。
- **主題感知色彩提取** — 策略不會讀取模板的 `theme1.xml` 來為程式碼新增的裝飾形狀重新著色。我們不需要這個功能，因為 9 個預設的 `fill_*` 方法只設定文字內容，不設定顏色。
- **內容感知版面選擇** — gamma.app 根據內容形狀選擇版面（「4 個短條列 → BULLETS，2 段長文 → TWO_COLUMN」）。此處由 LLM 在大綱中處理；策略只負責渲染。
- **圖片插入** — `SlideData` 上的 `image_prompt` 欄位有被收集，但實際上沒有插入任何圖片。PICTURE 佔位符保持空白。（gamma.app 呼叫圖片生成 API，我們沒有。）

如果你決定要彌補這些差距，請建立 issue 並為每個項目預留至少一整週的預算。

---

## 6. 本週期變更的逐檔清單

### 6.1 新增的檔案

| 檔案 | 用途 | 大小 |
|---|---|---|
| `backend/templates/__init__.py` | `STRATEGIES` 登錄表；輔助函式 `get_strategy` / `is_registered` / `list_registered` | 約 40 行 |
| `backend/templates/base.py` | `TemplateStrategy` ABC——每個策略實作的契約 | 約 290 行 |
| `backend/templates/ocean_gradient.py` | 第一個具體策略。`font_scale=1.0` 是校準基準。 | 約 38 行 |
| `backend/templates/college_elegance.py` | 自動腳手架後登錄 | 約 60 行 |
| `backend/templates/data_centric.py` | 同上 | 約 60 行 |
| `backend/templates/high_contrast.py` | 同上 | 約 60 行 |
| `backend/templates/minimalist_corporate.py` | 同上 | 約 60 行 |
| `backend/templates/modernist.py` | 同上 | 約 60 行 |
| `backend/templates/startup_edge.py` | 同上 | 約 60 行 |
| `backend/templates/zen_serenity.py` | 同上 | 約 60 行 |
| `utils/__init__.py` | 空的套件標記 | 0 行 |
| `utils/inspect_template.py` | 唯讀模板內省。`--json` 旗標供工具使用。 | 約 200 行 |
| `utils/scaffold_template_class.py` | 含多語言啟發式的策略類別生成器。 | 約 330 行 |
| `utils/validate_template_class.py` | 7 項檢查的端對端驗證器。`--all` 旗標可迭代整個登錄表。 | 約 270 行 |

### 6.2 修改的檔案

| 檔案 | 變更內容 |
|---|---|
| `backend/main.py` | (a) 將 `STRATEGIES` 接入 `/api/generate` 分派；(b) 在 `/api/templates` 中新增 `is_registered` 欄位；(c) 新增帶有導入酬載的 `POST /api/upload-template` 端點。 |
| `backend/llm_service.py` | 將兩個 demo 模式的 `speaker_notes` 字串擴充至 ≥50 個字元，以滿足 Pydantic 的 `min_length` 約束。**這是既有的 bug，非本週期工作所引起**，但阻礙了驗證——見 §9.1。 |
| `frontend/index.html` | 在模板選擇器旁新增檔案上傳按鈕，以及 5 步驟警告的對話框元素。 |
| `frontend/app.js` | 新增上傳處理器、下拉選單中的 `is_registered` 渲染、對話框顯示／關閉。 |
| `frontend/style.css` | 上傳按鈕、狀態徽章和對話框的樣式（附加約 140 行）。 |

### 6.3 未修改但值得了解的檔案

| 檔案 | 重要原因 |
|---|---|
| `backend/pptx_generator_template.py` | **舊版**模板生成器。仍然存在，可透過 `main.py` 中的 `else` 分支存取，適用於名稱不在 `STRATEGIES` 中的任何模板。刻意保留作安全網。一旦你在正式環境中信任策略系統，即可移除此檔案和分派分支。 |
| `backend/pptx_generator.py` | 完全**程式化繪製**的生成器。約 460 行。當 `request.template == "code_drawn"` 時仍為作用中路徑。獨立於模板之外。因為對 .pptx 檔案沒有任何外部依賴，適合用於除錯。 |
| `backend/llm_service.py`（其餘部分） | 有穩健的 3 次嘗試重試迴圈、系統提示和 demo 備援。請從頭到尾閱讀一遍。 |
| `start.sh` / `stop.sh` | PID 管理的 Uvicorn 生命週期。使用 `txt2pptx/server.log` 作為輸出。請閱讀這些腳本，而不是自行猜測如何啟動伺服器。 |

---

## 7. 如何執行／開發／驗證

### 7.1 首次設定

```bash
cd TeacherAssistV3

# 啟動虛擬環境（前任開發者使用 pptxenv/，但在全新環境中可能不存在）
python3 -m venv pptxenv
source pptxenv/bin/activate

# 依賴套件——目前尚無 requirements.txt（見 §10）
pip install fastapi uvicorn python-pptx pydantic httpx python-multipart

# 若要使用 Ollama 執行，請另外安裝並拉取模型：
ollama pull gpt-oss:20b
```

### 7.2 執行伺服器

```bash
cd txt2pptx
OLLAMA_MODEL=gpt-oss:20b bash start.sh        # PID 管理方式
# 或
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

然後開啟 `http://localhost:8000`。

```bash
curl http://localhost:8000/api/health     # {"status":"ok",…}
bash stop.sh
```

### 7.3 驗證模板策略（開發者迴圈）

```bash
# 從儲存庫根目錄執行，不是 txt2pptx/
python -m txt2pptx.utils.validate_template_class --all              # 所有已登錄的
python -m txt2pptx.utils.validate_template_class OceanGradientStrategy  # 單一策略
```

輸出至 `/tmp/validation/validation_<n>.pptx`。**在宣告策略可用之前，務必目視開啟確認**——驗證器只檢查結構正確性，不檢查美觀性。

### 7.4 API 端對端煙霧測試

目前沒有自動化測試套件（待辦事項——見 §10）。下方是前任開發者在交接期間使用的腳本；複製至 `/tmp/test_gen.py`：

```python
import json, urllib.request

PAYLOAD = {
    "text": "人工智慧（AI）正在革命性地改變各行各業。…",
    "num_slides": 5,
    "language": "zh-TW",
    "style": "professional",
}
TEMPLATES = ["ocean_gradient", "College_Elegance", "Data_Centric",
             "High_Contrast", "Minimalist_Corporate", "Modernist",
             "Startup_Edge", "Zen_Serenity"]

for tid in TEMPLATES:
    body = dict(PAYLOAD, template=tid)
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.loads(r.read())
    print(f"{tid:24s}  success={data.get('success')}  file={data.get('filename')}")
```

預期結果：全部 8 個 `success=True`。

### 7.5 不透過 UI 測試上傳流程

```bash
# 已登錄的模板
curl -X POST http://127.0.0.1:8000/api/upload-template \
     -F "file=@txt2pptx/templates/ocean_gradient.pptx"

# 未登錄的模板（重新命名以觸發 202 路徑）
cp txt2pptx/templates/ocean_gradient.pptx /tmp/SomeNewLook.pptx
curl -X POST http://127.0.0.1:8000/api/upload-template \
     -F "file=@/tmp/SomeNewLook.pptx" -w "\nHTTP %{http_code}\n"
```

第二個呼叫應回傳 HTTP 202 以及包含 `steps` 陣列的 JSON 主體。

---

## 8. API 參考（簡版）

### `POST /api/generate`
主體（`GenerateRequest`）：
```json
{
  "text": "字串（1..50000）",
  "num_slides": 8,
  "language": "zh-TW",
  "style": "professional",
  "template": "ocean_gradient"
}
```
回應（`GenerateResponse`）：`{ success, filename, message, outline }`。

### `GET /api/templates`
回傳 `{ templates: [{ id, name, description, available, is_template, is_registered }] }`。

### `POST /api/upload-template`（multipart）
欄位名稱：`file`。若已登錄回傳 200，未登錄回傳含導入酬載的 202，格式錯誤回傳 400。

### `GET /api/download/{filename}`
以正確的 MIME 類型串流傳輸 PPTX。

### `GET /api/health`
`{"status":"ok","version":"0.1.0"}`。

---

## 9. 已知問題與注意事項

### 9.1 Demo 備援的 `speaker_notes` 長度很脆弱

`SlideData.speaker_notes` 有 `min_length=50`。Demo 備援構建的是硬編碼的備註；**其中兩個短到只要編輯一個字元就會破壞 Pydantic 驗證**。本週期我們將兩者都擴充至 ≥56 個字元，但根本的脆弱性仍存在。未來的修復方式：將 `min_length` 降低至 30，或讓 demo 備援以程式化方式合成備註。見 `llm_service.py:186` 和 `:269`。

### 9.2 啟發式方法在比對 CONCLUSION 時必須跳過「空白」版面

幾個 PowerPoint 主題附帶的「Leer」/「Blank」版面只有 DATE/FOOTER/SLIDE_NUMBER 佔位符。腳手架工具的第一版因為 `"blank"` 關鍵字而將這些對應至 `CONCLUSION`——結果：空白的結論投影片。**已在** `scaffold_template_class.py` 中**修復**，方法是引入 `_has_content_placeholder()` 並移除誤導性關鍵字。若你新增關鍵字，任何非空白的 `SlideLayout` 都**不要**使用 `"blank"`/`"leer"`。

### 9.3 佔位符 idx 是針對個別版面的，不是全域的

每個策略中的 `placeholder_map` 是扁平的 `dict[str, int]`。這能運作是因為目前所有 8 個支援的模板恰好在各版面中使用穩定的索引（幾乎所有版面都是 idx 0 = 標題，idx 1 = 內文）。**這個假設對任何未來的模板都可能失效。** 若失效，最乾淨的修復方式是擴充 `TemplateStrategy`，讓 `placeholder_map` 變成 `dict[SlideLayout, dict[str, int]]`（逐版面）。請留意此問題。

### 9.4 SOCKS 代理 + httpx

若環境中 `ALL_PROXY` 設為 SOCKS URL，httpx 在沒有 `socksio` 的情況下會拒絕啟動。請安裝 `httpx[socks]` 或在啟動前取消設定該環境變數。

### 9.5 交接期間沙盒檔案權限問題

在上傳流程煙霧測試期間，我們留下了一個殘留檔案 `txt2pptx/templates/MyCustom.pptx`。這是一個有效的 PPTX（`ocean_gradient.pptx` 的副本），但沒有對應的已登錄策略，因此在 UI 中顯示為 `⚠ 未註冊`。**請手動刪除它**：

```bash
rm txt2pptx/templates/MyCustom.pptx
```

（前任開發者的沙盒沒有刪除權限。）

### 9.6 無測試、無 linter、無 requirements.txt

這些都在前任開發者的「想新增」清單上。都不阻塞開發。見 §10。

### 9.7 `code_drawn` 生成器和策略生成器各自獨立演進

若你在 `pptx_generator.py` 中更改 `Theme` 顏色或版面座標，**策略類別不會繼承那些變更**——它們各自讀取自己的 `.pptx` 檔案。這在架構上是正確的，但請注意：不要期望「我調整了品牌顏色」的更改會自動傳播。

### 9.8 前端的「簡報風格」選單刻意隱藏

`index.html` 有一個 `<!-- 已被注解掉 -->` 的風格選擇器區塊。使用者只能看到模板選擇。在沒有確定 `style` 在 `template` 旁邊應代表什麼含義之前，**不要**不小心重新啟用它。

---

## 10. 路線圖與建議的後續工作

大致按優先順序排列。每個項目都是一週以內可完成的工作（有特別說明者除外）。

### 高槓桿、低風險

1. **新增 `requirements.txt`**，從當前的 `pptxenv/` 衍生出鎖定版本。一小時任務。
2. **在 `txt2pptx/test/` 中新增煙霧測試腳本**（CLAUDE.md 顯示此資料夾已存在）。至少在 CI 中執行 `validate_template_class --all` 和 §7.4 的 API 煙霧測試。半天任務。
3. **Pre-commit hook**，執行 `python -m compileall txt2pptx/` 和 `python -m pyflakes txt2pptx/` 以提早捕捉語法錯誤。一小時任務。
4. **刪除殘留的 `MyCustom.pptx`**（§9.5）。

### 中等

5. **在 PICTURE 佔位符中插入真實圖片。** 選擇圖片來源（以 `image_prompt` 搜尋 Unsplash？本地 AI 圖片生成？）並接入 `_fill_image_left/right` 方法。1 週。
6. **自動調整文字大小** — 透過 PIL 或 python-pptx 文字框自動調整大小，測量渲染的文字寬度，並逐形狀調整 `font_scale`。1 週。
7. **主題感知色彩提取** — 在每個策略中，讀取模板的 `theme1.xml`，並為程式碼新增的裝飾形狀重新著色。3 天。
8. **逐版面佔位符映射**（§9.3），在下一個模板打破扁平映射假設時實作。2 天。

### 較大型

9. **用 `pytest` 建立完整的測試套件。** 尤其是每個策略的黃金檔案測試：渲染驗證簡報，斷言 XML 結構與快照相符。1 週。
10. **移除舊版 `pptx_generator_template.py`**，一旦你信任策略登錄表在正式環境中 ≥1 個月沒有迴歸。更新 `main.py` 以移除舊版備援分支。半天清理。
11. **內聯編輯 UI** — 最接近 gamma.app 同等功能的差距。在最終生成之前，在頁面上以可編輯儲存格渲染大綱。至少 2 週。

### 推測性

12. **模板外掛市集** — 讓使用者分享策略類別。需要沙盒化不受信任的程式碼；並非易事。

---

## 11. 決策日誌 — 為什麼事情是現在這個樣子

### 為什麼用策略模式，而不是設定檔？

我們對兩種方式都做了原型。列出版面索引和字體縮放比例的單一 `templates.yaml` 更短（每個模板約 10 行），但它無法表達覆寫行為。一旦模板需要自訂的 `_fill_key_stats`（例如：以圓形而非一排的方式排列統計數據），YAML 方式就迫使我們發明一種迷你語言。子類別將覆寫保持為純 Python。

### 為什麼腳手架工具要用三輪處理？

只用第一輪會留下空缺（大聲失敗）。只用第二輪會產生糟糕的指派，因為即使使用者明顯有其他意圖，豐富版面也會被名稱比對。兩者結合意味著：名稱具有描述性時使用規則，名稱沒有描述性時優雅回退，且永遠不留下空槽位。

### 為什麼保留舊版 `pptx_generator_template.py`？

風險管理。策略系統是新的。若正式環境出現迴歸，舊版生成器讓操作者只需調整一個設定旗標即可恢復到可運作的建置版本。在策略單一運作一個月沒有事件後再移除。

### 為什麼上傳時採用關閉失敗（fail-closed）策略（要求手動類別登錄）？

因為 gamma.app「任何模板，完全自動化」的 UX 對這個程式碼庫的資源來說是錯誤的目標。產生明顯損壞的輸出比拒絕檔案（並提供清晰的修復路徑）更糟。每新增一個模板的開發者成本約為 10–30 分鐘的手動審核——可以接受。

### 為什麼 `font_scale` 是單一數值？

務實考量。完美的實作會根據佔位符尺寸，逐 `_fill_*` 方法計算字體大小。但 (a) 我們沒有每個模板「正確」字體大小的基準資料，且 (b) 我們提供的模板是人類為人類規模的文字所設計的——因此單一全域縮放比例通常與正確值相差只有幾點。只有在出現真實的溢出問題時才需重新審視。

---

## 12. 我想對過去的自己說的話

1. **每次都先讀 `models.py`。** 這個程式碼庫中大多數細微的 bug 都追蹤回 Pydantic 約束悄悄拒絕某個值。
2. **在開啟任何 PowerPoint 檔案之前先執行驗證器。** 它快得多。
3. **不要相信 LLM 一定會產生恰好 9 張投影片的大綱。** 它通常會，但要把數量視為請求，而不是保證。
4. **前端沒有建置步驟** — `Ctrl-R` 是你唯一的部署方式。沒有強烈理由不要引入建置步驟；這種簡單性本身就是一個功能。
5. **`claudedocs/` 資料夾裡充滿了來自早期工作週期的中間分析。** 大多數作為背景資料仍然有用，但它們都早於本週期的策略重構。有疑問時，本 HANDOVER.md 優先於它們。

---

## 13. 聯絡方式與延伸閱讀

- 儲存庫根目錄的 CLAUDE.md 有權威性的「這個專案做什麼」說明和最近更新日誌。
- `claudedocs/dev_diary/2026-02-17_speaker_notes_optimization.md` 記錄了 speaker_notes 50 字元約束的設計。
- `claudedocs/重試機制設計文件.md` 涵蓋 LLM 重試策略。
- `claudedocs/architecture_analysis_dual_engine.md` 涵蓋程式化繪製與基於模板的雙路徑設計。
- `refData/` 資料夾有外部論文和規格（唯讀）。

有疑問時，讀原始碼。它很小。

祝你好運。— 離職開發者
