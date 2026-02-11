# PPTX 模板機制分析與製作指南

## 目前架構：程式碼繪製（Code-Drawn）

本專案 `pptx_generator.py` **不使用 .pptx 模板檔**，所有投影片都是從空白佈局開始，透過 python-pptx API 手動繪製。

### 核心證據

```python
# pptx_generator.py L446 — 空白建構，未傳入模板
prs = Presentation()

# 所有 builder 都使用 Blank layout
slide = prs.slides.add_slide(prs.slide_layouts[6])  # index 6 = Blank
```

### 目前的「模板」替代機制

| 層級 | 實作方式 | 位置 |
|------|---------|------|
| 色彩/字體 | `Theme` 類硬編碼 Ocean Gradient 色系 + Calibri 字體 | L15-34 |
| 佈局定義 | 9 個 `_build_*` 函式，各自用硬編碼 Inches 座標繪製 | L150-425 |
| 佈局分派 | `BUILDERS` 字典將 `SlideLayout` enum 映射到 builder | L431-441 |
| 元素繪製 | Helper 函式（`_add_text_box`, `_add_shape`, `_add_bullets`） | L40-143 |

每張投影片的繪製流程：

```
空白投影片
  |- _set_slide_bg()          -> 設定背景色
  |- _add_shape(RECTANGLE)    -> 裝飾條/卡片背景
  |- _add_text_box()          -> 標題/副標題
  |- _add_bullets()           -> 條列項目（手動 XML 插入 buChar）
  |- _add_shape(OVAL)         -> 圓形裝飾/icon 占位
  |- _add_image_placeholder() -> 灰色矩形假圖區域
```

### 這種設計的特點

**優點：**
- 不需額外的 .pptx 模板檔
- 精確控制每個元素的位置和樣式
- 所有邏輯自包含在單一 Python 檔案中

**缺點：**
- 修改佈局需要改動程式碼中的硬編碼座標（400+ 行）
- 無法讓使用者上傳自己的企業模板
- 新增佈局需要寫新的 builder 函式
- 圖片區域只是佔位符（灰色矩形），無法嵌入真實圖片
- 字體依賴系統安裝的 Calibri

---

## python-pptx 模板機制原理

### 三層繼承架構

```
Slide Master（母版）
   |- Slide Layout（版面配置）  <- 繼承母版的佔位符 type
         |- Slide（實際投影片）  <- 繼承版面配置的佔位符 idx
```

- `Presentation('template.pptx')` 載入模板的 slide_masters 和 slide_layouts
- 每個 slide_layout 包含 placeholders（佔位符），每個 placeholder 有 `idx` 和 `type`
- 程式碼透過 `slide.placeholders[idx]` 填入內容
- 位置、大小、格式全由模板決定，程式碼不再需要硬編碼座標

### Placeholder 三種關鍵類型

```
+----------------------------------------------+
|  Title Placeholder (idx=0)                    | <- shapes.title
|  type: TITLE                                  |
+----------------------------------------------+
|  Body/Content Placeholder (idx=1)             | <- placeholders[1]
|  type: BODY — 接受文字 bullets                 |
+----------------------------------------------+
|  Picture Placeholder (idx=2)                  | <- placeholders[2].insert_picture()
|  type: PICTURE — 接受圖片插入                  |
+----------------------------------------------+
```

---

## 模板檔必須包含的要素

### 1. 投影片大小（Slide Size）

16:9 寬螢幕（13.333" x 7.5"），與目前程式碼一致。使用模板後 `prs.slide_width / prs.slide_height` 設定可移除。

### 2. 主題（Theme）

模板內嵌的 Theme 取代目前的 `Theme` 類：

| Theme 要素 | 對應目前程式碼 | 模板中設定位置 |
|---|---|---|
| 色彩方案 (Color Scheme) | `Theme.PRIMARY`, `Theme.ACCENT` 等 12 個顏色 | PowerPoint -> 設計 -> 色彩 |
| 字體方案 (Font Scheme) | `Theme.TITLE_FONT = "Calibri"` | PowerPoint -> 設計 -> 字型 |
| 背景樣式 | `_set_slide_bg()` 各 builder 的背景色 | 在各 Slide Layout 上直接設定 |

### 3. Slide Layouts — 9 個版面配置

此為模板的核心。需為目前 9 種 `SlideLayout` enum 各設計一個版面配置：

