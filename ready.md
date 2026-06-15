# 🎬 Demo Ready — Context Engineering Lab

A presenter's script for demoing the lab live. Each experiment has a **Problem →
Run → Watch → Fix → Headline** beat. Every number on screen is a **real AWS Bedrock
call** — nothing is faked, so lean into that.

> Total run time: **~10–12 min** for all four, or pick two for a ~5 min version
> (Exp 1 + Exp 4 make the tightest story).

---

## ⏱️ Before you start (2 min setup)

```bash
# 1. Make sure AWS creds in .env are fresh (they expire every few hours).
#    If a run errors with "ExpiredToken", refresh them and retry.
# 2. Launch the lab:
.venv/bin/streamlit run streamlit_app.py
# 3. Open the browser tab it prints (usually http://localhost:8501).
```

- Have the **sidebar** visible — it lists the 4 experiments in order.
- Dark "mission control" theme loads automatically.
- **Do a throwaway warm-up run** of Exp 1 before the audience arrives so the first
  real run in front of them is warm (and to confirm creds work).

### The 60-second opener (say this on the landing page)

> "LLMs are **stateless** — every call starts from zero, and the **context window** is
> the model's entire world for that one inference. Context engineering is the craft of
> deciding **what goes in that window, in what order, and when to clear or compress it.**
> Get it wrong and you get bloated cost, worse accuracy, or a task that crashes mid-run.
> These four experiments each take one failure mode, show the naive version breaking,
> and show the fix — measured with **real model calls**. Watch the logs on each side:
> you'll see exactly what the agent is doing, live."

**The through-line** (point at the 4 cards): each experiment is one move in the same game.
1. **Don't load what you don't need.** (retrieval)
2. **When history must grow, compress it.** (compaction)
3. **When the session ends, persist outside the window.** (memory)
4. **When one window isn't enough, split the work across agents.** (architecture)

Every page is the same shape: **🐘 naive (the problem)** on the left, **🦊 engineered
(the fix)** on the right, each streaming its own live activity log.

---

## 1️⃣ Just-in-Time Retrieval — *"Why not just put everything in the context?"*

**PROBLEM (say):** "The obvious move is to dump all 7 papers into the prompt and ask
your question. But most of that text is irrelevant — it eats the attention budget and
can actually *hurt* the answer. More context isn't free."

**RUN:** Keep the default query (*"What do attention scores sum to, and why?"*) →
click **▶ Run both arms**.

**WATCH (point):**
- 🐘 Naive log: *"Loading all 7 papers… sending the whole corpus to the model."* The
  **Token X-ray** shows a huge bar — most of it irrelevant papers.
- 🦊 Just-in-Time log streams: *"📋 Reading the index… 🔧 `load_document` … 📄 Loaded only
  1706.03762."* It read a tiny index, picked the **one** relevant paper, and loaded just that.

**FIX (say):** "The index is the *map*; `load_document` fetches only the *territory* it
needs. Same question, a fraction of the tokens."

**HEADLINE (point at the comparison strip):** "**~8× fewer tokens** — and the answer
still cites the right paper, Section 3.2.1. Cheaper *and* sharper."

**TRANSITION:** "But sometimes you genuinely need the history. You can't just not load
it. What then?"

---

## 2️⃣ Compaction — *"When history must grow but the window won't"*

**PROBLEM (say):** "Some tasks need their running history — a synthesis that builds
across many documents. But history that grows forever eventually **overflows the window
and the task dies**. You can't truncate it away; you'd lose the work."

**SET-UP (point at the caption):** "We use a deliberately tiny **6,000-token** demo
window so overflow happens fast and visibly. Every token count is real."

**RUN:** Leave the slider at **7 papers** → **▶ Run both loops**.

**WATCH (point):**
- 🐘 Naive log climbs each iteration: *"📄 Paper 5/7 — 6,066 tok"* → *"💥 Overflow! task
  dies."* It stops at the ceiling. **Outcome: ❌ DIED.**
- 🦊 Engineered log climbs the same way, then *"⚡ Compaction fired after paper 5 —
  history summarized, context reset"* → tokens drop back to ~1,100 → it keeps going and
  **finishes all 7. Outcome: ✅ completed.**

**FIX (say):** "At 80% full, it **summarizes the history recall-first**, replaces the raw
turns with that summary, and continues. That's the **sawtooth** — climb, drop, climb,
drop — staying under the ceiling."

**HEADLINE (point at the sawtooth chart):** "Same task, same papers — only
`compaction_enabled` changed. Naive crashes; engineered survives past the window limit."

