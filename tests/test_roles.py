"""Tests for source/skills/build-deck/scripts/roles.py — the six fixed roles."""
import sys
import os
import unittest

# Add the scripts directory to sys.path so `import roles` resolves.
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
from primitives import ShapeError, _wrapped_lines
from roles import (
    ROLE_PLANNERS, TICK_H_EMU, TICK_W_FRAC, content_roles,
    plan_title, plan_section, plan_statement, plan_quote,
    plan_title_content, plan_two_column, plan_composed_title,
)

SLIDE_W, SLIDE_H = 12192000, 6858000
CONTENT_W = SLIDE_W - 2 * 609600  # margin-to-margin span: 10972800

GRID = {
    "margin_x": 609600,
    "margin_top": 548640,
    "margin_bottom": 548640,
    "columns": 12,
    "gutter": 203200,
    "baseline": 91440,
}
COLOUR_ROLES = {
    "ink": "#1A1A1A",
    "paper": "#FFFFFF",
    "accent": "#0B5FFF",
    "muted": "#6B7280",
}
SHAPE = {"corner": "rounded", "hairline_pt": 1.0}

# The two type ladders: presented (a room) and read (a document).
PRESENTED_SCALE = {"display": 96.0, "title": 60.0, "h1": 40.0,
                   "body": 24.0, "caption": 16.0}
READ_SCALE = {"display": 72.0, "title": 48.0, "h1": 32.0,
              "body": 18.0, "caption": 12.0}


def make_tokens(type_scale):
    return {
        "grid": dict(GRID),
        "type_scale": dict(type_scale),
        "colour_roles": dict(COLOUR_ROLES),
        "shape": dict(SHAPE),
    }


TOKENS = make_tokens(PRESENTED_SCALE)
TOKENS_READ = make_tokens(READ_SCALE)
LADDERS = (TOKENS, TOKENS_READ)

FIELDS_BY_ROLE = {
    "title": {"Title": "The quarter, measured",
              "Subtitle": "What moved and why it holds"},
    "section": {"Title": "Momentum"},
    "statement": {"Statement": "Ship the vocabulary, not the look."},
    "quote": {"Quote": "The best way to predict the future is to invent it.",
              "Attribution": "Alan Kay"},
    "title-content": {"Title": "What changed",
                      "Body": ["Pipeline doubled", "Churn held flat",
                               "Costs fell nine percent"]},
    "two-column": {"Title": "Before and after",
                   "Left": ["Manual deck builds", "Off-brand colours"],
                   "Right": ["Planned from tokens", "Linted before render"]},
}

# Which roles carry rank-2 supporting text alongside the rank-1 lead.
HAS_SUPPORT = {
    "title": True,
    "section": False,
    "statement": False,
    "quote": True,
    "title-content": True,
    "two-column": True,
}

# Every ranked text element's slides-field name, by element role.
NAME_BY_ELEMENT_ROLE = {
    "titleslide-title": "slides-field:Title",
    "titleslide-subtitle": "slides-field:Subtitle",
    "sectionslide-title": "slides-field:Title",
    "statement-text": "slides-field:Statement",
    "quote-text": "slides-field:Quote",
    "quote-attribution": "slides-field:Attribution",
    "bodyslide-title": "slides-field:Title",
    "bodyslide-body": "slides-field:Body",
    "twocol-title": "slides-field:Title",
    "twocol-left": "slides-field:Left",
    "twocol-right": "slides-field:Right",
}

# A pathologically long field (600+ chars) and its exact overflow message.
LONG = ("pathological " * 50).strip()          # 649 chars
LONG_BODY = ("pathological " * 120).strip()    # 1559 chars
OVERFLOW_CASES = {
    "title": (
        {"Title": LONG},
        "title slide content wraps deeper than the slide band — "
        "shorten the title or subtitle",
    ),
    "section": (
        {"Title": LONG},
        "section title wraps deeper than the slide band — shorten it",
    ),
    "statement": (
        {"Statement": LONG},
        "statement wraps deeper than the slide band — "
        "cut it to the line that lands",
    ),
    "quote": (
        {"Quote": LONG},
        "quote wraps deeper than the slide band — trim the quotation",
    ),
    "title-content": (
        {"Title": "What changed", "Body": [LONG_BODY]},
        "body wraps deeper than the content band — cut items or split the slide",
    ),
    "two-column": (
        {"Title": "Before and after", "Left": [LONG], "Right": ["Fine"]},
        "column wraps deeper than the content band — cut items or split the slide",
    ),
}


