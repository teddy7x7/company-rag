# 階段 1：大健檢與分級判定

> 生成時間：2026-06-12  
> 前置依賴：`docs/refine/stage0-build-context.md` ✅  
> 分析角色：資深軟體架構師 × AI 系統專家

---

## 1. 核心業務問題

### 這個系統解決了誰的什麼痛點？

**對象**：企業內部知識工作者（業務、HR、客服、管理層），以虛構保險公司 Insurellm 為情境載體。

**痛點**：企業文件通常散落在多份 Markdown / PDF / Word 中（合約、員工手冊、產品說明），人工查找耗時且容易遺漏關鍵細節。傳統關鍵字搜尋只能找「包含這個詞」的文件，無法理解語意意圖、無法跨文件整合答案。

**解法**：以 RAG（Retrieval-Augmented Generation）架構，讓使用者用自然語言提問，系統自動：
1. 理解問題語意、改寫查詢
2. 跨知識庫語意檢索
3. 重新排序最相關片段
4. 以 LLM 生成精準且可溯源的回答

**技術意圖**（V2 設計選擇）：不使用 LangChain 黑盒抽象，而是自行實作每個 pipeline 步驟，展現對 RAG 底層機制的深度理解。

---

## 2. 關鍵架構決策

### 決策 1：AI-assisted Semantic Chunking

**[決策點]** 捨棄 LangChain `RecursiveCharacterTextSplitter` 的固定長度分塊。

- **做法**：呼叫 `gpt-4.1-nano` 將每份文件切割成語意完整的 chunk，每個 chunk 強制包含三層結構：`headline`（可供檢索的標題）、`summary`（語意摘要）、`original_text`（原始文字）
- **優點**：chunk 本身帶有 LLM 生成的語意標籤，提升向量化品質；headline + summary 作為 dense retrieval 的「語意錨點」
- **代價**：ingestion 成本比固定分塊高（需要 LLM API 呼叫），且 chunk 邊界由 LLM 決定，難以精確預測
- **[假設]** 目前 overlap 策略（約 25%）是否與 chunk 語意邊界配合良好，尚未有量化驗證

### 決策 2：Dual-Query Retrieval（原始 + 改寫查詢合併）

**[決策點]** 單一 query 向量化後直接查詢，容易因使用者用語與文件用語不同而錯失相關內容。

- **做法**：`rewrite_query()` 以 LLM 生成一個「更適合知識庫查詢」的精鍊問題 → 分別對 original query 與 rewritten query 各取 Top-20 → `merge_chunks()` 合併去重 → 最終 reranker 選出 Top-10
- **優點**：提高 recall，尤其對模糊或口語化的問題效果顯著
- **代價**：每次問答觸發 3 次 LLM 呼叫（rewrite + 2 個 embed 查詢），延遲較高

### 決策 3：LLM-based Reranker 替代向量相似度排序

**[決策點]** 向量相似度只衡量語意距離，不衡量「對這個問題是否真的有用」。

- **做法**：將合併後的候選 chunk 全部送給 LLM，輸出 `RankOrder`（Pydantic structured output），按問題相關性重新排列
- **優點**：排序準確度明顯優於純向量相似度
- **[挑戰]** 當 chunk 數量多時，所有 chunk 全塞進一個 prompt，token 成本與 context window 限制需要注意

### 決策 4：LiteLLM 統一 Provider 介面

**[決策點]** 硬編碼特定 SDK（如 openai SDK）會讓模型切換成本極高。

- **做法**：所有 LLM 呼叫統一走 `litellm.completion()`，model 名稱以字串前綴區分 provider（如 `openai/...`、`groq/...`）
- **優點**：更換模型只需改一個常數；支援 fallback、retry、logging 等進階功能
- **現狀問題**：目前 `ingest.py` 與 `answer.py` / `eval.py` 的 MODEL 常數是獨立的，沒有集中管理（見優化建議）

### 決策 5：Pydantic Structured Output 保證可解析性

**[決策點]** 直接解析 LLM 自由文字格式容易因格式不穩定而崩潰。

- **做法**：所有結構化 LLM 回應（`Chunks`、`RankOrder`、`AnswerEval`、`RetrievalEval`）均定義 Pydantic BaseModel，透過 LiteLLM `response_format` 參數強制 JSON schema 輸出
- **優點**：解析穩定、有欄位驗證、IDE 有型別提示

### 決策 6：Tenacity Retry 應對 API Rate Limit

