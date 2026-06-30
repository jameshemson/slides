"""Tests for extract_brand.py — read a template's theme fonts/colours/layouts.

Stdlib unittest only. Runs the script as a subprocess (like test_render.py) and
asserts on the JSON it prints for the committed fixture template, whose theme is
the stock Office theme (Calibri; accent1 #4F81BD..accent6 #F79646; dk1/lt1 as
sysClr black/white). Until extract_brand.py exists these FAIL by design.

    python3 -m unittest tests.test_extract_brand
    python3 -m unittest discover tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")
TEMPLATE = os.path.join(FIXTURES, "sample-template.pptx")
EXTRACT_BRAND_PY = os.path.join(
    REPO_ROOT, "source", "skills", "build-deck", "scripts", "extract_brand.py"
)


class ExtractBrandTest(unittest.TestCase):
    """Happy path against the fixture's known stock-Office theme."""

    @classmethod
    def setUpClass(cls):
        cls.result = subprocess.run(
            [sys.executable, EXTRACT_BRAND_PY, TEMPLATE],
            capture_output=True, text=True,
        )

    def _data(self):
        self.assertEqual(
            self.result.returncode, 0,
            f"extract_brand exited {self.result.returncode}.\n"
            f"stdout: {self.result.stdout}\nstderr: {self.result.stderr}",
        )
        return json.loads(self.result.stdout)

    def test_exits_zero_and_has_keys(self):
        data = self._data()
        for key in ("template", "fonts", "colours", "layouts", "tokens"):
            self.assertIn(key, data)

    def test_fonts_from_fontscheme(self):
        data = self._data()
        self.assertEqual(data["fonts"].get("heading"), "Calibri")
        self.assertEqual(data["fonts"].get("body"), "Calibri")

    def test_accent_colours_from_srgbclr(self):
        data = self._data()
        self.assertEqual(data["colours"].get("accent"), "#4F81BD")   # accent1
        self.assertEqual(data["colours"].get("accent2"), "#C0504D")  # accent2

    def test_ink_paper_from_sysclr(self):
        # dk1/lt1 are sysClr with lastClr — proves the sysClr@lastClr path.
        data = self._data()
        self.assertEqual(data["colours"].get("ink"), "#000000")
        self.assertEqual(data["colours"].get("paper"), "#FFFFFF")

    def test_layouts_included(self):
        data = self._data()
        self.assertEqual(len(data["layouts"]), 11)
        names = [layout["name"] for layout in data["layouts"]]
        self.assertIn("title-content", names)

    def test_tokens_omits_grid(self):
        # extract_brand has no layout_map, so it deliberately omits the grid
        # (a meaningful grid must be measured from the brand's mapped layouts —
        # init_brand emits it; build-deck derives it at render time).
        data = self._data()
        self.assertNotIn("grid", data["tokens"])

    def test_tokens_type_scale_has_display(self):
        data = self._data()
        self.assertIn("type_scale", data["tokens"])
        self.assertIn("display", data["tokens"]["type_scale"])

    def test_tokens_colour_roles_nonempty(self):
        # The fixture has a full Office palette (accent/ink/paper), so colour_roles
        # must be populated with at least the four canonical roles.
        data = self._data()
        self.assertIn("colour_roles", data["tokens"])
        self.assertTrue(len(data["tokens"]["colour_roles"]) > 0)


class ExtractBrandErrorTest(unittest.TestCase):
    """Malformed input exits non-zero with a named error and no JSON."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-extract-error-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _run(self, path):
        return subprocess.run(
            [sys.executable, EXTRACT_BRAND_PY, path],
            capture_output=True, text=True,
        )

    def _assert_named_error(self, result, *needles):
        self.assertEqual(
            result.returncode, 1,
            f"expected exit 1; got {result.returncode}\nstderr: {result.stderr}",
        )
        msg = (result.stderr + result.stdout).lower()
        self.assertIn("error:", msg)
        self.assertEqual(result.stdout.strip(), "", "must not print JSON on error")
        for needle in needles:
            self.assertIn(needle.lower(), msg)

    def test_missing_file_is_named(self):
        missing = os.path.join(self._tmp, "nope.pptx")
        self._assert_named_error(self._run(missing), "not found", "nope.pptx")

    def test_garbage_file_is_named(self):
        bad = os.path.join(self._tmp, "bad.pptx")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("this is not a presentation")
        self._assert_named_error(self._run(bad), "could not open")


if __name__ == "__main__":
    unittest.main()
