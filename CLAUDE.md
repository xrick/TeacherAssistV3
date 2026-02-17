# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TXT2PPTX: A web application that converts plain text into structured PowerPoint presentations using LLM-generated outlines. The UI is in Traditional Chinese (zh-TW).

## Commands

```bash
# Activate virtual environment
source pptxenv/bin/activate

# Start server (from txt2pptx/)
cd txt2pptx && bash start.sh

# Stop server
cd txt2pptx && bash stop.sh

# Manual start (from repo root)
cd txt2pptx && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Health check
curl http://localhost:8000/api/health

# Install dependencies (no requirements.txt yet — install manually)
pip install fastapi uvicorn python-pptx pydantic httpx
```

## Environment Variables

- `OLLAMA_URL` — Ollama server address (default: `http://localhost:11434`)
- `OLLAMA_MODEL` — Model name (default: `gpt-oss:2b`). The local machine only has `gpt-oss:20b` installed, so start with `OLLAMA_MODEL=gpt-oss:20b bash start.sh`
- `PORT` — Uvicorn port (default: `8000`), used by start.sh/stop.sh

## Architecture

The app lives entirely in `txt2pptx/` with a 3-stage pipeline:

```
User text → [LLM Outline Generation] → [PPTX Builder] → .pptx file
                 llm_service.py          pptx_generator.py
```

### Backend (`txt2pptx/backend/`)

- **main.py** — FastAPI app. Routes: `POST /api/generate`, `GET /api/download/{filename}`, `GET /api/health`. Serves frontend static files from `/`. Output PPTX files are saved to `txt2pptx/generated/{uuid8}.pptx`.
- **models.py** — Pydantic v2 models. `GenerateRequest` (text, num_slides, language, style), `PresentationOutline` / `SlideData` (intermediate), `GenerateResponse` (output). `SlideLayout` enum defines 9 layout types: TITLE, SECTION, BULLETS, TWO_COLUMN, IMAGE_LEFT, IMAGE_RIGHT, KEY_STATS, COMPARISON, CONCLUSION.
- **llm_service.py** — Calls Ollama's OpenAI-compatible API (`/v1/chat/completions`) via `httpx`. `generate_outline()` is the entry point: tries LLM first, falls back to `generate_outline_demo()` (heuristic text-splitting) if Ollama is unavailable. Timeout is 600s for CPU-only inference. The `SYSTEM_PROMPT` is a long Chinese prompt that constrains LLM output to strict JSON matching the `PresentationOutline` schema — first slide must be title_slide, last must be conclusion, bullets limited to 3-5 per slide.
- **pptx_generator.py** — Builds PPTX using `python-pptx`. All slides are **code-drawn** (no .pptx template file): starts from `Presentation()` blank, uses `slide_layouts[6]` (Blank), and positions every element via hardcoded Inches coordinates (~460 lines). A `BUILDERS` dict maps each `SlideLayout` enum to a builder function. `Theme` class holds the Ocean Gradient color scheme (primary `#065A82`, accent `#02C39A`) and Calibri fonts.

### Frontend (`txt2pptx/frontend/`)

Vanilla HTML/CSS/JS (no build step). `app.js` calls `/api/generate`, shows progress simulation, renders outline preview, and provides download link. Keyboard shortcut: Ctrl+Enter to generate.

### Key Data Flow

1. Frontend POSTs `{text, num_slides, language, style}` to `/api/generate`
2. `llm_service.generate_outline()` sends text + SYSTEM_PROMPT to Ollama, parses JSON response into `PresentationOutline`
3. `pptx_generator.generate_pptx()` iterates `outline.slides`, dispatches each to a layout-specific builder via `BUILDERS` dict
4. PPTX bytes saved to `txt2pptx/generated/`, filename returned to frontend

### PPTX Generation — Code-Drawn Design

The current architecture does **not** use .pptx template files. All 9 slide types are drawn programmatically:

- Background colors via `_set_slide_bg()`
- Shapes (rectangles, ovals) via `_add_shape()`
- Text boxes with manual positioning via `_add_text_box()`
- Bullet lists with custom XML markers via `_add_bullets()`
- Image areas are gray placeholder rectangles (no real image insertion)
- A template file `txt2pptx/templates/ocean_gradient.pptx` has been created for future migration to template-based generation
- See `claudedocs/how_to/pptx_template_guide.md` for migration analysis toward template-based approach

### LLM Integration

Uses Ollama's OpenAI-compatible endpoint (`/v1/chat/completions`), **not** the native `/api/chat`. Response parsing strips markdown fences before `json.loads()`. When Ollama is unreachable, the demo fallback splits input text into paragraphs and distributes across slides with rotating layouts.

## Project Structure

```text
txt2pptx/
  backend/           # FastAPI + python-pptx
  frontend/          # Vanilla HTML/CSS/JS (no build step)
  generated/         # Output PPTX files (auto-created, gitignored ideally)
  templates/         # .pptx template files (ocean_gradient.pptx)
  start.sh / stop.sh # Server lifecycle scripts (PID-managed)
claudedocs/          # Claude-generated analysis & documentation
  how_to/            # Template guides, Google Slides workflow docs
refData/             # Reference materials, papers, plans
pptxenv/             # Python virtual environment (not in git)
```

## Tech Stack

- Python 3.11, FastAPI, Uvicorn, httpx, python-pptx, Pydantic v2
- No test framework configured yet
- No linter/formatter configured yet
- No requirements.txt yet — dependencies listed in start.sh error message

---

## Recent Updates

### 2026-02-17: Speaker Notes 品質優化與重試機制實作

**完成項目**:

1. ✅ **重試機制實作** - 3 次重試，100% LLM 成功率
2. ✅ **模板 UI 優化** - 8 個中文模板名稱顯示
3. ✅ **Speaker Notes 品質提升** - 從 18.1 字 → 72.4 字 (100% 達標)

#### 1. 重試機制 (LLM Retry Logic)

**實作位置**: [txt2pptx/backend/llm_service.py](txt2pptx/backend/llm_service.py)

**環境變數**:

- `LLM_MAX_RETRIES=3` - 最大重試次數
- `LLM_RETRY_DELAY=1.0` - 重試間隔（秒）

**測試結果**:

```text
總測試次數: 10
LLM 成功: 10/10 (100%)
Demo Fallback: 0/10 (0%)
平均響應時間: 78.1 秒
```

**關鍵代碼**:
```python
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
RETRY_DELAY = float(os.environ.get("LLM_RETRY_DELAY", "1.0"))

for attempt in range(1, MAX_RETRIES + 1):
    try:
        logger.info(f"🚀 Attempting Ollama LLM (嘗試 {attempt}/{MAX_RETRIES})")
        result = await generate_outline_with_llm(request)
        logger.info(f"✅ LLM generation successful on attempt {attempt}")
        return result
    except Exception as e:
        if attempt < MAX_RETRIES:
            logger.info(f"🔄 Retrying in {RETRY_DELAY}s...")
            await asyncio.sleep(RETRY_DELAY)
```

#### 2. 模板 UI 優化

