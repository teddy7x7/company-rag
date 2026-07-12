# Insurellm RAG System — Enterprise Knowledge QA with Evaluation Harness

A production-grade Retrieval-Augmented Generation (RAG) platform for insurance policy and company knowledge consultation. Built from the ground up **without LangChain abstractions**, the system implements AI-assisted semantic chunking, dual-query retrieval with LLM reranking, and a comprehensive **Evaluation-as-Code** harness with automated regression testing — all wired into a CI/CD pipeline.

> **Design philosophy**: Understand the underlying mechanisms, write every pipeline step explicitly, and prove quality with quantifiable metrics — not vibes.

---

## Technical Architecture

The system orchestrates four pipeline stages — **Ingest → Retrieve → Generate → Evaluate** — each backed by purpose-built modules rather than opaque framework wrappers.
For more details, please refer to the documents in the `docs/architecture` folder.

```mermaid
flowchart TD
    subgraph Ingestion ["1 · Ingestion Pipeline"]
        KB["Knowledge Base<br/>(Markdown files)"] --> Fetch["fetch_documents()"]
        Fetch --> Pool["multiprocessing.Pool<br/>(parallel)"]
        Pool --> LLM_Chunk["LLM Semantic Chunking<br/>(headline + summary + text)"]
        LLM_Chunk --> Embed_I["OpenAI Embedding"]
        Embed_I --> VDB[(ChromaDB<br/>Vector Store)]
    end

    subgraph Retrieval ["2 · Retrieval & Reranking"]
        User([User Query]) --> QR["Query Rewriter<br/>(Utility Model)"]
        User --> Embed_Q1["Embed original query"]
        QR --> Embed_Q2["Embed rewritten query"]
        Embed_Q1 --> VS1["Vector Search (Top-K)"]
        Embed_Q2 --> VS2["Vector Search (Top-K)"]
        VS1 --> Merge["merge_chunks()<br/>(deduplicate)"]
        VS2 --> Merge
        Merge --> Rerank["LLM Reranker<br/>(Utility Model + Pydantic)"]
    end

    subgraph Generation ["3 · Answer Generation"]
        Rerank --> Prompt["RAG Prompt Assembly"]
        Prompt --> Gen["LLM Generation<br/>(Generation Model)"]
        Gen --> Answer([Answer + Sources])
    end

    subgraph Evaluation ["4 · Evaluation Harness"]
        Answer --> RetEval["Retrieval Metrics<br/>(MRR · nDCG · Coverage)"]
        Answer --> AnsEval["LLM-as-a-Judge<br/>(Accuracy · Completeness · Relevance)"]
        RetEval --> Baseline["Baseline Snapshot<br/>(JSON)"]
        AnsEval --> Baseline
        Baseline --> Regression["Regression Detector"]
        Regression --> CICD["CI/CD Gate<br/>(exit code)"]
    end

    VDB --> VS1
    VDB --> VS2

    style Ingestion fill:#e8f5e9,stroke:#4caf50
    style Retrieval fill:#e3f2fd,stroke:#2196f3
    style Generation fill:#fff3e0,stroke:#ff9800
    style Evaluation fill:#fce4ec,stroke:#e91e63
```

---

## Key Technical Decisions

### 1. AI-Assisted Semantic Chunking (vs. Fixed-Length Splitting)

Traditional `RecursiveCharacterTextSplitter` blindly cuts text by token count, breaking semantic coherence. Instead, we call a lightweight LLM (`gpt-4.1-nano`) to split each document into **semantically complete chunks**, each containing:
- `headline` — a searchable context title
- `summary` — a dense semantic anchor for embedding quality
- `original_text` — the verbatim source for answer grounding

This approach significantly improves retrieval precision at the cost of higher ingestion latency (mitigated by `multiprocessing.Pool` parallelism and `tenacity` retry with exponential backoff).

### 2. Dual-Query Retrieval + LLM Reranking

A single embedding query often misses relevant documents when user phrasing differs from document terminology. Our retrieval strategy:
1. **Rewrite** the user's conversational query into a focused search query using LLM
2. **Execute two parallel vector searches** (original + rewritten), each returning Top-K candidates
3. **Merge and deduplicate** the combined results
4. **Rerank** via LLM with Pydantic-enforced structured output (`RankOrder`), selecting the most relevant chunks

### 3. Decoupled Model Tier Hierarchy

Not every pipeline task needs the same model. We split LLM usage into three roles centralized in [`config.py`](config.py):

| Role | Model | Purpose |
|------|-------|---------|
| **Utility** | `gpt-4.1-nano` | Query rewriting, chunking, reranking — speed & cost optimized |
| **Generation** | `gpt-4.1-mini` | User-facing RAG answers — quality optimized |
| **Judge** | `gpt-4.1-mini` | LLM-as-a-Judge evaluation — credibility optimized |

All model constants are overridable via environment variables for easy experimentation. See [ADR-002](docs/adr/adr-002-model-hierarchy.md).

---

## Quality Assurance & Evaluation Harness

Quality is not subjective — it is measured, versioned, and gated.

### Evaluation Metrics

| Phase | Metric | What It Measures |
|-------|--------|------------------|
| **Retrieval** | Mean Reciprocal Rank (MRR) | Rank position of the first relevant document |
| **Retrieval** | Normalized Discounted Cumulative Gain (nDCG) | Overall ranking quality |
| **Retrieval** | Keyword Coverage | Percentage of golden keywords captured in context |
| **Generation** | Accuracy (1-5) | Factual correctness vs. gold standard |
| **Generation** | Completeness (1-5) | Whether all parts of the question are addressed |
| **Generation** | Relevance (1-5) | Whether the answer is focused and free of irrelevant content |

