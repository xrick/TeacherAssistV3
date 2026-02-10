# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TXT2PPTX: A web application that converts plain text into structured PowerPoint presentations using LLM-generated outlines. The UI is in Traditional Chinese (zh-TW).

## Commands

```bash
# Activate virtual environment
source pptxenv/bin/activate

# Start development server (from repo root)
cd txt2pptx && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the start script
cd txt2pptx && bash start.sh

# Health check
curl http://localhost:8000/api/health
```

## Environment Variables

- `OLLAMA_URL` — Ollama server address (default: `http://localhost:11434`)
- `OLLAMA_MODEL` — Model name (default: `gpt-oss:2b`). The local machine has `gpt-oss:20b` available.

## Architecture

The app lives entirely in `txt2pptx/` with a 3-stage pipeline:

```
User text → [LLM Outline Generation] → [PPTX Builder] → .pptx file
                 llm_service.py          pptx_generator.py
```

### Backend (`txt2pptx/backend/`)

- **main.py** — FastAPI app. Routes: `POST /api/generate`, `GET /api/download/{filename}`, `GET /api/health`. Serves frontend from `/`.
- **models.py** — Pydantic models. `GenerateRequest` (input), `PresentationOutline` / `SlideData` (intermediate), `GenerateResponse` (output). `SlideLayout` enum defines 9 layout types.
- **llm_service.py** — Calls Ollama's OpenAI-compatible API (`/v1/chat/completions`) via `httpx`. `generate_outline()` is the entry point: tries LLM first, falls back to `generate_outline_demo()` (heuristic-based) if Ollama is unavailable. Timeout is 600s for CPU-only inference.
- **pptx_generator.py** — Builds PPTX using `python-pptx`. A `BUILDERS` dict maps each `SlideLayout` enum to a builder function (`_build_title_slide`, `_build_bullets_slide`, etc.). `Theme` class holds color/font config.

### Frontend (`txt2pptx/frontend/`)

Vanilla HTML/CSS/JS (no build step). `app.js` calls `/api/generate`, shows progress simulation, renders outline preview, and provides download link.

### Key Data Flow

1. Frontend POSTs `{text, num_slides, language, style}` to `/api/generate`
2. `llm_service.generate_outline()` sends text + system prompt to Ollama, parses JSON response into `PresentationOutline`
3. `pptx_generator.generate_pptx()` iterates `outline.slides`, dispatches each to a layout-specific builder
4. PPTX bytes saved to `txt2pptx/generated/`, filename returned to frontend

### LLM Integration

Uses Ollama's OpenAI-compatible endpoint (not the native `/api/chat`). The system prompt in `SYSTEM_PROMPT` instructs the LLM to output strict JSON matching the `PresentationOutline` schema. Response parsing strips markdown fences before `json.loads()`.

## Tech Stack

- Python 3.11, FastAPI, Uvicorn, httpx, python-pptx, Pydantic v2
- Virtual environment at `pptxenv/` (not in git ideally)
- No test framework configured yet
- No linter/formatter configured yet
