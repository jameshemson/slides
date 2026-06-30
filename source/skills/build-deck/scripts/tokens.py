"""Design-token derivation layer for the build-deck pipeline.

This module holds ONLY generic structural defaults — grid fractions, type-scale
point sizes, and luminance-based colour-role assignments. It contains no brand-
specific values. Brand colours, coordinates, and fonts come from the template
and brand.json at render time, passed in by the caller.

The no-brand-literal spirit of render.py and pptxlib.py is preserved: the only
hex strings that appear here are those computed at runtime from caller-supplied
data; the only coordinate literals are the generic proportional constants used
when no geometry can be derived from the template.

Public API
----------
grid_from_rects(rects, slide_w, slide_h) -> dict
    Derive a grid sub-dict from a list of content-placeholder rects.

derive_grid(prs, layout_indices=None) -> dict
    Collect content-placeholder rects from the brand's mapped layouts (or all
    layouts when layout_indices is None/empty) and call grid_from_rects.

default_type_scale() -> dict
    Return the generic default type-scale point sizes.

resolve_colour_roles(colours) -> dict
    Map a name->hex dict to the four canonical colour roles.

resolve_tokens(brand, prs) -> dict
    Build a full tokens dict by merging template-derived defaults with any
    explicit overrides in brand["tokens"].
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptxlib import CONTENT_PLACEHOLDER_TYPES  # noqa: E402


# ---------------------------------------------------------------------------
# Grid derivation
# ---------------------------------------------------------------------------


def grid_from_rects(rects, slide_w, slide_h):
    """Derive a grid sub-dict from a list of content-placeholder rects.

    Parameters
    ----------
    rects : list of (left, top, width, height) int tuples, all in EMU.
        Already filtered to non-None geometry.
    slide_w, slide_h : int
        Slide dimensions in EMU.

    Returns
    -------
    dict with keys: margin_x, margin_top, margin_bottom, columns, gutter,
    baseline. All values are ints except columns (a count).

    Rules
    -----
    margin_x     = min(left) over rects
    margin_top   = min(top) over rects
    margin_bottom = slide_h - max(top + height) over rects
    columns      = 12 (constant)
    gutter       = smallest positive horizontal gap between any two rects that
                   share the same top within 12 700 EMU; if no such pair
                   exists, round(slide_w * 0.0167).
    baseline     = round(slide_h * 0.0133)

    Fallback (empty rects)
    ----------------------
    margin_x = round(slide_w * 0.05)
    margin_top = margin_bottom = round(slide_h * 0.08)
    columns = 12
    gutter = round(slide_w * 0.0167)
    baseline = round(slide_h * 0.0133)
    """
    baseline = round(slide_h * 0.0133)

    if not rects:
        margin_x = round(slide_w * 0.05)
        margin_top = round(slide_h * 0.08)
        margin_bottom = round(slide_h * 0.08)
        gutter = round(slide_w * 0.0167)
        return {
            "margin_x": margin_x,
            "margin_top": margin_top,
            "margin_bottom": margin_bottom,
            "columns": 12,
            "gutter": gutter,
            "baseline": baseline,
        }

    margin_x = min(r[0] for r in rects)
    margin_top = min(r[1] for r in rects)
    margin_bottom = slide_h - max(r[1] + r[3] for r in rects)

    # Smallest positive horizontal gap between rects sharing the same top
    # within a tolerance of 12 700 EMU.
    _TOLERANCE = 12700
    min_gap = None
    for i, a in enumerate(rects):
        for j, b in enumerate(rects):
            if i == j:
                continue
            if abs(a[1] - b[1]) <= _TOLERANCE and b[0] >= a[0]:
                gap = b[0] - (a[0] + a[2])
                if gap > 0:
                    if min_gap is None or gap < min_gap:
                        min_gap = gap

    gutter = min_gap if min_gap is not None else round(slide_w * 0.0167)

    return {
        "margin_x": margin_x,
        "margin_top": margin_top,
        "margin_bottom": margin_bottom,
        "columns": 12,
        "gutter": gutter,
        "baseline": baseline,
    }


def derive_grid(prs, layout_indices=None):
    """Collect content-placeholder rects from the brand's layouts and derive a grid.

    Uses CONTENT_PLACEHOLDER_TYPES from pptxlib to identify which placeholders
    carry content. Only rects where all four geometry values are non-None are
    included.

    Parameters
    ----------
    prs : pptx.Presentation
    layout_indices : iterable of int, optional
        Restrict measurement to these layout indices — the layouts the brand
        actually uses (brand.json's layout_map values). This is the right
        "brand surface" to measure: a real template can carry unused or odd
        extra layouts (the bundled default carries several) whose placeholder
        geometry would otherwise pollute the grid. Out-of-range indices are
        ignored. When None or empty, every layout is measured (the fallback).

    Returns
    -------
    dict — the "grid" sub-dict (see grid_from_rects for keys).
    """
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    layouts = list(prs.slide_layouts)
    if layout_indices:
        wanted = {i for i in layout_indices if 0 <= i < len(layouts)}
        if wanted:
            layouts = [layouts[i] for i in sorted(wanted)]

    rects = []
    for layout in layouts:
        for ph in layout.placeholders:
            if ph.placeholder_format.type in CONTENT_PLACEHOLDER_TYPES:
                left = ph.left
                top = ph.top
                width = ph.width
                height = ph.height
                if all(v is not None for v in (left, top, width, height)):
                    rects.append((left, top, width, height))

    return grid_from_rects(rects, slide_w, slide_h)


# ---------------------------------------------------------------------------
# Type scale
# ---------------------------------------------------------------------------


def default_type_scale():
    """Return the generic default type-scale point sizes.

    Returns
    -------
    dict with keys: display, h1, body, caption — all floats (pt).
    """
    return {
        "display": 40.0,
        "h1": 28.0,
        "body": 18.0,
        "caption": 12.0,
    }


# ---------------------------------------------------------------------------
# Colour roles
# ---------------------------------------------------------------------------


def _normalise_hex(value):
    """Normalise a hex colour string to '#RRGGBB' uppercase, or None.

    Accepts '#RRGGBB', 'RRGGBB', and '#RGB' / 'RGB' shorthand.
    Returns None for any unparseable input.
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


def _luminance(hex_str):
    """Perceptual luminance (0–255 scale) for a normalised '#RRGGBB' string."""
    text = hex_str.lstrip("#")
    r = int(text[0:2], 16)
    g = int(text[2:4], 16)
    b = int(text[4:6], 16)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def resolve_colour_roles(colours):
    """Map a name->hex dict to the four canonical colour roles.

    Parameters
    ----------
    colours : dict
        Keys are arbitrary colour names; values are hex strings (any of
        '#RRGGBB', 'RRGGBB', '#RGB').

    Returns
    -------
    dict with keys ink, paper, accent, muted — all '#RRGGBB' uppercase.
    Returns {} if no valid hex values are found.

    Resolution rules
    ----------------
    accent  = norm(colours['accent']) or first valid hex by insertion order
    ink     = norm(colours['ink'])    or darkest valid hex by luminance
    paper   = norm(colours['paper'])  or lightest valid hex by luminance
    muted   = norm(colours['muted'])  or norm(colours['accent2']) or accent

    Luminance = 0.2126*R + 0.7152*G + 0.0722*B on 0-255 channels.
    """
    # Normalise all provided values, preserving insertion order.
    normalised = {}
    for k, v in colours.items():
        norm = _normalise_hex(v)
        if norm is not None:
            normalised[k] = norm

    if not normalised:
        return {}

    valid_values = list(normalised.values())

    # accent: explicit key wins; otherwise the first valid hex in order.
    if "accent" in normalised:
        accent = normalised["accent"]
    else:
        accent = next(
            (normalised[k] for k in colours if k in normalised), None
        )

    # ink: explicit key wins; otherwise darkest by luminance.
    if "ink" in normalised:
        ink = normalised["ink"]
    else:
        ink = min(valid_values, key=_luminance)

    # paper: explicit key wins; otherwise lightest by luminance.
    if "paper" in normalised:
        paper = normalised["paper"]
    else:
        paper = max(valid_values, key=_luminance)

    # muted: explicit key > accent2 > accent.
    if "muted" in normalised:
        muted = normalised["muted"]
    elif "accent2" in normalised:
        muted = normalised["accent2"]
    else:
        muted = accent

    return {
        "ink": ink,
        "paper": paper,
        "accent": accent,
        "muted": muted,
    }


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------


def resolve_tokens(brand, prs):
    """Build a full tokens dict by deriving defaults and merging explicit values.

    Derived values come from the template (grid) and generic constants
    (type_scale, colour_roles). Explicit values in brand['tokens'] win per
    sub-dict and per key.

    Parameters
    ----------
    brand : dict
        As read from brand.json. May contain 'colours' and 'tokens' keys.
    prs : pptx.Presentation
        The loaded template.

    Returns
    -------
    dict with sub-dicts: grid, type_scale, colour_roles.
    """
    layout_map = brand.get("layout_map", {}) or {}
    layout_indices = [v for v in layout_map.values() if isinstance(v, int)]

    derived = {
        "grid": derive_grid(prs, layout_indices),
        "type_scale": default_type_scale(),
        "colour_roles": resolve_colour_roles(brand.get("colours", {}) or {}),
    }

    explicit = brand.get("tokens", {}) or {}

    result = {}
    for sub in set(derived) | set(explicit):
        result[sub] = {**derived.get(sub, {}), **explicit.get(sub, {})}

    return result
