# Knowledge Brain

*An experiment in using AI for knowledge retention. An AI tutor quizzes me on Shakespeare, every right answer becomes a card, and spaced recall checks weeks later that I still know it.*

## The experiment

Here's the question I'm trying to answer: can an AI tutor make knowledge stick, instead of just making it available?

The premise is that recognition isn't recall. It's easy to read widely and "feel" informed, but much harder to retrieve an idea later in context, or in conversation. Most tools built on AI make the first problem worse. They summarize, they answer, they make everything one search away, and none of that puts anything in your head. So this project tries the opposite: the AI never hands me knowledge. It asks for it. Everything I know has to come out of my own mouth before it gets saved, and then it has to come out again, from memory, on a schedule.

I've been running the experiment on my own Shakespeare knowledge base, which lets me combine two things I'm interested in: AI's effect on retention, and the Bard's plays. Shakespeare turns out to be a good subject for this. There's a lot to know, I care about knowing it, and I can't fake my way through "What happens after the play-within-the-play?" But don't leave yet! Nothing in the system is Shakespeare-specific. You could use these tools to track mastery of any text-based knowledge base you want. The same pipeline runs a brain about large language models and one about vector search.

It is deliberately not an automatic note-taker. Every card in the knowledge base was produced by a human, challenged by an AI tutor, and explicitly approved before being filed. The knowledge base contains only what cleared that bar.

## How a session goes

Say it's a Tuesday evening and I want to work on *Henry IV, Part 1*. I open Claude Code in this folder and type `/memory-mine`.

The tutor asks what I want to be quizzed on, confirms the subject, and starts asking. The questions are open by design: "Why does Hal reject Falstaff?" rather than "Who does Hal reject at the end?" I type what I remember. Then one of three things happens:

- **I'm right.** The tutor drafts a card from my answer, tightened to a line, in my words, and waits for my yes. I say yes, and the card is filed.
- **I'm half right.** It digs in with follow-up questions, then asks whether I want a card out of what I established.
- **I'm wrong, or I don't know.** No card, and it does not tell me the answer. The question gets saved and comes back in a later session. Looking the answer up would be recognition; the point is to recall it.

If the questions are giving too much away, I say "more open." If they're too vague to answer, "more specific." "Easier," "harder," and "challenge" (for a question I think is wrong) round out the vocabulary. After ten questions it offers to keep going. When I stop, it lists the cards it filed and how many questions I missed, without saying which.

Twice a week, I also run a review session: `python3 quiz.py`. It shows me the question on each card that's due, I type the answer from memory, and Claude grades me against my own card. Recall it and the card moves up a ladder (3, 7, 21, 60, then 120 days before I see it again). Fumble it and it drops back to the bottom. The session opens and closes with a mastery readout, so I always know where I stand:

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

Every card starts unproven. Solidity is earned by recall, never assumed.

That's the whole loop: get asked, answer from memory, approve a card, get asked again later. The rest of this README is what the loop has taught me, the rules it runs on, and how to run it yourself.

## What the experiment has shown so far

None of these were in the original design. Each came from using the system and noticing what worked, and what didn't.

**Quizzing beats recounting when the knowledge is already yours.** The first version of this project only captured by recounting: I'd explain something I'd just read, the tutor would push back, and a card would come out. That works for new material. Then I pointed it at Shakespeare and found that most of what I know about the plays was already in my head, and writing cards from memory is strangely hard. You don't know what you know until something asks. Being quizzed produces more cards per session than recounting ever did, and it means I spend most of the session actually recalling, which is the part that drives retention anyway.

**The grain of the question matters more than anything else about it.** My first quiz sessions produced questions so full of plot that the answer was sitting in them: "Who kills Polonius behind the arras?" leaks the arras. The rule now is that a question may not contain a fact that would itself make a good card. But no rule gets the grain right every time, and the real fix was letting me adjust it mid-session with a word or two. A tool you can tune while you use it is a tool you keep using.

**Cards must be tiny.** My first cards were four-sentence paragraphs, and I couldn't recall a single one cold. One idea per card, around twenty words, and recall became possible. Five sharp cards beat one encyclopedic card every time.

**Never reveal the answer.** The hardest rule to keep and the most important one. When I miss a question, every instinct says "just tell me." But the moment the tutor tells me, I've recognized the answer instead of recalling it, and the card I'd make from it would be the tutor's knowledge, not mine. So the question goes back in the queue and comes back later, when recalling it counts for something.

**Culling is part of owning a knowledge base.** I've deleted plenty of cards. A card that stopped earning its place is noise in every future session, and a base you've pruned is one you trust.

**Sessions, not streaks.** Twice a week for twenty minutes is my real number, so that's what the scheduler assumes. Nothing counts days, nothing nags, a skipped week just means a slightly longer session, and doing extra never becomes the new expectation.

**The friction was in capture, not on the screen.** The tutor originally lived in ChatGPT, which meant every card took four apps: chat, download, Finder, terminal. I nearly built a graphical interface to fix that. Instead the tutor moved into Claude Code, where it runs beside the scripts and files cards directly, and the friction disappeared without a single screen being built.

## The rules it runs on

A few principles hold the whole thing together, and the code enforces them rather than hoping.

**The card is the only source of truth.** The tutor never answers a question for me during capture. The quiz grades my recount against the card's text alone, so a true fact that isn't on the card earns no credit. And when I ask the knowledge base a question it can't answer, it says so instead of improvising:

```
Not in the knowledge base. The closest related cards cover AI vocabulary,
cloud computing, and tech regulation topics, but nothing on the French
Revolution.
```

