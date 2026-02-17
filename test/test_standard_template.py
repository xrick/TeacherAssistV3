#!/usr/bin/env python3
"""整合測試：使用 standard_template.pptx 模板生成簡報"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "txt2pptx"))

from backend.models import GenerateRequest
from backend.llm_service import generate_outline
from backend.pptx_generator_template import generate_pptx
import asyncio

async def main():
    # Read test content
    test_file = Path(__file__).parent / "Discrete_mathematics.txt"
    test_text = test_file.read_text(encoding="utf-8")

    print("=" * 80)
    print("整合測試：Discrete Mathematics (離散數學)")
    print("=" * 80)
    print(f"\n📄 測試文字內容（{len(test_text)} 字元）:")
    print(test_text[:200] + "..." if len(test_text) > 200 else test_text)
    print()

    # Create request
    request = GenerateRequest(
        text=test_text,
        num_slides=8,
        language="zh-TW",
        style="professional",
        template="standard_template"  # 指定使用 standard_template
    )

    print("🔄 Step 1: 生成 Outline (呼叫 LLM)...")
    print("-" * 80)

    try:
        outline = await generate_outline(request)
        print(f"✅ Outline 生成成功")
        print(f"   標題: {outline.title}")
        print(f"   副標題: {outline.subtitle}")
        print(f"   投影片數量: {len(outline.slides)}")
        print()

        # Analyze outline content richness
        print("📊 內容豐富度分析:")
        print("-" * 80)

        total_bullets = 0
        total_speaker_notes_length = 0
        layouts_used = {}

        for i, slide in enumerate(outline.slides, 1):
            print(f"\n投影片 {i}: {slide.layout}")
            print(f"  標題: {slide.title}")

            if slide.bullets:
                total_bullets += len(slide.bullets)
                for j, bullet in enumerate(slide.bullets[:3], 1):  # Show first 3
                    bullet_len = len(bullet)
                    print(f"  - Bullet {j} ({bullet_len} 字): {bullet[:50]}{'...' if len(bullet) > 50 else ''}")

            if slide.speaker_notes:
                notes_len = len(slide.speaker_notes)
                total_speaker_notes_length += notes_len
                print(f"  📝 Speaker notes ({notes_len} 字): {slide.speaker_notes[:80]}{'...' if len(slide.speaker_notes) > 80 else ''}")

            if slide.stats:
                print(f"  📊 Stats: {slide.stats}")

            # Count layout usage
            layout_name = slide.layout.value if hasattr(slide.layout, 'value') else str(slide.layout)
            layouts_used[layout_name] = layouts_used.get(layout_name, 0) + 1

        print("\n" + "=" * 80)
        print("📈 統計摘要:")
        print("=" * 80)
        print(f"總投影片數: {len(outline.slides)}")
        print(f"總 bullet 數: {total_bullets}")
        print(f"平均每張 bullet: {total_bullets / len(outline.slides):.1f}")
        print(f"Speaker notes 總長度: {total_speaker_notes_length} 字")
        print(f"平均每張 speaker notes: {total_speaker_notes_length / len(outline.slides):.1f} 字")
        print(f"\nLayout 使用分佈:")
        for layout, count in sorted(layouts_used.items()):
            print(f"  {layout}: {count} 次")

        # Check if content is rich (based on new SYSTEM_PROMPT)
        print("\n" + "=" * 80)
        print("🎯 新 SYSTEM_PROMPT 效果檢查:")
        print("=" * 80)

        checks = []

        # Check 1: Bullet length (should be 15-20 chars for complete sentences)
        avg_bullet_length = sum(len(b) for s in outline.slides if s.bullets for b in s.bullets) / total_bullets if total_bullets > 0 else 0
        check1 = avg_bullet_length >= 15
        checks.append(("Bullet 長度 >= 15 字", check1, f"{avg_bullet_length:.1f} 字"))

        # Check 2: Speaker notes presence (should be 50-100 chars)
        slides_with_notes = sum(1 for s in outline.slides if s.speaker_notes)
        check2 = slides_with_notes >= len(outline.slides) * 0.7  # At least 70% have notes
        checks.append(("Speaker notes 覆蓋率 >= 70%", check2, f"{slides_with_notes}/{len(outline.slides)}"))

        # Check 3: Average speaker notes length
        avg_notes_length = total_speaker_notes_length / slides_with_notes if slides_with_notes > 0 else 0
        check3 = avg_notes_length >= 50
        checks.append(("Speaker notes 平均長度 >= 50 字", check3, f"{avg_notes_length:.1f} 字"))

        # Check 4: Layout diversity (at least 5 different layouts)
        check4 = len(layouts_used) >= 5
        checks.append(("Layout 多樣性 >= 5 種", check4, f"{len(layouts_used)} 種"))

        for desc, passed, value in checks:
            status = "✅" if passed else "❌"
            print(f"{status} {desc}: {value}")

        passed_checks = sum(1 for _, p, _ in checks if p)
        print(f"\n通過檢查: {passed_checks}/{len(checks)}")

        if passed_checks == len(checks):
            print("🎉 所有檢查通過！新 SYSTEM_PROMPT 正在生效。")
        elif passed_checks >= len(checks) * 0.5:
            print("⚠️ 部分檢查未通過，SYSTEM_PROMPT 可能部分生效。")
        else:
            print("🚨 大部分檢查未通過，可能正在使用 demo fallback 或 SYSTEM_PROMPT 未生效。")

        # Step 2: Generate PPTX using code-drawn approach (template support not yet implemented)
        print("\n" + "=" * 80)
        print("🔄 Step 2: 生成 PPTX (使用 code-drawn 方式)")
        print("=" * 80)

        pptx_bytes = generate_pptx(outline)

        output_file = Path(__file__).parent / "output_standard_template.pptx"
        output_file.write_bytes(pptx_bytes)

        print(f"✅ PPTX 生成成功")
        print(f"   檔案大小: {len(pptx_bytes):,} bytes")
        print(f"   輸出路徑: {output_file}")

        print("\n" + "=" * 80)
        print("✅ 測試完成")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
