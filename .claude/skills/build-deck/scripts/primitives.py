"""primitives.py — D-002 carve-out: the ONLY module that emits colour and
coordinate literals to pptx slide objects.

Every colour value and every EMU coordinate written here is taken directly
from the caller-supplied tokens dict.  There are no brand literals in this
module.  The two numeric constants below (EMU_PER_PT, LINE_HEIGHT) are generic
typography conversion factors, not brand values.

Relationship to charts.py: this module plays the same isolation role for
shape/text drawing that charts.py plays for chart images — render.py delegates
all literal-emitting work here so the rest of the renderer stays literal-free.
"""

from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor

# Generic typography constants — the ONLY non-token numeric constants allowed.
EMU_PER_PT = 12700
LINE_HEIGHT = 1.2


class ShapeError(Exception):
    """A primitive that cannot be drawn. render.py turns this into a SpecError."""


def _normalise_hex(value) -> "str | None":
    """Accept '#abc', 'abc', '#aabbcc', 'aabbcc'; return '#RRGGBB' uppercase or None."""
    if not isinstance(value, str):
        return None
    s = value.lstrip("#").strip()
    if len(s) == 3 and all(c in "0123456789abcdefABCDEF" for c in s):
        s = s[0] * 2 + s[1] * 2 + s[2] * 2
    if len(s) == 6 and all(c in "0123456789abcdefABCDEF" for c in s):
        return "#" + s.upper()
    return None


def plan_stat_row(stats, tokens, slide_w, slide_h, region=None) -> list:
    """PURE function — no pptx objects.  Returns a list of element dicts.

    Each element dict has keys:
      role, text, left, top, width, height, font_pt, colour
    where left/top/width/height are in EMU and colour is '#RRGGBB'.
    """
    grid = tokens["grid"]
    ts = tokens["type_scale"]
    roles = tokens["colour_roles"]

    # Validate required keys.
    missing_roles = [k for k in ("accent", "ink") if k not in roles]
    if missing_roles:
        raise ShapeError(f"colour_roles missing: {', '.join(missing_roles)}")
    missing_ts = [k for k in ("display", "caption") if k not in ts]
    if missing_ts:
        raise ShapeError(f"type_scale missing: {', '.join(missing_ts)}")

    N = len(stats)
    if N == 0:
        raise ShapeError("stat_row needs at least one stat")

    margin_x = grid["margin_x"]
    gutter = grid["gutter"]
    baseline = grid["baseline"]

    content_left = margin_x
    content_w = slide_w - 2 * margin_x
    cell_w = (content_w - (N - 1) * gutter) // N

    number_pt = ts["display"]
    label_pt = ts["caption"]

    number_h = round(number_pt * EMU_PER_PT * LINE_HEIGHT)
    label_h = round(label_pt * EMU_PER_PT * LINE_HEIGHT)
    row_block_h = number_h + baseline + label_h

    if region is None:
        band_top = grid["margin_top"]
        band_bottom = slide_h - grid["margin_bottom"]
    else:
        _l, t, _w, h = region
        band_top = t
        band_bottom = t + h

    row_top = band_top + (band_bottom - band_top - row_block_h) // 2

    elements = []
    for i in range(N):
        cell_left = content_left + i * (cell_w + gutter)
        if i < N - 1:
            width_i = cell_w
        else:
            # Last cell absorbs rounding remainder.
            width_i = content_w - (N - 1) * (cell_w + gutter)

        elements.append({
            "role": "stat-number",
            "text": str(stats[i]["value"]),
            "left": cell_left,
            "top": row_top,
            "width": width_i,
            "height": number_h,
            "font_pt": number_pt,
            "colour": roles["accent"],
        })
        elements.append({
            "role": "stat-label",
            "text": str(stats[i]["label"]),
            "left": cell_left,
            "top": row_top + number_h + baseline,
            "width": width_i,
            "height": label_h,
            "font_pt": label_pt,
            "colour": roles["ink"],
        })

    return elements


def draw(slide, elements) -> list:
    """Add a textbox per element to slide; return the list of added shapes."""
    added = []
    for el in elements:
        tb = slide.shapes.add_textbox(
            Emu(el["left"]),
            Emu(el["top"]),
            Emu(el["width"]),
            Emu(el["height"]),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = el["text"]
        run.font.size = Pt(el["font_pt"])
        run.font.color.rgb = RGBColor.from_string(el["colour"].lstrip("#"))
        added.append(tb)
    return added
