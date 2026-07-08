"""Tests for primitives.py — D-002 carve-out."""
import json
import math
import shutil
import subprocess
import sys
import os
import tempfile
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
    plan_cycle, plan_matrix, ShapeError, _normalise_hex,
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

    def test_label_breaks_on_slash(self):
        # ' / ' in a label becomes a line break (the card-body convention);
        # every label box takes the tallest line count so bottoms align.
        stats = [{"value": "56", "label": "Days / to close"},
                 {"value": "4%", "label": "Win rate"}]
        els = plan_stat_row(stats, TOKENS, SLIDE_W, SLIDE_H)
        labels = [e for e in els if e["role"] == "stat-label"]
        self.assertEqual(labels[0]["text"], "Days\nto close")
        self.assertEqual(labels[1]["text"], "Win rate")
        one_line = round(12.0 * primitives.EMU_PER_PT * primitives.LINE_HEIGHT)
        for lab in labels:  # both boxes sized for two lines
            self.assertEqual(lab["height"], 2 * one_line)
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

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

    def test_card_grid_over_good_count_is_advisory(self):
        # 7 cards: no hard cap any more — plans lint-clean, card-count advises.
        els = plan_card_grid([{"label": str(i)} for i in range(7)],
                             TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("card-count", ids)

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

    def test_process_over_five_is_advisory(self):
        # 6 steps: no hard cap any more — plans lint-clean, process-count advises.
        els = plan_process([{"label": str(i)} for i in range(6)],
                           TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("process-count", ids)

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

    def test_cycle_ring(self):
        for n in (2, 3, 4, 5, 6):
            els = plan_cycle([{"label": f"S{i}"} for i in range(n)],
                             TOKENS, SLIDE_W, SLIDE_H)
            self._lint_clean(els)
            self.assertEqual(_roles(els).count("cycle-node"), n)
            self.assertEqual(_roles(els).count("cycle-edge"), n)  # closes the loop

    def test_cycle_over_six_is_advisory(self):
        # 7 stages: the ring just gets denser — lint-clean, cycle-count advises.
        els = plan_cycle([{"label": str(i)} for i in range(7)],
                         TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("cycle-count", ids)

    def test_matrix_quadrants(self):
        spec = {"x": "Effort", "y": "Impact", "quadrants": [
            {"label": "QW"}, {"label": "BB", "emphasis": True},
            {"label": "DP"}, {"label": "FI"}]}
        els = plan_matrix(spec, TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("matrix-cell"), 4)
        self.assertEqual(_roles(els).count("matrix-axis"), 2)  # x + y captions
        self.assertIn("#4F81BD", _fills(els))  # emphasised quadrant

    def test_matrix_needs_four(self):
        with self.assertRaises(ShapeError):
            plan_matrix({"quadrants": [{"label": "a"}, {"label": "b"}]},
                        TOKENS, SLIDE_W, SLIDE_H)

    def test_process_icon_replaces_number(self):
        els = plan_process([{"label": "Plan", "icon": "idea"},
                            {"label": "Ship", "icon": "fast"}],
                           TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("process-icon"), 2)
        self.assertEqual(_roles(els).count("process-number"), 0)  # icon takes the slot

    def test_comparison_icon(self):
        els = plan_comparison([{"header": "Before", "body": "slow", "icon": "decline"},
                               {"header": "After", "body": "fast", "icon": "growth",
                                "emphasis": True}], TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        self.assertEqual(_roles(els).count("comparison-icon"), 2)

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

    def test_tree_with_icons_large_hits_element_cap(self):
        # 7 icon'd nodes: no hard count cap — the planner plans it, and the
        # lint's element cap (box+text+icon per node) is the backstop.
        kids = [_node(f"c{i}", icon="growth") for i in range(6)]
        root = _node("root", *kids)  # 7 nodes, all-but-root icon'd
        els = plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        with self.assertRaises(lint.LintError):
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)

    def test_tree_large_hits_element_cap(self):
        # 10 nodes plan without a ShapeError; 29 elements bust ELEMENT_CAP, and
        # the tree-count advisory names the craft rule.
        root = _node("R", *[_node(f"c{i}") for i in range(9)])  # 10 nodes
        els = plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        with self.assertRaises(lint.LintError):
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("tree-count", ids)

    def test_tree_deep_is_advisory(self):
        # Depth 5: plans lint-clean; tree-depth advises 3 levels or fewer.
        root = _node("a", _node("b", _node("c", _node("d", _node("e")))))
        els = plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        self._lint_clean(els)
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("tree-depth", ids)

    def test_all_defaults_stay_under_cap(self):
        # 5-step process with details is the worst case; must fit the cap.
        els = plan_process(
            [{"label": f"S{i}", "detail": "why & who"} for i in range(5)],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertLessEqual(len(els), lint.ELEMENT_CAP)
        self._lint_clean(els)


# A small header + two data rows: one text column, two money/percent columns.
TABLE = {
    "header": ["Metric", "Q1", "Q2"],
    "rows": [
        {"cells": ["Revenue", "$1.2M", "$1.5M"], "emphasis": False},
        {"cells": ["Growth", "4%", "9%"], "emphasis": False},
    ],
}


class TestPlanTable(unittest.TestCase):
    """plan_table (D-001/D-002/D-004/D-008/D-009): ONE native-table element that
    carries its colours/sizes as vectors and per-column alignment; hard caps and
    a band-fit guard raise ShapeError.

    Contract pinned here (the implementer follows these exact keys):
      element keys : kind "table", role "table-grid", text, left/top/width/height,
                     fills [hex], text_colours [hex], font_pts [pt], stroke (hairline),
                     col_aligns [ "left" | "right" ]  (per column, header order)
      alignment key: col_aligns
    """

    # Grid/band geometry the existing token fixture implies.
    MARGIN_X = 457200
    CONTENT_LEFT = 457200
    CONTENT_RIGHT = SLIDE_W - 457200        # 8686800
    BAND_TOP = 1600200
    BAND_BOTTOM = SLIDE_H - 731837          # 6126163

    def _plan(self, table, region=None):
        return primitives.plan_table(table, TOKENS, SLIDE_W, SLIDE_H, region)

    def test_returns_single_table_element(self):
        els = self._plan(TABLE)
        self.assertEqual(len(els), 1)          # D-001: one GraphicFrame, not per-cell boxes
        el = els[0]
        self.assertEqual(el["kind"], "table")
        self.assertEqual(el["role"], "table-grid")
        # A text key so a lint margins violation can name the element.
        self.assertIn("text", el)
        self.assertIsInstance(el["text"], str)
        # D-008 vector keys the lint validates.
        self.assertIsInstance(el["fills"], list)
        self.assertIsInstance(el["text_colours"], list)
        self.assertIsInstance(el["font_pts"], list)

    def test_geometry_within_content_span_and_band(self):
        el = self._plan(TABLE)[0]
        # Spans margin to margin (the _content_span rule the other planners use).
        self.assertEqual(el["left"], self.CONTENT_LEFT)
        self.assertEqual(el["left"] + el["width"], self.CONTENT_RIGHT)
        # Sits inside the band.
        self.assertGreaterEqual(el["top"], self.BAND_TOP)
        self.assertLessEqual(el["top"] + el["height"], self.BAND_BOTTOM)
        self.assertGreater(el["width"], 0)
        self.assertGreater(el["height"], 0)

    def test_optical_centre_top(self):
        # Same optical-centre placement as plan_card_grid: the block's vertical
        # centre sits above the band centre, but not jammed to the top.
        el = self._plan(TABLE)[0]
        band_centre = (self.BAND_TOP + self.BAND_BOTTOM) / 2
        row_centre = el["top"] + el["height"] / 2
        self.assertLess(row_centre, band_centre)
        self.assertGreater(
            row_centre, self.BAND_TOP + 0.25 * (self.BAND_BOTTOM - self.BAND_TOP))

    def test_default_fills_text_colours_and_font(self):
        # D-002: header = ink fill + paper text; data = paper fill + ink text;
        # a muted bottom hairline rides the scalar `stroke` key (D-008).
        el = self._plan(TABLE)[0]
        ink = TOKENS["colour_roles"]["ink"]
        paper = TOKENS["colour_roles"]["paper"]
        muted = TOKENS["colour_roles"]["muted"]
        self.assertIn(ink, el["fills"])       # header band
        self.assertIn(paper, el["fills"])     # data band
        self.assertIn(ink, el["text_colours"])
        self.assertIn(paper, el["text_colours"])
        self.assertEqual(el["stroke"], muted)  # row hairline
        # Body type-scale size throughout (no shrink-to-fit).
        self.assertIn(TOKENS["type_scale"]["body"], el["font_pts"])
        self.assertTrue(all(p == TOKENS["type_scale"]["body"] for p in el["font_pts"]))

    def test_nine_data_rows_plan_at_body(self):
        # 9 data rows: no hard row cap — the full band fits them at body size
        # (no step-down), and the table-count advisory names the craft rule.
        table = {"header": ["A", "B", "C"],
                 "rows": [{"cells": [str(i), "x", "y"], "emphasis": False}
                          for i in range(9)]}
        els = self._plan(table)
        self.assertEqual(len(els), 1)
        self.assertEqual(els[0]["font_pts"], [TOKENS["type_scale"]["body"]])
        self.assertFalse(els[0]["font_stepped"])
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("table-count", ids)

    def test_six_columns_is_advisory(self):
        # 6 columns: no hard column cap — table-column-count advises.
        table = {"header": ["A", "B", "C", "D", "E", "F"],
                 "rows": [{"cells": ["1", "2", "3", "4", "5", "6"],
                           "emphasis": False}]}
        els = self._plan(table)
        self.assertEqual(len(els), 1)
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))
        ids = {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}
        self.assertIn("table-column-count", ids)

    def test_rejects_one_column(self):
        table = {"header": ["Only"],
                 "rows": [{"cells": ["a"], "emphasis": False},
                          {"cells": ["b"], "emphasis": False}]}  # a list, not a table
        with self.assertRaises(ShapeError):
            self._plan(table)

    def test_band_overflow_raises_named(self):
        # A short placed region: (1 + n_rows) * row_h cannot fit, so the band-fit
        # guard fires before drawing and the message names how many rows fit /
        # tells the author to cut rows or split the slide (D-004).
        short = (self.MARGIN_X, self.BAND_TOP,
                 SLIDE_W - 2 * self.MARGIN_X, 400000)
        table = {"header": ["A", "B", "C"],
                 "rows": [{"cells": [str(i), "x", "y"], "emphasis": False}
                          for i in range(3)]}
        with self.assertRaises(ShapeError) as cm:
            self._plan(table, region=short)
        self.assertIn("row", str(cm.exception).lower())

    def test_emphasis_row_accent_fill_paper_text(self):
        # REQ-002 / D-002: an emphasised row fills with accent and reverses to
        # paper text.
        table = {"header": ["Metric", "Q1", "Q2"],
                 "rows": [
                     {"cells": ["Revenue", "$1.2M", "$1.5M"], "emphasis": False},
                     {"cells": ["Total", "$2.7M", "$3.0M"], "emphasis": True},
                 ]}
        el = self._plan(table)[0]
        self.assertIn(TOKENS["colour_roles"]["accent"], el["fills"])
        self.assertIn(TOKENS["colour_roles"]["paper"], el["text_colours"])

    def test_numeric_columns_right_text_left(self):
        # D-009: a column whose data cells are all numeric (money/percent) is
        # right-aligned; a text column stays left. col_aligns is header order.
        el = self._plan(TABLE)[0]
        aligns = el["col_aligns"]
        self.assertEqual(len(aligns), 3)
        self.assertEqual(aligns[0], "left")    # "Revenue" / "Growth" — text
        self.assertEqual(aligns[1], "right")   # "$1.2M" / "4%"      — numeric
        self.assertEqual(aligns[2], "right")   # "$1.5M" / "9%"      — numeric


class TestWrapAwareHeights(unittest.TestCase):
    """Planners estimate word-wrap, so declared heights cover the rendered
    text — the fix for text spilling out of its box and overlapping the
    element below, which the box-only lint could not see."""

    LONG = ("A genuinely long run of body copy that the renderer will "
            "word-wrap across several lines inside a narrow card cell")

    def test_wrapped_lines_counts_wrap_not_just_breaks(self):
        wide = primitives._wrapped_lines("short", 3000000, 18.0)
        self.assertEqual(wide, 1)
        narrow = primitives._wrapped_lines(self.LONG, 1500000, 18.0)
        self.assertGreater(narrow, 2)
        # Explicit breaks still count.
        self.assertEqual(primitives._wrapped_lines("a\nb\nc", 3000000, 18.0), 3)
        # Wider box or smaller type never needs MORE lines.
        self.assertLessEqual(
            primitives._wrapped_lines(self.LONG, 3000000, 18.0), narrow)
        self.assertLessEqual(
            primitives._wrapped_lines(self.LONG, 1500000, 12.0), narrow)

    def test_card_body_box_grows_to_wrapped_height(self):
        cards = [{"label": "One", "body": self.LONG},
                 {"label": "Two", "body": "Short."}]
        els = plan_card_grid(cards, TOKENS, SLIDE_W, SLIDE_H)
        body = next(e for e in els if e["role"] == "card-body")
        two_lines = 2 * primitives._line_h(TOKENS["type_scale"]["body"])
        self.assertGreater(body["height"], two_lines)
        # And the text still sits inside its panel — the lint stays clean.
        lint.check(els, TOKENS, SLIDE_W, SLIDE_H)

    def test_card_text_too_deep_for_band_raises(self):
        cards = [{"label": "One", "body": " / ".join([self.LONG] * 6)}
                 for _ in range(3)]
        short_band = (457200, 1600200, 8229600, 1200000)
        with self.assertRaises(ShapeError) as cm:
            plan_card_grid(cards, TOKENS, SLIDE_W, SLIDE_H, region=short_band)
        self.assertIn("wraps deeper", str(cm.exception))

    def test_comparison_panels_grow_and_stay_lint_clean(self):
        sides = [{"header": "Before", "body": self.LONG},
                 {"header": "After", "body": "Better."}]
        els = plan_comparison(sides, TOKENS, SLIDE_W, SLIDE_H)
        lint.check(els, TOKENS, SLIDE_W, SLIDE_H)

    def test_timeline_long_events_grow_label_and_stay_lint_clean(self):
        nodes = [{"date": "Q1", "event": self.LONG},
                 {"date": "Q2", "event": "Ship"},
                 {"date": "Q3", "event": "Scale"}]
        els = plan_timeline(nodes, TOKENS, SLIDE_W, SLIDE_H)
        label = next(e for e in els if e["role"] == "timeline-label")
        line_h = primitives._line_h(TOKENS["type_scale"]["body"])
        self.assertGreater(label["height"], 2 * line_h)
        lint.check(els, TOKENS, SLIDE_W, SLIDE_H)

    def test_icon_list_rows_grow_to_wrapped_text(self):
        rows = [{"icon": "check", "text": self.LONG},
                {"icon": "check", "text": "Short."}]
        els = plan_icon_list(rows, TOKENS, SLIDE_W, SLIDE_H)
        text = next(e for e in els if e["role"] == "iconlist-text")
        self.assertGreater(
            text["height"], primitives._line_h(TOKENS["type_scale"]["body"]))
        lint.check(els, TOKENS, SLIDE_W, SLIDE_H)

    def test_matrix_body_too_deep_for_cell_raises(self):
        quads = [{"label": "Q", "body": " / ".join([self.LONG] * 4)}
                 for _ in range(4)]
        with self.assertRaises(ShapeError) as cm:
            plan_matrix({"quadrants": quads}, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("wraps deeper", str(cm.exception))

    def test_freeform_text_overflowing_placement_raises(self):
        els = [{"kind": "text", "text": self.LONG, "scale": "h1",
                "colour": "ink", "placement": {"cols": (1, 3), "rows": (1, 2)}}]
        with self.assertRaises(ShapeError) as cm:
            plan_freeform(els, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("overflows its placement", str(cm.exception))

    def test_tree_label_too_long_for_node_raises(self):
        root = _node("Root", *[_node(self.LONG)] + [_node("B"), _node("C")])
        with self.assertRaises(ShapeError) as cm:
            plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("wraps deeper", str(cm.exception))

    def test_cycle_label_too_long_for_node_raises(self):
        steps = [{"label": self.LONG}, {"label": "B"}, {"label": "C"}]
        with self.assertRaises(ShapeError) as cm:
            plan_cycle(steps, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("wraps deeper", str(cm.exception))

    def test_stat_row_long_labels_grow_and_stay_lint_clean(self):
        stats = [{"value": "56", "label": "Average number of days from first "
                                          "contact to a signed agreement"},
                 {"value": "4%", "label": "Win rate"}]
        els = plan_stat_row(stats, TOKENS, SLIDE_W, SLIDE_H)
        label = next(e for e in els if e["role"] == "stat-label")
        line_h = primitives._line_h(TOKENS["type_scale"]["caption"])
        self.assertGreater(label["height"], line_h)
        lint.check(els, TOKENS, SLIDE_W, SLIDE_H)


class DrawNameStampTest(unittest.TestCase):
    """draw() must stamp an element's optional `name` onto the shape it
    creates — the revise round trip reads this back to match a rendered
    shape to its spec element."""

    def test_text_and_box_name_stamp_round_trips(self):
        prs = Presentation(TEMPLATE)
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        text = {
            "role": "bodyslide-title", "text": "Hi",
            "left": 600000, "top": 1700000, "width": 2000000, "height": 400000,
            "font_pt": 18.0, "colour": "#FFFFFF",
            "name": "slides-field:Title",
        }
        box = {
            "role": "card-panel", "kind": "box", "container": True,
            "fill": "#4F81BD",
            "left": 457200, "top": 1600200, "width": 3000000, "height": 2000000,
            "name": "slides-field:Title",
        }
        text_shape, box_shape = primitives.draw(slide, [text, box])
        self.assertEqual(text_shape.name, "slides-field:Title")
        self.assertEqual(box_shape.name, "slides-field:Title")

    def test_element_without_name_keeps_library_default(self):
        prs = Presentation(TEMPLATE)
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        text = {
            "role": "card-title", "text": "Hi",
            "left": 600000, "top": 1700000, "width": 2000000, "height": 400000,
            "font_pt": 18.0, "colour": "#FFFFFF",
        }
        shapes = primitives.draw(slide, [text])
        self.assertFalse(shapes[0].name.startswith("slides-field:"))


# --- glyph-aware estimator + stat-number ladder (D-407/D-408) ----------------
#
# The live incident these pin: a composed stat-row on the pack "presented"
# ladder (display 96pt) with the pack grid on a 16:9 canvas gave each of 4
# stats a 2 590 800 EMU cell; "$8.4M" is a single space-free token, so the
# old whitespace-split estimator counted 1 line, but PowerPoint CHARACTER-
# wraps an over-long token — the real render was 2 lines and the wrapped "M"
# overprinted the label below.

# The exact pack tokens of the incident (tokens.pack_grid / PACK_TYPE_SCALES
# "presented", pinned literally so this test cannot drift with the pack).
PACK_TOKENS = {
    "grid": {
        "margin_x": 609600,
        "margin_top": 548640,
        "margin_bottom": 548640,
        "columns": 12,
        "gutter": 203200,
        "baseline": 91211,
    },
    "type_scale": {
        "display": 96.0,
        "title": 60.0,
        "h1": 40.0,
        "body": 24.0,
        "caption": 16.0,
    },
    "colour_roles": {
        "ink": "#1A1A1A",
        "paper": "#FFFFFF",
        "accent": "#0B5FFF",
        "muted": "#6B7280",
    },
}
PACK_W, PACK_H = 12192000, 6858000
# 4 stats across the pack grid: (content_w - 3*gutter) // 4.
PACK_CELL_W = (PACK_W - 2 * 609600 - 3 * 203200) // 4   # 2590800

PACK_STATS = [
    {"value": "$8.4M", "label": "Revenue / +12% QoQ"},
    {"value": "412", "label": "Enterprise customers"},
    {"value": "98.2%", "label": "Retention / trailing 12 months"},
    {"value": "$1.9M", "label": "Net new ARR"},
]


class TokenWrapTest(unittest.TestCase):
    """D-407: _wrapped_lines is glyph-aware and token-safe — a single
    space-free token wider than its box counts the character-wrap lines
    PowerPoint will actually draw, instead of assuming one line."""

    def test_dollar_stat_char_wraps_at_display_size(self):
        # The fix: "$8.4M" at 96pt in a 2590800 EMU cell is ~3.09em against a
        # ~2.13em budget — two rendered lines, not one.
        self.assertGreaterEqual(
            primitives._wrapped_lines("$8.4M", PACK_CELL_W, 96.0), 2)

    def test_short_number_stays_one_line(self):
        self.assertEqual(
            primitives._wrapped_lines("8.4", PACK_CELL_W, 96.0), 1)

    def test_long_url_token_char_wraps_to_ceil(self):
        url = "https://example.com/a/very/long/path/that/never/breaks"
        budget_em = PACK_CELL_W / (18.0 * primitives.EMU_PER_PT)
        expected = math.ceil(primitives._text_em(url) / budget_em)
        self.assertGreater(expected, 1)
        self.assertEqual(
            primitives._wrapped_lines(url, PACK_CELL_W, 18.0), expected)

    def test_multi_word_short_text_unchanged(self):
        # Ordinary word-wrap behaviour is preserved: short multi-word text is
        # one line, explicit breaks still count, and a narrow box wraps words.
        self.assertEqual(primitives._wrapped_lines("Win rate", 3000000, 18.0), 1)
        self.assertEqual(primitives._wrapped_lines("a\nb", 3000000, 18.0), 2)
        self.assertGreater(
            primitives._wrapped_lines(
                "several plain words that share one narrow box", 1500000, 18.0),
            1)


class GlyphWidthTest(unittest.TestCase):
    """D-407: _text_em sums per-character em advances by glyph class."""

    def test_wide_glyphs_wider_than_narrow(self):
        self.assertGreater(primitives._text_em("MW"), primitives._text_em("il"))

    def test_digits_wider_than_default(self):
        self.assertGreater(primitives._text_em("88"), primitives._text_em("xx"))

    def test_exact_table_values(self):
        self.assertEqual(primitives.GLYPH_EM, {
            "digit": 0.60,
            "upper": 0.72,
            "wide": 0.85,
            "default": 0.52,
            "space": 0.33,
        })
        # "$8.4M" = default + digit + default + digit + wide.
        self.assertAlmostEqual(primitives._text_em("$8.4M"),
                               0.52 + 0.60 + 0.52 + 0.60 + 0.85)
        # M and W match upper too — wide wins; @ is wide; space is space.
        self.assertAlmostEqual(primitives._text_em("M"), 0.85)
        self.assertAlmostEqual(primitives._text_em("W"), 0.85)
        self.assertAlmostEqual(primitives._text_em("@"), 0.85)
        self.assertAlmostEqual(primitives._text_em("A B"), 0.72 + 0.33 + 0.72)


class StatNeverWrapsTest(unittest.TestCase):
    """D-408: a stat number never wraps. On the exact incident tokens the
    planner steps the ladder (display -> title -> h1) until every value is
    one estimated line in its cell, so the planned rects can no longer
    under-provision the row."""

    def setUp(self):
        self.els = plan_stat_row(PACK_STATS, PACK_TOKENS, PACK_W, PACK_H)
        self.numbers = [e for e in self.els if e["role"] == "stat-number"]
        self.labels = [e for e in self.els if e["role"] == "stat-label"]

    def test_every_number_is_one_line_at_a_ladder_step(self):
        self.assertEqual(len(self.numbers), 4)
        for num in self.numbers:
            self.assertIn(num["font_pt"], (96.0, 60.0, 40.0))
            self.assertEqual(
                primitives._wrapped_lines(
                    num["text"], num["width"], num["font_pt"]),
                1)

    def test_number_box_plus_baseline_clears_label(self):
        baseline = PACK_TOKENS["grid"]["baseline"]
        for num, lab in zip(self.numbers, self.labels):
            self.assertLessEqual(
                num["top"] + num["height"] + baseline, lab["top"])
        # And the box is sized for the CHOSEN step, not display.
        for num in self.numbers:
            self.assertEqual(
                num["height"],
                round(num["font_pt"] * primitives.EMU_PER_PT
                      * primitives.LINE_HEIGHT))

    def test_stepped_row_marks_font_stepped(self):
        # "$8.4M" cannot fit its cell at display 96pt, so the whole row steps
        # down and every number element owns up to it.
        for num in self.numbers:
            self.assertLess(num["font_pt"], 96.0)
            self.assertTrue(num.get("font_stepped"))

    def test_unstepped_row_carries_no_font_stepped(self):
        els = plan_stat_row([{"value": "56", "label": "Days"}],
                            PACK_TOKENS, PACK_W, PACK_H)
        num = next(e for e in els if e["role"] == "stat-number")
        self.assertEqual(num["font_pt"], 96.0)
        self.assertNotIn("font_stepped", num)

    def test_too_wide_value_raises_naming_it(self):
        long_token = "123456789012345678901234567890"  # 30 chars, no spaces
        stats = PACK_STATS[:3] + [{"value": long_token, "label": "Huge"}]
        with self.assertRaises(ShapeError) as cm:
            plan_stat_row(stats, PACK_TOKENS, PACK_W, PACK_H)
        self.assertIn(long_token, str(cm.exception))
        self.assertIn("cannot fit its cell", str(cm.exception))


# --- T-801 (REQ-204/D-409): percent placement + full-bleed -------------------


class SubrectPercentTest(unittest.TestCase):
    """_subrect: {x, y} percent placements resolve fractionally against the
    band — EXACT EMU, no gutter/baseline insets (D-409: the author owns the
    geometry). Mirrors render._place_region's maths."""

    BASE = (457200, 1600200, 8229600, 4525963)
    GRID = TOKENS["grid"]  # gutter/baseline nonzero — insets would show

    def _sub(self, **axes):
        placement = {"cols": None, "rows": None, "x": None, "y": None}
        placement.update(axes)
        return primitives._subrect(self.BASE, placement, self.GRID)

    def test_x_only_exact_full_band_vertically(self):
        # left = bl + round(0.2*bw) = 457200 + 1645920; width = round(0.5*bw).
        self.assertEqual(
            self._sub(x=(0.20, 0.70)),
            (2103120, 1600200, 4114800, 4525963),
        )

    def test_y_only_exact_full_band_horizontally(self):
        # top = bt + round(0.1*bh) = 1600200 + 452596;
        # height = round(0.25*bh) = 1131491.
        self.assertEqual(
            self._sub(y=(0.10, 0.35)),
            (457200, 2052796, 8229600, 1131491),
        )

    def test_both_axes_exact(self):
        self.assertEqual(
            self._sub(x=(0.20, 0.70), y=(0.10, 0.35)),
            (2103120, 2052796, 4114800, 1131491),
        )

    def test_grid_placement_keeps_insets(self):
        # Existing behaviour pin: a cols placement still gets the breathing
        # inset (gutter/2 horizontally, baseline vertically).
        pad_x = self.GRID["gutter"] // 2
        pad_y = self.GRID["baseline"]
        left, top, w, h = self._sub(cols=(1, 6))
        self.assertEqual(left, 457200 + pad_x)
        self.assertEqual(top, 1600200 + pad_y)
        self.assertEqual(w, 6 * 8229600 // 12 - 2 * pad_x)
        self.assertEqual(h, 4525963 - 2 * pad_y)


class FreeformPercentTest(unittest.TestCase):
    """plan_freeform with percent placements: dot geometry lands at the exact
    band fractions — the dumbbell acceptance maths at the planner level."""

    def test_dot_lands_at_exact_fraction(self):
        mx = TOKENS["grid"]["margin_x"]
        band_w = SLIDE_W - 2 * mx
        els = plan_freeform([
            {"kind": "dot", "colour": "accent",
             "placement": {"cols": None, "rows": None,
                           "x": (0.63, 0.67), "y": (0.18, 0.26)}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        dot = els[0]
        self.assertEqual(dot["role"], "freeform-dot")
        self.assertEqual(dot["left"], mx + round(0.63 * band_w))
        self.assertEqual(dot["width"], round(0.04 * band_w))

    def test_single_axis_percent_spans_band_on_the_other(self):
        mx = TOKENS["grid"]["margin_x"]
        mt = TOKENS["grid"]["margin_top"]
        els = plan_freeform([
            {"kind": "box", "fill": "paper",
             "placement": {"cols": None, "rows": None,
                           "x": (0.25, 0.75), "y": None}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        box = els[0]
        self.assertEqual(box["top"], mt)
        self.assertEqual(box["height"], SLIDE_H - mt - TOKENS["grid"]["margin_bottom"])

    def test_dumbbell_row_plans_lint_clean(self):
        # One category row of the acceptance case: caption, two dots, a rail.
        els = plan_freeform([
            {"kind": "text", "scale": "caption", "colour": "ink",
             "text": "Alpha",
             "placement": {"cols": None, "rows": None,
                           "x": (0.02, 0.16), "y": (0.18, 0.26)}},
            {"kind": "dot", "colour": "muted",
             "placement": {"cols": None, "rows": None,
                           "x": (0.18, 0.22), "y": (0.18, 0.26)}},
            {"kind": "line", "colour": "muted",
             "placement": {"cols": None, "rows": None,
                           "x": (0.22, 0.63), "y": (0.18, 0.26)}},
            {"kind": "dot", "colour": "accent",
             "placement": {"cols": None, "rows": None,
                           "x": (0.63, 0.67), "y": (0.18, 0.26)}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))


class FreeformFullBleedTest(unittest.TestCase):
    """plan_freeform full-bleed: the box spans the FULL SLIDE (0,0,w,h),
    carries full_bleed + container, and the whole gate still clears."""

    FULL_BLEED = {"kind": "box", "fill": "accent", "full_bleed": True,
                  "placement": None}

    def test_box_spans_the_slide(self):
        els = plan_freeform([dict(self.FULL_BLEED)], TOKENS, SLIDE_W, SLIDE_H)
        box = els[0]
        self.assertEqual(
            (box["left"], box["top"], box["width"], box["height"]),
            (0, 0, SLIDE_W, SLIDE_H),
        )
        self.assertTrue(box["full_bleed"])
        self.assertTrue(box["container"])
        # A wash meets the slide edge squarely, whatever the corner token.
        self.assertEqual(box["shape"], "rect")

    def test_full_bleed_with_contained_text_passes_the_gate(self):
        # Container semantics: elements inside the wash overlap it legally,
        # and the margins rule carves the wash out (REQ-204).
        els = plan_freeform([
            dict(self.FULL_BLEED),
            {"kind": "text", "scale": "h1", "colour": "paper",
             "text": "Edge to edge",
             "placement": {"cols": (2, 11), "rows": (5, 8),
                           "x": None, "y": None}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))


@unittest.skipUnless(
    os.environ.get("RASTER_MEASURE"),
    "opt-in: set RASTER_MEASURE=1 (needs a raster backend + PIL)")
class RasterMeasureTest(unittest.TestCase):
    """The reproducible measurement backing the estimator bound (REQ-201):
    render the live-incident stat row end to end under brand fidelity,
    rasterise slide 1, and print its ink row bands so a human can verify the
    number no longer overprints its label. Opt-in because it needs a
    rasteriser backend (LibreOffice/PowerPoint/Keynote) and PIL."""

    SPEC = (
        "---\n"
        "deck: estimator raster measure\n"
        "audience: engineering leadership\n"
        "register: presented live\n"
        "---\n"
        "\n"
        "## Slide 1\n"
        "layout: composed\n"
        "Title: What moved this quarter\n"
        "Block: stat-row\n"
        "$8.4M | Revenue / +12% QoQ\n"
        "412 | Enterprise customers\n"
        "98.2% | Retention / trailing 12 months\n"
        "$1.9M | Net new ARR\n"
    )
    BRAND = {
        "fidelity": "brand",
        "fonts": {"heading": "Calibri", "body": "Calibri"},
        "colours": {
            "ink": "#1A1A1A",
            "paper": "#FFFFFF",
            "accent": "#0B5FFF",
            "muted": "#6B7280",
        },
    }

    def test_stat_row_renders_rasterises_and_prints_ink_bands(self):
        from PIL import Image  # noqa: PLC0415 — opt-in dependency
        import raster  # noqa: PLC0415 — scripts dir is on sys.path

        tmp = tempfile.mkdtemp(prefix="slides-raster-measure-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        spec_path = os.path.join(tmp, "deck.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(self.SPEC)
        brand_path = os.path.join(tmp, "brand.json")
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(self.BRAND, fh)
        out_path = os.path.join(tmp, "out.pptx")
        render_py = os.path.join(os.path.abspath(_SCRIPTS_DIR), "render.py")
        proc = subprocess.run(
            [sys.executable, render_py, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"render failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}")

        pngs = raster.rasterise(out_path, os.path.join(tmp, "png"))
        self.assertGreaterEqual(len(pngs), 1)

        # Ink row bands: contiguous pixel rows containing any non-paper ink.
        im = Image.open(pngs[0]).convert("L")
        w, h = im.size
        px = im.load()
        bands, start = [], None
        for y in range(h):
            has_ink = any(px[x, y] < 200 for x in range(w))
            if has_ink and start is None:
                start = y
            elif not has_ink and start is not None:
                bands.append((start, y - 1))
                start = None
        if start is not None:
            bands.append((start, h - 1))
        print(f"\nRASTER_MEASURE {os.path.basename(pngs[0])} size={w}x{h} "
              f"ink row bands (px): {bands}")


if __name__ == "__main__":
    unittest.main()
