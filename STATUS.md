# Status

A snapshot of where the slides skill pack stands. Last updated 2026-06-26.

## Released

All on `main`, each git-tagged with a GitHub release (latest first):

| Version | What it added |
|---------|---------------|
| v0.5.0 | One-step brand onboarding: `init_brand.py` builds a complete `brand.json` (fonts, colours, and a heuristic `layout_map`) from a template or deck; `build-deck` and `narrative` offer it when `.slides/` is missing. |
| v0.4.0 | Brand extraction: `pptxlib.read_theme` (inverse of `apply_theme`) and `extract_brand.py` read a deck's theme fonts and colours; `teach-slides` pre-fills `brand.json` from a supplied deck. |
| v0.3.0 | AI-voice slop detection: `presentation-craft/reference/ai-voice.md` (the Claudism catalogue, vocabulary watchlist, assistant-artifact slop, uniform rhythm) as a third `slop-check` layer. |
| v0.2.0 | Native charts: `build-deck` draws bar, column, pie, scatter, and line charts from a `Chart:` block (matplotlib), placed on-brand; degrades to a `VISUAL TO ADD` note when matplotlib is absent. |
| v0.1.0 | Initial release: five skills, cross-harness pipeline, python-pptx renderer, two-layer slop detector. |

Automated gates at this snapshot: `python3 -m unittest discover tests` 59 passing, `npm test` 44 passing, `npm run check-sync` in sync.

## Owed before a fully human-verified release

These could not run in the build environment; each needs a human in Claude Code or desktop PowerPoint. The releases above shipped ahead of them by choice.

- [ ] Run the live arc once in Claude Code: `teach-slides` -> `narrative` -> `build-deck` -> `slop-check`. Confirm `teach-slides` writes a real `.slides/` and `narrative` pushes back on a one-line prompt. Exercise the v0.5.0 fast path: `init_brand.py` from a deck produces a renderable `.slides/brand.json`.
- [ ] Open a `build-deck`-rendered `.pptx` in **desktop PowerPoint**. Confirm it reads on-brand, with no strapline, ad copy, or sensational titles, and that `Chart:` slides' embedded pictures sit correctly. (Verified in-session via LibreOffice render, not PowerPoint.)
- [ ] Smoke-test one skill in **Codex** and one in **opencode** (`codex exec`, `opencode run`).
- [ ] Re-verify that Codex repo-local discovery is still `.agents/skills/` against current Codex docs.

## Deferred (next touch of those files)

- DEF-001: extract a `_render_chart_slide` helper from `build_deck` in `render.py` (the chart branch is long).
- DEF-002: promote `charts.py`'s recurring inline tuning constants (axis headroom, label offset, fill alpha, marker size, legend anchor) to named module constants.

## Unconfirmed

- LICENSE is assumed MIT.
- Graphic Continuum attribution wording in `data-viz.md`.

## Working on the repo

Edit `source/skills/`, never the generated output dirs. After any source change run `npm run build`, then the gate before pushing: `npm run check-sync && npm test && python3 -m unittest discover tests`. `matplotlib` is an optional dependency, needed only to draw chart slides.
