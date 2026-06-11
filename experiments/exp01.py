"""
experiments/exp01.py

Clean, importable logic for Experiment 1 (JIT Retrieval vs Load-Everything),
extracted from the notebook.

PURE PYTHON ONLY: no Streamlit, no notebook code, no prints, no pandas.
All configuration comes from `core.settings`; each function does one job.

Public API:
    run_naive(question)       -> dict
    run_progressive(question) -> dict

Token counts are real: naive uses the Bedrock Converse `usage`; progressive
uses the agent's accumulated usage. The per-segment `breakdown` (for the Token
X-ray) uses core.tokenizer.

Both arms return `facts_found: bool | None` — True/False when the question
matches an entry in data/evals/exp01.json, None otherwise. This shows accuracy
alongside token efficiency: the full research claim (Section 4.2) is that fewer,
focused tokens produce better answers, not just cheaper ones.
"""

import json
import time
from typing import Any

from core.settings import settings
from core.tokenizer import count_tokens


def _load_index() -> list[dict]:
    return json.loads(settings.index_path.read_text(encoding="utf-8"))


def _load_evals() -> list[dict]:
    path = settings.root / "data" / "evals" / "exp01.json"
    return json.loads(path.read_text(encoding="utf-8"))


INDEX = _load_index()
EVALS = _load_evals()


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _eval_for_question(question: str) -> dict | None:
    """Return the eval entry whose question matches, or None if not in the eval set."""
    lowered = question.strip().lower()
    return next((e for e in EVALS if e["question"].strip().lower() == lowered), None)


def _all_facts_present(answer: str, facts: list[str]) -> bool:
    """True if every expected fact appears in the answer (case-insensitive)."""
    lowered = answer.lower()
    return all(fact.lower() in lowered for fact in facts)


def _read_paper(rel_path: str) -> str:
    return (settings.root / rel_path).read_text(encoding="utf-8", errors="ignore")


def _bedrock_client():
    """Build a bedrock-runtime client (kept out of import time)."""
    import boto3

    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def _converse(prompt: str) -> dict:
    """Run one Bedrock Converse call with the configured model."""
    return _bedrock_client().converse(
        modelId=settings.bedrock_model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={
            "maxTokens": settings.output_max_tokens,
            "temperature": settings.temperature,
        },
    )


def _converse_answer(response: dict) -> str:
    return response["output"]["message"]["content"][0]["text"]


# --------------------------------------------------------------------------- #
# Arm 1 -- Naive (load everything)
# --------------------------------------------------------------------------- #
def _build_corpus_blob() -> tuple[str, dict[str, int]]:
    """Concatenate every paper; return (blob, per-paper token breakdown)."""
    parts: list[str] = []
    breakdown: dict[str, int] = {}
    for paper in INDEX:
        text = _read_paper(paper["path"])
        parts.append(f"\n\n=== {paper['title']} ===\n{text}")
        breakdown[paper["title"]] = count_tokens(text)
    return "".join(parts), breakdown


def _naive_prompt(words: list[str], question: str) -> str:
    return f"{' '.join(words)}\n\nQuestion: {question}\nAnswer:"


def _is_context_overflow(error: Exception) -> bool:
    return "too long" in str(error).lower()


def _answer_with_fit(words: list[str], question: str) -> tuple[dict, bool]:
    """Send the capped blob, shrinking on overflow.

    Returns (converse_response, truncated).
    """
    max_words = settings.naive_max_words
    truncated = len(words) > max_words
    while True:
        try:
            return _converse(_naive_prompt(words[:max_words], question)), truncated
        except Exception as error:  # noqa: BLE001 - inspect message for overflow
            if _is_context_overflow(error) and max_words > settings.naive_overflow_min_words:
                max_words = int(max_words * settings.naive_overflow_shrink_factor)
                truncated = True
                continue
            raise


