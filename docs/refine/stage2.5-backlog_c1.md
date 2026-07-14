# 階段 2.5 — 優化儲備計畫 (Refine Backlog) C1

> **Review 日期**：2026-07-12
> **本次審查核心範圍**：
> 1. 階段 2 (L1 + L2) 修復後的全模塊交叉審查
> 2. `docs/architecture/*` 四份架構大綱中已識別的工程風險與效能瓶頸
> 3. `docs/evaluation_result/evaluation-report-20260709_175414.md` 的 150 題全量評估報告
> 4. `docs/.private/Insurellm-RAG-update-draft.md` 的人工觀察筆記

---

## 問題清單

---

### ~~[B-01] baseline.py 未保存 `ans_eval.feedback` — 評估報告失去可追溯性~~ ✅ 已修復

- **發現管道**：人工發現（使用者在 draft 中明確指出）
- **嚴重程度**：高（未來致命）
- **狀態**：✅ **已修復 (2026-07-13)**
- **修復內容**：
  1. `baseline.py` 的 `run_full_evaluation()` 與 `run_subset_evaluation()` 中，`results.append(...)` 現在一併寫入 `generated_answer` 與 `feedback` 欄位
  2. `report.py` 的失敗案例表格新增 `Judge Feedback` 欄位（截斷至 100 字元以保持表格可讀性，`|` 與換行符號自動轉義）
  3. 重新執行 `baseline.py save` 並生成 [`evaluation-report-20260713_172437.md`](../evaluation_result/evaluation-report-20260713_172437.md)，確認 Feedback 欄位正確顯示

---

### [B-02] `CRITICAL_CASE_INDICES` 硬編碼 — 分層抽樣假設脆弱

- **發現管道**：AI 識別（`baseline-overview.md` M1 段已指出）+ 人工確認
- **嚴重程度**：中（一般優化）
- **影響分析**：
  `CRITICAL_CASE_INDICES = [0, 65, 80, 90, 95, 100, 140]` 完全依賴 `tests.jsonl` 的排列順序不變。一旦測試集增刪或重新排序，這組索引對應的問題類別就會悄悄錯位，卻沒有任何驗證機制去偵測。目前只是「分層抽樣的雛形」，不是真正的分層抽樣。
- **預計 Refine 方案**：
  1. 改為按 `category` 欄位動態抽取每類別的代表性測試（例如：每類別取第一題，或隨機取一題）
  2. 若需維持確定性（reproducibility），可設定 `random.seed` 或使用固定的 hash-based 選取策略
  3. 新增啟動時的 sanity check：驗證選中的索引是否仍覆蓋所有 7 個 category

---

### ~~[B-03] `baseline.py` CLI 缺少 `--subset` 入口~~ ✅ 已修復

- **發現管道**：人工發現（使用者在 draft 中明確指出）
- **嚴重程度**：中（一般優化）
- **狀態**：✅ **已修復 (2026-07-14)**
- **修復內容**：`argparse` 新增 `--subset` boolean flag，三個 action 全部支援：
  - `run --subset`：執行子集評估並列印指標
  - `save --subset`：執行子集評估並保存為快照（节省 ~95% Token 成本）
  - `compare --subset`：當即時評估时跳過對 150 題全距；同時自動將全量快照內嵌的 `subset_avg_*` 鍵取出作為比對基準，避免空值比對

---

### ~~[B-04] `compare` 必須重跑全量測試 — 無法直接比對兩份快照~~ ✅ 已修復

- **發現管道**：人工發現（使用者在 draft 中明確指出）
- **嚴重程度**：中（一般優化）
- **狀態**：✅ **已修復 (2026-07-14)**
- **修復內容**：`argparse` 新增 `--baseline` 與 `--current` 兩個可選參數，支援三種模式：
  - **全量模式**（原有）：`compare` 無額外參數 → 跟全量評估 + 最新快照比對
  - **離線模式**（新增）：`compare --baseline A.json --current B.json` → 直接讀取兩份 JSON，零 API 調用
  - **半離線模式**（新增）：`compare --baseline A.json` → 讀取指定基準，`current` 由即時評估提供

  `compare` 輸出表頭同時顯示兩份快照的 label，方便辨識。

---

### ~~[B-05] 評估報告命名不規範 — `save_baseline` 的報告輸出路徑硬編碼~~ ✅ 已修復

