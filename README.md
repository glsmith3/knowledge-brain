# Knowledge Brain

*A personal learning-capture system that turns what you learn into knowledge you can actually retrieve.*

## What is this?

Knowledge Brain converts learning conversations with an AI tutor into a structured, durable knowledge base of human-approved Markdown cards.

The premise: recognition isn't recall. It's easy to read widely and feel informed, but much harder to retrieve an idea later, in context, where it would actually change your thinking. Knowledge Brain attacks that gap in stages — capture what you learn in a format that lasts (v1), make it queryable (v2), and practice recalling it (v3).

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
5. **Ask.** Query the knowledge base with `ask.py` — structural facts straight from the file system, or free-form questions answered from the cards with citations back to the card files. See "Asking your knowledge base" below.
6. **Review.** Run short recall sessions with `quiz.py` — type what you remember, get coached against your own card, and watch the mastery readout move. See "Practicing recall" below.

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

## Asking your knowledge base

`ask.py` is the retrieval layer. It has two modes, matched to two kinds of questions.

**Structural questions get deterministic answers.** How many cards, what weeks, what topics — the file system already knows these exactly. `--index` prints them without an LLM, an API key, or a cent of cost:

```bash
python3 ask.py --index
```

```
Knowledge Brain index
=====================
Cards: 4 total — 0 personal, 4 examples

By week:
  examples/  (4 card(s), undated samples)
    - Post-Agentic AI Vocabulary
    - Platform As A Service Vs Infrastructure As A Service
    - Cloud Service Mesh
    - FTC Facebook Privacy Settlement
...
```

