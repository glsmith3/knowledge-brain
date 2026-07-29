#!/usr/bin/env python3
"""Unit tests for the quiz.py engine. Run: python3 -m unittest test_quiz -v"""

import unittest
from datetime import date, datetime, timedelta

import quiz


def card(slug, confidence="medium", date_learned="2026-07-11", week="week-of-2026-07-06"):
    return {
        "slug": slug, "path": f"knowledge/{week}/topic/{slug}.md",
        "group": "personal", "week": week, "term": slug.title(),
        "topic": "Topic", "tags": [], "date_learned": date_learned,
        "confidence": confidence, "source": "", "source_context": "",
        "definition": f"Definition of {slug}.",
    }


def entry(c, grade, rung, ts):
    return quiz.make_entry(c, "graded", grade, rung, ts)


TODAY = date(2026, 7, 29)


class TestLadder(unittest.TestCase):
    def test_got_climbs_one_rung(self):
        self.assertEqual(quiz.apply_grade(0, "got"), 1)
        self.assertEqual(quiz.apply_grade(2, "got"), 3)

    def test_got_caps_at_top(self):
        self.assertEqual(quiz.apply_grade(quiz.TOP_RUNG, "got"), quiz.TOP_RUNG)

    def test_partial_holds(self):
        for rung in range(len(quiz.LADDER)):
            self.assertEqual(quiz.apply_grade(rung, "partial"), rung)

    def test_missed_drops_to_bottom(self):
        for rung in range(len(quiz.LADDER)):
            self.assertEqual(quiz.apply_grade(rung, "missed"), 0)


class TestSeeding(unittest.TestCase):
    def test_high_confidence_starts_mid_ladder(self):
        self.assertEqual(quiz.seed_rung("high"), quiz.HIGH_CONFIDENCE_SEED)

    def test_everything_else_starts_at_bottom(self):
        for c in ("medium", "low", "", None):
            self.assertEqual(quiz.seed_rung(c), 0)

    def test_new_card_is_due_immediately_with_seeded_rung(self):
        states = quiz.build_states([card("a", confidence="high")], [], TODAY)
        self.assertEqual(states[0]["rung"], quiz.HIGH_CONFIDENCE_SEED)
        self.assertEqual(states[0]["due"], TODAY)
        self.assertEqual(quiz.state_label(states[0]), "new")


class TestReplay(unittest.TestCase):
    def test_due_date_comes_from_rung_interval(self):
        c = card("a")
        ts = datetime(2026, 7, 20, 20, 0)
        states = quiz.build_states([c], [entry(c, "got", 1, ts)], TODAY)
        self.assertEqual(states[0]["due"], date(2026, 7, 20) + timedelta(days=quiz.LADDER[1]))

    def test_latest_entry_wins(self):
        c = card("a")
        entries = [entry(c, "got", 1, datetime(2026, 7, 1)),
                   entry(c, "missed", 0, datetime(2026, 7, 20))]
        states = quiz.build_states([c], entries, TODAY)
        self.assertEqual(states[0]["rung"], 0)
        self.assertEqual(states[0]["last_grade"], "missed")

    def test_retry_entries_never_affect_schedule(self):
        c = card("a")
        real = entry(c, "missed", 0, datetime(2026, 7, 20))
        retry = quiz.make_entry(c, "retry", "got", 0, datetime(2026, 7, 20, 20, 30))
        states = quiz.build_states([c], [real, retry], TODAY)
        self.assertEqual(states[0]["rung"], 0)
        self.assertEqual(states[0]["last_grade"], "missed")

    def test_late_review_is_just_due_not_penalized(self):
        c = card("a")
        states = quiz.build_states([c], [entry(c, "got", 1, datetime(2026, 1, 1))], TODAY)
        self.assertLess(states[0]["due"], TODAY)          # long overdue
        self.assertEqual(states[0]["rung"], 1)            # rung untouched by lateness
        self.assertEqual(quiz.apply_grade(1, "got"), 2)   # grading unaffected


class TestSelection(unittest.TestCase):
    def make_states(self):
        c1, c2, c3 = card("solid-due"), card("shaky-due"), card("fresh")
        entries = [
            entry(c1, "got", 2, datetime(2026, 6, 1)),    # rung 2, overdue
            entry(c2, "missed", 0, datetime(2026, 7, 20)),  # rung 0, overdue
        ]
        return quiz.build_states([c1, c2, c3], entries, TODAY)

    def test_shakiest_first_then_most_overdue(self):
        due = quiz.select_due(self.make_states(), TODAY)
        slugs = [s["card"]["slug"] for s in due]
        # rung 0 entries first (shaky-due before fresh: earlier due date), then rung 2
        self.assertEqual(slugs, ["shaky-due", "fresh", "solid-due"])

    def test_session_cap_is_a_hard_boundary_on_the_core(self):
        cards = [card(f"c{i:02}") for i in range(20)]
        states = quiz.build_states(cards, [], TODAY)
        due = quiz.select_due(states, TODAY)
        core, spill = due[:quiz.SESSION_CARD_CAP], due[quiz.SESSION_CARD_CAP:]
        self.assertEqual(len(core), quiz.SESSION_CARD_CAP)
        self.assertEqual(len(spill), 8)

    def test_month_scoping(self):
        july = card("july", date_learned="2026-07-11")
        august = card("august", date_learned="2026-08-02", week="week-of-2026-08-03")
        states = quiz.build_states([july, august], [], TODAY)
        due = quiz.select_due(states, TODAY, month="2026-07")
        self.assertEqual([s["card"]["slug"] for s in due], ["july"])


class TestOvertime(unittest.TestCase):
    def test_value_order_spill_then_shaky_then_ahead(self):
        c_spill, c_shaky, c_ahead = card("spilled"), card("shaky"), card("ahead")
        entries = [
            entry(c_shaky, "missed", 0, datetime(2026, 7, 28)),  # rung 0, due in 2 days
            entry(c_ahead, "got", 3, datetime(2026, 7, 28)),     # rung 3, far future
        ]
        states = quiz.build_states([c_spill, c_shaky, c_ahead], entries, TODAY)
        spill = [s for s in states if s["card"]["slug"] == "spilled"]
        ot = quiz.overtime_queue(states, spill, TODAY)
        self.assertEqual([s["card"]["slug"] for s in ot], ["spilled", "shaky", "ahead"])


class TestCohort(unittest.TestCase):
    def test_month_from_date_learned(self):
        self.assertEqual(quiz.cohort(card("a", date_learned="2026-07-11")), "2026-07")

    def test_week_folder_fallback(self):
        c = card("a", date_learned="")
        self.assertEqual(quiz.cohort(c), "2026-07")

    def test_undated(self):
        c = card("a", date_learned="", week=None)
        self.assertEqual(quiz.cohort(c), "undated")


class TestLogSchema(unittest.TestCase):
    def test_no_session_or_effort_fields(self):
        """The never-rebaseline rule is structural: a review record cannot
        describe a session, only a single card review."""
        e = quiz.make_entry(card("a"), "graded", "got", 1, datetime(2026, 7, 29, 20, 0))
        self.assertEqual(set(e), {"slug", "path", "ts", "mode", "grade", "rung", "due"})
        for banned in ("session", "duration", "minutes", "count", "streak"):
            self.assertFalse(any(banned in k for k in e), banned)


if __name__ == "__main__":
    unittest.main()
