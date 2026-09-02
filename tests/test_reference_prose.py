"""Contract tests for presentation-craft/reference/composing-in-code.md.

Stdlib `unittest` only — no pytest, no third-party test deps.

Run from the repo root:

    python3 -m unittest tests.test_reference_prose
    python3 -m unittest discover tests

The reference is prose, so these are the parts of it that other things depend
on: the hard line ceiling the skill contract enforces, the seven sections a
reader (and the model) navigates by, the rules quoted verbatim elsewhere in the
pack, the names of the scripts and stamps the build path uses, and the
evidence-citation style the rest of the reference library keeps.
"""
import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE = os.path.join(
    REPO_ROOT, "source", "skills", "presentation-craft", "reference",
    "composing-in-code.md",
)

# scripts/transformers/skill-contract.test.js caps every file in
# presentation-craft/reference/ at this many lines.
LINE_CEILING = 190

HEADINGS = (
    "## Why code",
    "## Decide before you draw",
    "## Every slide",
    "## What reads as AI in drawn slides",
    "## The script",
    "## The boundary",
    "## Gates",
)

# Rules and facts that must survive any rewrite of the surrounding prose.
# Matched case-insensitively so a phrase may open a sentence.
PHRASES = (
    "decode with the speaker notes covered",
    "red never sits on grey or ink",
    "content is data, never code",
    "--permission",
    "not covered",
)

# The vocabulary the build path is written in: spec keys, stamps, the one place
# spec text may appear, the gate scripts, and the worked example.
NAMES = (
    "structure",
    "motif",
    "Brief",
    "slides-lead",
    "slides-ghost",
    "JSON content block",
    "check_script.py",
    "lint_pptx.py",
    "stamp.py",
    "check_fonts.py",
    "example.build.cjs",
)

# The evidence-citation style of composition.md and design-research.md: every
# rule carries a parenthesised source tag.
SOURCE_TAG = re.compile(
    r"\((Duarte|Reynolds|Tufte|Gestalt|WCAG|Cowan|design-research|PP s|decks §)[^)]*\)"
)
MIN_SOURCE_TAGS = 8


class ComposingInCodeReferenceTest(unittest.TestCase):
    """The reference file exists and holds its contract."""

    @classmethod
    def setUpClass(cls):
        with open(REFERENCE, encoding="utf-8") as handle:
            cls.text = handle.read()

    def test_within_line_ceiling(self):
        lines = len(self.text.splitlines())
        self.assertLessEqual(
            lines, LINE_CEILING,
            f"composing-in-code.md has {lines} lines, over the {LINE_CEILING}-line "
            f"ceiling the skill contract enforces",
        )

    def test_has_the_seven_sections(self):
        for heading in HEADINGS:
            self.assertIn(heading, self.text, f"missing section heading: {heading!r}")

    def test_keeps_the_verbatim_rules(self):
        lowered = self.text.lower()
        for phrase in PHRASES:
            self.assertIn(phrase, lowered, f"missing verbatim rule: {phrase!r}")

    def test_names_the_build_path_vocabulary(self):
        for name in NAMES:
            self.assertIn(name, self.text, f"missing name: {name!r}")

    def test_cites_its_sources(self):
        tags = SOURCE_TAG.findall(self.text)
        self.assertGreaterEqual(
            len(tags), MIN_SOURCE_TAGS,
            f"only {len(tags)} parenthesised source tag(s); the reference library "
            f"cites its evidence (expected at least {MIN_SOURCE_TAGS})",
        )


if __name__ == "__main__":
    unittest.main()