- **發現管道**：人工發現（使用者在 draft 中指出）+ 聯檢碰撞
- **嚴重程度**：低（程式碼微調）
- **狀態**：✅ **已修復 (2026-07-14)**
- **修復內容**：
  `save_baseline()` 內的報告輸出路徑改為動態組合：`docs/evaluation_result/evaluation-report-{timestamp}.md`。每次 `baseline.py save` 會同時產生：
  - `evaluation/baselines/{timestamp}.json`（已有）
  - `docs/evaluation_result/evaluation-report-{timestamp}.md`（新增）

  兩者時間戳對齊，消除了每次覆蓋同一份報告、無法保留瞭測歷史的問題。

---

### ~~[B-06] 評估迴圈缺乏逐筆錯誤處理 — 單筆 API 失敗會中斷全量評估~~ ✅ 已修復

- **發現管道**：AI 識別（`baseline-overview.md` M2 段明確指出）
- **嚴重程度**：高（未來致命）
- **狀態**：✅ **已修復 (2026-07-14)**
- **修復內容**：
  1. `run_full_evaluation()` 與 `run_subset_evaluation()` 的 `for` 迴圈中，每筆迭代加上 `try/except Exception`，單筆失敗時印出警告並 `continue`，不中斷整個評估流程
  2. 新增 `FAILURE_RATE_THRESHOLD = 0.20` 常數（可配置），當失敗率超過 20% 時，整體評估結果標記為 `is_reliable: false` 並輸出 🚨 警告
  3. summary dict 新增 `failed_count`、`is_reliable`、`errors` 三個欄位，保留每筆失敗的 index / question / error 訊息以利事後追蹤
  4. 失敗案例從分母中排除（改用 `succeeded` 作為除數），確保指標平均值不被零值拉低

---

### [B-07] 回歸閾值設計不精確 — 不同尺度指標共用同一絕對閾值

- **發現管道**：AI 識別（`baseline-overview.md` M4 段深入分析）
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  `REGRESSION_THRESHOLD = 0.05` 對 MRR/nDCG（0-1 尺度）和 Accuracy/Completeness/Relevance（1-5 尺度）使用相同的絕對值閾值。MRR 掉 0.05 = 5% 的退化；Accuracy 掉 0.05 = 僅 1% 的退化。兩者被視為同等嚴重的 regression，這在統計上不精確。此外，LLM judge 本身對同一答案的評分變異度可達 ±0.3，絕對閾值 0.05 極易因抽樣雜訊而誤觸 regression。
- **預計 Refine 方案**：
  1. 改用百分比閾值（例如 `delta / baseline < -0.05`），讓每個指標按自身尺度衡量退化幅度
  2. 或為不同指標設定獨立閾值字典（MRR: 0.05, Accuracy: 0.25）
  3. 長期可考慮多次重跑取置信區間，但短期改用百分比閾值即可顯著改善

---

### [B-08] `answer.py` 缺少輸入安全過濾（Guardrails） — 無關問題仍觸發全鏈路查詢

- **發現管道**：人工發現（使用者在 draft 中詳細描述）
- **嚴重程度**：高（未來致命）
- **影響分析**：
  目前 `answer_question()` 對任何輸入都直接執行完整的 RAG 管線（rewrite → 雙路檢索 → rerank → 生成），不做任何輸入分類或過濾。這導致：
  1. 無關問題（如「今天天氣如何？」）仍會觸發 3 次 LLM 調用 + 2 次 embedding 查詢，浪費成本
  2. UI 右側面板會顯示不相關但向量距離「最近」的 chunks，誤導用戶
  3. 惡意輸入（prompt injection、超長 payload）沒有任何防護
- **預計 Refine 方案**（參照 draft 中的設計思路）：
  1. 在 `answer_question()` 入口處新增輕量 LLM 分類器（或 rule-based），將輸入分為：
     - `history_sufficient`：歷史對話已有答案，直接回覆
     - `knowledge_query`：屬於四大知識分類之一，正常走 RAG 管線，且將分類結果注入 rewrite prompt 以強化檢索
     - `out_of_bound`：
       - `greeting`：寒暄，簡單回覆後引導回知識庫
       - `ambiguous`：模糊問題，先確認意圖
       - `unsafe`：惡意輸入，拒絕服務
  2. 在 `fetch_context_unranked()` 中增加 distance 閾值過濾，丟棄距離過遠的 chunks
  3. 新增基本的 rate limit 和 input length 限制

