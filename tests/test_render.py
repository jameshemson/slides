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
import subprocess
import sys
import tempfile
import unittest

from pptx import Presentation

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


if __name__ == "__main__":
    unittest.main()
