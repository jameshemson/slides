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

import math

from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

# Generic typography/layout constants — the ONLY non-token numeric constants
# allowed (generic, not brand values).
EMU_PER_PT = 12700
LINE_HEIGHT = 1.2
# Per-character glyph advance in em (a fraction of the point size) for a
# mixed-case proportional sans face. Digits and capitals run wider than the
# lowercase average (~0.45-0.55em across common sans faces); M/W/@ are the
# widest common glyphs; a space is narrow. _text_em sums these to estimate
# where the renderer's word-wrap will break; deliberately a touch generous so
# a planner errs toward allocating MORE height, never less.
GLYPH_EM = {
    "digit": 0.60,
    "upper": 0.72,
    "wide": 0.85,
    "default": 0.52,
    "space": 0.33,
}
# Optical centre: place the row's vertical centre slightly above the geometric
# centre (~45% from the top). Dead-centre reads as marginally low; the optical
# centre is the conventional resting point for a single focal element.
OPTICAL_CENTRE = 0.45

# Draw order (z): filled panels sit behind connectors, which sit behind text.
# A card is a container box with its text layered on top; the lint permits the
# overlap only because the box is a container (see lint.check_no_overlap), and
# draw() must paint the box first or the text would be hidden. Elements with an
# equal z keep their planned order (stable sort).
_Z_BY_KIND = {"box": 0, "table": 0, "edge": 1, "connector": 1, "icon": 2, "text": 2}


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

    D-408: a stat number never wraps. The planner walks the type ladder
    (display -> title -> h1) and takes the first step at which EVERY value
    fits its cell on one line per the glyph-aware estimator; a value too wide
    even at the h1 floor raises ShapeError. A stepped-down row marks its
    number elements "font_stepped" (the render-note channel). Stat numbers
    carry no hierarchy rank — unchanged.
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

    gutter = grid["gutter"]
    baseline = grid["baseline"]

    content_left, content_w = _content_span(tokens, slide_w, region)
    cell_w = (content_w - (N - 1) * gutter) // N
    # Per-cell widths: the last cell absorbs the rounding remainder (same rule
    # as _even_cells).
    widths = [cell_w] * (N - 1) + [content_w - (N - 1) * (cell_w + gutter)]

    # D-408: a stat number never wraps — the fix for "$8.4M" character-
    # wrapping at display size and overprinting its label. First ladder step
    # where every value is one estimated line in its own cell wins.
    values = [str(s["value"]) for s in stats]
    number_pt = None
    for step in (ts[k] for k in ("display", "title", "h1") if k in ts):
        if all(_wrapped_lines(v, w, step) == 1 for v, w in zip(values, widths)):
            number_pt = step
            break
    if number_pt is None:
        widest = max(values, key=_text_em)
        raise ShapeError(
            f"stat value {widest!r} cannot fit its cell — shorten it or cut stats"
        )
    font_stepped = number_pt != ts["display"]
    label_pt = ts["caption"]

    # ' / ' breaks a label line (the card/panel body convention). Every label
    # box takes the tallest label's line count — wrap-estimated at the cell
    # width, not just explicit breaks — so the row's bottoms align.
    labels = [_split_body(s["label"]) for s in stats]
    label_lines = max(_wrapped_lines(lab, cell_w, label_pt) for lab in labels)

    number_h = round(number_pt * EMU_PER_PT * LINE_HEIGHT)
    label_h = label_lines * round(label_pt * EMU_PER_PT * LINE_HEIGHT)
    row_block_h = number_h + baseline + label_h

    if region is None:
        band_top = grid["margin_top"]
        band_bottom = slide_h - grid["margin_bottom"]
    else:
        _l, t, _w, h = region
        band_top = t
        band_bottom = t + h

    if row_block_h > band_bottom - band_top:
        raise ShapeError(
            f"stat labels wrap to {label_lines} line(s) and the row no longer "
            f"fits its band — shorten the labels or use fewer stats"
        )

    row_top = band_top + round((band_bottom - band_top - row_block_h) * OPTICAL_CENTRE)

    elements = []
    for i in range(N):
        cell_left = content_left + i * (cell_w + gutter)
        width_i = widths[i]

        number_el = {
            "role": "stat-number",
            "text": values[i],
            "left": cell_left,
            "top": row_top,
            "width": width_i,
            "height": number_h,
            "font_pt": number_pt,
            "colour": roles["accent"],
        }
        if font_stepped:
            # The render-note channel: a row that stepped down the ladder to
            # keep its numbers on one line owns up to it in the run summary.
            number_el["font_stepped"] = True
        elements.append(number_el)
        elements.append({
            "role": "stat-label",
            "text": labels[i],
            "left": cell_left,
            "top": row_top + number_h + baseline,
            "width": width_i,
            "height": label_h,
            "font_pt": label_pt,
            "colour": roles["ink"],
        })

    return elements


# --- shared geometry helpers for the box-based primitives --------------------
#
# Every primitive below is a PURE planner: it returns a list of element dicts
# (box/text/connector) and touches no pptx object. Geometry comes from the grid
# tokens; every colour is a colour_roles value. The look is grounded in the
# design research (James's own decks + the Visme guide + Gestalt Common Region):
# equal panels grouped by a shared fill/outline, 3-5 siblings, grey field with
# one accent, hierarchy by size. draw() renders whatever these return.

_STROKE_EMU = EMU_PER_PT  # 1pt hairline panel outline (generic, not a brand value)


def _line_h(font_pt) -> int:
    """Line box height in EMU for a point size (matches plan_stat_row)."""
    return round(font_pt * EMU_PER_PT * LINE_HEIGHT)


def _text_em(text) -> float:
    """Width of `text` in em: the sum of its per-character GLYPH_EM advances.

    Class per character: "MW@" -> wide (M and W also match upper — wide wins),
    0-9 -> digit, A-Z -> upper, space -> space, anything else -> default.
    """
    em = GLYPH_EM
    total = 0.0
    for ch in str(text):
        if ch in "MW@":
            total += em["wide"]
        elif "0" <= ch <= "9":
            total += em["digit"]
        elif "A" <= ch <= "Z":
            total += em["upper"]
        elif ch == " ":
            total += em["space"]
        else:
            total += em["default"]
    return total


def _wrapped_lines(text, width_emu, font_pt) -> int:
    """Estimate the line count of `text` word-wrapped in a box `width_emu` wide.

    The renderer draws every text element with word_wrap on, so a line longer
    than its box wraps at render time — invisible to a planner that counts only
    explicit '\\n' breaks, which is exactly how rendered text used to spill out
    of its box and overlap the element below. This is the planner's stand-in
    for that line-breaker: each '\\n' segment is greedily word-packed against
    an em-width budget (width_emu at font_pt), each word costing its summed
    GLYPH_EM advances (_text_em). A single space-free token wider than the
    budget cannot word-wrap — PowerPoint CHARACTER-wraps it — so it costs
    ceil(token_em / budget_em) lines; the old flat per-character count assumed
    any single token was one line, which is exactly how "$8.4M" at display
    size rendered on two lines and overprinted the label below it. An
    estimate, not font metrics — the render-back check stays the ground
    truth — but it errs generous, so declared heights cover what the renderer
    will actually draw.
    """
    # At least one default glyph per line (the old `max(1, per_line)` guard),
    # so a degenerate width can never divide by zero or loop a token forever.
    budget_em = max(width_emu / (font_pt * EMU_PER_PT), GLYPH_EM["default"])
    space_em = GLYPH_EM["space"]
    total = 0
    for segment in str(text).split("\n"):
        words = segment.split()
        if not words:
            total += 1
            continue
        lines = 0
        current = None  # em width of the open line; None = no open line
        for word in words:
            w_em = _text_em(word)
            if w_em > budget_em:
                # An unbreakable token wider than the line: close the open
                # line, then charge the character-wrap lines PowerPoint will
                # draw. Conservative: its last fragment counts as a full
                # line, so the next word opens a fresh one.
                if current is not None:
                    lines += 1
                    current = None
                lines += math.ceil(w_em / budget_em)
            elif current is None:
                current = w_em
            elif current + space_em + w_em <= budget_em:
                current += space_em + w_em
            else:
                lines += 1
                current = w_em
        if current is not None:
            lines += 1
        total += max(1, lines)
    return total


