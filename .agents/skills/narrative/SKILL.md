---
name: narrative
description: Shape a vague idea into a deck story through real back-and-forth, then write a deck spec the build-deck skill can render.
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. If `.slides/` is absent or incomplete, set up the brand first, then resume here: offer the fast path (`../build-deck/scripts/init_brand.py` reads fonts and colours from a template or an existing deck and writes a brand-fidelity profile) or the fuller `teach-slides` (via `$skill teach-slides` or `/skills`) interview.

Read [narrative.md](../presentation-craft/reference/narrative.md) for the Plan and Create craft, [slop.md](../presentation-craft/reference/slop.md) for the full detector, and [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the file you will write.

---

*(Treat the user's message that invoked this skill as the task input.)*

You shape a vague idea into a deck story. This is a conversation, not a one-shot generation. You and the user work `presentation-craft`'s Plan, then Create, with the user answering and deciding at each step. The output is a `<deck>.deck.md` file that `build-deck` (via `$skill build-deck` or `/skills`) renders.

Do not race to slides. A deck spec written without the thinking comes out generic. The thinking is the work.

## Push back on thin input

A one-line prompt is a starting point, not a brief. If the user hands you "a deck about our Q3 results", you do not produce a deck spec. You ask the discovery questions below and wait.

## Step 1: Plan, who and why

Settle who the deck is for and the job it has to do. Work these with the user:

- **Register.** Presented live, read without a narrator, or both. This sets how hard each slide works.
- **Audience.** Their role, what they already know, what they walked in wanting. One real audience, not "everyone".
- **The gap.** Where the audience stands now, and where they need to stand after. The deck closes that gap.
- **Think, feel, do.** What the audience should think, feel, and do once the deck ends.
- **Common ground.** What you and the audience already agree on. The story starts there.



Ask the user these questions and wait for the answers. Do not move to Step 2 until Plan is settled and the user has confirmed it.

**Stop and wait.** Show the user the Plan in a few lines. Get a yes before going on.

## Step 2: Create, the story and the outline

With Plan agreed, shape what the deck says:

- **The one idea.** One sentence the whole deck serves. If the deck has two ideas, it is two decks.
- **The story structure.** A deliberate arc, not a topic list. Common ground, then the gap, then the path, then the resolution. See `narrative.md`.
- **The storyboard.** Work the slide-by-slide outline as a list before any slide exists. Each slide carries one point.
- **Give each beat the form its one idea needs.** As you storyboard, name the shape each idea wants — a slide is rarely a heading over bullets, and that default is the slop. The named compositions are *common* shapes, not the whole world: a set of 3–5 siblings (a **card grid**), a contrast that resolves (a **comparison**), an ordered sequence (a **process**), dated milestones (a **timeline**), a few hero numbers (a **stat row**), values the audience will read rather than compare (a **table**). When the idea is something else — a node graph, an annotated diagram, a bespoke figure — compose it **freeform** (boxes, text, arrows placed exactly, to grid cells or percent bounds) rather than bending it into the nearest named shape. A design-led beat — the title, a section turn, the hero statement — may be composed *entirely*: freeform with fine percent placement on a `Canvas:` ground, for the moments that carry the deck. And when a beat's data fits no chart type, hand-drawing the graphic is encouraged — a dumbbell, a slope: percent placement means you place data accurately. Do not force-fit; the form serves the idea, not the menu. `build-deck` draws all of these as real, on-brand boxes.
- **Decide the deck-level brief.** Two lines that govern every slide, settled here and written into the spec's frontmatter: `structure:`, the ground plan — which beats sit on ink and which on paper (the dark-open-and-close sandwich around light evidence, or a deck committed to dark throughout) — and `motif:`, the one element repeated across the deck so the slides read as one object rather than a sequence. A deck with neither reads as a template sequence, whatever each slide does alone.
- **Commit the brief for each beat.** Before a slide exists, say four things out loud: the one thing it carries; the form that one thing earns, and *why this content needs this shape* rather than the shape you reach for by default; what leads the eye; and a named reference for the look — a specific deck, page, or object, never an adjective like "clean" or "modern". If you cannot name why the content earns the form, the beat has not earned that form — it wants a different one, or it wants cutting. The render only executes this decision; make it here, in the outline the user signs off, not at the moment a box gets drawn.
- **Test every message.** A bare fact does not persuade. For each beat, find the story or the consequence that makes the audience reach the conclusion themselves.

**Stop and wait.** Show the user the outline, one line per slide. Walk it with them. Take their cuts and reorderings before you write the spec.

## Step 3: Run the slop detector

The detector runs in two phases, both from `slop.md`.

**Reflex Rejection, while drafting.** Before you write a title, a slide, or a note, name the reflex you are about to reach for and reject it: the tacked-on strapline, the wall of text, the slide-as-script, bullet soup, the deck about the presenter, unearned hype — and the *device reflex*, reaching for a hero number, a dumbbell, a big-text statement because that is what you always reach for, not because this beat earns it. The device is never the problem; the reflex is. A hero metric is right when one number is the whole point; a dumbbell when the gap between two values is the message; big text when the line is the turn. Earn the form from the content. Do not ban the device, and do not default to it — replace each reflex with the form the beat's brief called for.

**The slop check, on the outline.** Before you agree the outline with the user, run the Deck Slop Test and the five-dimension prose score. Fix what it finds. Read the outline as a whole, too: if one device carries slide after slide — three hero-number slides, a run of dumbbells, five near-identical stat rows — that repetition is its own slop, however good each slide reads alone. Vary the form across the deck; a deck of one device reads as a template, not as your argument. The skill that produces decks must not produce slop.

## Step 4: Write the deck spec

Write `<deck>.deck.md`, conforming to [deck-spec.md](../presentation-craft/reference/deck-spec.md):

- A frontmatter block: `deck`, `audience`, `register`, plus `structure:` and `motif:` — the deck-level brief you settled in Step 2. Write both; `build-deck` composes from them and warns when a presented deck has neither.
- One `## Slide N` section per slide, numbered 1..N with no gaps.
- `layout:` first on each slide — and choose it by asking the beat's form first. The storyboard already named the shape each idea wants (Step 2); the spec is where that survives or dies. A beat with a form — a set, a contrast, a sequence, milestones, hero numbers, exact values, data — is `layout: composed` (or a `Chart:`). The six fixed roles — `title`, `section`, `statement`, `title-content`, `two-column`, `quote` — carry the framing beats: a true title, a divider, a single hero claim, a quotation, one image or a chart with a line or two of prose. A design-led framing beat may instead be `composed` entirely — a title, section, or statement moment built freeform with percent placement and a `Canvas:` ground, when the storyboard named that treatment. `title-content` over bullets is a deliberate choice for a genuinely prose beat, never the fallback for an unshaped one — a heading over bullets is the default Step 2 called slop.
- `Brief:` directly after `layout:` on every slide — Step 2's four-part composition brief for that beat in one line: the one thing it carries; the form that one thing earns and why; what leads the eye; the named reference. `build-deck` composes from it and never draws it.
- A composed slide carries an optional `Title:` and one or more `Block:` lines. Named shortcuts cover the common shapes — `stat-row`, `card-grid`, `comparison`, `process`, `timeline`, `tree` (an org chart / decomposition), `cycle` (a loop of stages), `matrix` (a 2×2 of quadrants), `table` (exact values side by side), and `icon-list` (icons as bullets) — and `freeform` places token-bound boxes, text, arrows, and icons on the grid for anything else. On-brand line **icons** are available too: as an `icon-list`, a `[icon-name]` prefix on a card or tree node, or in freeform. Every block is drawn as token-locked shapes that pass a mechanical lint, so none can go off-brand. Prefix the one card / winning panel / turning-point milestone / lead node with `!` to make it lead. Blocks stack, or place them with `at cols 1-6` / `at left`.
- The named blocks are good by construction — fast paths, not the ceiling. `freeform` trades that guarantee for freedom and leans on your judgement (the lint still guarantees on-brand, but not well-composed): it is the main stage for design-led slides and for hand-drawn data graphics — percent placement (`x A%-B%` / `y A%-B%`) puts an element at exact fractions of the band, and a `full-bleed` panel colour-blocks the slide behind the content. Keep the accent to one or two marks. The grammar is in [deck-spec.md](../presentation-craft/reference/deck-spec.md); what good looks like is in [composition.md](../presentation-craft/reference/composition.md) and [design-research.md](../presentation-craft/reference/design-research.md).
- Reserve `Visual:` for what code cannot draw at all — a photograph, a real diagram, an unsupported chart. A fixed role stays right for a true title, a section divider, a single hero statement, one image, or a chart with a line or two.
- Only the fields the role allows, plus `Brief:` and optional `Visual:` and `Notes:`; a `title-content` slide may also carry a `Chart:` block.
- A `Visual:` field describes an image, diagram, or unsupported chart in plain words. `build-deck` records it as a note for a person to place; it does not draw it.
- A `Chart:` block carries structured data (bar, column, line, pie, scatter, or waterfall) that `build-deck` draws as an on-brand chart — reach for `native: true` when the deck travels to be edited, a board pack the recipient will tweak in PowerPoint. Use it when the data fits one of those; use `Visual:` for everything else (histograms, maps, diagrams, photos). The format is in [deck-spec.md](../presentation-craft/reference/deck-spec.md).
- `Notes:` carries what the presenter says. Notes are prose and held to the prose-slop standard.

The spec carries content and structure only, never fonts, colours, or coordinates. Those live in `brand.json` (and, for template fidelity, the template).

A half-finished spec is a valid file. If the conversation has to pause, write what you have. The user, or a later run, can resume from it.

When the spec is written, name the file and point the user at `build-deck` (via `$skill build-deck` or `/skills`) to render it, `slop-check` (via `$skill slop-check` or `/skills`) to audit it first, or `revise` (via `$skill revise` or `/skills`) to change it after rendering.
