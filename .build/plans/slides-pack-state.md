slug: slides-pack
base_ref: 2b661ae84a73996fbf338c8ee34d471485d8f300
phase: implement
task: Build the `slides` skill pack — 5 skills, cross-platform pipeline, python-pptx renderer, two-layer slop detector
started: 2026-05-16
last_updated: 2026-05-16
complexity: complex
requirements: [REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007]
decisions: [D-001, D-002, D-003, D-004, D-005, D-006, D-007, D-008, D-009, D-010, D-011, D-012]
assumptions_confirmed:
  - A-001 confirmed (python-pptx 1.0.2 installed; skill handles a miss gracefully)
  - A-002 confirmed (Node contributor-only; build repo install story verified)
  - A-003 confirmed (user statement: pack is brand-agnostic)
  - A-004 inferred (one brand profile per project; proceeding)
  - A-005 inferred (Codex discovery .agents/skills/ per build/HARNESSES.md; re-verify before release)
workstreams:
  - A pipeline-and-scaffold (T-010..T-019) — copy build pipeline, 3 repo-specific files, manifests, docs, tests
  - B source-review (T-040) — COMPLETE before workflow start (notes/source-review.md + approach.md + slop-detector.md)
  - D renderer (T-001, T-003, T-004, T-030..T-033) — python-pptx scripts, deck-spec grammar, fixtures, render tests
  - C skills (T-002, T-050..T-060) — 5 SKILL.md, 6 reference files, 4 opencode wrappers, 2 slop fixtures
  - E integrate-and-verify (T-070..T-073) — generated trees, automated checks, end-to-end smoke
execution_manifest:
  wave_0: [T-001, T-002, T-003, T-004] — validation scaffolding (fixtures, deck-spec grammar, failing render test)
  wave_1: [T-010..T-019 (A), T-030..T-033 (D)] — A and D in parallel; B (T-040) already done
  wave_2: [T-050, T-051, T-052, T-053, T-054, T-055, T-056, T-057, T-058, T-059, T-060] — C, after B and D
  wave_3: [T-070, T-071, T-072, T-073] — E integrate and verify
  notes: same-wave tasks share no files_modified; depends_on edges per the plan's execution_manifest YAML
completed_tasks: [T-040, T-001, T-002, T-003, T-004, T-010, T-011, T-012, T-013, T-014, T-015, T-016, T-017, T-018, T-019, T-030, T-031, T-032, T-033]
history:
  - 2026-05-16 — Workflow initialised. git init, base commit 2b661ae. Explored build/pm-skills/impeccable reference repos; python-pptx 1.0.2 installed. PLAN.md adopted verbatim as slides-pack-plan.md (T-040 marked complete — notes/ artifacts supersede the plan's draft craft guidance). Context and requirements artifacts written. Phase 1 (Plan) complete; advancing to Phase 2 (Review).
  - 2026-05-16 — Phase 2 (Review) complete. PASS — no critical findings. 4 important findings (I-001: T-016 must_haves need concrete test-port adaptations per file; I-002: Stress-test prose incorrectly lists check-sync.js as repo-agnostic; I-003: skill-contract.test.js needs vacuous-pass guard; I-004: stale Workflow artifacts section). 4 minor findings. user-invocable field spelling confirmed as 'user-invocable' (with 'c') from frontmatter.js. All REQs covered; manifest acyclic; notes files sufficient for T-051..T-055. Advancing to Phase 3 (Implement).
  - 2026-05-16 — Phase 3 Wave 0 complete (commit 6eba644). T-001..T-004 done: fixture template (11 layouts), deck-spec grammar, sample deck, clean/sloppy slop fixtures, test_render.py (8 tests, red by design). I-002/I-004 plan corrections applied. Build decision D-013 logged (render.py does not draw charts; Visual field → speaker notes).
  - 2026-05-16 — Phase 3 Wave 1 complete (commit 88a7a14). Workstream A (T-010..T-019) DONE_WITH_CONCERNS: pipeline ported (6 verbatim), 3 rewritten, manifests, docs, tests. Workstream D (T-030..T-033) DONE: renderer, 8/8 render tests pass. Worktree isolation unavailable (harness saw no git at startup) — agents ran in shared dir on disjoint files, orchestrator committed. Accepted concerns: source/commands/.gitkeep, builder.test.js .md-only leakage guard. Integrated checks: npm run build exit 0; npm test 35/44 (9 Wave-2-pending by design); test_render 8/8.
  - 2026-05-16 — Phase 3b mid-review (Sonnet) PROCEED. Verbatim copies confirmed byte-identical; 3 rewritten files correct; D-002 compliance clean; both accepted concerns sound; 9 test fails confirmed all Wave-2-pending (not bugs). Four low-severity Wave-2 notes: watch slop.md ≤190 lines; SKILL.md files carry the leakage-test burden (wrap $ARGUMENTS in claude-only, no bare /slides: in portable prose); source/commands/*.md description must match SKILL.md description; .gitkeep can stay. Dispatching Wave 2 (Workstream C).
