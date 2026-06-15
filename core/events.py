"""
core/events.py

Tiny, framework-agnostic event plumbing for the live demo UI.

An experiment that wants to narrate itself accepts an optional `on_event`
callback: `Callable[[dict], None]`. It calls it with small structured events as
work happens. The Streamlit page turns those into live log lines; a notebook or
test could just print them. NO Strands / Streamlit imports here on purpose.

Event shapes (all plain dicts):
    {"kind": "log",    "text": "🔧 load_document"}
    {"kind": "metric", "label": "Input tokens", "value": 11396}
    {"kind": "answer", "text": "..."}            # the arm's final answer
"""

from typing import Callable, Optional

# An experiment-facing event sink.
OnEvent = Optional[Callable[[dict], None]]


def emitter(on_event: OnEvent) -> Callable[..., None]:
    """Return an `emit(kind, **data)` helper that's a no-op when on_event is None."""
    def emit(kind: str, **data) -> None:
        if on_event is not None:
            on_event({"kind": kind, **data})
    return emit


def strands_tool_callback(emit: Callable[..., None]) -> Callable[..., None]:
    """Build a Strands `callback_handler` that emits one log event per tool call.

    Strands streams a `contentBlockStart` event carrying `toolUse` when the model
    starts a tool call. We only parse that dict shape -- no Strands import needed.
    """
    def _handler(**kwargs) -> None:
        tool_use = (
            kwargs.get("event", {})
            .get("contentBlockStart", {})
            .get("start", {})
            .get("toolUse")
        )
        if tool_use and tool_use.get("name"):
            emit("log", text=f"🔧 {tool_use['name']}")
    return _handler


__all__ = ["OnEvent", "emitter", "strands_tool_callback"]
