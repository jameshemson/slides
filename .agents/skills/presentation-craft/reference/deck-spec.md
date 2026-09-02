# The deck spec

A deck spec is the contract between thinking and building: `narrative` writes one, `build-deck` reads it and renders the `.pptx`, `slop-check` reviews it, and a person can read and edit it directly. It is plain Markdown — a half-finished spec is still a valid, resumable file. It carries the *content and structure* of a deck, never fonts, colours, or coordinates: those live in the user's brand profile (`brand.json` — plus the template, in template fidelity). The spec says what each slide means; the brand says how it looks.

## File shape

A deck spec is a Markdown file, conventionally named `<deck>.deck.md`. It has a frontmatter block, then one section per slide.

```
---
deck: <the deck's title>
audience: <who it is for — their objective, knowledge, what they want>
register: presented | read | hybrid
---

## Slide 1
layout: title
Title: ...
Subtitle: ...

## Slide 2
layout: section
Title: ...

## Slide 3
layout: composed
Block: stat-row
value | label
value | label
```

### Frontmatter

A YAML block fenced by `---`, before any slide.

- `deck` — the deck's title. Required.
- `audience` — who the deck is for: their objective, knowledge level, what they walked in wanting. Required. One or two sentences, not a demographic.
- `register` — `presented` (you narrate it live), `read` (it travels without you — a board pack, an update), or `hybrid` (both). Optional; defaults to `presented`. The register sets how hard each slide works (see [slides.md](slides.md)).
- `structure` and `motif` — optional, the deck-level composition brief: `structure` names the ground plan (say, dark open and close with light evidence between) and `motif` the one element repeated across the deck. narrative asks for both; build-deck composes from them and warns when a presented deck has neither.

### Slides

Each slide is a `## Slide N` heading, with `N` counting up from 1 with no gaps. Under the heading:

- `layout:` — a semantic role, on its own line, required, first. One of the six roles below.
- One labelled field per line, as `Field: value`. The fields allowed depend on the role.
- A field may carry a block instead of an inline value: write `Field:` alone, then the lines that follow (a bullet list, or short paragraphs) up to the next `Field:`, the next `## Slide`, or end of file.

## Layout roles

