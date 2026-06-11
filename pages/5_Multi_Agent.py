"""
pages/5_Multi_Agent.py

Streamlit UI for Experiment 5 (Multi-Agent vs Single-Agent). Thin shell: call
the pure functions in experiments/exp05.py and render the headline -- the parent
context staying tiny while the single agent's window bloats -- plus the honest
latency tradeoff and the isolated per-sub-agent token usage.
"""

import sys
from pathlib import Path

# Ensure the project root is importable, whether launched via streamlit_app.py
# or directly via `streamlit run pages/...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from experiments.exp05 import run_multi_agent, run_single_agent

st.set_page_config(page_title="Exp 5: Multi-Agent", layout="wide")

st.title("Experiment 5 — Multi-Agent vs Single-Agent")
st.markdown(
    """
**The problem:** one agent doing a multi-part task bloats its single context with
all the exploration. **The fix:** sub-agents with isolated windows that return
only summaries -- context compression by **architecture** (Section 8.3). From the
parent's view, a sub-agent is just a tool call that returns a summary.
"""
)

if st.button("▶ Run both", type="primary"):
    with st.spinner("Single agent (loads every paper into one window)..."):
        single = run_single_agent()
    with st.spinner("Multi-agent (3 isolated sub-agents + composer)..."):
        multi = run_multi_agent()

    ratio = single["peak_tokens"] / max(multi["parent_peak_tokens"], 1)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🐘 Single agent")
        st.metric("Peak context tokens", f"{single['peak_tokens']:,}")
        st.metric("Latency", f"{single['latency']:.1f}s")
        st.markdown("**Answer:**")
        st.write(single["answer"])

    with col2:
        st.subheader("🦊 Multi-agent (orchestrator)")
        st.metric(
            "Parent context tokens",
            f"{multi['parent_peak_tokens']:,}",
            delta=f"{multi['parent_peak_tokens'] - single['peak_tokens']:,} vs single",
            delta_color="inverse",
        )
        st.metric(
            "Latency",
            f"{multi['latency']:.1f}s",
            delta=f"{multi['latency'] - single['latency']:+.1f}s vs single",
            delta_color="off",
        )
        st.metric("Context compression", f"{ratio:.0f}×")
        st.markdown("**Answer:**")
        st.write(multi["answer"])

    # Headline chart: parent window vs single window
    st.divider()
    st.subheader("Context peak — single window vs parent window")
    chart = pd.DataFrame(
        {"peak context tokens": [single["peak_tokens"], multi["parent_peak_tokens"]]},
        index=["single agent", "multi-agent parent"],
    )
    st.bar_chart(chart)

    # Sub-agent isolation table
    usage = multi["subagent_usage"]
    if usage:
        st.markdown(
            f"**Sub-agent windows (hidden from the parent — "
            f"{multi['subagent_tokens']:,} tokens total):**"
        )
        sub_df = pd.DataFrame([
            {
                "specialist": u["name"],
                "papers": ", ".join(u["papers"]),
                "peak tokens": f"{u['peak_tokens']:,}",
            }
            for u in usage
        ])
        st.dataframe(sub_df, hide_index=True, use_container_width=True)
    else:
        st.warning("No sub-agent usage recorded.")

    st.divider()
    st.info(
        "**How parallel execution works:** Sonnet 4.6 returns all 3 tool calls in ONE "
        "response turn. Strands' `ConcurrentToolExecutor` fires them as concurrent asyncio "
        "tasks automatically — total latency ≈ the slowest specialist, not their sum."
    )
else:
    st.info("Press **Run both** to compare a single window against delegated sub-agents.")
