import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import config

def get_status_emoji(score: float, metric_type: str) -> str:
    """Get emoji and status text based on scores."""
    if metric_type == "mrr" or metric_type == "ndcg":
        if score >= 0.90: return "🟢 Excellent"
        if score >= 0.75: return "🟡 Acceptable"
        return "🔴 Poor"
    elif metric_type == "coverage":
        if score >= 90.0: return "🟢 Excellent"
        if score >= 75.0: return "🟡 Acceptable"
        return "🔴 Poor"
    elif metric_type in ["accuracy", "completeness", "relevance"]:
        if score >= 4.5: return "🟢 Excellent"
        if score >= 3.5: return "🟡 Acceptable"
        return "🔴 Poor"
    return ""

def generate_markdown_report(summary: dict, output_path: str = "docs/evaluation-report.md"):
    """Generate a formatted Markdown report from evaluation summary."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp = summary.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    # Format timestamp if it is in filename format YYYYMMDD_HHMMSS
    if "_" in timestamp and len(timestamp) == 15:
        try:
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    # Group detail results by category
    category_metrics = defaultdict(list)
    failures = []

    for item in summary.get("detail_results", []):
        cat = item["category"]
        metrics = item["metrics"]
        category_metrics[cat].append(metrics)
        
        # Consider a failure if accuracy is low (< 3.0) or MRR is 0 (keywords not found)
        if metrics.get("accuracy", 5.0) < 3.0 or metrics.get("mrr", 1.0) == 0:
            failures.append(item)

    # Calculate category averages
    cat_summary_rows = []
    for cat, items in category_metrics.items():
        avg_mrr = sum(x["mrr"] for x in items) / len(items)
        avg_ndcg = sum(x["ndcg"] for x in items) / len(items)
        avg_cov = sum(x["keyword_coverage"] for x in items) / len(items)
        avg_acc = sum(x["accuracy"] for x in items) / len(items)
        avg_comp = sum(x["completeness"] for x in items) / len(items)
        avg_rel = sum(x["relevance"] for x in items) / len(items)
        cat_summary_rows.append(
            f"| {cat} | {len(items)} | {avg_mrr:.4f} | {avg_ndcg:.4f} | {avg_cov:.1f}% | {avg_acc:.2f}/5 | {avg_comp:.2f}/5 | {avg_rel:.2f}/5 |"
        )

    md_content = f"""# 📊 RAG System Evaluation Report

> **Generated at:** {timestamp}  
> **Evaluation Dataset:** {len(summary.get("detail_results", []))} test cases  

---

## ⚙️ Model Configurations

| Role | Model Identifier | Purpose |
|------|------------------|---------|
| **Utility Model** | `{summary.get("model_utility", config.UTILITY_MODEL)}` | Query rewriting, chunking, reranking |
| **Generation Model** | `{summary.get("model_generation", config.GENERATION_MODEL)}` | Generating customer-facing answers |
| **Judge Model** | `{summary.get("model_judge", config.JUDGE_MODEL)}` | LLM-as-a-judge quality scoring |

---

## 📈 Executive Summary

### Retrieval Performance
| Metric | Score | Status | Description |
|--------|-------|--------|-------------|
| **Mean Reciprocal Rank (MRR)** | `{summary.get("avg_mrr", 0.0):.4f}` | {get_status_emoji(summary.get("avg_mrr", 0.0), "mrr")} | Measures how high the first relevant chunk ranks |
| **nDCG** | `{summary.get("avg_ndcg", 0.0):.4f}` | {get_status_emoji(summary.get("avg_ndcg", 0.0), "ndcg")} | Measures overall ranking quality of top results |
| **Keyword Coverage** | `{summary.get("avg_coverage", 0.0):.1f}%` | {get_status_emoji(summary.get("avg_coverage", 0.0), "coverage")} | Percentage of golden keywords found in retrieved chunks |

