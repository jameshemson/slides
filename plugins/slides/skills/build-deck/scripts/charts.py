"""charts.py — render a deck spec's Chart block to an on-brand PNG.

`render.py` calls `render_png(chart, colours, font, out_path)` when a slide
carries a structured `Chart:` block. This module owns ALL matplotlib use and
the chart-drawing craft (direct value labels, no legend, stripped spines,
emphasis colour vs muted). It is imported lazily by render.py only on a chart
slide, so a chartless deck never needs matplotlib (D-009).

Relationship to D-002: render.py never lets this module touch the slide or the
template. Every colour comes from the caller-supplied `brand["colours"]`; the
font family is a caller-supplied name (registered by render.py from a brand
font file). There are no colour or font-family literals here. The figure-canvas
size, DPI, and in-chart text sizes ARE fixed here — they describe the rendered
image, not slide or template geometry, which render.py derives from the template
when it places the picture.
"""
import matplotlib

matplotlib.use("Agg")  # headless image backend; no display required
import matplotlib.pyplot as plt  # noqa: E402

# Image-canvas parameters (NOT slide/template geometry — see module docstring).
# bbox_inches="tight" crops to content, so the placed aspect follows the chart.
_FIG_W, _FIG_H = 12.0, 5.0
_DPI = 200
_PAD = 0.22  # breathing room around the tight-cropped image
_LABEL_SIZE = 19
_TICK_SIZE = 14
_ANNOT_SIZE = 14
_BAR_THICK = 0.6
_LINE_W = 3.2
_CONNECTOR_W = 1.4  # thin waterfall connector between consecutive bars
_TARGET_LW = 1.4  # target/goal reference line weight

# Kept in sync with render.py's CHART_TYPES (D-010): the two tuples are
# deliberately duplicated so render.py never imports matplotlib. Both change
# together.
CHART_TYPES = ("bar", "column", "line", "pie", "scatter", "waterfall")


class ChartError(Exception):
    """A chart that cannot be drawn. render.py turns this into a SpecError."""


# --- colour resolution (D-006); every value from the caller's brand ----------


def _normalise_hex(value):
    """Return '#RRGGBB' (uppercase) for a hex string, or None if unparseable.

    Self-contained on purpose (review IMP-002): charts.py does not import the
    private helper from pptxlib. Accepts '#abc', 'abc', '#aabbcc', 'aabbcc'.
    """
    if not isinstance(value, str):
        return None
    text = value.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return None
    try:
        int(text, 16)
    except ValueError:
        return None
    return "#" + text.upper()


# Generic grey-push fallback for the muted role — used only when the brand names
# no `muted`. It must never be the paper colour: a de-emphasised bar or a second
# grouped series drawn in paper is invisible on a paper background. Generic
# default, not a brand value (like the generic type-scale defaults elsewhere).
_MUTED_FALLBACK = "#BFBFBF"
_INK_FALLBACK = "#333333"


def _resolve_colours(colours):
    """Resolve (emphasis, muted, spend, ink) from a brand colour dict (D-006).

    emphasis = colours['accent'] else 'growth' else first value.
    muted    = colours['muted']  else a neutral grey (NEVER paper — a paper bar
               is invisible on a paper background).
    spend    = colours['spend']  else emphasis.
    ink      = colours['ink']    else a dark default.
    Raises ChartError if no usable colour is present.
    """
    if not isinstance(colours, dict) or not colours:
        raise ChartError("chart needs at least one brand colour, but "
                         "brand.json 'colours' is empty")
    ordered = [c for c in (_normalise_hex(v) for v in colours.values()) if c]
    if not ordered:
        raise ChartError("brand.json 'colours' has no valid hex value for the "
                         "chart")

    def pick(key):
        return _normalise_hex(colours.get(key))

    emphasis = pick("accent") or pick("growth") or ordered[0]
    muted = pick("muted") or _MUTED_FALLBACK
    spend = pick("spend") or emphasis
    ink = pick("ink") or _INK_FALLBACK
    return emphasis, muted, spend, ink


# --- public entry point ------------------------------------------------------


