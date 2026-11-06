"""Structural contract for the composition-by-code release (0.20.0)."""
import json
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
REF = os.path.join(REPO_ROOT, "source", "skills", "presentation-craft", "reference")

NEW_FILES = [
    os.path.join(SCRIPTS, "emit_tokens.py"),
    os.path.join(SCRIPTS, "stamp.py"),
    os.path.join(SCRIPTS, "lint_pptx.py"),
    os.path.join(SCRIPTS, "check_script.py"),
    os.path.join(SCRIPTS, "check_fonts.py"),
    os.path.join(REF, "composing-in-code.md"),
    os.path.join(REPO_ROOT, "source", "skills", "build-deck", "reference", "example.build.cjs"),
]
CARRIERS = [
    ("package.json", lambda j: j["version"]),
    (".claude-plugin/plugin.json", lambda j: j["version"]),
    (".claude-plugin/marketplace.json", lambda j: j["plugins"][0]["version"]),
    ("plugins/slides/.codex-plugin/plugin.json", lambda j: j["version"]),
]


class ScriptPathContractTest(unittest.TestCase):
    def test_new_artifacts_exist(self):
        for path in NEW_FILES:
            with self.subTest(path=path):
                self.assertTrue(os.path.isfile(path), f"missing {path}")

    def test_version_is_0_21_0_everywhere(self):
        for rel, getter in CARRIERS:
            with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
                self.assertEqual(getter(json.load(fh)), "0.21.0", rel)

    def test_changelog_has_release(self):
        with open(os.path.join(REPO_ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
            self.assertIn("## [0.20.0]", fh.read())


if __name__ == "__main__":
    unittest.main()
