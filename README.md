# slides

A skill pack that takes you from a vague idea to a finished, on-brand, slop-free PowerPoint deck. Six skills for Claude Code, Codex, and OpenCode — all six are portable across every harness.

## Skills

| Skill | What it does |
|-------|-------------|
| `presentation-craft` | Shared knowledge base on presentation craft. Not invoked directly — every other skill in the pack draws on it |
| `/slides:teach-slides` | Onboards you to presentation craft: narrative, structure, design, and how to avoid slop |
| `/slides:narrative` | Shapes a vague idea into a tight, audience-aware deck story |
| `/slides:build-deck` | Renders an on-brand `.pptx` deck from a narrative and a template, drawing native charts from chart data in the spec |
| `/slides:slop-check` | Audits a deck for generic, AI-flavoured slop and reports fixes |
| `/slides:revise` | Changes a rendered deck by conversation — syncs or extracts its spec, reconciles hand-edits, and re-renders through the same gates |

Every user-invocable skill works standalone. Run `/slides:narrative pitch our Q3 roadmap` without the full pipeline, or chain them: shape the story, build the deck, then slop-check it.

## Install

**Claude Code**

```
claude plugin add jameshemson/slides
```

**OpenCode** — copy the `.opencode/` directory (preserving the leading dot) into your project so the final layout is `<your-project>/.opencode/skills/<skill-name>/SKILL.md` and `<your-project>/.opencode/commands/<command-name>.md`. OpenCode discovers skills from those paths. Once copied, the five user-invocable skills are invocable as flat slash commands: `/teach-slides`, `/narrative`, `/build-deck`, `/slop-check`, `/revise`. Each command thin-wraps the matching bundled skill.

**Codex** (two paths, either works):

Via Plugins UI / CLI:

```
codex plugin marketplace add jameshemson/slides
codex plugin install slides/slides
```

Or via repo-local discovery: copy the `.agents/` directory into your project so the final layout is `<your-project>/.agents/skills/<skill-name>/SKILL.md`. Codex picks it up automatically.

All six skills are available in every harness. Unlike a typical orchestrated pack, no skill depends on Claude-only sub-agent or Task tooling, so nothing is excluded from OpenCode or Codex output.

## Requirements

Only `/slides:build-deck` and `/slides:revise` need anything beyond the skill files — `revise` re-renders through the same renderer, and can extract a spec from an existing `.pptx`:

- **Python 3.9+** and **python-pptx** (`pip install python-pptx`) to render a `.pptx`.
- **matplotlib** (`pip install matplotlib`) is optional, needed only to draw `Chart:` slides. Without it, chart slides fall back to a "VISUAL TO ADD" note and the rest of the deck renders normally.

On a managed macOS Python, add `--break-system-packages` to the `pip install`, or use a virtualenv. The other four skills are prompt-only and need no dependencies.

## Compatibility

| Skill | Claude Code | OpenCode | Codex |
|-------|:-----------:|:--------:|:-----:|
| `presentation-craft` | ✓ | ✓ | ✓ |
| `teach-slides` | ✓ | ✓ | ✓ |
| `narrative` | ✓ | ✓ | ✓ |
| `build-deck` | ✓ | ✓ | ✓ |
| `slop-check` | ✓ | ✓ | ✓ |
| `revise` | ✓ | ✓ | ✓ |

See [HARNESSES.md](HARNESSES.md) for the full capability matrix and install story.

## How it works

The pack moves an idea through five stages:

1. **Learn** — `/slides:teach-slides` grounds you in presentation craft: how to find the through-line, structure a deck, design slides that read, and recognise slop before it ships. It also captures your brand into a `.slides/` profile the other skills read; point it at a template or an existing deck and it reads your fonts and colours straight from that file rather than asking you to type them. And if `.slides/` is missing when you run `/slides:build-deck` or `/slides:narrative`, they offer to set up your brand from a template or deck in one step, so you are never left with an off-brand deck.
2. **Shape** — `/slides:narrative` turns a vague brief into a concrete story: the audience, the one thing they should remember, the spine of the argument, and a slide-by-slide outline.
3. **Build** — `/slides:build-deck` renders an on-brand `.pptx` from the narrative and a template, mapping content to layouts. A slide can carry a `Chart:` block (bar, column, pie, scatter, or line); the renderer draws it on-brand with matplotlib and places it on the slide. Without matplotlib installed, a chart slide degrades to a "VISUAL TO ADD" note, so the deck still builds.
4. **Check** — `/slides:slop-check` audits a finished deck for generic, AI-flavoured slop — hollow phrasing, filler bullets, decorative-but-empty visuals — and reports concrete fixes.
5. **Revise** — `/slides:revise` closes the loop: point it at the rendered `.pptx`, hand-edit a title in PowerPoint or LibreOffice first if you want to see it work, and it names the edit before anything is overwritten — nothing gets clobbered without a yes. To try this yourself: render a deck, change one slide's title in PowerPoint, save, then run `/slides:revise deck.pptx` and confirm it reports the title as changed and asks whether to fold it into the spec before it re-renders.

`presentation-craft` is the non-invocable knowledge base every other skill reads from. Editing craft guidance in one place keeps all five user-facing skills consistent.

Skill prompts are intentionally kept compact. Detailed craft guidance lives in reference files under `presentation-craft/reference/`, and `npm test` enforces hard line ceilings for the main skill prompts.

Generated skill outputs are committed artifacts. When changing `source/skills/`, run `npm run build` and commit the source changes, regenerated provider outputs, and any test updates together. `npm run check-sync` intentionally fails on an uncommitted source/output change set because it compares generated outputs against git.

## Standalone use

Each user-invocable skill is useful on its own:

- `/slides:teach-slides` — Learn presentation craft without building a deck
- `/slides:narrative shape a talk on our hiring plan` — Get a tight deck story from a rough idea
- `/slides:build-deck` — Render a `.pptx` from a narrative you already have
- `/slides:slop-check` — Audit any deck for slop, not just ones built with this pack
- `/slides:revise deck.pptx` — Change a rendered deck by conversation, even one you didn't build with this pack

## License

MIT
