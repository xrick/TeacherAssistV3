# 使用 Google Slides 製作 .pptx 模板指南

## 可行性結論

**可以，但有限制。** Google Slides 能匯出 `.pptx`，python-pptx 可以讀取，但 placeholder 控制能力比 PowerPoint 弱。

## 功能比較

| 面向 | Google Slides | PowerPoint |
|------|:---:|:---:|
| Slide Master 編輯 | 有（主題編輯器） | 有（投影片母版） |
| 新增自訂 Layout | 有 | 有 |
| 插入文字 Placeholder | 有 | 有 |
| 插入**圖片** Placeholder | **無原生支援** | 有 |
| 控制 Placeholder `idx` | **無法直接控制** | 可透過 XML 編輯 |
| 匯出 .pptx 格式 | 有 | 原生 |
| 色彩/字型方案 | 有（較簡化） | 完整控制 |

## 最大限制

1. **無法插入 Picture Placeholder** — Google Slides 的主題編輯器只能插入「文字佔位符」和「標題佔位符」，**沒有圖片佔位符選項**。這表示 `image_left`、`image_right`、`bullets`（含圖片區）這三種 layout 無法完整製作。
2. **Placeholder idx 不可控** — Google Slides 自動分配 idx，匯出後需要用 python-pptx 檢查實際數值才能在程式碼中正確對應。

---

## 逐步操作指南

### 第一步：建立新簡報

