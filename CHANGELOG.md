# Changelog

All notable changes to the slides skill pack are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/), and the pack uses
[semantic versioning](https://semver.org/).

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

[0.3.0]: https://github.com/jameshemson/slides/releases/tag/v0.3.0
[0.2.0]: https://github.com/jameshemson/slides/releases/tag/v0.2.0
[0.1.0]: https://github.com/jameshemson/slides/releases/tag/v0.1.0
