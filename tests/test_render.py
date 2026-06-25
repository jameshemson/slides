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
import json
import os
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
        for name in os.listdir(cls._tmp):
            os.remove(os.path.join(cls._tmp, name))
        os.rmdir(cls._tmp)


class RenderErrorTest(unittest.TestCase):
    """Negative-path coverage: malformed input must exit non-zero with a
    message naming the fault, and never emit a .pptx."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="slides-render-error-test-")

    @classmethod
    def tearDownClass(cls):
        for name in os.listdir(cls._tmp):
            os.remove(os.path.join(cls._tmp, name))
        os.rmdir(cls._tmp)

    def _run(self, name, spec_text, brand=None):
        """Write a spec (+ brand) and run render.py. Returns CompletedProcess."""
        if brand is None:
            brand = {
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
                            ("t-line", LINE_BLOCK)):
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
        counts = {}
        for px in img.getdata():
            counts[px] = counts.get(px, 0) + 1

        def near(target, tol=10):
            tr, tg, tb = target
            return sum(n for (r, g, b), n in counts.items()
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


if __name__ == "__main__":
    unittest.main()
