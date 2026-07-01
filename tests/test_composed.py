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
        """13 stats -> 26 elements -> over the element cap -> render fails, no file."""
        spec = (
            "---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
            "Block: stat-row\n"
            + "".join(f"{i} | label{i}\n" for i in range(13))
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

    def test_mixed_placement_rejected(self):
        # Several blocks must all be placed or all auto-placed, never a mix.
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Block: card-grid at cols 1-6\nA | x\nBlock: process\nPlan\n")
        self._assert_fails(spec, "mix of placed")

    def test_too_many_blocks_rejected(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                + "".join("Block: stat-row\n1 | a\n" for _ in range(5)))
        self._assert_fails(spec, "at most 4 blocks")

    def test_bad_placement_rejected(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
                "Block: card-grid at cols 1-99\nA | x\n")
        self._assert_fails(spec, "within 1-12")


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


class NewPrimitiveRenderTest(unittest.TestCase):
    """card-grid, comparison, process, timeline render as real drawn shapes."""

    def _render_block(self, block_text, out_name):
        spec = (
            "---\ndeck: d\naudience: a\n---\n\n## Slide 1\nlayout: composed\n"
            "Title: T\n" + block_text
        )
        return _run(spec, out_name=out_name)

    def _drawn(self, out):
        prs = Presentation(out)
        slide = prs.slides[0]
        self.assertEqual(slide.shapes.title.text, "T")
        return [s for s in slide.shapes if not s.is_placeholder]

    def test_card_grid_renders_panels(self):
        proc, out = self._render_block(
            "Block: card-grid\nSize | a\nKnowledge | b\n!Aim | c\n", "cards.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 3 panels + 3 labels + 3 bodies = 9 drawn shapes.
        self.assertEqual(len(self._drawn(out)), 9)

    def test_comparison_renders_two_panels(self):
        proc, out = self._render_block(
            "Block: comparison\nBefore | slow\n!After | fast\n", "cmp.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self._drawn(out)), 6)  # 2 panels + 2 headers + 2 bodies

    def test_process_renders_steps_and_connectors(self):
        proc, out = self._render_block(
            "Block: process\nPlan\nCreate\nDeliver\n", "proc.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 3 boxes + 3 numbers + 3 labels + 2 connectors = 11.
        self.assertEqual(len(self._drawn(out)), 11)

    def test_timeline_renders_dots_and_rail(self):
        proc, out = self._render_block(
            "Block: timeline\n2026 | Kickoff\n!2027 | Launch\n2028 | Scale\n",
            "tl.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 3 dots + 3 labels + 2 rail segments = 8.
        self.assertEqual(len(self._drawn(out)), 8)

    def test_comparison_wrong_count_fails(self):
        proc, out = self._render_block("Block: comparison\nOnly one | x\n", "bad.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("exactly two", proc.stderr + proc.stdout)

    def test_process_over_five_fails(self):
        block = "Block: process\n" + "".join(f"S{i}\n" for i in range(6))
        proc, out = self._render_block(block, "bad2.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("at most 5", proc.stderr + proc.stdout)

    def test_two_blocks_stack(self):
        # Two unplaced blocks stack top to bottom on one slide, no overlap.
        proc, out = self._render_block(
            "Block: stat-row\n56 | Days\n4% | Rate\nBlock: process\nPlan\nShip\n",
            "stack.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        drawn = self._drawn(out)
        # 2 numbers + 2 labels (stat-row) + 2 boxes + 2 numbers + 2 labels + 1
        # connector (process) = 11 shapes, all on one slide.
        self.assertEqual(len(drawn), 11)

    def test_placed_blocks_tile_side_by_side(self):
        # Left half card-grid, right half process — placed on the grid.
        proc, out = self._render_block(
            "Block: card-grid at cols 1-6\nWhy | reason\nWho | people\n"
            "Block: process at cols 7-12\nPlan\nShip\n",
            "tile.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        prs = Presentation(out)
        slide = prs.slides[0]
        drawn = [s for s in slide.shapes if not s.is_placeholder]
        mid = prs.slide_width // 2
        # Card panels sit left of centre; process boxes sit right of it.
        left_boxes = [s for s in drawn if s.left + s.width <= mid + 10000]
        right_boxes = [s for s in drawn if s.left >= mid - 10000]
        self.assertTrue(left_boxes, "no shapes in the left column")
        self.assertTrue(right_boxes, "no shapes in the right column")

    def test_freeform_renders_node_graph(self):
        # The case the fixed primitives can't express: nodes that connect.
        block = (
            "Block: freeform\n"
            "panel paper outline ink at cols 1-4 rows 1-8\n"
            "text h1 ink at cols 1-4 rows 1-3 | UK\n"
            "arrow ink at cols 5-5 rows 4-5\n"
            "panel accent at cols 6-9 rows 1-8\n"
            "text h1 paper at cols 6-9 rows 1-3 | Platform\n"
        )
        proc, out = self._render_block(block, "ff.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self._drawn(out)), 5)

    def test_freeform_bad_colour_fails(self):
        proc, out = self._render_block(
            "Block: freeform\ntext h1 purple at cols 1-6 rows 1-3 | Hi\n",
            "ffb.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("purple", proc.stderr + proc.stdout)

    def test_freeform_missing_at_fails(self):
        proc, out = self._render_block(
            "Block: freeform\ntext h1 ink hello world\n", "ffb2.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("at <placement>", proc.stderr + proc.stdout)

    def test_freeform_overlap_still_fails_hard(self):
        # The guardrail holds: freedom of arrangement, but no overlap.
        block = (
            "Block: freeform\n"
            "panel paper outline ink at cols 1-8 rows 1-8\n"
            "panel accent at cols 5-12 rows 4-10\n"
        )
        proc, out = self._render_block(block, "ffo.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("[overlap]", proc.stderr + proc.stdout)

    def test_freeform_icon_degrades_without_rasteriser(self):
        # No cairosvg here: the icon is dropped, the deck still builds, and the
        # summary names the fallback (mirrors the matplotlib chart fallback).
        import icons
        block = ("Block: freeform\n"
                 "icon growth accent at cols 1-3 rows 1-4\n"
                 "text h1 ink at cols 4-10 rows 1-4 | Up\n")
        proc, out = self._render_block(block, "ffi.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.isfile(out))
        if not icons.cairosvg_available():
            self.assertIn("cairosvg not installed", proc.stdout + proc.stderr)
            # the text still drew; the icon was dropped
            drawn = self._drawn(out)
            self.assertEqual(len(drawn), 1)

    def test_tree_renders_nodes_and_edges(self):
        block = ("Block: tree\n"
                 "Product\n"
                 "  Discovery\n"
                 "  Delivery\n"
                 "  !Growth\n")
        proc, out = self._render_block(block, "tree.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 4 nodes + 4 labels + 3 edges = 11 drawn shapes.
        self.assertEqual(len(self._drawn(out)), 11)

    def test_tree_indent_jump_fails(self):
        block = "Block: tree\nRoot\n    Grandchild\n"  # jumps root -> level 2
        proc, out = self._render_block(block, "treebad.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("jumps a level", proc.stderr + proc.stdout)

    def test_tree_two_roots_fails(self):
        block = "Block: tree\nRootA\nRootB\n"
        proc, out = self._render_block(block, "tree2.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("exactly one root", proc.stderr + proc.stdout)

    def test_icon_list_renders(self):
        import icons
        block = ("Block: icon-list\n"
                 "growth | Revenue up\n"
                 "team | Team scaled\n"
                 "fast | Shipping weekly\n")
        proc, out = self._render_block(block, "il.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        drawn = self._drawn(out)
        # 3 text rows always draw; the 3 icons draw only with a rasteriser.
        expected = 6 if icons.cairosvg_available() else 3
        self.assertEqual(len(drawn), expected)

    def test_icon_list_bad_icon_fails(self):
        proc, out = self._render_block(
            "Block: icon-list\nno-such | x\n", "ilbad.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no-such", proc.stderr + proc.stdout)

    def test_card_icon_prefix_renders(self):
        block = ("Block: card-grid\n"
                 "[growth] Grow | markets\n"
                 "[team] Serve | users\n")
        proc, out = self._render_block(block, "cardicon.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_cycle_renders(self):
        block = "Block: cycle\nPlan\nBuild\nMeasure\nLearn\n"
        proc, out = self._render_block(block, "cycle.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 4 nodes + 4 labels + 4 ring edges = 12 shapes.
        self.assertEqual(len(self._drawn(out)), 12)

    def test_matrix_renders(self):
        block = ("Block: matrix\nx: Effort\ny: Impact\n"
                 "Quick wins | do now\n!Big bets | plan\n"
                 "Deprioritise | skip\nFill-ins | maybe\n")
        proc, out = self._render_block(block, "matrix.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # 4 cells + 4 labels + 2 axis captions (+ up to 4 bodies if the region
        # is tall enough — bodies are clamped to the cell under a title).
        self.assertGreaterEqual(len(self._drawn(out)), 10)

    def test_matrix_wrong_count_fails(self):
        block = "Block: matrix\nOnly | one\nTwo | two\n"
        proc, out = self._render_block(block, "matbad.pptx")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("exactly four", proc.stderr + proc.stdout)