def render_png(chart, colours, font, out_path):
    """Render `chart` to a PNG at `out_path`. Raises ChartError on bad data.

    `chart` is the dict produced by render.py's _parse_chart_block. `colours`
    is brand.json's colour dict. `font` is a registered family name or None
    (then matplotlib's default is used).
    """
    ctype = chart.get("type")
    if ctype not in CHART_TYPES:
        raise ChartError(f"unknown chart type {ctype!r}; expected one of "
                         f"{', '.join(CHART_TYPES)}")
    emphasis, muted, spend, ink = _resolve_colours(colours)

    if font:
        plt.rcParams["font.family"] = font
    else:
        plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams.update({
        "text.color": ink, "axes.labelcolor": ink,
        "xtick.color": ink, "ytick.color": ink,
    })

    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H))
    try:
        if ctype == "column":
            _draw_bars(ax, chart, emphasis, muted, spend, ink, vertical=True)
        elif ctype == "bar":
            _draw_bars(ax, chart, emphasis, muted, spend, ink, vertical=False)
        elif ctype == "pie":
            _draw_pie(ax, chart, emphasis, muted, spend, ink)
        elif ctype == "scatter":
            _draw_scatter(ax, chart, emphasis, muted, spend, ink)
        elif ctype == "waterfall":
            _draw_waterfall(ax, chart, emphasis, muted, spend, ink)
        else:  # line
            _draw_line(ax, chart, emphasis, muted, spend, ink)
        fig.savefig(out_path, dpi=_DPI, bbox_inches="tight",
                    pad_inches=_PAD, transparent=True)
    finally:
        plt.close(fig)
    return out_path


# --- drawing -----------------------------------------------------------------


def _fmt(v, fmt=None):
    """Format a value label from the chart's `fmt` (prefix/suffix/abbreviate).

    - `prefix` / `suffix` wrap the number (`$`, `%`, `k`), so 362 -> `$362k`.
    - `abbreviate` (default on, skipped when a suffix is set) shortens large
      numbers: 362000 -> `362k`, 1_500_000 -> `1.5M`.
    A bare number drops a trailing .0. No brand literal — fmt is caller-supplied.
    """
    fmt = fmt or {}
    prefix, suffix = fmt.get("prefix", ""), fmt.get("suffix", "")
    if fmt.get("abbreviate", True) and not suffix and abs(v) >= 1000:
        for div, unit in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
            if abs(v) >= div:
                num = f"{v / div:.1f}".rstrip("0").rstrip(".")
                return f"{prefix}{num}{unit}"
    num = str(int(v)) if float(v).is_integer() else f"{v:g}"
    return f"{prefix}{num}{suffix}"


def _signed_fmt(v, fmt=None):
    """Format a signed delta label (D-007): a leading sign then _fmt of the
    magnitude, e.g. `+$40k` / `-$15k`. Zero reads as `+0` (styled via _fmt).
    The sign is explicit; the magnitude carries the caller's prefix/suffix."""
    sign = "-" if v < 0 else "+"
    return sign + _fmt(abs(v), fmt)


def _set_xlabels(ax, cats):
    """Set category tick labels, rotating them when long or many so they don't
    run into each other."""
    crowded = len(cats) > 5 or any(len(str(c)) > 7 for c in cats)
    if crowded:
        ax.set_xticklabels(cats, fontsize=_TICK_SIZE, rotation=25, ha="right")
    else:
        ax.set_xticklabels(cats, fontsize=_TICK_SIZE)


def _stack_bottoms(series_values):
    """Per-series bar bottoms for a stacked chart (D-007), pure (no
    matplotlib) — mirrors `_waterfall_segments`. `series_values` is a list of
    per-series value lists (one list per series, same length, one entry per
    category). Returns, per series, its bottoms = the elementwise cumulative
    sum of every PRIOR series, so the first series sits on the zero baseline
    and each later series stacks on the running total below it.

    Example: [[10, 20], [5, 5]] -> [[0, 0], [10, 20]].
    """
    if not series_values:
        return []
    n = len(series_values[0])
    running = [0] * n
    bottoms = []
    for values in series_values:
        bottoms.append(list(running))
        running = [r + v for r, v in zip(running, values)]
    return bottoms


