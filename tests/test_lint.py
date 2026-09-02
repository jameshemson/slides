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
        # Build one more than the cap for the count rule.
        # We only need check_count to fire; we don't require all other rules to pass.
        thirteen = []
        for i in range(lint.ELEMENT_CAP + 1):
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


def container_box(left=457200, top=1600200, width=3000000, height=2000000,
                  fill="#4F81BD"):
    return {
        "role": "card-panel", "kind": "box", "container": True,
        "fill": fill, "left": left, "top": top, "width": width, "height": height,
    }


class TestShapeElements(unittest.TestCase):
    """Box/panel elements: fill is token-checked, size is skipped, and a
    container may hold its text without tripping the overlap rule."""

    def test_box_fill_is_token_checked(self):
        box = container_box(fill="#123456")  # not in colour_roles
        violations = lint.check_colours([box], TOKENS)
        self.assertTrue(violations)
        self.assertIn("[colour]", violations[0])
        self.assertIn("fill", violations[0])

    def test_box_valid_fill_passes(self):
        self.assertEqual(lint.check_colours([container_box()], TOKENS), [])

    def test_box_has_no_size_to_check(self):
        # A box carries no font_pt; check_sizes must not flag (or crash on) it.
        self.assertEqual(lint.check_sizes([container_box()], TOKENS), [])

    def test_stroke_is_token_checked(self):
        box = container_box()
        box["stroke"] = "#00FF00"  # off-token
        violations = lint.check_colours([box], TOKENS)
        self.assertTrue(any("stroke" in v for v in violations))

    def test_container_holds_text_no_overlap(self):
        box = container_box()
        text = {
            "role": "card-title", "text": "On brand",
            "left": 600000, "top": 1700000, "width": 2000000, "height": 400000,
            "font_pt": 18.0, "colour": "#FFFFFF",
        }
        # Text sits wholly inside the container box -> legal, no overlap flag.
        self.assertEqual(lint.check_no_overlap([box, text]), [])
        # And the whole gate passes.
        self.assertIsNone(lint.check([box, text], TOKENS, SLIDE_W, SLIDE_H))

    def test_text_spilling_out_of_container_flagged(self):
        box = container_box(width=1000000)
        text = {
            "role": "card-title", "text": "spills",
            "left": 600000, "top": 1700000, "width": 3000000, "height": 400000,
            "font_pt": 18.0, "colour": "#000000",
        }
        self.assertTrue(lint.check_no_overlap([box, text]))

    def test_non_container_overlap_still_flagged(self):
        # A plain box (no container flag) overlapping text is still a fault.
        box = container_box()
        box["container"] = False
        text = {
            "role": "card-title", "text": "over",
            "left": 600000, "top": 1700000, "width": 2000000, "height": 400000,
            "font_pt": 18.0, "colour": "#000000",
        }
        self.assertTrue(lint.check_no_overlap([box, text]))


# --- Table-aware lint (T-004, REQ-004, decision D-008) --------------------
#
# A native pptx table is ONE element (kind "table"), so its colours and sizes
# travel as vectors rather than one-per-pseudo-element: `fills`, `text_colours`,
# and `font_pts`. The hairline colour rides the existing scalar `stroke` key.
# check_colours / check_sizes must validate every entry of those vectors; the
# margins/overlap/count rules treat the table as the single rectangle it is.


def good_table(left=457200, top=1600200, width=3000000, height=1200000):
    """A fully on-brand table element: every fill/text colour a token, every
    font size on the type scale, stroke a token, inside the grid margins."""
    return {
        "role": "table-grid",
        "kind": "table",
        "text": "table: A | B",
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        # header ink, data paper, emphasis accent — all in colour_roles
        "fills": ["#000000", "#FFFFFF", "#4F81BD"],
        # paper-on-ink header, ink-on-paper body — all in colour_roles
        "text_colours": ["#FFFFFF", "#000000"],
        "font_pts": [18.0],          # body, on the type scale
        "stroke": "#C0504D",         # muted hairline, a token colour
    }