### Answer Quality (LLM-as-a-judge)
| Dimension | Score | Status | Description |
|-----------|-------|--------|-------------|
| **Accuracy** | `{summary.get("avg_accuracy", 0.0):.2f}/5` | {get_status_emoji(summary.get("avg_accuracy", 0.0), "accuracy")} | Factually correct vs. reference answer |
| **Completeness** | `{summary.get("avg_completeness", 0.0):.2f}/5` | {get_status_emoji(summary.get("avg_completeness", 0.0), "completeness")} | Covers all aspects of the query |
| **Relevance** | `{summary.get("avg_relevance", 0.0):.2f}/5` | {get_status_emoji(summary.get("avg_relevance", 0.0), "relevance")} | Stays on topic, no fluff |

---

## 🗂️ Category Breakdown

| Category | Count | MRR | nDCG | Coverage | Accuracy | Completeness | Relevance |
|----------|-------|-----|------|----------|----------|--------------|-----------|
"""
    
    md_content += "\n".join(cat_summary_rows)
    md_content += "\n\n---\n\n## 🔍 Failure & Low Performance Analysis\n"
    
    if not failures:
        md_content += "✅ **Awesome! No test cases fell below acceptable accuracy (3.0) or retrieval MRR (0).**\n"
    else:
        md_content += f"⚠️ Found **{len(failures)}** case(s) requiring optimization:\n\n"
        md_content += "| Question | Category | MRR | Accuracy | Issue Type | Judge Feedback |\n"
        md_content += "|----------|----------|-----|----------|------------|----------------|\n"
        
        for item in failures:
            q = item["question"]
            short_q = q[:47] + "..." if len(q) > 50 else q
            m = item["metrics"]
            mrr = m.get("mrr", 0.0)
            acc = m.get("accuracy", 0.0)
            
            issues = []
            if mrr == 0: issues.append("Retrieval Missed")
            if acc < 3.0: issues.append(f"Low Quality Answer (Acc: {acc})")
            issue_str = ", ".join(issues)
            
            # Display Judge feedback (truncated for table readability)
            feedback = item.get("feedback", "—")
            # Escape pipe characters in feedback to prevent breaking table formatting
            feedback = feedback.replace("|", "\\|").replace("\n", " ")
            short_feedback = feedback[:100] + "..." if len(feedback) > 100 else feedback
            
            md_content += f"| {short_q} | {item['category']} | {mrr:.2f} | {acc:.1f}/5 | {issue_str} | {short_feedback} |\n"
            
    output_file.write_text(md_content, encoding="utf-8")
    print(f"📄 Markdown report generated successfully at: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Generate Markdown RAG Evaluation Report from Baseline JSON")
    parser.add_argument("snapshot", type=str, nargs="?", default=None, help="Path to baseline snapshot JSON file. If omitted, uses latest.")
    parser.add_argument("--output", type=str, default=None, help="Output path for the Markdown report. Defaults to docs/evaluation_result/evaluation-report-{timestamp}.md")
    
    args = parser.parse_args()

    baseline_dir = Path(__file__).parent / "baselines"
    
    if args.snapshot:
        snapshot_path = Path(args.snapshot)
    else:
        # Load latest
        if not baseline_dir.exists():
            print("❌ No baselines directory found. Run baseline.py first.")
            sys.exit(1)
        snapshots = sorted(baseline_dir.glob("*.json"))
        if not snapshots:
            print("❌ No baseline snapshot files found.")
            sys.exit(1)
        snapshot_path = snapshots[-1]

    if not snapshot_path.exists():
        print(f"❌ File not found: {snapshot_path}")
        sys.exit(1)

    print(f"📖 Reading snapshot from: {snapshot_path.name}")
    with open(snapshot_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
        
    # Derive default output path from the snapshot's timestamp to stay consistent
    # with the naming convention used by baseline.py save.
    if args.output:
        output_path = args.output
    else:
        ts = summary.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))
        output_path = f"docs/evaluation_result/evaluation-report-{ts}.md"

    generate_markdown_report(summary, output_path)

if __name__ == "__main__":
    main()