def plan(role, tokens):
    return ROLE_PLANNERS[role](FIELDS_BY_ROLE[role], tokens, SLIDE_W, SLIDE_H)


class TestRolePlannersRegistry(unittest.TestCase):
    def test_registry_maps_the_six_roles(self):
        self.assertEqual(
            set(ROLE_PLANNERS),
            {"title", "section", "statement", "quote",
             "title-content", "two-column"},
        )
        self.assertIs(ROLE_PLANNERS["title"], plan_title)
        self.assertIs(ROLE_PLANNERS["section"], plan_section)
        self.assertIs(ROLE_PLANNERS["statement"], plan_statement)
        self.assertIs(ROLE_PLANNERS["quote"], plan_quote)
        self.assertIs(ROLE_PLANNERS["title-content"], plan_title_content)
        self.assertIs(ROLE_PLANNERS["two-column"], plan_two_column)


class TestRoleContract(unittest.TestCase):
    """The shared element contract, proved for every role at both ladders."""

    def test_lint_passes_at_both_ladders(self):
        for role in ROLE_PLANNERS:
            for tokens in LADDERS:
                with self.subTest(role=role,
                                  ladder=tokens["type_scale"]["display"]):
                    els = plan(role, tokens)
                    self.assertIsNone(lint.check(els, tokens, SLIDE_W, SLIDE_H))

    def test_rank_hierarchy(self):
        for role in ROLE_PLANNERS:
            with self.subTest(role=role):
                els = plan(role, TOKENS)
                rank1 = [e["font_pt"] for e in els if e.get("rank") == 1]
                rank2 = [e["font_pt"] for e in els if e.get("rank") == 2]
                # Exactly one rank-1 lead per slide.
                self.assertEqual(len(rank1), 1)
                if HAS_SUPPORT[role]:
                    self.assertTrue(rank2)
                    self.assertLess(max(rank2), min(rank1))
                else:
                    self.assertEqual(rank2, [])

    def test_every_colour_is_a_token(self):
        allowed = set(COLOUR_ROLES.values())
        for role in ROLE_PLANNERS:
            with self.subTest(role=role):
                for el in plan(role, TOKENS):
                    for key in ("colour", "fill", "stroke"):
                        if key in el:
                            self.assertIn(el[key], allowed)

    def test_every_bbox_inside_margins(self):
        for role in ROLE_PLANNERS:
            with self.subTest(role=role):
                for el in plan(role, TOKENS):
                    self.assertGreaterEqual(el["left"], GRID["margin_x"])
                    self.assertGreaterEqual(el["top"], GRID["margin_top"])
                    self.assertLessEqual(
                        el["left"] + el["width"], SLIDE_W - GRID["margin_x"])
                    self.assertLessEqual(
                        el["top"] + el["height"],
                        SLIDE_H - GRID["margin_bottom"])

    def test_name_stamps_on_ranked_elements(self):
        for role in ROLE_PLANNERS:
            with self.subTest(role=role):
                for el in plan(role, TOKENS):
                    if "rank" in el:
                        self.assertEqual(
                            el["name"], NAME_BY_ELEMENT_ROLE[el["role"]])
                    else:
                        # Ticks, rules, marks: anatomy, never a spec field.
                        self.assertNotIn("name", el)
                        self.assertNotIn("rank", el)

    def test_ticks_and_rules_carry_empty_text(self):
        for role in ("title", "title-content", "two-column"):
            with self.subTest(role=role):
                for el in plan(role, TOKENS):
                    if el["role"].endswith(("-tick", "-rule")):
                        self.assertEqual(el["text"], "")

    def test_overflow_raises_exact_message(self):
        for role, (fields, message) in OVERFLOW_CASES.items():
            with self.subTest(role=role):
                with self.assertRaises(ShapeError) as ctx:
                    ROLE_PLANNERS[role](fields, TOKENS, SLIDE_W, SLIDE_H)
                self.assertEqual(str(ctx.exception), message)


