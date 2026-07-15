# 📊 RAG System Evaluation Report

> **Generated at:** 2026-07-15 14:38:29  
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
| **Mean Reciprocal Rank (MRR)** | `0.8718` | 🟡 Acceptable | Measures how high the first relevant chunk ranks |
| **nDCG** | `0.8438` | 🟡 Acceptable | Measures overall ranking quality of top results |
| **Keyword Coverage** | `93.8%` | 🟢 Excellent | Percentage of golden keywords found in retrieved chunks |

### Answer Quality (LLM-as-a-judge)
| Dimension | Score | Status | Description |
|-----------|-------|--------|-------------|
| **Accuracy** | `4.42/5` | 🟡 Acceptable | Factually correct vs. reference answer |
| **Completeness** | `4.29/5` | 🟡 Acceptable | Covers all aspects of the query |
| **Relevance** | `4.46/5` | 🟡 Acceptable | Stays on topic, no fluff |

---

## 🗂️ Category Breakdown

| Category | Count | MRR | nDCG | Coverage | Accuracy | Completeness | Relevance |
|----------|-------|-----|------|----------|----------|--------------|-----------|
| direct_fact | 69 | 0.9183 | 0.8865 | 95.9% | 4.61/5 | 4.36/5 | 4.61/5 |
| temporal | 20 | 1.0000 | 0.9277 | 100.0% | 4.95/5 | 4.80/5 | 4.60/5 |
| comparative | 10 | 0.8608 | 0.8696 | 100.0% | 4.60/5 | 4.60/5 | 4.60/5 |
| numerical | 10 | 0.9250 | 0.8670 | 95.0% | 4.60/5 | 4.40/5 | 4.30/5 |
| relationship | 10 | 0.9250 | 0.8817 | 95.0% | 4.50/5 | 4.50/5 | 4.40/5 |
| spanning | 20 | 0.6122 | 0.6379 | 80.6% | 3.65/5 | 3.80/5 | 4.00/5 |
| holistic | 10 | 0.7189 | 0.7065 | 85.0% | 3.10/5 | 3.10/5 | 4.20/5 |

---

## 🔍 Failure & Low Performance Analysis
⚠️ Found **20** case(s) requiring optimization:

| Question | Category | MRR | Accuracy | Issue Type | Judge Feedback |
|----------|----------|-----|----------|------------|----------------|
| How many Claimllm contracts does Insurellm have? | direct_fact | 0.57 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it states Insurellm has three Claimllm contracts with... |
| Which product does Sarah Williams lead design for? | direct_fact | 0.08 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect compared to the reference answer, which states that Sara... |
| What is the monthly payment for Greenstone Insu... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it states there is no information about a contract be... |
| Who signed the Metropolitan Life Group contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer fails to provide the requested factual information, specifically the identity o... |
| Who signed the Atlantic Risk Solutions contract... | direct_fact | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer does not provide the correct information regarding who signed the Atlantic Risk... |
| By what percentage did Sarah Williams improve u... | comparative | 0.67 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect because it states that there is no information about Sar... |
| Which product does Jessica Liu develop for? | relationship | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it states Jessica Liu works for Insurellm developing ... |
| Who is the technical lead for the product that ... | spanning | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) | The generated answer incorrectly identifies the product associated with the $10,000/month Standard T... |
| Which product did the Senior Data Scientist bui... | spanning | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is mostly accurate but contains a significant typographical error in the produc... |
| Which product does the UX Designer who improved... | spanning | 0.00 | 1.0/5 | Retrieval Missed, Low Quality Answer (Acc: 1.0) | The generated answer incorrectly identifies the UX Designer and the product they lead design for. Ac... |
| Who signed the Metropolitan Life Group contract... | spanning | 0.17 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer fails to provide the factual information present in the reference answer. It do... |
| By what percentage did the Account Executive in... | spanning | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is factually incorrect as it names the wrong Account Executive (Alex Thomson in... |
| How many core values does the company founded b... | spanning | 0.26 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer incorrectly states that Insurellm has five core values, while the reference ans... |
| What is Alex Chen's current job title? | direct_fact | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer states that Alex Chen's current job title is "Senior Backend Software Engineer,... |
| What is the monthly cost for Apex Reinsurance's... | numerical | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer fails to provide the specific and factual information given in the reference an... |
| How many employees at Insurellm have a current ... | holistic | 0.56 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is inaccurate as it identifies only one employee with a salary under $80,000 (E... |
| What is the total contract value of all Healthl... | holistic | 0.58 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is mostly accurate in calculations for the listed contracts but incomplete as i... |
| What is the average monthly subscription cost a... | holistic | 0.50 | 2.0/5 | Low Quality Answer (Acc: 2.0) | The generated answer provides a precise calculated average monthly subscription cost ($6,750) based ... |
| Which product has the fewest active contracts a... | holistic | 0.50 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer is inaccurate compared to the reference answer, which clearly states that Marke... |
| What is the longest contract duration among all... | holistic | 1.00 | 1.0/5 | Low Quality Answer (Acc: 1.0) | The generated answer correctly identifies the longest contract duration as 48 months, which matches ... |