- **做法**：`@retry(wait=wait_exponential(multiplier=1, min=10, max=240))` 裝飾在所有 LLM 呼叫函式上
- **評估**：`min=10` 秒的最小等待時間對互動式 chat 體驗影響極大——使用者輸入問題後若觸發 retry，需等待 10 秒以上才有回應，體驗很差
- **[挑戰]** retry 策略應依任務性質區分：background ingestion 可接受長等待，interactive query 應有更短的 timeout 或 fail-fast

### 決策 7：雙 Gradio UI 分離（Chat vs. Evaluation Dashboard）

- `app.py`：使用者對話介面，展示問答與 Retrieved Context
- `evaluator.py`：評估 Dashboard，展示 MRR、nDCG、Answer 評分，含 Category 分類長條圖
- **優點**：關注點分離清晰；評估 dashboard 是求職時的重要差異化展示

### 決策 8：LLM-as-a-judge 三維評分框架

- **三個維度**：Accuracy / Completeness / Relevance（各 1–5 分）
- **對應問題**：
  - Accuracy：是否有幻覺？
  - Completeness：是否遺漏關鍵資訊？
  - Relevance：是否答非所問或資訊過多？
- **評估資料集**：`evaluation/tests.jsonl`，包含 `question`、`keywords`（retrieval 評估用）、`reference_answer`（answer 評估用）、`category`

---

## 3. 致命傷清單

> 更新狀態（含使用者已修復項目）

| # | 問題 | 嚴重程度 | 狀態 |
|---|------|----------|------|
| 1 | **無 README.md** | 🔴 致命 | 🔄 歸入 Stage 3 處理 |
| 2 | **無 `.env.example`** | 🔴 致命 | ✅ 使用者已修復 |
| 3 | **MODEL 常數不一致**（`answer.py` vs `eval.py`） | 🔴 致命 | ✅ 使用者已統一 |
| 4 | **`eval.py` 殘留 dead code `db_name`** | 🟡 嚴重 | ✅ 使用者已刪除 |

**實質未修復致命傷：1 個（README，歸入 Stage 3）**

### 補充：模型選擇建議（對應致命傷 3 的延伸優化）

目前統一使用 `openai/gpt-4.1-nano` 是**合理但非最優**的做法。建議依任務性質差異化：

```python
# 建議配置（answer.py 與 eval.py）
UTILITY_MODEL    = "openai/gpt-4.1-nano"   # rewrite, rerank 等背景任務
GENERATION_MODEL = "openai/gpt-4.1-mini"   # 主要回答生成（使用者可見）
JUDGE_MODEL      = "openai/gpt-4.1-mini"   # LLM-as-a-judge（公信力更高）
```

這個設計決策值得在 README 中說明，展現「工程師對 cost vs. quality trade-off 的意識」。

---

## 4. 一般優化建議

### 優化 1：依賴清單瘦身（`pyproject.toml`）

**[問題]** 目前 `pyproject.toml` 包含整個 Udemy 8 週課程的所有套件（`torch`、`wandb`、`modal`、`gtts`、`xgboost` 等），與本 RAG 專案完全無關。

- 面試官看到一個 RAG 專案依賴 `torch 2.8.0`，會立刻質疑專案架構是否清晰
- 建議：抽出本專案實際使用的套件，建立乾淨的 `requirements.txt` 或 `pyproject.toml`
- 實際所需套件：`openai`、`chromadb`、`litellm`、`gradio`、`pydantic`、`tenacity`、`python-dotenv`、`pandas`、`tqdm`

### 優化 2：全域 Retry 策略分層化

**[問題]** `min=10` 秒等待對 interactive query 不可接受。

- 建議：ingestion pipeline 保持長等待（`min=10, max=240`）；`answer_question()` 的 retry 設為 `max_attempts=2, min=2, max=10`，超過就回傳友善錯誤訊息

### 優化 3：模組層級 ChromaDB 初始化移入 lazy init

**[問題]** `answer.py` 在 import 時立即執行：
```python
chroma = PersistentClient(path=DB_NAME)   # import 即連線
collection = chroma.get_or_create_collection(collection_name)
```
這導致：在 `evaluation/eval.py` import `answer_question` 時，也會立刻嘗試連線 ChromaDB，若 `preprocessed_db/` 不存在會報錯；且單元測試無法 mock。

- 建議：將初始化移入函式內或使用 `functools.lru_cache` lazy init

### 優化 4：缺乏 pytest 單元測試

**[問題]** 目前只有 E2E 評估（需要真實 API 與向量庫），無法在 CI 中快速驗證核心邏輯。

