# The slop detector

The spec for the slides skill's slop detection. When the skill is built this becomes `presentation-craft/reference/slop.md`, loaded by `narrative` and `build-deck` and run standalone by `slop-check`.

Slop is caught at **two layers** and in **two phases**.

**Two layers:**
- **Presentation slop.** The deck and the slide as artifacts. Distilled from James's craft (see `approach.md`, `source-review.md`).
- **Prose slop.** The sentences and the words. Adopted from `stop-slop` by Hardik Pandya (github.com/hardikpandya/stop-slop, MIT).

**Two phases:**
- **Reflex rejection (pre-generation).** Before writing a slide, a title, or a speaker note, name the reflex you are about to reach for, and reject it.
- **Slop check (post-generation).** Before delivering a deck or an outline, run the checks below and the score.

---

## Layer 1: presentation slop

The deck and slide as artifacts. Each is match-and-refuse: if you are about to do it, stop and rebuild the element.

- **The tacked-on strapline.** A title, then the content, then a tagline floated along the bottom of the slide. An AI tic, not a design. Refuse it by name. A slide has its content; it does not need a motto.
- **The slide as a document.** Walls of text. Register-aware: a read deck carries more than a presented one, but never a wall of words (see `approach.md`).
- **The slide as a script.** Text on the slide that the presenter reads aloud word for word. The slide supports the speaker; it is not the speaker's lines.
- **Bullet soup.** Many loose, sentence-long, unrelated points. A chart with three or four tight, parallel supporting points is not soup; eight full sentences are.
- **Restatement.** A title that restates the body, or a body that restates the title. Each element earns its place by adding something.
- **Being the hero.** A deck about the presenter, or about how good the product is. The audience is the hero.
- **Facts without story.** A deck that is only data, with no through-line. Facts inform; story carries.
- **Sensationalising and ad-copy voice.** Unearned emotion: hype, superlatives, and drama with nothing concrete beneath them. Earned emotion, grounded in a true and specific thing, is kept. This is the line; Layer 2's "telling instead of showing" and "vague declaratives" catch the same fault at sentence level.
- **Decoration over communication.** A chart, diagram, image, or animation that does not make the idea clearer than words alone. Chartjunk, boxes-and-arrows for show, stock-photo cliché, an image picked to fill space.
- **Register mismatch.** A spare image-led treatment forced onto a data deck, or a dense treatment forced onto a deck that will be presented live.
- **Leftover scaffolding.** Placeholder text, unedited template furniture, lorem ipsum, sample names, and "Agenda / Thank You / Any questions?" filler slides that carry nothing.

The detector returns severity-ranked findings, not a pass or fail verdict.

---

## Layer 2: prose slop

Adopted from `stop-slop` by Hardik Pandya (github.com/hardikpandya/stop-slop, MIT). stop-slop removes AI tells from prose.

**How it applies to slides.** It applies in full to **speaker notes** and to any prose the skill writes. It applies in spirit to **slide copy**, which is terse by nature: a slide title is a fragment by design, so the "complete sentences, no fragmentation" rule is a prose rule and does not govern slide copy. Everything else below holds for slide copy as much as for notes.

### Core rules

1. **Cut filler.** Remove throat-clearing openers, emphasis crutches, and adverbs.
2. **Break formulaic structures.** No binary contrasts, negative listing, dramatic fragmentation, rhetorical setups, false agency.
3. **Active voice.** Every sentence has a human subject doing something. No passive. No inanimate thing performing a human action.
4. **Be specific.** No vague declaratives ("the implications are significant"). Name the thing. No lazy extremes ("every", "always", "never") doing vague work.
5. **Put the reader in the room.** "You" beats "people". Specifics beat abstractions.
6. **Vary rhythm.** Mix sentence lengths. Two items beat three. No em dashes.
7. **Trust readers.** State facts directly; skip softening and hand-holding.
8. **Cut quotables.** If it sounds like a pull-quote, rewrite it.

### Banned phrases

- **Throat-clearing openers.** "Here's the thing", "Here's what / why ...", "The truth is", "It turns out", "Let me be clear", "The real X is". Cut, and state the point.
- **Emphasis crutches.** "Full stop.", "Period.", "Let that sink in.", "Make no mistake", "This matters because".
- **Business jargon.** navigate, unpack, lean into, landscape, game-changer, double down, deep dive, take a step back, moving forward, circle back, on the same page. Use plain words.
- **Adverbs.** Kill -ly words, and "really", "just", "literally", "genuinely", "honestly", "simply", "actually", "deeply", "truly", "fundamentally", "interestingly", "importantly", "crucially".
- **Filler.** "At its core", "In today's [X]", "It's worth noting", "At the end of the day", "When it comes to", "In a world where", "The reality is".
- **Meta-commentary.** "Hint:", "Plot twist:", "X is a feature not a bug", "Let me walk you through", "In this section we'll", "As we'll see".
- **Telling instead of showing.** "This is genuinely hard", "This is what leadership actually looks like", "actually matters". Show it.
- **Vague declaratives.** "The reasons are structural", "The implications are significant", "The stakes are high". Name the specific thing.

### Banned structures

- **Binary contrasts.** "Not X, it's Y", "X isn't the problem, Y is", "The answer isn't X, it's Y", "not just X but Y". State Y directly.
- **Negative listing.** "Not a X. Not a Y. A Z." State Z.
- **Dramatic fragmentation.** "[Noun]. That's it. That's the thing.", "X. And Y. And Z." Use complete sentences.
- **Rhetorical setups.** "What if [reframe]?", "Here's what I mean:", "Think about it:", "And that's okay." Make the point.
- **False agency.** Inanimate things doing human verbs: "the complaint becomes a fix", "the decision emerges", "the data tells us", "the culture shifts". Name the human, or use "you".
- **Narrator-from-a-distance.** "Nobody designed this", "This happens because", "People tend to". Put the reader in the room.
- **Passive voice.** "X was created", "mistakes were made". Name the actor; put them first.
- **Wh- sentence starters.** Restructure; lead with the subject.
- **Rhythm tics.** Three-item lists (use two or one), every paragraph ending punchily, staccato fragmentation, em dashes (remove, always).
- **Lazy extremes.** every, always, never, everyone, nobody. Use specifics.

The exhaustive phrase and structure lists live in stop-slop's `references/phrases.md` and `references/structures.md`; adopt them wholesale.

### Quick checks

Before delivering any prose (titles, slide copy, speaker notes): adverbs killed; passive voice has a named actor; no inanimate thing doing a human verb; no Wh- starters; no "here's what / this / that" throat-clearing; no "not X, it's Y" contrasts; sentence lengths vary; no em dashes; vague declaratives replaced with the specific thing; the reader is in the scene; no meta-joiners.

### Scoring

Rate the deck's written content 1-10 on each dimension: **Directness** (statements, not announcements), **Rhythm** (varied, not metronomic), **Trust** (respects the reader), **Authenticity** (sounds human), **Density** (nothing cuttable). Below 35 out of 50: revise.

---

## How it runs

- **In `narrative`.** Reflex rejection before drafting the story and outline; the slop check on the outline before it is agreed with the user.
- **In `build-deck`.** The slop check on the deck spec before rendering, and on slide copy and speaker notes as they are written.
- **In `slop-check`.** Both layers and the score, run standalone against any outline or finished `.pptx`.

The clean test fixtures must score clear; the sloppy fixtures must trip every planted pattern.
