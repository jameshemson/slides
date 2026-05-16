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

## Wave 1 — Workstreams A (pipeline) + D (renderer) — IN PROGRESS

Dispatched as two parallel opus agents in isolated worktrees. A = T-010..T-019 (pipeline, scaffold, manifests, docs, transformer tests). D = T-030..T-033 (pptxlib.py, inspect_template.py, make_template.py, render.py).

## Wave 2 — Workstream C — pending

## Wave 3 — Workstream E — pending
