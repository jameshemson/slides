#!/usr/bin/env python3
"""render.py — turn a deck spec + brand profile into a real .pptx.

`build-deck` runs this. It reads a deck spec (the content and structure of a
deck — see presentation-craft/reference/deck-spec.md) and a brand.json (which
names the user's template and the role-to-layout map), then fills the
template's existing placeholders to produce a .pptx.

Decision D-002 (refined as D-101): render.py itself still sets no fonts,
colours, or coordinates and adds no shape directly — the template carries all
visual design for the six fixed roles, and render.py only fills the placeholders
the chosen layout already defines. The ONE carve-out is the `composed` role:
there, render.py delegates drawing to primitives.py (the only module that emits
literals, all of them derived from brand.json design tokens), and every drawn
element must pass the mechanical lint (lint.py) before a shape is added. So the
old structural guarantee — "nowhere off-template to put a shape" — is replaced
for composed slides by a mechanical one: no element survives that is off-token,
off-grid, overlapping, or over the element cap. A spec still cannot smuggle a
tacked-on strapline onto a fixed-role slide.

Usage:

    python3 render.py --spec <deck-spec.md> --brand <brand.json> --out <out.pptx>

The template path is read from brand.json's `template` key — there is no
separate --template argument.

Exit status: 0 on success (a short run summary is printed). On any malformed
input it exits non-zero with a message naming the offending slide or key, and
never emits a half-built .pptx.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptxlib import fill_placeholders, load_template, resolve_role  # noqa: E402

# The six semantic roles and their fields, in the order the fields fill
# placeholders. The first field of each role fills the title placeholder.
ROLE_FIELDS = {
    "title": ["Title", "Subtitle"],
    "section": ["Title"],
    "statement": ["Statement"],
    "title-content": ["Title", "Body"],
    "two-column": ["Title", "Left", "Right"],
    "quote": ["Quote", "Attribution"],
}
# Fields that are optional for their role (absent is fine). Body is optional on
# title-content because a chart may stand in for it (Body and Chart may coexist,
# but at least one is required — enforced in _validate_slide_fields).
OPTIONAL_FIELDS = {
    "title": {"Subtitle"},
    "quote": {"Attribution"},
    "title-content": {"Body"},
}
# Block fields may carry a bullet list or short paragraphs across many lines.
BLOCK_FIELDS = {"Body", "Left", "Right"}
# Fields any slide may carry, handled outside the role's placeholder fill.
META_FIELDS = {"Visual", "Notes"}
# Structured block fields collect raw lines like a block but are parsed by a
# dedicated parser (not _block_items). Chart is the only one. It is NOT in
# BLOCK_FIELDS on purpose, so it skips the bullet-list / inline-value paths.
STRUCTURED_BLOCK_FIELDS = {"Chart"}
# Extra recognised field labels beyond ROLE_FIELDS and META_FIELDS.
EXTRA_FIELDS = {"Chart"}
# Roles a Chart may appear on.
CHART_ALLOWED_ROLES = {"title-content"}
# Chart types render.py accepts at parse time. Kept in sync with
# charts.CHART_TYPES (render.py must not import charts — and thus matplotlib —
# at module load, so the list is duplicated rather than imported).
# Two data shapes: category charts (categories + series) and point charts
# (x/y points).
CHART_TYPES = ("bar", "column", "line", "pie", "scatter")
CATEGORY_CHART_TYPES = ("bar", "column", "pie")
POINT_CHART_TYPES = ("line", "scatter")
REQUIRED_BRAND_KEYS = ("template", "fonts", "colours", "layout_map")


class SpecError(Exception):
    """A malformed deck spec or brand profile. Message names the offender."""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Render a deck spec into a .pptx by filling a template."
    )
    parser.add_argument("--spec", required=True, help="path to the deck spec .md")
    parser.add_argument("--brand", required=True, help="path to brand.json")
    parser.add_argument("--out", required=True, help="output .pptx path")
    parser.add_argument(
        "--charts-dir", default=None,
        help="directory for generated chart PNGs (default: <out>.charts)",
    )
    args = parser.parse_args(argv)

    charts_dir = args.charts_dir or (os.path.splitext(args.out)[0] + ".charts")

    try:
        brand = load_brand(args.brand)
        slides = parse_spec(args.spec)
        summary = build_deck(
            brand, slides, args.out,
            charts_dir=charts_dir, brand_path=args.brand,
        )
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(summary)
    return 0


# --- brand profile -----------------------------------------------------------


def load_brand(path):
    """Load and validate brand.json. Raises SpecError naming the bad key."""
    if not os.path.isfile(path):
        raise SpecError(f"brand profile not found: {path}")
    try:
        with open(path, encoding="utf-8") as fh:
            brand = json.load(fh)
    except json.JSONDecodeError as exc:
        raise SpecError(f"brand profile is not valid JSON: {exc}")
    if not isinstance(brand, dict):
        raise SpecError("brand profile must be a JSON object")

    for key in REQUIRED_BRAND_KEYS:
        if key not in brand:
            raise SpecError(f"brand profile missing required key: {key!r}")

    template = brand["template"]
    if not isinstance(template, str) or not template.strip():
        raise SpecError("brand profile key 'template' must be a non-empty path")
    # Resolve a relative template path against the brand profile's own
    # directory, so a .slides/ directory is self-contained and portable: it
    # works regardless of the working directory render.py runs from.
    if not os.path.isabs(template):
        brand_dir = os.path.dirname(os.path.abspath(path))
        template = os.path.normpath(os.path.join(brand_dir, template))
    brand["template"] = template

    layout_map = brand["layout_map"]
    if not isinstance(layout_map, dict) or not layout_map:
        raise SpecError("brand profile key 'layout_map' must be a non-empty object")
    for role, idx in layout_map.items():
        if not isinstance(idx, int) or isinstance(idx, bool):
            raise SpecError(
                f"brand profile key 'layout_map' maps role {role!r} to a "
                f"non-integer layout index"
            )

    if not isinstance(brand["fonts"], dict):
        raise SpecError("brand profile key 'fonts' must be an object")
    if not isinstance(brand["colours"], dict):
        raise SpecError("brand profile key 'colours' must be an object")

    return brand


# --- deck spec parsing -------------------------------------------------------


def parse_spec(path):
    """Parse a deck spec into an ordered list of slide dicts.

    Each slide dict: {"number": int, "role": str, "fields": {name: value},
    "meta": {"Visual": str?, "Notes": str?}}. A field value is a string for
    an inline field or a list of strings for a block field.

    Raises SpecError, naming the slide, for any structural fault.
    """
    if not os.path.isfile(path):
        raise SpecError(f"deck spec not found: {path}")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    body = _strip_frontmatter(text)
    raw_slides = _split_slides(body)
    if not raw_slides:
        raise SpecError("deck spec declares no slides")

    slides = []
    for expected_number, (declared_number, slide_lines) in enumerate(
        raw_slides, start=1
    ):
        if declared_number != expected_number:
            raise SpecError(
                f"slide headings must count 1..N with no gaps; expected "
                f"'## Slide {expected_number}' but found "
                f"'## Slide {declared_number}'"
            )
        slides.append(_parse_slide(expected_number, slide_lines))
    return slides


def _strip_frontmatter(text):
    """Drop the leading `---` YAML frontmatter block, returning the slide body."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip() == "---":
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == "---":
                return "\n".join(lines[j + 1:])
        raise SpecError("frontmatter block opened with '---' but never closed")
    return "\n".join(lines[i:])


