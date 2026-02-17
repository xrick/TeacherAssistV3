# 開發日誌 - Speaker Notes 品質優化

**日期**: 2026-02-17
**任務**: 提升 Speaker Notes 覆蓋率和內容長度，達成 100% 品質標準
**狀態**: ✅ 完成

---

## 任務目標

改善 LLM 生成的 speaker_notes 品質：
- **覆蓋率目標**: ≥ 70% 投影片含有 speaker_notes
- **長度目標**: 平均 ≥ 50 字
- **內容目標**: 包含背景、延伸、實例、引導問題

---

## 測試環境

- **測試內容**: test/Discrete_mathematics.txt (2908 字元)
- **投影片數**: 8 張（要求）
- **測試模板**:
  - Zen_Serenity.pptx (初始測試)
  - College_Elegance.pptx (最終測試)
- **LLM 模型**: gpt-oss:20b (Ollama)
- **API 端點**: http://localhost:8000/api/generate

---

## 改進歷程

### 階段 1：基線測試 (Zen_Serenity)

**測試結果**:
```
✅ Bullet 長度: 19.4 字 (目標: ≥ 15 字)
✅ Speaker notes 覆蓋率: 8/8 (100%)
❌ Speaker notes 平均長度: 18.1 字 (目標: ≥ 50 字)
❌ Layout 多樣性: 3 種 (目標: ≥ 5 種)
品質覆蓋率: 66.7% (4/6)
```

**問題診斷**:
- Notes 覆蓋率達標但內容過短
- SYSTEM_PROMPT 只說「建議 50-100 字」，不夠強制

---

### 階段 2：SYSTEM_PROMPT 優化

