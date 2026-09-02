"""
Mechanical lint gate for composed slides.

This module is the load-bearing mechanical gate that replaced the structural
guarantee previously provided by limiting slides to non-primitive elements.
Now that specs can compose primitives (drawn shapes), nothing prevents
off-brand colours, sizes, or layout violations from reaching a rendered slide
except this deterministic checker.

It is intentionally brand-agnostic: all thresholds come from the caller-
supplied tokens dict, not from any hard-coded brand values. The gate is
purely mechanical — if every violation message list is empty, the slide is
cleared; otherwise a LintError is raised with a human-readable summary.
"""

# The slide-level backstop against a wall of shapes. Sized to admit the richest
# single well-formed primitive (a 5-step process with detail lines ~ 24
# elements); the advisory count rules (3-5 items) are the real quality guard.
ELEMENT_CAP = 24

# Ghost display type on section slides draws at display × GHOST_MULTIPLE,
# deliberately underlapping: check_sizes admits exactly that one size for an
# element marked `ghost`, and check_no_overlap skips any pair containing one.
GHOST_MULTIPLE = 3.0

# WCAG 2.2 AA contrast floors. Text at or above LARGE_TEXT_PT counts as
# "large" (WCAG's 18pt / 14pt-bold threshold) and needs 3:1; anything
# smaller needs 4.5:1. check_contrast judges a run against the ground it
# actually sits on, not against the paper token.
LARGE_TEXT_PT = 18.0
CONTRAST_LARGE = 3.0
CONTRAST_SMALL = 4.5


class LintError(Exception):
    """A composed slide that fails the mechanical lint. render.py turns this into a SpecError."""


def _norm(h: str) -> str:
    """Normalise a hex colour string to '#RRGGBB' uppercase form."""
    return "#" + h.lstrip("#").upper()


# --- WCAG 2.2 contrast helpers ------------------------------------------
# These moved here from composition.py so the mechanical gate owns them:
# check_contrast is a hard rule, and composition.py (advisory) re-exports
# them by importing from this module. lint.py must never import composition
# at module level, so the direction of the dependency is one-way.

