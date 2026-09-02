/*
 * example.build.cjs - a worked example of composing a deck as code.
 *
 * It builds the six-slide sample deck (tests/fixtures/sample-deck.md) under one
 * brand's design tokens: a dark title with a half-bleed accent panel and a drawn
 * clock; a section slide that draws the hour; the six-hour cost made concrete as
 * six blocks; two resolved columns instead of four bullets; a comparison that
 * resolves, grey field against accent winner; a dark quote to close. Read it as
 * the shape of the contract, not as a layout to copy - every deck gets its own
 * composition.
 *
 * Run it:
 *   node example.build.cjs --tokens .slides/tokens.cjs --out sample.pptx
 *
 * The rules a per-deck build script follows:
 *   - Content is data. Every string that reaches a slide or a notes field lives
 *     in the C block below; no slide text is written inline anywhere else.
 *   - Only tokens. Every size comes from T.scale, every colour from T.colours,
 *     every font from T.fonts. A grey is a token colour plus transparency, never
 *     a literal grey, and text is never translucent.
 *   - Tokens in, deck out. The script loads the tokens module and reaches
 *     pptxgenjs through it, and touches nothing else - no file system, no
 *     network, no shelling out. It runs under Node's permission model with read
 *     access to the project and write access to the deck's directory only.
 *   - Text stays inside the margins, clear of other text boxes, and wholly on
 *     one ground so contrast can be measured; fill panels may bleed off the edge.
 *   - Marks carry labels: every drawn dot, line and block has words beside it.
 *   - Stamps: each text box's objectName tells the round trip which spec field it
 *     came from - one slides-lead per slide, slides-field for the other fields,
 *     plain deco- names for everything drawn.
 *   - Notes travel verbatim, so the deck can be read back into its spec.
 */

const argv = process.argv.slice(2);

function arg(name) {
  const i = argv.indexOf(name);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : null;
}

const tokensPath = arg("--tokens");
const outPath = arg("--out");

if (!tokensPath || !outPath) {
  console.error("usage: node example.build.cjs --tokens <tokens.cjs> --out <deck.pptx>");
  process.exit(2);
}

const T = require(require("path").resolve(tokensPath));
const pptxgen = T.loadPptxgen();

// Every word on every slide, in one place.
const C = JSON.parse('{"s1":{"title":"From status meeting to written update","subtitle":"A proposal for a two-week trial","clock":"60 min","notes":"Open by naming the trade the team lead is weighing: time back against the risk of drift. The deck answers both."},"s2":{"eyebrow":"01","title":"Where the hour goes","hour":"60 min","notes":"A short divider. Pause here so the room resets before the cost lands."},"s3":{"statement":"The weekly status meeting costs the team six hours every week.","count":"Six people. One hour. Every week.","block":"1 h","total":"= 6 h","notes":"Six people, one hour. Say the number plainly and let it sit before moving on."},"s4":{"title":"What the meeting does, and does not, do well","keeps":"Keeps","costs":"Costs","keepsOne":"It surfaces blockers fast, while everyone is in the room.","keepsTwo":"It gives quieter teammates a fixed moment to be heard.","costsOne":"It spends the same hour whether the week was eventful or quiet.","costsTwo":"It leaves no record anyone can search the following month.","notes":"Concede the real strengths first. The proposal keeps what works and fixes what does not."},"s5":{"title":"Two ways to spend the same hour","leftLabel":"The meeting","rightLabel":"The written update","left":"The meeting. Everyone stops at the same time. Updates are spoken once and gone. The slowest item sets the pace for all six people.","right":"The written update. Each person writes for ten minutes when it suits them. Blockers are flagged in the document and answered in a thread. The record stays searchable.","notes":"This is the heart of the argument. Walk the room across the comparison slowly."},"s6":{"mark":"“","quote":"I skip half of what I say in standup because it does not apply to most of the room.","attribution":"A teammate, in last month\'s retro","notes":"A real voice from inside the team carries more weight here than another bullet would."}}');

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";

const W = T.slide.w;
const H = T.slide.h;
const MX = T.margins.x;
const MT = T.margins.top;
const CONTENT_W = W - 2 * MX;
const ROUNDED = T.shape.corner === "rounded";

// Fresh options object per call, margin 0 so text aligns with the shapes.
function text(slide, body, opts) {
  slide.addText(body, Object.assign({ margin: 0 }, opts));
}

function mark(slide, kind, opts) {
  slide.addShape(kind, Object.assign({}, opts));
}

// A field or block, corner radius only when the brand's shape language is round.
function panel(slide, opts) {
  const o = Object.assign({}, opts);
  if (ROUNDED) {
    o.rectRadius = 0.12;
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, o);
  } else {
    slide.addShape(pres.shapes.RECTANGLE, o);
  }
}

