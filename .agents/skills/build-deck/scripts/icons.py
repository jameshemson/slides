"""icons.py — recolour + rasterise bundled iconoir line icons to token PNGs.

The composed pipeline draws an icon as a PNG placed on the grid. Icons ship as
iconoir SVGs (MIT, © Luca Burgio — see assets/icons/LICENSE) drawn with a
`currentColor` stroke, so recolouring an icon to a token colour is a pure string
substitution. render.py resolves an icon element to a PNG *after* the lint has
cleared it (the element carries a token colour), so the primitive planners stay
pure — the same split charts.py uses.

Rasterisation needs cairosvg (optional, lazy-imported, mirroring matplotlib for
charts). Absent, render.py drops the icon and notes it; the deck still builds.
This module holds no brand literal: the only colour it writes is the token hex
its caller passes in.
"""
import os

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "icons")
)


class IconError(Exception):
    """An unknown icon name, or an icon that cannot be rendered."""


def available():
    """The set of bundled icon names (each is an `.svg` basename under assets)."""
    try:
        return {f[:-4] for f in os.listdir(_ICONS_DIR) if f.endswith(".svg")}
    except FileNotFoundError:
        return set()


def _load_svg(name):
    path = os.path.join(_ICONS_DIR, name + ".svg")
    if not os.path.isfile(path):
        raise IconError(f"unknown icon {name!r}")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def recolour(svg, colour_hex):
    """Replace iconoir's `currentColor` stroke with a concrete hex, so the icon
    carries exactly one token colour. PURE string op — no dependency; runs in the
    unconditional test path."""
    return svg.replace("currentColor", colour_hex)


def cairosvg_available():
    """True when the optional rasteriser is importable."""
    try:
        import cairosvg  # noqa: F401 — availability probe only
        return True
    except Exception:  # noqa: BLE001 — any import failure means unavailable
        return False


def render_png(name, colour_hex, px, out_path):
    """Recolour icon `name` to `colour_hex` and rasterise to a `px`-square PNG at
    `out_path`; return `out_path`.

    Raises IconError if the name is unknown or cairosvg is unavailable —
    render.py catches the latter to degrade the icon rather than fail the deck.
    """
    svg = recolour(_load_svg(name), colour_hex)
    try:
        import cairosvg  # noqa: PLC0415 — optional, only on an icon slide
    except Exception as exc:  # noqa: BLE001
        raise IconError("cairosvg is not installed") from exc
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=out_path,
        output_width=int(px),
        output_height=int(px),
    )
    return out_path