**實作位置**: [txt2pptx/backend/main.py:92-127](txt2pptx/backend/main.py#L92-L127)

**8 個模板及中文名稱**:

- `College_Elegance` → 學院典雅
- `Data_Centric` → 數據導向
- `High_Contrast` → 高調對比
- `Minimalist_Corporate` → 極簡商務
- `Modernist` → 摩登現代
- `ocean_gradient` → 預設版面
- `Startup_Edge` → 新創活力
- `Zen_Serenity` → 靜謐禪意

**API 端點**: `GET /api/templates` 返回包含中文名稱的模板列表

#### 3. Speaker Notes 品質優化 🎯

**問題診斷**:

- 初始狀態: Notes 平均長度 18.1 字，不符合教學需求
- 根本原因: SYSTEM_PROMPT 說「建議」，Pydantic schema 說「Optional」

**解決方案**:

**A. SYSTEM_PROMPT 結構化** ([llm_service.py:48-54](txt2pptx/backend/llm_service.py#L48-L54)):

```python
- speaker_notes：**每頁必須提供 50-100 字的詳細補充說明**，包含：
  • 背景資訊和脈絡說明（10-20 字）
  • 重點內容的延伸解釋（20-30 字）
  • 實例或應用場景（20-30 字）
  • 引導討論的問題或思考點（10-20 字）
```

**B. Pydantic 強制約束** ([models.py:36](txt2pptx/backend/models.py#L36)):
```python
# 修改前
speaker_notes: Optional[str] = None

# 修改後
speaker_notes: str = Field(
    default="",
    min_length=50,      # 🎯 關鍵約束
    max_length=200,
    description="詳細補充說明，50-100字為佳"
)
```

**最終測試結果** (College_Elegance 模板):

```text
✅ Bullet 長度: 25.3 字 (目標: ≥ 15 字)
✅ Speaker notes 覆蓋率: 10/10 (100%)
✅ Speaker notes 平均長度: 72.4 字 (目標: ≥ 50 字) 🎉
✅ Layout 多樣性: 5 種 (bullets, key_stats, section_header, title_slide, two_column)
✅ 非 Demo Mode: 是
✅ PPTX 下載: 成功

品質覆蓋率: 100% (6/6) 🎉
```

**改進歷程**:

| 階段 | Notes 覆蓋率 | Notes 長度 | 品質通過率 |
|------|--------------|------------|------------|
| 初始 | 100% | 18.1 字 ❌ | 66.7% |
| SYSTEM_PROMPT 優化 | 0% ❌ | 0 字 | 50.0% |
| Pydantic min=30 | 100% | 46.0 字 ⚠️ | 50.0% |
| **Pydantic min=50** | **100%** | **72.4 字** ✅ | **100%** ✅ |

**關鍵洞察**:

- **Pydantic schema > SYSTEM_PROMPT**: 硬約束優先於軟引導
- **LLM 行為模式**: 生成長度 ≈ `min_length × 1.5`
- **結構化引導**: 4 項內容要求幫助 LLM 生成多層次內容

#### 測試框架

**整合測試**: [test/test_integration_template.py](test/test_integration_template.py)

- 測試內容: test/Discrete_mathematics.txt (2908 字元)
- 品質檢查: 6 項指標（bullet 長度、notes 覆蓋率、notes 長度、layout 多樣性、demo 偵測、下載成功）
- 模板支持: 可指定任意模板進行測試

**重試機制測試**: [test/test_retry_mechanism.py](test/test_retry_mechanism.py)

- 10 次連續測試，驗證成功率
- 品質評分: 4 項指標（bullet 長度、notes 覆蓋率、notes 長度、layout 多樣性）

#### 相關文檔

- [開發日誌 - 2026-02-17](claudedocs/dev_diary/2026-02-17_speaker_notes_optimization.md) - 完整技術分析
- [Notes 覆蓋率指標說明](claudedocs/Notes覆蓋率指標說明.md) - 指標定義與計算
- [重試機制實作總結](claudedocs/重試機制實作總結.md) - 重試策略與測試結果

#### 性能指標

- LLM 成功率: **100%** (10/10 測試)
- Speaker Notes 長度: **72.4 字** (144% 達標)
- 品質覆蓋率: **100%** (6/6 檢查)
- 響應時間: 86.9 秒（含 1 次重試）
- Layout 多樣性: **5 種** (超過目標)

---

### 2026-02-18: UI 簡化與模板系統修復

**完成項目**:

1. ✅ **UI 簡化** - 移除「簡報風格」選項，避免與模板選擇混淆
2. ✅ **模板映射修復** - 從 2/8 模板可用 → 8/8 模板全部可用 (100%)
3. ✅ **動態模板載入** - 實作完整的模板動態載入機制

#### 1. UI 簡化：移除「簡報風格」選項

**問題發現**:
- 前端同時存在「簡報風格」(style) 和「選擇模板」(template) 兩個選項
- 用戶對兩者功能產生混淆，不清楚差異

**解決方案**:

**A. 註解 HTML 選單** ([index.html:54-62](txt2pptx/frontend/index.html#L54-L62)):
```html
<!-- Commented out to avoid confusion with template selection -->
<!-- <div class="option-group">
    <label for="style">簡報風格</label>
    <select id="style">...</select>
</div> -->
```

**B. 設定預設風格** ([app.js:69](txt2pptx/frontend/app.js#L69)):
```javascript
style: 'professional', // Default style (style selector commented out to avoid confusion)
```

**C. 清理未使用參考** ([app.js:13](txt2pptx/frontend/app.js#L13)):
```javascript
// style: () => $('#style'), // Commented out - style selector removed from UI
```

**結果**: UI 更簡潔，用戶只需選擇模板，避免混淆。

#### 2. 模板映射問題診斷 🔍

**嚴重 Bug 發現**:

使用 `/sc:analyze --depth deep` 進行深度分析，發現：

| 模板 ID | 前端顯示 | 檔案存在 | 後端實作 | 實際使用 |
|---------|----------|----------|----------|----------|
| `College_Elegance` | ✅ 學院典雅 | ✅ 1.3 MB | ❌ 無 | ⚠️ fallback → code_drawn |
| `Data_Centric` | ✅ 數據導向 | ✅ 31 KB | ❌ 無 | ⚠️ fallback → code_drawn |
| `High_Contrast` | ✅ 高調對比 | ✅ 68 KB | ❌ 無 | ⚠️ fallback → code_drawn |
| `Minimalist_Corporate` | ✅ 極簡商務 | ✅ 927 KB | ❌ 無 | ⚠️ fallback → code_drawn |
| `Modernist` | ✅ 摩登現代 | ✅ 41 KB | ❌ 無 | ⚠️ fallback → code_drawn |
| `Startup_Edge` | ✅ 新創活力 | ✅ 42 KB | ❌ 無 | ⚠️ fallback → code_drawn |
| `Zen_Serenity` | ✅ 靜謐禪意 | ✅ 168 KB | ❌ 無 | ⚠️ fallback → code_drawn |
| `ocean_gradient` | ✅ 預設版面 | ✅ 26 KB | ✅ 有 | ✅ 正常使用模板 |

**結論**: **7/8 模板 (87.5%) 無法正常使用**

**根本原因**:

1. **硬編碼模板路徑** ([pptx_generator_template.py:27](txt2pptx/backend/pptx_generator_template.py#L27)):
   ```python
   TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "ocean_gradient.pptx"
   #                                                             ^^^^^^^^^^^^^^^^^^^
   #                                                             寫死的檔名
   ```

2. **GENERATORS 字典缺少條目** ([main.py:54-57](txt2pptx/backend/main.py#L54-L57)):
   ```python
   GENERATORS = {
       "code_drawn": generate_pptx_code_drawn,
       "ocean_gradient": generate_pptx_template,
       # ❌ 缺少其他 7 個模板的實作
   }
   ```

#### 3. 動態模板載入實作 (方案 A) 🔧

使用 `/sc:troubleshoot --fix` 實作完整修復。

**修改 1: pptx_generator_template.py**

**常數重構** (L27-29):
```python
# 修改前
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "ocean_gradient.pptx"

# 修改後
DEFAULT_TEMPLATE = "ocean_gradient.pptx"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
```

**函數簽名更新** (L272-291):
```python
# 修改前
def generate_pptx(outline: PresentationOutline) -> bytes:
    prs = Presentation(str(TEMPLATE_PATH))

# 修改後
def generate_pptx(outline: PresentationOutline, template_id: str = "ocean_gradient") -> bytes:
    """Generate PPTX bytes from a presentation outline using specified template.

    Args:
        outline: Presentation outline with slides data
        template_id: Template file name (without .pptx extension).
                    Defaults to "ocean_gradient".
                    Falls back to default template if specified template doesn't exist.

    Returns:
        PPTX file as bytes
    """
    # Resolve template path
    template_path = TEMPLATES_DIR / f"{template_id}.pptx"

    if not template_path.exists():
        logger.warning(f"Template {template_id} not found, using default template")
        template_path = TEMPLATES_DIR / DEFAULT_TEMPLATE

        if not template_path.exists():
            raise FileNotFoundError(f"Default template not found: {template_path}")

    logger.info(f"Loading template: {template_path.name}")
    prs = Presentation(str(template_path))
```

**修改 2: main.py**

**移除 GENERATORS 字典** ([main.py:53-58](txt2pptx/backend/main.py#L53-L58)):
```python
# 修改前
GENERATORS = {
    "code_drawn": generate_pptx_code_drawn,
    "ocean_gradient": generate_pptx_template,
}
generator = GENERATORS.get(request.template, generate_pptx_code_drawn)
pptx_bytes = generator(outline)

# 修改後
if request.template == "code_drawn":
    logger.info("Using code-drawn generator")
    pptx_bytes = generate_pptx_code_drawn(outline)
else:
    logger.info(f"Using template generator with template: {request.template}")
    pptx_bytes = generate_pptx_template(outline, template_id=request.template)
```

#### 4. 測試驗證 ✅

**單元測試** ([test/test_template_loading.py](test/test_template_loading.py)):

```text
🔍 檢查模板檔案...
  ✅ College_Elegance.pptx exists (1328120 bytes)
  ✅ Data_Centric.pptx exists (32120 bytes)
  ✅ High_Contrast.pptx exists (69876 bytes)
  ✅ Minimalist_Corporate.pptx exists (949412 bytes)
  ✅ Modernist.pptx exists (41602 bytes)
  ✅ ocean_gradient.pptx exists (27131 bytes)
  ✅ Startup_Edge.pptx exists (45212 bytes)
  ✅ Zen_Serenity.pptx exists (171785 bytes)

🔧 測試模板載入...
  ✅ College_Elegance: Success (1274596 bytes)
  ✅ Data_Centric: Success (30740 bytes)
  ✅ High_Contrast: Success (48293 bytes)
  ✅ Minimalist_Corporate: Success (940217 bytes)
  ✅ Modernist: Success (40243 bytes)
  ✅ ocean_gradient: Success (28944 bytes)
  ✅ Startup_Edge: Success (43411 bytes)
  ✅ Zen_Serenity: Success (170742 bytes)

🔄 測試 fallback 行為...
  ✅ Fallback works (28944 bytes)

成功載入: 8/8 個模板
Fallback 測試: ✅ 通過
🎉 所有測試通過！
```

**整合測試 (HTTP API)**:

```text
[1/8] 學院典雅... ✅
[2/8] 數據導向... ✅
[3/8] 高調對比... ✅
[4/8] 極簡商務... ✅
[5/8] 摩登現代... ✅
[6/8] 預設版面... ✅
[7/8] 新創活力... ✅
[8/8] 靜謐禪意... ✅

成功率: 100% (8/8)
```

**伺服器日誌驗證**:
```log
INFO:backend.main:Using template generator with template: College_Elegance
INFO:backend.pptx_generator_template:Loading template: College_Elegance.pptx
```

#### 技術亮點 💡

1. **動態模板解析**: 根據 `template_id` 參數動態載入對應的 .pptx 檔案
2. **優雅降級**: 找不到模板時自動使用預設模板，不會導致錯誤
3. **日誌追蹤**: 清楚記錄每次使用的模板，方便除錯
4. **向後兼容**: 保持原有 API 介面不變，只需新增參數
5. **完整測試**: 涵蓋單元測試和整合測試，確保修復穩定性

#### 影響範圍評估

| 影響類別 | 嚴重度 | 修復前 | 修復後 |
|---------|--------|--------|--------|
| **模板可用性** | 🔴 CRITICAL | 2/8 (25%) | 8/8 (100%) ✅ |
| **用戶體驗** | 🔴 HIGH | 選擇未套用 | 正確套用 ✅ |
| **功能正確性** | 🔴 HIGH | 87.5% 失效 | 100% 正常 ✅ |
| **UI 清晰度** | 🟡 MEDIUM | 選項混淆 | 簡潔明確 ✅ |

#### 性能指標

- **模板載入成功率**: 100% (8/8)
- **Fallback 機制**: 正常運作
- **API 整合測試**: 100% 通過 (8/8)
- **日誌可追溯性**: 完整記錄
