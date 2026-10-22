"""Kartonaut mission patch as polygons: one source for the silkscreen and the SVG files in docs/brand/.

The patch is a filled ring with the name cut out along the top and a second line along the bottom,
and the rocket in the open centre. Geometry in units of a 100 x 100 box (ring 48 outside, 33 inside),
scaled to the wanted diameter. Lettering is KiCad's stroke font turned into polygons, so the board
and the SVG look the same and the SVG needs no font.

Runs in KiCad's Python (pcbnew):

    "%LOCALAPPDATA%/Programs/KiCad/10.0/bin/python.exe" logo.py      # writes docs/brand/*.svg
"""
import math
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
BRAND = HERE.parents[2] / "docs" / "brand"
MM = pcbnew.FromMM

R_OUT, R_IN, R_TEXT = 48.0, 33.0, 40.5       # ring and centre line of the lettering
TEXT_H, TEXT_W = 7.4, 1.25                    # cap height and stroke width of the lettering
INK, ACCENT = "#0f1c2e", "#e8542a"

# rocket outline: nose as two cubic curves, fins straight
_ROCKET = [("M", 50, 22), ("C", 54.5, 28, 55.5, 33, 55.5, 38), ("L", 55.5, 59), ("L", 61, 66), ("L", 61, 70),
           ("L", 55.5, 66), ("L", 44.5, 66), ("L", 39, 70), ("L", 39, 66), ("L", 44.5, 59), ("L", 44.5, 38),
           ("C", 44.5, 33, 45.5, 28, 50, 22)]
FLAME = [(46.5, 68), (53.5, 68), (50, 77)]
STARS = [(33, 44, 1.5), (64, 28, 1.2), (68, 52, 1.0)]
DOTS = [(9.5, 50, 1.8), (90.5, 50, 1.8)]       # separators between the two lines of the ring


def rocket_points(steps=12):
    pts, cur = [], None
    for cmd, *a in _ROCKET:
        if cmd in "ML":
            cur = (a[0], a[1])
            pts.append(cur)
        else:
            p0, p1, p2, p3 = cur, (a[0], a[1]), (a[2], a[3]), (a[4], a[5])
            for k in range(1, steps + 1):
                t = k / steps
                pts.append(tuple((1 - t) ** 3 * p0[i] + 3 * (1 - t) ** 2 * t * p1[i] + 3 * (1 - t) * t ** 2 * p2[i]
                                 + t ** 3 * p3[i] for i in range(2)))
            cur = p3
    return pts[:-1]


