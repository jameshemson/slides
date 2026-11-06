# slides

A skill pack that takes you from a vague idea to a finished, on-brand, slop-free PowerPoint deck. Seven skills for Claude Code, Codex, and OpenCode, and all seven are portable across every harness.

## Skills

| Skill | What it does |
|-------|-------------|
| `/slides:slides` | **Start here.** The light route: a short grill on who the deck is for and what they should think, feel and do, the story shown back as headers for your approval, then the build with Anthropic's `pptx` skill and a check of fonts and colours against your brand |
| `presentation-craft` | Shared knowledge base on presentation craft. Not invoked directly. The five skills of the full route draw on it |
| `/slides:teach-slides` | Onboards you to presentation craft: narrative, structure, design, and how to avoid slop |
| `/slides:narrative` | Shapes a vague idea into a tight, audience-aware deck story |
| `/slides:build-deck` | Composes an on-brand `.pptx` deck as code from a narrative and your brand profile: a per-deck pptxgenjs script written under your design tokens, run inside Node's permission model, and gated by a mechanical lint (a template is optional; native charts included) |
| `/slides:slop-check` | Audits a deck for generic, AI-flavoured slop and reports fixes |
| `/slides:revise` | Changes a rendered deck by conversation — syncs or extracts its spec, reconciles hand-edits, and re-renders through the same gates |

Every user-invocable skill works standalone. Run `/slides:narrative pitch our Q3 roadmap` without the full pipeline, or chain them: shape the story, build the deck, then slop-check it.

## Install

**Claude Code**

```
claude plugin marketplace add jameshemson/slides
claude plugin install slides@slides
```

**OpenCode** — copy the `.opencode/` directory (preserving the leading dot) into your project so the final layout is `<your-project>/.opencode/skills/<skill-name>/SKILL.md` and `<your-project>/.opencode/commands/<command-name>.md`. OpenCode discovers skills from those paths. Once copied, the five user-invocable skills are invocable as flat slash commands: `/teach-slides`, `/narrative`, `/build-deck`, `/slop-check`, `/revise`. Each command thin-wraps the matching bundled skill.

**Codex** (two paths, either works):

Via Plugins UI / CLI:

```
codex plugin marketplace add jameshemson/slides
codex plugin install slides/slides
```

Or via repo-local discovery: copy the `.agents/` directory into your project so the final layout is `<your-project>/.agents/skills/<skill-name>/SKILL.md`. Codex picks it up automatically.

All seven skills are available in every harness. Unlike a typical orchestrated pack, no skill depends on Claude-only sub-agent or Task tooling, so nothing is excluded from OpenCode or Codex output.

## Requirements

Only `/slides:build-deck` and `/slides:revise` need anything beyond the skill files — `revise` re-renders through the same path, and can extract a spec from an existing `.pptx`:

- **Python 3.9+** and **python-pptx** (`pip install python-pptx`), always: the post-render lint, the stamp, the round trip, and the fallback renderer.
- **Node 22+** and **pptxgenjs 4.0.1** for the default path, in which the deck is composed as a per-deck script: `npm install --prefix .slides pptxgenjs@4.0.1 --no-audit --no-fund` once per project. The script runs under `node --permission` with read access to the project and write access to the deck's directory only. Without Node 22+ or pptxgenjs, `build-deck` renders through the Python fallback exactly as before.
- **matplotlib** (`pip install matplotlib`) is optional: it draws `Chart:` slides on the fallback path and powers the font-availability check. Without it, fallback chart slides become a "VISUAL TO ADD" note.
- **LibreOffice** (`brew install --cask libreoffice`) is optional: it enables the automatic render-back visual check. A brand font that is not installed on the machine is reported (`check_fonts.py`) and substituted in that preview only; the deck file always names the brand font.

On a managed macOS Python, add `--break-system-packages` to the `pip install`, or use a virtualenv. The other four skills are prompt-only and need no dependencies.

## Compatibility

