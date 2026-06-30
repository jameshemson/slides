"""Tests for primitives.py — D-002 carve-out."""
import sys
import os
import unittest

# Add the scripts directory to sys.path so `import primitives` resolves.
_SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "source",
    "skills",
    "build-deck",
    "scripts",
)
sys.path.insert(0, os.path.abspath(_SCRIPTS_DIR))

import primitives
from primitives import plan_stat_row, ShapeError, _normalise_hex
from pptx import Presentation

TEMPLATE = os.path.join(os.path.dirname(__file__), "fixtures", "sample-template.pptx")

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
STATS = [
    {"value": "56", "label": "Days"},
    {"value": "4%", "label": "Win rate"},
    {"value": "120", "label": "Deals"},
]


class TestPlanStatRow(unittest.TestCase):

    def setUp(self):
        self.els = plan_stat_row(STATS, TOKENS, SLIDE_W, SLIDE_H)

    def test_element_count(self):
        els = self.els
        self.assertEqual(len(els), 6)
        numbers = [e for e in els if e["role"] == "stat-number"]
        labels = [e for e in els if e["role"] == "stat-label"]
        self.assertEqual(len(numbers), 3)
        self.assertEqual(len(labels), 3)

    def test_margin_alignment(self):
        els = self.els
        left_min = min(e["left"] for e in els)
        right_max = max(e["left"] + e["width"] for e in els)
        self.assertEqual(left_min, 457200)
        self.assertEqual(right_max, SLIDE_W - 457200)
        self.assertEqual(right_max, 8686800)

    def test_number_and_label_style(self):
        els = self.els
        number = next(e for e in els if e["role"] == "stat-number")
        label = next(e for e in els if e["role"] == "stat-label")
        self.assertEqual(number["font_pt"], 40.0)
        self.assertEqual(number["colour"], "#4F81BD")
        self.assertEqual(label["font_pt"], 12.0)
        self.assertEqual(label["colour"], "#000000")

    def test_cells_separated_by_gutter(self):
        gutter = TOKENS["grid"]["gutter"]
        numbers = sorted(
            [e for e in self.els if e["role"] == "stat-number"],
            key=lambda e: e["left"],
        )
        for idx in range(len(numbers) - 1):
            prev = numbers[idx]
            nxt = numbers[idx + 1]
            # No overlap.
            self.assertLessEqual(prev["left"] + prev["width"], nxt["left"])
            # Gap is exactly gutter for all but the last boundary (last cell
            # absorbs rounding remainder, so gap >= gutter).
            if idx < len(numbers) - 2:
                self.assertEqual(nxt["left"], prev["left"] + prev["width"] + gutter)
            else:
                self.assertGreaterEqual(nxt["left"], prev["left"] + prev["width"] + gutter)

    def test_number_above_label_no_overlap(self):
        baseline = TOKENS["grid"]["baseline"]
        numbers = {i: e for i, e in enumerate(self.els) if e["role"] == "stat-number"}
        labels = {i: e for i, e in enumerate(self.els) if e["role"] == "stat-label"}
        # Elements alternate: number, label, number, label...
        num_list = [e for e in self.els if e["role"] == "stat-number"]
        lab_list = [e for e in self.els if e["role"] == "stat-label"]
        for num, lab in zip(num_list, lab_list):
            # Number top + height + baseline == label top.
            self.assertEqual(num["top"] + num["height"] + baseline, lab["top"])
            # No vertical overlap.
            self.assertLessEqual(num["top"] + num["height"], lab["top"])

    def test_empty_stats_raises(self):
        with self.assertRaises(ShapeError):
            plan_stat_row([], TOKENS, SLIDE_W, SLIDE_H)

    def test_draw_adds_nonplaceholder_shapes(self):
        prs = Presentation(TEMPLATE)
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        els = self.els
        shapes = primitives.draw(slide, els)
        non_placeholder = [s for s in slide.shapes if not s.is_placeholder]
        self.assertEqual(len(non_placeholder), 6)

    def test_normalise_hex(self):
        self.assertEqual(_normalise_hex("#abc"), "#AABBCC")
        self.assertEqual(_normalise_hex("4f81bd"), "#4F81BD")
        self.assertIsNone(_normalise_hex("nope"))


if __name__ == "__main__":
    unittest.main()
