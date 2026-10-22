"""Build the mainboard datasheet MS-MB-B.pdf.

Steps: figures (SVG -> PDF via Inkscape, KiCad renders copied), BOM from kicad/circuit.py
(make_bom.py), then pdflatex (MiKTeX, user install) twice for the table of contents.

Run:  python hardware/mainboard/datasheet/build.py
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MB = HERE.parent
FIG = HERE / "fig"
INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape.com")
MIKTEX = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64"
SVGS = [MB / "img" / n for n in ("system_blocks", "power_tree", "pyro_channel", "teensy_pinmap", "installation_side")]
SVGS.append(MB / "mainboard_placement")
RENDERS = ["render_top.png", "render_bottom.png", "render_iso.png"]


def crop_pdf(pdf, dpi=100, margin_pt=3):
    """pdfcrop without Ghostscript: rasterize with pdftoppm, find the non-white bounding box,
    set the page's CropBox and MediaBox to it. Invisible SVG elements leave white canvas
    around the drawing that --export-area-drawing keeps."""
    from PIL import Image, ImageChops
    from pypdf import PdfReader, PdfWriter
    png = pdf.with_suffix(".crop")
    subprocess.run([str(MIKTEX / "pdftoppm"), "-r", str(dpi), "-png", "-singlefile", str(pdf), str(png)],
                   check=True, capture_output=True)
    img = Image.open(png.with_suffix(".crop.png")).convert("RGB")
    bbox = ImageChops.difference(img, Image.new("RGB", img.size, "white")).getbbox()
    png.with_suffix(".crop.png").unlink()
    if not bbox:
        return
    reader = PdfReader(str(pdf))
    page = reader.pages[0]
    x0, y0, x1, y1 = (v * 72 / dpi for v in bbox)
    w, h = float(page.mediabox.width), float(page.mediabox.height)
    llx, lly = float(page.mediabox.left), float(page.mediabox.bottom)
    box = (llx + max(x0 - margin_pt, 0), lly + max(h - y1 - margin_pt, 0),
           llx + min(x1 + margin_pt, w), lly + min(h - y0 + margin_pt, h))
    page.mediabox.lower_left = box[:2]
    page.mediabox.upper_right = box[2:]
    page.cropbox.lower_left = box[:2]
    page.cropbox.upper_right = box[2:]
    writer = PdfWriter()
    writer.add_page(page)
    with open(pdf, "wb") as f:
        writer.write(f)


def figures():
    FIG.mkdir(exist_ok=True)
    for svg in SVGS:
        src, dst = svg.with_suffix(".svg"), FIG / (svg.name + ".pdf")
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            # the figures carry a full-canvas white rect; drop it so that --export-area-drawing
            # crops to the drawing and not to the canvas
            tmp = FIG / ("_" + svg.name + ".svg")
            tmp.write_text(src.read_text(encoding="utf-8").replace(
                '<rect width="100%" height="100%" fill="white"/>', ""), encoding="utf-8")
            subprocess.run([str(INKSCAPE), str(tmp), "--export-type=pdf", "--export-area-drawing",
                            f"--export-filename={dst}"], check=True, capture_output=True)
            tmp.unlink()
            crop_pdf(dst)
    for name in RENDERS:
        shutil.copy2(MB / "kicad" / "img" / name, FIG / name)


def main():
    figures()
    subprocess.run([sys.executable, str(HERE / "make_bom.py")], check=True)
    env = dict(os.environ, PATH=f"{MIKTEX};{os.environ['PATH']}")
    for _ in range(2):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-file-line-error", "MS-MB-B.tex"],
                           cwd=HERE, env=env, capture_output=True, text=True, errors="replace")
    log = (HERE / "MS-MB-B.log").read_text(encoding="utf-8", errors="replace")
    errors = [l for l in log.splitlines() if re.match(r"^.*:\d+: |^!", l)]
    lines = log.splitlines()
    over = [l + " | " + " ".join(lines[i + 1:i + 3]) for i, l in enumerate(lines)
            if re.match(r"Overfull \\hbox \(\d{2,}", l)]
    pages = re.search(r"Output written on .*\((\d+) pages", log)
    print("\n".join(errors[:20]))
    print(f"{len(over)} overfull boxes > 10pt" + (":\n  " + "\n  ".join(o[:200] for o in over[:5]) if over else ""))
    print(f"pages: {pages.group(1) if pages else 'no PDF'}")
    for ext in ("aux", "log", "out", "toc"):
        (HERE / f"MS-MB-B.{ext}").unlink(missing_ok=True)
    return 0 if pages and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