def _text_h(text, width_emu, font_pt) -> int:
    """Estimated rendered height in EMU of `text` wrapped in a `width_emu` box."""
    return _wrapped_lines(text, width_emu, font_pt) * _line_h(font_pt)


def _require(tokens, ts_keys):
    """Validate the token sub-dicts a primitive needs; return (grid, ts, roles).

    Raises ShapeError naming the missing role or type-scale step — the same
    failure mode plan_stat_row uses, so a thin brand profile fails loudly.
    """
    roles = tokens.get("colour_roles", {}) or {}
    missing = [k for k in ("accent", "ink", "paper", "muted") if k not in roles]
    if missing:
        raise ShapeError(f"colour_roles missing: {', '.join(missing)}")
    ts = tokens.get("type_scale", {}) or {}
    missing_ts = [k for k in ts_keys if k not in ts]
    if missing_ts:
        raise ShapeError(f"type_scale missing: {', '.join(missing_ts)}")
    return tokens["grid"], ts, roles


def _corner_shape(tokens):
    """The autoshape a panel should use for the brand's corner style: a sharp
    brand gets a plain rectangle, everything else the default rounded rectangle."""
    corner = (tokens.get("shape") or {}).get("corner", "rounded")
    return "rect" if str(corner).lower() in ("sharp", "square", "rect") \
        else "rounded_rectangle"


def _content_span(tokens, slide_w, region=None):
    """(left, width) of the horizontal span a primitive fills.

    A placement `region` narrows the span (a block placed in the left columns
    draws in the left columns); with no region it spans margin to margin."""
    if region is not None:
        return region[0], region[2]
    margin_x = tokens["grid"]["margin_x"]
    return margin_x, slide_w - 2 * margin_x


def _band(tokens, slide_h, region):
    """(top, bottom) of the vertical band a primitive fills — the region under a
    title if one was reserved, else the full margin-to-margin band."""
    grid = tokens["grid"]
    if region is None:
        return grid["margin_top"], slide_h - grid["margin_bottom"]
    _l, t, _w, h = region
    return t, t + h


def _even_cells(content_left, content_w, n, gutter):
    """n equal cells across the content width, separated by `gutter`.

    The last cell absorbs the rounding remainder so the row's right edge lands
    exactly on the content margin (same rule as plan_stat_row)."""
    cell_w = (content_w - (n - 1) * gutter) // n
    cells = []
    for i in range(n):
        left = content_left + i * (cell_w + gutter)
        width = cell_w if i < n - 1 else content_w - (n - 1) * (cell_w + gutter)
        cells.append((left, width))
    return cells


def _split_body(text):
    """A card/panel body: ' / ' marks a line break, so a few terse points can
    share one text element without exploding the element count."""
    return "\n".join(part.strip() for part in str(text).split(" / ") if part.strip())


# --- card-grid ---------------------------------------------------------------


def plan_card_grid(cards, tokens, slide_w, slide_h, region=None) -> list:
    """A row of equal panels — 'cluster by message: three or five topics'.

    cards: list of {"label": str, "body": str?, "emphasis": bool?}. One card may
    be marked emphasis to lead (accent fill, reversed text); the rest are paper
    panels with a hairline outline (Gestalt Common Region — the box binds its
    contents). Grouping is the point; hierarchy is by the one emphasised card.
    Count is advisory (card-count, ~3-5): past that, cells narrow until the
    lint's overlap/margin checks refuse the geometry.
    """
    grid, ts, roles = _require(tokens, ("h1", "body"))
    n = len(cards)
    if n == 0:
        raise ShapeError("card-grid needs at least one card")

    content_left, content_w = _content_span(tokens, slide_w, region)
    gutter = grid["gutter"]
    pad = gutter
    baseline = grid["baseline"]
    cells = _even_cells(content_left, content_w, n, gutter)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top

    label_pt, body_pt = ts["h1"], ts["body"]
    # Wrap-estimated at the narrowest cell so every card's declared box covers
    # what the renderer will draw; the tallest wrap sets the shared height so
    # the row's bottoms stay aligned.
    text_w = min(cw for _cl, cw in cells) - 2 * pad
    label_h = max(_text_h(str(c.get("label", "")), text_w, label_pt)
                  for c in cards)
    has_body = any((c.get("body") or "").strip() for c in cards)
    body_alloc = max(
        (_text_h(_split_body(c["body"]), text_w, body_pt)
         for c in cards if (c.get("body") or "").strip()),
        default=0,
    )
    has_icons = any(c.get("icon") for c in cards)
    icon_side = _line_h(label_pt) if has_icons else 0

    inner_h = ((icon_side + baseline) if has_icons else 0) + label_h \
        + (baseline + body_alloc if has_body else 0)
    if inner_h + 2 * pad > band_h:
        raise ShapeError(
            "card text wraps deeper than the band holds — cut card text, "
            "drop a card, or split the slide"
        )
    card_h = inner_h + 2 * pad
    card_top = band_top + round((band_h - card_h) * OPTICAL_CENTRE)

    elements = []
    for i, c in enumerate(cards):
        cl, cw = cells[i]
        emph = bool(c.get("emphasis"))
        panel = {
            "role": "card-panel", "kind": "box", "container": True, "shape": _corner_shape(tokens),
            "left": cl, "top": card_top, "width": cw, "height": card_h,
            "fill": roles["accent"] if emph else roles["paper"],
        }
        if not emph:
            panel["stroke"] = roles["ink"]
            panel["stroke_w"] = _STROKE_EMU
        elements.append(panel)
        text_colour = roles["paper"] if emph else roles["ink"]
        y = card_top + pad
        if has_icons:
            if c.get("icon"):
                elements.append({
                    "role": "card-icon", "kind": "icon", "name": c["icon"],
                    "left": cl + (cw - icon_side) // 2, "top": y,
                    "width": icon_side, "height": icon_side,
                    "colour": roles["paper"] if emph else roles["accent"],
                })
            y += icon_side + baseline
        elements.append({
            "role": "card-label", "text": str(c.get("label", "")),
            "left": cl + pad, "top": y,
            "width": cw - 2 * pad, "height": label_h,
            "font_pt": label_pt, "colour": text_colour, "bold": True,
        })
        body = (c.get("body") or "").strip()
        if has_body and body:
            elements.append({
                "role": "card-body", "text": _split_body(body),
                "left": cl + pad, "top": y + label_h + baseline,
                "width": cw - 2 * pad, "height": body_alloc,
                "font_pt": body_pt, "colour": text_colour,
            })
    return elements


# --- comparison / two-panel --------------------------------------------------


