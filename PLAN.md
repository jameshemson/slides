# Implementation Plan: `slides` skill pack

## Context

James used to be a presentation-skills practitioner and teacher and has a corpus of source material (8 PPTX/PDF files plus the Graphic Continuum chart) that captured his craft. He wants that craft turned into a shareable skill pack, modelled on `pbakaus/impeccable` and his own `pm-skills` and `build` repos, that helps anyone (not just him) go from nothing to a finished, on-brand, slop-free PowerPoint deck.

The pack must cover the whole arc, not just file generation: capture the installing user's brand up front, spitball a narrative back-and-forth before any slides exist, build the actual `.pptx`, and police the output with a slop detector tuned to the specific failure modes Claude exhibits with slides (straplines at the bottom of slides, sensationalising, ad-copy voice). It must run on Claude Code, Codex, and opencode. The repo lives at `/Users/jameshemson/repos/slides` (currently empty, not a git repo).

Four product decisions were confirmed with the user before planning: output is **PowerPoint `.pptx`**; portability **copies the `build` repo's cross-platform pipeline**; the UI is **deprioritised**; the source files are **reviewed collaboratively, not distilled solo**. Three structural decisions were then confirmed: a **series of skills** (not one skill with modes); `.pptx` is produced by **filling a real template** via python-pptx; and the skill is **brand-agnostic**, so each installing user sets up their own template/fonts/colours in a `teach`-style skill and the pack builds in that style.

---

## Status and immediate next step

This plan is a **draft pending the source-material assessment**. Before any implementation, James and Claude review the 8 source files (the storytelling, presenting, and visual-communication PPTX/PDF files) and the Graphic Continuum chart together, the activity formalised as task T-040. That assessment is the authority on the craft content and may revise this plan: the `presentation-craft` reference-file set (D-009), the Slide Slop Taxonomy in `slop.md`, the distilled narrative method, and the data-viz guidance can all change once the material is actually read and discussed. Implementation (Workstreams A, C, D, E) does not begin until the assessment is done and this plan is updated to reflect it. **The source-material assessment is the next action.**

---

## Discovery level

**`deep_dive`.** Evidence: net-new repo (empty directory, not under git); cross-cutting (5 skills + a Node build pipeline + a Python renderer + 4 hand-authored manifests across 6 generated output trees); ambiguous content (the craft references depend on a collaborative review session that has not happened); a real new runtime dependency (python-pptx); and the dominant requirement is qualitative (output must not look like AI slop), which needs a designed-in detector rather than a code check.

---

## Requirements and decisions

### Requirements

- **REQ-001** Capture the installing user's brand once, up front, via a `teach`-style skill: template (have one / build one / reuse an existing deck), fonts, colours, logo, audience, voice, presenting context. Persist it for reuse. The pack is brand-agnostic: it works for any user's brand, not James's.
- **REQ-002** Help the user craft a narrative through genuine multi-turn back-and-forth before any slide exists. The skill must push back on vague input and resist jumping to slides.
- **REQ-003** Build real, editable `.pptx` files in the user's brand style by filling the user's template's own slide layouts and placeholders (never setting fonts, colours, or coordinates in code).
- **REQ-004** A slop detector that catches presentation slop, both pre-generation (reflex rejection) and post-generation (a checklist). It must specifically catch: straplines/taglines at the bottom of a slide, sensationalising, ad-copy voice, title-restates-body, bullet soup, and the wider taxonomy. Embedded in `narrative` and `build-deck`, and available standalone as `slop-check`.
- **REQ-005** Slide-writing craft distilled from James's 8 source files plus the Graphic Continuum, into the `presentation-craft` core skill's reference files, via a collaborative review with James (not solo distillation).
- **REQ-006** Runs on Claude Code, Codex, and opencode from a single source tree, using the cross-platform build pipeline copied from the `build` repo. UI is out of scope.
- **REQ-007** Packaged as an installable plugin for all three harnesses (Claude marketplace, Codex marketplace, opencode bundle), matching `build`/`pm-skills`/`impeccable`.

### Decisions

