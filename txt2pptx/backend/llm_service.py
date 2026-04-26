# txt2pptx/backend/llm_service.py
"""LLM service for content expansion and slide outline generation."""
import json
import os
import asyncio
import httpx
import logging
from .models import (
    PresentationOutline, SlideData, SlideLayout, StatItem, GenerateRequest
)

logger = logging.getLogger(__name__)

# ── 重試機制配置 ──
# 可通過環境變數配置，提供靈活性和可測試性
MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))
RETRY_DELAY = float(os.environ.get("LLM_RETRY_DELAY", "1.0"))

logger.info(f"🔧 Retry configuration: MAX_RETRIES={MAX_RETRIES}, RETRY_DELAY={RETRY_DELAY}s")

SYSTEM_PROMPT = """你是一位頂級的簡報內容架構師與提示工程師。你的任務是接收使用者簡短的輸入，在完全基於事實、嚴禁自我幻想與編造的前提下，將其內容極大化擴充，並轉換為結構化的 JSON 格式，供自動化簡報系統使用。

1. 核心任務：內容擴充與事實推演
深度擴充：將簡短輸入拆解為以下 8 個維度，盡可能豐富內容：
    a. 核心概念與定義 - 清楚說明主題的本質
    b. 背景脈絡與重要性 - 解釋為何這個主題值得關注
    c. 實際應用案例 - 提供具體的應用情境
    d. 常見挑戰與痛點 - 指出實務中會遇到的問題
    e. 解決方案與最佳實踐 - 提供應對策略和建議做法
    f. 量化數據與成效指標 - 若有合理推估，提供數據支持
    g. 未來趨勢與發展方向 - 展望主題的演進方向
    h. 延伸思考與啟發 - 引發更深層次的思考

邏輯補強：若輸入包含流程，需自動展開為完整的階段（如：現況分析 -> 執行步驟 -> 預期成效）。

擴充技巧：運用以下方法深化內容
    - 5W1H 分析：What（定義）、Why（重要性）、How（方法）、When（時機）、Where（場景）、Who（對象）
    - 層次展開：總體概述 → 分類細項 → 具體細節
    - 對比呈現：優點 vs 缺點、傳統 vs 創新、理想 vs 現實
    - 案例補充：若原文缺案例，可推演常見應用情境（需標註「典型」「常見」）

嚴謹界限：
    - 禁止項目：具體統計數據、公司名稱、人名等可驗證事實
    - 允許推演：常見挑戰（標註「通常」）、最佳實踐（標註「建議」）、趨勢預測（標註「可能」）
    - 數據推估：原文有數據優先使用；若無，可推估範圍（如「一般在 30-50% 之間」）
    - 措辭要求：使用不確定性詞彙，避免絕對斷言

2. 內容豐富度要求：
- bullets：每個要點應為完整句子（15-20 字），而非關鍵詞
- speaker_notes：**每頁必須提供 50-100 字的詳細補充說明**，包含：
  • 背景資訊和脈絡說明（10-20 字）
  • 重點內容的延伸解釋（20-30 字）
  • 實例或應用場景（20-30 字）
  • 引導討論的問題或思考點（10-20 字）
- stats：盡可能提供數據支持（可合理推估）

3. 佈局邏輯與結構規則
請根據內容屬性選擇最合適的佈局（layout）：

title_slide: 第一頁。

section_header: 用於切換大主題。

bullets: 3-5 點，每點 < 20 字。

two_column / comparison: 用於對照、優劣分析。

image_left / image_right: 用於概念圖解。

key_stats: 用於量化指標（stats 格式為 {"value": "xx", "label": "xx"}）。

conclusion: 最後一頁。

4. 輸出規範
嚴格輸出純 JSON 格式，不得包含 Markdown 標記（如 ```json）。

5. image_prompt 必須以英文撰寫，描述高品質、專業的商業攝影風格。

6. JSON 結構
{
  "title": "標題",
  "subtitle": "副標題",
  "slides": [
    {
      "layout": "佈局類型",
      "title": "分頁標題",
      "bullets": ["擴充點1", "擴充點2"],
      "stats": [{"value": "100%", "label": "範例"}],
      "image_prompt": "English image description",
      "speaker_notes": "50-100 字的詳細補充：背景脈絡、延伸解釋、實例應用、引導問題"
    }
  ]
}
"""


