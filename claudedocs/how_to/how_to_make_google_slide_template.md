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

---

## 佔位符（Placeholder）概念說明

### 佔位符不是普通的文字方塊

它們看起來很像，但在 PowerPoint 內部是**完全不同的物件**。

| | 普通文字方塊 (TextBox) | 佔位符 (Placeholder) |
|---|---|---|
| 比喻 | 你自己在白紙上畫一個框 | 表格裡預印好的空格欄位 |
| 誰定義位置？ | 程式碼自己指定座標 | **模板（Layout）預先定義好** |
| 繼承關係 | 無 | Master → Layout → Slide 三層繼承 |
| 有 `idx` 嗎？ | 無 | 有（如 idx=0 是標題，idx=1 是內文） |
| 有 `type` 嗎？ | 無 | 有（TITLE、BODY、PICTURE 等） |

### 佔位符的三層繼承

```text
Slide Master（母版）
  定義：「標題在上方，字體 36pt Calibri Bold」
       ↓ 繼承
Slide Layout（版面配置）
  定義：「這個 Layout 有標題(idx=0) + 內文(idx=1) + 圖片(idx=2)」
  覆寫：「標題位置改到左邊，內文佔 60% 寬」
       ↓ 繼承
Slide（實際投影片）
  只需要：placeholders[0].text = "我的標題"
  位置、大小、字體 → 全部從上面繼承
```

### 佔位符類型一覽

| type 值 | 用途 | 填入方式 |
|---------|------|----------|
| `TITLE` (15) | 標題 | `.text = "..."` |
| `BODY` (6) | 內文/條列 | `.text_frame.text = "..."` |
| `PICTURE` (18) | 圖片區域 | `.insert_picture(image_file)` |
| `SUBTITLE` (4) | 副標題 | `.text = "..."` |
| `SLIDE_NUMBER` (12) | 頁碼 | 自動填入 |
| `TABLE` (14) | 表格 | `.insert_table(rows, cols)` |

### 程式碼對比：文字方塊 vs 佔位符

目前 `pptx_generator.py` 用的是**文字方塊**（手動指定座標）：

```python
# 目前做法：手動指定每個座標（文字方塊）
txBox = slide.shapes.add_textbox(
    Inches(0.8),    # 左邊距 ← 自己算
    Inches(0.5),    # 上邊距 ← 自己算
    Inches(11.733), # 寬度   ← 自己算
    Inches(0.8)     # 高度   ← 自己算
)
txBox.text_frame.text = "標題文字"
```

如果改用**佔位符**（位置由模板決定）：

```python
# 模板做法：位置由模板決定（佔位符）
slide = prs.slides.add_slide(prs.slide_layouts[0])  # 使用 title_slide Layout
slide.placeholders[0].text = "標題文字"  # idx=0 → 標題佔位符，位置自動
slide.placeholders[1].text = "副標題"    # idx=1 → 副標題佔位符，位置自動
```

### 圖片佔位符的價值

這是佔位符最有價值的地方。目前專案的「圖片區」只是灰色矩形：

```python
# 目前：假圖片（灰色矩形 + 文字標籤）
_add_image_placeholder(slide, 7.2, 1.2, 5.2, 5.0, "圖片區域")
# 結果：一個灰色方塊，無法放入真正的圖片
```

用 Picture Placeholder 就能插入真正的圖片：

```python
# 模板做法：真實圖片插入
slide.placeholders[2].insert_picture(open('photo.jpg', 'rb'))
# 結果：圖片自動縮放到佔位符定義的大小和位置
```

### 在 PowerPoint / Google Slides 中辨認佔位符

在主題編輯器中，寫著「按一下以編輯...」的框就是佔位符：

```text
┌──────────────────────────────────────┐
│  按一下以編輯母片標題樣式              │  ← TITLE Placeholder (idx=0)
│  (Click to edit Master title style)   │
├──────────────────────────────────────┤
│  按一下以編輯母片文字樣式              │  ← BODY Placeholder (idx=1)
│  • 第二層                             │
│  • 第三層                             │
└──────────────────────────────────────┘
```

它們和手動插入的文字方塊外觀一樣，但內部的 XML 結構完全不同：

```xml
<!-- 普通文字方塊的 XML -->
<p:sp>
  <p:nvSpPr>
    <p:nvPr/>  <!-- 空的，無佔位符資訊 -->
  </p:nvSpPr>
</p:sp>

<!-- 佔位符的 XML -->
<p:sp>
  <p:nvSpPr>
    <p:nvPr>
      <p:ph idx="0" type="title"/>  <!-- 有 idx 和 type -->
    </p:nvPr>
  </p:nvSpPr>
</p:sp>
```

---

## 在 Google Slides 母片上插入佔位符

### 進入主題編輯器

1. 開啟 Google Slides 簡報
2. 上方選單 → **投影片 (Slide)** → **編輯主題 (Edit theme)**

左側面板會列出「母版 (Master)」和下方的多個「版面配置 (Layouts)」。

### 插入佔位符的操作

**選擇你要編輯的 Layout**（點選左側某個版面配置），然後：

上方選單 → **插入 (Insert)** → **佔位符 (Placeholder)** → 可選類型：

- 標題文字 (Title text)
- 副標題文字 (Subtitle text)
- 內文文字 (Body text)
- 圖片 (Image) — 僅部分版本支援
- 未編號清單 / 編號清單

