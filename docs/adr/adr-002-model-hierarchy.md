# ADR-002: Decoupled Model Tier Hierarchy

## Status
Accepted

## Context
RAG pipelines require multiple LLM invocations: query rewriting, semantic reranking, response generation, and evaluation scoring (judging). Running all of these tasks on a single high-tier model (e.g., GPT-4) generates high API costs and latency. Conversely, running everything on a lower-tier model (e.g., GPT-3.5 or small local models) reduces response accuracy and judgment quality. We need to match each pipeline task to a suitable model tier.

## Alternatives Considered
1.  **Unified High-Tier Model Configuration**: Run all steps on a single top-tier model. Highest accuracy but financially unsustainable for high-throughput applications.
2.  **Unified Low-Tier Model Configuration**: Run all steps on a single low-cost model. Poor response quality and unreliable evaluation scoring.
3.  **Decoupled Model Tier Configuration (Selected)**: Segment models based on task requirements: Utility vs. Generation vs. Judge.

## Decision
We decouple model definitions in a centralized configuration ([config.py](../../config.py)):
1.  **Utility Tasks (Query Rewrite, Chunking, Reranking)**: Configured to use a lightweight, fast model (`gpt-4.1-nano`). These tasks benefit from high speed and low cost, as they process intermediate pipeline stages.
2.  **Generation Tasks (User-Facing RAG Answer)**: Configured to use a balanced mid-tier model (`gpt-4.1-mini`) to ensure professional, accurate, and fluent customer responses.
3.  **Judge Tasks (LLM-as-a-Judge Evaluation)**: Configured to use a high-fidelity model (`gpt-4.1-mini` or higher) to ensure consistent, reliable, and bias-free evaluation scores.

## Consequences
*   Significantly lowers the token cost of pipeline runs.
*   Enables rapid local prototyping by allowing developers to swap any model role via environment variables (`UTILITY_MODEL`, `GENERATION_MODEL`, `JUDGE_MODEL`) without editing core codebase files.
*   Ensures evaluation results remain highly credible by retaining stronger models for the judging step.
