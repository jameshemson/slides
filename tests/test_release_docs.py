"""Content contract for the release docs and version carriers (0.22.0)."""
import json
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARRIERS = [
    ("package.json", lambda j: j["version"]),
    (".claude-plugin/plugin.json", lambda j: j["version"]),
    (".claude-plugin/marketplace.json", lambda j: j["plugins"][0]["version"]),
    ("plugins/slides/.codex-plugin/plugin.json", lambda j: j["version"]),
]

REQUIRED = [
    ("README.md", "/slides:slides"),
    ("README.md", "claude plugin install slides@slides"),
    ("README.md", "v0.21.0"),
    ("HARNESSES.md", "`slides`"),
    ("CLAUDE.md", "scripts/brand.py"),
    ("CHANGELOG.md", "## [0.22.0]"),
]

# The removed route must not be offered as though it still exists.
FORBIDDEN = [
    ("README.md", "/slides:build-deck"),
    ("README.md", "/slides:narrative"),
    ("HARNESSES.md", "`build-deck`"),
    ("CLAUDE.md", "presentation-craft"),
    ("README.md", "claude plugin add jameshemson"),
]


def _read(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class ReleaseDocsTest(unittest.TestCase):
    def test_carriers_read_0_22_0(self):
        for rel, getter in CARRIERS:
            with self.subTest(carrier=rel):
                self.assertEqual(getter(json.loads(_read(rel))), "0.22.0")

    def test_required_content(self):
        for rel, needle in REQUIRED:
            with self.subTest(file=rel, needle=needle):
                self.assertIn(needle, _read(rel))

    def test_forbidden_content(self):
        for rel, needle in FORBIDDEN:
            with self.subTest(file=rel, needle=needle):
                self.assertNotIn(needle, _read(rel))


if __name__ == "__main__":
    unittest.main()
