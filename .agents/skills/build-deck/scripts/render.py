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
import csv
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
# Canvas (REQ-205/D-405) names the colour role a brand-fidelity slide's
# background is painted with; template fidelity rejects it by name (D-411).
# Brief is the composition brief narrative commits per slide (the one thing,
# the form it earns and why, what leads, a named reference): accepted on
# every role, read by build-deck when it composes, never drawn, never notes.
META_FIELDS = {"Visual", "Notes", "Canvas", "Brief"}
# The colour roles a `Canvas:` value may name — the same four canonical role
# names the freeform vocabulary uses (_FREEFORM_COLOURS); listed in the error.
CANVAS_ROLES = ("ink", "paper", "accent", "muted")
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
# (x/y points). `line` is dual: `points:` keeps the x-y path, while
# `categories:` + one or more `series` joins the category pipeline (that is
# how a line chart carries multiple series).
CHART_TYPES = ("bar", "column", "line", "pie", "scatter", "waterfall")
CATEGORY_CHART_TYPES = ("bar", "column", "pie", "waterfall")
POINT_CHART_TYPES = ("line", "scatter")
# Required brand.json keys per fidelity mode (identity-not-layout-plan
# REQ-002). Template fidelity needs the template and the role->layout join;
# brand fidelity draws everything from tokens, so only identity is required.
REQUIRED_BRAND_KEYS = ("template", "fonts", "colours", "layout_map")
REQUIRED_BRAND_KEYS_BRAND = ("fonts", "colours")


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
        register = parse_frontmatter(args.spec).get("register")
        summary = build_deck(
            brand, slides, args.out,
            charts_dir=charts_dir, brand_path=args.brand, spec_path=args.spec,
            register=register,
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
    """Load and validate brand.json per its fidelity mode.

    Raises SpecError naming the bad key. Template fidelity requires the
    four classic keys; brand fidelity requires identity only (fonts,
    colours) — `template` and `layout_map` are optional there, but when
    present are validated and normalised the same way, so one profile can
    carry both modes' data (identity-not-layout-plan REQ-002).
    """
    if not os.path.isfile(path):
        raise SpecError(f"brand profile not found: {path}")
    try:
        with open(path, encoding="utf-8") as fh:
            brand = json.load(fh)
    except json.JSONDecodeError as exc:
        raise SpecError(f"brand profile is not valid JSON: {exc}")
    if not isinstance(brand, dict):
        raise SpecError("brand profile must be a JSON object")

    import tokens  # noqa: PLC0415 — light, stdlib-only module
    try:
        mode = tokens.fidelity_of(brand)
    except ValueError as exc:
        raise SpecError(str(exc))

    required = (
        REQUIRED_BRAND_KEYS_BRAND if mode == "brand" else REQUIRED_BRAND_KEYS
    )
    for key in required:
        if key not in brand:
            raise SpecError(f"brand profile missing required key: {key!r}")

    if "template" in brand:
        template = brand["template"]
        if not isinstance(template, str) or not template.strip():
            raise SpecError(
                "brand profile key 'template' must be a non-empty path"
            )
        # Resolve a relative template path against the brand profile's own
        # directory, so a .slides/ directory is self-contained and portable:
        # it works regardless of the working directory render.py runs from.
        if not os.path.isabs(template):
            brand_dir = os.path.dirname(os.path.abspath(path))
            template = os.path.normpath(os.path.join(brand_dir, template))
        brand["template"] = template

    if "layout_map" in brand:
        layout_map = brand["layout_map"]
        if not isinstance(layout_map, dict) or not layout_map:
            raise SpecError(
                "brand profile key 'layout_map' must be a non-empty object"
            )
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

    spec_dir = os.path.dirname(os.path.abspath(path))
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
        slides.append(_parse_slide(expected_number, slide_lines, spec_dir))
    return slides


def _frontmatter_split(text):
    """Split spec text into (frontmatter_lines, body). Frontmatter may be []."""
    lines = text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].strip() == "---":
        for j in range(i + 1, len(lines)):
            if lines[j].strip() == "---":
                return lines[i + 1:j], "\n".join(lines[j + 1:])
        raise SpecError("frontmatter block opened with '---' but never closed")
    return [], "\n".join(lines[i:])


def _strip_frontmatter(text):
    """Drop the leading `---` YAML frontmatter block, returning the slide body."""
    return _frontmatter_split(text)[1]


def parse_frontmatter(path):
    """Read a spec's frontmatter as a {key: value} dict (keys lowercased).

    The deck-spec frontmatter is flat `key: value` lines (deck, audience,
    register) — parsed minimally, no YAML library. Lines without a colon are
    ignored. A spec with no frontmatter yields {}. Raises SpecError for a
    missing file or an unclosed block, matching parse_spec.
    """
    if not os.path.isfile(path):
        raise SpecError(f"deck spec not found: {path}")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    meta = {}
    for line in _frontmatter_split(text)[0]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key:
            meta[key] = value.strip()
    return meta


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


def _parse_slide(number, lines, spec_dir=None):
    """Parse one slide's lines into role, fields, and meta. Raises SpecError.

    A `layout: composed` slide is routed to _parse_composed_slide before the
    field loop, so its repeated `Block:` lines never trip the stray-field guard.
    The six fixed roles keep their original parse path below, unchanged. spec_dir
    resolves a chart's relative `data:` CSV path.
    """
    if _prescan_layout(lines) == "composed":
        return _parse_composed_slide(number, lines, spec_dir)

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
            fields[current_field] = _parse_chart_block(
                number, current_block, spec_dir
            )
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


# A composed slide reads best with a handful of blocks; more is a wall, not a
# composition. Advisory threshold (the block-count note fires past it) — the
# lint's element cap is the hard backstop, and the advisory count rules police
# items within a block.
MAX_COMPOSED_BLOCKS = 4

# 'at <placement>' shortcuts: half-band placements on the 12x12 block grid.
_PLACEMENT_SHORTCUTS = {
    "left": {"cols": (1, 6), "rows": None, "x": None, "y": None},
    "right": {"cols": (7, 12), "rows": None, "x": None, "y": None},
    "top": {"cols": None, "rows": (1, 6), "x": None, "y": None},
    "bottom": {"cols": None, "rows": (7, 12), "x": None, "y": None},
}

# REQ-204: fine-grained percent bounds — `x 10%-60%` / `y 33.5%-40%`.
# Integers or decimals; the % signs are required (that is what separates the
# percent grammar from a cols/rows typo).
_PERCENT_BOUNDS_RE = re.compile(r"\b(x|y)\s+(\d+(?:\.\d+)?)%\s*-\s*(\d+(?:\.\d+)?)%")


def _parse_placement(number, text):
    """Parse an `at ...` clause into
    {'cols': (c1,c2)|None, 'rows': (r1,r2)|None, 'x': (f0,f1)|None, 'y': ...}.

    The content band is a 12-column by 12-row grid. `cols 1-6` is the left half,
    `rows 1-6` the top half; the two combine (`cols 1-6 rows 7-12` = lower left).
    `left`/`right`/`top`/`bottom` are shortcuts. An unspecified axis spans full.

    REQ-204: `x A%-B%` / `y A%-B%` place by exact band fraction instead —
    parsed to (A/100, B/100) under the 'x'/'y' keys — so the model can
    hand-draw data-accurate graphics (a dumbbell, a slope). The two grammars
    must not mix within one placement: an axis is either on the grid (with its
    breathing insets) or author-owned percent (exact, D-409), never both.
    """
    low = text.strip().lower()
    if low == "full-bleed":
        raise SpecError(
            f"slide {number}: 'at full-bleed' applies only to freeform "
            f"box/panel elements, not to blocks"
        )
    if low in _PLACEMENT_SHORTCUTS:
        return dict(_PLACEMENT_SHORTCUTS[low])
    place = {"cols": None, "rows": None, "x": None, "y": None}
    for m in re.finditer(r"\b(cols|rows)\s+(\d+)\s*-\s*(\d+)", low):
        axis, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        if not 1 <= a <= b <= 12:
            raise SpecError(
                f"slide {number}: placement {axis} {a}-{b} must be within 1-12 "
                f"with start <= end"
            )
        place[axis] = (a, b)
    for m in _PERCENT_BOUNDS_RE.finditer(low):
        axis, token = m.group(1), m.group(0)
        a, b = float(m.group(2)), float(m.group(3))
        if a > 100 or b > 100:
            raise SpecError(
                f"slide {number}: placement {token!r} is out of range — "
                f"percent bounds must sit within 0-100%"
            )
        if a >= b:
            raise SpecError(
                f"slide {number}: placement {token!r} needs start < end — "
                f"equal or inverted percent bounds place nothing"
            )
        place[axis] = (a / 100.0, b / 100.0)
    if (place["cols"] or place["rows"]) and (place["x"] or place["y"]):
        raise SpecError(
            f"slide {number}: placement {text!r} would mix cols/rows with "
            f"x%/y% — pick one grammar per placement"
        )
    if all(place[k] is None for k in ("cols", "rows", "x", "y")):
        raise SpecError(
            f"slide {number}: could not read placement {text!r}; use e.g. "
            f"'at cols 1-6', 'at rows 1-6', 'at x 10%-60%', 'at left', 'at top'"
        )
    return place


