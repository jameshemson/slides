# Harness capability matrix

This table is the authoritative reference for transformer decisions. A skill that depends on a row marked "No" for a harness must be excluded from that harness's output. `slides` doesn't, so it ships to all three.

| Capability | Claude Code | OpenCode | Codex |
| --- | --- | --- | --- |
| Repo-local skill directory | `.claude/skills/` | `.opencode/skills/` (also reads `.claude/skills/`) | `.agents/skills/` |
| Runtime `$ARGUMENTS` substitution in SKILL.md | Yes | No | No |
| Slash-command skill invocation | Yes, `/slides:slides` | Yes, `/slides`, via the `.opencode/commands/slides.md` wrapper | No: use `$slides` or `$slides:slides` |
| Plugin distribution | Yes, `.claude-plugin/` | No: copy the `.opencode/` bundle | Yes, `codex plugin marketplace add jameshemson/slides` |
| AskUserQuestion, for the grill's one multiple-choice question | Yes | Stripped: asked as plain text | Stripped: asked as plain text |
| Runtime for `slides`: Python 3.9+ with python-pptx, for its brand script | Yes | Yes | Yes |

## The build

`slides` builds with Anthropic's `pptx` skill where that is installed. That skill is proprietary and this repo only calls it. Without it, the skill says so and builds with whatever .pptx tooling the harness has. This pack no longer ships a renderer of its own, so that fallback depends entirely on the harness and is untested on Codex and OpenCode.

## OpenCode install story

OpenCode reads both `.opencode/skills/` and `.claude/skills/`, so opening this repo root directly in OpenCode lists the skill twice.

**Supported path:** copy this repo's `.opencode/` directory (including the leading dot) into the target project, so the layout is `<target-project>/.opencode/skills/slides/SKILL.md` and `<target-project>/.opencode/commands/slides.md`. Do not flatten to `<target-project>/skills/`, because OpenCode will not find it there.

The command's body is a single `@.opencode/skills/slides/SKILL.md` line. OpenCode resolves `@<path>` against the project worktree and inlines the file at invocation time. Commands use flat names, so a local command called `slides` would collide and one of the two would need renaming.

## Codex install story

Two supported paths:

**Repo-local discovery.** Codex reads skills from `.agents/skills/` when a user opens the repo as their workspace. To add the skill to another project without installing the plugin, copy this repo's `.agents/` directory into it, so the layout is `<target-project>/.agents/skills/slides/SKILL.md`.

**Plugins UI / CLI install.**

```sh
codex plugin marketplace add jameshemson/slides
codex plugin install slides/slides
```

The marketplace manifest is at `.agents/plugins/marketplace.json` and the plugin manifest is at `plugins/slides/.codex-plugin/plugin.json`. Both are hand-authored and committed.

A user who both clones the repo and installs the plugin will see the skill twice. The two copies are byte-identical (enforced by a sandbox test), so only the listing is noisier.

**Cross-harness bridge.** This repo also emits `.codex/skills/`, byte-identical to `.agents/skills/`, so cross-reading harnesses (notably Cursor, which documents `.codex/skills/` as a scan path) can find the skill without further configuration.

## Source and build

Skills are authored in `source/skills/` using Claude syntax (`$ARGUMENTS`, `/slides:<name>` slash references). OpenCode slash commands are authored in `source/commands/`. The build script (`npm run build`) transforms and writes provider-specific outputs to `.claude/skills/`, `.opencode/skills/`, `.agents/skills/`, `plugins/slides/skills/`, `.codex/skills/`, and `.opencode/commands/`. All output directories are committed.

The `codex`, `codex-plugin`, and `codex-cross` providers share the same rewrite config by identity in `scripts/transformers/providers.js`, so their three outputs are always byte-identical. A 3-way sandbox test in `builder.test.js` enforces this.

Transforms applied for non-Claude targets:
- `argumentsToken`: standalone `$ARGUMENTS` lines become a prose instruction; inline occurrences become "the user's request".
- `skillReference`: `/slides:<name>` references become `` `<name>` ``.
- `removeClaudeOnlySections`: `<!-- claude-only -->` ... `<!-- /claude-only -->` blocks are stripped.
- Frontmatter: Claude-only fields (`user-invocable`, `argument-hint`, `model`, `effort`, `context`, `allowed-tools`) are stripped.
