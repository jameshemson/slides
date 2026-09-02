"""Tests for source/skills/build-deck/scripts/lint_pptx.py

The post-render gate reads a real .pptx, so every test builds one with
python-pptx, saves it to a temp file, and lints the file — never a stub.
Geometry and palette assertions call the lint.py check they expect to fire
and assert ITS message, so the wording stays coupled to the one mechanical
gate rather than being restated here.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

# Add the scripts directory to sys.path so `import lint_pptx` works.
_SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "source",
    "skills",
    "build-deck",
    "scripts",
)
sys.path.insert(0, os.path.abspath(_SCRIPTS_DIR))

from lxml import etree  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.chart.data import CategoryChartData  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.chart import XL_CHART_TYPE  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE  # noqa: E402
from pptx.util import Inches, Pt  # noqa: E402

import lint  # noqa: E402
import lint_pptx  # noqa: E402
import tokens as tokens_mod  # noqa: E402

BRAND = {
    "fidelity": "brand",
    "fonts": {"heading": "Georgia", "body": "Calibri"},
    "colours": {
        "accent": "#4F81BD",
        "accent2": "#C0504D",
        "ink": "#101010",
        "paper": "#FFFFFF",
    },
}

# ink / paper / accent / muted, and the "presented" type scale the absent
# register selects: display 96, title 60, h1 40, body 24, caption 16.
INK = "#101010"
PAPER = "#FFFFFF"
ACCENT = "#4F81BD"
MUTED = "#C0504D"
OFF_TOKEN = "#123456"     # dark: reads on paper, so only [colour] fires
OFF_TOKEN_LIGHT = "#EEDDCC"  # light: reads under ink text

TOKENS = tokens_mod.resolve_tokens(BRAND, None, None)

SLIDE_W, SLIDE_H = 12192000, 6858000

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


# ---------------------------------------------------------------------------
# Deck-building helpers
# ---------------------------------------------------------------------------

def _deck():
    """A blank 16:9 presentation the way pptxgenjs LAYOUT_WIDE lays one out."""
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def _slide(prs):
    """A blank slide (layout 6 carries no placeholders)."""
    return prs.slides.add_slide(prs.slide_layouts[6])


def _apply_alpha(colour_element, alpha):
    """Append <a:alpha val="N"/> to the a:srgbClr under an a:solidFill."""
    fill = colour_element.find(_A + "solidFill")
    srgb = fill.find(_A + "srgbClr")
    node = etree.SubElement(srgb, _A + "alpha")
    node.set("val", str(alpha))


def _style_run(run, pt, rgb, font, alpha=None):
    if pt is not None:
        run.font.size = Pt(pt)
    if font is not None:
        run.font.name = font
    if rgb is not None:
        run.font.color.rgb = RGBColor.from_string(rgb.lstrip("#"))
        if alpha is not None:
            _apply_alpha(run._r.find(_A + "rPr"), alpha)


def _text(slide, text, x, y, w, h, pt, rgb, font, name=None):
    """One textbox holding one run. Positions are inches."""
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        shape.name = name
    run = shape.text_frame.paragraphs[0].add_run()
    run.text = text
    _style_run(run, pt, rgb, font)
    return shape


def _runs(slide, specs, x, y, w, h, name=None):
    """One textbox holding several runs in one paragraph.

    `specs` is a list of (text, pt, rgb, font, alpha_or_None). An alpha is the
    OOXML <a:alpha> value: 100000 opaque, 30000 heavily translucent.
    """
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        shape.name = name
    paragraph = shape.text_frame.paragraphs[0]
    for text, pt, rgb, font, alpha in specs:
        run = paragraph.add_run()
        run.text = text
        _style_run(run, pt, rgb, font, alpha)
    return shape


def _box(slide, x, y, w, h, rgb, name=None, alpha=None):
    """A rectangle with a solid fill and no text. Positions are inches."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        shape.name = name
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(rgb.lstrip("#"))
    if alpha is not None:
        _apply_alpha(shape._element.spPr, alpha)
    return shape