def _parse_block_header(number, rest):
    """Parse a `Block:` header value into (type, placement|None).

    'stat-row'              -> ('stat-row', None)
    'card-grid at cols 1-6' -> ('card-grid', {'cols': (1,6), 'rows': None})
    'process at top'        -> ('process', {'cols': None, 'rows': (1,6)})
    """
    parts = rest.split()
    if not parts:
        raise SpecError(
            f"slide {number}: 'Block:' needs a type (e.g. 'Block: stat-row')"
        )
    btype = parts[0].lower()
    if len(parts) == 1:
        return btype, None
    if parts[1].lower() != "at":
        raise SpecError(
            f"slide {number}: unexpected text in 'Block: {rest}'; use "
            f"'Block: <type> at <placement>'"
        )
    place_text = " ".join(parts[2:]).strip()
    if not place_text:
        raise SpecError(
            f"slide {number}: 'at' needs a placement "
            f"(e.g. 'at cols 1-6', 'at left', 'at top')"
        )
    return btype, _parse_placement(number, place_text)


def _parse_composed_slide(number, lines, spec_dir=None):
    """Parse a `composed` slide into title, blocks, and meta. Raises SpecError.

    Recognises `Title:` (optional, inline), `Brief:` (optional, meta), `Canvas:` (optional, a colour-role
    name, REQ-205), `Notes:` (optional, meta), and one or more
    `Block: <type> [at <placement>]` blocks, each followed by its item
    lines. Several blocks either all carry an `at ...` placement (they tile the
    grid) or none do (they stack top to bottom). Returns:

        {"number", "role": "composed", "fields": {"Title": str?, "Canvas": str?},
         "blocks": [parsed block dict + "placement", ...], "meta": {"Notes": str?}}
    """
    title = None
    canvas = None
    brief = None
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
        if low.startswith("canvas:"):
            # REQ-205: the colour role this slide's background is painted
            # with, validated here (this parser never reaches
            # _validate_slide_fields).
            canvas = _validate_canvas_value(
                number, stripped.split(":", 1)[1].strip()
            )
            current = None
            continue
        if low.startswith("brief:"):
            brief = stripped.split(":", 1)[1].strip()
            current = None
            continue
        if low.startswith("notes:"):
            value = stripped.split(":", 1)[1].strip()
            notes_lines = [value] if value else []
            current = "notes"
            continue
        if low.startswith("block:"):
            rest = stripped.split(":", 1)[1].strip()
            btype, placement = _parse_block_header(number, rest)
            current = {"type": btype, "items": [], "placement": placement}
            blocks.append(current)
            continue
        # continuation line
        if not stripped:
            continue
        if current == "notes":
            notes_lines.append(stripped)
        elif isinstance(current, dict):
            # Keep leading indentation: the tree block reads it as hierarchy.
            # Every other block parser strips each item, so this is transparent.
            current["items"].append(raw.rstrip())
        # else: a stray line before any Block/Title/Notes — ignored.

    if not blocks:
        raise SpecError(
            f"slide {number}: composed slide has no 'Block:' (need at least "
            f"one, e.g. 'Block: stat-row')"
        )
    placed = [b for b in blocks if b.get("placement") is not None]
    if placed and len(placed) != len(blocks):
        raise SpecError(
            f"slide {number}: mix of placed and auto-placed blocks; give every "
            f"'Block:' an 'at ...' clause, or none (they then stack top to bottom)"
        )

    parsed_blocks = []
    for b in blocks:
        parsed = _parse_composed_block(number, b, spec_dir)
        parsed["placement"] = b.get("placement")
        parsed_blocks.append(parsed)
    fields = {}
    if title:
        fields["Title"] = title
    if canvas:
        fields["Canvas"] = canvas
    meta = {"Notes": " ".join(notes_lines)} if notes_lines else {}
    if brief:
        meta["Brief"] = brief
    return {
        "number": number,
        "role": "composed",
        "fields": fields,
        "blocks": parsed_blocks,
        "meta": meta,
    }


# Composed block types and the item key each parses its lines into. The order
# is the vocabulary a composed slide may draw from; render dispatches on it too.
COMPOSED_BLOCK_TYPES = (
    "stat-row", "card-grid", "comparison", "process", "timeline", "tree",
    "cycle", "matrix", "icon-list", "table", "chart", "freeform",
)

# Freeform vocabulary — the escape hatch. Colours are role names and sizes are
# scale names (never hex/pt), so a freeform element is on-token by construction;
# the mechanical lint enforces the rest. These name sets are the canonical token
# keys, so they can be validated at parse time without the resolved tokens.
_FREEFORM_KINDS = {"box", "panel", "text", "arrow", "dot", "line", "icon"}
_FREEFORM_COLOURS = {"ink", "paper", "accent", "muted"}
_FREEFORM_SCALES = {"display", "h1", "body", "caption"}


def _clean_item(item):
    """Strip a leading '-'/'*' bullet and a leading '!' emphasis marker.

    Returns (emphasis, text). A line beginning '!' marks the one element that
    leads — the hero card, the winning panel, the milestone that is the turn."""
    text = item.strip()
    if text[:1] in "-*":
        text = text[1:].strip()
    emphasis = text[:1] == "!"
    if emphasis:
        text = text[1:].strip()
    return emphasis, text


def _pipe_fields(text):
    """Split a `a | b` item line into stripped fields."""
    return [p.strip() for p in text.split("|")]


def _extract_icon(number, text):
    """Pull a leading `[icon-name]` off an item, returning (name|None, rest).

    Validates the name against the bundled icon set. Shared by card/process/tree
    items so any of them may carry an optional icon."""
    if text.startswith("[") and "]" in text:
        end = text.find("]")
        name = text[1:end].strip().lower()
        rest = text[end + 1:].strip()
        import icons as _icons  # noqa: PLC0415
        if name not in _icons.available():
            raise SpecError(f"slide {number}: unknown icon {name!r}")
        return name, rest
    return None, text


def _require_name(number, name, allowed, what):
    if name not in allowed:
        raise SpecError(
            f"slide {number}: unknown freeform {what} {name!r}; use one of "
            f"{', '.join(sorted(allowed))}"
        )


def _parse_freeform_element(number, item):
    """Parse one freeform line into an element dict. Raises SpecError.

    Grammar: `<kind> <style...> at <placement> [| text]`
      panel <fill> [outline <stroke>] at <placement>
      box   <fill> [outline <stroke>] at <placement>
      text  <scale> <colour>          at <placement> | the words
      arrow|dot|line <colour>         at <placement>
    Colours are role names (ink/paper/accent/muted), sizes scale names
    (display/h1/body/caption), placement is `cols A-B` / `rows C-D` (or a
    shortcut) on the block's 12x12 grid, or exact percent bounds
    `x A%-B%` / `y A%-B%` of the band (REQ-204). A box/panel may instead sit
    `at full-bleed`: the whole slide, margins included.
    """
    line = item.strip()
    if line[:1] in "-*":
        line = line[1:].strip()
    spec, sep, text = line.partition("|")
    text = text.strip()
    tokens = spec.split()
    if not tokens:
        raise SpecError(f"slide {number}: empty freeform line")
    kind = tokens[0].lower()
    if kind not in _FREEFORM_KINDS:
        raise SpecError(
            f"slide {number}: freeform element starts with one of "
            f"{', '.join(sorted(_FREEFORM_KINDS))}, got {tokens[0]!r}"
        )
    lowered = [t.lower() for t in tokens]
    if "at" not in lowered:
        raise SpecError(
            f"slide {number}: freeform element needs 'at <placement>' "
            f"(e.g. 'at cols 1-6 rows 1-3')"
        )
    at_idx = lowered.index("at")
    style = tokens[1:at_idx]
    place_text = " ".join(tokens[at_idx + 1:])
    if place_text.strip().lower() == "full-bleed":
        # REQ-204: `at full-bleed` paints the whole slide, margins included —
        # only a box/panel may carry it (a background wash, not a text home).
        if kind not in ("box", "panel"):
            raise SpecError(
                f"slide {number}: 'at full-bleed' applies only to freeform "
                f"box/panel elements, not {kind!r}"
            )
        el = {"kind": "box", "placement": None, "full_bleed": True}
    else:
        placement = _parse_placement(number, place_text)
        el = {"kind": "box" if kind == "panel" else kind,
              "placement": placement}

    if kind == "text":
        if len(style) != 2:
            raise SpecError(
                f"slide {number}: freeform text needs '<scale> <colour>' "
                f"(e.g. 'h1 ink'), got {' '.join(style) or '(nothing)'!r}"
            )
        scale, colour = style[0].lower(), style[1].lower()
        _require_name(number, scale, _FREEFORM_SCALES, "type scale")
        _require_name(number, colour, _FREEFORM_COLOURS, "colour")
        if not text:
            raise SpecError(
                f"slide {number}: freeform text needs words after '|'"
            )
        el.update({"scale": scale, "colour": colour, "text": text})
    elif kind in ("box", "panel"):
        if not style:
            raise SpecError(
                f"slide {number}: freeform {kind} needs a fill colour "
                f"(e.g. 'paper outline ink')"
            )
        _require_name(number, style[0].lower(), _FREEFORM_COLOURS, "colour")
        el["fill"] = style[0].lower()
        if len(style) >= 2 and style[1].lower() == "outline":
            if len(style) < 3:
                raise SpecError(
                    f"slide {number}: freeform 'outline' needs a colour after it"
                )
            _require_name(number, style[2].lower(), _FREEFORM_COLOURS, "colour")
            el["stroke"] = style[2].lower()
    elif kind == "icon":
        if len(style) != 2:
            raise SpecError(
                f"slide {number}: freeform icon needs '<name> <colour>' "
                f"(e.g. 'growth accent'), got "
                f"{' '.join(style) or '(nothing)'!r}"
            )
        name, colour = style[0].lower(), style[1].lower()
        import icons as _icons  # noqa: PLC0415 — light, only on an icon line
        if name not in _icons.available():
            raise SpecError(
                f"slide {number}: unknown icon {name!r}; see the bundled "
                f"assets/icons for the available names"
            )
        _require_name(number, colour, _FREEFORM_COLOURS, "colour")
        el["name"] = name
        el["colour"] = colour
    else:  # arrow, dot, line
        if len(style) != 1:
            raise SpecError(
                f"slide {number}: freeform {kind} needs one colour "
                f"(e.g. '{kind} ink at ...')"
            )
        _require_name(number, style[0].lower(), _FREEFORM_COLOURS, "colour")
        el["colour"] = style[0].lower()
    return el


