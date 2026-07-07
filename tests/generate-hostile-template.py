#!/usr/bin/env python3
"""Generate tests/fixtures/hostile-template.pptx — the WORST-CASE test fixture.

This fixture exists to prove brand fidelity is immune to template quality
(identity-not-layout REQ-012). It is the sample fixture's evil twin: same
layout names and role mapping, but every design fault the drawn-role renderer
was built to escape is baked in deliberately:

* **No hierarchy.** The master's `p:txStyles` titleStyle AND bodyStyle
  level-1 `defRPr sz` are both set to 2800 (28pt) — body == title, so a
  placeholder-filled slide cannot express rank by size. Template fidelity
  renders it anyway and fires the non-blocking "hierarchy will not read"
  tripwire; brand fidelity never opens the file.
* **Decoration.** A garish full-width accent rectangle (solid 1F4E79) sits
  across the top of layouts 0-3 — the design debt a faithful placeholder
  fill reproduces on every slide.
* **Cramped placeholders.** Every content placeholder on layouts 0-5 is
  shrunk to ~60% of its width and height, so filled text is squeezed into
  boxes far smaller than the slide could offer.

Layouts 0, 1, 2, 3, 5 are renamed to the same semantic roles the sample
fixture uses (title, title-content, section, two-column, statement; quote
shares section), so the two fixtures are interchangeable in a brand.json
layout_map. Run from the repo root:

    python3 tests/generate-hostile-template.py

Re-running always produces the same layout structure (deterministic), though
the .pptx is a zip and is not guaranteed byte-identical across runs.
"""
import os

from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls

# Same mapping as generate-fixture-template.py: default-template layout index
# to the role name render.py resolves.
ROLE_NAMES = {
    0: "title",
    1: "title-content",
    2: "section",
    3: "two-column",
    5: "statement",
}

# The hostile master type sizes: body == title (28pt each, in hundredths).
HOSTILE_SZ = "2800"
# The decorative bar's garish solid fill and height (EMU).
ACCENT_HEX = "1F4E79"
ACCENT_BAR_H = 457200  # 0.5 inch across the full slide width
# Content placeholders shrink to this fraction of their width/height.
CRAMP = 0.6
# Layouts that carry the decorative accent bar / the cramped placeholders.
DECORATED_LAYOUTS = range(0, 4)
CRAMPED_LAYOUTS = range(0, 6)

_P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Placeholder types that hold slide content (mirrors
# pptxlib.CONTENT_PLACEHOLDER_TYPES without importing the scripts dir).
from pptx.enum.shapes import PP_PLACEHOLDER  # noqa: E402

CONTENT_PLACEHOLDER_TYPES = frozenset(
    {
        PP_PLACEHOLDER.TITLE,
        PP_PLACEHOLDER.CENTER_TITLE,
        PP_PLACEHOLDER.SUBTITLE,
        PP_PLACEHOLDER.BODY,
        PP_PLACEHOLDER.OBJECT,
    }
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "tests", "fixtures", "hostile-template.pptx")


def _flatten_master_type_scale(prs):
    """Set the master's titleStyle and bodyStyle level-1 sizes to the SAME
    value — the hostile condition render.py's template-fidelity tripwire
    (body >= title) exists to catch."""
    master = prs.slide_masters[0]
    tx = master.element.find(f"{{{_P_NS}}}txStyles")
    for tag in ("titleStyle", "bodyStyle"):
        style = tx.find(f"{{{_P_NS}}}{tag}")
        lvl1 = style.find(f"{{{_A_NS}}}lvl1pPr")
        def_rpr = lvl1.find(f"{{{_A_NS}}}defRPr")
        if def_rpr is None:
            def_rpr = lvl1.makeelement(f"{{{_A_NS}}}defRPr", {})
            lvl1.append(def_rpr)
        def_rpr.set("sz", HOSTILE_SZ)


def _add_accent_bar(layout, slide_w, shape_id):
    """Append a full-width solid-fill rectangle across the top of a layout.

    python-pptx 1.0.2's LayoutShapes has no add_shape, so the <p:sp> element
    is built directly and appended to the layout's shape tree.
    """
    sp_xml = (
        f"<p:sp {nsdecls('p', 'a')}>"
        f"<p:nvSpPr>"
        f'<p:cNvPr id="{shape_id}" name="hostile-accent-bar"/>'
        f"<p:cNvSpPr/><p:nvPr/>"
        f"</p:nvSpPr>"
        f"<p:spPr>"
        f'<a:xfrm><a:off x="0" y="0"/>'
        f'<a:ext cx="{slide_w}" cy="{ACCENT_BAR_H}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{ACCENT_HEX}"/></a:solidFill>'
        f"</p:spPr>"
        f"<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>"
        f"</p:sp>"
    )
    layout.shapes._spTree.append(parse_xml(sp_xml))


def _cramp_placeholders(layout):
    """Shrink every content placeholder to ~60% of its width and height."""
    for ph in layout.placeholders:
        if ph.placeholder_format.type not in CONTENT_PLACEHOLDER_TYPES:
            continue
        if ph.width is not None:
            ph.width = int(ph.width * CRAMP)
        if ph.height is not None:
            ph.height = int(ph.height * CRAMP)


def main():
    prs = Presentation()  # bundled default template: master + named layouts

    # A fresh default Presentation() has no slides; guard anyway so the
    # fixture is always layouts-only even if python-pptx changes.
    xml_slides = prs.slides._sldIdLst
    for sld in list(xml_slides):
        xml_slides.remove(sld)

    _flatten_master_type_scale(prs)

    for i in DECORATED_LAYOUTS:
        _add_accent_bar(prs.slide_layouts[i], prs.slide_width, 900 + i)
    for i in CRAMPED_LAYOUTS:
        _cramp_placeholders(prs.slide_layouts[i])

    for idx, role in ROLE_NAMES.items():
        prs.slide_layouts[idx].name = role

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)

    reopened = Presentation(OUT)
    master = reopened.slide_masters[0]
    tx = master.element.find(f"{{{_P_NS}}}txStyles")
    sizes = {}
    for tag in ("titleStyle", "bodyStyle"):
        lvl1 = tx.find(f"{{{_P_NS}}}{tag}").find(f"{{{_A_NS}}}lvl1pPr")
        sizes[tag] = lvl1.find(f"{{{_A_NS}}}defRPr").get("sz")
    print(f"wrote {OUT}")
    print(f"master sizes: {sizes} (hostile: body == title)")
    print(f"{len(reopened.slide_layouts)} layouts:")
    for i, layout in enumerate(reopened.slide_layouts):
        phs = ", ".join(
            f"idx{ph.placeholder_format.idx}:{ph.placeholder_format.type}"
            for ph in layout.placeholders
        )
        bars = sum(
            1 for s in layout.shapes
            if not s.is_placeholder and s.name == "hostile-accent-bar"
        )
        print(f"  [{i}] {layout.name!r} — {phs or 'no placeholders'}"
              f"{' + accent bar' if bars else ''}")


if __name__ == "__main__":
    main()
