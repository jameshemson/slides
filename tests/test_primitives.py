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
import lint
from primitives import (
    plan_stat_row, plan_card_grid, plan_comparison, plan_process,
    plan_timeline, plan_freeform, plan_tree, plan_icon_list,
    ShapeError, _normalise_hex,
)


def _node(label, *children, emphasis=False, icon=None):
    return {"label": label, "emphasis": emphasis, "icon": icon,
            "children": list(children)}
from pptx import Presentation
from pptx.dml.color import RGBColor

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

    def test_draw_renders_box_with_token_fill(self):
        prs = Presentation(TEMPLATE)
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        box = {
            "role": "card-panel", "kind": "box", "container": True,
            "fill": "#4F81BD",
            "left": 457200, "top": 1600200, "width": 3000000, "height": 2000000,
        }
        text = {
            "role": "card-title", "text": "Hi",
            "left": 600000, "top": 1700000, "width": 2000000, "height": 400000,
            "font_pt": 18.0, "colour": "#FFFFFF",
        }
        shapes = primitives.draw(slide, [text, box])  # unordered on purpose
        non_placeholder = [s for s in slide.shapes if not s.is_placeholder]
        self.assertEqual(len(non_placeholder), 2)
        # The box must paint behind the text: it is added first despite being
        # second in the element list (z-order sort).
        self.assertEqual(shapes[0].fill.fore_color.rgb, RGBColor.from_string("4F81BD"))

    def test_optical_centre_top_biased(self):
        # Default placement sits at the optical centre (~45% from top): the row's
        # vertical centre is ABOVE the band's geometric centre, but still in the
        # middle band (not jammed to the top).
        top = min(e["top"] for e in self.els)
        bottom = max(e["top"] + e["height"] for e in self.els)
        row_centre = (top + bottom) / 2
        band_top = TOKENS["grid"]["margin_top"]
        band_bottom = SLIDE_H - TOKENS["grid"]["margin_bottom"]
        band_centre = (band_top + band_bottom) / 2
        self.assertLess(row_centre, band_centre)
        self.assertGreater(row_centre, band_top + 0.25 * (band_bottom - band_top))


def _roles(els):
    return [e["role"] for e in els]


def _fills(els):
    return {e.get("fill") for e in els if e.get("kind") == "box"}


