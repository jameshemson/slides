# Status

A snapshot of where the slides skill pack stands. Last updated 2026-07-01.

## Released

All on `main`, each git-tagged with a GitHub release (latest first):

| Version | What it added |
|---------|---------------|
| v0.11.0 | Chart polish from real-usage feedback: a Chart `format:` (`$` / `%` / `$k` / `$m`, or `prefix:`/`suffix:`) formats value labels (`362` → `$362k`), large numbers abbreviate by default; long/many category labels rotate so they don't collide; the multi-series legend moved below the chart so it no longer crowds the slide title. |
| v0.10.0 | The render-back visual-QA loop — the lint *with eyes*. `raster.py` rasterises a rendered deck to per-slide PNGs (+ a contact sheet) so `build-deck` can look at it for the things geometry can't see (overflow, font fallback, clutter). Pluggable backend, none required: headless LibreOffice preferred, Keynote/macOS fallback (opt-in, opens the app), else a clear degrade. PDF→PNG via PyMuPDF/poppler; a `looks_blank` check + CLI. build-deck Step 4 runs it automatically on LibreOffice. |
| v0.9.0 | More diagram vocabulary + data→chart. `cycle` (3–6 stages on a ring) and `matrix` (a 2×2 of quadrants with optional axis captions). Icons on `process` and `comparison` items (completing icons across every block). A `Chart:` can read its data from a CSV (`data: file.csv`) — a spreadsheet exports straight to a chart, multiple series draw as grouped bars. Fixes a pre-existing charts.py bug where a second grouped series (or a de-emphasised bar) drew in paper/white; `muted` now falls back to grey, never paper. |
| v0.8.0 | A brand-constrained visual vocabulary. Icons (44 curated iconoir line icons, recoloured to a token colour, as an `icon-list`, a `[icon]` prefix on cards/tree, or in `freeform`; optional `cairosvg`, else skipped + noted). A hierarchy/`tree` primitive (indented list → tidy org chart / decomposition, elbow-connector edges, capped). The brand's **real type scale** read from the template master (`pptxlib.read_type_scale` → a hero display, monotonic, generic fallback) and a **shape-language** token (rounded/sharp), so composed slides read as the brand without copying its layouts. The Design philosophy is now in CLAUDE.md. Back-compatible; new tokens optional. |
| v0.7.0 | Boxes, not bullets. The `composed` role grows from one primitive to five — `card-grid`, `comparison`, `process`, `timeline` alongside `stat-row` — drawn as real filled boxes, plus a `freeform` block that places token-bound boxes/text/arrows on the grid for anything the named shapes don't cover. Multi-block slides stack or place on a 12×12 grid; the mechanical lint is shape-aware; `composition.py` grows to 20 advisory rules. `narrative` now reaches for compositions (the fix for decks that came out as headings over bullets), and a committed `design-research.md` records the evidence base (the user's own decks + the canon) so it can't be lost to a scratchpad again. |
| v0.6.0 | A third composition mode + an advisory composition-quality layer. A new `composed` deck-spec role composes brand-locked primitives (`stat_row`) on a token grid derived from the template, behind a load-bearing mechanical lint (`tokens.py`, `primitives.py`, `lint.py`). Over it, `composition.py` (a 9-rule registry) + `lint.review` say "what good looks like" as non-blocking advisories — evidence-cited (deep research over Tufte/Duarte/Reynolds/Gestalt/WCAG/Cowan, reconciled with real decks). Brand-agnostic and back-compatible: the `tokens` key is optional, the six fixed roles unchanged. |
| v0.5.0 | One-step brand onboarding: `init_brand.py` builds a complete `brand.json` (fonts, colours, and a heuristic `layout_map`) from a template or deck; `build-deck` and `narrative` offer it when `.slides/` is missing. |
| v0.4.0 | Brand extraction: `pptxlib.read_theme` (inverse of `apply_theme`) and `extract_brand.py` read a deck's theme fonts and colours; `teach-slides` pre-fills `brand.json` from a supplied deck. |
| v0.3.0 | AI-voice slop detection: `presentation-craft/reference/ai-voice.md` (the Claudism catalogue, vocabulary watchlist, assistant-artifact slop, uniform rhythm) as a third `slop-check` layer. |
| v0.2.0 | Native charts: `build-deck` draws bar, column, pie, scatter, and line charts from a `Chart:` block (matplotlib), placed on-brand; degrades to a `VISUAL TO ADD` note when matplotlib is absent. |
| v0.1.0 | Initial release: five skills, cross-harness pipeline, python-pptx renderer, two-layer slop detector. |