def plan_comparison(sides, tokens, slide_w, slide_h, region=None) -> list:
    """Two panels set side by side so a difference is unmissable.

    sides: exactly two {"header": str, "body": str?, "emphasis": bool?}. A
    comparison must RESOLVE, not just balance — mark the winning side emphasis
    ('order for impact') and it fills with the accent; the design tilts to the
    turn instead of sitting symmetric.
    """
    grid, ts, roles = _require(tokens, ("h1", "body"))
    if len(sides) != 2:
        raise ShapeError("comparison needs exactly two panels")

    content_left, content_w = _content_span(tokens, slide_w, region)
    gutter = grid["gutter"]
    pad = gutter
    baseline = grid["baseline"]
    cells = _even_cells(content_left, content_w, 2, gutter)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top

    header_pt, body_pt = ts["h1"], ts["body"]
    # Wrap-estimated at the panel's text width; the taller side sets the
    # shared panel height so the pair stays level.
    text_w = min(cw for _cl, cw in cells) - 2 * pad
    header_h = max(_text_h(str(s.get("header", "")), text_w, header_pt)
                   for s in sides)
    body_alloc = max(
        (_text_h(_split_body(s["body"]), text_w, body_pt)
         for s in sides if (s.get("body") or "").strip()),
        default=_line_h(body_pt),
    )
    has_icons = any(s.get("icon") for s in sides)
    icon_side = _line_h(header_pt) if has_icons else 0
    inner_h = ((icon_side + baseline) if has_icons else 0) + header_h \
        + baseline + body_alloc
    if inner_h + 2 * pad > band_h:
        raise ShapeError(
            "comparison text wraps deeper than the band holds — cut the "
            "panel bodies or split the slide"
        )
    panel_h = inner_h + 2 * pad
    panel_top = band_top + round((band_h - panel_h) * OPTICAL_CENTRE)

    elements = []
    for i, s in enumerate(sides):
        cl, cw = cells[i]
        emph = bool(s.get("emphasis"))
        panel = {
            "role": "comparison-panel", "kind": "box", "container": True, "shape": _corner_shape(tokens),
            "left": cl, "top": panel_top, "width": cw, "height": panel_h,
            "fill": roles["accent"] if emph else roles["paper"],
        }
        if not emph:
            panel["stroke"] = roles["ink"]
            panel["stroke_w"] = _STROKE_EMU
        elements.append(panel)
        text_colour = roles["paper"] if emph else roles["ink"]
        y = panel_top + pad
        if has_icons:
            if s.get("icon"):
                elements.append({
                    "role": "comparison-icon", "kind": "icon", "name": s["icon"],
                    "left": cl + (cw - icon_side) // 2, "top": y,
                    "width": icon_side, "height": icon_side,
                    "colour": roles["paper"] if emph else roles["accent"],
                })
            y += icon_side + baseline
        elements.append({
            "role": "comparison-header", "text": str(s.get("header", "")),
            "left": cl + pad, "top": y,
            "width": cw - 2 * pad, "height": header_h,
            "font_pt": header_pt, "colour": text_colour, "bold": True,
        })
        body = (s.get("body") or "").strip()
        if body:
            elements.append({
                "role": "comparison-body", "text": _split_body(body),
                "left": cl + pad, "top": y + header_h + baseline,
                "width": cw - 2 * pad, "height": body_alloc,
                "font_pt": body_pt, "colour": text_colour,
            })
    return elements


# --- process / flow ----------------------------------------------------------


def plan_process(steps, tokens, slide_w, slide_h, region=None) -> list:
    """3 (up to 5) numbered steps left to right, joined by arrows.

    steps: list of {"label": str, "detail": str?}, numbered by order. Each step
    is a paper box with a big accent number, a bold label, and an optional light
    detail line; a muted arrow bridges the gap to the next. This is James's real
    'Plan -> Create -> Deliver' pattern, deliberately NOT a SmartArt chevron
    ribbon. Count is advisory (process-count, ~3-5); past that the arrows and
    cells shrink until the lint refuses the geometry.
    """
    grid, ts, roles = _require(tokens, ("h1", "body", "caption"))
    n = len(steps)
    if n == 0:
        raise ShapeError("process needs at least one step")

    content_left, content_w = _content_span(tokens, slide_w, region)
    gutter = grid["gutter"]
    pad = gutter
    baseline = grid["baseline"]
    cells = _even_cells(content_left, content_w, n, gutter)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top

    num_pt, label_pt, detail_pt = ts["h1"], ts["body"], ts["caption"]
    num_h = _line_h(num_pt)
    # Wrap-estimated at the narrowest step's text width; the deepest wrap sets
    # the shared heights so every box stays level.
    text_w = min(cw for _cl, cw in cells) - 2 * pad
    label_h = max(_text_h(str(s.get("label", "")), text_w, label_pt)
                  for s in steps)
    has_detail = any((s.get("detail") or "").strip() for s in steps)
    detail_h = max(
        (_text_h(_split_body(s["detail"]), text_w, detail_pt)
         for s in steps if (s.get("detail") or "").strip()),
        default=0,
    )
    inner_h = num_h + baseline + label_h + (baseline + detail_h if has_detail else 0)
    if inner_h + 2 * pad > band_h:
        raise ShapeError(
            "process text wraps deeper than the band holds — cut the step "
            "labels/details or use fewer steps"
        )
    box_h = inner_h + 2 * pad
    box_top = band_top + round((band_h - box_h) * OPTICAL_CENTRE)

    elements = []
    for i, s in enumerate(steps):
        cl, cw = cells[i]
        elements.append({
            "role": "process-step", "kind": "box", "container": True, "shape": _corner_shape(tokens),
            "left": cl, "top": box_top, "width": cw, "height": box_h,
            "fill": roles["paper"], "stroke": roles["ink"], "stroke_w": _STROKE_EMU,
        })
        if s.get("icon"):
            # An icon takes the number's slot (centred), so element count is flat.
            iside = max(1, min(num_h, cw - 2 * pad))
            elements.append({
                "role": "process-icon", "kind": "icon", "name": s["icon"],
                "left": cl + (cw - iside) // 2, "top": box_top + pad,
                "width": iside, "height": iside, "colour": roles["accent"],
            })
        else:
            elements.append({
                "role": "process-number", "text": str(i + 1),
                "left": cl + pad, "top": box_top + pad,
                "width": cw - 2 * pad, "height": num_h,
                "font_pt": num_pt, "colour": roles["accent"], "bold": True,
            })
        elements.append({
            "role": "process-label", "text": str(s.get("label", "")),
            "left": cl + pad, "top": box_top + pad + num_h + baseline,
            "width": cw - 2 * pad, "height": label_h,
            "font_pt": label_pt, "colour": roles["ink"], "bold": True,
        })
        detail = (s.get("detail") or "").strip()
        if has_detail and detail:
            elements.append({
                "role": "process-detail", "text": _split_body(detail),
                "left": cl + pad,
                "top": box_top + pad + num_h + baseline + label_h + baseline,
                "width": cw - 2 * pad, "height": detail_h,
                "font_pt": detail_pt, "colour": roles["ink"],
            })
        if i < n - 1:
            gap_left = cl + cw
            gap_right = cells[i + 1][0]
            inset = (gap_right - gap_left) // 6
            arrow_top = box_top + (box_h - label_h) // 2
            elements.append({
                "role": "process-connector", "kind": "connector",
                "shape": "right_arrow",
                "left": gap_left + inset, "top": arrow_top,
                "width": (gap_right - gap_left) - 2 * inset, "height": label_h,
                "fill": roles["ink"],
            })
    return elements


# --- timeline / milestones ---------------------------------------------------