def _split_slides(body):
    """Split the slide body into (slide_number, lines) pairs by `## Slide N`."""
    slides = []
    current_number = None
    current_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Slide"):
            if current_number is not None:
                slides.append((current_number, current_lines))
            token = stripped[len("## Slide"):].strip()
            try:
                current_number = int(token)
            except ValueError:
                raise SpecError(
                    f"slide heading is not numbered: '{stripped}'"
                )
            current_lines = []
        elif current_number is not None:
            current_lines.append(line)
    if current_number is not None:
        slides.append((current_number, current_lines))
    return slides


def _parse_slide(number, lines):
    """Parse one slide's lines into role, fields, and meta. Raises SpecError.

    A `layout: composed` slide is routed to _parse_composed_slide before the
    field loop, so its repeated `Block:` lines never trip the stray-field guard.
    The six fixed roles keep their original parse path below, unchanged.
    """
    if _prescan_layout(lines) == "composed":
        return _parse_composed_slide(number, lines)

    role = None
    fields = {}
    order = []
    current_field = None
    current_block = []

    def _close_block():
        if current_field is None:
            return
        if current_field in BLOCK_FIELDS:
            items = _block_items(current_block)
            fields[current_field] = items
        elif current_field in STRUCTURED_BLOCK_FIELDS:
            fields[current_field] = _parse_chart_block(number, current_block)
        # Inline fields were already stored from the `Field: value` line.

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()

        # `layout:` line — required first.
        if stripped.lower().startswith("layout:"):
            if role is not None:
                raise SpecError(f"slide {number} declares 'layout:' twice")
            role = stripped.split(":", 1)[1].strip()
            continue

        label, value = _field_label(line)
        if label is not None:
            # A new labelled field closes any open block field.
            _close_block()
            current_field = label
            current_block = []
            if label in STRUCTURED_BLOCK_FIELDS:
                # A structured block (Chart) must be a block, never inline.
                if value:
                    raise SpecError(
                        f"slide {number}: {label!r} must be a block, not an "
                        f"inline value (write '{label}:' then indented lines)"
                    )
                # Following lines are collected and parsed in _close_block.
            elif label in BLOCK_FIELDS:
                if value:
                    # Allow a block field given an inline value on one line.
                    fields[label] = [value]
                    current_field = None
                else:
                    fields[label] = []
            else:
                fields[label] = value
            if label not in order:
                order.append(label)
            continue

        # A colon-led, field-shaped line that is not a known field, seen
        # outside an open block field, is a typo'd or stray field (a
        # tacked-on `Strapline:`, a misspelt `Titel:`). Fail loudly naming
        # it rather than dropping it silently. Inside a block field a
        # colon-led line is legitimate prose and is left alone.
        if (
            current_field not in BLOCK_FIELDS
            and current_field not in STRUCTURED_BLOCK_FIELDS
            and _looks_like_field_decl(line)
        ):
            bad = line.split(":", 1)[0].strip()
            known = sorted(
                set(META_FIELDS).union(*ROLE_FIELDS.values()).union(EXTRA_FIELDS)
            )
            raise SpecError(
                f"slide {number} has an unrecognised field {bad!r}; "
                f"expected one of {', '.join(known)}"
            )

        # A non-label line belongs to the open block field, if any.
        if current_field in BLOCK_FIELDS or current_field in STRUCTURED_BLOCK_FIELDS:
            current_block.append(line)
        # Otherwise it is blank/decoration outside any field — ignored.

    _close_block()

    if role is None:
        raise SpecError(f"slide {number} has no 'layout:' line")
    if role not in ROLE_FIELDS:
        raise SpecError(
            f"slide {number} uses unknown role {role!r}; expected one of "
            f"{', '.join(sorted(ROLE_FIELDS))}"
        )

    _validate_slide_fields(number, role, fields)
    return {
        "number": number,
        "role": role,
        "fields": fields,
        "meta": {k: fields[k] for k in META_FIELDS if k in fields},
    }


