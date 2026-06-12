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

## 5. 實作計畫（等待確認後展開）

```
P1 → config.py 建立 + ingest/answer/eval 同步修改 import
P2 → tests/ 目錄 + test_eval_metrics.py + test_answer_utils.py
P3 → .github/workflows/test.yml
P4 → evaluation/baseline.py + evaluator.py 整合
P5 → evaluation/report.py + docs/evaluation-report.md 初始版本
P6 → tests/test_prompt_regression.py（最後執行）
```

> **注意**：P1–P3 為純程式碼工程，不需要真實 API；P4–P6 需要一次完整評估跑通才能建立基準。

---

*分析完成。等待確認大綱後，依序輸出各元件的實作程式碼。*
