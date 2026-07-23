# Knowledge Brain

A lightweight pipeline that turns learning conversations with ChatGPT into a
structured, quiz-app-ready Markdown knowledge base — no custom app, no UI.

## How it works

1. **Set up the tutor.** Paste the contents of `system_prompt.md` into a
   Custom GPT's instructions (or as the first message of a session). This
   makes the AI propose `learned` blocks as you talk, and wait for your
   yes / edit / skip before moving on.

   **Important:** in the GPT's Configure tab, turn ON the **Code
   Interpreter & Data Analysis** capability. This lets it generate a
   downloadable, correctly-dated transcript file at the end of a session
   instead of you having to copy/paste the conversation manually.

2. **Have a normal conversation.** Explore whatever topic you want. When the
   AI proposes a `learned` block, just reply naturally:
   - `yes` — confirm it as written
   - `edit: <correction>` — confirm with your correction appended
   - `skip` — drop it

3. **Wrap up the session.** Say something like "let's wrap up" or "export
   this session." The GPT can generate a `.txt` file named
   `session-YYYY-MM-DD.txt` (using the actual current date). The file may
   be either a full transcript with fenced `learned` blocks and replies, or
   just the confirmed learned YAML card(s). Download it and drop it into
   `knowledge-inbox/`.

4. **Run the extractor via Codex**, from this folder:
   ```
   codex "extract learnings from knowledge-inbox/session-2026-07-11.txt and file them into knowledge/"
   ```
   or run the script directly:
   ```
   python3 -m pip install -r requirements.txt
   ```
   then:
   ```
   python3 extract_learnings.py knowledge-inbox/session-2026-07-11.txt
   ```
   Add `--dry-run` first if you want to preview what would happen without
   writing any files.

5. **Check the summary.** The script prints how many concepts were created,
   updated, skipped, or left ambiguous (e.g. if your reply wasn't clearly
   yes/edit/skip — nothing gets filed automatically in that case).

## What you end up with

```
knowledge/
  cellular-biology/
    mitochondria.md
    glycolysis.md
  roman-history/
    punic-wars.md
```

Each file has YAML frontmatter (term, topic, date, tags, confidence,
source context) plus a clean Markdown body — structured for a future quiz
app to glob the folder and read straight off the frontmatter, no NLP
parsing required.

## Weekly organization

Every concept gets filed under a week folder based on the date the script
is run, e.g.:

```
knowledge/
  week-of-2026-07-06/
    cellular-biology/
      mitochondria.md
    roman-history/
      punic-wars.md
  week-of-2026-07-13/
    cellular-biology/
      mitochondria.md   <- same term, different week, kept separate on purpose
```

The week label always uses the **Monday** of that week, so any day you run
the script within the same week lands in the same folder. This means:

- The same concept coming up **twice in one week** gets treated as a
  revisit (updates the existing file — see "Topic folder matching" below,
  same logic applies at the term level).
- The same concept coming up **in a different week** gets its own fresh
  entry in that week's folder — repeats across weeks are expected and
  fine, since the whole point is to see chronologically what you focused
  on each week.

By default the week is calculated from today's date. If you're filing an
old transcript later and want it to land in the week it actually happened,
use `--week-of` with any date from that week:

```
python3 extract_learnings.py old-session.txt --week-of 2026-06-15
```

## Topic folder matching

To keep similar topics from splitting into duplicate folders (e.g. "Cell
Biology" vs "Cellular Biology"), the script fuzzy-matches new topic names
against your existing topic subfolders **within that same week's folder**.
If something's a close enough match, it reuses the existing folder and
prints a line like:

```
🔀 Merged topic 'Cell Biology' into existing folder 'cellular-biology/'
```

If it merges something you didn't want merged, just move the file into a
new folder manually — the script only checks existing folder names at run
time, so it won't try to "unmerge" anything on its own.

## Notes / known limitations (v1)

- The script expects `You said:` / `ChatGPT said:` turn markers, which is
  how ChatGPT's plain-text copy typically comes out. If your export format
  differs, replies may be classified as "ambiguous" and won't get filed —
  check the printed warnings.
- Ambiguous replies are never auto-filed. If something didn't get saved
  and you're not sure why, re-check your reply text right after that
  `learned` block in the transcript.
- If an inbox file contains raw learned YAML instead of a full transcript,
  the extractor treats it as already confirmed and files it directly.
- Re-running the same inbox file is safe: if the exact same definition is
  already present in that week's card, the script reports it as unchanged
  instead of appending a duplicate revisit.
- Editing a concept later just appends a "Revisited on [date]" section to
  the existing file rather than rewriting it — keeps history, but you may
  want to manually clean up a file occasionally if it gets long.
