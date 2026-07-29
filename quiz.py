#!/usr/bin/env python3
"""
quiz.py

Recall practice over the knowledge base — the v3 retention layer.

    python3 quiz.py               Graded session: type what you remember,
                                  Claude coaches you against your card.
                                  Needs ANTHROPIC_API_KEY.
    python3 quiz.py --self        Flashcard session: recall mentally,
                                  reveal, self-grade. No API, no cost.
    python3 quiz.py --status      Mastery readout. No API.
    python3 quiz.py --month 2026-07
                                  Session scoped to one month's cards.

Review history is appended to review-log.jsonl — local, gitignored, plain
text, one line per review. Cards are never modified. A graded session sends
the card under review and your typed answer to the Anthropic API; --self
and --status never call the API.

The file is split into ENGINE (scheduling, state, grading — interface-
agnostic) and SKIN (terminal I/O). A future local web page would be a new
skin over the same engine; that seam is deliberate.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import ask  # card loader, dedupe, MODEL constant — the shared v2 foundation

# ---------------------------------------------------------------- ENGINE --

# Interval ladder, in days. "got" climbs one rung, "partial" holds,
# "missed" drops to the bottom. Boring beats clever.
LADDER = [3, 7, 21, 60, 120]
TOP_RUNG = len(LADDER) - 1

# A card's tutor-assigned confidence seeds its starting rung: high starts
# mid-ladder, everything else starts at the bottom.
HIGH_CONFIDENCE_SEED = 2

# Cap on what a session ASKS (the obligation). Overtime past the cap is
# always offered, never demanded, and never recorded as a baseline.
SESSION_CARD_CAP = 12

LOG_NAME = "review-log.jsonl"
GRADES = ("got", "partial", "missed")


def seed_rung(confidence) -> int:
    return HIGH_CONFIDENCE_SEED if str(confidence).lower() == "high" else 0


def apply_grade(rung: int, grade: str) -> int:
    if grade == "got":
        return min(rung + 1, TOP_RUNG)
    if grade == "partial":
        return rung
    return 0  # missed


def cohort(card: dict) -> str:
    """Month bucket for reporting: from date_learned, else week folder."""
    d = card.get("date_learned") or ""
    if len(d) >= 7 and d[4:5] == "-":
        return d[:7]
    if card.get("week"):
        return card["week"][len("week-of-"):len("week-of-") + 7]
    return "undated"


def active_cards(repo_root: Path) -> list:
    """The quizzable set: all cards, example/personal duplicates removed."""
    return ask.dedupe_for_prompt(ask.load_cards(repo_root))


def load_log(log_path: Path) -> list:
    entries = []
    if not log_path.exists():
        return entries
    for lineno, line in enumerate(log_path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"⚠️  Skipping malformed review-log line {lineno}")
    return entries


def make_entry(card: dict, mode: str, grade: str, rung: int, now: datetime) -> dict:
    """One review record. Deliberately carries NO session-level data
    (no durations, no counts) — the never-rebaseline rule is structural."""
    return {
        "slug": card["slug"],
        "path": card["path"],
        "ts": now.isoformat(timespec="seconds"),
        "mode": mode,  # "graded" | "self" | "retry"
        "grade": grade,
        "rung": rung,  # rung AFTER this review
        "due": (now.date() + timedelta(days=LADDER[rung])).isoformat(),
    }


def append_log(log_path: Path, entry: dict) -> None:
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def build_states(cards: list, entries: list, today: date) -> list:
    """Replay the log into per-card state. Retries never affect schedule."""
    latest = {}
    for e in sorted(entries, key=lambda e: e.get("ts", "")):
        if e.get("mode") == "retry":
            continue
        latest[e.get("slug")] = e
    states = []
    for card in sorted(cards, key=lambda c: c["slug"]):
        e = latest.get(card["slug"])
        if e is None:
            states.append({
                "card": card, "rung": seed_rung(card.get("confidence")),
                "last": None, "due": today, "last_grade": None,
            })
        else:
            rung = int(e["rung"])
            last = date.fromisoformat(e["ts"][:10])
            states.append({
                "card": card, "rung": rung, "last": last,
                "due": last + timedelta(days=LADDER[rung]),
                "last_grade": e.get("grade"),
            })
    return states


def state_label(st: dict) -> str:
    if st["last"] is None:
        return "new"
    return "solid" if st["rung"] >= 2 else "shaky"


def in_month(st: dict, month) -> bool:
    return month is None or cohort(st["card"]) == month


def select_due(states: list, today: date, month=None) -> list:
    """Everything due, shakiest first, then most overdue. Late reviews are
    just reviews — there is no penalty for lateness anywhere."""
    due = [s for s in states if in_month(s, month) and s["due"] <= today]
    due.sort(key=lambda s: (s["rung"], s["due"].isoformat(), s["card"]["slug"]))
    return due


def overtime_queue(states: list, spill: list, today: date, month=None) -> list:
    """Value order past the core session: remaining due, then shaky cards
    not yet due, then ahead-of-schedule practice (soonest due first)."""
    spill_slugs = {s["card"]["slug"] for s in spill}
    rest = [s for s in states
            if in_month(s, month)
            and s["card"]["slug"] not in spill_slugs
            and s["due"] > today]
    shaky = [s for s in rest if state_label(s) == "shaky"]
    ahead = [s for s in rest if state_label(s) != "shaky"]
    key = lambda s: (s["due"].isoformat(), s["card"]["slug"])
    return spill + sorted(shaky, key=key) + sorted(ahead, key=key)


def why_line(st: dict, today: date) -> str:
    if st["last"] is None:
        return "new card, first test"
    if st["last_grade"] == "missed":
        return "you missed this one last time"
    if st["due"] <= today:
        return f"due — last seen {(today - st['last']).days} day(s) ago"
    return f"ahead of schedule — not due until {st['due'].isoformat()}"


# ------------------------------------------------------- ENGINE: GRADING --

GRADING_INSTRUCTIONS = """\
You are grading one recall attempt against one card from the user's
personal knowledge base.

