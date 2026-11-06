"""Tests for source/skills/slides/scripts/brand.py"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "source", "skills", "slides", "scripts"))

import brand as check_brand  # noqa: E402

A ="http://schemas.openxmlformats.org/drawingml/2006/main"
BRAND = {
    "fonts": {"heading": "Georgia", "body": "Georgia"},
    "colours": {"ink": "#1B1B1B", "paper": "#FFFFFF"},
}
# python-pptx's default template: theme fonts Calibri, dk1 000000, lt1 FFFFFF, accent1 4F81BD.


class CheckBrandTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.brand = os.path.join(self._dir.name, "brand.json")
        with open(self.brand, "w", encoding="utf-8") as handle:
            json.dump(BRAND, handle)
        self.deck = os.path.join(self._dir.name, "deck.pptx")
        self.prs = Presentation()
        self.slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])

    def _add_text(self, text="Hello", font="Georgia", colour="1B1B1B", slide=None):
        box = (slide or self.slide).shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        run = box.text_frame.paragraphs[0].add_run()
        run.text = text
        if font:
            run.font.name = font
        if colour:
            run.font.color.rgb = RGBColor.from_string(colour)
        return run

    def _check(self):
        self.prs.save(self.deck)
        return check_brand.check_deck(self.deck, self.brand)

    def test_clean_deck_has_nothing_off_brand(self):
        self._add_text()
        result = self._check()
        self.assertEqual(result["fonts"], {})
        self.assertEqual(result["colours"], {})

    def test_off_brand_font_named_with_its_slide(self):
        self._add_text()
        second = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self._add_text(font="Courier New", slide=second)
        self.assertEqual(self._check()["fonts"], {"Courier New": [2]})

    def test_off_brand_hex_colour_named_with_its_slide(self):
        self._add_text(colour="FF0000")
        self.assertEqual(self._check()["colours"], {"#FF0000": [1]})

    def test_scheme_colour_is_judged_by_what_it_resolves_to(self):
        run = self._add_text(colour=None)
        fill = etree.SubElement(run._r.get_or_add_rPr(), f"{{{A}}}solidFill")
        etree.SubElement(fill, f"{{{A}}}schemeClr", val="accent1")
        self.assertIn("#4F81BD", self._check()["colours"])

    def test_scheme_colour_that_resolves_to_the_brand_passes(self):
        run = self._add_text(colour=None)
        fill = etree.SubElement(run._r.get_or_add_rPr(), f"{{{A}}}solidFill")
        etree.SubElement(fill, f"{{{A}}}schemeClr", val="bg1")
        self.assertEqual(self._check()["colours"], {})

    def test_tint_of_a_brand_colour_passes(self):
        run = self._add_text(colour=None)
        fill = etree.SubElement(run._r.get_or_add_rPr(), f"{{{A}}}solidFill")
        colour = etree.SubElement(fill, f"{{{A}}}srgbClr", val="1B1B1B")
        etree.SubElement(colour, f"{{{A}}}alpha", val="50000")
        self.assertEqual(self._check()["colours"], {})

    def test_text_naming_no_font_is_judged_by_the_theme(self):
        self._add_text(font=None)
        self.assertEqual(self._check()["fonts"], {"Calibri": [1]})

    def test_theme_font_reference_is_followed(self):
        self._add_text(font="+mn-lt")
        self.assertEqual(self._check()["fonts"], {"Calibri": [1]})

    def test_chart_font_is_checked(self):
        data = CategoryChartData()
        data.categories = ["A"]
        data.add_series("S", (1,))
        frame = self.slide.shapes.add_chart(
            XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(4), Inches(3), data
        )
        frame.chart.font.name = "Arial"
        self.assertEqual(self._check()["fonts"].get("Arial"), [1])

    def test_off_brand_theme_gets_a_note_not_a_failure(self):
        self._add_text()
        result = self._check()
        self.assertEqual(len(result["notes"]), 1)
        self.assertIn("Calibri", result["notes"][0])
        self.assertEqual(result["fonts"], {})

    def test_brand_without_colours_is_refused(self):
        with open(self.brand, "w", encoding="utf-8") as handle:
            json.dump({"fonts": copy.deepcopy(BRAND["fonts"])}, handle)
        self._add_text()
        self.prs.save(self.deck)
        with self.assertRaises(ValueError):
            check_brand.check_deck(self.deck, self.brand)

    def _main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = check_brand.main(list(args))
        return code, out.getvalue()

    def test_cli_exit_codes(self):
        self._add_text()
        self.prs.save(self.deck)
        code, text = self._main("check", self.deck, "--brand", self.brand)
        self.assertEqual(code, 0)
        self.assertIn("on brand", text)

        self._add_text(font="Comic Sans MS")
        self.prs.save(self.deck)
        code, text = self._main("check", self.deck, "--brand", self.brand)
        self.assertEqual(code, 1)
        self.assertIn("font Comic Sans MS: slide 1", text)

        missing = os.path.join(self._dir.name, "missing.pptx")
        code, _ = self._main("check", missing, "--brand", self.brand)
        self.assertEqual(code, 2)

    def test_capture_keeps_every_theme_colour_and_both_fonts(self):
        self.prs.save(self.deck)
        captured = check_brand.capture_brand(self.deck)
        self.assertEqual(captured["fonts"], {"heading": "Calibri", "body": "Calibri"})
        self.assertEqual(len(captured["colours"]), 12)
        for name in ("ink", "ink2", "paper", "paper2", "accent", "accent6", "link", "link2"):
            self.assertRegex(captured["colours"][name], r"^#[0-9A-F]{6}$")

    def test_deck_built_on_its_own_theme_passes_against_its_capture(self):
        self.prs.save(self.deck)
        with open(self.brand, "w", encoding="utf-8") as handle:
            json.dump(check_brand.capture_brand(self.deck), handle)
        for slot in ("tx2", "bg2", "accent1", "accent6"):
            run = self._add_text(font=None, colour=None)
            fill = etree.SubElement(run._r.get_or_add_rPr(), f"{{{A}}}solidFill")
            etree.SubElement(fill, f"{{{A}}}schemeClr", val=slot)
        result = self._check()
        self.assertEqual(result["fonts"], {})
        self.assertEqual(result["colours"], {})
        self.assertEqual(result["notes"], [])

    def test_capture_cli_prints_json_and_refuses_a_bad_file(self):
        self.prs.save(self.deck)
        code, text = self._main("capture", self.deck)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text), check_brand.capture_brand(self.deck))

        code, _ = self._main("capture", self.brand)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