// A grey that is still on-brand: a token colour, thinned.
function tint(colour, transparency) {
  return { color: colour, transparency: transparency };
}

// ---------------------------------------------------------------- 1. title --
// Dark ground, the accent panel bleeding off the right edge, the hour drawn.
{
  const s = pres.addSlide();
  s.background = { color: T.colours.ink };

  const px = 9.2;
  const pw = W - px;
  const cx = px + pw / 2; // clock centre
  const cy = 3.5;
  // 1.35, not 1.5: the ring is a mark, and marks stay inside the margins unless
  // they bleed to an edge (the panel does; the ring must not cross the margin).
  const r = 1.35;

  mark(s, pres.shapes.RECTANGLE, {
    x: px, y: 0, w: pw, h: H,
    fill: { color: T.colours.accent }, line: { color: T.colours.accent },
    objectName: "deco-accent-panel",
  });
  mark(s, pres.shapes.OVAL, {
    x: cx - r, y: cy - r, w: 2 * r, h: 2 * r,
    fill: { color: T.colours.accent }, line: { color: T.colours.paper, width: 5 },
    objectName: "deco-clock-ring",
  });
  mark(s, pres.shapes.LINE, {
    x: cx, y: cy - 1.1, w: 0, h: 1.1,
    line: { color: T.colours.paper, width: 5 },
    objectName: "deco-clock-hand-hour",
  });
  mark(s, pres.shapes.LINE, {
    x: cx, y: cy, w: 0.85, h: 0,
    line: { color: T.colours.paper, width: 5 },
    objectName: "deco-clock-hand-minute",
  });
  mark(s, pres.shapes.OVAL, {
    x: cx - 0.09, y: cy - 0.09, w: 0.18, h: 0.18,
    fill: { color: T.colours.paper }, line: { color: T.colours.paper },
    objectName: "deco-clock-pin",
  });
  text(s, C.s1.clock, {
    x: cx - 1.0, y: cy + 0.22, w: 2.0, h: 0.62,
    fontFace: T.fonts.heading, fontSize: T.scale.body, color: T.colours.paper,
    align: "center", objectName: "deco-clock-label",
  });

  text(s, C.s1.title, {
    x: MX, y: 1.95, w: 8.1, h: 2.95,
    fontFace: T.fonts.heading, fontSize: T.scale.title, bold: true,
    color: T.colours.paper, valign: "bottom", lineSpacingMultiple: 0.95,
    objectName: "slides-lead:Title",
  });
  text(s, C.s1.subtitle, {
    x: MX, y: 5.05, w: 8.1, h: 0.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, color: T.colours.accent,
    objectName: "slides-field:Subtitle",
  });

  s.addNotes(C.s1.notes);
}

// -------------------------------------------------------------- 2. section --
// The hour as a ring with the meeting eaten out of it.
{
  const s = pres.addSlide();
  s.background = { color: T.colours.paper };

  const dx = 7.55;
  const dy = 1.15;
  const d = 5.0;

  mark(s, pres.shapes.OVAL, {
    x: dx, y: dy, w: d, h: d,
    fill: { color: T.colours.paper },
    line: { color: T.colours.ink, width: 18, transparency: 88 },
    objectName: "deco-hour-ring",
  });
  mark(s, pres.shapes.BLOCK_ARC, {
    x: dx, y: dy, w: d, h: d,
    fill: { color: T.colours.accent }, line: { color: T.colours.accent, width: 0 },
    angleRange: [270, 180],
    objectName: "deco-hour-arc",
  });
  // body size, not h1: the label has to sit inside the ring's hole in any font
  text(s, C.s2.hour, {
    x: dx + d / 2 - 1.0, y: dy + d / 2 - 0.35, w: 2.0, h: 0.7,
    fontFace: T.fonts.heading, fontSize: T.scale.body, bold: true,
    color: T.colours.ink, align: "center", valign: "middle",
    objectName: "deco-hour-label",
  });

  text(s, C.s2.eyebrow, {
    x: MX, y: 1.6, w: 2.0, h: 0.55,
    fontFace: T.fonts.heading, fontSize: T.scale.body, bold: true,
    color: T.colours.accent, objectName: "deco-section-number",
  });
  text(s, C.s2.title, {
    x: MX, y: 2.3, w: 6.4, h: 2.6,
    fontFace: T.fonts.heading, fontSize: T.scale.title, bold: true,
    color: T.colours.ink, valign: "top", lineSpacingMultiple: 0.95,
    objectName: "slides-lead:Title",
  });

  s.addNotes(C.s2.notes);
}

