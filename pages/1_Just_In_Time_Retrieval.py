"""
pages/1_Just_In_Time_Retrieval.py

Streamlit UI for Experiment 1 (template page for the "mission control" look).
Thin shell: collect a query, call experiments/exp01.py, stream each arm's
activity into a live log, and render metrics + the Token X-ray. No experiment
logic lives here.
"""

import sys
from pathlib import Path

# Ensure the project root is importable, so this page works whether launched via
# `streamlit run streamlit_app.py` or directly via `streamlit run pages/...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from app_ui import arm_title, experiment_header, inject_css, metric_chips, stream_run
from experiments.exp01 import run_naive, run_progressive

st.set_page_config(page_title="Exp 1 · Just-in-Time Retrieval", layout="wide")
inject_css()

experiment_header(
    1,
    "Just-in-Time Retrieval",
    "Why not just put all the documents in the context? Watch the Token X-ray show "
    "exactly where every token goes — load-everything vs an index + one fetched paper.",
)


def token_xray(breakdown: dict[str, int]) -> None:
    """Draw a horizontal bar of where tokens go (largest at top)."""
    df = pd.DataFrame({"tokens": breakdown}).sort_values("tokens", ascending=True)
    st.bar_chart(df, horizontal=True)


def facts_badge(facts_found) -> None:
    if facts_found is True:
        st.success("✅ Key facts present in answer")
    elif facts_found is False:
        st.error("❌ Expected facts missing from answer")


query = st.text_input("Query", value="What do attention scores sum to, and why?")

if st.button("▶ Run both arms", type="primary"):
    col1, col2 = st.columns(2, gap="large")

    with col1:
        arm_title("🐘", "Naive — load everything")
        with st.status("Running…", expanded=True) as s:
            naive = stream_run(s, run_naive, query)
            s.update(label="✅ Done", state="complete")
        metric_chips([
            ("Input tokens", f"{naive['input_tokens']:,}"),
            ("Latency", f"{naive['latency']:.1f}s"),
        ])
        if naive["truncated"]:
            st.warning("Too big to fit — some papers were dropped to fit the window.")
        facts_badge(naive.get("facts_found"))
        st.markdown("**Answer:**")
        st.write(naive["answer"])
        st.caption("Token X-ray — tokens per paper")
        token_xray(naive["breakdown"])

    with col2:
        arm_title("🦊", "Just-in-Time — load on demand")
        with st.status("Running…", expanded=True) as s2:
            prog = stream_run(s2, run_progressive, query)
            s2.update(label="✅ Done", state="complete")
        metric_chips([
            ("Total tokens", f"{prog['total_tokens']:,}"),
            ("Latency", f"{prog['latency']:.1f}s"),
            ("Loaded", prog["doc_loaded"]),
        ])
        facts_badge(prog.get("facts_found"))
        st.markdown("**Answer:**")
        st.write(prog["answer"])
        st.caption("Token X-ray — tokens per segment")
        token_xray(prog["breakdown"])

    # Headline comparison strip
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Token reduction", f"{naive['input_tokens'] / max(prog['total_tokens'], 1):.1f}×")
    m2.metric("Naive tokens", f"{naive['input_tokens']:,}")
    m3.metric(
        "Just-in-Time tokens",
        f"{prog['total_tokens']:,}",
        delta=f"{prog['total_tokens'] - naive['input_tokens']:,} vs naive",
        delta_color="inverse",
    )
else:
    st.info("Enter a query and press **Run both arms** to compare — each arm streams its steps live.")