class TestRequiredFields(unittest.TestCase):
    def test_title_requires_title(self):
        for fields in ({}, {"Title": ""}, {"Title": "   "}):
            with self.assertRaises(ShapeError) as ctx:
                plan_title(fields, TOKENS, SLIDE_W, SLIDE_H)
            self.assertEqual(str(ctx.exception), "title slide needs a Title")

    def test_section_requires_title(self):
        with self.assertRaises(ShapeError):
            plan_section({}, TOKENS, SLIDE_W, SLIDE_H)

    def test_statement_requires_statement(self):
        with self.assertRaises(ShapeError):
            plan_statement({}, TOKENS, SLIDE_W, SLIDE_H)

    def test_quote_requires_quote(self):
        with self.assertRaises(ShapeError):
            plan_quote({"Attribution": "Someone"}, TOKENS, SLIDE_W, SLIDE_H)

    def test_title_content_requires_title(self):
        with self.assertRaises(ShapeError):
            plan_title_content({"Body": ["x"]}, TOKENS, SLIDE_W, SLIDE_H)

    def test_two_column_names_the_missing_field(self):
        base = dict(FIELDS_BY_ROLE["two-column"])
        for missing in ("Title", "Left", "Right"):
            fields = {k: v for k, v in base.items() if k != missing}
            with self.assertRaises(ShapeError) as ctx:
                plan_two_column(fields, TOKENS, SLIDE_W, SLIDE_H)
            self.assertIn(missing, str(ctx.exception))


