# 階段 2 L2：Harness 評估框架補強分析

> 生成時間：2026-06-12  
> 前置依賴：`docs/refine/stage1-analysis.md` ✅  
> 目標：讓 repo 展現「AI 品質工程」思維，而非只是 AI 應用開發

---

## 1. 目前評估 / 測試現況

### 已有的評估機制

| 元件 | 位置 | 功能 |
|------|------|------|
| **Retrieval 指標計算** | `evaluation/eval.py` | MRR（Mean Reciprocal Rank）、nDCG、Keyword Coverage |
| **Answer LLM-as-a-judge** | `evaluation/eval.py` | 三維評分：Accuracy / Completeness / Relevance（1–5 分） |
| **測試資料集** | `evaluation/tests.jsonl` | JSONL 格式，含 question / keywords / reference_answer / category |
| **評估資料模型** | `evaluation/test.py` | Pydantic `TestQuestion`，型別安全載入 |
| **評估 Dashboard** | `evaluator.py` | Gradio UI，含 Category 分類長條圖，顏色閾值標示 |
| **CLI 單測工具** | `evaluation/eval.py:main()` | `uv run eval.py <test_row_number>` 單題驗證 |

### 現有框架的品質水位

**優點**：
- 指標選擇正確——MRR 衡量 recall 排名、nDCG 衡量排名質量、LLM-as-a-judge 衡量語意品質
- Pydantic structured output 確保 judge 回應可解析
- 視覺化 Dashboard 展示友好
- 有分類（category）標籤，可做分層分析

**問題**：
- 每次評估結果**沒有保存**，無法跨時間比較（沒有 baseline）
- Prompt 改動後**沒有自動回歸測試機制**，靠人工手動跑
- 評估只能**全跑或跑單題**，沒有 fast-track（只跑 critical case）
- `MODEL` 常數在 `eval.py` 與 `answer.py` 分開定義，judge 模型與生成模型不同但可能造成混淆
- 沒有任何 **pytest 單元測試**，純函式（`calculate_mrr`、`calculate_ndcg`、`merge_chunks`）無保護
- 評估是**同步逐筆**執行，整個 dataset 跑完耗時長

---

## 2. 建議補齊的評估元件清單

---

### 元件 A：集中化模型配置 `config.py`

| 項目 | 內容 |
|------|------|
| **解決什麼問題** | 模型常數散落三個檔案（ingest / answer / eval），修改時容易遺漏；且 judge 用哪個模型不透明 |
| **對應 AI 系統風險** | 配置漂移（Config Drift）——不同模組用不同模型版本，導致評估結果無法復現 |
| **建議工具/做法** | 新建 `config.py`，所有模型常數從環境變數讀取，提供合理預設值 |
| **實作難度** | 🟢 低 |
| **對求職加分程度** | 🟡 中（基礎工程素養，面試官預期有） |

**設計草稿**：
```python
# config.py
import os

# Model hierarchy: nano for background tasks, mini for user-facing & judging
UTILITY_MODEL    = os.getenv("UTILITY_MODEL",    "openai/gpt-4.1-nano")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "openai/gpt-4.1-mini")
JUDGE_MODEL      = os.getenv("JUDGE_MODEL",      "openai/gpt-4.1-mini")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL",  "text-embedding-3-large")

DB_NAME          = os.getenv("DB_NAME",          "preprocessed_db")
COLLECTION_NAME  = os.getenv("COLLECTION_NAME",  "docs")
RETRIEVAL_K      = int(os.getenv("RETRIEVAL_K",  "20"))
FINAL_K          = int(os.getenv("FINAL_K",      "10"))
```

---

### 元件 B：pytest 純函式單元測試