def _background(slide, rgb):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string(rgb.lstrip("#"))


def _chart(slide, x, y, w, h, name=None):
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(x), Inches(y), Inches(w), Inches(h),
        _chart_data(),
    )
    if name:
        frame.name = name
    return frame


def _chart_data():
    data = CategoryChartData()
    data.categories = ["Q1", "Q2"]
    data.add_series("Revenue", (1.0, 2.0))
    return data


def _style_chart_font(font, pt, rgb, name):
    font.size = Pt(pt)
    font.color.rgb = RGBColor.from_string(rgb.lstrip("#"))
    font.name = name


# ---------------------------------------------------------------------------
# Running helpers
# ---------------------------------------------------------------------------

class _Deck:
    """A saved .pptx plus a brand.json beside it, cleaned up on exit."""

    def __init__(self, prs):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "deck.pptx")
        prs.save(self.path)
        self.brand = os.path.join(self.dir, "brand.json")
        with open(self.brand, "w", encoding="utf-8") as handle:
            json.dump(BRAND, handle)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


def _report(prs):
    with _Deck(prs) as deck:
        return lint_pptx.lint_deck(deck.path, BRAND)


def _violations(prs):
    """Every violation across the deck, flattened."""
    return [v for s in _report(prs)["slides"] for v in s["violations"]]


def _notes(prs):
    return [n for s in _report(prs)["slides"] for n in s["notes"]]


def _run_main(prs, extra=()):
    """Run the CLI over a saved deck. Returns (exit_code, stdout)."""
    with _Deck(prs) as deck:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = lint_pptx.main([deck.path, "--brand", deck.brand, *extra])
        return code, out.getvalue()


def _emu_box(x, y, w, h):
    return {
        "left": int(Inches(x)),
        "top": int(Inches(y)),
        "width": int(Inches(w)),
        "height": int(Inches(h)),
    }


def _tagged(messages, tag):
    return [m for m in messages if tag in m]


# ---------------------------------------------------------------------------
# The clean baseline and the four per-run identity rules
# ---------------------------------------------------------------------------

def _clean_prs(body_pt=24, body_rgb=INK, body_font="Calibri"):
    """A lead and a supporting line — the shape every other test perturbs."""
    prs = _deck()
    slide = _slide(prs)
    _text(slide, "The turn", 1, 1, 6, 1, 60, ACCENT, "Georgia",
          name="slides-lead:Title")
    _text(slide, "Supporting line", 1, 2.5, 6, 0.8, body_pt, body_rgb,
          body_font, name="body")
    return prs


class TestCleanDeck(unittest.TestCase):
    def test_clean_deck(self):
        prs = _clean_prs()
        self.assertEqual(_violations(prs), [])
        code, out = _run_main(_clean_prs())
        self.assertEqual(code, 0)
        self.assertIn("lint: clean (1 slides, 2 elements)", out)


class TestRunIdentity(unittest.TestCase):
    def test_off_token_colour(self):
        prs = _clean_prs(body_rgb=OFF_TOKEN)
        violations = _violations(prs)
        self.assertTrue(_tagged(violations, "[colour]"), violations)
        code, out = _run_main(_clean_prs(body_rgb=OFF_TOKEN))
        self.assertEqual(code, 1)
        self.assertIn("lint: 1 violation(s) on 1 slide(s)", out)

    def test_off_scale_size(self):
        violations = _violations(_clean_prs(body_pt=22))
        self.assertTrue(_tagged(violations, "[size]"), violations)
        self.assertTrue(any("22.0" in m for m in _tagged(violations, "[size]")))

    def test_missing_font(self):
        violations = _violations(_clean_prs(body_font=None))
        explicit = _tagged(violations, "[explicit]")
        self.assertTrue(explicit, violations)
        self.assertTrue(any("fontFace" in m for m in explicit), explicit)

    def test_wrong_font(self):
        violations = _violations(_clean_prs(body_font="Arial"))
        font_violations = _tagged(violations, "[font]")
        self.assertTrue(font_violations, violations)
        self.assertIn("Arial", font_violations[0])


