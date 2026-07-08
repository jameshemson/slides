"""Renderer tests for source/skills/build-deck/scripts/render.py.

Stdlib `unittest` only — no pytest, no third-party test deps (python-pptx is
the renderer's own runtime dependency and is imported here to inspect output).

Run from the repo root:

    python3 -m unittest tests.test_render
    python3 -m unittest discover tests

Until render.py exists these tests FAIL by design (REQ-003 Wave 0 gate): the
subprocess call returns non-zero and no .pptx is produced. They pass once
render.py turns the sample deck spec into a valid .pptx.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")
TEMPLATE = os.path.join(FIXTURES, "sample-template.pptx")
DECK_SPEC = os.path.join(FIXTURES, "sample-deck.md")
RENDER_PY = os.path.join(
    REPO_ROOT, "source", "skills", "build-deck", "scripts", "render.py"
)

# The parse-contract tests at the bottom of this file (TableParseTest,
# WaterfallParseTest) call render.py's parse functions in-process, so import it
# as a module. Its own directory carries pptxlib; put that on the path first.
# The subprocess-based tests above do not use this import; it is purely
# additive.
sys.path.insert(0, os.path.dirname(RENDER_PY))
import render  # noqa: E402

# tests/fixtures/sample-template.pptx has its layouts renamed to role names by
# generate-fixture-template.py. `quote` has no dedicated layout and shares the
# `section` layout (TITLE + BODY) — index 2.
LAYOUT_MAP = {
    "title": 0,
    "title-content": 1,
    "section": 2,
    "two-column": 3,
    "statement": 5,
    "quote": 2,
}
LAYOUT_NAME_FOR_ROLE = {
    "title": "title",
    "section": "section",
    "statement": "statement",
    "title-content": "title-content",
    "two-column": "two-column",
    "quote": "section",  # quote shares the section layout in this fixture
}

# What sample-deck.md declares, slide by slide: (role, primary-field text).
# The primary field of each role fills the slide's title placeholder.
EXPECTED_SLIDES = [
    ("title", "From status meeting to written update"),
    ("section", "Where the hour goes"),
    ("statement", "The weekly status meeting costs the team six hours every week."),
    ("title-content", "What the meeting does, and does not, do well"),
    ("two-column", "Two ways to spend the same hour"),
    ("quote", "I skip half of what I say in standup because it does not apply to most of the room."),
]


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-render-test-")
        cls.out_path = os.path.join(cls._tmp, "out.pptx")
        brand_path = os.path.join(cls._tmp, "brand.json")
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "fidelity": "template",
                    "template": TEMPLATE,
                    "fonts": {"heading": "Calibri", "body": "Calibri"},
                    "colours": {
                        "primary": "#1F3A5F",
                        "accent": "#E07A3F",
                        "ink": "#1A1A1A",
                        "paper": "#FFFFFF",
                    },
                    "layout_map": LAYOUT_MAP,
                },
                fh,
            )
        cls.result = subprocess.run(
            [
                sys.executable,
                RENDER_PY,
                "--spec", DECK_SPEC,
                "--brand", brand_path,
                "--out", cls.out_path,
            ],
            capture_output=True,
            text=True,
        )

    def _presentation(self):
        self.assertTrue(
            os.path.exists(self.out_path),
            f"render.py produced no .pptx.\nstdout: {self.result.stdout}\n"
            f"stderr: {self.result.stderr}",
        )
        return Presentation(self.out_path)

    def test_render_exits_zero(self):
        self.assertEqual(
            self.result.returncode,
            0,
            f"render.py exited {self.result.returncode}.\n"
            f"stdout: {self.result.stdout}\nstderr: {self.result.stderr}",
        )

    def test_output_reopens(self):
        # A valid .pptx that python-pptx can parse again.
        self._presentation()

    def test_slide_count_matches_spec(self):
        prs = self._presentation()
        self.assertEqual(
            len(prs.slides),
            len(EXPECTED_SLIDES),
            "slide count must equal the number of `## Slide` sections in the spec",
        )

    def test_each_slide_uses_the_mapped_layout(self):
        prs = self._presentation()
        for i, (role, _) in enumerate(EXPECTED_SLIDES):
            with self.subTest(slide=i + 1, role=role):
                self.assertEqual(
                    prs.slides[i].slide_layout.name,
                    LAYOUT_NAME_FOR_ROLE[role],
                    f"slide {i + 1} ({role}) must use the layout brand.json maps it to",
                )

    def test_primary_field_fills_the_title_placeholder(self):
        prs = self._presentation()
        for i, (role, expected) in enumerate(EXPECTED_SLIDES):
            with self.subTest(slide=i + 1, role=role):
                title = prs.slides[i].shapes.title
                self.assertIsNotNone(title, f"slide {i + 1} has no title placeholder")
                self.assertEqual(title.text.strip(), expected)

    def test_body_field_fills_a_content_placeholder(self):
        prs = self._presentation()
        # Slide 4 is the title-content slide; its Body has four bullets.
        body_text = " ".join(
            ph.text
            for ph in prs.slides[3].placeholders
            if ph.placeholder_format.idx != 0
        )
        for bullet in (
            "surfaces blockers fast",
            "no record anyone can search",
        ):
            self.assertIn(bullet, body_text)

    def test_visual_field_is_recorded_in_speaker_notes(self):
        prs = self._presentation()
        # Slide 5 carries a Visual: field; render.py records it in the notes.
        notes = prs.slides[4].notes_slide.notes_text_frame.text
        self.assertIn("VISUAL TO ADD", notes)
        self.assertIn("two-panel diagram", notes)

    def test_no_text_box_outside_template_placeholders(self):
        # The structural guarantee against an injected strapline: render.py
        # fills only the template's own placeholders and never adds a shape.
        prs = self._presentation()
        for i, slide in enumerate(prs.slides):
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame.text.strip():
                    with self.subTest(slide=i + 1, shape=shape.shape_id):
                        self.assertTrue(
                            shape.is_placeholder,
                            f"slide {i + 1} has text in a non-placeholder shape",
                        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)


class RenderErrorTest(unittest.TestCase):
    """Negative-path coverage: malformed input must exit non-zero with a
    message naming the fault, and never emit a .pptx."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-render-error-test-")

    @classmethod
    def tearDownClass(cls):
        # rmtree (not os.remove): a chart error may leave a sidecar charts dir.
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _run(self, name, spec_text, brand=None):
        """Write a spec (+ brand) and run render.py. Returns CompletedProcess."""
        if brand is None:
            brand = {
                "fidelity": "template",
                "template": TEMPLATE,
                "fonts": {"heading": "Calibri", "body": "Calibri"},
                "colours": {"ink": "#1A1A1A"},
                "layout_map": dict(LAYOUT_MAP),
            }
        spec_path = os.path.join(self._tmp, f"{name}.deck.md")
        brand_path = os.path.join(self._tmp, f"{name}.brand.json")
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec_text)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(brand, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        self.assertFalse(
            os.path.exists(out_path),
            "render.py must not emit a .pptx on malformed input",
        )
        return result

    def _assert_named_error(self, result, *needles):
        self.assertEqual(
            result.returncode, 1,
            f"expected exit 1; got {result.returncode}\nstderr: {result.stderr}",
        )
        msg = (result.stderr + result.stdout).lower()
        self.assertIn("error:", msg)
        for needle in needles:
            self.assertIn(needle.lower(), msg)

    def test_slide_number_gap_is_named(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: section\nTitle: One\n\n"
                "## Slide 3\nlayout: section\nTitle: Three\n")
        self._assert_named_error(self._run("gap", spec), "slide", "3")

    def test_unknown_role_is_named(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: splash\nTitle: One\n")
        self._assert_named_error(self._run("role", spec), "slide 1", "splash")

    def test_unrecognised_field_is_named(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: title\nTitle: Hi\n"
                "Strapline: Innovate. Accelerate. Dominate.\n")
        self._assert_named_error(self._run("field", spec), "slide 1", "strapline")

    def test_field_overflow_is_named(self):
        # two-column carries 3 fields; point it at the 1-placeholder
        # statement layout so the fill overflows.
        brand = {
            "fidelity": "template",
            "template": TEMPLATE,
            "fonts": {"heading": "Calibri", "body": "Calibri"},
            "colours": {"ink": "#1A1A1A"},
            "layout_map": {**LAYOUT_MAP, "two-column": 5},
        }
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: two-column\nTitle: T\nLeft: L\nRight: R\n")
        self._assert_named_error(
            self._run("overflow", spec, brand), "slide 1", "placeholder")

    def test_missing_brand_key_is_named(self):
        brand = {
            "fidelity": "template",
            "template": TEMPLATE,
            "fonts": {"heading": "Calibri", "body": "Calibri"},
            "colours": {"ink": "#1A1A1A"},
        }  # no layout_map
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: section\nTitle: One\n")
        self._assert_named_error(
            self._run("brandkey", spec, brand), "layout_map")

    # --- chart faults (REQ-005): every malformed Chart block fails loudly ---

    def _chart_brand(self, colours=None):
        return {
            "fidelity": "template",
            "template": TEMPLATE,
            "fonts": {"heading": "Helvetica Neue", "body": "Helvetica Neue"},
            "colours": CHART_COLOURS if colours is None else colours,
            "layout_map": dict(LAYOUT_MAP),
        }

    def _chart_spec(self, chart_block, role="title-content", title="T",
                    body="A line."):
        head = f"## Slide 1\nlayout: {role}\nTitle: {title}\n"
        if body:
            head += f"Body: {body}\n"
        return "---\ndeck: d\naudience: a\n---\n\n" + head + chart_block

    def test_chart_unknown_type_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: donut\n  categories: A, B\n  series X: 1, 2\n")
        self._assert_named_error(
            self._run("ctype", spec, self._chart_brand()), "slide 1", "donut")

    def test_chart_length_mismatch_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: column\n  categories: A, B, C\n  series X: 1, 2\n")
        self._assert_named_error(
            self._run("clen", spec, self._chart_brand()), "slide 1", "length")

    def test_chart_non_numeric_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: column\n  categories: A, B\n  series X: 1, two\n")
        self._assert_named_error(
            self._run("cnum", spec, self._chart_brand()), "slide 1", "two")

    def test_chart_unknown_emphasis_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: column\n  emphasis: Z\n"
            "  categories: A, B\n  series X: 1, 2\n")
        self._assert_named_error(
            self._run("cemph", spec, self._chart_brand()), "slide 1", "z")

    def test_chart_on_wrong_role_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: column\n  categories: A, B\n  series X: 1, 2\n",
            role="statement", body=None)
        # statement carries Statement, not Title; give it one plus the Chart.
        spec = spec.replace("Title: T\n", "Statement: S\n")
        self._assert_named_error(
            self._run("crole", spec, self._chart_brand()),
            "slide 1", "title-content")

    def test_chart_empty_colours_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: column\n  categories: A, B\n  series X: 1, 2\n")
        self._assert_named_error(
            self._run("ccol", spec, self._chart_brand(colours={})),
            "slide 1", "colour")

    def test_chart_inline_value_is_named(self):
        spec = self._chart_spec("Chart: column\n")
        self._assert_named_error(
            self._run("cinline", spec, self._chart_brand()),
            "slide 1", "block")

    def test_chart_empty_block_is_named(self):
        # A Chart: label with no body lines before end of slide.
        spec = self._chart_spec("Chart:\n")
        self._assert_named_error(
            self._run("cempty", spec, self._chart_brand()), "slide 1", "chart")

    def test_chart_marker_missing_point_is_named(self):
        spec = self._chart_spec(
            "Chart:\n  type: line\n  points: 0 10, 1 20\n  marker: 5 Late\n")
        self._assert_named_error(
            self._run("cmark", spec, self._chart_brand()), "slide 1", "marker")

    def test_chart_line_emphasis_is_named(self):
        # emphasis is meaningless on a line chart; fail loudly, not silently.
        spec = self._chart_spec(
            "Chart:\n  type: line\n  emphasis: X\n  points: 0 10, 1 20\n")
        self._assert_named_error(
            self._run("clineemph", spec, self._chart_brand()),
            "slide 1", "emphasis")

    def test_chart_pie_multi_series_is_named(self):
        # A pie shows one whole; more than one series is ambiguous.
        spec = self._chart_spec(
            "Chart:\n  type: pie\n  categories: A, B\n"
            "  series X: 1, 2\n  series Y: 3, 4\n")
        self._assert_named_error(
            self._run("cpie", spec, self._chart_brand()), "slide 1", "pie")

    def test_chart_scatter_emphasis_is_named(self):
        # scatter has no categories to emphasise; fail loudly.
        spec = self._chart_spec(
            "Chart:\n  type: scatter\n  emphasis: Z\n  points: 0 1, 1 2\n")
        self._assert_named_error(
            self._run("cscatteremph", spec, self._chart_brand()),
            "slide 1", "emphasis")


