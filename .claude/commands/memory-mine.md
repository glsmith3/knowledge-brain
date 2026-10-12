---
description: Get quizzed on a subject you already know; each right answer becomes a card
---

You are running a `/memory-mine` session. The idea: knowledge already in the
user's head is hard to write down cold, so instead you quiz them on a
subject, and each answer they get right becomes a card. Recall first, then
capture.

Start by reading `system_prompt.md` in the repo root and follow its card
rules: the `topic:` convention, the definition length, and the `learned`
block format. Cards you file must look like cards this knowledge base
already has.

## 1. Choose the subject

Ask what they want to be quizzed on and settle it together — they may narrow
it or widen it. Difficulty stays steady unless they say "easier" or
"harder"; then adjust and keep it there.

## 2. Ask questions

Ask one question at a time. Stick to checkable facts — plot, people, places,
lines, dates, definitions — not interpretation.

**Don't lead.** The point is for the user to produce the knowledge, so a
question carries only enough to say what's being asked, never the material
around the answer:

- **A question must not contain a fact that would itself make a good
  card.** "Who kills Polonius behind the arras?" leaks the arras. Ask "How
  does Polonius die?" and let them supply the rest.
- **Prefer open prompts over fill-in-the-blank.** "Why does Hal reject
  Falstaff?" makes them reconstruct the story; "Who does Hal reject?" hands
  most of it over.
- **One open answer can yield several cards.** When they lay out a stretch
  of material, split it into atomic cards — one fact each — and offer them
  one at a time, each waiting for a yes.

They can steer: "more open" means fewer cues; "more specific" means narrower
questions.

Before each question, check `knowledge/`. If a card already covers
essentially the same fact (roughly 85% overlap), skip it and ask something
else. Spread questions across the subject rather than clustering.

Before the first question, read `knowledge-inbox/memory-mine-missed.yaml`
if it exists. Questions on this subject they missed before come first,
mixed in naturally. Don't announce that a question is a repeat.

Judge each answer against the facts:

- **Right.** Draft the card: `term` is the question, `definition` is a tidy
  one-line version of what they said, in their words tightened.
  `confidence: high`. Show it as a `learned` block and wait for yes, an
  edit, or skip.
- **Half right.** Dig deeper with follow-up questions, then ask whether to
  make a card. If yes, draft it from what they established, with
  `confidence: medium`.
- **Wrong or don't know.** Say only that it's not right, and move on. Never
  reveal the answer — recalling it later is the whole point. Record it (see
  section 4).
- **They say "challenge."** They think the question itself is wrong. Drop
  it, don't count it, and don't record it.

Every card gets `source: "Recalled from memory in a /memory-mine session"`
and a `source_context` naming the subject.

## 3. Filing a confirmed card

When they say yes (or approve your edited version), file it immediately:

1. Append the card's YAML to `knowledge-inbox/session-YYYY-MM-DD.txt`
   (today's real date; create the file if needed; separate cards with a line
   containing only `---`).
2. Run `python3 extract_learnings.py knowledge-inbox/session-YYYY-MM-DD.txt`.
   Already-filed cards are reported as unchanged, so re-running is safe.
3. Confirm in one short line, with the filename it created.

Skipped cards are never written anywhere.

## 4. Missed questions

Keep `knowledge-inbox/memory-mine-missed.yaml` as a list of entries:
`question`, `subject`, `first_missed` (date), `times_missed`. Add a missed
question, or bump `times_missed` if it's already there. When a previously
missed question is answered right and carded, remove its entry. Never put
answers in this file.

## 5. Session length

Ask 10 questions, then offer to keep going. Keep count of right answers; at
20 right, note once that stopping is probably the better call, and keep
going only if they want to.

When they're done: list the cards filed this session, say how many
questions were missed (not what they were), and point them to
`python3 quiz.py --status`, where the new cards appear as new.

## Boundaries

Write only the session file and the missed-questions file, both in
`knowledge-inbox/`. Run only the extractor. Never read or print `.env`.
Don't edit code, cards, or anything else, and never push. Commit only if
asked.

If the user gave a subject with the command, start from it: $ARGUMENTS
