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
_PAD = 0.12
_LABEL_SIZE = 19
_TICK_SIZE = 14
_ANNOT_SIZE = 14
_BAR_THICK = 0.6
_LINE_W = 3.2

CHART_TYPES = ("bar", "column", "line", "pie", "scatter")


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
        else:  # line
            _draw_line(ax, chart, emphasis, muted, spend, ink)
        fig.savefig(out_path, dpi=_DPI, bbox_inches="tight",
                    pad_inches=_PAD, transparent=True)
    finally:
        plt.close(fig)
    return out_path


# --- drawing -----------------------------------------------------------------


def _fmt(v):
    """Compact numeric label: drop a trailing .0, else %g."""
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _draw_bars(ax, chart, emphasis, muted, spend, ink, vertical):
    cats = chart["categories"]
    series = chart["series"]
    emph = chart.get("emphasis")
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
                ax.text(x, v, _fmt(v), ha="center", va="bottom",
                        fontsize=_LABEL_SIZE, fontweight="bold", color=ink)
            ax.set_xticks(list(pos))
            ax.set_xticklabels(cats, fontsize=_TICK_SIZE)
            ax.set_ylim(0, max(values) * 1.18 or 1)
            _strip(ax, muted, keep_x=True)
        else:
            order = list(reversed(range(n)))
            ax.barh(order, values, height=_BAR_THICK, color=colours, zorder=3)
            span = (max(values) or 1)
            for y, v, name in zip(order, values, cats):
                ax.text(v + span * 0.01, y, _fmt(v), va="center", ha="left",
                        fontsize=_LABEL_SIZE, fontweight="bold", color=ink)
                ax.text(-span * 0.01, y, name, va="center", ha="right",
                        fontsize=_TICK_SIZE, color=ink)
            ax.set_xlim(0, span * 1.18)
            _strip(ax, muted, keep_x=False, keep_y=False)
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
            ax.set_xticklabels(cats, fontsize=_TICK_SIZE)
            _strip(ax, muted, keep_x=True)
        else:
            ax.set_yticks(list(base))
            ax.set_yticklabels(cats, fontsize=_TICK_SIZE)
            _strip(ax, muted, keep_x=False)
        leg = ax.legend(loc="upper center", ncol=len(series), frameon=False,
                        bbox_to_anchor=(0.5, 1.08), fontsize=_TICK_SIZE)
        for t in leg.get_texts():
            t.set_color(ink)

    _callout(ax, chart, spend, ink)


def _draw_line(ax, chart, emphasis, muted, spend, ink):
    points = chart["points"]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    at = dict(points)
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
    ax.set_ylim(0, max(ys) * 1.12 or 1)
    _strip(ax, muted, keep_x=True)
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
    labels = [f"{c}  {_fmt(v)}" for c, v in zip(cats, values)]
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
