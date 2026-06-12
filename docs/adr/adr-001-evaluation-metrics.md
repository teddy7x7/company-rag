# ADR-001: Evaluation Metrics Selection

## Status
Accepted

## Context
A major challenge in deploying Retrieval-Augmented Generation (RAG) systems for domain-specific tasks (e.g., insurance policy consultation) is verifying that answers are factually correct, complete, and relevant. Traditional text overlap metrics like BLEU or ROUGE evaluate word overlap, failing to assess semantic accuracy or compliance. Furthermore, we must separately assess the quality of the retrieval phase (which documents were fetched) and the generation phase (how the LLM answered based on those documents).

## Alternatives Considered
1.  **Lexical Overlap Metrics (BLEU / ROUGE)**: Simple to calculate but score correct semantic paraphrases poorly and fail to penalize hallucinations or subtle factual errors.
2.  **Manual Human Evaluation**: High quality, but slow, expensive, and impossible to run continuously as a gatekeeper in a CI/CD pipeline.
3.  **Semantic Retrieval Metrics + Structured LLM-as-a-Judge (Selected)**: Segment the evaluation into independent retrieval and generation verification tasks using specialized metrics.

## Decision
We implement a dual-phase quantitative evaluation system:
1.  **Retrieval Phase**: Measured using Mean Reciprocal Rank (MRR), Normalized Discounted Cumulative Gain (nDCG), and Keyword Coverage. These verify that the vector database returns high-relevance chunks and positions them correctly at the top of the context window.
2.  **Generation Phase**: Measured using a structured LLM-as-a-Judge model (via Pydantic outputs) grading answers on a 1-5 scale across three dimensions:
    *   *Accuracy*: Is the information factually correct relative to the gold standard?
    *   *Completeness*: Does it answer all parts of the question?
    *   *Relevance*: Does it answer the question directly without irrelevant information?

## Consequences
*   Allows automatic quality reporting that aligns with human judgment.
*   Enforces modular quality checks, helping developers isolate whether a regression is caused by search ranking failures or answer generation failures.
*   Increases API costs during evaluation runs due to LLM judging (mitigated by using a cost-efficient model tier and a critical cases subset).
