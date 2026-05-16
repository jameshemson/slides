---
name: build-deck
description: Render a deck spec into an on-brand .pptx by filling the user's own template, after a slop check on the spec.
user-invocable: true
argument-hint: "[path to a .deck.md spec]"
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. If `.slides/` is absent or incomplete, run /slides:teach-slides first, then resume here.

Read [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the spec format and [slop.md](../presentation-craft/reference/slop.md) for the detector you run before rendering.

---

$ARGUMENTS

You render a deck spec into a real `.pptx`. The spec carries the content; the user's template in `.slides/` carries the look. The renderer fills the template's existing placeholders and never adds a shape, so the output stays on-brand.

If the user did not name a spec, ask which `.deck.md` file to render. If no spec exists yet, point them at /slides:narrative to write one.

## Step 1: Check the toolchain

The renderer needs Python. Run `python3 --version` and `python3 -c "import pptx"`.

If `python3` is missing, tell the user to install Python 3.9 or newer. If the `import pptx` line fails, give them the remedy:

```
pip install python-pptx
```

On macOS with a managed Python that command can refuse. Tell the user they can run `pip install --break-system-packages python-pptx`, or make a virtualenv. Wait for the toolchain to work before rendering.

## Step 2: Run the slop detector on the spec

Render slop and you ship slop. Run the detector on the deck spec before `render.py` touches it.

Run both layers from `slop.md`: the presentation-slop checks and the prose-slop checks, plus the five-dimension score on the notes. Catch the tacked-on strapline, the wall of text, the slide-as-script, bullet soup, restatement, the deck about the presenter, unearned hype.

Fix what you find in the spec itself. Show the user the changes and get a yes. A clean spec renders to a clean deck.

## Step 3: Render

Run `render.py` from the project root, so the relative `template` path inside `brand.json` resolves:

```
python3 scripts/render.py --spec <deck>.deck.md \
    --brand .slides/brand.json --out <deck>.pptx
```

`render.py` reads the template path from `brand.json`'s `template` key. There is no `--template` argument.

On success it exits 0 and prints a one-line summary. On a malformed spec or brand profile it exits 1, prints `error: ...` naming the offending slide, role, or key, and writes nothing.

If the render fails, read the error. It names the fault: a slide numbered out of sequence, a role with more fields than its layout has placeholders, a missing `brand.json` key. Fix the spec or, for a layout-map fault, send the user back to /slides:teach-slides. Then run again.

## Step 4: Report

Print the render summary. It states how many slides were written and which slides carry a `VISUAL TO ADD` note.

A `Visual:` field in the spec is recorded in that slide's speaker notes, prefixed `VISUAL TO ADD:`. The renderer does not draw the image, chart, or diagram. Tell the user which slides carry one and that placing the visual in PowerPoint is their step. Point them at the speaker notes, where each visual is described and the reason it belongs there is given.

Tell the user where the `.pptx` was written. To audit the finished deck, point them at /slides:slop-check.