// ------------------------------------------------------------ 3. statement --
// Six people, one hour each: the number made countable.
{
  const s = pres.addSlide();
  s.background = { color: T.colours.paper };

  text(s, C.s3.statement, {
    x: MX, y: 1.45, w: 6.2, h: 2.7,
    fontFace: T.fonts.heading, fontSize: T.scale.h1, bold: true,
    color: T.colours.ink, valign: "top", lineSpacingMultiple: 1.05,
    objectName: "slides-field:Statement",
  });
  text(s, C.s3.count, {
    x: MX, y: 4.35, w: 6.2, h: 0.5,
    fontFace: T.fonts.body, fontSize: T.scale.caption, color: T.colours.ink,
    objectName: "deco-count-note",
  });

  const gx = 7.45;
  const gy = 1.35;
  const cw = 1.58;
  const gap = 0.2;
  for (let i = 0; i < 6; i++) {
    const bx = gx + (i % 3) * (cw + gap);
    const by = gy + Math.floor(i / 3) * (cw + gap);
    panel(s, {
      x: bx, y: by, w: cw, h: cw,
      fill: { color: T.colours.accent }, line: { color: T.colours.accent },
      objectName: "deco-hour-block-" + (i + 1),
    });
    text(s, C.s3.block, {
      x: bx + 0.05, y: by + 0.05, w: cw - 0.1, h: cw - 0.1,
      fontFace: T.fonts.heading, fontSize: T.scale.body, bold: true,
      color: T.colours.paper, align: "center", valign: "middle",
      objectName: "deco-hour-block-label-" + (i + 1),
    });
  }

  text(s, C.s3.total, {
    x: gx, y: 4.95, w: 3 * cw + 2 * gap, h: 1.75,
    fontFace: T.fonts.heading, fontSize: T.scale.display, bold: true,
    color: T.colours.accent, valign: "middle", objectName: "slides-lead",
  });

  s.addNotes(C.s3.notes);
}

// -------------------------------------------------------- 4. title-content --
// The four bullets resolved into what the meeting keeps and what it costs.
{
  const s = pres.addSlide();
  s.background = { color: T.colours.paper };

  const colGap = 0.6;
  const colW = (CONTENT_W - colGap) / 2;
  const rx = MX + colW + colGap;
  const pad = 0.42;
  const py = 2.55;
  const ph = 3.7;

  // a measure short of the full column, so the title breaks where it reads best
  text(s, C.s4.title, {
    x: MX, y: MT + 0.05, w: 11.4, h: 1.5,
    fontFace: T.fonts.heading, fontSize: T.scale.h1, bold: true,
    color: T.colours.ink, valign: "top", objectName: "slides-lead:Title",
  });

  panel(s, {
    x: MX, y: py, w: colW, h: ph,
    fill: tint(T.colours.ink, 94), line: tint(T.colours.ink, 100),
    objectName: "deco-panel-keeps",
  });
  text(s, C.s4.keeps, {
    x: MX + pad, y: py + 0.3, w: colW - 2 * pad, h: 0.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, bold: true,
    color: T.colours.accent, objectName: "deco-panel-label-keeps",
  });
  text(s, [
    { text: C.s4.keepsOne, options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: C.s4.keepsTwo, options: {} },
  ], {
    x: MX + pad, y: py + 1.05, w: colW - 2 * pad, h: 2.3,
    fontFace: T.fonts.body, fontSize: T.scale.body, color: T.colours.ink,
    valign: "top", objectName: "slides-field:Body",
  });

  panel(s, {
    x: rx, y: py, w: colW, h: ph,
    fill: tint(T.colours.ink, 94), line: tint(T.colours.ink, 100),
    objectName: "deco-panel-costs",
  });
  text(s, C.s4.costs, {
    x: rx + pad, y: py + 0.3, w: colW - 2 * pad, h: 0.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, bold: true,
    color: T.colours.ink, objectName: "deco-panel-label-costs",
  });
  text(s, [
    { text: C.s4.costsOne, options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: C.s4.costsTwo, options: {} },
  ], {
    x: rx + pad, y: py + 1.05, w: colW - 2 * pad, h: 2.3,
    fontFace: T.fonts.body, fontSize: T.scale.body, color: T.colours.ink,
    valign: "top", objectName: "slides-field:Body",
  });

  s.addNotes(C.s4.notes);
}

