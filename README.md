# Knowledge Brain

*A personal learning-capture system that turns what you learn into knowledge you can actually retrieve.*

## What is this?

Knowledge Brain converts learning conversations with an AI tutor into a structured, durable knowledge base of human-approved Markdown cards.

The premise: recognition isn't recall. It's easy to read widely and feel informed, but much harder to retrieve an idea later, in context, where it would actually change your thinking. Knowledge Brain attacks that gap in stages — capture what you learn in a format that lasts (v1), make it queryable (v2, planned), and practice recalling it (v3, planned).

It is deliberately not an automatic note-taker. Every card in the knowledge base was explained by a human, challenged by an AI tutor, and explicitly approved before being filed. The knowledge base contains only what cleared that bar.

## Why does it exist?

I read and listen to a lot about AI — Hacker News, podcasts, technical articles — and I kept hitting the same failure: when a topic came back around, I recognized it, but I couldn't retrieve it in context to make a difference in my thinking.

Traditional notes didn't fix this. Notes capture information, but they don't make you practice it, and they pile up in formats that nothing else can build on. Automatic AI note-capture is worse: it preserves everything, including your misunderstandings, without ever making you engage.

So I built a system around a different capture mechanism: **recounting**. Instead of the AI summarizing content for me, I explain what I learned *to* the AI, which is prompted to push back — ask clarifying questions, catch errors, tighten the explanation — before anything is saved. Explaining a concept to a critical listener is itself a proven retention technique; here, the act of capturing knowledge doubles as the first rehearsal of it.

## How it works

The pipeline has four stages:

1. **Learn.** Out in the world, on human-made sources — an article, a podcast episode, a discussion thread.
2. **Recount.** Start a session with the tutor (a custom GPT running `system_prompt.md`) and explain what you learned, including where you learned it. The tutor's job is to interrogate the explanation: clarify, correct, and compress it into a candidate card — a `learned` block with a term, topic, tags, source, confidence level, and a short definition.
3. **Approve.** You review the card and reply `yes`, `edit: ...`, or `skip`. Nothing enters the knowledge base without explicit approval. Confirmed cards are saved (currently by hand) into the `knowledge-inbox/` staging folder.
4. **File.** Run the extractor — `python extract_learnings.py <inbox-file>` — which converts the confirmed YAML into a Markdown card with structured frontmatter, filed under `knowledge/week-of-YYYY-MM-DD/<topic>/`. Re-running on the same file is safe: identical cards are detected and reported as unchanged rather than duplicated.

The output format is intentionally boring: plain Markdown files with YAML frontmatter, organized chronologically by week. Boring formats are durable, human-readable, and machine-consumable — which is what lets future layers (retrieval, quizzing) build directly on the same files without migration.

Capture happens in bursts — when something is genuinely worth keeping, not on a schedule. The knowledge base is small by design.

This repository ships with a few representative cards in [`examples/`](examples/) so you can see the output format. My own knowledge base stays local: the pipeline files real cards to `knowledge/`, which is not tracked in this repo.

## Quickstart

**Prerequisites:** Python 3 (tested on 3.9) and Git. A ChatGPT account for the tutor.

**1. Clone and install.**

```bash
git clone https://github.com/<your-account>/knowledge-brain.git
cd knowledge-brain
python3 -m pip install -r requirements.txt
```

The only dependency is PyYAML. To keep it isolated, you can create a virtualenv first with `python3 -m venv .venv && source .venv/bin/activate`.

**2. Set up the tutor.** In ChatGPT, create a Custom GPT and paste the full contents of [`system_prompt.md`](system_prompt.md) as its instructions. This is the critical listener you'll recount your learning to. *(This step is done in the ChatGPT UI, so it's the one part of this guide not verified by a script.)*

**3. Capture a card.** Recount something you learned to the tutor. It will push back — ask clarifying questions, catch errors, make you compress the idea — and then propose a `learned` card in YAML. Reply `yes`, `edit: ...`, or `skip`. At the end of the session, ask it to export, and it hands you a `.txt` of the confirmed cards. Drop that file into `knowledge-inbox/`.

**4. File the card.** Run the extractor on your inbox file:

```bash
python3 extract_learnings.py knowledge-inbox/session-2026-07-23.txt
```

```
📅 Filing into week folder: knowledge/week-of-2026-07-20
📥 Treating raw learned YAML file as confirmed.
✅ created: knowledge/week-of-2026-07-20/software-engineering/idempotency.md
```

The card lands at `knowledge/week-of-YYYY-MM-DD/<topic>/<slug>.md` with YAML frontmatter. The week folder is anchored to the Monday of that week, so a card learned on Thursday the 23rd files under `week-of-2026-07-20`.

**5. Verify dedup.** Run the exact same command again. Nothing is duplicated:

```
⏸️  unchanged: knowledge/week-of-2026-07-20/software-engineering/idempotency.md
```

## Design decisions

**Recounting, not summarizing.** The human explains the concept to the AI, not the other way around. This is the whole point: explaining to a critical listener is a retention technique, so capture and rehearsal are the same act. An AI that summarized *for* you would defeat it — you'd file the words without ever engaging.

**Human approval is a hard gate.** Nothing is filed until you reply `yes`. The tutor proposes; you decide. This keeps misunderstandings, half-formed ideas, and the tutor's own errors out of the durable base.

**Boring, durable formats.** Cards are plain Markdown with YAML frontmatter — no database, no server, no lock-in. You can read them in any editor, grep them, and diff them in Git. This is also what lets planned layers (retrieval, quizzing) build directly on the same files with no migration.

**Selective by design.** Capture happens in bursts, only when something clears the bar. A small knowledge base of things you actually understand is the feature, not a limitation to be automated away.

**Safe to re-run.** The extractor is idempotent: filing the same confirmed card twice detects the duplicate and reports it as unchanged rather than creating a second copy, so you never have to track what you've already processed.

## Roadmap

v1 (this repo) is the capture-and-file pipeline. The later layers are designed but not built — and they're the reason the output format is deliberately plain:

- **v2 — Retrieval.** Ask questions across the knowledge base and get answers with citations back to the specific card files, so a learning can resurface in context when it's relevant.
- **v3 — Spaced-repetition quizzing.** Turn the same cards into recall practice on a review schedule, closing the loop from capture to long-term retention.

Both build on the existing Markdown-plus-frontmatter files. No format change required.
