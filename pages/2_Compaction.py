"""
pages/2_Compaction.py

Streamlit UI for Experiment 2 (Compaction). Thin shell: collect N, call the pure
functions in experiments/exp02.py, stream each loop's activity into a live log,
and render the token sawtooth + outcome. No experiment logic lives here.
"""

import sys
from pathlib import Path

# Ensure the project root is importable, whether launched via streamlit_app.py
# or directly via `streamlit run pages/...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from app_ui import arm_title, experiment_header, inject_css, metric_chips, stream_run
from core.settings import settings
from experiments.exp02 import run_engineered, run_naive

st.set_page_config(page_title="Exp 2 · Compaction", layout="wide")
inject_css()

experiment_header(
    2,
    "Compaction — the sawtooth",
    "Some tasks NEED their history — you can't just truncate it. But unbounded growth "
    "overflows the window and the task dies. The fix: summarize at a threshold and keep going.",
)

window = settings.compaction_window_tokens
st.caption(
    f"Demo window: **{window:,} tokens** · compact at "
    f"**{int(settings.compaction_threshold * window):,}** "
    f"(small numbers so overflow is fast + visible; every token count is real)."
)

n = st.slider("Papers to read (running-synthesis task)", 2, 7, 7)


def outcome_badge(completed: bool) -> str:
    return "✅ completed" if completed else "❌ DIED (overflow)"


if st.button("▶ Run both loops", type="primary"):
    col1, col2 = st.columns(2, gap="large")

    with col1:
        arm_title("🐘", "Naive — history grows unbounded")
        with st.status("Running…", expanded=True) as s:
            naive = stream_run(s, run_naive, n)
            s.update(label="✅ Done", state="complete")
        metric_chips([
            ("Outcome", outcome_badge(naive["completed"])),
            ("Papers", f"{naive['papers_processed']} / {n}"),
            ("Peak tokens", f"{max(naive['tokens_per_iter']):,}"),
        ])
        st.caption("Real input tokens after each iteration")
        st.line_chart(naive["tokens_per_iter"])
        st.markdown("**Final theme list:**")
        st.write(naive["final_answer"])

    with col2:
        arm_title("🦊", "Engineered — compact at threshold")
        with st.status("Running…", expanded=True) as s2:
            eng = stream_run(s2, run_engineered, n)
            s2.update(label="✅ Done", state="complete")
        metric_chips([
            ("Outcome", outcome_badge(eng["completed"])),
            ("Papers", f"{eng['papers_processed']} / {n}"),
            ("Peak tokens", f"{max(eng['tokens_per_iter']):,}"),
            ("Compactions", f"{len(eng['compaction_events'])}"),
        ])
        st.caption("Real input tokens after each iteration")
        st.line_chart(eng["tokens_per_iter"])
        st.markdown("**Final theme list:**")
        st.write(eng["final_answer"])

    # The sawtooth: naive vs engineered on one axis, with the window ceiling.
    st.divider()
    st.subheader("The sawtooth — context drops at each compaction event")
    naive_s = pd.Series(naive["tokens_per_iter"], index=range(1, len(naive["tokens_per_iter"]) + 1), name="naive")
    eng_s = pd.Series(eng["tokens_per_iter"], index=range(1, len(eng["tokens_per_iter"]) + 1), name="engineered")
    chart = pd.concat([naive_s, eng_s], axis=1)
    chart["context limit"] = window
    chart.index.name = "iteration"
    st.line_chart(chart)

    st.markdown(
        "**Same task, same papers — only `compaction_enabled` changed.** "
        "Naive hits the ceiling and dies; engineered compacts, drops, and completes."
    )
else:
    st.info("Pick N and press **Run both loops** — each loop streams its iterations live.")
