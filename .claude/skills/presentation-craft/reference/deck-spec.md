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

A role is a *semantic* job, not a template layout. `build-deck` resolves each role to one of the user's own template layouts through `brand.json`'s `layout_map`, then fills that layout's placeholders. Six roles cover the decks this skill builds:

| Role | Job | Fields (in order) |
|------|-----|-------------------|
| `title` | The opening slide | `Title`, `Subtitle` (optional) |
| `section` | A divider that signposts a new part | `Title` |
| `statement` | A single hero idea — a number, a phrase, a claim | `Statement` |
| `title-content` | A heading and its supporting content | `Title`, `Body` |
| `two-column` | A two-part comparison or pairing | `Title`, `Left`, `Right` |
| `quote` | A quotation given room to breathe | `Quote`, `Attribution` (optional) |

`Body`, `Left`, and `Right` are block fields: a tight bullet list, or one or two short paragraphs. One idea per slide still holds — a `title-content` slide carries one point and the few lines that earn it, not a wall.

## The Visual field

Any slide may carry an optional `Visual:` field: a plain-language description of an image, diagram, or chart that belongs on that slide ("a full-bleed photograph of the real product in use"; "a column chart, four quarters, Q4 coloured to carry the point").

`build-deck` does not draw the visual. It records the description in the slide's speaker notes, prefixed `VISUAL TO ADD:`, so the person finishing the deck knows exactly what to place and why. Choosing the right chart or diagram is craft, taught in [data-viz.md](data-viz.md); placing it is a deliberate human step, not a thing code guesses.

## Speaker notes

Any slide may carry `Notes:` — what the presenter says, or, for a read deck, the context a reader needs. Notes are prose and are held to the prose-slop standard in [slop.md](slop.md). The slide is not the script; the notes are.

## The brand profile (`brand.json`)

`build-deck` needs two inputs: the deck spec, and the user's brand profile. `teach-slides` writes `brand.json` into `.slides/`; `render.py` reads it. Its keys:

- `template` — path to the user's `.pptx`/`.potx` template.
- `fonts` — `{ "heading": "...", "body": "..." }`. Carried by the template; recorded here for reference and for `make_template.py`.
- `colours` — named brand colours as hex. Same: the template owns them; this records them.
- `layout_map` — maps each of the six roles to a layout index in the template. This is the join between a spec's semantic roles and the user's real layouts.

`render.py` validates all four keys and reports the missing or malformed one by name rather than emitting a broken file.

## Rules the spec must hold

- Slides numbered 1..N with no gaps; every slide has a `layout:` line first.
- Only the fields its role allows, plus optional `Visual:` and `Notes:`.
- `render.py` fills only the template's existing placeholders. It never adds a text box, so a spec cannot smuggle a tacked-on strapline onto a slide — there is nowhere off-template for one to go.
- A malformed spec fails loudly: `render.py` exits non-zero naming the offending slide and line. It never emits a half-built `.pptx`.
</content>
</invoke>
