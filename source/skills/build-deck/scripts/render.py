#!/usr/bin/env python3
"""render.py — turn a deck spec + brand profile into a real .pptx.

`build-deck` runs this. It reads a deck spec (the content and structure of a
deck — see presentation-craft/reference/deck-spec.md) and a brand.json (which
names the user's template and the role-to-layout map), then fills the
template's existing placeholders to produce a .pptx.

Decision D-002 is absolute: this script sets no fonts, colours, or
coordinates. The template carries all visual design; render.py only fills the
placeholders the chosen layout already defines and never adds a shape — so a
spec cannot smuggle a tacked-on strapline onto a slide.

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
# Fields that are optional for their role (absent is fine).
OPTIONAL_FIELDS = {
    "title": {"Subtitle"},
    "quote": {"Attribution"},
}
# Block fields may carry a bullet list or short paragraphs across many lines.
BLOCK_FIELDS = {"Body", "Left", "Right"}
# Fields any slide may carry, handled outside the role's placeholder fill.
META_FIELDS = {"Visual", "Notes"}
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
    args = parser.parse_args(argv)

    try:
        brand = load_brand(args.brand)
        slides = parse_spec(args.spec)
        summary = build_deck(brand, slides, args.out)
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
    """Parse one slide's lines into role, fields, and meta. Raises SpecError."""
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
            if label in BLOCK_FIELDS:
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

        # A non-label line belongs to the open block field, if any.
        if current_field in BLOCK_FIELDS:
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
    # Every field name any role declares, plus the two meta fields.
    known = set(META_FIELDS)
    for role_fields in ROLE_FIELDS.values():
        known.update(role_fields)
    # Match case-insensitively, then normalise to the canonical capitalisation.
    canonical = {name.lower(): name for name in known}
    if label.lower() not in canonical:
        return None, None
    value = line.split(":", 1)[1].strip()
    return canonical[label.lower()], value


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


def _validate_slide_fields(number, role, fields):
    """Check a slide carries exactly the fields its role allows. Raises SpecError."""
    allowed = set(ROLE_FIELDS[role]) | META_FIELDS
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


# --- rendering ---------------------------------------------------------------


def build_deck(brand, slides, out_path):
    """Render parsed slides into a .pptx at out_path. Returns a summary string."""
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

    layout_map = brand["layout_map"]
    visual_slides = []

    for spec in slides:
        number = spec["number"]
        role = spec["role"]

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

        _drop_unused(unused)
        _apply_meta(slide, spec["meta"])
        if "Visual" in spec["meta"]:
            visual_slides.append(number)

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    prs.save(out_path)

    visual_note = (
        f"; {len(visual_slides)} carry a VISUAL TO ADD note "
        f"(slides {', '.join(map(str, visual_slides))})"
        if visual_slides
        else "; no visuals flagged"
    )
    return f"rendered {len(slides)} slide(s) to {out_path}{visual_note}"


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


def _apply_meta(slide, meta):
    """Write a slide's Visual and Notes fields into its speaker notes.

    A Visual description is recorded — not drawn — prefixed 'VISUAL TO ADD:'.
    Notes prose sits alongside it. Order: notes prose, then the visual line.
    """
    if not meta:
        return
    parts = []
    notes = meta.get("Notes")
    if notes:
        parts.append(_meta_text(notes))
    visual = meta.get("Visual")
    if visual:
        parts.append(f"VISUAL TO ADD: {_meta_text(visual)}")
    if not parts:
        return
    notes_tf = slide.notes_slide.notes_text_frame
    notes_tf.text = "\n\n".join(parts)


def _meta_text(value):
    """Flatten a meta field value (string or list) to a single string."""
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return str(value)


if __name__ == "__main__":
    sys.exit(main())
