# 📊 RAG System Evaluation Report

> **Generated at:** 2026-07-14 12:24:43  
> **Evaluation Dataset:** 149 test cases  

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
| **Mean Reciprocal Rank (MRR)** | `0.8892` | 🟡 Acceptable | Measures how high the first relevant chunk ranks |
| **nDCG** | `0.8606` | 🟡 Acceptable | Measures overall ranking quality of top results |
| **Keyword Coverage** | `95.0%` | 🟢 Excellent | Percentage of golden keywords found in retrieved chunks |

### Answer Quality (LLM-as-a-judge)
| Dimension | Score | Status | Description |
|-----------|-------|--------|-------------|
| **Accuracy** | `4.48/5` | 🟡 Acceptable | Factually correct vs. reference answer |
| **Completeness** | `4.26/5` | 🟡 Acceptable | Covers all aspects of the query |
| **Relevance** | `4.48/5` | 🟡 Acceptable | Stays on topic, no fluff |

---

## 🗂️ Category Breakdown

| Category | Count | MRR | nDCG | Coverage | Accuracy | Completeness | Relevance |
|----------|-------|-----|------|----------|----------|--------------|-----------|
| direct_fact | 69 | 0.9204 | 0.8898 | 95.9% | 4.54/5 | 4.17/5 | 4.61/5 |
| temporal | 20 | 1.0000 | 0.9290 | 100.0% | 4.95/5 | 4.75/5 | 4.65/5 |
| comparative | 10 | 0.8903 | 0.8945 | 100.0% | 4.50/5 | 4.30/5 | 4.60/5 |
| numerical | 10 | 0.9250 | 0.8760 | 95.0% | 5.00/5 | 4.80/5 | 4.70/5 |
| relationship | 10 | 0.9500 | 0.9337 | 100.0% | 5.00/5 | 4.70/5 | 4.50/5 |
| spanning | 20 | 0.7048 | 0.7093 | 86.6% | 3.70/5 | 4.05/5 | 3.80/5 |
| holistic | 10 | 0.7229 | 0.7034 | 85.0% | 3.60/5 | 3.20/5 | 4.30/5 |

---

## 🔍 Failure & Low Performance Analysis
⚠️ Found **17** case(s) requiring optimization:

| Question | Category | MRR | Accuracy | Issue Type | Judge Feedback |
|----------|----------|-----|----------|------------|----------------|
| How many Claimllm contracts does Insurellm have? | direct_fact | 0.58 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it states there are four Claimllm contracts, whereas ... |
| Which product does Sarah Williams lead design for? | direct_fact | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect because it explicitly states there is no information abo... |
| What is the monthly payment for Greenstone Insu... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is inaccurate because it denies the presence of information on the monthly paym... |
| Who signed the Metropolitan Life Group contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it fails to provide the name of the individual who si... |
| What is the duration of the FastTrack Insurance... | direct_fact | 0.17 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer does not provide the key information given in the reference answer, which is th... |
| Who signed the Atlantic Risk Solutions contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect since the reference clearly states that Michael Torres, ... |
| By what percentage did Sarah Williams improve u... | comparative | 0.67 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect because it claims there is no information about Sarah Wi... |
| Who is the technical lead for the product that ... | spanning | 0.08 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it fails to identify Robert Chen as the technical lea... |
| Which product did the Senior Data Scientist bui... | spanning | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer introduces an incorrect product name 'Markellm' instead of the correct 'Marketl... |
| Which product does the UX Designer who improved... | spanning | 0.08 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer incorrectly identifies the product and company the UX Designer leads design for... |
| How many covered members does the client who su... | spanning | 0.53 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer introduces information about two clients subscribing to the Healthllm Professio... |
| Who signed the Metropolitan Life Group contract... | spanning | 0.17 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it claims that the signatories are not mentioned, whe... |
| How many core values does the company founded b... | spanning | 0.47 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer incorrectly states that the company has five core values and that the fifth is ... |
| What is Alex Chen's current job title? | direct_fact | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is partially correct in identifying Alex Chen's role as a Backend Software Engi... |
| How many employees at Insurellm have a current ... | holistic | 0.58 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is inaccurate compared to the reference answer. It identifies only one employee... |
| Which product has the fewest active contracts a... | holistic | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect compared to the reference answer. The reference answer c... |
| What is the longest contract duration among all... | holistic | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer correctly identifies the longest contract duration as 48 months, which aligns w... |
