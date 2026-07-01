---
name: build-deck
description: Render a deck spec into an on-brand .pptx by filling the user's own template, after a slop check on the spec.
user-invocable: true
argument-hint: "[path to a .deck.md spec]"
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. If `.slides/` is absent or incomplete, set up the brand first, then resume here: offer the fast path (`scripts/init_brand.py` reads the fonts, colours, and a layout map straight from a template or an existing deck) or the fuller /slides:teach-slides interview.

Read [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the spec format and [slop.md](../presentation-craft/reference/slop.md) for the detector you run before rendering.

---

$ARGUMENTS

You render a deck spec into a real `.pptx`. The spec carries the content; the user's template in `.slides/` carries the look. For the six fixed roles the renderer fills the template's existing placeholders and adds no shape, so the output stays on-brand. The `composed` role is the one carve-out: it draws brand-locked primitives — a `stat-row`, `card-grid`, `comparison`, `process`, `timeline`, or a `freeform` arrangement, stacked or placed on the grid — from the brand's design `tokens`, and every element must pass a mechanical lint — token colour, type-scale size, within the grid margins, no overlap, under the element cap — or the render fails with a named error. Free composition, still bounded.

If the user did not name a spec, ask which `.deck.md` file to render. If no spec exists yet, point them at /slides:narrative to write one.

## Step 1: Check the toolchain

The renderer needs Python. Run `python3 --version` and `python3 -c "import pptx"`.

If `python3` is missing, tell the user to install Python 3.9 or newer. If the `import pptx` line fails, give them the remedy:

```
pip install python-pptx
```

On macOS with a managed Python that command can refuse. Tell the user they can run `pip install --break-system-packages python-pptx`, or make a virtualenv. Wait for the toolchain to work before rendering.

If the spec carries any `Chart:` slides, drawing them needs matplotlib: `pip install matplotlib` (same `--break-system-packages` note applies). It is optional — without it, chart slides still render, falling back to a `VISUAL TO ADD:` note. For charts to use the brand font, `brand.json` must name a `font_files` path; otherwise the chart text uses a fallback font and the run summary says so.

## Step 2: Run the slop detector on the spec

Render slop and you ship slop. Run the detector on the deck spec before `render.py` touches it.

Run both layers from `slop.md`: the presentation-slop checks and the prose-slop checks, plus the five-dimension score on the notes. Catch the tacked-on strapline, the wall of text, the slide-as-script, bullet soup, restatement, the deck about the presenter, unearned hype.

Fix what you find in the spec itself. Show the user the changes and get a yes. A clean spec renders to a clean deck.

## Step 3: Render

Run the bundled `scripts/render.py` (it sits beside this skill). Pass the deck spec, the project's `.slides/brand.json`, and an output path:

```
python3 scripts/render.py --spec <deck>.deck.md \
    --brand .slides/brand.json --out <deck>.pptx
```

`render.py` reads the template path from `brand.json`'s `template` key. There is no `--template` argument. A relative `template` path resolves against the `brand.json` file's own directory, so the working directory does not matter.

On success it exits 0 and prints a one-line summary. On a malformed spec or brand profile it exits 1, prints `error: ...` naming the offending slide, role, or key, and writes nothing.

If the render fails, read the error. It names the fault: a slide numbered out of sequence, a role with more fields than its layout has placeholders, a missing `brand.json` key. Fix the spec or, for a layout-map fault, send the user back to /slides:teach-slides. Then run again.

## Step 4: Render-back visual check

The mechanical lint proves a slide is on-brand and on-grid, but it cannot see the
rendered pixels — text that overflowed its box, a font that fell back, a slide
that reads as cluttered. This step is the lint *with eyes*: rasterise the deck and
look at it. It needs a deck-to-image backend, so it is optional and degrades.

Check for a backend: `python3 -c "import sys; sys.path.insert(0,'scripts'); import raster; print(raster.available_backend())"`.

- **`libreoffice`** (headless, safe): rasterise and review automatically —
  `python3 scripts/raster.py <deck>.pptx --out-dir <deck>.review --sheet --check`.
  Then **open the per-slide PNGs (and `contact-sheet.png`) and look**: does any text
  overflow its box or wrap badly? Do elements collide or crowd the edge? Does each
  composed slide read as *composed*, or templated? Report what you see as
  suggestions (the deck already rendered), and note any `[check] likely-blank`
  slide from the summary.
- **`keynote`** (macOS): the render-back works via Keynote, but it **opens the
  Keynote app** (and may prompt for automation permission), so do not run it
  automatically — tell the user it is available and run it only if they ask.
- **`None`**: tell the user the visual check is unavailable and that installing
  LibreOffice (`brew install --cask libreoffice`) enables an automatic, headless
  render-back review.

## Step 5: Report

Print the render summary. It states how many slides were written, which carry a native chart, which carry a `VISUAL TO ADD` note, any matplotlib or brand-font fallback warning, and any non-blocking composition advisory notes on `composed` slides (evidence-cited "what good looks like" — see [composition.md](../presentation-craft/reference/composition.md)). Surface advisories to the user as suggestions, not errors; the deck still rendered.

A `Chart:` block is drawn natively and placed on the slide (PNGs are written to a `.charts/` folder beside the `.pptx` and embedded in it). A `Visual:` field is recorded in the slide's speaker notes, prefixed `VISUAL TO ADD:`, and is not drawn — tell the user which slides carry one and that placing it in PowerPoint is their step. If the summary reports a matplotlib fallback, tell the user that those chart slides became notes and that `pip install matplotlib` will draw them on the next run.

Tell the user where the `.pptx` was written. To audit the finished deck, point them at /slides:slop-check.