class Patch:
    """Polygons of one patch with centre (cx, cy) in mm (KiCad coordinates) and diameter d in mm.
    top/bottom: lettering in the ring; without lettering the ring stays solid (small marks)."""

    def __init__(self, cx, cy, d, top="", bottom="", mirror=False):
        self.cx, self.cy, self.s = cx, cy, d / (2 * R_OUT)
        self.mirror = mirror
        self.ink = self.disc(50, 50, R_OUT)
        self.ink.BooleanSubtract(self.disc(50, 50, R_IN))
        if top or bottom:
            cut = self.lettering(top, +1)
            cut.BooleanAdd(self.lettering(bottom, -1))
            for x, y, r in DOTS:
                cut.BooleanAdd(self.disc(x, y, r))
            self.ink.BooleanSubtract(cut)
        self.ink.BooleanAdd(self.poly(rocket_points()))
        for x, y, r in STARS:
            self.ink.BooleanAdd(self.disc(x, y, r))
        self.accent = self.poly(FLAME)

    def pt(self, x, y):
        u = (x - 50) * self.s * (-1 if self.mirror else 1)
        return MM(self.cx + u), MM(self.cy + (y - 50) * self.s)

    def poly(self, pts):
        p = pcbnew.SHAPE_POLY_SET()
        p.NewOutline()
        for x, y in pts:
            p.Append(*self.pt(x, y))
        return p

    def disc(self, x, y, r, n=96):
        return self.poly([(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n))
                          for k in range(n)])

    def glyph(self, ch, x, y, angle):
        t = pcbnew.PCB_TEXT(pcbnew.BOARD())
        t.SetText(ch)
        h = MM(TEXT_H * self.s)
        t.SetTextSize(pcbnew.VECTOR2I(h, h))
        t.SetTextThickness(MM(TEXT_W * self.s))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        t.SetPosition(pcbnew.VECTOR2I(*self.pt(x, y)))
        t.SetTextAngleDegrees(-angle if self.mirror else angle)
        t.SetMirrored(self.mirror)
        p = pcbnew.SHAPE_POLY_SET()
        t.TransformTextToPolySet(p, 0, MM(0.002), pcbnew.ERROR_INSIDE)
        return p

    def lettering(self, text, side):
        """side +1: along the top, read from outside; -1: along the bottom, read from inside."""
        out = pcbnew.SHAPE_POLY_SET()
        if not text:
            return out
        adv = []
        for ch in text:
            if ch == " ":
                adv.append(0.55 * TEXT_H)
                continue
            bb = self.glyph(ch, 50, 50, 0).BBox()
            adv.append(pcbnew.ToMM(bb.GetWidth()) / self.s + 0.32 * TEXT_H)
        pos, total = 0.0, sum(adv)
        for ch, a in zip(text, adv):
            phi = (pos + a / 2 - total / 2) / R_TEXT          # radians along the ring, 0 at top/bottom
            pos += a
            if ch == " ":
                continue
            x = 50 + R_TEXT * math.sin(phi)
            y = 50 - side * R_TEXT * math.cos(phi)
            out.BooleanAdd(self.glyph(ch, x, y, -side * math.degrees(phi)))
        return out

    def silk(self):
        p = pcbnew.SHAPE_POLY_SET(self.ink)
        p.BooleanAdd(self.accent)
        return p

    def shapes(self, board, layer):
        """Filled silkscreen polygons, holes fractured for Gerber."""
        p = self.silk()
        p.Fracture()
        out = []
        for i in range(p.OutlineCount()):
            one = pcbnew.SHAPE_POLY_SET()
            one.AddOutline(p.COutline(i))
            s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
            s.SetPolyShape(one)
            s.SetFilled(True)
            s.SetWidth(0)
            s.SetLayer(layer)
            board.Add(s)
            out.append(s)
        return out


def svg_path(p):
    d = []
    for i in range(p.OutlineCount()):
        chains = [p.COutline(i)] + [p.CHole(i, h) for h in range(p.HoleCount(i))]
        for c in chains:
            pts = [c.CPoint(k) for k in range(c.PointCount())]
            d.append("M" + " ".join(f"{pcbnew.ToMM(q.x):.2f},{pcbnew.ToMM(q.y):.2f}" for q in pts) + "Z")
    return "".join(d)


def write_svg(path, top, bottom, ink=INK, accent=ACCENT, disc="#ffffff"):
    """100 x 100 SVG; the open centre is filled with `disc` so the patch reads on dark pages too."""
    p = Patch(50, 50, 2 * R_OUT, top, bottom)
    back = f'<circle cx="50" cy="50" r="{R_IN + 0.5}" fill="{disc}"/>' if disc else ""
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="400" height="400">'
        f'<title>Kartonaut</title>{back}'
        f'<path fill="{ink}" fill-rule="evenodd" d="{svg_path(p.ink)}"/>'
        f'<path fill="{accent}" d="{svg_path(p.accent)}"/></svg>\n', encoding="utf-8")


if __name__ == "__main__":
    BRAND.mkdir(parents=True, exist_ok=True)
    write_svg(BRAND / "kartonaut_patch.svg", "KARTONAUT", "TVC · Ø 75 MM")
    write_svg(BRAND / "kartonaut_1.svg", "KARTONAUT 1", "ERSTFLUG")
    write_svg(BRAND / "kartonaut_patch_mono.svg", "KARTONAUT", "TVC · Ø 75 MM", ink="#000000", accent="#000000", disc="")
    print("written to", BRAND)