# ---------------------------------------------------------------------------
# Second-run tests — a shape is not one uniform run
# ---------------------------------------------------------------------------

def _two_run_prs(second, panel=None):
    """A textbox whose first run is clean and whose second is `second`."""
    prs = _deck()
    slide = _slide(prs)
    if panel is not None:
        _box(slide, 1, 1, 6, 2, panel, name="panel")
    _runs(slide, [("First ", 24, INK, "Calibri", None), second],
          1.5, 1.5, 4, 1, name="body")
    return prs


class TestSecondRun(unittest.TestCase):
    def test_second_run_off_scale(self):
        violations = _violations(_two_run_prs(("second", 22, INK, "Calibri", None)))
        sized = _tagged(violations, "[size]")
        self.assertEqual(len(sized), 1, violations)
        self.assertIn("second", sized[0])

    def test_second_run_off_token(self):
        violations = _violations(
            _two_run_prs(("second", 24, OFF_TOKEN, "Calibri", None)))
        coloured = _tagged(violations, "[colour]")
        self.assertEqual(len(coloured), 1, violations)
        self.assertIn("second", coloured[0])

    def test_second_run_wrong_font(self):
        violations = _violations(_two_run_prs(("second", 24, INK, "Arial", None)))
        fonts = _tagged(violations, "[font]")
        self.assertEqual(len(fonts), 1, violations)
        self.assertIn("second", fonts[0])

    def test_second_run_missing_colour(self):
        violations = _violations(_two_run_prs(("second", 24, None, "Calibri", None)))
        explicit = _tagged(violations, "[explicit]")
        self.assertEqual(len(explicit), 1, violations)
        self.assertIn("second", explicit[0])
        self.assertIn("colour", explicit[0])

    def test_second_run_low_contrast(self):
        # Both runs sit on the ink panel; only the muted one fails, and only
        # because 16pt is below the large-text threshold.
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 1, 1, 6, 2, INK, name="panel")
        _runs(slide, [("paper run ", 16, PAPER, "Calibri", None),
                      ("muted run", 16, MUTED, "Calibri", None)],
              1.5, 1.5, 4, 1, name="body")
        violations = _violations(prs)
        contrast = _tagged(violations, "[contrast]")
        self.assertEqual(len(contrast), 1, violations)
        self.assertIn("muted run", contrast[0])

    def test_alpha_reduces_contrast(self):
        def build(alpha):
            prs = _deck()
            slide = _slide(prs)
            _box(slide, 1, 1, 6, 2, INK, name="panel")
            _runs(slide, [("Ghosted", 24, PAPER, "Calibri", alpha)],
                  1.5, 1.5, 4, 1, name="body")
            return prs

        faded = _violations(build(30000))
        self.assertTrue(_tagged(faded, "[contrast]"), faded)
        self.assertEqual(_violations(build(None)), [])


# ---------------------------------------------------------------------------
# The text box's own paint
# ---------------------------------------------------------------------------

class TestTextBoxPaint(unittest.TestCase):
    def test_text_box_fill_off_token(self):
        prs = _deck()
        slide = _slide(prs)
        shape = _text(slide, "On a chip", 1, 1, 4, 1, 24, PAPER, "Calibri",
                      name="chip")
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(OFF_TOKEN.lstrip("#"))
        violations = _violations(prs)
        coloured = _tagged(violations, "[colour]")
        self.assertTrue(coloured, violations)
        self.assertTrue(any("fill" in m for m in coloured), coloured)

    def test_text_box_line_off_token(self):
        prs = _deck()
        slide = _slide(prs)
        shape = _text(slide, "Outlined", 1, 1, 4, 1, 24, INK, "Calibri",
                      name="outline")
        shape.line.color.rgb = RGBColor.from_string(OFF_TOKEN.lstrip("#"))
        violations = _violations(prs)
        coloured = _tagged(violations, "[colour]")
        self.assertTrue(coloured, violations)
        self.assertTrue(any("stroke" in m for m in coloured), coloured)