def _parse_tree_items(number, items):
    """Parse an indented list into a nested tree node dict. Raises SpecError.

    2-space indentation = one level (measured from the least-indented line); a
    leading `[icon]` sets a node icon, a leading `!` emphasises it. Exactly one
    root; a level may only jump down by one.
    """
    parsed = [(len(it) - len(it.lstrip(" ")), it.strip()) for it in items]
    if not parsed:
        raise SpecError(f"slide {number}: tree block is empty")
    base = min(indent for indent, _ in parsed)
    root = None
    stack = []  # [(level, node), ...]
    for raw_indent, text in parsed:
        level = (raw_indent - base) // 2
        if text[:1] in "-*":
            text = text[1:].strip()
        emphasis = text[:1] == "!"
        if emphasis:
            text = text[1:].strip()
        icon = None
        if text.startswith("[") and "]" in text:
            end = text.find("]")
            icon = text[1:end].strip().lower()
            text = text[end + 1:].strip()
            import icons as _icons  # noqa: PLC0415
            if icon not in _icons.available():
                raise SpecError(
                    f"slide {number}: unknown icon {icon!r} in tree node"
                )
        if not text:
            raise SpecError(f"slide {number}: a tree node needs a label")
        node = {"label": text, "emphasis": emphasis, "icon": icon, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        if not stack:
            if level != 0:
                raise SpecError(
                    f"slide {number}: tree must start at the root (level 0)"
                )
            if root is not None:
                raise SpecError(
                    f"slide {number}: a tree needs exactly one root node"
                )
            root = node
        else:
            if level != stack[-1][0] + 1:
                raise SpecError(
                    f"slide {number}: tree indentation jumps a level at "
                    f"{text!r}"
                )
            stack[-1][1]["children"].append(node)
        stack.append((level, node))
    return root


def _parse_composed_block(number, block, spec_dir=None):
    """Parse one composed block's raw item lines by type. Raises SpecError.

    Item grammar (a leading '-'/'*' bullet and a leading '!' emphasis marker are
    tolerated on every type):
      stat-row    `value | label`         -> {"stats": [{value, label}]}
      card-grid   `label | body?`         -> {"cards": [{label, body, emphasis}]}
      comparison  `header | body?` x2     -> {"sides": [{header, body, emphasis}]}
      process     `label | detail?`       -> {"steps": [{label, detail}]}
      timeline    `date | event`          -> {"nodes": [{date, event, emphasis}]}
    """
    btype = block["type"]
    items = [it for it in block["items"] if it.strip()]
    if btype not in COMPOSED_BLOCK_TYPES:
        raise SpecError(
            f"slide {number}: unknown composed block type {btype!r}; expected "
            f"one of: {', '.join(COMPOSED_BLOCK_TYPES)}"
        )
    if not items:
        raise SpecError(
            f"slide {number}: {btype} block is empty (add item lines)"
        )

    if btype == "stat-row":
        stats = []
        for item in items:
            _emph, text = _clean_item(item)
            if "|" not in text:
                raise SpecError(
                    f"slide {number}: stat-row line {item!r} must be "
                    f"'value | label'"
                )
            value, label = _pipe_fields(text)[0], text.split("|", 1)[1].strip()
            if not value:
                raise SpecError(
                    f"slide {number}: stat-row line {item!r} has an empty value"
                )
            stats.append({"value": value, "label": label})
        return {"type": "stat-row", "stats": stats}

    if btype == "card-grid":
        cards = []
        for item in items:
            emph, text = _clean_item(item)
            icon, text = _extract_icon(number, text)
            fields = _pipe_fields(text)
            if not fields[0]:
                raise SpecError(
                    f"slide {number}: card-grid line {item!r} needs a label "
                    f"(write '[icon] Label | optional body')"
                )
            cards.append({
                "label": fields[0],
                "body": fields[1] if len(fields) > 1 else "",
                "emphasis": emph,
                "icon": icon,
            })
        return {"type": "card-grid", "cards": cards}

    if btype == "comparison":
        if len(items) != 2:
            raise SpecError(
                f"slide {number}: comparison needs exactly two lines "
                f"('Header | body'), got {len(items)}"
            )
        sides = []
        for item in items:
            emph, text = _clean_item(item)
            icon, text = _extract_icon(number, text)
            fields = _pipe_fields(text)
            if not fields[0]:
                raise SpecError(
                    f"slide {number}: comparison line {item!r} needs a header"
                )
            sides.append({
                "header": fields[0],
                "body": fields[1] if len(fields) > 1 else "",
                "emphasis": emph,
                "icon": icon,
            })
        return {"type": "comparison", "sides": sides}

    if btype == "process":
        steps = []
        for item in items:
            _emph, text = _clean_item(item)
            icon, text = _extract_icon(number, text)
            fields = _pipe_fields(text)
            if not fields[0]:
                raise SpecError(
                    f"slide {number}: process line {item!r} needs a step label"
                )
            steps.append({
                "label": fields[0],
                "detail": fields[1] if len(fields) > 1 else "",
                "icon": icon,
            })
        return {"type": "process", "steps": steps}

    if btype == "freeform":
        els = [_parse_freeform_element(number, it) for it in items]
        return {"type": "freeform", "elements": els}

    if btype == "tree":
        return {"type": "tree", "root": _parse_tree_items(number, items)}

    if btype == "cycle":
        stages = []
        for item in items:
            _emph, text = _clean_item(item)
            label = _pipe_fields(text)[0]
            if not label:
                raise SpecError(
                    f"slide {number}: cycle line {item!r} needs a stage label"
                )
            stages.append({"label": label})
        return {"type": "cycle", "stages": stages}

    if btype == "matrix":
        xlab = ylab = None
        quads = []
        for item in items:
            low = item.strip().lower()
            if low.startswith("x:"):
                xlab = item.split(":", 1)[1].strip()
                continue
            if low.startswith("y:"):
                ylab = item.split(":", 1)[1].strip()
                continue
            emph, text = _clean_item(item)
            fields = _pipe_fields(text)
            if not fields[0]:
                raise SpecError(
                    f"slide {number}: matrix quadrant {item!r} needs a label"
                )
            quads.append({
                "label": fields[0],
                "body": fields[1] if len(fields) > 1 else "",
                "emphasis": emph,
            })
        if len(quads) != 4:
            raise SpecError(
                f"slide {number}: matrix needs exactly four quadrant lines "
                f"(top-left, top-right, bottom-left, bottom-right), got "
                f"{len(quads)}"
            )
        return {"type": "matrix",
                "spec": {"x": xlab, "y": ylab, "quadrants": quads}}

    if btype == "chart":
        # Same `key: value` grammar `Chart:` already parses (data: CSV
        # included), nested under a "chart" key exactly as `table` nests under
        # "table" below (REQ-006/D-006). `_parse_chart_block` raises its own
        # SpecErrors (e.g. "chart block has no 'type'") — nothing extra here.
        return {"type": "chart", "chart": _parse_chart_block(number, items, spec_dir)}

    if btype == "table":
        # Key lines (matrix x:/y: precedent): `data:` names a CSV, `emphasis:`
        # marks a data row by its first cell. Every other item line is a table
        # row; the first is the header, split on '|'; a leading '!' via
        # _clean_item flags a data row.
        data_file = emphasis_label = None
        row_lines = []
        for item in items:
            low = item.strip().lower()
            if low.startswith("data:"):
                data_file = item.split(":", 1)[1].strip()
                continue
            if low.startswith("emphasis:"):
                emphasis_label = item.split(":", 1)[1].strip()
                continue
            row_lines.append(item)

        if data_file is not None:
            if row_lines:
                raise SpecError(
                    f"slide {number}: table 'data:' cannot be combined with "
                    f"inline rows (use one or the other)"
                )
            header, rows = _read_table_csv(number, data_file, spec_dir)
        else:
            if not row_lines:
                raise SpecError(
                    f"slide {number}: table block needs a header row and at "
                    f"least one data row"
                )
            header = _pipe_fields(_clean_item(row_lines[0])[1])
            rows = []
            for item in row_lines[1:]:
                emph, text = _clean_item(item)
                rows.append({"cells": _pipe_fields(text), "emphasis": emph})

        if len(header) < 2:
            raise SpecError(
                f"slide {number}: a one-column table is a list, not a table; "
                f"use 'Block: icon-list' or a Body with bullets"
            )
        for row in rows:
            if len(row["cells"]) != len(header):
                raise SpecError(
                    f"slide {number}: table row {' | '.join(row['cells'])!r} "
                    f"has {len(row['cells'])} cells but the header has "
                    f"{len(header)} (ragged row)"
                )
        if emphasis_label is not None:
            first_col = [r["cells"][0] for r in rows if r["cells"]]
            matched = False
            for r in rows:
                if r["cells"] and r["cells"][0] == emphasis_label:
                    r["emphasis"] = True
                    matched = True
            if not matched:
                raise SpecError(
                    f"slide {number}: table emphasis {emphasis_label!r} matches "
                    f"no row; first-column values are: {', '.join(first_col)}"
                )
        return {"type": "table", "table": {"header": header, "rows": rows}}

    if btype == "icon-list":
        rows = []
        for item in items:
            _emph, text = _clean_item(item)
            if "|" not in text:
                raise SpecError(
                    f"slide {number}: icon-list line {item!r} must be "
                    f"'icon | text'"
                )
            name, txt = text.split("|", 1)
            name, txt = name.strip().lower(), txt.strip()
            import icons as _icons  # noqa: PLC0415
            if name not in _icons.available():
                raise SpecError(f"slide {number}: unknown icon {name!r}")
            if not txt:
                raise SpecError(
                    f"slide {number}: icon-list line {item!r} needs text"
                )
            rows.append({"icon": name, "text": txt})
        return {"type": "icon-list", "rows": rows}

    # timeline
    nodes = []
    for item in items:
        emph, text = _clean_item(item)
        if "|" in text:
            date, event = _pipe_fields(text)[0], text.split("|", 1)[1].strip()
        else:
            date, event = "", text
        if not event:
            raise SpecError(
                f"slide {number}: timeline line {item!r} needs an event "
                f"(write 'date | event')"
            )
        nodes.append({"date": date, "event": event, "emphasis": emph})
    return {"type": "timeline", "nodes": nodes}


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


def _is_chart_number(token):
    """True when a CSV cell would parse as a chart number (shape probing)."""
    try:
        float(str(token).strip())
        return True
    except ValueError:
        return False


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


def _parse_bool_key(number, key, value):
    """Parse a chart boolean key's value: true/yes or false/no, case-
    insensitive. Raises SpecError naming the key and the bad token verbatim
    (native-charts-plan.md D-001/D-009)."""
    low = value.strip().lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    raise SpecError(
        f"slide {number}: chart '{key}:' must be true or false, got "
        f"{value.strip()!r}"
    )


def _parse_target(number, value):
    """Parse a chart `target:` value into {'value': float, 'label': str|None}.

    Grammar (D-009): 'target: 50' or 'target: 50 | goal' — the label is
    optional. Raises SpecError naming the bad token when the value is not
    numeric.
    """
    raw_value, _, raw_label = value.partition("|")
    token = raw_value.strip()
    try:
        target_value = float(token)
    except ValueError:
        raise SpecError(
            f"slide {number}: chart 'target:' value {token!r} is not a number"
        )
    label = raw_label.strip() or None
    return {"value": target_value, "label": label}


# Chart value-label format shorthands → {prefix?, suffix?, abbreviate?}.
CHART_FORMAT_SHORTHANDS = {
    "$": {"prefix": "$"},
    "$k": {"prefix": "$", "suffix": "k"},
    "$m": {"prefix": "$", "suffix": "M"},
    "%": {"suffix": "%"},
    "k": {"suffix": "k"},
    "m": {"suffix": "M"},
    "currency": {"prefix": "$"},
    "percent": {"suffix": "%"},
    "compact": {},
    "plain": {"abbreviate": False},
}


def _read_chart_csv(number, path, ctype):
    """Read a CSV into chart data. Raises SpecError naming the slide.

    Category charts: header row = [axis, series1, series2, ...], first column =
    category labels. Point charts (line/scatter): first two columns = x, y.
    Returns {"categories", "series"} or {"points"}.
    """
    if not os.path.isfile(path):
        raise SpecError(f"slide {number}: chart data file not found: {path}")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise SpecError(
            f"slide {number}: chart data {path!r} needs a header row and at "
            f"least one data row"
        )
    header, body = [c.strip() for c in rows[0]], rows[1:]
    category_shape = ctype in CATEGORY_CHART_TYPES
    if ctype == "line":
        # A line CSV is dual-shaped: 3+ columns (several series) or a
        # non-numeric first column (category labels) read as a category
        # chart; exactly two numeric columns stay x,y points (back-compat).
        # To force categories with 2 numeric columns, use inline
        # `categories:` + `series` instead of `data:`.
        category_shape = (len(header) >= 3
                          or not all(_is_chart_number(r[0]) for r in body))
    if category_shape:
        if len(header) < 2:
            raise SpecError(
                f"slide {number}: chart data {path!r} needs a category column "
                f"and at least one series column"
            )
        cats = [r[0].strip() for r in body]
        series = []
        for col in range(1, len(header)):
            name = header[col] or f"Series {col}"
            values = [_chart_number(number, r[col]) for r in body]
            series.append({"name": name, "values": values})
        return {"categories": cats, "series": series}
    # point charts: first two columns are x, y
    points = [(_chart_number(number, r[0]), _chart_number(number, r[1]))
              for r in body if len(r) >= 2]
    if not points:
        raise SpecError(f"slide {number}: chart data {path!r} has no x,y rows")
    return {"points": points}


def _read_table_csv(number, data_file, spec_dir):
    """Read a table CSV into (header, rows). Raises SpecError naming the file.

    Header row then data rows, all plain strings — a table CSV carries no
    numeric coercion (a table shows values verbatim). Rows come back in the
    same `{"cells": [...], "emphasis": bool}` shape as inline rows; emphasis is
    always False here and is set later by the `emphasis:` key line.
    """
    path = (data_file if os.path.isabs(data_file)
            else os.path.join(spec_dir or ".", data_file))
    if not os.path.isfile(path):
        raise SpecError(f"slide {number}: table data file not found: {path}")
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            raw = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    except UnicodeDecodeError:
        raise SpecError(
            f"slide {number}: table data file {path!r} is not valid UTF-8"
        )
    if len(raw) < 2:
        raise SpecError(
            f"slide {number}: table data {path!r} needs a header row and at "
            f"least one data row"
        )
    header = [c.strip() for c in raw[0]]
    rows = [{"cells": [c.strip() for c in r], "emphasis": False}
            for r in raw[1:]]
    return header, rows


def _parse_chart_block(number, lines, spec_dir=None):
    """Parse a Chart block's raw lines into a chart dict. Raises SpecError.

    Data is either typed inline (`categories`/`series`/`points`) or read from a
    CSV named by `data:` (resolved against the spec's directory) — not both.

    `native:`/`stacked:`/`target:` (native-charts-plan.md REQ-001/004/005) are
    ALWAYS present on the returned dict — default False/False/None — so
    downstream code never `.get`-guesses. `stacked:` is legal only on a
    multi-series bar/column chart (not combined with `emphasis:`); `target:`
    is legal only on column/bar/line.

    Returns one of:
      bar/column: {type, categories: [str], series: [{name, values:[float]}],
                   emphasis: str|None, callout: str|None, fmt, native, stacked,
                   target}
      line:       {type, points: [(x,y)], markers: [{x,label}],
                   callout: str|None, fmt, native, stacked, target}
    """
    ctype = categories = callout = emphasis = data_file = None
    fmt_key = prefix_key = suffix_key = total_key = None
    native_key = stacked_key = target_key = None
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
        elif key == "data":
            data_file = value
        elif key == "format":
            fmt_key = value
        elif key == "prefix":
            prefix_key = value
        elif key == "suffix":
            suffix_key = value
        elif key == "total":
            total_key = value
        elif key == "native":
            native_key = value
        elif key == "stacked":
            stacked_key = value
        elif key == "target":
            target_key = value
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

    fmt = {}
    if fmt_key is not None:
        shorthand = fmt_key.strip().lower()
        if shorthand not in CHART_FORMAT_SHORTHANDS:
            raise SpecError(
                f"slide {number}: unknown chart format {fmt_key!r}; use one of "
                f"{', '.join(sorted(CHART_FORMAT_SHORTHANDS))}, or prefix:/suffix:"
            )
        fmt.update(CHART_FORMAT_SHORTHANDS[shorthand])
    if prefix_key is not None:
        fmt["prefix"] = prefix_key
    if suffix_key is not None:
        fmt["suffix"] = suffix_key

    # `total:` only means anything on a waterfall (the computed end bar). Absent
    # -> "Total"; `none` -> no total bar; any other value renames the bar.
    if ctype == "waterfall":
        if total_key is None:
            total_label = "Total"
        elif total_key.strip().lower() == "none":
            total_label = None
        else:
            total_label = total_key.strip()
    elif total_key is not None:
        raise SpecError(
            f"slide {number}: 'total:' is only supported on a waterfall chart, "
            f"not {ctype!r}"
        )

    # native:/stacked:/target: (native-charts-plan.md REQ-001/004/005): always
    # present on the returned dict. Type-legality is checked here (it depends
    # only on ctype); stacked's series-count/emphasis conflicts are checked
    # further below, once `series` is final (a `data:` CSV may still populate
    # it).
    native = (_parse_bool_key(number, "native", native_key)
              if native_key is not None else False)

    stacked = (_parse_bool_key(number, "stacked", stacked_key)
               if stacked_key is not None else False)
    if stacked and ctype not in ("bar", "column"):
        raise SpecError(
            f"slide {number}: chart 'stacked:' is only supported on bar or "
            f"column charts, not {ctype!r}"
        )

    target = None
    if target_key is not None:
        if ctype not in ("column", "bar", "line"):
            raise SpecError(
                f"slide {number}: chart 'target:' is only supported on "
                f"column, bar, or line charts, not {ctype!r}"
            )
        target = _parse_target(number, target_key)

    if data_file is not None:
        if categories or series or points:
            raise SpecError(
                f"slide {number}: chart 'data:' cannot be combined with inline "
                f"categories/series/points"
            )
        path = (data_file if os.path.isabs(data_file)
                else os.path.join(spec_dir or ".", data_file))
        loaded = _read_chart_csv(number, path, ctype)
        categories = loaded.get("categories")
        series = loaded.get("series", [])
        points = loaded.get("points")

    # `line` is dual-shaped: `points:` keeps the x-y path; the category
    # grammar (categories + series) is how a line carries multiple series.
    if ctype == "line" and points is not None and (categories or series):
        raise SpecError(
            f"slide {number}: a line chart takes either 'points:' or "
            f"'categories:' + 'series', not both"
        )
    category_line = ctype == "line" and points is None

    if ctype in CATEGORY_CHART_TYPES or category_line:
        if not categories:
            raise SpecError(
                f"slide {number}: chart type {ctype!r} needs 'categories'"
                + (" + 'series', or 'points'" if category_line else "")
            )
        if not series:
            raise SpecError(
                f"slide {number}: chart type {ctype!r} needs at least one "
                f"'series'"
            )
        if category_line and markers:
            raise SpecError(
                f"slide {number}: chart 'marker:' needs a points line (it is "
                f"x-keyed); use 'callout:' instead"
            )
        if ctype == "pie" and len(series) != 1:
            raise SpecError(
                f"slide {number}: a pie chart needs exactly one series, not "
                f"{len(series)}"
            )
        if ctype == "waterfall" and len(series) != 1:
            raise SpecError(
                f"slide {number}: a waterfall chart needs exactly one series "
                f"of signed deltas, not {len(series)}"
            )
        if ctype == "waterfall" and emphasis is not None:
            raise SpecError(
                f"slide {number}: 'emphasis' is not supported on a waterfall "
                f"chart; the sign colouring already marks rises and falls — use "
                f"'callout' to point at a bar instead"
            )
        for s in series:
            if len(s["values"]) != len(categories):
                raise SpecError(
                    f"slide {number}: chart series {s['name']!r} has "
                    f"{len(s['values'])} values but there are "
                    f"{len(categories)} categories (length mismatch)"
                )
        if category_line:
            # On a line, emphasis names the SERIES to accent (the one line
            # that carries the point) — not a category, which has no single
            # mark to colour on a line chart.
            if emphasis is not None and emphasis not in {s["name"]
                                                         for s in series}:
                raise SpecError(
                    f"slide {number}: chart emphasis {emphasis!r} is not one "
                    f"of the series names (on a line chart, emphasis names a "
                    f"series, not a category)"
                )
        elif emphasis is not None and emphasis not in categories:
            raise SpecError(
                f"slide {number}: chart emphasis {emphasis!r} is not one of "
                f"the categories"
            )
        if stacked and len(series) < 2:
            raise SpecError(
                f"slide {number}: chart 'stacked:' needs at least two series, "
                f"got {len(series)} (a single series has nothing to stack)"
            )
        if stacked and emphasis is not None:
            raise SpecError(
                f"slide {number}: chart 'stacked:' cannot combine with "
                f"'emphasis:' (a stacked chart reads by series, emphasis "
                f"names a category — drop one)"
            )
        if ctype == "waterfall":
            return {"type": ctype, "categories": categories, "series": series,
                    "callout": callout, "fmt": fmt, "total_label": total_label,
                    "native": native, "stacked": stacked, "target": target}
        return {"type": ctype, "categories": categories, "series": series,
                "emphasis": emphasis, "callout": callout, "fmt": fmt,
                "native": native, "stacked": stacked, "target": target}

    # scatter, or a line given `points:` (a category-shaped line routed above)
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
            "callout": callout, "fmt": fmt,
            "native": native, "stacked": stacked, "target": target}