---

### ~~[B-09] `answer.py` SYSTEM_PROMPT 缺乏引導語 — 用戶不知道可以問什麼~~ ✅ 已修復

- **發現管道**：人工發現（使用者在 draft 中指出）
- **嚴重程度**：低（程式碼微調）
- **狀態**：✅ **已修復 (2026-07-14)**
- **修復內容**：
  1. `answer.py` 的 `SYSTEM_PROMPT` 新增四大分類說明（company / products / employees / contracts），並將原本籠統的「If you don't know the answer, say so」改為「If a question falls outside the above areas, politely say so and suggest what kinds of questions you can help with」，讓 LLM 有足夠 context 主動引導用戶
  2. `app.py` 的 `Chatbot` 加入初始 `value=WELCOME_MESSAGE`，啟動即顯示 emoji 引導訊息（含四大分類 bullet list）
  3. `app.py` 標題副標改為明確列出四大分類；`Textbox` placeholder 改為具體示範問句
  4. 新增 `gr.Examples` 提供三個涵蓋 products / employees / contracts 的示範問題，點擊即可填入輸入框

---

### [B-10] `answer.py` 檢索管線串行 I/O — 三次 LLM/API 呼叫未並行化

- **發現管道**：AI 識別（`answer-overview.md` M4 段指出）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  `fetch_context()` 內部依序呼叫 `rewrite_query()` → `fetch_context_unranked(original)` → `fetch_context_unranked(rewritten)`，造成三次序列網路 I/O 阻塞。其中後兩次向量查詢是獨立的，可以並行。理論上可將端到端延遲降低 30-40%。
- **預計 Refine 方案**：
  1. 短期：使用 `concurrent.futures.ThreadPoolExecutor` 將兩次 `fetch_context_unranked` 並行執行
  2. 長期：重構為 `asyncio` 原生非同步，連同 `rewrite_query` 一起併發（rewrite 完成後再發起第二路查詢）

---

### [B-11] `eval.py` 評估全程同步序列 — 是整個 pipeline 最大延遲瓶頸

- **發現管道**：AI 識別（`eval-overview.md` M3/M4 段 + `baseline-overview.md` M2 段）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  `evaluate_answer()` 內部和批量評估 generator 都是同步序列執行。150 題全量評估 = 150 次序列阻塞的 LLM 調用（加上 retrieval 階段的呼叫），估計耗時 30-60 分鐘。docstring 和 TODO 都已承認此問題但尚未實作修復。
- **預計 Refine 方案**：
  1. 使用 `asyncio.Semaphore` 控制併發數量，以 `litellm.acompletion()` 取代同步 `completion()`
  2. 配合 rate limit 設定合理的併發上限（例如 5-10 個同時請求）
  3. 需同步修改 `evaluator.py` Gradio UI 的 generator 消費邏輯以支援 async

---

### [B-12] `ingest.py` M5 批次 embedding 無拆分 — 大量 chunks 可能超限

- **發現管道**：AI 識別（`ingest-overview.md` M5 段明確指出「目前管線裡最脆弱的一段」）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  `create_embeddings()` 將所有 chunks 的文字一次性送入 `openai.embeddings.create()`。若 chunk 數量達到數千筆，可能超過 embedding API 的單次請求限制（8191 tokens per input / batch size）。且此函式沒有 `@retry` 裝飾器，失敗時不會自動重試。
- **預計 Refine 方案**：
  1. 按 batch size 拆分（例如每 100 筆一批）
  2. 加上 `@retry` 裝飾器
  3. 加入進度條以提供可視性

---

### [B-13] `answer.py` 的 `rewrite_query()` 未傳入 `history` — 功能參數被浪費

- **發現管道**：AI 識別（代碼審查）
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  `rewrite_query()` 函式簽名接受 `history` 參數，且 prompt 中使用了 `{history}` 變數。但在 `fetch_context()` 呼叫時 `rewrite_query(original_question)` 未傳入 history，導致多輪對話中的指代消解（如「那這款呢？」）無法正確運作。
- **預計 Refine 方案**：
  將 `fetch_context()` 改為接受 `history` 參數並傳遞給 `rewrite_query()`。同步更新 `answer_question()` 的調用鏈。