| 項目 | 內容 |
|------|------|
| **解決什麼問題** | 核心計算邏輯（MRR、nDCG、chunk 合併）無任何測試保護，重構時容易引入靜默錯誤 |
| **對應 AI 系統風險** | 指標計算錯誤——評估分數錯了，整個品質管控體系失去可信度 |
| **建議工具/做法** | `pytest` + `tests/` 目錄，純函式直接測試，無需 API mock |
| **實作難度** | 🟢 低 |
| **對求職加分程度** | 🟡 中高（展現工程紀律，與只會跑 notebook 的人形成對比） |

**可測試的純函式**：
- `evaluation/eval.py: calculate_mrr(keyword, retrieved_docs)` 
- `evaluation/eval.py: calculate_ndcg(keyword, retrieved_docs, k)`
- `evaluation/eval.py: calculate_dcg(relevances, k)`
- `utils/answer.py: merge_chunks(chunks, reranked)`

**測試目錄結構**：
```
tests/
├── __init__.py
├── test_eval_metrics.py     # 測試 MRR / nDCG 計算
└── test_answer_utils.py     # 測試 merge_chunks
```

---

### 元件 C：評估基準快照 + 回歸偵測

| 項目 | 內容 |
|------|------|
| **解決什麼問題** | 改了 Prompt 或模型後，沒有辦法知道品質是否下降——這是 Appier JD3 面試官最常問的問題 |
| **對應 AI 系統風險** | 靜默品質退化（Silent Regression）——系統看起來能跑，但答案品質已悄悄變差 |
| **建議工具/做法** | `evaluation/baseline.py`：將每次評估結果以 JSON 儲存，並與上次基準比較，差異超過閾值時輸出 warning |
| **實作難度** | 🟡 中 |
| **對求職加分程度** | 🔴 高（這是「Harness 測試工程」的核心展示，JD3 Appier 明確要求） |

**設計草稿**：
```python
# evaluation/baseline.py
import json
from datetime import datetime
from pathlib import Path

BASELINE_DIR = Path("evaluation/baselines")
REGRESSION_THRESHOLD = 0.05  # 超過 5% 退化視為 regression

def save_baseline(results: dict, label: str = None):
    """儲存評估結果為基準快照。"""
    BASELINE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = label or timestamp
    path = BASELINE_DIR / f"{label}.json"
    results["timestamp"] = timestamp
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return path

def load_latest_baseline() -> dict | None:
    """載入最新一筆基準快照。"""
    if not BASELINE_DIR.exists():
        return None
    snapshots = sorted(BASELINE_DIR.glob("*.json"))
    if not snapshots:
        return None
    return json.loads(snapshots[-1].read_text())

def check_regression(current: dict, baseline: dict) -> list[str]:
    """比較當前結果與基準，列出退化指標。"""
    warnings = []
    for metric in ["avg_mrr", "avg_ndcg", "avg_accuracy", "avg_completeness"]:
        if metric in baseline and metric in current:
            delta = current[metric] - baseline[metric]
            if delta < -REGRESSION_THRESHOLD:
                warnings.append(
                    f"⚠️ REGRESSION [{metric}]: "
                    f"{baseline[metric]:.4f} → {current[metric]:.4f} "
                    f"(↓{abs(delta):.4f})"
                )
    return warnings
```

---

### 元件 D：CI/CD GitHub Actions（pytest 自動化）

| 項目 | 內容 |
|------|------|
| **解決什麼問題** | 沒有自動化測試流程，任何 PR 或程式碼改動都需要人工驗證 |
| **對應 AI 系統風險** | 部署風險——未測試的程式碼進入 main branch |
| **建議工具/做法** | `.github/workflows/test.yml`，使用 `uv` 安裝依賴，跑 `pytest tests/` |
| **實作難度** | 🟢 低（有元件 B 的測試後即可加） |
| **對求職加分程度** | 🟡 中高（讓 repo 首頁出現綠色 badge，一眼可見工程素養） |

**設計草稿**：
```yaml
# .github/workflows/test.yml
name: Unit Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pytest tests/ -v
```

---

### 元件 E：評估報告自動輸出（Markdown Report）

