#!/usr/bin/env python3
"""extract_brand.py — read a template's brand (fonts/colours/layouts) and emit derived tokens.

Given a .pptx/.potx, print JSON describing the brand the deck already carries:
heading/body fonts and named colours read from the theme, plus the layout list,
plus a derived tokens block. teach-slides uses this to pre-fill brand.json from a
deck the user already has, so the interview becomes confirm-and-adjust instead of
blank entry. It is a superset of inspect_template.py, which prints layouts only.

The tokens block here carries only `type_scale` and `colour_roles`. The `grid`
is deliberately omitted: a meaningful grid must be measured from the layouts the
brand actually uses (its layout_map), which extract_brand does not build —
init_brand.py, which does build a layout_map, emits the grid. build-deck also
derives the grid at render time. Emitting an all-layouts grid here would risk a
polluted gutter winning as an explicit override.

Usage:

    python3 extract_brand.py <template.pptx>

Output JSON: {"template": <abspath>, "fonts": {"heading","body"},
"colours": {name: "#RRGGBB", ...}, "layouts": [...],
"tokens": {"type_scale": {...}, "colour_roles": {...}}}.
fonts/colours come from pptxlib.read_theme (the inverse of apply_theme);
layouts from list_layouts; tokens from the tokens module.

Exit status: 0 on success (JSON to stdout); non-zero with a message on stderr if
the file is missing or is not a readable presentation. Nothing is printed to
stdout on error.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptxlib import list_layouts, load_template, read_theme  # noqa: E402
import tokens  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a template's brand (fonts, colours, layouts) as JSON."
    )
    parser.add_argument("template", help="path to a .pptx or .potx file")
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
    report = {
        "template": os.path.abspath(args.template),
        "fonts": theme["fonts"],
        "colours": theme["colours"],
        "layouts": list_layouts(prs),
        "tokens": {
            "type_scale": (tokens.type_scale_from_master(prs)
                           or tokens.default_type_scale()),
            "colour_roles": tokens.resolve_colour_roles(theme["colours"]),
        },
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
