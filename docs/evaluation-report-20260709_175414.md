# 📊 RAG System Evaluation Report

> **Generated at:** 2026-07-09 17:54:14  
> **Evaluation Dataset:** 150 test cases  

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
| **Mean Reciprocal Rank (MRR)** | `0.8755` | 🟡 Acceptable | Measures how high the first relevant chunk ranks |
| **nDCG** | `0.8417` | 🟡 Acceptable | Measures overall ranking quality of top results |
| **Keyword Coverage** | `93.3%` | 🟢 Excellent | Percentage of golden keywords found in retrieved chunks |

### Answer Quality (LLM-as-a-judge)
| Dimension | Score | Status | Description |
|-----------|-------|--------|-------------|
| **Accuracy** | `4.50/5` | 🟢 Excellent | Factually correct vs. reference answer |
| **Completeness** | `4.25/5` | 🟡 Acceptable | Covers all aspects of the query |
| **Relevance** | `4.42/5` | 🟡 Acceptable | Stays on topic, no fluff |

---

## 🗂️ Category Breakdown

| Category | Count | MRR | nDCG | Coverage | Accuracy | Completeness | Relevance |
|----------|-------|-----|------|----------|----------|--------------|-----------|
| direct_fact | 70 | 0.9254 | 0.8887 | 96.0% | 4.57/5 | 4.21/5 | 4.57/5 |
| temporal | 20 | 1.0000 | 0.9332 | 100.0% | 4.95/5 | 4.80/5 | 4.55/5 |
| comparative | 10 | 0.8289 | 0.8147 | 90.0% | 4.50/5 | 4.40/5 | 4.20/5 |
| numerical | 10 | 0.9250 | 0.8441 | 95.0% | 5.00/5 | 4.80/5 | 4.70/5 |
| relationship | 10 | 0.9250 | 0.8742 | 95.0% | 5.00/5 | 4.80/5 | 4.50/5 |
| spanning | 20 | 0.6276 | 0.6507 | 81.6% | 3.90/5 | 3.85/5 | 3.80/5 |
| holistic | 10 | 0.7205 | 0.7043 | 85.0% | 3.30/5 | 2.90/5 | 4.20/5 |

---

## 🔍 Failure & Low Performance Analysis
⚠️ Found **17** case(s) requiring optimization:

| Question | Category | MRR | Accuracy | Issue Type |
|----------|----------|-----|----------|------------|
| How many Claimllm contracts does Insurellm have? | direct_fact | 0.56 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| Which product does Sarah Williams lead design for? | direct_fact | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) |
| What is the monthly payment for Greenstone Insu... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| Who signed the Metropolitan Life Group contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| What is the duration of the FastTrack Insurance... | direct_fact | 0.22 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| Who signed the Atlantic Risk Solutions contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| By what percentage did Sarah Williams improve u... | comparative | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| What product does the IIOTY award winner work on? | spanning | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) |
| Who is the technical lead for the product that ... | spanning | 0.06 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| Which product does the UX Designer who improved... | spanning | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) |
| How many covered members does the client who su... | spanning | 0.66 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| Who signed the Metropolitan Life Group contract... | spanning | 0.28 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| What is Alex Chen's current job title? | direct_fact | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| How many employees at Insurellm have a current ... | holistic | 0.57 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| What is the total contract value of all Healthl... | holistic | 0.58 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| Which product has the fewest active contracts a... | holistic | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
| What is the longest contract duration among all... | holistic | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) |
