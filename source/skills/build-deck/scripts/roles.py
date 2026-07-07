"""roles.py — the six fixed slide roles, planned from brand tokens.

The brand-fidelity half of the identity-not-layout vocabulary: instead of
filling a template's placeholders (which reproduces its layouts *and its
design debt*), each fixed role — title, section, statement, quote,
title-content, two-column — is PLANNED here as token-bound element dicts, the
same contract the composed primitives emit, so the mechanical lint gates them
and primitives.draw() renders them.

Design bar: these planners define a VOCABULARY, not a house look — every
colour resolves to the brand's colour_roles, every size to its type scale,
every position to its grid, so a finished slide reads as the brand. The
anatomy is evidence from the freehand study: the eyebrow tick over an
assertion title (title and body slides), the ghost numeral behind a section
title, and hierarchy carried by size — each role's lead text is rank 1 and its
supporting text rank 2, which the [hierarchy] lint holds strictly apart.

Planner purity: no pptx objects, dict-building only, all geometry integer
EMU; a role that cannot be planned raises primitives.ShapeError.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from primitives import (  # noqa: E402
    EMU_PER_PT,
    OPTICAL_CENTRE,
    ShapeError,
    _band,
    _content_span,
    _even_cells,
    _line_h,
    _require,
    _text_h,
)
from lint import GHOST_MULTIPLE  # noqa: E402

# The eyebrow tick (freehand study): a short accent bar seated above a slide's
# title. Generic anatomy constants, not brand values — the tick's COLOUR is
# always the brand's accent role.
TICK_H_EMU = 4 * EMU_PER_PT   # a 4pt-tall bar
TICK_W_FRAC = 0.055           # tick width = round(slide_w * TICK_W_FRAC)


def _field(fields, key) -> str:
    """The stripped string value of a spec field ('' when absent/empty)."""
    value = (fields or {}).get(key)
    if value is None:
        return ""
    return str(value).strip()


def _items(fields, key) -> list:
    """A block field (Body/Left/Right) normalised to a list of non-empty
    strings — the spec may carry it as a list of strings OR a single string."""
    value = (fields or {}).get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value]
    else:
        items = [str(value).strip()]
    return [item for item in items if item]


def _tick(role, tokens, slide_w, top, roles) -> dict:
    """The eyebrow tick element: an accent bar at the content's left edge.

    Carries "text": "" so a margins violation can format its message, and no
    name/rank — it is anatomy, not a spec field."""
    return {
        "role": role, "kind": "box", "shape": "rect",
        "left": tokens["grid"]["margin_x"], "top": top,
        "width": round(slide_w * TICK_W_FRAC), "height": TICK_H_EMU,
        "fill": roles["accent"], "text": "",
    }


def _hairline_emu(tokens) -> int:
    """The brand's hairline stroke width in EMU (shape token, 1pt default)."""
    return round((tokens.get("shape") or {}).get("hairline_pt", 1.0) * EMU_PER_PT)


# --- title -------------------------------------------------------------------


def plan_title(fields, tokens, slide_w, slide_h) -> list:
    """The deck's opening slide: eyebrow tick, display-size assertion title,
    muted subtitle — seated at the optical centre of the band.

    fields: {"Title": str (required), "Subtitle": str?}.
    """
    grid, ts, roles = _require(tokens, ("display", "body"))
    title = _field(fields, "Title")
    if not title:
        raise ShapeError("title slide needs a Title")
    subtitle = _field(fields, "Subtitle")

    baseline = grid["baseline"]
    content_left, content_w = _content_span(tokens, slide_w)
    band_top, band_bottom = _band(tokens, slide_h, None)
    band_h = band_bottom - band_top

    title_h = _text_h(title, content_w, ts["display"])
    block_h = TICK_H_EMU + 2 * baseline + title_h
    subtitle_h = 0
    if subtitle:
        subtitle_h = _text_h(subtitle, content_w, ts["body"])
        block_h += baseline + subtitle_h
    if block_h > band_h:
        raise ShapeError(
            "title slide content wraps deeper than the slide band — "
            "shorten the title or subtitle"
        )

    top = band_top + round((band_h - block_h) * OPTICAL_CENTRE)
    elements = [_tick("titleslide-tick", tokens, slide_w, top, roles)]
    title_top = top + TICK_H_EMU + 2 * baseline
    elements.append({
        "role": "titleslide-title", "text": title,
        "left": content_left, "top": title_top,
        "width": content_w, "height": title_h,
        "font_pt": ts["display"], "colour": roles["ink"], "align": "left",
        "rank": 1, "name": "slides-field:Title",
    })
    if subtitle:
        elements.append({
            "role": "titleslide-subtitle", "text": subtitle,
            "left": content_left, "top": title_top + title_h + baseline,
            "width": content_w, "height": subtitle_h,
            "font_pt": ts["body"], "colour": roles["muted"],
            "rank": 2, "name": "slides-field:Subtitle",
        })
    # The lower-right quadrant stays empty: it is the reserved logo region (a
    # future logo element lands there), so no element may occupy it.
    return elements


