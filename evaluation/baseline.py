import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path to run directly if needed
sys.path.append(str(Path(__file__).parent.parent))

from evaluation.test import load_tests
from evaluation.eval import evaluate_retrieval, evaluate_answer
from evaluation.report import generate_markdown_report
import config

BASELINE_DIR = Path(__file__).parent / "baselines"
REGRESSION_THRESHOLD = 0.05  # 5% threshold

# Critical case indices representing each question category
CRITICAL_CASE_INDICES = [0, 65, 80, 90, 95, 100, 140]

# Failure rate threshold: if more than this fraction of test cases fail,
# the overall result is flagged as unreliable.
FAILURE_RATE_THRESHOLD = 0.20


def run_subset_evaluation(indices: list[int] = CRITICAL_CASE_INDICES) -> dict:
    """Run evaluation on a subset of test questions (e.g. critical cases) to save token cost.

    Each test case is wrapped in its own try/except so that a single API
    failure (timeout, rate-limit, Pydantic parse error, etc.) does not abort
    the entire run.  Failed cases are collected in the returned ``errors``
    list and excluded from metric averages.
    """
    tests = load_tests()
    subset_tests = [tests[i] for i in indices if 0 <= i < len(tests)]
    total_tests = len(subset_tests)
    if total_tests == 0:
        print("❌ No valid subset tests found!")
        return {}

    print(f"🚀 Running fast subset evaluation on {total_tests} critical cases...")

    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0

    results = []
    errors = []       # Collect per-case error details
    failed_count = 0  # Number of cases that raised an exception

    for idx, test in enumerate(subset_tests):
        orig_idx = indices[idx]
        print(f" [Subset {idx + 1}/{total_tests}] (Orig Index #{orig_idx}) Question: {test.question[:50]}...")

        try:
            # Retrieval Evaluation
            ret_eval = evaluate_retrieval(test)

            # Answer Quality Evaluation
            ans_eval, generated_answer, _ = evaluate_answer(test)

            total_mrr += ret_eval.mrr
            total_ndcg += ret_eval.ndcg
            total_coverage += ret_eval.keyword_coverage
            total_accuracy += ans_eval.accuracy
            total_completeness += ans_eval.completeness
            total_relevance += ans_eval.relevance

            results.append({
                "question": test.question,
                "category": test.category,
                "generated_answer": generated_answer,
                "feedback": ans_eval.feedback,
                "metrics": {
                    "mrr": ret_eval.mrr,
                    "ndcg": ret_eval.ndcg,
                    "keyword_coverage": ret_eval.keyword_coverage,
                    "accuracy": ans_eval.accuracy,
                    "completeness": ans_eval.completeness,
                    "relevance": ans_eval.relevance,
                },
            })

        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            error_msg = f"[Subset {idx + 1}] orig_idx={orig_idx} | {type(exc).__name__}: {exc}"
            print(f"   ⚠️ Skipping case due to error: {error_msg}")
            errors.append({"orig_index": orig_idx, "question": test.question, "error": error_msg})

    succeeded = total_tests - failed_count
    failure_rate = failed_count / total_tests if total_tests > 0 else 0.0
    is_reliable = failure_rate <= FAILURE_RATE_THRESHOLD

    if not is_reliable:
        print(
            f"\n🚨 High failure rate detected: {failed_count}/{total_tests} cases failed "
            f"({failure_rate:.0%} > {FAILURE_RATE_THRESHOLD:.0%} threshold). "
            "Results are marked as UNRELIABLE."
        )

    divisor = succeeded if succeeded > 0 else 1  # Avoid ZeroDivisionError
    return {
        "avg_mrr": total_mrr / divisor,
        "avg_ndcg": total_ndcg / divisor,
        "avg_coverage": total_coverage / divisor,
        "avg_accuracy": total_accuracy / divisor,
        "avg_completeness": total_completeness / divisor,
        "avg_relevance": total_relevance / divisor,
        "failed_count": failed_count,
        "is_reliable": is_reliable,
        "errors": errors,
        "detail_results": results,
    }

