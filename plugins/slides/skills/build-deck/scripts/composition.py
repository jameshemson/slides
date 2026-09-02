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
# _rel_luminance and contrast_ratio now live in lint.py, which owns the hard
# contrast gate (lint.check_contrast); they are re-exported here so the
# advisory rules below — and any existing caller importing them from
# composition — keep working unchanged. lint.py imports composition only
# lazily inside review(), so this module-level import raises no cycle.

from lint import contrast_ratio, _rel_luminance  # noqa: F401


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


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _numbers(elements):
    return [e for e in elements if e["role"] == "stat-number"]


def _labels(elements):
    return [e for e in elements if e["role"] == "stat-label"]


def _by_role(elements, role):
    return [e for e in elements if e.get("role") == role]


def _accent_boxes(elements, tokens):
    """How many box elements are filled with the accent colour (the emphasis)."""
    accent = tokens["colour_roles"].get("accent")
    if not accent:
        return 0
    accent = _norm(accent)
    return sum(
        1 for e in elements
        if e.get("kind") == "box" and _norm(e.get("fill", "#")) == accent
    )


def _all_terse(texts, max_words):
    """True if every text is at most `max_words` words (blank strings ignored)."""
    return all(len(str(t).split()) <= max_words for t in texts if str(t).strip())


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
    # Per line: a stat label may break on ' / ' (already "\n" by planning
    # time), and a two-line label of terse lines is not a wordy label.
    return all(
        len(line.split()) <= 3
        for e in _labels(elements)
        for line in str(e["text"]).split("\n")
        if line.strip()
    )


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


# --- card-grid ---------------------------------------------------------------

def _check_card_count(elements, tokens, slide_w, slide_h):
    return 2 <= len(_by_role(elements, "card-panel")) <= 5


def _check_card_label_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse((e["text"] for e in _by_role(elements, "card-label")), 3)


def _check_card_one_accent(elements, tokens, slide_w, slide_h):
    return _accent_boxes(_by_role(elements, "card-panel"), tokens) <= 1


# --- comparison --------------------------------------------------------------

def _check_comparison_resolves(elements, tokens, slide_w, slide_h):
    panels = _by_role(elements, "comparison-panel")
    if not panels:
        return True
    return _accent_boxes(panels, tokens) == 1


def _check_comparison_header_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse(
        (e["text"] for e in _by_role(elements, "comparison-header")), 3)


# --- process -----------------------------------------------------------------

def _check_process_count(elements, tokens, slide_w, slide_h):
    return 2 <= len(_by_role(elements, "process-step")) <= 5


def _check_process_label_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse((e["text"] for e in _by_role(elements, "process-label")), 3)


# --- timeline ----------------------------------------------------------------

def _check_timeline_count(elements, tokens, slide_w, slide_h):
    return 2 <= len(_by_role(elements, "timeline-dot")) <= 6


def _check_timeline_emphasis(elements, tokens, slide_w, slide_h):
    dots = _by_role(elements, "timeline-dot")
    if not dots:
        return True
    return _accent_boxes(dots, tokens) >= 1


def _check_timeline_terseness(elements, tokens, slide_w, slide_h):
    # A timeline label is "date\nevent"; judge the event line's terseness.
    events = [
        str(e["text"]).split("\n")[-1]
        for e in _by_role(elements, "timeline-label")
    ]
    return _all_terse(events, 3)


# --- freeform ----------------------------------------------------------------

def _check_freeform_one_accent(elements, tokens, slide_w, slide_h):
    # Freeform trades good-by-construction for freedom, so it carries only one
    # advisory guardrail: grey-push the field, spend the accent on one or two
    # marks. Counts any element (fill or text colour) using the accent.
    accent = tokens["colour_roles"].get("accent")
    if not accent:
        return True
    accent = _norm(accent)
    used = sum(
        1 for e in elements
        if _norm(str(e.get("fill") or e.get("colour") or "#")) == accent
    )
    return used <= 2


# --- tree --------------------------------------------------------------------

def _check_tree_count(elements, tokens, slide_w, slide_h):
    return 2 <= len(_by_role(elements, "tree-node")) <= 8


def _check_tree_depth(elements, tokens, slide_w, slide_h):
    # Node boxes sit in per-depth rows, so distinct tops count the levels.
    return len({e["top"] for e in _by_role(elements, "tree-node")}) <= 3