# ---------------------------------------------------------------------------
# Ground resolution
# ---------------------------------------------------------------------------

class TestGround(unittest.TestCase):
    def test_straddling_text_is_ground_violation(self):
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 1, 1, 4, 2, INK, name="panel")
        _text(slide, "Half on, half off", 3, 1.5, 4, 1, 24, PAPER, "Calibri",
              name="body")
        violations = _violations(prs)
        ground = _tagged(violations, "[ground]")
        self.assertTrue(ground, violations)
        self.assertIn("straddles a panel edge", ground[0])

    def test_topmost_containing_panel_wins(self):
        # The ink panel is beneath, but the paper panel wholly holds the text,
        # so ink type on it reads — and the deck is clean.
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 1, 1, 6, 4, INK, name="under")
        _box(slide, 1.5, 1.5, 5, 3, PAPER, name="over")
        _text(slide, "Ink on paper", 2, 2, 3, 1, 24, INK, "Calibri", name="body")
        self.assertEqual(_violations(prs), [])

    def test_translucent_panel_composites(self):
        def build(text_colour):
            prs = _deck()
            slide = _slide(prs)
            _background(slide, INK)
            _box(slide, 1, 1, 6, 3, ACCENT, name="wash", alpha=50000)
            _text(slide, "Over the wash", 1.5, 1.5, 4, 1, 24, text_colour,
                  "Calibri", name="body")
            return prs

        muted = _violations(build(MUTED))
        self.assertTrue(_tagged(muted, "[contrast]"), muted)
        self.assertEqual(_violations(build(PAPER)), [])

    def test_background_ground(self):
        prs = _deck()
        slide = _slide(prs)
        _background(slide, INK)
        _text(slide, "Muted on ink", 1, 1, 4, 1, 16, MUTED, "Calibri",
              name="body")
        violations = _violations(prs)
        self.assertTrue(_tagged(violations, "[contrast]"), violations)

    def test_muted_on_ink_panel_fails_contrast(self):
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 1, 1, 6, 2, INK, name="panel")
        _text(slide, "Muted", 1.5, 1.5, 4, 0.8, 16, MUTED, "Calibri", name="body")
        violations = _violations(prs)
        self.assertTrue(_tagged(violations, "[contrast]"), violations)

    def test_paper_on_ink_panel_is_clean(self):
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 1, 1, 6, 2, INK, name="panel")
        _text(slide, "Paper", 1.5, 1.5, 4, 0.8, 16, PAPER, "Calibri", name="body")
        self.assertEqual(_violations(prs), [])

    def test_ghost_is_exempt(self):
        # Muted at 16pt on ink is exactly the pair the contrast rule stops —
        # unless the shape declares itself a ghost.
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 1, 1, 6, 2, INK, name="panel")
        _text(slide, "01", 1.5, 1.5, 4, 0.8, 16, MUTED, "Calibri",
              name="slides-ghost")
        self.assertEqual(_violations(prs), [])

    def test_ghost_excluded_from_hierarchy(self):
        # A decorative glyph may be the biggest thing on the slide — the
        # fallback renderer's ghost numeral is — without outranking the lead.
        prs = _deck()
        slide = _slide(prs)
        _text(slide, "Quote text", 1, 3, 8, 1.5, 40, INK, "Georgia",
              name="slides-lead:Quote")
        _text(slide, "\u201c", 1, 1, 2, 1.5, 96, MUTED, "Georgia",
              name="slides-ghost")
        self.assertEqual(_violations(prs), [])

    def test_full_bleed_panel_is_clean(self):
        prs = _deck()
        slide = _slide(prs)
        _box(slide, 0, 0, 5, 7.5, ACCENT, name="wash")
        self.assertEqual(_violations(prs), [])

    def test_background_off_token(self):
        prs = _deck()
        slide = _slide(prs)
        _background(slide, OFF_TOKEN)
        _text(slide, "On a strange ground", 1, 1, 5, 1, 24, PAPER, "Calibri",
              name="body")
        violations = _violations(prs)
        background = _tagged(violations, "[background]")
        self.assertTrue(background, violations)
        self.assertIn("is not a brand token", background[0])


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _table_prs(off_scale=False, off_token_fill=False):
    prs = _deck()
    slide = _slide(prs)
    frame = slide.shapes.add_table(
        2, 2, Inches(1), Inches(1), Inches(6), Inches(1.5))
    frame.name = "grid"
    table = frame.table
    for r in range(2):
        for c in range(2):
            cell = table.cell(r, c)
            cell.text = f"cell {r}{c}"
            run = cell.text_frame.paragraphs[0].runs[0]
            pt = 22 if (off_scale and r == 1 and c == 1) else 24
            _style_run(run, pt, INK, "Calibri")
    if off_token_fill:
        cell = table.cell(0, 0)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(
            OFF_TOKEN_LIGHT.lstrip("#"))
    return prs


