"""Tests for source/skills/build-deck/scripts/lint.py"""
import sys
import os
import unittest

# Add the scripts directory to sys.path so `import lint` works.
_SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "source",
    "skills",
    "build-deck",
    "scripts",
)
sys.path.insert(0, os.path.abspath(_SCRIPTS_DIR))

import lint

TOKENS = {
    "grid": {
        "margin_x": 457200,
        "margin_top": 1600200,
        "margin_bottom": 731837,
        "columns": 12,
        "gutter": 152400,
        "baseline": 91211,
    },
    "type_scale": {
        "display": 40.0,
        "h1": 28.0,
        "body": 18.0,
        "caption": 12.0,
    },
    "colour_roles": {
        "ink": "#000000",
        "paper": "#FFFFFF",
        "accent": "#4F81BD",
        "muted": "#C0504D",
    },
}

SLIDE_W, SLIDE_H = 9144000, 6858000


def good_elements():
    return [
        {
            "role": "stat-number",
            "text": "56",
            "left": 457200,
            "top": 2000000,
            "width": 2000000,
            "height": 600000,
            "font_pt": 40.0,
            "colour": "#4F81BD",
        },
        {
            "role": "stat-label",
            "text": "Days",
            "left": 457200,
            "top": 2700000,
            "width": 2000000,
            "height": 200000,
            "font_pt": 12.0,
            "colour": "#000000",
        },
        {
            "role": "stat-number",
            "text": "4%",
            "left": 4000000,
            "top": 2000000,
            "width": 2000000,
            "height": 600000,
            "font_pt": 40.0,
            "colour": "#4F81BD",
        },
    ]


class TestCleanPasses(unittest.TestCase):
    def test_clean_passes(self):
        els = good_elements()
        result = lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIsNone(result)
        self.assertEqual(lint.check_colours(els, TOKENS), [])
        self.assertEqual(lint.check_sizes(els, TOKENS), [])
        self.assertEqual(lint.check_within_margins(els, TOKENS, SLIDE_W, SLIDE_H), [])
        self.assertEqual(lint.check_no_overlap(els), [])
        self.assertEqual(lint.check_count(els), [])


class TestColourRule(unittest.TestCase):
    def test_off_token_colour(self):
        els = good_elements()
        els[0]["colour"] = "#ABCDEF"
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        msg = str(ctx.exception)
        self.assertIn("[colour]", msg)
        self.assertIn(els[0]["text"], msg)
        # Also verify the helper itself returns non-empty
        violations = lint.check_colours(els, TOKENS)
        self.assertTrue(len(violations) > 0)


class TestSizeRule(unittest.TestCase):
    def test_off_scale_size(self):
        els = good_elements()
        els[0]["font_pt"] = 99.0
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        msg = str(ctx.exception)
        self.assertIn("[size]", msg)


class TestMarginRule(unittest.TestCase):
    def test_out_of_margin(self):
        els = good_elements()
        els[0]["left"] = 0
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        msg = str(ctx.exception)
        self.assertIn("[margins]", msg)


class TestOverlapRule(unittest.TestCase):
    def test_overlap(self):
        els = good_elements()
        # Make elements 0 and 2 share the exact same rect
        els[2]["left"] = els[0]["left"]
        els[2]["top"] = els[0]["top"]
        els[2]["width"] = els[0]["width"]
        els[2]["height"] = els[0]["height"]
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        msg = str(ctx.exception)
        self.assertIn("[overlap]", msg)


class TestCountRule(unittest.TestCase):
    def test_over_cap(self):
        # Build 13 elements for the count rule.
        # We only need check_count to fire; we don't require all other rules to pass.
        thirteen = []
        for i in range(13):
            thirteen.append({
                "role": f"item-{i}",
                "text": str(i),
                "left": 457200,
                "top": 1600200 + i * 50000,
                "width": 500000,
                "height": 40000,
                "font_pt": 12.0,
                "colour": "#000000",
            })

        # The rule helper must flag the count
        violations = lint.check_count(thirteen)
        self.assertTrue(len(violations) > 0)
        self.assertIn("[count]", violations[0])

        # check() must also raise (count violation alone is sufficient)
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(thirteen, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[count]", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