def stacked_with_table(n):
    """`n` clean, non-overlapping, within-margin elements; element 0 is a
    table. Used to prove a table counts as exactly ONE element for the cap."""
    els = []
    for i in range(n):
        top = 1600200 + i * 50000
        if i == 0:
            els.append(good_table(left=457200, top=top, width=500000, height=40000))
        else:
            els.append({
                "role": f"item-{i}",
                "text": str(i),
                "left": 457200,
                "top": top,
                "width": 500000,
                "height": 40000,
                "font_pt": 12.0,
                "colour": "#000000",
            })
    return els


class TestTableColours(unittest.TestCase):
    """check_colours must hold every entry of a table's fills / text_colours
    vectors to the token palette (D-008), and still trip on the scalar stroke."""

    def test_off_token_fill_flagged(self):
        # RED until T-009: check_colours ignores `fills` today.
        t = good_table()
        t["fills"] = ["#000000", "#ABCDEF", "#4F81BD"]  # #ABCDEF off-token
        violations = lint.check_colours([t], TOKENS)
        self.assertTrue(violations, "expected a [colour] violation for the off-token fill")
        self.assertTrue(any("[colour]" in v for v in violations))
        self.assertTrue(
            any("#ABCDEF" in v for v in violations),
            "the violation should name the off-token hex",
        )

    def test_off_token_text_colour_flagged(self):
        # RED until T-009: check_colours ignores `text_colours` today.
        t = good_table()
        t["text_colours"] = ["#FFFFFF", "#123456"]  # #123456 off-token
        violations = lint.check_colours([t], TOKENS)
        self.assertTrue(violations, "expected a [colour] violation for the off-token text colour")
        self.assertTrue(any("[colour]" in v for v in violations))
        self.assertTrue(
            any("#123456" in v for v in violations),
            "the violation should name the off-token hex",
        )

    def test_off_token_stroke_still_flagged(self):
        # Already green: `stroke` is a scalar key the existing rule checks.
        t = good_table()
        t["stroke"] = "#00FF00"  # off-token
        violations = lint.check_colours([t], TOKENS)
        self.assertTrue(any("stroke" in v and "[colour]" in v for v in violations))


class TestTableSizes(unittest.TestCase):
    def test_off_scale_font_pt_flagged(self):
        # RED until T-009: check_sizes ignores the `font_pts` vector today.
        t = good_table()
        t["font_pts"] = [18.0, 99.0]  # 99.0 not on the type scale
        violations = lint.check_sizes([t], TOKENS)
        self.assertTrue(violations, "expected a [size] violation for the off-scale font_pts entry")
        self.assertTrue(any("[size]" in v for v in violations))
        self.assertTrue(any("99" in v for v in violations))


class TestTableClean(unittest.TestCase):
    def test_clean_table_passes(self):
        # Already green now (vectors ignored); must STAY green after T-009.
        t = good_table()
        self.assertEqual(lint.check_colours([t], TOKENS), [])
        self.assertEqual(lint.check_sizes([t], TOKENS), [])
        self.assertEqual(
            lint.check_within_margins([t], TOKENS, SLIDE_W, SLIDE_H), []
        )
        self.assertIsNone(lint.check([t], TOKENS, SLIDE_W, SLIDE_H))


class TestTableMargins(unittest.TestCase):
    def test_out_of_margin_names_text_key(self):
        # Already green: the table carries a `text` key, so the margins message
        # formats without a KeyError (lint.py line ~115 reads el['text']).
        t = good_table()
        t["left"] = 0  # left of margin_x
        violations = lint.check_within_margins([t], TOKENS, SLIDE_W, SLIDE_H)
        self.assertTrue(violations)
        self.assertTrue(any("[margins]" in v for v in violations))
        self.assertTrue(
            any(t["text"] in v for v in violations),
            "the margins message must include the element's text key",
        )