1. 前往 [slides.google.com](https://slides.google.com) → **空白簡報**
2. 點選 **投影片** → **編輯主題** 進入母版編輯模式

### 第二步：設定投影片尺寸

1. **檔案** → **頁面設定** → 選擇 **寬螢幕 16:9**（與目前程式碼一致）

### 第三步：設定主題（Master）

在主題編輯器的最上方是「母版」（Master），所有 Layout 都會繼承它：

1. 設定背景色（Ocean Gradient 風格的漸層或純色）
2. 加入靜態裝飾元素：
   - 頂部 accent bar（插入矩形，設定為主色 `#1B3A5C`，高度約 0.06 吋）
   - 頁碼佔位符（插入 → 特殊字元 或 文字方塊寫「#」）

### 第四步：建立 9 個 Layout

在母版下方逐一新增版面配置，每個 Layout 按以下規格：

#### Layout 0 — title_slide（封面）

1. 右鍵母版 → **新增版面配置**，命名為 `title_slide`
2. 插入佔位符 → **標題**（大字，置中偏上）
3. 插入佔位符 → **副標題**（小字，置中偏下）
4. 加入底部裝飾條（靜態矩形）

#### Layout 1 — section_header（章節頁）

1. 新增版面配置，命名為 `section_header`
2. 插入 **標題** 佔位符（置中）
3. 插入 **副標題** 佔位符

#### Layout 2 — bullets（條列）

1. 新增版面配置，命名為 `bullets`
2. 插入 **標題** 佔位符（頂部）
3. 插入 **內文** 佔位符（左側，佔約 60% 寬度）
4. **圖片區：** 插入一個灰色矩形作為視覺佔位（非真正的 Picture Placeholder）

#### Layout 3 — two_column（雙欄）

1. 新增版面配置，命名為 `two_column`
2. 插入 **標題** 佔位符
3. 左欄：插入 **小標題** + **內文** 佔位符
4. 右欄：插入 **小標題** + **內文** 佔位符

#### Layout 4 — image_left（左圖右文）

1. 新增版面配置，命名為 `image_left`
2. 插入 **標題** 佔位符
3. 左側：灰色矩形充當圖片區（標注 "IMAGE"）
4. 右側：插入 **內文** 佔位符

#### Layout 5 — image_right（右圖左文）

- 同 Layout 4，左右對調

#### Layout 6 — key_stats（數據頁）

1. 插入 **標題** 佔位符
2. 插入 3-4 個 **內文** 佔位符（排列成卡片式）

#### Layout 7 — comparison（對比頁）

- 與 Layout 3 相同結構，中間可加「VS」圓形裝飾

#### Layout 8 — conclusion（結論頁）

1. 插入 **標題** 佔位符
2. 插入 **內文** 佔位符

### 第五步：關閉主題編輯器

點選右上角 **X** 關閉主題編輯模式

### 第六步：匯出為 .pptx

1. **檔案** → **下載** → **Microsoft PowerPoint (.pptx)**
2. 將檔案存放至 `txt2pptx/templates/ocean_gradient.pptx`

### 第七步：檢查 Placeholder idx（關鍵步驟）

匯出後**必須**用 python-pptx 確認每個 Layout 的 placeholder idx：

```python
from pptx import Presentation

prs = Presentation('templates/ocean_gradient.pptx')
for i, layout in enumerate(prs.slide_layouts):
    print(f"\n--- Layout {i}: {layout.name} ---")
    for ph in layout.placeholders:
        print(f"  idx={ph.placeholder_format.idx}, "
              f"type={ph.placeholder_format.type}, "
              f"name='{ph.name}', "
              f"size=({ph.width}, {ph.height})")
```

將輸出的 `idx` 值記錄下來，用於程式碼中的 `slide.placeholders[idx]` 對應。

### 第八步：程式碼適配

根據第七步得到的 idx 值，建立映射表：

```python
# 範例 — 實際 idx 以檢查結果為準
LAYOUT_MAP = {
    SlideLayout.TITLE_SLIDE: {
        'index': 0, 'title_idx': 0, 'subtitle_idx': 1
    },
    SlideLayout.BULLETS: {
        'index': 2, 'title_idx': 0, 'body_idx': 1
        # 無 picture_idx（Google Slides 限制）
    },
    # ...
}
```

---

## Google Slides 模板的補強方案

由於 Google Slides 無法建立 Picture Placeholder，匯出後可用 python-pptx 腳本補強：

```python
from pptx import Presentation
from pptx.util import Inches
from pptx.oxml.ns import qn
from lxml import etree
import copy

prs = Presentation('templates/ocean_gradient.pptx')

# 找到 bullets layout (index 2)，手動加入 Picture Placeholder
layout = prs.slide_layouts[2]
sp_tree = layout.placeholders._element.getparent()

# 建立 picture placeholder XML
pic_ph = etree.SubElement(sp_tree, qn('p:sp'))
# ... (需要手動構建 placeholder XML，較複雜)

prs.save('templates/ocean_gradient_enhanced.pptx')
```

---

## 方案比較與建議

| 方案 | 難度 | 完整度 | 推薦場景 |
|------|------|--------|----------|
| PowerPoint 製作 | 中 | 100% | 有 PowerPoint 授權 |
| Google Slides + 補強腳本 | 高 | ~90% | 僅有 Google 帳號 |
| LibreOffice Impress | 中 | ~85% | Linux 環境 |
| 純 python-pptx 腳本產生模板 | 高 | 100% | 完全程式化控制 |

### 建議

如果沒有 PowerPoint，推薦使用**「純 python-pptx 腳本產生模板」**方案 — 直接用程式碼建立 `.pptx` 模板檔，可以精確控制所有 placeholder 的 `idx`、`type`、位置和大小，避免 Google Slides 的限制。

---

## 建議的工作流程

```
最佳方案（有 PowerPoint）:
  PowerPoint 製作 → 完整 placeholder 支援 → 直接使用

務實方案（僅有 Google Slides）:
  Google Slides 製作基本 Layout
    → 匯出 .pptx
    → 用 python-pptx 腳本補強（加入 Picture Placeholder）
    → 用檢查腳本確認 idx
    → 最終模板

自動化方案（無任何簡報軟體）:
  python-pptx 腳本
    → 程式化建立所有 Layout + Placeholder
    → 完整控制 idx / type / 位置
    → 最終模板
```
