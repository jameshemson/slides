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

ELEMENT_CAP = 12


class LintError(Exception):
    """A composed slide that fails the mechanical lint. render.py turns this into a SpecError."""


def _norm(h: str) -> str:
    """Normalise a hex colour string to '#RRGGBB' uppercase form."""
    return "#" + h.lstrip("#").upper()


def check_colours(elements: list, tokens: dict) -> list:
    """
    Return violation messages for elements whose colour is not in the token palette.

    Tag: [colour]
    """
    allowed = {_norm(v) for v in tokens["colour_roles"].values()}
    messages = []
    for el in elements:
        if _norm(el["colour"]) not in allowed:
            messages.append(
                f"[colour] element role={el['role']!r} text={el['text']!r} "
                f"has colour {el['colour']!r} which is not in colour_roles"
            )
    return messages


def check_sizes(elements: list, tokens: dict) -> list:
    """
    Return violation messages for elements whose font_pt is not in the type scale.

    Tag: [size]
    """
    allowed = set(tokens["type_scale"].values())
    messages = []
    for el in elements:
        if el["font_pt"] not in allowed:
            messages.append(
                f"[size] element role={el['role']!r} text={el['text']!r} "
                f"has font_pt={el['font_pt']} which is not in type_scale"
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


def check_no_overlap(elements: list) -> list:
    """
    Return violation messages for every pair of elements whose rectangles intersect
    with positive area.

    Tag: [overlap]
    Intersection test: (a.left < b.left+b.width) and (b.left < a.left+a.width)
                       and (a.top < b.top+b.height) and (b.top < a.top+a.height)
    """
    messages = []
    n = len(elements)
    for i in range(n):
        a = elements[i]
        for j in range(i + 1, n):
            b = elements[j]
            if (
                a["left"] < b["left"] + b["width"]
                and b["left"] < a["left"] + a["width"]
                and a["top"] < b["top"] + b["height"]
                and b["top"] < a["top"] + a["height"]
            ):
                messages.append(
                    f"[overlap] elements overlap: "
                    f"role={a['role']!r} text={a['text']!r} "
                    f"and role={b['role']!r} text={b['text']!r}"
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
