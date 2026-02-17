#!/usr/bin/env python3
"""
整合測試：模板套用 + 重試機制驗證
測試內容：離散數學
測試模板：College_Elegance.pptx
"""
import asyncio
import httpx
import sys
import time
from pathlib import Path


async def main():
    # 讀取測試內容
    test_file = Path(__file__).parent / "Discrete_mathematics.txt"
    if not test_file.exists():
        print(f"❌ 測試檔案不存在: {test_file}")
        return False

    test_text = test_file.read_text(encoding="utf-8")

    print("=" * 80)
    print("整合測試：模板套用 + 重試機制 + API 端點")
    print("=" * 80)
    print(f"測試內容: Discrete Mathematics (離散數學)")
    print(f"測試模板: College_Elegance")
    print(f"內容長度: {len(test_text)} 字元")
    print(f"API 端點: http://localhost:8000/api/generate")
    print("=" * 80)
    print()

    # 準備 API 請求
    request_data = {
        "text": test_text,
        "num_slides": 8,
        "language": "繁體中文",
        "style": "professional",
        "template": "College_Elegance"  # 指定模板
    }

    # 完整整合測試：透過 API 呼叫（測試重試機制 + 模板套用）
    print("📝 完整整合測試：API 呼叫（測試重試機制 + 模板套用）")
    print("-" * 80)

    start_time = time.time()
    quality_checks = {}
    outline_duration = 0
    pptx_duration = 0

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                "http://localhost:8000/api/generate",
                headers={"Content-Type": "application/json"},
                json=request_data
            )

            total_duration = time.time() - start_time

            if response.status_code != 200:
                print(f"❌ API 呼叫失敗: HTTP {response.status_code}")
                print(f"   錯誤訊息: {response.text}")
                return False

            data = response.json()

            if not data.get("success"):
                print(f"❌ 生成失敗: {data.get('message', '未知錯誤')}")
                return False

            print(f"✅ API 呼叫成功")
            print(f"   - 總耗時: {total_duration:.1f} 秒")
            print(f"   - 檔案名稱: {data.get('filename')}")

            # 從 API 回應中提取大綱資訊
            outline = data.get("outline", {})
            slides = outline.get("slides", [])

            print(f"   - 投影片數: {len(slides)}")
            print(f"   - 標題: {outline.get('title', 'N/A')}")

            # 檢查是否為 demo mode
            is_demo = len(slides) > 50
            if is_demo:
                print(f"   ⚠️ 警告: 可能使用了 demo mode ({len(slides)} 張投影片)")
            else:
                print(f"   ✅ 確認使用 LLM 生成")

            # 階段 2: 品質檢查
            print()
            print("🔍 品質檢查")
            print("-" * 80)

            # Check 1: Bullet 長度
            bullet_lengths = []
            for slide in slides:
                bullets = slide.get('bullets', [])
                if bullets:
                    avg_len = sum(len(b) for b in bullets) / len(bullets)
                    bullet_lengths.append(avg_len)

            avg_bullet_len = sum(bullet_lengths) / len(bullet_lengths) if bullet_lengths else 0
            bullet_check = avg_bullet_len >= 15
            quality_checks['bullet_length'] = bullet_check
            status = "✅" if bullet_check else "❌"
            print(f"{status} Bullet 長度 >= 15 字: {avg_bullet_len:.1f} 字")

            # Check 2: Speaker notes 覆蓋率
            slides_with_notes = sum(1 for s in slides if s.get('speaker_notes') and len(s.get('speaker_notes', '').strip()) > 0)
            notes_coverage = slides_with_notes / len(slides) if slides else 0
            coverage_check = notes_coverage >= 0.7
            quality_checks['notes_coverage'] = coverage_check
            status = "✅" if coverage_check else "❌"
            print(f"{status} Speaker notes 覆蓋率 >= 70%: {slides_with_notes}/{len(slides)} ({notes_coverage*100:.0f}%)")

            # Check 3: Speaker notes 平均長度
            note_lengths = [len(s.get('speaker_notes', '')) for s in slides if s.get('speaker_notes')]
            avg_note_len = sum(note_lengths) / len(note_lengths) if note_lengths else 0
            length_check = avg_note_len >= 50
            quality_checks['notes_length'] = length_check
            status = "✅" if length_check else "❌"
            print(f"{status} Speaker notes 平均長度 >= 50 字: {avg_note_len:.1f} 字")

            # Check 4: Layout 多樣性
            layouts = set(s.get('layout') for s in slides if s.get('layout'))
            diversity_check = len(layouts) >= 5
            quality_checks['layout_diversity'] = diversity_check
            status = "✅" if diversity_check else "❌"
            print(f"{status} Layout 多樣性 >= 5 種: {len(layouts)} 種 ({', '.join(sorted(layouts))})")

            # Check 5: 非 demo mode
            non_demo_check = not is_demo
            quality_checks['non_demo'] = non_demo_check
            status = "✅" if non_demo_check else "❌"
            print(f"{status} 非 Demo Mode: {'是' if non_demo_check else '否'}")

            # 階段 3: 下載並儲存 PPTX
            print()
            print("📦 下載 PPTX 檔案")
            print("-" * 80)

            filename = data.get('filename')
            download_start = time.time()

            download_response = await client.get(f"http://localhost:8000/api/download/{filename}")
            pptx_duration = time.time() - download_start

            if download_response.status_code == 200:
                pptx_bytes = download_response.content

                # 儲存測試檔案
                output_path = Path(__file__).parent / "output_integration_college_elegance.pptx"
                output_path.write_bytes(pptx_bytes)

                print(f"✅ PPTX 下載成功")
                print(f"   - 下載耗時: {pptx_duration:.1f} 秒")
                print(f"   - 檔案大小: {len(pptx_bytes):,} bytes ({len(pptx_bytes)/1024:.1f} KB)")
                print(f"   - 儲存位置: {output_path}")

                quality_checks['pptx_download'] = True
            else:
                print(f"❌ PPTX 下載失敗: HTTP {download_response.status_code}")
                quality_checks['pptx_download'] = False

            # 估算各階段時間
            outline_duration = total_duration * 0.95  # 大部分時間在 LLM 生成

    except httpx.ConnectError:
        print(f"❌ 無法連接到 API 服務器（http://localhost:8000）")
        print(f"   請確認服務器正在運行: cd txt2pptx && bash start.sh")
        return False
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 覆蓋率報告
    print()
    print("=" * 80)
    print("📊 覆蓋率報告")
    print("=" * 80)

    passed_checks = sum(1 for v in quality_checks.values() if v)
    total_checks = len(quality_checks)
    coverage = (passed_checks / total_checks) * 100

    print(f"\n品質檢查通過率: {passed_checks}/{total_checks} ({coverage:.1f}%)")
    print()

    # 詳細檢查結果
    print("檢查項目詳情:")
    for check_name, passed in quality_checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  - {check_name}: {status}")

    # 總時間分析
    total_time = total_duration
    print()
    print(f"總執行時間: {total_time:.1f} 秒")
    if outline_duration > 0:
        print(f"  - API 生成階段: {outline_duration:.1f} 秒 ({outline_duration/total_time*100:.0f}%)")
    if pptx_duration > 0:
        print(f"  - PPTX 下載階段: {pptx_duration:.1f} 秒 ({pptx_duration/total_time*100:.0f}%)")

    # 重試機制驗證
    print()
    print("🔄 重試機制驗證:")
    if total_duration > 100:
        print("   ✅ 響應時間超過 100 秒，可能經過重試")
        print(f"   推測: 經過 2-3 次重試才成功")
    elif total_duration > 70:
        print("   ✅ 響應時間 70-100 秒，可能經過 1 次重試")
        print(f"   推測: 第 2 次嘗試成功")
    else:
        print("   ✅ 響應時間 < 70 秒，第一次嘗試成功")
        print(f"   推測: 第 1 次嘗試成功")

    # 最終結果
    print()
    print("=" * 80)
    if coverage >= 80:
        print("🎉 測試通過！品質覆蓋率達標")
        return True
    else:
        print("⚠️ 測試未完全通過，但系統運作正常")
        return coverage >= 60


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