def _validate_canvas_value(number, value):
    """A `Canvas:` value must name one of the four canonical colour roles
    (REQ-205). Returns the normalised (lower-cased) role name, or raises a
    SpecError naming the bad value and listing the roles."""
    canvas = str(value or "").strip().lower()
    if canvas not in CANVAS_ROLES:
        raise SpecError(
            f"slide {number}: unknown Canvas colour role {value!r}; "
            f"use one of {', '.join(CANVAS_ROLES)}"
        )
    return canvas


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

    # REQ-205: a Canvas value must name a colour role; normalise it in place
    # so the renderer and the round trip read one canonical spelling.
    if "Canvas" in fields:
        fields["Canvas"] = _validate_canvas_value(number, fields["Canvas"])
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


def build_deck(brand, slides, out_path, charts_dir=None, brand_path=None,
                spec_path=None, register=None):
    """Render parsed slides into a .pptx at out_path. Returns a summary string.

    A slide carrying a `Chart` is drawn natively: charts.py renders a PNG and
    it is placed below the body line. If matplotlib is not importable the chart
    degrades to a `VISUAL TO ADD:` note (D-011) so the deck still builds.

    spec_path (REQ-001/D-003), when given, stamps the rendered deck's
    core_properties.comments with `slides-spec: <basename> sha256:<sha>` so
    a deck names the spec it came from; direct in-process callers that omit
    it get no stamp.

    register, when given, is the spec frontmatter's register line; it keys
    the pack type scale in brand fidelity (tokens.resolve_tokens) and is
    ignored in template fidelity.
    """
    import tokens as tokens_mod  # noqa: PLC0415 — fidelity + brand-mode tokens
    try:
        fidelity = tokens_mod.fidelity_of(brand)
    except ValueError as exc:
        raise SpecError(str(exc))

    hierarchy_note = None
    if fidelity == "template":
        template = brand.get("template")
        if not template:
            raise SpecError("brand profile missing required key: 'template'")
        if not os.path.isfile(template):
            raise SpecError(
                f"template named in brand profile not found: {template}"
            )
        try:
            prs = load_template(template)
        except Exception as exc:  # noqa: BLE001
            raise SpecError(f"could not open template {template}: {exc}")

        # Strip any pre-existing slides so a user may reuse a real deck as a
        # template; only its masters and layouts matter.
        sld_id_lst = prs.slides._sldIdLst
        for sld in list(sld_id_lst):
            sld_id_lst.remove(sld)

        layout_map = brand.get("layout_map")
        if not layout_map:
            raise SpecError("brand profile missing required key: 'layout_map'")

        # REQ-008 tripwire: a master whose body text is as big as its title
        # cannot express hierarchy — the fault that placeholder fill copies
        # verbatim. Non-blocking: the deck still renders, the summary says so.
        from pptxlib import read_type_scale  # noqa: PLC0415
        _sizes = read_type_scale(prs)
        _t, _b = _sizes.get("title"), _sizes.get("body")
        if _t and _b and _b >= _t:
            hierarchy_note = (
                f"template master body size ({_b:g}pt) >= title size "
                f"({_t:g}pt) — hierarchy will not read; consider "
                f'"fidelity": "brand"'
            )
    else:
        # Brand fidelity (D-305): the base deck is built in-process from the
        # brand's identity. The template file, even when brand.json names
        # one, is never opened here.
        prs = _brand_base_presentation(brand)
        layout_map = None

    if charts_dir is None:
        charts_dir = os.path.splitext(out_path)[0] + ".charts"
    visual_slides = []
    chart_slides = []        # drawn natively
    fallback_slides = []     # matplotlib absent -> VISUAL TO ADD note
    charts_mod = "unset"     # imported lazily once, on the first chart slide
    native_charts_mod = "unset"  # imported lazily once, on the first native chart
    font_family = "unset"    # resolved lazily once, when first drawing a chart
    font_warning = None
    composed_tokens = None   # resolved lazily once, on the first composed slide
    composed_advisories = []  # [(slide_number, [finding, ...])] — non-blocking
    icon_fallback_slides = []  # [(slide_number, [icon name, ...])] — rasteriser absent
    # Non-blocking render adjustments, one note each: a chart that requested
    # `native:` but fell back to the matplotlib image (native-charts-plan.md
    # D-005 — unsupportable type, or the backend is unavailable), or a table
    # stepped down to caption size to fit its band.
    render_notes = []
    if hierarchy_note:
        render_notes.append(hierarchy_note)
    section_counter = 0  # brand fidelity: ordinal for the section ghost numeral
    # Reflex/earn-it check (deck-level): accumulate each content slide's primary
    # device across the whole deck, then flag one device carried deck-wide after
    # the loop. Fidelity-agnostic — composed slides route the same in both modes.
    import composition as _composition  # noqa: PLC0415 — deck-level advisory
    device_tally = []
    content_slides = 0

    for spec in slides:
        number = spec["number"]
        role = spec["role"]

        if role not in ("title", "section"):
            content_slides += 1
        if role == "composed":
            _blocks = spec.get("blocks") or []
            _first = _blocks[0].get("type") if _blocks else None
            if _first in _composition.DECK_DEVICE_TYPES:
                device_tally.append(_first)

        # D-411: Canvas is brand-fidelity vocabulary — placeholder fill has
        # no token background to paint. Rejected by name, never silently
        # dropped.
        if fidelity == "template" and (
            spec.get("meta", {}).get("Canvas")
            or spec.get("fields", {}).get("Canvas")
        ):
            raise SpecError(
                f"slide {number}: Canvas is a brand-fidelity field; "
                f'remove it or set "fidelity": "brand"'
            )

        if fidelity == "brand":
            if composed_tokens is None:
                composed_tokens = tokens_mod.resolve_tokens(
                    brand, prs, register
                )
            if role == "composed":
                (advisories, dropped_icons, slide_render_notes, font_family,
                 font_warning) = _render_composed_slide(
                    prs, brand, spec, composed_tokens, charts_dir,
                    font_family, font_warning, brand_path, pack_canvas=True
                )
                if advisories:
                    composed_advisories.append((number, advisories))
                if dropped_icons:
                    icon_fallback_slides.append((number, dropped_icons))
                render_notes.extend(slide_render_notes)
            else:
                if role == "section":
                    section_counter += 1
                (advisories, slide_render_notes, chart_kind, font_family,
                 font_warning) = _render_role_slide_brand(
                    prs, brand, spec, composed_tokens, charts_dir,
                    font_family, font_warning, brand_path,
                    ordinal=section_counter if role == "section" else None,
                )
                if advisories:
                    composed_advisories.append((number, advisories))
                render_notes.extend(slide_render_notes)
                if chart_kind in ("native", "image"):
                    chart_slides.append(number)
                elif chart_kind == "fallback":
                    fallback_slides.append(number)
                if "Visual" in spec["meta"]:
                    visual_slides.append(number)
            continue

        if role == "composed":
            if composed_tokens is None:
                composed_tokens = tokens_mod.resolve_tokens(
                    brand, prs, register
                )
            (advisories, dropped_icons, slide_render_notes, font_family,
             font_warning) = _render_composed_slide(
                prs, brand, spec, composed_tokens, charts_dir,
                font_family, font_warning, brand_path
            )
            if advisories:
                composed_advisories.append((number, advisories))
            if dropped_icons:
                icon_fallback_slides.append((number, dropped_icons))
            render_notes.extend(slide_render_notes)
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
            # native-charts-plan.md D-002/D-005: `native: true` tries the
            # native_charts backend first (lazy import, cached like charts_mod
            # below); an unsupportable chart or a missing native_charts module
            # falls back to the matplotlib image path with a run-summary note
            # naming the reason — never an error.
            native_ok = False
            if chart["native"]:
                if native_charts_mod == "unset":
                    try:
                        import native_charts as native_charts_mod  # noqa: PLC0415
                    except ImportError:
                        native_charts_mod = None
                if native_charts_mod is None:
                    reason = "native chart backend unavailable"
                else:
                    native_ok, reason = native_charts_mod.supported(chart)
                if not native_ok:
                    render_notes.append(
                        f"slide {number}: {reason}; drawn as an image"
                    )

            if not native_ok and charts_mod == "unset":
                try:
                    import charts as charts_mod  # noqa: PLC0415
                except ImportError:
                    charts_mod = None

            if native_ok or charts_mod is not None:
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

                if native_ok:
                    native_charts_mod.insert(
                        slide, chart, brand["colours"], region
                    )
                    chart_slides.append(number)
                else:
                    if font_family == "unset":
                        font_family, font_warning = register_brand_font(
                            brand, brand_path
                        )
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
            else:
                # Graceful degradation (D-011): record the chart as a note.
                extra_visual = chart_to_note(chart)
                fallback_slides.append(number)

        _drop_unused(unused)
        _apply_meta(slide, spec["meta"], extra_visual=extra_visual)
        if "Visual" in spec["meta"]:
            visual_slides.append(number)

    # Deck-level reflex/earn-it advisory: one named device carried across the
    # deck. Appended under sentinel slide 0 (a deck-wide finding has no one
    # slide); the summary renders it "slide 0 [deck-device-repetition] ...".
    # Wrapped like every advisory (mirrors the composed-slide review guard): a
    # broken advisory layer must never change the exit code of a render that
    # already passed its lint gate.
    try:
        _dev_adv = _composition.deck_device_repetition(
            device_tally, content_slides)
        if _dev_adv:
            composed_advisories.append((0, [_dev_adv]))
    except Exception:  # noqa: BLE001 — advisory must never block a render
        pass

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if spec_path is not None:
        # Lineage stamp (REQ-001/D-003): deck_to_spec.py / the revise skill
        # read this back to find the spec a rendered deck came from. The
        # fixture template (and any user template) may already carry text in
        # core_properties.comments (e.g. python-pptx's own default) — that is
        # overwritten unconditionally, by design (plan risk 4): on a
        # generated deck, the comments field is ours.
        import stamp as stamp_mod
        prs.core_properties.comments = stamp_mod.lineage_comment(spec_path)

    prs.save(out_path)

    return _summary(out_path, len(slides), visual_slides, chart_slides,
                    fallback_slides, font_warning,
                    composed_advisories=composed_advisories,
                    icon_fallback_slides=icon_fallback_slides,
                    render_notes=render_notes, fidelity=fidelity)