class TestTableCount(unittest.TestCase):
    """A table is a single native GraphicFrame — one element for the cap (D-001)."""

    def test_table_at_cap_passes(self):
        # Already green: ELEMENT_CAP elements, one of them a table, is legal.
        els = stacked_with_table(lint.ELEMENT_CAP)
        self.assertEqual(len(els), lint.ELEMENT_CAP)
        self.assertEqual(lint.check_count(els), [])
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

    def test_table_over_cap_fails(self):
        els = stacked_with_table(lint.ELEMENT_CAP + 1)
        violations = lint.check_count(els)
        self.assertTrue(violations)
        self.assertIn("[count]", violations[0])
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[count]", str(ctx.exception))


# --- Chart-element lint regression pins (T-005, REQ-006, decision D-006) --
#
# `Block: chart` on a composed slide is planned by render.py as ONE element of
# kind "chart" — `{"role": "chart-figure", "kind": "chart", "text": "chart:
# <type>", left/top/width/height}` — carrying only role/text/bbox, no colour
# or font keys (chart internals derive from brand["colours"] by construction,
# on both the image and native backends). These are GREEN-FROM-START
# regression pins: lint.py needs NO change for this kind — the bbox rules
# (margins/overlap/count) are kind-generic, and check_colours/check_sizes
# naturally see no colour/font keys on a chart element to flag.


def good_chart(left=457200, top=1600200, width=3000000, height=300000):
    """A clean composed chart element: role/text/bbox only, no colour/font
    keys, positioned to sit inside margins without overlapping good_elements()."""
    return {
        "role": "chart-figure",
        "kind": "chart",
        "text": "chart: column",
        "left": left,
        "top": top,
        "width": width,
        "height": height,
    }


def stacked_with_chart(n):
    """`n` clean, non-overlapping, within-margin elements; element 0 is a
    chart. Used to prove a chart counts as exactly ONE element for the cap."""
    els = []
    for i in range(n):
        top = 1600200 + i * 50000
        if i == 0:
            els.append(good_chart(left=457200, top=top, width=500000, height=40000))
        else:
            els.append({
                "role": f"item-{i}",
                "text": str(i),
                "left": 457200,
                "top": top,
                "width": 500000,
                "height": 40000,
                "font_pt": 12.0,
                "colour": "#000000",
            })
    return els


