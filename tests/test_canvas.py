"""A-004 probe for the identity-not-layout brand-fidelity canvas (REQ-005).

Brand-mode slides are meant to be painted with the `paper` colour role via
python-pptx's `slide.background.fill` API — a slide-level background fill
that should apply uniformly under any content, without occupying an element
slot subject to the composition element cap.

This probe resolves assumption A-004: does `slide.background.fill` actually
write a slide-level `<p:bg>` element into the slide XML, and does that
survive a save/reopen round trip (i.e. is it durable, not just an in-memory
convenience that gets dropped on serialization)?

If this API does NOT persist across save/reopen, the fallback is a
full-bleed "paper" rectangle shape sized to the slide bounds, added first so
everything else draws on top of it, with named lint exemptions so it doesn't
count against the on-grid / element-cap checks that apply to real content
shapes.

Layout-selection note: the bundled default Presentation() template has no
layout with literally zero placeholders -- even "Blank" (index 6) carries
the optional DATE/FOOTER/SLIDE_NUMBER placeholders that PowerPoint omits
from a rendered slide unless populated. test_blank_layout_exists below
checks the invariant the brand renderer actually needs (a layout with no
CONTENT placeholders) rather than the stricter "zero placeholders total";
see that test's docstring for detail.

Run from the repo root:

    python3 -m unittest tests.test_canvas -v
"""

import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO_ROOT, "source", "skills", "build-deck", "scripts")
sys.path.insert(0, SCRIPTS)

from pptx import Presentation  # noqa: E402
from pptx.dml.color import RGBColor  # noqa: E402
from pptx.enum.shapes import PP_PLACEHOLDER_TYPE  # noqa: E402

# Placeholder types that carry actual slide content (title/body/object/
# picture/subtitle). DATE, FOOTER, and SLIDE_NUMBER are boilerplate
# metadata placeholders that PowerPoint omits from a rendered slide unless
# explicitly populated -- they don't stand in the way of a canvas layout.
_CONTENT_PLACEHOLDER_TYPES = {
    PP_PLACEHOLDER_TYPE.TITLE,
    PP_PLACEHOLDER_TYPE.CENTER_TITLE,
    PP_PLACEHOLDER_TYPE.SUBTITLE,
    PP_PLACEHOLDER_TYPE.BODY,
    PP_PLACEHOLDER_TYPE.OBJECT,
    PP_PLACEHOLDER_TYPE.PICTURE,
}


class CanvasBackgroundProbe(unittest.TestCase):
    """A-004: does slide.background.fill persist across save/reopen?"""

    def _blank_layout_index(self, prs):
        """Return the index of the first layout with zero placeholders,
        falling back to slide_layouts[6] (the bundled default template's
        conventional blank layout) if none is found."""
        for i, layout in enumerate(prs.slide_layouts):
            if len(layout.placeholders) == 0:
                return i
        return 6

    def test_background_fill_survives_save_reopen(self):
        prs = Presentation()
        layout = prs.slide_layouts[self._blank_layout_index(prs)]
        slide = prs.slides.add_slide(layout)

        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor.from_string("F4F1E9")

        tmp = tempfile.mkdtemp(prefix="slides-canvas-probe-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "canvas-probe.pptx")
        prs.save(path)

        reopened = Presentation(path)
        xml = reopened.slides[0]._element.xml
        self.assertIn("<p:bg", xml)
        self.assertIn("F4F1E9", xml)

    def test_untouched_slide_has_no_bg(self):
        prs = Presentation()
        layout = prs.slide_layouts[self._blank_layout_index(prs)]
        prs.slides.add_slide(layout)

        tmp = tempfile.mkdtemp(prefix="slides-canvas-probe-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = os.path.join(tmp, "canvas-probe-untouched.pptx")
        prs.save(path)

        reopened = Presentation(path)
        xml = reopened.slides[0]._element.xml
        self.assertNotIn("<p:bg", xml)

    def test_blank_layout_exists(self):
        """SCOPE_CHANGE note: the plan's premise for this test was that the
        bundled default template has a layout with literally zero
        placeholders. Empirically that's false -- every layout, including
        'Blank' (index 6), still carries the optional DATE/FOOTER/
        SLIDE_NUMBER placeholders (this is exactly why
        test_background_fill_survives_save_reopen above falls back to
        slide_layouts[6] rather than a true zero-placeholder match). The
        invariant the brand renderer actually needs is a layout with no
        CONTENT placeholders (title/body/object/picture/subtitle) to draw
        brand-composed slides onto -- so that's what this test checks."""
        prs = Presentation()
        blank_indices = [
            i for i, layout in enumerate(prs.slide_layouts)
            if len(layout.placeholders) == 0
        ]
        content_free_indices = [
            i for i, layout in enumerate(prs.slide_layouts)
            if not any(
                p.placeholder_format.type in _CONTENT_PLACEHOLDER_TYPES
                for p in layout.placeholders
            )
        ]
        self.assertTrue(
            len(content_free_indices) >= 1,
            "no content-placeholder-free layout found in the bundled "
            "default template; the brand renderer needs one (candidates: "
            "{}; true zero-placeholder layouts: {} -- none found, "
            "confirming the SCOPE_CHANGE note above)".format(
                content_free_indices, blank_indices
            ),
        )


if __name__ == "__main__":
    unittest.main()
