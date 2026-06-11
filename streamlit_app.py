"""
streamlit_app.py

The lab's landing page and multipage entry point. Run the whole lab with:

    streamlit run streamlit_app.py

Because this script lives at the project root, Streamlit puts the root on the
import path, so every page under pages/ can import experiments/, core/, tools/.
"""

import streamlit as st

st.set_page_config(page_title="Context Engineering Lab", layout="wide")

st.title("Context Engineering Lab")
st.markdown(
    """
> *"Context engineering is curating what the model sees so that you get a better result."*
> — Birgitta Böckeler, Thoughtworks, 2026
"""
)

st.divider()

col_a, col_b = st.columns([2, 1])
with col_a:
    st.markdown("### What is context engineering?")
    st.markdown(
        """
LLMs are **stateless** — every call starts from zero. The **context window** is the
model's entire world for one inference, and the attention budget is finite. Context
engineering is the discipline of deciding **what goes in that window, in what order,
and when to clear or compress it**.

Poor context management leads to bloated costs, degraded accuracy, and tasks that
crash mid-run. The experiments below each isolate one failure mode and show the fix —
measured with **real AWS Bedrock calls**, no fake numbers.
        """
    )
with col_b:
    st.markdown("### Quick facts")
    st.metric("Experiments built", "5")
    st.metric("Papers in corpus", "7")
    st.metric("Models", "Haiku 3.5 · Sonnet 4.6")

st.divider()
st.markdown("### Experiments — use the sidebar to navigate")

EXPERIMENTS = [
    {
        "num": "1",
        "title": "Progressive Disclosure",
        "emoji": "🔭",
        "problem": "Loading all 7 papers upfront fills the context with irrelevant text and hurts answer accuracy.",
        "fix": "Agent reads a lightweight index first, then fetches only the one relevant paper on demand.",
        "metric": "~8× token reduction · same or better accuracy",
    },
    {
        "num": "2",
        "title": "Context Rot",
        "emoji": "🦠",
        "problem": "Each agent-loop iteration appends a tool output. Context grows unbounded; the model starts missing earlier facts.",
        "fix": "Truncate documents after reading; clear tool outputs between iterations. Context stays flat.",
        "metric": "Tokens held steady vs unbounded growth",
    },
    {
        "num": "3",
        "title": "Compaction",
        "emoji": "🗜️",
        "problem": "Some tasks need their full history — you can't just truncate. Growth eventually overflows and the task dies.",
        "fix": "At 80% of the context ceiling, summarize history (compact) and keep going — the sawtooth pattern.",
        "metric": "Task completes vs crashes mid-way",
    },
    {
        "num": "4",
        "title": "External Memory",
        "emoji": "🗂️",
        "problem": "LLMs are stateless. A new session starts blank — all earlier work is gone.",
        "fix": "Write structured findings to disk (notes.json) after each paper; read them back next session.",
        "metric": "4/4 papers covered vs ~2/4 naive",
    },
    {
        "num": "5",
        "title": "Multi-Agent",
        "emoji": "🕸️",
        "problem": "One agent loading 4 papers for a multi-part task bloats context to ~80k tokens.",
        "fix": "3 isolated specialist sub-agents each work in their own window; orchestrator sees only 3 summaries.",
        "metric": "27× context compression · specialists run in parallel",
    },
]

for i in range(0, len(EXPERIMENTS), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        if i + j >= len(EXPERIMENTS):
            break
        e = EXPERIMENTS[i + j]
        with col:
            with st.container(border=True):
                st.markdown(f"#### {e['emoji']} {e['num']} — {e['title']}")
                st.markdown(f"**Problem:** {e['problem']}")
                st.markdown(f"**Fix:** {e['fix']}")
                st.caption(f"📊 {e['metric']}")