class TestChartElementKind(unittest.TestCase):
    """Regression pins for the composed `Block: chart` element (kind "chart"),
    planned by render.py per D-006. These are GREEN-FROM-START pins: lint.py
    itself needs no change to handle this element shape."""

    def test_clean_chart_passes_alongside_other_elements(self):
        """Regression pin: a clean chart element (inside margins, not
        overlapping) alongside other elements produces no violations from
        lint.check or any individual rule helper."""
        els = good_elements() + [good_chart()]
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))
        self.assertEqual(lint.check_colours(els, TOKENS), [])
        self.assertEqual(lint.check_sizes(els, TOKENS), [])
        self.assertEqual(lint.check_within_margins(els, TOKENS, SLIDE_W, SLIDE_H), [])
        self.assertEqual(lint.check_no_overlap(els), [])
        self.assertEqual(lint.check_count(els), [])

    def test_out_of_margin_names_text_key(self):
        """Regression pin: a chart placed outside the grid margins produces a
        [margins] violation whose message includes the element's `text` key
        (no KeyError — lint.py's margins message reads el['text'])."""
        chart = good_chart(left=0)  # left of margin_x
        violations = lint.check_within_margins([chart], TOKENS, SLIDE_W, SLIDE_H)
        self.assertTrue(violations)
        self.assertTrue(any("[margins]" in v for v in violations))
        self.assertTrue(
            any(chart["text"] in v for v in violations),
            "the margins message must include the element's text key",
        )
        with self.assertRaises(lint.LintError) as ctx:
            lint.check([chart], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[margins]", str(ctx.exception))

    def test_overlap_with_filled_box_flagged(self):
        """Regression pin: a chart overlapping a filled (non-container) box
        element produces an [overlap] violation — a chart is a filled
        element, not a 1-D line kind (connector/edge), so it is not exempt
        from the overlap rule."""
        box = container_box()
        box["container"] = False
        chart = good_chart(
            left=box["left"], top=box["top"], width=box["width"], height=box["height"]
        )
        violations = lint.check_no_overlap([box, chart])
        self.assertTrue(violations)
        self.assertTrue(any("[overlap]" in v for v in violations))
        with self.assertRaises(lint.LintError) as ctx:
            lint.check([box, chart], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[overlap]", str(ctx.exception))

    def test_chart_at_cap_passes(self):
        """Regression pin: a chart counts as exactly ONE element toward
        ELEMENT_CAP — ELEMENT_CAP elements including one chart is legal."""
        els = stacked_with_chart(lint.ELEMENT_CAP)
        self.assertEqual(len(els), lint.ELEMENT_CAP)
        self.assertEqual(lint.check_count(els), [])
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

    def test_chart_over_cap_fails(self):
        """Regression pin: ELEMENT_CAP + 1 elements including one chart still
        trips the [count] rule — the chart earns no exemption from the cap."""
        els = stacked_with_chart(lint.ELEMENT_CAP + 1)
        violations = lint.check_count(els)
        self.assertTrue(violations)
        self.assertIn("[count]", violations[0])
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[count]", str(ctx.exception))

    def test_no_colour_or_size_violations(self):
        """Regression pin: check_colours/check_sizes produce NO violations for
        a chart element — it carries no `colour`/`fill`/`stroke` or `font_pt`
        keys, since chart internals derive from the brand by construction."""
        chart = good_chart()
        self.assertEqual(lint.check_colours([chart], TOKENS), [])
        self.assertEqual(lint.check_sizes([chart], TOKENS), [])


# --- Ghost type + hierarchy lint (T-201, the fixed-role planners) ----------
#
# A section slide's ghost numeral is display type at display × GHOST_MULTIPLE,
# deliberately underlapping the title. check_sizes must admit exactly that one
# size for an element marked `ghost` (and nothing else off-scale), and
# check_no_overlap must skip any pair containing a ghost. check_hierarchy is
# the new advisory-turned-hard rule for the roles: rank-2 supporting text must
# sit strictly below rank-1 lead text on the type scale.


def ghost_element(font_pt):
    """A ghost numeral inside margins, muted, with the given size."""
    return {
        "role": "sectionslide-ghost",
        "text": "03",
        "ghost": True,
        "left": 4000000,
        "top": 1600200,
        "width": 2000000,
        "height": 2000000,
        "font_pt": font_pt,
        "colour": "#C0504D",
    }


class TestGhostSizeRule(unittest.TestCase):
    """A `ghost` element is allowed exactly display × GHOST_MULTIPLE."""

    def test_ghost_accepted_at_exact_multiple(self):
        el = ghost_element(TOKENS["type_scale"]["display"] * 3.0)  # 120.0
        self.assertEqual(lint.check_sizes([el], TOKENS), [])
        self.assertIsNone(lint.check([el], TOKENS, SLIDE_W, SLIDE_H))

    def test_ghost_rejected_off_multiple(self):
        el = ghost_element(TOKENS["type_scale"]["display"] * 2.5)  # 100.0
        violations = lint.check_sizes([el], TOKENS)
        self.assertTrue(violations)
        self.assertIn("[size]", violations[0])
        with self.assertRaises(lint.LintError) as ctx:
            lint.check([el], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[size]", str(ctx.exception))


class TestGhostOverlapRule(unittest.TestCase):
    """check_no_overlap skips any pair containing a ghost element."""

    def _pair(self, ghost):
        a = {
            "role": "sectionslide-title", "text": "Momentum",
            "left": 457200, "top": 1600200, "width": 3000000, "height": 900000,
            "font_pt": 28.0, "colour": "#000000",
        }
        b = {
            "role": "sectionslide-ghost" if ghost else "stat-number",
            "text": "03",
            "left": 457200, "top": 1600200, "width": 3000000, "height": 900000,
            "font_pt": 40.0, "colour": "#C0504D",
        }
        if ghost:
            b["ghost"] = True
        return [a, b]

    def test_overlap_skipped_when_one_is_ghost(self):
        self.assertEqual(lint.check_no_overlap(self._pair(ghost=True)), [])

    def test_overlap_flagged_when_neither_is_ghost(self):
        violations = lint.check_no_overlap(self._pair(ghost=False))
        self.assertTrue(violations)
        self.assertIn("[overlap]", violations[0])


class TestHierarchyRule(unittest.TestCase):
    """[hierarchy]: rank-2 text must sit strictly below rank-1 text in size."""

    def _ranked(self, rank, font_pt, top=1600200):
        return {
            "role": f"bodyslide-rank{rank}", "text": "t",
            "left": 457200, "top": top, "width": 2000000, "height": 200000,
            "font_pt": font_pt, "colour": "#000000", "rank": rank,
        }

    def test_supporting_below_lead_passes(self):
        els = [self._ranked(1, 40.0), self._ranked(2, 24.0, top=2000000)]
        self.assertEqual(lint.check_hierarchy(els), [])

    def test_supporting_reaching_lead_fails_naming_both_sizes(self):
        els = [self._ranked(1, 40.0), self._ranked(2, 40.0, top=2000000)]
        violations = lint.check_hierarchy(els)
        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0],
            "[hierarchy] rank-2 text at 40.0pt reaches rank-1 text at 40.0pt "
            "— supporting text must sit below the lead",
        )

    def test_unranked_elements_never_trigger(self):
        els = good_elements()  # no element carries a rank
        self.assertEqual(lint.check_hierarchy(els), [])
        # Even equal sizes are fine when nothing is ranked.
        unranked = [
            {"role": "a", "text": "x", "left": 457200, "top": 1600200,
             "width": 1000000, "height": 200000, "font_pt": 40.0,
             "colour": "#000000"},
            {"role": "b", "text": "y", "left": 457200, "top": 2000000,
             "width": 1000000, "height": 200000, "font_pt": 40.0,
             "colour": "#000000"},
        ]
        self.assertEqual(lint.check_hierarchy(unranked), [])

    def test_wired_into_check(self):
        # Otherwise-clean elements (on token, on scale, inside margins, no
        # overlap) that break only the hierarchy must still fail the gate.
        els = [self._ranked(1, 40.0), self._ranked(2, 40.0, top=2000000)]
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[hierarchy]", str(ctx.exception))


# --- Full-bleed margins carve-out (T-801, REQ-204) --------------------------
#
# A freeform box placed `at full-bleed` deliberately paints the whole slide,
# margins included. check_within_margins skips elements with a truthy
# `full_bleed` flag (mirroring the ghost pattern); the SAME geometry without
# the flag is still a margins fault. Colour stays token-checked either way,
# and container semantics make overlap with contained elements legal.


def full_bleed_box(fill="#4F81BD", **overrides):
    el = {
        "role": "freeform-panel", "kind": "box", "container": True,
        "full_bleed": True, "text": "full-bleed wash",
        "fill": fill, "left": 0, "top": 0, "width": SLIDE_W, "height": SLIDE_H,
    }
    el.update(overrides)
    return el


class TestFullBleedMargins(unittest.TestCase):
    def test_full_bleed_skips_the_margins_rule(self):
        self.assertEqual(
            lint.check_within_margins([full_bleed_box()], TOKENS,
                                      SLIDE_W, SLIDE_H),
            [],
        )

    def test_same_geometry_without_the_flag_fails(self):
        el = full_bleed_box()
        del el["full_bleed"]
        violations = lint.check_within_margins([el], TOKENS, SLIDE_W, SLIDE_H)
        self.assertTrue(violations)
        self.assertIn("[margins]", violations[0])
        with self.assertRaises(lint.LintError) as ctx:
            lint.check([el], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[margins]", str(ctx.exception))

    def test_colour_rule_still_applies(self):
        off_token = full_bleed_box(fill="#ABCDEF")
        violations = lint.check_colours([off_token], TOKENS)
        self.assertTrue(violations)
        self.assertIn("[colour]", violations[0])
        with self.assertRaises(lint.LintError) as ctx:
            lint.check([off_token], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[colour]", str(ctx.exception))

    def test_container_semantics_admit_contained_elements(self):
        # The wash is a container covering the whole slide: any element it
        # wholly holds overlaps it legally, and the full gate clears.
        els = [full_bleed_box()] + good_elements()
        self.assertEqual(lint.check_no_overlap(els), [])
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))


# --- Contrast rule (T-004) -------------------------------------------------
#
# check_contrast is the seventh hard rule: text must read on the ground it
# actually sits on. It is opt-in by data — only an element carrying BOTH
# `colour` and `ground` is judged — so every caller that predates it
# (render.py never sets `ground`) is unaffected.


def contrast_element(colour="#C0504D", ground="#000000", font_pt=12.0):
    # 12pt, not 24pt: muted-on-ink is 4.50:1, which CLEARS the 3:1 large-text
    # floor. Only below LARGE_TEXT_PT does the 4.5:1 small-text floor bite —
    # and 12.0 is on this module's TOKENS type_scale, so check_sizes stays
    # clean and the contrast rule is the only thing check() can trip on.
    return {
        "role": "x",
        "text": "t",
        "left": 457200,
        "top": 2000000,
        "width": 2000000,
        "height": 600000,
        "font_pt": font_pt,
        "colour": colour,
        "ground": ground,
    }


class TestContrastRule(unittest.TestCase):
    def test_contrast_fails_muted_on_ink(self):
        el = contrast_element(colour="#C0504D", ground="#000000", font_pt=12.0)
        violations = lint.check_contrast([el], TOKENS)
        self.assertEqual(len(violations), 1, violations)
        self.assertIn("[contrast]", violations[0])

    def test_contrast_passes_paper_on_ink(self):
        el = contrast_element(colour="#FFFFFF", ground="#000000", font_pt=12.0)
        self.assertEqual(lint.check_contrast([el], TOKENS), [])

    def test_contrast_skips_without_ground(self):
        el = contrast_element()
        del el["ground"]
        self.assertEqual(lint.check_contrast([el], TOKENS), [])

    def test_contrast_ghost_exempt(self):
        by_flag = contrast_element()
        by_flag["ghost"] = True
        self.assertEqual(lint.check_contrast([by_flag], TOKENS), [])

        by_role = contrast_element()
        by_role["role"] = "slides-ghost"
        self.assertEqual(lint.check_contrast([by_role], TOKENS), [])

    def test_check_raises_on_contrast(self):
        # Otherwise valid: token colour, on-scale size, inside the margins,
        # nothing to overlap — only the ground makes it unreadable.
        el = contrast_element()
        self.assertEqual(lint.check_colours([el], TOKENS), [])
        self.assertEqual(lint.check_sizes([el], TOKENS), [])
        self.assertEqual(
            lint.check_within_margins([el], TOKENS, SLIDE_W, SLIDE_H), []
        )
        with self.assertRaises(lint.LintError) as ctx:
            lint.check([el], TOKENS, SLIDE_W, SLIDE_H)
        self.assertIn("[contrast]", str(ctx.exception))



if __name__ == "__main__":
    unittest.main()
