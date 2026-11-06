#!/usr/bin/env python3
"""brand.py: capture a brand's fonts and colours, and hold a finished .pptx to them.

Fonts and colours only. Layout, sizes, spacing and contrast are not checked here,
on purpose. The check reads through the deck's theme, so a deck built on theme
colours and inherited fonts is judged by what they resolve to. A tint of a brand
colour counts as that colour. Pictures are not looked inside.

Checked on each slide: its shapes and text, its charts, its layout's shapes, and
whichever background is in force.

Usage:

    python3 brand.py capture <template.pptx or .potx>      prints a brand.json
    python3 brand.py check <deck.pptx> --brand <brand.json> [--json]

brand.json needs "fonts" and "colours", each mapping any name to a value, so an
extra font or shade the brand allows can simply be added:

    {"fonts": {"heading": "Georgia", "body": "Georgia", "mono": "Courier New"},
     "colours": {"ink": "#1B1B1B", "paper": "#FAFAFA", "accent": "#C8102E"}}

Exit status for check: 0 on brand, 1 off-brand items found. For either command, 2
means the file could not be read.
"""
import argparse
import json
import re
import sys
import zipfile

from lxml import etree
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
HEX = re.compile(r"^#?([0-9A-Fa-f]{6})$")
# A shape's p:style holds fallbacks that its own properties usually override.
NOT_STYLE = "[not(ancestor::p:style)]"
COLOURS = (
    ".//*[self::a:srgbClr or self::a:sysClr or self::a:schemeClr]" + NOT_STYLE
)
FONTS = ".//a:latin" + NOT_STYLE
TITLE_TYPES = ("title", "ctrTitle")
# Every slot of a theme's colour scheme, under the names brand.json uses.
SLOT_NAMES = {
    "dk1": "ink", "lt1": "paper", "dk2": "ink2", "lt2": "paper2",
    "accent1": "accent", "accent2": "accent2", "accent3": "accent3",
    "accent4": "accent4", "accent5": "accent5", "accent6": "accent6",
    "hlink": "link", "folHlink": "link2",
}


def _parse(blob):
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.fromstring(blob, parser)


def read_brand(path):
    """Return ({lowercased font: font}, {upper-case hex}) from a brand.json."""
    with open(path, encoding="utf-8") as handle:
        brand = json.load(handle)
    fonts = {
        value.strip().lower(): value.strip()
        for value in (brand.get("fonts") or {}).values()
        if isinstance(value, str) and value.strip()
    }
    colours = set()
    for value in (brand.get("colours") or {}).values():
        match = HEX.match(value) if isinstance(value, str) else None
        if match:
            colours.add(match.group(1).upper())
    if not fonts or not colours:
        raise ValueError("brand.json needs both fonts and colours")
    return fonts, colours


def _theme_values(root):
    """Return the colour slots, major font and minor font of a parsed theme."""
    colours = {}
    for slot in root.find(".//a:clrScheme", NS):
        child = slot[0]
        value = child.get("val") if child.tag.endswith("srgbClr") else child.get("lastClr")
        colours[etree.QName(slot).localname] = (value or "").upper()
    return {
        "colours": colours,
        "major": root.find(".//a:majorFont/a:latin", NS).get("typeface"),
        "minor": root.find(".//a:minorFont/a:latin", NS).get("typeface"),
    }


def read_theme(master):
    """Return the theme values and clrMap of a slide master."""
    theme = _theme_values(_parse(master.part.part_related_by(RT.THEME).blob))
    theme["clr_map"] = dict(_parse(master.part.blob).find("p:clrMap", NS).attrib)
    return theme


def capture_brand(path):
    """Return a brand.json dict from the theme of a .pptx or .potx."""
    with zipfile.ZipFile(path) as package:
        names = sorted(n for n in package.namelist() if re.fullmatch(r"ppt/theme/theme\d+\.xml", n))
        if not names:
            raise ValueError("no theme found")
        theme = _theme_values(_parse(package.read(names[0])))
    return {
        "fonts": {"heading": theme["major"], "body": theme["minor"]},
        "colours": {
            SLOT_NAMES[slot]: f"#{value}"
            for slot, value in theme["colours"].items()
            if slot in SLOT_NAMES and value
        },
    }


def _colour(element, theme):
    """Resolve a colour element to upper-case hex, or None if it has no fixed value."""
    tag = etree.QName(element).localname
    if tag == "srgbClr":
        return (element.get("val") or "").upper() or None
    if tag == "sysClr":
        return (element.get("lastClr") or "").upper() or None
    slot = element.get("val")
    if slot == "phClr":
        return None
    return theme["colours"].get(theme["clr_map"].get(slot, slot))


def _font(typeface, theme):
    """Resolve a typeface, following +mj-lt and +mn-lt to the theme's fonts."""
    if typeface == "+mj-lt":
        return theme["major"]
    if typeface == "+mn-lt":
        return theme["minor"]
    return None if not typeface or typeface.startswith("+") else typeface


