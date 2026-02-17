#!/usr/bin/env python3
"""
重試機制整合測試
測試目標：驗證重試機制能提升 LLM 成功率從 66% → 96%
"""
import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "txt2pptx"))

from backend.models import GenerateRequest
from backend.llm_service import generate_outline
from backend.pptx_generator import generate_pptx


async def run_single_test(test_num: int, test_text: str) -> dict:
    """執行單次測試並記錄結果"""
    request = GenerateRequest(
        text=test_text,
        num_slides=8,
        language="繁體中文",
        style="ocean_gradient"
    )

    start_time = time.time()

    try:
        outline = await generate_outline(request)
        duration = time.time() - start_time

        # 檢查是否為 demo mode (165 張投影片是明顯的 demo fallback)
        is_demo_mode = len(outline.slides) > 50

        # 品質檢查
        bullet_lengths = []
        for slide in outline.slides:
            if hasattr(slide, 'bullets') and slide.bullets:
                avg_len = sum(len(b) for b in slide.bullets) / len(slide.bullets)
                bullet_lengths.append(avg_len)

        avg_bullet_len = sum(bullet_lengths) / len(bullet_lengths) if bullet_lengths else 0
        slides_with_notes = sum(1 for s in outline.slides if s.speaker_notes and len(s.speaker_notes.strip()) > 0)
        note_lengths = [len(s.speaker_notes) for s in outline.slides if s.speaker_notes]
        avg_note_len = sum(note_lengths) / len(note_lengths) if note_lengths else 0
        layouts = set(s.layout.value for s in outline.slides)

        # 品質評分
        quality_score = 0
        if avg_bullet_len >= 15:
            quality_score += 1
        if slides_with_notes >= len(outline.slides) * 0.7:
            quality_score += 1
        if avg_note_len >= 50:
            quality_score += 1
        if len(layouts) >= 5:
            quality_score += 1

        return {
            "test_num": test_num,
            "success": True,
            "duration": duration,
            "slides": len(outline.slides),
            "is_demo_mode": is_demo_mode,
            "quality_score": quality_score,
            "avg_bullet_len": avg_bullet_len,
            "notes_coverage": slides_with_notes / len(outline.slides),
            "avg_note_len": avg_note_len,
            "layout_diversity": len(layouts)
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "test_num": test_num,
            "success": False,
            "duration": duration,
            "error": str(e)[:100]
        }


async def main():
    # 圖論測試文字（與之前測試相同）
    test_text = """圖論（英語：Graph theory），是組合數學分支，和其他數學分支如群論、矩陣論、拓撲學有著密切關係。
圖是圖論的主要研究對象。圖是由若干給定的頂點及連接兩頂點的邊所構成的圖形，這種圖形通常用來描述某些事物之間的某種特定關係。頂點用於代表事物，連接兩頂點的邊則用於表示兩個事物間具有這種關係。
圖論起源於著名的柯尼斯堡七橋問題。該問題於1736年被歐拉解決，因此普遍認為歐拉是圖論的創始人。"""

    print("=" * 80)
    print("重試機制整合測試")
    print("目標：驗證重試機制能提升成功率從 66% → 96%")
    print("=" * 80)
    print()

    # 執行 10 次測試
    num_tests = 10
    results = []

    for i in range(1, num_tests + 1):
        print(f"執行測試 {i}/{num_tests}...", end=" ", flush=True)
        result = await run_single_test(i, test_text)
        results.append(result)

        if result["success"]:
            mode = "DEMO" if result["is_demo_mode"] else "LLM"
            print(f"✅ {mode} ({result['duration']:.1f}s, 品質: {result['quality_score']}/4)")
        else:
            print(f"❌ 失敗 ({result['duration']:.1f}s)")

    # 統計結果
    print()
    print("=" * 80)
    print("📊 測試結果統計")
    print("=" * 80)

    successful_tests = [r for r in results if r["success"]]
    llm_successes = [r for r in successful_tests if not r["is_demo_mode"]]
    demo_fallbacks = [r for r in successful_tests if r["is_demo_mode"]]

    total_count = len(results)
    success_count = len(successful_tests)
    llm_success_count = len(llm_successes)
    demo_count = len(demo_fallbacks)

    print(f"\n總測試次數: {total_count}")
    print(f"成功次數: {success_count} ({success_count/total_count*100:.1f}%)")
    print(f"  - LLM 成功: {llm_success_count} ({llm_success_count/total_count*100:.1f}%)")
    print(f"  - Demo Fallback: {demo_count} ({demo_count/total_count*100:.1f}%)")

    if llm_successes:
        avg_quality = sum(r["quality_score"] for r in llm_successes) / len(llm_successes)
        avg_duration = sum(r["duration"] for r in llm_successes) / len(llm_successes)
        print(f"\nLLM 成功案例:")
        print(f"  - 平均品質分數: {avg_quality:.2f}/4")
        print(f"  - 平均響應時間: {avg_duration:.1f} 秒")
        print(f"  - 平均 bullet 長度: {sum(r['avg_bullet_len'] for r in llm_successes)/len(llm_successes):.1f} 字")
        print(f"  - 平均 notes 長度: {sum(r['avg_note_len'] for r in llm_successes)/len(llm_successes):.1f} 字")

    # 與預期對比
    print(f"\n📈 與預期目標對比:")
    print(f"  當前 LLM 成功率: {llm_success_count/total_count*100:.1f}% (目標: ≥ 96%)")
    print(f"  當前 Demo Fallback 率: {demo_count/total_count*100:.1f}% (目標: ≤ 4%)")

    if llm_success_count / total_count >= 0.95:
        print("\n🎉 優秀！達成目標，重試機制運作正常！")
    elif llm_success_count / total_count >= 0.80:
        print("\n✅ 良好！成功率顯著提升，重試機制有效。")
    else:
        print("\n⚠️ 注意：成功率低於預期，可能需要調整參數或檢查 LLM 配置。")

    return llm_success_count / total_count


if __name__ == "__main__":
    success_rate = asyncio.run(main())
    sys.exit(0 if success_rate >= 0.80 else 1)