The card is the ONLY source of truth. Grade the recount strictly against
the card text. If the recount contains true information that is not on the
card, it earns no credit for that information — you are measuring recall
of this card, not general knowledge.

Choose exactly one grade:
- got: the recount captures the card's core idea accurately.
- partial: the core idea is half-there — something important is missing or
  fuzzy, but nothing is outright wrong.
- missed: the recount is wrong, or misses the card's core idea.

Then coach, don't judge: one to three sentences. Name what the user got
right (if anything), then close the gap by stating what the card actually
says. No scores, no praise padding, and no verdict words like "incorrect",
"wrong", or "fail" — instead of labeling the answer, supply the correction
("the card places this in Google Cloud, not AWS").

Reply in exactly this format:
GRADE: <got|partial|missed>
FEEDBACK: <your coaching feedback>"""


def grade_recount(card: dict, recount: str):
    """Returns (grade, feedback). Raises SystemExit with a helpful message
    on missing key/SDK, mirroring ask.py's precedent."""
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Missing API key: ANTHROPIC_API_KEY\n\n"
            "Graded sessions call the Anthropic API. Set your key first:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n\n"
            "(Or run a no-API session with:  python3 quiz.py --self)"
        )
        sys.exit(1)
    try:
        import anthropic
    except ModuleNotFoundError:
        print(
            "Missing dependency: anthropic\n\n"
            "Install it from this project directory with:\n"
            "  python3 -m pip install -r requirements.txt\n"
        )
        sys.exit(1)

    user_content = (
        f"CARD\nterm: {card['term']}\ndefinition:\n{card['definition']}\n\n"
        f"USER'S RECOUNT\n{recount}"
    )
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=ask.MODEL,
            max_tokens=2000,
            system=GRADING_INSTRUCTIONS,
            messages=[{"role": "user", "content": user_content}],
        )
    except anthropic.APIConnectionError:
        print("Could not reach the Anthropic API. Check your connection and try again.")
        sys.exit(1)
    except anthropic.APIStatusError as e:
        print(f"Anthropic API error ({e.status_code}): {e.message}")
        sys.exit(1)

    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
    grade, feedback = None, []
    for line in text.splitlines():
        if line.upper().startswith("GRADE:"):
            candidate = line.split(":", 1)[1].strip().lower()
            if candidate in GRADES:
                grade = candidate
        elif line.upper().startswith("FEEDBACK:"):
            feedback.append(line.split(":", 1)[1].strip())
        elif feedback:
            feedback.append(line.strip())
    if grade is None:
        # Unparseable grader output: show it, count it as partial (hold).
        return "partial", text
    return grade, " ".join(feedback).strip()


# ------------------------------------------------------------------ SKIN --

def print_status(states: list, today: date) -> None:
    print("Knowledge Brain — mastery")
    print("=========================")
    groups = defaultdict(list)
    for s in states:
        groups[cohort(s["card"])].append(s)
    for month in sorted(groups):
        sts = groups[month]
        solid = sum(1 for s in sts if state_label(s) == "solid")
        bar = "#" * solid + "-" * (len(sts) - solid)
        print(f"{month}  [{bar}]  {solid}/{len(sts)} solid")
        for label in ("shaky", "new"):
            for s in sts:
                if state_label(s) != label:
                    continue
                detail = f"due {s['due'].isoformat()}" if s["due"] > today else "due now"
                if s["last_grade"]:
                    detail = f"last: {s['last_grade']}, {detail}"
                print(f"  {label:5}: {s['card']['term']}  ({detail})")
    due_count = len([s for s in states if s["due"] <= today])
    print(f"\nDue now: {due_count} card(s)")


