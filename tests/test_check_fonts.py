"""Tests for source/skills/build-deck/scripts/check_fonts.py"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_DIR = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
sys.path.insert(0, _SCRIPTS_DIR)

import check_fonts  # noqa: E402


def _probe(answer):
    return lambda name: answer


class FontStatusTest(unittest.TestCase):
    def test_installed_when_probe_finds(self):
        self.assertEqual(check_fonts.font_status("Georgia", [_probe("installed")]), "installed")

    def test_missing_when_probe_ran(self):
        self.assertEqual(
            check_fonts.font_status("Georgia", [_probe(None), _probe("missing")]), "missing"
        )

    def test_unknown_when_no_probe_runs(self):
        self.assertEqual(check_fonts.font_status("Georgia", [_probe(None)]), "unknown")
        self.assertEqual(check_fonts.font_status("Georgia", []), "unknown")

    def test_later_probe_overrides_missing(self):
        self.assertEqual(
            check_fonts.font_status("Georgia", [_probe("missing"), _probe("installed")]),
            "installed",
        )

    def test_all_runnable_miss(self):
        self.assertEqual(
            check_fonts.font_status(
                "Georgia", [_probe("missing"), _probe(None), _probe("missing")]
            ),
            "missing",
        )

    def test_real_probes_return_valid_values(self):
        for name in ("Arial", "No Such Family 12345"):
            self.assertIn(check_fonts.font_status(name), ("installed", "missing", "unknown"))


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="slides-check-fonts-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _brand(self, heading, body):
        path = os.path.join(self.tmp, "brand.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"fonts": {"heading": heading, "body": body}, "colours": {}}, fh)
        return path

    def test_cli_prints_one_line_per_family(self):
        answers = {"Georgia": "installed", "Calibri": "missing"}
        fake = [lambda name: answers.get(name)]
        out = io.StringIO()
        with mock.patch.object(check_fonts, "DEFAULT_PROBES", fake):
            with contextlib.redirect_stdout(out):
                code = check_fonts.main(["--brand", self._brand("Georgia", "Calibri")])
        self.assertEqual(code, 0)
        lines = out.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "font Georgia: installed")
        self.assertTrue(lines[1].startswith("font Calibri: missing"))
        self.assertIn("substitut", lines[1])

    def test_cli_unknown_line(self):
        out = io.StringIO()
        with mock.patch.object(check_fonts, "DEFAULT_PROBES", [lambda name: None]):
            with contextlib.redirect_stdout(out):
                code = check_fonts.main(["--font", "Roboto"])
        self.assertEqual(code, 0)
        self.assertTrue(out.getvalue().startswith("font Roboto: unknown"))

    def test_cli_dedupes_same_family(self):
        out = io.StringIO()
        with mock.patch.object(check_fonts, "DEFAULT_PROBES", [lambda name: "installed"]):
            with contextlib.redirect_stdout(out):
                code = check_fonts.main(["--brand", self._brand("Roboto", "Roboto")])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip().splitlines(), ["font Roboto: installed"])

    def test_cli_no_fonts_exits_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = check_fonts.main([])
        self.assertEqual(code, 2)
        self.assertIn("error:", err.getvalue())

    def test_cli_unreadable_brand_exits_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = check_fonts.main(["--brand", os.path.join(self.tmp, "missing.json")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
