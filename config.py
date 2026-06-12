"""
Centralized configuration for the Insurellm RAG system.

Design rationale:
  We differentiate model roles to balance cost vs. quality:
  - UTILITY_MODEL:    Lightweight background tasks (query rewrite, reranking, chunking).
                      Speed and cost matter more than output quality.
  - GENERATION_MODEL: User-facing answer generation — the output the user sees.
                      Quality matters; slightly higher cost is justified.
  - JUDGE_MODEL:      LLM-as-a-judge evaluation. A stronger model gives more credible scores.

All constants can be overridden via environment variables for easy experimentation.
"""

import os
from pathlib import Path

# ── Project Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT        = Path(__file__).parent
DB_NAME             = str(PROJECT_ROOT / os.getenv("DB_NAME", "preprocessed_db"))
KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "knowledge-base"

# ── Vector Store ──────────────────────────────────────────────────────────────
COLLECTION_NAME  = os.getenv("COLLECTION_NAME", "docs")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

# ── Model Hierarchy ───────────────────────────────────────────────────────────
UTILITY_MODEL    = os.getenv("UTILITY_MODEL",    "openai/gpt-4.1-nano")
GENERATION_MODEL = os.getenv("GENERATION_MODEL", "openai/gpt-4.1-mini")
JUDGE_MODEL      = os.getenv("JUDGE_MODEL",      "openai/gpt-4.1-mini")

# ── Retrieval ─────────────────────────────────────────────────────────────────
RETRIEVAL_K      = int(os.getenv("RETRIEVAL_K", "20"))  # candidates from vector DB
FINAL_K          = int(os.getenv("FINAL_K",     "10"))  # after LLM reranking

# ── Ingestion ─────────────────────────────────────────────────────────────────
AVERAGE_CHUNK_SIZE = int(os.getenv("AVERAGE_CHUNK_SIZE", "100"))
INGEST_WORKERS     = int(os.getenv("INGEST_WORKERS",     "3"))
