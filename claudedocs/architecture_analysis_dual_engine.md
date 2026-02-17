# 雙引擎 PPTX 生成系統 - 架構分析報告

**分析日期**: 2026-02-17
**專案**: TeacherAssist TXT2PPTX
**分析範圍**: 後端雙引擎支援 + 前端 UI 選項 + 降級機制

---

## 📊 執行摘要

**結論**: ✅ **雙引擎系統已實作完成 90%**

- ✅ 第一階段（後端支援）：**已完成**
- ⚠️ 第二階段（前端 UI）：**已完成基礎版，需升級為進階設定**
- ❌ 降級機制：**未實作**

---

## 🏗️ 現況架構分析

### 1. 後端雙引擎實作（已完成）

#### 1.1 主路由邏輯 ([main.py](../txt2pptx/backend/main.py))

```python
# L13-14: 雙引擎導入
from .pptx_generator import generate_pptx as generate_pptx_code_drawn
from .pptx_generator_template import generate_pptx as generate_pptx_template

# L54-59: 引擎分派邏輯
GENERATORS = {
    "code_drawn": generate_pptx_code_drawn,
    "ocean_gradient": generate_pptx_template,
}
generator = GENERATORS.get(request.template, generate_pptx_code_drawn)
pptx_bytes = generator(outline)
```

**優點**：
- ✅ 統一介面：兩個 generator 都接收 `PresentationOutline`，回傳 `bytes`
- ✅ 擴充性佳：新增模板只需在 `GENERATORS` dict 加入新項目
- ✅ 預設降級：若 `template` 參數錯誤，自動使用 `code_drawn`

**缺點**：
- ❌ 無模板檔案驗證：若 `ocean_gradient.pptx` 遺失或損毀，會在生成時才崩潰
- ❌ 無明確的 fallback 策略：預設降級是靜默的，使用者無法得知發生切換

---

#### 1.2 資料模型 ([models.py](../txt2pptx/backend/models.py))

```python
# L51: GenerateRequest 已支援 template 參數
template: str = Field(default="code_drawn")
```

**優點**：
- ✅ 型別安全：透過 Pydantic v2 驗證
- ✅ 預設值明確：`code_drawn` 作為 fallback

**缺點**：
- ❌ 無 enum 約束：接受任意字串，未驗證模板是否存在
- 💡 建議：改用 `Enum` 或 `Literal["code_drawn", "ocean_gradient"]`

---

#### 1.3 程式碼繪製引擎 ([pptx_generator.py](../txt2pptx/backend/pptx_generator.py))

**技術特徵**：
- 從空白 `Presentation()` 建立
- 使用 `Blank` layout (index 6)
- 手動繪製所有元素（硬編碼座標 Inches）
- 約 460 行程式碼
- 支援 9 種 layout：TITLE, SECTION, BULLETS, TWO_COLUMN, IMAGE_LEFT, IMAGE_RIGHT, KEY_STATS, COMPARISON, CONCLUSION

**優缺點**：
- ✅ 無外部依賴：不需模板檔案
- ✅ 完全控制：精確定位每個元素
- ❌ 難以維護：修改樣式需改程式碼
- ❌ 無法讓使用者自訂模板

---

#### 1.4 模板引擎 ([pptx_generator_template.py](../txt2pptx/backend/pptx_generator_template.py))

**技術特徵**：
- 載入 `templates/ocean_gradient.pptx` 模板
- 透過 `slide.placeholders[idx]` 填入內容
- 支援相同的 9 種 layout
- 約 288 行程式碼（比 code_drawn 少 37%）