class TestNewPrimitives(unittest.TestCase):
    """card-grid, comparison, process, timeline: planners are pure, produce
    lint-clean geometry, keep colours on-token, and honour emphasis."""

    def _lint_clean(self, els):
        # Every primitive's default output must pass the hard gate.
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

    def test_card_grid_shape_and_lint(self):
        els = plan_card_grid(
            [{"label": "Size"}, {"label": "Know"}, {"label": "Aim"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        # 3 panels + 3 labels, no body.
        self.assertEqual(_roles(els).count("card-panel"), 3)
        self.assertEqual(_roles(els).count("card-label"), 3)
        # Panels are paper with an ink outline (grouped, grey field).
        self.assertEqual(_fills(els), {"#FFFFFF"})

    def test_card_grid_emphasis_fills_accent(self):
        els = plan_card_grid(
            [{"label": "a"}, {"label": "b", "emphasis": True}],
            TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertIn("#4F81BD", _fills(els))  # the hero card fills with accent

    def test_card_grid_rejects_too_many(self):
        with self.assertRaises(ShapeError):
            plan_card_grid([{"label": str(i)} for i in range(7)],
                           TOKENS, SLIDE_W, SLIDE_H)

    def test_comparison_two_panels(self):
        els = plan_comparison(
            [{"header": "Before", "body": "a / b"},
             {"header": "After", "body": "b / a", "emphasis": True}],
            TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("comparison-panel"), 2)
        self.assertIn("#4F81BD", _fills(els))  # the winning side tilts to accent

    def test_comparison_needs_exactly_two(self):
        with self.assertRaises(ShapeError):
            plan_comparison([{"header": "solo"}], TOKENS, SLIDE_W, SLIDE_H)

    def test_process_numbered_with_connectors(self):
        els = plan_process(
            [{"label": "Plan"}, {"label": "Create"}, {"label": "Deliver"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("process-step"), 3)
        self.assertEqual(_roles(els).count("process-connector"), 2)  # n-1
        nums = [e["text"] for e in els if e["role"] == "process-number"]
        self.assertEqual(nums, ["1", "2", "3"])
        # The number is the accent; the label is ink (lead by size + colour).
        num = next(e for e in els if e["role"] == "process-number")
        self.assertEqual(num["colour"], "#4F81BD")

    def test_process_rejects_over_five(self):
        with self.assertRaises(ShapeError):
            plan_process([{"label": str(i)} for i in range(6)],
                         TOKENS, SLIDE_W, SLIDE_H)

    def test_timeline_dots_rail_labels(self):
        els = plan_timeline(
            [{"date": "26", "event": "Kick"},
             {"date": "27", "event": "Ship", "emphasis": True},
             {"date": "28", "event": "Scale"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("timeline-dot"), 3)
        self.assertEqual(_roles(els).count("timeline-rail"), 2)   # n-1 segments
        self.assertEqual(_roles(els).count("timeline-label"), 3)
        # The emphasised milestone dot is the accent; the rest are muted to ink.
        dots = [e for e in els if e["role"] == "timeline-dot"]
        self.assertIn("#4F81BD", {d["fill"] for d in dots})

    def test_freeform_plans_lint_clean_kit(self):
        # The whole freeform kit (panel/text/arrow/dot/line) plans lint-clean
        # when placed without overlap; text sits inside its container panel.
        els = plan_freeform([
            {"kind": "box", "fill": "paper", "stroke": "ink",
             "placement": {"cols": (1, 6), "rows": (1, 10)}},
            {"kind": "text", "scale": "h1", "colour": "ink", "text": "In panel",
             "placement": {"cols": (1, 6), "rows": (1, 4)}},
            {"kind": "arrow", "colour": "ink",
             "placement": {"cols": (7, 8), "rows": (5, 6)}},
            {"kind": "dot", "colour": "accent",
             "placement": {"cols": (9, 10), "rows": (1, 3)}},
            {"kind": "line", "colour": "ink",
             "placement": {"cols": (1, 12), "rows": (12, 12)}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        roles = set(_roles(els))
        self.assertEqual(roles, {"freeform-panel", "freeform-text",
                                 "freeform-arrow", "freeform-dot", "freeform-line"})

    def test_freeform_colours_resolve_to_tokens(self):
        els = plan_freeform([
            {"kind": "box", "fill": "accent",
             "placement": {"cols": (1, 12), "rows": (1, 8)}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(els[0]["fill"], "#4F81BD")  # role name -> brand hex

    def test_icon_list_rows(self):
        rows = [{"icon": "growth", "text": "Up"}, {"icon": "team", "text": "Bigger"}]
        els = plan_icon_list(rows, TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("iconlist-icon"), 2)
        self.assertEqual(_roles(els).count("iconlist-text"), 2)
        icon = next(e for e in els if e["role"] == "iconlist-icon")
        self.assertEqual(icon["kind"], "icon")
        self.assertEqual(icon["colour"], "#4F81BD")  # accent marker

    def test_card_with_icon_lint_clean(self):
        cards = [{"label": "Grow", "icon": "growth"},
                 {"label": "Serve", "icon": "team"}]
        els = plan_card_grid(cards, TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("card-icon"), 2)

    def test_panel_corner_honours_shape_token(self):
        # Default (no shape token) -> rounded; a sharp brand -> plain rectangle.
        cards = [{"label": "A"}, {"label": "B"}, {"label": "C"}]
        default = plan_card_grid(cards, TOKENS, SLIDE_W, SLIDE_H)
        panel = next(e for e in default if e["role"] == "card-panel")
        self.assertEqual(panel["shape"], "rounded_rectangle")

        sharp = dict(TOKENS, shape={"corner": "sharp"})
        panel2 = next(e for e in plan_card_grid(cards, sharp, SLIDE_W, SLIDE_H)
                      if e["role"] == "card-panel")
        self.assertEqual(panel2["shape"], "rect")

    def test_tree_org_chart_lint_clean(self):
        root = _node("CEO", _node("Eng"), _node("Sales"), _node("Ops"))
        els = plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("tree-node"), 4)
        self.assertEqual(_roles(els).count("tree-edge"), 3)  # N-1 edges

    def test_tree_depth_three_lint_clean(self):
        root = _node("R", _node("A", _node("A1"), _node("A2")), _node("B"))
        self._lint_clean(plan_tree(root, TOKENS, SLIDE_W, SLIDE_H))

    def test_tree_emphasis_fills_accent(self):
        root = _node("Vision", _node("Now", emphasis=True), _node("Next"))
        els = plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("#4F81BD", _fills(els))

    def test_tree_with_icons_lower_cap(self):
        # 7 icon'd nodes exceeds the with-icons cap of 6.
        kids = [_node(f"c{i}", icon="growth") for i in range(6)]
        root = _node("root", *kids)  # 7 nodes, all-but-root icon'd
        with self.assertRaises(ShapeError):
            plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)

    def test_tree_over_cap_raises(self):
        root = _node("R", *[_node(f"c{i}") for i in range(9)])  # 10 nodes
        with self.assertRaises(ShapeError):
            plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)

    def test_tree_too_deep_raises(self):
        root = _node("a", _node("b", _node("c", _node("d", _node("e")))))
        with self.assertRaises(ShapeError):
            plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)

    def test_all_defaults_stay_under_cap(self):
        # 5-step process with details is the worst case; must fit the cap.
        els = plan_process(
            [{"label": f"S{i}", "detail": "why & who"} for i in range(5)],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertLessEqual(len(els), lint.ELEMENT_CAP)
        self._lint_clean(els)


if __name__ == "__main__":
    unittest.main()