---

### [B-14] `answer.py` 模組載入時即初始化 ChromaDB — 單元測試無法 mock

- **發現管道**：AI 識別（`stage1-analysis.md` 優化 3 已指出）
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  ```python
  chroma = PersistentClient(path=config.DB_NAME)          # L23
  collection = chroma.get_or_create_collection(...)        # L24
  ```
  在 `import` 階段就執行，若 `preprocessed_db/` 不存在會直接報錯。且 CI 環境中 import `answer_question` 時會觸發資料庫連線，無法透過 mock 隔離。
- **預計 Refine 方案**：
  改用 lazy initialization（`functools.lru_cache` 或首次呼叫時初始化），與 `OpenAI()` client 已完成的延遲初始化保持一致。

---

### [B-15] 評估報告中的失敗案例分析缺乏根因分類

- **發現管道**：聯檢碰撞（評估報告 × 架構文件）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  評估報告中 17 個失敗案例（Accuracy = 1.0/5）可明確分為至少三類根因：
  1. **Retrieval Missed**（MRR = 0）：3 筆 — 向量庫根本沒撈到相關 chunk（spanning 類型的跨文件問題為主）
  2. **Retrieval Partial but Answer Wrong**（MRR > 0 但 Accuracy = 1.0）：12 筆 — 撈到了部分相關 chunk 但生成回答嚴重偏離（多為需要精確數值的 direct_fact 和 holistic 類型）
  3. **全類別短板**：`spanning`（跨文件推理）和 `holistic`（全局統計）是系統性弱點，不是個別 prompt 可修的

  目前報告只有一個 `Issue Type` 欄位，無法體現上述分類層次，也沒有將 feedback 文字呈現出來（見 B-01）。
- **預計 Refine 方案**：
  1. 先修復 B-01（保存 feedback）
  2. 在 `report.py` 中按根因分類展示失敗案例
  3. 標記出系統性弱點（spanning / holistic），將其列入 README 的「Known Limitations」

---

### [B-16] `pyproject.toml` 依賴清單包含大量未使用套件 — 面試官紅旗

- **發現管道**：AI 識別（`stage1-analysis.md` 優化 1 已指出）+ 本次代碼覆查確認
- **嚴重程度**：中（一般優化）
- **影響分析**：
  `pyproject.toml` 包含了 8 個 `langchain-*` 相關套件（`langchain`, `langchain-chroma`, `langchain-community`, `langchain-core`, `langchain-openai`, `langchain-text-splitters`, `langchain-huggingface`, `langchain-ollama`, `langchain-anthropic`, `langchain-experimental`），但 V2 的核心代碼已完全脫離 LangChain 框架，這些依賴完全未被使用。此外 `scikit-learn`, `plotly`, `tiktoken` 也未被任何模塊 import。
  - 面試官看到一個「不用 LangChain」的 RAG 項目，依賴列表卻包含整個 LangChain 生態系，會立刻質疑專案的工程素養和清理程度
  - `uv sync` 安裝了大量不必要的套件，拉長 CI build 時間和 Docker image 體積
- **預計 Refine 方案**：
  1. 清理 `pyproject.toml`，只保留實際 import 的套件：`chromadb`, `gradio`, `litellm`, `openai`, `pandas`, `python-dotenv`, `tqdm`, `tenacity`, `pydantic`, `numpy`
  2. 若保留 `langchain` 作為 V1 歷史紀錄的說明，改為在 README 中提及而非放在依賴中
  3. 清理後重新 `uv sync` 並驗證所有功能正常

---

### [B-17] `answer.py` 問答生成未使用 Streaming — 用戶等待體驗差

- **發現管道**：AI 識別（`answer-overview.md` M5 段指出）
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  `answer_question()` 使用同步 `completion()` 調用，等整個回答生成完畢後才一次性返回。在完整 RAG 管線（rewrite + 雙路檢索 + rerank + 生成）耗時約 5-10 秒期間，用戶看到的是完全空白的聊天框，體驗很差。
- **預計 Refine 方案**：
  1. 在 `answer_question()` 中改用 `completion(..., stream=True)` 並逐 token 返回
  2. 在 `app.py` 中將 `chat()` 改為 Gradio streaming generator
  3. 先單獨返回 context（右側面板立刻顯示），再逐步生成答案（左側逐字出現）

---