def plan_timeline(nodes, tokens, slide_w, slide_h, region=None) -> list:
    """Dated milestones as dots on a rail — Start ...o...o...o... End.

    nodes: list of {"date": str, "event": str, "emphasis": bool?}. One milestone
    is the turn: mark it emphasis and it gets a larger accent dot and a bold
    label while the rest stay muted — a timeline still obeys grey-push + one
    accent, so it reads as a sequence with a hero beat, not an even dotted rule.
    Count is advisory (timeline-count, ~3-6); at extreme counts the dots
    collide and the lint's overlap check refuses the slide.
    """
    grid, ts, roles = _require(tokens, ("body",))
    n = len(nodes)
    if n == 0:
        raise ShapeError("timeline needs at least one milestone")

    content_left, content_w = _content_span(tokens, slide_w, region)
    gutter = grid["gutter"]
    baseline = grid["baseline"]
    cells = _even_cells(content_left, content_w, n, gutter)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top

    label_pt = ts["body"]
    line_h = _line_h(label_pt)
    # Each label is date-over-event; wrap-estimate both at the cell width and
    # let the deepest label set the shared height so the rail stays level.
    texts = []
    for nd in nodes:
        date = str(nd.get("date", "")).strip()
        event = str(nd.get("event", "")).strip()
        texts.append(f"{date}\n{event}" if date and event else (date or event))
    label_w = min(cw for _cl, cw in cells)
    label_h = max(_text_h(t, label_w, label_pt) for t in texts)
    dot_d = line_h
    emph_dot_d = dot_d + baseline
    rail_h = max(EMU_PER_PT // 2, dot_d // 8)

    block_h = emph_dot_d + baseline + label_h
    if block_h > band_h:
        raise ShapeError(
            "timeline labels wrap deeper than the band holds — shorten the "
            "events or use fewer milestones"
        )
    block_top = band_top + round((band_h - block_h) * OPTICAL_CENTRE)
    rail_y = block_top + emph_dot_d // 2
    label_top = rail_y + emph_dot_d // 2 + baseline

    elements = []
    dot_edges = []  # (left, right) of each drawn dot, for exact rail seams
    for i, nd in enumerate(nodes):
        cl, cw = cells[i]
        centre = cl + cw // 2
        emph = bool(nd.get("emphasis"))
        d = emph_dot_d if emph else dot_d
        dleft = centre - d // 2
        dot_edges.append((dleft, dleft + d))
        elements.append({
            "role": "timeline-dot", "kind": "box", "shape": "oval",
            "left": dleft, "top": rail_y - d // 2,
            "width": d, "height": d,
            "fill": roles["accent"] if emph else roles["ink"],
        })
        elements.append({
            "role": "timeline-label", "text": texts[i],
            "left": cl, "top": label_top, "width": cw, "height": label_h,
            "font_pt": label_pt, "align": "center",
            "colour": roles["accent"] if emph else roles["ink"], "bold": emph,
        })
    for i in range(n - 1):
        left = dot_edges[i][1]        # right edge of dot i
        right = dot_edges[i + 1][0]   # left edge of dot i+1
        if right > left:
            elements.append({
                "role": "timeline-rail", "kind": "connector", "shape": "rect",
                "left": left, "top": rail_y - rail_h // 2,
                "width": right - left, "height": rail_h,
                "fill": roles["ink"],
            })
    return elements


# --- freeform ----------------------------------------------------------------


def _subrect(base, placement, grid):
    """A sub-rectangle of `base` for a {cols, rows} placement on its 12x12 grid.

    Mirrors render._place_region but relative to whatever band the freeform
    block was given, so element placement composes under block placement. A
    small inset keeps adjacent elements from touching.

    REQ-204/D-409: an {x, y} percent placement resolves as an exact band
    fraction instead — no insets, the author owns the geometry. An axis left
    unspecified spans the full band, as with single-axis grid spans."""
    bl, bt, bw, bh = base
    x, y = placement.get("x"), placement.get("y")
    if x or y:
        if x:
            left, width = bl + round(x[0] * bw), round((x[1] - x[0]) * bw)
        else:
            left, width = bl, bw
        if y:
            top, height = bt + round(y[0] * bh), round((y[1] - y[0]) * bh)
        else:
            top, height = bt, bh
        return (left, top, max(1, width), max(1, height))
    cols_n = grid.get("columns", 12) or 12
    rows_n = 12
    cols = placement.get("cols")
    rows = placement.get("rows")
    left = bl + (cols[0] - 1) * bw // cols_n if cols else bl
    right = bl + cols[1] * bw // cols_n if cols else bl + bw
    top = bt + (rows[0] - 1) * bh // rows_n if rows else bt
    bottom = bt + rows[1] * bh // rows_n if rows else bt + bh
    pad_x = grid.get("gutter", 0) // 2
    pad_y = grid.get("baseline", 0)
    return (left + pad_x, top + pad_y,
            max(1, (right - pad_x) - (left + pad_x)),
            max(1, (bottom - pad_y) - (top + pad_y)))


def plan_freeform(elements, tokens, slide_w, slide_h, region=None) -> list:
    """The escape hatch: place token-bound elements the named primitives don't
    cover — a matrix, a quadrant, a node graph, an annotated layout.

    Freedom in the arrangement, the SAME guardrails as every other composed
    block: each element's colour is a role name (ink/paper/accent/muted) and
    each text size a scale name (display/h1/body/caption), both resolved to the
    brand's tokens here, and every element still passes the mechanical lint
    (on-token, on-grid, no overlap outside a container, under the cap). What the
    lint does NOT prove is that the arrangement is *well* composed — that is the
    author's judgement, nudged by the one freeform advisory (grey-push).

    Each element dict (parsed by render._parse_freeform_element) carries:
      kind: box|panel|text|arrow|dot|line, a placement {cols,rows}, and either
      a `fill`(+`stroke`) / `colour` role name, plus `scale`+`text` for text.
    """
    grid, ts, roles = _require(tokens, ())
    if not elements:
        raise ShapeError("freeform needs at least one element")
    if region is None:
        mx = grid["margin_x"]
        band = (mx, grid["margin_top"], slide_w - 2 * mx,
                slide_h - grid["margin_top"] - grid["margin_bottom"])
    else:
        band = region

    out = []
    for el in elements:
        if el.get("full_bleed"):
            # REQ-204: a full-bleed box paints the whole slide, margins
            # included; the flag rides the element so lint's margins rule can
            # carve it out. Only box/panel parse with the flag (render.py).
            l, t, w, h = 0, 0, slide_w, slide_h
        else:
            l, t, w, h = _subrect(band, el["placement"], grid)
        kind = el["kind"]
        if kind in ("box", "panel"):
            box = {
                "role": "freeform-panel", "kind": "box", "container": True, "shape": _corner_shape(tokens),
                "left": l, "top": t, "width": w, "height": h,
                "fill": roles[el["fill"]],
            }
            if el.get("full_bleed"):
                # A background wash meets the slide edge squarely — a rounded
                # corner would show paper wedges at all four corners.
                box["full_bleed"] = True
                box["shape"] = "rect"
            if el.get("stroke"):
                box["stroke"] = roles[el["stroke"]]
                box["stroke_w"] = _STROKE_EMU
            out.append(box)
        elif kind == "text":
            # The author placed this box; middle-anchored text that wraps past
            # it spills BOTH ways into the neighbours, so refuse a placement
            # that cannot hold its text rather than render the spill.
            font_pt = ts[el["scale"]]
            needed = _wrapped_lines(el["text"], w, font_pt)
            if needed * _line_h(font_pt) > h:
                snippet = str(el["text"])[:40]
                raise ShapeError(
                    f"freeform text {snippet!r} wraps to ~{needed} line(s) at "
                    f"{el['scale']} size and overflows its placement — give it "
                    f"more rows, a smaller scale, or shorter text"
                )
            text_el = {
                "role": "freeform-text", "text": el["text"],
                "left": l, "top": t, "width": w, "height": h,
                "font_pt": font_pt, "colour": roles[el["colour"]],
                "anchor": "middle",
            }
            # A hero-scale line (display/h1) that wraps still fits its box — the
            # overflow check above already raised if it didn't — but multi-line
            # hero text reads as a wrapped paragraph, not a hero. Stamp it so the
            # run summary can own up, the way a stepped-down stat row does.
            if el["scale"] in ("display", "h1") and needed > 1:
                text_el["hero_wrapped"] = needed
            out.append(text_el)
        elif kind == "arrow":
            out.append({
                "role": "freeform-arrow", "kind": "connector",
                "shape": "right_arrow",
                "left": l, "top": t, "width": w, "height": h,
                "fill": roles[el["colour"]],
            })
        elif kind == "dot":
            out.append({
                "role": "freeform-dot", "kind": "box", "shape": "oval",
                "left": l, "top": t, "width": w, "height": h,
                "fill": roles[el["colour"]],
            })
        elif kind == "line":
            lh = min(h, EMU_PER_PT * 2)  # a hairline divider, centred in its cell
            out.append({
                "role": "freeform-line", "kind": "connector", "shape": "rect",
                "left": l, "top": t + (h - lh) // 2, "width": w, "height": lh,
                "fill": roles[el["colour"]],
            })
        elif kind == "icon":
            # A square icon centred in its placement cell. render.py resolves the
            # element to a recoloured PNG after the lint clears its token colour.
            side = min(w, h)
            out.append({
                "role": "freeform-icon", "kind": "icon", "name": el["name"],
                "left": l + (w - side) // 2, "top": t + (h - side) // 2,
                "width": side, "height": side,
                "colour": roles[el["colour"]],
            })
    return out


# --- hierarchy / tree --------------------------------------------------------


def plan_tree(root, tokens, slide_w, slide_h, region=None) -> list:
    """A tidy hierarchy: token box nodes with text (and optional icon), joined by
    elbow edges parent -> child.

    `root` is a nested node dict {label, emphasis?, icon?, children:[...]}. Layout
    comes from tidytree (deterministic, non-overlapping for small trees). Node
    boxes sit in per-depth rows; each edge is ONE elbow connector. One box per
    node keeps same-depth nodes gutter-separated; the lint exempts edges from
    the overlap rule, so edges may route between rows freely. Node count and
    depth are advisory (tree-count ~3-8, tree-depth <=3); a genuinely oversized
    tree hits the width guard below or the lint's element cap.
    """
    import tidytree  # noqa: PLC0415 — tree slides only

    grid, ts, roles = _require(tokens, ("h1", "body"))
    rows, max_x, max_depth = tidytree.layout(root)
    has_icons = any((nd.get("icon") for nd, _, _ in rows))

    content_left, content_w = _content_span(tokens, slide_w, region)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top
    gutter, baseline = grid["gutter"], grid["baseline"]
    label_pt = ts["body"]
    label_h = _line_h(label_pt)

    slots = max_x + 1.0
    slot_w = content_w / slots
    node_w = int(slot_w - gutter)
    if node_w < gutter:
        raise ShapeError("tree is too wide to fit; fewer nodes per level")

    n_levels = max_depth + 1
    row_h = band_h // n_levels
    icon_side = label_h if has_icons else 0
    node_h = max(label_h + baseline, min(row_h - baseline, 2 * label_h + baseline))
    pad = gutter // 2

    def cx(x):
        return int(content_left + (x + 0.5) * slot_w)

    def top_of(d):
        return band_top + d * row_h + (row_h - node_h) // 2

    elements = []
    geom = {}  # id(node) -> (centre_x, top, node_h)
    for node, x, d in rows:
        c = cx(x)
        left = c - node_w // 2
        t = top_of(d)
        emph = bool(node.get("emphasis"))
        panel = {
            "role": "tree-node", "kind": "box", "container": True, "shape": _corner_shape(tokens),
            "left": left, "top": t, "width": node_w, "height": node_h,
            "fill": roles["accent"] if emph else roles["paper"],
        }
        if not emph:
            panel["stroke"] = roles["ink"]
            panel["stroke_w"] = _STROKE_EMU
        elements.append(panel)
        text_colour = roles["paper"] if emph else roles["ink"]
        iside = max(1, min(icon_side, node_w - 2 * pad,
                           node_h - label_h - 2 * pad)) if node.get("icon") else 0
        # The tree's rows fix the node box, so the label must fit IT.
        if _text_h(str(node["label"]), node_w - 2 * pad, label_pt) \
                > node_h - 2 * pad - iside:
            raise ShapeError(
                f"tree node label {str(node['label'])!r} wraps deeper than its "
                f"box — shorten the label or prune the tree"
            )
        if node.get("icon"):
            elements.append({
                "role": "tree-icon", "kind": "icon", "name": node["icon"],
                "left": c - iside // 2, "top": t + pad, "width": iside, "height": iside,
                "colour": roles["accent"] if emph else roles["ink"],
            })
            elements.append({
                "role": "tree-label", "text": str(node["label"]),
                "left": left + pad, "top": t + pad + iside,
                "width": node_w - 2 * pad, "height": node_h - 2 * pad - iside,
                "font_pt": label_pt, "colour": text_colour,
                "align": "center", "anchor": "middle", "bold": emph,
            })
        else:
            elements.append({
                "role": "tree-label", "text": str(node["label"]),
                "left": left + pad, "top": t + pad,
                "width": node_w - 2 * pad, "height": node_h - 2 * pad,
                "font_pt": label_pt, "colour": text_colour,
                "align": "center", "anchor": "middle", "bold": emph,
            })
        geom[id(node)] = (c, t)

    for node, x, d in rows:
        pc, pt_ = geom[id(node)]
        for child in (node.get("children") or []):
            cc, ct = geom[id(child)]
            y1 = pt_ + node_h
            elements.append({
                "role": "tree-edge", "kind": "edge", "colour": roles["ink"],
                "x1": pc, "y1": y1, "x2": cc, "y2": ct,
                # a bounding box so the within-margins lint has geometry to check
                "left": min(pc, cc), "top": y1,
                "width": max(1, abs(cc - pc)), "height": max(1, ct - y1),
            })
    return elements


# --- icon-list (icons as bullets) --------------------------------------------


def plan_icon_list(rows, tokens, slide_w, slide_h, region=None) -> list:
    """A list where an accent icon replaces the bullet: icon left, text right.

    rows: list of {"icon": name, "text": str}. Icons are the one accent (a
    consistent marker, not a rainbow); the text is ink. Rows stack in the band,
    compressing as the count grows (advisory iconlist-count, ~3-6). Icons
    resolve to PNGs in render.py after the lint clears them.
    """
    grid, ts, roles = _require(tokens, ("body",))
    n = len(rows)
    if n == 0:
        raise ShapeError("icon-list needs at least one row")

    content_left, content_w = _content_span(tokens, slide_w, region)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top
    baseline, gutter = grid["baseline"], grid["gutter"]
    text_pt = ts["body"]
    line_h = _line_h(text_pt)
    icon_side = line_h
    text_left = content_left + icon_side + gutter
    text_w = content_w - icon_side - gutter
    # Every row takes the deepest wrapped text's height so the rows align.
    text_h = max(_text_h(str(r["text"]), text_w, text_pt) for r in rows)
    row_h = text_h + baseline
    if row_h * n > band_h:
        row_h = band_h // n
        if row_h < text_h:
            raise ShapeError(
                "icon-list text wraps deeper than the band holds — cut the "
                "row text or use fewer rows"
            )
    block_h = row_h * n
    top0 = band_top + round((band_h - block_h) * OPTICAL_CENTRE)

    elements = []
    for i, r in enumerate(rows):
        rt = top0 + i * row_h
        elements.append({
            "role": "iconlist-icon", "kind": "icon", "name": r["icon"],
            "left": content_left, "top": rt + (row_h - icon_side) // 2,
            "width": icon_side, "height": icon_side, "colour": roles["accent"],
        })
        elements.append({
            "role": "iconlist-text", "text": str(r["text"]),
            "left": text_left, "top": rt + (row_h - text_h) // 2,
            "width": text_w, "height": text_h,
            "font_pt": text_pt, "colour": roles["ink"], "anchor": "middle",
        })
    return elements


# --- cycle -------------------------------------------------------------------


def plan_cycle(steps, tokens, slide_w, slide_h, region=None) -> list:
    """A loop of 2-6 stages on a circle, joined by edges around the ring.

    steps: list of {"label": str}. Nodes are placed on a circle (top, clockwise);
    each edge runs node -> next -> ... -> back to the first, so the loop closes.
    Node sizing is tied to the ring spacing so nodes never overlap; stage count
    is advisory (cycle-count, ~3-6) — a crowded ring just gets denser.
    """
    grid, ts, roles = _require(tokens, ("body",))
    n = len(steps)
    if n < 2:
        raise ShapeError("cycle needs at least 2 stages")

    content_left, content_w = _content_span(tokens, slide_w, region)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top
    baseline = grid["baseline"]
    label_pt = ts["body"]
    line_h = _line_h(label_pt)

    r = int(min(content_w, band_h) * 0.34)
    spacing = 2 * r * math.sin(math.pi / n)          # min adjacent centre gap
    node_w = max(2 * grid["gutter"], min(content_w // 4, int(spacing * 0.7)))
    node_h = max(line_h, min(2 * line_h + baseline, int(spacing * 0.55)))
    cx = content_left + content_w // 2
    cy = band_top + band_h // 2

    centres = []
    for i in range(n):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        centres.append((cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang))))

    elements = []
    for i, (px, py) in enumerate(centres):
        left, top = px - node_w // 2, py - node_h // 2
        # The ring spacing fixes the node box, so the label must fit IT.
        label = str(steps[i].get("label", ""))
        if _text_h(label, node_w, label_pt) > node_h:
            raise ShapeError(
                f"cycle stage label {label!r} wraps deeper than its node — "
                f"shorten the label or use fewer stages"
            )
        elements.append({
            "role": "cycle-node", "kind": "box", "container": True,
            "shape": _corner_shape(tokens),
            "left": left, "top": top, "width": node_w, "height": node_h,
            "fill": roles["paper"], "stroke": roles["ink"], "stroke_w": _STROKE_EMU,
        })
        elements.append({
            "role": "cycle-label", "text": label,
            "left": left, "top": top, "width": node_w, "height": node_h,
            "font_pt": label_pt, "colour": roles["ink"],
            "align": "center", "anchor": "middle",
        })

    node_r = max(node_w, node_h) // 2
    for i in range(n):
        ax, ay = centres[i]
        bx, by = centres[(i + 1) % n]
        dist = math.hypot(bx - ax, by - ay) or 1
        ux, uy = (bx - ax) / dist, (by - ay) / dist
        sx, sy = int(ax + node_r * ux), int(ay + node_r * uy)
        ex, ey = int(bx - node_r * ux), int(by - node_r * uy)
        elements.append({
            "role": "cycle-edge", "kind": "edge", "colour": roles["ink"],
            "x1": sx, "y1": sy, "x2": ex, "y2": ey,
            "left": min(sx, ex), "top": min(sy, ey),
            "width": max(1, abs(ex - sx)), "height": max(1, abs(ey - sy)),
        })
    return elements


# --- matrix (2x2) ------------------------------------------------------------


def plan_matrix(spec, tokens, slide_w, slide_h, region=None) -> list:
    """A 2x2 quadrant matrix: four labelled panels, optional axis captions.

    spec: {"quadrants": [TL, TR, BL, BR]} where each is {label, body?, emphasis?},
    plus optional "x" (caption below) and "y" (caption above). One quadrant may be
    marked emphasis to lead. The two dimensions are conveyed by the captions and
    the quadrant labels.
    """
    grid, ts, roles = _require(tokens, ("h1", "body"))
    quads = spec.get("quadrants", [])
    if len(quads) != 4:
        raise ShapeError("matrix needs exactly four quadrants (TL, TR, BL, BR)")

    content_left, content_w = _content_span(tokens, slide_w, region)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top
    gutter = grid["gutter"]
    pad = gutter
    baseline = grid["baseline"]
    label_pt, body_pt, cap_pt = ts["h1"], ts["body"], ts["body"]
    cap_h = _line_h(cap_pt)

    xlab = (spec.get("x") or "").strip()
    ylab = (spec.get("y") or "").strip()
    top_strip = (cap_h + baseline) if ylab else 0
    bot_strip = (cap_h + baseline) if xlab else 0

    grid_top = band_top + top_strip
    grid_h = band_h - top_strip - bot_strip
    cols = _even_cells(content_left, content_w, 2, gutter)
    cell_h = (grid_h - gutter) // 2
    row_tops = [grid_top, grid_top + cell_h + gutter]
    coords = [(0, 0), (1, 0), (0, 1), (1, 1)]  # TL, TR, BL, BR

    # The 2x2 geometry fixes the cell, so text must fit IT: wrap-estimate the
    # labels and bodies and refuse the slide when a cell cannot hold its text.
    text_w = min(cw for _cl, cw in cols) - 2 * pad
    label_h = max(_text_h(str(q.get("label", "")), text_w, label_pt)
                  for q in quads)
    if cell_h < 2 * pad + label_h:
        raise ShapeError(
            "matrix needs more room; shorten the quadrant labels, drop the "
            "axis labels, or use a full slide"
        )
    avail = cell_h - 2 * pad - label_h - baseline
    body_alloc = max(
        (_text_h(_split_body(q["body"]), text_w, body_pt)
         for q in quads if (q.get("body") or "").strip()),
        default=0,
    )
    if body_alloc > max(avail, 0):
        raise ShapeError(
            "matrix quadrant text wraps deeper than its cell holds — cut the "
            "quadrant bodies or drop the axis labels"
        )
    elements = []
    if ylab:
        elements.append({
            "role": "matrix-axis", "text": ylab, "left": content_left,
            "top": band_top, "width": content_w, "height": cap_h,
            "font_pt": cap_pt, "colour": roles["muted"], "align": "center",
        })
    if xlab:
        elements.append({
            "role": "matrix-axis", "text": xlab, "left": content_left,
            "top": band_bottom - cap_h, "width": content_w, "height": cap_h,
            "font_pt": cap_pt, "colour": roles["muted"], "align": "center",
        })
    for q, (col, row) in zip(quads, coords):
        cl, cw = cols[col]
        ct = row_tops[row]
        emph = bool(q.get("emphasis"))
        panel = {
            "role": "matrix-cell", "kind": "box", "container": True,
            "shape": _corner_shape(tokens),
            "left": cl, "top": ct, "width": cw, "height": cell_h,
            "fill": roles["accent"] if emph else roles["paper"],
        }
        if not emph:
            panel["stroke"] = roles["ink"]
            panel["stroke_w"] = _STROKE_EMU
        elements.append(panel)
        tc = roles["paper"] if emph else roles["ink"]
        elements.append({
            "role": "matrix-label", "text": str(q.get("label", "")),
            "left": cl + pad, "top": ct + pad, "width": cw - 2 * pad,
            "height": label_h, "font_pt": label_pt, "colour": tc, "bold": True,
        })
        body = (q.get("body") or "").strip()
        if body and body_alloc:
            elements.append({
                "role": "matrix-body", "text": _split_body(body),
                "left": cl + pad, "top": ct + pad + label_h + baseline,
                "width": cw - 2 * pad, "height": body_alloc,
                "font_pt": body_pt, "colour": tc,
            })
    return elements


# --- table (native pptx GraphicFrame) ----------------------------------------

# Characters stripped before deciding a data cell is numeric: currency, percent,
# thousands separators, decimal points, and both a plain hyphen and the Unicode
# minus sign. Generic formatting glyphs, not brand values.
_NUM_STRIP = "$%,.+-−"
# Trailing magnitude suffixes that still leave a value numeric ("$1.2M", "40k").
_MAG_SUFFIX = "kmb"


def _is_numeric_cell(value) -> bool:
    """True when a data cell reads as a number (money/percent/magnitude).

    Strips currency/percent/sign/separator glyphs and one trailing magnitude
    suffix (k/M/B, case-insensitive); what remains must be all digits and
    non-empty. '$1.2M' and '4%' are numeric; 'Revenue' is not."""
    t = str(value).strip()
    for ch in _NUM_STRIP:
        t = t.replace(ch, "")
    if t and t[-1].lower() in _MAG_SUFFIX:
        t = t[:-1]
    return bool(t) and t.isdigit()


def plan_table(table, tokens, slide_w, slide_h, region=None) -> list:
    """A native PowerPoint table (ONE GraphicFrame), styled entirely from tokens.

    `table`: {"header": [str], "rows": [{"cells": [str], "emphasis": bool}, ...]}.
    Returns EXACTLY ONE element dict (kind "table", role "table-grid"): unlike the
    box/text primitives it is not exploded into per-cell shapes (D-001) — a 5x8
    table would eat the whole element cap and lose native editability. Its colours
    and sizes therefore travel as vectors (`fills`, `text_colours`, `font_pts`)
    for the lint (D-008), and per-column alignment as `col_aligns` (D-009).

    Styling (D-002): header = ink fill + paper bold text; data rows = paper fill +
    ink text with a muted bottom hairline (except the last); an emphasis row = accent
    fill + paper text. Column and row counts are advisory (table-column-count ~5,
    table-count ~6 rows); the band-fit guard (D-004) is geometric — a long table
    first steps its type down to caption to fit, and only when even caption
    cannot fit does it raise ShapeError, which render.py turns into a named
    SpecError. A one-column table stays a hard error (it is a list, not a table).
    """
    grid, ts, roles = _require(tokens, ("body",))
    header = list(table.get("header", []))
    rows = list(table.get("rows", []))
    ncols = len(header)
    nrows = len(rows)

    if ncols < 2:
        raise ShapeError(
            "a one-column table is a list, not a table; use icon-list or bullets"
        )
    if nrows < 1:
        raise ShapeError("table needs at least one data row")

    ink, paper, accent = roles["ink"], roles["paper"], roles["accent"]
    stroke = roles.get("muted") or ink  # the row hairline (D-008 scalar key)

    content_left, content_w = _content_span(tokens, slide_w, region)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top

    # Row height: one line box at cell_pt plus a baseline of vertical padding.
    # cell_pt is the ONE source of the table's type size — the lint vector
    # (font_pts) and the draw path (cell_pt) both read it, so they cannot
    # diverge (D-008). Band-fit (D-004): header + data rows must fit the
    # vertical band at body size; if not, step down to caption (still on the
    # type scale, so the lint stays green) before giving up.
    cell_pt = ts["body"]
    font_stepped = False
    row_h = _line_h(cell_pt) + grid["baseline"]
    total_h = (1 + nrows) * row_h
    if total_h > band_h:
        caption_pt = ts.get("caption")
        if caption_pt and caption_pt < cell_pt:
            cell_pt = caption_pt
            font_stepped = True
            row_h = _line_h(cell_pt) + grid["baseline"]
            total_h = (1 + nrows) * row_h
    if total_h > band_h:
        fits = max(0, band_h // row_h - 1)
        at_size = "even at caption size" if font_stepped else "in the band"
        raise ShapeError(
            f"table needs {1 + nrows} rows but only {fits} rows fit {at_size}; "
            f"cut rows or split the slide"
        )

    # Optical-centre placement, same as the box primitives.
    top = band_top + round((band_h - total_h) * OPTICAL_CENTRE)

    # Per-column numeric alignment (D-009): every data cell numeric -> right.
    col_aligns = []
    for c in range(ncols):
        column = [r.get("cells", [])[c] for r in rows if c < len(r.get("cells", []))]
        numeric = bool(column) and all(_is_numeric_cell(v) for v in column)
        col_aligns.append("right" if numeric else "left")

    # Colour/size vectors the lint validates (D-008): list every distinct value.
    fills, text_colours = [], []

    def _add(lst, v):
        if v not in lst:
            lst.append(v)

    _add(fills, ink)          # header band
    _add(text_colours, paper)  # header text
    emphasis_rows = []
    for i, r in enumerate(rows):
        if r.get("emphasis"):
            emphasis_rows.append(i)
            _add(fills, accent)
            _add(text_colours, paper)
        else:
            _add(fills, paper)
            _add(text_colours, ink)

    return [{
        "role": "table-grid",
        "kind": "table",
        "text": "table: " + " | ".join(header),
        "left": content_left,
        "top": top,
        "width": content_w,
        "height": total_h,
        # D-008 vector keys (the lint checks every entry on a table element).
        "fills": fills,
        "text_colours": text_colours,
        "font_pts": [cell_pt],
        "stroke": stroke,          # scalar hairline colour (existing lint checks it)
        "col_aligns": col_aligns,
        # Advisory-rule fields (T-010 reads these) + payload the draw path needs.
        "header": header,
        "rows": [list(r.get("cells", [])) for r in rows],
        "emphasis_rows": emphasis_rows,
        # Explicit draw colours/size so _add_table needs only this element.
        "header_fill": ink, "header_text": paper,
        "row_fill": paper, "row_text": ink,
        "emph_fill": accent, "emph_text": paper,
        "cell_pt": cell_pt,
        "font_stepped": font_stepped,
        "cell_margin": grid["gutter"] // 2,
    }]


# Autoshape names a box element may request via its "shape" key. Generic
# geometry, not brand values. Default is a rounded rectangle (the card/panel).
_SHAPE_BY_NAME = {
    "rect": MSO_SHAPE.RECTANGLE,
    "rectangle": MSO_SHAPE.RECTANGLE,
    "rounded": MSO_SHAPE.ROUNDED_RECTANGLE,
    "rounded_rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
    "oval": MSO_SHAPE.OVAL,
    "chevron": MSO_SHAPE.CHEVRON,
    "right_arrow": MSO_SHAPE.RIGHT_ARROW,
    "line": MSO_SHAPE.RECTANGLE,
}

_ALIGN_BY_NAME = {
    "left": PP_ALIGN.LEFT,
    "center": PP_ALIGN.CENTER,
    "centre": PP_ALIGN.CENTER,
    "right": PP_ALIGN.RIGHT,
}

_ANCHOR_BY_NAME = {
    "top": MSO_ANCHOR.TOP,
    "middle": MSO_ANCHOR.MIDDLE,
    "bottom": MSO_ANCHOR.BOTTOM,
}


def draw(slide, elements) -> list:
    """Add one shape per element to `slide`; return the added shapes.

    An element's `kind` selects the shape: "box"/"connector" draw a filled
    autoshape (card, panel, step, connector), anything else (the default, and
    every stat-row element) draws a text box. Elements are painted in z-order
    (boxes behind connectors behind text) so a card's text lands on top of its
    panel; within a z-band the planned order is kept (stable sort). Every
    colour written here comes from the element dict, which the caller filled
    from brand tokens — this module still emits no brand literal of its own.

    An element may carry an optional `name` stamp (e.g. "slides-field:Title",
    "slides-block:...") — the revise round trip reads this back off the
    rendered shape to match it to its spec element, so every shape-creating
    helper below writes it onto the shape it creates.
    """
    ordered = sorted(
        elements, key=lambda el: _Z_BY_KIND.get(el.get("kind", "text"), 2)
    )
    added = []
    for el in ordered:
        kind = el.get("kind")
        if kind in ("box", "connector"):
            added.append(_add_box(slide, el))
        elif kind == "table":
            added.append(_add_table(slide, el))
        elif kind == "edge":
            added.append(_add_edge(slide, el))
        elif kind == "icon":
            shp = _add_icon(slide, el)
            if shp is not None:
                added.append(shp)
        else:
            added.append(_add_text(slide, el))
    return added


def _add_edge(slide, el):
    """Draw one tree edge as a single elbow connector, parent -> child.

    An elbow connector is ONE shape per edge (so a tree stays under the element
    cap), routed by PowerPoint between the two points. The line colour is a
    token; the lint exempts connectors/edges from the overlap rule because a
    1-D line crossing a box is not a composition fault."""
    conn = slide.shapes.add_connector(
        MSO_CONNECTOR.ELBOW,
        Emu(el["x1"]), Emu(el["y1"]), Emu(el["x2"]), Emu(el["y2"]),
    )
    conn.line.color.rgb = RGBColor.from_string(el["colour"].lstrip("#"))
    if el.get("stroke_w"):
        conn.line.width = Emu(int(el["stroke_w"]))
    if el.get("name"):
        conn.name = el["name"]
    return conn


def _add_icon(slide, el):
    """Place a pre-rendered icon PNG on the grid. render.py recolours + rasterises
    the icon to `el['png']` after the lint clears it; an icon whose rasteriser was
    absent has no `png` and is dropped by render.py before draw, so this only ever
    places a real file. Returns None defensively if `png` is missing."""
    png = el.get("png")
    if not png:
        return None
    pic = slide.shapes.add_picture(
        png, Emu(el["left"]), Emu(el["top"]),
        width=Emu(el["width"]), height=Emu(el["height"]),
    )
    if el.get("name"):
        pic.name = el["name"]
    return pic


def _add_text(slide, el):
    """Draw one text element as a textbox. Colour and size come from the token
    element dict; an optional `font`, `align`, and `anchor` refine it."""
    tb = slide.shapes.add_textbox(
        Emu(el["left"]), Emu(el["top"]), Emu(el["width"]), Emu(el["height"]),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    anchor = _ANCHOR_BY_NAME.get(el.get("anchor"))
    if anchor is not None:
        tf.vertical_anchor = anchor
    # Trim the textbox's default internal padding so text seats tight inside a
    # card; harmless for a free-standing stat where the box hugs the text.
    tf.margin_left = tf.margin_right = 0
    tf.margin_top = tf.margin_bottom = 0
    align = _ALIGN_BY_NAME.get(el.get("align"))
    # A `\n` in the text splits into paragraphs (a card body's few lines);
    # every paragraph inherits the element's size, colour, weight, and font.
    lines = str(el["text"]).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if align is not None:
            p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.size = Pt(el["font_pt"])
        run.font.color.rgb = RGBColor.from_string(el["colour"].lstrip("#"))
        if el.get("bold"):
            run.font.bold = True
        if el.get("font"):
            run.font.name = el["font"]
    if el.get("name"):
        tb.name = el["name"]
    return tb


def _add_box(slide, el):
    """Draw one filled-shape element (card, panel, step, connector).

    Fill (and optional stroke) come from the token element dict. Shadows are
    turned off — the on-brand look is a flat token fill, not a drop shadow
    (guards the gradient/shadow SaaS cliché the composition rules warn against).
    """
    shape_enum = _SHAPE_BY_NAME.get(el.get("shape"), MSO_SHAPE.ROUNDED_RECTANGLE)
    shp = slide.shapes.add_shape(
        shape_enum,
        Emu(el["left"]), Emu(el["top"]), Emu(el["width"]), Emu(el["height"]),
    )
    shp.fill.solid()
    shp.fill.fore_color.rgb = RGBColor.from_string(el["fill"].lstrip("#"))
    stroke = el.get("stroke")
    if stroke:
        shp.line.color.rgb = RGBColor.from_string(stroke.lstrip("#"))
        if el.get("stroke_w"):
            shp.line.width = Emu(int(el["stroke_w"]))
    else:
        shp.line.fill.background()
    try:
        shp.shadow.inherit = False
    except Exception:  # noqa: BLE001 — some shapes lack a shadow element
        pass
    if el.get("name"):
        shp.name = el["name"]
    return shp


# Order of the leading child elements inside an <a:tcPr>: the border lines come
# first (lnL, lnR, lnT, lnB), then diagonals/3-D/fill/headers/ext. We insert our
# <a:lnB> before the first element that must follow it, so the cell XML stays
# schema-ordered (a solidFill written by python-pptx's cell.fill.solid() already
# sits later in the sequence). Generic OOXML schema order, not a brand value.
_TCPR_AFTER_LNB = (
    "a:lnTlToBr", "a:lnBlToTr", "a:cell3D",
    "a:noFill", "a:solidFill", "a:gradFill", "a:blipFill", "a:pattFill",
    "a:grpFill", "a:headers", "a:extLst",
)


def _set_cell_bottom_border(cell, hex_colour, width_emu):
    """Draw a solid bottom border (a:lnB) on a table cell via raw XML.

    python-pptx exposes cell fills and text but NOT cell borders, so we write the
    <a:lnB> element directly (lxml, already a python-pptx dependency). Inserted in
    schema order so PowerPoint accepts it. Colour is a token hex; width the caller's
    hairline EMU. Kept isolated so, per A-002, dropping the call degrades cleanly to
    fills-only without touching the rest of the table."""
    from pptx.oxml.ns import qn  # noqa: PLC0415 — table draw only
    tcPr = cell._tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn("a:lnB")):
        tcPr.remove(existing)
    lnB = tcPr.makeelement(
        qn("a:lnB"), {"w": str(int(width_emu)), "cap": "flat", "cmpd": "sng"}
    )
    solid = tcPr.makeelement(qn("a:solidFill"), {})
    clr = tcPr.makeelement(qn("a:srgbClr"), {"val": hex_colour.lstrip("#").upper()})
    solid.append(clr)
    lnB.append(solid)
    after = {qn(t) for t in _TCPR_AFTER_LNB}
    insert_idx = len(tcPr)
    for i, child in enumerate(tcPr):
        if child.tag in after:
            insert_idx = i
            break
    tcPr.insert(insert_idx, lnB)


def _add_table(slide, el):
    """Draw the ONE table element as a native pptx GraphicFrame table.

    Theme table styling is stripped (D-003: first_row/horz_banding off) so the
    default blue-banded look never leaks; every cell fill/text/size/alignment is
    set explicitly from the token element dict (D-002), and a muted bottom hairline
    is written per data row except the last. Columns are equal width and rows equal
    height, with the last of each absorbing the rounding remainder so the frame's
    edges land exactly where planned."""
    header = el["header"]
    data_rows = el["rows"]                      # list of list of cell strings
    emphasis = set(el.get("emphasis_rows", []))
    col_aligns = el.get("col_aligns", [])
    ncols = len(header)
    nrows = 1 + len(data_rows)
    left, top = el["left"], el["top"]
    width, height = el["width"], el["height"]

    gf = slide.shapes.add_table(
        nrows, ncols, Emu(left), Emu(top), Emu(width), Emu(height)
    )
    tbl = gf.table
    # D-003: kill the built-in banded table style.
    tbl.first_row = False
    tbl.horz_banding = False

    # Equal column widths / row heights; last absorbs the remainder.
    col_w = width // ncols
    for c in range(ncols):
        tbl.columns[c].width = Emu(
            col_w if c < ncols - 1 else width - col_w * (ncols - 1)
        )
    row_h = height // nrows
    for r in range(nrows):
        tbl.rows[r].height = Emu(
            row_h if r < nrows - 1 else height - row_h * (nrows - 1)
        )

    pt = el["cell_pt"]
    margin = int(el.get("cell_margin", 0))
    stroke = el.get("stroke")
    stroke_w = _STROKE_EMU

    def _style(cell, fill_hex, text_hex, text, align, bold):
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(fill_hex.lstrip("#"))
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Emu(margin)
        cell.margin_right = Emu(margin)
        cell.margin_top = Emu(margin)
        cell.margin_bottom = Emu(margin)
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT if align == "right" else PP_ALIGN.LEFT
        run = p.add_run()
        run.text = str(text)
        run.font.size = Pt(pt)
        run.font.color.rgb = RGBColor.from_string(text_hex.lstrip("#"))
        run.font.bold = bold

    # Header row.
    for c in range(ncols):
        align = col_aligns[c] if c < len(col_aligns) else "left"
        _style(tbl.cell(0, c), el["header_fill"], el["header_text"],
               header[c], align, True)

    # Data rows.
    last = len(data_rows) - 1
    for di, cells in enumerate(data_rows):
        emph = di in emphasis
        fill_hex = el["emph_fill"] if emph else el["row_fill"]
        text_hex = el["emph_text"] if emph else el["row_text"]
        for c in range(ncols):
            align = col_aligns[c] if c < len(col_aligns) else "left"
            value = cells[c] if c < len(cells) else ""
            cell = tbl.cell(di + 1, c)
            _style(cell, fill_hex, text_hex, value, align, False)
            # A muted bottom hairline on every data row except the last (D-002).
            if stroke and di < last:
                _set_cell_bottom_border(cell, stroke, stroke_w)
    if el.get("name"):
        gf.name = el["name"]
    return gf
