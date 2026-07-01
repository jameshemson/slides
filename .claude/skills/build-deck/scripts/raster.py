#!/usr/bin/env python3
"""raster.py — rasterise a rendered .pptx to per-slide PNGs (pluggable backend).

The render-back visual-QA loop: build-deck renders a .pptx, this turns it into
per-slide images, and the build-deck skill (or a person) LOOKS at them for the
things the mechanical lint can't see from geometry alone — text that overflowed
its box, a font that fell back, a slide that reads as cluttered rather than
composed. It is the lint with eyes.

There is no pure-Python way to render a .pptx, so this needs an external app to
do the .pptx -> PDF step; the PDF -> PNG step is pure-Python (PyMuPDF) or poppler
(pdftoppm). Backends are tried in order and NONE is bundled or required — like
matplotlib for charts, an absent backend degrades to a clear message:

  1. LibreOffice (`soffice --headless --convert-to pdf`) — headless, portable,
     CI-friendly; the same path Anthropic's own pptx skill uses.
  2. Keynote (macOS, AppleScript export to PDF) — no install if Keynote is
     present, but GUI-driven and macOS-only. Experimental.

Usage:

    python3 raster.py <deck.pptx> --out-dir <dir> [--dpi N] [--sheet] [--check]

Exit status: 0 on success (PNG paths printed). If no backend is available it
exits non-zero with a message naming how to enable one, and writes nothing.
"""
import argparse
import os
import shutil
import subprocess
import sys


class RasterError(Exception):
    """A .pptx that cannot be rasterised (no backend, or a backend failed)."""


# --- backend detection -------------------------------------------------------


def _libreoffice_bin():
    """Path to a LibreOffice/soffice binary, or None."""
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    mac_app = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac_app if os.path.isfile(mac_app) else None


def _keynote_available():
    """True if this is macOS with Keynote installed."""
    return sys.platform == "darwin" and os.path.isdir("/Applications/Keynote.app")


def available_backend():
    """The backend that would be used: 'libreoffice', 'keynote', or None."""
    if _libreoffice_bin():
        return "libreoffice"
    if _keynote_available():
        return "keynote"
    return None


# --- .pptx -> PDF ------------------------------------------------------------


def _libreoffice_to_pdf(pptx_path, tmp_dir):
    """Convert a .pptx to PDF with headless LibreOffice; return the PDF path."""
    binary = _libreoffice_bin()
    proc = subprocess.run(
        [binary, "--headless", "--convert-to", "pdf", "--outdir", tmp_dir,
         pptx_path],
        capture_output=True, text=True, timeout=180,
    )
    base = os.path.splitext(os.path.basename(pptx_path))[0]
    pdf = os.path.join(tmp_dir, base + ".pdf")
    if proc.returncode != 0 or not os.path.isfile(pdf):
        raise RasterError(
            f"LibreOffice failed to convert {pptx_path}: "
            f"{(proc.stderr or proc.stdout).strip()[:300]}"
        )
    return pdf


def _keynote_to_pdf(pptx_path, out_pdf):
    """Convert a .pptx to PDF by driving Keynote via AppleScript (macOS only).

    Experimental: this opens Keynote and may prompt once for automation
    permission. Not headless, not unit-tested — the LibreOffice path is preferred.
    """
    script = (
        'on run argv\n'
        '  set inFile to POSIX file (item 1 of argv)\n'
        '  set outFile to POSIX file (item 2 of argv)\n'
        '  tell application "Keynote"\n'
        '    set theDoc to open inFile\n'
        '    export theDoc to outFile as PDF\n'
        '    close theDoc saving no\n'
        '  end tell\n'
        'end run\n'
    )
    proc = subprocess.run(
        ["osascript", "-e", script, os.path.abspath(pptx_path),
         os.path.abspath(out_pdf)],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0 or not os.path.isfile(out_pdf):
        raise RasterError(
            f"Keynote failed to export {pptx_path}: {proc.stderr.strip()[:300]}"
        )
    return out_pdf


# --- PDF -> PNGs (pure-Python PyMuPDF, else poppler) -------------------------


def _pdf_to_pngs(pdf_path, out_dir, dpi):
    """Rasterise each PDF page to out_dir/slide-N.png; return the paths in order."""
    os.makedirs(out_dir, exist_ok=True)
    try:
        import fitz  # PyMuPDF  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return _pdf_to_pngs_poppler(pdf_path, out_dir, dpi)
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    paths = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix)
        path = os.path.join(out_dir, f"slide-{i}.png")
        pix.save(path)
        paths.append(path)
    doc.close()
    return paths


