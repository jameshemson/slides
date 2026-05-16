# Harness capability matrix

This table is the authoritative reference for transformer decisions. Any new skill that depends on a row marked "No" for a given harness must be excluded from that harness's output. Today, none of the five slides skills do — all five are portable.

| Capability | Claude Code | OpenCode | Codex |
| --- | --- | --- | --- |
| Repo-local skill directory | `.claude/skills/` | `.opencode/skills/` (also reads `.claude/skills/`) | `.agents/skills/` |
| Runtime `$ARGUMENTS` substitution in SKILL.md | Yes | No | No |
| Slash-command skill invocation (`/slides:name`) | Yes | Yes — via `.opencode/commands/*.md` wrappers shipped by this plugin (flat names: `/narrative` etc.) | No — use `$<name>` or `$slides:<name>` (plugin-namespaced) |
| Plugin distribution | Yes — `.claude-plugin/` | No — copy `.opencode/` bundle | Yes — `codex plugin marketplace add smonggliddery/slides` |
| Sub-agent / Task tools (`Agent`, `TaskCreate`, etc.) | Yes | No | No |
| Per-skill `model` / `effort` / `context` frontmatter | Yes | No | No |
| Per-skill `allowed-tools` frontmatter | Yes | No | No |

## Skill availability

| Skill | Claude Code | OpenCode | Codex | Notes |
| --- | --- | --- | --- | --- |
| `presentation-craft` | Yes | Yes | Yes | Portable. Shared knowledge base, non-invocable |
| `teach-slides` | Yes | Yes | Yes | Portable |
| `narrative` | Yes | Yes | Yes | Portable |
| `build-deck` | Yes | Yes | Yes | Portable |
| `slop-check` | Yes | Yes | Yes | Portable |

All five skills run on every harness. No skill relies on Claude-only sub-agent or Task tooling, so no provider has an `exclude` list — every output tree contains the full five-skill set.

## OpenCode install story

OpenCode reads both `.opencode/skills/` and `.claude/skills/`. This means opening this repo root directly in OpenCode produces duplicate entries for the five skills (one from each path).

**Supported OpenCode path**: copy this repo's `.opencode/` directory (including the leading dot) into the target project so the final layout is `<target-project>/.opencode/skills/<skill-name>/SKILL.md` and `<target-project>/.opencode/commands/<command-name>.md`. Do not flatten to `<target-project>/skills/` — OpenCode will not find skills there. Do not point OpenCode at this repo root directly (duplicate skills will appear).

**Slash command bundle.** In addition to the five skills at `.opencode/skills/`, we ship four OpenCode slash commands at `.opencode/commands/` (`teach-slides.md`, `narrative.md`, `build-deck.md`, `slop-check.md`) — one per user-invocable skill. `presentation-craft` is a non-invocable knowledge base and has no command wrapper. Each command's body is a single `@.opencode/skills/<name>/SKILL.md` line — OpenCode resolves `@<path>` against the project worktree and inlines the file content at invocation time (verified against OpenCode `packages/opencode/src/session/prompt.ts`). Users invoke as `/narrative <task>` etc.; pass-through arguments become the skill's task input. Commands use flat (non-namespaced) names: collision with an unrelated local command in the user's project is possible and requires renaming one of the two.

## Codex install story

Two supported paths:

**Repo-local discovery.** Codex reads skills directly from `.agents/skills/` when a user opens the repo as their workspace. The committed `.agents/skills/` tree is a distribution artifact — no build step required for consumers. To add these skills to another project without installing the plugin, copy this repo's `.agents/` directory into that project so the final layout is `<target-project>/.agents/skills/<skill-name>/SKILL.md`.

**Plugins UI / CLI install.** Users who don't want to clone the repo can register this repo as a Codex marketplace and install the `slides` plugin from the Plugins UI:

```sh
codex plugin marketplace add smonggliddery/slides
codex plugin install slides/slides
```

The marketplace manifest is at `.agents/plugins/marketplace.json`; the plugin manifest is at `plugins/slides/.codex-plugin/plugin.json`. Both are hand-authored and committed. All five skills ship in the plugin.

A user who both clones the repo AND installs the plugin will see duplicate entries for the five skills. The two copies are byte-identical (enforced by a sandbox byte-equality test); behavior is the same, only the UI listing is noisier.

**Cross-harness skill bridge.** In addition to `.agents/skills/` (Codex CLI primary) and `plugins/slides/skills/` (Codex plugin package), this repo also emits `.codex/skills/`. Byte-identical to `.agents/skills/` (enforced by a 3-way sandbox byte-equality test — `codex` ↔ `codex-plugin` ↔ `codex-cross` share `codexRewrites` by reference). This path exists so cross-reading harnesses — notably Cursor, which documents `.codex/skills/` as a scan path — can discover the skills without additional configuration.

## Source and build

Skills are authored in `source/skills/` using Claude syntax (`$ARGUMENTS`, `/slides:<name>` slash references). OpenCode slash commands are authored in `source/commands/`. The build script (`npm run build`) transforms and writes provider-specific outputs to `.claude/skills/`, `.opencode/skills/`, `.agents/skills/`, `plugins/slides/skills/`, `.codex/skills/`, and `.opencode/commands/`. All output directories are committed.

The `codex`, `codex-plugin`, and `codex-cross` providers share the same rewrite config by identity in `scripts/transformers/providers.js`, so `.agents/skills/` (repo-local), `plugins/slides/skills/` (plugin-packaged), and `.codex/skills/` (cross-harness bridge) are always byte-identical. A 3-way sandbox test in `builder.test.js` enforces this invariant.

Transforms applied for non-Claude targets:
- `argumentsToken`: standalone `$ARGUMENTS` lines become a prose instruction; inline occurrences become "the user's request".
- `skillReference`: `/slides:<name>` references become `` `<name>` ``.
- `removeClaudeOnlySections`: `<!-- claude-only -->` … `<!-- /claude-only -->` blocks are stripped.
- Frontmatter: Claude-only fields (`user-invocable`, `argument-hint`, `model`, `effort`, `context`, `allowed-tools`) are stripped.
