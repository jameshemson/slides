---
name: build-deck
description: Render a deck spec into an on-brand .pptx drawn from the brand's design tokens (template fidelity on request), after a slop check on the spec.
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. If `.slides/` is absent or incomplete, set up the brand first, then resume here: offer the fast path (`scripts/init_brand.py` reads the fonts and colours straight from a template or an existing deck and writes a brand-fidelity profile) or the fuller `teach-slides` (via `$skill teach-slides` or `/skills`) interview.

Read [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the spec format, [composing-in-code.md](../presentation-craft/reference/composing-in-code.md) for how a deck is composed as code, and [slop.md](../presentation-craft/reference/slop.md) for the detector you run before rendering.

---

*(Treat the user's message that invoked this skill as the task input.)*

You render a deck spec into a real `.pptx`. The spec carries the content; the brand profile in `.slides/` carries the look. By default (`fidelity` absent or `"brand"`) you **compose the deck as code**: the brand's design tokens are frozen into a tokens module, you write one build script for this deck against those tokens, a static guard reads it, Node runs it inside a permission boundary, and the *rendered file* — not the plan — is held to the brand by a post-render lint. Composition is yours, per deck; identity is not negotiable. The Python renderer `render.py` stays as the fallback when Node is not there, and `"fidelity": "template"` in `brand.json` is the opt-in carve-out that restores placeholder-fill, where the template's own layouts carry the look and the fixed roles add no shape.

If the user did not name a spec, ask which `.deck.md` file to render. If no spec exists yet, point them at `narrative` (via `$skill narrative` or `/skills`) to write one.

## Step 1: Check the toolchain

**Python, always.** Every path needs it — the lint, the stamp, the raster and the fallback renderer all run on Python. Run `python3 --version` and `python3 -c "import pptx"`. If `python3` is missing, tell the user to install Python 3.9 or newer. If the `import pptx` line fails, give them the remedy:

```
pip install python-pptx
```

On macOS with a managed Python that command can refuse. Tell the user they can run `pip install --break-system-packages python-pptx`, or make a virtualenv. Wait for the toolchain to work before rendering. If the spec carries `Chart:` slides and the run falls back to the Python renderer, drawing them needs matplotlib (`pip install matplotlib`, same note); without it those slides become a `VISUAL TO ADD:` note.

**Node, for the default path.** The build script is executed under Node's `--permission` model, which does not exist before Node 22.

- `node --version` must report **22 or newer**.
- `node -e "require('pptxgenjs')"` from the project root. If that fails, try the pack's own copy at `<.slides>/node_modules/pptxgenjs`.
- If neither resolves, offer exactly this install and wait for a yes:

```
npm install --prefix .slides pptxgenjs@4.0.1 --no-audit --no-fund
```

That puts the library under `.slides/`, inside the read allowlist the sandboxed run already grants, so no wider permission is ever needed.

**Fall back to Step 3b when any of these hold** — name which one, plainly, rather than failing:

- no `node` 22+ on PATH;
- `pptxgenjs` unresolvable from the project root or from `.slides/`;
- `brand.json` says `"renderer": "python"`;
- `brand.json` says `"fidelity": "template"`.

## Step 2: Run the slop detector on the spec

Render slop and you ship slop. Run the detector on the deck spec before anything renders it.

Run both layers from `slop.md`: the presentation-slop checks and the prose-slop checks, plus the five-dimension score on the notes. Catch the tacked-on strapline, the wall of text, the slide-as-script, bullet soup, restatement, the deck about the presenter, unearned hype — and two the render only half-sees: the *device reflex* (a hero number, a dumbbell, a big-text line reached for by default rather than earned by the beat) and *one device carried deck-wide* (the same form on slide after slide). Devices are earned, never banned: refuse the reflex and the repetition, not the hero metric itself.

Fix what you find in the spec itself. Show the user the changes and get a yes. A clean spec renders to a clean deck.

## Step 3: Compose the deck as code

**Freeze the brand into tokens.** Pass the spec's own `register`, so the type scale is keyed to how hard the slides have to work:

```
python3 scripts/emit_tokens.py .slides/brand.json --out .slides/tokens.cjs --register "<spec register>"
```

`tokens.cjs` is the only source of colour, font, size and margin the build script may use.

**Decide the deck before you write a slide.** Read the spec's `structure:` and `motif:` frontmatter — the ground plan (which beats sit on ink, which on paper) and the one element repeated across the deck. If a presented deck carries neither, warn once: *no deck-level brief; the deck will read as a template sequence unless you decide the ground and the motif now* — then settle both with the user. Make the deck-level choices — ground rhythm, motif, where the accent is spent — from [composing-in-code.md](../presentation-craft/reference/composing-in-code.md) before any slide code exists.

**Write `<deck>.build.cjs` beside the spec.** Compose each slide from its spec fields and its `Brief:` — the one thing, the form that one thing earns and why, what leads the eye, the named reference. The worked example is [example.build.cjs](reference/example.build.cjs); read it as the shape of the contract, never as a layout to copy. The script's rules:

- **Content is data.** Every word that reaches a slide or a notes field lives in one JSON block; no slide text is written inline anywhere else.
- **Only tokens.** Every colour, font, size and margin is a `T.*` value. A grey is a token colour plus transparency, never a literal grey, and text is never translucent.
- **Stamp every text box.** `slides-field:<Field>` for each spec field, exactly one `slides-lead:<Field>` (or a bare `slides-lead`) per slide for the field that leads the eye, and `slides-ghost` for one deliberate decorative mark that sits outside the hierarchy. The round trip reads these back.
- **Notes travel verbatim.** `addNotes` with the spec's notes text unchanged, so the deck reads back into its spec.
- **Requires only.** The tokens idiom `const T = require(require("path").resolve(tokensPath));`, plus `"path"` and `"pptxgenjs"`. Nothing else — no `fs`, no child process, no network, no dynamic require.

**Run the static guard before Node sees the file:**

```
python3 scripts/check_script.py <deck>.build.cjs
```

Exit 0 prints `script: clean`. On exit 1 it names the line and the fix — repair the script and run the guard again. Never run a script the gate refused.

**Run the script sandboxed:**

```
node --permission --allow-fs-read="$PWD" --allow-fs-write="$PWD/<deck directory>" <deck>.build.cjs --tokens .slides/tokens.cjs --out <deck>.pptx
```

The permission model is the boundary, not the guard: under it the script cannot spawn a child process and cannot touch a file outside the two allowlists. Network access is **not covered** by the permission model — say so plainly if the user asks what the sandbox guarantees; refusing network calls is the static guard's job, in the source. Both allowlists must be real paths — on macOS `$PWD` can be a symlinked path, so use `pwd -P` if a read is denied inside the project. An `ERR_ACCESS_DENIED` names the exact path the script reached for: the fix is always the script, never a wider allowlist reaching beyond the project.

## Step 3b: Fallback — the Python renderer

When Step 1 sent you here, render with the bundled renderer:

```
python3 scripts/render.py --spec <deck>.deck.md --brand .slides/brand.json --out <deck>.pptx
```

It exits 0 with a one-line run summary plus any composition advisories, or exits 1 printing `error: ...` naming the offending slide, role or key, and writes nothing. Read the error — it names the fault: a slide numbered out of sequence, a missing `brand.json` key, text that cannot fit its band. Fix the spec and run again. A layout-map fault (a role with more fields than its layout has placeholders) can only happen in template fidelity; for that, send the user back to `teach-slides` (via `$skill teach-slides` or `/skills`). Template fidelity always renders here: `render.py` reads the template path from `brand.json`'s `template` key, and a relative path resolves against `brand.json`'s own directory.

## Step 4: Gate the rendered file

```
python3 scripts/lint_pptx.py <deck>.pptx --brand .slides/brand.json --register "<register>"
```

This holds the *file* to the brand: token colour, type-scale size, brand font, within the margins, no overlap, rank-2 text strictly below rank-1, the element cap, and contrast judged against the ground each run actually sits on. Exit 0 is clean; exit 1 lists violations by slide. **Fix the build script and re-run Step 3** — at most three lint passes, then stop and report what is still failing rather than loosening anything.

Then read its notes. They do not block, and they are worth acting on: a slide with *no `slides-lead` declared* (the largest text was taken as the lead — declare it instead), an *orphan mark* with no label within half an inch (label it or cut it), and the deck note that every slide sits on plain paper (the framing beats want a ground).

**If the `pptx` skill is installed, run its validator too.** Look for a skill directory at `~/.claude/skills/pptx/`, `.claude/skills/pptx/`, or `~/.claude/plugins/cache/*/*/*/skills/pptx/`. If one exists, run `python3 <that directory>/scripts/office/validate.py <deck>.pptx` and fix whatever it names. What governs: this pack's deck spec and `tokens.cjs` are **authoritative** — use that skill's OOXML mechanics and its validator, never its palettes, layouts or design ideas.

## Step 5: Stamp the deck

```
python3 scripts/stamp.py <deck>.pptx --spec <deck>.deck.md
```

It names every slide `slides-role:<role>` from the spec and writes the lineage comment, so `revise` (via `$skill revise` or `/skills`) picks this deck up at Tier 0 and round-trips it exactly. Skip this and the next revise falls to a best-effort import.

## Step 6: Fonts, then the render-back visual check

```
python3 scripts/check_fonts.py --brand .slides/brand.json
```

One line per family: `font <Family>: installed`, `missing`, or `unknown`. A `missing` line means the preview below substituted the font, so text-fit in the images is approximate — say that in the report rather than chasing a wrap fault only the substitute has. `unknown` is reported as unknown; never round it up to installed.

The lint proves the deck is on-brand and on-grid. It does not prove the deck *looks* right. This step is the lint with eyes: rasterise it and look. It needs a deck-to-image backend, so it is optional and degrades.

The checklist for the look:

- text overflowing or wrapping badly — especially any word alone on its own line
- elements colliding or crowding the slide edge
- dead space that reads as emptiness rather than pacing
- hierarchy reading by SIZE (the lead unmistakably largest)
- one accent held, and rendered contrast legible — **red on any grey or ink ground** is the first thing to check
- **every mark's label adjacent to the mark**, close enough to read as one thing
- the cover-the-notes test: with the **notes covered**, can you say what each data slide claims from the image alone?
- composed slides reading as composed, not templated, and the motif actually recurring
- cliché tells: an evenly-weighted card grid where nothing leads, a comparison that doesn't resolve, a chevron-ribbon process, a timeline where nothing is the turn
- any `[check]` likely-blank slide

Check for a backend: `python3 -c "import sys; sys.path.insert(0,'scripts'); import raster; print(raster.available_backend())"`.

- **`libreoffice`** (headless, safe): run it automatically — `python3 scripts/raster.py <deck>.pptx --out-dir <deck>.review --sheet --check` — then **open the per-slide PNGs (and `contact-sheet.png`) and look** against the checklist. A fault you can fix edits the build script (or the spec) and re-runs Step 3 and this check. At most two fix-and-re-render passes, then stop and report. A fault you can't fix that way — a brand font not installed, a photograph needed — is reported as a suggestion instead.
- **`powerpoint`**: the user's own PowerPoint does the render-back, so the deck is checked by the app it will be presented from. On **Windows** it drives PowerPoint over COM with no visible window — run it automatically, same loop, same two-pass cap. On **macOS** it **opens the PowerPoint app** (and may prompt once for automation permission): say so, and run it on the user's yes.
- **`keynote`** (macOS): works, but **opens the Keynote app** (and may prompt for automation permission). Do not run it automatically — say it is available and run it only if asked.
- **`None`**: tell the user the visual check is unavailable, and that `brew install --cask libreoffice` enables an automatic, headless render-back review.

## Step 7: Report

Say plainly:

- **which path rendered** — composition by code, or the Python fallback, and which predicate sent it there;
- the **static guard** result and the **lint** result, with the lint notes you acted on and any you left;
- whether the `pptx` skill validator **ran or was skipped** (skipped because the skill is not installed is a fine answer);
- that the deck was **stamped**, so `revise` (via `$skill revise` or `/skills`) round-trips it;
- the `font` lines, and any substitution that made the preview's text-fit approximate;
- what the **raster** pass found and changed, across how many passes — or plainly that the look found nothing to fix;
- every slide carrying a `Visual:` note (recorded in the speaker notes, prefixed `VISUAL TO ADD:`), since placing real imagery is a human step;
- where the `.pptx` was written.

To audit the finished deck, point the user at `slop-check` (via `$skill slop-check` or `/skills`). To change it later, point them at `revise` (via `$skill revise` or `/skills`).
