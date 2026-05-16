---
name: narrative
description: Shape a vague idea into a deck story through real back-and-forth, then write a deck spec the build-deck skill can render.
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. If `.slides/` is absent or incomplete, run `teach-slides` (via the skill tool) first, then resume here.

Read [narrative.md](../presentation-craft/reference/narrative.md) for the Plan and Create craft, [slop.md](../presentation-craft/reference/slop.md) for the full detector, and [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the file you will write.

---

*(Treat the user's message that invoked this skill as the task input.)*

You shape a vague idea into a deck story. This is a conversation, not a one-shot generation. You and the user work `presentation-craft`'s Plan, then Create, with the user answering and deciding at each step. The output is a `<deck>.deck.md` file that `build-deck` (via the skill tool) renders.

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
- **Test every message.** A bare fact does not persuade. For each beat, find the story or the consequence that makes the audience reach the conclusion themselves.

**Stop and wait.** Show the user the outline, one line per slide. Walk it with them. Take their cuts and reorderings before you write the spec.

## Step 3: Run the slop detector

The detector runs in two phases, both from `slop.md`.

**Reflex Rejection, while drafting.** Before you write a title, a slide, or a note, name the reflex you are about to reach for and reject it: the tacked-on strapline, the wall of text, the slide-as-script, bullet soup, the deck about the presenter, unearned hype. Replace each with the craft before generating.

**The slop check, on the outline.** Before you agree the outline with the user, run the Deck Slop Test and the five-dimension prose score. Fix what it finds. The skill that produces decks must not produce slop.

## Step 4: Write the deck spec

Write `<deck>.deck.md`, conforming to [deck-spec.md](../presentation-craft/reference/deck-spec.md):

- A frontmatter block: `deck`, `audience`, `register`.
- One `## Slide N` section per slide, numbered 1..N with no gaps.
- `layout:` first on each slide, one of the six roles: `title`, `section`, `statement`, `title-content`, `two-column`, `quote`.
- Only the fields the role allows, plus optional `Visual:` and `Notes:`.
- A `Visual:` field describes an image, chart, or diagram in plain words. `build-deck` records it as a note for a person to place; it does not draw it.
- `Notes:` carries what the presenter says. Notes are prose and held to the prose-slop standard.

The spec carries content and structure only, never fonts, colours, or coordinates. Those live in the template and `brand.json`.

A half-finished spec is a valid file. If the conversation has to pause, write what you have. The user, or a later run, can resume from it.

When the spec is written, name the file and point the user at `build-deck` (via the skill tool) to render it, or `slop-check` (via the skill tool) to audit it first.
