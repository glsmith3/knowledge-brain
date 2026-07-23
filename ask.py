#!/usr/bin/env python3
"""
ask.py

Query the knowledge base. Two modes:

    python3 ask.py --index
        Print structural facts about the knowledge base straight from the
        file system — no LLM, no API key, no cost.

    python3 ask.py "what did I learn about service meshes?"
        Ask a question; answered by an LLM from the cards, with citations.
        (Question mode lands in the next step of the v2 build.)

Cards are loaded from examples/ (public samples) and knowledge/ (personal,
local-only). See the README retrieval section for the design rationale.
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    print(
        "Missing dependency: PyYAML\n\n"
        "Install it from this project directory with:\n"
        "  python3 -m pip install -r requirements.txt\n"
    )
    sys.exit(1)

# Model used by question mode. One obvious constant, per the v2 brief.
MODEL = "claude-sonnet-5"

# The frontmatter fence is the FIRST pair of --- lines only. Card bodies can
# legally contain later --- separators: extract_learnings.py appends
# "Revisited on" sections that way. Never split on every ---.
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_card(path: Path, group: str, repo_root: Path):
    """Parse one card file into a dict, or None (with a warning) if malformed."""
    match = FRONTMATTER_RE.match(path.read_text())
    if not match:
        print(f"⚠️  Skipping {path}: no YAML frontmatter found")
        return None
    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        print(f"⚠️  Skipping {path}: malformed frontmatter ({e})")
        return None
    if not isinstance(fm, dict) or not fm.get("term"):
        print(f"⚠️  Skipping {path}: frontmatter has no 'term' field")
        return None

    rel = path.relative_to(repo_root)
    week = next((part for part in rel.parts if part.startswith("week-of-")), None)
    return {
        "path": str(rel),
        "group": group,  # "example" or "personal"
        "slug": path.stem,
        "week": week,
        "term": fm["term"],
        "topic": fm.get("topic", "Uncategorized"),
        "tags": fm.get("tags", []),
        "date_learned": str(fm.get("date_learned", "")),
        "confidence": fm.get("confidence", ""),
        "source_context": fm.get("source_context", ""),
        "source": fm.get("source", ""),
        "definition": match.group(2).strip(),
    }


def load_cards(repo_root: Path) -> list:
    """
    Load every card under examples/ and knowledge/.

    This loader is the scaling seam: if the knowledge base ever outgrows a
    comfortable context budget, an embedding-based retriever replaces this
    load-everything function and nothing downstream changes.
    """
    cards = []
    groups = (("example", repo_root / "examples"), ("personal", repo_root / "knowledge"))
    for group, base in groups:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            card = parse_card(path, group, repo_root)
            if card is not None:
                cards.append(card)
    return cards


def dedupe_for_prompt(cards: list) -> list:
    """
    The curated examples were cleaned from real cards, so the same card can
    exist in both examples/ and knowledge/. Question mode keeps the personal
    copy so citations point at the canonical file. --index reports both.
    """
    personal_slugs = {c["slug"] for c in cards if c["group"] == "personal"}
    return [
        c for c in cards
        if c["group"] == "personal" or c["slug"] not in personal_slugs
    ]


def print_index(cards: list) -> None:
    examples = [c for c in cards if c["group"] == "example"]
    personal = [c for c in cards if c["group"] == "personal"]
    personal_slugs = {c["slug"] for c in personal}
    overlap = [c for c in examples if c["slug"] in personal_slugs]

    print("Knowledge Brain index")
    print("=====================")
    print(f"Cards: {len(cards)} total — {len(personal)} personal, {len(examples)} examples")
    if overlap:
        print(
            f"({len(overlap)} example card(s) duplicate personal cards; "
            "question mode deduplicates, preferring the personal copy)"
        )
    print()

    print("By week:")
    by_week = defaultdict(list)
    for card in personal:
        by_week[card["week"] or "(no week folder)"].append(card)
    for week in sorted(by_week):
        print(f"  {week}  ({len(by_week[week])} card(s))")
        for card in by_week[week]:
            print(f"    - {card['term']}  [{card['date_learned']}]")
    if examples:
        print(f"  examples/  ({len(examples)} card(s), undated samples)")
        for card in examples:
            print(f"    - {card['term']}")
    print()

    print("By topic:")
    by_topic = defaultdict(list)
    for card in cards:
        by_topic[card["topic"]].append(card)
    for topic in sorted(by_topic):
        print(f"  {topic}  ({len(by_topic[topic])})")
        for card in by_topic[topic]:
            print(f"    - {card['term']}  [{card['path']}]")


def main():
    parser = argparse.ArgumentParser(
        description="Ask questions of your knowledge base."
    )
    parser.add_argument(
        "question", nargs="?",
        help="A question to answer from the cards (uses the Anthropic API)",
    )
    parser.add_argument(
        "--index", action="store_true",
        help="Print a structural index of the knowledge base (no API call, no key needed)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    cards = load_cards(repo_root)

    if not cards:
        print(
            "No cards found — examples/ and knowledge/ are both empty.\n\n"
            "Capture a card first (see the README Quickstart), or clone the\n"
            "repo fresh to get the bundled example cards."
        )
        sys.exit(1)

    if args.index:
        print_index(cards)
        return

    if args.question:
        print(
            "Question mode is not built yet — it lands in the next step of the\n"
            "v2 build. Use --index for structural facts about the knowledge base."
        )
        sys.exit(1)

    parser.print_help()


if __name__ == "__main__":
    main()
