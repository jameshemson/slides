# Data, charts, and diagrams

How a slide turns data or an idea into a picture. The craft is in the choice: the
right chart for the relationship, the right diagram for the idea.

## Message first, chart second

Decide what the data has to say before choosing how to draw it. Name the one point
the chart must land. Then pick the form that says it. A chart chosen before its
message has no job, and it shows.

## Choose the chart by the relationship

A chart's type follows from the relationship in the data. The Graphic Continuum
(Schwabish and Ribecca) sorts chart types into six families, one per relationship.
Identify the relationship, then choose within its family.

- **Distribution.** How values spread across a range. The data is one variable and
  the question is its shape, its centre, and its outliers.
- **Time.** How a value moves over a period. The question is the trend, the
  direction, the change from start to end.
- **Comparing categories.** How separate items rank against each other. The data is
  discrete groups and the question is which is larger.
- **Geospatial.** How a value varies by place. The data is tied to location and the
  question is the pattern across a map.
- **Part-to-whole.** How the pieces of one total divide up. The question is the
  share each part holds of the whole.
- **Relationship.** How two or more variables move together. The question is
  correlation, the link between one measure and another.

This taxonomy is for choosing the chart. Encoding the relationship is the craft. The
specific chart within a family is a secondary choice the user makes in the tool.

## Make the point stand out

A chart is built to land one point, so build the rest of it to step back.

- Colour the insight. Mute everything else to grey.
- Keep the palette to two or three colours.
- Drop gridlines and borders. They add ink and carry nothing.
- Label directly on the data. A legend makes the eye travel back and forth; a direct
  label does not.

A chart loaded with decoration buries its own point. Strip it to what carries the
message.

## Diagrams are first-class

When an idea is a process, a structure, a relationship, or a journey, a diagram
carries it better than a paragraph or a list. A flow, a cycle, a hierarchy, a set of
steps, a layered model, a before-and-after: each shows the shape of an idea.

A concept diagram is a distinct treatment from a data chart, and a slide may pair
text with a strong diagram or infographic. Three rules:

- The diagram's shape mirrors the idea's shape.
- It holds one concept, not several.
- It gives the eye a single clear path to follow.

## A diagram must simplify, not decorate

A diagram earns its place only when the idea is clearer with it than without it. A
diagram that adds complexity, that uses boxes and arrows for their own sake, or that
needs a key to decode has failed. A diagram that obscures is slop. A diagram that
makes the idea click is craft.

## How the visual reaches the deck

The renderer draws three chart families directly: bar and column (comparing
categories), and line (change over time). A slide carries them as a structured
`Chart:` block in the deck spec; `build-deck` renders an on-brand PNG with
matplotlib — direct labels, no legend, stripped axes, the insight in the brand
accent and the rest muted — and places it below the slide's one-line `Body`. The
`Chart:` format is in [deck-spec.md](deck-spec.md).

Everything else still travels as a `Visual:` field: a plain-language description
of what belongs there and why. The other chart families (scatter for
relationship, a histogram for distribution, a map for geospatial), concept
diagrams, and photographs are recorded in the speaker notes, prefixed
`VISUAL TO ADD:`, for a person to place in PowerPoint. If matplotlib is not
installed, a `Chart:` slide degrades to the same note, so the deck still builds.

So for the three drawn families the skill's job is to pick the right one, name
the point, and mark the insight to emphasise. For the rest it is to choose the
right form and describe it precisely. Either way the choice is the craft this
file teaches.
