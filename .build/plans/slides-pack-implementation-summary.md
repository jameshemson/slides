# slides-pack — implementation summary

Living record of Phase 3. Updated per wave.

## Build decisions taken during implementation

- **D-013 — v1 render.py does not draw charts or images.** The canonical execution manifest has no chart-rendering task: T-033 scopes render.py to "fills only template placeholders"; T-032 lists only text layouts; `test_render.py` asserts text placeholders only. Drawing a chart via `add_chart` requires code-set coordinates, which D-002 forbids. So a slide's chart/image/diagram is expressed with an optional `Visual:` field carrying a plain-language description; render.py records it in the slide's speaker notes prefixed `VISUAL TO ADD:`. `data-viz.md` still teaches full chart selection as craft. Resolves an inconsistency between the plan's prose ("renders native chart types") and its manifest (no such task) in favour of the manifest. Native chart-placeholder rendering is documented future work.
- The deck-spec grammar (T-003) defines **six** semantic roles: `title`, `section`, `statement`, `title-content`, `two-column`, `quote`. The plan named five "etc."; `quote` was added (the source review calls out quote/statement typographic treatment as core craft). `quote` shares the `section` layout where a template has no dedicated quote layout.

## Wave 0 — validation scaffolding — COMPLETE (committed 6eba644)

| Task | Files | Result |
|------|-------|--------|
| T-001 | `tests/generate-fixture-template.py`, `tests/fixtures/sample-template.pptx` | Script regenerates the fixture deterministically; template exposes 11 named layouts (≥4 required). Layouts 0/1/2/3/5 renamed to role names. |
| T-003 | `source/skills/presentation-craft/reference/deck-spec.md`, `tests/fixtures/sample-deck.md` | Grammar fully specified: frontmatter + `## Slide N` + `layout:` role + labelled fields + `Visual:`/`Notes:`. brand.json schema documented. sample-deck.md conforms, exercises all 6 roles. |
| T-002 | `source/skills/slop-check/fixtures/{clean,sloppy}-deck.md` | sloppy-deck.md carries all 5 planted defects (verified: 2 em dashes, 1 `Strapline:` field, 7-bullet slide, sensational title, ad-copy lines). clean-deck.md carries none (0 em dashes). |
| T-004 | `tests/test_render.py` | 8 stdlib-unittest assertions (exit code, reopen, slide count, layout mapping, title fill, body fill, Visual→notes, no text outside placeholders). Fails by design — 8 failures, render.py absent. |

Wave 0 verification: `python3 tests/generate-fixture-template.py` → 11 layouts; `python3 -m unittest tests.test_render` → 8 failures (expected, render.py absent).

## Wave 1 — Workstreams A (pipeline) + D (renderer) — COMPLETE (committed 88a7a14)

Two parallel opus agents in the shared dir (worktree isolation unavailable — harness saw no git repo at startup; agents touched disjoint file sets; orchestrator committed).

**Workstream A (T-010..T-019) — DONE_WITH_CONCERNS.** 25 files: 6 verbatim pipeline copies (build.js, check-sync.js, utils/transform/builder/frontmatter.js — confirmed byte-identical to `build`); 3 rewritten (body-rewrites.js `/slides:`, providers.js 5 trees + `exclude:[]`, version-carriers.js 4 carriers); package.json; 4 manifests (`0.1.0`); 5 repo docs (AGENTS.md symlink→CLAUDE.md); 4 ported transformer tests + new skill-contract.test.js. `npm run build` exits 0. `npm test` 35/44 pass — the 9 fails are all Wave-2-pending (no SKILL.md / no `source/commands/*.md` yet) and written for the final 5-skill/4-command tree, not weakened. skill-contract.test.js's vacuous-pass guard fires correctly (I-003 satisfied).
- Concern accepted: A created `source/commands/.gitkeep` because the verbatim `builder.js`'s `buildCommandProvider` does `readdirSync('source/commands')` and ENOENTs on a missing dir. Wave 2 adds the 4 wrappers and may delete `.gitkeep`.
- Concern accepted: A added `if (!file.endsWith('.md')) continue;` to builder.test.js's real-tree leakage scan, because slides' `source/skills/` carries non-`.md` files (`build-deck/scripts/*.py`, `slop-check/fixtures/`). Reasonable; flag for architect review.

**Workstream D (T-030..T-033) — DONE.** 4 files under `source/skills/build-deck/scripts/`: pptxlib.py (5 helpers `load_template`/`list_layouts`/`resolve_role`/`fill_placeholders`/`apply_theme`, zero font/colour/coordinate literals — confirmed by literal scan), inspect_template.py, make_template.py, render.py. All 8 `tests.test_render` pass. inspect_template + make_template verify green.
- python-pptx workarounds: (1) `slide.shapes.title` returns a fresh wrapper per access → `fill_placeholders` keys placeholders by `placeholder_format.idx`, lowest-idx content placeholder = title target; (2) theme part has no element graph → `apply_theme` rewrites `theme_part.blob` via lxml directly.
- For Wave 2: `render.py --spec --brand --out` (template path comes from brand.json, no `--template`). brand.json needs `template`/`fonts`/`colours`/`layout_map`. On malformed input render.py prints `error: ...` naming the slide/role/key and exits 1, writing nothing. inspect_template.py prints `{template, layouts:[{index,name,placeholders:[{idx,type}]}]}`. The `quote` role has no dedicated layout — map it to the `section` layout. teach-slides must pick layout indices with enough content placeholders for each role (title/title-content/two-column/quote need 2-3, section/statement need 1).

Wave 1 integrated verification (orchestrator, commit 88a7a14): `npm run build` exit 0; `npm test` 35 pass / 9 fail (Wave-2-pending); `python3 -m unittest tests.test_render` 8/8 OK. Generated output trees left untracked until T-070.

## Wave 2 — Workstream C — pending

## Wave 3 — Workstream E — pending