def _draw_bars(ax, chart, emphasis, muted, spend, ink, vertical):
    cats = chart["categories"]
    series = chart["series"]
    emph = chart.get("emphasis")
    fmt = chart.get("fmt")
    target = chart.get("target")
    n = len(cats)

    if len(series) == 1:
        values = series[0]["values"]
        if emph is None:
            colours = [emphasis] * n
        else:
            colours = [emphasis if c == emph else muted for c in cats]
        pos = range(n)
        if vertical:
            ax.bar(pos, values, width=_BAR_THICK, color=colours, zorder=3)
            for x, v in zip(pos, values):
                ax.text(x, v, _fmt(v, fmt), ha="center", va="bottom",
                        fontsize=_LABEL_SIZE, fontweight="bold", color=ink)
            ax.set_xticks(list(pos))
            _set_xlabels(ax, cats)
            top = max(values) * 1.18 or 1
            if target:
                top = max(top, target["value"] * 1.1)
            ax.set_ylim(0, top)
            _strip(ax, muted, keep_x=True)
            if target:
                _draw_target(ax, target, True, n - 1, spend, muted, emphasis,
                             ink, fmt)
        else:
            order = list(reversed(range(n)))
            ax.barh(order, values, height=_BAR_THICK, color=colours, zorder=3)
            span = (max(values) or 1)
            for y, v, name in zip(order, values, cats):
                ax.text(v + span * 0.01, y, _fmt(v, fmt), va="center", ha="left",
                        fontsize=_LABEL_SIZE, fontweight="bold", color=ink)
                ax.text(-span * 0.01, y, name, va="center", ha="right",
                        fontsize=_TICK_SIZE, color=ink)
            xmax = span * 1.18
            if target:
                xmax = max(xmax, target["value"] * 1.1)
            ax.set_xlim(0, xmax)
            _strip(ax, muted, keep_x=False, keep_y=False)
            if target:
                _draw_target(ax, target, False, n - 1, spend, muted, emphasis,
                             ink, fmt)
    elif chart.get("stacked"):
        # Stacked bars (D-007): one full-width bar per category; series
        # accumulate via _stack_bottoms. A single total label above each
        # stack keeps it clean rather than labelling every segment.
        palette = [emphasis, muted, spend]
        series_values = [s["values"] for s in series]
        bottoms = _stack_bottoms(series_values)
        totals = [sum(vals) for vals in zip(*series_values)]
        pos = list(range(n))
        for i, s in enumerate(series):
            col = palette[i % len(palette)]
            if vertical:
                ax.bar(pos, s["values"], bottom=bottoms[i], width=_BAR_THICK,
                       color=col, zorder=3, label=s["name"])
            else:
                ax.barh(pos, s["values"], left=bottoms[i], height=_BAR_THICK,
                        color=col, zorder=3, label=s["name"])
        if vertical:
            for x, tot in zip(pos, totals):
                ax.text(x, tot, _fmt(tot, fmt), ha="center", va="bottom",
                        fontsize=_LABEL_SIZE, fontweight="bold", color=ink)
            ax.set_xticks(pos)
            _set_xlabels(ax, cats)
            top = (max(totals) if totals else 0) * 1.18 or 1
            if target:
                top = max(top, target["value"] * 1.1)
            ax.set_ylim(0, top)
            _strip(ax, muted, keep_x=True)
            if target:
                _draw_target(ax, target, True, n - 1, spend, muted, emphasis,
                             ink, fmt)
        else:
            tot_span = (max(totals) if totals else 0) or 1
            for y, tot in zip(pos, totals):
                ax.text(tot + tot_span * 0.01, y, _fmt(tot, fmt), va="center",
                        ha="left", fontsize=_LABEL_SIZE, fontweight="bold",
                        color=ink)
            ax.set_yticks(pos)
            ax.set_yticklabels(cats, fontsize=_TICK_SIZE)
            xmax = tot_span * 1.18
            if target:
                xmax = max(xmax, target["value"] * 1.1)
            ax.set_xlim(0, xmax)
            _strip(ax, muted, keep_x=False)
            if target:
                _draw_target(ax, target, False, n - 1, spend, muted, emphasis,
                             ink, fmt)
        # Legend BELOW the chart, matching the grouped multi-series branch.
        leg = ax.legend(loc="upper center", ncol=len(series), frameon=False,
                        bbox_to_anchor=(0.5, -0.16), fontsize=_TICK_SIZE)
        for t in leg.get_texts():
            t.set_color(ink)
    else:
        # Multiple series: grouped bars, one palette colour each, bottom legend.
        palette = [emphasis, muted, spend]
        width = _BAR_THICK / len(series)
        base = range(n)
        for i, s in enumerate(series):
            offs = [b + (i - (len(series) - 1) / 2) * width for b in base]
            col = palette[i % len(palette)]
            if vertical:
                ax.bar(offs, s["values"], width=width, color=col, zorder=3,
                       label=s["name"])
            else:
                ax.barh(offs, s["values"], height=width, color=col, zorder=3,
                        label=s["name"])
        if vertical:
            ax.set_xticks(list(base))
            _set_xlabels(ax, cats)
            top = max(max(s["values"]) for s in series) * 1.12 or 1
            if target:
                top = max(top, target["value"] * 1.1)
            ax.set_ylim(0, top)
            _strip(ax, muted, keep_x=True)
            if target:
                _draw_target(ax, target, True, n - 1, spend, muted, emphasis,
                             ink, fmt)
        else:
            ax.set_yticks(list(base))
            ax.set_yticklabels(cats, fontsize=_TICK_SIZE)
            _strip(ax, muted, keep_x=False)
            if target:
                xmax = max(max(s["values"]) for s in series) * 1.12 or 1
                xmax = max(xmax, target["value"] * 1.1)
                ax.set_xlim(0, xmax)
                _draw_target(ax, target, False, n - 1, spend, muted, emphasis,
                             ink, fmt)
        # Legend BELOW the chart, so it never crowds the slide title above it.
        leg = ax.legend(loc="upper center", ncol=len(series), frameon=False,
                        bbox_to_anchor=(0.5, -0.16), fontsize=_TICK_SIZE)
        for t in leg.get_texts():
            t.set_color(ink)

    _callout(ax, chart, spend, ink)