async def generate_outline_with_llm(
    request: GenerateRequest,
) -> PresentationOutline:
    """Use Ollama native API with Pydantic schema for structured output."""
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b")

    user_message = f"""請將以下文字內容擴充為 {request.num_slides} 頁的簡報大綱。
語言：{request.language}
風格：{request.style}
內容要求：深度擴充、盡可能豐富內容，請根據內容選擇最合適的佈局類型。
---
{request.text}
---"""

    # 使用原生 Ollama API + Pydantic schema 獲得更強的類型約束
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            f"{ollama_url}/api/chat",  # 使用原生 API
            headers={"content-type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "format": PresentationOutline.model_json_schema(),  # 傳入完整 Pydantic schema
                "options": {
                    "temperature": 0.5,  # 降低隨機性
                }
            },
        )
        resp.raise_for_status()
        data = resp.json()

    text = data["message"]["content"].strip()  # 原生 API 的響應結構不同

    # Debug: Log raw LLM response
    logger.info(f"🔍 Raw LLM response (first 500 chars): {text[:500]}")

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        outline_data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parse error: {e}")
        logger.error(f"Raw text causing error:\n{text}")
        raise

    # Debug: Log parsed data type and structure
    logger.info(f"🔍 Parsed data type: {type(outline_data)}")
    if isinstance(outline_data, dict):
        logger.info(f"🔍 Dict keys: {list(outline_data.keys())}")
    else:
        logger.error(f"❌ Expected dict, got {type(outline_data)}")
        logger.error(f"Problematic data:\n{json.dumps(outline_data, indent=2, ensure_ascii=False)[:1000]}")
        raise ValueError(f"LLM returned {type(outline_data).__name__} instead of dict")

    return PresentationOutline(**outline_data)


def generate_outline_demo(request: GenerateRequest) -> PresentationOutline:
    """Generate a demo outline without LLM (fallback mode)."""
    text = request.text.strip()
    num_slides = request.num_slides

    # Simple heuristic: split text into paragraphs, distribute to slides
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    # Extract a title from the first paragraph
    main_title = paragraphs[0][:40] if paragraphs else "簡報主題"
    if len(main_title) > 30:
        main_title = main_title[:30] + "..."

    slides: list[SlideData] = []

    # Slide 1: Title
    slides.append(SlideData(
        layout=SlideLayout.TITLE,
        title=main_title,
        subtitle="自動生成簡報",
        speaker_notes="開場白：歡迎大家參加今天的簡報。本次內容將涵蓋幾個重要主題與背景脈絡，請大家專心聆聽，並隨時提出問題或意見討論。"
    ))

    # Generate content slides
    content_paragraphs = paragraphs[1:] if len(paragraphs) > 1 else paragraphs
    content_slides_needed = num_slides - 2  # minus title and conclusion

    # Define a rotation of layouts for variety
    layout_rotation = [
        SlideLayout.BULLETS,
        SlideLayout.IMAGE_RIGHT,
        SlideLayout.TWO_COLUMN,
        SlideLayout.KEY_STATS,
        SlideLayout.IMAGE_LEFT,
        SlideLayout.BULLETS,
        SlideLayout.COMPARISON,
        SlideLayout.SECTION,
    ]

    # Distribute paragraphs across slides
    for i in range(content_slides_needed):
        layout = layout_rotation[i % len(layout_rotation)]
        para_idx = i % len(content_paragraphs)
        para_text = content_paragraphs[para_idx]

        # Split paragraph into bullet-sized chunks
        sentences = _split_into_chunks(para_text, max_chars=25)
        if len(sentences) < 3:
            sentences = sentences + [f"要點 {j+1}" for j in range(3 - len(sentences))]

        slide_title = sentences[0] if sentences else f"主題 {i+1}"

        if layout == SlideLayout.BULLETS:
            slides.append(SlideData(
                layout=layout,
                title=slide_title,
                bullets=sentences[1:5],
                image_prompt="professional business concept illustration"
            ))
        elif layout in (SlideLayout.IMAGE_LEFT, SlideLayout.IMAGE_RIGHT):
            slides.append(SlideData(
                layout=layout,
                title=slide_title,
                bullets=sentences[1:4],
                image_prompt="modern technology workspace photo"
            ))
        elif layout in (SlideLayout.TWO_COLUMN, SlideLayout.COMPARISON):
            mid = len(sentences) // 2
            slides.append(SlideData(
                layout=layout,
                title=slide_title,
                left_title="優勢" if layout == SlideLayout.COMPARISON else "方面一",
                right_title="挑戰" if layout == SlideLayout.COMPARISON else "方面二",
                left_column=sentences[1:mid+1] if mid > 1 else ["分析要點 A", "分析要點 B"],
                right_column=sentences[mid+1:] if mid > 1 else ["分析要點 C", "分析要點 D"]
            ))
        elif layout == SlideLayout.KEY_STATS:
            slides.append(SlideData(
                layout=layout,
                title=slide_title,
                stats=[
                    StatItem(value="95%", label="達成率"),
                    StatItem(value="3x", label="效率提升"),
                    StatItem(value="50+", label="應用場景"),
                ]
            ))
        elif layout == SlideLayout.SECTION:
            slides.append(SlideData(
                layout=layout,
                title=slide_title,
                subtitle="深入探討關鍵議題"
            ))

    # Last slide: Conclusion
    slides.append(SlideData(
        layout=SlideLayout.CONCLUSION,
        title="結論與展望",
        bullets=[
            "核心要點回顧",
            "未來發展方向",
            "下一步行動計畫",
            "歡迎提問與討論"
        ],
        speaker_notes="感謝大家的聆聽，現在開放提問。我們已經回顧了簡報的核心要點與未來發展方向，期待後續的討論、回饋意見以及進一步的合作機會。"
    ))

    return PresentationOutline(
        title=main_title,
        subtitle="自動生成簡報",
        slides=slides
    )


