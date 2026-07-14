# 📊 RAG System Evaluation Report

> **Generated at:** 2026-07-14 16:44:17  
> **Evaluation Dataset:** 7 test cases  

---

## ⚙️ Model Configurations

| Role | Model Identifier | Purpose |
|------|------------------|---------|
| **Utility Model** | `openai/gpt-4.1-nano` | Query rewriting, chunking, reranking |
| **Generation Model** | `openai/gpt-4.1-mini` | Generating customer-facing answers |
| **Judge Model** | `openai/gpt-4.1-mini` | LLM-as-a-judge quality scoring |

---

## 📈 Executive Summary

### Retrieval Performance
| Metric | Score | Status | Description |
|--------|-------|--------|-------------|
| **Mean Reciprocal Rank (MRR)** | `0.8631` | 🟡 Acceptable | Measures how high the first relevant chunk ranks |
| **nDCG** | `0.8327` | 🟡 Acceptable | Measures overall ranking quality of top results |
| **Keyword Coverage** | `91.7%` | 🟢 Excellent | Percentage of golden keywords found in retrieved chunks |

### Answer Quality (LLM-as-a-judge)
| Dimension | Score | Status | Description |
|-----------|-------|--------|-------------|
| **Accuracy** | `4.14/5` | 🟡 Acceptable | Factually correct vs. reference answer |
| **Completeness** | `3.57/5` | 🟡 Acceptable | Covers all aspects of the query |
| **Relevance** | `4.57/5` | 🟢 Excellent | Stays on topic, no fluff |

---

## 🗂️ Category Breakdown

| Category | Count | MRR | nDCG | Coverage | Accuracy | Completeness | Relevance |
|----------|-------|-----|------|----------|----------|--------------|-----------|
| direct_fact | 1 | 0.6667 | 0.6667 | 66.7% | 5.00/5 | 5.00/5 | 5.00/5 |
| temporal | 1 | 1.0000 | 0.9524 | 100.0% | 3.00/5 | 2.00/5 | 5.00/5 |
| comparative | 1 | 1.0000 | 1.0000 | 100.0% | 5.00/5 | 4.00/5 | 5.00/5 |
| numerical | 1 | 1.0000 | 0.8797 | 100.0% | 5.00/5 | 5.00/5 | 5.00/5 |
| relationship | 1 | 1.0000 | 0.8793 | 100.0% | 5.00/5 | 5.00/5 | 4.00/5 |
| spanning | 1 | 0.7500 | 0.7500 | 75.0% | 5.00/5 | 3.00/5 | 3.00/5 |
| holistic | 1 | 0.6250 | 0.7006 | 100.0% | 1.00/5 | 1.00/5 | 5.00/5 |

---

## 🔍 Failure & Low Performance Analysis
⚠️ Found **1** case(s) requiring optimization:

| Question | Category | MRR | Accuracy | Issue Type | Judge Feedback |
|----------|----------|-----|----------|------------|----------------|
| How many employees at Insurellm have a current ... | holistic | 0.62 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect compared to the reference answer. It states that only on... |
