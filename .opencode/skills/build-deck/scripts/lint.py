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


class LintError(Exception):
    """A composed slide that fails the mechanical lint. render.py turns this into a SpecError."""


def _norm(h: str) -> str:
    """Normalise a hex colour string to '#RRGGBB' uppercase form."""
    return "#" + h.lstrip("#").upper()


# Every key on an element that carries a colour. Text elements colour their
# `colour`; box/connector elements colour their `fill` and (optionally) `stroke`.
# Whichever are present must all be token colours — the gate is the same.
_COLOUR_KEYS = ("colour", "fill", "stroke")


def check_colours(elements: list, tokens: dict) -> list:
    """
    Return violation messages for elements whose colour is not in the token palette.

    Checks every colour-bearing key present on the element (`colour` for text,
    `fill`/`stroke` for boxes) — a card panel's fill is held to the token
    palette exactly like a stat number's text colour.

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
    return messages


def check_sizes(elements: list, tokens: dict) -> list:
    """
    Return violation messages for elements whose font_pt is not in the type scale.

    Box and connector elements carry no `font_pt` (they hold no text) and are
    skipped — only text is held to the type scale.

    Tag: [size]
    """
    allowed = set(tokens["type_scale"].values())
    messages = []
    for el in elements:
        font_pt = el.get("font_pt")
        if font_pt is None:
            continue
        if font_pt not in allowed:
            messages.append(
                f"[size] element role={el['role']!r} text={el.get('text')!r} "
                f"has font_pt={font_pt} which is not in type_scale"
            )
    return messages


def check_within_margins(elements: list, tokens: dict, slide_w: int, slide_h: int) -> list:
    """
    Return violation messages for elements that fall outside the grid margins.

    Tag: [margins]
    Checks: left >= margin_x, top >= margin_top,
            left+width <= slide_w - margin_x,
            top+height <= slide_h - margin_bottom.
    """
    grid = tokens["grid"]
    mx = grid["margin_x"]
    mt = grid["margin_top"]
    mb = grid["margin_bottom"]
    messages = []
    for el in elements:
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
    Run all five lint rules and raise LintError if any violations are found.

    Returns None if the slide is clean.
    """
    messages = (
        check_colours(elements, tokens)
        + check_sizes(elements, tokens)
        + check_within_margins(elements, tokens, slide_w, slide_h)
        + check_no_overlap(elements)
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