# --- waterfall (running-total floating bars) ---------------------------------


def _waterfall_segments(values):
    """Pure geometry for a waterfall (no matplotlib). Given signed deltas,
    return (bottoms, heights, running):

    - `running[i]` is the cumulative total AFTER applying delta i.
    - `heights[i]` is the non-negative magnitude of delta i (bar height).
    - `bottoms[i]` is the lower edge of bar i — the smaller of the running
      levels either side of the delta — so a rise floats up from the previous
      level and a fall hangs down to the new level.

    Example: [40, -15, 25] -> bottoms [0, 25, 25], heights [40, 15, 25],
    running [40, 25, 50].
    """
    bottoms, heights, running = [], [], []
    prev = 0
    for v in values:
        new = prev + v
        bottoms.append(min(prev, new))
        heights.append(abs(v))
        running.append(new)
        prev = new
    return bottoms, heights, running


def _waterfall_colours(values, emphasis, muted, spend, ink):
    """Sign-coded bar colours (D-005), length len(values)+1:

    - a rise (delta >= 0) -> `emphasis` (accent);
    - a fall (delta < 0)  -> `spend`, but if the brand names no distinct spend
      (its fallback IS `emphasis`) -> `muted`, so rises and falls never share a
      colour and a fall is never the paper colour;
    - the trailing entry is the computed total bar -> `ink`.
    """
    fall = muted if _normalise_hex(spend) == _normalise_hex(emphasis) else spend
    colours = [emphasis if v >= 0 else fall for v in values]
    colours.append(ink)  # the appended total bar
    return colours


