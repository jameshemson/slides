# The deck spec

A deck spec is the contract between thinking and building: `narrative` writes one, `build-deck` reads it and renders the `.pptx`, `slop-check` reviews it, and a person can read and edit it directly. It is plain Markdown — a half-finished spec is still a valid, resumable file. It carries the *content and structure* of a deck, never fonts, colours, or coordinates: those live in the user's template and `brand.json`. The spec says what each slide means; the template says how it looks.

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
Notes: ...

## Slide 2
layout: section
Title: ...
```

### Frontmatter

A YAML block fenced by `---`, before any slide.

- `deck` — the deck's title. Required.
- `audience` — who the deck is for: their objective, knowledge level, what they walked in wanting. Required. One or two sentences, not a demographic.
- `register` — `presented` (you narrate it live), `read` (it travels without you — a board pack, an update), or `hybrid` (both). Optional; defaults to `presented`. The register sets how hard each slide works (see [slides.md](slides.md)).

### Slides

Each slide is a `## Slide N` heading, with `N` counting up from 1 with no gaps. Under the heading:

- `layout:` — a semantic role, on its own line, required, first. One of the six roles below.
- One labelled field per line, as `Field: value`. The fields allowed depend on the role.
- A field may carry a block instead of an inline value: write `Field:` alone, then the lines that follow (a bullet list, or short paragraphs) up to the next `Field:`, the next `## Slide`, or end of file.

## Layout roles

A role is a *semantic* job, not a template layout. `build-deck` resolves each role to one of the user's own template layouts through `brand.json`'s `layout_map`, then fills that layout's placeholders. Six fixed roles cover most decks; a seventh mode, `composed`, composes brand-locked primitives on the grid (see [The composed role](#the-composed-role)). `Body`, `Left`, and `Right` are block fields: a tight bullet list, or one or two short paragraphs — one idea per slide still holds, so a `title-content` slide carries one point and the few lines that earn it, not a wall.

| Role | Job | Fields (in order) |
|------|-----|-------------------|
| `title` | The opening slide | `Title`, `Subtitle` (optional) |
| `section` | A divider that signposts a new part | `Title` |
| `statement` | A single hero idea — a number, a phrase, a claim | `Statement` |
| `title-content` | A heading and its supporting content | `Title`, `Body` |
| `two-column` | A two-part comparison or pairing | `Title`, `Left`, `Right` |
| `quote` | A quotation given room to breathe | `Quote`, `Attribution` (optional) |

## The composed role

`layout: composed` is a different mode. Instead of filling a fixed layout's placeholders, it composes brand-locked *primitives* on the template's own grid — invention in the arrangement, consistency guaranteed by the design tokens (below) and a mechanical lint. The six fixed roles stay the safe default; `composed` is for a set, a contrast, a sequence, or milestones — the ideas a bulleted slide flattens. A composed slide carries an optional `Title:`, an optional `Notes:`, and one or more `Block:` lines — each naming a primitive, then its indented item lines:

```
## Slide 5
layout: composed
Title: What moved this quarter
Block: stat-row
56 | Days to close
4% | Win rate
120 | New deals
```

### Primitives

Each item line is pipe-separated. A leading `-`/`*` bullet is tolerated; a leading `!` marks the one element that leads — the hero card, the winning panel, the milestone that is the turn.

| Block | Item line | Good count | The one that leads |
|-------|-----------|-----------|--------------------|
| `stat-row` | `value \| label` | 3–5 | — |
| `card-grid` | `label \| body?` | 3–5 | `!` the hero card |
| `comparison` | `header \| body?` (exactly two) | 2 | `!` the winning side |
| `process` | `label \| detail?` | 3–5 steps | — (numbered in order) |
| `timeline` | `date \| event` | 3–5 | `!` the turning point |
| `tree` | an indented list (2-space = one level) | ≤8 (6 with icons), ≤3 deep | `!` the node that leads |
| `cycle` | one stage label per line | 3–6 stages | — |
| `matrix` | four `label \| body?` lines (TL, TR, BL, BR); optional `x:` / `y:` axis captions | 2×2 | `!` the quadrant that leads |
| `icon-list` | `icon-name \| text` | 3–6 | — |
| `table` | first line = header `col \| col`; then `cell \| cell` rows | ≤6 data rows | `!` the emphasis row |
| `chart` | same `key: value` grammar as `Chart:` below, incl. `data:` CSV and `native:` | — | — |

