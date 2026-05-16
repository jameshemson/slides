#!/usr/bin/env python3
"""inspect_template.py — describe a .pptx/.potx template as JSON.

Given a presentation file, print every slide layout to stdout: its index,
name, and placeholders (each placeholder's idx and type). This is the input a
person — or `teach-slides` — uses to build brand.json's layout_map: it shows
which real layout sits at which index and what placeholders it offers.

Usage:

    python3 inspect_template.py <template.pptx>

Exit status: 0 on success, non-zero (with a message on stderr) if the file is
missing or is not a readable presentation.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pptxlib import load_template, list_layouts  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a .pptx/.potx template's layouts and placeholders as JSON."
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

    report = {
        "template": os.path.abspath(args.template),
        "layouts": list_layouts(prs),
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