| 項目 | 內容 |
|------|------|
| **解決什麼問題** | 評估結果只在 Gradio UI 中顯示，無法輸出為可 commit 的文件，面試官看不到歷史評估結果 |
| **對應 AI 系統風險** | 結果不可追溯——每次評估跑完後消失，無法展示持續優化的過程 |
| **建議工具/做法** | `evaluation/report.py`：評估後自動生成 `docs/evaluation-report.md` |
| **實作難度** | 🟡 中 |
| **對求職加分程度** | 🟡 中（增加 repo 的「可讀性」，面試官不需要跑程式就能看到評估結果） |

**報告格式設計**：
```markdown
# RAG Evaluation Report
Generated: 2026-06-12 16:00 | Model: openai/gpt-4.1-mini | Dataset: 100 questions

## Retrieval Performance
| Metric | Score | Status |
|--------|-------|--------|
| MRR    | 0.847 | 🟢 Good |
| nDCG   | 0.891 | 🟢 Good |
| Coverage | 84.3% | 🟡 Acceptable |

## Answer Quality (LLM-as-a-judge)
| Dimension   | Score | Status |
|-------------|-------|--------|
| Accuracy    | 4.21/5 | 🟢 Good |
| Completeness | 3.87/5 | 🟡 Acceptable |
| Relevance   | 4.45/5 | 🟢 Good |

## Category Breakdown
...
```

---

### 元件 F：Prompt Regression 測試框架

| 項目 | 內容 |
|------|------|
| **解決什麼問題** | 修改 SYSTEM_PROMPT 後沒有自動化方式驗證影響，只能主觀感覺 |
| **對應 AI 系統風險** | Prompt 漂移（Prompt Drift）——迭代優化 prompt 時，舊的表現被意外破壞 |
| **建議工具/做法** | 在元件 C 的基準快照基礎上，加入 `tests/test_prompt_regression.py`：修改 prompt 後自動跑一個快速子集（critical cases），比對分數是否退化 |
| **實作難度** | 🔴 高（需要定義「critical case」子集，且每次跑都需要 API 費用） |
| **對求職加分程度** | 🔴 高（這是 Appier JD3 面試題的標準答案：「修改 Prompt 之後如何回歸測試」） |

**設計概念**：
```python
# tests/test_prompt_regression.py
"""
Prompt Regression Test
執行條件：手動觸發，不在 CI 自動跑（避免 API 費用）
用途：修改 SYSTEM_PROMPT 後，快速驗證 critical cases 沒有退化
"""
import pytest
from evaluation.baseline import load_latest_baseline, check_regression

CRITICAL_CASE_INDICES = [0, 5, 12, 23, 41]  # 代表各 category 的 critical cases

@pytest.mark.integration  # 用 marker 區分，CI 只跑 unit，手動跑 integration
def test_prompt_regression():
    """若分數退化超過閾值，測試失敗並列出退化指標。"""
    # 跑 critical cases 子集
    current = run_subset_evaluation(CRITICAL_CASE_INDICES)
    baseline = load_latest_baseline()

    if baseline is None:
        pytest.skip("No baseline found. Run `python -m evaluation.baseline save` first.")

    regressions = check_regression(current, baseline)
    assert not regressions, "\n".join(regressions)
```

---

## 3. 建議補強優先順序

> 排序原則：加分程度 × (1 / 難度) × 前後依賴關係

| 優先順序 | 元件 | 加分 | 難度 | 關鍵理由 |
|----------|------|------|------|----------|
| 🥇 P1 | **A：config.py** | 中 | 低 | 其他元件的前提，必須先做 |
| 🥈 P2 | **B：pytest 純函式測試** | 中高 | 低 | CI 的前提；展現工程紀律；幾乎零風險 |
| 🥉 P3 | **D：GitHub Actions CI** | 中高 | 低 | 依賴 P2；讓 repo 首頁有綠色 badge |
| 4 | **C：評估基準快照 + 回歸偵測** | 高 | 中 | Harness 核心展示；回答 JD3 面試題的關鍵物證 |
| 5 | **E：評估報告 Markdown 輸出** | 中 | 中 | 讓評估結果可 commit、可追溯；增強 repo 可讀性 |
| 6 | **F：Prompt Regression 測試** | 高 | 高 | 最高 JD3 匹配度，但建議在 C/E 完成後再做 |

