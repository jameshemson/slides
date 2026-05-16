# slides-pack — Phase 2 Review

**Reviewer:** `/build:review-plan` (skeptical senior-engineer gate)
**Reviewed:** 2026-05-16
**Verdict:** PASS — no critical (blocker-severity) findings. Four important findings, all fixable before or during implementation without replanning the architecture. Phase advances to `implement`.

---

## Verified claims from reference repos

Before the plan findings, the following load-bearing claims were verified against the actual source files.

### `user-invocable` field spelling — CONFIRMED

`build`'s `scripts/transformers/frontmatter.js` `CLAUDE_ONLY_FIELDS` set (lines 8–15) spells the field:

```js
const CLAUDE_ONLY_FIELDS = new Set([
  'user-invocable',   // ← with a 'c', NOT 'user-invokable' with a 'k'
  'argument-hint',
  'model',
  'effort',
  'context',
  'allowed-tools',
]);
```

**The correct spelling is `user-invocable`.** The context file's warning that `pm-skills` uses `user-invokable` (with a 'k') was accurate. All slides `SKILL.md` command files must use `user-invocable` or the field leaks into Codex/opencode output.

### Repo-agnostic vs repo-specific split — PARTIALLY CONFIRMED with one discrepancy

- `build.js`, `utils.js`, `transform.js`, `builder.js`, `frontmatter.js` — confirmed repo-agnostic (no provider-specific or path-specific content). Copy verbatim: correct.
- `body-rewrites.js` line 21: `/\/build:([\w-]+)/g` — confirmed. Plan's instruction to rewrite to `/\/slides:([\w-]+)/g` is correct.
- `providers.js` — confirmed: non-Claude providers all carry `exclude: ['build', 'eval']`. Plan's `exclude: []` for all slides providers is correct.
- `version-carriers.js` — confirmed: carrier 3 is `plugins/build/.codex-plugin/plugin.json`. Plan correctly renames to `plugins/slides/.codex-plugin/plugin.json`.
- **`check-sync.js` — repo-specific, not repo-agnostic.** `check-sync.js` imports `{ PROVIDERS, COMMAND_PROVIDERS }` from `./transformers/providers.js` and iterates `PROVIDERS.outputDir` values. It is NOT a verbatim copy — see finding I-002.

### Notes files — SUFFICIENT for T-051..T-055

`notes/source-review.md`, `notes/approach.md`, and `notes/slop-detector.md` were read. All three exist and contain substantive, principle-only craft content:

- `source-review.md` (161 lines): complete section per source file, including visual pass results, 8 logged decisions, anti-pattern catalogue, and emotion-line decision.
- `approach.md` (83 lines): distilled Plan/Create/Deliver method, visual-craft principles, data/chart/diagram guidance, and the slop line — principle-only, no named examples.
- `slop-detector.md` (97 lines): two-layer detector spec (presentation slop + prose slop from `stop-slop`), banned-phrase list, banned-structure list, quick checks, 5-dimension scoring rubric.

Collectively sufficient to write `narrative.md`, `slides.md`, `data-viz.md`, `delivery.md`, and `slop.md` without re-distilling source files. T-040 is legitimately complete.

### Execution manifest — wave conflicts, acyclicity, REQ coverage

- **Same-wave file conflicts:** checked per wave. None found. Wave 0: T-001/T-002/T-003 have no file overlap; T-004 (test_render.py) has no overlap with others. Wave 1: 13 tasks across A and D share no `files_modified`. Wave 2: 11 tasks, each owns distinct skill/reference files. Wave 3: T-070 is build output (generated trees), T-071/T-072/T-073 modify no files.
- **Acyclicity:** `depends_on` edges form a DAG. Wave 0 → Wave 1 → Wave 2 → Wave 3 ordering is topologically consistent. No cycles found.
- **REQ coverage:** REQ-001 → T-031/032/056; REQ-002 → T-057; REQ-003 → T-001/003/004/030-033/058; REQ-004 → T-002/051/059 + embedded in 057/058; REQ-005 → T-040/052-055; REQ-006 → T-010-019/070/071/073; REQ-007 → T-018/019/070. All 7 requirements covered.

---

## Placeholder scan

Zero violations. No "TBD", no "handle appropriately", no "follow existing patterns" without naming the pattern. The only genuinely deferred content (craft reference files) is backed by T-040 producing concrete notes artifacts. The self-review's "Pass" on this is correct.

---

## Findings by severity

### Critical (blocker)

None.

---

### Important

**[I-001] T-016 `must_haves` are insufficient to guide the test-port work**

Severity: Important. Will produce subtly wrong tests that technically pass but miss slides-specific adaptations.