A knowledge base that quietly backfills from the model's general knowledge stops being a record of what I know.

**A human approves every card.** The tutor proposes; I decide with `yes`, `edit: ...`, or `skip`. Nothing is filed without that. This keeps misunderstandings, half-formed ideas, and the tutor's own errors out of the durable base.

**Boring, durable formats.** Cards are plain Markdown files with YAML frontmatter, filed by week and topic. No database, no server, no lock-in. I can read them in any editor, grep them, and diff them in Git, and every later layer of the system (retrieval, quizzing) was built directly on the same files with no migration.

**Selective by design.** Capture happens in bursts, when something is worth keeping, not on a schedule. A small knowledge base of things I actually understand is the feature.

## Try it yourself

**Prerequisites:** Python 3 (tested on 3.9) and Git. For the tutor, [Claude Code](https://claude.com/claude-code). For graded quizzing and questions, an [Anthropic API key](https://console.anthropic.com/) in `ANTHROPIC_API_KEY` (or a gitignored `.env` file in the repo root); the tutor itself needs no key.

**1. Clone and install.**

```bash
git clone https://github.com/<your-account>/knowledge-brain.git
cd knowledge-brain
python3 -m pip install -r requirements.txt
```

**2. Get quizzed, or recount.** Open Claude Code in the repo folder. Two commands ship with it, in `.claude/commands/`:

- `/memory-mine` quizzes you on a subject you already know. Right answers become cards.
- `/tutor` is for something you just learned. You explain it, the tutor interrogates the explanation, and a card comes out the other end.

Both read their rules from [`system_prompt.md`](system_prompt.md), the tutor's rulebook, and both file approved cards into `knowledge/` on the spot.

**3. Review.** `python3 quiz.py` runs a graded recall session over whatever is due. `--status` shows the mastery readout with no API call. `--self` is flashcard mode, no key needed. `--practice` runs every card in random order and records nothing, for zero-stakes rehearsal. On a Mac, `Quiz.command` starts a session with a double-click.

**4. Ask.** `python3 ask.py "what did I learn about service meshes?"` answers from your cards, with the file path of every card it used:

```
According to your knowledge base, you learned about **Cloud Service Mesh**
[examples/google-cloud/cloud-service-mesh.md]:

- Cloud Service Mesh is a Google Cloud layer built for Kubernetes that manages
  how microservices communicate with one another.
- It helps handle traffic control, secure connections between services, and
  monitoring of service-to-service activity.
...
```

`python3 ask.py --index` prints the structural facts (how many cards, which weeks, which topics) straight from the file system, no API call.

This repository ships with a few representative cards in [`examples/`](examples/) so you can see the format. My own knowledge base stays local: the pipeline files real cards to `knowledge/`, which is not tracked here, and the review history in `review-log.jsonl` is never committed. Graded quizzing and question mode send the card under review (and your typed answer) to the Anthropic API; `--status`, `--self`, `--index`, and the extractor never do.

## Under the hood

**The card.** Every card is one Markdown file: YAML frontmatter with a term (usually a question), topic, tags, source, and confidence level, then a short definition. Files are named from the term, so a folder listing reads like a quiz: `how-does-polonius-die.md`.

**The extractor.** `extract_learnings.py` turns the tutor's confirmed YAML into card files under `knowledge/week-of-YYYY-MM-DD/<topic>/`. The tutor commands run it for you. It's idempotent: run it twice on the same file and the second run reports every card as unchanged, so nothing is ever duplicated.

```
✅ created: knowledge/week-of-2026-07-20/software-engineering/idempotency.md
```

```
⏸️  unchanged: knowledge/week-of-2026-07-20/software-engineering/idempotency.md
```

**Retrieval without a vector database.** The obvious way to answer questions over documents is RAG: embed the cards, retrieve the top matches. This project doesn't, on purpose. A knowledge base of a few dozen or even a few hundred cards fits in one model context, so `ask.py` sends everything with every question. Nothing relevant is ever left out, and questions about the collection as a whole ("what topics have I covered?") work, which top-k retrieval can't manage. Card loading is isolated in one function, so if the base ever outgrows a comfortable context budget, an embedding-based retriever replaces that function and nothing downstream changes. The seam is documented, not built.

**The scheduler.** A five-rung ladder: 3, 7, 21, 60, 120 days. A right answer climbs one rung; a wrong answer drops to the bottom; cards the tutor marked high-confidence start partway up. A session asks at most 12 cards, shakiest and most overdue first, gives anything you missed one more look before it ends, and offers more only after that. Review history is one line per card review in `review-log.jsonl`, plain text; the mastery readout is computed from it. Delete the file and the system honestly forgets.

**The engine/skin split.** `quiz.py` keeps scheduling, state, and grading separate from the terminal interface, so a different front end could sit on the same engine. After two months of use I decided not to build one, since the friction turned out to be elsewhere, but the seam stays in case the evidence changes.

## Open questions

- **Culling.** Cards that stopped earning their place get deleted by hand, and that happens more than I expected. A proper pass, reviewing a month's cards and keeping or cutting each, would make the knowledge base easier to trust as it grows.
- **Resurfacing.** Old cards showing up during new learning ("you captured something related in March"). Unresolved: how to do this without turning the tutor into a distraction machine.
- **Does it work?** The honest answer is: it's early. A few months in, with a few dozen Shakespeare cards, the mastery readout is climbing and the questions I missed in September are ones I can answer now. That's the experiment. I'll know more by spring.