def _draw_waterfall(ax, chart, emphasis, muted, spend, ink):
    values = chart["series"][0]["values"]
    cats = list(chart["categories"])
    fmt = chart.get("fmt")
    n = len(values)
    bottoms, heights, running = _waterfall_segments(values)
    colours = _waterfall_colours(values, emphasis, muted, spend, ink)

    total_label = chart.get("total_label")
    has_total = total_label is not None
    total = running[-1] if running else 0
    half = _BAR_THICK / 2.0
    pos = list(range(n))

    # Floating delta bars.
    ax.bar(pos, heights, bottom=bottoms, width=_BAR_THICK,
           color=colours[:n], zorder=3)

    # Muted connectors at each running level, carrying into the total bar.
    for i in range(n - 1):
        ax.plot([i + half, (i + 1) - half], [running[i], running[i]],
                color=muted, lw=_CONNECTOR_W, zorder=2, solid_capstyle="round")
    if has_total and n >= 1:
        ax.plot([(n - 1) + half, n - half], [running[-1], running[-1]],
                color=muted, lw=_CONNECTOR_W, zorder=2, solid_capstyle="round")

    # Appended total bar: 0 -> final running total, drawn in ink.
    if has_total:
        ax.bar([n], [abs(total)], bottom=[min(0, total)], width=_BAR_THICK,
               color=ink, zorder=3)

    # Signed value labels: above the bar top for rises, below it for falls.
    for i, v in enumerate(values):
        if v >= 0:
            y, va = bottoms[i] + heights[i], "bottom"
        else:
            y, va = bottoms[i], "top"
        ax.text(i, y, _signed_fmt(v, fmt), ha="center", va=va,
                fontsize=_LABEL_SIZE, fontweight="bold", color=ink, zorder=4)
    if has_total:
        ax.text(n, max(0, total), _fmt(total, fmt), ha="center", va="bottom",
                fontsize=_LABEL_SIZE, fontweight="bold", color=ink, zorder=4)

    # Category ticks (plus the total label when present).
    labels = cats + [total_label] if has_total else cats
    ax.set_xticks(pos + [n] if has_total else pos)
    _set_xlabels(ax, labels)

    # Y-limits: headroom above every bar top and below any sub-zero bottom.
    tops = [bottoms[i] + heights[i] for i in range(n)] + [total]
    y_max = max(tops + [0])
    y_min = min(bottoms + [total, 0])
    top = (y_max * 1.18) or 1
    bottom = y_min * 1.15 if y_min < 0 else 0
    ax.set_ylim(bottom, top)

    _strip(ax, muted, keep_x=True)
    _callout(ax, chart, spend, ink)


def _draw_line(ax, chart, emphasis, muted, spend, ink):
    points = chart["points"]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    at = dict(points)
    fmt = chart.get("fmt")
    target = chart.get("target")
    ax.fill_between(xs, ys, color=emphasis, alpha=0.16, zorder=1)
    ax.plot(xs, ys, color=emphasis, lw=_LINE_W, zorder=2,
            solid_capstyle="round")
    for m in chart.get("markers", []):
        x = m["x"]
        y = at[x]
        ax.scatter([x], [y], s=90, color=spend, zorder=5)
        ax.annotate(m["label"], (x, y), xytext=(0, -28),
                    textcoords="offset points", ha="center",
                    fontsize=_ANNOT_SIZE, fontweight="bold", color=ink)
    top = max(ys) * 1.12 or 1
    if target:
        top = max(top, target["value"] * 1.1)
    ax.set_ylim(0, top)
    _strip(ax, muted, keep_x=True)
    if target:
        _draw_target(ax, target, True, max(xs), spend, muted, emphasis, ink,
                     fmt)
    _callout(ax, chart, spend, ink)


