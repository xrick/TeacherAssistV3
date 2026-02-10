"""LLM service for content expansion and slide outline generation."""
import json
import httpx
import logging
from .models import (
    PresentationOutline, SlideData, SlideLayout, StatItem, GenerateRequest
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位專業的簡報設計師。你的任務是將使用者提供的文字內容，擴充並組織成結構化的簡報大綱。

## 輸出格式
請嚴格輸出以下 JSON 格式（不要包含 markdown 標記）：

{
  "title": "簡報標題",
  "subtitle": "副標題（可選）",
  "slides": [
    {
      "layout": "布局類型",
      "title": "投影片標題",
      "subtitle": "副標題（可選）",
      "bullets": ["要點1", "要點2", "要點3"],
      "left_column": ["左欄要點"],
      "right_column": ["右欄要點"],
      "left_title": "左欄標題",
      "right_title": "右欄標題",
      "stats": [{"value": "95%", "label": "準確率"}],
      "image_prompt": "描述適合此頁的圖片",
      "speaker_notes": "講者備註"
    }
  ]
}

## 可用布局類型
- title_slide: 封面頁（必須是第一頁），只需 title + subtitle
- section_header: 章節分隔頁，只需 title + subtitle
- bullets: 標題 + 條列式要點（3-5個 bullets）
- two_column: 雙欄佈局（left_title + left_column + right_title + right_column）
- image_left: 左圖右文（title + bullets + image_prompt）
- image_right: 左文右圖（title + bullets + image_prompt）
- key_stats: 關鍵數據頁（title + stats，2-4個統計數字）
- comparison: 對比頁（left_title + left_column + right_title + right_column）
- conclusion: 結語頁（title + bullets），必須是最後一頁

## 規則
1. 第一頁必須是 title_slide，最後一頁必須是 conclusion
2. 每頁 bullets 控制在 3-5 點，每點不超過 20 個字
3. 布局要多樣化，不要連續使用同一種布局
4. stats 的 value 要簡短有力（數字+單位）
5. image_prompt 用英文撰寫，描述適合此頁的商業圖片風格
6. 內容要專業、結構清晰、有邏輯遞進關係
7. 使用者指定多少頁就產生多少頁
"""


async def generate_outline_with_llm(
    request: GenerateRequest,
    api_key: str
) -> PresentationOutline:
    """Use Anthropic API to generate presentation outline."""
    user_message = f"""請將以下文字內容擴充為 {request.num_slides} 頁的簡報大綱。
語言：{request.language}
風格：{request.style}

---
{request.text}
---

請直接輸出 JSON，不要加 ```json 標記。"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()

    text = data["content"][0]["text"].strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    outline_data = json.loads(text)
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
        speaker_notes="開場白：歡迎大家參加今天的簡報。"
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
        speaker_notes="感謝大家的聆聽，現在開放提問。"
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
    """Main entry: try LLM first, fallback to demo mode."""
    api_key = request.api_key

    if api_key:
        try:
            logger.info("Using Anthropic API for outline generation")
            return await generate_outline_with_llm(request, api_key)
        except Exception as e:
            logger.warning(f"LLM generation failed: {e}, falling back to demo mode")

    logger.info("Using demo mode for outline generation")
    return generate_outline_demo(request)