# --- composed role parsing ---------------------------------------------------


def _prescan_layout(lines):
    """Return the slide's declared layout role from its first `layout:` line.

    Used to route a composed slide to its own parser before the field loop runs.
    Returns None if no layout line is present (the main parser then raises the
    usual "no 'layout:' line" error).
    """
    for raw in lines:
        stripped = raw.strip()
        if stripped.lower().startswith("layout:"):
            return stripped.split(":", 1)[1].strip()
    return None


def _parse_composed_slide(number, lines):
    """Parse a `composed` slide into title, blocks, and meta. Raises SpecError.

    Recognises `Title:` (optional, inline), `Notes:` (optional, meta), and one
    or more `Block: <type>` blocks, each followed by indented item lines up to
    the next Title/Notes/Block. Returns:

        {"number", "role": "composed", "fields": {"Title": str?},
         "blocks": [parsed block dict, ...], "meta": {"Notes": str?}}
    """
    title = None
    notes_lines = []
    blocks = []
    current = None  # None | "notes" | a raw block dict {"type", "items"}

    for raw in lines:
        stripped = raw.strip()
        low = stripped.lower()
        if low.startswith("layout:"):
            continue
        if low.startswith("title:"):
            title = stripped.split(":", 1)[1].strip()
            current = None
            continue
        if low.startswith("notes:"):
            value = stripped.split(":", 1)[1].strip()
            notes_lines = [value] if value else []
            current = "notes"
            continue
        if low.startswith("block:"):
            btype = stripped.split(":", 1)[1].strip().lower()
            if not btype:
                raise SpecError(
                    f"slide {number}: 'Block:' needs a type "
                    f"(e.g. 'Block: stat-row')"
                )
            current = {"type": btype, "items": []}
            blocks.append(current)
            continue
        # continuation line
        if not stripped:
            continue
        if current == "notes":
            notes_lines.append(stripped)
        elif isinstance(current, dict):
            current["items"].append(stripped)
        # else: a stray line before any Block/Title/Notes — ignored.

    if not blocks:
        raise SpecError(
            f"slide {number}: composed slide has no 'Block:' (need at least "
            f"one, e.g. 'Block: stat-row')"
        )
    if len(blocks) > 1:
        raise SpecError(
            f"slide {number}: a composed slide takes one 'Block:' in this "
            f"release; stacking multiple blocks on a slide is a planned "
            f"follow-up"
        )

    parsed_blocks = [_parse_composed_block(number, b) for b in blocks]
    fields = {"Title": title} if title else {}
    meta = {"Notes": " ".join(notes_lines)} if notes_lines else {}
    return {
        "number": number,
        "role": "composed",
        "fields": fields,
        "blocks": parsed_blocks,
        "meta": meta,
    }


def _parse_composed_block(number, block):
    """Parse one composed block's raw item lines by type. Raises SpecError.

    stat-row: each item is `value | label` (a leading '-'/'*' bullet is
    tolerated). Returns {"type": "stat-row", "stats": [{"value", "label"}, ...]}.
    """
    btype = block["type"]
    if btype == "stat-row":
        stats = []
        for item in block["items"]:
            text = item
            if text[:1] in "-*":
                text = text[1:].strip()
            if "|" not in text:
                raise SpecError(
                    f"slide {number}: stat-row line {item!r} must be "
                    f"'value | label'"
                )
            value, label = text.split("|", 1)
            value = value.strip()
            label = label.strip()
            if not value:
                raise SpecError(
                    f"slide {number}: stat-row line {item!r} has an empty value"
                )
            stats.append({"value": value, "label": label})
        if not stats:
            raise SpecError(
                f"slide {number}: stat-row block is empty (add 'value | label' "
                f"lines)"
            )
        return {"type": "stat-row", "stats": stats}

    raise SpecError(
        f"slide {number}: unknown composed block type {btype!r}; expected one "
        f"of: stat-row"
    )


