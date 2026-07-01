"""Tests for raster.py — the render-back rasteriser.

The .pptx -> PDF step needs an external app (LibreOffice/Keynote) that isn't
present in CI, so it isn't unit-tested here; everything downstream (PDF -> PNG,
the blank check, the contact sheet, backend detection, graceful degradation) is.
"""
import os
import sys
import tempfile
import unittest

_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "source", "skills",
                 "build-deck", "scripts")
)
sys.path.insert(0, _SCRIPTS_DIR)

import raster  # noqa: E402
from raster import RasterError  # noqa: E402

try:
    import fitz  # noqa: F401
    HAVE_FITZ = True
except Exception:  # noqa: BLE001
    HAVE_FITZ = False

try:
    from PIL import Image
    HAVE_PIL = True
except Exception:  # noqa: BLE001
    HAVE_PIL = False


class TestBackendDetection(unittest.TestCase):
    def test_available_backend_is_known_or_none(self):
        self.assertIn(raster.available_backend(),
                      ("libreoffice", "keynote", None))

    def test_no_backend_raises_named_error(self):
        original = raster.available_backend
        raster.available_backend = lambda: None
        try:
            with tempfile.TemporaryDirectory() as tmp:
                pptx = os.path.join(tmp, "d.pptx")
                open(pptx, "wb").close()
                with self.assertRaises(RasterError) as ctx:
                    raster.rasterise(pptx, tmp)
            self.assertIn("no rasteriser", str(ctx.exception).lower())
        finally:
            raster.available_backend = original

    def test_missing_deck_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RasterError):
                raster.rasterise(os.path.join(tmp, "nope.pptx"), tmp)


@unittest.skipUnless(HAVE_FITZ, "PyMuPDF not installed")
class TestPdfToPngs(unittest.TestCase):
    def test_splits_pages_to_pngs(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, "deck.pdf")
            doc = fitz.open()
            for _ in range(3):
                doc.new_page()
            doc.save(pdf)
            doc.close()
            pngs = raster._pdf_to_pngs(pdf, tmp, dpi=72)
            self.assertEqual(len(pngs), 3)
            for p in pngs:
                self.assertTrue(os.path.isfile(p))
                with open(p, "rb") as fh:
                    self.assertEqual(fh.read(8), b"\x89PNG\r\n\x1a\n")


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestPixelChecks(unittest.TestCase):
    def _png(self, tmp, name, draw_rect=False):
        img = Image.new("RGB", (400, 300), (255, 255, 255))
        if draw_rect:
            for x in range(150, 250):
                for y in range(120, 180):
                    img.putpixel((x, y), (0, 0, 0))
        p = os.path.join(tmp, name)
        img.save(p)
        return p

    def test_blank_slide_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(raster.looks_blank(self._png(tmp, "blank.png")))
            self.assertFalse(
                raster.looks_blank(self._png(tmp, "inked.png", draw_rect=True)))

    def test_contact_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            pngs = [self._png(tmp, f"s{i}.png", draw_rect=True) for i in range(3)]
            out = raster.contact_sheet(pngs, os.path.join(tmp, "sheet.png"))
            self.assertTrue(out and os.path.isfile(out))


if __name__ == "__main__":
    unittest.main()
