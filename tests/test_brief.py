"""Tests for the optional Brief: field (the composition brief), the
structure:/motif: frontmatter, and the slides-lead:<Field> stamp."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
RENDER_PY = os.path.join(SCRIPTS, "render.py")
DECK_TO_SPEC_PY = os.path.join(SCRIPTS, "deck_to_spec.py")
DECK_SPEC_MD = os.path.join(
    REPO_ROOT, "source", "skills", "presentation-craft", "reference", "deck-spec.md"
)
sys.path.insert(0, SCRIPTS)

import deck_to_spec  # noqa: E402
import render  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.util import Inches  # noqa: E402

BRAND = {
    "fidelity": "brand",
    "fonts": {"heading": "Calibri", "body": "Calibri"},
    "colours": {
        "accent": "#4F81BD",
        "accent2": "#C0504D",
        "ink": "#000000",
        "paper": "#FFFFFF",
    },
}

BRIEF = (
    "One number is the whole point; a hero figure, and six blocks make it "
    "concrete; the number leads; reference: the Stripe annual letter"
)

FIXED_SPEC = f"""---
deck: Brief test
audience: A team lead deciding whether to trial written updates.
register: presented
---

## Slide 1
layout: statement
Brief: {BRIEF}
Statement: The weekly status meeting costs the team six hours every week.
Notes: Say the number plainly.
"""

COMPOSED_SPEC = f"""---
deck: Brief test composed
audience: A team lead deciding whether to trial written updates.
register: presented
---

## Slide 1
layout: composed
Brief: {BRIEF}
Title: What moved this quarter
Block: stat-row
56 | Days to close
4% | Win rate
120 | New deals
Notes: A hero row of three numbers.
"""

AFTER_BODY_SPEC = f"""---
deck: Brief after body
audience: A team lead deciding whether to trial written updates.
register: presented
---

## Slide 1
layout: title-content
Title: What the meeting does well
Body:
- It surfaces blockers fast.
- It gives quieter teammates a fixed moment.
Brief: {BRIEF}
Notes: Concede the strengths first.
"""

FRONTMATTER_SPEC = """---
deck: Deck-level brief
audience: A team lead deciding whether to trial written updates.
register: presented
structure: dark open and close, light evidence between
motif: six one-hour blocks
---

## Slide 1
layout: statement
Statement: The weekly status meeting costs the team six hours every week.
"""

UNKNOWN_SPEC = FIXED_SPEC.replace("Brief:", "Foo:")


def _without_brief(spec_text):
    kept = [line for line in spec_text.splitlines() if not line.startswith("Brief:")]
    return "\n".join(kept) + "\n"


class BriefTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="slides-brief-")
        self.brand = os.path.join(self.tmp, "brand.json")
        with open(self.brand, "w", encoding="utf-8") as fh:
            json.dump(BRAND, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def _render(self, spec_path, out_name):
        out = os.path.join(self.tmp, out_name)
        proc = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec_path, "--brand", self.brand, "--out", out],
            capture_output=True,
            text=True,
        )
        return proc, out

    def _against(self, pptx_path, spec_path):
        return subprocess.run(
            [sys.executable, DECK_TO_SPEC_PY, pptx_path, "--brand", self.brand, "--against", spec_path],
            capture_output=True,
            text=True,
        )

    def test_fixed_role_brief_renders_and_is_not_in_notes(self):
        spec = self._write("fixed.deck.md", FIXED_SPEC)
        proc, out = self._render(spec, "fixed.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        notes = Presentation(out).slides[0].notes_slide.notes_text_frame.text
        self.assertIn("Say the number plainly.", notes)
        self.assertNotIn("Brief", notes)
        self.assertNotIn("Stripe annual letter", notes)

    def test_composed_brief_renders(self):
        spec = self._write("composed.deck.md", COMPOSED_SPEC)
        proc, out = self._render(spec, "composed.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        notes = Presentation(out).slides[0].notes_slide.notes_text_frame.text
        self.assertNotIn("Stripe annual letter", notes)

    def test_parse_spec_exposes_brief(self):
        for name, text in (("fixed.deck.md", FIXED_SPEC), ("composed.deck.md", COMPOSED_SPEC)):
            with self.subTest(spec=name):
                parsed = render.parse_spec(self._write(name, text))
                self.assertEqual(parsed[0]["meta"]["Brief"], BRIEF)

    def test_brief_after_body_is_recognised(self):
        parsed = render.parse_spec(self._write("after-body.deck.md", AFTER_BODY_SPEC))
        self.assertEqual(parsed[0]["meta"]["Brief"], BRIEF)
        self.assertEqual(len(parsed[0]["fields"]["Body"]), 2)

    def test_fixed_brief_is_not_drift(self):
        with_brief = self._write("fixed.deck.md", FIXED_SPEC)
        without = self._write("fixed-plain.deck.md", _without_brief(FIXED_SPEC))
        proc, out = self._render(with_brief, "fixed.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        a = self._against(out, with_brief)
        b = self._against(out, without)
        self.assertEqual(a.returncode, 0, a.stdout + a.stderr)
        self.assertEqual(a.returncode, b.returncode)
        self.assertEqual(a.stdout, b.stdout)

    def test_composed_brief_is_not_drift(self):
        with_brief = self._write("composed.deck.md", COMPOSED_SPEC)
        without = self._write("composed-plain.deck.md", _without_brief(COMPOSED_SPEC))
        proc, out = self._render(with_brief, "composed.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        a = self._against(out, with_brief)
        b = self._against(out, without)
        self.assertNotEqual(a.returncode, 1, a.stderr)
        self.assertEqual(a.returncode, b.returncode)
        self.assertEqual(a.stdout, b.stdout)

    def test_structure_and_motif_frontmatter_render(self):
        spec = self._write("frontmatter.deck.md", FRONTMATTER_SPEC)
        proc, _ = self._render(spec, "frontmatter.pptx")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        front = render.parse_frontmatter(spec)
        self.assertTrue(front["structure"].startswith("dark open"))
        self.assertEqual(front["motif"], "six one-hour blocks")

    def test_unknown_field_still_errors(self):
        spec = self._write("unknown.deck.md", UNKNOWN_SPEC)
        proc, _ = self._render(spec, "unknown.pptx")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unrecognised field 'Foo'", proc.stderr)

    def test_lead_stamp_reads_as_field(self):
        prs = Presentation()
        prs.slide_width = 12192000
        prs.slide_height = 6858000
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.name = "slides-role:title"
        lead = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(1))
        lead.name = "slides-lead:Title"
        lead.text_frame.text = "Hello"
        sub = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(6), Inches(1))
        sub.name = "slides-field:Subtitle"
        sub.text_frame.text = "World"
        self.assertEqual(
            deck_to_spec._stamped_fields(slide, "title"),
            {"Title": "Hello", "Subtitle": "World"},
        )

    def test_deck_spec_reference_within_ceiling(self):
        with open(DECK_SPEC_MD, encoding="utf-8") as fh:
            text = fh.read()
        self.assertLessEqual(len(text.splitlines()), 190)
        for needle in ("Brief:", "`structure`", "`motif`", "composing-in-code.md"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
