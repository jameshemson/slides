# Changelog

All notable changes to the slides skill pack are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/), and the pack uses
[semantic versioning](https://semver.org/).

## [Unreleased]

### Added

- **A third composition mode: compose from brand-locked atoms.** A new
  `composed` deck-spec role draws *primitives* on the template's own grid
  instead of filling fixed placeholders — invention in the arrangement,
  consistency guaranteed by design tokens plus a mechanical lint. This release
  ships one primitive, `stat-row` (a row of hero numbers with labels), and is
  fully brand-agnostic: everything derives from the user's template and
  `brand.json`.
- **A design-token layer (`tokens.py`).** An optional `tokens` block in
  `brand.json` carries a `grid` (margins, columns, gutter, baseline — derived
  from the geometry of the template's own *mapped* layouts, so unused template
  layouts can't pollute it), a `type_scale` (named point sizes), and
  `colour_roles` (ink, paper, accent, muted — mapped from the palette by
  luminance). `init_brand.py` and `extract_brand.py` now emit a starting block;
  `build-deck` derives defaults at render time when it is absent.
- **A load-bearing mechanical lint (`lint.py`).** Composed mode reopens the
  "add a shape" door that the renderer used to close structurally, so a
  deterministic lint is the new guarantee: every fill is a token colour, every
  size a type-scale step, every element within the margins, nothing overlaps,
  and the element count is under a cap — enforced at the render gate, failing
  loudly by slide and element with no half-built `.pptx`.
- **The literal quarantine (`primitives.py`).** Primitives are the only code
  allowed to emit colour/coordinate literals, and only ever token-derived ones.
  `render.py` and `pptxlib.py` keep their zero-literal, no-direct-shape
  guarantee; the six fixed roles are unchanged and existing decks render
  identically (the `tokens` key is optional).

### Fixed

- Removed stray `</content>`/`</invoke>` artifact lines accidentally committed
  at the end of `presentation-craft/reference/deck-spec.md`.

## [0.5.0] - 2026-06-26

### Added

- **One-step brand setup, so onboarding actually happens.** A new
  `init_brand.py` turns a single template or existing deck into a complete,
  renderable `brand.json` — `template`, theme `fonts` and `colours` (via
  v0.4.0's `read_theme`), and a proposed `layout_map`. The layout map is a
  heuristic that maps each of the six semantic roles to one of the template's
  real layouts: a normalised name match first (with `quote` falling back to a
  `section` layout), otherwise the tightest-fitting layout with enough content
  placeholders for the role's fields, so a role is never mapped to a layout that
  would overflow at render.
- **build-deck and narrative offer the fast path.** When `.slides/` is absent,
  the Context Gathering Protocol now offers to set the brand up from a template
  or deck in one step (init_brand) as well as the full `teach-slides` interview,
  so a user is no longer silently left with an off-brand deck. teach-slides
  remains the authoritative, fuller brand capture.

## [0.4.0] - 2026-06-26

### Added

- **Brand extraction from a template deck.** A new `extract_brand.py` reads a
  `.pptx`/`.potx` and prints its brand as the deck already carries it: heading
  and body fonts and a named colour palette (accent colours plus `ink` and
  `paper`) from the theme, alongside the layout list. It is a superset of
  `inspect_template.py`. Backed by a new `pptxlib.read_theme(prs)`, the inverse
  of `apply_theme` (reads the same `fontScheme`/`clrScheme`, handling both
  `srgbClr` and `sysClr` colour children).
- **teach-slides reads your brand instead of asking for it.** When you supply a
  template or an existing deck (Step 3 paths a/b), teach-slides now runs
  `extract_brand.py` and pre-fills `brand.json` fonts and colours; the interview
  becomes confirm-and-adjust rather than typing every hex. The no-deck starter
  path (c, `make_template`) is unchanged.

## [0.3.0] - 2026-06-26

### Added

- **Layer 3 of the slop detector: AI-voice tells.** A new reference file
  `presentation-craft/reference/ai-voice.md` catches the analytical register a
  language model slips into to sound insightful, which the prose-slop layer
  misses. It holds the Claudism catalogue (fifteen families, from performative
  pushback and the reframe announcement to the colon reveal and the aphoristic
  closer), an AI vocabulary watchlist, assistant-artifact slop (a trailing
  "shall I draft the next slide?" or model self-reference fails the draft
  outright, like an em dash), and uniform-rhythm detection. `slop-check` and the
  `presentation-craft` reference index are wired to it; the `slop-check`
  fixtures gained planted Layer 3 tells, locked by `tests/test_fixtures.py`.
  Adapted from the detector in the `pm-skills` repo.

## [0.2.0] - 2026-06-26

### Added

- **Native chart rendering in `build-deck`.** A `title-content` slide can carry
  a structured `Chart:` block, and the renderer draws it as an on-brand chart
  placed below the slide's body line. Five chart types across four Graphic
  Continuum families:
  - `bar` and `column` (comparing categories)
  - `line` (change over time, with optional labelled event markers)
  - `pie` (part-to-whole)
  - `scatter` (relationship)
- **Brand-driven styling, no hardcoded design.** Chart colours come from
  `brand.json` `colours`; an optional `emphasis:` paints one category in the
  brand accent and mutes the rest. Charts use the brand font when `brand.json`
  names a `font_files` path. The renderer adds no font, colour, or coordinate
  literals: chart geometry is derived from the template.
- **`slop-check` chart-consistency criterion.** Flags a chart whose figures
  contradict the numbers in the slide's body or notes.

### Changed

- The deck spec gains a `Chart:` field (documented in
  `presentation-craft/reference/deck-spec.md`); `data-viz.md`, the `build-deck`
  and `narrative` skill prompts, and `slop-check` are updated to match.
- `Body:` is now optional on a `title-content` slide when a `Chart:` is present
  (a chart and a one-line body may coexist; at least one is required).

### Dependencies

- `matplotlib` is a new optional dependency, needed only to draw `Chart:`
  slides (`pip install matplotlib`). It is imported lazily, so a deck with no
  charts never needs it. When matplotlib is absent, a chart slide degrades to a
  "VISUAL TO ADD" note built from the chart data, and the deck still builds.

## [0.1.0] - 2026-05-16

### Added

- Initial release. Five skills — `presentation-craft` (shared knowledge base),
  `teach-slides`, `narrative`, `build-deck`, `slop-check` — portable across
  Claude Code, OpenCode, and Codex.
- A `python-pptx` renderer that fills the user's own template, and a two-layer
  (presentation + prose) slop detector.

[0.5.0]: https://github.com/jameshemson/slides/releases/tag/v0.5.0
[0.4.0]: https://github.com/jameshemson/slides/releases/tag/v0.4.0
[0.3.0]: https://github.com/jameshemson/slides/releases/tag/v0.3.0
[0.2.0]: https://github.com/jameshemson/slides/releases/tag/v0.2.0
[0.1.0]: https://github.com/jameshemson/slides/releases/tag/v0.1.0