---

## 4. 與 JD 面試題的直接對應

| Appier JD3 面試題（預期） | 由哪個元件回答 |
|---------------------------|----------------|
| 「你如何在評估準確度與 Token 成本之間取得平衡？」 | 元件 A（差異化 UTILITY vs GENERATION 模型）+ 元件 F（critical case 子集降低成本） |
| 「當你修改了 Prompt 之後，如何自動化執行回歸測試？」 | 元件 C（基準快照） + 元件 F（Prompt Regression Test） |
| 「如果模型輸出的品質突然下降，你的系統如何偵測並告警？」 | 元件 C（`check_regression()` + warning 輸出） |
| 「你的評估基準如何確保沒有測試集污染？」 | 元件 B（知識庫與測試集獨立，`tests.jsonl` 是從 knowledge-base 衍生的 ground truth，不影響 retrieval）|

---

## 5. 實作進度紀錄 (截至 2026-06-12)

### 🥇 P1：集中式配置與角色分離 (`config.py`) ✅
* **進度**：已完成
* **說明**：建立 [config.py](../../config.py)，統一管理模型與資料庫路徑。將模型拆分為 `UTILITY_MODEL` (`gpt-4.1-nano` 用於重寫與 rerank)、`GENERATION_MODEL` (`gpt-4.1-mini` 用於 RAG 回答) 與 `JUDGE_MODEL` (`gpt-4.1-mini` 用於評估裁判)。更新了 `answer.py`, `ingest.py`, 與 `eval.py` 以參照此配置。

### 🥈 P2：pytest 單元測試保護 ✅
* **進度**：已完成
* **說明**：
  * 建立 [test_eval_metrics.py](../../tests/test_eval_metrics.py) 覆蓋 MRR, DCG 與 nDCG 之數學計算。
  * 建立 [test_answer_utils.py](../../tests/test_answer_utils.py) 覆蓋區塊合併邏輯 `merge_chunks`。
  * 在 `pyproject.toml` 加上 `pythonpath = ["."]` 確保測試能正確載入專案模組。

### 🥉 P3：CI/CD GitHub Actions 運作機制 ✅
* **進度**：已完成
* **說明**：建立 [.github/workflows/test.yml](../../.github/workflows/test.yml)。整合了 `astral-sh/setup-uv@v5` 以加快快取與相依性同步，並在 pytest 中帶入所需的 API 金鑰（藉由 GitHub Secrets 傳遞）。
* **優化**：將 `utils/answer.py` 中 `openai = OpenAI()` 的初始化延遲至 `fetch_context_unranked` 執行，使 pytest 能在無 API 密鑰環境下成功進行 Module Collection，防止 CI 崩潰。

### 4️⃣ P4：評估基準快照與回歸偵測 (`evaluation/baseline.py`) ✅
* **進度**：已完成
* **說明**：建立獨立 CLI 模組 [evaluation/baseline.py](../../evaluation/baseline.py)，支援 `run` (僅執行評估), `save` (執行並儲存快照), `compare` (與最新快照比對)。
* **核心功能**：
  1. **全面評估 (`run`)**：載入 `tests.jsonl`，對所有測試問題進行檢索（MRR/nDCG/Coverage）與回答品質（LLM-as-a-judge Accuracy/Completeness/Relevance）評估。
  2. **儲存基準快照 (`save`)**：將評估平均結果與詳細紀錄儲存為帶有時間戳的 JSON 檔案於 `evaluation/baselines/`。
  3. **退化偵測 (`compare`)**：比較當前執行結果與最新基準，找出退化的指標。
