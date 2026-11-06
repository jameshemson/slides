# Slides Plugin

A skill pack that takes someone from a vague idea to a finished, on-brand, slop-free PowerPoint deck. Seven skills: `presentation-craft` (shared knowledge, non-invocable) plus six user-invocable skills: `slides`, the light route to start with, and `teach-slides`, `narrative`, `build-deck`, `slop-check`, `revise`.

## Design philosophy

The pack constrains to a brand's *identity*, not to a house style, and leaves *composition* to the model. Guardrails and freedom are separated on purpose — changes should preserve that separation:

- **Identity is the constraint.** Colour and type come from the user's own brand, captured as design tokens (with logo and shape language to follow); the grid and the register-keyed type ladder are the pack's own defaults, overridable per key. Every drawn element must resolve to a token; a mechanical lint enforces it, so nothing goes off-brand.
- **Composition is the craft.** How a slide is arranged is the model's judgement, per deck: by default the model composes each deck as a pptxgenjs script (`<deck>.build.cjs`) under the brand tokens, run inside Node's permission model, and the lint gates the file (`lint_pptx.py`: every visible run on-token, on-scale, in the brand font and legible on its real ground). We never impose a "slides-skill look" — a finished deck should read as *the brand*, not as this tool. The Python renderer (`render.py`) is the fallback for machines without Node 22+ and for template fidelity.
- **Extract identity, not layout.** Faithfully filling a template's placeholders reproduces its layouts — *frozen composition thinking*: equity when the template is genuinely well-made, debt when it is the usual restrictive corporate template (which most are). Brand-constrained composition from tokens — the `composed`/`freeform` path and the six drawn fixed roles — is the default (`"fidelity": "brand"`, also the absent-key default), so a weak template's debt is never inherited; template placeholder-fill is the explicit opt-in (`"fidelity": "template"`) for the good template whose layouts are worth standing on.
- **No generated imagery, no slop.** Visual meaning is built from structured, on-token elements (the composed primitives and the freeform placer), never AI-generated images; a `Visual:` note defers real photography to a human. An adversarial slop-check guards the prose.
- **The lint is the only rigidity.** On-token colour, type-scale size, on-grid, no overlap, text hierarchy (rank-2 strictly below rank-1), and the element cap are absolute; composition quality is advisory. Constrain what is unsafe; leave the rest free.

The craft behind this lives in `source/skills/presentation-craft/reference/` (`slides.md`, `composition.md`, `composing-in-code.md`, `design-research.md`).

## Structure

### Source (single source of truth)

- `source/skills/` — all skill source files. Edit here, not in the generated output directories.
- `source/commands/` — OpenCode slash-command wrappers. Edit here.

### Generated output (committed, do not edit directly)

- `.claude/skills/` — Claude Code output. Identity transform; source is emitted as-is.
  - `presentation-craft/` — Shared presentation-craft knowledge base. Non-invocable.
  - `teach-slides/` — Onboards a user to presentation craft.
  - `narrative/` — Shapes a vague idea into a deck story.
  - `build-deck/` — Renders an on-brand `.pptx` deck.
  - `slop-check/` — Audits a deck for generic, AI-flavoured slop.
  - `revise/` — Changes a rendered deck by conversation; syncs or extracts its spec, re-renders through the gates.
- `.opencode/skills/` — OpenCode output. Contains all seven skills. Claude-only fields stripped, `$ARGUMENTS` and `/slides:` references rewritten.
- `.opencode/commands/` — OpenCode slash commands. Six flat `.md` files, each a thin `@.opencode/skills/<name>/SKILL.md` include so users can invoke the six user-invocable skills as `/slides`, `/teach-slides`, `/narrative`, `/build-deck`, `/slop-check`, `/revise`. Do not edit directly.
- `.agents/skills/` — Codex output for repo-local discovery. All seven skills.
- `plugins/slides/skills/` — Codex output for Plugins UI install packaging. Byte-identical to `.agents/skills/` (enforced by a 3-way sandbox test in `builder.test.js`). Do not edit directly.
- `.codex/skills/` — Codex cross-harness bridge. Byte-identical to `.agents/skills/` via shared `codexRewrites` by reference. Exists so tools that cross-read `.codex/skills/` (notably Cursor) can discover our skills. Do not edit directly.