**Everything else gets the model.** Question mode assembles the entire knowledge base into one prompt and asks Claude, with instructions to answer only from the cards and cite the file path of every card used. It needs an [Anthropic API key](https://console.anthropic.com/) in `ANTHROPIC_API_KEY`:

```bash
python3 ask.py "what did I learn about service meshes?"
```

```
According to your knowledge base, you learned about **Cloud Service Mesh**
[examples/google-cloud/cloud-service-mesh.md]:

- Cloud Service Mesh is a Google Cloud layer built for Kubernetes that manages
  how microservices communicate with one another.
- It helps handle traffic control, secure connections between services, and
  monitoring of service-to-service activity.
...
```

If the cards can't answer, it says so instead of improvising:

```bash
python3 ask.py "what did I learn about the French Revolution?"
```

```
Not in the knowledge base. The closest related cards cover AI vocabulary,
cloud computing, and tech regulation topics, but nothing on the French
Revolution.
```

That refusal is deliberate. The tutor prompt forbids the AI from becoming the source of truth during capture; question mode enforces the same rule at retrieval. A knowledge base that quietly backfills answers from the model's general knowledge stops being a record of what you learned.

One thing to know: asking a question sends your local cards to the Anthropic API; `--index` never does.

## Retrieval design: why there's no vector database (yet)

The obvious way to build retrieval over documents is RAG: embed the cards, store vectors, retrieve the top-k matches for each question. This repo doesn't do that, on purpose.

**The knowledge base fits in one context window.** A few dozen cards is a few thousand tokens. At that scale, sending everything with every question means nothing relevant is ever left out — no retrieval step, no similarity threshold to tune, no embedding pipeline to maintain. A vector database here would be machinery the scale doesn't justify.

**Full context answers questions top-k retrieval can't.** "What topics have I covered?" and "outline what I learned in July" are questions about the collection as a whole. A retriever that sees only the k most similar cards structurally can't answer them well. Full context can, and those corpus-level questions are half the point of having a knowledge base.

**The seam for scaling is already there.** Card loading (`load_cards` in `ask.py`) is isolated from prompt assembly. If the base ever outgrows a comfortable context budget — roughly a few hundred cards, on the order of 100K tokens — an embedding-based retriever replaces that one function: embed cards, retrieve top-k, same citation contract. Nothing downstream changes. The seam is documented, not built, because building it now would be optimizing for a problem this knowledge base doesn't have.

## Practicing recall

`quiz.py` closes the loop. Capture writes cards; retrieval finds them; recall practice makes sure you can still *produce* what's on them from memory — because the premise of this whole repo is that recognition isn't recall. Re-reading your cards feels productive and proves nothing. Recounting them does.

**Check where you stand** — anytime, no API, no cost:

```bash
python3 quiz.py --status
```

```
Knowledge Brain — mastery
=========================
2026-07  [----]  0/4 solid
  new  : Cloud Service Mesh  (due now)
  new  : FTC Facebook Privacy Settlement  (due now)
  new  : Platform As A Service Vs Infrastructure As A Service  (due now)
  new  : Post-Agentic AI Vocabulary  (due now)

Due now: 4 card(s)
```

Every card starts unproven — solidity is earned by recall, never assumed. Mastery is reported by month, so "am I on top of what I learned in July?" always has a two-second answer.

**Run a session** with `python3 quiz.py` (or double-click `Quiz.command` on macOS). The session shows a card's term, you type what you remember, and Claude coaches you against your card:

```
--- FTC Facebook Privacy Settlement  (topic: Technology Regulation)
    [new card, first test]
  Type what you remember (finish with an empty line; 'q' alone to stop):
  > In 2019 the FTC fined Facebook five billion dollars and imposed sweeping
  > privacy-governance requirements because Facebook had violated an earlier
  > consent order and misled users about their data controls. ...

  GOT — This captures the card's core points precisely — the $5B penalty, the
  violation of a prior consent order, misleading users about data controls,
  and the significance of enforcement extending to ongoing corporate
  oversight and executive accountability rather than just punishment.
```

The grading rule is strict, and it's the same rule that governs capture and retrieval: **the card is the only source of truth.** Claude grades your recount against the card's text alone — a true fact that isn't on the card earns no credit, because the quiz measures recall of what you captured, not general knowledge. Feedback coaches rather than judges: what you got, then what the card actually says.

**How scheduling works.** Each card sits on a rung of a five-step ladder (3, 7, 21, 60, 120 days between reviews). Recall it and it climbs; fumble it and it drops to the bottom; cards the tutor marked high-confidence start partway up. A session asks for at most 12 cards, shakiest and most-overdue first, and anything you miss gets one more look before the session ends. There are no streaks and no daily anything — the scheduler thinks in sessions, whenever you have them, and skipping a week just makes the next session slightly longer. Reviewing more than the session asks is always offered, never expected: extra effort is welcome, but it never becomes the new baseline.

**Other modes:** `--self` runs a flashcard session (recall mentally, reveal, self-grade) with no API and no key; `--month 2026-07` scopes a session to one month's cards for a focused check-up.

Review history lives in `review-log.jsonl` — plain text, one line per review, local and never committed. Delete it and the system honestly forgets; read it and you know everything it knows. A graded session sends the card under review and your typed answer to the Anthropic API; `--self` and `--status` never call the API.

## Design decisions

**Recounting, not summarizing.** The human explains the concept to the AI, not the other way around. This is the whole point: explaining to a critical listener is a retention technique, so capture and rehearsal are the same act. An AI that summarized *for* you would defeat it — you'd file the words without ever engaging.

**Human approval is a hard gate.** Nothing is filed until you reply `yes`. The tutor proposes; you decide. This keeps misunderstandings, half-formed ideas, and the tutor's own errors out of the durable base.

**Boring, durable formats.** Cards are plain Markdown with YAML frontmatter — no database, no server, no lock-in. You can read them in any editor, grep them, and diff them in Git. It's also what let both later layers — retrieval (v2) and recall practice (v3) — build directly on the same files with no migration.

**Selective by design.** Capture happens in bursts, only when something clears the bar. A small knowledge base of things you actually understand is the feature, not a limitation to be automated away.

**Safe to re-run.** The extractor is idempotent: filing the same confirmed card twice detects the duplicate and reports it as unchanged rather than creating a second copy, so you never have to track what you've already processed.

## Roadmap

All three planned layers are now built: capture (v1), retrieval (v2), and recall practice (v3) — each reading the same plain Markdown cards directly, with no database and no migration. That was the bet behind the deliberately boring file format, and it has now paid off twice.

Still open:

- **A local web skin for review sessions.** `quiz.py` deliberately separates the recall engine from the terminal interface, the same seam pattern as retrieval. Whether a friendlier front end is worth building will be decided by the review log — evidence of how the terminal sessions actually get used — not by enthusiasm.
- **Tutor-loop resurfacing.** Old cards surfacing during new learning sessions ("you captured something related in March"). Unresolved: how to do this without turning the tutor into a distraction machine.