def run_naive(question: str) -> dict[str, Any]:
    """Glue all papers into one prompt and answer in a single Bedrock call.

    Returns: answer, input_tokens, output_tokens, latency, breakdown, truncated,
             facts_found (bool if question is in evals, else None).
    """
    blob, breakdown = _build_corpus_blob()

    start = time.time()
    response, truncated = _answer_with_fit(blob.split(), question)
    latency = time.time() - start

    answer = _converse_answer(response)
    usage = response["usage"]
    eval_entry = _eval_for_question(question)
    return {
        "answer": answer,
        "input_tokens": usage["inputTokens"],
        "output_tokens": usage["outputTokens"],
        "latency": latency,
        "breakdown": breakdown,
        "truncated": truncated,
        "facts_found": _all_facts_present(answer, eval_entry["expected_facts"]) if eval_entry else None,
    }


# --------------------------------------------------------------------------- #
# Arm 2 -- Progressive disclosure
# --------------------------------------------------------------------------- #
def _build_index_prompt() -> str:
    lines = "".join(
        f"[{p['id']}] {p['title']} - {p['desc']}\n" for p in INDEX
    )
    return f"Available research papers:\n{lines}"


def _build_system_prompt(index_prompt: str) -> str:
    return f"""You are a research assistant with access to AI/ML papers.
{index_prompt}
When answering a question:
1. Identify which paper contains the answer
2. Call load_document with that paper's ID
3. Read it and answer with a citation

Be precise. Cite the paper ID in your answer."""


def _message_text(message: dict) -> str:
    """Join all text blocks of an assistant message into one string."""
    return "".join(b.get("text", "") for b in message.get("content", []) if "text" in b)


def _loaded_doc_ids(agent) -> list[str]:
    """Scan the agent transcript for load_document calls; return doc ids."""
    ids: list[str] = []
    for message in agent.messages:
        for block in message.get("content", []):
            if isinstance(block, dict) and block.get("toolUse", {}).get("name") == "load_document":
                ids.append(block["toolUse"]["input"]["doc_id"])
    return ids


def _progressive_breakdown(system_prompt: str, question: str, doc_loaded: str) -> dict[str, int]:
    doc_tokens = 0
    if doc_loaded != "NONE":
        doc_tokens = count_tokens(_read_paper(f"data/corpus/{doc_loaded}.txt"))
    return {
        "system+index": count_tokens(system_prompt),
        "document": doc_tokens,
        "question": count_tokens(question),
    }


def _progressive_steps(index_prompt: str, doc_ids: list[str]) -> list[str]:
    steps = [f"Read index (~{count_tokens(index_prompt)} tokens), chose a paper"]
    steps += [f"Called load_document('{doc_id}')" for doc_id in doc_ids]
    steps.append("Answered with a citation")
    return steps


def _build_agent():
    """Construct the progressive Strands agent (imports kept local)."""
    from strands import Agent
    from strands.models import BedrockModel
    from tools.load_document import load_document

    model = BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.aws_region,
        temperature=settings.temperature,
        max_tokens=settings.output_max_tokens,
    )
    index_prompt = _build_index_prompt()
    system_prompt = _build_system_prompt(index_prompt)
    agent = Agent(model=model, tools=[load_document], system_prompt=system_prompt)
    return agent, index_prompt, system_prompt


def run_progressive(question: str) -> dict[str, Any]:
    """Agent sees only a lightweight index, then loads the ONE relevant paper.

    Returns: answer, total_tokens, latency, doc_loaded, breakdown, steps,
             facts_found (bool if question is in evals, else None).
    """
    agent, index_prompt, system_prompt = _build_agent()

    start = time.time()
    result = agent(question)
    latency = time.time() - start

    doc_ids = _loaded_doc_ids(agent)
    doc_loaded = doc_ids[0] if doc_ids else "NONE"
    answer = _message_text(result.message)
    eval_entry = _eval_for_question(question)
    return {
        "answer": answer,
        "total_tokens": result.metrics.accumulated_usage["inputTokens"],
        "latency": latency,
        "doc_loaded": doc_loaded,
        "breakdown": _progressive_breakdown(system_prompt, question, doc_loaded),
        "steps": _progressive_steps(index_prompt, doc_ids),
        "facts_found": _all_facts_present(answer, eval_entry["expected_facts"]) if eval_entry else None,
    }


__all__ = ["run_naive", "run_progressive", "INDEX", "EVALS"]
