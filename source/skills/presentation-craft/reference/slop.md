# The slop detector

The full specification for slop detection. The slop-check skill runs this standalone;
narrative and build-deck load it as a reference.

Slop is caught at two layers and in two phases.

**Two layers.** Layer 1 is presentation slop: the deck and the slide as artifacts.
Layer 2 is prose slop: the sentences and the words, adopted from `stop-slop` by
Hardik Pandya (github.com/hardikpandya/stop-slop, MIT).

**Two phases.** Reflex rejection runs pre-generation: before writing a slide, a
title, or a note, name the reflex you are about to reach for and reject it. The slop
check runs post-generation: before delivering a deck or an outline, run the checks
and the score below.

The detector returns severity-ranked findings, not a pass-or-fail verdict.

## Layer 1: presentation slop

Each entry is match-and-refuse. If you are about to do it, stop and rebuild the
element.

- **The tacked-on strapline.** A title, then the content, then a tagline floated
  along the bottom of the slide. An AI tic, not a design. Refuse it by name. A slide
  has its content; it does not need a motto. *Detect:* a slide carries a short
  slogan field below or beside its real content, often a `Strapline:` line or three
  punchy words doing no informational work.
- **The slide as a document.** A wall of words on one slide. *Detect:* a slide whose
  body runs to dense paragraphs or more text than a glance can take in. Register-aware:
  a read deck carries more than a presented one, but a wall fails in either.
- **The slide as a script.** Text the presenter would read aloud word for word.
  *Detect:* slide copy written in full speaking sentences, the kind that belong in
  speaker notes, not on the slide.
- **Bullet soup.** Many loose, sentence-long, unrelated points on one slide.
  *Detect:* a bullet list of roughly six or more full sentences, or bullets that do
  not share one parent point. A chart with three or four tight, parallel points is
  not soup.
- **Restatement.** A title that restates the body, or a body that restates the
  title. *Detect:* the title and the content say the same thing in different words;
  one of them adds nothing.
- **Being the hero.** A deck about the presenter or about how good the product is.
  *Detect:* the deck's subject is the speaker or the product, and the audience and
  their gain are absent.
- **Facts without story.** A deck that is only data, with no through-line. *Detect:*
  slide after slide of figures with no narrative connecting them.
- **Sensationalising and ad-copy voice.** Unearned emotion: hype, superlatives, and
  drama with nothing concrete beneath them. *Detect:* superlative claims
  ("transform everything", "the future is here"), urgency or fear pitches, adjective
  stacks. Earned emotion, grounded in a true and specific thing, is kept. This is
  the line; flag only the unearned kind.
- **Decoration over communication.** A chart, diagram, image, or animation that does
  not make the idea clearer than words alone. *Detect:* chartjunk, boxes and arrows
  for show, a diagram that needs a key to decode, a stock-photo cliché, an image
  picked to fill space.
- **Register mismatch.** A spare image-led treatment forced onto a data deck, or a
  dense treatment forced onto a deck that will be presented live. *Detect:* the
  slide's density does not match the deck's stated register.
- **Leftover scaffolding.** Placeholder text, unedited template furniture, lorem
  ipsum, sample names, and filler slides ("Agenda", "Thank You", "Any questions?")
  that carry nothing. *Detect:* boilerplate strings, divider-slide defaults, and
  slides with no real content.

## Layer 2: prose slop

Adopted from `stop-slop` (Hardik Pandya, github.com/hardikpandya/stop-slop, MIT),
which removes AI tells from prose. It applies in full to speaker notes and to any
prose the skill writes. It applies in spirit to slide copy, which is terse by
nature: a slide title is a fragment by design, so the complete-sentences rule does
not govern slide copy. Everything else below holds for both.

### Core rules

1. **Cut filler.** Remove throat-clearing openers, emphasis crutches, and adverbs.
2. **Break formulaic structures.** No binary contrasts, negative listing, dramatic
   fragmentation, rhetorical setups, false agency.