def _summary(out_path, n_slides, visual_slides, chart_slides, fallback_slides,
             font_warning, composed_advisories=None, icon_fallback_slides=None,
             render_notes=None, fidelity=None):
    """Compose the one-line run summary, naming charts, notes, and warnings."""
    parts = [f"rendered {n_slides} slide(s) to {out_path}"]
    if fidelity == "brand":
        parts.append(
            '; fidelity: brand — pack design '
            '(set "fidelity": "template" in brand.json for template '
            'placeholder-fill)'
        )
    elif fidelity == "template":
        parts.append(
            '; fidelity: template — the template carries the look '
            '(set "fidelity": "brand" for pack design)'
        )
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
    if render_notes:
        parts.append(
            f"; {len(render_notes)} render note(s): "
            + "; ".join(render_notes)
        )
    if icon_fallback_slides:
        n = sum(len(names) for _, names in icon_fallback_slides)
        parts.append(
            f"; cairosvg not installed — {n} icon(s) not drawn "
            f"(slides {', '.join(str(s) for s, _ in icon_fallback_slides)}); "
            f"pip install cairosvg to draw them"
        )
    if font_warning:
        parts.append(f" [warning: {font_warning}]")
    if composed_advisories:
        n = sum(len(f) for _, f in composed_advisories)
        # One finding per line, id + message: the note should teach the craft
        # rule it is nudging toward, not just name it.
        parts.append(
            f"; {n} composition advisory note(s) (not blocking):\n"
            + "\n".join(
                f"  slide {num} [{fd['rule_id']}] {fd.get('message', '')}"
                for num, finds in composed_advisories
                for fd in finds
            )
        )
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