Within a card or panel body, ` / ` breaks a line, so a few terse points share one box: `Fast / Focused / Owned`. A **comparison** must *resolve, not balance* — mark the winning side with `!`. A **card grid** holds 3–5 siblings with terse labels. A **process** is 3–5 numbered steps left to right, drawn as boxes joined by arrows (not a chevron ribbon). A **timeline** is dated milestones on a rail with one beat emphasised. A **tree** is an org chart / decomposition: indent to nest, `!` to lead a node. An **icon-list** replaces the bullet with an accent icon. A **cycle** is 3–6 stages on a ring (a loop); a **matrix** is a 2×2 of quadrants with optional axis captions. A **table** is for exact values a reader looks up — three plans against four attributes, a short line-item budget — where the numbers themselves are the point, not the shape. It is not a chart substitute: reach for a chart when the shape carries the meaning, a table when the digits do. The first item line is the header; each line after it is a data row with the same cell count, and a leading `!` marks the one row that leads. Instead of typing rows, `data: costs.csv` loads the header and rows from a CSV in the spec's folder (mutually exclusive with inline rows), and `emphasis: <label>` marks the data row whose first cell equals `<label>`. A table takes 2–5 columns and 1–8 data rows (fewer if the band is short); past that the render fails naming how many rows fit. It styles straight from tokens: an ink header band, paper rows on muted hairlines, at most one accent row, and numeric columns right-aligned.

```
Block: table
Plan | Price | Seats
Starter | $12 | 3
! Growth | $40 | 25
```

**Icons.** A curated set of on-brand line icons (recoloured to a token colour) is available: as an `icon-list`, as a `[icon-name]` prefix on a `card-grid`, `tree`, `process`, or `comparison` item, or in `freeform` (`icon <name> <colour> at <placement>`). Icons need `cairosvg` (`pip install cairosvg`); absent, they are skipped and the summary says so. See `assets/icons/` for the names.

### Freeform — compose anything else

The named blocks are shortcuts for the shapes that recur most; they are not the whole vocabulary. When an idea wants something they don't cover — a 2×2 matrix, a quadrant, a node graph, an annotated diagram — use `Block: freeform` and place the elements yourself. Each line is one element:

```
Block: freeform
panel paper outline ink at cols 1-6 rows 1-8
text h1 ink at cols 1-6 rows 1-3 | Three markets
arrow ink at cols 7-7 rows 4-5
panel accent at cols 8-12 rows 1-8
text h1 paper at cols 8-12 rows 1-3 | One backbone
```

- `panel <fill> [outline <stroke>]` (or `box …`) — a filled, optionally outlined box that can hold text.
- `text <scale> <colour> | the words` — `<scale>` is `display` / `h1` / `body` / `caption`.
- `arrow <colour>`, `dot <colour>`, `line <colour>` — a connector, a marker, a hairline divider.
- `<colour>` is a role name — `ink`, `paper`, `accent`, `muted` — never a hex, so it stays on-brand.
- `at <placement>` positions the element on the block's 12×12 grid (`cols A-B`, `rows C-D`, or a shortcut).

Freeform gives freedom, not a safety net beyond the lint: it guarantees the result is *on-brand* (token colours, on the grid, no overlap, under the element cap), not that it is *well composed* — that is your judgement. Its one advisory nudge is grey-push: keep the accent to one or two marks.

### Several blocks, and placement

