---
name: slides
description: Make a slide deck from an idea and some notes. Asks a few short questions, shows the story back as slide headers for approval, then builds the .pptx. Use whenever someone asks for a deck, slides, a presentation or a talk, even if all they give you is one line.
---

*(Treat the user's message that invoked this skill as the task input.)*

Make the deck in three steps. No slide gets made until the person has approved the headers: a story is cheap to fix as a list and expensive to fix as slides, and anyone can judge a story by reading its headers.

## 1. A short grill

The person knows their audience and what this deck is for, and you don't, so this thinking is theirs. Don't work it out for them. Read what they've given you, then ask all of this in one go, skipping only what they've already told you:

- **Who is it for, and where are they on this now?** One real audience. If the answer is "everyone" or "the team", ask once for something sharper.
- **Will you present it live, or will they read it alone?** This decides how much goes on each slide.
- **What should they think, feel and do afterwards?** Three short answers, in their words: the core idea, the shift in how they feel, and the action.

If there are no notes, ask for them.

Then the brand. Look for `.slides/brand.json`, then `~/.slides/brand.json`, and if there is one, use it without asking, because starting every deck from the same file is what keeps them consistent. If not, ask whether there's a brand to follow. From a template or an on-brand deck, run `python3 scripts/brand.py capture <file>` and save the output as `.slides/brand.json`, or in `~/.slides/` if they want it for every deck. If the brand is only written down, write the file yourself. Show them the fonts and colours, ask about any extra font or shade the brand allows, and get a yes, because anything missing from the file will count as off brand. `scripts/` is in this skill's folder, and `brand.py` needs python-pptx (`pip install python-pptx`, or a virtualenv if the system Python refuses).



This should take a couple of minutes, so don't add questions. If they're stuck on one, offer a suggestion to react to. If they've said they aren't around to answer, make your own calls, say what you assumed, and carry on.

## 2. Find the story and show it back

Their think, feel and do are the brief, so keep only what serves them, however good the rest is. The one idea comes from their think.

Then choose the shape that suits this deck, because the same facts in a different order can land very differently. None of these is the default, and not every deck needs a turn:

- **A story,** to change minds: the situation and what's wrong, something that makes it relatable, the turn, their role.
- **A flow,** when order carries the meaning: chronological, step by step, or climbing from least to most important.
- **A contrast,** when things need weighing: problem and solution, compare and contrast, cause and effect, pros and cons.
- **Tell, tell, tell,** to explain or report: what you'll tell them, the content, then what you told them.

Whichever you choose, the audience is the hero and you're the guide. Start where they are, not with you or your work, and end on what they do, coming back to the opening if you can.

Reply with the one idea in a sentence, the shape and why in a few words, then the headers in order, one line per slide. Leave out layouts and slide contents, so the story is all there is to judge.

> **The one idea:** A guided first week would cut early churn for less than the discount we run now.
>
> **Shape:** problem and solution, because they need to approve a change.
>
> 1. Most customers we lose leave in their first month
> 2. They leave before they finish setup
> 3. Discounts haven't changed that
> 4. A guided first week cut early churn in the pilot
> 5. It costs less than the discount
> 6. Approve the rollout this quarter

Before you send them, check:

- Read alone and in order, the headers tell the whole story, and the reader knows what to do at the end.
- Each one says something and makes sense by itself. "Results" and "Next steps" say nothing.
- Each one is short, in words the audience uses.
- The story would break without each one. A presented deck needs far fewer slides than a read one, because the speaker carries the rest.
- The notes back every claim. Mark anything else "(my inference)", so the person decides on it now and doesn't find it later in their own voice.

Ask if it's right, and change it until they say yes.

## 3. Build

Use the `pptx` skill to build a .pptx. That skill may point you to a slides skill instead, but this is that skill, and a PowerPoint file is what's wanted, so stay with it. Give it:

- the approved headers, word for word, as the slide titles, plus a title slide if the deck needs one. If a header really won't fit, ask before changing it, because they approved that wording.
- who it's for, whether it's presented or read, and their think, feel and do.
- the notes.
- the brand's fonts and colours, if there is a brand, set as the deck's theme so anything added later in PowerPoint matches too. These override the `pptx` skill's own palette and font suggestions.

If it's presented, the slides back up the speaker, and what they'd say goes in the speaker notes. If it's read, the slides carry the detail, because nobody is there to explain it.

How it looks is the `pptx` skill's call, within the brand if there is one.

If there's a brand, run `python3 scripts/brand.py check <deck> --brand <file>` once the deck is built, and fix what it names. It checks fonts and colours only. If it names something the brand really does allow, ask, and add it to the brand file rather than taking it off the slide.

Keep figures exact. When it's done, give the file's path and slide count, and list anything on the slides the notes don't directly support.

If there's no `pptx` skill here, say so and build the .pptx with whatever this environment has.
