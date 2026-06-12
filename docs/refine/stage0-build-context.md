# 階段 0：Context 建立確認清單

> 生成時間：2026-06-12  
> 狀態：✅ 已確認（含補充修正）

---

## 專案演進背景（重要補充）

本專案為 **第二版本（V2）**，不包含在 git log 中的 V1 已使用 LangChain 內建功能（如 DocumentLoader、TextSplitter、RetrievalQA chain 等）完成初始實作。

**V2 的核心設計決策**：自行撰寫函式取代 LangChain 的多個抽象層，主要包含：
- **AI-assisted chunking**（`utils/ingest.py`）：以 LLM 語意分塊取代 LangChain `RecursiveCharacterTextSplitter`，讓每個 chunk 附帶 headline + summary + original_text 三層結構
- **Dual-query retrieval + LLM reranking**（`utils/answer.py`）：取代 LangChain 的單一 retriever，加入 query rewriting、雙查詢合併、LLM reranker
- **直接操作 ChromaDB Client**：取代 `langchain-chroma` 封裝，獲得更細粒度的向量庫控制

**V2 的技術意圖**：展現「理解底層機制、能跳出框架抽象自行實作」的工程能力，這與 JD1 TrendLife 強調的「追根究底的技術好奇心」直接對應。

**未來優化方向（供後續階段參考）**：
若需補強功能（如 Agentic workflow、multi-step reasoning、記憶機制），優先考慮以 **LangChain + LangGraph** 實現，理由：
  - LangGraph 的 StateGraph 天然適合補強 multi-turn context 管理與 Human-in-the-loop
  - LangChain 的 LCEL 可以讓 pipeline 更具可組合性與可測試性
  - 保持與 JD2 ITRI（「熟悉 LangChain」）和 JD3 Appier（「工作流編排」）的技術對齊

---

## 專案基本資訊

- **主要語言與版本**：Python 3.12.12（由 `.python-version` 指定）
- **技術棧（框架、主要套件）**：
  - **RAG 核心**：LangChain（langchain, langchain-core, langchain-openai, langchain-chroma, langchain-community）
  - **向量資料庫**：ChromaDB（PersistentClient，本地持久化）
  - **LLM 統一介面**：LiteLLM（支援 OpenAI、Groq 等多家 provider 切換）
  - **Embedding**：OpenAI `text-embedding-3-large`
  - **UI 框架**：Gradio 5.x（兩個 Gradio 介面：聊天 & 評估 dashboard）
  - **資料驗證**：Pydantic v2（BaseModel 廣泛使用）
  - **重試機制**：Tenacity（`retry` + `wait_exponential`）
  - **並行處理**：`multiprocessing.Pool`（文件 ingestion 階段）
  - **套件管理**：uv（`pyproject.toml` + `uv.lock`）
- **專案核心功能（簡要描述）**：
  企業知識庫 RAG 問答系統，以虛構保險公司「Insurellm」為情境。
  Pipeline 包含：
  1. **Ingestion**：LLM 輔助語意分塊（AI chunking via GPT-4.1-nano） → OpenAI Embedding → ChromaDB 向量存儲
  2. **Retrieval**：Query rewriting + Dual-query 策略 + LLM-based re-ranking（Top-K 先取 20，rerank 後取 10）
  3. **Generation**：RAG 生成答案（透過 LiteLLM 路由至 Groq/OpenAI）
  4. **Evaluation**：自動化評估框架，涵蓋 Retrieval（MRR、nDCG、Keyword Coverage）與 Answer（LLM-as-a-judge，三維評分）

- **測試覆蓋情況**：**部分**
  - 有：`evaluation/tests.jsonl`（測試資料集）、`evaluation/eval.py`（評估邏輯）、`evaluation/test.py`（資料模型）
  - 無：標準 pytest 單元測試（無 `tests/` 目錄、無 `test_*.py` 檔案）
  - 評估框架屬於 End-to-End 功能評估，不是傳統單元測試

---

## 已讀取的檔案清單

| # | 路徑 | 說明 |
|---|------|------|
| 1 | `.python-version` | Python 版本 3.12.12 |
| 2 | `.gitignore` | 版本控制忽略規則 |
| 3 | `pyproject.toml` | 專案設定與完整依賴清單 |
| 4 | `app.py` | 主應用程式進入點（Gradio Chat UI） |
| 5 | `evaluator.py` | 評估 Dashboard 進入點（Gradio Eval UI） |
| 6 | `utils/answer.py` | RAG 核心邏輯（retrieval + rerank + generation） |
| 7 | `utils/ingest.py` | 文件 ingestion pipeline |
| 8 | `evaluation/eval.py` | 評估框架核心邏輯 |
| 9 | `evaluation/test.py` | 測試資料模型與載入器 |
| 10 | `docs/20260611-ai-engineer-job-describition-examples.md` | 目標職缺 JD |
| 11 | `docs/portfolio-polish-workflow.md` | 工作流程文件 |

---

## 尚未讀取但可能重要的檔案

| 路徑 | 為何重要 |
|------|----------|
| `evaluation/tests.jsonl` | 測試資料集（38KB）。了解測試問題類型（direct_fact / spanning / temporal）、資料規模、問題分布，對評估框架的完整度判斷至關重要 |
| `knowledge-base/company/*.md` | 實際知識庫內容，影響 chunking 策略評估（目前有 4 個子目錄：company、contracts、employees、products） |
| `knowledge-base/contracts/*.md` | 同上 |
| `knowledge-base/employees/*.md` | 同上 |
| `knowledge-base/products/*.md` | 同上 |
| `requirements.txt` | 可能與 `pyproject.toml` 有版本衝突，影響環境重現性 |
| `.env.example`（不存在） | **缺失**：專案沒有 `.env.example`，面試官 clone 後無法知道需要哪些 API key，這是一個潛在問題 |
| `README.md`（不存在） | **缺失**：沒有 README，這是求職 portfolio 最嚴重的問題之一 |

---

## 目標職缺 JD

**確認已收到**：`docs/20260611-ai-engineer-job-describition-examples.md`（共 3 份 JD）

### 與本專案最相關的 3 個技術要求

以下依綜合 3 份 JD 的重疊程度排列：

1. **LLM / RAG 系統開發能力**（來自 JD1 TrendLife & JD2 ITRI & JD3 Appier）
   > JD2：「熟悉 LangChain 或 LlamaIndex」、「數據研發：資料處理與評估」  
   > JD3：「LLM/Agent 開發興趣或經驗」  
   > ✅ 本專案完整實現：V1 以 LangChain 完成基礎，V2 自行撰寫函式取代 LangChain 多個抽象層（AI chunking + dual-query retrieval + LLM reranking），展現底層理解能力

2. **系統化評估框架 / Benchmark evaluation**（來自 JD3 Appier 加分條件，也是最差異化競爭點）
   > JD3（必備）：「基準測試評估（Benchmark evaluation）有濃厚興趣」  
   > JD3（加分）：「Harness 測試工程、評估/測試工作流」  
   > JD3（加分）：「強烈重視量化指標與系統化評估」  
   > ✅ 本專案已有：MRR、nDCG、Keyword Coverage + LLM-as-a-judge（三維評分）評估框架

3. **快速 PoC、敏捷疊代思維**（來自 JD1 TrendLife）
   > JD1：「能在沒有完整需求規格的情況下，根據模糊問題進行假設並著手開發」  
   > JD1：「傾向先快速做小原型來驗證與疊代」  
   > ✅ 本專案 commit 歷史顯示：從 Udemy 課程 codebase 快速演進，自行加入評估框架

---

*資訊已確認（含使用者補充），可進入階段 1。*
