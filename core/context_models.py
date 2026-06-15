"""
core/context_models.py

The three "labeled lunchboxes" (Pydantic models) that the whole lab speaks in.
These are framework-agnostic: NO Strands, NO Streamlit imports here on purpose,
so any layer (notebook, experiment module, UI) can use them.
"""

from pydantic import BaseModel
from typing import Literal


class ContextItem(BaseModel):
    """One piece of stuff we put in front of the model, plus its token size."""
    content: str
    source_type: Literal["system", "index", "document", "question"]
    tokens: int


class ContextPolicy(BaseModel):
    """The switch that decides HOW we build context.

    Experiment 1 used `mode` to pick load_everything vs progressive.
    Experiment 2 (Compaction) reuses `max_tokens` as the context-window ceiling and
    adds two knobs: whether to compact at all, and the fill fraction at which
    compaction fires.

    The `truncate_tool_output_to` / `clear_old_tool_results` knobs below are legacy
    from the removed Context Rot experiment (truncate + clear old tool outputs);
    they're kept so the whole lab shares one policy type, but no active experiment
    uses them.
    """
    # `mode` kept permissive so all experiments can share one policy type.
    mode: Literal["load_everything", "progressive", "naive", "engineered"] = "engineered"

    # --- budgeting knobs (legacy: the removed Context Rot experiment) ---
    max_tokens: int = 8000                       # budget / window ceiling
    truncate_tool_output_to: int | None = 1500   # cap per tool output, in tokens
    clear_old_tool_results: bool = True          # replace old raw tool outputs with a stub

    # --- Exp 2 compaction knobs (engineered arm only) ---
    compaction_enabled: bool = True              # summarize + reset history near the limit
    compaction_threshold: float = 0.8            # compact when tokens > threshold * max_tokens


class ContextTrace(BaseModel):
    """The X-ray report: where every token went."""
    segment_breakdown: dict[str, int]    # source_type -> token count
    total_tokens: int
    steps: list[dict] = []               # per-iteration: {iteration, total_tokens, needle_present}