**模板對應**：
```python
LAYOUT_MAP = {
    SlideLayout.TITLE:       0,   # TITLE (CENTER_TITLE + SUBTITLE)
    SlideLayout.SECTION:     1,   # SECTION_HEADER
    SlideLayout.BULLETS:     2,   # TITLE_AND_BODY (+ PICTURE)
    SlideLayout.TWO_COLUMN:  3,   # TITLE_AND_TWO_COLUMNS
    SlideLayout.IMAGE_LEFT:  4,   # TITLE_ONLY (+ PICTURE左)
    SlideLayout.IMAGE_RIGHT: 5,   # ONE_COLUMN_TEXT (+ PICTURE右)
    SlideLayout.KEY_STATS:   6,   # CAPTION_ONLY (3個統計卡片)
    SlideLayout.COMPARISON:  7,   # TITLE_AND_TWO_COLUMNS_1
    SlideLayout.CONCLUSION:  8,   # BLANK
}
```

**Placeholder 索引常數**：
```python
PH_TITLE = 0        # 標題
PH_BODY = 1         # 內文/副標題
PH_BODY_RIGHT = 2   # 右欄內文
PH_BODY_COL2 = 3    # 第二欄
PH_BODY_COL3 = 4    # 第三欄
PH_PICTURE = 10     # 圖片佔位符
PH_SLIDE_NUM = 12   # 頁碼
```

**優缺點**：
- ✅ 程式碼更簡潔：少 37% 程式碼
- ✅ 樣式可替換：更換模板檔即可改變外觀
- ✅ 支援真實圖片：可透過 `PH_PICTURE` 插入圖片（目前未實作）
- ❌ 模板依賴：若檔案遺失會失敗
- ❌ 無錯誤處理：模板損毀時會崩潰

---

### 2. 前端 UI 實作（已完成基礎版）

#### 2.1 HTML 選單 ([index.html](../txt2pptx/frontend/index.html))

```html
<!-- L72-78: 模板選擇下拉選單 -->
<div class="option-group">
    <label for="template">簡報模板</label>
    <select id="template">
        <option value="code_drawn">經典繪製</option>
        <option value="ocean_gradient" selected>Ocean Gradient</option>
    </select>
</div>
```

**位置**: 與「投影片數量」、「簡報風格」、「語言」並列於同一列

**預設值**: `ocean_gradient`（模板引擎）

---

#### 2.2 JavaScript 邏輯 ([app.js](../txt2pptx/frontend/app.js))

```javascript
// L16: 元素綁定
template: () => $('#template'),

// L60-66: 請求組裝
const request = {
    text: text,
    num_slides: parseInt(els.numSlides().value),
    style: els.style().value,
    language: els.language().value,
    template: els.template().value,  // ← 取得使用者選擇
};

// L77-81: API 呼叫
const response = await fetch(`${API_BASE}/api/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
});
```

**優點**：
- ✅ 完整傳遞參數到後端
- ✅ 與其他選項一致的處理方式

**缺點**：
- ❌ 無前端驗證：未檢查模板是否可用
- ❌ 無錯誤處理：若模板生成失敗，使用者只看到通用錯誤訊息
- ❌ 無說明文字：使用者不知道兩個選項的差異

---

### 3. 模板檔案

**路徑**: `txt2pptx/templates/`

**已有檔案**：
- ✅ `ocean_gradient.pptx` (27KB)
- ✅ `standard_template.pptx` (36KB)

**問題**：
- ❌ 未檢查檔案完整性（啟動時或 API 呼叫前）
- ❌ 未在前端列出可用模板（目前硬編碼）

---

## ⚠️ 缺失功能分析

### 缺失 1: 降級機制（Fallback Mechanism）

**現況**：
- `GENERATORS.get(request.template, generate_pptx_code_drawn)` 僅處理**鍵值錯誤**
- 若 `ocean_gradient.pptx` 遺失，`pptx_generator_template.py` L274 會拋出 `FileNotFoundError`
- 若模板損毀，`Presentation()` 會拋出異常

**需求**：
根據您的需求「提供降級機制以防模板出問題」，應實作：

1. **預先驗證** (啟動時)：
   - 檢查 `templates/` 目錄下所有 .pptx 檔案
   - 驗證模板可被 `python-pptx` 正常開啟
   - 記錄可用模板列表

2. **即時降級** (生成時)：
   ```python
   try:
       pptx_bytes = generate_pptx_template(outline)
   except (FileNotFoundError, Exception) as e:
       logger.warning(f"模板生成失敗，降級到程式碼繪製: {e}")
       pptx_bytes = generate_pptx_code_drawn(outline)
   ```

3. **使用者通知**：
   - 在 `GenerateResponse` 中新增 `fallback_used: bool` 欄位
   - 前端顯示警告：「模板不可用，已使用經典繪製模式」

---

### 缺失 2: 進階設定 UI（方案 B）

**現況**：
- 模板選單與其他選項並列於同一列
- 無法收合、無說明文字、無進階提示

**需求**：
根據您選擇的「方案 B：進階設定」，應實作：

#### 2.1 摺疊面板設計

```html
<div class="options-row">
    <!-- 基本選項：投影片數量、風格、語言 -->
