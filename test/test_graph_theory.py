#!/usr/bin/env python3
"""
整合測試：圖論 (Graph Theory)
測試 ocean_gradient 主題的簡報品質
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "txt2pptx"))

from backend.models import GenerateRequest
from backend.llm_service import generate_outline
from backend.pptx_generator import generate_pptx


async def main():
    # 圖論測試文字
    test_text = """圖論（英語：Graph theory），是組合數學分支，和其他數學分支如群論、矩陣論、拓撲學有著密切關係。
圖是圖論的主要研究對象。圖是由若干給定的頂點及連接兩頂點的邊所構成的圖形，這種圖形通常用來描述某些事物之間的某種特定關係。頂點用於代表事物，連接兩頂點的邊則用於表示兩個事物間具有這種關係。
圖論起源於著名的柯尼斯堡七橋問題。該問題於1736年被歐拉解決，因此普遍認為歐拉是圖論的創始人。
圖論的研究對象相當於一維的單純複形。
歷史:
一般認為，歐拉於1736年出版的關於柯尼斯堡七橋問題的論文是圖論領域的第一篇文章[3]。此問題被推廣為著名的歐拉路問題，亦即一筆畫問題。而此論文與范德蒙的一篇關於騎士週遊問題的文章，則是繼承了萊布尼茨提出的「位置分析」的方法。歐拉提出的關於凸多邊形頂點數、棱數及面數之間的關係的歐拉公式與圖論有密切聯繫，此後又被柯西等人[4][5]進一步研究推廣，成了拓撲學的起源。1857年，哈密頓發明了「環遊世界遊戲」（icosian game），與此相關的則是另一個廣為人知的圖論問題「哈密頓路徑問題」。

西爾維斯特於1878年發表在《自然》上的一篇論文中首次提出「圖」這一名詞[6]。

歐拉的論文發表後一個多世紀，凱萊研究了在微分學中出現的一種數學分析的特殊形式，而這最終將他引向對一種特殊的被稱為「樹」的圖的研究。由於有機化學中有許多樹狀結構的分子，這些研究對於理論化學有著重要意義，尤其是其中關於具有某一特定性質的圖的計數問題。除凱萊的成果外，波利亞也於1935至1937年發表了一些成果，1959年，De Bruijn做了一些推廣。這些研究成果奠定了圖的計數理論的基礎。凱萊將他關於樹的研究成果與當時有關化合物的研究聯繫起來，而圖論中有一部分術語正是來源於這種將數學與化學相聯繫的做法。

