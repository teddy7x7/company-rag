# ADR-005: AI-Assisted Semantic Chunking Strategy

## Status
Accepted

## Context
A major bottleneck in RAG pipeline performance is document chunking. Traditional text splitting strategies (e.g., `RecursiveCharacterTextSplitter` or token-based sliding windows) divide documents using strict physical constraints, such as token or character counts. This approach presents several challenges in domain-specific insurance consulting:
1.  **Semantic Context Loss**: A physical boundary can cut a sentence in half, separating a critical insurance condition from its specific monetary limit.
2.  **Lack of Search Anchors**: Raw paragraphs lack context markers. If a user asks "Who is eligible under Plan B?", a raw paragraph saying "Eligibility is restricted to..." might have low cosine similarity because the term "Plan B" only appeared at the very top of the PDF.
3.  **Low Embedding Precision**: Embedding long paragraphs directly mixes different concepts, dilute semantic representation, and degrade vector search precision.

We need a chunking strategy that preserves semantic completeness and attaches dense, searchable metadata to every text segment.

## Alternatives Considered
1.  **Fixed-Length Character Splitting (with Overlap)**: Simple and fast, but frequently splits key tables or nested bullets, leading to lost contexts.
2.  **Recursive Paragraph/Sentence Splitters**: Marginally better at respecting paragraph breaks but still fails to synthesize search anchors or structure.
3.  **AI-Assisted Semantic Layout Chunking (Selected)**: Use a lightweight LLM to read the entire document, identify semantic boundaries naturally, and return structured, metadata-rich chunks.

## Decision
We choose to implement an **AI-Assisted Semantic Chunking Strategy**:
1.  **AI-Assisted Splitting**: We use a cost-effective, fast model (`gpt-4.1-nano`) to split each document into a list of semantically coherent `Chunk` structures (defined via Pydantic).
2.  **Structured Content Extraction**: Each chunk must extract:
    *   `headline` — A concise contextual title (e.g., "Health Plan B Eligibility Requirements").
    *   `summary` — A dense semantic summary summarizing the core facts of the chunk.
    *   `original_text` — The exact, verbatim text from the document for answer grounding.
3.  **Search Index Composition**: When indexing in ChromaDB (see `Chunk.as_result()` in [ingest.py](../../utils/ingest.py)), we index a combined string containing `[Headline] [Summary] [Original Text]`. This ensures dense keyword and semantic representation for embedding queries, while preserving the exact raw text for generation.

## Consequences
*   **Significantly Improved Retrieval precision**: Retrieval metrics (MRR/nDCG) show substantial gains because user queries match the descriptive headline/summary anchors rather than fragmented sentences.
*   **Increased Ingestion Latency**: Generating chunks via LLM is slower than simple character splicing. We mitigated this by running document processing in parallel using `multiprocessing.Pool`.
*   **API Cost Overhead**: Ingesting documents now incurs LLM token costs. Using a lightweight utility model (`gpt-4.1-nano`) keeps these costs minimal (fractions of a cent per document).
*   **Resiliency to API Failures**: To prevent network timeouts or Rate Limit (HTTP 429) errors from crashing the ingestion workflow, we wrapped the chunking function with a `tenacity` retry policy using exponential backoff.