def _full_band(grid, slide_w, slide_h):
    """The full content band (left, top, width, height) inside the margins."""
    mx = grid.get("margin_x", 0)
    mt = grid.get("margin_top", 0)
    mb = grid.get("margin_bottom", 0)
    return (mx, mt, slide_w - 2 * mx, slide_h - mt - mb)


def _place_region(base_band, placement, tokens):
    """Sub-rect of the band for an explicit `at cols/rows` placement.

    The band is a 12-column by 12-row grid. A small breathing inset keeps two
    adjacent placements from touching, so the slide-level lint's no-overlap rule
    is never even tested at the seam.

    REQ-204/D-409: an `x A%-B%` / `y A%-B%` placement resolves as an exact
    band fraction instead — no insets, the author owns the geometry. An axis
    left unspecified spans the full band, as with single-axis grid spans.
    """
    bl, bt, bw, bh = base_band
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
    grid = tokens.get("grid", {}) or {}
    cols_n = grid.get("columns", 12) or 12
    rows_n = 12
    cols, rows = placement.get("cols"), placement.get("rows")
    if cols:
        left = bl + (cols[0] - 1) * bw // cols_n
        right = bl + cols[1] * bw // cols_n
    else:
        left, right = bl, bl + bw
    if rows:
        top = bt + (rows[0] - 1) * bh // rows_n
        bottom = bt + rows[1] * bh // rows_n
    else:
        top, bottom = bt, bt + bh
    pad_x = grid.get("gutter", 0) // 2
    pad_y = grid.get("baseline", 0)
    left += pad_x
    right -= pad_x
    top += pad_y
    bottom -= pad_y
    return (left, top, max(1, right - left), max(1, bottom - top))


def _stack_regions(base_band, n, tokens):
    """Split the band into n stacked full-width slices, top to bottom."""
    bl, bt, bw, bh = base_band
    gap = tokens.get("grid", {}).get("baseline", 0)
    slice_h = (bh - (n - 1) * gap) // n
    regions = []
    for i in range(n):
        top = bt + i * (slice_h + gap)
        h = slice_h if i < n - 1 else bh - (n - 1) * (slice_h + gap)
        regions.append((bl, top, bw, h))
    return regions


def _composed_regions(base_band, blocks, tokens):
    """One region per block: the whole band for a lone block, an explicit
    placement per block when any carries one, else an even top-to-bottom stack."""
    n = len(blocks)
    if n == 0:
        return []
    if n == 1 and blocks[0].get("placement") is None:
        return [base_band]
    if any(b.get("placement") is not None for b in blocks):
        return [_place_region(base_band, b["placement"], tokens) for b in blocks]
    return _stack_regions(base_band, n, tokens)


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


def _icon_px(el):
    """Raster size (px) for an icon element: ~200 dpi at its placed width, clamped."""
    px = round(el["width"] / 914400 * 200)
    return max(48, min(px, 512))


def _overload_hint(blocks):
    """One teaching line for a composed slide that failed the lint because a
    block simply carries too many items. The count caps are advisory now, so
    the geometry is what refuses — this restores the old caps' "split the
    slide" guidance exactly when that happens. Returns "" when no block looks
    overloaded (the lint failure is then something else).
    """
    def tree_nodes(node):
        return 1 + sum(tree_nodes(c) for c in (node.get("children") or []))

    # (parsed-items key, count fn, count past which a block rarely fits)
    heavy = {
        "stat-row": ("stats", len, 5),
        "card-grid": ("cards", len, 5),
        "process": ("steps", len, 5),
        "timeline": ("nodes", len, 6),
        "icon-list": ("rows", len, 6),
        "cycle": ("stages", len, 6),
        "tree": ("root", tree_nodes, 8),
        "table": ("table", lambda t: len(t.get("rows") or []), 8),
    }
    for block in blocks:
        entry = heavy.get(block.get("type"))
        if entry is None:
            continue
        key, count, good = entry
        n = count(block.get(key) or {})
        if n > good:
            noun = "rows" if block["type"] == "table" else "items"
            return (
                f"hint: the {block['type']} block has {n} {noun}; that many "
                f"rarely fits — cut {noun} or split the slide"
            )
    return ""


def _brand_base_presentation(brand):
    """The brand-fidelity base deck, built in-process (D-305).

    python-pptx's bundled default package, stripped of slides, with the
    brand's fonts and colours written into the theme (pptxlib.apply_theme) —
    identity from brand.json, geometry from nobody. The template file, even
    when brand.json names one, is never opened: its identity was extracted
    into fonts/colours at init time.
    """
    from pptx import Presentation as _Presentation  # noqa: PLC0415
    from pptxlib import apply_theme  # noqa: PLC0415

    prs = _Presentation()
    # The bundled default package is 4:3 (10in x 7.5in). The pack canvas is
    # 16:9 — matching tokens.pack_grid's default dims — so brand decks land
    # in the modern frame regardless of what python-pptx ships.
    prs.slide_width = 12192000
    prs.slide_height = 6858000
    sld_id_lst = prs.slides._sldIdLst
    for sld in list(sld_id_lst):
        sld_id_lst.remove(sld)
    apply_theme(prs, brand)
    return prs