def _field_label(line):
    """If `line` is a `Field: value` line, return (label, value); else (None,None).

    A label is a known role/meta field followed by a colon. List-item lines
    ('- ...') and indented continuation are not labels.
    """
    if not line.strip() or ":" not in line:
        return None, None
    head = line.split(":", 1)[0]
    # A label sits at the start of the line, no leading list marker.
    if head != head.strip():
        return None, None
    if head.lstrip().startswith(("-", "*")):
        return None, None
    label = head.strip()
    # Every field name any role declares, plus the meta and extra fields.
    known = set(META_FIELDS) | set(EXTRA_FIELDS)
    for role_fields in ROLE_FIELDS.values():
        known.update(role_fields)
    # Match case-insensitively, then normalise to the canonical capitalisation.
    canonical = {name.lower(): name for name in known}
    if label.lower() not in canonical:
        return None, None
    value = line.split(":", 1)[1].strip()
    return canonical[label.lower()], value


_FIELD_DECL_HEAD = re.compile(r"^[A-Za-z][\w -]*$")


def _looks_like_field_decl(line):
    """True if `line` is shaped like a `Field: value` declaration.

    Used to catch a typo'd or stray field at a slide's top level. A line
    qualifies when it has a colon, an unindented head with no list marker,
    and a head that reads like a field name (a word, not a number or URL).
    """
    if ":" not in line:
        return False
    head = line.split(":", 1)[0]
    if head != head.strip() or not head.strip():
        return False
    if head.lstrip().startswith(("-", "*")):
        return False
    return bool(_FIELD_DECL_HEAD.match(head.strip()))


def _block_items(block_lines):
    """Turn a block field's raw lines into a list of paragraph strings.

    A bullet list ('- item' / '* item') yields one item per bullet. Plain
    prose lines are kept as separate paragraphs. Blank lines are dropped.
    """
    items = []
    for raw in block_lines:
        text = raw.strip()
        if not text:
            continue
        if text[0] in "-*" and text[1:2] in (" ", ""):
            text = text[1:].strip()
        items.append(text)
    return items


def _chart_number(number, token):
    """Parse one numeric chart token to float, or raise SpecError naming it."""
    try:
        return float(token.strip())
    except ValueError:
        raise SpecError(
            f"slide {number}: chart value {token.strip()!r} is not a number"
        )


def _parse_points(number, value):
    """Parse a line chart's `points:` value into a list of (x, y) float pairs.

    Format: comma-separated 'x y' pairs, e.g. '0 76900, 12 34300'.
    """
    points = []
    for chunk in value.split(","):
        parts = chunk.split()
        if len(parts) != 2:
            raise SpecError(
                f"slide {number}: chart point {chunk.strip()!r} must be two "
                f"numbers 'x y'"
            )
        points.append((_chart_number(number, parts[0]),
                       _chart_number(number, parts[1])))
    if not points:
        raise SpecError(f"slide {number}: chart 'points' is empty")
    return points


def _parse_marker(number, value):
    """Parse a line chart `marker:` value 'x label' into {'x', 'label'}."""
    parts = value.split(None, 1)
    if len(parts) != 2:
        raise SpecError(
            f"slide {number}: chart marker {value.strip()!r} must be 'x label'"
        )
    return {"x": _chart_number(number, parts[0]), "label": parts[1].strip()}


def _parse_chart_block(number, lines):
    """Parse a Chart block's raw lines into a chart dict. Raises SpecError.

    Returns one of:
      bar/column: {type, categories: [str], series: [{name, values:[float]}],
                   emphasis: str|None, callout: str|None}
      line:       {type, points: [(x,y)], markers: [{x,label}],
                   callout: str|None}
    """
    ctype = categories = callout = emphasis = None
    points = None
    series = []
    markers = []
    seen = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        seen = True
        if ":" not in line:
            raise SpecError(
                f"slide {number}: chart line {line!r} is not 'key: value'"
            )
        head, _, value = line.partition(":")
        key = head.strip().lower()
        value = value.strip()
        if key == "type":
            ctype = value.lower()
        elif key == "categories":
            categories = [c.strip() for c in value.split(",") if c.strip()]
        elif key == "emphasis":
            emphasis = value
        elif key == "callout":
            callout = value
        elif key == "points":
            points = _parse_points(number, value)
        elif key == "marker":
            markers.append(_parse_marker(number, value))
        elif key == "series" or key.startswith("series "):
            name = head.strip()[len("series"):].strip() or "Series"
            values = [_chart_number(number, t)
                      for t in value.split(",") if t.strip()]
            if not values:
                raise SpecError(
                    f"slide {number}: chart series {name!r} has no values"
                )
            series.append({"name": name, "values": values})
        else:
            raise SpecError(
                f"slide {number}: unknown chart key {head.strip()!r}"
            )

    if not seen:
        raise SpecError(f"slide {number}: chart block is empty")
    if ctype is None:
        raise SpecError(f"slide {number}: chart block has no 'type'")
    if ctype not in CHART_TYPES:
        raise SpecError(
            f"slide {number}: unknown chart type {ctype!r}; expected one of "
            f"{', '.join(CHART_TYPES)}"
        )

    if ctype in CATEGORY_CHART_TYPES:
        if not categories:
            raise SpecError(
                f"slide {number}: chart type {ctype!r} needs 'categories'"
            )
        if not series:
            raise SpecError(
                f"slide {number}: chart type {ctype!r} needs at least one "
                f"'series'"
            )
        if ctype == "pie" and len(series) != 1:
            raise SpecError(
                f"slide {number}: a pie chart needs exactly one series, not "
                f"{len(series)}"
            )
        for s in series:
            if len(s["values"]) != len(categories):
                raise SpecError(
                    f"slide {number}: chart series {s['name']!r} has "
                    f"{len(s['values'])} values but there are "
                    f"{len(categories)} categories (length mismatch)"
                )
        if emphasis is not None and emphasis not in categories:
            raise SpecError(
                f"slide {number}: chart emphasis {emphasis!r} is not one of "
                f"the categories"
            )
        return {"type": ctype, "categories": categories, "series": series,
                "emphasis": emphasis, "callout": callout}

    # line or scatter (point charts)
    if not points:
        raise SpecError(
            f"slide {number}: chart type {ctype!r} needs 'points'"
        )
    if emphasis is not None:
        raise SpecError(
            f"slide {number}: 'emphasis' is not supported for a {ctype} chart; "
            f"use 'marker' to call out a point instead"
        )
    point_xs = {x for x, _ in points}
    for m in markers:
        if m["x"] not in point_xs:
            raise SpecError(
                f"slide {number}: chart marker at x={m['x']:g} has no matching "
                f"point"
            )
    return {"type": ctype, "points": points, "markers": markers,
            "callout": callout}