class TestTables(unittest.TestCase):
    def test_clean_table(self):
        self.assertEqual(_violations(_table_prs()), [])

    def test_table_cell_runs_checked(self):
        violations = _violations(_table_prs(off_scale=True))
        sized = _tagged(violations, "[size]")
        self.assertTrue(sized, violations)
        self.assertIn("22.0", sized[0])
        self.assertIn("cell 11", sized[0])

    def test_table_cell_fill_off_token(self):
        violations = _violations(_table_prs(off_token_fill=True))
        coloured = _tagged(violations, "[colour]")
        self.assertTrue(coloured, violations)
        self.assertTrue(any("fills" in m for m in coloured), coloured)
        self.assertTrue(any(OFF_TOKEN_LIGHT in m for m in coloured), coloured)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

class TestCharts(unittest.TestCase):
    def test_chart_text_checked(self):
        prs = _deck()
        slide = _slide(prs)
        frame = _chart(slide, 1, 1, 6, 3, name="figure")
        chart = frame.chart
        chart.has_title = True
        chart.chart_title.text_frame.text = "Revenue"  # font wholly inherited
        chart.category_axis.tick_labels.font.size = Pt(12)  # off the scale
        series = chart.plots[0].series[0]
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = RGBColor.from_string(
            OFF_TOKEN.lstrip("#"))

        violations = _violations(prs)
        chart_messages = _tagged(violations, "[chart]")
        self.assertTrue(chart_messages, violations)
        self.assertTrue(
            any("[explicit]" in m and "title" in m for m in chart_messages),
            chart_messages)
        self.assertTrue(any("[size]" in m and "12.0" in m for m in chart_messages),
                        chart_messages)
        self.assertTrue(any("[colour]" in m and OFF_TOKEN in m
                            for m in chart_messages), chart_messages)

    def test_clean_chart(self):
        prs = _deck()
        slide = _slide(prs)
        frame = _chart(slide, 1, 1, 6, 3, name="figure")
        chart = frame.chart
        for axis in (chart.category_axis, chart.value_axis):
            _style_chart_font(axis.tick_labels.font, 16, INK, "Calibri")
        series = chart.plots[0].series[0]
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = RGBColor.from_string(
            ACCENT.lstrip("#"))
        self.assertEqual(_violations(prs), [])


# ---------------------------------------------------------------------------
# Geometry — the wording comes from lint.py itself
# ---------------------------------------------------------------------------