// ----------------------------------------------------------- 5. two-column --
// Six people stopped at once, against six people writing on their own time.
{
  const s = pres.addSlide();
  s.background = { color: T.colours.paper };

  const colGap = 0.6;
  const colW = (CONTENT_W - colGap) / 2;
  const rx = MX + colW + colGap;
  const pad = 0.42;
  const py = 1.85;
  const ph = 4.85;
  const dotStep = 0.72;
  const dotD = 0.5;
  const stagger = [0, 0.3, 0.08, 0.4, 0.16, 0.34];

  text(s, C.s5.title, {
    x: MX, y: MT + 0.05, w: 10.6, h: 1.0,
    fontFace: T.fonts.heading, fontSize: T.scale.h1, bold: true,
    color: T.colours.ink, valign: "top", objectName: "slides-lead:Title",
  });

  // the meeting: a grey field, six dots stopped at the same moment
  panel(s, {
    x: MX, y: py, w: colW, h: ph,
    fill: tint(T.colours.ink, 94), line: tint(T.colours.ink, 100),
    objectName: "deco-panel-meeting",
  });
  text(s, C.s5.leftLabel, {
    x: MX + pad, y: 2.1, w: colW - 2 * pad, h: 0.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, bold: true,
    color: T.colours.ink, objectName: "deco-panel-label-meeting",
  });
  for (let i = 0; i < 6; i++) {
    mark(s, pres.shapes.OVAL, {
      x: MX + 0.45 + i * dotStep, y: 2.85, w: dotD, h: dotD,
      fill: tint(T.colours.ink, 60), line: tint(T.colours.ink, 100),
      objectName: "deco-dot-meeting-" + (i + 1),
    });
  }
  mark(s, pres.shapes.LINE, {
    x: MX + 0.45, y: 3.7, w: 5 * dotStep + dotD, h: 0,
    line: { color: T.colours.ink, width: 2, transparency: 60 },
    objectName: "deco-rule-meeting",
  });
  text(s, C.s5.left, {
    x: MX + pad, y: 3.95, w: colW - 2 * pad, h: 2.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, color: T.colours.ink,
    valign: "top", objectName: "slides-field:Left",
  });

  // the written update: the accent field, six marks on their own time
  panel(s, {
    x: rx, y: py, w: colW, h: ph,
    fill: { color: T.colours.accent }, line: { color: T.colours.accent },
    objectName: "deco-panel-written",
  });
  text(s, C.s5.rightLabel, {
    x: rx + pad, y: 2.1, w: colW - 2 * pad, h: 0.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, bold: true,
    color: T.colours.paper, objectName: "deco-panel-label-written",
  });
  for (let i = 0; i < 6; i++) {
    mark(s, pres.shapes.OVAL, {
      x: rx + 0.45 + i * dotStep, y: 2.85 + stagger[i], w: dotD, h: dotD,
      fill: { color: T.colours.paper }, line: { color: T.colours.paper },
      objectName: "deco-dot-written-" + (i + 1),
    });
  }
  mark(s, pres.shapes.LINE, {
    x: rx + 0.45, y: 3.7, w: 5 * dotStep + dotD, h: 0,
    line: { color: T.colours.paper, width: 2, transparency: 50 },
    objectName: "deco-rule-written",
  });
  text(s, C.s5.right, {
    x: rx + pad, y: 3.95, w: colW - 2 * pad, h: 2.6,
    fontFace: T.fonts.body, fontSize: T.scale.body, color: T.colours.paper,
    valign: "top", objectName: "slides-field:Right",
  });

  s.addNotes(C.s5.notes);
}

// ---------------------------------------------------------------- 6. quote --
// Dark close, one voice from inside the team.
{
  const s = pres.addSlide();
  s.background = { color: T.colours.ink };

  text(s, C.s6.mark, {
    x: MX, y: 1.5, w: 2.2, h: 1.4,
    fontFace: T.fonts.heading, fontSize: T.scale.display, bold: true,
    color: T.colours.accent, valign: "top", objectName: "slides-ghost",
  });
  text(s, C.s6.quote, {
    x: MX, y: 3.0, w: 10.2, h: 2.5,
    fontFace: T.fonts.heading, fontSize: T.scale.h1, color: T.colours.paper,
    valign: "top", lineSpacingMultiple: 1.05, objectName: "slides-lead:Quote",
  });
  text(s, C.s6.attribution, {
    x: MX, y: 5.75, w: 10.2, h: 0.5,
    fontFace: T.fonts.body, fontSize: T.scale.caption, color: T.colours.accent,
    objectName: "slides-field:Attribution",
  });

  s.addNotes(C.s6.notes);
}

pres
  .writeFile({ fileName: outPath })
  .then(() => console.log("wrote " + outPath))
  .catch((err) => {
    console.error(err.message);
    process.exit(1);
  });