def _draw_pie(ax, chart, emphasis, muted, spend, ink):
    cats = chart["categories"]
    values = chart["series"][0]["values"]
    emph = chart.get("emphasis")
    palette = [emphasis, muted, spend, ink]
    if emph is None:
        colours = [palette[i % len(palette)] for i in range(len(cats))]
    else:
        colours = [emphasis if c == emph else muted for c in cats]
    labels = [f"{c}  {_fmt(v, chart.get('fmt'))}" for c, v in zip(cats, values)]
    ax.pie(
        values, labels=labels, colors=colours, startangle=90,
        counterclock=False, wedgeprops={"linewidth": 0},
        textprops={"color": ink, "fontsize": _TICK_SIZE},
    )
    ax.set_aspect("equal")
    _callout(ax, chart, spend, ink)


def _draw_scatter(ax, chart, emphasis, muted, spend, ink):
    points = chart["points"]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    at = dict(points)
    ax.scatter(xs, ys, s=90, color=emphasis, zorder=3)
    for m in chart.get("markers", []):
        x = m["x"]
        y = at[x]
        ax.scatter([x], [y], s=130, color=spend, zorder=5)
        ax.annotate(m["label"], (x, y), xytext=(0, -28),
                    textcoords="offset points", ha="center",
                    fontsize=_ANNOT_SIZE, fontweight="bold", color=ink)
    # A scatter needs both axes to read the relationship: keep them, muted.
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("bottom", "left"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color(muted)
    ax.tick_params(colors=ink, labelsize=_TICK_SIZE)
    ax.grid(False)
    _callout(ax, chart, spend, ink)


def _callout(ax, chart, spend, ink):
    text = chart.get("callout")
    if not text:
        return
    ax.annotate(text, xy=(0.5, 1.0), xycoords="axes fraction",
                xytext=(0, 6), textcoords="offset points", ha="center",
                va="bottom", fontsize=_ANNOT_SIZE, fontweight="bold",
                color=spend)


def _draw_target(ax, target, vertical, span, spend, muted, emphasis, ink, fmt):
    """Draw a target/goal reference line (D-008/D-009), under the bars/line
    (zorder 2, below the zorder=3 bars/zorder=2+ line). `vertical` selects a
    horizontal rule (`axhline`, for column/line charts, whose value axis is
    y) vs a vertical rule (`axvline`, for bar charts, whose value axis is x).

    `span` is the caller's already-resolved position along the axis that is
    NOT the value axis — the last category index for bar/column charts, or
    the rightmost x for a line chart — where the label anchors: the right
    edge of the horizontal rule, or the top of the vertical one. The label is
    nudged clear of the rule itself (off to the side, not centred on it) so
    the line never reads as a strikethrough under the text.

    Colour falls to `muted` when the brand names no distinct `spend` (i.e.
    spend == emphasis, _resolve_colours' fallback) — the same guard
    `_waterfall_colours` uses — so the line is never invisible. The label (if
    given) borrows `_callout`'s offset-point styling but is set in `ink`, not
    `spend`, so it reads as a plain data label rather than a highlight.
    """
    value = target["value"]
    label = target.get("label")
    colour = muted if _normalise_hex(spend) == _normalise_hex(emphasis) else spend
    text = f"{label} {_fmt(value, fmt)}" if label else None
    if vertical:
        ax.axhline(value, color=colour, lw=_TARGET_LW, zorder=2)
        if text:
            ax.annotate(text, xy=(span, value), xytext=(0, 6),
                        textcoords="offset points", ha="right", va="bottom",
                        fontsize=_ANNOT_SIZE, fontweight="bold", color=ink)
    else:
        ax.axvline(value, color=colour, lw=_TARGET_LW, zorder=2)
        if text:
            ax.annotate(text, xy=(value, span), xytext=(6, 6),
                        textcoords="offset points", ha="left", va="bottom",
                        fontsize=_ANNOT_SIZE, fontweight="bold", color=ink)


def _strip(ax, muted, keep_x=True, keep_y=False):
    """Remove chartjunk: hide spines, ticks, gridlines. `muted` tints the kept
    baseline. No colour literal — `muted` is a resolved brand colour."""
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_visible(keep_x)
    if keep_x:
        ax.spines["bottom"].set_color(muted)
    if not keep_y:
        ax.set_yticks([])
    ax.tick_params(left=False, bottom=False)
    ax.grid(False)
