# 📊 RAG System Evaluation Report

> **Generated at:** 2026-07-13 17:24:37  
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
| **Mean Reciprocal Rank (MRR)** | `0.8811` | 🟡 Acceptable | Measures how high the first relevant chunk ranks |
| **nDCG** | `0.8548` | 🟡 Acceptable | Measures overall ranking quality of top results |
| **Keyword Coverage** | `95.0%` | 🟢 Excellent | Percentage of golden keywords found in retrieved chunks |

### Answer Quality (LLM-as-a-judge)
| Dimension | Score | Status | Description |
|-----------|-------|--------|-------------|
| **Accuracy** | `4.43/5` | 🟡 Acceptable | Factually correct vs. reference answer |
| **Completeness** | `4.29/5` | 🟡 Acceptable | Covers all aspects of the query |
| **Relevance** | `4.43/5` | 🟡 Acceptable | Stays on topic, no fluff |

---

## 🗂️ Category Breakdown

| Category | Count | MRR | nDCG | Coverage | Accuracy | Completeness | Relevance |
|----------|-------|-----|------|----------|----------|--------------|-----------|
| direct_fact | 70 | 0.9218 | 0.8926 | 97.4% | 4.54/5 | 4.31/5 | 4.60/5 |
| temporal | 20 | 1.0000 | 0.9418 | 100.0% | 4.95/5 | 4.95/5 | 4.45/5 |
| comparative | 10 | 0.8878 | 0.8777 | 100.0% | 4.60/5 | 4.50/5 | 4.40/5 |
| numerical | 10 | 0.8917 | 0.8428 | 95.0% | 4.60/5 | 4.50/5 | 4.70/5 |
| relationship | 10 | 0.9250 | 0.9019 | 95.0% | 4.60/5 | 4.20/5 | 4.40/5 |
| spanning | 20 | 0.6685 | 0.6837 | 84.1% | 3.55/5 | 3.85/5 | 3.85/5 |
| holistic | 10 | 0.7221 | 0.6996 | 85.0% | 3.80/5 | 3.40/5 | 4.10/5 |

---

## 🔍 Failure & Low Performance Analysis
⚠️ Found **20** case(s) requiring optimization:

| Question | Category | MRR | Accuracy | Issue Type | Judge Feedback |
|----------|----------|-----|----------|------------|----------------|
| How many Claimllm contracts does Insurellm have? | direct_fact | 0.57 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect since it states that Insurellm has three Claimllm contra... |
| Which product does Sarah Williams lead design for? | direct_fact | 0.17 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect because it fails to provide the specific product Sarah W... |
| What is the monthly payment for Greenstone Insu... | direct_fact | 0.55 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer does not provide the specific monthly payment amount for Greenstone Insurance's... |
| Who signed the Metropolitan Life Group contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it states that the signer on behalf of Metropolitan L... |
| What is the duration of the FastTrack Insurance... | direct_fact | 0.16 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it states there is no information available about the... |
| Who signed the Atlantic Risk Solutions contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect because it states there is no information about the sign... |
| By what percentage did Sarah Williams improve u... | comparative | 0.67 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer incorrectly states that there is no information about Sarah Williams improving ... |
| Which product does Jessica Liu develop for? | relationship | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer fails to provide any factual information about the product Jessica Liu develops... |
| What product does the IIOTY award winner work on? | spanning | 0.75 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it identifies the IIOTY award winner as Kevin Zhang w... |
| Who is the technical lead for the product that ... | spanning | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) | The generated answer correctly identifies the product and its price point but fails to provide the k... |
| Which product did the Senior Data Scientist bui... | spanning | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is mostly correct but contains a spelling error in the product name: 'Markellm'... |
| Which product does the UX Designer who improved... | spanning | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it does not mention Sarah Williams as the UX Designer... |
| How many covered members does the client who su... | spanning | 0.56 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it names 'Advantage Medical Coverage' instead of 'Har... |
| Who signed the Metropolitan Life Group contract... | spanning | 0.27 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is inaccurate because it states the signatories are unknown, while the referenc... |
| When is the telematics-based pricing feature sc... | spanning | 0.68 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer inaccurately states that there is no telematics-based pricing feature scheduled... |
| What is Alex Chen's current job title? | direct_fact | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is incorrect regarding the specific job title; it states 'Senior Backend Softwa... |
| What is the monthly cost for Apex Reinsurance's... | numerical | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer fails to provide the specific information requested, which is the monthly cost ... |
| How many employees at Insurellm have a current ... | holistic | 0.57 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect when compared to the reference answer. It identifies onl... |
| Which product has the fewest active contracts a... | holistic | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect compared to the reference answer. The reference answer c... |
| What is the longest contract duration among all... | holistic | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer correctly identifies the longest contract duration as 48 months, matching the r... |
