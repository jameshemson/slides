# Design research: the evidence base

Why the composed primitives look the way they do. This is the committed record of
the research behind `build-deck`'s compositions, so the reasoning survives the
work. It reconciles three sources: the user's own decks (*Powerful Presenting*,
*This Episode of Bluey is Called*, *Telling Sticky Stories*, *Storytelling*,
*Thinking / Communicating visually*), the Visme *Non-Designer's Guide to Creating
Memorable Visual Slides*, and the design canon (Tufte, Duarte, Reynolds, the
Heath brothers, Gestalt, Cowan, WCAG/APCA), hardened with a web pass.

Citation shorthand: **PP s\<n\>** = *Powerful Presenting* slide; **Visme p\<n\>** =
the guide's page; **Abela / Evergreen** = the two chart-choosers; canon authors by
name. The rules that this feeds live in [composition.py](../../build-deck/scripts/composition.py)
and are summarised in [composition.md](composition.md); the craft is in [slides.md](slides.md).

## The governing stance

Composition quality is **advisory, not absolute**. Controlled work (Bateman,
*Useful Junk?*, CHI 2010) shows tasteful embellishment does not reduce
comprehension and can aid recall — so "strip everything to minimalism" is not a
law. Only the on-system tier (token colours, type scale, grid, no overlap) is
hard. Everything below is a band, not a gate.

## The design system

- **Hierarchy is size.** The most important element is the largest; scale encodes
  rank. Set the reading order by type size, then weight. (Visme p91–92; PP s112/s114)
- **Contrast has five levers — colour is one.** Size, Shape, Shade, Colour,
  Proximity. Lead by size, never by colour alone. (PP s101; WCAG 1.4.1)
- **Type scale ≈ 4:1, floor 30pt.** The guide's ladder: body/label 30, sub-head
  48, title 72, hero 120pt. A hero number dominates its label ~3–4× — a bigger
  jump than a single modular step (1.25/1.333/1.5), on purpose. (Visme p23; modular
  scale, alistapart)
- **Readable from the back.** Size to the furthest viewer: ~1in cap-height per 10ft,
  or text subtending ≥10 arc-minutes (≥15–20 safe). Projected body rarely below
  ~24pt; heading ~30pt. Read-on-screen decks may go to ~18pt. (USSC signage; Extron;
  accessibility consensus)
- **Colour: 3–4 total, grey-push the field, colour the insight.** Push everything
  to a neutral, then spend one accent on what carries the point. 60-30-10
  (dominant/secondary/accent) is a proportioning heuristic, not a law. Red = danger
  (Western). For several unavoidable series, use a colour-blind-safe set
  (Okabe–Ito). (Visme p66/p80–82; PP s125/s128/s129; Wong, *Nature Methods*)
- **Imagery: full-bleed and real.** Full-screen photos, cropped to the subject,
  one per slide; never boxed clip-art or stock cliché. Seat text in the image's
  quiet region, or on a scrim (30–50% overlay / floor-fade / blur) that clears the
  same contrast bar tested against the worst-case patch. (Visme p39–54; NN/g
  text-over-images)
