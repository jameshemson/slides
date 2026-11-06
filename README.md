# slides

A skill that takes you from an idea and some notes to a finished, on-brand PowerPoint deck. It asks what only you can answer, shows you the story as slide headers before anything is built, then builds the deck. For Claude Code, Codex and OpenCode.

## How it works

Ask for a deck, or run `/slides:slides` with the topic and any notes you have.

1. **A short grill.** Who is it for, and where are they on this now? Will you present it live, or will they read it alone? What should they think, feel and do afterwards? You answer in your own words, because that thinking is yours. It only asks what you haven't already told it.
2. **The story, shown back.** The one idea, the shape it chose (a story, a flow, a contrast, or tell them, tell them, tell them) and the slide headers, one line each. You change them until they read right. Nothing gets built before you say yes.
3. **The build.** Anthropic's `pptx` skill builds the deck, with your approved headers word for word. How it looks is that skill's call, within your brand.

## Your brand

The first time, point it at a template or an on-brand deck. It reads the fonts and colours into `.slides/brand.json`, or `~/.slides/brand.json` to use them for every deck, and shows you what it found. After that every deck starts from the same file, the brand becomes the deck's theme, and `scripts/brand.py check` names anything off brand by slide.

The check looks at fonts and colours only, and doesn't look inside pictures. It can only be as good as the brand file, so add any extra font or shade your brand allows.

## Install

**Claude Code**

```
claude plugin marketplace add jameshemson/slides
claude plugin install slides@slides
```

**OpenCode:** copy the `.opencode/` directory (keeping the leading dot) into your project, so the layout is `<your-project>/.opencode/skills/slides/SKILL.md` and `<your-project>/.opencode/commands/slides.md`. Then run `/slides`.

**Codex**, either way:

```
codex plugin marketplace add jameshemson/slides
codex plugin install slides/slides
```

Or copy the `.agents/` directory into your project, so the layout is `<your-project>/.agents/skills/slides/SKILL.md`.

See [HARNESSES.md](HARNESSES.md) for how each tool differs.

## Requirements

- **Python 3.9+** and **python-pptx** (`pip install python-pptx`) for the brand script. On a managed macOS Python, add `--break-system-packages`, or use a virtualenv.
- **Anthropic's `pptx` skill** for the intended build. It is proprietary, so this skill only calls it. Where it's missing, the skill says so and uses whatever that tool has, which is untested.

## Earlier versions

Up to v0.21.0 this was a pack of six skills: `teach-slides`, `narrative`, `build-deck`, `slop-check`, `revise` and `presentation-craft`, with their own renderer and lint. They were removed in v0.22.0 and are still in the repo at the `v0.21.0` tag.

## Working on it

Edit `source/skills/`, never the generated output directories. After any change, run `npm run build`, then commit the source, the regenerated outputs and any test updates together. `npm run check-sync` deliberately fails on an uncommitted source or output change, because it compares the generated outputs against git.

## License

MIT
