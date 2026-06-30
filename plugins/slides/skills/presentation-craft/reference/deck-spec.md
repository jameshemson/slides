# The deck spec

A deck spec is the contract between thinking and building. `narrative` writes one; `build-deck` reads it and renders the `.pptx`; `slop-check` reviews it; a person can read and edit it directly. It is plain Markdown — a half-finished spec is still a valid, resumable file.

A deck spec carries the *content and structure* of a deck. It never carries fonts, colours, or coordinates: those live in the user's template and `brand.json`. The spec says what each slide means; the template says how it looks.

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

A role is a *semantic* job, not a template layout. `build-deck` resolves each role to one of the user's own template layouts through `brand.json`'s `layout_map`, then fills that layout's placeholders. Six fixed roles cover most decks; a seventh mode, `composed`, composes brand-locked primitives on the grid (see [The composed role](#the-composed-role)).

| Role | Job | Fields (in order) |
|------|-----|-------------------|
| `title` | The opening slide | `Title`, `Subtitle` (optional) |
| `section` | A divider that signposts a new part | `Title` |
| `statement` | A single hero idea — a number, a phrase, a claim | `Statement` |
| `title-content` | A heading and its supporting content | `Title`, `Body` |
| `two-column` | A two-part comparison or pairing | `Title`, `Left`, `Right` |
| `quote` | A quotation given room to breathe | `Quote`, `Attribution` (optional) |

`Body`, `Left`, and `Right` are block fields: a tight bullet list, or one or two short paragraphs. One idea per slide still holds — a `title-content` slide carries one point and the few lines that earn it, not a wall.

## The composed role

`layout: composed` is a different mode. Instead of filling a fixed layout's placeholders, it composes brand-locked *primitives* on the template's own grid — invention in the arrangement, consistency guaranteed by the design tokens (below) and a mechanical lint. The six fixed roles stay the safe default; `composed` is for a bespoke arrangement that still cannot go off-brand.

A composed slide carries an optional `Title:`, an optional `Notes:`, and a `Block:` line — naming a primitive, then its indented items:

```
## Slide 5
layout: composed
Title: What moved this quarter
Block: stat-row
56 | Days to close
4% | Win rate
120 | New deals
```

Primitives in this release:

- `stat-row` — a row of hero numbers with labels, spread evenly across the content width and snapped to the grid margins. Each item is `value | label`.

Every primitive draws only in the brand's token colours and type-scale sizes, snapped within the grid. A composed slide that would place an off-token colour, an off-scale size, an element outside the margins, overlapping elements, or more than the element cap fails the render with a named error rather than producing an off-brand slide — the mechanical lint is what makes free composition safe. `build-deck` draws `composed` on the layout named in `layout_map` (falling back to the `statement`, then `title` layout). This release takes one `Block:` per composed slide and auto-places it. Explicit grid placement (choosing rows and columns), stacking several blocks on one slide, and further primitives (card, table) are planned follow-ups.

## The Visual field

Any slide may carry an optional `Visual:` field: a plain-language description of an image, diagram, or chart that belongs on that slide ("a full-bleed photograph of the real product in use"; "a column chart, four quarters, Q4 coloured to carry the point").

`build-deck` does not draw the visual. It records the description in the slide's speaker notes, prefixed `VISUAL TO ADD:`, so the person finishing the deck knows exactly what to place and why. Choosing the right chart or diagram is craft, taught in [data-viz.md](data-viz.md); placing it is a deliberate human step, not a thing code guesses.

Use `Visual:` for anything `build-deck` cannot draw: photographs, concept diagrams, and the chart families not yet supported (scatter, histogram, map). For the bar, column, and line families, use the `Chart:` field below, which `build-deck` draws.

## The Chart field

A `title-content` slide may carry a `Chart:` block: structured data `build-deck` draws as an on-brand chart and places below the slide's content. `Chart:` and `Body:` may both appear — the one-line `Body:` explains the chart above it (one of the two is required). `Chart:` is allowed on `title-content` only.

`Chart:` is a block: write `Chart:` on its own line, then indented `key: value` lines. Five types in two data shapes:

- **Category charts** — `type: bar` (horizontal), `type: column` (vertical), or `type: pie` (part-to-whole). Need `categories:` (comma-separated labels) and `series <Name>:` (comma-separated numbers, one per category). `bar`/`column` take one or more series; `pie` takes exactly one. Optional `emphasis:` names the one category to colour in the brand accent (one slice, for a pie); the rest go muted. Optional `callout:` is a short annotation.
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

Colours come from `brand.json` `colours` (accent for the emphasis, a muted tone for the rest); the chart text uses the brand font when `brand.json` names a `font_files` path. Drawing needs `matplotlib` (`pip install matplotlib`). If it is not installed, the chart degrades to a `VISUAL TO ADD:` note built from the chart data, so the deck still builds. Choosing the right chart for the data is craft, taught in [data-viz.md](data-viz.md).

## Speaker notes

Any slide may carry `Notes:` — what the presenter says, or, for a read deck, the context a reader needs. Notes are prose and are held to the prose-slop standard in [slop.md](slop.md). The slide is not the script; the notes are.

## The brand profile (`brand.json`)

`build-deck` needs two inputs: the deck spec, and the user's brand profile. `teach-slides` writes `brand.json` into `.slides/`; `render.py` reads it. Its keys:

- `template` — path to the user's `.pptx`/`.potx` template.
- `fonts` — `{ "heading": "...", "body": "..." }`. Carried by the template; recorded here for reference and for `make_template.py`.
- `colours` — named brand colours as hex. Same: the template owns them; this records them.
- `layout_map` — maps each of the six roles (and, optionally, `composed`) to a layout index in the template. This is the join between a spec's semantic roles and the user's real layouts.
- `tokens` (optional) — the design-token system the `composed` role draws from: `grid` (margins, columns, gutter, baseline — derived from the geometry of the template's own mapped layouts), `type_scale` (named point sizes: display, h1, body, caption), and `colour_roles` (ink, paper, accent, muted — mapped from the palette). Omit it and `build-deck` derives sensible defaults at render time; `init_brand.py`/`extract_brand.py` write a starting block you can edit. Fixed-role slides ignore `tokens`, so existing decks are unaffected.

`render.py` validates the four required keys (`tokens` is optional) and reports the missing or malformed one by name rather than emitting a broken file.

`teach-slides` can fill `fonts` and `colours` automatically. Pointed at a template or an existing deck, `extract_brand.py` reads the heading and body fonts and the palette (accent colours plus `ink` and `paper`) straight from the file's theme, so the brand profile reflects the real deck instead of hand-typed values. The user confirms or adjusts what it read.

`init_brand.py` goes one step further: it writes a complete `brand.json` — `template`, `fonts`, `colours`, and a proposed `layout_map` — from a single template or deck, so a project can be brand-ready without the full interview. `build-deck` and `narrative` offer this when `.slides/` is missing; the user confirms the result and can refine it later with `teach-slides`.

## Rules the spec must hold

- Slides numbered 1..N with no gaps; every slide has a `layout:` line first.
- Only the fields its role allows, plus optional `Visual:` and `Notes:`.
- For the six fixed roles, `render.py` fills only the template's existing placeholders and adds no shape — so a spec cannot smuggle a tacked-on strapline onto one. The `composed` role is the one carve-out: it draws token-bound primitives, but every element must pass the mechanical lint (token colour, scale size, within margins, no overlap, under the element cap) before it is added, so a composed slide cannot go off-brand either.
- A malformed spec fails loudly: `render.py` exits non-zero naming the offending slide and line. It never emits a half-built `.pptx`.