def _validate_slide_fields(number, role, fields):
    """Check a slide carries exactly the fields its role allows. Raises SpecError."""
    has_chart = "Chart" in fields
    if has_chart and role not in CHART_ALLOWED_ROLES:
        raise SpecError(
            f"slide {number}: 'Chart' is only allowed on a title-content "
            f"slide, not {role!r}"
        )

    allowed = set(ROLE_FIELDS[role]) | META_FIELDS
    if role in CHART_ALLOWED_ROLES:
        allowed |= {"Chart"}
    required = set(ROLE_FIELDS[role]) - OPTIONAL_FIELDS.get(role, set())

    for name in fields:
        if name not in allowed:
            raise SpecError(
                f"slide {number} ({role}) has field {name!r}, which is not "
                f"allowed for this role"
            )
    for name in required:
        value = fields.get(name)
        empty = value is None or value == "" or value == []
        if empty:
            raise SpecError(
                f"slide {number} ({role}) is missing required field {name!r}"
            )

    # title-content needs either a Body or a Chart (Body and Chart may coexist).
    if role in CHART_ALLOWED_ROLES:
        body = fields.get("Body")
        body_empty = body is None or body == "" or body == []
        if body_empty and not has_chart:
            raise SpecError(
                f"slide {number}: title-content slide needs a Body or a Chart"
            )


# --- rendering ---------------------------------------------------------------