Generation metrics use an **LLM-as-a-Judge** pattern with Pydantic structured outputs to ensure parseable, multi-dimensional scoring. See [ADR-001](docs/adr/adr-001-evaluation-metrics.md).

### Regression Testing Pipeline

Evaluating all 150 test questions on every commit is expensive. Instead, we use a **stratified critical-case subset** of 7 representative questions spanning all categories (`direct_fact`, `temporal`, `comparative`, `numerical`, `relationship`, `spanning`, `holistic`).

```mermaid
flowchart LR
    TestData["tests.jsonl<br/>(150 questions)"] --> EvalEngine["Evaluation Engine"]
    EvalEngine --> Snapshot["Baseline Snapshot<br/>(timestamped JSON)"]
    Snapshot --> Report["Markdown Report<br/>(auto-generated)"]
    EvalEngine --> SubsetRun["Critical Subset<br/>(7 questions)"]
    SubsetRun --> Compare["Regression Detector"]
    Compare --> Gate{"Δ > 5%?"}
    Gate -- Yes --> Fail["CI Fail<br/>(exit 1)"]
    Gate -- No --> Pass["CI Pass<br/>(exit 0)"]
```

Three CLI actions drive the workflow:
- **`run`** — Execute evaluation and print summary (exploratory)
- **`save`** — Execute, snapshot to JSON, and auto-generate Markdown report
- **`compare`** — Run critical subset, compare against latest baseline, fail on regression

See [ADR-003](docs/adr/adr-003-regression-testing.md).

### CI/CD Integration

GitHub Actions runs the fast unit test suite on every push/PR. Integration regression tests (requiring API keys) are gated behind `@pytest.mark.integration` for local or secure CI execution.

---

## Project Structure

```
.
├── app.py                     # Gradio Chat UI entry point
├── evaluator.py               # Gradio Evaluation Dashboard UI
├── config.py                  # Centralized model & DB configuration
├── utils/
│   ├── answer.py              # RAG core: rewrite → retrieve → rerank → generate
│   └── ingest.py              # ETL: fetch → LLM chunk → embed → store
├── evaluation/
│   ├── eval.py                # Retrieval & generation metric calculators
│   ├── baseline.py            # Baseline snapshot, regression detection CLI
│   ├── report.py              # Auto-generate Markdown evaluation reports
│   ├── test.py                # Pydantic data model for test questions
│   └── tests.jsonl            # 150-question evaluation dataset
├── tests/
│   ├── test_eval_metrics.py   # Unit tests: MRR, DCG, nDCG calculations
│   ├── test_answer_utils.py   # Unit tests: merge_chunks logic
│   └── test_prompt_regression.py  # Integration: critical-case regression gate
├── knowledge-base/            # Source documents (company, contracts, employees, products)
├── preprocessed_db/           # ChromaDB persistent vector store
├── docs/
│   ├── adr/                   # Architecture Decision Records (ADR-001 ~ 003)
│   ├── architecture/          # Module-level architecture overviews
│   └── evaluation-report.md   # Latest auto-generated evaluation report
└── .github/workflows/test.yml # CI pipeline (pytest on push/PR)
```

---

## Quick Start

### Prerequisites
- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) package manager

### 1. Clone & Configure
```bash
git clone https://github.com/teddy7x7/company-rag.git
cd company-rag
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (required)
```

### 2. Install Dependencies
```bash
uv sync --all-extras --dev
```

### 3. Build the Vector Store
```bash
uv run python utils/ingest.py
```

### 4. Launch the Chat UI
```bash
uv run python app.py
```
Or launch the Evaluation Dashboard:
```bash
uv run python evaluator.py
```

### 5. Run Tests
```bash
# Fast unit tests (no API keys needed)
uv run pytest -m "not integration"

# Prompt regression test (requires API keys + baseline snapshot)
uv run pytest -k test_prompt_regression
```

### 6. Manage Evaluation Baselines
```bash
# Run full evaluation and save a baseline snapshot
uv run python evaluation/baseline.py save --label "v1_baseline"

# Compare current performance against the latest baseline
uv run python evaluation/baseline.py compare
```

---

## Architecture Decision Records

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/adr/adr-001-evaluation-metrics.md) | Evaluation Metrics Selection — MRR + nDCG + LLM-as-a-Judge over BLEU/ROUGE |
| [ADR-002](docs/adr/adr-002-model-hierarchy.md) | Decoupled Model Tier Hierarchy — Utility vs. Generation vs. Judge |
| [ADR-003](docs/adr/adr-003-regression-testing.md) | Regression Testing Strategy — Critical-case subset gating for CI |

---

## Known Limitations & Future Roadmap

### Limitations
- **API Dependency**: Requires OpenAI API keys for embeddings, generation, and evaluation. No offline mode.
- **Synchronous LLM Calls**: Retrieval pipeline executes three sequential LLM calls (rewrite + 2 vector searches + rerank). An `asyncio` concurrent implementation would significantly reduce latency.
- **Knowledge Base Format**: Currently supports Markdown files only. PDF/DOCX ingestion would require additional parsers.
- **Conversation History**: No token-count truncation on chat history — extended conversations may exceed the context window.

### Roadmap
- **Async Pipeline**: Refactor retrieval and evaluation loops to use `asyncio` for concurrent LLM calls, reducing end-to-end latency.
- **Semantic Caching**: Add a Redis-based semantic cache to skip retrieval and generation for near-duplicate queries.
- **Local Model Support**: Integrate Ollama/vLLM endpoints for on-premise deployments with strict data governance requirements.
- **Agentic Workflows**: Leverage LangGraph `StateGraph` for multi-step reasoning, Human-in-the-loop review, and tool-calling capabilities.
