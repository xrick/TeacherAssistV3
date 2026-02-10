這是一個為您的專案 **TeacherAssist (TXT2PPTX)** 撰寫的專業 `README.md` 文件草案。此文件根據您提供的程式碼結構（FastAPI 後端、Vanilla JS 前端、python-pptx 渲染）進行編寫，旨在展現專業感並為未來擴充預留空間。

---

# TeacherAssist: AI 智慧簡報生成系統 (TXT2PPTX)

TeacherAssist 是一款基於 **RAG (Retrieval-Augmented Generation)** 概念開發的輕量級 Web 應用程式。使用者只需輸入簡短的文字描述，系統即可透過大語言模型（LLM）進行內容擴充與邏輯分頁，最終自動渲染並輸出專業的 PowerPoint (.pptx) 簡報文件。

## 核心亮點

* **全自動工作流**：從「純文字輸入」到「結構化大綱」再到「PPTX 渲染」的一鍵式體驗。
* **多樣化佈局**：內建 9 種專業投影片佈局（封面、章節頁、雙欄對比、數據分析等），避免內容單調。
* **LLM 驅動**：預設對接 Ollama (Local LLM) 進行離線運算，並支持 Anthropic Claude API 以獲得更高質量的擴充內容。
* **專業視覺規範**：內建「Ocean Gradient」主題色系，自動處理字體、對齊、圖標預留位與頁碼渲染。

## 系統架構

專案採用前後端分離架構，流程如下：

1. **Frontend**：Vanilla HTML/CSS/JS 提供即時進度模擬與大綱預覽。
2. **Backend (FastAPI)**：處理 API 請求並協調整個生成 pipeline。
3. **LLM Service**：將使用者輸入轉化為符合 `PresentationOutline` Pydantic 模型之 JSON 結構。
4. **PPTX Generator**：基於 `python-pptx` 進行高精度的座標定位與圖形渲染。

## 快速上手

### 環境需求

* Python 3.11+
* Ollama (如需使用本地 LLM)

### 安裝步驟

1. 克隆專案並進入目錄。
2. 建立虛擬環境並安裝依賴：
```bash
python -m venv pptxenv
source pptxenv/bin/activate
pip install fastapi uvicorn python-pptx pydantic httpx

```



### 啟動服務

使用內建腳本啟動：

```bash
cd txt2pptx
bash start.sh

```

訪問 `http://localhost:8000` 即可開始使用。

## 未來擴充應用路徑 (Roadmap)

本專案之原型已打下良好基礎，未來可往以下專業方向擴充：

1. **真正的 RAG 整合**：目前僅限於文字輸入擴充，未來可引入文件檢索功能，讓簡報內容基於企業內部 PDF 或知識庫生成。
2. **AI 圖像自動生成**：串接 Stable Diffusion 或 DALL-E 3，根據 `image_prompt` 欄位自動生成並填充簡報圖片。
3. **VLM 佈局審查**：引入多模態模型（如 Qwen2-VL）對渲染後的簡報進行「視覺美感審查」，實現自動排版修正。
4. **多主題模板引擎**：支持自定義 .pptx 模板上傳，讓系統在使用者指定的企業標誌與視覺識別系統 (VI) 下運行。

## 開放 API

* `POST /api/generate`：提交生成任務。
* `GET /api/download/{filename}`：下載成品。
* `GET /api/health`：系統狀態檢查。

---

*本專案為 TeacherAssist 系列之 V3 版本 prototype，旨在探索「文字即簡報」的高效教學輔助場景。*
