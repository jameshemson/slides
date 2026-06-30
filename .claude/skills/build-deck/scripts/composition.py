"""
Advisory composition registry for stat_row slides.

Rules in this module are ADVISORY only — they never block a build.
They are brand-agnostic: every threshold and colour reference is
resolved from the tokens dict at call-time; no brand literals appear
here.  Concreteness (deck-specific guidance, authored examples) lives
in documentation, not here.

Public surface
--------------
RULES : list[dict]
    Each rule has keys: id, tier, severity, applies_to, source,
    message, check.

    check(elements, tokens, slide_w, slide_h) -> bool
        Returns True  when the slide SATISFIES the rule (no problem).
        Returns False when the slide SHOULD warn.

Contrast helpers (WCAG 2.2)
----------------------------
_hex_to_rgb(h)          -> (r, g, b) in 0..255
_norm(h)                -> "#RRGGBB" uppercase, normalises input
_rel_luminance(h)       -> float  (linearised sRGB)
contrast_ratio(h1, h2)  -> float
"""

# ---------------------------------------------------------------------------
# WCAG contrast helpers — stdlib only, no external imports
# ---------------------------------------------------------------------------

def _norm(h: str) -> str:
    """Return colour as '#RRGGBB' uppercase, stripping any leading '#'."""
    h = h.strip().lstrip("#").upper()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def _hex_to_rgb(h: str):
    """Return (r, g, b) tuple in 0-255 range from a hex colour string."""
    h = _norm(h).lstrip("#")
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


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _numbers(elements):
    return [e for e in elements if e["role"] == "stat-number"]


def _labels(elements):
    return [e for e in elements if e["role"] == "stat-label"]


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

def _check_hierarchy_ratio(elements, tokens, slide_w, slide_h):
    nums = _numbers(elements)
    labs = _labels(elements)
    if not nums or not labs:
        return True
    ratio = nums[0]["font_pt"] / labs[0]["font_pt"]
    return 2.5 <= ratio <= 6


def _check_stat_count(elements, tokens, slide_w, slide_h):
    return len(_numbers(elements)) <= 5


def _check_contrast(elements, tokens, slide_w, slide_h):
    paper = tokens["colour_roles"].get("paper")
    if not paper:
        return True
    for num in _numbers(elements):
        if contrast_ratio(num["colour"], paper) < 3.0:
            return False
    for lab in _labels(elements):
        threshold = 4.5 if lab["font_pt"] < 18 else 3.0
        if contrast_ratio(lab["colour"], paper) < threshold:
            return False
    return True


def _check_value_terseness(elements, tokens, slide_w, slide_h):
    return all(len(e["text"]) <= 6 for e in _numbers(elements))


def _check_label_terseness(elements, tokens, slide_w, slide_h):
    return all(len(e["text"].split()) <= 3 for e in _labels(elements))


def _check_breathing_room(elements, tokens, slide_w, slide_h):
    if not elements:
        return True
    grid = tokens["grid"]
    top_margin = grid["margin_top"]
    bottom_margin = grid["margin_bottom"]
    band_top = top_margin
    band_bottom = slide_h - bottom_margin
    band_h = band_bottom - band_top
    row_top = min(e["top"] for e in elements)
    row_bottom = max(e["top"] + e["height"] for e in elements)
    row_block = row_bottom - row_top
    if band_h <= 0:
        return True
    return row_block <= 0.5 * band_h


def _check_one_accent(elements, tokens, slide_w, slide_h):
    cr = tokens["colour_roles"]
    accent = cr.get("accent")
    if not accent:
        return True
    ink = cr.get("ink")
    muted = cr.get("muted")
    label_palette = {_norm(c) for c in (ink, muted) if c is not None}
    for num in _numbers(elements):
        if _norm(num["colour"]) != _norm(accent):
            return False
    for lab in _labels(elements):
        if _norm(lab["colour"]) not in label_palette:
            return False
    return True


def _check_decoration_present(elements, tokens, slide_w, slide_h):
    allowed = {"stat-number", "stat-label"}
    return all(e["role"] in allowed for e in elements)


def _check_emphasis_colour_only(elements, tokens, slide_w, slide_h):
    nums = _numbers(elements)
    labs = _labels(elements)
    if not nums or not labs:
        return True
    return nums[0]["font_pt"] > labs[0]["font_pt"]


# ---------------------------------------------------------------------------
# RULES registry
# ---------------------------------------------------------------------------

RULES = [
    {
        "id": "hierarchy-ratio",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#3 (user decks §F; no perceptual study — advisory band)",
        "message": (
            "Number should be ~3-4x its label (advisory band 2.5-6); "
            "size the number up / label down."
        ),
        "check": _check_hierarchy_ratio,
    },
    {
        "id": "stat-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#4 (Cowan working memory ~3-5)",
        "message": "Keep a stat row to ~3-5 figures; more is a table.",
        "check": _check_stat_count,
    },
    {
        "id": "contrast",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#9 (WCAG 2.2 AA)",
        "message": (
            "Ensure WCAG AA contrast (number >=3:1, small label >=4.5:1) "
            "vs the paper background."
        ),
        "check": _check_contrast,
    },
    {
        "id": "value-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#3 / inknarrates",
        "message": "Hero values stay terse (<=~5 chars: \"56\", \"4%\", \"$1.2M\").",
        "check": _check_value_terseness,
    },
    {
        "id": "label-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#3 (user decks §F)",
        "message": "Labels stay to <=3 words.",
        "check": _check_label_terseness,
    },
    {
        "id": "breathing-room",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report (whitespace=pacing; §E)",
        "message": (
            "Leave whitespace; the row shouldn't fill the content band."
        ),
        "check": _check_breathing_room,
    },
    {
        "id": "one-accent",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#7 (grey-push; user decks §D)",
        "message": (
            "One accent — numbers in the accent, labels in ink/muted; "
            "not a rainbow."
        ),
        "check": _check_one_accent,
    },
    {
        "id": "decoration-present",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "impeccable hero-metric ban / report#2",
        "message": (
            "No decoration; a strong stat row is the numbers + labels, "
            "nothing else."
        ),
        "check": _check_decoration_present,
    },
    {
        "id": "emphasis-colour-only",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "stat-row",
        "source": "report#9 (WCAG 1.4.1) / report#8",
        "message": (
            "Emphasise by size, not colour alone."
        ),
        "check": _check_emphasis_colour_only,
    },
]