# --- section -----------------------------------------------------------------


def plan_section(fields, tokens, slide_w, slide_h, region=None, ordinal=None) -> list:
    """A section divider: title-size heading, and — when the section is
    numbered — a ghost numeral in muted display type behind it.

    fields: {"Title": str (required)}. `ordinal` (an int >= 1) numbers the
    section; the ghost is drawn ONLY then. The ghost deliberately underlaps
    the title (the lint's overlap rule skips ghost pairs) and takes exactly
    display × GHOST_MULTIPLE, the one off-scale size the size rule sanctions.
    """
    grid, ts, roles = _require(tokens, ("display", "title"))
    title = _field(fields, "Title")
    if not title:
        raise ShapeError("section slide needs a Title")

    content_left, content_w = _content_span(tokens, slide_w, region)
    band_top, band_bottom = _band(tokens, slide_h, region)
    band_h = band_bottom - band_top

    elements = []
    if isinstance(ordinal, int) and not isinstance(ordinal, bool) and ordinal >= 1:
        # Right half of the band, full band height — clamped inside the
        # margins by construction. Planned first so it paints behind the title.
        elements.append({
            "role": "sectionslide-ghost", "text": f"{ordinal:02d}",
            "ghost": True,
            "left": content_left + content_w // 2, "top": band_top,
            "width": content_w // 2, "height": band_h,
            "font_pt": ts["display"] * GHOST_MULTIPLE,
            "colour": roles["muted"], "align": "right", "anchor": "middle",
        })

    title_w = content_w * 7 // 12
    title_h = _text_h(title, title_w, ts["title"])
    if title_h > band_h:
        raise ShapeError(
            "section title wraps deeper than the slide band — shorten it"
        )
    elements.append({
        "role": "sectionslide-title", "text": title,
        "left": content_left,
        "top": band_top + round((band_h - title_h) * OPTICAL_CENTRE),
        "width": title_w, "height": title_h,
        "font_pt": ts["title"], "colour": roles["ink"], "align": "left",
        "rank": 1, "name": "slides-field:Title",
    })
    return elements


# --- statement ---------------------------------------------------------------


def plan_statement(fields, tokens, slide_w, slide_h) -> list:
    """One sentence, display size, centred at the optical centre — the slide
    IS the assertion, so nothing else shares it.

    fields: {"Statement": str (required)}.
    """
    _grid, ts, roles = _require(tokens, ("display",))
    statement = _field(fields, "Statement")
    if not statement:
        raise ShapeError("statement slide needs a Statement")

    content_left, content_w = _content_span(tokens, slide_w)
    band_top, band_bottom = _band(tokens, slide_h, None)
    band_h = band_bottom - band_top

    width = round(content_w * 10 / 12)
    height = _text_h(statement, width, ts["display"])
    if height > band_h:
        raise ShapeError(
            "statement wraps deeper than the slide band — "
            "cut it to the line that lands"
        )
    return [{
        "role": "statement-text", "text": statement,
        "left": content_left + (content_w - width) // 2,
        "top": band_top + round((band_h - height) * OPTICAL_CENTRE),
        "width": width, "height": height,
        "font_pt": ts["display"], "colour": roles["ink"],
        "align": "center", "anchor": "middle",
        "rank": 1, "name": "slides-field:Statement",
    }]


# --- quote -------------------------------------------------------------------