def _check_tree_label_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse((e["text"] for e in _by_role(elements, "tree-label")), 4)


def _check_tree_one_accent(elements, tokens, slide_w, slide_h):
    return _accent_boxes(_by_role(elements, "tree-node"), tokens) <= 1


# --- icon-list ---------------------------------------------------------------

def _check_iconlist_count(elements, tokens, slide_w, slide_h):
    return 2 <= len(_by_role(elements, "iconlist-icon")) <= 6


# --- cycle / matrix ----------------------------------------------------------

def _check_cycle_count(elements, tokens, slide_w, slide_h):
    return 2 <= len(_by_role(elements, "cycle-node")) <= 6


def _check_cycle_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse((e["text"] for e in _by_role(elements, "cycle-label")), 3)


def _check_matrix_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse((e["text"] for e in _by_role(elements, "matrix-label")), 3)


def _check_matrix_one_accent(elements, tokens, slide_w, slide_h):
    return _accent_boxes(_by_role(elements, "matrix-cell"), tokens) <= 1


# --- table -------------------------------------------------------------------
# A table is ONE element (kind "table", role "table-grid"): a native
# GraphicFrame, not per-cell boxes.  So these rules read the element's own
# structural keys — "header" (list), "rows" (list of data-row cell lists),
# "emphasis_rows" (indices) — defensively (.get, never raise).

def _tables(elements):
    return [e for e in elements if e.get("role") == "table-grid"]


def _check_table_count(elements, tokens, slide_w, slide_h):
    return all(len(t.get("rows") or []) <= 6 for t in _tables(elements))


def _check_table_column_count(elements, tokens, slide_w, slide_h):
    return all(len(t.get("header") or []) <= 5 for t in _tables(elements))


def _check_table_cell_terseness(elements, tokens, slide_w, slide_h):
    for t in _tables(elements):
        cells = list(t.get("header") or [])
        for row in (t.get("rows") or []):
            cells.extend(row or [])
        if not _all_terse(cells, 6):
            return False
    return True


def _check_table_one_accent(elements, tokens, slide_w, slide_h):
    return all(len(t.get("emphasis_rows") or []) <= 1 for t in _tables(elements))


# --- bodyslide / statement (drawn fixed-role slides) --------------------------
# These roles are drawn (not composed) fixed-role slides — a title-content
# ("bodyslide-") slide and a hero-claim ("statement-") slide. The checks
# filter by the EXACT role (never the family) so a rule never judges a
# sibling role sharing the same family prefix.

def _check_role_body_length(elements, tokens, slide_w, slide_h):
    bodies = _by_role(elements, "bodyslide-body")
    return len(bodies) <= 5 and _all_terse((e["text"] for e in bodies), 40)


def _check_statement_terseness(elements, tokens, slide_w, slide_h):
    return _all_terse((e["text"] for e in _by_role(elements, "statement-text")), 16)


# ---------------------------------------------------------------------------
# RULES registry
# ---------------------------------------------------------------------------

# Block-count is a slide-structure note, not an element-family rule, so it
# cannot live in RULES (lint.review gates rules by primitive family and never
# sees the parsed blocks). render.py appends this finding itself when a
# composed slide carries more than MAX_COMPOSED_BLOCKS blocks — same shape as
# a review finding, same advisory guarantee.
BLOCK_COUNT = {
    "rule_id": "block-count",
    "tier": "quality",
    "severity": "advisory",
    "message": (
        "A composed slide reads best with at most 4 blocks; "
        "more is a wall — split the slide."
    ),
}

# Deck-level device repetition (the reflex/earn-it check, mechanical half). Like
# BLOCK_COUNT this is a cross-slide note that cannot live in RULES — lint.review
# is single-slide and family-gated, so it never sees the deck as a set. render.py
# accumulates each content slide's primary device across the whole deck and calls
# the helper below after the render loop, appending any finding to the same
# advisory channel BLOCK_COUNT uses (same shape, same advisory guarantee).
#
# Only NAMED composed primitives count. `freeform` is excluded: it is mechanically
# uniform but visually heterogeneous (a node graph, a dumbbell, and an annotated
# layout are all freeform), so a count cannot tell a repeated dumbbell from three
# distinct figures — that catch lives in the prose reflex. Fixed roles are
# excluded too: statement/quote bookends are narrative framing, not a device
# reflex.
DECK_DEVICE_TYPES = frozenset({
    "stat-row", "card-grid", "comparison", "process", "timeline",
    "tree", "cycle", "matrix", "table", "icon-list",
})