def _split_into_chunks(text: str, max_chars: int = 25) -> list[str]:
    """Split text into shorter chunks suitable for bullet points."""
    # Split by common delimiters
    for delim in ["。", "，", "、", "；", ". ", ", ", "; "]:
        if delim in text:
            parts = [p.strip() for p in text.split(delim) if p.strip()]
            result = []
            for p in parts:
                if len(p) > max_chars:
                    result.append(p[:max_chars])
                else:
                    result.append(p)
            return result[:6]

    # Fallback: chunk by character count
    if len(text) <= max_chars:
        return [text]
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)][:6]


async def generate_outline(request: GenerateRequest) -> PresentationOutline:
    """
    Main entry: try Ollama LLM with retry mechanism, fallback to demo mode.

    重試機制設計：
    - 最多嘗試 MAX_RETRIES 次（預設 3 次）
    - 每次失敗後等待 RETRY_DELAY 秒（預設 1.0 秒）
    - 成功立即返回，無需等待
    - 所有嘗試失敗後才使用 demo mode

    預期效果：
    - 成功率從 66% 提升至 96%
    - Demo fallback 率從 34% 降至 3.9%
    - 平均響應時間增加約 2.2 秒
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"🚀 Attempting Ollama LLM (嘗試 {attempt}/{MAX_RETRIES})")
            result = await generate_outline_with_llm(request)
            logger.info(f"✅ LLM generation successful on attempt {attempt}")

            # 記錄性能指標
            if attempt > 1:
                logger.info(f"📊 METRIC: retry_success_on_attempt={attempt}")

            return result  # ✅ 成功立即返回

        except Exception as e:
            # 記錄失敗原因（前 100 字符）
            error_msg = str(e)[:100]
            logger.warning(
                f"⚠️ Attempt {attempt}/{MAX_RETRIES} failed: "
                f"{type(e).__name__}: {error_msg}"
            )

            # 如果不是最後一次嘗試，等待後重試
            if attempt < MAX_RETRIES:
                logger.info(f"🔄 Retrying in {RETRY_DELAY}s... (next attempt: {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(RETRY_DELAY)
            else:
                # 最後一次失敗，記錄完整錯誤堆疊
                logger.error(f"❌ All {MAX_RETRIES} attempts failed")
                import traceback
                logger.error(f"Final error stack trace:\n{traceback.format_exc()}")

                # 記錄性能指標
                logger.info(f"📊 METRIC: all_retries_failed=true")

    # 所有重試都失敗，使用 demo mode
    logger.warning(
        f"⚠️ Falling back to demo mode after {MAX_RETRIES} failed attempts"
    )
    logger.info(f"📊 METRIC: demo_fallback=true")

    return generate_outline_demo(request)