- **Data: one point per chart.** Maximise data-ink — drop gridlines, borders,
  chartjunk. Direct-label over legends. Emphasise the one series that carries the
  point, grey the rest. Choose the chart from the *relationship* (Abela's four;
  FT Visual Vocabulary's nine), not the data type. Title the finding, not the axis.
  (Visme p79–83; Tufte; Abela; Evergreen; FT)
- **Grouping is Gestalt.** A shared container (card, panel, hairline) binds its
  contents — *Common Region* — which is the citeable basis for card grids and
  two-panel comparisons. Alignment and proximity group without borders; whitespace
  separates. (Visme p102–107; NN/g common-region)

## The primitives — a palette, not a taxonomy

These are the shapes the user's decks reach for most, sized to working memory
(Cowan ~3–5, not Miller 7±2). Treat them as a starting palette, never a closed
menu: when an idea wants a shape none of them fit, compose it *freeform* rather
than force-fit it into the nearest one. The house rule governs — the slide takes
whatever form its one idea needs ([slides.md](slides.md)). Forcing every idea into
five shapes is its own slop; it just swaps bullet-slop for box-slop.

- **card-grid** — 3–5 sibling ideas of equal type, or one paragraph detonated into
  labelled chunks ("What / Where / When / Who"). A row of equal panels, bold
  1–3-word label + at most one line of body. One card may lead; the rest are
  siblings, not a rainbow. *Cliché to avoid:* the evenly-weighted icon+title+lorem
  grid where nothing leads. (PP s75 "cluster by message: three or five topics /
  MECE"; s119–139; Cowan)
- **comparison** — two panels set side by side so a difference is unmissable. Same
  structure both sides, a one-word verdict header each; the design **tilts to the
  winner** ("Order for impact: Demotivating → Motivating" — the same facts
  reordered). A comparison must *resolve, not balance*. *Cliché to avoid:* symmetric
  pros-and-cons with no verdict. (PP s79–82; Bluey s45–48)
- **process** — 3 (up to 5) numbered steps left to right, each a box with a big
  accent number and a terse verb label, joined by an arrow. This is his real
  "Plan → Create → Deliver" pattern. *Cliché to avoid:* the SmartArt chevron ribbon
  stuffed with jargon. (PP s14/16/39; Bluey s44; Cowan)
- **timeline** — dated milestones as dots on a rail, Start …•…•…•… End. Node = date
  + a ≤3-word event; one milestone is the turn (emphasise it, grey the rest).
  *Cliché to avoid:* the even dotted rule where every node is a date + a paragraph
  and nothing leads. Roadmap-timeline geometry leans on Evergreen/Visme (thinner in
  the storytelling decks). (Evergreen; Visme p84; Cowan)
- **freeform** — the escape hatch for everything else: a matrix, a quadrant, a
  node graph, an annotated layout. Freedom in the arrangement, the *same* hard
  guardrails as every block (on-token, on-grid, no overlap, under the cap); the
  lint proves it's on-brand, not that it's well composed — that is the author's
  judgement, nudged only by grey-push (keep the accent to one or two marks). Reach
  for it instead of bending an idea to fit the named shapes.

## Speak his language

Use his words in prompts and copy: **Plan · Create · Deliver**; **"you are not the
hero"**; the **big idea / sticky idea** (Heath SUCCESs); **Think · Feel · Do**;
**cluster by message / three or five topics / MECE / kill your darlings**;
**Beginning · Middle · End**; **"Can you contrast?" / "Order for impact"**;
design pillars **Grid · Colour · Hierarchy · Layout**; contrast levers **Size ·
Shape · Shade · Colour · Proximity**; **signpost** and **"So what? / What next?"**.
(PP s6/s19/s42/s75/s97/s101; Bluey s26)

## Myths kept out

Deliberately absent — folklore the research flagged, some of which the user's own
decks repeat:

- **Mehrabian 7-38-55** ("words are 7%"). Applies only to conflicting
  feeling-cues; not a law of communication. *His decks teach it (PP s153–158) — use
  the Music/Dance/Lyrics framing if helpful, never the numbers.*
- **Dale's Cone** ("remember 10% of what we read"). The cone carried no numbers;
  they were invented later.
- **"Images processed 60,000× faster," "90% visual," "43% more persuasive."**
  Untraceable marketing stats. Picture-superiority is real but modest.
- **Raw Miller 7±2.** Use Cowan ~3–5.
- **10-20-30 and 6×6 / 7×7 bullet rules as absolutes.** Keep the intent (few
  slides, big type, one idea) — the 30pt ≈ the accessibility floor — drop the
  numbers-as-law. 60-30-10 and rule-of-thirds are heuristics, not gates.
- **The "Z-pattern" as eye-tracking evidence.** The F-pattern is the finding; Z is
  a design convention. The house craft's "top-left hottest, clear path" stands.

## Judgement a machine should not fake

The generator must not pretend to test these; they are for the author:

- **Concreteness beats magnitude.** A hero number must be imaginable, not just big.
  The single biggest cliché differentiator. (Reynolds; Heath; report open question)
- **Story before stat.** The number is a climactic beat, not an opener.
- **It earns its place.** If a figure, card, or step doesn't move the argument, cut it.
- **Sequence is a design decision.** The same facts reordered motivate or deflate —
  end on the turn you want carried out the door.

## Sources

The user's decks in `Work Stuff/` (Powerful Presenting, This Episode of Bluey is
Called, Telling Sticky Stories, Storytelling, Thinking/Communicating visually) and
the Visme *Non-Designer's Guide* (PDF); the two Data-Viz chart-choosers (Abela;
Lyons & Evergreen). Canon: Tufte *Visual Display*; Duarte *slide:ology*; Reynolds
*Presentation Zen*; Heath *Made to Stick*; Gestalt (NN/g); Cowan (2001) working
memory; WCAG 2.2 AA and APCA (WCAG 3 candidate, for dark backgrounds); Bateman
*Useful Junk?* (CHI 2010); FT Visual Vocabulary; Okabe–Ito / Wong (*Nature
Methods*). Full web citations are captured in the build's research notes.
