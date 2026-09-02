"""Prose contract for the authored skill prompts in source/skills/.

Stdlib `unittest` only. The Node suite (`scripts/transformers/skill-contract.test.js`)
owns the structural gate — frontmatter fields and the line ceilings. This suite
owns the *content* gate: the facts a skill prompt must carry for the
composition-by-code path to be operable at all — the exact commands, the
fallback predicates, the gate names, and the order the steps run in.

Run from the repo root:

    python3 -m unittest tests.test_skill_prose
    python3 -m unittest discover tests
"""
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(REPO_ROOT, "source", "skills")

BUILD_DECK = "build-deck/SKILL.md"
NARRATIVE = "narrative/SKILL.md"
REVISE = "revise/SKILL.md"
SLOP_CHECK = "slop-check/SKILL.md"
CRAFT = "presentation-craft/SKILL.md"

# The command SKILL.md ceiling enforced by skill-contract.test.js; asserted here
# too so a Python-only run still catches an over-long build-deck prompt.
COMMAND_SKILL_LINE_LIMIT = 170

SANDBOX_COMMAND = (
    'node --permission --allow-fs-read="$PWD" '
    '--allow-fs-write="$PWD/<deck directory>" <deck>.build.cjs '
    "--tokens .slides/tokens.cjs --out <deck>.pptx"
)
FALLBACK_COMMAND = (
    "python3 scripts/render.py --spec <deck>.deck.md "
    "--brand .slides/brand.json --out <deck>.pptx"
)

# (relative file, substring that must appear verbatim)
REQUIRED = [
    # build-deck: the whole composition-by-code path, end to end.
    (BUILD_DECK, "composing-in-code.md"),
    (BUILD_DECK, "python3 scripts/emit_tokens.py .slides/brand.json --out .slides/tokens.cjs"),
    (BUILD_DECK, "python3 scripts/check_script.py <deck>.build.cjs"),
    (BUILD_DECK, SANDBOX_COMMAND),
    (BUILD_DECK, FALLBACK_COMMAND),
    (BUILD_DECK, "no `node` 22+ on PATH"),
    (BUILD_DECK, "pptxgenjs"),
    (BUILD_DECK, '"renderer": "python"'),
    (BUILD_DECK, '"fidelity": "template"'),
    (BUILD_DECK, "pptxgenjs@4.0.1"),
    (BUILD_DECK, "validate.py"),
    (BUILD_DECK, "authoritative"),
    (BUILD_DECK, "not covered"),
    (BUILD_DECK, "red on any grey or ink"),
    (BUILD_DECK, "notes covered"),
    (BUILD_DECK, "every mark's label adjacent to the mark"),
    (BUILD_DECK, "font "),
    (BUILD_DECK, "slides-field:<Field>"),
    (BUILD_DECK, "slides-lead"),
    (BUILD_DECK, "slides-ghost"),
    (BUILD_DECK, 'const T = require(require("path").resolve(tokensPath));'),
    (BUILD_DECK, "structure:"),
    (BUILD_DECK, "motif:"),
    (BUILD_DECK, "Brief:"),
    # narrative: the deck-level brief and the per-slide brief reach the spec.
    (NARRATIVE, "structure:"),
    (NARRATIVE, "motif:"),
    (NARRATIVE, "Brief:"),
    # revise: the script-built round trip.
    (REVISE, "slides-lead"),
    (REVISE, "stamp.py"),
    (REVISE, "slides-role:"),
    (REVISE, "Node 22"),
    # slop-check: where a script-built deck's field text lives.
    (SLOP_CHECK, "slides-field:"),
    # presentation-craft: the reference library entry.
    (CRAFT, "composing-in-code.md"),
]

# build-deck's steps must read in the order they are run.
ORDERED = [
    "scripts/emit_tokens.py",
    "scripts/check_script.py",
    "node --permission",
    "scripts/lint_pptx.py",
    "scripts/stamp.py",
    "scripts/check_fonts.py",
    "scripts/raster.py",
]


def read_skill(relative):
    with open(os.path.join(SKILLS, relative), encoding="utf-8") as handle:
        return handle.read()


class SkillProseTests(unittest.TestCase):
    def test_required_substrings_present(self):
        """Every fact the new path depends on is spelled out in the prompt."""
        for relative, needle in REQUIRED:
            with self.subTest(skill=relative, needle=needle):
                text = read_skill(relative)
                self.assertIn(
                    needle,
                    text,
                    f"{relative} must carry {needle!r}",
                )

    def test_build_deck_steps_are_in_running_order(self):
        """emit → guard → sandboxed run → lint → stamp → fonts → raster."""
        text = read_skill(BUILD_DECK)
        previous_name, previous_index = None, -1
        for needle in ORDERED:
            index = text.find(needle)
            self.assertNotEqual(index, -1, f"{BUILD_DECK} must mention {needle!r}")
            self.assertGreater(
                index,
                previous_index,
                f"{BUILD_DECK}: {needle!r} must come after {previous_name!r}",
            )
            previous_name, previous_index = needle, index

    def test_build_deck_within_line_ceiling(self):
        """The command-skill prompt ceiling, mirrored from the Node contract test."""
        text = read_skill(BUILD_DECK)
        lines = len(text.splitlines())
        self.assertLessEqual(
            lines,
            COMMAND_SKILL_LINE_LIMIT,
            f"{BUILD_DECK} is {lines} lines; ceiling is {COMMAND_SKILL_LINE_LIMIT}",
        )

    def test_command_skills_within_line_ceiling(self):
        """The four other command prompts stay under the same ceiling."""
        for relative in (NARRATIVE, REVISE, SLOP_CHECK):
            with self.subTest(skill=relative):
                lines = len(read_skill(relative).splitlines())
                self.assertLessEqual(
                    lines,
                    COMMAND_SKILL_LINE_LIMIT,
                    f"{relative} is {lines} lines; ceiling is {COMMAND_SKILL_LINE_LIMIT}",
                )


if __name__ == "__main__":
    unittest.main()