def build_deck(brand, slides, out_path, charts_dir=None, brand_path=None):
    """Render parsed slides into a .pptx at out_path. Returns a summary string.

    A slide carrying a `Chart` is drawn natively: charts.py renders a PNG and
    it is placed below the body line. If matplotlib is not importable the chart
    degrades to a `VISUAL TO ADD:` note (D-011) so the deck still builds.
    """
    template = brand["template"]
    if not os.path.isfile(template):
        raise SpecError(f"template named in brand profile not found: {template}")
    try:
        prs = load_template(template)
    except Exception as exc:  # noqa: BLE001
        raise SpecError(f"could not open template {template}: {exc}")

    # Strip any pre-existing slides so a user may reuse a real deck as a
    # template; only its masters and layouts matter.
    sld_id_lst = prs.slides._sldIdLst
    for sld in list(sld_id_lst):
        sld_id_lst.remove(sld)

    if charts_dir is None:
        charts_dir = os.path.splitext(out_path)[0] + ".charts"

    layout_map = brand["layout_map"]
    visual_slides = []
    chart_slides = []        # drawn natively
    fallback_slides = []     # matplotlib absent -> VISUAL TO ADD note
    charts_mod = "unset"     # imported lazily once, on the first chart slide
    font_family = "unset"    # resolved lazily once, when first drawing a chart
    font_warning = None
    composed_tokens = None   # resolved lazily once, on the first composed slide

    for spec in slides:
        number = spec["number"]
        role = spec["role"]

        if role == "composed":
            if composed_tokens is None:
                import tokens  # noqa: PLC0415 — light; composed decks only
                composed_tokens = tokens.resolve_tokens(brand, prs)
            _render_composed_slide(prs, brand, spec, composed_tokens)
            continue

        if role not in layout_map:
            raise SpecError(
                f"slide {number}: role {role!r} is not in brand profile's "
                f"layout_map"
            )
        try:
            layout = resolve_role(prs, layout_map, role)
        except IndexError:
            raise SpecError(
                f"slide {number}: layout_map points role {role!r} at index "
                f"{layout_map[role]}, which the template does not have"
            )

        slide = prs.slides.add_slide(layout)

        ordered_fields = _ordered_role_fields(spec)
        try:
            unused = fill_placeholders(slide, ordered_fields)
        except ValueError:
            content_count = _content_placeholder_count(slide)
            raise SpecError(
                f"slide {number} ({role}) has {len(ordered_fields)} fields "
                f"but its layout offers only {content_count} content "
                f"placeholder(s)"
            )

        chart = spec["fields"].get("Chart")
        extra_visual = None
        if chart:
            if charts_mod == "unset":
                try:
                    import charts as charts_mod  # noqa: PLC0415
                except ImportError:
                    charts_mod = None
            if charts_mod is None:
                # Graceful degradation (D-011): record the chart as a note.
                extra_visual = chart_to_note(chart)
                fallback_slides.append(number)
            else:
                if font_family == "unset":
                    font_family, font_warning = register_brand_font(
                        brand, brand_path
                    )
                host = _object_placeholder(slide)
                if host is None:
                    raise SpecError(
                        f"slide {number}: title-content layout has no content "
                        f"placeholder to host a chart; re-run teach-slides"
                    )
                body_val = spec["fields"].get("Body")
                has_body = body_val not in (None, "", [])
                title_ph = slide.shapes.title
                if has_body:
                    _resize_to_text(slide, host, title_ph)
                    # Body stays (it holds the explanatory line); keep it out
                    # of the drop list.
                    unused = [p for p in unused
                              if p._element is not host._element]
                region = _chart_region(number, prs, slide, host, title_ph,
                                       has_body)
                os.makedirs(charts_dir, exist_ok=True)
                png = os.path.join(charts_dir, f"slide{number}.png")
                try:
                    charts_mod.render_png(
                        chart, brand["colours"], font_family, png
                    )
                except charts_mod.ChartError as exc:
                    raise SpecError(f"slide {number}: {exc}")
                _place_picture(slide, png, region)
                chart_slides.append(number)

        _drop_unused(unused)
        _apply_meta(slide, spec["meta"], extra_visual=extra_visual)
        if "Visual" in spec["meta"]:
            visual_slides.append(number)

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    prs.save(out_path)

    return _summary(out_path, len(slides), visual_slides, chart_slides,
                    fallback_slides, font_warning)


def _summary(out_path, n_slides, visual_slides, chart_slides, fallback_slides,
             font_warning):
    """Compose the one-line run summary, naming charts, notes, and warnings."""
    parts = [f"rendered {n_slides} slide(s) to {out_path}"]
    if chart_slides:
        parts.append(
            f"; {len(chart_slides)} native chart(s) "
            f"(slides {', '.join(map(str, chart_slides))})"
        )
    if visual_slides:
        parts.append(
            f"; {len(visual_slides)} carry a VISUAL TO ADD note "
            f"(slides {', '.join(map(str, visual_slides))})"
        )
    if not chart_slides and not visual_slides:
        parts.append("; no visuals flagged")
    if fallback_slides:
        parts.append(
            f"; matplotlib not installed — {len(fallback_slides)} chart "
            f"slide(s) fell back to VISUAL TO ADD notes "
            f"(slides {', '.join(map(str, fallback_slides))}); "
            f"pip install matplotlib to draw them"
        )
    if font_warning:
        parts.append(f" [warning: {font_warning}]")
    return "".join(parts)


def _ordered_role_fields(spec):
    """The slide's content fields as (name, value) pairs, in role field order.

    Optional fields that are absent are dropped, so a `title` slide with no
    Subtitle fills only the title placeholder.
    """
    pairs = []
    for name in ROLE_FIELDS[spec["role"]]:
        if name in spec["fields"]:
            value = spec["fields"][name]
            if value == "" or value == []:
                continue
            pairs.append((name, value))
    return pairs


def _content_placeholder_count(slide):
    """Count content placeholders on a slide (no furniture). For error text."""
    from pptxlib import CONTENT_PLACEHOLDER_TYPES

    return sum(
        1
        for ph in slide.placeholders
        if ph.placeholder_format.type in CONTENT_PLACEHOLDER_TYPES
    )


def _drop_unused(placeholders):
    """Remove content placeholders left unfilled, so no empty prompts show.

    Furniture (date/footer/slide number) is never in this list and is kept.
    """
    for ph in placeholders:
        element = ph._element
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)


# --- composed role rendering (D-101 carve-out) -------------------------------


def _resolve_composed_layout(prs, brand):
    """Resolve the layout a composed slide draws on (D-107).

    Prefer an explicit 'composed' mapping; fall back to the statement, then the
    title layout, then index 0 — so a brand.json predating composed mode still
    renders one without edits.
    """
    layout_map = brand.get("layout_map", {}) or {}
    for key in ("composed", "statement", "title"):
        idx = layout_map.get(key)
        if isinstance(idx, int):
            try:
                return prs.slide_layouts[idx]
            except IndexError:
                continue
    return prs.slide_layouts[0]