| # | Layout 名稱 | 所需 Placeholders | placeholder idx 建議 |
|---|---|---|---|
| 0 | `title_slide` | Title(0) + Subtitle(1) | idx=0, 1 |
| 1 | `section_header` | Title(0) + Subtitle(1) | idx=0, 1 |
| 2 | `bullets` | Title(0) + Body/Bullets(1) + Picture(2) | idx=0, 1, 2 |
| 3 | `two_column` | Title(0) + LeftTitle(10) + LeftBody(11) + RightTitle(12) + RightBody(13) | idx=0, 10-13 |
| 4 | `image_left` | Title(0) + Picture(1) + Body(2) | idx=0, 1, 2 |
| 5 | `image_right` | Title(0) + Body(1) + Picture(2) | idx=0, 1, 2 |
| 6 | `key_stats` | Title(0) + Body(1)...(4) 或用自訂 text placeholders | idx=0, 10-13 |
| 7 | `comparison` | Title(0) + LeftTitle(10) + LeftBody(11) + RightTitle(12) + RightBody(13) | idx=0, 10-13 |
| 8 | `conclusion` | Title(0) + Body(1) | idx=0, 1 |

### 4. Slide Master 裝飾元素

目前程式碼手動繪製的裝飾，應改放入模板：

| 裝飾 | 程式碼位置 | 應放入模板何處 |
|---|---|---|
| 頂部 accent bar | `_add_top_accent_bar()` | Slide Master 或各 Layout 的靜態形狀 |
| 頁碼 | `_add_slide_number()` | Slide Master 的 slide number placeholder |
| 底部裝飾條 | `_build_title_slide` L168 | title_slide Layout 的靜態形狀 |
| VS 圓形 | `_build_comparison` L381 | comparison Layout 的靜態形狀 |

---

## 模板製作步驟（在 PowerPoint 中）

1. **新建簡報** -> 設計 -> 投影片大小 -> 寬螢幕 16:9
2. **檢視 -> 投影片母版** -> 進入母版編輯模式
3. 在母版上設定：
   - 背景、色彩方案、字型方案
   - 頂部 accent bar（靜態形狀）
   - 頁碼佔位符（右下角）
4. **為每種 Layout 新增版面配置**，插入對應的佔位符
   - 插入 -> 佔位符 -> 選擇文字/圖片/內容
5. 調整每個佔位符的位置、大小、預設字型
6. **關閉母版檢視** -> 另存為 `.pptx`

---

## 程式碼改動方向

使用模板後，`generate_pptx()` 從「手動繪製」變成「填入佔位符」：

```python
# 改寫前（目前：手動繪製 400+ 行）
prs = Presentation()
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
_add_text_box(slide, title, 0.8, 0.5, 11.733, 0.8, ...)  # 硬編碼座標
_add_shape(slide, RECTANGLE, 0, 0, 13.333, 0.06, ...)     # 手動裝飾

# 改寫後（模板方式）
prs = Presentation('templates/ocean_gradient.pptx')
slide = prs.slides.add_slide(prs.slide_layouts[2])  # bullets layout
slide.shapes.title.text = title                       # 自動定位
slide.placeholders[1].text_frame.text = bullets[0]    # 自動定位
slide.placeholders[2].insert_picture('image.png')     # 圖片插入
```

### 完整對應關係

```
目前架構                         模板架構
----------                       ----------
Theme 類 (12 個顏色常數)    ->   .pptx 內嵌 Theme（色彩+字型方案）
9 個 _build_* 函式 (400行)  ->   9 個 Slide Layouts + Placeholders
_add_text_box() 硬編碼座標  ->   slide.placeholders[idx].text = ...
_add_image_placeholder()    ->   placeholders[idx].insert_picture()
_add_shape() 裝飾元素       ->   Layout 上的靜態形狀（設計時放好）
BUILDERS 字典分派           ->   SlideLayout enum -> layout index 映射
```

### 預期效果

- `pptx_generator.py` 從 ~460 行壓縮到 ~100 行
- 使用者可替換 `.pptx` 模板檔自訂企業品牌風格，無需修改程式碼
- 圖片佔位符可透過 `insert_picture()` 插入真實圖片

### 建議的模板存放路徑

```
txt2pptx/
  templates/
    ocean_gradient.pptx   <- 預設模板
    corporate.pptx        <- 企業模板（未來擴充）
```

程式碼透過 `GenerateRequest` 新增 `template` 欄位讓前端選擇模板。