class TestGeometry(unittest.TestCase):
    def test_text_past_margin(self):
        prs = _deck()
        slide = _slide(prs)
        _text(slide, "Edge", 0.1, 1, 4, 1, 24, INK, "Calibri", name="body")
        element = {"role": "body", "text": "Edge", **_emu_box(0.1, 1, 4, 1)}
        expected = lint.check_within_margins(
            [element], TOKENS, SLIDE_W, SLIDE_H)[0]
        self.assertIn("slide 1: " + expected, _violations(prs))

    def test_text_on_text_overlap(self):
        prs = _deck()
        slide = _slide(prs)
        _text(slide, "Alpha", 1, 1, 4, 1, 60, INK, "Georgia", name="a")
        _text(slide, "Beta", 2, 1.2, 4, 1, 24, INK, "Calibri", name="b")
        a = {"role": "a", "text": "Alpha", **_emu_box(1, 1, 4, 1)}
        b = {"role": "b", "text": "Beta", **_emu_box(2, 1.2, 4, 1)}
        expected = lint.check_no_overlap([a, b])[0]
        self.assertIn("slide 1: " + expected, _violations(prs))

    def test_lead_must_be_largest(self):
        prs = _deck()
        slide = _slide(prs)
        _text(slide, "Lead", 1, 1, 4, 1, 40, INK, "Georgia",
              name="slides-lead:Title")
        _text(slide, "Louder", 1, 3, 6, 1, 60, INK, "Calibri", name="body")
        expected = lint.check_hierarchy([
            {"role": "slides-lead:Title", "rank": 1, "font_pt": 40.0},
            {"role": "body", "rank": 2, "font_pt": 60.0},
        ])[0]
        self.assertIn("slide 1: " + expected, _violations(prs))

    def test_element_cap(self):
        prs = _deck()
        slide = _slide(prs)
        for i in range(lint.ELEMENT_CAP + 1):
            row, col = divmod(i, 5)
            _box(slide, 0.8 + col * 0.6, 0.7 + row * 0.6, 0.4, 0.4, ACCENT,
                 name=f"mark-{i}")
        expected = lint.check_count([{}] * (lint.ELEMENT_CAP + 1))[0]
        self.assertIn("slide 1: " + expected, _violations(prs))


# ---------------------------------------------------------------------------
# Notes — advisory, never a violation
# ---------------------------------------------------------------------------

class TestNotes(unittest.TestCase):
    def test_no_lead_note(self):
        prs = _deck()
        slide = _slide(prs)
        _text(slide, "Biggest line", 1, 1, 6, 1, 60, INK, "Georgia", name="a")
        _text(slide, "Smaller line", 1, 2.5, 6, 1, 24, INK, "Calibri", name="b")
        notes = _notes(prs)
        self.assertTrue(any("no slides-lead declared" in n for n in notes), notes)
        self.assertTrue(any("Biggest line" in n for n in notes), notes)

    def test_orphan_mark_note(self):
        alone = _deck()
        slide = _slide(alone)
        _box(slide, 2, 2, 0.3, 0.3, ACCENT, name="dot")
        notes = _notes(alone)
        self.assertTrue(
            any("orphan mark 'dot'" in n for n in notes), notes)

        labelled = _deck()
        slide = _slide(labelled)
        _box(slide, 2, 2, 0.3, 0.3, ACCENT, name="dot")
        _text(slide, "Labelled", 2.5, 2, 2, 0.3, 24, INK, "Calibri",
              name="label")
        self.assertFalse(
            any("orphan mark" in n for n in _notes(labelled)), _notes(labelled))

    def test_all_paper_deck_note(self):
        report = _report(_clean_prs())
        self.assertIn(lint_pptx.DECK_NOTE_NO_GROUND, report["deck_notes"])

        grounded = _deck()
        slide = _slide(grounded)
        _box(slide, 0, 0, 5, 7.5, ACCENT, name="wash")
        self.assertEqual(_report(grounded)["deck_notes"], [])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCli(unittest.TestCase):
    def test_unreadable_exits_2(self):
        with _Deck(_clean_prs()) as deck:
            missing = os.path.join(deck.dir, "nope.pptx")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(
                    io.StringIO()):
                code = lint_pptx.main([missing, "--brand", deck.brand])
            self.assertEqual(code, 2)
            self.assertIn("error:", err.getvalue())

            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(
                    io.StringIO()):
                code = lint_pptx.main([
                    deck.path, "--brand", os.path.join(deck.dir, "nope.json")])
            self.assertEqual(code, 2)
            self.assertIn("error:", err.getvalue())

    def test_json_output(self):
        code, out = _run_main(_clean_prs(), extra=("--json",))
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertEqual(len(report["slides"]), 1)
        self.assertEqual(report["slides"][0]["elements"], 2)


if __name__ == "__main__":
    unittest.main()
