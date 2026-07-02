---
name: revise
description: Change a rendered deck by conversation — sync or extract its spec, reconcile hand-edits, revise, and re-render through the same brand and slop gates.
user-invocable: true
argument-hint: "[path to a .pptx or .deck.md]"
---

## MANDATORY PREPARATION

Load the `presentation-craft` skill. Read its [SKILL.md](../presentation-craft/SKILL.md) and run its Context Gathering Protocol — Step 6 needs a brand to re-render into. If `.slides/` is absent, don't make the user wait on the full interview: the Context Gathering Protocol's fast path works on the deck being revised too — a rendered `.pptx` carries masters and layouts the same way a template does — so copy it to `.slides/template.pptx` and run `../build-deck/scripts/init_brand.py .slides/template.pptx --template-ref template.pptx > .slides/brand.json`. Fall back to the fuller /slides:teach-slides interview if the user wants it.

Read [deck-spec.md](../presentation-craft/reference/deck-spec.md) for the spec contract and [slop.md](../presentation-craft/reference/slop.md) for the detector you run on changed content. Read [narrative.md](../presentation-craft/reference/narrative.md) only if the revision turns out to be structural (Step 4).

---

$ARGUMENTS

You change a deck that already exists — one you rendered last week, one a colleague hand-edited in PowerPoint, or one that predates the pack entirely. It goes back through the same brand, lint, and slop gates the first render went through. The spec is the source of truth; nothing gets overwritten without a yes.

## Step 1: Check the toolchain

The renderer needs Python. Run `python3 --version` and `python3 -c "import pptx"`.

If `python3` is missing, tell the user to install Python 3.9 or newer. If the `import pptx` line fails, give them the remedy:

```
pip install python-pptx
```

On macOS with a managed Python that command can refuse. Tell the user they can run `pip install --break-system-packages python-pptx`, or make a virtualenv. Wait for the toolchain to work before going on.

## Step 2: Identify the input

If `$ARGUMENTS` names neither a `.pptx` nor a `.deck.md`, ask which file to revise.

A `.deck.md` is already the spec — nothing to sync or extract. Skip straight to Step 4.

A `.pptx` needs its tier read first. Pull the lineage stamp render.py writes into the file's own metadata:

```
python3 -c "
from pptx import Presentation
print((Presentation('<deck>.pptx').core_properties.comments or '').strip())
"
```

- **Stamp found** (`slides-spec: <name> sha256:<hash>`) **and `<name>` exists** nearby (same directory as the deck, or the project root): **Tier 1, sync.** Say so plainly — "found the lineage stamp, found the spec, checking for drift" — and go to Step 3a.
- **Stamp found but `<name>` can't be located** (moved, renamed): ask the user for its path before giving up. If they don't have it, fall to Tier 2 and say why — the spec the stamp names couldn't be found.
- **No stamp at all**, or `comments` is empty: **Tier 2, import.** Say plainly this deck is foreign to the pack (or pre-dates the lineage stamp) and go to Step 3b.

## Step 3a: Tier 1 — sync the spec

Run the drift check — pass `--brand` so roles resolve exactly off the layout map rather than by heuristic guess:

```
python3 ../build-deck/scripts/deck_to_spec.py <deck>.pptx --brand .slides/brand.json \
    --against <deck>.deck.md
```

**Exit 0** — deck and spec agree. Go to Step 4.

**Exit 2** — the deck (or the spec) changed since the last render. Before reconciling anything, check which side moved: hash the spec file on disk and compare it to the sha in the stamp you read in Step 2.

```
python3 -c "import hashlib; print(hashlib.sha256(open('<deck>.deck.md','rb').read()).hexdigest())"
```

Compare the printed hash to the stamp's `sha256:` field verbatim. If they match, only the pptx was hand-edited — walk each diff line below. If they don't match, the *spec* was edited since render too — this isn't a simple hand-edit, so stop and ask the user which file is newer (check modification times) and which one should win before touching either.

Once you know the pptx alone changed, walk the diff output — each line names a slide and field with both texts, `slide 4 Title: pptx='…' spec='…'` — and for each one ask: fold the pptx's version into the spec (the default), or let the spec win and discard the hand-edit. A slide that exists in one file but not the other gets the same choice: fold it in as a new spec slide, or leave it out. Apply what's chosen by editing the spec file directly.

<!-- claude-only -->
Use the AskUserQuestion tool for the fold-in/spec-wins choice, one difference at a time, so the user picks rather than types.
<!-- /claude-only -->

## Step 3b: Tier 2 — import a spec

Run the extractor:

```
python3 ../build-deck/scripts/deck_to_spec.py <deck>.pptx --brand .slides/brand.json \
    --out <deck>.deck.md --report <deck>.import-report.md
```

Drop `--brand .slides/brand.json` if `.slides/` doesn't exist yet — extraction still runs, just guessing every slide's role from its shapes instead of reading it off a known layout map.

Walk the `.import-report.md` with the user honestly. This is a best-effort import, not a sync: some slides may have been flattened to `title-content` because their content was drawn shapes rather than placeholders, pictures and charts need re-declaring since a PNG can't be reversed to data, and roles may have been guessed rather than known. Say what the report says — don't round it up to "your deck is now in the pipeline" until the user has seen the losses.

The extracted frontmatter carries a placeholder `audience` and a default `register` — the spec contract requires a real audience before anything renders again (see deck-spec.md), so ask the user for both now.

<!-- claude-only -->
Use the AskUserQuestion tool to ask for audience and register as concrete choices once the report's been walked.
<!-- /claude-only -->

## Step 4: Revise

This is the conversation. If `$ARGUMENTS` didn't already say what to change, ask what the user wants and on which slide.

Keep it targeted and slide-level: open the spec, find the slide in question, edit it. When writing new or replacement content, hold the same discipline `narrative` applies from scratch — one idea per slide, the reflex rejections from slop.md before you write a word.

For a structural change — reordering, adding or cutting a slide, reshaping the arc — read narrative.md and work Plan and Create properly rather than shuffling text in place. A reorder is a new outline, not a find-and-replace.

A half-finished spec is still a valid file. If the conversation pauses here, what's written stays usable — nothing downstream has run yet.

## Step 5: Slop-check the change

Run the Deck Slop Test from slop.md on the slides you touched, and the five-dimension prose score on any notes you changed. Leave slides you didn't touch alone — re-auditing them is wasted work and invites edits nobody asked for.

## Step 6: Re-render

Same shape as build-deck's Step 3:

```
python3 ../build-deck/scripts/render.py --spec <deck>.deck.md \
    --brand .slides/brand.json --out <deck>.pptx
```

Never point `--out` at the original `.pptx` without an explicit yes. If the user hesitates, offer `<deck>-v2.pptx` instead and render there.

Point the user at build-deck's Step 4 render-back check before calling the revision done — the lint proves on-brand, not that nothing overflowed.

## Step 7: Report

Tell the user what changed, where the spec lives, and where the deck was written (the original path, or the `-v2` one). The new render carries a fresh lineage stamp, so this deck round-trips again — the next `/slides:revise` starts at Tier 1.
