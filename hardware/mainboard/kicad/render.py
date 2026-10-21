"""Layer plots for the Design Guide from the per-layer PDFs that make.sh exports with kicad-cli.

Cuts each page to the board, writes img/layer_<name>.png (300 dpi) and joins all pages into
img/layers.pdf with a title per page. The 3D renders (img/render_*.png) come from make.sh directly.
"""
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
IMG = HERE / "img"
TITLES = {"F_Cu": "F.Cu - Bauteilseite, Signale", "In1_Cu": "In1.Cu - GND-Flaeche",
          "In2_Cu": "In2.Cu - Signale", "B_Cu": "B.Cu - Versorgungsflaeche GND_PWR / 5V_SYS",
          "Bestueckung": "Bestueckungsdruck und Bauteilumrisse"}
X0, Y0 = 100.0, 50.0                    # board origin in the PCB file (gen_pcb.py)


def crop_renders(margin=40):
    """Cut the 3D renders to the board: the background is a vertical gradient, so a pixel belongs to
    the board (or its shadow) where it differs from the left edge pixel of its row."""
    import numpy as np
    from PIL import Image
    for name in ("render_top", "render_bottom", "render_iso"):
        path = IMG / f"{name}.png"
        if not path.exists():
            continue
        a = np.asarray(Image.open(path).convert("RGB")).astype(int)
        diff = np.abs(a - a[:, :1, :]).sum(axis=2) > 40
        ys, xs = np.nonzero(diff)
        if len(xs) == 0:
            continue
        box = (max(xs.min() - margin, 0), max(ys.min() - margin, 0),
               min(xs.max() + margin, a.shape[1]), min(ys.max() + margin, a.shape[0]))
        Image.open(path).crop(box).save(path)


def main():
    crop_renders()
    out, sources = pymupdf.open(), []
    mm = 72 / 25.4
    clip = pymupdf.Rect((X0 - 3) * mm, (Y0 - 3) * mm, (X0 + 57) * mm, (Y0 + 123) * mm)
    for name, title in TITLES.items():
        pdf = IMG / f"_{name}.pdf"
        d = pymupdf.open(pdf)
        d[0].get_pixmap(dpi=300, clip=clip).save(IMG / f"layer_{name}.png")
        page = out.new_page(width=clip.width, height=clip.height + 22)
        page.show_pdf_page(pymupdf.Rect(0, 22, clip.width, clip.height + 22), d, 0, clip=clip)
        page.insert_text((6, 15), title, fontsize=8)
        sources.append(d)
    out.save(IMG / "layers.pdf")
    for d in sources:              # the sources stay open until the joined PDF is written; make.sh deletes them
        d.close()
    print("img/layers.pdf, img/layer_*.png")


if __name__ == "__main__":
    main()
