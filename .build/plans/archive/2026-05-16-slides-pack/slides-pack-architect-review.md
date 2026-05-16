# slides-pack — Architect Review

**Reviewer:** `/build:architect-review`
**Date:** 2026-05-16
**Review target:** `git diff 2b661ae84a73996fbf338c8ee34d471485d8f300 HEAD` (146 files, the whole build)
**Verify verdict carried in:** PARTIAL (all automated gates green; REQ-001/002 interactive behaviour environmental)

## Verdict: PASS_WITH_NOTES

The build delivers what the plan promised: a 5-skill cross-platform presentation pack, a python-pptx template-fill renderer, and a two-layer slop detector. Every gate re-run independently — `npm test` 44/44, `python3 -m unittest discover tests` 8/8, `npm run build` exit 0, `npm run check-sync` in sync with zero post-build drift, 5 manifests parse, 4 version carriers read `0.1.0`, leak scan clean. The 6 verbatim pipeline files are byte-identical to `build`. D-002 holds (no font/colour/coordinate literals in `pptxlib.py`/`render.py`). Plan fidelity high; the two documented deviations (D-013; the sixth `quote` role) are justified with a paper trail. All four Phase-2 review findings addressed.

## Findings (all Minor, none blocking)

- **[Minor] F1 — `render.py` silently mishandles an unknown spec field.** An unrecognised `Field:`-shaped line is not rejected; render.py's own docstring promises it never fails silently. Fix: warn or raise `SpecError` on an unrecognised field-shaped line. Low urgency — the slop detector catches a real `Strapline:` upstream and the structural guard (no text box outside placeholders) holds regardless.
- **[Minor] F2 — REQ-001/REQ-002 acceptance unverified.** The interactive `teach-slides` interview, the multi-turn `narrative` conversation, live Codex/opencode invocation, and opening a `.pptx` in desktop PowerPoint were not executed (not auto-runnable here). Environmental gaps, not defects. Fix: manual release-checklist run. Also re-verify A-005 (Codex discovery path).
- **[Minor] F3 — no negative-path tests for `render.py`.** The `SpecError` branches (slide-number gap, role/layout mismatch, missing brand keys, malformed JSON) are untested; `test_render.py` covers only the happy path. Fix: add `unittest` cases asserting non-zero exit and a named error.
- **[Minor] F4 — slop detection is LLM-judged, not deterministic.** Acceptable for a prompt-driven detector. Fix (optional): a lightweight grep-based fixture sanity test so a future fixture edit cannot silently remove the planted defects.

Nothing blocks shipping. The architecture is sound, verbatim-copy discipline exact, D-002 honoured, the pipeline produces clean in-sync output, deviations documented.

## Disposition by the orchestrator

- **F1, F3, F4 — addressed in a post-review polish pass** (commit after this review). F1: render.py raises `SpecError` on an unrecognised field-shaped line at a slide's top level (block-field prose untouched). F3: `tests/test_render.py` gains a negative-path test class. F4: `tests/test_fixtures.py` added — asserts the planted defects.
- **F2 — release-checklist item.** Carried forward; cannot be executed in this environment. Listed in the completion summary.
