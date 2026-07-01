---
name: teach-slides
description: Capture a user's brand once (template, fonts, colours, voice, audience) into a project .slides/ directory the other slides skills read.
user-invocable: true
argument-hint: "[path to a .pptx/.potx template, optional]"
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol. `teach-slides` is the skill that protocol routes to, so here you do the gathering rather than the check.

Read [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the `brand.json` shape you will write.

---

$ARGUMENTS

You capture the user's brand once. Every other slides skill reads what you write, so a deck comes out on-brand instead of generic. The brand lives in a `.slides/` directory at the project root: `context.md`, `brand.json`, `template.pptx`.

For a one-step start, `../build-deck/scripts/init_brand.py <template> --template-ref template.pptx` writes a complete `brand.json` (fonts, colours, and a proposed layout map) straight from a template or deck — this is the fast path build-deck and narrative offer. This skill is the fuller capture: it also gathers voice, audience, logo, and lets the user hand-check the layout map. Run it when the user wants that depth, or to refine what `init_brand.py` proposed.

If `.slides/` already exists, tell the user what it holds and ask whether to refresh it or keep it. Do not overwrite without a yes.

## Step 1: Check the toolchain

The renderer needs Python. Run `python3 --version` and `python3 -c "import pptx"`.

If `python3` is missing, tell the user to install Python 3.9 or newer. If the `import pptx` line fails, give them the remedy:

```
pip install python-pptx
```

On macOS with a managed Python, that command can refuse. Tell the user they can run `pip install --break-system-packages python-pptx`, or make a virtualenv (`python3 -m venv .venv && source .venv/bin/activate && pip install python-pptx`). Wait for the toolchain to work before going on. The interview can run in parallel, but Step 4 needs a working `inspect_template.py`.

## Step 2: Interview the user

Gather the brand. You need: a template source, heading and body fonts, brand colours as hex, a logo, the usual audience, the voice, and the presenting context.

<!-- claude-only -->
Use the AskUserQuestion tool to ask these in small batches so the user picks rather than types. Offer concrete options and an "other" path.
<!-- /claude-only -->

Ask the user these questions and wait for the answers before moving on:

- **Template source.** Three paths, covered in Step 3.
- **Fonts.** The heading typeface and the body typeface. If the user is supplying a template or deck (paths a/b), do not ask blank: Step 3 reads the fonts from the file and you confirm them here. Only ask outright for the starter path (c).
- **Colours.** The brand colours as hex (`#1A1A2E`), each with a name (`ink`, `accent`). Same as fonts: for a supplied template or deck, Step 3 reads the palette from the file and you confirm or adjust it rather than asking the user to type every hex.
- **Logo.** Where the logo file sits, if there is one.
- **Audience.** Who the user usually presents to: their role, what they know, what they walk in wanting.
- **Voice.** How the user's decks should sound: plain and direct, warm, formal. Ask for one deck they think sounds right.
- **Context.** Where these decks get shown: a boardroom, a sales call, a conference stage, a doc sent round.

Push back on vague answers. "Professional" is not a voice. Ask for a real example.

## Step 3: Settle the template

A template carries the masters and layouts a deck is built from. Offer three paths and let the user choose.

**(a) Ingest an existing template.** The user has a `.pptx` or `.potx` brand template. Take its path. This is the best case.

**(b) Reuse an existing deck.** The user has a finished deck whose look they like. A deck carries masters and layouts the same way a template does, so a real `.pptx` deck works as a template. `render.py` strips the deck's own slides and keeps only its layouts.

**(c) Generate a starter.** The user has neither. Fall back to `make_template.py`. Run it with the brand fonts and colours from Step 2:

```
python3 ../build-deck/scripts/make_template.py --out .slides/template.pptx \
    --colours '#1A1A2E,#E94560' --heading-font Georgia --body-font Verdana
```

It writes an 11-layout themed starter. Layouts 0/1/2/3/5 come role-named `title`, `title-content`, `section`, `two-column`, `statement`. Tell the user this is a starting point they can open and refine in PowerPoint.

Copy the chosen file (a or b) to `.slides/template.pptx`. For path (c) the script already wrote it there.

For paths (a) and (b), read the brand straight out of the file instead of making the user type it. Run `extract_brand.py` on the copied template:

```
python3 ../build-deck/scripts/extract_brand.py .slides/template.pptx
```

It prints JSON `{template, fonts:{heading,body}, colours:{name:#hex}, layouts:[...], tokens:{type_scale, colour_roles}}` — the theme's real heading/body fonts and its palette (accent1 as `accent`, then `accent2`..`accent6`, plus `ink` and `paper`), the layouts for Step 4, and a starting design-token block (the composed role reads it; the type scale is derived from the master's own sizes). Show the user what you read and let them **confirm or adjust** it: rename a colour, drop one they do not use, add a `muted` or `spend` the theme lacks. Use the confirmed values as the `fonts` and `colours` you write in Step 5. Because `extract_brand.py` already returns the layouts, paths (a)/(b) can skip the separate `inspect_template.py` call in Step 4 and map roles from this output. Path (c)'s starter was themed from the Step 2 answers, so it needs no extraction.

## Step 4: Map the layouts

For paths (a)/(b) you already have the layouts from the Step 3 `extract_brand.py` output — use those. Only for path (c) run `inspect_template.py` on the chosen template:

```
python3 ../build-deck/scripts/inspect_template.py .slides/template.pptx
```

It prints JSON: `{template, layouts:[{index,name,placeholders:[{idx,type}]}]}`. Show the user the layouts you found: index, name, and placeholder count for each.

Map the six semantic roles to layout indices:

| Role | Wants | Placeholders needed |
|------|-------|---------------------|
| `title` | the opening slide | 2 to 3 |
| `title-content` | a heading and its content | 2 to 3 |
| `two-column` | a comparison or pairing | 2 to 3 |
| `quote` | a quotation with room | 2 to 3 |
| `section` | a divider | 1 |
| `statement` | one hero idea | 1 |

A role assigned to a layout with fewer content placeholders than the role has fields fails at render time. Pick layouts with enough room. `quote` may point at the same layout as `section` if no dedicated quote layout exists.

Confirm the mapping with the user before writing it.

## Step 5: Write the brand

Write three files into `.slides/` at the project root.

**`brand.json`** is what the renderer reads. Write `template` as `template.pptx`, the path relative to `brand.json` itself, so `.slides/` stays self-contained: `render.py` resolves a relative template path against the brand profile's own directory and finds the sibling file whatever directory it runs from.

```json
{
  "template": "template.pptx",
  "fonts": { "heading": "Georgia", "body": "Verdana" },
  "colours": { "ink": "#1A1A2E", "accent": "#E94560" },
  "layout_map": {
    "title": 0, "title-content": 1, "section": 2,
    "two-column": 3, "statement": 5, "quote": 2
  }
}
```

**`context.md`** is for a person and for the other skills to read. Write the voice, the audience norms, the presenting context, the template described in plain words, and the layout map with a line on why each role points where it does.

**`template.pptx`** is the chosen template, already copied in from Step 3.

Tell the user the brand is captured, name the three files, and point them at /slides:narrative to shape their first deck.
