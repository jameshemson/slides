#!/usr/bin/env python3
"""init_brand.py — build a complete brand.json from a template or deck.

One-step brand setup: given a .pptx/.potx, print a ready-to-use brand.json so a
deck comes out on-brand without the full teach-slides interview. Fonts and
colours always come from pptxlib.read_theme. Two emission shapes, selected by
--fidelity; both are fidelity-explicit, so a profile behaves the same before
and after the code default (tokens.DEFAULT_FIDELITY) flips:

- "brand" (the default onboarding — identity-not-layout REQ-009): the template
  is an identity source only, read once here and kept in the "template" key as
  the pointer to it. Emits {fidelity, template, fonts, colours, tokens}, where
  tokens carries the pack's own type scale and grid plus the colour-role
  assignments (tokens.resolve_tokens in brand fidelity). No layout_map is
  emitted and the layout heuristic never runs, so a weird or hostile template
  cannot fail brand init: if it opens and has a theme, it onboards.
- "template" (legacy placeholder-fill): the pre-v0.17 shape plus an explicit
  "fidelity": "template" key in front. Adds the heuristic layout_map that maps
  each semantic role to one of the template's real layouts, with a "composed"
  entry for single-title canvas slides (aliased to statement, then title, then
  index 0), and tokens derived from the template (master type scale,
  mapped-layout grid).

teach-slides remains the authoritative, richer brand capture.

Usage:

    python3 init_brand.py <template.pptx> [--template-ref NAME]
        [--fidelity {brand,template}]

The `template` field defaults to the input's absolute path; --template-ref sets
it instead (skills pass "template.pptx" after copying the file into .slides/).

Exit status: 0 on success (JSON to stdout); non-zero with a message on stderr
if the file is missing or is not a readable presentation — or, in template
fidelity only, if no layout can host one of the six roles. Nothing is printed
to stdout on error.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptxlib import (  # noqa: E402
    CONTENT_PLACEHOLDER_TYPES,
    list_layouts,
    load_template,
    read_theme,
)
from render import OPTIONAL_FIELDS, ROLE_FIELDS  # noqa: E402
import tokens  # noqa: E402

# A role with no dedicated layout falls back to a sibling: a quote reads well on
# a section layout. Every other role aliases only to itself.
ROLE_ALIASES = {"quote": ["quote", "section"]}


def _norm(name):
    """Lowercase, alphanumeric-only form for matching a layout name to a role."""
    return "".join(c for c in (name or "").lower() if c.isalnum())


def _content_count(layout, content_names):
    """Count a layout dict's content placeholders (from list_layouts)."""
    return sum(1 for p in layout["placeholders"] if p["type"] in content_names)


def suggest_layout_map(layouts, role_fields, optional_fields, content_names):
    """Map each semantic role to a layout index. Raises ValueError if a role
    cannot be hosted.

    Per role: required_min = the non-optional field count (the minimum render
    needs to avoid overflow); full = all fields. A layout is a candidate when it
    has content_count >= required_min (and > 0). Among candidates, prefer a
    name/alias match; else the smallest layout that also fits `full` (so optional
    fields fit too); else the largest candidate (closest fit). Ties break to the
    lowest index. Uses only layout names and placeholder counts — no literals.
    """
    mapping = {}
    for role, fields in role_fields.items():
        full = len(fields)
        required_min = full - len(optional_fields.get(role, set()))
        scored = [(layout, _content_count(layout, content_names))
                  for layout in layouts]
        candidates = [(c, n) for c, n in scored if n >= required_min and n > 0]
        if not candidates:
            raise ValueError(
                f"could not map role {role!r} to a layout with >= "
                f"{required_min} content placeholder(s)"
            )
        aliases = {_norm(a) for a in ROLE_ALIASES.get(role, [role])}
        named = [(c, n) for c, n in candidates if _norm(c["name"]) in aliases]
        if named:
            chosen = min(named, key=lambda cn: cn[0]["index"])[0]
        else:
            fits_full = [(c, n) for c, n in candidates if n >= full]
            if fits_full:
                chosen = min(fits_full, key=lambda cn: (cn[1], cn[0]["index"]))[0]
            else:
                chosen = max(candidates, key=lambda cn: (cn[1], -cn[0]["index"]))[0]
        mapping[role] = chosen["index"]
    return mapping


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a complete brand.json from a template or deck."
    )
    parser.add_argument("template", help="path to a .pptx or .potx file")
    parser.add_argument(
        "--template-ref", default=None,
        help="value for the brand.json 'template' field "
             "(default: the input's absolute path)",
    )
    parser.add_argument(
        "--fidelity", choices=tokens.FIDELITY_MODES, default="brand",
        help="brand.json shape: 'brand' (pack-designed rendering; the "
             "template is an identity source only — the default) or "
             "'template' (legacy placeholder-fill with a heuristic "
             "layout_map)",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.template):
        print(f"error: template not found: {args.template}", file=sys.stderr)
        return 1
    try:
        prs = load_template(args.template)
    except Exception as exc:  # noqa: BLE001 — report any open failure cleanly
        print(f"error: could not open template: {exc}", file=sys.stderr)
        return 1

    theme = read_theme(prs)
    template_ref = args.template_ref or os.path.abspath(args.template)

    if args.fidelity == "brand":
        # REQ-009: brand fidelity never runs the layout heuristic — a template
        # that opens and has a theme always onboards. resolve_tokens sees the
        # explicit fidelity and returns the pack scale/grid + colour roles.
        report = {
            "fidelity": "brand",
            "template": template_ref,
            "fonts": theme["fonts"],
            "colours": theme["colours"],
        }
        report["tokens"] = tokens.resolve_tokens(report, prs)
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    content_names = {t.name for t in CONTENT_PLACEHOLDER_TYPES}
    try:
        layout_map = suggest_layout_map(
            list_layouts(prs), ROLE_FIELDS, OPTIONAL_FIELDS, content_names
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    report = {
        "fidelity": "template",
        "template": template_ref,
        "fonts": theme["fonts"],
        "colours": theme["colours"],
        "layout_map": layout_map,
    }
    # D-107: composed slides draw on the statement layout (single-title canvas),
    # falling back to title, then index 0.
    report["layout_map"]["composed"] = report["layout_map"].get(
        "statement", report["layout_map"].get("title", 0)
    )
    report["tokens"] = tokens.resolve_tokens(report, prs)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