def plan_quote(fields, tokens, slide_w, slide_h) -> list:
    """A quotation under an oversized accent quote mark, attribution below.

    fields: {"Quote": str (required), "Attribution": str?}. The mark is a
    decorative glyph — display-size text with no rank or name, so it never
    constrains the hierarchy; the quotation itself is the rank-1 lead.
    """
    grid, ts, roles = _require(tokens, ("display", "title", "body"))
    quote = _field(fields, "Quote")
    if not quote:
        raise ShapeError("quote slide needs a Quote")
    attribution = _field(fields, "Attribution")

    baseline = grid["baseline"]
    content_left, content_w = _content_span(tokens, slide_w)
    band_top, band_bottom = _band(tokens, slide_h, None)

    mark_side = _line_h(ts["display"])
    quote_w = content_w * 9 // 12
    quote_h = _text_h(quote, quote_w, ts["title"])
    quote_top = band_top + mark_side + baseline
    bottom = quote_top + quote_h

    elements = [
        {
            "role": "quote-mark", "text": "“",
            "left": content_left, "top": band_top,
            "width": mark_side, "height": mark_side,
            "font_pt": ts["display"], "colour": roles["accent"],
        },
        {
            "role": "quote-text", "text": quote,
            "left": content_left, "top": quote_top,
            "width": quote_w, "height": quote_h,
            "font_pt": ts["title"], "colour": roles["ink"],
            "rank": 1, "name": "slides-field:Quote",
        },
    ]
    if attribution:
        attr_text = "— " + attribution
        attr_h = _text_h(attr_text, quote_w, ts["body"])
        elements.append({
            "role": "quote-attribution", "text": attr_text,
            "left": content_left, "top": bottom + baseline,
            "width": quote_w, "height": attr_h,
            "font_pt": ts["body"], "colour": roles["muted"],
            "rank": 2, "name": "slides-field:Attribution",
        })
        bottom = bottom + baseline + attr_h
    if bottom > band_bottom:
        raise ShapeError(
            "quote wraps deeper than the slide band — trim the quotation"
        )
    return elements


# --- title-content -----------------------------------------------------------


def plan_title_content(fields, tokens, slide_w, slide_h) -> list:
    """The workhorse body slide: eyebrow tick, h1 assertion title, body items
    stacked below with a muted hairline rule between neighbours.

    fields: {"Title": str (required), "Body": list-of-str or str?}.
    """
    grid, ts, roles = _require(tokens, ("h1", "body"))
    title = _field(fields, "Title")
    if not title:
        raise ShapeError("title-content slide needs a Title")
    body = _items(fields, "Body")

    baseline = grid["baseline"]
    content_left, content_w = _content_span(tokens, slide_w)
    band_top, band_bottom = _band(tokens, slide_h, None)

    title_h = _text_h(title, content_w, ts["h1"])
    title_top = band_top + TICK_H_EMU + 2 * baseline
    item_hs = [_text_h(item, content_w, ts["body"]) for item in body]
    bottom = title_top + title_h
    if body:
        bottom += 2 * baseline + sum(item_hs) + (len(body) - 1) * baseline
    if bottom > band_bottom:
        raise ShapeError(
            "body wraps deeper than the content band — "
            "cut items or split the slide"
        )

    elements = [
        _tick("bodyslide-tick", tokens, slide_w, band_top, roles),
        {
            "role": "bodyslide-title", "text": title,
            "left": content_left, "top": title_top,
            "width": content_w, "height": title_h,
            "font_pt": ts["h1"], "colour": roles["ink"],
            "rank": 1, "name": "slides-field:Title",
        },
    ]
    stroke_w = _hairline_emu(tokens)
    y = title_top + title_h + 2 * baseline
    for i, (item, item_h) in enumerate(zip(body, item_hs)):
        if i:
            # A muted hairline rule vertically centred in the baseline gap
            # above this item; edges are exempt from the overlap rule.
            rule_top = (y - baseline) + (baseline - stroke_w) // 2
            rule_y = rule_top + stroke_w // 2
            elements.append({
                "role": "bodyslide-rule", "kind": "edge",
                "colour": roles["muted"], "stroke_w": stroke_w, "text": "",
                "x1": content_left, "y1": rule_y,
                "x2": content_left + content_w, "y2": rule_y,
                "left": content_left, "top": rule_top,
                "width": content_w, "height": stroke_w,
            })
        elements.append({
            "role": "bodyslide-body", "text": item,
            "left": content_left, "top": y,
            "width": content_w, "height": item_h,
            "font_pt": ts["body"], "colour": roles["ink"],
            "rank": 2, "name": "slides-field:Body",
        })
        y += item_h + baseline
    return elements


# --- two-column ----------------------------------------------------------------