def _pdf_to_pngs_poppler(pdf_path, out_dir, dpi):
    """Fallback: rasterise via poppler's pdftoppm."""
    if not shutil.which("pdftoppm"):
        raise RasterError(
            "no PDF rasteriser: install PyMuPDF (pip install pymupdf) or "
            "poppler (brew install poppler)"
        )
    prefix = os.path.join(out_dir, "slide")
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), pdf_path, prefix],
        check=True, capture_output=True, timeout=180,
    )
    pages = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
    # pdftoppm writes slide-1.png, slide-2.png (or slide-01.png); normalise order.
    return [os.path.join(out_dir, f) for f in pages]


# --- public entry point ------------------------------------------------------


def rasterise(pptx_path, out_dir, dpi=110):
    """Rasterise `pptx_path` to per-slide PNGs in `out_dir`; return the paths.

    Raises RasterError if no backend is available (naming how to enable one) or a
    backend fails, so the caller degrades rather than crashing.
    """
    if not os.path.isfile(pptx_path):
        raise RasterError(f"deck not found: {pptx_path}")
    backend = available_backend()
    if backend is None:
        raise RasterError(
            "no rasteriser available for the render-back check. Install "
            "LibreOffice (brew install --cask libreoffice) for a headless "
            "backend, or use Keynote on macOS."
        )
    os.makedirs(out_dir, exist_ok=True)
    if backend == "libreoffice":
        pdf = _libreoffice_to_pdf(pptx_path, out_dir)
    else:
        pdf = _keynote_to_pdf(pptx_path, os.path.join(out_dir, "_deck.pdf"))
    return _pdf_to_pngs(pdf, out_dir, dpi)


# --- cheap pixel checks (advisory signals; the real check is looking) --------


def looks_blank(png_path, ink_threshold=0.004):
    """True if a slide image is almost entirely one colour — a likely empty or
    broken slide. The modal grey is treated as the background; a slide with very
    little ink far from it reads as blank."""
    try:
        from PIL import Image  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return False
    hist = Image.open(png_path).convert("L").histogram()
    total = sum(hist) or 1
    bg = max(range(256), key=lambda v: hist[v])
    far = sum(hist[v] for v in range(256) if abs(v - bg) > 24)
    return (far / total) < ink_threshold


def contact_sheet(png_paths, out_path, cols=3, thumb_w=480):
    """Stitch slide PNGs into a single review sheet. Returns out_path or None."""
    try:
        from PIL import Image  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return None
    if not png_paths:
        return None
    thumbs = []
    for p in png_paths:
        im = Image.open(p).convert("RGB")
        scale = thumb_w / im.width
        thumbs.append(im.resize((thumb_w, max(1, int(im.height * scale)))))
    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(t.height for t in thumbs)
    sheet = Image.new("RGB", (cols * thumb_w, rows * cell_h), (240, 240, 240))
    for i, t in enumerate(thumbs):
        x = (i % cols) * thumb_w
        y = (i // cols) * cell_h
        sheet.paste(t, (x, y))
    sheet.save(out_path)
    return out_path


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rasterise a .pptx to per-slide PNGs for the render-back check."
    )
    parser.add_argument("pptx", help="path to a rendered .pptx")
    parser.add_argument("--out-dir", required=True, help="directory for the PNGs")
    parser.add_argument("--dpi", type=int, default=110, help="raster resolution")
    parser.add_argument("--sheet", action="store_true",
                        help="also write a contact-sheet.png review grid")
    parser.add_argument("--check", action="store_true",
                        help="flag likely-blank slides")
    args = parser.parse_args(argv)

    try:
        pngs = rasterise(args.pptx, args.out_dir, dpi=args.dpi)
    except RasterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"rasterised {len(pngs)} slide(s) via {available_backend()}")
    for p in pngs:
        print(f"  {p}")
    if args.check:
        blank = [os.path.basename(p) for p in pngs if looks_blank(p)]
        if blank:
            print(f"  [check] likely-blank slide(s): {', '.join(blank)}")
    if args.sheet:
        sheet = contact_sheet(pngs, os.path.join(args.out_dir, "contact-sheet.png"))
        if sheet:
            print(f"  contact sheet: {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