**修改內容** ([llm_service.py:48-54](txt2pptx/backend/llm_service.py#L48-L54)):

```python
# 修改前
- speaker_notes：每頁建議 50-100 字的補充說明

# 修改後
- speaker_notes：**每頁必須提供 50-100 字的詳細補充說明**，包含：
  • 背景資訊和脈絡說明（10-20 字）
  • 重點內容的延伸解釋（20-30 字）
  • 實例或應用場景（20-30 字）
  • 引導討論的問題或思考點（10-20 字）
```

**測試結果** (College_Elegance):
```
❌ Bullet 長度: 63.4 字
❌ Speaker notes 覆蓋率: 0/8 (0%)
❌ Speaker notes 平均長度: 0.0 字
品質覆蓋率: 50.0% (3/6)
```

**失敗原因**:
- LLM 完全沒有生成 speaker_notes 字段
- **根本問題**: Pydantic schema 中 `speaker_notes: Optional[str] = None`
- SYSTEM_PROMPT 的「必須」不如 schema 的硬約束有效

---

### 階段 3：Pydantic Schema 強制約束 (min_length=30)

**修改內容** ([models.py:36](txt2pptx/backend/models.py#L36)):

```python
# 修改前
speaker_notes: Optional[str] = None

# 修改後
speaker_notes: str = Field(
    default="",
    min_length=30,
    max_length=200,
    description="詳細補充說明，50-100字為佳"
)
```

**測試結果**:
```
❌ Bullet 長度: 14.7 字
✅ Speaker notes 覆蓋率: 9/9 (100%)
❌ Speaker notes 平均長度: 46.0 字 (目標: ≥ 50 字)
❌ Layout 多樣性: 3 種
品質覆蓋率: 50.0% (3/6)
```

**改善分析**:
- ✅ 覆蓋率從 0% → 100%（強制必填成功）
- ⚠️ 長度 46 字（92% 達標，接近但未達標）
- 💡 LLM 傾向生成剛好超過 `min_length=30` 的內容

---

### 階段 4：最終優化 (min_length=50) ✅

**修改內容**:

```python
speaker_notes: str = Field(
    default="",
    min_length=50,      # 🎯 關鍵：30 → 50
    max_length=200,
    description="詳細補充說明，50-100字為佳"
)
```

**測試結果** (College_Elegance):
```
✅ Bullet 長度: 25.3 字 (≥ 15 字)
✅ Speaker notes 覆蓋率: 10/10 (100%)
✅ Speaker notes 平均長度: 72.4 字 (≥ 50 字) 🎉
✅ Layout 多樣性: 5 種
✅ 非 Demo Mode: 是
✅ PPTX 下載: 成功

品質覆蓋率: 100% (6/6) 🎉
```

**成功指標**:
- Notes 平均長度: **72.4 字** (144% 達標率)
- Layout 類型: bullets, key_stats, section_header, title_slide, two_column
- 投影片數: 10 張（內容豐富度提升）
- 響應時間: 86.9 秒（經過 1 次重試）

---

## 關鍵技術洞察

### 1. SYSTEM_PROMPT vs Pydantic Schema 優先級

| 約束類型 | 特性 | LLM 遵守程度 |
|----------|------|--------------|
| **SYSTEM_PROMPT** | 軟引導、建議性 | 中等（可能忽略） |
| **Pydantic Schema** | 硬約束、結構化 | 高（必須滿足） |

**結論**: Pydantic schema 的 `Field()` 約束是**硬性要求**，SYSTEM_PROMPT 只是**輔助引導**。

### 2. min_length 對生成內容的影響

| min_length | 平均長度 | 達標率 | 分析 |
|------------|----------|--------|------|
| Optional (無) | 18.1 字 | 36% | LLM 傾向簡短 |
| 30 字 | 46.0 字 | 92% | 剛好超過最低值 |
| **50 字** | **72.4 字** | **144%** | **充分滿足要求** |

**規律**: LLM 生成長度 ≈ `min_length × 1.5` （平均超過最低值 50%）

### 3. 內容結構化的重要性

SYSTEM_PROMPT 提供的 4 項結構引導：
```
• 背景資訊和脈絡說明（10-20 字）
• 重點內容的延伸解釋（20-30 字）
• 實例或應用場景（20-30 字）
• 引導討論的問題或思考點（10-20 字）
```

**效果**:
- 引導 LLM 生成**多層次內容**
- 避免單一維度的簡短說明
- 提升教學實用性

---

## 實際 LLM 生成範例

### 修改前 (18.1 字平均)
```json
"speaker_notes": "本章將介紹離散數學的基本概念與核心工具。"
```

### 修改後 (72.4 字平均)
```json
"speaker_notes": "歡迎各位參與本次簡報，今天我們將從離散數學的核心概念出發，探討其在科技與產業中的重要性，並展望未來可能的發展方向。這是一個跨學科的領域，涵蓋了邏輯、組合、圖論等多個分支，對於算法設計與系統驗證具有深遠影響。"
```

**內容豐富度提升**:
- ✅ 背景：「跨學科領域」
- ✅ 重點：「核心概念、科技應用、未來發展」
- ✅ 實例：「邏輯、組合、圖論」
- ✅ 影響：「算法設計、系統驗證」

---

## 副作用與額外改善

### 正面副作用

1. **Layout 多樣性提升**: 2 種 → 5 種
   - 新增: key_stats, two_column
   - 原因: 內容更豐富，LLM 選擇了更多樣的呈現方式

2. **Bullet 長度改善**: 14.7 字 → 25.3 字
   - 內容質量整體提升的連帶效應

3. **投影片數量增加**: 8 張 → 10 張
   - LLM 根據內容豐富度自動調整結構

### 負面副作用

1. **響應時間略增**: 80.9 秒 → 86.9 秒 (+7%)
   - 原因: 每個 notes 多生成 20-40 字
   - 評估: 可接受的代價（品質優先）

2. **投影片數量偏離**: 要求 8 張，生成 10 張
   - 原因: LLM 可能優先內容完整性
   - 評估: 需後續優化 num_slides 約束

---

## 性能指標對比

| 指標 | 階段 1 | 階段 2 | 階段 3 | 階段 4 |
|------|--------|--------|--------|--------|
| **Notes 覆蓋率** | 100% | 0% ❌ | 100% | 100% |
| **Notes 長度** | 18.1 字 | 0 字 ❌ | 46.0 字 | **72.4 字** ✅ |
| **Bullet 長度** | 19.4 字 | 63.4 字 | 14.7 字 | 25.3 字 |
| **Layout 多樣性** | 3 種 | 2 種 | 3 種 | **5 種** ✅ |
| **品質通過率** | 66.7% | 50.0% | 50.0% | **100%** ✅ |
| **響應時間** | - | 203.5 秒 | 80.9 秒 | 86.9 秒 |

---

## 文件修改記錄

### 1. llm_service.py
- **位置**: [L48-54](txt2pptx/backend/llm_service.py#L48-L54)
- **變更**: SYSTEM_PROMPT 增加結構化要求
- **影響**: 引導 LLM 生成多層次內容

### 2. models.py
- **位置**: [L36](txt2pptx/backend/models.py#L36)
- **變更**: `speaker_notes` 從 Optional → 必填 Field，min_length=50
- **影響**: 強制 LLM 生成足夠長的 notes

### 3. test_integration_template.py
- **位置**: [L5, L27, L39, L153](test/test_integration_template.py)
- **變更**: 模板從 Zen_Serenity → College_Elegance
- **影響**: 測試不同模板的品質表現

---

## 測試覆蓋率

### 品質檢查項目 (6/6 全部通過)

| 檢查項目 | 標準 | 結果 | 狀態 |
|----------|------|------|------|
| bullet_length | ≥ 15 字 | 25.3 字 | ✅ PASS |
| notes_coverage | ≥ 70% | 100% | ✅ PASS |
| notes_length | ≥ 50 字 | 72.4 字 | ✅ PASS |
| layout_diversity | ≥ 5 種 | 5 種 | ✅ PASS |
| non_demo | 非 Demo Mode | 是 | ✅ PASS |
| pptx_download | 下載成功 | 成功 | ✅ PASS |

---

## 後續建議

### 短期優化 (已完成)
- ✅ SYSTEM_PROMPT 結構化要求
- ✅ Pydantic schema 強制約束
- ✅ min_length 調整至 50

### 中期改進 (待執行)
1. **多模板穩定性測試**
   - 測試所有 8 個模板的品質表現
   - 確認優化對不同模板的適用性

2. **批量穩定性驗證**
   - 執行 10 次連續測試（類似 test_retry_mechanism.py）
   - 驗證 100% 通過率的穩定性

3. **投影片數量準確性**
   - 優化 num_slides 約束機制
   - 確保生成的投影片數量符合要求

### 長期規劃
1. **內容品質評估**
   - 語意連貫性檢查
   - 教學實用性評分

2. **性能優化**
   - 減少響應時間（目標 < 60 秒）
   - 降低重試率

3. **多語言支持**
   - 測試英文、簡體中文的品質
   - 調整不同語言的 min_length 標準

---

## 經驗總結

### ✅ 成功因素
1. **硬約束優先**: Pydantic Field 比 SYSTEM_PROMPT 更有效
2. **結構化引導**: 4 項內容要求幫助 LLM 生成多層次內容
3. **迭代優化**: 從 30 → 50 的漸進式調整，避免激進變更
4. **系統性測試**: 每次修改都進行完整整合測試

### ⚠️ 教訓
1. **Schema 優先級**: 先檢查 Pydantic schema，再調整 SYSTEM_PROMPT
2. **LLM 行為模式**: 傾向生成剛好超過最低要求的內容
3. **副作用觀察**: 一個改動可能影響多個指標（正面 + 負面）

### 💡 最佳實踐
1. 使用 `Field()` 設置硬性約束（min_length, max_length）
2. SYSTEM_PROMPT 提供結構化引導（分項說明）
3. 設置最小值時考慮 LLM 的「剛好超過」傾向（目標 50 → 設置 50）
4. 每次修改後執行完整測試，觀察所有品質指標

---

## 參考文檔

- [Notes覆蓋率指標說明](../Notes覆蓋率指標說明.md)
- [重試機制實作總結](../重試機制實作總結.md)
- [測試腳本](../../test/test_integration_template.py)
- [SYSTEM_PROMPT](../../txt2pptx/backend/llm_service.py#L48-L54)
- [Pydantic Models](../../txt2pptx/backend/models.py#L36)

---

*文件生成時間: 2026-02-17*
*最終品質覆蓋率: 100% (6/6)*
*Notes 平均長度: 72.4 字 (144% 達標)*