def _blank_layout(prs):
    """The layout brand-fidelity slides draw on.

    The first layout with no CONTENT placeholders — T-200 finding: every
    bundled layout carries date/footer/slide-number furniture, so a literal
    zero-placeholder layout does not exist; "Blank" (index 6 in the bundled
    default) is the canonical hit. Falls back to index 6, then the last.
    """
    from pptxlib import CONTENT_PLACEHOLDER_TYPES  # noqa: PLC0415

    layouts = list(prs.slide_layouts)
    for layout in layouts:
        if not any(
            ph.placeholder_format.type in CONTENT_PLACEHOLDER_TYPES
            for ph in layout.placeholders
        ):
            return layout
    return layouts[6] if len(layouts) > 6 else layouts[-1]


def _strip_placeholders(slide):
    """Remove EVERY inherited placeholder from a brand-fidelity slide —
    furniture included. Brand mode draws everything it wants shown."""
    _drop_unused(list(slide.placeholders))


def _paint_background(slide, canvas_hex):
    """Paint the slide's own background with a canvas colour (REQ-005/205) —
    the paper role by default, or the slide's `Canvas:` role.

    A slide-level solid fill, not a shape: it costs no lint element and
    covers whatever the layout would otherwise show through (A-004 probe:
    python-pptx persists the <p:bg> across save/reopen).
    """
    from pptx.dml.color import RGBColor  # noqa: PLC0415

    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor.from_string(canvas_hex.lstrip("#"))


def _brand_chart_region(elements, tokens, slide_w, slide_h):
    """The band left under a brand-mode title-content slide's planned text:
    full content width, from two baselines below the deepest element to the
    bottom margin. None when nothing usable remains (< four baselines)."""
    grid = tokens["grid"]
    bottom = slide_h - grid["margin_bottom"]
    content_bottom = max(
        (el["top"] + el["height"] for el in elements),
        default=grid["margin_top"],
    )
    top = content_bottom + 2 * grid["baseline"]
    if bottom - top < 4 * grid["baseline"]:
        return None
    return (grid["margin_x"], top, slide_w - 2 * grid["margin_x"], bottom - top)


def _render_role_slide_brand(prs, brand, spec, tokens, charts_dir,
                             font_family, font_warning, brand_path,
                             ordinal=None):
    """Render a fixed-role slide in brand fidelity (REQ-004/005/007).

    The role's drawn anatomy comes from roles.py, gates through the same
    mechanical lint as composed slides (plus check_hierarchy's rank
    invariant), draws on a clean canvas painted with the slide's `Canvas:`
    colour role (paper by default, REQ-205/D-405), and stamps the slide and
    its field shapes for the revise round trip. A title-content Chart occupies
    the band below the planned text — its bbox joins the lint and is
    fulfilled after draw, the composed `Block: chart` pattern exactly.

    Returns (advisories, render_notes, chart_kind, font_family,
    font_warning); chart_kind is "native", "image", "fallback", or None.
    """
    import lint  # noqa: PLC0415
    import primitives  # noqa: PLC0415
    import roles as roles_mod  # noqa: PLC0415

    number = spec["number"]
    role = spec["role"]
    slide = prs.slides.add_slide(_blank_layout(prs))
    _strip_placeholders(slide)

    # REQ-205/D-405: the slide is painted with its `Canvas:` colour role
    # (paper unless the spec says otherwise); the planner re-resolves its
    # content colours for contrast via roles.content_roles (D-410).
    canvas = spec["meta"].get("Canvas") or "paper"
    try:
        roles_mod.content_roles(tokens, canvas)  # validates against the brand
    except primitives.ShapeError as exc:
        raise SpecError(f"slide {number}: {exc}")
    _paint_background(slide, tokens["colour_roles"][canvas])

    slide_w, slide_h = prs.slide_width, prs.slide_height
    planner = roles_mod.ROLE_PLANNERS[role]
    try:
        if role == "section":
            elements = planner(
                spec["fields"], tokens, slide_w, slide_h, ordinal=ordinal,
                canvas=canvas,
            )
        else:
            elements = planner(
                spec["fields"], tokens, slide_w, slide_h, canvas=canvas
            )
    except primitives.ShapeError as exc:
        raise SpecError(f"slide {number}: {exc}")

    # A chart on a Canvas slide needs no special handling: the chart figure
    # (native or PNG) draws its own plot area and simply sits on the painted
    # canvas, exactly as it sits on paper (REQ-205 scope note).
    chart = spec["fields"].get("Chart")
    chart_el = None
    if chart:
        region = _brand_chart_region(elements, tokens, slide_w, slide_h)
        if region is None:
            raise SpecError(
                f"slide {number}: no room for the chart below the body — "
                f"trim the body or drop it"
            )
        chart_el = {
            "kind": "chart",
            "role": "chart-figure",
            "text": f"chart: {chart['type']}",
            "left": region[0],
            "top": region[1],
            "width": region[2],
            "height": region[3],
        }
        elements.append(chart_el)

    try:
        lint.check(elements, tokens, slide_w, slide_h)
    except lint.LintError as exc:
        raise SpecError(f"slide {number}: {role} slide failed lint:\n{exc}")

    try:
        advisories = lint.review(elements, tokens, slide_w, slide_h)
    except Exception:  # noqa: BLE001 — advisory must never block a render
        advisories = []

    if chart_el is not None:
        elements = [el for el in elements if el is not chart_el]

    primitives.draw(slide, elements)
    slide.name = f"slides-role:{role}"

    # D-310: lead text that stepped down the ladder is owned up to, the
    # table body->caption precedent exactly.
    render_notes = [
        f"slide {number}: {role} text stepped down to fit the band"
        for el in elements if el.get("font_stepped")
    ]
    chart_kind = None
    extra_visual = None
    if chart:
        region = (chart_el["left"], chart_el["top"],
                  chart_el["width"], chart_el["height"])
        if chart["native"]:
            try:
                import native_charts  # noqa: PLC0415
            except ImportError:
                ok, reason = False, "native chart backend unavailable"
            else:
                ok, reason = native_charts.supported(chart)
            if ok:
                native_charts.insert(slide, chart, brand["colours"], region)
                chart_kind = "native"
            else:
                render_notes.append(
                    f"slide {number}: {reason}; drawn as an image"
                )
        if chart and chart_kind is None:
            try:
                import charts as charts_mod  # noqa: PLC0415
            except ImportError:
                charts_mod = None
            if charts_mod is None:
                extra_visual = chart_to_note(chart)
                chart_kind = "fallback"
            else:
                if font_family == "unset":
                    font_family, font_warning = register_brand_font(
                        brand, brand_path
                    )
                os.makedirs(charts_dir, exist_ok=True)
                png = os.path.join(charts_dir, f"slide{number}.png")
                try:
                    charts_mod.render_png(
                        chart, brand["colours"], font_family, png
                    )
                except charts_mod.ChartError as exc:
                    raise SpecError(f"slide {number}: {exc}")
                _place_picture(slide, png, region)
                chart_kind = "image"

    _apply_meta(slide, spec["meta"], extra_visual=extra_visual)
    return advisories, render_notes, chart_kind, font_family, font_warning


