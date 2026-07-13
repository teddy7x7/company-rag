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

### [B-01] baseline.py 未保存 `ans_eval.feedback` — 評估報告失去可追溯性

- **發現管道**：人工發現（使用者在 draft 中明確指出）
- **嚴重程度**：高（未來致命）
- **影響分析**：
  目前 `run_full_evaluation()` 在 `results.append(...)` 時只保存了六項數值指標（mrr, ndcg, coverage, accuracy, completeness, relevance），完全丟棄了 `ans_eval.feedback` 這個 LLM Judge 給出的文字評語。這導致：
  1. 儲存的 baseline JSON 檔案中無法追溯「為什麼這題被扣分」
  2. `report.py` 的 `Failure & Low Performance Analysis` 區塊只能顯示數值分數，無法展示 Judge 的具體理由
  3. 面試官或協作者看到 17 個失敗案例（如評估報告所示），卻無從得知失敗根因，嚴重削弱 Harness 的展示力
- **預計 Refine 方案**：
  1. 在 `baseline.py` 的 `run_full_evaluation()` 中，將 `ans_eval.feedback` 與 `generated_answer` 一併寫入 `results` dict
  2. 在 `report.py` 的失敗案例表格中新增 `Feedback` 欄位
  3. 同步更新 `run_subset_evaluation()` 以保持一致性

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

### [B-03] `baseline.py` CLI 缺少 `--subset` 入口

- **發現管道**：人工發現（使用者在 draft 中明確指出）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  `run_subset_evaluation()` 函式已實作完成，但 `main()` 的 `argparse` 只有 `run` / `save` / `compare` 三個 action，且全部呼叫 `run_full_evaluation()`。子集評估只能透過 `test_prompt_regression.py` 間接觸發，無法從 CLI 直接執行。這降低了日常開發中快速驗證的效率。
- **預計 Refine 方案**：
  在 `argparse` 中新增 `--subset` flag（或 `--mode full|subset`），讓 `run`、`save`、`compare` 三個 action 都能選擇跑全量或子集。

---

### [B-04] `compare` 必須重跑全量測試 — 無法直接比對兩份快照

- **發現管道**：人工發現（使用者在 draft 中明確指出）
- **嚴重程度**：中（一般優化）
- **影響分析**：
  目前 `compare` action 會先呼叫 `run_full_evaluation()` 拿到 `current`，再與 `load_latest_baseline()` 比較。若測試集有 150 題，每次 compare 都要花費大量時間和 Token。在本地開發的快速疊代場景下，工程師只是想比較兩份已保存的 JSON 檔，不需要重新跑測試。
- **預計 Refine 方案**：
  新增 `--baseline` 和 `--current` 參數，允許直接指定兩個 JSON 檔案路徑進行離線比對。若未指定 `--current`，才 fallback 到重新跑評估。

---

### [B-05] 評估報告命名不規範 — `save_baseline` 的報告輸出路徑硬編碼

- **發現管道**：人工發現（使用者在 draft 中指出）+ 聯檢碰撞
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  `save_baseline()` 內部呼叫 `generate_markdown_report(summary, "docs/evaluation-report.md")` 使用固定路徑，每次都覆蓋同一份報告。若要保留歷史評估報告，必須手動呼叫 `report.py` 指定不同的 `--output` 路徑。這與 baseline JSON 本身帶時間戳的設計不一致。
- **預計 Refine 方案**：
  報告輸出路徑改為動態生成，與 baseline JSON 的時間戳對齊，例如：`docs/evaluation_result/evaluation-report-{timestamp}.md`。

---

### [B-06] 評估迴圈缺乏逐筆錯誤處理 — 單筆 API 失敗會中斷全量評估

- **發現管道**：AI 識別（`baseline-overview.md` M2 段明確指出）
- **嚴重程度**：高（未來致命）
- **影響分析**：
  `run_full_evaluation()` 和 `run_subset_evaluation()` 的 `for` 迴圈中，`evaluate_retrieval()` 和 `evaluate_answer()` 沒有任何 `try/except` 包覆。若第 50 筆測試因為 LLM API timeout、rate limit、或 Pydantic JSON 解析失敗而拋出異常，前面已花費的 49 次 API 調用成本全部浪費，且不會產出任何結果。