</div>

<!-- 進階設定（可摺疊） -->
<details class="advanced-settings">
    <summary>⚙️ 進階設定</summary>
    <div class="advanced-content">
        <div class="option-group">
            <label for="generationMode">生成模式</label>
            <select id="generationMode">
                <option value="template" selected>模板模式（推薦）</option>
                <option value="code_drawn">程式碼繪製模式</option>
            </select>
            <p class="option-hint">
                模板模式：使用預設專業模板，生成速度快、樣式統一<br>
                程式碼繪製：完全程式化繪製，靈活性高、可精確控制
            </p>
        </div>

        <div class="option-group" id="templateSelector">
            <label for="template">選擇模板</label>
            <select id="template">
                <!-- 動態載入可用模板 -->
            </select>
        </div>
    </div>
</details>
```

#### 2.2 互動邏輯

- 預設收合（進階使用者才展開）
- 選擇「程式碼繪製模式」時，隱藏「選擇模板」下拉選單
- 選擇「模板模式」時，顯示模板選單

---

### 缺失 3: 模板可用性檢查

**現況**：
- 前端硬編碼模板選項
- 無 API 端點查詢可用模板

**需求**：

#### 3.1 新增 API 端點

```python
@app.get("/api/templates")
async def list_templates():
    """列出所有可用的模板。"""
    templates = []
    template_dir = BASE_DIR / "templates"

    for template_file in template_dir.glob("*.pptx"):
        try:
            # 驗證模板可開啟
            test_prs = Presentation(str(template_file))
            templates.append({
                "id": template_file.stem,
                "name": template_file.stem.replace("_", " ").title(),
                "available": True
            })
        except Exception as e:
            logger.warning(f"模板 {template_file.name} 不可用: {e}")
            templates.append({
                "id": template_file.stem,
                "name": template_file.stem.replace("_", " ").title(),
                "available": False
            })

    # 始終保證 code_drawn 可用
    templates.insert(0, {
        "id": "code_drawn",
        "name": "經典繪製（程式碼繪製）",
        "available": True
    })

    return {"templates": templates}
```

#### 3.2 前端動態載入

```javascript
async function loadTemplates() {
    const response = await fetch('/api/templates');
    const data = await response.json();

    const templateSelect = els.template();
    templateSelect.innerHTML = '';

    data.templates.forEach(t => {
        const option = document.createElement('option');
        option.value = t.id;
        option.textContent = t.name;
        option.disabled = !t.available;
        templateSelect.appendChild(option);
    });
}

// 頁面載入時執行
document.addEventListener('DOMContentLoaded', loadTemplates);
```

---

## 📋 實作計畫

### 階段一：後端降級機制與驗證（優先）

**目標**: 確保系統在模板失效時仍能正常運作

#### 任務 1.1: 模板驗證工具函式

**檔案**: `txt2pptx/backend/template_validator.py`（新建）

```python
"""Template validation and health check utilities."""
from pathlib import Path
from pptx import Presentation
import logging

logger = logging.getLogger(__name__)