class TestOptionalAndBlockFields(unittest.TestCase):
    def test_title_without_subtitle(self):
        els = plan_title({"Title": "Alone"}, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(
            [e["role"] for e in els], ["titleslide-tick", "titleslide-title"])
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

    def test_quote_without_attribution(self):
        els = plan_quote({"Quote": "Less, but better."},
                         TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual([e["role"] for e in els], ["quote-mark", "quote-text"])
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

    def test_body_accepts_a_single_string(self):
        as_list = plan_title_content(
            {"Title": "T", "Body": ["One point"]}, TOKENS, SLIDE_W, SLIDE_H)
        as_str = plan_title_content(
            {"Title": "T", "Body": "One point"}, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(as_list, as_str)

    def test_columns_accept_single_strings(self):
        els = plan_two_column(
            {"Title": "T", "Left": "Only left", "Right": "Only right"},
            TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(
            len([e for e in els if e["role"] == "twocol-left"]), 1)
        self.assertEqual(
            len([e for e in els if e["role"] == "twocol-right"]), 1)
        self.assertIsNone(lint.check(els, TOKENS, SLIDE_W, SLIDE_H))

    def test_rule_between_body_items(self):
        els = plan(  # three items -> two rules, hairline-thick, muted
            "title-content", TOKENS)
        rules = [e for e in els if e["role"] == "bodyslide-rule"]
        self.assertEqual(len(rules), 2)
        for rule in rules:
            self.assertEqual(rule["kind"], "edge")
            self.assertEqual(rule["colour"], COLOUR_ROLES["muted"])
            self.assertEqual(rule["stroke_w"], round(SHAPE["hairline_pt"] * 12700))
            self.assertEqual(rule["height"], rule["stroke_w"])
            self.assertEqual(rule["y1"], rule["y2"])  # horizontal

    def test_two_column_rule_spans_the_deeper_column(self):
        els = plan("two-column", TOKENS)
        rule = next(e for e in els if e["role"] == "twocol-rule")
        cols = [e for e in els if e["role"] in ("twocol-left", "twocol-right")]
        self.assertEqual(rule["x1"], rule["x2"])  # vertical
        self.assertEqual(rule["y1"], min(e["top"] for e in cols))
        self.assertEqual(
            rule["y2"], max(e["top"] + e["height"] for e in cols))


class TestTickAnatomy(unittest.TestCase):
    def test_tick_dimensions(self):
        for role, tick_role in (("title", "titleslide-tick"),
                                ("title-content", "bodyslide-tick"),
                                ("two-column", "twocol-tick")):
            with self.subTest(role=role):
                els = plan(role, TOKENS)
                tick = next(e for e in els if e["role"] == tick_role)
                self.assertEqual(tick["kind"], "box")
                self.assertEqual(tick["fill"], COLOUR_ROLES["accent"])
                self.assertEqual(tick["left"], GRID["margin_x"])
                self.assertEqual(tick["width"], round(SLIDE_W * TICK_W_FRAC))
                self.assertEqual(tick["height"], TICK_H_EMU)


class TestSectionGhost(unittest.TestCase):
    def test_ordinal_emits_ghost(self):
        els = plan_section({"Title": "Momentum"}, TOKENS, SLIDE_W, SLIDE_H,
                           ordinal=3)
        ghosts = [e for e in els if e["role"] == "sectionslide-ghost"]
        self.assertEqual(len(ghosts), 1)
        ghost = ghosts[0]
        self.assertEqual(ghost["text"], "03")
        self.assertIs(ghost["ghost"], True)
        self.assertEqual(ghost["font_pt"], 96.0 * 3)   # display × GHOST_MULTIPLE
        self.assertEqual(ghost["colour"], COLOUR_ROLES["muted"])
        self.assertNotIn("rank", ghost)
        self.assertNotIn("name", ghost)

    def test_ghosted_section_clears_the_lint_at_both_ladders(self):
        for tokens in LADDERS:
            with self.subTest(ladder=tokens["type_scale"]["display"]):
                els = plan_section({"Title": "Momentum"}, tokens,
                                   SLIDE_W, SLIDE_H, ordinal=3)
                self.assertIsNone(lint.check(els, tokens, SLIDE_W, SLIDE_H))

    def test_no_ordinal_no_ghost(self):
        for ordinal in (None, 0, "3"):
            with self.subTest(ordinal=ordinal):
                els = plan_section({"Title": "Momentum"}, TOKENS,
                                   SLIDE_W, SLIDE_H, ordinal=ordinal)
                self.assertEqual(
                    [e for e in els if e["role"] == "sectionslide-ghost"], [])


class TestComposedTitle(unittest.TestCase):
    def test_band_math(self):
        els, band = plan_composed_title(
            "Where the margin went", TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(len(els), 1)
        el = els[0]
        self.assertEqual(el["role"], "composedtitle-heading")
        self.assertEqual(el["font_pt"], 40.0)
        self.assertEqual(el["colour"], COLOUR_ROLES["ink"])
        self.assertEqual(el["rank"], 1)
        self.assertEqual(el["name"], "slides-field:Title")
        # One line of h1: round(40 * 12700 * 1.2) = 609600 EMU.
        self.assertEqual(
            (el["left"], el["top"], el["width"], el["height"]),
            (609600, 548640, 10972800, 609600),
        )
        # Band: (margin_x, title_bottom + 2*baseline, content_w,
        #        (slide_h - margin_bottom) - title_bottom - 2*baseline)
        self.assertEqual(band, (609600, 1341120, 10972800, 4968240))

    def test_lint_passes_at_both_ladders(self):
        for tokens in LADDERS:
            with self.subTest(ladder=tokens["type_scale"]["display"]):
                els, _band = plan_composed_title(
                    "Where the margin went", tokens, SLIDE_W, SLIDE_H)
                self.assertIsNone(lint.check(els, tokens, SLIDE_W, SLIDE_H))

    def test_title_consuming_the_band_raises(self):
        with self.assertRaises(ShapeError) as ctx:
            plan_composed_title(LONG, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(
            str(ctx.exception),
            "composed title leaves no room below it — "
            "shorten the title or drop it",
        )


class LineFitTest(unittest.TestCase):
    """REQ-202: lead text prefers the ladder step that HOLDS ITS LINE COUNT,
    not merely the first that fits the band — 'Q3 Business Review' must land
    one-lined at the title step, not two-lined at display."""

    def _title_el(self, els):
        return next(e for e in els if e["role"] == "titleslide-title")

    def test_title_steps_down_to_hold_one_line(self):
        text = "Q3 Business Review"
        els = plan_title({"Title": text}, TOKENS, SLIDE_W, SLIDE_H)
        title = self._title_el(els)
        # Two-lined at display (the v0.17 bug), one-lined at the title step.
        self.assertEqual(_wrapped_lines(text, CONTENT_W, 96.0), 2)
        self.assertEqual(title["font_pt"], 60.0)
        self.assertEqual(_wrapped_lines(text, CONTENT_W, 60.0), 1)
        self.assertIs(title.get("font_stepped"), True)

    def test_short_title_stays_at_display(self):
        els = plan_title({"Title": "Fieldnote"}, TOKENS, SLIDE_W, SLIDE_H)
        title = self._title_el(els)
        self.assertEqual(title["font_pt"], 96.0)
        self.assertEqual(_wrapped_lines("Fieldnote", CONTENT_W, 96.0), 1)
        self.assertNotIn("font_stepped", title)

    def test_unfittable_title_takes_two_lines_at_the_floor(self):
        # One line is impossible even at the floor step (60pt holds 14.4em;
        # this is ~28em), so the floor relaxes to two lines rather than raise.
        text = "A plain-language account of the quarter and what it means"
        els = plan_title({"Title": text}, TOKENS, SLIDE_W, SLIDE_H)
        title = self._title_el(els)
        self.assertEqual(title["font_pt"], 60.0)
        self.assertEqual(_wrapped_lines(text, CONTENT_W, 60.0), 2)
        self.assertIs(title.get("font_stepped"), True)

    def test_600_char_title_still_raises(self):
        with self.assertRaises(ShapeError) as ctx:
            plan_title({"Title": LONG}, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(
            str(ctx.exception),
            "title slide content wraps deeper than the slide band — "
            "shorten the title or subtitle",
        )

    def test_section_title_holds_one_line(self):
        text = "Where the quarter went"
        els = plan_section({"Title": text}, TOKENS, SLIDE_W, SLIDE_H)
        title = next(e for e in els if e["role"] == "sectionslide-title")
        self.assertEqual(title["width"], CONTENT_W * 7 // 12)
        self.assertEqual(
            _wrapped_lines(text, title["width"], title["font_pt"]), 1)

    def test_statement_spans_full_content_width(self):
        els = plan_statement(
            FIELDS_BY_ROLE["statement"], TOKENS, SLIDE_W, SLIDE_H)
        el = els[0]
        self.assertEqual(el["left"], GRID["margin_x"])
        self.assertEqual(el["width"], CONTENT_W)
        self.assertEqual(el["align"], "center")
        self.assertLessEqual(
            _wrapped_lines(el["text"], el["width"], el["font_pt"]), 3)


class ContentRolesTest(unittest.TestCase):
    """D-410: content_roles maps the four colour roles onto a canvas."""

    def test_paper_canvas_is_identity(self):
        self.assertEqual(content_roles(TOKENS, canvas="paper"), COLOUR_ROLES)

    def test_default_canvas_is_paper(self):
        self.assertEqual(content_roles(TOKENS), COLOUR_ROLES)

    def test_ink_canvas_inverts_for_legibility(self):
        roles = content_roles(TOKENS, canvas="ink")
        self.assertEqual(roles["ink"], COLOUR_ROLES["paper"])
        # Muted lightens too — grey-on-dark does not read.
        self.assertEqual(roles["muted"], COLOUR_ROLES["paper"])
        self.assertEqual(roles["paper"], COLOUR_ROLES["ink"])
        self.assertEqual(roles["accent"], COLOUR_ROLES["accent"])

    def test_bad_canvas_raises_naming_it(self):
        with self.assertRaises(ShapeError) as ctx:
            content_roles(TOKENS, canvas="plum")
        self.assertIn("plum", str(ctx.exception))

    def test_luminance_boundary_uses_the_tokens_formula(self):
        # Pure green: a naive channel mean is 85 (dark) but tokens._luminance
        # weights green at .7152 -> 182.4 (light), so the mapping stays
        # identity — this discriminates the formula from a naive average.
        tokens = make_tokens(PRESENTED_SCALE)
        tokens["colour_roles"]["accent"] = "#00FF00"
        self.assertEqual(
            content_roles(tokens, canvas="accent")["ink"], COLOUR_ROLES["ink"])
        # Mid-grey straddles the threshold: 128.0 is light (strict < 128),
        # 127.0 is dark.
        tokens["colour_roles"]["accent"] = "#808080"
        self.assertEqual(
            content_roles(tokens, canvas="accent")["ink"], COLOUR_ROLES["ink"])
        tokens["colour_roles"]["accent"] = "#7F7F7F"
        self.assertEqual(
            content_roles(tokens, canvas="accent")["ink"],
            COLOUR_ROLES["paper"])


class CanvasKwargTest(unittest.TestCase):
    """Planners route their colours through content_roles(tokens, canvas);
    default canvas='paper' is the identity, so existing suites (which call
    with no canvas) prove current renders are unchanged."""

    def test_statement_on_ink_canvas_uses_paper_text(self):
        els = plan_statement(
            FIELDS_BY_ROLE["statement"], TOKENS, SLIDE_W, SLIDE_H,
            canvas="ink")
        self.assertEqual(els[0]["colour"], COLOUR_ROLES["paper"])

    def test_title_on_ink_canvas_lightens_text_keeps_accent_tick(self):
        els = plan_title(
            FIELDS_BY_ROLE["title"], TOKENS, SLIDE_W, SLIDE_H, canvas="ink")
        by_role = {e["role"]: e for e in els}
        self.assertEqual(
            by_role["titleslide-title"]["colour"], COLOUR_ROLES["paper"])
        self.assertEqual(
            by_role["titleslide-subtitle"]["colour"], COLOUR_ROLES["paper"])
        self.assertEqual(
            by_role["titleslide-tick"]["fill"], COLOUR_ROLES["accent"])

    def test_section_ghost_lightens_on_ink_canvas(self):
        els = plan_section({"Title": "Momentum"}, TOKENS, SLIDE_W, SLIDE_H,
                           ordinal=2, canvas="ink")
        ghost = next(e for e in els if e["role"] == "sectionslide-ghost")
        self.assertEqual(ghost["colour"], COLOUR_ROLES["paper"])

    def test_every_planner_accepts_canvas_and_drops_dark_illegible_inks(self):
        # On a dark canvas no element may keep ink or muted (grey-on-dark).
        banned = {COLOUR_ROLES["ink"], COLOUR_ROLES["muted"]}
        for role in ROLE_PLANNERS:
            with self.subTest(role=role):
                els = ROLE_PLANNERS[role](
                    FIELDS_BY_ROLE[role], TOKENS, SLIDE_W, SLIDE_H,
                    canvas="ink")
                for el in els:
                    for key in ("colour", "fill", "stroke"):
                        if key in el:
                            self.assertNotIn(el[key], banned)

    def test_composed_title_accepts_canvas(self):
        els, _band = plan_composed_title(
            "Where the margin went", TOKENS, SLIDE_W, SLIDE_H, canvas="ink")
        self.assertEqual(els[0]["colour"], COLOUR_ROLES["paper"])


class ComposedTitleLineCapTest(unittest.TestCase):
    """plan_composed_title has a single step (h1), so REQ-202's criterion
    applies directly: past two lines it raises its existing ShapeError."""

    def test_two_line_heading_still_plans(self):
        # ~28em wraps to two lines at h1's 21.6em budget — allowed.
        text = "A plain-language account of the quarter and what it means"
        self.assertEqual(_wrapped_lines(text, CONTENT_W, 40.0), 2)
        els, _band = plan_composed_title(text, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(els[0]["font_pt"], 40.0)

    def test_three_line_heading_raises_the_existing_error(self):
        text = ("A heading that keeps qualifying itself until it has "
                "wrapped well past the two lines a composed slide can "
                "afford to spend on it")
        self.assertGreater(_wrapped_lines(text, CONTENT_W, 40.0), 2)
        with self.assertRaises(ShapeError) as ctx:
            plan_composed_title(text, TOKENS, SLIDE_W, SLIDE_H)
        self.assertEqual(
            str(ctx.exception),
            "composed title leaves no room below it — "
            "shorten the title or drop it",
        )


if __name__ == "__main__":
    unittest.main()