All seven skills are portable: nothing depends on Claude-only sub-agent or Task tooling, so no provider has an `exclude` list.

### Static manifests (hand-authored, committed)

- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — Claude Code plugin descriptors.
- `plugins/slides/.codex-plugin/plugin.json` — Codex plugin manifest.
- `.agents/plugins/marketplace.json` — Codex marketplace catalog pointing at `./plugins/slides`.

These four JSON files are NOT regenerated by `npm run build`. Edit them by hand; version bumps must be applied across all four version carriers together (see "Versioning" below).

## Conventions

- Each skill has a SKILL.md with frontmatter (name, description, and, for user-invocable skills, user-invocable, argument-hint, model, effort, context).
- Reference files go in `reference/` subdirectories within the skill that owns them — primarily `presentation-craft/reference/`.
- Cross-skill references use the `/slides:skillname` invocation format (Claude syntax; transformer rewrites for other harnesses).
- `presentation-craft` is the shared knowledge base; the five skills of the full route draw on it rather than duplicating craft guidance. `slides` stands alone on purpose: it leaves layout to Anthropic's `pptx` skill and holds only fonts and colours to the brand, through its own `scripts/brand.py`.
- All skills must work standalone in every harness.

## Build pipeline

```
npm run build       # regenerate all output directories from source/skills/
npm run check-sync  # verify version parity + outputs match what is committed
npm test            # run transformer, builder, manifest, skill-contract, and check-sync tests
```

Transformer scripts live in `scripts/`. Harness capability details and transform rules are in `HARNESSES.md`.

### Pre-push checklist

Full version-drift coverage requires BOTH commands to pass before push:

- `npm run check-sync` — catches structural drift of generated output directories AND version drift via a pre-build parity assertion across all four version carriers listed in `scripts/transformers/version-carriers.js`.
- `npm test` — cross-checks the same version parity in-process via `manifests.test.js` (reading the same `VERSION_CARRIERS` list), AND verifies the drift-detection mechanism itself by spawning `check-sync.js` with a mismatched version in `check-sync.test.js`.

Neither command alone is a complete gate. CI (`.github/workflows/ci.yml`) runs the same three gates on push and PR to main; the Node-dependent tests (`tests/test_build_script.py`, `tests/test_sandbox.py`) need pptxgenjs 4.0.1 under `.build/runtime` (`npm install --prefix .build/runtime pptxgenjs@4.0.1`) and skip in CI.

## Versioning

Version lives in four files that MUST be bumped together:

- `.claude-plugin/plugin.json` (Claude Code plugin)
- `.claude-plugin/marketplace.json` (Claude Code marketplace — `plugins[0].version`)
- `plugins/slides/.codex-plugin/plugin.json` (Codex plugin)
- `package.json` (build pipeline)

The canonical list lives in `scripts/transformers/version-carriers.js`. `npm run check-sync` fails if any of the four disagree. `manifests.test.js` enforces the same parity in-process. See the pre-push checklist above.

## Testing

Test each skill standalone before testing the full idea-to-deck flow. See README.md for verification steps.

After any source change, run `npm run build` before committing.

### Testing caveats (accepted risks)

One known risk in the current test suite, judged acceptable for this single-maintainer repo:

- **`check-sync.test.js` mutates a committed file.** The test writes `"99.99.99"` into `plugins/slides/.codex-plugin/plugin.json`, spawns `check-sync.js` synchronously, and restores in a `try/finally`. If Node dies between the write and the restore (vanishingly unlikely — `spawnSync` is synchronous), the working tree is dirty. Recovery: `git checkout -- plugins/slides/.codex-plugin/plugin.json`. Concurrency with other writers to the same file is avoided by `--test-concurrency=1` in the `test` script; do not remove that flag without redesigning the test to sandbox the file.
