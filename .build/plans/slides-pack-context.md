# slides-pack — context

Repo conventions, discovered patterns, constraints, and assumptions for the `slides` skill-pack build. Read alongside `slides-pack-plan.md` and `slides-pack-requirements.md`.

## Repo

- Path: `/Users/jameshemson/repos/slides`. Greenfield. `git init`'d at the start of this workflow; base commit `2b661ae` holds `PLAN.md` + `notes/` + `.claude/` + `.gitignore`.
- Plugin name: `slides`. Invocations: `/slides:teach-slides`, `/slides:narrative`, `/slides:build-deck`, `/slides:slop-check`. `presentation-craft` is a non-invocable dependency skill.
- Reference repos (read-only models, not modified):
  - `build` pipeline: `/Users/jameshemson/.claude/plugins/marketplaces/build/` (also `/Users/jameshemson/repos/build/`).
  - `pm-skills`: `/Users/jameshemson/.claude/plugins/marketplaces/pm-skills/` — core+command layout, Reflex Rejection / Slop Test patterns.
  - `impeccable`: `/Users/jameshemson/.claude/plugins/marketplaces/impeccable/` — `.impeccable/` persisted-context pattern, teach skill, context-missing routing.

## Tooling state (verified this session)

- `python3` = `/opt/homebrew/bin/python3`. `python-pptx 1.0.2` installed into user site-packages (`pip install --user --break-system-packages`); importable by system `python3`. So `python3 -m unittest discover tests` works without a venv.
- `node v25.9.0`. ES modules supported. No npm dependencies (the pipeline is pure Node stdlib; tests use `node:test`).
- Python install was externally-managed (PEP 668); end users get the same wall. `build-deck`/`teach-slides` must probe for `python3` + `python-pptx` and print the `pip install python-pptx` remedy (note: end users may also need `--break-system-packages` or a venv — the skill should mention both).

## Build pipeline — porting facts (Workstream A)

Source of truth for what to copy verbatim vs rewrite. Confirmed by reading the `build` repo.

**Copy VERBATIM from `build`** (repo-agnostic):
- `scripts/build.js`, `scripts/check-sync.js`
- `scripts/transformers/utils.js`, `transform.js`, `builder.js`, `frontmatter.js`

**Rewrite (repo-specific)** — 3 files:
- `scripts/transformers/body-rewrites.js` — change the slash-command regex `/\/build:([\w-]+)/g` → `/\/slides:([\w-]+)/g`. Everything else identical.
- `scripts/transformers/providers.js` — 5 providers: `claude` → `.claude/skills`, `opencode` → `.opencode/skills`, `codex` → `.agents/skills`, `codex-plugin` → `plugins/slides/skills`, `codex-cross` → `.codex/skills`. **`exclude: []` for EVERY provider** (D-004: all 5 slides skills are portable — `build` excludes `build`/`eval` because those use orchestration tools; slides has none). `codex`/`codex-plugin`/`codex-cross` MUST share one `codexRewrites` object by reference (byte-equality contract). `COMMAND_PROVIDERS` = opencode → `.opencode/commands`.
- `scripts/transformers/version-carriers.js` — 4 carriers: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (`j.plugins?.[0]?.version`), `plugins/slides/.codex-plugin/plugin.json`, `package.json`.

**Tests** — PORT (adapt, not verbatim): `build`'s `*.test.js` reference build-specific things (excluded skills `build`/`eval`, "4 portable skills", real `source/skills/` tree, marketplace listing). Port `builder.test.js`, `transform.test.js`, `manifests.test.js`, `check-sync.test.js` adjusting expectations to the slides repo (5 skills, 0 excludes, 4 manifests). `skill-contract.test.js` is new: assert every `SKILL.md` has `name`+`description` frontmatter and enforce line ceilings (presentation-craft ≤210, command skills ≤170, reference files ≤190).

**Frontmatter Claude-only fields.** `build`'s `frontmatter.js` `CLAUDE_ONLY_FIELDS` set (copied verbatim) strips: `user-invocable`, `argument-hint`, `model`, `effort`, `context`, `allowed-tools` for non-Claude targets. **CRITICAL spelling note:** `build` uses `user-invocable` (with a 'c'); `pm-skills` SKILL.md files use `user-invokable` (with a 'k'). The slides repo copies `build`'s `frontmatter.js`, so slides command `SKILL.md` files MUST declare the field with the spelling that `frontmatter.js` actually strips — read `build/scripts/transformers/frontmatter.js` and match it exactly, or the field leaks into Codex/opencode output. Verify against the source file; do not trust either exploration summary blindly.

**`package.json`** (model from `build`): `{"name": "slides-plugin", "version": "<X.Y.Z>", "type": "module", "scripts": {"build": "node scripts/build.js", "check-sync": "node scripts/check-sync.js", "test": "node --test --test-concurrency=1 scripts/transformers/*.test.js"}}`. Zero dependencies.