* **回歸閾值**：設定 `REGRESSION_THRESHOLD = 0.05`。若關鍵平均分數（MRR, nDCG, Accuracy, Completeness, Relevance）退化超過 5%，`compare` 階段將輸出警告並以非零的 exit code 結束以標記失敗（適合 CI 整合）。
* **CLI 使用範例**：
  * 僅執行評估並印出摘要：
    ```bash
    uv run python evaluation/baseline.py run
    ```
  * 執行評估並儲存為基準快照（可選標籤）：
    ```bash
    uv run python evaluation/baseline.py save --label "v1_baseline"
    ```
  * 與最新基準比對偵測退化：
    ```bash
    uv run python evaluation/baseline.py compare
    ```

### 5️⃣ P5：評估報告自動輸出 (Markdown Report) ✅
* **進度**：已完成
* **說明**：建立獨立報告生成模組 [evaluation/report.py](../../evaluation/report.py)，可讀取 JSON 格式的基準快照並自動輸出為極具美感的 RAG 評估 Markdown 報告 `docs/evaluation-report.md` (default name)。
* **報告特點**：
  * **視覺標記**：使用綠、黃、紅燈號標示各指標健康度（MRR、nDCG、Coverage、Accuracy、Completeness、Relevance）。
  * **細分統計**：提供問題類別（Category）之平均表現表格。
  * **弱點分析**：自動列出失敗或低分（Accuracy < 3.0 或 MRR = 0）的案例，便於開發者針對性優化。
* **自動整合**：已整合至 [evaluation/baseline.py](../../evaluation/baseline.py)，在執行 `save` 行為儲存新基準時，將會自動更新並重新生成最新的 Markdown 報告。
* **CLI 使用範例**：
  * 使用最新基準快照產生 Markdown 報告：
    ```bash
    uv run python evaluation/report.py
    ```
  * 指定特定的基準快照 JSON 產生報告：
    ```bash
    uv run python evaluation/report.py evaluation/baselines/20260612_170000.json
    ```

### 6️⃣ P6：Prompt Regression 測試框架 (`tests/test_prompt_regression.py`) ✅
* **進度**：已完成
* **說明**：建立 [test_prompt_regression.py](../../tests/test_prompt_regression.py) 作為集成測試。
* **設計規格**：
  * **關鍵子集設計**：定義 `CRITICAL_CASE_INDICES = [0, 65, 80, 90, 95, 100, 140]`，橫跨全部 7 個問題種類（如 direct_fact, temporal, numerical 等），避免每次測試都執行全部 150 題而產生龐大 API 費用與時間成本。
  * **快速回歸測試**：利用 `@pytest.mark.integration` 將其與一般快速單元測試區隔開。
  * **自動比對與 Skip**：載入最新基準 JSON，若無基準則自動 Skip。有基準時，比對子集平均指標分數，一旦退化超過 5% 門檻（`REGRESSION_THRESHOLD`），測試即失敗並顯示詳細報告。
  * **標記註冊**：在 `pyproject.toml` 中向 pytest 註冊自訂 `integration` 標記，避免編譯警告。
* **測試執行指令**：
  ```bash
  # 排除 integration 標記，僅跑快速單元測試（適用於 CI）
  uv run pytest -m "not integration"
  
  # 指定只執行 Prompt Regression 測試
  uv run pytest -k test_prompt_regression
  ```

---

*階段 2 P1 至 P6 的 Harness 評估框架優化工作已全數完成並驗證通過。*

---

## 後續疊代修復紀錄（來自 Stage 2.5 Backlog）

---

### 🛡️ [B-06] 評估迴圈逐筆錯誤處理 ✅ (2026-07-14)

**問題本質**：`run_full_evaluation()` 和 `run_subset_evaluation()` 的 `for` 迴圈中沒有任何 `try/except`，單筆 API 失敗（timeout / rate limit / Pydantic parse error）會直接拋出異常，中斷整個評估流程，前面已花費的所有 API 成本全部浪費。

