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
