---
name: build-deck
description: Render a deck spec into an on-brand .pptx drawn from the brand's design tokens (template fidelity on request), after a slop check on the spec.
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. If `.slides/` is absent or incomplete, set up the brand first, then resume here: offer the fast path (`scripts/init_brand.py` reads the fonts and colours straight from a template or an existing deck and writes a brand-fidelity profile) or the fuller `teach-slides` (via the skill tool) interview.

Read [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the spec format and [slop.md](../presentation-craft/reference/slop.md) for the detector you run before rendering.

---

*(Treat the user's message that invoked this skill as the task input.)*

You render a deck spec into a real `.pptx`. The spec carries the content; the brand profile in `.slides/` carries the look. By default (`fidelity` absent or `"brand"`) every slide — the six fixed roles included — is drawn from the brand's design `tokens` on a clean 16:9 paper canvas built in-process; the template file is never opened at render time, it is an identity source read at init. The `composed` role draws the same way — a `stat-row`, `card-grid`, `comparison`, `process`, `timeline`, or a `freeform` arrangement, stacked or placed on the grid. Every drawn element must pass a mechanical lint — token colour, type-scale size, within the grid margins, no overlap, under the element cap, rank-2 text strictly below rank-1 — or the render fails with a named error. Free composition, still bounded. `"fidelity": "template"` in `brand.json` is the opt-in carve-out: it restores the placeholder-fill mode, where the template's own layouts carry the look and the fixed roles fill their placeholders and add no shape.

If the user did not name a spec, ask which `.deck.md` file to render. If no spec exists yet, point them at `narrative` (via the skill tool) to write one.

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

Run both layers from `slop.md`: the presentation-slop checks and the prose-slop checks, plus the five-dimension score on the notes. Catch the tacked-on strapline, the wall of text, the slide-as-script, bullet soup, restatement, the deck about the presenter, unearned hype — and two the render only half-sees: the *device reflex* (a hero number, a dumbbell, a big-text line reached for by default rather than earned by the beat) and *one device carried deck-wide* (the same form on slide after slide). Devices are earned, never banned: refuse the reflex and the repetition, not the hero metric itself.

Fix what you find in the spec itself. Show the user the changes and get a yes. A clean spec renders to a clean deck.

## Step 3: Render

Run the bundled `scripts/render.py` (it sits beside this skill). Pass the deck spec, the project's `.slides/brand.json`, and an output path:

```
python3 scripts/render.py --spec <deck>.deck.md \
    --brand .slides/brand.json --out <deck>.pptx
```

In template fidelity, `render.py` reads the template path from `brand.json`'s `template` key — there is no `--template` argument — and a relative path resolves against the `brand.json` file's own directory, so the working directory does not matter. In brand fidelity the template file is not opened at all; the canvas is built in-process.

On success it exits 0 and prints a run summary (one line, plus a line per composition advisory). On a malformed spec or brand profile it exits 1, prints `error: ...` naming the offending slide, role, or key, and writes nothing.

If the render fails, read the error. It names the fault: a slide numbered out of sequence, a missing `brand.json` key, text that cannot fit its band. Fix the spec and run again. A layout-map fault (a role with more fields than its layout has placeholders) can only happen in template fidelity — for that, send the user back to `teach-slides` (via the skill tool).

## Step 4: Render-back visual check

The mechanical lint proves a slide is on-brand and on-grid, and the planners
estimate word-wrap so a text box is drawn at the height its text actually needs
(a block whose text cannot fit fails the render with a named error instead).
But an estimate is not pixels — a font that fell back, an edge case the wrap
estimate missed, a slide that reads as cluttered. This step is the lint *with
eyes*: rasterise the deck and look at it. It needs a deck-to-image backend, so
it is optional and degrades.

The checklist for the look:

- text overflowing or wrapping badly — especially any word alone on its own line
- elements colliding or crowding the slide edge
- dead space that reads as emptiness rather than pacing
- hierarchy reading by SIZE (the lead unmistakably largest)
- one accent held (grey field, colour spent on the insight) and rendered
  contrast legible (small text vs its actual background)
- composed slides reading as composed, not templated
- freeform slides especially — they have no advisory rules, the look is
  their only craft check
- cliché tells: an evenly-weighted card grid where nothing leads, a
  comparison that doesn't resolve, a chevron-ribbon process, a timeline
  where nothing is the turn
- any `[check]` likely-blank slide

Check for a backend: `python3 -c "import sys; sys.path.insert(0,'scripts'); import raster; print(raster.available_backend())"`.

- **`libreoffice`** (headless, safe): rasterise and review automatically —
  `python3 scripts/raster.py <deck>.pptx --out-dir <deck>.review --sheet --check`.
  Then **open the per-slide PNGs (and `contact-sheet.png`) and look** against
  the checklist above. When you find a fault you can fix by editing the deck
  spec — tighter text, a different block or placement, a Canvas moment,
  cutting an item — edit the spec and re-render (Step 3) and re-raster. At
  most two fix-and-re-render passes, then stop and report. A fault you can't
  fix from the spec (a brand font not installed, a photograph needed) is
  reported as a suggestion instead, same as before.
- **`powerpoint`**: the user's own Microsoft PowerPoint does the render-back —
  the same `raster.py` command, and the deck is checked by the very app it will
  be presented from. On **Windows** this drives PowerPoint over COM with no
  visible window, so run it automatically like LibreOffice, including the same
  look-against-the-checklist, edit-the-spec, re-render-and-re-raster loop,
  capped at two passes. On **macOS** it **opens the PowerPoint app** (and may
  prompt once for automation permission), so say so and run it — and that
  same fix-and-re-render loop — on the user's yes.
- **`keynote`** (macOS): the render-back works via Keynote, but it **opens the
  Keynote app** (and may prompt for automation permission), so do not run it
  automatically — tell the user it is available and run it only if they ask.
- **`None`**: tell the user the visual check is unavailable and that installing
  LibreOffice (`brew install --cask libreoffice`) enables an automatic, headless
  render-back review.

## Step 5: Report

Print the render summary. It states how many slides were written, which carry a native chart, which carry a `VISUAL TO ADD` note, any matplotlib or brand-font fallback warning, and any non-blocking composition advisory notes on `composed` and drawn role slides (evidence-cited "what good looks like" — see [composition.md](../presentation-craft/reference/composition.md)), plus a note when a role's lead text stepped down the type ladder to fit, a deck-level note when one named composed device carries most of the deck (the repetition flag), and a note when a freeform hero line wrapped past one line. Surface advisories to the user as suggestions, not errors; the deck still rendered.

A `Chart:` block is drawn natively and placed on the slide (PNGs are written to a `.charts/` folder beside the `.pptx` and embedded in it). A `Visual:` field is recorded in the slide's speaker notes, prefixed `VISUAL TO ADD:`, and is not drawn — tell the user which slides carry one and that placing it in PowerPoint is their step. If the summary reports a matplotlib fallback, tell the user that those chart slides became notes and that `pip install matplotlib` will draw them on the next run.

If Step 4's render-back loop ran, include a short "what the look found and changed" note — which faults it caught and fixed, across how many passes — or say plainly the look found nothing to fix.

Tell the user where the `.pptx` was written. To audit the finished deck, point them at `slop-check` (via the skill tool). To change it later, point them at `revise` (via the skill tool).