**修復範圍**：`evaluation/baseline.py`

| 修改項目 | 說明 |
|---------|------|
| `FAILURE_RATE_THRESHOLD = 0.20` | 新增常數：失敗率超過此閾值時標記整體結果為不可信 |
| `run_subset_evaluation()` | 每筆迭代包覆 `try/except Exception`，失敗時 print 警告並 `continue` |
| `run_full_evaluation()` | 同上，同時保持 critical case subset 累積邏輯不受影響 |
| `summary["failed_count"]` | 新增欄位：本次評估失敗的案例數 |
| `summary["is_reliable"]` | 新增欄位：`True` if 失敗率 ≤ 20%，否則 `False` |
| `summary["errors"]` | 新增欄位：list of `{index, question, error}` 供事後根因追蹤 |
| 分母改為 `succeeded` | 失敗案例從除數中排除，防止指標平均值被零值拉低 |

**修復後行為**：
- ✅ 單筆失敗 → 跳過，繼續評估後續 case，成本不浪費
- ✅ 失敗率 ≤ 20% → `is_reliable: true`，正常輸出結果
- 🚨 失敗率 > 20% → `is_reliable: false`，標明結果可信度存疑
- 📋 所有失敗案例的錯誤訊息保存至 `errors` 欄位，可從 baseline JSON 中直接追蹤

---

### 📋 [B-05] 評估報告命名規範化 ✅ (2026-07-14)

**問題本質**：`save_baseline()` 呼叫 `generate_markdown_report(summary, "docs/evaluation-report.md")` 使用固定路徑，每次 `baseline.py save` 都覆蓋同一份報告，無法保留歷史評估紀錄。與 baseline JSON 本身帶時間戳的設計不一致。

**修復範圍**：`evaluation/baseline.py` — `save_baseline()`

```diff
-    generate_markdown_report(summary, "docs/evaluation-report.md")
+    report_path = f"docs/evaluation_result/evaluation-report-{timestamp}.md"
+    generate_markdown_report(summary, report_path)
```

**修復後行為**：每次 `baseline.py save` 自動同時產生：
- `evaluation/baselines/{timestamp}.json` — 原有快照
- `docs/evaluation_result/evaluation-report-{timestamp}.md` — 新的時間戳對齊報告

兩者命名完全同步，歷史評估報告自動保留，無需手動呼叫 `report.py`。

**後續補充修復** — `evaluation/report.py` `--output` 預設值對齊：

發現 `report.py` 的 `--output` 預設值仍殘留舊的硬編碼 `"docs/evaluation-report.md"`，與 `baseline.py save` 的新行為不一致。無參數執行 `report.py` 時會覆蓋舊檔，而非產生時間戳命名的新報告。

```diff
-    parser.add_argument("--output", default="docs/evaluation-report.md", ...)
+    parser.add_argument("--output", default=None, ...)

-    generate_markdown_report(summary, args.output)
+    if args.output:
+        output_path = args.output
+    else:
+        ts = summary.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
+        output_path = f"docs/evaluation_result/evaluation-report-{ts}.md"
+    generate_markdown_report(summary, output_path)
```

`README.md` CLI 說明同步更新，補上無參數用法：
```bash
# [Optional] Retroactively generate a report from the latest snapshot
uv run python evaluation/report.py

# [Optional] Or specify an older snapshot and a custom output path
uv run python evaluation/report.py evaluation/baselines/<timestamp>.json --output docs/evaluation_result/evaluation-report-<timestamp>.md
```

**後續補充修復 2** — `save_baseline()` 有 `--label` 時 filename 缺少時間戳前綴（排序 Bug）：