def _drop_composed_placeholders(slide, keep_title):
    """Remove the layout's content placeholders so no 'click to add' prompts show.

    Keeps the title placeholder when keep_title is True (it holds the Title).
    Furniture (date/footer/slide number) is never touched.
    """
    from pptxlib import CONTENT_PLACEHOLDER_TYPES  # noqa: PLC0415

    title = slide.shapes.title
    title_idx = title.placeholder_format.idx if title is not None else None
    to_drop = []
    for ph in slide.placeholders:
        if ph.placeholder_format.type not in CONTENT_PLACEHOLDER_TYPES:
            continue
        if keep_title and ph.placeholder_format.idx == title_idx:
            continue
        to_drop.append(ph)
    _drop_unused(to_drop)


def _render_composed_slide(prs, brand, spec, tokens):
    """Render a composed slide: fill an optional title, then draw token-bound
    primitives that must pass the mechanical lint before any shape is added.

    primitives.py is the only module that emits literals; lint.py is the gate
    that replaces D-002's structural guarantee. A lint or shape failure becomes
    a SpecError naming the slide, so no half-built deck is saved.
    """
    import primitives  # noqa: PLC0415 — composed decks only
    import lint  # noqa: PLC0415

    number = spec["number"]
    layout = _resolve_composed_layout(prs, brand)
    slide = prs.slides.add_slide(layout)

    grid = tokens.get("grid", {}) or {}
    slide_w, slide_h = prs.slide_width, prs.slide_height

    title = spec.get("fields", {}).get("Title")
    title_ph = slide.shapes.title
    region = None
    if title and title_ph is not None:
        title_ph.text = title
        _, tt, _, th = _geom(slide, title_ph)
        if None not in (tt, th):
            title_bottom = tt + th
        else:
            # Title placeholder inherits geometry we cannot read; reserve a
            # generic top band so the row never overlaps the title.
            title_bottom = grid.get("margin_top", 0) + round(slide_h * 0.12)
        if "margin_x" in grid and "margin_bottom" in grid:
            bottom = slide_h - grid["margin_bottom"]
            if bottom - title_bottom > 0:
                region = (grid["margin_x"], title_bottom,
                          slide_w - 2 * grid["margin_x"],
                          bottom - title_bottom)
        _drop_composed_placeholders(slide, keep_title=True)
    else:
        _drop_composed_placeholders(slide, keep_title=False)

    # Plan every block, then lint the slide's FULL element list once before any
    # shape is drawn — the gate is slide-level, so overlap and the element cap
    # are enforced across all blocks together, not per block.
    all_elements = []
    for block in spec.get("blocks", []):
        btype = block.get("type")
        if btype == "stat-row":
            try:
                all_elements.extend(
                    primitives.plan_stat_row(
                        block["stats"], tokens, slide_w, slide_h, region
                    )
                )
            except primitives.ShapeError as exc:
                raise SpecError(f"slide {number}: {exc}")
        else:
            raise SpecError(
                f"slide {number}: unknown composed block type {btype!r}; "
                f"expected one of: stat-row"
            )

    try:
        lint.check(all_elements, tokens, slide_w, slide_h)
    except lint.LintError as exc:
        raise SpecError(
            f"slide {number}: composed slide failed lint:\n{exc}"
        )
    primitives.draw(slide, all_elements)

    _apply_meta(slide, spec.get("meta", {}))
    return slide


def _apply_meta(slide, meta, extra_visual=None):
    """Write a slide's Visual and Notes fields into its speaker notes.

    A Visual description is recorded — not drawn — prefixed 'VISUAL TO ADD:'.
    Notes prose sits alongside it. Order: notes prose, then the visual line(s).
    `extra_visual` is a second VISUAL TO ADD line (the matplotlib-absent chart
    fallback synthesised by chart_to_note), appended after any Visual field.
    """
    meta = meta or {}
    parts = []
    notes = meta.get("Notes")
    if notes:
        parts.append(_meta_text(notes))
    visual = meta.get("Visual")
    if visual:
        parts.append(f"VISUAL TO ADD: {_meta_text(visual)}")
    if extra_visual:
        parts.append(f"VISUAL TO ADD: {extra_visual}")
    if not parts:
        return
    notes_tf = slide.notes_slide.notes_text_frame
    notes_tf.text = "\n\n".join(parts)


def _meta_text(value):
    """Flatten a meta field value (string or list) to a single string."""
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return str(value)


# --- chart placement and font (D-002 carve-out: geometry from the template) --


def register_brand_font(brand, brand_path):
    """Register brand.json `font_files` with matplotlib for chart text.

    Returns (family_name_or_None, warning_or_None). family is the family the
    chart should use; None means matplotlib's default (with a warning). A
    relative font path resolves against the brand.json directory, like
    `template`. Imported matplotlib lazily — only reached on a chart slide.
    """
    font_files = brand.get("font_files")
    if not isinstance(font_files, dict) or not font_files:
        return None, "no brand font file supplied; charts use a fallback font"

    from matplotlib import font_manager  # noqa: PLC0415

    base = os.path.dirname(os.path.abspath(brand_path)) if brand_path else ""
    registered = None
    for family, path in font_files.items():
        if not os.path.isabs(path) and base:
            path = os.path.normpath(os.path.join(base, path))
        if not os.path.isfile(path):
            return None, (f"brand font file not found ({path}); charts use a "
                          f"fallback font")
        try:
            font_manager.fontManager.addfont(path)
        except Exception:  # noqa: BLE001
            return None, (f"could not register brand font ({path}); charts use "
                          f"a fallback font")
        registered = family
    return registered, None


