# ADR-004: Framework-free Vanilla RAG Architecture Selection

## Status
Accepted

## Context
Standard RAG development often defaults to high-level framework wrappers like LangChain or LlamaIndex. While these frameworks enable rapid prototyping, they introduce substantial technical debt for production systems:
1.  **Opaque Abstractions**: High-level classes hide prompt details and API mechanics. Debugging a failed retrieval or generation involves digging through nested, framework-specific execution stacks.
2.  **Config & API Drift**: Frequent framework updates often deprecate major components, leading to pipeline breakages and configuration drift.
3.  **Dependency Bloat**: High-level libraries pull in massive, transient dependencies (e.g., unused LangChain sub-packages). This increases docker image sizes, dependency conflict risks, and startup overhead.
4.  **Limited Customization**: Fine-tuning specialized steps—such as injecting customized double-query deduplication (`merge_chunks`) or writing custom LLM rerank logic—often requires fighting the framework's pre-packaged class interfaces.

To build a robust enterprise policy QA platform (Insurellm) where data flow must be fully auditable and performant, we need complete control over the RAG pipeline.

## Alternatives Considered
1.  **Unified RAG Frameworks (LangChain / LlamaIndex)**: Fast initial setup but leads to high abstraction debt, dependency bloat, and poor traceback debuggability.
2.  **Vendor-Specific SDKs Only (OpenAI/Anthropic natively)**: Extremely lightweight but locks the codebase into a single LLM provider, complicating migration to other models or self-hosted model endpoints.
3.  **Framework-free Vanilla RAG with Lightweight Utilities (Selected)**: Write core RAG pipeline orchestration natively in Python. Standardize LLM calls through a lightweight translation layer (`litellm`) and database storage through the database's native client (`chromadb`).

## Decision
We choose to implement a **Framework-free Vanilla RAG Architecture**:
1.  **No Abstraction Wrappers**: We build the four pipeline stages (Ingest, Retrieve, Generate, Evaluate) entirely from scratch using vanilla Python.
2.  **Lightweight Interface Standardization**: We use `litellm` solely as a model-agnostic completion wrapper (supporting unified model invocation schemas without workflow orchestration code) and `chromadb` for direct vector queries.
3.  **Explicit Data Flow**: Every pipeline step (e.g., calling the embedding API, rewriting user queries, merging lists, rendering prompts) is explicitly written in plain Python.

## Consequences
*   **100% Traceability**: Eliminates framework tracebacks. Developers can insert breakpoints and trace issues (e.g., prompt formatting errors or retrieval misses) directly inside standard Python loops.
*   **Dependency Slimming**: We successfully pruned 14 unused packages from `pyproject.toml` (including all `langchain-*` libraries), leaving only 9 core packages, resulting in a cleaner development environment and much faster dependency synchronization.
*   **Precision Control**: Enables custom algorithmic optimization at individual stages (e.g., custom parallel dual-query vector search, customized keyword coverage calculation) without framework constraint.
*   **Increased Code Ownership**: The development team must implement standard components (like query rewriters and chunk-merging utilities) manually, but this increases understanding and long-term control of the system.
