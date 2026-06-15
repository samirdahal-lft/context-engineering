"""
pages/3_External_Memory.py

Streamlit UI for Experiment 3 (External Memory / Note-Taking). Thin shell: call
the pure functions in experiments/exp03.py, stream each session's activity into a
live log, and render the coverage difference plus the visible external memory
(notes.json) that survived a session reset.
"""

import sys
from pathlib import Path

# Ensure the project root is importable, whether launched via streamlit_app.py
# or directly via `streamlit run pages/...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import streamlit as st

from app_ui import arm_title, experiment_header, inject_css, metric_chips, stream_run
from core.settings import settings
from experiments.exp03 import ALL_PAPERS, run_engineered, run_naive

_TITLES = {p["id"]: p["title"] for p in json.loads(settings.index_path.read_text())}

st.set_page_config(page_title="Exp 3 · External Memory", layout="wide")
inject_css()

experiment_header(
    3,
    "External Memory / Note-Taking",
    "LLMs are stateless — a new session starts blank. The fix: write structured notes to "
    "disk and read them back next session. The demo runs TWO sessions with a hard reset between.",
)

n_total = len(ALL_PAPERS)

if st.button("▶ Run both (two sessions each, with reset)", type="primary"):
    col1, col2 = st.columns(2, gap="large")

    with col1:
        arm_title("🐘", "Naive — no external memory")
        with st.status("Running…", expanded=True) as s:
            naive = stream_run(s, run_naive)
            s.update(label="✅ Done", state="complete")
        metric_chips([("Papers covered", f"{len(naive['papers_covered'])} / {n_total}")])
        st.caption("Session 2 never saw session 1's work.")
        for pid in ALL_PAPERS:
            title = _TITLES.get(pid, pid)
            if pid in naive["papers_covered"]:
                st.success(f"✅ {pid} — {title}")
            else:
                st.error(f"❌ {pid} — {title} (lost at reset)")
        st.markdown("**Final brief:**")
        st.write(naive["final_brief"])

    with col2:
        arm_title("🦊", "Engineered — external notes")
        with st.status("Running…", expanded=True) as s2:
            eng = stream_run(s2, run_engineered)
            s2.update(label="✅ Done", state="complete")
        metric_chips([
            ("Papers covered", f"{len(eng['papers_covered'])} / {n_total}"),
            ("vs naive", f"+{len(eng['papers_covered']) - len(naive['papers_covered'])}"),
        ])
        for pid in ALL_PAPERS:
            title = _TITLES.get(pid, pid)
            if pid in eng["papers_covered"]:
                st.success(f"✅ {pid} — {title}")
            else:
                st.warning(f"⚠️ {pid} — {title}")
        with st.expander("External memory (notes.json) — what session 2 read back"):
            st.json(eng["notes_snapshot"])
        st.markdown("**Final brief (synthesized from the notes):**")
        st.write(eng["final_brief"])

    st.divider()
    st.markdown(
        "**The engineered agent survived a full session reset** because its state "
        "lived outside the context window, on disk -- a structured, human-inspectable "
        "`notes.json` it could read back and resume from."
    )
else:
    st.info("Press **Run both** — each session streams its tool calls live (load_document, save_finding, read_progress).")
