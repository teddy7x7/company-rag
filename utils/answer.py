from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential

# Debugging litellm
# import os

# must set before "import litellm"
# logging.getLogger("LiteLLM").setLevel(logging.DEBUG)
# os.environ["LITELLM_LOG"] = "DEBUG"  # or "INFO"

from litellm import completion

load_dotenv(override=True)

import config

# openai = OpenAI() # move into fetch_context_unranked function, to avoid initilizing OpenAI unnecessarily.

chroma = PersistentClient(path=config.DB_NAME)
collection = chroma.get_or_create_collection(config.COLLECTION_NAME)

wait = wait_exponential(multiplier=1, min=10, max=240)

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.

The Knowledge Base covers four areas:
- **Company**: Insurellm's history, culture, careers, and overview
- **Products**: Eight AI-powered insurance platforms — Carllm (auto), Homellm (home), Lifellm (life), Healthllm (health), Bizllm (commercial), Claimllm (claims processing), Markellm (marketplace), and Rellm (enterprise reinsurance)
- **Employees**: Profiles of Insurellm's 32 current employees, including roles, compensation, and performance history
- **Contracts**: Details of Insurellm's 32 active client contracts, including terms, pricing, and SLAs

Your answer will be evaluated for accuracy, relevance and completeness, so make sure it only answers the question and fully answers it.
If you don't know the answer, say so, or ask for clarification.
If a question falls outside the above areas, politely say so and suggest what kinds of questions you can help with.
For context, here are specific extracts from the Knowledge Base that might be directly relevant to the user's question:
{context}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""


class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )


@retry(wait=wait)
def rerank(question, chunks):
    system_prompt = """
You are a document re-ranker.
You are provided with a question and a list of relevant chunks of text from a query of a knowledge base.
The chunks are provided in the order they were retrieved; this should be approximately ordered by relevance, but you may be able to improve on that.
You must rank order the provided chunks by relevance to the question, with the most relevant chunk first.
Reply only with the list of ranked chunk ids, nothing else. Include all the chunk ids you are provided with, reranked.
"""
    user_prompt = f"The user has asked the following question:\n\n{question}\n\nOrder all the chunks of text by relevance to the question, from most relevant to least relevant. Include all the chunk ids you are provided with, reranked.\n\n"
    user_prompt += "Here are the chunks:\n\n"
    for index, chunk in enumerate(chunks):
        user_prompt += f"# CHUNK ID: {index + 1}:\n\n{chunk.page_content}\n\n"
    user_prompt += "Reply only with the list of ranked chunk ids, nothing else."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = completion(model=config.UTILITY_MODEL, messages=messages, response_format=RankOrder)
    reply = response.choices[0].message.content
    order = RankOrder.model_validate_json(reply).order
    return [chunks[i - 1] for i in order]


def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata['source']}:\n{chunk.page_content}" for chunk in chunks
    )
    system_prompt = SYSTEM_PROMPT.format(context=context)
    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )


@retry(wait=wait)
def rewrite_query(question, history=[]):
    """Rewrite the user's question to be a more specific question that is more likely to surface relevant content in the Knowledge Base."""
    message = f"""
You are in a conversation with a user, answering questions about the company Insurellm.
You are about to look up information in a Knowledge Base to answer the user's question.

This is the history of your conversation so far with the user:
{history}

And this is the user's current question:
{question}

Respond only with a short, refined question that you will use to search the Knowledge Base.
It should be a VERY short specific question most likely to surface content. Focus on the question details.
IMPORTANT: Respond ONLY with the precise knowledgebase query, nothing else.
"""
    response = completion(model=config.UTILITY_MODEL, messages=[{"role": "system", "content": message}])
    return response.choices[0].message.content


def merge_chunks(chunks1, chunks2):
    merged = chunks1[:]
    existing = [chunk.page_content for chunk in chunks1]
    for chunk in chunks2:
        if chunk.page_content not in existing:
            merged.append(chunk)
    return merged


def fetch_context_unranked(question):
    openai = OpenAI()
    query = openai.embeddings.create(model=config.EMBEDDING_MODEL, input=[question]).data[0].embedding
    results = collection.query(query_embeddings=[query], n_results=config.RETRIEVAL_K)
    chunks = []
    for result in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append(Result(page_content=result[0], metadata=result[1]))
    return chunks


def fetch_context(original_question):
    rewritten_question = rewrite_query(original_question)
    chunks1 = fetch_context_unranked(original_question)
    chunks2 = fetch_context_unranked(rewritten_question)
    chunks = merge_chunks(chunks1, chunks2)
    return rerank(original_question, chunks)[:config.FINAL_K]


@retry(wait=wait)
def answer_question(question: str, history: list[dict] = []) -> tuple[str, list]:
    """
    Answer a question using RAG and return the answer and the retrieved context.
    Used by the evaluation pipeline (synchronous, non-streaming).
    """
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)
    response = completion(model=config.GENERATION_MODEL, messages=messages)
    return response.choices[0].message.content, chunks


def answer_question_stream(question: str, history: list[dict] = []):
    """
    Answer a question using RAG with token-by-token streaming.
    Used by the Gradio Chat UI (app.py) for a responsive experience.

    Yields:
        (partial_answer: str, chunks: list | None)
        - First yield : ("", chunks) — retrieval complete, context ready to display
        - Subsequent  : (accumulated_text, None) — streaming tokens, chunks already sent
    """
    chunks = fetch_context(question)
    messages = make_rag_messages(question, history, chunks)

    # Yield context immediately so the UI can render the right panel without waiting
    yield "", chunks

    response = completion(model=config.GENERATION_MODEL, messages=messages, stream=True)
    accumulated = ""
    for part in response:
        delta = part.choices[0].delta.content or ""
        if delta:
            accumulated += delta
            yield accumulated, None