def run_full_evaluation():
    """Run evaluation for all tests in the test dataset.

    Each test case is wrapped in its own try/except so that a single API
    failure (timeout, rate-limit, Pydantic parse error, etc.) does not abort
    the entire run.  Failed cases are collected in the returned ``errors``
    list and excluded from metric averages.
    """
    tests = load_tests()
    total_tests = len(tests)
    if total_tests == 0:
        print("❌ No tests found in tests.jsonl!")
        return None

    print(f"🚀 Running RAG evaluation on {total_tests} test cases...")

    results = []
    errors = []       # Collect per-case error details
    failed_count = 0  # Number of cases that raised an exception

    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0

    # Subset metrics accumulation
    sub_mrr = 0.0
    sub_ndcg = 0.0
    sub_coverage = 0.0
    sub_accuracy = 0.0
    sub_completeness = 0.0
    sub_relevance = 0.0
    sub_count = 0

    for idx, test in enumerate(tests):
        print(f" [{idx + 1}/{total_tests}] Question: {test.question[:50]}...")

        try:
            # Retrieval Evaluation
            ret_eval = evaluate_retrieval(test)

            # Answer Quality Evaluation
            ans_eval, generated_answer, _ = evaluate_answer(test)

            total_mrr += ret_eval.mrr
            total_ndcg += ret_eval.ndcg
            total_coverage += ret_eval.keyword_coverage
            total_accuracy += ans_eval.accuracy
            total_completeness += ans_eval.completeness
            total_relevance += ans_eval.relevance

            # Check if this is a critical case
            if idx in CRITICAL_CASE_INDICES:
                sub_mrr += ret_eval.mrr
                sub_ndcg += ret_eval.ndcg
                sub_coverage += ret_eval.keyword_coverage
                sub_accuracy += ans_eval.accuracy
                sub_completeness += ans_eval.completeness
                sub_relevance += ans_eval.relevance
                sub_count += 1

            results.append({
                "question": test.question,
                "category": test.category,
                "generated_answer": generated_answer,
                "feedback": ans_eval.feedback,
                "metrics": {
                    "mrr": ret_eval.mrr,
                    "ndcg": ret_eval.ndcg,
                    "keyword_coverage": ret_eval.keyword_coverage,
                    "accuracy": ans_eval.accuracy,
                    "completeness": ans_eval.completeness,
                    "relevance": ans_eval.relevance,
                },
            })

        except Exception as exc:  # noqa: BLE001
            failed_count += 1
            error_msg = f"[Case {idx + 1}] {type(exc).__name__}: {exc}"
            print(f"   ⚠️ Skipping case due to error: {error_msg}")
            errors.append({"index": idx, "question": test.question, "error": error_msg})

    succeeded = total_tests - failed_count
    failure_rate = failed_count / total_tests if total_tests > 0 else 0.0
    is_reliable = failure_rate <= FAILURE_RATE_THRESHOLD

    if not is_reliable:
        print(
            f"\n🚨 High failure rate detected: {failed_count}/{total_tests} cases failed "
            f"({failure_rate:.0%} > {FAILURE_RATE_THRESHOLD:.0%} threshold). "
            "Results are marked as UNRELIABLE."
        )

    divisor = succeeded if succeeded > 0 else 1  # Avoid ZeroDivisionError
    summary = {
        "model_utility": config.UTILITY_MODEL,
        "model_generation": config.GENERATION_MODEL,
        "model_judge": config.JUDGE_MODEL,
        "avg_mrr": total_mrr / divisor,
        "avg_ndcg": total_ndcg / divisor,
        "avg_coverage": total_coverage / divisor,
        "avg_accuracy": total_accuracy / divisor,
        "avg_completeness": total_completeness / divisor,
        "avg_relevance": total_relevance / divisor,

        # Store subset averages within baseline summary
        "subset_avg_mrr": sub_mrr / sub_count if sub_count > 0 else 0.0,
        "subset_avg_ndcg": sub_ndcg / sub_count if sub_count > 0 else 0.0,
        "subset_avg_coverage": sub_coverage / sub_count if sub_count > 0 else 0.0,
        "subset_avg_accuracy": sub_accuracy / sub_count if sub_count > 0 else 0.0,
        "subset_avg_completeness": sub_completeness / sub_count if sub_count > 0 else 0.0,
        "subset_avg_relevance": sub_relevance / sub_count if sub_count > 0 else 0.0,

        "failed_count": failed_count,
        "is_reliable": is_reliable,
        "errors": errors,
        "detail_results": results,
    }

    return summary

def save_baseline(summary: dict, label: str = None) -> Path:
    """Save the evaluation summary as a baseline snapshot.

    JSON filename format:
    - No label : ``{timestamp}.json``             e.g. ``20260714_122443.json``
    - With label: ``{timestamp}_{label}.json``    e.g. ``20260714_122443_v1_baseline.json``

    The timestamp prefix ensures alphabetical sort always reflects chronological
    order, so ``load_latest_baseline()`` and ``report.py`` always pick the
    correct file regardless of the label string.

    The Markdown report is automatically saved to
    ``docs/evaluation_result/evaluation-report-{timestamp}.md``,
    keeping report filenames in sync with their companion baseline JSON files.
    """
    BASELINE_DIR.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Always prefix filename with timestamp so alphabetical == chronological.
    filename = f"{timestamp}_{label}.json" if label else f"{timestamp}.json"
    path = BASELINE_DIR / filename

    summary["timestamp"] = timestamp
    summary["label"] = label or timestamp

    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"💾 Saved baseline snapshot to: {path}")

    # Automatically generate a timestamped Markdown report alongside the snapshot.
    # Path mirrors the JSON naming convention to keep the two in sync.
    report_path = f"docs/evaluation_result/evaluation-report-{timestamp}.md"
    try:
        generate_markdown_report(summary, report_path)
    except Exception as e:
        print(f"⚠️ Failed to generate Markdown report: {e}")

    return path