- 建議：至少為以下函式補充 pytest + mock 測試：
  - `merge_chunks()`（純函式，可直接測試）
  - `calculate_mrr()`（純函式）
  - `calculate_ndcg()`（純函式）
  - `rerank()` 的 Pydantic 解析邏輯

### 優化 5：Conversation History Token 數量控制

**[問題]** `answer_question()` 接收 `history: list[dict]` 並全部帶入 prompt，沒有任何 token 截斷機制，長對話可能超出 context window。

- 建議：加入 `history[-N:]` 滑動視窗，或以 `tiktoken` 計算 token 數量後截斷

### 優化 6：模型常數集中管理

**[問題]** `ingest.py`、`answer.py`、`eval.py` 各自定義 `MODEL` 常數，未來修改需改三個地方，且語意不清（都叫 `MODEL`）。

- 建議：建立 `config.py` 集中定義：
```python
UTILITY_MODEL    = os.getenv("UTILITY_MODEL", "openai/gpt-4.1-nano")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "openai/gpt-4.1-mini")
JUDGE_MODEL      = os.getenv("JUDGE_MODEL", "openai/gpt-4.1-mini")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
```
  允許透過 `.env` 覆蓋，展現「配置與程式碼分離」的工程意識。

### 優化 7：缺乏日誌系統

**[問題]** 全系統沒有任何 `logging` 呼叫，debug 只能靠 `print()`，不適合 production-ready 展示。

- 建議：加入基本 `logging` 配置，至少記錄：查詢改寫結果、retrieval 數量、API 呼叫耗時

### 優化 8：Gradio UI 缺乏輸入驗證

**[問題]** 空白問題或超長 prompt 會直接送到 API，可能觸發無意義的費用或錯誤。

### 優化 9：知識庫文件格式假設過強

**[問題]** `fetch_documents()` 硬編碼只讀取 `*.md` 檔案，不支援 PDF、DOCX 等常見格式。

- 對於 portfolio demo 來說影響不大，但可在 README 的「已知限制」章節誠實說明，展現技術判斷力

### 優化 10：缺乏 CI/CD

**[問題]** 沒有 GitHub Actions，面試官無法一眼看到 pipeline 是否可自動執行。

- 建議：加入基本的 `pytest` 自動執行 workflow（至少讓純函式測試在 CI 跑起來）

---

## 5. 分級判定

| 評估維度 | 判定 | 說明 |
|----------|------|------|
| **致命傷數量** | 1 個（待 Stage 3） | README 缺失，其餘已修復 |
| **架構複雜度** | 中 | 手刻 pipeline 展現工程思維；但缺 async、缺 observability |
| **與 JD 匹配程度** | 中高 | RAG + LiteLLM + Pydantic + 評估框架，與 Appier JD3 高度契合 |
| **Harness / 評估框架現有程度** | 基礎 | 有 MRR + nDCG + LLM-as-a-judge；缺 regression test 自動化閉環、缺 prompt regression |

### 建議路線

```
☑ L1 完成後，空閒時疊代 L2
```

**理由**：
- L1 主要工作為補齊 README + 架構 Mermaid 圖（Stage 3）+ 依賴清單清理（優化 1）
- L2 的 Harness 強化（Prompt regression test、評估閉環自動化）能顯著提升對 Appier JD3 的競爭力
- 目前的評估框架已有足夠基礎，L2 是錦上添花而非從零起步

### 投遞時機判斷

| 狀態 | 可否投遞 |
|------|----------|
| 當前（Stage 1 完成後） | ⚠️ 不建議，README 缺失是硬傷 |
| Stage 3 L1 完成後 | ✅ 可投遞 TrendLife & ITRI JD |
| Stage 3 L1 + L2 完成後 | ✅ 可投遞 Appier JD3（差異化競爭） |

---

## 推理標記索引

| 標記 | 位置 | 內容摘要 |
|------|------|----------|
| [假設] | 決策 1 | Overlap 策略與語意邊界配合程度未驗證 |
| [決策點] | 決策 2 | Dual-query 提升 recall 但增加延遲 |
| [挑戰] | 決策 3 | Reranker 的 token 成本在 chunk 數量多時需注意 |
| [挑戰] | 決策 6 | Retry min=10s 對 interactive chat 體驗影響 |
| [致命] | 第 3 節 | README 缺失（歸入 Stage 3） |

---

*階段 1 完成。建議：跳過階段 2（致命傷已修復），直接進入**階段 3 L1：文檔工程**。*