- **預計 Refine 方案**：
  1. 在迴圈內加上 `try/except`，單筆失敗時記錄錯誤、跳過該筆，繼續評估後續測試
  2. 在 summary 中加入 `failed_count` 和 `errors` 欄位，保留錯誤資訊
  3. 若失敗率超過可配置閾值（例如 > 20%），整體評估標記為不可信

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

### [B-09] `answer.py` SYSTEM_PROMPT 缺乏引導語 — 用戶不知道可以問什麼

- **發現管道**：人工發現（使用者在 draft 中指出）
- **嚴重程度**：低（程式碼微調）
- **影響分析**：
  Gradio Chat UI 啟動後，用戶面對空白對話框，不知道系統的知識範圍涵蓋哪些（company、contracts、employees、products）。在求職展示場景下，面試官可能隨意輸入一個問題然後得到不佳的回答，造成負面第一印象。
- **預計 Refine 方案**：
  1. 在 `app.py` 中為 `Chatbot` 設定初始歡迎訊息，引導用戶針對四大分類進行提問
  2. 提供 2-3 個 example questions 作為 Gradio UI 的 `examples` 參數

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

## 優先級排序建議

| 優先級 | 編號 | 名稱 | 嚴重度 | 難度 | 理由 |
|--------|------|------|--------|------|------|
| 🥇 P1 | **B-01** | 保存 feedback 至 baseline JSON | 高 | 低 | 數據一旦不保存就永遠消失；修復簡單且不改架構 |
| 🥈 P2 | **B-06** | 評估迴圈逐筆錯誤處理 | 高 | 低 | 一筆失敗炸掉整個 pipeline 是最高風險的穩定性問題 |
| 🥉 P3 | **B-03** | CLI `--subset` flag | 中 | 低 | 解鎖已寫好的子集評估功能，幾行代碼即可完成 |
| 4 | **B-04** | `compare` 離線比對兩份快照 | 中 | 低 | 大幅提升開發效率，且修改範圍僅限 argparse + 一個分支 |
| 5 | **B-05** | 報告命名規範化 | 低 | 低 | 與 B-01 一起修可順帶完成 |
| 6 | **B-13** | `rewrite_query` 傳入 history | 低 | 低 | 一行修改，修復多輪對話的指代消解能力 |
| 7 | **B-14** | ChromaDB lazy init | 低 | 低 | 改善測試可 mock 性和 CI 穩定性 |
| 8 | **B-09** | Chat UI 歡迎引導語 | 低 | 低 | 展示面優化，幾分鐘可完成 |
| 9 | **B-02** | 動態分層抽樣 | 中 | 中 | 需設計選取策略，但提升回歸測試可靠度 |
| 10 | **B-07** | 回歸閾值百分比化 | 低 | 低 | 統計精確度提升，改動不大 |
| 11 | **B-15** | 報告失敗案例根因分類 | 中 | 中 | 依賴 B-01，提升 Harness 展示力 |
| 12 | **B-10** | answer.py 檢索並行化 | 中 | 中 | 顯著降低用戶端延遲，但需處理線程安全 |
| 13 | **B-12** | ingest.py embedding 批次拆分 | 中 | 中 | 當前知識庫規模小影響不大，但擴展時必修 |
| 14 | **B-08** | 輸入安全過濾（Guardrails） | 高 | 高 | 涉及分類器設計、UI 聯動、多路邏輯，是最大的功能增量 |
| 15 | **B-11** | eval.py async 重構 | 中 | 高 | 全鏈路異步化工作量大，但長期必要 |

---

## 第三步決策建議

- **B-01 + B-06**：嚴重度高且難度低，建議立即修復後重新 commit，不需要等到階段 3。
- **B-03 / B-04 / B-05 / B-13 / B-14**：一組低難度的快速優化，可打包為一個 commit。
- **B-08（Guardrails）**：是最大的功能增量，設計複雜度高，建議獨立規劃為一個完整 Sprint，不與文檔工程（階段 3）混在一起。
- 其餘中/低優先級項目 → 封存紀錄，直接挺進階段 3 文檔工程，並將此清單轉化為 README 的「Future Roadmap」展現成長思維。
