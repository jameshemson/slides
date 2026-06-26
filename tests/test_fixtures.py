"""Sanity tests for the slop-check fixtures (REQ-004).

The slop detector is prose, judged by an LLM — it cannot be unit-tested.
What CAN be locked down is the fixtures it is judged against: the sloppy
fixture must keep every planted defect and the clean fixture must keep
none, so a future edit cannot silently weaken the verification gate.

Run from the repo root:

    python3 -m unittest discover tests
"""
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "source", "skills", "slop-check", "fixtures")


def _read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


def _max_consecutive_bullets(text):
    """The longest run of consecutive Markdown bullet lines in `text`."""
    longest = run = 0
    for line in text.splitlines():
        if line.lstrip().startswith("- "):
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return longest


class SloppyFixtureTest(unittest.TestCase):
    """sloppy-deck.md must carry every planted defect."""

    def setUp(self):
        self.text = _read("sloppy-deck.md")

    def test_carries_an_em_dash(self):
        self.assertIn("—", self.text)

    def test_carries_a_tacked_on_strapline(self):
        self.assertIn("Strapline:", self.text)

    def test_carries_a_bullet_soup_slide(self):
        self.assertGreaterEqual(_max_consecutive_bullets(self.text), 7)

    def test_carries_a_chart_prose_mismatch(self):
        # A chart/notes figure that contradicts the slide's prose (REQ-007):
        # the Body claims "grew 40%" while the chart and notes say 12%.
        self.assertIn("grew 40%", self.text)
        self.assertIn("12%", self.text)

    def test_carries_an_assistant_artifact(self):
        # Layer 3 (AI-voice): a trailing "shall I draft..." offer, an
        # absolute-fail tell like the em dash.
        self.assertIn("Would you like me to", self.text)

    def test_carries_a_claudism(self):
        # Layer 3: an aphoristic closer ("That's the whole game.").
        self.assertIn("That's the whole game", self.text)


class CleanFixtureTest(unittest.TestCase):
    """clean-deck.md must carry none of the planted defects."""

    def setUp(self):
        self.text = _read("clean-deck.md")

    def test_has_no_em_dash(self):
        self.assertNotIn("—", self.text)

    def test_has_no_strapline(self):
        self.assertNotIn("Strapline:", self.text)

    def test_has_no_bullet_soup(self):
        self.assertLess(_max_consecutive_bullets(self.text), 7)

    def test_has_no_chart_prose_mismatch(self):
        # The clean deck's chart figures agree with its prose (REQ-007).
        self.assertNotIn("grew 40%", self.text)

    def test_has_no_ai_voice_tells(self):
        # The clean deck carries no Layer 3 assistant-artifact or Claudism.
        self.assertNotIn("Would you like me to", self.text)
        self.assertNotIn("That's the whole game", self.text)


if __name__ == "__main__":
    unittest.main()
