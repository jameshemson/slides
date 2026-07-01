# Changelog

All notable changes to the slides skill pack are recorded here. The format
follows [Keep a Changelog](https://keepachangelog.com/), and the pack uses
[semantic versioning](https://semver.org/).

## [0.8.0] - 2026-07-01

A brand-constrained visual vocabulary. The composed role gains icons, a
hierarchy/tree diagram, and — the deeper win — the brand's *real* type scale, so
composed slides read as the brand's own without copying its template layouts.
Grounded in the Design philosophy now in CLAUDE.md: constrain to identity, let
the model compose. Back-compatible: the six fixed roles and existing `brand.json`
files render unchanged (the new tokens are optional).

### Added

- **Icons (iconoir).** 44 curated monochrome line icons (MIT, © Luca Burgio,
  bundled with LICENSE) recoloured to a token colour and rasterised to PNG —
  on-brand by construction. Usable as a `Block: icon-list` (icons as bullets), a
  `[icon-name]` prefix on a `card-grid` or `tree` node, or in `freeform`
  (`icon <name> <colour> at <placement>`). Rasterising needs the optional
  `cairosvg`; absent, icons are skipped and the run summary says so (mirrors the
  matplotlib chart fallback). Pure planners emit the icon element; `render.py`
  resolves it to a PNG after the lint clears its token colour.
- **A hierarchy/tree primitive (`Block: tree`).** An indented list (2-space =
  one level, `[icon]`/`!` prefixes) renders a tidy org chart / decomposition:
  token box nodes joined by one elbow connector per edge, deterministic layout,
  node cap 8 (6 with icons) and depth ≤3. Serves org charts, decomposition trees,
  and depth-1 mind maps from one routine.
- **A real brand type scale.** `tokens.type_scale` is now read from the template
  master's own title/body sizes (`pptxlib.read_type_scale`) instead of a generic
  default: a hero `display` above the title, then `h1`/`body`/`caption`,
  guaranteed monotonic, with a wholesale fallback to the generic scale when the
  master can't be read. So composed slides use the brand's real type.
- **A shape-language token.** `tokens.shape` (corner: rounded|sharp, hairline) is
  honoured by every box primitive instead of a hardcoded rounded rectangle;
  default stays rounded.
- **Ten new advisory rules** for tree and icon-list; `lint` now exempts 1-D lines
  (connectors/edges) from the overlap rule so tree edges route freely.

### Changed

- **Design philosophy is now in CLAUDE.md** — identity is the constraint,
  composition is the craft, extract identity not layout, no generated imagery,
  the lint is the only rigidity.
- `narrative` reaches for the fuller vocabulary (tree, icons, icon-list);
  composed slides without an explicit `tokens.type_scale` now use the
  brand-derived scale rather than the generic one (an intended enrichment, still
  lint-clean).

### Deferred (tracked in STATUS)

Logo capture (python-pptx cannot write pictures to masters, so it can't be
cleanly fixture-tested — a follow-up); `[icon]` on process/comparison; shape
auto-inference from template shapes.

## [0.7.0] - 2026-07-01

Boxes, not bullets. The `composed` role grows from one primitive to five and
learns to arrange them, so a deck can carry real designed compositions — card
grids, comparisons, processes, timelines — instead of headings over bullet
lists. Grounded in a committed evidence base drawn from the user's own decks and
the design canon. Back-compatible: the six fixed roles, `stat-row`, and existing
`brand.json` files are untouched.

### Added

- **Four new composed primitives, drawn as real boxes.** `card-grid` (3–5
  sibling panels), `comparison` (two panels that resolve to a winner),
  `process` (3–5 numbered steps joined by arrows — not a chevron ribbon), and
  `timeline` (dated milestones on a rail with one beat emphasised) join
  `stat-row`. `primitives.py` now draws filled shapes (cards, panels, steps,
  connectors, dots) from token colours, flat and shadow-free, with text layered
  on top. Every primitive is good by construction and grounded in the research.
- **Multi-block slides and explicit grid placement.** A composed slide takes up
  to four blocks: with no placement they stack top to bottom; or place each on a
  12×12 band grid with `at cols 1-6` / `at left` / `at top` / a quadrant. A
  leading `!` marks the one element that leads (hero card, winning panel, the
  turn).
- **A `freeform` composed block — compose anything the named shapes don't
  cover.** Place token-bound boxes, text, arrows, dots, and dividers on the grid
  to build a matrix, a quadrant, a node graph, or an annotated layout. Colours are
  role names and sizes scale names (never hex/pt), and every element passes the
  same mechanical lint — freedom in the arrangement, the guardrails held. The
  named primitives are reframed as a *palette*, not a taxonomy: `narrative` now
  teaches composing freeform (or describing a `Visual:`) rather than force-fitting
  an idea into the nearest shape — which would only swap bullet-slop for box-slop.
- **Advisory rules for every new primitive.** `composition.py` grows from 9 to
  20 rules — count bands (Cowan ~3–5), terseness, one-accent, the cliché
  guards (a comparison must resolve; a timeline needs a turn), and freeform's one
  guardrail (grey-push). `lint.review` now
  judges each block's family in isolation, so a multi-block slide is reviewed
  primitive by primitive with no cross-family false flags.
- **A committed design-research evidence base.** `presentation-craft/reference/
  design-research.md` records why the compositions are shaped as they are —
  the design system (hierarchy, type scale, imagery, colour, data display), the
  four primitives, the user's own vocabulary, and the myths kept out — cited to
  the user's decks (Powerful Presenting, Bluey, Telling Sticky Stories), the
  Visme *Non-Designer's Guide*, and the canon (Tufte, Cowan, Gestalt Common
  Region, WCAG/APCA, FT Visual Vocabulary, Okabe–Ito).

### Changed

- **`narrative` now reaches for compositions.** The authoring skill teaches
  matching each beat to its form and reaching for `layout: composed` — the
  root-cause fix for decks that came out as headings over bullets.
- The mechanical lint is shape-aware (box fills/strokes held to the token
  palette; overlap permitted only inside a declared `container`), and the
  element cap is 24 to admit the richest single primitive.

## [0.6.0] - 2026-06-30

A third way to build a slide: compose from brand-locked atoms, with an
evidence-cited sense of what good looks like. Two stacked slices — the
`composed` deck-spec role (token system + `stat_row` primitive + load-bearing
mechanical lint) and the advisory composition-quality layer over it. Fully
brand-agnostic and back-compatible: existing decks and `brand.json` files render
unchanged (the `tokens` key is optional; the six fixed roles are untouched).

### Added

- **A composition-quality layer: say what good looks like.** An evidence-cited,
  brand-agnostic advisory tier over composed slides. `composition.py` is a
  9-rule registry (hierarchy-ratio, stat-count, contrast/WCAG, value- and
  label-terseness, breathing-room, one-accent, no-decoration, emphasise-by-size)
  modelled on impeccable's rule-registry pattern; `lint.review` runs it and
  returns non-blocking findings (the existing `lint.check` system gate still
  hard-fails). The `stat_row` recipe now places at the optical centre and is
  good by construction — a default row trips no advisory. Every rule cites a
  source from a deep-research pass (Tufte, Duarte, Reynolds, Gestalt, WCAG 2.2,
  Cowan) reconciled with the user's own presentation decks; folklore (Dale's
  Cone, Mehrabian 7-38-55, 6×6, raw Miller 7±2, "60,000× faster") is
  deliberately excluded. Concreteness/story judgement is documented, not
  mechanised. See `presentation-craft/reference/composition.md`. Advisory by
  design (Bateman *Useful Junk?*: don't encode "maximise minimalism" as an
  absolute).
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
