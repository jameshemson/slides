---
name: slop-check
description: Run an adversarial slop review over a deck spec or a finished .pptx, returning severity-ranked findings.
user-invocable: true
argument-hint: "[path to a .deck.md spec or a .pptx]"
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md).

Read [slop.md](../presentation-craft/reference/slop.md) in full: the two layers, the banned phrases and structures, the emotion line, and the score. This skill runs that detector standalone.

---

$ARGUMENTS

You run an adversarial slop review. The job is to catch generic, AI-flavoured slop in a deck before it ships, and to say where it is and how bad it is. You return findings, not a verdict.

If the user did not name a file, ask for the deck spec or the `.pptx` to review.

## Step 1: Read the deck

The skill takes either form.

**A deck spec (`.deck.md`).** Read the Markdown directly. You see the slide structure, the field text, the speaker notes, and the `Visual:` descriptions.

**A finished `.pptx`.** Read it with `python-pptx`. Run `python3 -c "import pptx"` first; if it fails, tell the user to `pip install python-pptx` (on a managed macOS Python, `pip install --break-system-packages python-pptx` or a virtualenv). Then pull each slide's placeholder text, the layout name, and the speaker notes:

```
python3 -c "
from pptx import Presentation
p = Presentation('deck.pptx')
for i, s in enumerate(p.slides, 1):
    print(f'--- slide {i}: {s.slide_layout.name} ---')
    for ph in s.placeholders:
        print(repr(ph.text))
    if s.has_notes_slide:
        print('notes:', repr(s.notes_slide.notes_text_frame.text))
"
```

## Step 2: Run both layers of the detector

Work through `slop.md` end to end.

**Layer 1, presentation slop.** Check every slide for: the tacked-on strapline, the slide as a document, the slide as a script, bullet soup, title and body restating each other, the deck being about the presenter or the product, facts with no story, unearned hype and ad-copy voice, decoration that does not clarify, register mismatch, leftover scaffolding.

**Layer 2, prose slop.** Check the speaker notes and any prose against the banned phrases and banned structures: throat-clearing openers, emphasis crutches, business jargon, adverbs, filler, binary contrasts, negative listing, dramatic fragmentation, passive voice, em dashes, lazy extremes.

Hold the emotion line. Earned emotion, grounded in something true and concrete, passes. Flag only the unearned kind.

## Step 3: Score

Rate the deck's written content 1 to 10 on each dimension from `slop.md`: Directness, Rhythm, Trust, Authenticity, Density. Report the five numbers and the total out of 50. Below 35, the deck needs a revision pass.

## Step 4: Report findings

Return a list of findings ranked by severity. For each finding:

- **Where.** The slide number and field, or the line of notes.
- **What.** The slop pattern, named from `slop.md`.
- **The quote.** The offending text, so the user sees it.
- **The fix.** What to write instead, concrete.

Rank highest severity first: absolute bans (the tacked-on strapline, leftover scaffolding, unearned emotion) at the top, then the rest.

Do not return a pass-or-fail verdict. A deck with two minor prose tics and a deck with a strapline on every slide are not the same, and one label would hide that. Give the user the ranked findings and the score, and let them decide what to fix.
