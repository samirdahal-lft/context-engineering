"""
app_ui.py

Shared Streamlit presentation helpers for the "mission control" look. Imported by
the experiment pages (via the root-path shim they already set up). Streamlit-only
on purpose -- this is the VIEW layer, kept out of core/ so core/ stays
framework-agnostic.

What it provides:
    inject_css()                 -> one-time CSS for the dark console look
    experiment_header(...)       -> styled hero with a number badge
    arm_title(emoji, text)       -> a per-arm heading
    metric_chips([(label,val)])  -> compact metric pills
    LiveLog(status)              -> callable event sink that streams into st.status
"""

import queue
import threading
from html import escape

import streamlit as st

# Accent + ink, kept in sync with .streamlit/config.toml.
_ACCENT = "#00E0C6"

_CSS = f"""
<style>
/* ---- page rhythm ---- */
.block-container {{ padding-top: 2.2rem; max-width: 1200px; }}

/* ---- experiment hero ---- */
.exp-hero {{
  display: flex; align-items: center; gap: 0.9rem; margin-bottom: 0.2rem;
}}
.exp-badge {{
  flex: 0 0 auto; width: 2.4rem; height: 2.4rem; border-radius: 0.7rem;
  display: grid; place-items: center; font-weight: 800; font-size: 1.1rem;
  color: #04110f; background: {_ACCENT};
  box-shadow: 0 0 18px rgba(0,224,198,0.45);
}}
.exp-hero h1 {{ font-size: 1.5rem; margin: 0; line-height: 1.15; }}
.exp-sub {{ color: #8aa0b2; margin: 0.1rem 0 1.1rem 0; font-size: 0.93rem; }}

/* ---- per-arm heading ---- */
.arm-title {{
  font-weight: 700; font-size: 1.05rem; letter-spacing: 0.2px;
  margin: 0.2rem 0 0.5rem 0;
}}

/* ---- metric chips ---- */
.chips {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.6rem 0 0.2rem 0; }}
.chip {{
  display: flex; flex-direction: column; gap: 1px; padding: 0.4rem 0.7rem;
  background: #10151e; border: 1px solid #222c3a; border-radius: 0.6rem; min-width: 84px;
}}
.chip-v {{ font-weight: 800; font-size: 1.05rem; color: {_ACCENT}; font-variant-numeric: tabular-nums; }}
.chip-l {{ font-size: 0.7rem; color: #8aa0b2; text-transform: uppercase; letter-spacing: 0.4px; }}

/* ---- live log console (inside st.status) ---- */
.logline {{
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.8rem; line-height: 1.5; color: #aebfce;
  padding: 1px 0; border-left: 2px solid transparent; padding-left: 8px;
  animation: logfade 0.25s ease-out;
}}
.logline.metric {{ color: #cfe9e3; }}
.logline b {{ color: {_ACCENT}; }}
@keyframes logfade {{ from {{ opacity: 0; transform: translateY(2px); }} to {{ opacity: 1; transform: none; }} }}
</style>
"""


def inject_css() -> None:
    """Inject the mission-control CSS once per page run."""
    st.markdown(_CSS, unsafe_allow_html=True)


def experiment_header(num: int, title: str, subtitle: str) -> None:
    """Render the styled hero: a number badge + title, with a subtitle line."""
    st.markdown(
        f"<div class='exp-hero'><div class='exp-badge'>{num}</div>"
        f"<h1>{escape(title)}</h1></div>"
        f"<p class='exp-sub'>{subtitle}</p>",
        unsafe_allow_html=True,
    )


def arm_title(emoji: str, text: str) -> None:
    """A per-arm heading (e.g. '🐘 Naive — load everything')."""
    st.markdown(f"<div class='arm-title'>{emoji} {escape(text)}</div>", unsafe_allow_html=True)


def metric_chips(items: list[tuple[str, str]]) -> None:
    """Render compact metric pills from (label, value) pairs."""
    chips = "".join(
        f"<div class='chip'><span class='chip-v'>{escape(str(v))}</span>"
        f"<span class='chip-l'>{escape(label)}</span></div>"
        for label, v in items
    )
    st.markdown(f"<div class='chips'>{chips}</div>", unsafe_allow_html=True)


class LiveLog:
    """Callable event sink that streams experiment events into an st.status box.

    Pass an instance straight to an experiment's `on_event=` param; each event is
    rendered as a console line the instant it arrives. `answer` events are ignored
    here (the page renders the final answer in its own area).
    """

    def __init__(self, status) -> None:
        self._status = status

    def __call__(self, ev: dict) -> None:
        kind = ev.get("kind")
        if kind == "log":
            self._status.markdown(
                f"<div class='logline'>{escape(str(ev.get('text', '')))}</div>",
                unsafe_allow_html=True,
            )
        elif kind == "metric":
            self._status.markdown(
                f"<div class='logline metric'>▸ {escape(str(ev.get('label', '')))}: "
                f"<b>{escape(str(ev.get('value', '')))}</b></div>",
                unsafe_allow_html=True,
            )


_DONE = object()  # sentinel: the worker finished


def stream_run(status, run_fn, *args, **kwargs):
    """Run an experiment that accepts `on_event=`, streaming its events LIVE into
    `status` — safely.

    Agent frameworks (Strands) run the model in a worker thread, so their callbacks
    fire OFF the Streamlit script thread; writing to the UI there raises
    NoSessionContext. So we run `run_fn` in a worker that only pushes events to a
    queue, and render them here on the MAIN thread (Streamlit-safe) as they arrive.
    Returns whatever `run_fn` returns; re-raises any error it hit.
    """
    q: queue.Queue = queue.Queue()
    box: dict = {}

    def worker():
        try:
            box["result"] = run_fn(*args, on_event=q.put, **kwargs)
        except BaseException as err:          # surface on the main thread
            box["error"] = err
        finally:
            q.put(_DONE)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    log = LiveLog(status)
    while True:
        ev = q.get()                          # blocks until the next event
        if ev is _DONE:
            break
        log(ev)                               # main-thread render -> streams live
    thread.join()

    if "error" in box:
        raise box["error"]
    return box.get("result")


__all__ = [
    "inject_css", "experiment_header", "arm_title", "metric_chips", "LiveLog", "stream_run",
]