A composed slide takes up to four blocks. With no placement they **stack** top to bottom. Or place each on the grid with `at`: `Block: card-grid at cols 1-6` (left half), `at cols 7-12` (right half), the shortcuts `at left` / `at right` / `at top` / `at bottom`, or a quadrant like `at cols 1-6 rows 7-12` (lower left) over a 12-column by 12-row band. Either place every block or none — not a mix. Every primitive draws only in the brand's token colours and type-scale sizes, snapped within the grid. A composed slide that would place an off-token colour, an off-scale size, an element outside the margins, overlapping elements, or more than the element cap fails the render with a named error rather than an off-brand slide — the mechanical lint is what makes free composition safe. Beyond that hard gate, `build-deck` runs an *advisory* review for each primitive (count, terseness, one-accent, and the cliché guards) and prints non-blocking notes in the run summary; see [composition.md](composition.md) and [design-research.md](design-research.md). `build-deck` draws `composed` on the layout named in `layout_map` (falling back to the `statement`, then `title` layout).

## The Visual field

Any slide may carry an optional `Visual:` field: a plain-language description of an image, diagram, or chart that belongs on that slide ("a full-bleed photograph of the real product in use"; "a column chart, four quarters, Q4 coloured to carry the point"). `build-deck` does not draw it — it records the description in the slide's speaker notes, prefixed `VISUAL TO ADD:`, so the person finishing the deck knows exactly what to place and why. Use `Visual:` for anything `build-deck` cannot draw: photographs, concept diagrams, and the chart families it does not support (histogram, map); for the families it does draw, use the `Chart:` field below. Choosing the right chart or diagram is craft, taught in [data-viz.md](data-viz.md); placing it is a deliberate human step, not a thing code guesses.

## The Chart field

A `title-content` slide may carry a `Chart:` block: structured data `build-deck` draws as an on-brand chart and places below the slide's content. `Chart:` and `Body:` may both appear — the one-line `Body:` explains the chart above it (one of the two is required). `Chart:` is allowed on `title-content` only. Write `Chart:` on its own line, then indented `key: value` lines. The types fall in two data shapes:

- **Category charts** — `type: bar` (horizontal), `type: column` (vertical), `type: pie` (part-to-whole), or `type: waterfall` (a running total built from signed deltas). Need `categories:` (comma-separated labels) and `series <Name>:` (comma-separated numbers, one per category). `bar`/`column` take one or more series; `pie` and `waterfall` take exactly one. On `bar`/`column`/`pie`, optional `emphasis:` names the one category to colour in the brand accent (one slice, for a pie); the rest go muted (a waterfall colours by sign instead — see below). Optional `callout:` is a short annotation. A multi-series `bar`/`column` may add `stacked: true` to draw one full-width bar per category, one total label per stack (needs ≥2 series; not combined with `emphasis:`).
- **Point charts** — `type: line` (filled) or `type: scatter` (dots). Need `points:` as comma-separated `x y` pairs. Optional `marker: <x> <label>` annotates the point at that x. Optional `callout:`. `emphasis:` does not apply.

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

