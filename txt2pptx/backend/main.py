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
from .pptx_generator import generate_pptx as generate_pptx_code_drawn
from .pptx_generator_template import generate_pptx as generate_pptx_template

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

        # Step 2: Generate PPTX (根據模板選擇)
        GENERATORS = {
            "code_drawn": generate_pptx_code_drawn,
            "ocean_gradient": generate_pptx_template,
        }
        generator = GENERATORS.get(request.template, generate_pptx_code_drawn)
        pptx_bytes = generator(outline)

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


@app.get("/api/templates")
async def list_templates():
    """列出所有可用的簡報模板。"""
    # 模板中英文名稱對照表
    TEMPLATE_NAMES = {
        "College_Elegance": "學院典雅",
        "Data_Centric": "數據導向",
        "High_Contrast": "高調對比",
        "Minimalist_Corporate": "極簡商務",
        "Modernist": "摩登現代",
        "ocean_gradient": "預設版面",
        "Startup_Edge": "新創活力",
        "Zen_Serenity": "靜謐禪意",
    }

    templates = [
        {
            "id": "code_drawn",
            "name": "經典繪製",
            "description": "完全程式化繪製，靈活性高",
            "available": True,
            "is_template": False
        }
    ]

    # 檢查 templates 目錄下的所有 .pptx 檔案
    templates_dir = BASE_DIR / "templates"
    if templates_dir.exists():
        for template_file in templates_dir.glob("*.pptx"):
            template_id = template_file.stem
            try:
                # 嘗試載入模板驗證可用性
                from pptx import Presentation
                test_prs = Presentation(str(template_file))
                available = True
            except Exception as e:
                logger.warning(f"模板 {template_file.name} 不可用: {e}")
                available = False

            # 使用中文名稱對照表，若無對應則使用原始格式化名稱
            chinese_name = TEMPLATE_NAMES.get(template_id, template_id.replace("_", " ").title())

            templates.append({
                "id": template_id,
                "name": chinese_name,
                "description": f"使用 {chinese_name} 模板",
                "available": available,
                "is_template": True
            })

    return {"templates": templates}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
