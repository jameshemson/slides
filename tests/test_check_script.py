"""Tests for source/skills/build-deck/scripts/check_script.py"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_DIR = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
sys.path.insert(0, _SCRIPTS_DIR)

import check_script  # noqa: E402

EXAMPLE = os.path.join(
    REPO_ROOT, "source", "skills", "build-deck", "reference", "example.build.cjs"
)

CLEAN = """// A minimal deck script within the boundary.
const args = process.argv.slice(2);
const tokensPath = args[args.indexOf("--tokens") + 1];
const outPath = args[args.indexOf("--out") + 1];
const T = require(require("path").resolve(tokensPath));
const pptxgen = T.loadPptxgen();
const C = JSON.parse('{"title":"Hello"}');
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
const s = pres.addSlide();
s.addText(C.title, { x: 1, y: 1, w: 6, h: 1, fontSize: T.scale.title, color: T.colours.ink, fontFace: T.fonts.heading, objectName: "slides-lead:Title" });
pres.writeFile({ fileName: outPath });
"""


def _with(line):
    return CLEAN + line + "\n"


class CheckTest(unittest.TestCase):
    def test_clean_script_has_no_violations(self):
        self.assertEqual(check_script.check(CLEAN), [])

    def test_idiom_allowed(self):
        self.assertEqual(
            check_script.check('const T = require(require("path").resolve(tokensPath));\n'), []
        )

    def test_path_and_pptxgenjs_allowed(self):
        self.assertEqual(
            check_script.check('const p = require("path");\nconst g = require(\'pptxgenjs\');\n'),
            [],
        )

    def _assert_one(self, line, needle):
        messages = check_script.check(_with(line))
        self.assertEqual(len(messages), 1, messages)
        self.assertTrue(messages[0].startswith("line 13:"), messages[0])
        self.assertIn(needle, messages[0])

    def test_require_fs(self):
        self._assert_one('const fs = require("fs");', "require('fs') is not allowed")

    def test_require_child_process(self):
        messages = check_script.check(_with("const cp = require('child_process');"))
        self.assertEqual(len(messages), 2, messages)
        self.assertIn("require('child_process') is not allowed", messages[0])
        self.assertIn("child processes are not allowed", messages[1])

    def test_require_os(self):
        self._assert_one('const os = require("os");', "require('os') is not allowed")

    def test_require_local_module(self):
        self._assert_one('const h = require("./helper");', "require('./helper') is not allowed")

    def test_dynamic_require(self):
        self._assert_one("const m = require(name);", "dynamic require is not allowed")

    def test_eval(self):
        self._assert_one('eval("1+1");', "eval is not allowed")

    def test_new_function(self):
        self._assert_one('const f = new Function("return 1");', "new Function is not allowed")

    def test_dynamic_import(self):
        self._assert_one('import("fs").then(() => {});', "dynamic import is not allowed")

    def test_process_env(self):
        self._assert_one("const home = process.env.HOME;", "the environment is not readable")

    def test_fetch(self):
        self._assert_one('fetch("https://example.com");', "network access is not allowed")

    def test_spawn(self):
        self._assert_one('spawn("ls");', "child processes are not allowed")

    def test_exec_sync(self):
        self._assert_one('execSync("ls");', "child processes are not allowed")

    def test_comment_is_not_exempt(self):
        self._assert_one("// later: require('fs')", "require('fs') is not allowed")

    def test_content_block_is_ignored(self):
        script = CLEAN.replace(
            "const C = JSON.parse('{\"title\":\"Hello\"}');",
            "const C = JSON.parse('{\"title\":\"process.env fetch( eval(\"}');",
        )
        self.assertEqual(check_script.check(script), [])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="slides-check-script-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, text):
        path = os.path.join(self.tmp, "deck.build.cjs")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_clean_exits_0(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_script.main([self._write(CLEAN)])
        self.assertEqual(code, 0)
        self.assertIn("script: clean", out.getvalue())

    def test_violation_exits_1(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_script.main([self._write(_with('const fs = require("fs");'))])
        self.assertEqual(code, 1)
        self.assertIn("script: 1 violation(s)", out.getvalue())

    def test_missing_file_exits_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = check_script.main([os.path.join(self.tmp, "nope.cjs")])
        self.assertEqual(code, 2)
        self.assertIn("error:", err.getvalue())

    @unittest.skipUnless(os.path.isfile(EXAMPLE), "example.build.cjs not present yet")
    def test_example_is_clean(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            self.assertEqual(check_script.check(fh.read()), [])


if __name__ == "__main__":
    unittest.main()
