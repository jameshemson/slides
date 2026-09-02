"""Tests for source/skills/build-deck/scripts/stamp.py"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")
DECK_SPEC = os.path.join(FIXTURES, "sample-deck.md")
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
RENDER_PY = os.path.join(SCRIPTS, "render.py")
sys.path.insert(0, SCRIPTS)

import deck_to_spec  # noqa: E402
import stamp  # noqa: E402
from pptx import Presentation  # noqa: E402

BRAND = {
    "fidelity": "brand",
    "fonts": {"heading": "Calibri", "body": "Calibri"},
    "colours": {
        "accent": "#4F81BD",
        "accent2": "#C0504D",
        "ink": "#000000",
        "paper": "#FFFFFF",
    },
}

EXPECTED_ROLES = ["title", "section", "statement", "title-content", "two-column", "quote"]


def _blank_deck(path, count):
    prs = Presentation()
    prs.slide_width = 12192000
    prs.slide_height = 6858000
    for _ in range(count):
        prs.slides.add_slide(prs.slide_layouts[6])
    prs.save(path)
    return path


class LineageCommentTest(unittest.TestCase):
    def test_matches_regex_and_sha(self):
        comment = stamp.lineage_comment(DECK_SPEC)
        match = deck_to_spec.STAMP_RE.match(comment)
        self.assertIsNotNone(match, comment)
        with open(DECK_SPEC, "rb") as fh:
            expected = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(match.group("sha"), expected)
        self.assertEqual(match.group("name"), "sample-deck.md")


class StampDeckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="slides-stamp-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_names_slides_in_spec_order(self):
        deck = _blank_deck(os.path.join(self.tmp, "six.pptx"), 6)
        self.assertEqual(stamp.stamp_deck(deck, DECK_SPEC), 6)
        prs = Presentation(deck)
        self.assertEqual(
            [s.name for s in prs.slides],
            [f"slides-role:{role}" for role in EXPECTED_ROLES],
        )
        self.assertEqual(prs.core_properties.comments, stamp.lineage_comment(DECK_SPEC))

    def test_out_path_leaves_input_untouched(self):
        deck = _blank_deck(os.path.join(self.tmp, "six.pptx"), 6)
        out = os.path.join(self.tmp, "stamped.pptx")
        stamp.stamp_deck(deck, DECK_SPEC, out)
        self.assertNotEqual(Presentation(deck).slides[0].name, "slides-role:title")
        self.assertEqual(Presentation(out).slides[0].name, "slides-role:title")

    def test_count_mismatch_exits_1(self):
        deck = _blank_deck(os.path.join(self.tmp, "five.pptx"), 5)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = stamp.main([deck, "--spec", DECK_SPEC])
        self.assertEqual(code, 1)
        self.assertIn(
            "error: deck has 5 slide(s) but spec sample-deck.md has 6", err.getvalue()
        )

    def test_cli_success_message(self):
        deck = _blank_deck(os.path.join(self.tmp, "six.pptx"), 6)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = stamp.main([deck, "--spec", DECK_SPEC])
        self.assertEqual(code, 0)
        self.assertIn("stamped 6 slide(s)", out.getvalue())

    def test_render_stamp_equals_helper(self):
        brand_path = os.path.join(self.tmp, "brand.json")
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(BRAND, fh)
        out = os.path.join(self.tmp, "rendered.pptx")
        proc = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", DECK_SPEC, "--brand", brand_path, "--out", out],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            Presentation(out).core_properties.comments, stamp.lineage_comment(DECK_SPEC)
        )

    def test_render_calls_helper(self):
        with open(RENDER_PY, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("stamp_mod.lineage_comment(spec_path)", source)
        self.assertNotIn("hashlib.sha256(", source)


if __name__ == "__main__":
    unittest.main()