DECK_DEVICE_REPETITION = {
    "rule_id": "deck-device-repetition",
    "tier": "quality",
    "severity": "advisory",
    "message": "",  # deck_device_repetition() fills this with the device + count
}


def deck_device_repetition(devices, content_slides):
    """One device carried deck-wide reads as a template, not an argument.

    `devices` is the list of named composed devices — one per composed slide whose
    first block is a DECK_DEVICE_TYPES primitive (freeform and fixed roles are not
    in it; render.py pre-filters). `content_slides` is the count of non-framing
    slides (all but title/section) — the denominator for "how much of the deck is
    this one device". Returns an advisory finding (same shape as BLOCK_COUNT) when
    the most-repeated device is on >= 3 slides AND strictly more than half the
    content slides; else None. Advisory only — never blocks a render.
    """
    if not devices or content_slides <= 0:
        return None
    counts = {}
    for name in devices:
        counts[name] = counts.get(name, 0) + 1
    top = max(counts, key=counts.get)  # first-inserted on a tie (deterministic)
    n = counts[top]
    if n < 3 or n / content_slides <= 0.5:
        return None
    finding = dict(DECK_DEVICE_REPETITION)
    finding["message"] = (
        f"{n} of the deck's slides are a '{top}' — one device repeated reads as "
        f"monotony; vary the form or let the point earn a different shape."
    )
    return finding


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
        "message": "Labels stay to <=3 words per line.",
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
    # --- card-grid -----------------------------------------------------------
    {
        "id": "card-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "card-grid",
        "source": "report#4 (Cowan); PP s75 'three or five topics / MECE'",
        "message": "Keep a card grid to 3-5 cards; 6+ is a wall, 1 isn't a grid.",
        "check": _check_card_count,
    },
    {
        "id": "card-label-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "card-grid",
        "source": "report#3 (decks §F); Visme p118 lorem anti-pattern",
        "message": "Card labels stay to <=3 words; one line of body at most.",
        "check": _check_card_label_terseness,
    },
    {
        "id": "card-one-accent",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "card-grid",
        "source": "report#7 (grey-push, one accent; decks §D)",
        "message": (
            "At most one card leads (accent fill); the rest are siblings, "
            "not a rainbow."
        ),
        "check": _check_card_one_accent,
    },
    # --- comparison ----------------------------------------------------------
    {
        "id": "comparison-resolves",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "comparison",
        "source": "PP s79-82 / Bluey s45-48 ('order for impact'; end on the turn)",
        "message": (
            "A comparison should resolve, not balance — mark the winning side "
            "(the turn), don't leave both equal."
        ),
        "check": _check_comparison_resolves,
    },
    {
        "id": "comparison-header-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "comparison",
        "source": "report#3 (decks §F)",
        "message": "Comparison headers stay to <=3 words (a one-word verdict).",
        "check": _check_comparison_header_terseness,
    },
    # --- process -------------------------------------------------------------
    {
        "id": "process-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "process",
        "source": "report#4 (Cowan); PP s14 3-step 'Plan/Create/Deliver'",
        "message": "Keep a process to 3-5 steps; his signature is three.",
        "check": _check_process_count,
    },
    {
        "id": "process-label-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "process",
        "source": "report#3 (terse verb / 1-3-word step)",
        "message": "Step labels stay to <=3 words (a terse verb).",
        "check": _check_process_label_terseness,
    },
    # --- timeline ------------------------------------------------------------
    {
        "id": "timeline-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "timeline",
        "source": "report#4 (Cowan ~3-5)",
        "message": "Keep a timeline to ~3-6 milestones; more is a table on a rail.",
        "check": _check_timeline_count,
    },
    {
        "id": "timeline-emphasis",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "timeline",
        "source": "report#7 (grey-push, one accent); Visme p91 (hierarchy)",
        "message": (
            "Emphasise one milestone (the turn); an even dotted rule has no "
            "hierarchy."
        ),
        "check": _check_timeline_emphasis,
    },
    {
        "id": "timeline-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "timeline",
        "source": "report#3; Evergreen (date + <=3-word event)",
        "message": "Each milestone is a date + a <=3-word event, not a paragraph.",
        "check": _check_timeline_terseness,
    },
    # --- freeform ------------------------------------------------------------
    {
        "id": "freeform-one-accent",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "freeform",
        "source": "report#7 (grey-push, one accent; decks §D)",
        "message": (
            "Grey-push the field — keep the accent to one or two marks, "
            "not a rainbow."
        ),
        "check": _check_freeform_one_accent,
    },
    # --- tree ----------------------------------------------------------------
    {
        "id": "tree-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "tree",
        "source": "report#4 (Cowan); org-chart legibility",
        "message": "Keep a tree to ~3-8 nodes; more is a diagram, not a slide.",
        "check": _check_tree_count,
    },
    {
        "id": "tree-depth",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "tree",
        "source": "report#4 (Cowan); org-chart legibility",
        "message": "Keep a tree to 3 levels or fewer; deeper is a diagram, not a slide.",
        "check": _check_tree_depth,
    },
    {
        "id": "tree-label-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "tree",
        "source": "report#3 (terse labels)",
        "message": "Tree node labels stay to <=4 words.",
        "check": _check_tree_label_terseness,
    },
    {
        "id": "tree-one-accent",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "tree",
        "source": "report#7 (grey-push, one accent)",
        "message": (
            "At most one node leads (accent fill); the rest are the grey field."
        ),
        "check": _check_tree_one_accent,
    },
    # --- icon-list -----------------------------------------------------------
    {
        "id": "iconlist-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "iconlist",
        "source": "report#4 (Cowan)",
        "message": "Keep an icon list to ~3-6 rows.",
        "check": _check_iconlist_count,
    },
    # --- cycle ---------------------------------------------------------------
    {
        "id": "cycle-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "cycle",
        "source": "report#4 (Cowan)",
        "message": "Keep a cycle to ~3-6 stages.",
        "check": _check_cycle_count,
    },
    {
        "id": "cycle-label-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "cycle",
        "source": "report#3 (terse labels)",
        "message": "Cycle stage labels stay to <=3 words.",
        "check": _check_cycle_terseness,
    },
    # --- matrix --------------------------------------------------------------
    {
        "id": "matrix-label-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "matrix",
        "source": "report#3 (terse labels)",
        "message": "Matrix quadrant labels stay to <=3 words.",
        "check": _check_matrix_terseness,
    },
    {
        "id": "matrix-one-accent",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "matrix",
        "source": "report#7 (grey-push, one accent)",
        "message": "At most one quadrant leads (accent); the rest are the grey field.",
        "check": _check_matrix_one_accent,
    },
    # --- table ---------------------------------------------------------------
    {
        "id": "table-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "table-grid",
        "source": "report#4 (Cowan)",
        "message": (
            "Keep a table to ~6 data rows; more is a spreadsheet — "
            "cut rows or split the slide."
        ),
        "check": _check_table_count,
    },
    {
        "id": "table-column-count",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "table-grid",
        "source": "report#4 (Cowan); column legibility at body width",
        "message": (
            "Keep a table to ~5 columns; more squeezes every cell — "
            "cut columns or split the slide."
        ),
        "check": _check_table_column_count,
    },
    {
        "id": "table-cell-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "table-grid",
        "source": "report#3 (terse cells)",
        "message": (
            "Table cells stay terse (<=~6 words each); a cell holding a "
            "sentence belongs in prose, not a grid."
        ),
        "check": _check_table_cell_terseness,
    },
    {
        "id": "table-one-accent",
        "tier": "slop",
        "severity": "advisory",
        "applies_to": "table-grid",
        "source": "report#7 (grey-push, one accent)",
        "message": (
            "At most one row leads (accent fill); the rest are the grey field, "
            "not a rainbow."
        ),
        "check": _check_table_one_accent,
    },
    # --- bodyslide / statement (drawn fixed-role slides) ---------------------
    {
        "id": "role-body-length",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "bodyslide-body",
        "source": "report#3; deck-spec (one point per slide)",
        "message": (
            "a title-content slide carries one point and the few lines that "
            "earn it — a shaped list belongs in composed"
        ),
        "check": _check_role_body_length,
    },
    {
        "id": "statement-terseness",
        "tier": "quality",
        "severity": "advisory",
        "applies_to": "statement-text",
        "source": "report#3",
        "message": "a statement is a single hero claim — cut it to the line that lands",
        "check": _check_statement_terseness,
    },
]