### [B-18] ~~CI workflow 未排除 integration 測試 — 可能意外消耗 API Token~~ ✅ 已修復

- **發現管道**：AI 識別（代碼審查 `.github/workflows/test.yml`）
- **嚴重程度**：中（一般優化）
- **狀態**：✅ **已修復 (2026-07-13)**
- **修復內容**：
  將 `.github/workflows/test.yml` 的測試命令由
  ```
  uv run pytest tests/ -v
  ```
  改為
  ```
  uv run pytest tests/ -v -m "not integration"
  ```
  CI 現在只執行 unit tests，`test_prompt_regression.py`（`@pytest.mark.integration`）在 CI 中被自動跳過，與 ADR-003 的設計意圖對齊。

---

### [B-19] `temp/vector_db_ingestion_check.py` 應模組化 — 有用但結構粗糙

- **發現管道**：人工發現（使用者在 draft 中明確提問）
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  該腳本包含兩個實用的檢查功能：
  1. **Ingestion Cost Check**：計算知識庫所有 Markdown 的 token 數和 embedding API 預估費用
  2. **Ingestion Result Check**：連接 ChromaDB 列出所有 collection、document 數量，並抽驗前 3 筆

  目前放在 `temp/` 目錄下，作為一次性腳本使用。功能有用，但寫法較粗糙（硬編碼路徑、兩個功能混在一個檔案中、缺乏 CLI 參數）。
- **預計 Refine 方案**：
  1. 將兩個功能拆分為 `utils/check_cost.py` 和 `utils/check_db.py`（或合併為 `utils/inspect.py` 的兩個子命令）
  2. 改用 `config.py` 中的路徑常數取代硬編碼
  3. 加入 argparse 支援選擇 embedding 模型和目標 collection
  4. 若判定 portfolio 展示價值不高，也可保持在 `temp/` 不遷移

---

### [B-20] `answer.py` 缺少生成後自我檢查（Self-Reflection）— 錯誤答案直接返回

- **發現管道**：人工發現（使用者在 draft L28-30 中詳述）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  目前生成的答案直接返回用戶，無任何品質檢查。從評估報告的 17 個失敗案例中可見，很多情況下系統撈到了部分正確的 chunks（MRR > 0），但生成回答嚴重偏離（Accuracy = 1.0/5）。若在生成後加入 LLM 自我檢查，可在返回前攔截低品質回答。
- **預計 Refine 方案**（參照 draft 設計思路）：
  1. 生成答案後，用輕量 LLM 檢查：答案是否完整？是否與 context 一致？
  2. 若不通過，保存當前 context，重新 rewrite query 並補充查詢，合併新舊 context 後再次生成
  3. 設置最大迭代次數（例如 2-3 次），超過後返回「資訊不足」的誠實回覆並引導用戶改進問題
  4. 此功能增加了 1-2 次額外的 LLM 調用，需權衡成本與品質

---

### [B-21] `fetch_context_unranked()` 未返回 distance — 無法按距離過濾低相關 chunks

- **發現管道**：人工發現（使用者在 draft L26-27 中指出）+ 聯檢碰撞
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  `collection.query()` 返回的結果包含 `distances` 欄位，但 `fetch_context_unranked()` 在建構 `Result` 物件時完全忽略了這個資訊。這導致無法實現「距離過遠的 chunks 直接丟棄」的過濾策略（B-08 的一部分）。
- **預計 Refine 方案**：
  1. 將 `distances` 保存到 `Result.metadata` 中
  2. 在 `fetch_context()` 中加入可配置的 distance threshold，過濾明顯不相關的 chunks
  3. 此修改是 B-08（Guardrails）的前置依賴之一

---

## 優先級排序建議

