# slides-pack — requirements

Canonical `REQ-*`, `D-*`, `A-*` inventory with acceptance criteria and `must_haves`. Lifted from `slides-pack-plan.md`; the plan's execution manifest is the task-level authority.

## Requirements

- **REQ-001** Capture the installing user's brand once, up front, via a `teach`-style skill (template / fonts / colours / logo / audience / voice / context). Persist for reuse. Brand-agnostic.
  - Acceptance: running `teach-slides` writes `.slides/context.md`, `.slides/brand.json`, `.slides/template.pptx`. Tasks: T-031, T-032, T-056.
- **REQ-002** Help the user craft a narrative through genuine multi-turn back-and-forth before any slide exists; push back on vague input; resist jumping to slides.
  - Acceptance: `narrative` given a one-line prompt asks discovery questions instead of generating a deck spec. Task: T-057.
- **REQ-003** Build real, editable `.pptx` files by filling the user's template's own layouts/placeholders; never set fonts/colours/coordinates in code.
  - Acceptance: `test_render.py` passes — slide count matches spec, each slide uses the mapped layout, placeholder text matches, NO text box exists outside template placeholders. Tasks: T-001, T-003, T-004, T-030..T-033, T-058.
- **REQ-004** A slop detector catching presentation slop pre- and post-generation. Must specifically catch: bottom straplines/taglines, sensationalising, ad-copy voice, title-restates-body, bullet soup, plus the wider taxonomy. Embedded in `narrative` + `build-deck`; standalone as `slop-check`.
  - Acceptance: `slop-check` flags every planted defect in `sloppy-deck.md` and returns zero high-severity findings on `clean-deck.md`. Tasks: T-002, T-051, T-059.
- **REQ-005** Slide-writing craft distilled from the source set, into `presentation-craft/reference/` files, via collaborative review (not solo distillation).
  - Acceptance: `notes/source-review.md` exists with a section per source file + the chart, each naming principles and a target reference doc. **T-040 already COMPLETE** — see `notes/{source-review,approach,slop-detector}.md`. Tasks: T-052..T-055.
- **REQ-006** Runs on Claude Code, Codex, opencode from a single `source/` tree via the cross-platform pipeline copied from `build`. UI out of scope.
  - Acceptance: `npm run build` exits 0 emitting 6 output trees; `npm run check-sync` exits 0 clean; no literal `$ARGUMENTS` / `/slides:` under non-Claude trees. Tasks: T-010..T-019, T-070, T-071, T-073.
- **REQ-007** Packaged as an installable plugin for all three harnesses (Claude marketplace, Codex marketplace, opencode bundle).
  - Acceptance: 4 manifests parse as JSON and carry an identical version; `check-sync` enforces parity. Tasks: T-018, T-019, T-070.

## Decisions

- **D-001** Five skills: `presentation-craft` (core, non-invocable), `teach-slides`, `narrative`, `build-deck`, `slop-check`.
- **D-002** `.pptx` via template-fill with python-pptx; Claude's judgement → content + layout choice, never geometry.
- **D-003** Cross-platform pipeline copied from `build`; `source/skills/` single source of truth; output committed to `.claude/`, `.opencode/`, `.agents/`, `plugins/slides/`, `.codex/`.
- **D-004** All 5 skills portable; `providers.js` `exclude: []` everywhere; AskUserQuestion guidance wrapped in `<!-- claude-only -->`.
- **D-005** Brand context in `.slides/`: `context.md` + `brand.json` + `template.pptx`.
- **D-006** `narrative`→`build-deck` contract is a markdown deck spec with a defined per-slide grammar (`## Slide N`, `layout:` role, labelled fields).
- **D-007** Slop detector lives in `presentation-craft`: pre-gen Reflex Rejection, post-gen Deck Slop Test, Slide Slop Taxonomy, match-and-refuse bans.
- **D-008** Source distillation is collaborative; no autonomous agent re-distils. (T-040 already done — agents transcribe the notes, they do not re-distil.)
- **D-009** `presentation-craft/reference/`: `narrative.md`, `slides.md`, `data-viz.md`, `delivery.md`, `slop.md`, `deck-spec.md`.
- **D-010** No orchestrator skill in v1 (would be Claude-only, breaks REQ-006). Skills chain via "What's Next" pointers.
- **D-011** python-pptx scripts live in `build-deck/scripts/`; `teach-slides` calls them via `../build-deck/scripts/`.
- **D-012** Graphic Continuum encoded in `data-viz.md` as a taxonomy with attribution to Schwabish & Ribecca; the poster image is not redistributed.

## Assumptions

- **A-001** (med-high) python3 available on the end-user machine; the skill handles a miss gracefully with a `pip install` prompt. Confirmed for the dev box.
- **A-002** (high) Node only needed by contributors regenerating output; end users consume committed trees.
- **A-003** (high) The 8 source files are universal craft material, not brand assets.
- **A-004** (med) One brand profile per project. Inferred — proceeding with it.
- **A-005** (med) Codex repo-local discovery is `.agents/skills/`; re-verify before release.

## must_haves (cross-cutting, every task inherits the relevant ones)

- Template-fill renderer sets no font/colour/coordinate literals — all read from `brand.json` or the template.
- No text box outside the template's placeholders in any generated `.pptx` (structural guard against an injected strapline).
- The slop detector returns severity-ranked findings, not a binary pass/fail.
- Craft reference files are principle-only — no named examples ship.
- `exclude: []` for every provider; no `$ARGUMENTS` or `/slides:` literal leaks into non-Claude output trees.
- The 4 version-carrying manifests share one identical version string.
- Every `SKILL.md` carries `name` + `description` frontmatter and respects its line ceiling.
- Tests are written and passing for every workstream that produces code.