T-016 covers porting four test files (`builder.test.js`, `transform.test.js`, `manifests.test.js`, `check-sync.test.js`). The `must_haves` only mention "no `$ARGUMENTS`/`/slides:` literal leaks" and "4 carriers share one version". But the `build` originals contain deeply hardcoded strings that must all change:

- `builder.test.js` — byte-equality test hardcodes skill names `['architect-review', 'impl-plan', 'review-plan', 'verify']` and path `plugins/build/skills`. These must become `['build-deck', 'narrative', 'slop-check', 'teach-slides']` and `plugins/slides/skills`. The command-file count assertion also hardcodes 4 from `.opencode/commands/`.
- `manifests.test.js` — hardcodes `plugin.name === 'build'`, `codexPluginPath = 'plugins/build/.codex-plugin/plugin.json'`, `codexSkillsDir = 'plugins/build/skills'`, `PORTABLE_SKILLS = ['architect-review', ...]`. The `source/commands` parity test filters on `['build', 'eval']` which must change to `['presentation-craft']`.
- `check-sync.test.js` — hardcodes `plugins/build/.codex-plugin/plugin.json`; must become `plugins/slides/.codex-plugin/plugin.json`.
- `transform.test.js` — SAMPLE fixture uses `/build:impl-plan` and `/build:review-plan`; under slides' `body-rewrites.js` these will not be rewritten, so the rewrite tests will fail or pass vacuously unless the fixture uses `/slides:` references.

**Fix required before T-016 starts:** Expand T-016 `must_haves` to name each required adaptation per file. At minimum add: "byte-equality test in `builder.test.js` uses `['build-deck','narrative','slop-check','teach-slides']` and `plugins/slides/skills`"; "`manifests.test.js` asserts `plugin.name === 'slides'` and `PORTABLE_SKILLS` is the 4 invocable slides skills"; "`check-sync.test.js` references `plugins/slides/.codex-plugin/plugin.json`"; "`transform.test.js` SAMPLE uses `/slides:build-deck` not `/build:`".

---

**[I-002] Stress-test prose falsely lists `check-sync.js` as repo-agnostic**

Severity: Important. Will confuse the Wave 1 implementor when they discover T-011 omits `check-sync.js` and T-015 covers it separately.

The Stress-test section (under Approach) states: "`transform.js`, `builder.js`, `frontmatter.js`, `utils.js`, `build.js`, and `check-sync.js` are repo-agnostic (verified by reading them)."

This is false for `check-sync.js`. The file imports `{ PROVIDERS, COMMAND_PROVIDERS }` from `./transformers/providers.js` and iterates output directories — it is repo-specific. The execution manifest handles this correctly (T-011 omits it; T-015 says "copy of build's check-sync.js, importing the slides providers and version-carriers"). The prose and the manifest contradict each other. An implementor following the Stress-test description will attempt a verbatim copy of `check-sync.js` and get a build that references `build`'s provider paths.

**Fix:** Remove `check-sync.js` from the Stress-test's "repo-agnostic" list. Add: "(check-sync.js imports providers.js and is repo-specific — handled in T-015)."

---

**[I-003] `skill-contract.test.js` will pass vacuously in Wave 1 when `source/skills/` is empty**

Severity: Important (silent false-positive hiding a test bug).

`skill-contract.test.js` (T-017) validates frontmatter and line ceilings on every `SKILL.md`. In Wave 1 there are no `SKILL.md` files. If the test uses a glob (e.g. `glob('source/skills/*/SKILL.md')`), an empty result means the loop body never runs — the test passes with zero assertions made, offering no signal that the test itself is correctly written. The bug only becomes visible in Wave 2 when skill files exist.

**Fix:** T-017 `must_haves` should include: "when run against an empty `source/skills/` directory, the test throws/fails with a clear message (e.g. 'no SKILL.md files found — is this the right directory?') rather than passing vacuously." This guards against a silent mis-implementation of the glob.

---

**[I-004] The `## Workflow artifacts` section at the bottom of the plan is stale ("N/A — standalone plan")**

Severity: Important (wrong information in a section a Phase 3 implementor will read).

The plan contains two coverage points for workflow artifacts: a correct one in the "Status and immediate next step" block (Phase 1–4 artifact map) and a stale one in the required `## Workflow artifacts` section at the end, which says "N/A — standalone plan" and references a now-obsolete path at `/Users/jameshemson/.claude/plans/`. The plan was adopted verbatim into the `/build` workflow, so the "standalone plan" description is no longer accurate. The self-review's "Pass" on this section is therefore incorrect.

**Fix:** Replace the body of `## Workflow artifacts` with the Phase 1–4 artifact map already present in the Status block. Remove the stale "standalone plan" paragraph and the obsolete path.

---

### Minor

**[M-001] T-016 and T-017 have a parallelism hazard in Wave 1**