| 優先級 | 編號 | 名稱 | 嚴重度 | 難度 | 理由 |
|--------|------|------|--------|------|------|
| 🥇 P1 | ~~**B-01**~~ ✅ | ~~保存 feedback 至 baseline JSON~~ | 高 | 低 | **已修復 (2026-07-13)** — 同時修復 `baseline.py` 與 `report.py`，新評估報告已含 Judge Feedback 欄位 |
| 🥈 P2 | ~~**B-06**~~ ✅ | ~~評估迴圈逐筆錯誤處理~~ | 高 | 低 | **已修復 (2026-07-14)** — 雙迴圈加 `try/except`，新增 `failed_count`/`is_reliable`/`errors` 欄位，失敗率 >20% 整體標記 UNRELIABLE |
| 🥉 P3 | ~~**B-18**~~ ✅ | ~~CI 排除 integration 測試~~ | 中 | 低 | **已修復 (2026-07-13)** — 一行修改，防止 CI 意外消耗 API Token，與 ADR-003 對齊 |
| 4 | ~~**B-03**~~ ✅ | ~~CLI `--subset` flag~~ | 中 | 低 | **已修復 (2026-07-14)** — 新增 `--subset` flag，`run`/`save`/`compare` 全部支援子集模式 |
| 5 | ~~**B-04**~~ ✅ | ~~`compare` 離線比對兩份快照~~ | 中 | 低 | **已修復 (2026-07-14)** — 新增 `--baseline`/`--current` 參數，支援零 API 成本的離線比對 |
| 6 | ~~**B-05**~~ ✅ | ~~報告命名規範化~~ | 低 | 低 | **已修復 (2026-07-14)** — 報告輸出路徑改為動態 `evaluation-report-{timestamp}.md`，與 baseline JSON 時間戳對齊 |
| 7 | **B-16** | 依賴清單瘦身 | 中 | 低 | 面試官紅旗項目，清理後展現工程素養 |
| 8 | **B-13** | `rewrite_query` 傳入 history | 低 | 低 | 一行修改，修復多輪對話的指代消解能力 |
| 9 | **B-14** | ChromaDB lazy init | 低 | 低 | 改善測試可 mock 性和 CI 穩定性 |
| 10 | ~~**B-09**~~ ✅ | ~~Chat UI 歡迎引導語~~ | 低 | 低 | **已修復 (2026-07-14)** — `Chatbot` 加入歡迎訊息、`gr.Examples` 示範問題、`SYSTEM_PROMPT` 補充四大分類說明 |
| 11 | **B-02** | 動態分層抽樣 | 中 | 中 | 需設計選取策略，但提升回歸測試可靠度 |
| 12 | **B-07** | 回歸閾值百分比化 | 低 | 低 | 統計精確度提升，改動不大 |
| 13 | **B-15** | 報告失敗案例根因分類 | 中 | 中 | 依賴 B-01，提升 Harness 展示力 |
| 14 | **B-21** | `fetch_context_unranked` 返回 distance | 低 | 低 | B-08 的前置依賴，改動很小 |
| 15 | **B-19** | `temp/` 檢查腳本模組化 | 低 | 低 | 有用但非關鍵，可選擇性遷移 |
| 16 | **B-10** | answer.py 檢索並行化 | 中 | 中 | 顯著降低用戶端延遲，但需處理線程安全 |
| 17 | **B-12** | ingest.py embedding 批次拆分 | 中 | 中 | 當前知識庫規模小影響不大，但擴展時必修 |
| 18 | **B-17** | answer.py Streaming 輸出 | 低 | 中 | 改善用戶端等待體驗，需改 app.py 配合 |
| 19 | **B-20** | 生成後自我檢查（Self-Reflection） | 中 | 高 | 可攔截低品質回答，但增加 LLM 調用成本，需權衡 |
| 20 | **B-08** | 輸入安全過濾（Guardrails） | 高 | 高 | 涉及分類器設計、UI 聯動、多路邏輯，是最大的功能增量 |
| 21 | **B-11** | eval.py async 重構 | 中 | 高 | 全鏈路異步化工作量大，但長期必要 |

---

## 第三步決策建議

- ✅ ~~**B-01 + B-06 + B-18**：嚴重度高且難度低，建議立即修復後重新 commit，不需要等到階段 3。~~
- **B-03 / B-04 / B-05 / B-13 / B-14 / B-16**：一組低難度的快速優化，可打包為一個 commit。其中 B-16（依賴清單瘦身）是面試官的紅旗項目，建議優先處理。
- **B-08（Guardrails）+ B-20（Self-Reflection）+ B-21（distance 過濾）**：構成一個完整的「輸入→輸出品質防護」功能集。設計複雜度高，建議獨立規劃為一個完整 Sprint，不與文檔工程（階段 3）混在一起。
- 其餘中/低優先級項目 → 封存紀錄，直接挺進階段 3 文檔工程，並將此清單轉化為 README 的「Future Roadmap」展現成長思維。
