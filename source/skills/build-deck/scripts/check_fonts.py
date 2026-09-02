#!/usr/bin/env python3
"""Report whether the brand's font families are installed on this machine.

    python3 check_fonts.py --brand .slides/brand.json [--font NAME ...]

The deck file always names the brand font (the lint enforces it). This answers
a different question: will the render-back preview on THIS machine draw that
font, or substitute one? Each family gets one of three answers: installed,
missing (LibreOffice substitutes; treat text-fit as approximate), or unknown
(no checker could run here). Three probes — matplotlib's font manager,
fontconfig's fc-list, a scan of the platform font folders — are aggregated:
installed if any probe finds the family, missing only when every probe that
could run missed it, unknown when none could run. A matplotlib miss never
hides a font the system folders can see; LibreOffice reads the system's.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

MISSING_NOTE = "LibreOffice substitutes it in the render-back; treat text-fit as approximate"
UNKNOWN_NOTE = "no font checker on this machine (install matplotlib or fontconfig)"


def matplotlib_probe(name):
    """installed / missing via matplotlib's font manager; None when matplotlib is absent."""
    try:
        from matplotlib import font_manager
    except Exception:
        return None
    try:
        font_manager.findfont(
            font_manager.FontProperties(family=name), fallback_to_default=False
        )
        return "installed"
    except Exception:
        return "missing"


def fc_list_probe(name):
    """installed / missing via fontconfig's fc-list; None when fc-list is absent."""
    exe = shutil.which("fc-list")
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, ":", "family"], capture_output=True, text=True, timeout=20
        ).stdout
    except Exception:
        return None
    families = {
        part.strip().lower() for line in out.splitlines() for part in line.split(",")
    }
    return "installed" if name.strip().lower() in families else "missing"


def _font_dirs():
    if sys.platform == "darwin":
        return [
            "/Library/Fonts",
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
            os.path.expanduser("~/Library/Fonts"),
        ]
    if sys.platform.startswith("win"):
        dirs = []
        windir = os.environ.get("WINDIR")
        if windir:
            dirs.append(os.path.join(windir, "Fonts"))
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
        return dirs
    return []


def font_dir_probe(name):
    """installed / missing by scanning the platform font folders; None off macOS/Windows."""
    dirs = [d for d in _font_dirs() if os.path.isdir(d)]
    if not dirs:
        return None
    key = name.replace(" ", "").lower()
    for directory in dirs:
        try:
            entries = os.listdir(directory)
        except OSError:
            continue
        for entry in entries:
            stem = os.path.splitext(entry)[0].replace(" ", "").lower()
            if stem.startswith(key):
                return "installed"
    return "missing"


DEFAULT_PROBES = [matplotlib_probe, fc_list_probe, font_dir_probe]


def font_status(name, probes=None):
    """'installed' if any runnable probe finds the family, 'missing' only when
    every runnable probe misses, 'unknown' when no probe could run.

    A matplotlib miss never hides a font the system folders or fontconfig can
    see — the inventories differ, and LibreOffice reads the system's."""
    answered = False
    for probe in (DEFAULT_PROBES if probes is None else probes):
        answer = probe(name)
        if answer == "installed":
            return "installed"
        if answer == "missing":
            answered = True
    return "missing" if answered else "unknown"


def describe(name, status):
    if status == "installed":
        return f"font {name}: installed"
    if status == "missing":
        return f"font {name}: missing — {MISSING_NOTE}"
    return f"font {name}: unknown — {UNKNOWN_NOTE}"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report whether the brand's font families are installed here."
    )
    parser.add_argument("--brand", default=None, help="brand.json (fonts.heading / fonts.body)")
    parser.add_argument("--font", action="append", default=[], help="a family name (repeatable)")
    args = parser.parse_args(argv)

    names = []
    if args.brand:
        try:
            with open(args.brand, encoding="utf-8") as fh:
                brand = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        fonts = brand.get("fonts") or {}
        names.extend(v for v in (fonts.get("heading"), fonts.get("body")) if v)
    names.extend(args.font)

    ordered = []
    for name in names:
        if name not in ordered:
            ordered.append(name)
    if not ordered:
        print("error: no font named; pass --brand brand.json or --font NAME", file=sys.stderr)
        return 2
    for name in ordered:
        print(describe(name, font_status(name)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