def read_recount() -> str:
    print("  Type what you remember (finish with an empty line; 'q' alone to stop):")
    lines = []
    while True:
        try:
            line = input("  > ")
        except EOFError:
            return None
        if line.strip() == "q" and not lines:
            return None
        if line.strip() == "" and lines:
            return "\n".join(lines)
        if line.strip() == "":
            continue
        lines.append(line)


def quiz_one(st: dict, today: date, graded: bool, log_path: Path, mode: str):
    """Run one card. Returns the grade, or None if the user stopped."""
    card = st["card"]
    print(f"\n--- {card['term']}  (topic: {card['topic']})")
    print(f"    [{why_line(st, today)}]")

    if graded:
        recount = read_recount()
        if recount is None:
            return None
        grade, feedback = grade_recount(card, recount)
        print(f"\n  {grade.upper()} — {feedback}")
    else:
        try:
            input("  Recall it in your head, then press Enter to reveal... ")
        except EOFError:
            return None
        print(f"\n  {card['definition']}\n")
        answer = ""
        while answer not in ("1", "2", "3", "q"):
            try:
                answer = input("  How did you do? 1=got it  2=partial  3=missed  (q=stop): ").strip()
            except EOFError:
                return None
        if answer == "q":
            return None
        grade = {"1": "got", "2": "partial", "3": "missed"}[answer]

    new_rung = st["rung"] if mode == "retry" else apply_grade(st["rung"], grade)
    append_log(log_path, make_entry(card, mode, grade, new_rung, datetime.now()))
    return grade


def run_session(repo_root: Path, graded: bool, month=None) -> None:
    today = date.today()
    log_path = repo_root / LOG_NAME
    cards = active_cards(repo_root)
    if not cards:
        print("No cards found — capture something first (see the README).")
        sys.exit(1)
    if month is not None and not any(cohort(c) == month for c in cards):
        months = sorted({cohort(c) for c in cards})
        print(f"No cards in {month}. Months with cards: {', '.join(months)}")
        sys.exit(1)

    states = build_states(cards, load_log(log_path), today)
    before = {s["card"]["slug"]: state_label(s) for s in states}
    print_status([s for s in states if in_month(s, month)], today)

    due = select_due(states, today, month)
    core, spill = due[:SESSION_CARD_CAP], due[SESSION_CARD_CAP:]
    if not core:
        print("\nNothing due. Come back when the readout says otherwise —")
        print("or practice ahead anytime with:  python3 quiz.py --month YYYY-MM")
        return

    mode = "graded" if graded else "self"
    missed, stopped = [], False
    for st in core:
        grade = quiz_one(st, today, graded, log_path, mode)
        if grade is None:
            stopped = True
            break
        if grade == "missed":
            missed.append(st)

    # Same-session retry: the learn-it-now pass. Logged as mode="retry",
    # which the scheduler ignores — the miss above already set the schedule.
    if missed and not stopped:
        print(f"\n=== One more look at what you missed ({len(missed)}) ===")
        for st in missed:
            if quiz_one(st, today, graded, log_path, "retry") is None:
                stopped = True
                break

    # Closing readout + deltas.
    states = build_states(cards, load_log(log_path), today)
    print()
    print_status([s for s in states if in_month(s, month)], today)
    for s in states:
        slug = s["card"]["slug"]
        if slug in before and before[slug] != state_label(s):
            print(f"  {s['card']['term']}: {before[slug]} -> {state_label(s)}")

    # Overtime: offered, never demanded, never remembered.
    if stopped:
        return
    ot = overtime_queue(states, select_due(states, today, month)[SESSION_CARD_CAP:],
                        today, month)
    while ot:
        try:
            more = input(f"\n{len(ot)} more worth reviewing — keep going? (y / Enter to stop): ")
        except EOFError:
            return
        if more.strip().lower() != "y":
            return
        batch, ot = ot[:SESSION_CARD_CAP], ot[SESSION_CARD_CAP:]
        for st in batch:
            if quiz_one(st, today, graded, log_path, mode) is None:
                return


def main():
    parser = argparse.ArgumentParser(description="Recall practice over your knowledge base.")
    parser.add_argument("--self", dest="self_mode", action="store_true",
                        help="Flashcard mode: reveal and self-grade (no API, no key)")
    parser.add_argument("--status", action="store_true",
                        help="Print the mastery readout and exit (no API)")
    parser.add_argument("--month", metavar="YYYY-MM",
                        help="Scope the session to one month's cards")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    if args.status:
        cards = active_cards(repo_root)
        if not cards:
            print("No cards found — capture something first (see the README).")
            sys.exit(1)
        states = build_states(cards, load_log(repo_root / LOG_NAME), date.today())
        print_status(states, date.today())
        return

    run_session(repo_root, graded=not args.self_mode, month=args.month)


if __name__ == "__main__":
    main()