Automated gates at this snapshot: `python3 -m unittest discover tests` 254 passing, `npm test` 44 passing, `npm run check-sync` in sync. `cairosvg` and `matplotlib` are installed locally: the icon raster path is verified (icons recolour to the brand accent and rasterise crisply) and the multi-series grouped-bar chart is verified visually (Revenue accent + Cost grey). On a machine without `cairosvg`, icons degrade to a note (as designed).

The render-back visual-QA loop (v0.10.0) is scaffold-only in this environment: no
rasteriser was installed. Its testable parts (backend detection, degradation,
PDF→PNG, the blank check, contact sheet) pass; the `.pptx`→PDF step needs an
external app (LibreOffice or Keynote) and is verified manually, not in CI. To
enable the automatic headless render-back review: `brew install --cask
libreoffice`. The Keynote backend works on macOS but opens the app, so build-deck
runs it only if the user asks.

Visual-vocabulary follow-ups deferred by design (v0.8.0): **logo capture** —
python-pptx cannot write pictures to a master/layout, so a positive fixture/test
can't be built cleanly and detect-only is low value; `[icon]` on process and
comparison items (it lands in freeform, icon-list, card, and tree); shape
**auto-inference** from the template's own shapes (the `shape` token defaults +
explicit override ship now). Icons need the optional `cairosvg` to rasterise,
like `matplotlib` for charts.

Composed mode follow-ups shipped in v0.7.0: four more primitives, a `freeform`
block, explicit grid placement (`Block: … at cols/rows`), stacking several blocks
per slide, and a shape-aware lint. Still deferred by design: further primitives
(table, funnel); the render-to-PNG vision loop (a pluggable rasteriser — local
PowerPoint/Keynote if present, else LibreOffice headless, else degrade to the
note); wiring the composition rules into `slop-check`; region-aware
breathing-room and small-number contrast. Concreteness stays doc-only (authored
judgement, not a mechanical test).

## Owed before a fully human-verified release

These could not run in the build environment; each needs a human in Claude Code or desktop PowerPoint. The releases above shipped ahead of them by choice.

- [ ] Run the live arc once in Claude Code: `teach-slides` -> `narrative` -> `build-deck` -> `slop-check`. Confirm `teach-slides` writes a real `.slides/` and `narrative` pushes back on a one-line prompt. Exercise the v0.5.0 fast path: `init_brand.py` from a deck produces a renderable `.slides/brand.json`.
- [ ] Open a `build-deck`-rendered `.pptx` in **desktop PowerPoint**. Confirm it reads on-brand, with no strapline, ad copy, or sensational titles, and that `Chart:` slides' embedded pictures sit correctly. (Verified in-session via LibreOffice render, not PowerPoint.)
- [ ] Smoke-test one skill in **Codex** and one in **opencode** (`codex exec`, `opencode run`).
- [ ] Re-verify that Codex repo-local discovery is still `.agents/skills/` against current Codex docs.
- [ ] **Eyeball a `composed` stat-row slide** rendered from a real template against a placeholder-filled slide from the same template (open in any viewer — PowerPoint, Keynote, or a LibreOffice/Keynote PNG export; no specific tool required). The lint guarantees on-brand-by-tokens, not beautiful; confirm the composed slide sits in the template's own rhythm and reads as the same deck. (The automated test confirms the row aligns to the derived margins; the eye confirms it looks right.) While there, confirm the **advisory composition notes read as helpful, not noisy** on a real deck.
- [ ] **Eyeball the v0.7.0 primitives** — `card-grid`, `comparison`, `process`, `timeline`, and a `freeform` slide — rendered from a real template. Confirm the boxes read on-brand and the compositions look intentional, not templated (the lint proves on-brand, not well-composed, especially for `freeform`). Confirm `narrative` actually reaches for a composition (and `freeform` when an idea fits none of the five) rather than defaulting to bullets.
- [ ] **Eyeball the v0.8.0 vocabulary** with `cairosvg` installed: a `tree`, an `icon-list`, and a card/tree with a `[icon]` — confirm the icons recolour to the brand accent and sit crisply, the tree reads as an org chart, and the brand-derived type scale looks right (composed slides should feel like the brand). The raster path is skip-guarded in tests; this is the human confirmation.

## Deferred (next touch of those files)

- DEF-001: extract a `_render_chart_slide` helper from `build_deck` in `render.py` (the chart branch is long).
- DEF-002: promote `charts.py`'s recurring inline tuning constants (axis headroom, label offset, fill alpha, marker size, legend anchor) to named module constants.

## Unconfirmed

- LICENSE is assumed MIT.
- Graphic Continuum attribution wording in `data-viz.md`.

## Working on the repo

Edit `source/skills/`, never the generated output dirs. After any source change run `npm run build`, then the gate before pushing: `npm run check-sync && npm test && python3 -m unittest discover tests`. `matplotlib` is an optional dependency, needed only to draw chart slides.
