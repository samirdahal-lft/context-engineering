"""
experiments/exp04.py

Clean, importable logic for Experiment 4 (Multi-Agent vs Single-Agent),
extracted from notebooks/exp04_multi_agent.ipynb.

PURE PYTHON ONLY: no notebook code, no plotting, no prints.

Both arms run the SAME 3-part comparison task with the SAME load_document tool;
the only difference is the architecture:

    run_single_agent()  -> dict   one agent loads every paper into one window
    run_multi_agent()   -> dict   a Sonnet orchestrator calls 3 specialist tools

Multi-agent pattern (real Agents-as-Tools):
  - Orchestrator (Sonnet 4.6) receives the task and 3 tool descriptions
  - It returns all 3 tool calls in ONE response turn (parallel batching)
  - Strands' built-in ConcurrentToolExecutor fires all 3 as asyncio tasks
  - Each sub-agent works in its own isolated context window
  - Only the summary strings enter the orchestrator's window (~1-3k tokens)

The headline is the real peak context size (max single-call inputTokens, from
the model's usage). The parent's peak excludes the sub-agents' raw work
entirely -- that is "context compression by architecture" (Section 8.3).
"""

import time
from typing import Any

from agents.subagents import (
    SUBAGENT_TOOLS,
    get_usage,
    peak_input_tokens,
    reset_usage,
)
from core.events import OnEvent, emitter, strands_tool_callback
from core.settings import settings

TASK = (
    "Compare how three areas handle long-context problems: "
    "(1) attention/architecture, (2) position effects, (3) retrieval. "
    "Cover the relevant paper(s) for each area."
)
# Every paper the single agent must pull into its one window.
SINGLE_PAPERS = ["1706.03762", "2307.03172", "2404.06654", "2005.11401"]


def _run_agent(
    system_prompt: str,
    user_prompt: str,
    tools: list,
    model_id: str | None = None,
    max_tokens: int | None = None,
    callback_handler=None,
) -> tuple[str, int, float]:
    """Run one agent; return (answer_text, real_peak_tokens, latency_seconds)."""
    from strands import Agent
    from strands.models import BedrockModel

    model = BedrockModel(
        model_id=model_id or settings.bedrock_model_id,
        region_name=settings.aws_region,
        temperature=settings.temperature,
        max_tokens=max_tokens or settings.output_max_tokens,
    )
    agent = Agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        callback_handler=callback_handler,
    )
    start = time.time()
    result = agent(user_prompt)
    latency = time.time() - start
    text = "".join(
        b.get("text", "") for b in result.message.get("content", []) if "text" in b
    )
    return text, peak_input_tokens(result), latency


def run_single_agent(on_event: OnEvent = None) -> dict[str, Any]:
    """Naive: one agent loads every paper itself and reasons in one window."""
    from tools.load_document import load_document

    emit = emitter(on_event)
    cb = strands_tool_callback(emit) if on_event is not None else None
    emit("log", text=f"📄 Loading all {len(SINGLE_PAPERS)} papers into ONE window…")
    system_prompt = (
        "You are a research analyst. Use load_document to read ALL of these papers: "
        f"{SINGLE_PAPERS}. Then write a structured comparison of how three areas "
        "handle long-context problems: (1) attention/architecture, (2) position "
        "effects, (3) retrieval. Cite paper ids."
    )
    text, peak, latency = _run_agent(system_prompt, TASK, [load_document], callback_handler=cb)
    emit("metric", label="Peak context", value=f"{peak:,} tok")
    emit("metric", label="Latency", value=f"{latency:.1f}s")
    return {"answer": text, "peak_tokens": peak, "latency": latency}


def run_multi_agent(on_event: OnEvent = None) -> dict[str, Any]:
    """Engineered: real Agents-as-Tools — the orchestrator LLM calls 3 specialist tools.

    Sonnet 4.6 batches all 3 tool calls in ONE response turn; Strands'
    ConcurrentToolExecutor fires them in parallel automatically (no extra code).
    Each specialist runs in its own isolated context window; only the summary
    string it returns enters the orchestrator's window (~1-3k tokens total).
    """
    emit = emitter(on_event)
    cb = strands_tool_callback(emit) if on_event is not None else None
    reset_usage()
    emit("log", text="🎯 Orchestrator dispatching 3 specialists (run in parallel)…")
    orchestrator_system = (
        "You are a research coordinator with three independent specialist tools: "
        "research_attention, research_position, research_retrieval. "
        "Call ALL THREE tools to gather specialist summaries, then synthesize them "
        "into a single structured comparison."
    )
    text, peak, latency = _run_agent(
        orchestrator_system,
        TASK,
        SUBAGENT_TOOLS,
        model_id=settings.orchestrator_model_id,
        max_tokens=settings.orchestrator_output_tokens,
        callback_handler=cb,
    )
    emit("log", text="🧩 Specialists returned; composing the final comparison…")
    emit("metric", label="Parent context", value=f"{peak:,} tok")
    emit("metric", label="Latency", value=f"{latency:.1f}s")
    usage = get_usage()
    return {
        "answer": text,
        "parent_peak_tokens": peak,
        "subagent_usage": usage,
        "subagent_tokens": sum(u["peak_tokens"] for u in usage),
        "latency": latency,
    }


__all__ = ["run_single_agent", "run_multi_agent", "TASK", "SINGLE_PAPERS"]