# tests/fixtures/sample-template.pptx maps title-content to layout index 1,
# whose content placeholder (idx 1) hosts the resized Body line; the chart is a
# separate picture placed below it. Distinct accent/muted colours let the pixel
# histogram prove emphasis colouring without sampling exact coordinates.
CHART_COLOURS = {
    "accent": "#2E8B6F",
    "muted": "#8AA3A0",
    "spend": "#D98E5A",
    "ink": "#1F3A34",
}
COLUMN_BLOCK = (
    "Chart:\n  type: column\n  emphasis: 2031\n"
    "  categories: 2026, 2027, 2028, 2029, 2030, 2031\n"
    "  series Balance: 76900, 34300, 37400, 21900, 24600, 27300\n"
)
BAR_BLOCK = (
    "Chart:\n  type: bar\n  emphasis: Conservatory\n"
    "  categories: Conservatory, Car, Kitchen\n  series Cost: 49, 18, 14\n"
)
LINE_BLOCK = (
    "Chart:\n  type: line\n"
    "  points: 0 76900, 12 34300, 26 19600, 60 27300\n  marker: 26 Car\n"
)
PIE_BLOCK = (
    "Chart:\n  type: pie\n  emphasis: Rent\n"
    "  categories: Rent, Food, Travel, Savings\n"
    "  series Spend: 1200, 400, 200, 300\n"
)
SCATTER_BLOCK = (
    "Chart:\n  type: scatter\n"
    "  points: 1 2, 2 4, 3 5, 4 8\n  marker: 4 Peak\n"
)


