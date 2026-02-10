"""TXT2PPTX FastAPI Application."""
import os
import uuid
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .models import GenerateRequest, GenerateResponse
from .llm_service import generate_outline
from .pptx_generator import generate_pptx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TXT2PPTX", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).parent.parent
GENERATED_DIR = BASE_DIR / "generated"
FRONTEND_DIR = BASE_DIR / "frontend"
GENERATED_DIR.mkdir(exist_ok=True)

# Serve frontend static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index_file = FRONTEND_DIR / "index.html"
    return index_file.read_text(encoding="utf-8")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_presentation(request: GenerateRequest):
    """Generate a PPTX presentation from text input."""
    try:
        # Step 1: Generate outline
        logger.info(f"Generating outline for {len(request.text)} chars, {request.num_slides} slides")
        outline = await generate_outline(request)
        logger.info(f"Outline generated: {outline.title}, {len(outline.slides)} slides")

        # Step 2: Generate PPTX
        pptx_bytes = generate_pptx(outline)

        # Step 3: Save file
        filename = f"{uuid.uuid4().hex[:8]}.pptx"
        filepath = GENERATED_DIR / filename
        filepath.write_bytes(pptx_bytes)
        logger.info(f"PPTX saved: {filepath} ({len(pptx_bytes)} bytes)")

        return GenerateResponse(
            success=True,
            filename=filename,
            message="簡報生成成功",
            outline=outline
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失敗: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download generated PPTX file."""
    filepath = GENERATED_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="檔案不存在")
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
