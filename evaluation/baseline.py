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
import config

BASELINE_DIR = Path(__file__).parent / "baselines"
REGRESSION_THRESHOLD = 0.05  # 5% threshold

def run_full_evaluation():
    """Run evaluation for all tests in the test dataset."""
    tests = load_tests()
    total_tests = len(tests)
    if total_tests == 0:
        print("❌ No tests found in tests.jsonl!")
        return None

    print(f"🚀 Running RAG evaluation on {total_tests} test cases...")

    results = []
    
    total_mrr = 0.0
    total_ndcg = 0.0
    total_coverage = 0.0
    total_accuracy = 0.0
    total_completeness = 0.0
    total_relevance = 0.0

    for idx, test in enumerate(tests):
        print(f" [{idx + 1}/{total_tests}] Question: {test.question[:50]}...")
        
        # Retrieval Evaluation
        ret_eval = evaluate_retrieval(test)
        total_mrr += ret_eval.mrr
        total_ndcg += ret_eval.ndcg
        total_coverage += ret_eval.keyword_coverage

        # Answer Quality Evaluation
        ans_eval, generated_answer, _ = evaluate_answer(test)
        total_accuracy += ans_eval.accuracy
        total_completeness += ans_eval.completeness
        total_relevance += ans_eval.relevance

        results.append({
            "question": test.question,
            "category": test.category,
            "metrics": {
                "mrr": ret_eval.mrr,
                "ndcg": ret_eval.ndcg,
                "keyword_coverage": ret_eval.keyword_coverage,
                "accuracy": ans_eval.accuracy,
                "completeness": ans_eval.completeness,
                "relevance": ans_eval.relevance
            }
        })

    summary = {
        "model_utility": config.UTILITY_MODEL,
        "model_generation": config.GENERATION_MODEL,
        "model_judge": config.JUDGE_MODEL,
        "avg_mrr": total_mrr / total_tests,
        "avg_ndcg": total_ndcg / total_tests,
        "avg_coverage": total_coverage / total_tests,
        "avg_accuracy": total_accuracy / total_tests,
        "avg_completeness": total_completeness / total_tests,
        "avg_relevance": total_relevance / total_tests,
        "detail_results": results
    }

    return summary

def save_baseline(summary: dict, label: str = None) -> Path:
    """Save the evaluation summary as a baseline snapshot."""
    BASELINE_DIR.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = label or timestamp
    path = BASELINE_DIR / f"{label}.json"
    summary["timestamp"] = timestamp
    summary["label"] = label
    
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"💾 Saved baseline snapshot to: {path}")
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
            diff_str = f"+{diff:.4f}" if diff >= 0 else f"{diff:.4f}"
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