def _scan(root, index, theme, brand_fonts, brand_colours, fonts, colours):
    """Record every off-brand colour and named font under an element."""
    for element in root.xpath(COLOURS, namespaces=NS):
        value = _colour(element, theme)
        if value and value not in brand_colours:
            colours.setdefault(value, set()).add(index)
    for element in root.xpath(FONTS, namespaces=NS):
        name = _font(element.get("typeface"), theme)
        if name and name.lower() not in brand_fonts:
            fonts.setdefault(name, set()).add(index)


def _inherited_fonts(sptree, layout_sets_font, theme):
    """Yield the theme font behind each run of text that names no font itself."""
    for run in sptree.xpath(".//*[self::a:r or self::a:fld]", namespaces=NS):
        if not (run.findtext("a:t", default="", namespaces=NS) or "").strip():
            continue
        if run.find("a:rPr/a:latin", NS) is not None:
            continue
        if run.xpath("../a:pPr/a:defRPr/a:latin", namespaces=NS):
            continue
        if run.xpath("ancestor::*[self::p:txBody or self::a:txBody]/a:lstStyle//a:latin",
                     namespaces=NS):
            continue
        placeholder = run.xpath("ancestor::p:sp/p:nvSpPr/p:nvPr/p:ph", namespaces=NS)
        if placeholder and layout_sets_font:
            continue
        is_title = placeholder and placeholder[0].get("type") in TITLE_TYPES
        yield theme["major"] if is_title else theme["minor"]


def check_deck(deck_path, brand_path):
    """Return {"fonts": {name: [slides]}, "colours": {hex: [slides]}, "notes": [...]}."""
    brand_fonts, brand_colours = read_brand(brand_path)
    prs = Presentation(deck_path)
    fonts, colours, notes = {}, {}, []

    for index, slide in enumerate(prs.slides, 1):
        layout = slide.slide_layout
        master = layout.slide_master
        theme = read_theme(master)
        slide_root = _parse(slide.part.blob)
        layout_root = _parse(layout.part.blob)
        master_root = _parse(master.part.blob)
        scan = (index, theme, brand_fonts, brand_colours, fonts, colours)

        sptree = slide_root.find("p:cSld/p:spTree", NS)
        _scan(sptree, *scan)
        _scan(layout_root.find("p:cSld/p:spTree", NS), *scan)
        for root in (slide_root, layout_root, master_root):
            background = root.find("p:cSld/p:bg", NS)
            if background is not None:
                _scan(background, *scan)
                break
        for rel in slide.part.rels.values():
            if rel.reltype == RT.CHART:
                _scan(_parse(rel.target_part.blob), *scan)

        layout_sets_font = bool(
            layout_root.xpath(".//p:sp[p:nvSpPr/p:nvPr/p:ph]//a:latin", namespaces=NS)
        )
        for name in _inherited_fonts(sptree, layout_sets_font, theme):
            if name and name.lower() not in brand_fonts:
                fonts.setdefault(name, set()).add(index)

        off_theme = [
            name for name in (theme["major"], theme["minor"])
            if name and name.lower() not in brand_fonts
        ]
        off_theme += [
            f"#{theme['colours'][slot]}" for slot in ("dk1", "lt1")
            if theme["colours"].get(slot) not in brand_colours
        ]
        if off_theme and not notes:
            listed = ", ".join(dict.fromkeys(off_theme))
            notes.append(
                f"The deck's theme is not on brand ({listed}), so anything added "
                "later in PowerPoint will not match."
            )

    return {
        "fonts": {name: sorted(found) for name, found in sorted(fonts.items())},
        "colours": {f"#{hex_}": sorted(found) for hex_, found in sorted(colours.items())},
        "notes": notes,
    }


def _report(result):
    lines = []
    for kind, key in (("font", "fonts"), ("colour", "colours")):
        for name, slides in result[key].items():
            listed = ", ".join(str(n) for n in slides)
            lines.append(f"{kind} {name}: slide{'s' if len(slides) > 1 else ''} {listed}")
    if lines:
        lines.insert(0, f"off brand: {len(lines)} item(s)")
    else:
        lines.append("on brand: every font and colour matches")
    lines += [f"note: {note}" for note in result["notes"]]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Capture a brand, or check a .pptx against one.")
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture", help="print a brand.json from a template's theme")
    capture.add_argument("template", help="a .pptx or .potx")
    check = commands.add_parser("check", help="check a finished .pptx's fonts and colours")
    check.add_argument("deck", help="the finished .pptx")
    check.add_argument("--brand", required=True, help="path to brand.json")
    check.add_argument("--json", action="store_true", dest="as_json", help="print JSON")
    args = parser.parse_args(argv)

    if args.command == "capture":
        try:
            print(json.dumps(capture_brand(args.template), indent=2))
        except Exception as exc:  # noqa: BLE001: any unreadable file is reported the same way
            print(f"error: could not read {args.template}: {exc}", file=sys.stderr)
            return 2
        return 0

    try:
        result = check_deck(args.deck, args.brand)
    except Exception as exc:  # noqa: BLE001: any unreadable deck or brand is reported the same way
        print(f"error: could not check {args.deck}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.as_json else _report(result))
    return 1 if result["fonts"] or result["colours"] else 0


if __name__ == "__main__":
    sys.exit(main())