四色問題可謂是圖論研究史上最著名也是產生成果最多的問題之一：「是否任何一幅畫在平面上的地圖都可以用四種顏色染色，使得任意兩個相鄰的區域不同色？」這一問題由法蘭西斯·古德里於1852年提出，而最早的文字記載則出現在德摩根於1852年寫給哈密頓的一封信上。包括凱萊、肯普等在內的許多人都曾給出過錯誤的證明。泰特（Peter Guthrie Tait）、希伍德、拉姆齊和Hadwige（Hugo Hadwiger）對此問題的研究與推廣引發了對嵌入具有不同虧格的曲面的圖的著色問題的研究。一百多年後，四色問題仍未解決。1969年，Heinrich Heesch發表了一個用計算機解決此問題的方法。1976年，凱尼斯·阿佩爾和沃夫岡·哈肯藉助計算機給出了一個證明，此方法按某些性質將所有地圖分為1936類並利用計算機一一驗證了它們可以用四種顏色染色。但此方法由於過於複雜，在當時未被廣泛接受。
1860年之1930年間，若當、庫拉托夫斯基和惠特尼從之前獨立於圖論發展的拓撲學中吸取大量內容進入圖論，而現代代數方法的使用更讓圖論與拓撲走上共同發展的道路。其中應用代數較早者如物理學家基爾霍夫於1845年發表的基爾霍夫電路定律。
圖論中概率方法的引入，尤其是埃爾德什和Alfréd Rényi關於隨機圖連通的漸進概率的研究使得圖論產生了新的分支隨機圖論。"""

    print("=" * 80)
    print("整合測試：Graph Theory (圖論)")
    print("主題：Ocean Gradient")
    print("=" * 80)

    # 準備請求
    request = GenerateRequest(
        text=test_text,
        num_slides=8,
        language="繁體中文",
        style="ocean_gradient"
    )

    # 生成大綱
    print("\n📝 生成簡報大綱...")
    outline = await generate_outline(request)

    print(f"\n✅ 大綱生成完成！")
    print(f"   - 總投影片數: {len(outline.slides)}")
    print(f"   - 主題: {outline.theme}")

    # 品質檢查
    print("\n" + "=" * 80)
    print("🎯 品質檢查:")
    print("=" * 80)

    checks_passed = 0
    checks_total = 4

    # 1. Bullet 長度檢查
    bullet_lengths = []
    for slide in outline.slides:
        if hasattr(slide, 'bullets') and slide.bullets:
            avg_len = sum(len(b) for b in slide.bullets) / len(slide.bullets)
            bullet_lengths.append(avg_len)

    avg_bullet_len = sum(bullet_lengths) / len(bullet_lengths) if bullet_lengths else 0
    bullet_check = avg_bullet_len >= 15
    status = "✅" if bullet_check else "❌"
    print(f"{status} Bullet 長度 >= 15 字: {avg_bullet_len:.1f} 字")
    if bullet_check:
        checks_passed += 1

    # 2. Speaker notes 覆蓋率
    slides_with_notes = sum(1 for s in outline.slides if s.speaker_notes and len(s.speaker_notes.strip()) > 0)
    notes_coverage = slides_with_notes / len(outline.slides)
    coverage_check = notes_coverage >= 0.7
    status = "✅" if coverage_check else "❌"
    print(f"{status} Speaker notes 覆蓋率 >= 70%: {slides_with_notes}/{len(outline.slides)}")
    if coverage_check:
        checks_passed += 1

    # 3. Speaker notes 平均長度
    note_lengths = [len(s.speaker_notes) for s in outline.slides if s.speaker_notes]
    avg_note_len = sum(note_lengths) / len(note_lengths) if note_lengths else 0
    length_check = avg_note_len >= 50
    status = "✅" if length_check else "❌"
    print(f"{status} Speaker notes 平均長度 >= 50 字: {avg_note_len:.1f} 字")
    if length_check:
        checks_passed += 1

    # 4. Layout 多樣性
    layouts = set(s.layout.value for s in outline.slides)
    diversity_check = len(layouts) >= 5
    status = "✅" if diversity_check else "❌"
    print(f"{status} Layout 多樣性 >= 5 種: {len(layouts)} 種")
    if diversity_check:
        checks_passed += 1

    print(f"\n通過檢查: {checks_passed}/{checks_total}")

    if checks_passed == checks_total:
        print("🎉 完美！所有檢查都通過，SYSTEM_PROMPT 完全生效。")
    elif checks_passed >= checks_total * 0.7:
        print("⚠️ 部分檢查未通過，SYSTEM_PROMPT 可能部分生效。")
    else:
        print("🚨 大部分檢查未通過，可能正在使用 demo fallback 或 SYSTEM_PROMPT 未生效。")

    # 生成 PPTX
    print(f"\n📦 生成 PPTX 檔案...")
    pptx_bytes = generate_pptx(outline)

    # 儲存測試檔案
    output_path = Path(__file__).parent / "output_graph_theory.pptx"
    output_path.write_bytes(pptx_bytes)

    print(f"✅ 測試完成！檔案已儲存至: {output_path}")

    return checks_passed, checks_total


if __name__ == "__main__":
    passed, total = asyncio.run(main())
    sys.exit(0 if passed == total else 1)