def load_latest_baseline() -> dict | None:
    """Load the latest baseline snapshot."""
    if not BASELINE_DIR.exists():
        return None
    snapshots = sorted(BASELINE_DIR.glob("*.json"))
    if not snapshots:
        return None
    
    # Load the latest based on alphabetical sort (which works because they start with timestamp YYYYMMDD_HHMMSS)
    latest_path = snapshots[-1]
    print(f"📖 Loaded latest baseline from: {latest_path.name}")
    return json.loads(latest_path.read_text(encoding="utf-8"))

def check_regression(current: dict, baseline: dict) -> list[str]:
    """Compare current results with baseline and detect regressions."""
    warnings = []
    metrics_to_check = {
        "avg_mrr": "Mean Reciprocal Rank (MRR)",
        "avg_ndcg": "nDCG",
        "avg_coverage": "Keyword Coverage",
        "avg_accuracy": "LLM Judge Accuracy",
        "avg_completeness": "LLM Judge Completeness",
        "avg_relevance": "LLM Judge Relevance"
    }

    for metric, label in metrics_to_check.items():
        if metric in baseline and metric in current:
            delta = current[metric] - baseline[metric]
            # If the metric is keyword coverage (0-100 scale), convert delta to a percentage difference or adapt threshold
            threshold = REGRESSION_THRESHOLD * 100 if metric == "avg_coverage" else REGRESSION_THRESHOLD
            
            if delta < -threshold:
                warnings.append(
                    f"⚠️ REGRESSION [{label}]: "
                    f"Baseline = {baseline[metric]:.4f}, Current = {current[metric]:.4f} "
                    f"(Dropped by {abs(delta):.4f})"
                )
    return warnings

def main():
    parser = argparse.ArgumentParser(description="Insurellm RAG Evaluation Baseline Snapshot Tool")
    parser.add_argument("action", choices=["run", "save", "compare"], help="Action to perform: run (evaluate only), save (evaluate and save as baseline), compare (evaluate and compare to latest baseline)")
    parser.add_argument("--label", type=str, default=None, help="Custom label for the saved baseline snapshot")
    
    args = parser.parse_args()

    if args.action == "run":
        summary = run_full_evaluation()
        if summary:
            print("\n📈 Current Evaluation Summary:")
            print(f"  Avg MRR: {summary['avg_mrr']:.4f}")
            print(f"  Avg nDCG: {summary['avg_ndcg']:.4f}")
            print(f"  Avg Coverage: {summary['avg_coverage']:.1f}%")
            print(f"  Avg Accuracy: {summary['avg_accuracy']:.2f}/5")
            print(f"  Avg Completeness: {summary['avg_completeness']:.2f}/5")
            print(f"  Avg Relevance: {summary['avg_relevance']:.2f}/5")

    elif args.action == "save":
        summary = run_full_evaluation()
        if summary:
            save_baseline(summary, args.label)

    elif args.action == "compare":
        baseline = load_latest_baseline()
        if not baseline:
            print("❌ No baseline snapshot found! Please run `uv run python evaluation/baseline.py save` first.")
            sys.exit(1)
            
        current = run_full_evaluation()
        if not current:
            sys.exit(1)

        print("\n📊 Comparing current run to baseline...")
        print(f"  Metric | Baseline ({baseline.get('label', 'unknown')}) | Current | Delta")
        print("  " + "-" * 70)
        
        metrics = ["avg_mrr", "avg_ndcg", "avg_coverage", "avg_accuracy", "avg_completeness", "avg_relevance"]
        for m in metrics:
            base_val = baseline.get(m, 0.0)
            curr_val = current.get(m, 0.0)
            diff = curr_val - base_val
            # diff_str = f"+{diff:.4f}" if diff >= 0 else f"{diff:.4f}"
            # prevent extremely small negative diff from being printed as -0.0000
            diff_str = f"{diff + 0.0:+.4f}"

            print(f"  {m:<16} | {base_val:.4f} | {curr_val:.4f} | {diff_str}")

        warnings = check_regression(current, baseline)
        if warnings:
            print("\n🚨 Regression Warnings Found:")
            for w in warnings:
                print(f"  {w}")
            sys.exit(1)
        else:
            print("\n✅ No regression detected (all metrics within threshold).")

if __name__ == "__main__":
    main()