Instead of typing the data inline, a chart may read it from a CSV with `data: <file.csv>` (resolved against the spec's folder) — `data:` and the inline `categories`/`series`/`points` are mutually exclusive. A category chart's CSV is a header row (`category, Series1, Series2, …`) then one row per category; a point chart's first two columns are `x, y`. So a spreadsheet exports straight to a chart, and multiple series draw as grouped bars. Format the value labels with `format:` — `$` (currency), `%` (percent), or `$k` / `$m` (currency in thousands / millions, so `362` reads as `$362k`); or set `prefix:` / `suffix:` directly. Large numbers abbreviate by default (`362000` → `362k`); `format: plain` keeps them exact. `native: true` draws a native, editable PowerPoint chart instead of an image, for `bar`/`column`/`pie`/`line`/`scatter`; a chart PowerPoint can't draw that way (`waterfall`) or one carrying a drawn annotation (`target:`, `callout:`, `marker:`) falls back to the image automatically and the run summary names why. Without `format:`, native value labels show exact numbers (`General`) — the image path's automatic abbreviation isn't expressible natively. Optional `target: <value> [| label]` draws a goal line on `column`, `bar`, or `line` charts (image path), extending the axis to include it. A **waterfall** shows how a starting figure becomes an ending one — a running total built from signed changes. It is a category chart with exactly one `series` of signed deltas: a positive number rises, a negative one falls, and `build-deck` appends a computed total bar at the end. Rises take the brand accent, falls a distinct spend tone (a muted grey when the brand names no spend colour), and the total bar sits in ink — so the sign already carries the emphasis. `emphasis:` is therefore rejected on a waterfall; use `callout:` to point at a bar. The delta labels are signed (`+$40k` / `-$15k`); the total is unsigned. `total: Closing` renames the total bar, `total: none` drops it. Like every chart, a waterfall can read its deltas from a CSV with `data:`.

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

## Speaker notes

Any slide may carry `Notes:` — what the presenter says, or, for a read deck, the context a reader needs. Notes are prose and are held to the prose-slop standard in [slop.md](slop.md). The slide is not the script; the notes are.

## The brand profile (`brand.json`)

`build-deck` needs two inputs: the deck spec, and the user's brand profile. `teach-slides` writes `brand.json` into `.slides/`; `render.py` reads it. Its keys:

- `template` — path to the user's `.pptx`/`.potx` template.
- `fonts` — `{ "heading": "...", "body": "..." }`. Carried by the template; recorded here for reference and for `make_template.py`.
- `colours` — named brand colours as hex. Same: the template owns them; this records them.
- `layout_map` — maps each of the six roles (and, optionally, `composed`) to a layout index in the template. This is the join between a spec's semantic roles and the user's real layouts.
- `tokens` (optional) — the design-token system the `composed` role draws from: `grid` (margins, columns, gutter, baseline — from the template's mapped layouts), `type_scale` (display, h1, body, caption — **derived from the master's own title/body sizes**, so composed slides use the brand's real type), `colour_roles` (ink, paper, accent, muted — from the palette), and `shape` (corner: rounded|sharp, hairline — the brand's box style). Omit it and `build-deck` derives sensible defaults at render time; `init_brand.py`/`extract_brand.py` write a starting block you can edit. Fixed-role slides ignore `tokens`, so existing decks are unaffected.

`render.py` validates the four required keys (`tokens` is optional) and reports the missing or malformed one by name rather than emitting a broken file. `teach-slides` can fill `fonts` and `colours` automatically: pointed at a template or an existing deck, `extract_brand.py` reads the heading and body fonts and the palette (accent colours plus `ink` and `paper`) straight from the file's theme, so the profile reflects the real deck instead of hand-typed values, and the user confirms or adjusts what it read. `init_brand.py` goes one step further — it writes a complete `brand.json` (`template`, `fonts`, `colours`, and a proposed `layout_map`) from a single template or deck, so a project can be brand-ready without the full interview; `build-deck` and `narrative` offer this when `.slides/` is missing, and the user confirms the result and can refine it later with `teach-slides`.

## The lineage stamp

`build-deck` stamps every rendered deck's `core_properties.comments` with `slides-spec: <spec basename> sha256:<sha256 of the spec file>`, overwriting whatever a template's own comments field held — a generated deck's comments are the pack's to set, by design.
The `revise` skill reads the stamp to find and sync a deck's spec (`deck_to_spec.py --against`); a deck with no stamp, or whose named spec no longer exists, is imported best-effort instead (the foreign tier).

## Rules the spec must hold

- Slides numbered 1..N with no gaps; every slide has a `layout:` line first.
- Only the fields its role allows, plus optional `Visual:` and `Notes:`.
- For the six fixed roles, `render.py` fills only the template's existing placeholders and adds no shape — so a spec cannot smuggle a tacked-on strapline onto one. The `composed` role is the one carve-out: it draws token-bound primitives, but every element must pass the mechanical lint (token colour, scale size, within margins, no overlap, under the element cap) before it is added, so a composed slide cannot go off-brand either.
- A malformed spec fails loudly: `render.py` exits non-zero naming the offending slide and line. It never emits a half-built `.pptx`.