選擇類型後，**在版面上拖曳**畫出佔位符的位置和大小。

> **重要：** Google Slides 的「插入 → 佔位符」選單**只有在主題編輯模式下才會出現**。在普通編輯模式下，「插入」選單裡不會有「佔位符」這個選項。

### 操作示範（以 bullets Layout 為例）

```text
第一步：在左側面板，右鍵 → 新增版面配置 (New layout)
第二步：重新命名為 "bullets"

第三步：插入 → 佔位符 → 標題文字
        在頂部拖曳出一個長條框
        ┌─────────────────────────────────┐
        │  按一下新增標題                    │ ← Title placeholder
        └─────────────────────────────────┘

第四步：插入 → 佔位符 → 內文文字
        在左下方拖曳出一個大框
        ┌──────────────────┐
        │  按一下新增文字    │ ← Body placeholder
        │                  │
        │                  │
        └──────────────────┘

完成後的 Layout 看起來像：
┌─────────────────────────────────────┐
│  按一下新增標題                       │
├───────────────────┬─────────────────┤
│                   │                 │
│  按一下新增文字    │  (空白區域，     │
│  • 項目一         │   可放靜態裝飾)   │
│  • 項目二         │                 │
│                   │                 │
└───────────────────┴─────────────────┘
```

### 佔位符 vs 文字方塊 — 在 Google Slides 中的差異

| 操作 | 結果 |
|------|------|
| 主題編輯器中 → 插入 → **佔位符** | 真正的 placeholder，匯出 .pptx 後 python-pptx 可透過 `placeholders[idx]` 存取 |
| 主題編輯器中 → 插入 → **文字方塊** | 變成 Layout 上的**靜態裝飾**，每張套用此 Layout 的投影片都會顯示，但程式碼無法透過 idx 存取 |
| 普通模式中 → 插入 → 文字方塊 | 只存在於該張投影片，與模板無關 |

### 每個 Layout 需要的佔位符配置

| Layout | 需插入的佔位符 |
|--------|---------------|
| title_slide | 標題文字 + 副標題文字 |
| section_header | 標題文字 + 副標題文字 |
| bullets | 標題文字 + 內文文字 |
| two_column | 標題文字 + 內文文字 x2（左右各一） |
| image_left | 標題文字 + 內文文字（右側）+ 圖片佔位符或灰色矩形（左側） |
| image_right | 標題文字 + 內文文字（左側）+ 圖片佔位符或灰色矩形（右側） |
| key_stats | 標題文字 + 內文文字 x3~4（排成卡片） |
| comparison | 標題文字 + 內文文字 x2（左右各一） |
| conclusion | 標題文字 + 內文文字 |

### 匯出後驗證 idx

完成所有 Layout 後，匯出為 `.pptx`，用 Python 腳本確認 idx：

```python
from pptx import Presentation

prs = Presentation('your_template.pptx')
for i, layout in enumerate(prs.slide_layouts):
    print(f"\n--- Layout {i}: {layout.name} ---")
    for ph in layout.placeholders:
        print(f"  idx={ph.placeholder_format.idx}  "
              f"type={ph.placeholder_format.type}  "
              f"name='{ph.name}'")
```

Google Slides 自動分配的 `idx` 通常從 0 開始遞增，但**順序不一定與你插入的順序相同**，所以這一步驗證不可省略。

---

## Accent Bar（強調裝飾條）說明

### 什麼是 Accent Bar？

就是一條**很細的彩色長條**，放在投影片的頂部或底部，純粹做裝飾用。

```text
┌══════════════════════════════════════┐  ← 這條就是 accent bar
│                                      │     （寬度填滿整張投影片，高度極薄）
│                                      │
│         投影片內容區域                 │
│                                      │
│                                      │
└──────────────────────────────────────┘
```

### 在本專案中的實作

`pptx_generator.py` 裡的 `_add_top_accent_bar()` 做的事情：

```python
# 在投影片頂端畫一條 accent 色的細長矩形
_add_shape(slide, MSO_SHAPE.RECTANGLE,
    left=0,           # 最左邊
    top=0,            # 最頂端
    width=13.333,     # 填滿整張 16:9 投影片寬度
    height=0.06,      # 極薄（約 1.5mm）
    fill_color=Theme.ACCENT  # #02C39A（薄荷綠）
)
```

產生的結果就是一條寬 13.333 吋、高 0.06 吋的薄荷綠色細線，貼在投影片最上方。

### 為什麼要用它？

- **視覺一致性** — 每張投影片頂部都有同一條色線，讓整份簡報有統一的品牌感
- **專業感** — 企業簡報常見的設計手法，用品牌色做微小的裝飾點綴
- **分隔作用** — 把投影片頂部邊緣和內容做一個視覺區隔

### 在模板中如何處理

Accent bar 不承載任何內容，只是一個設計元素。在模板化架構中，這類裝飾應該放在 **Slide Master** 或各 **Layout** 上作為**靜態形狀**（不是佔位符），而不是每次都用程式碼畫。

在 Google Slides 主題編輯器中的做法：

1. 選擇母版（Master）或特定 Layout
2. **插入** → **形狀** → **矩形**
3. 拉到投影片頂端，調整為極扁的長條
4. 設定填充色為主題的 accent 色（如 `#02C39A`）
5. 設定無框線

這樣每張套用此母版/Layout 的投影片都會自動帶有這條裝飾，無需程式碼介入。