def _hex_to_rgb(h: str):
    """Return (r, g, b) tuple in 0-255 range from a hex colour string."""
    h = h.strip().lstrip("#").upper()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rel_luminance(h: str) -> float:
    """
    Relative luminance per WCAG 2.2.
    Linearises each sRGB channel:
        lin = c/12.92          if c <= 0.03928
        lin = ((c+0.055)/1.055)**2.4  otherwise
    L = 0.2126*R + 0.7152*G + 0.0722*B
    """
    r, g, b = _hex_to_rgb(h)
    channels = []
    for raw in (r, g, b):
        c = raw / 255.0
        if c <= 0.03928:
            channels.append(c / 12.92)
        else:
            channels.append(((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(h1: str, h2: str) -> float:
    """
    WCAG contrast ratio between two hex colours.
    ((L_light + 0.05) / (L_dark + 0.05))
    """
    l1 = _rel_luminance(h1)
    l2 = _rel_luminance(h2)
    light, dark = (l1, l2) if l1 >= l2 else (l2, l1)
    return (light + 0.05) / (dark + 0.05)


# Every key on an element that carries a colour. Text elements colour their
# `colour`; box/connector elements colour their `fill` and (optionally) `stroke`.
# Whichever are present must all be token colours — the gate is the same.
_COLOUR_KEYS = ("colour", "fill", "stroke")


def check_colours(elements: list, tokens: dict) -> list:
    """
    Return violation messages for elements whose colour is not in the token palette.

    Checks every colour-bearing key present on the element (`colour` for text,
    `fill`/`stroke` for boxes) — a card panel's fill is held to the token
    palette exactly like a stat number's text colour. A `kind == "table"`
    element is a single native GraphicFrame whose per-cell colours travel as the
    `fills` and `text_colours` vectors; every entry of each is held to the same
    palette (its hairline colour rides the scalar `stroke` key, already checked).

    Tag: [colour]
    """
    allowed = {_norm(v) for v in tokens["colour_roles"].values()}
    messages = []
    for el in elements:
        for key in _COLOUR_KEYS:
            value = el.get(key)
            if value is None:
                continue
            if _norm(value) not in allowed:
                messages.append(
                    f"[colour] element {_label(el)} "
                    f"has {key}={value!r} which is not in colour_roles"
                )
        if el.get("kind") == "table":
            for key in ("fills", "text_colours"):
                for i, value in enumerate(el.get(key) or []):
                    if _norm(value) not in allowed:
                        messages.append(
                            f"[colour] element {_label(el)} "
                            f"has {key}[{i}]={value!r} which is not in colour_roles"
                        )
    return messages


def check_sizes(elements: list, tokens: dict) -> list:
    """
    Return violation messages for elements whose font_pt is not in the type scale.

    Box and connector elements carry no `font_pt` (they hold no text) and are
    skipped — only text is held to the type scale. A `kind == "table"` element
    carries its per-cell sizes in the `font_pts` vector instead of a scalar
    `font_pt`; every entry is held to the type scale the same way. An element
    marked `ghost` (the section slide's numeral) is allowed exactly
    display × GHOST_MULTIPLE instead of the scale set — one sanctioned size,
    not a free pass.

    Tag: [size]
    """
    allowed = set(tokens["type_scale"].values())
    display_pt = tokens["type_scale"].get("display")
    ghost_pt = None if display_pt is None else display_pt * GHOST_MULTIPLE
    messages = []
    for el in elements:
        font_pt = el.get("font_pt")
        if font_pt is not None:
            if el.get("ghost"):
                ok = ghost_pt is not None and font_pt == ghost_pt
            else:
                ok = font_pt in allowed
            if not ok:
                messages.append(
                    f"[size] element role={el['role']!r} text={el.get('text')!r} "
                    f"has font_pt={font_pt} which is not in type_scale"
                )
        if el.get("kind") == "table":
            for i, size in enumerate(el.get("font_pts") or []):
                if size not in allowed:
                    messages.append(
                        f"[size] element role={el['role']!r} text={el.get('text')!r} "
                        f"has font_pts[{i}]={size} which is not in type_scale"
                    )
    return messages


def check_within_margins(elements: list, tokens: dict, slide_w: int, slide_h: int) -> list:
    """
    Return violation messages for elements that fall outside the grid margins.

    Tag: [margins]
    Checks: left >= margin_x, top >= margin_top,
            left+width <= slide_w - margin_x,
            top+height <= slide_h - margin_bottom.

    An element marked `full_bleed` (a freeform box placed `at full-bleed`)
    deliberately paints the whole slide, margins included, and is skipped —
    the REQ-204 full-bleed carve-out, mirroring the ghost pattern in
    check_sizes/check_no_overlap. Its colour is still token-checked.
    """
    grid = tokens["grid"]
    mx = grid["margin_x"]
    mt = grid["margin_top"]
    mb = grid["margin_bottom"]
    messages = []
    for el in elements:
        if el.get("full_bleed"):
            continue
        violations = []
        if el["left"] < mx:
            violations.append(f"left={el['left']} < margin_x={mx}")
        if el["top"] < mt:
            violations.append(f"top={el['top']} < margin_top={mt}")
        if el["left"] + el["width"] > slide_w - mx:
            violations.append(
                f"left+width={el['left'] + el['width']} > slide_w-margin_x={slide_w - mx}"
            )
        if el["top"] + el["height"] > slide_h - mb:
            violations.append(
                f"top+height={el['top'] + el['height']} > slide_h-margin_bottom={slide_h - mb}"
            )
        if violations:
            messages.append(
                f"[margins] element role={el['role']!r} text={el['text']!r} "
                f"exceeds margins: {'; '.join(violations)}"
            )
    return messages


def _intersects(a: dict, b: dict) -> bool:
    """True if rectangles a and b overlap with positive area."""
    return (
        a["left"] < b["left"] + b["width"]
        and b["left"] < a["left"] + a["width"]
        and a["top"] < b["top"] + b["height"]
        and b["top"] < a["top"] + a["height"]
    )


def _within(inner: dict, outer: dict) -> bool:
    """True if `inner`'s rectangle sits wholly inside `outer`'s (edges may touch)."""
    return (
        inner["left"] >= outer["left"]
        and inner["top"] >= outer["top"]
        and inner["left"] + inner["width"] <= outer["left"] + outer["width"]
        and inner["top"] + inner["height"] <= outer["top"] + outer["height"]
    )


def _label(el: dict) -> str:
    """A short identifier for a violation message (text elements carry text)."""
    if el.get("text") is not None:
        return f"role={el['role']!r} text={el['text']!r}"
    return f"role={el['role']!r}"


# 1-D line elements (connectors, tree edges) are exempt from the overlap rule: a
# line crossing a box is not a composition fault, and a tree's elbow edges must be
# free to route between rows. Filled elements (box/text/icon) still may not overlap.
_LINE_KINDS = frozenset({"connector", "edge"})


def check_no_overlap(elements: list) -> list:
    """
    Return violation messages for every pair of elements whose rectangles intersect
    with positive area — UNLESS one is a `container` box that wholly holds the
    other, or one is a 1-D line (connector/edge). A card lays its text on top of
    its panel, and a panel may nest inside a larger panel; that stacking is legal
    only when the outer element is `container: True`. Two free FILLED elements (a
    stat number over a stat label, two sibling panels) that intersect are a fault.

    Tag: [overlap]
    """
    messages = []
    n = len(elements)
    for i in range(n):
        a = elements[i]
        for j in range(i + 1, n):
            b = elements[j]
            if not _intersects(a, b):
                continue
            # Ghost type deliberately underlaps (a section slide's numeral sits
            # behind its title), so a pair containing a ghost is never a fault.
            if a.get("ghost") or b.get("ghost"):
                continue
            # Lines never count as overlapping anything.
            if a.get("kind") in _LINE_KINDS or b.get("kind") in _LINE_KINDS:
                continue
            # Legal nesting: a container that wholly holds its partner.
            if (a.get("container") and _within(b, a)) or (
                b.get("container") and _within(a, b)
            ):
                continue
            messages.append(
                f"[overlap] elements overlap: {_label(a)} and {_label(b)}"
            )
    return messages


def check_hierarchy(elements: list) -> list:
    """
    Return a violation message when supporting text reaches the lead's size.

    Elements may carry a `rank`: 1 marks the slide's lead text, 2 its
    supporting text. Hierarchy on these slides is carried by SIZE, so every
    rank-2 size must sit strictly below every rank-1 size. Elements without a
    rank (ticks, rules, decorative glyphs, ghosts — and tables, which carry no
    rank) are ignored: they never constrain the hierarchy.

    Tag: [hierarchy]
    """
    rank1 = [el["font_pt"] for el in elements
             if el.get("rank") == 1 and el.get("font_pt") is not None]
    rank2 = [el["font_pt"] for el in elements
             if el.get("rank") == 2 and el.get("font_pt") is not None]
    if rank1 and rank2:
        min1, max2 = min(rank1), max(rank2)
        if max2 >= min1:
            return [
                f"[hierarchy] rank-2 text at {max2}pt reaches rank-1 text at "
                f"{min1}pt — supporting text must sit below the lead"
            ]
    return []


def check_contrast(elements: list, tokens: dict) -> list:
    """
    Return violation messages for text whose colour does not read on its ground.

    Only elements that carry both `colour` and `ground` (hex) are judged — a
    caller that knows the real background sets `ground`; an element without
    it is skipped, so the check is inert for callers that predate it. An
    element marked `ghost`, or whose `role` starts with "slides-ghost", is the
    one written exception. Threshold: CONTRAST_LARGE at or above
    LARGE_TEXT_PT, else CONTRAST_SMALL.

    Tag: [contrast]
    """
    messages = []
    for el in elements:
        colour, ground = el.get("colour"), el.get("ground")
        if colour is None or ground is None or el.get("font_pt") is None:
            continue
        if el.get("ghost") or str(el.get("role", "")).startswith("slides-ghost"):
            continue
        ratio = contrast_ratio(_norm(colour), _norm(ground))
        needed = CONTRAST_LARGE if el["font_pt"] >= LARGE_TEXT_PT else CONTRAST_SMALL
        if ratio < needed:
            messages.append(
                f"[contrast] element {_label(el)} colour={_norm(colour)} on "
                f"ground={_norm(ground)} has ratio {ratio:.2f}, below {needed} "
                f"for {el['font_pt']}pt text"
            )
    return messages


def check_count(elements: list) -> list:
    """
    Return a violation message if the number of elements exceeds ELEMENT_CAP.

    Tag: [count]
    """
    if len(elements) > ELEMENT_CAP:
        return [
            f"[count] slide has {len(elements)} elements which exceeds the cap of {ELEMENT_CAP}"
        ]
    return []


def check(elements: list, tokens: dict, slide_w: int, slide_h: int) -> None:
    """
    Run all seven lint rules and raise LintError if any violations are found.

    Returns None if the slide is clean.
    """
    messages = (
        check_colours(elements, tokens)
        + check_sizes(elements, tokens)
        + check_within_margins(elements, tokens, slide_w, slide_h)
        + check_no_overlap(elements)
        + check_hierarchy(elements)
        + check_contrast(elements, tokens)
        + check_count(elements)
    )
    if messages:
        header = "Composed slide failed mechanical lint:"
        raise LintError(header + "\n" + "\n".join(messages))
    return None


def review(elements: list, tokens: dict, slide_w: int, slide_h: int) -> list:
    """Run the ADVISORY composition rules and return findings; NEVER raises.

    This is the advisory tier — distinct from check(), the hard system gate.
    Each finding is {"rule_id", "tier", "severity", "message"}. The advisory
    layer can never change a render's exit code: a broken or missing composition
    module yields [] (guarded lazy import), and a rule whose check raises is
    skipped (per-rule try/except). Rules are run only when the slide contains
    elements they apply to (applies_to gating) — so an empty slide yields [].
    """
    try:
        import composition  # noqa: PLC0415 — lazy + guarded; advisory must not block
    except Exception:  # noqa: BLE001 — a broken advisory module must never block
        return []

    def _family(name):
        # An element's primitive family is the prefix of its role
        # ("stat-number" -> "stat"); a rule's is the prefix of applies_to
        # ("stat-row" -> "stat"). A rule runs only against its own family.
        return str(name).split("-", 1)[0]

    # Group elements by primitive family, so a rule judges ONLY its own block's
    # elements. On a multi-block slide a stat-row rule must not see the process
    # boxes stacked below it (that would false-flag decoration/breathing-room).
    by_family = {}
    for el in elements:
        if isinstance(el, dict):
            by_family.setdefault(_family(el.get("role", "")), []).append(el)

    findings = []
    for rule in getattr(composition, "RULES", []):
        subset = by_family.get(_family(rule.get("applies_to", "")))
        if not subset:
            continue
        try:
            satisfied = rule["check"](subset, tokens, slide_w, slide_h)
        except Exception:  # noqa: BLE001 — a throwing advisory rule is skipped
            continue
        if not satisfied:
            findings.append({
                "rule_id": rule["id"],
                "tier": rule["tier"],
                "severity": rule["severity"],
                "message": rule["message"],
            })
    return findings
