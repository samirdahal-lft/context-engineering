# 🎙️ Demo Voiceover Scripts — 4 clips, one per slide

Read each aloud while you screen-record that experiment. ~60–75s each.

## Before you record (3 quick tips)
1. **Warm-up run first** — run each experiment once before recording (confirms AWS creds are
   fresh and warms the cache so the real take is faster).
2. **Two arms have a long wait** — Exp 1's naive side (~50s) and Exp 4 (~30–60s). Either talk
   through it, or **pause/cut the recording during the wait** and resume when results appear.
3. **Numbers vary slightly per run** — the scripts say "around / roughly." Glance at the actual
   on-screen number and say that.

`[Run]` = click the run button.

---

## 🎬 Clip 1 — Just-in-Time Retrieval

> "This first experiment asks a simple question: why not just put all your documents into the
> model's context? I've got seven research papers. On the **left** is the naive approach — dump
> all seven into one prompt and ask my question. On the **right** is just-in-time retrieval: the
> agent reads a tiny index first, then loads only the one paper it actually needs.
>
> Let me run both. `[Run]`
>
> Watch the right side stream what the agent's doing — it reads the index… and there, it fires
> `load_document` and pulls just **one** paper: Attention Is All You Need.
>
> And here's the result. The naive side sent around **200,000 tokens**. Just-in-time sent about
> **13,000** — roughly **15× fewer**. Look at the Token X-ray: on the left, almost all of it is
> irrelevant papers eating the attention budget; on the right, it's basically just the one paper
> that matters.
>
> And the kicker — fewer tokens didn't mean a worse answer. It's the *sharper* one, citing the
> exact section. Less context, better result. That's the whole game."

---

## 🎬 Clip 2 — Compaction

> "Sometimes you genuinely need your history — you can't just not load it. This experiment is
> about what happens when that history grows too big.
>
> I'm using a deliberately tiny **6,000-token** window so it fails fast and visibly. The task:
> read papers one by one, keep a running list of themes. **Left** is naive — just keep appending.
> **Right** is engineered — compact the history when it fills up.
>
> Let me run it. `[Run]`
>
> Watch the naive side climb — paper one, two, three, the token count keeps rising… and there —
> it crosses six thousand, overflows the window, and the task **dies**. It never finishes.
>
> Now the engineered side climbs the same way, but watch — there's the **compaction event**: it
> summarizes everything so far, and the count drops right back down. Then it keeps going and
> finishes all seven papers.
>
> That's the **sawtooth** — climb, compress, climb, compress. Same task, same papers, one flag
> different. Naive crashes; engineered survives past the window limit."

---

## 🎬 Clip 3 — External Memory

> "LLMs are stateless. When a session ends, everything in the context window is just… gone. This
> experiment shows how to survive that.
>
> I'm running the task as **two separate sessions with a hard reset** in between — a brand-new
> agent, no shared memory. **Left** has no external memory. **Right** writes its findings to a
> file on disk.
>
> Run it. `[Run]`
>
> On the right, watch session one — it reads each paper and calls `save_finding`, writing to
> notes-dot-json. Then the hard reset. Session two starts completely fresh… but it calls
> `read_progress`, pulls those notes back off disk, and picks up right where it left off.
>
> Here's the payoff. The naive agent covered only **two of four** papers — session two never saw
> session one's work. The engineered agent covered **all four**. And it's not magic — I can open
> the notes file right here and read exactly what it remembered. State that lives *outside* the
> context window survives a full reset."

---

## 🎬 Clip 4 — Multi-Agent

> "Last one, and it's my favorite. When one agent has to do a big, multi-part task, it loads
> everything into a single context window — and that window balloons.
>
> **Left** is a single agent reading all the papers itself. **Right** is a multi-agent setup: an
> orchestrator that delegates to three specialist sub-agents, each working in its own isolated
> window.
>
> Run it. `[Run]` — this one takes a little longer, so let me talk through it.
>
> Watch the orchestrator dispatch all three specialists at once — attention, position, retrieval.
> They run **in parallel**, each in its own context, and hand back just a short summary.
>
> And the numbers tell the story. The single agent's context peaked around **80,000 tokens**. The
> orchestrator? About **three thousand** — roughly **27× smaller**. All the heavy lifting happened
> in the specialists' windows, down in this table, completely hidden from the parent.
>
> And because the three ran in parallel, it's **not** three times slower — it's about the same as
> the single agent. That's **context compression by architecture**: the boundary between agents
> *is* the compression."

---

## (Optional) Closing line for the last slide
> "Four problems, four fixes, one idea: the context window is a budget you actively manage — by
> retrieving less, compressing what grows, persisting what must outlive the session, and splitting
> work when one window isn't enough. And every number you just saw came from a real model call."