def _object_placeholder(slide):
    """The content placeholder that hosts the chart (the non-title one)."""
    from pptxlib import CONTENT_PLACEHOLDER_TYPES  # noqa: PLC0415

    title = slide.shapes.title
    title_idx = title.placeholder_format.idx if title is not None else None
    cands = [
        ph for ph in slide.placeholders
        if ph.placeholder_format.type in CONTENT_PLACEHOLDER_TYPES
        and ph.placeholder_format.idx != title_idx
    ]
    cands.sort(key=lambda p: p.placeholder_format.idx)
    return cands[0] if cands else None


def _geom(slide, ph):
    """(left, top, width, height) for a placeholder, falling back to the layout.

    A slide placeholder often inherits geometry (returns None); read the layout
    placeholder of the same idx in that case. Any value may still be None.
    """
    idx = ph.placeholder_format.idx
    layout_ph = None
    for p in slide.slide_layout.placeholders:
        if p.placeholder_format.idx == idx:
            layout_ph = p
            break

    def pick(attr):
        value = getattr(ph, attr)
        if value is None and layout_ph is not None:
            value = getattr(layout_ph, attr)
        return value

    return pick("left"), pick("top"), pick("width"), pick("height")


def _resize_to_text(slide, host, title_ph):
    """Shrink the body placeholder to roughly one line so the chart sits below.

    Sets explicit geometry on the slide placeholder (so it stops inheriting)
    and uses the title placeholder's height as a template-derived one-line
    proxy — no inch literal.
    """
    hl, ht, hw, _ = _geom(slide, host)
    _, _, _, th = _geom(slide, title_ph)
    if None in (hl, ht, hw, th):
        return  # cannot resize without geometry; chart region falls back
    host.left, host.top, host.width, host.height = hl, ht, hw, th


def _chart_region(number, prs, slide, host, title_ph, has_body):
    """Compute the chart's (left, top, width, height) from the template.

    With a body line: span the content width, from just below the resized body
    line down to a bottom margin that mirrors the title's top margin. Chart
    only: use the content placeholder's full region.
    """
    hl, ht, hw, hh = _geom(slide, host)
    if None in (hl, ht, hw, hh):
        raise SpecError(
            f"slide {number}: chart host placeholder has no resolvable "
            f"geometry; re-run teach-slides"
        )
    if not has_body:
        return hl, ht, hw, hh
    _, tt, _, _ = _geom(slide, title_ph)
    margin = tt if tt is not None else ht
    top = ht + hh  # host was resized to one line, so this is the body's bottom
    bottom = prs.slide_height - margin
    height = bottom - top
    if height <= 0:
        raise SpecError(
            f"slide {number}: no room below the body line for a chart"
        )
    return hl, top, hw, height


def _png_size(path):
    """(width, height) in pixels from a PNG's IHDR — no Pillow dependency."""
    import struct  # noqa: PLC0415

    with open(path, "rb") as fh:
        header = fh.read(24)
    return struct.unpack(">II", header[16:24])


def _place_picture(slide, png_path, region):
    """Add the chart PNG, fit inside `region` preserving aspect, centred."""
    left, top, width, height = region
    iw, ih = _png_size(png_path)
    scale = min(width / iw, height / ih)
    w = int(iw * scale)
    h = int(ih * scale)
    x = int(left + (width - w) / 2)
    y = int(top + (height - h) / 2)
    slide.shapes.add_picture(png_path, x, y, width=w, height=h)


def _num_str(value):
    """Compact number for a synthesised note: drop a trailing .0."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def chart_to_note(chart):
    """Synthesise a human-readable VISUAL TO ADD note from a chart dict.

    Used when matplotlib is absent (D-011) so the deck still tells the reader
    exactly what chart belongs on the slide.
    """
    ctype = chart["type"]
    if ctype in ("bar", "column", "pie"):
        cats = chart["categories"]
        series = "; ".join(
            f"{s['name']}: "
            + ", ".join(f"{c} {_num_str(v)}"
                        for c, v in zip(cats, s["values"]))
            for s in chart["series"]
        )
        desc = f"{ctype.capitalize()} chart. {series}."
        if chart.get("emphasis"):
            desc += f" Emphasis: {chart['emphasis']}."
    else:  # line or scatter
        pts = ", ".join(
            f"({_num_str(x)}, {_num_str(y)})" for x, y in chart["points"]
        )
        desc = f"{ctype.capitalize()} chart. Points: {pts}."
        if chart.get("markers"):
            marks = "; ".join(
                f"{m['label']} at {_num_str(m['x'])}"
                for m in chart["markers"]
            )
            desc += f" Markers: {marks}."
    if chart.get("callout"):
        desc += f" Callout: {chart['callout']}."
    return desc + " (Install matplotlib to draw this automatically.)"


if __name__ == "__main__":
    sys.exit(main())