| Skill | Claude Code | OpenCode | Codex |
|-------|:-----------:|:--------:|:-----:|
| `presentation-craft` | ✓ | ✓ | ✓ |
| `teach-slides` | ✓ | ✓ | ✓ |
| `narrative` | ✓ | ✓ | ✓ |
| `build-deck` | ✓ | ✓ | ✓ |
| `slides` | ✓ | ✓ | ✓ |
| `slop-check` | ✓ | ✓ | ✓ |
| `revise` | ✓ | ✓ | ✓ |

See [HARNESSES.md](HARNESSES.md) for the full capability matrix and install story.

## How it works

**The light route.** `/slides:slides` does it in one go. It asks who the deck is for, whether it's presented or read, and what they should think, feel and do. It shows the story back as slide headers, and builds nothing until you approve them. Then it builds with Anthropic's `pptx` skill and checks the deck's fonts and colours against your brand. It needs python-pptx, and works best where the `pptx` skill is installed. Your brand is captured once, from a template or an on-brand deck, so every deck starts from the same file.

**The full route.** The other skills move an idea through five stages:

1. **Learn** — `/slides:teach-slides` grounds you in presentation craft: how to find the through-line, structure a deck, design slides that read, and recognise slop before it ships. It also captures your brand into a `.slides/` profile the other skills read; point it at a template or an existing deck and it reads your fonts and colours straight from that file rather than asking you to type them. And if `.slides/` is missing when you run `/slides:build-deck` or `/slides:narrative`, they offer to set up your brand from a template or deck in one step, so you are never left with an off-brand deck.
2. **Shape** — `/slides:narrative` turns a vague brief into a concrete story: the audience, the one thing they should remember, the spine of the argument, and a slide-by-slide outline.
3. **Build** — `/slides:build-deck` composes the deck as code: from the narrative's deck-level brief (`structure:`, `motif:`) and each slide's `Brief:`, it writes a per-deck pptxgenjs script under your brand's design tokens, runs it inside Node's permission model, and gates the file — every visible run held to an explicit token colour, a type-scale size, the brand font and legible contrast on its real ground, plus margins, overlap, hierarchy and an element cap — then stamps it for the round trip and rasters it for a look. On request, or without Node, the Python renderer draws every slide from the same tokens (or fills your own template's layouts).
4. **Check** — `/slides:slop-check` audits a finished deck for generic, AI-flavoured slop — hollow phrasing, filler bullets, decorative-but-empty visuals — and reports concrete fixes.
5. **Revise** — `/slides:revise` closes the loop: point it at the rendered `.pptx`, hand-edit a title in PowerPoint or LibreOffice first if you want to see it work, and it names the edit before anything is overwritten — nothing gets clobbered without a yes. To try this yourself: render a deck, change one slide's title in PowerPoint, save, then run `/slides:revise deck.pptx` and confirm it reports the title as changed and asks whether to fold it into the spec before it re-renders.

`presentation-craft` is the non-invocable knowledge base the full route reads from. Editing craft guidance in one place keeps all five user-facing skills consistent.

Skill prompts are intentionally kept compact. Detailed craft guidance lives in reference files under `presentation-craft/reference/`, and `npm test` enforces hard line ceilings for the main skill prompts.

Generated skill outputs are committed artifacts. When changing `source/skills/`, run `npm run build` and commit the source changes, regenerated provider outputs, and any test updates together. `npm run check-sync` intentionally fails on an uncommitted source/output change set because it compares generated outputs against git.

## Standalone use

Each user-invocable skill is useful on its own:

- `/slides:teach-slides` — Learn presentation craft without building a deck
- `/slides:narrative shape a talk on our hiring plan` — Get a tight deck story from a rough idea
- `/slides:build-deck` — Render a `.pptx` from a narrative you already have
- `/slides:slop-check` — Audit any deck for slop, not just ones built with this pack
- `/slides:revise deck.pptx` — Change a rendered deck by conversation, even one you didn't build with this pack

## Roadmap

- **Done in 0.20.0: composition by code.** The model composes each deck as a pptxgenjs script under the brand tokens; the lint gates the file; the Python renderer is the fallback.
- **Where Anthropic's `pptx` skill is installed, `build-deck` runs its validator after the lint; using its thumbnail grid in `slop-check` and `revise` is next.** That skill is proprietary, so the pack only ever calls it by path.

## License

MIT
