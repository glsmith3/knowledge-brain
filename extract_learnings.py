#!/usr/bin/env python3
"""
extract_learnings.py

Parses a ChatGPT session transcript, finds proposed ```learned``` blocks,
matches each one to the user's confirming reply (yes / edit / skip), and
files confirmed concepts as Markdown files with YAML frontmatter under
knowledge/<topic>/<slug>.md.

Usage:
    python3 extract_learnings.py path/to/transcript.txt
    python3 extract_learnings.py path/to/transcript.txt --knowledge-dir ./knowledge
    python3 extract_learnings.py path/to/transcript.txt --dry-run
"""

import argparse
import difflib
import re
import sys
from datetime import date, timedelta
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

LEARNED_BLOCK_RE = re.compile(
    r"```(?:learned|yaml|yml)?[ \t]*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)

# Turn markers commonly seen in ChatGPT copy/export text. Both are optional —
# if absent, we just look at the next chunk of plain text after a block.
TURN_MARKER_RE = re.compile(r"^(You said:|ChatGPT said:)\s*$", re.MULTILINE)

REQUIRED_FIELDS = ["term", "topic", "definition"]

# How similar a new topic name has to be to an existing folder name before
# we treat them as the same topic (0-1, higher = stricter). 0.72 catches
# things like "Cell Biology" vs "Cellular Biology" without over-merging
# genuinely different topics.
TOPIC_MATCH_THRESHOLD = 0.72


def week_folder_name(reference_date: date) -> str:
    """
    Returns a stable folder name for the week containing reference_date,
    e.g. 'week-of-2026-07-06' for the Monday that starts that week. Using
    Monday as the anchor means every day in the same week produces the
    same folder name, regardless of which day the script runs on.
    """
    monday = reference_date - timedelta(days=reference_date.weekday())
    return f"week-of-{monday.isoformat()}"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_yaml_documents(raw_yaml: str, location: str) -> list:
    """Parse one or more YAML documents and keep mapping-shaped cards."""
    try:
        documents = list(yaml.safe_load_all(raw_yaml))
    except yaml.YAMLError as e:
        print(f"⚠️  Skipping malformed YAML in {location}: {e}")
        return []

    parsed = []
    for i, data in enumerate(documents, start=1):
        if data is None:
            continue
        if not isinstance(data, dict):
            print(f"⚠️  Skipping YAML document {i} in {location}: not a mapping")
            continue
        parsed.append(data)
    return parsed


def looks_like_learned_card(data: dict) -> bool:
    return all(data.get(field) for field in REQUIRED_FIELDS)


def find_blocks_with_positions(transcript: str):
    """
    Return list of (block_dict, start_idx, end_idx, assume_confirmed) items.

    Full transcripts should contain fenced learned blocks and user replies.
    Raw inbox files may contain one or more learned YAML documents; those are
    treated as already confirmed because the user deliberately staged them.
    """
    blocks = []
    for m in LEARNED_BLOCK_RE.finditer(transcript):
        location = f"fenced block near offset {m.start()}"
        for data in parse_yaml_documents(m.group(1), location):
            blocks.append((data, m.start(), m.end(), False))
    if blocks:
        return blocks

    raw_blocks = []
    for data in parse_yaml_documents(transcript, "raw inbox file"):
        if looks_like_learned_card(data):
            raw_blocks.append((data, 0, len(transcript), True))
    if raw_blocks:
        print("📥 Treating raw learned YAML file as confirmed.")
        return raw_blocks

    return blocks


def extract_reply_text(transcript: str, after_idx: int, next_block_idx: int) -> str:
    """
    Grab the text between the end of one learned block and the start of the
    next (or end of file), and try to isolate the user's actual reply from
    it using turn markers if present.
    """
    chunk = transcript[after_idx:next_block_idx]

    markers = list(TURN_MARKER_RE.finditer(chunk))
    if markers:
        # find first "You said:" marker, take text up to the next marker
        for i, mk in enumerate(markers):
            if mk.group(1) == "You said:":
                start = mk.end()
                end = markers[i + 1].start() if i + 1 < len(markers) else len(chunk)
                return chunk[start:end].strip()
        return chunk.strip()

    # No markers — just use the first non-empty paragraph as the reply
    for para in chunk.strip().split("\n\n"):
        if para.strip():
            return para.strip()
    return ""


def classify_reply(reply: str):
    """Return ('confirmed', edit_text_or_None) | ('skipped', None) | ('ambiguous', None)."""
    if not reply:
        return ("ambiguous", None)

    lower = reply.strip().lower()

    edit_match = re.match(r"^edit:\s*(.+)", reply.strip(), re.IGNORECASE | re.DOTALL)
    if edit_match:
        return ("confirmed", edit_match.group(1).strip())

    if re.search(r"\b(skip|no|not yet|not now)\b", lower):
        return ("skipped", None)

    if re.search(r"\b(yes|yep|correct|good|confirmed|right)\b", lower):
        return ("confirmed", None)

    return ("ambiguous", None)


def apply_edit(data: dict, edit_text: str) -> dict:
    """Append the user's correction to the original definition rather than
    replacing it, so context isn't lost."""
    data = dict(data)
    original = data.get("definition", "").strip()
    data["definition"] = f"{original}\n\n(Correction: {edit_text})"
    return data


def validate(data: dict) -> list:
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    return missing


def resolve_topic_slug(topic: str, knowledge_dir: Path) -> tuple:
    """
    Turn a topic name into a folder slug, reusing an existing folder if one
    is close enough (e.g. "Cell Biology" -> existing "cellular-biology").
    Returns (slug, merged_from_display_name_or_None).
    """
    new_slug = slugify(topic)

    if not knowledge_dir.exists():
        return new_slug, None

    existing_slugs = [p.name for p in knowledge_dir.iterdir() if p.is_dir()]
    if not existing_slugs:
        return new_slug, None

    if new_slug in existing_slugs:
        return new_slug, None

    matches = difflib.get_close_matches(
        new_slug, existing_slugs, n=1, cutoff=TOPIC_MATCH_THRESHOLD
    )
    if matches:
        return matches[0], topic  # merged into an existing folder
    return new_slug, None


def write_card(data: dict, knowledge_dir: Path, dry_run: bool) -> str:
    topic_slug, merged_from = resolve_topic_slug(data.get("topic", "uncategorized"), knowledge_dir)
    if merged_from:
        print(f"🔀 Merged topic '{merged_from}' into existing folder '{topic_slug}/'")
    term_slug = slugify(data["term"])
    topic_dir = knowledge_dir / topic_slug
    filepath = topic_dir / f"{term_slug}.md"

    today = date.today().isoformat()

    if filepath.exists():
        existing = filepath.read_text()
        if data["definition"].strip() in existing:
            return f"⏸️  unchanged: {filepath}"
        action = "updated"
        if not dry_run:
            addition = (
                f"\n\n---\n\n**Revisited on {today}:**\n\n{data['definition'].strip()}\n"
            )
            filepath.write_text(existing + addition)
        return f"🔁 {action}: {filepath}"
    else:
        action = "created"
        if not dry_run:
            topic_dir.mkdir(parents=True, exist_ok=True)
            frontmatter = {
                "term": data["term"],
                "topic": data.get("topic", "Uncategorized"),
                "date_learned": today,
                "tags": data.get("tags", []),
                "confidence": data.get("confidence", "medium"),
                "source_context": data.get("source_context", ""),
                "source": data.get("source", ""),
            }
            fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
            body = data["definition"].strip()
            filepath.write_text(f"---\n{fm_yaml}---\n\n{body}\n")
        return f"✅ {action}: {filepath}"


def main():
    parser = argparse.ArgumentParser(description="Extract confirmed learnings from a transcript.")
    parser.add_argument("transcript", type=Path, help="Path to the exported transcript .txt file")
    parser.add_argument(
        "--knowledge-dir", type=Path, default=Path("knowledge"),
        help="Base folder for knowledge files (default: ./knowledge). Each week gets its own subfolder inside this."
    )
    parser.add_argument(
        "--week-of", type=str, default=None,
        help="Override which week this session belongs to, as any date in YYYY-MM-DD format "
             "within that week (default: today, i.e. the current week)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without writing any files"
    )
    args = parser.parse_args()

    if not args.transcript.exists():
        print(f"❌ Transcript not found: {args.transcript}")
        sys.exit(1)

    if args.week_of:
        try:
            reference_date = date.fromisoformat(args.week_of)
        except ValueError:
            print(f"❌ --week-of must be in YYYY-MM-DD format, got: {args.week_of}")
            sys.exit(1)
    else:
        reference_date = date.today()

    week_dir = args.knowledge_dir / week_folder_name(reference_date)
    print(f"📅 Filing into week folder: {week_dir}")

    transcript = args.transcript.read_text()
    blocks = find_blocks_with_positions(transcript)

    if not blocks:
        print("No ```learned``` blocks or raw learned YAML found in this transcript.")
        return

    created, updated, unchanged, skipped, ambiguous = 0, 0, 0, 0, 0

    for i, (data, start, end, assume_confirmed) in enumerate(blocks):
        next_block_idx = blocks[i + 1][1] if i + 1 < len(blocks) else len(transcript)
        if assume_confirmed:
            reply = ""
            status, edit_text = "confirmed", None
        else:
            reply = extract_reply_text(transcript, end, next_block_idx)
            status, edit_text = classify_reply(reply)

        term = data.get("term", "<unknown term>")

        if status == "skipped":
            print(f"⏭️  Skipped: {term} (reply: {reply[:40]!r})")
            skipped += 1
            continue

        if status == "ambiguous":
            print(f"❓ Ambiguous reply for '{term}', not filed (reply: {reply[:40]!r})")
            ambiguous += 1
            continue

        if edit_text:
            data = apply_edit(data, edit_text)

        missing = validate(data)
        if missing:
            print(f"⚠️  '{term}' missing required fields {missing}, not filed")
            ambiguous += 1
            continue

        result = write_card(data, week_dir, args.dry_run)
        if result.startswith("✅"):
            created += 1
        elif result.startswith("🔁"):
            updated += 1
        else:
            unchanged += 1
        print(result)

    print()
    print("Summary:")
    print(f"  ✅ {created} new concept(s) added")
    print(f"  🔁 {updated} concept(s) updated")
    print(f"  ⏸️  {unchanged} unchanged duplicate(s)")
    print(f"  ⏭️  {skipped} skipped")
    print(f"  ❓ {ambiguous} ambiguous / not filed")
    if args.dry_run:
        print("\n(dry run — no files were actually written)")


if __name__ == "__main__":
    main()
