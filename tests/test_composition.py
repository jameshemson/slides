"""Tests for source/skills/build-deck/scripts/composition.py"""
import sys
import os
import unittest

# ---------------------------------------------------------------------------
# Path setup — add the scripts directory so `import composition` works.
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "source",
        "skills",
        "build-deck",
        "scripts",
    )
)
sys.path.insert(0, _SCRIPTS_DIR)

import composition
from composition import contrast_ratio, RULES

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TOKENS = {
    "grid": {
        "margin_x": 457200,
        "margin_top": 274638,
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

SLIDE_W = 9144000
SLIDE_H = 6858000


def good_elements():
    """
    A clean 3-stat row.
    Numbers at font_pt=40, colour=#4F81BD (accent).
    Labels at font_pt=12, colour=#000000 (ink).
    Positioned well within the content band, terse values and labels.
    """
    # Content band: margin_top=274638 .. slide_h-margin_bottom=6126163
    # We put the row block near the top of the band, well under half the band.
    col_w = 2400000
    num_h = 457200   # ~0.5 in
    lab_h = 274638   # ~0.3 in
    gap   = 91211    # baseline gap between number and label

    stats = [
        ("56",        "Days"),
        ("4%",        "Win rate"),
        ("120",       "New deals"),
    ]

    elements = []
    for i, (val, lbl) in enumerate(stats):
        left = TOKENS["grid"]["margin_x"] + i * (col_w + TOKENS["grid"]["gutter"])
        top_num = TOKENS["grid"]["margin_top"] + 200000   # a little below top margin
        top_lab = top_num + num_h + gap

        elements.append({
            "role": "stat-number",
            "text": val,
            "left": left,
            "top": top_num,
            "width": col_w,
            "height": num_h,
            "font_pt": 40.0,
            "colour": "#4F81BD",
        })
        elements.append({
            "role": "stat-label",
            "text": lbl,
            "left": left,
            "top": top_lab,
            "width": col_w,
            "height": lab_h,
            "font_pt": 12.0,
            "colour": "#000000",
        })
    return elements


def rule_by_id(rid):
    return next(r for r in RULES if r["id"] == rid)


# ---------------------------------------------------------------------------
# Registry shape tests
# ---------------------------------------------------------------------------

EXPECTED_IDS = [
    "hierarchy-ratio",
    "stat-count",
    "contrast",
    "value-terseness",
    "label-terseness",
    "breathing-room",
    "one-accent",
    "decoration-present",
    "emphasis-colour-only",
    # card-grid
    "card-count",
    "card-label-terseness",
    "card-one-accent",
    # comparison
    "comparison-resolves",
    "comparison-header-terseness",
    # process
    "process-count",
    "process-label-terseness",
    # timeline
    "timeline-count",
    "timeline-emphasis",
    "timeline-terseness",
    # freeform
    "freeform-one-accent",
    # tree
    "tree-count",
    "tree-label-terseness",
    "tree-one-accent",
    # icon-list
    "iconlist-count",
    # cycle
    "cycle-count",
    "cycle-label-terseness",
    # matrix
    "matrix-label-terseness",
    "matrix-one-accent",
]

REQUIRED_KEYS = {"id", "tier", "severity", "applies_to", "message", "source", "check"}


class TestRegistryShape(unittest.TestCase):

    def test_registry_shape(self):
        self.assertEqual(len(RULES), len(EXPECTED_IDS),
                         f"Expected exactly {len(EXPECTED_IDS)} rules")
        ids_seen = [r["id"] for r in RULES]
        self.assertEqual(len(ids_seen), len(set(ids_seen)), "Rule ids must be unique")
        self.assertEqual(sorted(ids_seen), sorted(EXPECTED_IDS),
                         "Rule ids must match the 9 expected ids exactly")
        for rule in RULES:
            with self.subTest(rule_id=rule.get("id", "<missing>")):
                self.assertEqual(set(rule.keys()), REQUIRED_KEYS)
                self.assertTrue(callable(rule["check"]))
                self.assertIn(rule["tier"], {"quality", "slop"})
                self.assertEqual(rule["severity"], "advisory")
                self.assertTrue(rule["source"], "source must be truthy")


# ---------------------------------------------------------------------------
# Per-rule PASS and TRIGGER tests
# ---------------------------------------------------------------------------

class TestHierarchyRatio(unittest.TestCase):

    def test_pass(self):
        # good_elements: 40/12 = 3.33, within [2.5, 6]
        rule = rule_by_id("hierarchy-ratio")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        # label font_pt=30 -> ratio 40/30 = 1.33, outside [2.5, 6]
        elems = good_elements()
        for e in elems:
            if e["role"] == "stat-label":
                e["font_pt"] = 30.0
        rule = rule_by_id("hierarchy-ratio")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


class TestStatCount(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("stat-count")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        # 6 stat-numbers
        base = good_elements()
        extra = []
        for i in range(3):
            extra.append({
                "role": "stat-number",
                "text": "9",
                "left": 0,
                "top": 300000,
                "width": 500000,
                "height": 200000,
                "font_pt": 40.0,
                "colour": "#4F81BD",
            })
        rule = rule_by_id("stat-count")
        self.assertFalse(rule["check"](base + extra, TOKENS, SLIDE_W, SLIDE_H))


class TestContrast(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("contrast")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        # number colour #DDDDDD on white paper — low contrast
        elems = good_elements()
        for e in elems:
            if e["role"] == "stat-number":
                e["colour"] = "#DDDDDD"
        rule = rule_by_id("contrast")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


class TestValueTerseness(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("value-terseness")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        elems = good_elements()
        for e in elems:
            if e["role"] == "stat-number":
                e["text"] = "1,234,567"
                break
        rule = rule_by_id("value-terseness")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


class TestLabelTerseness(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("label-terseness")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        elems = good_elements()
        for e in elems:
            if e["role"] == "stat-label":
                e["text"] = "this is a long label"
                break
        rule = rule_by_id("label-terseness")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


class TestBreathingRoom(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("breathing-room")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        # An element that fills the whole band
        band_top = TOKENS["grid"]["margin_top"]
        band_bottom = SLIDE_H - TOKENS["grid"]["margin_bottom"]
        band_h = band_bottom - band_top
        huge_elem = {
            "role": "stat-number",
            "text": "99",
            "left": 500000,
            "top": band_top,
            "width": 2000000,
            "height": band_h,   # fills the entire band
            "font_pt": 40.0,
            "colour": "#4F81BD",
        }
        rule = rule_by_id("breathing-room")
        self.assertFalse(rule["check"]([huge_elem], TOKENS, SLIDE_W, SLIDE_H))


class TestOneAccent(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("one-accent")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        elems = good_elements()
        # Set a number to a non-accent colour
        for e in elems:
            if e["role"] == "stat-number":
                e["colour"] = "#00FF00"
                break
        rule = rule_by_id("one-accent")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


class TestDecorationPresent(unittest.TestCase):

    def test_pass(self):
        rule = rule_by_id("decoration-present")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        elems = good_elements()
        elems.append({
            "role": "blob",
            "text": "",
            "left": 100000,
            "top": 100000,
            "width": 200000,
            "height": 200000,
            "font_pt": 0.0,
            "colour": "#FF0000",
        })
        rule = rule_by_id("decoration-present")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


class TestEmphasisColourOnly(unittest.TestCase):

    def test_pass(self):
        # good_elements: number font_pt=40 > label font_pt=12
        rule = rule_by_id("emphasis-colour-only")
        self.assertTrue(rule["check"](good_elements(), TOKENS, SLIDE_W, SLIDE_H))

    def test_trigger(self):
        # number and label same font size — emphasis by colour only
        elems = good_elements()
        for e in elems:
            if e["role"] == "stat-number":
                e["font_pt"] = 12.0
        rule = rule_by_id("emphasis-colour-only")
        self.assertFalse(rule["check"](elems, TOKENS, SLIDE_W, SLIDE_H))


# ---------------------------------------------------------------------------
# Contrast ratio helper tests
# ---------------------------------------------------------------------------

class TestContrastRatio(unittest.TestCase):

    def test_black_on_white(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#FFFFFF"), 21, places=0)

    def test_accent_on_white(self):
        self.assertGreaterEqual(contrast_ratio("#4F81BD", "#FFFFFF"), 3.0)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Integration: lint.review over the registry + good-by-construction.
# (composition rules are advisory; lint.review is the runner — never raises.)
# ---------------------------------------------------------------------------
import lint  # noqa: E402
from primitives import (  # noqa: E402
    plan_stat_row, plan_card_grid, plan_comparison, plan_process, plan_timeline,
    plan_freeform, plan_tree, plan_icon_list, plan_cycle, plan_matrix,
)

_INTEG_STATS = [
    {"value": "56", "label": "Days"},
    {"value": "4%", "label": "Win rate"},
    {"value": "120", "label": "Deals"},
]


class TestReviewIntegration(unittest.TestCase):
    def test_default_stat_row_is_clean(self):
        # Good by construction: the default stat_row trips no advisory rule.
        els = plan_stat_row(_INTEG_STATS, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(lint.review(els, TOKENS, SLIDE_W, SLIDE_H), [])

    def test_applies_to_gating_empty(self):
        # No stat-row elements -> no stat-row rules run -> no findings.
        self.assertEqual(lint.review([], TOKENS, SLIDE_W, SLIDE_H), [])

    def test_review_never_raises_on_malformed(self):
        for bad in ([{"role": "stat-number"}], [{}], ["notadict"]):
            try:
                out = lint.review(bad, TOKENS, SLIDE_W, SLIDE_H)
            except Exception as exc:  # pragma: no cover
                self.fail(f"review raised on {bad!r}: {exc}")
            self.assertIsInstance(out, list)

    def test_weak_row_flags_advisories(self):
        weak = plan_stat_row(
            [{"value": str(i), "label": "this is a long label"} for i in range(6)],
            TOKENS, SLIDE_W, SLIDE_H,
        )
        findings = lint.review(weak, TOKENS, SLIDE_W, SLIDE_H)
        ids = {f["rule_id"] for f in findings}
        self.assertIn("stat-count", ids)
        self.assertIn("label-terseness", ids)
        self.assertTrue(findings and all(f["severity"] == "advisory" for f in findings))


class TestNewPrimitiveReview(unittest.TestCase):
    """Every new primitive is good by construction, and its advisory rules
    fire on a weak input."""

    def _ids(self, els):
        return {f["rule_id"] for f in lint.review(els, TOKENS, SLIDE_W, SLIDE_H)}

    def test_card_grid_clean(self):
        els = plan_card_grid(
            [{"label": "Size"}, {"label": "Knowledge"},
             {"label": "Aim", "emphasis": True}], TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_card_grid_two_accents_flag(self):
        els = plan_card_grid(
            [{"label": "A", "emphasis": True}, {"label": "B", "emphasis": True},
             {"label": "C"}], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("card-one-accent", self._ids(els))

    def test_comparison_clean(self):
        els = plan_comparison(
            [{"header": "Before", "body": "slow"},
             {"header": "After", "body": "fast", "emphasis": True}],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_comparison_no_verdict_flags(self):
        els = plan_comparison(
            [{"header": "A", "body": "x"}, {"header": "B", "body": "y"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("comparison-resolves", self._ids(els))

    def test_process_clean(self):
        els = plan_process(
            [{"label": "Plan"}, {"label": "Create"}, {"label": "Deliver"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_process_wordy_label_flags(self):
        els = plan_process(
            [{"label": "Plan the whole thing out"}, {"label": "Do"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("process-label-terseness", self._ids(els))

    def test_timeline_clean(self):
        els = plan_timeline(
            [{"date": "26", "event": "Kick"},
             {"date": "27", "event": "Ship", "emphasis": True},
             {"date": "28", "event": "Scale"}], TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_timeline_no_turn_flags(self):
        els = plan_timeline(
            [{"date": "26", "event": "Kick"}, {"date": "27", "event": "Ship"}],
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("timeline-emphasis", self._ids(els))

    def test_tree_clean(self):
        root = {"label": "CEO", "emphasis": False, "icon": None, "children": [
            {"label": "Eng", "emphasis": True, "icon": None, "children": []},
            {"label": "Sales", "emphasis": False, "icon": None, "children": []},
        ]}
        els = plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_tree_two_accents_flag(self):
        root = {"label": "CEO", "emphasis": True, "icon": None, "children": [
            {"label": "Eng", "emphasis": True, "icon": None, "children": []},
            {"label": "Ops", "emphasis": False, "icon": None, "children": []},
        ]}
        self.assertIn("tree-one-accent", self._ids(plan_tree(root, TOKENS, SLIDE_W, SLIDE_H)))

    def test_cycle_clean(self):
        els = plan_cycle([{"label": "Plan"}, {"label": "Build"}, {"label": "Learn"}],
                         TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_matrix_clean(self):
        spec = {"quadrants": [{"label": "QW"}, {"label": "BB", "emphasis": True},
                              {"label": "DP"}, {"label": "FI"}]}
        self.assertEqual(self._ids(plan_matrix(spec, TOKENS, SLIDE_W, SLIDE_H)), set())

    def test_icon_list_clean(self):
        rows = [{"icon": "growth", "text": "Up"}, {"icon": "team", "text": "Bigger"},
                {"icon": "fast", "text": "Faster"}]
        els = plan_icon_list(rows, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_multiblock_rules_isolated(self):
        # A stat-row stacked with a process: stat rules see only stat elements,
        # process rules only process elements -> no cross-family false flags.
        stat = plan_stat_row(_INTEG_STATS, TOKENS, SLIDE_W, SLIDE_H)
        proc = plan_process(
            [{"label": "Plan"}, {"label": "Ship"}], TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(stat + proc), set())

    def test_freeform_restrained_is_clean(self):
        # One accent mark among several -> grey-push respected, no advisory.
        els = plan_freeform([
            {"kind": "box", "fill": "paper", "stroke": "ink",
             "placement": {"cols": (1, 6), "rows": (1, 8)}},
            {"kind": "text", "scale": "h1", "colour": "ink", "text": "A",
             "placement": {"cols": (1, 6), "rows": (1, 3)}},
            {"kind": "box", "fill": "accent",
             "placement": {"cols": (7, 12), "rows": (1, 8)}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(self._ids(els), set())

    def test_freeform_rainbow_flags(self):
        # Three accent marks -> grey-push guardrail warns (advisory).
        els = plan_freeform([
            {"kind": "box", "fill": "accent",
             "placement": {"cols": (1, 4), "rows": (1, 6)}},
            {"kind": "box", "fill": "accent",
             "placement": {"cols": (5, 8), "rows": (1, 6)}},
            {"kind": "text", "scale": "h1", "colour": "accent", "text": "C",
             "placement": {"cols": (9, 12), "rows": (1, 6)}},
        ], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("freeform-one-accent", self._ids(els))
