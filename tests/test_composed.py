"""End-to-end tests for the `composed` deck-spec role (render.py + primitives + lint).

Stdlib unittest only. The render path is exercised via subprocess (like
test_render.py); the off-token lint gate, which is not reachable from spec text,
is exercised by calling the exact lint.check the render branch calls.

Run from the repo root:

    python3 -m unittest tests.test_composed -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from pptx import Presentation

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")
TEMPLATE = os.path.join(FIXTURES, "sample-template.pptx")
COMPOSED_SPEC = os.path.join(FIXTURES, "composed-deck.md")
SAMPLE_SPEC = os.path.join(FIXTURES, "sample-deck.md")
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
RENDER_PY = os.path.join(SCRIPTS, "render.py")

# Measured content margin of the fixture's mapped layouts (the two-column left
# edge). The composed stat_row must align to it exactly (REQ-011).
MARGIN_X = 457200

# A brand.json with tokens left implicit (derived) and composed mapped to the
# statement layout (single title, index 5).
BRAND = {
    "template": TEMPLATE,
    "fonts": {"heading": "Calibri", "body": "Calibri"},
    "colours": {"accent": "#4F81BD", "accent2": "#C0504D",
                "ink": "#000000", "paper": "#FFFFFF"},
    "layout_map": {"title": 0, "title-content": 1, "section": 2,
                   "two-column": 3, "statement": 5, "quote": 2, "composed": 5},
}


def _run(spec_text, out_name="out.pptx", brand=None):
    """Render spec_text via render.py in a temp dir. Returns (proc, out_path)."""
    tmp = tempfile.mkdtemp()
    spec_path = os.path.join(tmp, "deck.md")
    with open(spec_path, "w", encoding="utf-8") as fh:
        fh.write(spec_text)
    brand_path = os.path.join(tmp, "brand.json")
    with open(brand_path, "w", encoding="utf-8") as fh:
        json.dump(brand or BRAND, fh)
    out_path = os.path.join(tmp, out_name)
    proc = subprocess.run(
        [sys.executable, RENDER_PY, "--spec", spec_path,
         "--brand", brand_path, "--out", out_path],
        capture_output=True, text=True,
    )
    return proc, out_path


def _run_file(spec_path, brand=None):
    tmp = tempfile.mkdtemp()
    brand_path = os.path.join(tmp, "brand.json")
    with open(brand_path, "w", encoding="utf-8") as fh:
        json.dump(brand or BRAND, fh)
    out_path = os.path.join(tmp, "out.pptx")
    proc = subprocess.run(
        [sys.executable, RENDER_PY, "--spec", spec_path,
         "--brand", brand_path, "--out", out_path],
        capture_output=True, text=True,
    )
    return proc, out_path


class ComposedRenderTest(unittest.TestCase):
    """The fixture composed deck renders a stat row aligned to template margins."""

    @classmethod
    def setUpClass(cls):
        cls.proc, cls.out = _run_file(COMPOSED_SPEC)

    def test_render_succeeds(self):
        self.assertEqual(self.proc.returncode, 0,
                         f"render failed: {self.proc.stderr}\n{self.proc.stdout}")
        self.assertTrue(os.path.isfile(self.out), "no .pptx written")

    def test_six_stat_shapes(self):
        prs = Presentation(self.out)
        slide = prs.slides[0]
        drawn = [s for s in slide.shapes if not s.is_placeholder]
        self.assertEqual(len(drawn), 6,
                         "expected 3 numbers + 3 labels as non-placeholder shapes")

    def test_stat_row_aligns_to_margins(self):
        """REQ-011: over the drawn (non-placeholder) shapes, the row's left edge
        is the derived margin and its right edge is the symmetric margin."""
        prs = Presentation(self.out)
        slide = prs.slides[0]
        drawn = [s for s in slide.shapes if not s.is_placeholder]
        self.assertTrue(drawn, "no drawn shapes")
        left = min(s.left for s in drawn)
        right = max(s.left + s.width for s in drawn)
        self.assertEqual(left, MARGIN_X)
        self.assertEqual(right, prs.slide_width - MARGIN_X)

    def test_title_placeholder_filled(self):
        prs = Presentation(self.out)
        slide = prs.slides[0]
        self.assertIsNotNone(slide.shapes.title)
        self.assertEqual(slide.shapes.title.text, "What moved this quarter")


class ComposedLintGateTest(unittest.TestCase):
    """The mechanical lint is wired into the render gate."""

    def test_over_cap_fails_render(self):
        """7 stats -> 14 elements -> over the element cap -> render fails, no file."""
        spec = (
            "---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
            "Block: stat-row\n"
            + "".join(f"{i} | label{i}\n" for i in range(7))
        )
        proc, out = _run(spec)
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stderr + proc.stdout
        self.assertIn("error:", combined)
        self.assertIn("[count]", combined)
        self.assertFalse(os.path.isfile(out), "a half-built .pptx was written")

    def test_off_token_colour_blocked_by_gate(self):
        """Off-token colour isn't reachable from spec text, so exercise the exact
        gate the render branch calls: plan a row, mutate a colour off-token,
        and confirm lint.check raises."""
        sys.path.insert(0, SCRIPTS)
        import tokens
        import primitives
        import lint

        prs = Presentation(TEMPLATE)
        toks = tokens.resolve_tokens(BRAND, prs)
        els = primitives.plan_stat_row(
            [{"value": "1", "label": "x"}, {"value": "2", "label": "y"}],
            toks, prs.slide_width, prs.slide_height,
        )
        els[0]["colour"] = "#ABCDEF"  # not in colour_roles
        with self.assertRaises(lint.LintError) as ctx:
            lint.check(els, toks, prs.slide_width, prs.slide_height)
        msg = str(ctx.exception)
        self.assertIn("[colour]", msg)


class ComposedSpecErrorTest(unittest.TestCase):
    """Malformed composed specs fail loudly with no output."""

    def _assert_fails(self, spec, needle):
        proc, out = _run(spec)
        self.assertNotEqual(proc.returncode, 0)
        combined = proc.stderr + proc.stdout
        self.assertIn("error:", combined)
        self.assertIn(needle, combined)
        self.assertFalse(os.path.isfile(out))

    def test_stat_line_without_pipe(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Block: stat-row\n56 Days to close\n")
        self._assert_fails(spec, "value | label")

    def test_empty_block(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Block: stat-row\n")
        self._assert_fails(spec, "stat-row")

    def test_no_block(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Title: Just a title\n")
        self._assert_fails(spec, "Block")

    def test_unknown_block_type(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Block: pie-tower\n1 | a\n")
        self._assert_fails(spec, "pie-tower")

    def test_multiple_blocks_rejected(self):
        # This release takes one Block: per composed slide; stacking is a
        # follow-up. A second block must fail loudly (no overlapping output).
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Block: stat-row\n1 | a\nBlock: stat-row\n2 | b\n")
        self._assert_fails(spec, "one 'Block:'")


class BackCompatTest(unittest.TestCase):
    """REQ-009: the existing six-role sample deck renders unchanged."""

    def test_sample_deck_still_renders(self):
        proc, out = _run_file(SAMPLE_SPEC)
        self.assertEqual(proc.returncode, 0,
                         f"sample deck failed: {proc.stderr}\n{proc.stdout}")
        prs = Presentation(out)
        self.assertEqual(len(prs.slides), 6)
        # No composed slides here, so no non-placeholder text shapes (the
        # existing invariant test_render.py also asserts).
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame and shape.text_frame.text.strip():
                    self.assertTrue(
                        shape.is_placeholder,
                        "sample deck gained a non-placeholder text shape",
                    )


if __name__ == "__main__":
    unittest.main()


class CompositionAdvisoryTest(unittest.TestCase):
    """The advisory composition layer surfaces non-blocking notes in the summary."""

    def test_clean_composed_deck_has_no_advisory(self):
        # The fixture composed deck is good by construction -> no advisory lines.
        proc, out = _run_file(COMPOSED_SPEC)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("advisory", (proc.stdout + proc.stderr).lower())

    def test_weak_composed_deck_advises_without_blocking(self):
        # 6 stats (system cap is 12 elements, so the gate passes) + 5-word
        # labels -> stat-count + label-terseness advisories, render still succeeds.
        spec = (
            "---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
            "Block: stat-row\n"
            + "".join(f"{i} | this is a long label\n" for i in range(6))
        )
        proc, out = _run(spec)
        self.assertEqual(proc.returncode, 0,
                         f"advisory layer must not block: {proc.stderr}")
        self.assertTrue(os.path.isfile(out), "a .pptx should still be written")
        combined = proc.stdout + proc.stderr
        self.assertIn("advisory", combined.lower())
        self.assertIn("stat-count", combined)
        self.assertIn("label-terseness", combined)