T-016 and T-017 are both Wave 1 with no ordering constraint between them. T-016's `verify: "npm test"` runs all tests including T-017's `skill-contract.test.js`. If T-016's verify runs before T-017 is complete, `npm test` may encounter a partially-written or absent `skill-contract.test.js`. Not a file conflict (different files) but a verify-step ordering hazard.

**Fix:** Either T-016 `depends_on: ["T-017"]`, or scope T-016's verify command to its own four test files only, saving the full `npm test` for T-071.

---

**[M-002] T-010 and T-018 verify commands use `require()` which fails in ESM context on Node < 22**

T-010 verify: `node -e "const p=require('./package.json');..."` and T-018 uses `require('fs')`. With `type: module` in `package.json`, `require()` in `node -e` throws `ERR_REQUIRE_ESM` on Node < 22. The dev machine runs Node 25 so this works, but the verify commands are also documentation for contributors and will mislead a contributor on an older Node.

**Fix (low urgency given Node 25):** Replace with `import()` equivalents or add a note that Node >= 22 is required. The plan's dependencies section already notes "Node.js, no version pin beyond ES modules support" — pin to >= 22 to be safe.

---

**[M-003] Line ceilings in T-017 exceed reference targets without justification**

T-017 sets ceilings: `presentation-craft ≤ 210`, `command skills ≤ 170`, `reference files ≤ 190`. These are higher than the build/pm-skills convention (reference files target 80–150). The plan offers no rationale. `slop.md` in particular (a full taxonomy with banned phrases and structures) is likely to hit 190 and still be thin.

**Fix:** Document why these ceilings differ from the reference targets, and consider whether `slop.md` should have a higher or separate ceiling. If content genuinely requires it, justify it in T-017 `must_haves`.

---

**[M-004] T-070 `files_modified` lists directories, not files**

T-070 lists `.claude/skills`, `.opencode/skills`, etc. as `files_modified`. These are bulk-generated output trees, so this is pragmatic, but it means any tooling that reads `files_modified` to route work cannot identify individual generated files. Acceptable as-is; noted for any future automation.

---

## REQ/D/A coverage assessment

| Item | Status | Notes |
|------|--------|-------|
| REQ-001 | Covered | T-031, T-032, T-056 |
| REQ-002 | Covered | T-057 |
| REQ-003 | Covered | T-001, T-003, T-004, T-030–T-033, T-058 |
| REQ-004 | Covered | T-002, T-051, T-059 + embedded in T-057/T-058 |
| REQ-005 | Covered | T-040 (complete), T-052–T-055 |
| REQ-006 | Covered | T-010–T-019, T-070, T-071, T-073 |
| REQ-007 | Covered | T-018, T-019, T-070 |
| D-001–D-012 | All realised | Decisions map to tasks per plan self-review |
| A-001–A-005 | All documented | Mitigations adequate for all medium/inferred assumptions |

---

## Test-quality assessment

- `test_render.py` assertions (slide count, layout mapping, placeholder text, absence of non-placeholder text boxes) are substantive and behaviorally meaningful. Not weak.
- `slop-check` fixture test (T-072) is LLM-judged and therefore non-deterministic, but the fixture-planting approach (five named defects) provides adequate determinism for the detection claims.
- `skill-contract.test.js` passes vacuously in Wave 1 — flagged I-003.
- `builder.test.js` byte-equality test will pass vacuously or incorrectly if T-016 `must_haves` are not expanded — flagged I-001. This is the highest-risk test gap.

---

## Architecture assessment

The architecture is sound. The template-fill approach via python-pptx is the only viable choice for real `.pptx` output. Copying the `build` pipeline rather than re-inventing it is the right call. Separating `narrative` from `build-deck` (multi-turn spitball cannot race to generation) is well-justified. The slop detector being baked in at generation time, not only as a post-hoc checker, is the right shape for the problem.

The highest-risk non-code area is the craft reference files: they must be distilled enough to be readable, specific enough to be actionable, and short enough to stay within line ceilings — a subjective balance. The notes are excellent raw material; the T-052–T-055 tasks are the implementation's centre of gravity for quality.

---

## Summary

**Verdict: PASS — advance to implement.**

No critical findings. Four important findings: I-001 (expand T-016 `must_haves` with concrete test-port adaptations — do this before implementation starts) and I-002 (fix the Stress-test prose about `check-sync.js`) are the highest-priority fixes. I-003 (vacuous-pass guard in `skill-contract.test.js`) and I-004 (stale `## Workflow artifacts` section) are lower-friction document corrections that can be addressed at the start of implementation.

The plan is coherent, placeholder-free, and structurally sound. The execution manifest is acyclic with no same-wave file conflicts and complete REQ coverage. The notes files are sufficient to write the reference files without re-distilling source material. Proceed.
