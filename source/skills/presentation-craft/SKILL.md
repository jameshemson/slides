---
name: presentation-craft
description: Core knowledge for making on-brand, slop-free presentations. Premise, the Plan-Create-Deliver method, the operational slop detector, and the reference library. Loaded by every slides command skill.
---

This skill holds the presentation craft that the slides skill pack is built on. It
is not invoked on its own. The teach-slides, narrative, build-deck, and slop-check
skills each load it first, so the premise, the method, and the slop detector govern
every deck the pack produces.

## Premise

Three ideas shape everything below.

**A presentation is communication, not information transfer.** The slides are what
stands behind the speaker. The communication is what happens in front: the speaker
and the audience, in a room together. A deck that only moves information is a
document. The job is to change what the audience thinks, feels, and does.

**The audience is the hero.** The presenter is the mentor, and a mentor's job is to
get the hero somewhere. A deck that is about the presenter, or about how good the
product is, has the roles reversed.

**Story moves people; facts alone do not.** Faced with facts that contradict them,
people dig in. A story lets the audience reach the conclusion on their own and make
it theirs. Story leads, facts support. A pile of facts is not persuasion.

## The method: Plan, Create, Deliver

Plan, Create, Deliver is the arc of making any presentation. Most of the work sits
in Plan and Create, the thinking, before a single slide exists.

- **Plan.** Who the deck is for and the job it has to do. The register, the
  audience, the common ground, what they should think, feel, and do, and the gap
  from where they are to where they need to be.
- **Create.** What the deck says and the shape it takes. The one idea, a storyboard
  worked before any slide, every message tested past bare facts, and a deliberate
  story structure.
- **Deliver.** How the deck is presented. Kept lean: the skill builds decks, not
  speakers. It shapes the speaker notes and offers a short primer.

## Context Gathering Protocol

A deck built without the user's brand context comes out generic and off-brand. You
MUST have confirmed brand context before doing any deck work.

**Required context.** The user's brand profile: their template, fonts, colours,
voice, and audience norms. This lives in a `.slides/` directory at the project root,
written by the teach-slides skill, with `brand.json` as its core file.

**Gathering order:**

1. **Check for `.slides/` (fast).** Read `.slides/brand.json` from the project root.
   If it exists and carries the required keys, proceed.
2. **Run teach-slides (REQUIRED).** If `.slides/` is absent or incomplete, run the
   teach-slides skill NOW, before anything else. Do NOT infer a brand from guesswork
   and do NOT impose a default look. Once teach-slides has written the brand
   profile, resume the original task.

Every command skill in the pack performs this check before it builds. The brand
profile is the join between the constant craft and the user's own look.

## The operational slop detector

The slop detector runs in two phases. Reflex Rejection fires pre-generation. The
Deck Slop Test fires post-generation. Both must pass. The full taxonomy, both
layers, and the score live in `reference/slop.md`; the version below is the
operational, always-loaded one.

### Reflex Rejection (pre-generation)

Before writing a slide, a title, or a speaker note, name the reflex you are about to
reach for, and reject it. Common reflexes to catch and replace:

- A title, then content, then a slogan floated at the bottom of the slide.
- A slide written as a wall of text, or as a script to be read aloud.
- A bullet list of six or more loose, unrelated sentences.
- A title that restates the body, or a body that restates the title.
- A deck about the presenter or the product instead of the audience.
- Superlatives, hype, and urgency with nothing concrete beneath them.
- A chart or diagram that decorates rather than clarifies.
- Throat-clearing openers, business jargon, em dashes, passive voice.

Replace each with the craft in the reference files before generating.

### Deck Slop Test (post-generation)

Before delivering a deck or an outline, check every item:

- [ ] No tacked-on strapline on any slide.
- [ ] No slide is a wall of text or a script to be read aloud.
- [ ] No bullet-soup slide; every list shares one parent point.
- [ ] No title and body restating each other.
- [ ] The audience is the hero, not the presenter or the product.
- [ ] Story carries the deck; facts support it.
- [ ] Every emotional beat is earned by something true and concrete.
- [ ] Every chart, diagram, and image makes its idea clearer than words alone.
- [ ] The treatment matches the deck's register.
- [ ] No leftover scaffolding, placeholder text, or filler slides.
- [ ] Prose passes the Layer 2 quick checks in `slop.md`.

The detector returns severity-ranked findings, not a pass-or-fail verdict.

### Absolute bans

Match and refuse on sight, every time:

- **The tacked-on strapline.** A title, the content, then a tagline floated along
  the bottom of a slide. An AI tic, not a design. A slide has its content; it does
  not need a motto. Rebuild the slide without it.
- **Leftover scaffolding.** Placeholder text, lorem ipsum, unedited template
  furniture, and sample names never ship.
- **Unearned emotion.** Sensationalism, ad-copy voice, and hype with nothing
  concrete beneath them. Earned emotion, grounded in a true and specific thing, is
  kept; the unearned kind is refused.

## The reference library

Six reference files carry the full craft. Read the one the task needs.

- **`reference/narrative.md`**: Plan and Create. Read when working the story, the
  audience, and the slide-by-slide outline.
- **`reference/slides.md`**: visual craft. Read when designing how the slides look.
- **`reference/data-viz.md`**: charts and diagrams. Read when a slide carries data
  or a concept that needs a picture.
- **`reference/delivery.md`**: delivery and speaker notes. Read when writing the
  notes or the delivery primer.
- **`reference/slop.md`**: the full slop detector, three layers and the score. Read
  when running the slop check or when in doubt about a slop call.
- **`reference/ai-voice.md`**: Layer 3 of the detector, the AI-voice tells (the
  Claudism catalogue, vocabulary watchlist, assistant-artifact slop). Read with
  `slop.md` when running the slop check.
- **`reference/deck-spec.md`**: the deck spec format. Read when writing or reading
  a `.deck.md` file.