class ChartRenderTest(unittest.TestCase):
    """REQ-001..004, 009: charts render to PNG and place as a picture."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-chart-render-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _render(self, name, chart_block, brand=None, body="A line.", env=None,
                font_files=None):
        if brand is None:
            brand = {
                "fidelity": "template",
                "template": TEMPLATE,
                "fonts": {"heading": "Helvetica Neue", "body": "Helvetica Neue"},
                "colours": CHART_COLOURS,
                "layout_map": dict(LAYOUT_MAP),
            }
            if font_files is not None:
                brand["font_files"] = font_files
        head = "## Slide 1\nlayout: title-content\nTitle: T\n"
        if body:
            head += f"Body: {body}\n"
        spec = "---\ndeck: d\naudience: a\n---\n\n" + head + chart_block
        spec_path = os.path.join(self._tmp, f"{name}.deck.md")
        brand_path = os.path.join(self._tmp, f"{name}.brand.json")
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        charts_dir = os.path.join(self._tmp, f"{name}.charts")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(brand, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path,
             "--charts-dir", charts_dir],
            capture_output=True, text=True, env=env,
        )
        return result, out_path, charts_dir

    def _ok(self, result, out_path):
        self.assertEqual(
            result.returncode, 0,
            f"render failed.\nstdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertTrue(os.path.exists(out_path), "no .pptx produced")
        return Presentation(out_path)

    def _pictures(self, slide):
        return [s for s in slide.shapes
                if s.shape_type == MSO_SHAPE_TYPE.PICTURE]

    def test_chart_slide_has_one_picture(self):
        result, out, _ = self._render("col", COLUMN_BLOCK)
        prs = self._ok(result, out)
        self.assertEqual(len(self._pictures(prs.slides[0])), 1)

    def test_sidecar_png_written(self):
        result, out, charts_dir = self._render("png", COLUMN_BLOCK)
        self._ok(result, out)
        pngs = [f for f in os.listdir(charts_dir) if f.endswith(".png")]
        self.assertTrue(pngs, f"no PNG in {charts_dir}")

    def test_picture_sits_below_body_within_slide(self):
        result, out, _ = self._render("region", COLUMN_BLOCK)
        prs = self._ok(result, out)
        slide = prs.slides[0]
        pic = self._pictures(slide)[0]
        body = next(p for p in slide.placeholders
                    if p.placeholder_format.idx != 0)
        self.assertIsNotNone(pic.top)
        self.assertGreaterEqual(pic.top, body.top + body.height)
        self.assertGreaterEqual(pic.left, 0)
        self.assertLessEqual(pic.left + pic.width, prs.slide_width + 1)
        self.assertLessEqual(pic.top + pic.height, prs.slide_height + 1)

    def test_each_type_renders_a_picture(self):
        for name, block in (("t-bar", BAR_BLOCK), ("t-col", COLUMN_BLOCK),
                            ("t-line", LINE_BLOCK), ("t-pie", PIE_BLOCK),
                            ("t-scatter", SCATTER_BLOCK)):
            with self.subTest(chart=name):
                result, out, _ = self._render(name, block)
                prs = self._ok(result, out)
                self.assertEqual(len(self._pictures(prs.slides[0])), 1)

    def test_emphasis_colour_present(self):
        # Whole-image histogram: both the brand accent and the muted colour
        # must appear, proving emphasis colouring sourced from brand.json.
        from PIL import Image

        result, out, charts_dir = self._render("hist", COLUMN_BLOCK)
        self._ok(result, out)
        png = os.path.join(
            charts_dir,
            next(f for f in os.listdir(charts_dir) if f.endswith(".png")))
        img = Image.open(png).convert("RGB")
        histogram = img.getcolors(maxcolors=2 ** 24) or []

        def near(target, tol=10):
            tr, tg, tb = target
            return sum(n for n, (r, g, b) in histogram
                       if abs(r - tr) <= tol and abs(g - tg) <= tol
                       and abs(b - tb) <= tol)

        accent = (0x2E, 0x8B, 0x6F)
        muted = (0x8A, 0xA3, 0xA0)
        self.assertGreater(near(accent), 200, "brand accent not found in chart")
        self.assertGreater(near(muted), 200, "muted colour not found in chart")

    def test_missing_font_warns(self):
        result, out, _ = self._render("nofont", COLUMN_BLOCK)
        self._ok(result, out)
        self.assertIn("font", (result.stdout + result.stderr).lower())
        self.assertIn("fallback", (result.stdout + result.stderr).lower())

    def test_font_file_registered_no_warning(self):
        import matplotlib
        ttf = os.path.join(os.path.dirname(matplotlib.__file__),
                           "mpl-data", "fonts", "ttf", "DejaVuSans.ttf")
        self.assertTrue(os.path.isfile(ttf), "matplotlib DejaVuSans missing")
        result, out, _ = self._render(
            "withfont", COLUMN_BLOCK, font_files={"DejaVu Sans": ttf})
        self._ok(result, out)
        self.assertNotIn("fallback", (result.stdout + result.stderr).lower())

    def test_matplotlib_absent_falls_back_to_note(self):
        # REQ-009/D-011: hide matplotlib via a PYTHONPATH shim; the chart slide
        # falls back to a VISUAL TO ADD note and the deck still builds.
        shim = os.path.join(self._tmp, "shim")
        os.makedirs(shim, exist_ok=True)
        with open(os.path.join(shim, "matplotlib.py"), "w") as fh:
            fh.write('raise ImportError("matplotlib hidden for test")\n')
        env = dict(os.environ)
        env["PYTHONPATH"] = shim + os.pathsep + env.get("PYTHONPATH", "")
        result, out, _ = self._render("absent", COLUMN_BLOCK, env=env)
        prs = self._ok(result, out)
        slide = prs.slides[0]
        self.assertEqual(len(self._pictures(slide)), 0, "should not draw a chart")
        notes = slide.notes_slide.notes_text_frame.text
        self.assertIn("VISUAL TO ADD", notes)
        summary = (result.stdout + result.stderr).lower()
        self.assertIn("matplotlib", summary)
        self.assertIn("pip install matplotlib", summary)


# --- T-001 (Wave 0, red-first): parse contract for the `table` composed block
# and the `waterfall` chart type. Both features are unimplemented, so every case
# below fails right now for a named pre-implementation reason:
#   * a `table` block  -> SpecError "unknown composed block type 'table'"
#     (raised at the top of _parse_composed_block, before any table logic — so
#      the shape/CSV cases raise it instead of returning, and the malformed
#      cases raise it instead of their eventual table-specific message).
#   * a `waterfall` chart -> SpecError "unknown chart type 'waterfall'"
#     (raised after the _parse_chart_block key loop). The two `total:`-bearing
#     cases raise earlier, on the not-yet-recognised `total:` key -> SpecError
#     "unknown chart key 'total'"; the chart_to_note case falls through the
#     point-chart branch -> KeyError 'points'. Each is the genuine current fault.
# These assert the desired end-state behaviour; they go green when T-006 lands.


class TableParseTest(unittest.TestCase):
    """REQ-001/002/003: the `table` composed block parse contract.

    The parse branch must return, nested under a `"table"` key exactly as
    `matrix` nests under `"spec"`:

        {"type": "table",
         "table": {"header": [...],
                   "rows": [{"cells": [...], "emphasis": bool}, ...]}}
    """

    def _parse_table(self, body, files=None):
        """Write a one-slide composed spec (plus optional sidecar files) and
        parse it through the public `parse_spec` entry point, so `spec_dir` is
        threaded exactly as at runtime. Returns the parsed first block dict, or
        propagates SpecError for a malformed spec."""
        tmp = tempfile.mkdtemp(prefix="slides-table-parse-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name, content in (files or {}).items():
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write(content)
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: composed\n" + body)
        spec_path = os.path.join(tmp, "deck.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec)
        return render.parse_spec(spec_path)[0]["blocks"][0]

    def test_header_and_rows_shape(self):
        block = self._parse_table(
            "Block: table\n"
            "Name | Q1 | Q2\n"
            "Alpha | 1 | 2\n"
            "Beta | 3 | 4\n"
        )
        self.assertEqual(block["type"], "table")
        self.assertEqual(block["table"], {
            "header": ["Name", "Q1", "Q2"],
            "rows": [
                {"cells": ["Alpha", "1", "2"], "emphasis": False},
                {"cells": ["Beta", "3", "4"], "emphasis": False},
            ],
        })

    def test_emphasis_marker_sets_row_flag(self):
        block = self._parse_table(
            "Block: table\n"
            "Name | Q1\n"
            "Alpha | 1\n"
            "! Beta | 2\n"
        )
        rows = block["table"]["rows"]
        self.assertEqual(rows[0], {"cells": ["Alpha", "1"], "emphasis": False})
        self.assertEqual(rows[1], {"cells": ["Beta", "2"], "emphasis": True})

    def test_ragged_row_raises(self):
        # Row cell count != header cell count.
        with self.assertRaisesRegex(render.SpecError, r"(?i)cell|ragged"):
            self._parse_table(
                "Block: table\n"
                "Name | Q1 | Q2\n"
                "Alpha | 1\n"
            )

    def test_one_column_header_raises(self):
        # A single-column table is a list; the message points elsewhere.
        with self.assertRaisesRegex(render.SpecError, r"(?i)column"):
            self._parse_table(
                "Block: table\n"
                "OnlyOne\n"
                "Alpha\n"
            )

    def test_data_csv_loads_header_and_rows(self):
        block = self._parse_table(
            "Block: table\n"
            "data: costs.csv\n",
            files={"costs.csv": "Item,Q1,Q2\nAlpha,1,2\nBeta,3,4\n"},
        )
        self.assertEqual(block["type"], "table")
        self.assertEqual(block["table"], {
            "header": ["Item", "Q1", "Q2"],
            "rows": [
                {"cells": ["Alpha", "1", "2"], "emphasis": False},
                {"cells": ["Beta", "3", "4"], "emphasis": False},
            ],
        })

    def test_data_plus_inline_rows_raises(self):
        # `data:` and inline rows are mutually exclusive.
        with self.assertRaisesRegex(render.SpecError, r"(?i)inline|combined"):
            self._parse_table(
                "Block: table\n"
                "data: costs.csv\n"
                "Extra | 9 | 9\n",
                files={"costs.csv": "Item,Q1,Q2\nAlpha,1,2\n"},
            )

    def test_emphasis_key_marks_matching_row(self):
        block = self._parse_table(
            "Block: table\n"
            "data: costs.csv\n"
            "emphasis: Beta\n",
            files={"costs.csv": "Item,Q1\nAlpha,1\nBeta,2\n"},
        )
        rows = block["table"]["rows"]
        self.assertEqual(rows[0], {"cells": ["Alpha", "1"], "emphasis": False})
        self.assertEqual(rows[1], {"cells": ["Beta", "2"], "emphasis": True})

    def test_emphasis_key_no_match_raises(self):
        # An emphasis label matching no first cell fails, naming the label.
        with self.assertRaisesRegex(render.SpecError, r"Zeta"):
            self._parse_table(
                "Block: table\n"
                "data: costs.csv\n"
                "emphasis: Zeta\n",
                files={"costs.csv": "Item,Q1\nAlpha,1\nBeta,2\n"},
            )


class WaterfallParseTest(unittest.TestCase):
    """REQ-006/007/010: the `waterfall` chart parse contract.

    A waterfall takes `categories` plus exactly one `series` of signed deltas,
    accepts an optional `total:` (default label "Total", `none` disables it),
    and rejects `emphasis:` (the sign colouring already encodes emphasis).
    """

    def _parse_chart(self, lines, spec_dir=None):
        return render._parse_chart_block(1, lines, spec_dir)

    def test_type_accepted_with_single_series(self):
        chart = self._parse_chart([
            "type: waterfall",
            "categories: Start, Rent, Food, Save",
            "series Cash: 40, -15, -10, 25",
        ])
        self.assertEqual(chart["type"], "waterfall")
        self.assertEqual(chart["categories"], ["Start", "Rent", "Food", "Save"])
        self.assertEqual(len(chart["series"]), 1)
        self.assertEqual(chart["series"][0]["values"], [40, -15, -10, 25])

    def test_two_series_raises(self):
        with self.assertRaisesRegex(render.SpecError, r"(?i)series"):
            self._parse_chart([
                "type: waterfall",
                "categories: A, B",
                "series X: 1, 2",
                "series Y: 3, 4",
            ])

    def test_emphasis_raises(self):
        with self.assertRaisesRegex(render.SpecError, r"(?i)emphasis"):
            self._parse_chart([
                "type: waterfall",
                "emphasis: A",
                "categories: A, B",
                "series X: 1, 2",
            ])

    def test_total_defaults_to_total_label(self):
        chart = self._parse_chart([
            "type: waterfall",
            "categories: A, B, C",
            "series X: 10, -5, 20",
        ])
        self.assertEqual(chart.get("total_label"), "Total")

    def test_total_none_disables_total(self):
        chart = self._parse_chart([
            "type: waterfall",
            "categories: A, B",
            "series X: 10, -5",
            "total: none",
        ])
        self.assertIsNone(chart["total_label"])

    def test_total_on_non_waterfall_raises(self):
        with self.assertRaisesRegex(render.SpecError, r"(?i)waterfall"):
            self._parse_chart([
                "type: column",
                "categories: A, B",
                "series X: 1, 2",
                "total: 5",
            ])

    def test_data_csv_single_series(self):
        tmp = tempfile.mkdtemp(prefix="slides-waterfall-parse-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with open(os.path.join(tmp, "wf.csv"), "w", encoding="utf-8") as fh:
            fh.write("Stage,Delta\nStart,40\nRent,-15\nFood,-10\n")
        chart = self._parse_chart(
            ["type: waterfall", "data: wf.csv"], spec_dir=tmp)
        self.assertEqual(chart["type"], "waterfall")
        self.assertEqual(chart["categories"], ["Start", "Rent", "Food"])
        self.assertEqual(len(chart["series"]), 1)
        self.assertEqual(chart["series"][0]["values"], [40, -15, -10])

    def test_chart_to_note_includes_signed_deltas_and_total(self):
        chart = {
            "type": "waterfall",
            "categories": ["Start", "Rent", "Save"],
            "series": [{"name": "Cash", "values": [40, -15, 25]}],
            "emphasis": None,
            "callout": None,
            "fmt": {},
            "total_label": "Total",
        }
        note = render.chart_to_note(chart)
        self.assertIn("+40", note)
        self.assertTrue(
            "-15" in note or "−15" in note,
            f"signed negative delta missing from note: {note!r}",
        )
        self.assertIn("+25", note)
        self.assertIn("50", note)  # computed total: 40 - 15 + 25


class CategoryLineParseTest(unittest.TestCase):
    """`type: line` is dual-shaped: `points:` keeps the x-y path, while the
    category grammar (categories + one or more series) is how a line chart
    carries multiple series. `emphasis:` on a category-line names a SERIES.
    """

    def _parse_chart(self, lines, spec_dir=None):
        return render._parse_chart_block(1, lines, spec_dir)

    def test_category_line_parses_like_column(self):
        chart = self._parse_chart([
            "type: line",
            "categories: Q1, Q2, Q3",
            "series Plan: 10, 20, 30",
            "series Actual: 12, 18, 33",
        ])
        self.assertEqual(chart["type"], "line")
        self.assertEqual(chart["categories"], ["Q1", "Q2", "Q3"])
        self.assertEqual([s["name"] for s in chart["series"]],
                         ["Plan", "Actual"])
        self.assertNotIn("points", chart)

    def test_points_line_still_parses(self):
        chart = self._parse_chart(["type: line", "points: 0 10, 1 20"])
        self.assertEqual(chart["points"], [(0.0, 10.0), (1.0, 20.0)])
        self.assertNotIn("categories", chart)

    def test_both_grammars_raise(self):
        with self.assertRaisesRegex(render.SpecError, r"not both"):
            self._parse_chart([
                "type: line",
                "points: 0 10, 1 20",
                "categories: A, B",
                "series X: 1, 2",
            ])

    def test_neither_grammar_raises(self):
        with self.assertRaisesRegex(render.SpecError, r"'series', or 'points'"):
            self._parse_chart(["type: line", "callout: hi"])

    def test_emphasis_names_a_series(self):
        chart = self._parse_chart([
            "type: line",
            "categories: Q1, Q2",
            "series Plan: 10, 20",
            "series Actual: 12, 18",
            "emphasis: Actual",
        ])
        self.assertEqual(chart["emphasis"], "Actual")

    def test_emphasis_not_a_series_raises_teaching(self):
        # Q1 is a category; on a line chart emphasis must name a series.
        with self.assertRaisesRegex(render.SpecError,
                                    r"names a\s+series, not a\s+category"):
            self._parse_chart([
                "type: line",
                "categories: Q1, Q2",
                "series Plan: 10, 20",
                "emphasis: Q1",
            ])

    def test_marker_on_category_line_raises(self):
        with self.assertRaisesRegex(render.SpecError, r"marker"):
            self._parse_chart([
                "type: line",
                "categories: Q1, Q2",
                "series Plan: 10, 20",
                "marker: 1 Late",
            ])

    def test_series_length_mismatch_raises(self):
        with self.assertRaisesRegex(render.SpecError, r"length mismatch"):
            self._parse_chart([
                "type: line",
                "categories: Q1, Q2, Q3",
                "series Plan: 10, 20",
            ])

    def test_csv_three_columns_reads_as_series(self):
        tmp = tempfile.mkdtemp(prefix="slides-catline-parse-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with open(os.path.join(tmp, "trend.csv"), "w", encoding="utf-8") as fh:
            fh.write("Quarter,Plan,Actual\nQ1,10,12\nQ2,20,18\n")
        chart = self._parse_chart(["type: line", "data: trend.csv"],
                                  spec_dir=tmp)
        self.assertEqual(chart["categories"], ["Q1", "Q2"])
        self.assertEqual([s["name"] for s in chart["series"]],
                         ["Plan", "Actual"])

    def test_csv_text_first_column_reads_as_series(self):
        # Two columns, but a non-numeric first column is category labels.
        tmp = tempfile.mkdtemp(prefix="slides-catline-parse-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with open(os.path.join(tmp, "trend.csv"), "w", encoding="utf-8") as fh:
            fh.write("Quarter,Plan\nQ1,10\nQ2,20\n")
        chart = self._parse_chart(["type: line", "data: trend.csv"],
                                  spec_dir=tmp)
        self.assertEqual(chart["categories"], ["Q1", "Q2"])
        self.assertEqual(len(chart["series"]), 1)

    def test_csv_two_numeric_columns_stay_points(self):
        # Back-compat pin: an x,y CSV keeps the point shape.
        tmp = tempfile.mkdtemp(prefix="slides-catline-parse-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        with open(os.path.join(tmp, "xy.csv"), "w", encoding="utf-8") as fh:
            fh.write("x,y\n0,10\n1,20\n")
        chart = self._parse_chart(["type: line", "data: xy.csv"],
                                  spec_dir=tmp)
        self.assertEqual(chart["points"], [(0.0, 10.0), (1.0, 20.0)])
        self.assertNotIn("categories", chart)

    def test_chart_to_note_handles_category_line(self):
        # The matplotlib-absent note must not KeyError on a category-line.
        chart = self._parse_chart([
            "type: line",
            "categories: Q1, Q2",
            "series Plan: 10, 20",
            "series Actual: 12, 18",
        ])
        note = render.chart_to_note(chart)
        self.assertIn("Line chart", note)
        self.assertIn("Plan", note)
        self.assertIn("Actual", note)


# --- T-001 (Wave 0, red-first), continued: native-charts-plan.md REQ-001,
# REQ-003, REQ-004, REQ-005, REQ-006; decisions D-001, D-005, D-009.
#
# `native:`, `stacked:`, and `target:` are not yet recognised chart keys, so
# every line carrying one of them raises SpecError "unknown chart key
# '<key>'" the moment `_parse_chart_block`'s key loop reaches it — the
# genuine current fault, regardless of what other keys/lines surround it.
# Positive-path cases below (no key mismatch to check) are left uncaught and
# so simply error out on that same SpecError right now. Cross-validation
# cases assert the *desired* end-state wording (naming bar/column, 'series',
# 'emphasis', or the allowed point-chart types) — text the current "unknown
# chart key" message does not contain, so these fail red as assertion
# mismatches, not as accidental passes. Both go green once T-006 lands.


class NativeChartParseTest(unittest.TestCase):
    """REQ-001/D-001: the `native:` chart key parse contract.

    Pinned shape: `chart["native"]` is always present as a bool (key present
    even when the spec never mentions `native:` — default False), set from
    `true`/`false` (case-insensitive); anything else is a SpecError naming
    'native'.
    """

    def _parse_chart(self, lines, spec_dir=None):
        return render._parse_chart_block(1, lines, spec_dir)

    def test_native_true_parses_true(self):
        chart = self._parse_chart([
            "type: column",
            "categories: A, B",
            "series X: 1, 2",
            "native: true",
        ])
        self.assertIs(chart["native"], True)

    def test_native_false_parses_false(self):
        chart = self._parse_chart([
            "type: column",
            "categories: A, B",
            "series X: 1, 2",
            "native: false",
        ])
        self.assertIs(chart["native"], False)

    def test_native_absent_defaults_false(self):
        # No `native:` line at all — the key must still be present (pinned
        # shape: key always present, boolean), not merely absent-equivalent.
        chart = self._parse_chart([
            "type: column",
            "categories: A, B",
            "series X: 1, 2",
        ])
        self.assertIn("native", chart)
        self.assertIs(chart["native"], False)

    def test_native_invalid_value_raises(self):
        # Strengthened past a bare 'native' substring check (today's "unknown
        # chart key 'native'" message would already satisfy that trivially,
        # coincidentally passing before implementation) by also requiring the
        # bad token 'maybe' appear, so this is genuinely red right now.
        with self.assertRaises(render.SpecError) as cm:
            self._parse_chart([
                "type: column",
                "categories: A, B",
                "series X: 1, 2",
                "native: maybe",
            ])
        msg = str(cm.exception).lower()
        self.assertIn("native", msg)
        self.assertIn("maybe", msg)


class StackedTargetParseTest(unittest.TestCase):
    """REQ-004/005, D-009: the `stacked:` and `target:` chart key parse
    contract.

    Pinned shapes:
      chart["stacked"] -> bool, legal only on multi-series bar/column.
      chart["target"]  -> {"value": float, "label": str|None}, legal only on
                           column/bar/line (D-009's optional '| label').
    """

    def _parse_chart(self, lines, spec_dir=None):
        return render._parse_chart_block(1, lines, spec_dir)

    def _assert_chart_error(self, lines, *needles, spec_dir=None):
        with self.assertRaises(render.SpecError) as cm:
            self._parse_chart(lines, spec_dir=spec_dir)
        msg = str(cm.exception).lower()
        for needle in needles:
            self.assertIn(needle.lower(), msg)

    # --- stacked ---

    def test_stacked_true_two_series_column(self):
        chart = self._parse_chart([
            "type: column",
            "categories: A, B",
            "series X: 1, 2",
            "series Y: 3, 4",
            "stacked: true",
        ])
        self.assertIs(chart["stacked"], True)

    def test_stacked_on_pie_raises_naming_bar_column(self):
        self._assert_chart_error(
            ["type: pie", "categories: A, B", "series X: 1, 2",
             "stacked: true"],
            "bar", "column",
        )

    def test_stacked_single_series_raises(self):
        self._assert_chart_error(
            ["type: column", "categories: A, B", "series X: 1, 2",
             "stacked: true"],
            "series",
        )

    def test_stacked_with_emphasis_raises(self):
        self._assert_chart_error(
            ["type: column", "emphasis: A", "categories: A, B",
             "series X: 1, 2", "series Y: 3, 4", "stacked: true"],
            "emphasis",
        )

    # --- target ---

    def test_target_value_only(self):
        chart = self._parse_chart([
            "type: column",
            "categories: A, B",
            "series X: 1, 2",
            "target: 50",
        ])
        self.assertEqual(chart["target"], {"value": 50.0, "label": None})

    def test_target_with_label(self):
        chart = self._parse_chart([
            "type: column",
            "categories: A, B",
            "series X: 1, 2",
            "target: 50 | goal",
        ])
        self.assertEqual(chart["target"], {"value": 50.0, "label": "goal"})

    def test_target_non_numeric_raises(self):
        # Strengthened past a bare 'target' substring check (same rationale
        # as test_native_invalid_value_raises) by requiring the bad token.
        with self.assertRaises(render.SpecError) as cm:
            self._parse_chart([
                "type: column", "categories: A, B", "series X: 1, 2",
                "target: abc",
            ])
        self.assertIn("abc", str(cm.exception).lower())

    def test_target_on_scatter_raises_naming_allowed_types(self):
        self._assert_chart_error(
            ["type: scatter", "points: 0 1, 1 2", "target: 50"],
            "column", "bar", "line",
        )


class ComposedChartBlockTest(unittest.TestCase):
    """REQ-006: `Block: chart` on a composed slide reuses `_parse_chart_block`'s
    grammar (including `data:` CSV, resolved against spec_dir), nested under a
    `"chart"` key exactly as `table` nests under `"table"`:

        {"type": "chart", "chart": {<same dict _parse_chart_block returns>}}

    `chart` is not yet in COMPOSED_BLOCK_TYPES, so every case below raises
    SpecError "unknown composed block type 'chart'" right now — the genuine
    current fault, raised at the top of _parse_composed_block before any
    chart-specific logic runs (so the CSV case fails the same way as the
    inline case). These assert the desired end-state; they go green once
    T-006 adds 'chart' to COMPOSED_BLOCK_TYPES and delegates to
    _parse_chart_block(items, spec_dir).
    """

    def _parse_composed(self, body, files=None):
        tmp = tempfile.mkdtemp(prefix="slides-composed-chart-parse-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for name, content in (files or {}).items():
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                fh.write(content)
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                "## Slide 1\nlayout: composed\n" + body)
        spec_path = os.path.join(tmp, "deck.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec)
        return render.parse_spec(spec_path)[0]["blocks"][0]

    def test_chart_block_parses_inline(self):
        block = self._parse_composed(
            "Block: chart\n"
            "type: column\n"
            "categories: A, B\n"
            "series X: 1, 2\n"
        )
        self.assertEqual(block["type"], "chart")
        chart = block["chart"]
        self.assertEqual(chart["type"], "column")
        self.assertEqual(chart["categories"], ["A", "B"])
        self.assertEqual(len(chart["series"]), 1)
        self.assertEqual(chart["series"][0]["name"], "X")
        self.assertEqual(chart["series"][0]["values"], [1, 2])

    def test_chart_block_data_csv_resolves_against_spec_dir(self):
        block = self._parse_composed(
            "Block: chart\n"
            "type: column\n"
            "data: sales.csv\n",
            files={"sales.csv": "Category,X\nA,1\nB,2\n"},
        )
        self.assertEqual(block["type"], "chart")
        chart = block["chart"]
        self.assertEqual(chart["type"], "column")
        self.assertEqual(chart["categories"], ["A", "B"])
        self.assertEqual(chart["series"][0]["values"], [1, 2])


class LineageStampTest(unittest.TestCase):
    """REQ-001 / D-003: `build_deck` must stamp every rendered .pptx's
    `core_properties.comments` with `slides-spec: <basename> sha256:<hash>`,
    so a deck names the spec it came from. render.py does not yet touch
    core_properties — these tests are pinned to fail red until T-004 adds
    the stamp before `prs.save`.

    tests/fixtures/sample-deck.md (reused, byte-for-byte, from RenderTest's
    fixtures) is not itself named `<deck>.deck.md` per deck-spec.md's
    documented convention, so its content is copied into this test's own
    tmpdir under a conforming name before rendering — the stamp regex below
    requires a literal `.deck.md` suffix, and the fixture file is left
    untouched either way.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-lineage-test-")
        with open(DECK_SPEC, "rb") as fh:
            spec_bytes = fh.read()
        cls.spec_path = os.path.join(cls._tmp, "sample.deck.md")
        with open(cls.spec_path, "wb") as fh:
            fh.write(spec_bytes)
        cls.brand_path = os.path.join(cls._tmp, "brand.json")
        with open(cls.brand_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "fidelity": "template",
                    "template": TEMPLATE,
                    "fonts": {"heading": "Calibri", "body": "Calibri"},
                    "colours": {
                        "primary": "#1F3A5F",
                        "accent": "#E07A3F",
                        "ink": "#1A1A1A",
                        "paper": "#FFFFFF",
                    },
                    "layout_map": LAYOUT_MAP,
                },
                fh,
            )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _render(self, name):
        """Run render.py against the conforming-named spec copy into a fresh
        output path. Returns the reopened Presentation."""
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        result = subprocess.run(
            [
                sys.executable,
                RENDER_PY,
                "--spec", self.spec_path,
                "--brand", self.brand_path,
                "--out", out_path,
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"render.py exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertTrue(
            os.path.exists(out_path), "render.py produced no .pptx"
        )
        return Presentation(out_path)

    def test_stamp_matches_basename_and_spec_sha256(self):
        stamp_re = re.compile(
            r"^slides-spec: (?P<basename>.+\.deck\.md) "
            r"sha256:(?P<sha>[0-9a-f]{64})$"
        )
        prs = self._render("stamped")
        comments = prs.core_properties.comments
        match = stamp_re.match(comments)
        self.assertIsNotNone(
            match,
            f"core_properties.comments {comments!r} does not match "
            f"{stamp_re.pattern!r}",
        )
        self.assertEqual(
            match.group("basename"),
            os.path.basename(self.spec_path),
            "the stamped basename must equal the spec file's own basename",
        )
        with open(self.spec_path, "rb") as fh:
            expected_sha = hashlib.sha256(fh.read()).hexdigest()
        self.assertEqual(
            match.group("sha"),
            expected_sha,
            "the stamped sha256 must equal hashlib.sha256 of the spec "
            "file's bytes",
        )

    def test_stamp_is_deterministic_across_renders(self):
        prs_a = self._render("run-a")
        prs_b = self._render("run-b")
        self.assertEqual(
            prs_a.core_properties.comments,
            prs_b.core_properties.comments,
            "two renders of the same spec must produce the same lineage "
            "stamp",
        )


class LoadBrandFidelityTest(unittest.TestCase):
    """load_brand per fidelity mode (identity-not-layout REQ-002): brand
    fidelity requires identity only; template fidelity keeps the four keys."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="slides-brand-fidelity-test-")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _write(self, brand):
        path = os.path.join(self._tmp, "brand.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(brand, fh)
        return path

    IDENTITY = {
        "fonts": {"heading": "Calibri", "body": "Calibri"},
        "colours": {"ink": "#1A1A1A"},
    }

    def test_brand_fidelity_needs_identity_only(self):
        brand = render.load_brand(
            self._write({"fidelity": "brand", **self.IDENTITY}))
        self.assertNotIn("template", brand)
        self.assertNotIn("layout_map", brand)

    def test_brand_fidelity_missing_fonts_is_named(self):
        with self.assertRaises(render.SpecError) as ctx:
            render.load_brand(self._write(
                {"fidelity": "brand", "colours": {"ink": "#1A1A1A"}}))
        self.assertIn("fonts", str(ctx.exception))

    def test_brand_fidelity_still_resolves_relative_template(self):
        # A brand-fidelity profile may carry a template (the identity
        # source); when present its path is normalised exactly as before.
        rel = os.path.relpath(TEMPLATE, self._tmp)
        brand = render.load_brand(self._write(
            {"fidelity": "brand", "template": rel, **self.IDENTITY}))
        self.assertTrue(os.path.isabs(brand["template"]))
        self.assertTrue(os.path.isfile(brand["template"]))

    def test_brand_fidelity_still_validates_layout_map_shape(self):
        with self.assertRaises(render.SpecError) as ctx:
            render.load_brand(self._write(
                {"fidelity": "brand", "layout_map": {"title": "zero"},
                 **self.IDENTITY}))
        self.assertIn("layout_map", str(ctx.exception))

    def test_template_fidelity_missing_layout_map_is_named(self):
        with self.assertRaises(render.SpecError) as ctx:
            render.load_brand(self._write(
                {"fidelity": "template", "template": TEMPLATE,
                 **self.IDENTITY}))
        self.assertIn("layout_map", str(ctx.exception))

    def test_bad_fidelity_value_is_named(self):
        with self.assertRaises(render.SpecError) as ctx:
            render.load_brand(self._write(
                {"fidelity": "faithful", **self.IDENTITY}))
        self.assertIn("faithful", str(ctx.exception))


# --- brand fidelity (identity-not-layout, T-302) -----------------------------
#
# The identity-only brand profile the brand-fidelity suites below share:
# deliberately NO `template` and NO `layout_map` — REQ-002/REQ-006's
# acceptance shape (identity is all brand fidelity needs). The hostile
# fixture is generate-hostile-template.py's output: body == title (28pt) in
# the master, a decorative accent bar on layouts 0-3, cramped placeholders —
# the template-quality faults brand fidelity must be immune to (REQ-012).
BRAND_IDENTITY = {
    "fidelity": "brand",
    "fonts": {"heading": "Calibri", "body": "Calibri"},
    "colours": {
        "ink": "#1A1A1A",
        "paper": "#FFFFFF",
        "accent": "#0B5FFF",
        "muted": "#6B7280",
    },
}
HOSTILE_TEMPLATE = os.path.join(FIXTURES, "hostile-template.pptx")
# The pack "presented" ladder steps the assertions below pin (tokens.py
# PACK_TYPE_SCALES; sample-deck.md's register is "presented").
PACK_H1_PT = 40.0
PACK_BODY_PT = 24.0


class BrandModeRenderTest(unittest.TestCase):
    """The brand-fidelity render path (identity-not-layout REQ-004/005/007):
    the sample deck drawn on a clean 16:9 paper canvas from identity alone —
    no template opened, every role drawn, stamped, and hierarchy-safe."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-brand-render-test-")
        cls.out_path = os.path.join(cls._tmp, "out.pptx")
        brand_path = os.path.join(cls._tmp, "brand.json")
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(BRAND_IDENTITY, fh)
        cls.result = subprocess.run(
            [
                sys.executable,
                RENDER_PY,
                "--spec", DECK_SPEC,
                "--brand", brand_path,
                "--out", cls.out_path,
            ],
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _presentation(self):
        self.assertTrue(
            os.path.exists(self.out_path),
            f"render.py produced no .pptx.\nstdout: {self.result.stdout}\n"
            f"stderr: {self.result.stderr}",
        )
        return Presentation(self.out_path)

    def test_render_exits_zero_and_writes_file(self):
        self.assertEqual(
            self.result.returncode,
            0,
            f"render.py exited {self.result.returncode}.\n"
            f"stdout: {self.result.stdout}\nstderr: {self.result.stderr}",
        )
        self.assertTrue(os.path.exists(self.out_path))

    def test_every_slide_has_zero_placeholders(self):
        # Brand fidelity strips EVERY inherited placeholder — furniture
        # included; everything shown is drawn.
        prs = self._presentation()
        for i, slide in enumerate(prs.slides):
            with self.subTest(slide=i + 1):
                self.assertEqual(len(slide.placeholders), 0)

    def test_every_slide_paints_paper_background(self):
        # REQ-005: a slide-level <p:bg> solid fill in the paper colour.
        prs = self._presentation()
        for i, slide in enumerate(prs.slides):
            xml = slide._element.xml
            with self.subTest(slide=i + 1):
                self.assertIn("<p:bg", xml)
                self.assertIn("FFFFFF", xml)

    def test_slides_carry_role_stamps(self):
        # The revise round trip reads roles back from slide.name.
        prs = self._presentation()
        for i, (role, _) in enumerate(EXPECTED_SLIDES):
            with self.subTest(slide=i + 1, role=role):
                self.assertEqual(prs.slides[i].name, f"slides-role:{role}")

    def test_every_slide_carries_field_stamps(self):
        prs = self._presentation()
        for i, slide in enumerate(prs.slides):
            stamped = [
                s for s in slide.shapes
                if (s.name or "").startswith("slides-field:")
            ]
            with self.subTest(slide=i + 1):
                self.assertTrue(
                    stamped,
                    f"slide {i + 1} has no shape named 'slides-field:*'",
                )

    def test_title_content_hierarchy_reads(self):
        # Slide 4 is the title-content slide: every Body run must sit
        # strictly under the Title run on the pack ladder (h1 40 / body 24).
        prs = self._presentation()
        slide = prs.slides[3]
        titles = [s for s in slide.shapes if s.name == "slides-field:Title"]
        bodies = [s for s in slide.shapes if s.name == "slides-field:Body"]
        self.assertEqual(len(titles), 1)
        self.assertTrue(bodies, "no slides-field:Body shapes drawn")
        title_sizes = {
            run.font.size.pt
            for para in titles[0].text_frame.paragraphs
            for run in para.runs
        }
        self.assertEqual(title_sizes, {PACK_H1_PT})
        for shape in bodies:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    self.assertEqual(run.font.size.pt, PACK_BODY_PT)
                    self.assertLess(run.font.size.pt, PACK_H1_PT)

    def test_summary_names_brand_fidelity(self):
        self.assertIn("fidelity: brand", self.result.stdout)

    def test_canvas_is_16_9(self):
        # The in-process base deck is widescreen regardless of what
        # python-pptx's bundled default package ships (D-305).
        prs = self._presentation()
        self.assertEqual(prs.slide_width, 12192000)

    def test_theme_fonts_carry_brand_identity(self):
        # Identity from brand.json reaches the theme: the deck's major and
        # minor Latin typefaces are the brand fonts, read back through the
        # same theme-XML path pptxlib.apply_theme writes.
        import pptxlib  # noqa: PLC0415 — scripts dir is on sys.path above

        prs = self._presentation()
        fonts = pptxlib.read_theme(prs).get("fonts", {})
        self.assertEqual(fonts.get("heading"), "Calibri")
        self.assertEqual(fonts.get("body"), "Calibri")

    def test_visual_field_is_recorded_in_speaker_notes(self):
        # Slide 5 carries a Visual: field; the brand path records it in the
        # notes exactly as template fill does.
        prs = self._presentation()
        notes = prs.slides[4].notes_slide.notes_text_frame.text
        self.assertIn("VISUAL TO ADD:", notes)
        self.assertIn("two-panel diagram", notes)


class TemplatelessBrandTest(unittest.TestCase):
    """REQ-006 acceptance (review-2 finding 3): an identity-only profile —
    no template, no layout_map — renders end to end in brand fidelity, while
    the SAME profile in template fidelity exits 1 naming the missing
    'template' key. The two modes genuinely differ."""

    MINIMAL_SPEC = ("---\ndeck: d\naudience: a\n---\n\n"
                    "## Slide 1\nlayout: section\nTitle: One\n")

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="slides-templateless-test-")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _render(self, brand, name):
        spec_path = os.path.join(self._tmp, f"{name}.deck.md")
        brand_path = os.path.join(self._tmp, f"{name}.brand.json")
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(self.MINIMAL_SPEC)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(brand, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        return result, out_path

    def test_identity_only_profile_renders_end_to_end(self):
        result, out_path = self._render(dict(BRAND_IDENTITY), "brandok")
        self.assertEqual(
            result.returncode, 0,
            f"identity-only brand-fidelity render failed.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertTrue(os.path.exists(out_path))
        # Reopens as a valid one-slide deck.
        self.assertEqual(len(Presentation(out_path).slides), 1)

    def test_same_profile_in_template_fidelity_fails_naming_template(self):
        brand = dict(BRAND_IDENTITY)
        brand["fidelity"] = "template"
        result, out_path = self._render(brand, "templatemode")
        self.assertEqual(
            result.returncode, 1,
            f"expected exit 1; got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertIn("template", (result.stderr + result.stdout).lower())
        self.assertFalse(
            os.path.exists(out_path),
            "render.py must not emit a .pptx when the template is missing",
        )


class TwoMassiveBulletsTest(unittest.TestCase):
    """THE identity-not-layout regression: an assertion title over two long
    body bullets. Brand fidelity draws the pack ladder — every body run
    strictly smaller than the title run. Template fidelity against the
    hostile fixture reproduces its body == title flatness verbatim and only
    warns (the REQ-008 tripwire); against the sample fixture the tripwire
    stays silent."""

    BULLETS = [
        "The meeting spends one full hour of six people's attention every "
        "single week whether the agenda is heavy or nearly empty, and the "
        "slowest item always sets the pace for everyone in the room",
        "A written update takes each person about ten minutes at a moment "
        "they choose, leaves a searchable record for the whole team, and "
        "surfaces blockers in a thread that anyone can answer",
    ]
    SPEC = (
        "---\ndeck: d\naudience: a\n---\n\n"
        "## Slide 1\nlayout: title-content\n"
        "Title: Quarterly business review\n"
        "Body:\n"
        + "".join(f"- {b}\n" for b in BULLETS)
    )

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="slides-massive-bullets-test-")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _render(self, brand, name):
        spec_path = os.path.join(self._tmp, f"{name}.deck.md")
        brand_path = os.path.join(self._tmp, f"{name}.brand.json")
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(self.SPEC)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(brand, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        return result, out_path

    def _template_brand(self, template):
        return {
            "fidelity": "template",
            "template": template,
            "fonts": {"heading": "Calibri", "body": "Calibri"},
            "colours": dict(BRAND_IDENTITY["colours"]),
            "layout_map": dict(LAYOUT_MAP),
        }

    def test_brand_mode_body_sits_strictly_under_the_title(self):
        result, out_path = self._render(dict(BRAND_IDENTITY), "brand")
        self.assertEqual(
            result.returncode, 0,
            f"brand-fidelity render failed.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        slide = Presentation(out_path).slides[0]
        titles = [s for s in slide.shapes if s.name == "slides-field:Title"]
        bodies = [s for s in slide.shapes if s.name == "slides-field:Body"]
        self.assertEqual(len(titles), 1, "expected one slides-field:Title")
        self.assertEqual(len(bodies), 2, "expected one shape per bullet")
        title_sizes = {
            run.font.size.pt
            for para in titles[0].text_frame.paragraphs
            for run in para.runs
        }
        self.assertEqual(title_sizes, {PACK_H1_PT})
        for shape in bodies:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    self.assertEqual(run.font.size.pt, PACK_BODY_PT)
                    self.assertLess(
                        run.font.size.pt, PACK_H1_PT,
                        "a body run is not strictly smaller than the title",
                    )

    def test_hostile_template_mode_renders_flat_and_trips_the_wire(self):
        # The old world: placeholder fill copies the hostile master's
        # body == title (28pt each) flatness verbatim; the render still
        # exits 0, and the only defence is the non-blocking summary note.
        result, out_path = self._render(
            self._template_brand(HOSTILE_TEMPLATE), "hostile")
        self.assertEqual(
            result.returncode, 0,
            f"hostile template-fidelity render failed.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertTrue(os.path.exists(out_path))
        self.assertIn("hierarchy will not read", result.stdout)

    def test_sample_template_mode_stays_tripwire_silent(self):
        # A healthy master (title 44 / body 32) must not trip the wire.
        result, _ = self._render(self._template_brand(TEMPLATE), "sample")
        self.assertEqual(
            result.returncode, 0,
            f"sample template-fidelity render failed.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertNotIn("hierarchy will not read", result.stdout)


class BrandStepDownNoteTest(unittest.TestCase):
    """D-310: brand-fidelity lead text that cannot land at its first ladder
    step draws one step down AND the run summary owns up to it."""

    def test_long_statement_notes_the_step_down(self):
        tmp = tempfile.mkdtemp(prefix="slides-stepdown-test-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        statement = (
            "The weekly status meeting quietly costs this team six full hours."
        )
        spec = ("---\ndeck: d\naudience: a\n---\n\n"
                f"## Slide 1\nlayout: statement\nStatement: {statement}\n")
        spec_path = os.path.join(tmp, "deck.md")
        brand_path = os.path.join(tmp, "brand.json")
        out_path = os.path.join(tmp, "out.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(BRAND_IDENTITY, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"render failed.\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}",
        )
        self.assertIn(
            "statement text stepped down to fit the band", result.stdout)


class ParseFrontmatterTest(unittest.TestCase):
    """parse_frontmatter: the spec's register reaches the renderer (REQ-003)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="slides-frontmatter-test-")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _write(self, text):
        path = os.path.join(self._tmp, "spec.deck.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_reads_register(self):
        meta = render.parse_frontmatter(self._write(
            "---\ndeck: d\naudience: a\nregister: presented live\n---\n\n"
            "## Slide 1\nlayout: section\nTitle: One\n"))
        self.assertEqual(meta["register"], "presented live")
        self.assertEqual(meta["deck"], "d")

    def test_keys_lowercased_and_colonless_lines_ignored(self):
        meta = render.parse_frontmatter(self._write(
            "---\nRegister: read\njust a stray line\n---\n\n## Slide 1\n"
            "layout: section\nTitle: One\n"))
        self.assertEqual(meta, {"register": "read"})

    def test_no_frontmatter_yields_empty(self):
        meta = render.parse_frontmatter(self._write(
            "## Slide 1\nlayout: section\nTitle: One\n"))
        self.assertEqual(meta, {})

    def test_missing_file_is_named(self):
        with self.assertRaises(render.SpecError):
            render.parse_frontmatter(os.path.join(self._tmp, "absent.md"))

    def test_unclosed_block_is_named(self):
        with self.assertRaises(render.SpecError) as ctx:
            render.parse_frontmatter(self._write("---\ndeck: d\n"))
        self.assertIn("frontmatter", str(ctx.exception))


# --- T-801 (REQ-204/D-404/D-409): percent placement + full-bleed -------------
#
# Freeform elements (and blocks) accept fine-grained percent bounds
# (`x A%-B%` / `y A%-B%`, exact band fractions, no insets) so the model can
# hand-draw data-accurate graphics; a box/panel may sit `at full-bleed`
# (the whole slide, margins included — the lint carves it out).


class PercentPlacementParseTest(unittest.TestCase):
    """_parse_placement: the `x A%-B%` / `y A%-B%` grammar (REQ-204)."""

    def _err(self, text, *needles):
        with self.assertRaises(render.SpecError) as cm:
            render._parse_placement(1, text)
        msg = str(cm.exception)
        for needle in needles:
            self.assertIn(needle, msg)

    def test_single_axis_x(self):
        self.assertEqual(
            render._parse_placement(1, "x 10%-60%"),
            {"cols": None, "rows": None, "x": (0.10, 0.60), "y": None},
        )

    def test_single_axis_y(self):
        self.assertEqual(
            render._parse_placement(1, "y 30%-40%"),
            {"cols": None, "rows": None, "x": None, "y": (0.30, 0.40)},
        )

    def test_both_axes(self):
        self.assertEqual(
            render._parse_placement(1, "x 20%-65% y 18%-26%"),
            {"cols": None, "rows": None, "x": (0.20, 0.65), "y": (0.18, 0.26)},
        )

    def test_decimals(self):
        self.assertEqual(
            render._parse_placement(1, "x 12.5%-63.75%"),
            {"cols": None, "rows": None, "x": (0.125, 0.6375), "y": None},
        )

    def test_full_span_bounds(self):
        self.assertEqual(
            render._parse_placement(1, "x 0%-100%")["x"], (0.0, 1.0))

    def test_equal_bounds_named_quoting_token(self):
        self._err("x 40%-40%", "x 40%-40%", "start < end")

    def test_inverted_bounds_named_quoting_token(self):
        self._err("x 60%-20%", "x 60%-20%", "start < end")

    def test_over_100_named_quoting_token(self):
        self._err("y 20%-120%", "y 20%-120%", "0-100")

    def test_mixed_grammar_named(self):
        self._err("cols 1-6 x 20%-40%",
                  "mix cols/rows with x%/y% — pick one grammar per placement")
        self._err("rows 2-5 y 10%-30%", "pick one grammar per placement")

    def test_percent_signs_required(self):
        # Without the % signs neither grammar matches — the generic
        # could-not-read error names the text.
        with self.assertRaises(render.SpecError) as cm:
            render._parse_placement(1, "x 20-65")
        self.assertIn("could not read placement", str(cm.exception))

    def test_grid_grammar_untouched(self):
        # Existing placements keep parsing; the dict simply gains x/y keys.
        self.assertEqual(
            render._parse_placement(1, "cols 1-6"),
            {"cols": (1, 6), "rows": None, "x": None, "y": None},
        )
        self.assertEqual(
            render._parse_placement(1, "left"),
            {"cols": (1, 6), "rows": None, "x": None, "y": None},
        )


class PercentPlaceRegionTest(unittest.TestCase):
    """_place_region: percent placements resolve fractionally against the
    band — EXACT, no insets (D-409: the author owns the geometry). Grid
    placements keep their breathing insets."""

    BAND = (1000000, 2000000, 8000000, 6000000)
    TOKENS = {"grid": {"columns": 12, "gutter": 152400, "baseline": 91211}}

    def _place(self, **axes):
        placement = {"cols": None, "rows": None, "x": None, "y": None}
        placement.update(axes)
        return render._place_region(self.BAND, placement, self.TOKENS)

    def test_x_only_exact_full_band_vertically(self):
        self.assertEqual(
            self._place(x=(0.10, 0.60)),
            (1800000, 2000000, 4000000, 6000000),
        )

    def test_y_only_exact_full_band_horizontally(self):
        self.assertEqual(
            self._place(y=(0.25, 0.50)),
            (1000000, 3500000, 8000000, 1500000),
        )

    def test_both_axes_exact(self):
        self.assertEqual(
            self._place(x=(0.10, 0.60), y=(0.25, 0.50)),
            (1800000, 3500000, 4000000, 1500000),
        )

    def test_decimal_fractions_round_to_emu(self):
        self.assertEqual(
            self._place(x=(0.125, 0.6375)),
            (2000000, 2000000, 4100000, 6000000),
        )

    def test_grid_placement_keeps_insets(self):
        # The existing behaviour pin: cols placements still get the gutter/
        # baseline breathing inset percent placements do without.
        left, top, w, h = render._place_region(
            self.BAND, {"cols": (1, 6), "rows": None, "x": None, "y": None},
            self.TOKENS)
        self.assertEqual((left, top), (1000000 + 76200, 2000000 + 91211))
        self.assertEqual(w, 4000000 - 152400)
        self.assertEqual(h, 6000000 - 2 * 91211)


class FullBleedParseTest(unittest.TestCase):
    """`at full-bleed` parses only on freeform box/panel elements; anything
    else — other kinds, blocks — fails with a named SpecError."""

    def test_box_parses_with_flag(self):
        el = render._parse_freeform_element(1, "box accent at full-bleed")
        self.assertEqual(el["kind"], "box")
        self.assertTrue(el["full_bleed"])
        self.assertIsNone(el["placement"])
        self.assertEqual(el["fill"], "accent")

    def test_panel_parses_with_flag(self):
        el = render._parse_freeform_element(
            1, "panel ink outline accent at full-bleed")
        self.assertTrue(el["full_bleed"])
        self.assertEqual(el["fill"], "ink")
        self.assertEqual(el["stroke"], "accent")

    def test_other_kinds_named_error(self):
        for line in ("dot accent at full-bleed",
                     "line muted at full-bleed",
                     "arrow ink at full-bleed",
                     "text h1 ink at full-bleed | words"):
            with self.subTest(line=line):
                with self.assertRaises(render.SpecError) as cm:
                    render._parse_freeform_element(1, line)
                msg = str(cm.exception)
                self.assertIn("full-bleed", msg)
                self.assertIn("box/panel", msg)

    def test_block_at_full_bleed_named_error(self):
        with self.assertRaises(render.SpecError) as cm:
            render._parse_block_header(1, "stat-row at full-bleed")
        msg = str(cm.exception)
        self.assertIn("full-bleed", msg)
        self.assertIn("block", msg)


class FullBleedRenderTest(unittest.TestCase):
    """End to end: a full-bleed box paints the whole slide (0,0,w,h), the
    margins lint carves it out, and contained elements draw on top."""

    SPEC = ("---\ndeck: d\naudience: a\n---\n\n"
            "## Slide 1\nlayout: composed\n"
            "Block: freeform\n"
            "box accent at full-bleed\n"
            "text h1 paper at cols 2-11 rows 5-8 | Edge to edge\n")

    def test_full_bleed_box_spans_the_slide(self):
        tmp = tempfile.mkdtemp(prefix="slides-fullbleed-test-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        spec_path = os.path.join(tmp, "deck.md")
        brand_path = os.path.join(tmp, "brand.json")
        out_path = os.path.join(tmp, "out.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(self.SPEC)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(BRAND_IDENTITY, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"full-bleed render failed.\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}",
        )
        prs = Presentation(out_path)
        slide = prs.slides[0]
        washes = [
            s for s in slide.shapes
            if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
            and s.left == 0 and s.top == 0
            and s.width == prs.slide_width and s.height == prs.slide_height
        ]
        self.assertEqual(len(washes), 1, "expected one full-slide box")
        from pptx.dml.color import RGBColor
        self.assertEqual(
            washes[0].fill.fore_color.rgb, RGBColor.from_string("0B5FFF"))
        # A wash meets the slide edge squarely — no rounded paper wedges.
        from pptx.enum.shapes import MSO_SHAPE
        self.assertEqual(washes[0].auto_shape_type, MSO_SHAPE.RECTANGLE)


class DumbbellRenderTest(unittest.TestCase):
    """The REQ-204 acceptance case: a hand-drawn 3-category dumbbell chart
    from percent-placed freeform dots and connecting lines, rendered brand
    fidelity. Each dot's left EMU in the produced .pptx must land at
    margin_x + round(frac * content_w) — the data positions ARE the geometry."""

    # Per category: (2019 value frac, 2026 value frac) — dot spans are the
    # value +/- 2% so each dot CENTRES on its value; asserted on dot left
    # (value - 0.02). First category pins the acceptance positions 20%/65%.
    CATS = [
        ("Alpha", 0.20, 0.65, "18%-22%", "63%-67%", "22%-63%", "18%-26%"),
        ("Beta", 0.26, 0.60, "24%-28%", "58%-62%", "28%-58%", "44%-52%"),
        ("Gamma", 0.32, 0.72, "30%-34%", "70%-74%", "34%-70%", "70%-78%"),
    ]

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-dumbbell-test-")
        lines = ["---", "deck: d", "audience: a", "---", "",
                 "## Slide 1", "layout: composed", "Block: freeform"]
        for name, _v19, _v26, dot19, dot26, rail, band in cls.CATS:
            lines.append(f"text caption ink at x 2%-16% y {band} | {name}")
            lines.append(f"dot muted at x {dot19} y {band}")
            lines.append(f"line muted at x {rail} y {band}")
            lines.append(f"dot accent at x {dot26} y {band}")
        spec_path = os.path.join(cls._tmp, "deck.md")
        brand_path = os.path.join(cls._tmp, "brand.json")
        cls.out_path = os.path.join(cls._tmp, "out.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(BRAND_IDENTITY, fh)
        cls.result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", cls.out_path],
            capture_output=True, text=True,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_render_exits_zero(self):
        self.assertEqual(
            self.result.returncode, 0,
            f"dumbbell render failed.\nstdout: {self.result.stdout}\n"
            f"stderr: {self.result.stderr}",
        )

    def _dots_by_colour(self):
        """The slide's oval shapes, grouped by fill hex, sorted by top —
        category order. Lines are rectangles, so ovals are exactly the dots."""
        from pptx.enum.shapes import MSO_SHAPE
        prs = Presentation(self.out_path)
        slide = prs.slides[0]
        dots = {}
        for shape in slide.shapes:
            if shape.shape_type != MSO_SHAPE_TYPE.AUTO_SHAPE:
                continue
            if shape.auto_shape_type != MSO_SHAPE.OVAL:
                continue
            dots.setdefault(str(shape.fill.fore_color.rgb), []).append(shape)
        for shapes in dots.values():
            shapes.sort(key=lambda s: s.top)
        return prs, dots

    def test_dot_lefts_match_percent_maths_exactly(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        prs, dots = self._dots_by_colour()
        # Brand fidelity draws the pack grid: margin_x = 5% of the slide
        # width (tokens.pack_grid), the band the percent bounds resolve on.
        margin_x = round(prs.slide_width * 0.05)
        content_w = prs.slide_width - 2 * margin_x
        tol = round(0.01 * content_w)  # within 1% of content width
        muted = dots.get("6B7280", [])
        accent = dots.get("0B5FFF", [])
        self.assertEqual(len(muted), 3, "expected one muted dot per category")
        self.assertEqual(len(accent), 3, "expected one accent dot per category")
        for i, (name, v19, v26, *_rest) in enumerate(self.CATS):
            for dot, value in ((muted[i], v19), (accent[i], v26)):
                expected = margin_x + round((value - 0.02) * content_w)
                with self.subTest(category=name, value=value):
                    self.assertLessEqual(
                        abs(dot.left - expected), tol,
                        f"dot left {dot.left} not within {tol} EMU of "
                        f"{expected} (frac {value - 0.02})",
                    )


class CanvasRenderTest(unittest.TestCase):
    """REQ-205/D-405/D-410/D-411: an optional `Canvas: <colour-role>` field
    on composed and the six fixed roles — brand fidelity only — paints the
    slide background with that token role and re-resolves content colours
    for contrast. Template fidelity rejects the field by name (never a
    silent drop), and an unknown role is a named SpecError listing the
    canonical four."""

    INK_HEX = "1A1A1A"       # BRAND_IDENTITY colours, pinned
    PAPER_HEX = "FFFFFF"
    ACCENT_HEX = "0B5FFF"

    STATEMENT_SPEC = (
        "---\ndeck: d\naudience: a\n---\n\n"
        "## Slide 1\nlayout: statement\n"
        "Statement: Hero moments stop being white.\n"
        "Canvas: ink\n"
    )
    COMPOSED_SPEC = (
        "---\ndeck: d\naudience: a\n---\n\n"
        "## Slide 1\nlayout: composed\n"
        "Title: What moved this quarter\n"
        "Canvas: accent\n"
        "Block: stat-row\n"
        "56 | Days to close\n"
        "4% | Churn rate\n"
    )

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="slides-canvas-render-test-")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)

    def _render(self, spec_text, brand, name):
        spec_path = os.path.join(self._tmp, f"{name}.deck.md")
        brand_path = os.path.join(self._tmp, f"{name}.brand.json")
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec_text)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(brand, fh)
        result = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        return result, out_path

    def _run_colours(self, shape):
        return {
            str(run.font.color.rgb)
            for para in shape.text_frame.paragraphs
            for run in para.runs
        }

    def test_statement_on_ink_canvas_paints_bg_and_inverts_the_text(self):
        # Exit 0 IS the lint-green pin: a lint failure is a SpecError and
        # exits 1 before any .pptx is written.
        result, out_path = self._render(
            self.STATEMENT_SPEC, dict(BRAND_IDENTITY), "ink-statement")
        self.assertEqual(
            result.returncode, 0,
            f"Canvas: ink render failed.\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}",
        )
        slide = Presentation(out_path).slides[0]
        xml = slide._element.xml
        self.assertIn("<p:bg", xml, "no slide-level background painted")
        self.assertIn(self.INK_HEX, xml, "background is not the ink hex")
        statements = [
            s for s in slide.shapes if s.name == "slides-field:Statement"
        ]
        self.assertEqual(len(statements), 1)
        # D-410: on a dark canvas the statement's ink inverts to paper.
        self.assertEqual(self._run_colours(statements[0]), {self.PAPER_HEX})

    def test_composed_on_accent_canvas_recolours_title_not_blocks(self):
        result, out_path = self._render(
            self.COMPOSED_SPEC, dict(BRAND_IDENTITY), "accent-composed")
        self.assertEqual(
            result.returncode, 0,
            f"Canvas: accent render failed.\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}",
        )
        slide = Presentation(out_path).slides[0]
        # The background is the accent role, painted slide-level.
        from pptx.enum.dml import MSO_FILL  # noqa: PLC0415
        fill = slide.background.fill
        self.assertEqual(fill.type, MSO_FILL.SOLID)
        self.assertEqual(str(fill.fore_color.rgb), self.ACCENT_HEX)
        # The composed title re-resolves through content_roles: the accent
        # canvas is dark, so ink text inverts to paper.
        titles = [s for s in slide.shapes if s.name == "slides-field:Title"]
        self.assertEqual(len(titles), 1)
        self.assertEqual(self._run_colours(titles[0]), {self.PAPER_HEX})
        # BLOCK primitives keep their own token colours (D-410 scope): the
        # stat numbers stay accent, exactly as they draw on paper.
        stat_runs = {
            run.text: str(run.font.color.rgb)
            for s in slide.shapes
            if (s.name or "").startswith("slides-block:stat-row")
            for para in s.text_frame.paragraphs
            for run in para.runs
        }
        self.assertEqual(stat_runs.get("56"), self.ACCENT_HEX)
        self.assertEqual(stat_runs.get("4%"), self.ACCENT_HEX)

    def test_unknown_canvas_role_is_a_named_error_listing_the_roles(self):
        spec = self.STATEMENT_SPEC.replace("Canvas: ink", "Canvas: navy")
        result, out_path = self._render(
            spec, dict(BRAND_IDENTITY), "navy")
        self.assertEqual(
            result.returncode, 1,
            f"expected exit 1 on Canvas: navy.\nstdout: {result.stdout}\n"
            f"stderr: {result.stderr}",
        )
        self.assertIn("navy", result.stderr)
        for role in ("ink", "paper", "accent", "muted"):
            self.assertIn(role, result.stderr)
        self.assertFalse(
            os.path.exists(out_path),
            "no .pptx may be written on a bad Canvas value",
        )

    def test_template_fidelity_rejects_canvas_naming_the_slide(self):
        # D-411: never a silent drop — the error names the slide and the fix.
        brand = {
            "fidelity": "template",
            "template": TEMPLATE,
            "fonts": {"heading": "Calibri", "body": "Calibri"},
            "colours": dict(BRAND_IDENTITY["colours"]),
            "layout_map": dict(LAYOUT_MAP),
        }
        result, out_path = self._render(
            self.STATEMENT_SPEC, brand, "template-reject")
        self.assertEqual(
            result.returncode, 1,
            f"expected exit 1 for Canvas under template fidelity.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )
        self.assertIn("slide 1", result.stderr)
        self.assertIn("Canvas is a brand-fidelity field", result.stderr)
        self.assertIn('"fidelity": "brand"', result.stderr)
        self.assertFalse(
            os.path.exists(out_path),
            "no .pptx may be written when Canvas meets template fidelity",
        )

    def test_composed_canvas_under_template_fidelity_is_also_rejected(self):
        # The composed parser stores Canvas in fields, not meta — the D-411
        # gate must catch that shape too.
        brand = {
            "fidelity": "template",
            "template": TEMPLATE,
            "fonts": {"heading": "Calibri", "body": "Calibri"},
            "colours": dict(BRAND_IDENTITY["colours"]),
            "layout_map": {**LAYOUT_MAP, "composed": 5},
        }
        result, _ = self._render(
            self.COMPOSED_SPEC, brand, "template-composed-reject")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Canvas is a brand-fidelity field", result.stderr)


# ---------------------------------------------------------------------------
# Deck-level device repetition + freeform hero-wrap notes surface in the run
# summary (composition.deck_device_repetition + primitives hero_wrapped stamp).
# Brand fidelity (no `fidelity` key → brand): composed slides draw from tokens.
# ---------------------------------------------------------------------------

COMPOSED_BRAND = {
    "template": TEMPLATE,
    "fonts": {"heading": "Calibri", "body": "Calibri"},
    "colours": {"accent": "#4F81BD", "accent2": "#C0504D",
                "ink": "#000000", "paper": "#FFFFFF"},
    "layout_map": {"title": 0, "title-content": 1, "section": 2,
                   "two-column": 3, "statement": 5, "quote": 2, "composed": 5},
}

_FRONT = "---\ndeck: d\naudience: a\n---\n\n"
_STAT = "layout: composed\nBlock: stat-row\n56 | Days\n4% | Rate\n"
_CARDS = "layout: composed\nBlock: card-grid\nSize | a\nKnowledge | b\n!Aim | c\n"
_CMP = "layout: composed\nBlock: comparison\nBefore | slow\n!After | fast\n"
_PROC = "layout: composed\nBlock: process\nPlan\nCreate\nDeliver\n"
_TL = ("layout: composed\nBlock: timeline\n"
       "2026 | Kickoff\n!2027 | Launch\n2028 | Scale\n")


def _deck_spec(*slide_bodies):
    """A minimal deck spec: each arg is one slide's body (its layout/fields)."""
    out = [_FRONT]
    for i, body in enumerate(slide_bodies, start=1):
        out.append(f"## Slide {i}\n{body}\n")
    return "".join(out)


class DeckDeviceRepetitionRenderTest(unittest.TestCase):
    """End-to-end: the deck-level repetition advisory and the freeform hero-wrap
    render note reach the printed run summary."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-deck-advisory-test-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _render(self, name, spec_text):
        spec_path = os.path.join(self._tmp, f"{name}.deck.md")
        brand_path = os.path.join(self._tmp, f"{name}.brand.json")
        out_path = os.path.join(self._tmp, f"{name}.pptx")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(spec_text)
        with open(brand_path, "w", encoding="utf-8") as fh:
            json.dump(COMPOSED_BRAND, fh)
        proc = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path,
             "--brand", brand_path, "--out", out_path],
            capture_output=True, text=True,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"render failed:\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
        return proc.stdout + proc.stderr

    def test_repeated_device_advises(self):
        # 4 stat-row + 1 comparison composed slides: stat-row dominates.
        summary = self._render("repeat", _deck_spec(
            _STAT, _STAT, _STAT, _STAT, _CMP))
        self.assertIn("deck-device-repetition", summary)
        self.assertIn("stat-row", summary)

    def test_varied_deck_no_advisory(self):
        # 5 distinct devices → no single device dominates.
        summary = self._render("varied", _deck_spec(
            _STAT, _CARDS, _CMP, _PROC, _TL))
        self.assertNotIn("deck-device-repetition", summary)

    def test_statement_bookend_no_advisory(self):
        # 2 statement (fixed-role) slides bracket 3 varied composed slides:
        # fixed roles are not tallied, composed devices vary → nothing dominates.
        summary = self._render("bookend", _deck_spec(
            "layout: statement\nStatement: The meeting costs six hours a week.",
            _STAT, _CARDS, _CMP,
            "layout: statement\nStatement: Write it down instead.",
        ))
        self.assertNotIn("deck-device-repetition", summary)

    def test_freeform_hero_wrap_note(self):
        # A display-scale freeform line that wraps in a tall box that still holds
        # it is owned up to in the run summary, by slide number.
        summary = self._render("hero", _deck_spec(
            "layout: composed\nBlock: freeform\n"
            "text display ink at cols 1-12 rows 1-11 | The weekly status meeting",
        ))
        self.assertIn("freeform hero text wrapped", summary)
        self.assertIn("slide 1", summary)


if __name__ == "__main__":
    unittest.main()