A role is a *semantic* job, not a layout. In brand fidelity — the default — `build-deck` composes each role from the brand's design tokens on a clean canvas — as code when Node is present (see [composing-in-code.md](composing-in-code.md)), otherwise through the pack's drawn roles, whose lead text steps down the type ladder rather than wrap (the run summary says when it did). In template fidelity it instead resolves each role to one of the user's own template layouts through `brand.json`'s `layout_map` and fills that layout's placeholders. Choose by the beat's form: an idea with a shape — a set, a contrast, a sequence, milestones, numbers, data — belongs in `composed`, which arranges brand-locked primitives on the grid (see [The composed role](#the-composed-role)); the six fixed roles carry the framing beats around those — the title, the divider, the hero claim, the quotation, the prose beat that genuinely is a heading and a few lines. A design-led framing beat — the title, a section turn, the hero statement — may instead be `composed` outright, built freeform on a `Canvas:` ground. `Body`, `Left`, and `Right` are block fields: a tight bullet list, or one or two short paragraphs — one idea per slide still holds, so a `title-content` slide carries one point and the few lines that earn it, not a wall, and never a list a composed shape would say better.

| Role | Job | Fields (in order) |
|------|-----|-------------------|
| `title` | The opening slide | `Title`, `Subtitle` (optional) |
| `section` | A divider that signposts a new part | `Title` |
| `statement` | A single hero idea — a number, a phrase, a claim | `Statement` |
| `title-content` | A heading and its supporting content | `Title`, `Body` |
| `two-column` | A two-part comparison or pairing | `Title`, `Left`, `Right` |
| `quote` | A quotation given room to breathe | `Quote`, `Attribution` (optional) |

## The composed role

`layout: composed` is a different mode. Instead of filling a fixed layout's placeholders, it composes brand-locked *primitives* on the brand grid — invention in the arrangement, consistency guaranteed by the design tokens (below) and a mechanical lint. It is the first reach for any beat with a form — a set, a contrast, a sequence, milestones, numbers, exact values: the ideas a bulleted slide flattens. A composed slide carries an optional `Title:`, an optional `Notes:`, and one or more `Block:` lines — each naming a primitive, then its indented item lines:

```
## Slide 5
layout: composed
Title: What moved this quarter
Block: stat-row
56 | Days to close
4% | Win rate
```

### Primitives

Each item line is pipe-separated. A leading `-`/`*` bullet is tolerated; a leading `!` marks the one element that leads — the hero card, the winning panel, the milestone that is the turn. The "good count" column is best practice, not a gate: past it the deck still renders and the run summary carries an advisory note naming the craft rule. The only hard stops are structural (a comparison has two sides, a matrix four quadrants, a table at least two columns) and geometric — the mechanical lint refuses what physically cannot fit the slide, and the error then says to cut items or split the slide.

| Block | Item line | Good count | The one that leads |
|-------|-----------|-----------|--------------------|
| `stat-row` | `value \| label` | 3–5 | — |
| `card-grid` | `label \| body?` | 3–5 | `!` the hero card |
| `comparison` | `header \| body?` (exactly two) | 2 | `!` the winning side |
| `process` | `label \| detail?` | 3–5 steps | — (numbered in order) |
| `timeline` | `date \| event` | 3–6 | `!` the turning point |
| `tree` | an indented list (2-space = one level) | 3–8 nodes, ≤3 deep | `!` the node that leads |
| `cycle` | one stage label per line | 3–6 stages | — |
| `matrix` | four `label \| body?` lines (TL, TR, BL, BR); optional `x:` / `y:` axis captions | 2×2 | `!` the quadrant that leads |
| `icon-list` | `icon-name \| text` | 3–6 | — |
| `table` | first line = header `col \| col`; then `cell \| cell` rows | 2–5 cols, ≤6 data rows | `!` the emphasis row |
| `chart` | same `key: value` grammar as `Chart:` below, incl. `data:` CSV and `native:` | — | — |

Within a card or panel body — and in a stat-row label — ` / ` breaks a line, so a few terse points share one box: `Fast / Focused / Owned`, or a stat labelled `Days / to close`. A stat number never wraps — it steps down the type ladder to fit, and the run summary says so. A **comparison** must *resolve, not balance* — mark the winning side with `!`. A **card grid** holds 3–5 siblings with terse labels. A **process** is 3–5 numbered steps left to right, drawn as boxes joined by arrows (not a chevron ribbon). A **timeline** is dated milestones on a rail with one beat emphasised. A **tree** is an org chart / decomposition: indent to nest, `!` to lead a node. An **icon-list** replaces the bullet with an accent icon. A **cycle** is 3–6 stages on a ring (a loop); a **matrix** is a 2×2 of quadrants with optional axis captions. A **table** is for exact values a reader looks up — three plans against four attributes, a short line-item budget — where the numbers themselves are the point, not the shape. It is not a chart substitute: reach for a chart when the shape carries the meaning, a table when the digits do. The first item line is the header; each line after it is a data row with the same cell count, and a leading `!` marks the one row that leads. Instead of typing rows, `data: costs.csv` loads the header and rows from a CSV in the spec's folder (mutually exclusive with inline rows), and `emphasis: <label>` marks the data row whose first cell equals `<label>`. A table reads best at 2–5 columns and up to ~6 data rows; a longer table steps its type down to caption size to fit the band, the run summary says so, and only when even caption size cannot fit does the render fail, naming how many rows fit. It styles straight from tokens: an ink header band, paper rows on muted hairlines, at most one accent row, and numeric columns right-aligned.

```
Block: table
Plan | Price | Seats
Starter | $12 | 3
! Growth | $40 | 25
```

**Icons.** A curated set of on-brand line icons (recoloured to a token colour) is available: as an `icon-list`, as a `[icon-name]` prefix on a `card-grid`, `tree`, `process`, or `comparison` item, or in `freeform` (`icon <name> <colour> at <placement>`). Icons need `cairosvg` (`pip install cairosvg`); absent, they are skipped and the summary says so. See `assets/icons/` for the names.

### Freeform — compose anything else

The named blocks are fast paths for the shapes that recur most; they are not the ceiling. For a shape they don't cover — a node graph, an annotated diagram — and for the design-led slides where the composition itself carries the meaning — a title moment, a hero statement, a hand-drawn data graphic — `Block: freeform` is the main stage: place the elements yourself. Each line is one element:

```
Block: freeform
panel paper outline ink at cols 1-6 rows 1-8
text h1 ink at cols 1-6 rows 1-3 | Three markets
panel accent at cols 8-12 rows 1-8
text h1 paper at cols 8-12 rows 1-3 | One backbone
```

- `panel <fill> [outline <stroke>]` (or `box …`) — a filled, optionally outlined box that can hold text. `panel <colour> at full-bleed` (box/panel only) spans the whole slide, margins included, behind the content — the partial colour-blocking wash.
- `text <scale> <colour> | the words` — `<scale>` is `display` / `h1` / `body` / `caption`.
- `arrow <colour>`, `dot <colour>`, `line <colour>` — a connector, a marker, a hairline divider.
- `<colour>` is a role name — `ink`, `paper`, `accent`, `muted` — never a hex, so it stays on-brand.
- `at <placement>` positions the element on the block's 12×12 grid (`cols A-B`, `rows C-D`, or a shortcut) — or by exact percent bounds: `x A%-B%` / `y A%-B%` (0–100, decimals fine, start strictly below end; never mixed with cols/rows in one placement), resolved exactly against the content band with no insets — the author owns the geometry. A single-axis placement spans the full band on the other axis.

Freeform gives freedom, not a safety net beyond the lint: it guarantees the result is *on-brand* (token colours, on the grid, no overlap, under the element cap), not that it is *well composed* — that is your judgement. Its one advisory nudge is grey-push: keep the accent to one or two marks. Percent placement is also how you hand-draw the data graphics no `Chart:` type covers — a dumbbell (`line ink at x 10%-60% y 47%-49%`, a dot at each end), a slope, a bespoke annotated figure — because you place data accurately, to the fraction.

### Several blocks, and placement

A composed slide reads best with at most four blocks (past that, a `block-count` advisory fires — the element cap is the hard backstop). With no placement they **stack** top to bottom. Or place each on the grid with `at`: `Block: card-grid at cols 1-6` (left half), `at cols 7-12` (right half), the shortcuts `at left` / `at right` / `at top` / `at bottom`, a quadrant like `at cols 1-6 rows 7-12` (lower left) over a 12-column by 12-row band, or exact percent bounds (`at x A%-B%` / `y A%-B%` — the same grammar as freeform, above). Either place every block or none — not a mix. Every primitive draws only in the brand's token colours and type-scale sizes, snapped within the grid. A composed slide that would place an off-token colour, an off-scale size, an element outside the margins, overlapping elements, or more than the element cap fails the render with a named error rather than an off-brand slide — the mechanical lint is what makes free composition safe. Text is measured as it will wrap: a box grows to the lines its text actually needs, and a block whose text wraps deeper than its space fails the render with a named error telling you what to cut — so write block items terse, and split a slide rather than cram one. Beyond that hard gate, `build-deck` runs an *advisory* review for each primitive (count, terseness, one-accent, and the cliché guards) and prints non-blocking notes in the run summary; see [composition.md](composition.md) and [design-research.md](design-research.md). In brand fidelity `build-deck` draws `composed` on the clean canvas like every slide; in template fidelity, on the layout named in `layout_map` (falling back to the `statement`, then `title` layout).

## The Brief, Visual, Notes, and Canvas fields

Any slide may carry `Brief:` — the composition brief narrative commits (the one thing; the form it earns and why; what leads the eye; a named reference); build-deck composes from it and never draws it. Write it directly after `layout:` so a reader meets the brief first. Any slide may carry an optional `Visual:` field: a plain-language description of an image, diagram, or chart that belongs on that slide ("a full-bleed photograph of the real product in use"; "a column chart, four quarters, Q4 coloured to carry the point"). `build-deck` does not draw it — it records the description in the slide's speaker notes, prefixed `VISUAL TO ADD:`, so the person finishing the deck knows exactly what to place and why. Use `Visual:` for anything `build-deck` cannot draw: photographs, concept diagrams, and the chart families it does not support (histogram, map); for the families it does draw, use the `Chart:` field below. Choosing the right chart or diagram is craft, taught in [data-viz.md](data-viz.md); placing it is a deliberate human step, not a thing code guesses. Any slide may also carry `Notes:` — what the presenter says, or, for a read deck, the context a reader needs. Notes are prose and are held to the prose-slop standard in [slop.md](slop.md); the slide is not the script, the notes are. In brand fidelity any slide — composed or fixed-role — may also carry `Canvas: <colour-role>` (`ink`, `paper`, `accent`, or `muted`): the slide background paints with that token role, and the slide's text recolours automatically to keep contrast on a dark ground. Canvas is brand-fidelity vocabulary only; template fidelity rejects the field by name.

## The Chart field

A `title-content` slide may carry a `Chart:` block: structured data `build-deck` draws as an on-brand chart and places below the slide's content. `Chart:` and `Body:` may both appear — the one-line `Body:` explains the chart above it (one of the two is required). `Chart:` is allowed on `title-content` only. Write `Chart:` on its own line, then indented `key: value` lines. The types fall in two data shapes:

- **Category charts** — `type: bar` (horizontal), `type: column` (vertical), `type: pie` (part-to-whole), or `type: waterfall` (a running total built from signed deltas). Need `categories:` (comma-separated labels) and `series <Name>:` (comma-separated numbers, one per category). `bar`/`column` take one or more series; `pie` and `waterfall` take exactly one. On `bar`/`column`/`pie`, optional `emphasis:` names the one category to colour in the brand accent (one slice, for a pie); the rest go muted (a waterfall colours by sign instead — see below). Optional `callout:` is a short annotation. A multi-series `bar`/`column` may add `stacked: true` to draw one full-width bar per category, one total label per stack (needs ≥2 series; not combined with `emphasis:`).
- **Point charts** — `type: line` (filled) or `type: scatter` (dots). Need `points:` as comma-separated `x y` pairs. Optional `marker: <x> <label>` annotates the point at that x. Optional `callout:`. `emphasis:` does not apply. **`type: line` is dual-shaped** — it also takes the category grammar (`categories:` + one or more `series <Name>:` lines, mutually exclusive with `points:`), which is how a line chart carries several series: two trends compared over the same quarters. One series keeps the filled accent look; several draw one line each with a legend below. On a category line, `emphasis:` names the **series** to accent (the one line that carries the point) — not a category — and the rest go muted; `marker:` is x-keyed, so it needs the `points:` shape — use `callout:` instead.

```
## Slide 4
layout: title-content
Title: Where the savings land, year by year
Body: After the spends, the pot grows again every year.
Chart:
  type: column
  emphasis: 2031
  categories: 2026, 2027, 2028, 2029, 2030, 2031
  series Balance: 76900, 34300, 37400, 21900, 24600, 27300
```

Instead of typing the data inline, a chart may read it from a CSV with `data: <file.csv>` (resolved against the spec's folder) — `data:` and the inline `categories`/`series`/`points` are mutually exclusive. A category chart's CSV is a header row (`category, Series1, Series2, …`) then one row per category; a point chart's first two columns are `x, y`. So a spreadsheet exports straight to a chart, and multiple series draw as grouped bars. A line CSV is read by shape: three or more columns, or a non-numeric first column, is category data (each numeric column a series); exactly two numeric columns stay `x, y` points — to force category treatment on two numeric columns, write `categories:` + `series` inline instead of `data:`. Format the value labels with `format:` — `$` (currency), `%` (percent), or `$k` / `$m` (currency in thousands / millions, so `362` reads as `$362k`); or set `prefix:` / `suffix:` directly. Large numbers abbreviate by default (`362000` → `362k`); `format: plain` keeps them exact. `native: true` draws a native, editable PowerPoint chart instead of an image, for `bar`/`column`/`pie`/`line`/`scatter`; a chart PowerPoint can't draw that way (`waterfall`) or one carrying a drawn annotation (`target:`, `callout:`, `marker:`) falls back to the image automatically and the run summary names why. Without `format:`, native value labels show exact numbers (`General`) — the image path's automatic abbreviation isn't expressible natively. Optional `target: <value> [| label]` draws a goal line on `column`, `bar`, or `line` charts (image path), extending the axis to include it. A **waterfall** shows how a starting figure becomes an ending one — a running total built from signed changes. It is a category chart with exactly one `series` of signed deltas: a positive number rises, a negative one falls, and `build-deck` appends a computed total bar at the end. Rises take the brand accent, falls a distinct spend tone (a muted grey when the brand names no spend colour), and the total bar sits in ink — so the sign already carries the emphasis. `emphasis:` is therefore rejected on a waterfall; use `callout:` to point at a bar. The delta labels are signed (`+$40k` / `-$15k`); the total is unsigned. `total: Closing` renames the total bar, `total: none` drops it. Like every chart, a waterfall can read its deltas from a CSV with `data:`.

```
## Slide 5
layout: title-content
Title: Where the cash went this year
Body: Strong Q1 collections, then two heavy build quarters.
Chart:
  type: waterfall
  format: $k
  categories: Opening, Q1, Q2, Q3, Q4
  series Cash: 240, 60, -85, -40, 55
  total: Closing
```

Colours come from `brand.json` `colours` (accent for the emphasis, a muted tone for the rest); the chart text uses the brand font when `brand.json` names a `font_files` path. Drawing needs `matplotlib` (`pip install matplotlib`). If it is not installed, the chart degrades to a `VISUAL TO ADD:` note built from the chart data, so the deck still builds. Choosing the right chart for the data is craft, taught in [data-viz.md](data-viz.md).

## The brand profile (`brand.json`)

`build-deck` needs two inputs: the deck spec, and the user's brand profile. `teach-slides` writes `brand.json` into `.slides/`; `render.py` reads it. Its keys:

- `fidelity` (optional) — `"brand"` (the default when absent) draws every slide, fixed roles included, from design tokens on a clean 16:9 canvas built in-process; the template file is never opened at render time. `"template"` restores the pre-v0.17 placeholder-fill byte-identically (and warns, non-blocking, when the master's body size is at or above its title size — hierarchy will not read).
- `template` — path to the user's `.pptx`/`.potx`. In brand fidelity an optional pointer back to the identity source; required, and opened, only in template fidelity.
- `fonts` — `{ "heading": "...", "body": "..." }`. Required in both modes.
- `colours` — named brand colours as hex. Required in both modes.
- `layout_map` — **template fidelity only**: maps each of the six roles (and, optionally, `composed`) to a layout index in the template — the join between a spec's semantic roles and the template's real layouts. In brand fidelity roles are drawn from tokens and no map is read.
- `tokens` (optional) — per-key overrides of the design-token defaults the `composed` role and (in brand fidelity) the fixed roles draw from: `grid` (margins, columns, gutter, baseline), `type_scale` (display, title, h1, body, caption), `colour_roles` (ink, paper, accent, muted — from the palette), and `shape` (corner: rounded|sharp, hairline — the brand's box style). In brand fidelity the defaults are **the pack's own**: a register-keyed type scale (presented decks get 96/60/40/24/16pt; an unambiguously read deck 72/48/32/18/12) and the pack grid. In template fidelity they derive from the template (grid from the mapped layouts, type scale from the master's own sizes). An explicit key here wins over either default.

`render.py` validates the required keys per fidelity — `fonts` and `colours` in brand fidelity; those plus `template` and `layout_map` in template fidelity — and reports the missing or malformed one by name rather than emitting a broken file. `teach-slides` can fill `fonts` and `colours` automatically: pointed at a template or an existing deck, `extract_brand.py` reads the heading and body fonts and the palette (accent colours plus `ink` and `paper`) straight from the file's theme, so the profile reflects the real deck instead of hand-typed values, and the user confirms or adjusts what it read. `init_brand.py` goes one step further — it writes a complete brand-fidelity `brand.json` (`fidelity`, a `template` ref, `fonts`, `colours`, `tokens`; `--fidelity template` emits the legacy shape with a proposed `layout_map`) from a single template or deck, so a project can be brand-ready without the full interview; `build-deck` and `narrative` offer this when `.slides/` is missing, and the user confirms the result and can refine it later with `teach-slides`.

## The lineage stamp

`build-deck` stamps every rendered deck's `core_properties.comments` with `slides-spec: <spec basename> sha256:<sha256 of the spec file>`, overwriting whatever a template's own comments field held — a generated deck's comments are the pack's to set, by design. The `revise` skill reads the stamp to find and sync a deck's spec (`deck_to_spec.py --against`); a deck with no stamp, or whose named spec no longer exists, is imported best-effort instead (the foreign tier).

## Rules the spec must hold

- Slides numbered 1..N with no gaps; every slide has a `layout:` line first.
- Only the fields its role allows, plus optional `Brief:`, `Visual:`, `Notes:`, and — brand fidelity only — `Canvas:`.
- Every drawn element — a fixed role's anatomy in brand fidelity, and every `composed` primitive — must pass the mechanical lint (token colour, scale size, within margins, no overlap, under the element cap, rank-2 text strictly below rank-1) before it is added, so no slide can go off-brand and a spec cannot smuggle a tacked-on strapline onto one. In template fidelity the fixed roles keep the structural guarantee instead: `render.py` fills only the template's existing placeholders and adds no shape.
- A malformed spec fails loudly: `render.py` exits non-zero naming the offending slide and line. It never emits a half-built `.pptx`.