- **D-001** Five skills: `presentation-craft` (core knowledge, not user-invocable), `teach-slides`, `narrative`, `build-deck`, `slop-check`. Series-of-skills layout (user-chosen), modelled on `pm-skills` (core + commands).
- **D-002** `.pptx` is produced by template-fill via python-pptx: a Python helper opens the user's template and instantiates its own layouts (user-chosen). Claude's judgement goes into content and layout choice, never geometry.
- **D-003** Cross-platform pipeline copied from `build`: `source/skills/` is the single source of truth; `scripts/build.js` plus transformers emit committed output to `.claude/skills/`, `.opencode/skills/`, `.opencode/commands/`, `.agents/skills/`, `plugins/slides/skills/`, and `.codex/skills/`.
- **D-004** All 5 skills are portable: none use `Agent`/`Task`/`Skill` orchestration tools, so `providers.js` excludes nothing (unlike `build`, which excludes its orchestrator). Interactive Q&A is written as portable prose; Claude-specific "use the AskUserQuestion tool" guidance is wrapped in `<!-- claude-only -->` so the transformer strips it for Codex/opencode.
- **D-005** Brand context is persisted in a project-level `.slides/` directory: `context.md` (human and LLM readable: voice, audience, template description, layout map), `brand.json` (machine readable for the renderer: template path, font names, colour hex, the semantic-role-to-layout map), and `template.pptx` (the user's template, copied in). Mirrors impeccable's `.impeccable/` directory.
- **D-006** The `narrative`-to-`build-deck` contract is a markdown **deck spec** with a defined per-slide grammar (`## Slide N` headings carrying a `layout:` semantic role and labelled content fields). It is human-editable and parsed by `render.py`.
- **D-007** The slop detector lives in `presentation-craft` (a pre-generation Reflex Rejection procedure, a post-generation Deck Slop Test checklist, a Slide Slop Taxonomy, and match-and-refuse absolute bans). Modelled on `pm-skills`' PM Reflex Rejection and PM Slop Test.
- **D-008** Source-material distillation (REQ-005) is a collaborative workstream: James and Claude review the files together; nothing is baked in without James steering. No autonomous agent performs the distillation.
- **D-009** Proposed `presentation-craft/reference/` set: `narrative.md`, `slides.md`, `data-viz.md`, `delivery.md`, `slop.md`, `deck-spec.md`. The collaborative review (T-040) may split or merge these; the set is a committed starting structure, not a guess to be deferred.
- **D-010** No orchestrator skill in v1. An orchestrator would be Claude-only (needs `Agent`/`Skill`/`Task`), breaking REQ-006. Skills chain via "What's Next" pointers and direct invocation, exactly as `pm-skills` does. An orchestrator is noted as future work.
- **D-011** python-pptx scripts (`pptxlib.py`, `inspect_template.py`, `make_template.py`, `render.py`) live in `build-deck/scripts/`. `teach-slides` calls `inspect_template.py` and `make_template.py` via the relative path `../build-deck/scripts/`, the same cross-skill reference pattern `pm-skills` uses for `../product-management/reference/`.
- **D-012** The Graphic Continuum (Jonathan Schwabish and Severino Ribecca) is encoded in `data-viz.md` as a chart-selection taxonomy with attribution. The poster image itself is not redistributed.

### Assumptions

- **A-001** (confidence: medium-high) Python 3 is available on the end user's machine. macOS ships it; `build-deck` checks for `python3` and `python-pptx` and instructs `pip install python-pptx` if missing. Evidence: platform is darwin; standard for the target audience.
- **A-002** (confidence: high) Node.js is needed only by contributors who regenerate output (`npm run build`); end users consume the committed generated trees and never run Node. Evidence: `build`'s install story (README lines 19-39) ships generated trees committed.
- **A-003** (confidence: high) The 8 source files are craft teaching material suitable for universal distillation, not brand assets to bake in. Evidence: user statement "this skill isn't just for me, so it needs to use the user's template and fonts and colours."
- **A-004** (confidence: medium) One brand profile per project (one `.slides/` directory). The user did not select "decks for multiple brands." Agencies use separate project folders. Flagged in Open Questions.
- **A-005** (confidence: medium) Codex repo-local discovery is `.agents/skills/` and `build`'s `HARNESSES.md` matrix is current. Evidence: `build/HARNESSES.md` verified 2026-04-22/23. Worth re-checking before release.

---

## Problem

There is no tool that takes someone from a vague idea to a finished, on-brand, non-slop PowerPoint deck while teaching the storytelling craft along the way; Claude left to itself produces sensationalised, ad-copy, strapline-laden slides.

---

## Approach

A single-source skill repo, structured exactly like the `build` plugin, containing five skills that span the arc. The cross-platform build pipeline is copied wholesale from `build` (only `providers.js`, `body-rewrites.js`, `version-carriers.js`, and the manifests are repo-specific). The five skills mirror the `pm-skills` shape: one non-invocable core knowledge skill plus four user-invocable command skills.

```
                 ┌─────────────────────────────────────────────┐
                 │ presentation-craft  (core, not invocable)    │
                 │  craft references + slop detector + protocol │
                 └───────────────┬─────────────────────────────┘
                   loaded by every command skill below
   ┌──────────────┬──────────────┴───────┬───────────────────┐
   ▼              ▼                      ▼                   ▼
teach-slides   narrative             build-deck          slop-check
  │ writes      │ spitballs, writes    │ render.py         │ runs slop
  ▼             ▼                      ▼   reads spec+     │ detector on
.slides/        <deck>.deck.md ────────►   brand.json+     │ any spec or
 context.md      (deck spec)            │   template.pptx  │ .pptx
 brand.json  ◄───────────────────────── │   ──► <deck>.pptx│
 template.pptx                          └── slop detector ◄┘ before deliver
```

**Data flow.** `teach-slides` interviews the user and inspects their template (`inspect_template.py`) or builds a starter (`make_template.py`), writing `.slides/{context.md,brand.json,template.pptx}`. `narrative` loads `.slides/context.md`, spitballs the story across multiple turns, and writes a deck spec (markdown, D-006). `build-deck` runs `render.py` with the deck spec + `brand.json` + `template.pptx` to emit the `.pptx`, having run the slop detector on the spec first. `slop-check` runs the detector standalone on any deck spec or `.pptx`. Every command skill begins by loading `presentation-craft`, which carries the Context Gathering Protocol (if `.slides/` is absent, route to `teach-slides`), exactly as every `pm-skills` skill loads `product-management`.

**Where it lives.** Repo `slides`, plugin name `slides`, invocations `/slides:teach-slides`, `/slides:narrative`, `/slides:build-deck`, `/slides:slop-check`. `presentation-craft` is a dependency skill, not user-invocable.

### Stress-test

The pipeline copy is low-risk: `transform.js`, `builder.js`, `frontmatter.js`, `utils.js`, `build.js`, and `check-sync.js` are repo-agnostic (verified by reading them); only `providers.js` (output dirs, excludes), `body-rewrites.js` (the `/build:` regex hard-codes the prefix at `body-rewrites.js:21`), and `version-carriers.js` (lists `build`'s manifests) carry `build`-specific values. `frontmatter.js`'s `CLAUDE_ONLY_FIELDS` set is generic and reused as-is.

The genuinely uncertain part is the renderer. The template-fill approach assumes the user's template exposes usable, distinguishable slide layouts that python-pptx can enumerate via `prs.slide_layouts` and whose placeholders can be filled by `idx`. This holds for well-formed `.pptx` templates but not for degenerate ones (a template with a single blank layout). Mitigation is built into the design: `inspect_template.py` surfaces what it found and `teach-slides` has the user confirm the role-to-layout map, so a weak template fails loudly during setup rather than silently producing bad decks. python-pptx cannot render exotic chart types or guarantee that filled text does not overflow a placeholder; both are handled by scoping (native chart types only; the slop detector flags overflow-prone walls of text) rather than pretended away.

The second uncertainty is that the craft reference content cannot be written until the collaborative review happens. This plan therefore specifies the review as a concrete, gated task (T-040) producing a concrete artifact (`notes/source-review.md`), and commits to a concrete reference-file set (D-009) that the review populates. It does not defer the content with a placeholder.

---

## Who uses this and how

- **Installing user, first run.** Installs the plugin, runs `/slides:narrative` or `/slides:build-deck`. The Context Gathering Protocol finds no `.slides/` directory and routes them into `teach-slides`, which interviews them and sets up their brand, then resumes the original task. Mirrors impeccable's "PRODUCT.md missing, run teach" behaviour.
- **User with a corporate template.** `teach-slides` ingests their `.pptx`/`.potx`, runs `inspect_template.py`, presents the discovered layouts, and has them map semantic roles (section divider, statement, two-column, etc.) to template layouts.
- **User with no template but existing decks.** `teach-slides` registers one of their existing decks as the template directly (a deck and a template are the same to python-pptx: both carry masters and layouts). No conversion needed.
- **User with nothing.** `teach-slides` runs `make_template.py` to generate a functional starter template themed with their colours and fonts, and tells them it is a starting point to refine in PowerPoint.
- **User who abandons `narrative` mid-spitball.** The deck spec is a plain markdown file written incrementally; a half-finished spec is still a valid, resumable file. Re-invoking `narrative` with the spec path resumes.
- **User who edits the deck spec or `brand.json` by hand.** `render.py` validates both and reports the offending line rather than producing a broken `.pptx`.
- **Codex / opencode user.** Installs via the harness-specific path (README documents all three). Skills behave identically; `$ARGUMENTS` and `/slides:` references are rewritten by the transformer; `<!-- claude-only -->` asides are stripped.
- **Contributor (James).** Edits `source/skills/`, runs `npm run build`, commits source + regenerated output + tests together. `npm run check-sync` fails on an uncommitted change set.
- **James, during the build.** Drives the collaborative source review (T-040), which gates the craft content.

---

## Files to change

Every file is **New** (greenfield repo). Grouped by workstream. The full file map is in the table below.

### Step 1: File structure mapping

| File | New/Mod | Responsibility | Depends on |
|------|---------|----------------|------------|
| `package.json` | New | Build scripts (`build`, `check-sync`, `test`); `type: module`; version carrier. No deps. | none |
| `.gitignore` | New | Ignore `node_modules/`, `.DS_Store`, `__pycache__/`, `*.tmp` | none |
| `README.md` | New | Per-harness install + compatibility + standalone use | manifests |
| `CLAUDE.md` | New | Contributor guide: source-of-truth, build, versioning | pipeline |
| `AGENTS.md` | New | Repo guide for Codex/opencode consumers | pipeline |
| `HARNESSES.md` | New | Capability matrix (ported from `build`) | none |
| `LICENSE` | New | MIT | none |
| `scripts/build.js` | New | Build entrypoint (copy from `build`) | transformers |
| `scripts/check-sync.js` | New | Version parity + output drift check (copy from `build`) | providers, version-carriers |
| `scripts/transformers/utils.js` | New | `ROOT`, `read`, `write` (copy verbatim) | none |
| `scripts/transformers/transform.js` | New | Compose frontmatter + body passes (copy verbatim) | frontmatter, body-rewrites |
| `scripts/transformers/builder.js` | New | Walk source, emit per provider (copy verbatim) | transform |
| `scripts/transformers/frontmatter.js` | New | Strip Claude-only frontmatter (copy verbatim) | none |
| `scripts/transformers/body-rewrites.js` | New | Rewrite `$ARGUMENTS`, `/slides:` refs, claude-only blocks | none |
| `scripts/transformers/providers.js` | New | Per-provider config: 5 output dirs, excludes `[]` | none |
| `scripts/transformers/version-carriers.js` | New | List the 4 version-carrying manifests | none |
| `scripts/transformers/builder.test.js` | New | Builder + byte-equality tests (port from `build`) | builder, providers |
| `scripts/transformers/transform.test.js` | New | Transform unit tests (port from `build`) | transform |
| `scripts/transformers/manifests.test.js` | New | Version parity test (port from `build`) | version-carriers |
| `scripts/transformers/check-sync.test.js` | New | Drift-detection self-test (port from `build`) | check-sync |
| `scripts/transformers/skill-contract.test.js` | New | Frontmatter validity + line ceilings for slides skills | source skills |
| `.claude-plugin/plugin.json` | New | Claude plugin descriptor | none |
| `.claude-plugin/marketplace.json` | New | Claude marketplace listing | none |
| `.agents/plugins/marketplace.json` | New | Codex marketplace catalog | none |
| `plugins/slides/.codex-plugin/plugin.json` | New | Codex plugin manifest | none |
| `source/skills/presentation-craft/SKILL.md` | New | Core: craft overview, Context Gathering Protocol, operational slop detector, reference pointers | reference files |
| `source/skills/presentation-craft/reference/narrative.md` | New | Story structure, through-line, audience-first, the spitball method | T-040 review |
| `source/skills/presentation-craft/reference/slides.md` | New | Visual craft: one idea per slide, assertion titles, slide-vs-speaker job, hierarchy | T-040 review |
| `source/skills/presentation-craft/reference/data-viz.md` | New | Graphic Continuum taxonomy, chart-by-relationship choice | T-040 review |
| `source/skills/presentation-craft/reference/delivery.md` | New | Presenting craft from the RADA manual and presenting decks | T-040 review |
| `source/skills/presentation-craft/reference/slop.md` | New | Full Slide Slop Taxonomy, detection rules, worked examples | T-040 review |
| `source/skills/presentation-craft/reference/deck-spec.md` | New | The deck-spec grammar (D-006), read by humans, `narrative`, `build-deck`, `render.py` | none |
| `source/skills/teach-slides/SKILL.md` | New | Interview user, inspect or build template, write `.slides/` | pptx scripts |
| `source/skills/narrative/SKILL.md` | New | Multi-turn spitball; produce a deck spec | deck-spec, slop |
| `source/skills/build-deck/SKILL.md` | New | Run `render.py`; run slop detector; deliver `.pptx` | render.py, slop |
| `source/skills/build-deck/scripts/pptxlib.py` | New | Shared python-pptx helpers: load, enumerate layouts, resolve roles, fill placeholders, apply theme | none |
| `source/skills/build-deck/scripts/inspect_template.py` | New | CLI: dump a template's layouts + placeholders as JSON | pptxlib |
| `source/skills/build-deck/scripts/make_template.py` | New | CLI: generate a themed starter template | pptxlib |
| `source/skills/build-deck/scripts/render.py` | New | CLI: deck spec + `brand.json` + template → `.pptx` | pptxlib, deck-spec |
| `source/skills/slop-check/SKILL.md` | New | Standalone adversarial slop review of a deck spec or `.pptx` | slop |
| `source/skills/slop-check/fixtures/clean-deck.md` | New | A clean deck-spec fixture (must pass the detector) | deck-spec |
| `source/skills/slop-check/fixtures/sloppy-deck.md` | New | A sloppy deck-spec fixture (straplines, ad copy, sensational title, em dashes, bullet soup) | deck-spec |
| `source/commands/teach-slides.md` | New | opencode slash-command wrapper | teach-slides |
| `source/commands/narrative.md` | New | opencode slash-command wrapper | narrative |
| `source/commands/build-deck.md` | New | opencode slash-command wrapper | build-deck |
| `source/commands/slop-check.md` | New | opencode slash-command wrapper | slop-check |
| `tests/generate-fixture-template.py` | New | Reproducibly create the fixture template | none |
| `tests/fixtures/sample-template.pptx` | New | Minimal multi-layout template for renderer tests (committed binary) | generate-fixture-template |
| `tests/fixtures/sample-deck.md` | New | A valid deck spec for renderer tests | deck-spec |
| `tests/test_render.py` | New | stdlib `unittest` for `render.py` | render.py, fixtures |
| `notes/source-review.md` | New | Working notes from the collaborative review; maps each source file to principles and target reference doc. Repo artifact, not shipped in skills. | T-040 |
| `.claude/skills/**` | New (generated) | Claude Code output | `npm run build` |
| `.opencode/skills/**`, `.opencode/commands/**` | New (generated) | opencode output | `npm run build` |
| `.agents/skills/**` | New (generated) | Codex repo-local output | `npm run build` |
| `plugins/slides/skills/**` | New (generated) | Codex plugin-packaged output | `npm run build` |
| `.codex/skills/**` | New (generated) | Codex cross-harness bridge output | `npm run build` |

---

## Data impact

None. The skill pack uses no database. The only persisted state is per-user local files in a project's `.slides/` directory and generated `.pptx` files, all created by the skills at runtime on the user's machine. There is no schema, no migration, no backfill.

---

## What existing behavior changes

Nothing. This is a greenfield repo at an empty path; there is no existing behavior, no existing users, and no current system to alter. The four reference repos (`build`, `impeccable`, `pm-skills`, `app-store-screenshots`) are read-only models and are not modified.

---

## New dependencies

- **python-pptx** (`>=1.0,<2.0`; current `1.0.2`). License: **MIT**, compatible. Maintenance: the de-facto standard for programmatic `.pptx`; maintained primarily by Steve Canny; mature and stable API; release cadence is slow because the surface is settled; effective bus factor 1, mitigated by maturity and stability. Size: pure Python; transitive deps `lxml`, `Pillow`, `XlsxWriter`, all common. Justification: it is the only viable library for reading and writing `.pptx`, and D-002 (template-fill) requires it. No existing dependency covers it (greenfield repo). It is an **end-user runtime** dependency for `build-deck` and `teach-slides`; the skill checks for it and instructs `pip install python-pptx` if absent.
- **Node.js** (runtime, contributor-only, no version pin beyond ES modules support). Used only to run `scripts/build.js`/`check-sync.js`/tests when regenerating output. End users consume committed generated trees and never need Node (A-002). Mirrors `build` and `impeccable`.
- **npm packages: none.** `build`'s `package.json` declares zero dependencies; the transformer code is pure Node stdlib. `slides` copies that: `package.json` has scripts only.
- **Test framework: none added.** `tests/test_render.py` uses Python's stdlib `unittest`, not pytest, to avoid a dependency.

---

## Access control and authorization

Not applicable in the conventional sense: this is an open-source skill plugin with no server, no endpoints, and no authentication. Anyone who installs it can use every skill. All state is local: `teach-slides` reads a template file the user points at, the `.slides/` directory and generated `.pptx` files are written into the user's own project, and nothing is transmitted off the machine. There is no plan/subscription gating. The skill scripts run with the user's own permissions via the harness's Bash tool.

---

## Abuse and edge cases

- **python3 or python-pptx missing.** `build-deck` and `teach-slides` probe for both before running any script and print the exact `pip install python-pptx` remedy; they do not crash.
- **Template with no usable layouts, or a corrupt `.pptx`.** `inspect_template.py` reports the layout count and any parse failure clearly; `teach-slides` falls back to `make_template.py`.
- **Malformed deck spec.** `render.py` validates the grammar and exits non-zero naming the offending slide and line; it never emits a half-built `.pptx`.
- **Hand-edited broken `brand.json`.** `render.py` validates required keys (`template`, `fonts`, `colours`, `layout_map`) and reports which is missing or malformed.
- **Exotic chart type** (sankey, marimekko, and other non-native Graphic Continuum types). `render.py` emits a clearly labelled placeholder slide plus a note in the run summary; it does not crash. `data-viz.md` still teaches the full taxonomy.
- **Very long deck** (200+ slides). python-pptx handles it; the slop detector flags excessive length as substance slop ("the deck is the document, not the talk").
- **`build-deck` run before `teach-slides`.** The Context Gathering Protocol detects the missing `.slides/` directory and routes to `teach-slides` first, then resumes.
- **Empty or vague narrative input.** `narrative` pushes back and asks discovery questions rather than generating a deck spec from one line (REQ-002 behaviour, modelled on `pm:brief` Step 1).
- **The detector over-flags (slop-checking the slop checker).** `slop-check` returns severity-ranked findings, not a binary pass/fail, and is tuned so `clean-deck.md` produces zero high-severity findings (a verification gate, T-072).
- **Claude-only syntax leaking into Codex/opencode output.** Caught by `check-sync` plus a test asserting no literal `$ARGUMENTS` and no `/slides:` substring under the non-Claude output trees (ported from `build`).
- **Concurrency.** Not relevant: local single-user CLI skills with no shared state.

---

## Out of scope

- An orchestrator skill (`/slides` running the whole arc autonomously). It would be Claude-only and break REQ-006 (D-010). Obvious next ask; deferred deliberately. Skills chain via "What's Next" pointers in v1.
- The UI (claude.ai, Claude Desktop, a custom web app). User deprioritised it.
- Multiple brand profiles inside one project. One `.slides/` per project (A-004); agencies use separate folders.
- Rendering exotic Graphic Continuum chart types natively. v1 renders native python-pptx chart types only.
- Generating a *designed* bespoke template. `make_template.py` produces a functional themed starter, not a design showcase.
- A marketing website for the pack (`pm-skills` and `impeccable` have one; not built here).
- Google Slides, Keynote, Marp, or HTML export. Output is `.pptx` only.
- Animations and slide transitions beyond what the user's template already carries.

---

## Risks and rollback

Ordered by severity.

1. **The collaborative review is skipped or compressed.** If the craft references (T-052 to T-055) are written without James steering, they become exactly the generic AI slop the pack exists to prevent. Mitigation: T-040 is an explicit, interactive, gating task; D-008 forbids autonomous distillation; Wave 2 content tasks `depends_on` T-040.
2. **Template-fill quality depends on the user's template.** A template with poorly-named or missing layouts yields poor decks. Mitigation: `inspect_template.py` surfaces the layout map for explicit user confirmation in `teach-slides`; `make_template.py` provides a clean fallback; `render.py` fails loudly on an unresolvable role.
3. **python-pptx cannot do everything.** Exotic charts, fine typography control, overflow detection. Mitigation: scope `render.py` to native features; placeholders + notes for the rest; the slop detector flags overflow-prone content.
4. **Harness conventions drift.** Codex/opencode skill discovery may change from `build`'s `HARNESSES.md` matrix (verified 2026-04). Mitigation: re-verify before release; the pipeline is data-driven via `providers.js`, so a fix is localised.
5. **Scope is large** (5 skills + renderer + pipeline). Mitigation: waves; Workstream A is a near-mechanical copy of `build`; Workstream D is self-contained; the real effort concentrates in B and C.

**Rollback.** Greenfield repo with nothing downstream. "Rollback" is `git revert` or not publishing. Every generated tree is reproducible from `source/` via `npm run build`, so a bad generated commit is fixed by rebuilding. No production system can break.

---

## Observability & monitoring

N/A - no production deployment. This is a local skill pack with no server or telemetry. The closest analogues, and the signals a contributor relies on: `npm run check-sync` (fails on version drift or uncommitted output drift), `npm test` (transformer + contract tests), and `python3 -m unittest` (renderer tests). Failure signature for a contributor: check-sync prints the drifted files; tests print the failing assertion. Failure signature for an end user: `build-deck`/`teach-slides` print the missing-dependency or malformed-input error inline at run time.

---

## Open questions

- **A-004 (one brand profile per project).** Believed true because the user did not select "decks for multiple brands" when offered it. Unverified for an agency use case. If multi-brand is needed, `.slides/` would gain named subdirectories and `brand.json` a profile selector; this is additive and does not change the v1 architecture. Confirm before T-056.
- **A-005 (`.agents/skills/` is Codex's discovery path).** Taken from `build/HARNESSES.md` (verified 2026-04-22). Re-verify against current Codex docs before release (cheap; one doc check).
- **A-001 (python-pptx availability).** The skill handles a missing dependency gracefully, so a wrong assumption degrades to a one-line install prompt, not a failure.
- **Reference-file set (D-009).** Proposed concretely, but the collaborative review (T-040) is the authority and may split or merge files. The risk is contained: it changes file names within Workstream C, not the architecture.
- **License.** MIT is assumed (matches `build`'s Codex manifest and `pm-skills` uses Apache 2.0; `impeccable` Apache 2.0). Confirm with the user; trivial to change in one file.
- **Graphic Continuum attribution wording.** The taxonomy is encoded with credit (D-012); confirm the exact attribution line with the user during T-054.

---

## Wave 0 validation design

Each requirement's fastest proof, established before feature code:

- **REQ-003 (`.pptx` build).** `tests/test_render.py` (stdlib `unittest`): given `tests/fixtures/sample-template.pptx` and `tests/fixtures/sample-deck.md`, `render.py` produces a `.pptx` that python-pptx can reopen; assert slide count matches the spec, each slide uses the mapped layout, placeholder text matches the spec, and no text box exists outside the template's placeholders (the structural guarantee against an injected strapline). Fails until T-033; passes after.
- **REQ-004 (slop detector).** `slop-check/fixtures/sloppy-deck.md` and `clean-deck.md`. The sloppy fixture contains a verbatim bottom strapline, an ad-copy line, a sensational title, an em dash, and a 7-bullet slide. Proof at T-072: `slop-check` flags every planted defect in the sloppy fixture and returns zero high-severity findings on the clean fixture. This is an LLM-judged check (the detector is prose), the same shape as `build`'s `eval` clean/flawed plan fixtures.
- **REQ-006 (cross-platform).** `npm run build` exits 0; `npm run check-sync` exits 0 on a clean tree; `manifests.test.js` asserts version parity; `builder.test.js` asserts no `$ARGUMENTS`/`/slides:` literal leaks into non-Claude output. Provable as soon as Workstream A lands.
- **REQ-007 (packaged).** The 4 manifests parse as JSON and carry an identical version; `check-sync` enforces it.
- **REQ-001, REQ-002, REQ-005.** Not unit-testable before coding because they are interactive skill behaviours and distilled prose. First testable point: REQ-001 at T-056 (run `teach-slides`, confirm `.slides/` is written); REQ-002 at T-057 (run `narrative` with a one-line prompt, confirm it asks questions instead of generating); REQ-005 at T-040 (inspect `notes/source-review.md` for a section per source file). Verified manually in T-072.

---

## Execution manifest

```yaml
execution_manifest:
  - id: T-001
    wave: 0
    depends_on: []
    files_modified: ["tests/generate-fixture-template.py", "tests/fixtures/sample-template.pptx"]
    requirements: ["REQ-003"]
    must_haves: ["script regenerates the .pptx deterministically", "fixture template exposes >=4 distinct named slide layouts"]
    verify: "python3 tests/generate-fixture-template.py && python3 -c \"from pptx import Presentation; print(len(Presentation('tests/fixtures/sample-template.pptx').slide_layouts))\""
    done: "sample-template.pptx exists and reports >=4 layouts"
  - id: T-002
    wave: 0
    depends_on: []
    files_modified: ["source/skills/slop-check/fixtures/clean-deck.md", "source/skills/slop-check/fixtures/sloppy-deck.md"]
    requirements: ["REQ-004"]
    must_haves: ["sloppy-deck.md contains a bottom strapline line, an ad-copy line, a sensational title, an em dash, and a 7-bullet slide", "clean-deck.md contains none of these"]
    verify: "grep -c '—' source/skills/slop-check/fixtures/sloppy-deck.md ; inspect both files against the planted-defect list"
    done: "both fixtures exist; sloppy one carries every planted defect, clean one carries none"
  - id: T-003
    wave: 0
    depends_on: []
    files_modified: ["source/skills/presentation-craft/reference/deck-spec.md", "tests/fixtures/sample-deck.md"]
    requirements: ["REQ-003"]
    must_haves: ["deck-spec.md defines the per-slide grammar: heading, layout role, labelled fields", "sample-deck.md is a valid deck spec under that grammar"]
    verify: "inspect deck-spec.md for a complete grammar definition; sample-deck.md parses against it by eye"
    done: "the deck-spec grammar is fully specified and a conforming sample exists"
  - id: T-004
    wave: 0
    depends_on: ["T-001", "T-003"]
    files_modified: ["tests/test_render.py"]
    requirements: ["REQ-003"]
    must_haves: ["test asserts slide count, per-slide layout, placeholder text, and absence of non-placeholder text boxes", "test currently fails because render.py is absent"]
    verify: "python3 -m unittest tests/test_render.py 2>&1 | grep -E 'Error|FAIL'"
    done: "test_render.py is complete and fails only because render.py does not yet exist"
  - id: T-010
    wave: 1
    depends_on: []
    files_modified: ["package.json", ".gitignore"]
    requirements: ["REQ-006"]
    must_haves: ["package.json has type:module and build/check-sync/test scripts and zero dependencies", ".gitignore covers node_modules, __pycache__, .DS_Store"]
    verify: "node -e \"const p=require('./package.json'); if(p.type!=='module')process.exit(1)\""
    done: "package.json and .gitignore exist and match build's shape"
  - id: T-011
    wave: 1
    depends_on: []
    files_modified: ["scripts/build.js", "scripts/transformers/utils.js", "scripts/transformers/transform.js", "scripts/transformers/builder.js", "scripts/transformers/frontmatter.js"]
    requirements: ["REQ-006"]
    must_haves: ["all five files are byte-identical copies of build's repo-agnostic pipeline files"]
    verify: "diff each file against the build repo equivalent"
    done: "the repo-agnostic pipeline files are copied verbatim"
  - id: T-012
    wave: 1
    depends_on: []
    files_modified: ["scripts/transformers/body-rewrites.js"]
    requirements: ["REQ-006"]
    must_haves: ["the slash-command regex matches /slides: not /build:", "$ARGUMENTS and claude-only-block rewrites are unchanged from build"]
    verify: "node -e \"import('./scripts/transformers/body-rewrites.js')\" ; grep 'slides' scripts/transformers/body-rewrites.js"
    done: "body-rewrites.js rewrites /slides: references"
  - id: T-013
    wave: 1
    depends_on: []
    files_modified: ["scripts/transformers/providers.js"]
    requirements: ["REQ-006"]
    must_haves: ["five providers map to .claude/skills, .opencode/skills, .agents/skills, plugins/slides/skills, .codex/skills", "exclude is [] for every provider", "codex/codex-plugin/codex-cross share one rewrite object by reference"]
    verify: "node -e \"import('./scripts/transformers/providers.js').then(m=>console.log(Object.keys(m.PROVIDERS)))\""
    done: "providers.js emits the five slides output trees with no exclusions"
  - id: T-014
    wave: 1
    depends_on: []
    files_modified: ["scripts/transformers/version-carriers.js"]
    requirements: ["REQ-007"]
    must_haves: ["lists the 4 version carriers: both .claude-plugin JSONs, the codex plugin.json, and package.json"]
    verify: "node -e \"import('./scripts/transformers/version-carriers.js').then(m=>console.log(m.VERSION_CARRIERS.length))\""
    done: "version-carriers.js lists all 4 carriers"
  - id: T-015
    wave: 1
    depends_on: ["T-013", "T-014"]
    files_modified: ["scripts/check-sync.js"]
    requirements: ["REQ-006"]
    must_haves: ["copy of build's check-sync.js, importing the slides providers and version-carriers"]
    verify: "node -e \"import('./scripts/check-sync.js')\" --check || true"
    done: "check-sync.js exists and resolves its imports"
  - id: T-016
    wave: 1
    depends_on: ["T-011", "T-012", "T-013", "T-014"]
    files_modified: ["scripts/transformers/builder.test.js", "scripts/transformers/transform.test.js", "scripts/transformers/manifests.test.js", "scripts/transformers/check-sync.test.js"]
    requirements: ["REQ-006", "REQ-007"]
    must_haves: ["builder.test.js asserts no $ARGUMENTS or /slides: literal leaks into non-Claude trees", "manifests.test.js asserts the 4 carriers share one version"]
    verify: "npm test"
    done: "ported transformer tests pass against the slides pipeline"
  - id: T-017
    wave: 1
    depends_on: ["T-011"]
    files_modified: ["scripts/transformers/skill-contract.test.js"]
    requirements: ["REQ-006"]
    must_haves: ["every SKILL.md has name and description frontmatter", "line ceilings: presentation-craft <=210, command skills <=170, reference files <=190"]
    verify: "npm test"
    done: "skill-contract.test.js enforces frontmatter and ceilings"
  - id: T-018
    wave: 1
    depends_on: []
    files_modified: [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json", "plugins/slides/.codex-plugin/plugin.json"]
    requirements: ["REQ-007"]
    must_haves: ["all 4 parse as JSON", "all 4 carry an identical version string", "Claude marketplace points skills at ./.claude/skills, Codex plugin at ./skills/"]
    verify: "node -e \"['.claude-plugin/plugin.json','.claude-plugin/marketplace.json','.agents/plugins/marketplace.json','plugins/slides/.codex-plugin/plugin.json'].forEach(f=>JSON.parse(require('fs').readFileSync(f)))\""
    done: "the 4 manifests exist, parse, and agree on version"
  - id: T-019
    wave: 1
    depends_on: []
    files_modified: ["README.md", "CLAUDE.md", "AGENTS.md", "HARNESSES.md", "LICENSE"]
    requirements: ["REQ-006", "REQ-007"]
    must_haves: ["README documents install for Claude Code, Codex, and opencode", "HARNESSES.md carries the capability matrix", "CLAUDE.md states source/skills is the source of truth"]
    verify: "inspect each file for the required sections"
    done: "all five repo docs exist with the required content"
  - id: T-030
    wave: 1
    depends_on: []
    files_modified: ["source/skills/build-deck/scripts/pptxlib.py"]
    requirements: ["REQ-003"]
    must_haves: ["functions: load_template, list_layouts, resolve_role, fill_placeholders, apply_theme", "no font, colour, or coordinate literals (all read from brand.json or the template)"]
    verify: "python3 -c \"import importlib.util,sys; spec=importlib.util.spec_from_file_location('p','source/skills/build-deck/scripts/pptxlib.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print([f for f in dir(m) if not f.startswith('_')])\""
    done: "pptxlib.py exposes the five named helpers and imports cleanly"
  - id: T-031
    wave: 1
    depends_on: ["T-030"]
    files_modified: ["source/skills/build-deck/scripts/inspect_template.py"]
    requirements: ["REQ-001"]
    must_haves: ["given a .pptx path, prints JSON of every layout with its index, name, and placeholder idx/type list"]
    verify: "python3 source/skills/build-deck/scripts/inspect_template.py tests/fixtures/sample-template.pptx"
    done: "inspect_template.py dumps the fixture template's layout map as JSON"
  - id: T-032
    wave: 1
    depends_on: ["T-030"]
    files_modified: ["source/skills/build-deck/scripts/make_template.py"]
    requirements: ["REQ-001"]
    must_haves: ["given colours and font names, writes a themed starter .pptx with at least the section/statement/title-content/two-column layouts"]
    verify: "python3 source/skills/build-deck/scripts/make_template.py --out /tmp/starter.pptx --colours '#1A1A2E,#E94560' --heading-font 'Georgia' --body-font 'Verdana' && python3 -c \"from pptx import Presentation; print(len(Presentation('/tmp/starter.pptx').slide_layouts))\""
    done: "make_template.py emits a valid themed starter template"
  - id: T-033
    wave: 1
    depends_on: ["T-030", "T-003", "T-004"]
    files_modified: ["source/skills/build-deck/scripts/render.py"]
    requirements: ["REQ-003"]
    must_haves: ["parses a deck spec, validates brand.json keys, fills only template placeholders, errors with the offending slide on malformed input", "test_render.py passes"]
    verify: "python3 -m unittest tests/test_render.py"
    done: "render.py turns the sample deck spec into a .pptx and all render tests pass"
  - id: T-040
    wave: 1
    depends_on: []
    files_modified: ["notes/source-review.md"]
    requirements: ["REQ-005"]
    must_haves: ["interactive: James steers; no autonomous distillation", "one section per source file plus the Graphic Continuum", "each section names >=1 craft principle and its target reference doc among narrative/slides/data-viz/delivery/slop", "James-specific anti-patterns for the slop detector are captured"]
    verify: "inspect notes/source-review.md for a section per source file each naming principles and a target doc"
    done: "source-review.md maps all 8 files plus the chart to principles and target reference docs, confirmed with James"
  - id: T-050
    wave: 2
    depends_on: ["T-040", "T-051"]
    files_modified: ["source/skills/presentation-craft/SKILL.md"]
    requirements: ["REQ-004", "REQ-005"]
    must_haves: ["frontmatter has name and description, no user-invocable", "carries the Context Gathering Protocol (route to teach-slides if .slides/ absent)", "carries the operational slop detector: Reflex Rejection, Deck Slop Test, absolute bans", "links every reference file"]
    verify: "inspect SKILL.md; npm test (skill-contract)"
    done: "presentation-craft/SKILL.md is the loadable core with protocol and slop detector"
  - id: T-051
    wave: 2
    depends_on: ["T-040", "T-002"]
    files_modified: ["source/skills/presentation-craft/reference/slop.md"]
    requirements: ["REQ-004"]
    must_haves: ["full Slide Slop Taxonomy: substance, voice, visual", "explicit named entries for bottom strapline, sensationalising, ad-copy voice, title-restates-body, bullet soup", "a detection rule per taxonomy entry", "flags every defect planted in sloppy-deck.md"]
    verify: "inspect slop.md against the sloppy-deck.md planted-defect list"
    done: "slop.md is the full detector reference and covers every planted fixture defect"
  - id: T-052
    wave: 2
    depends_on: ["T-040"]
    files_modified: ["source/skills/presentation-craft/reference/narrative.md"]
    requirements: ["REQ-005"]
    must_haves: ["story structure, through-line, audience-first, and the spitball method, sourced from notes/source-review.md"]
    verify: "inspect narrative.md; cross-check against source-review.md attributions"
    done: "narrative.md encodes the distilled storytelling craft"
  - id: T-053
    wave: 2
    depends_on: ["T-040"]
    files_modified: ["source/skills/presentation-craft/reference/slides.md"]
    requirements: ["REQ-005"]
    must_haves: ["one-idea-per-slide, assertion titles, slide-job vs speaker-job, visual hierarchy, sourced from notes/source-review.md"]
    verify: "inspect slides.md; cross-check against source-review.md attributions"
    done: "slides.md encodes the distilled visual-craft principles"
  - id: T-054
    wave: 2
    depends_on: ["T-040"]
    files_modified: ["source/skills/presentation-craft/reference/data-viz.md"]
    requirements: ["REQ-005"]
    must_haves: ["the Graphic Continuum six-family taxonomy with attribution to Schwabish and Ribecca", "chart-by-relationship selection guidance", "states which chart types render.py supports natively"]
    verify: "inspect data-viz.md for the taxonomy, the attribution line, and the native-type list"
    done: "data-viz.md encodes the chart-selection taxonomy with attribution"
  - id: T-055
    wave: 2
    depends_on: ["T-040"]
    files_modified: ["source/skills/presentation-craft/reference/delivery.md"]
    requirements: ["REQ-005"]
    must_haves: ["presenting and delivery craft from the RADA manual and presenting decks, sourced from notes/source-review.md"]
    verify: "inspect delivery.md; cross-check against source-review.md attributions"
    done: "delivery.md encodes the distilled delivery craft"
  - id: T-056
    wave: 2
    depends_on: ["T-031", "T-032", "T-050"]
    files_modified: ["source/skills/teach-slides/SKILL.md"]
    requirements: ["REQ-001"]
    must_haves: ["loads presentation-craft first", "interview covers template, fonts, colours, logo, audience, voice", "three template paths: ingest existing, reuse a deck, make_template fallback", "calls inspect_template.py via ../build-deck/scripts/", "writes .slides/context.md, brand.json, template.pptx", "interactive Q&A is portable prose; AskUserQuestion guidance is wrapped in claude-only markers"]
    verify: "inspect SKILL.md; npm test (skill-contract)"
    done: "teach-slides SKILL.md captures brand and writes the .slides/ directory"
  - id: T-057
    wave: 2
    depends_on: ["T-003", "T-050", "T-051"]
    files_modified: ["source/skills/narrative/SKILL.md"]
    requirements: ["REQ-002"]
    must_haves: ["loads presentation-craft and the Context Gathering Protocol first", "multi-turn spitball with explicit stop-and-wait gates before structuring", "pushes back on vague input", "writes a deck spec conforming to deck-spec.md", "runs the slop detector before delivering the spec"]
    verify: "inspect SKILL.md; npm test (skill-contract)"
    done: "narrative SKILL.md runs the spitball flow and emits a deck spec"
  - id: T-058
    wave: 2
    depends_on: ["T-033", "T-050", "T-051"]
    files_modified: ["source/skills/build-deck/SKILL.md"]
    requirements: ["REQ-003", "REQ-004"]
    must_haves: ["loads presentation-craft first", "probes for python3 and python-pptx and prints the install remedy", "runs the slop detector on the deck spec before rendering", "runs render.py with the spec, brand.json, and template", "reports the render summary including any chart placeholders"]
    verify: "inspect SKILL.md; npm test (skill-contract)"
    done: "build-deck SKILL.md renders a deck spec to .pptx with a slop gate"
  - id: T-059
    wave: 2
    depends_on: ["T-050", "T-051", "T-002"]
    files_modified: ["source/skills/slop-check/SKILL.md"]
    requirements: ["REQ-004"]
    must_haves: ["loads presentation-craft first", "accepts a deck spec or a .pptx (reads .pptx via python-pptx)", "returns severity-ranked findings, not pass/fail", "references the slop.md taxonomy"]
    verify: "inspect SKILL.md; npm test (skill-contract)"
    done: "slop-check SKILL.md runs the standalone adversarial slop review"
  - id: T-060
    wave: 2
    depends_on: ["T-056", "T-057", "T-058", "T-059"]
    files_modified: ["source/commands/teach-slides.md", "source/commands/narrative.md", "source/commands/build-deck.md", "source/commands/slop-check.md"]
    requirements: ["REQ-006"]
    must_haves: ["each command body is a single @.opencode/skills/<name>/SKILL.md include line", "one command per user-invocable skill; none for presentation-craft"]
    verify: "inspect the four files"
    done: "four opencode command wrappers exist"
  - id: T-070
    wave: 3
    depends_on: ["T-010", "T-011", "T-012", "T-013", "T-014", "T-015", "T-018", "T-050", "T-051", "T-052", "T-053", "T-054", "T-055", "T-056", "T-057", "T-058", "T-059", "T-060"]
    files_modified: [".claude/skills", ".opencode/skills", ".opencode/commands", ".agents/skills", "plugins/slides/skills", ".codex/skills"]
    requirements: ["REQ-006", "REQ-007"]
    must_haves: ["npm run build exits 0", "all six output trees are generated and committed", "no $ARGUMENTS or /slides: literal under non-Claude trees"]
    verify: "npm run build && grep -rl '\\$ARGUMENTS' .opencode/skills .agents/skills || echo CLEAN"
    done: "all generated output trees exist and are committed"
  - id: T-071
    wave: 3
    depends_on: ["T-070", "T-016", "T-017"]
    files_modified: []
    requirements: ["REQ-006", "REQ-007"]
    must_haves: ["npm run check-sync exits 0", "npm test exits 0", "python3 -m unittest exits 0"]
    verify: "npm run check-sync && npm test && python3 -m unittest discover tests"
    done: "all automated checks pass on the committed tree"
  - id: T-072
    wave: 3
    depends_on: ["T-070"]
    files_modified: []
    requirements: ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005"]
    must_haves: ["end-to-end run in Claude Code: teach-slides then narrative then build-deck then slop-check", "a real .pptx opens in PowerPoint", "slop-check flags every defect in sloppy-deck.md and zero high-severity findings on clean-deck.md"]
    verify: "run the four skills in sequence; open the .pptx; run slop-check on both fixtures"
    done: "the full arc produces a clean on-brand deck and the detector passes both fixtures"
  - id: T-073
    wave: 3
    depends_on: ["T-070"]
    files_modified: []
    requirements: ["REQ-006"]
    must_haves: ["one skill invoked in Codex and one in opencode", "invocation phrasing resolves; no Claude-only syntax visible"]
    verify: "load build-deck in Codex via $skill and slop-check in opencode via the skill tool"
    done: "skills invoke correctly in Codex and opencode"
```

---

## Workflow artifacts

N/A - standalone plan. This plan was produced by `/build:impl-plan` run standalone, not by the `/build` orchestrator, so there are no `.build/plans/{slug}-*.md` phase artifacts. This plan file is saved at `/Users/jameshemson/.claude/plans/design-a-slides-skill-generic-tarjan.md`. If James wants durable context through implementation, copy it into the new repo at `slides/notes/plans/` once the repo is initialised (mirroring `impeccable/notes/plans/`), alongside `notes/source-review.md` from T-040.

---

## UI contract

N/A - no web UI files change. The pack has no screens or components. Its visual output is the generated `.pptx`, whose appearance is governed entirely by D-002 (the template carries all design; code never sets geometry) and policed by REQ-004 (the slop detector). The visual "states" that matter are deck-level: a clean deck, a deck with planted slop, and a deck built on a weak template. These are verified by opening generated `.pptx` files in PowerPoint (T-072) and by the structural assertion in `test_render.py` that no text box exists outside the template's placeholders.

---

## Parallel workstreams

- **Workstream A: pipeline-and-scaffold.** Files: `package.json`, `.gitignore`, all of `scripts/`, the 4 manifests, the 5 repo docs. Complexity: simple (largely a verbatim copy of `build`, with 3 repo-specific files). Depends on: none. Tasks: T-010 to T-019.
- **Workstream B: source-review.** Files: `notes/source-review.md`. Complexity: complex (interactive, judgement-heavy, the content core). Depends on: none, but **gates Workstream C**. Interactive with James; not an autonomous agent. Tasks: T-040.
- **Workstream D: renderer.** Files: all of `build-deck/scripts/`, the deck-spec grammar, and the test fixtures. Complexity: complex (real Python, the highest-effort self-contained piece). Depends on: Wave 0 fixtures. Tasks: T-001, T-003, T-004, T-030 to T-033.
- **Workstream C: skills.** Files: all 5 `SKILL.md` files, the 6 `presentation-craft/reference/` files, the 4 opencode command wrappers, the 2 slop fixtures. Complexity: complex (the prose craft and behaviour). Depends on: Workstream B for craft content; Workstream D for the scripts and grammar the skills invoke. Tasks: T-002, T-050 to T-060.
- **Workstream E: integrate-and-verify.** Files: the 6 generated output trees. Complexity: simple (mechanical, plus manual smoke tests). Depends on: A, C, D. Tasks: T-070 to T-073.

A, B, and D run concurrently in Wave 1 and share no files. C is Wave 2 and waits on B and D. E is Wave 3. Workstream B is the critical path because it is interactive and gates the largest workstream.

---

## Implementation order

**Wave 0 (validation scaffolding).**
1. T-001: write `tests/generate-fixture-template.py` (uses python-pptx to build a minimal template with named layouts: title, section divider, statement, title-and-content, two-column) and run it to produce `tests/fixtures/sample-template.pptx`.
2. T-003: write `presentation-craft/reference/deck-spec.md` defining the grammar (a deck spec is markdown: a frontmatter block with `deck`, `audience`; then one `## Slide N` per slide carrying `layout: <role>` and labelled fields such as `Title:`, `Body:`, `Notes:`); write `tests/fixtures/sample-deck.md` conforming to it.
3. T-002: write `slop-check/fixtures/clean-deck.md` and `sloppy-deck.md` (the sloppy one carrying the five planted defects).
4. T-004: write `tests/test_render.py` (stdlib `unittest`) with the four assertions; confirm it fails because `render.py` is absent.

**Wave 1 (A, B, D in parallel).**
5. T-010 to T-019 (Workstream A): create `package.json` + `.gitignore`; copy the 5 repo-agnostic pipeline files from `build`; write `body-rewrites.js` (`/slides:` regex), `providers.js` (5 trees, no excludes), `version-carriers.js` (4 carriers); copy `check-sync.js`; port the 4 transformer tests; write `skill-contract.test.js` with the slides ceilings; write the 4 manifests; write the 5 repo docs.
6. T-030 to T-033 (Workstream D): write `pptxlib.py` (the five helpers); write `inspect_template.py`; write `make_template.py`; write `render.py` until `test_render.py` passes.
7. T-040 (Workstream B): James and Claude review the 8 source files plus the Graphic Continuum together, two passes (storytelling/narrative files, then presenting/visual/data files), recording extracted principles and James's own anti-patterns into `notes/source-review.md`, each mapped to a target reference doc.

**Wave 2 (Workstream C).**
8. T-051: write `slop.md` (the full taxonomy; must cover every planted fixture defect).
9. T-050: write `presentation-craft/SKILL.md` (protocol + operational slop detector + reference links).
10. T-052 to T-055: write `narrative.md`, `slides.md`, `data-viz.md`, `delivery.md` from `notes/source-review.md`.
11. T-056 to T-059: write the four command `SKILL.md` files.
12. T-060: write the four opencode command wrappers.

**Wave 3 (Workstream E).**
13. T-070: run `npm run build`; commit the 6 generated trees.
14. T-071: run `npm run check-sync`, `npm test`, `python3 -m unittest discover tests`; fix any drift or failure.
15. T-072: end-to-end run in Claude Code (`teach-slides` to `narrative` to `build-deck` to `slop-check`); open the `.pptx`; run `slop-check` on both fixtures.
16. T-073: smoke-test one skill in Codex and one in opencode.

---

## Verification

**Automated.**
- `npm run build` exits 0 and emits all 6 output trees (T-070).
- `npm run check-sync` exits 0 on a clean committed tree: version parity across the 4 carriers, no output drift (T-071).
- `npm test` exits 0: `builder.test.js` (no `$ARGUMENTS`/`/slides:` leak into non-Claude trees), `transform.test.js`, `manifests.test.js`, `check-sync.test.js`, `skill-contract.test.js` (frontmatter + line ceilings) (T-071).
- `python3 -m unittest discover tests` exits 0: `test_render.py` asserts slide count, per-slide layout, placeholder text, and the absence of any text box outside the template's placeholders (T-071).

**Manual (the qualitative core).**
- Run the full arc in Claude Code on a fresh project: `teach-slides` writes a complete `.slides/` directory; `narrative` asks discovery questions before generating and produces a readable deck spec; `build-deck` renders a `.pptx`; open it in PowerPoint and confirm it uses the template's layouts and carries no strapline, no ad copy, no sensational titles (T-072).
- Run `slop-check` on `sloppy-deck.md`: confirm it flags all five planted defects (bottom strapline, ad-copy line, sensational title, em dash, 7-bullet slide). Run it on `clean-deck.md`: confirm zero high-severity findings (T-072).
- Smoke-test in Codex (`$skill build-deck`) and opencode (skill tool): confirm invocation resolves and no Claude-only syntax is visible (T-073).

**What to look for.** The pass bar for T-072 is the requirement that started this whole pack: a stranger looking at the generated deck should not be able to say "AI made that" without doubt. A deck that renders cleanly but reads like ad copy is a fail, not a pass.

---

## Self-review

- **Spec coverage.** REQ-001 to REQ-007 each map to implementation tasks (REQ-001: T-031/032/056; REQ-002: T-057; REQ-003: T-001/003/004/030-033/058; REQ-004: T-002/051/059 + embedded in 057/058; REQ-005: T-040/052-055; REQ-006: T-010-019/070/071/073; REQ-007: T-018/019/070). Pass.
- **Requirement/decision coverage.** Every REQ appears in the execution manifest and the verification plan. D-001 to D-012 are realised across the file map and tasks (D-001 the 5-skill set; D-002/D-011 the renderer tasks; D-003/D-004 the pipeline tasks; D-005 teach-slides; D-006 T-003; D-007 T-051; D-008 T-040; D-009 T-052-055; D-010 Out of scope; D-012 T-054). Pass.
- **Placeholder scan.** No "TBD", no "handle appropriately", no "follow existing patterns" without naming them, no "similar to Task N". The genuinely emergent content (craft references) is handled by a concrete gated task (T-040) producing a concrete artifact, not a deferral. Pass.
- **Type consistency.** `.slides/` directory, `context.md`/`brand.json`/`template.pptx`, deck spec, the five `pptxlib` helpers, and the six reference files are named identically throughout. Pass.
- **File map matches steps.** Every file in the map appears in a task; every task's `files_modified` appears in the map. Pass.
- **All sections present.** Every required section exists; N/A sections (Data impact, Observability, UI contract, Workflow artifacts) state why. Pass.
- **Execution manifest validity.** Every task has all 8 fields. Same-wave tasks share no `files_modified` (checked per wave). Pass.
- **Observability coverage.** N/A justified (no production deployment). Pass.
- **Dependency justification.** python-pptx has license, maintenance, size, and necessity stated; Node.js noted as contributor-only; npm and test-framework dependencies explicitly zero. Pass.
