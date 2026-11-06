"""Content contract for the release docs and version carriers (0.21.0)."""
import json
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(REPO_ROOT, "source", "skills")

CARRIERS = [
    ("package.json", lambda j: j["version"]),
    (".claude-plugin/plugin.json", lambda j: j["version"]),
    (".claude-plugin/marketplace.json", lambda j: j["plugins"][0]["version"]),
    ("plugins/slides/.codex-plugin/plugin.json", lambda j: j["version"]),
]

REQUIRED = [
    ("README.md", "Node 22"),
    ("README.md", "pptxgenjs@4.0.1"),
    ("README.md", "--permission"),
    ("README.md", "LibreOffice"),
    ("HARNESSES.md", "pptxgenjs"),
    ("HARNESSES.md", "`revise`"),
    ("CLAUDE.md", "composing-in-code.md"),
    ("CHANGELOG.md", "## [0.20.0]"),
    ("CHANGELOG.md", "## [0.21.0]"),
    ("README.md", "/slides:slides"),
    ("HARNESSES.md", "`slides`"),
]

FORBIDDEN = [
    ("README.md", "Delegate rendering to Anthropic"),
    ("README.md", "pptxgenjs@4 "),
    ("CLAUDE.md", "There is no CI"),
]


def _read(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class ReleaseDocsTest(unittest.TestCase):
    def test_carriers_read_0_21_0(self):
        for rel, getter in CARRIERS:
            with self.subTest(carrier=rel):
                self.assertEqual(getter(json.loads(_read(rel))), "0.21.0")

    def test_required_content(self):
        for rel, needle in REQUIRED:
            with self.subTest(file=rel, needle=needle):
                self.assertIn(needle, _read(rel))

    def test_forbidden_content(self):
        for rel, needle in FORBIDDEN:
            with self.subTest(file=rel, needle=needle):
                self.assertNotIn(needle, _read(rel))

    def test_no_safe_font_pattern(self):
        offenders = []
        for root, _dirs, files in os.walk(SKILLS):
            for name in files:
                if name.endswith(".md"):
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8") as fh:
                        if "safe font" in fh.read().lower():
                            offenders.append(os.path.relpath(path, REPO_ROOT))
        if "safe font" in _read("README.md").lower():
            offenders.append("README.md")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
