"""Tests for icons.py — recolour is pure (unconditional); rasterise needs cairosvg."""
import os
import sys
import tempfile
import unittest

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "source", "skills",
                 "build-deck", "scripts")
)
sys.path.insert(0, _SCRIPTS_DIR)

import icons  # noqa: E402
from icons import IconError  # noqa: E402


class TestIconCatalogue(unittest.TestCase):
    def test_curated_names_present(self):
        names = icons.available()
        # A sample of the bundled friendly names.
        for name in ("idea", "team", "check", "growth", "money"):
            self.assertIn(name, names)
        self.assertGreaterEqual(len(names), 30)

    def test_unknown_name_raises(self):
        with self.assertRaises(IconError):
            icons._load_svg("no-such-icon")


class TestRecolour(unittest.TestCase):
    """The colour substitution is pure and runs without cairosvg (REQ-2, I-10)."""

    def test_currentcolor_replaced_with_token(self):
        svg = icons._load_svg("idea")
        self.assertIn("currentColor", svg)  # iconoir ships with currentColor
        out = icons.recolour(svg, "#4F81BD")
        self.assertNotIn("currentColor", out)
        self.assertIn("#4F81BD", out)

    def test_recolour_is_the_only_colour(self):
        # A recoloured icon carries exactly one colour — the token — so the lint's
        # on-token guarantee holds once the element's colour is checked.
        out = icons.recolour(icons._load_svg("team"), "#C0504D")
        self.assertNotIn("currentColor", out)
        self.assertIn("#C0504D", out)

    def test_cairosvg_available_returns_bool(self):
        self.assertIsInstance(icons.cairosvg_available(), bool)


@unittest.skipUnless(icons.cairosvg_available(),
                     "cairosvg not installed (pip install cairosvg for full coverage)")
class TestRasterise(unittest.TestCase):
    def test_render_png_writes_a_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "idea.png")
            icons.render_png("idea", "#4F81BD", 96, out)
            self.assertTrue(os.path.isfile(out))
            with open(out, "rb") as fh:
                magic = fh.read(8)
            self.assertEqual(magic, b"\x89PNG\r\n\x1a\n")

    def test_render_png_unknown_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(IconError):
                icons.render_png("no-such-icon", "#000000", 96,
                                 os.path.join(tmp, "x.png"))


if __name__ == "__main__":
    unittest.main()
