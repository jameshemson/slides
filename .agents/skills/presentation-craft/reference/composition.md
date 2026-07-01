# Composition quality: what good looks like

How `build-deck` judges a *composed* slide once it is on-brand. The system lint
(in `lint.py`) guarantees a composed slide is on-system — every fill a token
colour, every size a type-scale step, on the grid, no overlaps, under the element
cap — and it hard-fails the render if not. This layer is the next question:
not "is it on-system?" but "is it *well-composed*?"

These rules are **advisory**. They surface as non-blocking notes in the render
summary; they never fail a build. The recipe in `primitives.py` is built so the
default output already passes them — good by construction, not by correction.

The rules are evidence-cited: each carries a source tag from the deep-research
report (Tufte, Duarte, Reynolds, Gestalt, WCAG, Cowan) reconciled with the
brand's own presentation craft. "Say what good looks like" — don't guess at it.

## The governing meta-rule: advisory, not absolute

Do **not** encode "maximise minimalism / strip everything" as a hard rule.
Controlled work (Bateman, *Useful Junk?*, CHI 2010; Correll & Gleicher) shows
tasteful embellishment does not reduce comprehension and can improve recall
weeks later — extreme minimalism is not always best. So composition quality is
expressed as discrete, advisory checks, never as an unbounded "remove more."
Only the system tier is absolute.

## Three tiers

- **system** (hard, `lint.check`) — on-system or the render fails. Unchanged.
- **quality** / **slop** (advisory, `lint.review`) — the rules below. They warn,
  they never block.
- **doc-only** — judgement a machine should not fake (below). Guidance for the
  author, not a check.

## The advisory rules (`composition.py`)

Each rule reads the placed elements + the brand tokens and warns when a stat row
strays outside the band. Thresholds are advisory bands, not law.

| Rule | Tier | What good looks like (and the fix) | Source |
|------|------|-----------------------------------|--------|
| `hierarchy-ratio` | quality | The number dominates: ~3–4× its label (band 2.5–6×). Too close and the number doesn't read as the hero. *No perceptual study pins the exact ratio — this is an advisory band from the brand's own decks.* | report#3; decks §F |
| `stat-count` | quality | 3–5 figures in a row. More is a table, not a hero row — working memory holds ~3–5 items (Cowan, correcting the folkloric 7±2). | report#4 (Cowan) |
| `contrast` | quality | Legible: number ≥ 3:1 vs the paper (large text); a small label ≥ 4.5:1 (WCAG 2.2 AA). *Assumes the `paper` colour role is the background — true rendered contrast is a later vision-loop check.* | report#9 (WCAG) |
| `value-terseness` | quality | The value is terse (≤ ~5 chars): `56`, `4%`, `$1.2M`. A long number is a sentence, not a hero. | report#3; inknarrates |
| `label-terseness` | quality | The label is ≤ 3 words. | report#3; decks §F |
| `breathing-room` | quality | The row leaves whitespace — it shouldn't fill the content band. White space is pacing; a sparse slide signals importance. | report §E; decks §E |
| `one-accent` | quality | One accent: numbers in the accent colour, labels in ink/muted. Not a rainbow. Grey-push the field, colour the insight. | report#7; decks §D |
| `decoration-present` | slop | No decoration — a strong stat row is the numbers and labels, nothing else. (Guards against the gradient-accented "hero-metric" SaaS cliché.) | impeccable ban; report#2 |
| `emphasis-colour-only` | slop | The number leads by **size**, not colour alone (WCAG 1.4.1 — never rely on colour as the only signal). | report#9; report#8 |

## The advisory rules for the other primitives

The same tiers apply to `card-grid`, `comparison`, `process`, and `timeline`. Each
rule judges only its own block's elements (a stat-row rule never sees the process
boxes stacked below it), so a multi-block slide is reviewed primitive by primitive.
The defaults are good by construction; these warn when a spec strays.