發現當使用者傳入 `--label` 時，JSON 檔名為 `{label}.json`（如 `v1_baseline.json`），沒有時間戳前綴。
`load_latest_baseline()` 和 `report.py` 都依賴**字母排序**取最新快照，`v1_baseline.json` 的字母排序無法保證正確，導致：
1. `compare` 指令可能比對到錯誤的 baseline
2. `report.py` 無參數執行時可能讀到錯誤的「最新」快照
3. `test_prompt_regression.py` 的回歸比對基準可能錯誤

```diff
-    label = label or timestamp
-    path = BASELINE_DIR / f"{label}.json"
+    # Always prefix filename with timestamp so alphabetical == chronological.
+    filename = f"{timestamp}_{label}.json" if label else f"{timestamp}.json"
+    path = BASELINE_DIR / filename
     summary["timestamp"] = timestamp
-    summary["label"] = label
+    summary["label"] = label or timestamp
```

| 情況 | 修復前 | 修復後 |
|------|--------|--------|
| 無 label | `20260714_122443.json` ✅ | `20260714_122443.json` ✅ |
| 有 label | `v1_baseline.json` ❌ | `20260714_122443_v1_baseline.json` ✅ |

`README.md` 對應範例同步更新為新格式。

---

### 🔀 [B-04] `compare` 離線比對兩份快照 ✅ (2026-07-14)

**問題本質**：`compare` action 固定呼叫 `run_full_evaluation()` 重跑全量 150 題評估後才比對，無法直接比對兩份已存在的 JSON 快照，每次 compare 都要消耗大量時間和 API Token。

**修復範圍**：`evaluation/baseline.py` — `argparse` + `compare` 分支

**新增參數**：

| 參數 | 說明 |
|------|------|
| `--baseline <path>` | 指定 baseline 快照 JSON。省略時 fallback 到 `load_latest_baseline()` |
| `--current <path>` | 指定 current 快照 JSON 做離線比對。省略時 fallback 到 `run_full_evaluation()` |

**支援三種執行模式**：

```bash
# 全量模式（原有）：跑全量評估 + 最新快照比對
uv run python evaluation/baseline.py compare

# 半離線模式（新增）：指定 baseline，current 由即時評估提供
uv run python evaluation/baseline.py compare --baseline evaluation/baselines/20260709_175414.json

# 完全離線模式（新增）：兩份 JSON 直接比對，零 API 調用、零 Token 成本
uv run python evaluation/baseline.py compare \
    --baseline evaluation/baselines/20260709_175414.json \
    --current  evaluation/baselines/20260714_122443.json
```

輸出表頭同時顯示兩份快照的 `label`，方便辨識比對的對象。
`README.md` CLI 說明新增離線比對範例。

---

### ⚡ [B-03] `baseline.py` CLI `--subset` 入口 ✅ (2026-07-14)

**問題本質**：`run_subset_evaluation()` 函式雖已實作，但 `argparse` 的三個 action 全部呼叫 `run_full_evaluation()`，子集評估只能透過 `test_prompt_regression.py` 間接觸發，無法從 CLI 直接執行。

**修復範圍**：`evaluation/baseline.py` — `argparse` + `run` / `save` / `compare` 三個分支

**新增參數**：`--subset`（`store_true` flag）

| Action + Flag | 行為 |
|---|---|
| `run` | 跑全量評估 |
| `run --subset` | 只跑 7 題關鍵子集，~95% 更少 Token |
| `save --subset` | 子集評估並保存為快照 |
| `compare --subset` | 即時評估時跑子集；從全量快照取 `subset_avg_*` 作為比對基準 |
| `compare --subset --current <file>` | 兩份 JSON 離線比對（`--subset` 僅影響 live 路徑，不影響離線路徑） |

**設計細節**：當 `compare --subset` 且 `--current` 未指定（live 路徑）時，baseline 快照的比對鍵從 `avg_*` 自動映射為 `subset_avg_*`（全量 `save` 時已內嵌），避免空值比對造成假性 regression。

`README.md` CLI 說明 + `baseline.py` argparse epilog 同步新增 `--subset` 範例。