def plan_two_column(fields, tokens, slide_w, slide_h) -> list:
    """Tick + title over two even columns of body text, split by a muted
    vertical hairline centred in the gutter.

    fields: {"Title": str, "Left": list-of-str or str, "Right": list-of-str
    or str} — all three required.
    """
    grid, ts, roles = _require(tokens, ("h1", "body"))
    title = _field(fields, "Title")
    if not title:
        raise ShapeError("two-column slide needs a Title")
    left_items = _items(fields, "Left")
    if not left_items:
        raise ShapeError("two-column slide needs a Left column")
    right_items = _items(fields, "Right")
    if not right_items:
        raise ShapeError("two-column slide needs a Right column")

    baseline, gutter = grid["baseline"], grid["gutter"]
    content_left, content_w = _content_span(tokens, slide_w)
    band_top, band_bottom = _band(tokens, slide_h, None)

    title_h = _text_h(title, content_w, ts["h1"])
    title_top = band_top + TICK_H_EMU + 2 * baseline
    col_top = title_top + title_h + 2 * baseline
    cells = _even_cells(content_left, content_w, 2, gutter)

    def _column(items, cell, role, name):
        cl, cw = cell
        col_elements, y = [], col_top
        for item in items:
            item_h = _text_h(item, cw, ts["body"])
            col_elements.append({
                "role": role, "text": item,
                "left": cl, "top": y, "width": cw, "height": item_h,
                "font_pt": ts["body"], "colour": roles["ink"],
                "rank": 2, "name": name,
            })
            y += item_h + baseline
        return col_elements, y - baseline  # bottom of the last item

    left_els, left_bottom = _column(
        left_items, cells[0], "twocol-left", "slides-field:Left")
    right_els, right_bottom = _column(
        right_items, cells[1], "twocol-right", "slides-field:Right")
    deep_bottom = max(left_bottom, right_bottom)
    if deep_bottom > band_bottom:
        raise ShapeError(
            "column wraps deeper than the content band — "
            "cut items or split the slide"
        )

    stroke_w = _hairline_emu(tokens)
    rule_x = cells[0][0] + cells[0][1] + gutter // 2
    return [
        _tick("twocol-tick", tokens, slide_w, band_top, roles),
        {
            "role": "twocol-title", "text": title,
            "left": content_left, "top": title_top,
            "width": content_w, "height": title_h,
            "font_pt": ts["h1"], "colour": roles["ink"],
            "rank": 1, "name": "slides-field:Title",
        },
    ] + left_els + right_els + [{
        "role": "twocol-rule", "kind": "edge",
        "colour": roles["muted"], "stroke_w": stroke_w, "text": "",
        "x1": rule_x, "y1": col_top, "x2": rule_x, "y2": deep_bottom,
        "left": rule_x - stroke_w // 2, "top": col_top,
        "width": stroke_w, "height": deep_bottom - col_top,
    }]


# --- composed title -----------------------------------------------------------


def plan_composed_title(title, tokens, slide_w, slide_h):
    """The h1 heading a composed slide seats its blocks under.

    Returns (elements, band): one rank-1 heading element at the top margin,
    and the (left, top, width, height) band left below it — the region the
    composed planners fill. Raises ShapeError when the heading eats the band.
    """
    grid, ts, roles = _require(tokens, ("h1",))
    text = str(title)
    margin_x = grid["margin_x"]
    margin_top = grid["margin_top"]
    baseline = grid["baseline"]
    content_w = slide_w - 2 * margin_x

    title_h = _text_h(text, content_w, ts["h1"])
    title_bottom = margin_top + title_h
    band_top = title_bottom + 2 * baseline
    band_h = (slide_h - grid["margin_bottom"]) - band_top
    if band_h <= 0:
        raise ShapeError(
            "composed title leaves no room below it — "
            "shorten the title or drop it"
        )
    elements = [{
        "role": "composedtitle-heading", "text": text,
        "left": margin_x, "top": margin_top,
        "width": content_w, "height": title_h,
        "font_pt": ts["h1"], "colour": roles["ink"],
        "rank": 1, "name": "slides-field:Title",
    }]
    return elements, (margin_x, band_top, content_w, band_h)


ROLE_PLANNERS = {
    "title": plan_title,
    "section": plan_section,
    "statement": plan_statement,
    "quote": plan_quote,
    "title-content": plan_title_content,
    "two-column": plan_two_column,
}