def validate_template(template_path: Path) -> bool:
    """驗證模板檔案是否可用。"""
    try:
        prs = Presentation(str(template_path))
        # 檢查是否有足夠的 layouts
        if len(prs.slide_layouts) < 9:
            logger.warning(f"{template_path.name}: layouts 數量不足 (需要 9 個)")
            return False
        return True
    except Exception as e:
        logger.error(f"{template_path.name} 驗證失敗: {e}")
        return False

def get_available_templates(templates_dir: Path) -> dict[str, Path]:
    """取得所有可用的模板路徑。"""
    available = {}
    for template_file in templates_dir.glob("*.pptx"):
        if validate_template(template_file):
            available[template_file.stem] = template_file
    return available
```

**預期結果**:
- ✅ 可重用的模板驗證邏輯
- ✅ 啟動時或 API 呼叫前檢查模板健康度

---

#### 任務 1.2: 主路由降級邏輯

**檔案**: `txt2pptx/backend/main.py`

**修改位置**: L44-76 `generate_presentation()` 函式

**修改內容**:

```python
@app.post("/api/generate", response_model=GenerateResponse)
async def generate_presentation(request: GenerateRequest):
    """Generate a PPTX presentation from text input."""
    try:
        # Step 1: Generate outline
        logger.info(f"Generating outline for {len(request.text)} chars, {request.num_slides} slides")
        outline = await generate_outline(request)
        logger.info(f"Outline generated: {outline.title}, {len(outline.slides)} slides")

        # Step 2: Generate PPTX with fallback
        fallback_used = False
        selected_template = request.template

        if request.template != "code_drawn":
            # 嘗試使用模板生成
            try:
                template_path = BASE_DIR / "templates" / f"{request.template}.pptx"
                if not template_path.exists():
                    raise FileNotFoundError(f"模板檔案不存在: {template_path}")

                pptx_bytes = generate_pptx_template(outline)
                logger.info(f"使用模板 {request.template} 生成成功")

            except Exception as e:
                logger.warning(f"模板生成失敗，降級到程式碼繪製: {e}", exc_info=True)
                pptx_bytes = generate_pptx_code_drawn(outline)
                fallback_used = True
                selected_template = "code_drawn"
        else:
            # 直接使用程式碼繪製
            pptx_bytes = generate_pptx_code_drawn(outline)

        # Step 3: Save file
        filename = f"{uuid.uuid4().hex[:8]}.pptx"
        filepath = GENERATED_DIR / filename
        filepath.write_bytes(pptx_bytes)
        logger.info(f"PPTX saved: {filepath} ({len(pptx_bytes)} bytes)")

        message = "簡報生成成功"
        if fallback_used:
            message += "（已自動切換為經典繪製模式）"

        return GenerateResponse(
            success=True,
            filename=filename,
            message=message,
            outline=outline,
            template_used=selected_template,      # 新增
            fallback_used=fallback_used,          # 新增
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成失敗: {str(e)}")
```

**修改**: `models.py` - `GenerateResponse`

```python
class GenerateResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    message: str
    outline: Optional[PresentationOutline] = None
    template_used: Optional[str] = None      # 新增：實際使用的模板
    fallback_used: bool = False              # 新增：是否發生降級
```

**預期結果**:
- ✅ 模板失效時自動降級到 code_drawn
- ✅ 使用者可得知降級發生
- ✅ 不中斷服務

---

#### 任務 1.3: 模板列表 API

**檔案**: `txt2pptx/backend/main.py`

**新增內容**:

```python
from .template_validator import get_available_templates

# 在 app 初始化時快取可用模板
AVAILABLE_TEMPLATES = {}

@app.on_event("startup")
async def startup_event():
    """應用啟動時驗證模板。"""
    global AVAILABLE_TEMPLATES
    templates_dir = BASE_DIR / "templates"
    AVAILABLE_TEMPLATES = get_available_templates(templates_dir)
    logger.info(f"可用模板: {list(AVAILABLE_TEMPLATES.keys())}")

@app.get("/api/templates")
async def list_templates():
    """列出所有可用的簡報模板。"""
    templates = [
        {
            "id": "code_drawn",
            "name": "經典繪製",
            "description": "完全程式化繪製，靈活性高",
            "available": True,
            "is_template": False
        }
    ]

    for template_id, template_path in AVAILABLE_TEMPLATES.items():
        templates.append({
            "id": template_id,
            "name": template_id.replace("_", " ").title(),
            "description": f"使用 {template_path.name} 模板",
            "available": True,
            "is_template": True
        })

    return {"templates": templates}
```

**預期結果**:
- ✅ 前端可動態取得可用模板列表
- ✅ 啟動時驗證模板健康度
- ✅ 避免前端硬編碼模板選項

---

### 階段二：前端進階設定 UI（次要）

**目標**: 將模板選擇改為摺疊式進階設定面板

#### 任務 2.1: HTML 結構調整

**檔案**: `txt2pptx/frontend/index.html`

**修改位置**: L42-79

**修改內容**:

```html
<!-- 基本選項（保持不變） -->
<div class="options-row">
    <div class="option-group">
        <label for="numSlides">投影片數量</label>
        <select id="numSlides">
            <!-- ... -->
        </select>
    </div>
    <div class="option-group">
        <label for="style">簡報風格</label>
        <select id="style">
            <!-- ... -->
        </select>
    </div>
    <div class="option-group">
        <label for="language">語言</label>
        <select id="language">
            <!-- ... -->
        </select>
    </div>
</div>

<!-- 進階設定（新增摺疊面板） -->
<details class="advanced-settings">
    <summary>
        <span class="advanced-icon">⚙️</span>
        進階設定
        <span class="collapse-hint">(選填)</span>
    </summary>
    <div class="advanced-content">
        <div class="option-group">
            <label for="generationMode">生成模式</label>
            <select id="generationMode">
                <option value="template" selected>模板模式（推薦）</option>
                <option value="code_drawn">程式碼繪製模式</option>
            </select>
            <p class="option-hint">
                📄 <strong>模板模式</strong>: 使用預設專業模板，生成速度快、樣式統一<br>
                🖌️ <strong>程式碼繪製</strong>: 完全程式化繪製，靈活性高、可精確控制
            </p>
        </div>

        <div class="option-group" id="templateSelector">
            <label for="template">選擇模板</label>
            <select id="template">
                <option value="ocean_gradient" selected>Ocean Gradient</option>
                <!-- 動態載入其他模板 -->
            </select>
        </div>
    </div>
</details>
```

---

#### 任務 2.2: CSS 樣式

**檔案**: `txt2pptx/frontend/style.css`

**新增內容**:

```css
/* 進階設定摺疊面板 */
.advanced-settings {
    margin-top: 1rem;
    padding: 1rem;
    background: #F8FAFC;
    border-radius: 8px;
    border: 1px solid #E2E8F0;
}

.advanced-settings summary {
    cursor: pointer;
    font-weight: 600;
    color: #1E293B;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    user-select: none;
}

.advanced-settings summary:hover {
    color: #065A82;
}

.advanced-icon {
    font-size: 1.1em;
}

.collapse-hint {
    font-size: 0.85em;
    color: #94A3B8;
    font-weight: 400;
    margin-left: auto;
}

.advanced-content {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #E2E8F0;
}

.option-hint {
    font-size: 0.85rem;
    color: #64748B;
    margin-top: 0.5rem;
    line-height: 1.6;
}

/* 隱藏狀態（當選擇程式碼繪製時隱藏模板選單） */
.option-group.hidden {
    display: none;
}
```

---

#### 任務 2.3: JavaScript 邏輯

**檔案**: `txt2pptx/frontend/app.js`

**新增內容**:

```javascript
// ── 頁面載入時動態載入模板列表 ──
document.addEventListener('DOMContentLoaded', async () => {
    await loadAvailableTemplates();
    setupAdvancedSettings();
});

// 動態載入可用模板
async function loadAvailableTemplates() {
    try {
        const response = await fetch('/api/templates');
        const data = await response.json();

        const templateSelect = els.template();
        templateSelect.innerHTML = '';

        data.templates
            .filter(t => t.is_template)  // 只顯示真實模板
            .forEach(t => {
                const option = document.createElement('option');
                option.value = t.id;
                option.textContent = t.name;
                option.disabled = !t.available;
                if (t.id === 'ocean_gradient') {
                    option.selected = true;
                }
                templateSelect.appendChild(option);
            });

    } catch (error) {
        console.error('載入模板列表失敗:', error);
    }
}

// 進階設定互動邏輯
function setupAdvancedSettings() {
    const modeSelect = document.getElementById('generationMode');
    const templateSelector = document.getElementById('templateSelector');

    modeSelect.addEventListener('change', (e) => {
        if (e.target.value === 'code_drawn') {
            templateSelector.classList.add('hidden');
            els.template().value = 'code_drawn';
        } else {
            templateSelector.classList.remove('hidden');
            // 恢復為第一個可用模板
            if (els.template().value === 'code_drawn') {
                els.template().selectedIndex = 0;
            }
        }
    });
}

// 修改 generatePresentation() 函式
async function generatePresentation() {
    // ... (前面不變)

    // 根據生成模式決定 template 參數
    const mode = document.getElementById('generationMode').value;
    const template = mode === 'code_drawn' ? 'code_drawn' : els.template().value;

    const request = {
        text: text,
        num_slides: parseInt(els.numSlides().value),
        style: els.style().value,
        language: els.language().value,
        template: template,
    };

    // ... (後面不變)
}
```

---

#### 任務 2.4: 降級提示 UI

**檔案**: `txt2pptx/frontend/app.js`

**修改**: `showResult()` 函式

```javascript
function showResult(data) {
    // ... (現有邏輯)

    // 若發生降級，顯示警告訊息
    if (data.fallback_used) {
        const warningDiv = document.createElement('div');
        warningDiv.className = 'fallback-warning';
        warningDiv.innerHTML = `
            ⚠️ <strong>注意</strong>:
            原選模板不可用，已自動切換為經典繪製模式。
        `;
        els.resultSection().querySelector('.result-card').prepend(warningDiv);
    }

    // ... (現有邏輯)
}
```

**檔案**: `txt2pptx/frontend/style.css`

```css
.fallback-warning {
    background: #FEF3C7;
    border-left: 4px solid #F59E0B;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    border-radius: 4px;
    font-size: 0.9rem;
    color: #92400E;
}
```

---

## 📊 實作優先級建議

| 優先級 | 階段 | 任務 | 理由 | 預估時間 |
|--------|------|------|------|----------|
| 🔴 P0 | 階段一 | 任務 1.2 - 降級邏輯 | 確保系統可靠性，防止模板失效導致服務中斷 | 30 min |
| 🔴 P0 | 階段一 | 任務 1.1 - 模板驗證 | 提供可重用的驗證工具，支援後續所有任務 | 20 min |
| 🟡 P1 | 階段一 | 任務 1.3 - 模板列表 API | 動態取得模板，避免前端硬編碼 | 15 min |
| 🟡 P1 | 階段二 | 任務 2.4 - 降級提示 | 使用者體驗改善，讓使用者知道發生降級 | 10 min |
| 🟢 P2 | 階段二 | 任務 2.1-2.3 - 進階設定 UI | UI/UX 優化，符合「方案 B」需求 | 45 min |

**總預估時間**: 約 2 小時

---

## 🎯 成功驗收標準

### 階段一驗收標準

1. ✅ **降級機制正常**:
   - 刪除 `ocean_gradient.pptx` → 生成仍成功 → 使用 `code_drawn`
   - 損毀模板檔案 → 生成仍成功 → 使用 `code_drawn`
   - API 回應包含 `fallback_used: true` 和正確的 `template_used` 值

2. ✅ **模板驗證生效**:
   - 啟動時 log 顯示可用模板列表
   - `/api/templates` 回傳正確的模板資訊
   - 不可用模板標記為 `available: false`

3. ✅ **錯誤處理完善**:
   - 模板載入失敗 → 降級且記錄 warning log
   - 未捕獲異常 → 回傳 HTTP 500 且記錄 error log

### 階段二驗收標準

1. ✅ **UI 符合方案 B**:
   - 基本選項（投影片數量、風格、語言）維持可見
   - 進階設定預設摺疊
   - 展開進階設定可看到「生成模式」和「選擇模板」

2. ✅ **互動邏輯正確**:
   - 選擇「程式碼繪製模式」→ 隱藏「選擇模板」
   - 選擇「模板模式」→ 顯示「選擇模板」
   - 生成請求正確傳遞 `template` 參數

3. ✅ **降級提示顯示**:
   - 降級發生時，結果頁顯示黃色警告訊息
   - 訊息清楚說明已切換為經典繪製

---

## 🔍 技術債務與後續改進

### 技術債務

1. **models.py 缺乏型別約束**:
   - `template: str` 應改為 `Literal["code_drawn", "ocean_gradient", ...]`
   - 或使用 `TemplateType(Enum)` 並在 startup 時動態註冊可用模板

2. **圖片插入未實作**:
   - 模板支援 `PH_PICTURE` (idx=10)，但程式碼未使用
   - 未來可支援 `image_prompt` → AI 生成圖片 → 插入 placeholder

3. **無單元測試**:
   - `pptx_generator.py` 和 `pptx_generator_template.py` 缺少測試
   - 降級邏輯需要整合測試驗證

### 後續改進方向

1. **多模板支援**:
   - 新增企業模板、學術模板、極簡模板等
   - 允許使用者上傳自己的 .pptx 模板

2. **效能優化**:
   - 快取已驗證的模板 Presentation 物件（避免每次重新載入）
   - 使用非同步 I/O 減少模板驗證時間

3. **健康檢查端點**:
   ```python
   @app.get("/api/health")
   async def health():
       return {
           "status": "ok",
           "version": "0.1.0",
           "available_templates": list(AVAILABLE_TEMPLATES.keys()),
           "template_health": {
               t: validate_template(p)
               for t, p in AVAILABLE_TEMPLATES.items()
           }
       }
   ```

---

## 📚 附錄：技術決策紀錄

### 決策 1: 為何使用 `GENERATORS.get()` 而非 if-else？

**原因**: 擴充性

- 新增模板只需在 dict 加入新項目，不需修改 if-else 邏輯
- 符合 Open-Closed Principle (OCP)

### 決策 2: 為何降級到 code_drawn 而非顯示錯誤？

**原因**: 可用性優先

- 使用者的主要需求是「生成簡報」，不是「使用特定模板」
- 降級保證服務可用性，優於直接失敗
- 透過 `fallback_used` 通知使用者，保持透明度

### 決策 3: 為何不在 Pydantic 層驗證模板？

**原因**: 動態性

- 可用模板列表在啟動時才確定（檔案系統狀態）
- Pydantic validator 無法存取應用狀態（如 `AVAILABLE_TEMPLATES`）
- 驗證邏輯放在 API handler，可存取快取的模板列表

---

## ✅ 結論

**現況評估**:
- 雙引擎架構已實作 90%
- 後端邏輯完整，前端 UI 基礎已建立
- 缺少降級機制和進階設定 UI

**實作建議**:
1. **優先實作降級機制（任務 1.1, 1.2）** — 確保系統可靠性
2. **次要實作模板 API 與降級提示（任務 1.3, 2.4）** — 改善使用者體驗
3. **最後實作進階設定 UI（任務 2.1-2.3）** — 符合方案 B 需求

**總時程**: 約 2 小時可完成所有改進

---

**報告完成日期**: 2026-02-17
**分析人員**: Claude (Sonnet 4.5)