3. **Active voice.** Every sentence has a human subject doing something. No passive.
   No inanimate thing performing a human action.
4. **Be specific.** No vague declaratives. Name the thing. No lazy extremes doing
   vague work.
5. **Put the reader in the room.** "You" beats "people". Specifics beat abstractions.
6. **Vary rhythm.** Mix sentence lengths. Two items beat three. No em dashes.
7. **Trust readers.** State facts directly; skip softening and hand-holding.
8. **Cut quotables.** If it sounds like a pull-quote, rewrite it.

### Banned phrases

- **Throat-clearing openers.** "Here's the thing", "Here's what / why", "The truth
  is", "It turns out", "Let me be clear", "The real X is".
- **Emphasis crutches.** "Full stop.", "Period.", "Let that sink in.", "Make no
  mistake", "This matters because".
- **Business jargon.** navigate, unpack, lean into, landscape, game-changer, double
  down, deep dive, take a step back, moving forward, circle back, on the same page.
- **Adverbs.** Kill -ly words, and "really", "just", "literally", "genuinely",
  "honestly", "simply", "actually", "deeply", "truly", "fundamentally",
  "interestingly", "importantly", "crucially".
- **Filler.** "At its core", "In today's [X]", "It's worth noting", "At the end of
  the day", "When it comes to", "In a world where", "The reality is".
- **Meta-commentary.** "Hint:", "Plot twist:", "X is a feature not a bug", "Let me
  walk you through", "In this section we'll", "As we'll see".
- **Telling instead of showing.** "This is genuinely hard", "This is what leadership
  actually looks like", "actually matters".
- **Vague declaratives.** "The reasons are structural", "The implications are
  significant", "The stakes are high". Name the specific thing.

### Banned structures

- **Binary contrasts.** "Not X, it's Y", "X isn't the problem, Y is", "not just X
  but Y". State Y directly.
- **Negative listing.** "Not a X. Not a Y. A Z." State Z.
- **Dramatic fragmentation.** "[Noun]. That's it.", "X. And Y. And Z." Use complete
  sentences.
- **Rhetorical setups.** "What if [reframe]?", "Here's what I mean:", "Think about
  it:", "And that's okay." Make the point.
- **False agency.** Inanimate things doing human verbs: "the data tells us", "the
  culture shifts". Name the human, or use "you".
- **Narrator-from-a-distance.** "Nobody designed this", "People tend to". Put the
  reader in the room.
- **Passive voice.** "X was created", "mistakes were made". Name the actor first.
- **Wh- sentence starters.** Restructure; lead with the subject.
- **Rhythm tics.** Three-item lists where two would do, every paragraph ending
  punchily, staccato fragmentation, em dashes (remove, always).
- **Lazy extremes.** every, always, never, everyone, nobody. Use specifics.

The exhaustive phrase and structure lists live in stop-slop's `references/phrases.md`
and `references/structures.md`; adopt them wholesale.

### Quick checks

Before delivering any prose: adverbs killed; passive voice has a named actor; no
inanimate thing doing a human verb; no Wh- starters; no "here's what / this / that"
throat-clearing; no "not X, it's Y" contrasts; sentence lengths vary; no em dashes;
vague declaratives replaced with the specific thing; the reader is in the scene; no
meta-joiners.

### Scoring

Rate the deck's written content 1 to 10 on each dimension: **Directness**
(statements, not announcements), **Rhythm** (varied, not metronomic), **Trust**
(respects the reader), **Authenticity** (sounds human), **Density** (nothing
cuttable). Below 35 out of 50, revise.

## The emotion line

The detector passes earned emotion and catches only unearned emotion. Emotion
grounded in something true and concrete, a real situation or consequence or person,
is kept; the skill teaches it on purpose. Sensationalism, hype, ad-copy voice, and
adjective soup with nothing concrete beneath them are caught. Do not flag emotional
language wholesale. Flag emotion that has not been earned.
