#!/usr/bin/env python3
"""
測試所有模板能否正確載入
驗證修復後的動態模板載入功能
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "txt2pptx"))

from backend.pptx_generator_template import generate_pptx, TEMPLATES_DIR, DEFAULT_TEMPLATE
from backend.models import PresentationOutline, SlideData, SlideLayout

# 測試用的簡單 outline
TEST_OUTLINE = PresentationOutline(
    title="模板測試簡報",
    slides=[
        SlideData(
            layout=SlideLayout.TITLE,
            title="模板測試",
            subtitle="驗證動態模板載入功能"
        ),
        SlideData(
            layout=SlideLayout.BULLETS,
            title="測試內容",
            bullets=["項目一", "項目二", "項目三"]
        ),
    ]
)

# 所有應該存在的模板
ALL_TEMPLATES = [
    "College_Elegance",
    "Data_Centric",
    "High_Contrast",
    "Minimalist_Corporate",
    "Modernist",
    "ocean_gradient",
    "Startup_Edge",
    "Zen_Serenity",
]

def test_template_files_exist():
    """檢查所有模板檔案是否存在"""
    print("🔍 檢查模板檔案...")
    missing = []
    for template_id in ALL_TEMPLATES:
        template_path = TEMPLATES_DIR / f"{template_id}.pptx"
        if template_path.exists():
            print(f"  ✅ {template_id}.pptx exists ({template_path.stat().st_size} bytes)")
        else:
            print(f"  ❌ {template_id}.pptx MISSING")
            missing.append(template_id)

    return len(missing) == 0, missing

def test_template_loading():
    """測試每個模板能否正確載入並生成 PPTX"""
    print("\n🔧 測試模板載入...")
    results = []

    for template_id in ALL_TEMPLATES:
        try:
            print(f"  Testing {template_id}...", end=" ")
            pptx_bytes = generate_pptx(TEST_OUTLINE, template_id=template_id)

            if len(pptx_bytes) > 0:
                print(f"✅ Success ({len(pptx_bytes)} bytes)")
                results.append((template_id, True, len(pptx_bytes)))
            else:
                print(f"❌ Generated empty file")
                results.append((template_id, False, 0))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((template_id, False, str(e)))

    return results

def test_fallback_behavior():
    """測試不存在的模板會 fallback 到預設模板"""
    print("\n🔄 測試 fallback 行為...")
    fake_template = "nonexistent_template"

    try:
        print(f"  Testing with fake template '{fake_template}'...", end=" ")
        pptx_bytes = generate_pptx(TEST_OUTLINE, template_id=fake_template)

        if len(pptx_bytes) > 0:
            print(f"✅ Fallback works ({len(pptx_bytes)} bytes)")
            return True
        else:
            print(f"❌ Fallback failed (empty file)")
            return False
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
        return False

def main():
    print("=" * 60)
    print("模板載入測試")
    print("=" * 60)

    # Test 1: 檔案存在性
    files_ok, missing = test_template_files_exist()

    # Test 2: 模板載入
    results = test_template_loading()

    # Test 3: Fallback 行為
    fallback_ok = test_fallback_behavior()

    # 統計結果
    print("\n" + "=" * 60)
    print("測試結果總結")
    print("=" * 60)

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    print(f"✅ 成功載入: {success_count}/{total_count} 個模板")
    print(f"❌ 載入失敗: {total_count - success_count}/{total_count} 個模板")
    print(f"🔄 Fallback 測試: {'✅ 通過' if fallback_ok else '❌ 失敗'}")

    if success_count == total_count and fallback_ok:
        print("\n🎉 所有測試通過！")
        return 0
    else:
        print("\n⚠️ 部分測試失敗")
        if not files_ok:
            print(f"  缺少檔案: {', '.join(missing)}")

        failed = [tid for tid, success, _ in results if not success]
        if failed:
            print(f"  載入失敗: {', '.join(failed)}")

        return 1

if __name__ == "__main__":
    sys.exit(main())
