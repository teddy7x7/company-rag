import pytest
from evaluation.baseline import (
    run_subset_evaluation,
    load_latest_baseline,
    check_regression,
    CRITICAL_CASE_INDICES
)

@pytest.mark.integration
def test_prompt_regression():
    """
    Integration test to detect performance regressions on a representative subset
    of critical RAG cases. Requires active API credentials and an existing baseline.
    """
    # 1. Load baseline snapshot
    baseline = load_latest_baseline()
    if not baseline:
        pytest.skip(
            "⚠️ Skipping prompt regression test: No baseline snapshot found in evaluation/baselines/. "
            "Please run `uv run python evaluation/baseline.py save` first to establish a baseline."
        )

    # 2. Run fast evaluation on the critical case subset
    current_subset = run_subset_evaluation(CRITICAL_CASE_INDICES)
    
    # 3. Align baseline scores (support both subset-specific baseline keys and full-run fallbacks)
    mapped_baseline = {}
    subset_keys = {
        "subset_avg_mrr": "avg_mrr",
        "subset_avg_ndcg": "avg_ndcg",
        "subset_avg_coverage": "avg_coverage",
        "subset_avg_accuracy": "avg_accuracy",
        "subset_avg_completeness": "avg_completeness",
        "subset_avg_relevance": "avg_relevance"
    }

    has_subset_baseline = any(k in baseline for k in subset_keys)
    
    for baseline_key, target_key in subset_keys.items():
        if has_subset_baseline:
            # If baseline contains subset metrics, compare subset to subset
            mapped_baseline[target_key] = baseline.get(baseline_key, 0.0)
        else:
            # Fallback: compare subset against full run baseline (less precise, but works)
            mapped_baseline[target_key] = baseline.get(target_key, 0.0)

    # 4. Check for regressions
    regressions = check_regression(current_subset, mapped_baseline)
    
    # 5. Assert no quality degradation
    assert not regressions, (
        f"🚨 RAG Prompt Regression Detected!\n"
        f"Compared current subset against baseline snapshot ({baseline.get('label', 'unknown')}):\n" +
        "\n".join(f"  - {r}" for r in regressions)
    )
