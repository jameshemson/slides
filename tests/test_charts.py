"""Tests for chart data ingestion (CSV) + the charts colour resolver.

Unit tests import the pure helpers directly; the CSV render path is exercised via
render.py in a subprocess (like test_composed).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
FIXTURES = os.path.join(REPO_ROOT, "tests", "fixtures")
TEMPLATE = os.path.join(FIXTURES, "sample-template.pptx")
RENDER_PY = os.path.join(SCRIPTS, "render.py")
sys.path.insert(0, SCRIPTS)

import charts  # noqa: E402
import render  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402 (backend set to Agg by charts import above)

BRAND = {
    "template": TEMPLATE,
    "fonts": {"heading": "Calibri", "body": "Calibri"},
    "colours": {"accent": "#4F81BD", "accent2": "#C0504D",
                "ink": "#000000", "paper": "#FFFFFF"},
    "layout_map": {"title": 0, "title-content": 1, "section": 2,
                   "two-column": 3, "statement": 5, "quote": 2},
}


class TestResolveColours(unittest.TestCase):
    def test_muted_is_never_paper(self):
        # This brand has no explicit 'muted'; the fallback must not be the paper
        # colour (a paper bar is invisible on a paper background).
        emphasis, muted, spend, ink = charts._resolve_colours(BRAND["colours"])
        self.assertEqual(emphasis, "#4F81BD")
        self.assertNotEqual(charts._normalise_hex(muted), "#FFFFFF")
        self.assertNotEqual(charts._normalise_hex(ink), "#FFFFFF")

    def test_explicit_muted_wins(self):
        _e, muted, _s, _i = charts._resolve_colours(
            {"accent": "#111111", "muted": "#00FF00"})
        self.assertEqual(charts._normalise_hex(muted), "#00FF00")


class TestValueFormat(unittest.TestCase):
    def test_currency_thousands(self):
        # data in $k: 362 -> $362k (suffix set, no auto-abbreviate)
        self.assertEqual(charts._fmt(362, {"prefix": "$", "suffix": "k"}), "$362k")

    def test_percent(self):
        self.assertEqual(charts._fmt(85, {"suffix": "%"}), "85%")

    def test_default_abbreviates_large(self):
        self.assertEqual(charts._fmt(362000), "362k")
        self.assertEqual(charts._fmt(1_500_000), "1.5M")

    def test_small_number_not_abbreviated(self):
        self.assertEqual(charts._fmt(500), "500")

    def test_plain_disables_abbreviation(self):
        self.assertEqual(charts._fmt(362000, {"abbreviate": False}), "362000")

    def test_currency_prefix_abbreviates(self):
        self.assertEqual(charts._fmt(362000, {"prefix": "$"}), "$362k")


class TestChartFormatParsing(unittest.TestCase):
    def _fmt_of(self, *chart_lines):
        chart = render._parse_chart_block(1, list(chart_lines), None)
        return chart["fmt"]

    def test_format_dollar_k(self):
        fmt = self._fmt_of("type: column", "format: $k",
                           "categories: A, B", "series X: 1, 2")
        self.assertEqual(fmt, {"prefix": "$", "suffix": "k"})

    def test_format_percent(self):
        fmt = self._fmt_of("type: column", "format: %",
                           "categories: A, B", "series X: 1, 2")
        self.assertEqual(fmt, {"suffix": "%"})

    def test_explicit_prefix_suffix(self):
        fmt = self._fmt_of("type: column", "prefix: £", "suffix: m",
                           "categories: A, B", "series X: 1, 2")
        self.assertEqual(fmt, {"prefix": "£", "suffix": "m"})

    def test_unknown_format_fails(self):
        with self.assertRaises(render.SpecError):
            self._fmt_of("type: column", "format: bananas",
                         "categories: A", "series X: 1")


class TestReadChartCsv(unittest.TestCase):
    def _csv(self, text):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        return path

    def test_category_csv(self):
        path = self._csv("Quarter,Revenue,Cost\nQ1,100,60\nQ2,120,55\n")
        out = render._read_chart_csv(1, path, "column")
        self.assertEqual(out["categories"], ["Q1", "Q2"])
        names = [s["name"] for s in out["series"]]
        self.assertEqual(names, ["Revenue", "Cost"])
        self.assertEqual(out["series"][0]["values"], [100.0, 120.0])
        self.assertEqual(out["series"][1]["values"], [60.0, 55.0])

    def test_point_csv(self):
        path = self._csv("x,y\n0,10\n5,25\n10,40\n")
        out = render._read_chart_csv(1, path, "line")
        self.assertEqual(out["points"], [(0.0, 10.0), (5.0, 25.0), (10.0, 40.0)])

    def test_missing_file_raises(self):
        with self.assertRaises(render.SpecError):
            render._read_chart_csv(1, "/no/such.csv", "column")


class TestCsvChartRender(unittest.TestCase):
    def _run(self, spec_text, csv_text=None):
        tmp = tempfile.mkdtemp()
        if csv_text is not None:
            with open(os.path.join(tmp, "data.csv"), "w") as fh:
                fh.write(csv_text)
        spec = os.path.join(tmp, "deck.md")
        with open(spec, "w") as fh:
            fh.write(spec_text)
        brand = os.path.join(tmp, "brand.json")
        with open(brand, "w") as fh:
            json.dump(BRAND, fh)
        out = os.path.join(tmp, "out.pptx")
        proc = subprocess.run(
            [sys.executable, RENDER_PY, "--spec", spec, "--brand", brand,
             "--out", out], capture_output=True, text=True)
        return proc, out

    def test_data_csv_renders(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\n"
                "layout: title-content\nTitle: T\nBody: b\n"
                "Chart:\n  type: column\n  data: data.csv\n")
        proc, out = self._run(spec, "Quarter,Revenue,Cost\nQ1,100,60\nQ2,120,55\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.isfile(out))

    def test_data_plus_inline_fails(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\n"
                "layout: title-content\nTitle: T\nBody: b\n"
                "Chart:\n  type: column\n  data: data.csv\n"
                "  categories: A, B\n  series X: 1, 2\n")
        proc, out = self._run(spec, "Q,V\nA,1\n")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cannot be combined", proc.stderr + proc.stdout)

    def test_missing_csv_fails(self):
        spec = ("---\ndeck: d\naudience: a\n---\n\n## Slide 1\n"
                "layout: title-content\nTitle: T\nBody: b\n"
                "Chart:\n  type: column\n  data: nope.csv\n")
        proc, out = self._run(spec)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not found", proc.stderr + proc.stdout)


# --- waterfall (T-003, REQ-006) ----------------------------------------------
#
# These pin the contracts the waterfall implementer (T-008) must satisfy. Two
# pure helpers keep the maths and the sign-colouring unit-testable without
# reaching into matplotlib internals:
#
#   charts._waterfall_segments(values) -> (bottoms, heights, running)
#       Floating-bar geometry for a running-total waterfall. For a delta series
#       the i-th bar starts at `bottoms[i]` and has vertical extent
#       `heights[i]` (always >= 0). `running` is the cumulative total AFTER each
#       delta, so `running[-1]` is the end value. A falling (negative) delta
#       drops the bottom below the previous total; a net-negative run pushes a
#       bottom below zero.
#
#   charts._waterfall_colours(values, emphasis, muted, spend, ink) -> [colour]
#       One colour per delta bar PLUS a trailing colour for the appended total
#       bar, so len == len(values) + 1. Rises (delta >= 0) use `emphasis`;
#       falls use `spend`, EXCEPT when the brand has no distinct spend colour
#       (i.e. `spend == emphasis`, per _resolve_colours' fallback) in which case
#       falls use `muted` so a rise and a fall never share a colour (D-005).
#       The trailing total bar uses `ink`.


class TestWaterfallSegments(unittest.TestCase):
    def test_running_total_segments(self):
        # Deltas +40, -15, +25 -> running 40, 25, 50. A rise starts at the
        # prior total; a fall's bar spans down from the prior total.
        bottoms, heights, running = charts._waterfall_segments([40, -15, 25])
        self.assertEqual(bottoms, [0, 25, 25])
        self.assertEqual(heights, [40, 15, 25])
        self.assertEqual(running, [40, 25, 50])
        self.assertEqual(running[-1], 50)

    def test_net_negative_dips_below_zero(self):
        # +10 then -30 ends at -20, so the falling bar's bottom is below zero.
        bottoms, heights, running = charts._waterfall_segments([10, -30])
        self.assertEqual(bottoms, [0, -20])
        self.assertEqual(heights, [10, 30])
        self.assertEqual(running[-1], -20)
        self.assertLess(min(bottoms), 0)
        self.assertTrue(any(b < 0 for b in bottoms))


class TestWaterfallColours(unittest.TestCase):
    PAPER = "#FFFFFF"

    def test_no_spend_key_falls_use_muted(self):
        # BRAND has no 'spend': _resolve_colours falls spend back to emphasis,
        # so falls must use muted instead (rise and fall never share a colour).
        emphasis, muted, spend, ink = charts._resolve_colours(BRAND["colours"])
        self.assertEqual(spend, emphasis)  # precondition for this branch
        cols = charts._waterfall_colours([40, -15, 25], emphasis, muted, spend, ink)
        self.assertEqual(len(cols), 4)          # 3 deltas + appended total bar
        self.assertEqual(cols[0], emphasis)     # rise
        self.assertEqual(cols[2], emphasis)     # rise
        self.assertEqual(cols[-1], ink)         # computed total bar
        fall = cols[1]
        self.assertEqual(fall, muted)           # fall degrades to muted
        self.assertNotEqual(fall, emphasis)     # ... and differs from a rise
        self.assertNotEqual(
            charts._normalise_hex(fall), charts._normalise_hex(self.PAPER))

    def test_spend_key_falls_use_spend(self):
        # A brand with an explicit 'spend' colours falls in spend, rises in
        # emphasis; the two differ and neither fall is paper.
        colours = {"accent": "#4F81BD", "spend": "#C0504D",
                   "ink": "#000000", "paper": self.PAPER}
        emphasis, muted, spend, ink = charts._resolve_colours(colours)
        self.assertNotEqual(spend, emphasis)  # precondition for this branch
        cols = charts._waterfall_colours([40, -15, 25], emphasis, muted, spend, ink)
        self.assertEqual(len(cols), 4)
        self.assertEqual(cols[0], emphasis)
        self.assertEqual(cols[-1], ink)
        fall = cols[1]
        self.assertEqual(fall, spend)
        self.assertNotEqual(fall, emphasis)
        self.assertNotEqual(
            charts._normalise_hex(fall), charts._normalise_hex(self.PAPER))


class TestWaterfallRender(unittest.TestCase):
    def test_render_writes_png(self):
        chart = {
            "type": "waterfall",
            "categories": ["Start", "Q1", "Q2"],
            "series": [{"name": "Cash", "values": [40, -15, 25]}],
            "total_label": "Total",
            "callout": None,
            "fmt": {},
        }
        fd, out = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        charts.render_png(chart, BRAND["colours"], None, out)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 0)


# --- stacked bars (T-002, REQ-004, D-007) -------------------------------------
#
# charts._stack_bottoms(series_values) -> list[list[float]] is the pure
# per-series stacking helper (D-007). `series_values` is a list of per-series
# value lists (one list per series, same length each, one entry per category);
# the return is, per series, that series' bar BOTTOMS = the elementwise
# cumulative sum of every PRIOR series (so the first series sits on the zero
# baseline, and each later series' bottom is the running total below it).
# Mirrors TestWaterfallSegments above: pins the maths with no matplotlib.


class TestStackBottoms(unittest.TestCase):
    def test_two_series_accumulate(self):
        self.assertEqual(
            charts._stack_bottoms([[10, 20], [5, 5]]),
            [[0, 0], [10, 20]])

    def test_three_series_accumulate(self):
        self.assertEqual(
            charts._stack_bottoms([[1, 1], [2, 2], [3, 3]]),
            [[0, 0], [1, 1], [3, 3]])


# Fixtures for the stacked render tests below: two series, `stacked: True`,
# no emphasis (REQ-004 makes emphasis+stacked a SpecError at parse — that
# cross-validation is render.py/test_render.py's contract, not charts.py's).
_STACKED_COLUMN = {
    "type": "column",
    "stacked": True,
    "categories": ["Q1", "Q2"],
    "series": [{"name": "Revenue", "values": [10, 20]},
               {"name": "Cost", "values": [5, 5]}],
    "emphasis": None,
    "callout": None,
    "fmt": {},
}

_STACKED_BAR = dict(_STACKED_COLUMN, type="bar")


class TestStackedRender(unittest.TestCase):
    """render_png must draw a stacked composition (D-007) for both bar
    orientations. The plain "writes a PNG" assertions alone do NOT fail red
    today: render_png/_draw_bars silently ignore an unrecognised `stacked`
    key and still produce a valid (wrongly grouped, not stacked) PNG. So each
    orientation also pins the bar GEOMETRY directly via a real Axes: stacked
    bars for N categories must collapse to exactly N distinct bar centres
    (one stack per category), not N * len(series) grouped offsets."""

    def test_stacked_column_writes_png(self):
        fd, out = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        charts.render_png(_STACKED_COLUMN, BRAND["colours"], None, out)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_stacked_column_bars_share_one_x_per_category(self):
        # Fails red now: _draw_bars offsets each series to its own x
        # position regardless of `stacked`, so today there are 4 distinct
        # bar centres (2 series x 2 categories), not 2 (1 per category).
        fig, ax = plt.subplots()
        try:
            charts._draw_bars(ax, _STACKED_COLUMN, "#4F81BD", "#BFBFBF",
                               "#4F81BD", "#333333", vertical=True)
            centres = {round(p.get_x() + p.get_width() / 2, 6)
                       for p in ax.patches}
            self.assertEqual(len(centres), len(_STACKED_COLUMN["categories"]))
        finally:
            plt.close(fig)

    def test_stacked_bar_writes_png(self):
        fd, out = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        charts.render_png(_STACKED_BAR, BRAND["colours"], None, out)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_stacked_bar_bars_share_one_y_per_category(self):
        # Horizontal counterpart: same grouping bug, on the category (y) axis.
        fig, ax = plt.subplots()
        try:
            charts._draw_bars(ax, _STACKED_BAR, "#4F81BD", "#BFBFBF",
                               "#4F81BD", "#333333", vertical=False)
            centres = {round(p.get_y() + p.get_height() / 2, 6)
                       for p in ax.patches}
            self.assertEqual(len(centres), len(_STACKED_BAR["categories"]))
        finally:
            plt.close(fig)


# --- target line (T-002, REQ-005, D-008/D-009) --------------------------------
#
# `target:` (D-009) is stored on the chart dict as
# {"value": float, "label": str|None}. D-008 wires a `_draw_target` helper
# into bar/column/line drawing: a hairline in `spend` (muted when
# spend == emphasis) with a right-edge label, drawn under the bars
# (zorder 2), with axis limits extended to `max(data, target) * headroom`.

_TARGET_COLUMN = {
    "type": "column",
    "categories": ["Q1", "Q2", "Q3"],
    "series": [{"name": "Revenue", "values": [40, 55, 60]}],
    "emphasis": None,
    "callout": None,
    "fmt": {},
    "target": {"value": 100.0, "label": "goal"},
}


class TestTargetRender(unittest.TestCase):
    def test_draw_target_helper_exists_and_render_writes_png(self):
        # Fails red now via AssertionError: charts._draw_target (D-008/D-009)
        # does not exist yet, so hasattr is False before render_png is ever
        # exercised. Kept red-first without guessing _draw_target's eventual
        # call signature (that's T-008's decision) — see the sibling test
        # below for the limits contract, which only needs _draw_bars
        # (already exists) called directly with a real Axes.
        self.assertTrue(hasattr(charts, "_draw_target"),
                        "charts._draw_target (D-008/D-009) not implemented")
        fd, out = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        charts.render_png(_TARGET_COLUMN, BRAND["colours"], None, out)
        self.assertTrue(os.path.isfile(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_target_extends_ylim_beyond_data_max(self):
        # REQ-005: axis limits extend to include the target even when it
        # exceeds every data point (data max 60, target 100). Fails red now:
        # _draw_bars ignores `target` today, so ylim tops out near the data
        # max * 1.18 (~70.8), well under 100 * 1.1 (110).
        fig, ax = plt.subplots()
        try:
            charts._draw_bars(ax, _TARGET_COLUMN, "#4F81BD", "#BFBFBF",
                               "#4F81BD", "#333333", vertical=True)
            self.assertGreaterEqual(ax.get_ylim()[1], 100 * 1.1)
        finally:
            plt.close(fig)


if __name__ == "__main__":
    unittest.main()