**`source/` layout.** `source/skills/<skill>/SKILL.md` (+ `reference/`, `scripts/`, `fixtures/` subdirs as needed). `source/commands/<name>.md` — opencode wrappers: frontmatter with a `description:` field, then a single `@.opencode/skills/<name>/SKILL.md` include line. One wrapper per user-invocable skill; none for `presentation-craft`.

## Skill conventions (from pm-skills + impeccable)

- Core skill `presentation-craft`: no `user-invocable` field (non-invocable). Command skills: `user-invocable: true` (spelling per `frontmatter.js`) + `args:` if they take input.
- Command skills load the core via a `## MANDATORY PREPARATION`-style section: prose ("Use the presentation-craft skill — it carries the Context Gathering Protocol; follow it before proceeding; if no `.slides/` context exists, run teach-slides first") plus relative-path links to reference files: `../presentation-craft/reference/<file>.md`.
- Cross-skill script references use relative paths: `teach-slides` calls `../build-deck/scripts/inspect_template.py` and `make_template.py` (the `../product-management/reference/` pattern).
- `.slides/` persisted-context dir (D-005): `context.md` (human+LLM readable), `brand.json` (machine readable for `render.py`), `template.pptx` (the user's template copied in). Mirrors impeccable's `.impeccable/` sidecar pattern.
- Interactive Q&A: portable prose by default. Claude-specific "use the AskUserQuestion tool" guidance is wrapped in `<!-- claude-only -->` … `<!-- /claude-only -->` blocks so `body-rewrites.js` strips it for Codex/opencode (D-004).

## Craft-content constraint (Workstream C, the highest-risk area)

The reference files `narrative.md`, `slides.md`, `data-viz.md`, `delivery.md`, `slop.md` and the operational detector in `presentation-craft/SKILL.md` are written by **transcribing and structuring** `notes/source-review.md`, `notes/approach.md`, and `notes/slop-detector.md`. Rules:
- Source content ONLY from those three notes. Do not re-read the original PPTX/PDF source files; do not invent or pad craft.
- Principle-only: strip ALL named examples (decision 3 in `source-review.md`). No Wall-E, TOMS, Patagonia, JFK, Southwest, Bluey-as-IP, the Third Silesian War, the hole-in-the-trousers story. The notes name them as a record of source; shipped skill files teach the principle only.
- `slop.md` follows `notes/slop-detector.md` exactly: two layers (presentation slop; prose slop from `stop-slop`), two phases (reflex rejection pre-gen; slop check post-gen), the banned-phrase/structure lists, the quick checks, the 5-dimension 1-10 score (revise below 35/50).
- The emotion line: the detector passes EARNED emotion (grounded in a true, concrete thing) and catches only UNEARNED emotion (sensationalism, ad-copy hype). It must not flag "emotional language" wholesale.
- Register-aware: "one idea per slide" holds for both presented and read/data-led decks; the detector judges text *quality*, not text *presence*. A chart with 3-4 tight parallel points is not bullet soup.
- Attribution: Graphic Continuum → Schwabish & Ribecca; `stop-slop` → Hardik Pandya, github.com/hardikpandya/stop-slop, MIT; encode the public frameworks (SUCCESs/Heath, Duarte, RADA) with credit, do not reproduce third-party material.

## User constraints / decisions already settled

- Output: PowerPoint `.pptx` only (no Google Slides / Keynote / Marp / HTML).
- `.pptx` produced by template-fill via python-pptx — fill the user's template's own layouts/placeholders; code NEVER sets fonts, colours, or coordinates (D-002).
- Brand-agnostic: the pack works for any user's brand; `teach-slides` captures it. No James-specific brand baked in.
- Series of 5 skills, not one skill with modes (D-001). No orchestrator in v1 (D-010) — skills chain via "What's Next" pointers.
- Runs on Claude Code, Codex, opencode from one `source/` tree (REQ-006). UI out of scope.

## Open questions (proceeding with stated defaults — none block the build)

- License: MIT assumed (matches `build`). Trivial one-file change if wrong.
- A-004: one brand profile per project (one `.slides/`). Additive to change later.
- A-005: Codex repo-local discovery `.agents/skills/` per `build/HARNESSES.md` (verified 2026-04). Re-verify before release.
- Graphic Continuum attribution wording: credit Schwabish & Ribecca; exact line confirmable later.

## Out of scope

Orchestrator skill; UI; multiple brand profiles per project; native rendering of exotic chart types (sankey, marimekko — placeholder slide + run-summary note instead); a designed bespoke template (`make_template.py` makes a functional starter); a marketing website; non-`.pptx` export; animations beyond what the template carries.
