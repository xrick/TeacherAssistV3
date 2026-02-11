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