| Rule | Tier | What good looks like | Source |
|------|------|----------------------|--------|
| `card-count` | quality | 3–5 cards. 6+ is a wall; 1 isn't a grid. | report#4 (Cowan); decks "three or five topics / MECE" |
| `card-label-terseness` | quality | Card labels ≤ 3 words, one line of body. | report#3; the lorem-card anti-pattern |
| `card-one-accent` | slop | At most one card leads (accent fill); the rest are siblings, not a rainbow. | report#7 (grey-push, one accent) |
| `comparison-resolves` | slop | The comparison *resolves* — one side is marked the winner (the turn), not left balanced. | decks "order for impact"; end on the turn |
| `comparison-header-terseness` | quality | Headers ≤ 3 words (a one-word verdict). | report#3 |
| `process-count` | quality | 3–5 steps; the signature is three. | report#4 (Cowan); decks "Plan/Create/Deliver" |
| `process-label-terseness` | quality | Step labels ≤ 3 words (a terse verb). | report#3 |
| `timeline-count` | quality | ~3–6 milestones; more is a table on a rail. | report#4 (Cowan) |
| `timeline-emphasis` | slop | One milestone is the turn; an even dotted rule has no hierarchy. | report#7; Visme (hierarchy) |
| `timeline-terseness` | quality | A date + a ≤ 3-word event, not a paragraph. | report#3; Evergreen |
| `tree-count` | quality | ~3–8 nodes; more is a diagram, not a slide. | report#4 (Cowan) |
| `tree-label-terseness` | quality | Node labels ≤ 4 words. | report#3 |
| `tree-one-accent` | slop | At most one node leads (accent); the rest are the grey field. | report#7 |
| `icon-list-count` | quality | ~3–6 rows in an icon list. | report#4 (Cowan) |
| `cycle-count` | quality | ~3–6 stages on a cycle. | report#4 (Cowan) |
| `matrix-one-accent` | slop | At most one quadrant leads (accent); the rest are the grey field. | report#7 |
| `freeform-one-accent` | slop | The one freeform rule: grey-push the field, keep the accent to one or two marks. | report#7 |

The `freeform` block is otherwise deliberately advisory-free: it trades
good-by-construction for freedom, so its composition is the author's judgement.
The hard lint still holds (on-token, on-grid, no overlap, under the cap) — that is
the guardrail that makes the freedom safe.

The full evidence base — per-primitive layout patterns, James's own vocabulary, and
the design-system principles (hierarchy, type scale, imagery, colour) — is in
[design-research.md](design-research.md).

## Doc-only: judgement, not a check

These separate a strong stat row from the cliché more than any geometry can, but
they are authored judgement — the generator must not pretend to test them:

- **Concreteness beats magnitude.** A hero number must be *imaginable*, not just
  big. "5% of profits" is inert; "enough to…" lands. There is no mechanical test
  for this (research open question); it is the single biggest cliché
  differentiator. (report#2; Reynolds/Heath; decks §F)
- **Story before stat.** The number is a climactic beat (Duarte's S.T.A.R.
  "shocking statistic"), not an opener. Tell the story, then land the fact.
- **It earns its place.** If the figure doesn't move the argument, cut it.
- **Sequence is a design decision.** The same facts reordered motivate or
  deflate — end on the turn you want carried out the door.
- **Assertion titles.** Title the finding ("Revenue surged 23%"), not the axis
  ("Revenue"). (Alley assertion-evidence.)
- **You are not the hero.** The audience is; a slide centring the
  presenter/company is structurally wrong. (decks §G)

## The authoring anti-goal

Before composing a stat slide, answer one question:

> **What does this slide move the audience FROM → TO — and is the number
> concrete (imaginable), not just big?**

If you can't name the move, the slide hasn't earned its place yet.

## Myths not encoded

The research adversarial pass flagged these as folklore — they are deliberately
absent: the 6×6 / 7×7 bullet rule; Dale's Cone ("remember 10% of what we read");
Mehrabian 7-38-55; "visuals processed 60,000× faster"; raw Miller 7±2 (use
Cowan's ~3–5 instead); Kawasaki's 10-20-30 as a constant.