> **If asked / be honest:** the chart proves *survival* (the sawtooth). Whether the
> summary perfectly preserves every early theme is something we'd measure with a coverage
> check — it's the one claim here we haven't instrumented yet.

**TRANSITION:** "Compaction keeps state *inside* the window. But when the session ends,
even that is gone. How do you remember across a full reset?"

---

## 3️⃣ External Memory — *"LLMs are stateless; give them a notebook"*

**PROBLEM (say):** "When a session ends, the context is gone — a new session starts
blank and repeats work or loses decisions. We simulate this honestly: the demo runs the
task as **two separate sessions with a hard reset** (a brand-new agent) between them."

**RUN:** **▶ Run both (two sessions each, with reset)**.

**WATCH (point):**
- 🐘 Naive log: *"🅰️ Session 1 … ♻️ HARD RESET … 🅱️ Session 2: final brief with NO memory
  of session 1."* It only covers the 2 papers session 2 saw.
- 🦊 Engineered log: *"🔧 `save_finding`"* in session 1, then after the reset
  *"🔧 `read_progress`"* recovers the notes, then *"🧩 Synthesizing from notes.json."*
- **Open the `notes.json` expander** — show the real, human-readable artifact on disk,
  with the `task` and all four findings.

**FIX (say):** "State lives **outside** the context window — a structured `notes.json`
the agent writes as it works and reads back next session. It survives a total reset
because it never depended on the window."

**HEADLINE (point at the coverage badges):** "**4/4 papers covered vs 2/4** for naive.
And it's not a black box — you can open the memory and read it."

**TRANSITION:** "Compaction and memory manage *one* window over time. The last move
changes the **architecture** itself."

---

## 4️⃣ Multi-Agent — *"Compression by architecture"*

**PROBLEM (say):** "One agent doing a multi-part task has to pull **every** source into
**one** window — it balloons to ~80k tokens, all competing for attention at once."

**RUN:** **▶ Run both**. *(This one is the slowest — ~30–60s. Talk over it.)*

**WATCH (point):**
- 🐘 Single agent log: *"📄 Loading all 4 papers into ONE window."* Peak context is huge.
- 🦊 Multi-agent log: *"🎯 Orchestrator dispatching 3 specialists…"* then **three tool
  calls fire** — *"🔧 `research_attention` … 🔧 `research_position` … 🔧 `research_retrieval`"*
  — and *"🧩 Specialists returned; composing the final comparison."*
- Scroll to the **sub-agent table**: each specialist did ~12–48k tokens of work **in its
  own window**, hidden from the parent.

**FIX (say):** "Each specialist works in an **isolated window** and returns only a short
summary. The orchestrator only ever sees three summaries — never the raw papers. The
*boundary between agents is the compression.*"

**HEADLINE (point at the metric chips + bar chart):** "Parent context **~3k tokens vs
~80k** for the single agent — about **27× smaller**. And because Sonnet returns all three
tool calls in one turn, Strands runs them **in parallel** — so it's *comparable or faster*
than the single agent (~29s vs ~38s), **not 3× slower.**"

> **If asked / be honest:** we orchestrate the three specialists *explicitly* rather than
> trusting a small model to decide to delegate (it sometimes answers from memory and skips
> the tools). The isolation and the numbers are real and reproducible.

---

## 🎯 Closing (30 sec)

> "Four failure modes, four fixes, one idea: **the context window is a budget you actively
> manage** — by retrieving less, compressing what grows, persisting what must outlive the
> session, and splitting work when one window isn't enough. And every number you saw came
> from a real model call, with the work streaming live so you could see it happen."

---

## 🛟 If something goes wrong (Q&A / troubleshooting)

| Symptom | Fix |
|---|---|
| `ExpiredTokenException` mid-demo | AWS creds in `.env` expired (~few hours). Refresh them, rerun the arm. |
| A run feels slow | Naive arms send a lot of tokens (Exp 1) or run agents (Exp 4). Narrate over it — the live log shows it's working, not frozen. |
| "Are these numbers real?" | Yes — `usage.inputTokens` from each Converse call; CountTokens for the X-ray. Nothing hardcoded. |
| "Why is multi-agent not faster than 3×?" | The 3 specialists run **concurrently**, so total ≈ the slowest one, not the sum. |
| "Does compaction lose information?" | Honest answer: it provably *survives* (the sawtooth); theme-preservation isn't measured yet. |
| Logs appear all at once for an arm | Streamlit runs the two arms sequentially; within an arm the steps stream live. Expected. |

**Model note:** Exp 1–3 use **Claude 3.5 Haiku**; Exp 4's orchestrator + specialists use
**Claude Sonnet 4.6** (the only newer model enabled on this account).