def _render_composed_slide(prs, brand, spec, tokens, charts_dir,
                            font_family, font_warning, brand_path,
                            pack_canvas=False):
    """Render a composed slide: fill an optional title, then draw token-bound
    primitives that must pass the mechanical lint before any shape is added.

    primitives.py is the only module that emits literals; lint.py is the gate
    that replaces D-002's structural guarantee. A lint or shape failure becomes
    a SpecError naming the slide, so no half-built deck is saved.

    `font_family`/`font_warning` are build_deck's own lazily-resolved brand
    font state ("unset" until a matplotlib image chart first needs it) —
    threading them in and back out lets a composed deck's image charts use
    the same registered brand font as the title-content path, resolved at
    most once per run regardless of which path hits it first.

    Returns (advisories, dropped_icons, render_notes, font_family,
    font_warning): the advisory composition findings, any icon names dropped
    for want of a rasteriser, one note per non-blocking render adjustment (a
    `Block: chart` that requested `native: true` but fell back to a matplotlib
    image, REQ-006/D-005/D-006; a table stepped down to caption size), and the
    (possibly just-resolved) font state.
    """
    import primitives  # noqa: PLC0415 — composed decks only
    import lint  # noqa: PLC0415

    number = spec["number"]
    layout = _blank_layout(prs) if pack_canvas \
        else _resolve_composed_layout(prs, brand)
    slide = prs.slides.add_slide(layout)

    grid = tokens.get("grid", {}) or {}
    slide_w, slide_h = prs.slide_width, prs.slide_height

    title = spec.get("fields", {}).get("Title")
    base_band = _full_band(grid, slide_w, slide_h)
    title_elements = []
    if pack_canvas:
        # Brand fidelity: a clean canvas painted with the slide's `Canvas:`
        # colour role (paper unless the spec says otherwise, REQ-205/D-405),
        # and the title is a DRAWN element (D-308) — a blank layout has no
        # title placeholder to fill. Only the background and the composed
        # title recolour for the canvas (D-410): BLOCK primitives keep their
        # own token colours — a paper panel reads on any canvas.
        _strip_placeholders(slide)
        import roles as roles_mod  # noqa: PLC0415
        canvas = spec.get("fields", {}).get("Canvas") or "paper"
        try:
            roles_mod.content_roles(tokens, canvas)  # validates vs the brand
        except primitives.ShapeError as exc:
            raise SpecError(f"slide {number}: {exc}")
        _paint_background(slide, tokens["colour_roles"][canvas])
        if title:
            try:
                title_elements, base_band = roles_mod.plan_composed_title(
                    title, tokens, slide_w, slide_h, canvas=canvas
                )
            except primitives.ShapeError as exc:
                raise SpecError(f"slide {number}: {exc}")
    else:
        title_ph = slide.shapes.title
        if title and title_ph is not None:
            title_ph.text = title
            _, tt, _, th = _geom(slide, title_ph)
            if None not in (tt, th):
                title_bottom = tt + th
            else:
                # Title placeholder inherits geometry we cannot read; reserve
                # a generic top band so the row never overlaps the title.
                title_bottom = grid.get("margin_top", 0) + round(slide_h * 0.12)
            if "margin_x" in grid and "margin_bottom" in grid:
                bottom = slide_h - grid["margin_bottom"]
                if bottom - title_bottom > 0:
                    base_band = (grid["margin_x"], title_bottom,
                                 slide_w - 2 * grid["margin_x"],
                                 bottom - title_bottom)
            _drop_composed_placeholders(slide, keep_title=True)
        else:
            _drop_composed_placeholders(slide, keep_title=False)

    # Plan every block, then lint the slide's FULL element list once before any
    # shape is drawn — the gate is slide-level, so overlap and the element cap
    # are enforced across all blocks together, not per block.
    plan = {
        "stat-row": (primitives.plan_stat_row, "stats"),
        "card-grid": (primitives.plan_card_grid, "cards"),
        "comparison": (primitives.plan_comparison, "sides"),
        "process": (primitives.plan_process, "steps"),
        "timeline": (primitives.plan_timeline, "nodes"),
        "tree": (primitives.plan_tree, "root"),
        "cycle": (primitives.plan_cycle, "stages"),
        "matrix": (primitives.plan_matrix, "spec"),
        "table": (primitives.plan_table, "table"),
        "icon-list": (primitives.plan_icon_list, "rows"),
        "freeform": (primitives.plan_freeform, "elements"),
    }
    blocks = spec.get("blocks", [])
    regions = _composed_regions(base_band, blocks, tokens)
    all_elements = list(title_elements)
    # A `Block: chart` plans ONE inline element (D-006, mirrors the icons
    # pattern below) purely so the lint sees its bbox — no primitives planner
    # is involved. Fulfilment (native insert, matplotlib PNG, or a note)
    # happens after primitives.draw, once the block index is known so two
    # `Block: chart` on one slide never collide on a PNG name.
    chart_plans = []  # [(element_dict, chart_dict, region, block_index), ...]
    for i, (block, region) in enumerate(zip(blocks, regions)):
        btype = block.get("type")
        if btype == "chart":
            chart = block["chart"]
            chart_el = {
                "kind": "chart",
                "role": "chart-figure",
                "text": f"chart: {chart['type']}",
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3],
            }
            all_elements.append(chart_el)
            chart_plans.append((chart_el, chart, region, i))
            continue
        entry = plan.get(btype)
        if entry is None:
            raise SpecError(
                f"slide {number}: unknown composed block type {btype!r}"
            )
        planner, key = entry
        try:
            planned = planner(block[key], tokens, slide_w, slide_h, region)
        except primitives.ShapeError as exc:
            raise SpecError(f"slide {number}: {exc}")
        if pack_canvas:
            # D-303: block elements carry a stamp the revise round trip can
            # read back (forward-compat; composed import still flattens,
            # D-304). Template fidelity stays byte-identical — no stamps.
            for el in planned:
                el.setdefault("name", f"slides-block:{btype}:{i}")
        all_elements.extend(planned)

    try:
        lint.check(all_elements, tokens, slide_w, slide_h)
    except lint.LintError as exc:
        hint = _overload_hint(blocks)
        raise SpecError(
            f"slide {number}: composed slide failed lint:\n{exc}"
            + (f"\n{hint}" if hint else "")
        )

    # Advisory composition review — non-blocking. Wrapped so a broken advisory
    # layer can never change the render's exit code (the gate above already
    # passed). Returns findings for the run summary. The block-count note
    # (formerly a hard cap) rides the same guarantee.
    try:
        advisories = lint.review(all_elements, tokens, slide_w, slide_h)
        if len(blocks) > MAX_COMPOSED_BLOCKS:
            import composition  # noqa: PLC0415 — the advisory voice lives there
            advisories = list(advisories) + [dict(composition.BLOCK_COUNT)]
    except Exception:  # noqa: BLE001 — advisory must never block a render
        advisories = []

    # Non-blocking render adjustments the summary should own up to.
    render_notes = [
        f"slide {number}: table stepped down to caption size to fit the band"
        for el in all_elements
        if el.get("kind") == "table" and el.get("font_stepped")
    ]
    # D-408: stat numbers that stepped down the ladder rather than wrap.
    if any(el.get("role") == "stat-number" and el.get("font_stepped")
           for el in all_elements):
        render_notes.append(
            f"slide {number}: stat numbers stepped down to fit their cells"
        )
    # Reflex/earn-it: a freeform hero line (display/h1) that wrapped past one
    # line — it fits its box but reads as a paragraph, not a hero.
    render_notes += [
        f"slide {number}: freeform hero text wrapped to "
        f"{el['hero_wrapped']} lines"
        for el in all_elements
        if el.get("hero_wrapped")
    ]

    # Resolve icon elements to recoloured PNGs — AFTER the lint has cleared their
    # token colour, so the planners stay pure (the charts pattern). A missing
    # rasteriser drops the icon and is reported; the deck still builds (D-011).
    dropped_icons = []
    icon_elements = [el for el in all_elements if el.get("kind") == "icon"]
    if icon_elements:
        import icons as icons_mod  # noqa: PLC0415 — composed icon slides only
        os.makedirs(charts_dir, exist_ok=True)
        for el in icon_elements:
            png = os.path.join(
                charts_dir, f"icon-{el['name']}-{el['colour'].lstrip('#')}.png"
            )
            try:
                icons_mod.render_png(el["name"], el["colour"], _icon_px(el), png)
                el["png"] = png
            except icons_mod.IconError:
                dropped_icons.append(el["name"])
        if dropped_icons:
            all_elements = [
                el for el in all_elements
                if el.get("kind") != "icon" or el.get("png")
            ]

    # Chart elements must never reach primitives.draw/_add_text (D-006's
    # seam risk): remove the planned bbox placeholders now that lint has
    # cleared them, and fulfil each afterwards.
    if chart_plans:
        chart_ids = {id(el) for el, _, _, _ in chart_plans}
        all_elements = [el for el in all_elements if id(el) not in chart_ids]

    primitives.draw(slide, all_elements)

    # Fulfil each planned chart: native insert when requested and supported,
    # else a matplotlib PNG placed into the block's region, else (matplotlib
    # absent) a VISUAL TO ADD note via the same extra_visual seam the
    # title-content chart branch uses (D-005/D-006).
    chart_notes = []
    for _el, chart, region, idx in chart_plans:
        if chart["native"]:
            try:
                import native_charts  # noqa: PLC0415
            except ImportError:
                ok, reason = False, "native chart backend unavailable"
            else:
                ok, reason = native_charts.supported(chart)
            if ok:
                native_charts.insert(slide, chart, brand["colours"], region)
                continue
            render_notes.append(
                f"slide {number}: {reason}; drawn as an image"
            )
        try:
            import charts as charts_mod  # noqa: PLC0415
        except ImportError:
            chart_notes.append(chart_to_note(chart))
            continue
        if font_family == "unset":
            font_family, font_warning = register_brand_font(brand, brand_path)
        os.makedirs(charts_dir, exist_ok=True)
        png = os.path.join(charts_dir, f"slide{number}-block{idx}.png")
        try:
            charts_mod.render_png(chart, brand["colours"], font_family, png)
        except charts_mod.ChartError as exc:
            raise SpecError(f"slide {number}: {exc}")
        _place_picture(slide, png, region)

    if pack_canvas:
        slide.name = "slides-role:composed"

    _apply_meta(slide, spec.get("meta", {}), extra_visual=chart_notes or None)
    return (advisories, dropped_icons, render_notes, font_family,
            font_warning)


def _apply_meta(slide, meta, extra_visual=None):
    """Write a slide's Visual and Notes fields into its speaker notes.

    A Visual description is recorded — not drawn — prefixed 'VISUAL TO ADD:'.
    Notes prose sits alongside it. Order: notes prose, then the visual line(s).
    `extra_visual` is one or more further VISUAL TO ADD lines (the
    matplotlib-absent chart fallback synthesised by chart_to_note), appended
    after any Visual field. A single string yields one line (the
    title-content path, which has at most one chart per slide); a list/tuple
    yields one line per entry (the composed path, which may carry several
    `Block: chart` on one slide) — never f-string the list itself, which
    would leak its Python repr into the note.
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
        if isinstance(extra_visual, (list, tuple)):
            for note in extra_visual:
                parts.append(f"VISUAL TO ADD: {note}")
        else:
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
    if ctype in ("bar", "column", "pie") or (ctype == "line"
                                             and "categories" in chart):
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
    elif ctype == "waterfall":
        cats = chart["categories"]
        values = chart["series"][0]["values"]
        deltas = ", ".join(
            f"{c} {'+' if v >= 0 else '-'}{_num_str(abs(v))}"
            for c, v in zip(cats, values)
        )
        total = sum(values)
        desc = f"Waterfall chart. {deltas}."
        label = chart.get("total_label")
        if label:
            desc += f" {label}: {_num_str(total)}."
        else:
            desc += f" (Running total: {_num_str(total)}.)"
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
