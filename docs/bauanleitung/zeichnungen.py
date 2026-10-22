"""Technische Zeichnungen und 1:1-Bohrschablonen für die Modulbauweise von Kartonaut 1 (Erstflug).

    python docs/bauanleitung/zeichnungen.py

Schreibt
  docs/bauanleitung/Zeichnungen_Kartonaut1.pdf    Blatt Z1 … Z7 (A4 quer, maßstäblich, Maße in mm)
  docs/bauanleitung/Bohrschablonen_1zu1.pdf       Blatt S1 … S4 zum Ausdrucken in Originalgröße und Umwickeln des Rohrs
  docs/img/bauanleitung/Z*.png, S*.png            dieselben Blätter als Bild für die Bauanleitung
Alle Maße kommen aus cad/modular_params.py und cad/params.py (MS_CONFIG=erstflug), keine Zahl steht hier doppelt.
"""
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MS_CONFIG", "erstflug")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "cad"))
import params as P          # noqa: E402
import modular_params as M  # noqa: E402

import matplotlib            # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle, Circle, Polygon, FancyBboxPatch  # noqa: E402

IMG = ROOT / "docs" / "img" / "bauanleitung"
A4 = (297.0, 210.0)
DATE = "22.10.2026"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "hatch.linewidth": 0.4})
LW, LW_THIN = 0.7, 0.35
C_PART, C_DIM, C_HIDDEN, C_HOLE, C_CUT, C_WARN = "#111", "#1f4e9c", "#888", "#c0392b", "#e67e22", "#f2c4c4"
SEAM = -30.0     # Abwicklung und Schablonen beginnen bei 330°: dort liegt kein Loch, die Längslinie 0° liegt 30° rechts der Naht
import textwrap  # noqa: E402


def sx(phi, C):
    """Bogenlänge ab der Naht (330°) für den Winkel phi."""
    return ((phi - SEAM) % 360.0) / 360.0 * C


# --------------------------------------------------------------------------- Blatt und Ansicht
class Sheet:
    def __init__(self, nr, title, scale_txt, note=""):
        self.fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
        ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, A4[0]); ax.set_ylim(0, A4[1]); ax.set_aspect("equal"); ax.axis("off")
        self.ax = ax
        ax.add_patch(Rectangle((8, 8), A4[0] - 16, A4[1] - 16, fill=False, lw=0.8, ec="#333"))
        # Schriftfeld
        x0, y0, w, h = A4[0] - 8 - 110, 8, 110, 24
        ax.add_patch(Rectangle((x0, y0), w, h, fill=False, lw=0.8, ec="#333"))
        for yy in (y0 + 8, y0 + 16):
            ax.plot([x0, x0 + w], [yy, yy], lw=0.4, c="#333")
        ax.plot([x0 + 70, x0 + 70], [y0, y0 + 16], lw=0.4, c="#333")
        ax.text(x0 + 2, y0 + 19, f"{nr}  {title}", fontsize=9, weight="bold", va="center")
        ax.text(x0 + 2, y0 + 12, "Kartonaut 1 · Modulbauweise (Erstflug)", va="center")
        ax.text(x0 + 2, y0 + 4, "Maße in mm · Quelle cad/modular_params.py", va="center", fontsize=6)
        ax.text(x0 + 72, y0 + 12, f"Maßstab {scale_txt}", va="center")
        ax.text(x0 + 72, y0 + 4, f"Stand {DATE}", va="center")
        if note:
            ax.text(12, 11, "\n".join(textwrap.wrap(note, 118)), fontsize=6.0, va="bottom", color="#333", linespacing=1.25)
        self.nr = nr

    def view(self, ox, oy, s, label=None):
        v = View(self.ax, ox, oy, s)
        if label:
            self.ax.text(ox, oy, "", fontsize=8)
        return v

    def text(self, x, y, t, **kw):
        kw.setdefault("fontsize", 7)
        self.ax.text(x, y, t, **kw)

    def table(self, x, y, rows, col_w, row_h=4.2, header=True, fs=6.3):
        for i, row in enumerate(rows):
            yy = y - i * row_h
            xx = x
            for j, cell in enumerate(row):
                self.ax.text(xx + 1, yy - row_h / 2, str(cell), fontsize=fs, va="center",
                             weight="bold" if header and i == 0 else "normal")
                self.ax.add_patch(Rectangle((xx, yy - row_h), col_w[j], row_h, fill=(header and i == 0), fc="#eee",
                                            ec="#999", lw=0.3))
                xx += col_w[j]

    def save(self, pdf, png_name):
        pdf.savefig(self.fig)
        self.fig.savefig(IMG / png_name, dpi=170)
        plt.close(self.fig)


class View:
    """Ansicht mit Ursprung (ox, oy) auf dem Blatt und Maßstab s (Blatt-mm je Modell-mm)."""

    def __init__(self, ax, ox, oy, s):
        self.ax, self.ox, self.oy, self.s = ax, ox, oy, s

    def P(self, x, y):
        return self.ox + x * self.s, self.oy + y * self.s

    def line(self, pts, lw=LW, c=C_PART, ls="-", **kw):
        xs, ys = zip(*[self.P(*p) for p in pts])
        self.ax.plot(xs, ys, lw=lw, c=c, ls=ls, solid_capstyle="butt", **kw)

    def rect(self, x0, y0, x1, y1, lw=LW, c=C_PART, ls="-", fill=None, hatch=None, alpha=1.0):
        (a, b), (cc, d) = self.P(x0, y0), self.P(x1, y1)
        self.ax.add_patch(Rectangle((min(a, cc), min(b, d)), abs(cc - a), abs(d - b), fill=fill is not None,
                                    fc=fill or "none", ec=c, lw=lw, ls=ls, hatch=hatch, alpha=alpha))

    def circle(self, x, y, d, lw=LW, c=C_PART, ls="-", fill=None):
        self.ax.add_patch(Circle(self.P(x, y), d / 2 * self.s, fill=fill is not None, fc=fill or "none", ec=c, lw=lw, ls=ls))

    def hole(self, x, y, d, c=C_HOLE, label=None, cross=4.0):
        self.circle(x, y, d, c=c, lw=0.6)
        px, py = self.P(x, y)
        k = max(cross, d * self.s / 2 + 1.5)
        self.ax.plot([px - k, px + k], [py, py], lw=0.3, c=c)
        self.ax.plot([px, px], [py - k, py + k], lw=0.3, c=c)
        if label:
            self.ax.text(px + k * 0.7, py + k * 0.7, label, fontsize=5.6, color=c)

    def text(self, x, y, t, **kw):
        kw.setdefault("fontsize", 6.5)
        self.ax.text(*self.P(x, y), t, **kw)

    def center(self, pts):
        self.line(pts, lw=0.3, c="#666", ls=(0, (8, 2, 1, 2)))

    def dim(self, p0, p1, off, text=None, fs=6.0, c=C_DIM, ext=True):
        """Maßlinie zwischen p0 und p1 (Modellkoordinaten), um off (Blatt-mm) senkrecht versetzt."""
        (x0, y0), (x1, y1) = self.P(*p0), self.P(*p1)
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        nx, ny = -dy / L, dx / L
        a0 = (x0 + nx * off, y0 + ny * off)
        a1 = (x1 + nx * off, y1 + ny * off)
        if ext:
            sg = 1 if off >= 0 else -1
            for (bx, by), (ax_, ay_) in (((x0, y0), a0), ((x1, y1), a1)):
                self.ax.plot([bx + nx * sg * 0.8, ax_ + nx * sg * 1.2], [by + ny * sg * 0.8, ay_ + ny * sg * 1.2], lw=0.25, c=c)
        self.ax.annotate("", xy=a1, xytext=a0, arrowprops=dict(arrowstyle="<|-|>", lw=0.35, color=c,
                                                                mutation_scale=4.5, shrinkA=0, shrinkB=0))
        val = text if text is not None else fmt(L / self.s)
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90.5 or ang < -89.5:
            ang += 180
        mx, my = (a0[0] + a1[0]) / 2 + nx * 1.4, (a0[1] + a1[1]) / 2 + ny * 1.4
        self.ax.text(mx, my, val, fontsize=fs, color=c, ha="center", va="center", rotation=ang,
                     bbox=dict(fc="white", ec="none", pad=0.15))

    def leader(self, p, t_off, text, c="#333", fs=6.0):
        px, py = self.P(*p)
        tx, ty = px + t_off[0], py + t_off[1]
        self.ax.annotate(text, xy=(px, py), xytext=(tx, ty), fontsize=fs, color=c,
                         arrowprops=dict(arrowstyle="-|>", lw=0.35, color=c, mutation_scale=4),
                         ha="left" if t_off[0] >= 0 else "right", va="center")


def fmt(v):
    return f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def deg(v):
    return f"{fmt(v)}°"


# --------------------------------------------------------------------------- Lochlisten der Rohre (aus den Parametern)
def zl(z):
    return z - M.TUBE_BOTTOM_Z


def zu(z):
    return z - M.JOINT_Z


def lower_features():
    """(Art, phi, h0, h1, d/Breite, Text) auf dem unteren Rohr, h ab Rohrunterkante."""
    f = []
    for phi in M.SCREW_PHI:
        f.append(("hole", phi, zl(M.TVC_SCREW_Z), None, M.SCREW_HOLE_PAPER, "Kardan M3"))
    f.append(("hole", M.KEY_PHI, zl(M.KEY_Z), None, M.KEY_HOLE_D, "Schlüsselschalter"))
    for phi in M.BARO_PHI:
        f.append(("hole", phi, zl(M.BARO_Z), None, M.BARO_D, "Baro"))
    for nm, hd in (("Luke A1 (SD)", M.HATCH_A1), ("Luke B (Schalter)", M.HATCH_B)):
        f.append(("win", hd["phi"], zl(M.v_to_z(hd["v"][0])), zl(M.v_to_z(hd["v"][1])), hd.get("w", M.HATCH_W), nm))
    return f


def upper_features():
    f = []
    for phi in M.SCREW_PHI:
        f.append(("hole", phi, zu(M.JOINT_SCREW_Z), None, M.SCREW_HOLE_PAPER, "Stoß M3"))
    for phi in M.SHEAR_PIN_PHI:
        f.append(("hole", phi, zu(M.SHEAR_PIN_Z), None, M.SHEAR_PIN_D, "Abscherstift M2"))
    hd = M.HATCH_A2
    f.append(("win", hd["phi"], 0.0, zu(M.v_to_z(hd["v"][1])), M.HATCH_W, "Kerbe A2 (USB)"))
    return f


def coupler_features():
    f = []
    zc = M.COUPLER_Z[0]
    for phi in M.SCREW_PHI:
        f.append(("hole", phi, M.JOINT_SCREW_Z - zc, None, M.SCREW_HOLE_PAPER, "Stoß M3"))
    for phi in M.BARO_PHI:
        f.append(("hole", phi, M.BARO_Z - zc, None, M.BARO_D, "Baro"))
    for nm, hd in (("A1", M.HATCH_A1), ("B", M.HATCH_B), ("A2", M.HATCH_A2)):
        f.append(("win", hd["phi"], M.v_to_z(hd["v"][0]) - zc, M.v_to_z(hd["v"][1]) - zc, hd.get("w", M.HATCH_W), f"Fenster {nm}"))
    return f


def draw_development(v, C, L, feats, title, zones=(), guides=True):
    """Abwicklung von außen: x = Bogenlänge ab der Naht bei 330° (0 … C), y = h ab Unterkante (0 … L)."""
    v.rect(0, 0, C, L, lw=LW)
    for k in range(8):
        x = sx(45 * k, C)
        v.line([(x, 0), (x, L)], lw=0.25, c="#bbb", ls=(0, (3, 3)))
        v.text(x, L + 2.5 / v.s, deg(45 * k), ha="center", fontsize=5.8, color="#555")
    x0 = sx(0, C)
    v.line([(x0, 0), (x0, L)], lw=1.1, c="#2a7")
    v.text(x0, -5 / v.s, "Längslinie 0°", ha="center", fontsize=5.6, color="#2a7")
    v.text(0, -9 / v.s, "Naht 330°", ha="center", fontsize=5.2, color="#777")
    if guides:
        half = math.degrees(math.atan(10.0 / (M.TUBE_OD / 2 + M.RAMP_GUIDE_GAP)))
        for g in M.RAMP_GUIDE_PHI:
            a, b = sx(g - half, C), sx(g + half, C)
            hg = min(M.RAMP_GUIDE_H, L)
            v.rect(a, 0, b, hg, lw=0.3, c="#c99", fill=C_WARN, alpha=0.45)
            v.text((a + b) / 2, hg / 2, "Führung Startrampe: frei halten", ha="center", va="center", fontsize=4.6,
                   color="#a55", rotation=90)
    for (h0, h1, txt) in zones:
        v.rect(0, h0, C, h1, lw=0.3, c="#7a9", ls=(0, (2, 2)), fill="#e8f3ec", alpha=0.6)
        v.text(C + 2 / v.s, (h0 + h1) / 2, txt, va="center", fontsize=5.4, color="#386")
    for kind, phi, h0, h1, d, txt in feats:
        x = sx(phi, C)
        if kind == "hole":
            v.hole(x, h0, d, label=f"Ø{fmt(d)}")
        else:
            v.rect(x - d / 2, h0, x + d / 2, h1, lw=0.7, c=C_CUT, fill="#fbe3cf", hatch="////")
            v.text(x, (h0 + h1) / 2, txt, ha="center", va="center", fontsize=5.2, rotation=90, color="#8a4a12")
    v.text(C / 2, L + 8 / v.s, title, ha="center", fontsize=7, weight="bold")


def feature_table(feats, C):
    rows = [["Nr", "Art", "Winkel", "Bogen ab Naht", "h ab Kante", "Maß"]]
    k = 1
    for kind, phi, h0, h1, d, txt in sorted(feats, key=lambda f: (f[2], f[1])):
        s = sx(phi, C)
        if kind == "hole":
            rows.append([k, txt, deg(phi), fmt(s), fmt(h0), f"Ø {fmt(d)}"])
        else:
            rows.append([k, txt, deg(phi), f"{fmt(s - d / 2)} … {fmt(s + d / 2)}", f"{fmt(h0)} … {fmt(h1)}", f"{fmt(d)} × {fmt(h1 - h0)}"])
        k += 1
    return rows


# --------------------------------------------------------------------------- Z1 Übersicht
def z1(pdf):
    sh = Sheet("Z1", "Übersicht, Module und Trennstellen", "1:4",
               "Längsschnitt in der Ebene der Platine (Blick von +x). z = Abstand von der Düsenebene. "
               "Module: M1 Antrieb, M2 Unterteil (geklebt), M3 Avionik-Schlitten, M4 Oberteil mit Bergung, M5 Spitze. "
               "T1 … T5 sind die Trennstellen; nur dort wird geschraubt oder gesteckt.")
    s = 0.25
    v = sh.view(28, 150, s)       # z waagrecht (nach rechts), y senkrecht

    def zr(z0, z1, r0, r1, **kw):
        v.rect(z0, r0, z1, r1, **kw)
        v.rect(z0, -r1, z1, -r0, **kw)
    R, Ri = M.TUBE_OD / 2, M.TUBE_ID / 2
    zr(M.TUBE_BOTTOM_Z, M.JOINT_Z, Ri, R, fill="#efe6cf", lw=0.5)
    zr(M.JOINT_Z, M.TOP_Z, Ri, R, fill="#efe6cf", lw=0.5)
    zr(M.COUPLER_Z[0], M.COUPLER_Z[1], P.COUPLER_ID / 2, P.COUPLER_OD / 2, fill="#c9ad86", lw=0.4)
    zr(*M.KEY_RING_Z, M.KEY_RING_OD / 2 - M.KEY_RING_WALL, M.KEY_RING_OD / 2, fill="#6d8fc7", lw=0.4)
    v.rect(M.KEY_RING_Z[0], -M.KEY_RING_OD / 2 + 2.5, M.KEY_RING_Z[0] + 1.6, M.KEY_RING_OD / 2 - 2.5, fill="#6d8fc7", lw=0.3)
    # Kardan, Motor
    v.rect(0, -P.MOTOR_D / 2, P.MOTOR_L, P.MOTOR_D / 2, fill="#b9775a", lw=0.4)
    v.rect(P.MOTOR_TUBE_Z[0], -P.MOTOR_TUBE_OD / 2, P.MOTOR_TUBE_Z[1], P.MOTOR_TUBE_OD / 2, lw=0.4, c="#345")
    zr(P.TVC_RING_Z, P.TVC_RING_Z + P.OUTER_H, P.OUTER_RING_ID / 2, P.OUTER_RING_OD / 2, fill="#8fb1e0", lw=0.4)
    # Schlitten
    v.rect(*[M.DISC_Z[0], -M.DISC_OD / 2, M.DISC_Z[1], M.DISC_OD / 2], fill="#8fb1e0", lw=0.4)
    v.rect(M.BOARD_V0_Z, -M.BOARD_W / 2, M.BOARD_V0_Z + M.BOARD_L, M.BOARD_W / 2, fill="#2e7d4f", lw=0.4, alpha=0.85)
    zr(*M.SPIGOT_Z, M.SPIGOT_ID / 2, M.SPIGOT_OD / 2, fill="#8fb1e0", lw=0.4)
    v.rect(M.FLANGE_Z[0], -M.FLANGE_OD / 2, M.FLANGE_Z[1], M.FLANGE_OD / 2, fill="#8fb1e0", lw=0.4)
    # Bergung, Spitze
    zr(*M.PISTON_Z, P.COUPLER_ID / 2, P.COUPLER_OD / 2, fill="#c9ad86", lw=0.4)
    v.rect(M.PISTON_Z[0], -P.COUPLER_ID / 2, M.PISTON_Z[0] + 3, P.COUPLER_ID / 2, fill="#6d8fc7", lw=0.3)
    v.rect(M.CHUTE_Z[0], -P.CHUTE_D / 2, M.CHUTE_Z[1], P.CHUTE_D / 2, fill="#e8a49c", lw=0.4)
    zr(*M.NOSE_SHOULDER_Z, P.NOSE_SHOULDER_D / 2 - 1.2, P.NOSE_SHOULDER_D / 2, fill="#c9ad86", lw=0.3)
    import airframe
    prof = airframe.nose_profile()
    pts = [(M.TOP_Z + dz, r) for r, dz in prof] + [(M.TOP_Z + dz, -r) for r, dz in reversed(prof)]
    sh.ax.add_patch(Polygon([v.P(*p) for p in pts], closed=True, fc="#f4f4f4", ec="#111", lw=0.5))
    v.center([(-10, 0), (M.TOP_Z + P.NOSE_L + 10, 0)])
    # Stationen
    stations = [(0, "Düse"), (M.TUBE_BOTTOM_Z, ""), (M.TVC_SCREW_Z, "T1"), (M.KEY_Z, ""), (M.COUPLER_Z[0], ""),
                (M.BOARD_V0_Z, ""), (M.JOINT_Z, "Stoß"), (M.JOINT_SCREW_Z, "T2"), (M.FLANGE_Z[1], ""), (M.PISTON_Z[0], ""),
                (M.CHUTE_Z[0], ""), (M.CHUTE_Z[1], ""), (M.NOSE_SHOULDER_Z[0], ""), (M.SHEAR_PIN_Z, "T3"), (M.TOP_Z, ""),
                (M.TOP_Z + P.NOSE_L, "")]
    for i, (z, lab) in enumerate(stations):
        x, y = v.P(z, -R)
        yy = y - 6 - (i % 3) * 4.2
        sh.ax.plot([x, x], [y, yy + 2], lw=0.25, c="#888")
        sh.ax.text(x, yy, fmt(z), fontsize=5.2, ha="center", va="top", color=C_DIM)
        if lab:
            sh.ax.text(x, v.P(z, R)[1] + 2.5, lab, fontsize=6, ha="center", color="#a33", weight="bold")
    # Modulbänder
    mods = [("M1 Antrieb", 0, P.TVC_RING_Z + P.OUTER_H + 8), ("M2 Unterteil (Rohr 200, Schlüsselring, Kuppler geklebt)", M.TUBE_BOTTOM_Z, M.COUPLER_Z[1]),
            ("M3 Avionik-Schlitten", M.DISC_Z[0], M.FLANGE_Z[1]), ("M4 Oberteil (Rohr 500) mit Kolben und Schirm", M.JOINT_Z, M.TOP_Z),
            ("M5 Spitze", M.NOSE_SHOULDER_Z[0], M.TOP_Z + P.NOSE_L)]
    cols = ["#d35400", "#7f8c8d", "#2471a3", "#b7950b", "#7d3c98"]
    for i, (nm, a, b) in enumerate(mods):
        y = 150 + R * s + 12 + i * 5.0
        x0, x1 = v.P(a, 0)[0], v.P(b, 0)[0]
        sh.ax.add_patch(Rectangle((x0, y), x1 - x0, 3.2, fc=cols[i], ec="none", alpha=0.85))
        sh.ax.text(x0 + 1, y + 1.6, nm, fontsize=5.6, va="center", color="white", weight="bold")
    # Legende der Trennstellen
    rows = [["Trennstelle", "Wo", "Wie", "Lösen für"],
            ["T1", f"z {fmt(M.TVC_SCREW_Z)}, Kardanflansch", "3 × M3 × 6 radial in Einschmelzmuttern", "Kardan/Servo tauschen (nach unten)"],
            ["T2", f"z {fmt(M.JOINT_SCREW_Z)}, Rohrstoß", "3 × M3 × 6 durch Rohr oben + Kuppler in den Spant", "Oberteil ab, Schlitten heraus"],
            ["T3", f"z {fmt(M.SHEAR_PIN_Z)}, Spitze", "2 × M2-Nylon als Abscherstifte", "trennt beim Ausstoß"],
            ["T4", "Platine, Stirnseiten", "Stecker J5, J6, J1, J4, J9, J10", "Kabel Schlitten ↔ Rumpf/Kardan/Zünder"],
            ["T5", "Spant, oben", "2 Zünder-Klemmen M2, Ringschraube M4", "Zünder und Schockschnur je Flug"]]
    sh.table(12, 100, rows, [20, 46, 70, 52], row_h=4.4)
    sh.text(12, 103, "Trennstellen", fontsize=8, weight="bold")
    v2 = sh.view(255, 76, 0.42)
    # Querschnitt im Avionik-Kuppler (Blick von oben, +z), zeigt Platine, Träger, Luken
    v2.circle(0, 0, M.TUBE_OD); v2.circle(0, 0, M.TUBE_ID, lw=0.3)
    v2.circle(0, 0, P.COUPLER_OD, lw=0.3); v2.circle(0, 0, P.COUPLER_ID, lw=0.5)
    v2.rect(-M.BOARD_W / 2, -M.BOARD_T / 2, M.BOARD_W / 2, M.BOARD_T / 2, fill="#2e7d4f", lw=0.3)
    v2.rect(-8.9, M.BOARD_T / 2, 8.9, 13.5, fill="#3c9a62", lw=0.3)
    v2.rect(-M.BOARD_W / 2, M.TRAY_FLOOR_Y, M.BOARD_W / 2, -M.BOARD_T / 2, lw=0.4, c="#2471a3")
    v2.rect(-M.BAT2S["w"] / 2, M.TRAY_FLOOR_Y + 1.9, M.BAT2S["w"] / 2, M.TRAY_FLOOR_Y + 1.9 + M.BAT2S["h"], fill="#e9c46a", lw=0.3)
    v2.rect(-M.PANEL_W / 2, M.PANEL_Y[0], M.PANEL_W / 2, M.PANEL_Y[1], fill="#6d8fc7", lw=0.3)
    for nm, phi, w in (("Luke A", 90, M.HATCH_W), ("Luke B", 270, M.HATCH_B["w"])):
        a = math.degrees(w / 2 / (M.TUBE_OD / 2))
        for dd in (-a, a):
            v2.line([(35 * math.cos(math.radians(phi + dd)), 35 * math.sin(math.radians(phi + dd))),
                     (41 * math.cos(math.radians(phi + dd)), 41 * math.sin(math.radians(phi + dd)))], c=C_CUT, lw=0.8)
        v2.text(46 * math.cos(math.radians(phi)), 46 * math.sin(math.radians(phi)), nm, ha="center", va="center", color=C_CUT)
    for phi in (0, 90, 180, 270):
        v2.text(52 * math.cos(math.radians(phi)), 52 * math.sin(math.radians(phi)) - 2, deg(phi), ha="center", fontsize=5.5, color="#555")
    v2.text(44, 2, "Schlüssel\n(z 116)", fontsize=5, color="#555")
    v2.text(-60, -66, "Schnitt bei z ≈ 190, Blick von der Spitze\n+x = 0° (Längslinie), +y = 90° (Bestückungsseite)", fontsize=5.6)
    sh.save(pdf, "Z1_uebersicht.png")


# --------------------------------------------------------------------------- Z2–Z4 Abwicklungen
def z2(pdf):
    C, L = M.CIRC_TUBE, M.LOWER_L
    sh = Sheet("Z2", "Rohr unten 75 × 200: Abwicklung, Bohrungen, Fenster", "1:1,6",
               "Abwicklung von außen gesehen, Unterkante (Düsenseite) unten. Bogen = Abstand ab der Naht bei 330° entlang des Umfangs "
               f"(Umfang {fmt(C)}); die Längslinie 0° liegt {fmt(sx(0, C))} rechts der Naht. Bohren mit den 1:1-Schablonen S1/S2. Fenster und "
               "Barometer-Bohrungen erst NACH dem Einkleben des Kupplers durch beide Wände schneiden/bohren.")
    v = sh.view(24, 50, 1 / 1.6)
    zones = [(zl(P.TVC_RING_Z), zl(P.TVC_RING_Z + P.OUTER_FLANGE_H), "Kardanflansch"),
             (zl(M.KEY_RING_Z[0]), zl(M.KEY_RING_Z[1]), "Schlüsselring"),
             (zl(M.COUPLER_Z[0]), L, f"Kuppler ({fmt(M.COUPLER_GLUE)} geklebt)")]
    feats = lower_features()
    draw_development(v, C, L, feats, "Rohr unten, Abwicklung von außen", zones=zones)
    v.dim((C, 0), (C, L), -34, fmt(L))
    v.dim((0, 0), (C, 0), -9, f"Umfang {fmt(C)}")
    v.dim((0, L), (sx(0, C), L), 12, fmt(sx(0, C)))
    for kind, phi, h0, h1, d, txt in feats:
        if kind == "hole" and txt != "Baro":
            v.dim((sx(phi, C) + 5, 0), (sx(phi, C) + 5, h0), -2, fmt(h0), fs=5.2)
    sh.table(206, 192, feature_table(feats, C), [6, 21, 10, 18, 14, 12], row_h=4.0, fs=5.2)
    sh.save(pdf, "Z2_rohr_unten.png")


def z3(pdf):
    C, L = M.CIRC_TUBE, M.UPPER_L
    sh = Sheet("Z3", "Rohr oben 75 × 500: Abwicklung, Bohrungen, Kerbe", "1:3,3 (Detail 1:1,25)",
               "Unterkante = Rohrstoß (steckt auf dem Avionik-Kuppler). Stoßschrauben und Kerbe A2 mit Schablone S3 bei aufgestecktem Rohr durch "
               "Rohr und Kuppler bohren. Abscherstifte mit S4 bei eingesetzter Spitze durch Rohr und Schulter bohren (Ø 2, die M2-Nylonschraube "
               "schneidet ihr Gewinde selbst).")
    v = sh.view(40, 38, 1 / 3.3)
    zones = [(0, M.COUPLER_FREE, "Kuppler"), (zu(M.PISTON_Z[0]), zu(M.PISTON_Z[1]), "Kolben"),
             (zu(M.CHUTE_Z[0]), zu(M.CHUTE_Z[1]), "Fallschirm"), (zu(M.NOSE_SHOULDER_Z[0]), L, "Schulter Spitze")]
    feats = upper_features()
    draw_development(v, C, L, feats, "Rohr oben, Abwicklung", zones=zones, guides=False)
    v.dim((0, 0), (0, L), 9, fmt(L))
    sh.table(150, 192, feature_table(feats, C), [6, 28, 10, 20, 16, 15], row_h=4.2, fs=5.6)
    sc = 1 / 1.25
    vd = sh.view(150, 85, sc)
    W = sx(140, C)
    vd.rect(0, 0, W, 66, lw=0.5)
    vd.text(0, 74, "Detail Stoß, Naht (330°) bis 140°, 1:1,25", fontsize=6.5, weight="bold")
    for k in (0, 45, 90, 135):
        vd.line([(sx(k, C), 0), (sx(k, C), 66)], lw=0.25, c="#bbb", ls=(0, (3, 3)))
        vd.text(sx(k, C), 67.5, deg(k), ha="center", fontsize=5.5, color="#555")
    vd.line([(sx(0, C), 0), (sx(0, C), 66)], lw=1.0, c="#2a7")
    for kind, phi, h0, h1, d, txt in feats:
        x = sx(phi, C)
        if x > W:
            continue
        if kind == "hole" and h0 < 66:
            vd.hole(x, h0, d, label=f"Ø{fmt(d)}")
            vd.dim((x + 4, 0), (x + 4, h0), -2, fmt(h0))
        elif kind == "win":
            vd.rect(x - d / 2, 0, x + d / 2, h1, c=C_CUT, fill="#fbe3cf", hatch="////")
            vd.dim((x - d / 2, h1), (x + d / 2, h1), 3, fmt(d))
            vd.dim((x + d / 2, 0), (x + d / 2, h1), -5, fmt(h1))
    vd.dim((sx(0, C), 0), (sx(90, C), 0), -5, f"{fmt(sx(90, C) - sx(0, C))} (0° bis 90°)")
    vd.dim((sx(0, C), 0), (sx(135, C), 0), -11, f"{fmt(sx(135, C) - sx(0, C))} (0° bis 135°)")
    sh.save(pdf, "Z3_rohr_oben.png")


def z4(pdf):
    C, L = M.CIRC_COUPLER, P.COUPLER_L
    sh = Sheet("Z4", "Avionik-Kuppler 72,4 × 150: Abwicklung", "1:1,25",
               f"Unten {fmt(M.COUPLER_GLUE)} mm im unteren Rohr verklebt (Epoxid), oben {fmt(M.COUPLER_FREE)} mm frei für das obere Rohr. "
               "Alle Öffnungen entstehen beim Bohren/Schneiden durch das Rohr hindurch, diese Zeichnung dient der Kontrolle. "
               f"Oberkante = Auflage des Spant-Flanschs (Moosgummi-Dichtring). Umfang {fmt(C)}.")
    v = sh.view(24, 60, 1 / 1.4)
    zones = [(0, M.COUPLER_GLUE, "im Rohr unten verklebt"), (M.COUPLER_GLUE, L, "Rohr oben steckt")]
    feats = coupler_features()
    draw_development(v, C, L, feats, "Avionik-Kuppler, Abwicklung", zones=zones, guides=False)
    v.dim((0, M.COUPLER_GLUE), (0, 0), 6, fmt(M.COUPLER_GLUE))
    v.dim((0, L), (0, M.COUPLER_GLUE), 6, fmt(M.COUPLER_FREE))
    v.dim((0, 0), (C, 0), -9, f"Umfang {fmt(C)}")
    sh.table(206, 192, feature_table(feats, C), [6, 19, 10, 18, 15, 13], row_h=4.0, fs=5.2)
    sh.save(pdf, "Z4_kuppler.png")


# --------------------------------------------------------------------------- Z5 Avionik-Schlitten
def z5(pdf):
    sh = Sheet("Z5", "Avionik-Schlitten mit Ausstoßspant (Druckteil)", "1:1,25",
               "Ein Druckteil, stehend gedruckt (Flansch auf dem Bett), PETG, 3 Wände, 25 % Gyroid. Bezugsebene A = Unterseite des Flanschs "
               "(liegt auf der Kupplerkante). Einschmelzmuttern M3 kurz (Ø 4,0 × 5 vorgebohrt) in: 3 Schraubenaugen (radial), "
               "4 Platinensäulen, 2 Stirnaugen (untere Scheibe). Platine rev B1 mit 4 × M3 × 6 von oben.")
    s = 1 / 1.25
    A = M.FLANGE_Z[0]
    # Ansicht 1: von +y (Bestückungsseite), x = u, y = z - A (nach unten negativ)
    v = sh.view(62, 170, s)
    def zz(z):
        return z - A
    bw = M.BOARD_W / 2
    v.rect(-M.FLANGE_OD / 2, zz(M.FLANGE_Z[0]), M.FLANGE_OD / 2, zz(M.FLANGE_Z[1]), fill="#cfdcf0")
    v.rect(-M.SPIGOT_OD / 2, zz(M.SPIGOT_Z[0]), M.SPIGOT_OD / 2, zz(M.SPIGOT_Z[1]), fill="#dfe8f5")
    v.rect(-bw, zz(M.DISC_Z[1]), bw, zz(M.SPIGOT_Z[0]), lw=0.5, c="#2471a3")
    v.rect(-bw, zz(M.BOARD_V0_Z), bw, zz(M.BOARD_V0_Z + M.BOARD_L), lw=0.5, c="#2e7d4f", ls=(0, (4, 2)))
    v.rect(-M.DISC_OD / 2, zz(M.DISC_Z[0]), M.DISC_OD / 2, zz(M.DISC_Z[1]), fill="#cfdcf0")
    t = P.TEENSY
    v.rect(t["u0"], zz(M.BOARD_V0_Z + t["v0"]), t["u1"], zz(M.BOARD_V0_Z + t["v1"]), lw=0.4, c="#2e7d4f", ls=(0, (2, 2)))
    v.text(0, zz(M.BOARD_V0_Z + 60), "Teensy", ha="center", fontsize=5.5, color="#2e7d4f", rotation=90)
    for (u, vv) in M.BOARD_HOLES:
        v.hole(u, zz(M.BOARD_V0_Z + vv), M.INSERT_HOLE[0])
    v.hole(0, zz(M.JOINT_SCREW_Z), M.INSERT_HOLE[0], label="Auge 0°")
    v.center([(0, zz(M.DISC_Z[0]) - 6), (0, zz(M.FLANGE_Z[1]) + 6)])
    v.dim((-M.FLANGE_OD / 2, zz(M.FLANGE_Z[1])), (M.FLANGE_OD / 2, zz(M.FLANGE_Z[1])), 5, f"Ø {fmt(M.FLANGE_OD)}")
    v.dim((-M.SPIGOT_OD / 2, zz(M.SPIGOT_Z[0])), (M.SPIGOT_OD / 2, zz(M.SPIGOT_Z[0])), -4, f"Ø {fmt(M.SPIGOT_OD)}")
    v.dim((-M.DISC_OD / 2, zz(M.DISC_Z[0])), (M.DISC_OD / 2, zz(M.DISC_Z[0])), -5, f"Ø {fmt(M.DISC_OD)} (Scheibe)")
    xr = M.FLANGE_OD / 2
    v.dim((xr, 0), (xr, zz(M.FLANGE_Z[1])), -5, fmt(M.FLANGE_Z[1] - M.FLANGE_Z[0]))
    v.dim((xr, zz(M.SPIGOT_Z[0])), (xr, 0), -6, fmt(A - M.SPIGOT_Z[0]))
    v.dim((xr, zz(M.JOINT_SCREW_Z)), (xr, 0), -12, fmt(A - M.JOINT_SCREW_Z))
    v.dim((xr, zz(M.BOARD_V0_Z + M.BOARD_L)), (xr, 0), -18, fmt(A - M.BOARD_V0_Z - M.BOARD_L))
    v.dim((xr, zz(M.BOARD_V0_Z)), (xr, 0), -24, fmt(A - M.BOARD_V0_Z))
    v.dim((xr, zz(M.DISC_Z[0])), (xr, 0), -30, fmt(A - M.DISC_Z[0]))
    v.dim((-bw, zz(M.BOARD_V0_Z)), (bw, zz(M.BOARD_V0_Z)), -12, f"{fmt(M.BOARD_W)} (Platine)")
    u0, v0 = M.BOARD_HOLES[0]
    v.dim((M.BOARD_HOLES[0][0], zz(M.BOARD_V0_Z + v0)), (M.BOARD_HOLES[1][0], zz(M.BOARD_V0_Z + v0)), 6, fmt(2 * abs(u0)))
    v.dim((-bw, zz(M.BOARD_V0_Z + M.BOARD_HOLES[2][1])), (-bw, zz(M.BOARD_V0_Z + M.BOARD_HOLES[0][1])), -5,
          fmt(M.BOARD_HOLES[2][1] - M.BOARD_HOLES[0][1]))
    v.text(-M.FLANGE_OD / 2, 9, "A", fontsize=8, weight="bold", color="#a33")
    v.text(-M.FLANGE_OD / 2, 16, "Ansicht von +y (Bestückungsseite)", fontsize=6.5, weight="bold")
    # Ansicht 2: von +x (Seite), x = y-Koordinate
    v2 = sh.view(172, 170, s)
    v2.rect(-M.FLANGE_OD / 2, zz(M.FLANGE_Z[0]), M.FLANGE_OD / 2, zz(M.FLANGE_Z[1]), fill="#cfdcf0")
    v2.rect(-M.SPIGOT_OD / 2, zz(M.SPIGOT_Z[0]), M.SPIGOT_OD / 2, zz(M.SPIGOT_Z[1]), fill="#dfe8f5")
    v2.rect(-M.DISC_OD / 2, zz(M.DISC_Z[0]), M.DISC_OD / 2, zz(M.DISC_Z[1]), fill="#cfdcf0")
    v2.rect(-M.BOARD_T / 2, zz(M.BOARD_V0_Z), M.BOARD_T / 2, zz(M.BOARD_V0_Z + M.BOARD_L), fill="#2e7d4f", lw=0.3)
    v2.rect(M.TRAY_FLOOR_Y, zz(M.DISC_Z[1]), -M.BOARD_T / 2, zz(M.SPIGOT_Z[0]), lw=0.5, c="#2471a3")
    for nm, bat in (("2S", M.BAT2S), ("1S", M.BAT1S)):
        y0 = M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3
        v2.rect(y0, zz(M.BOARD_V0_Z + bat["v0"]), y0 + bat["h"], zz(M.BOARD_V0_Z + bat["v0"] + bat["l"]), fill="#e9c46a", lw=0.3)
        v2.text(y0 + bat["h"] / 2, zz(M.BOARD_V0_Z + bat["v0"] + bat["l"] / 2), nm, ha="center", va="center", fontsize=5.5, rotation=90)
    va, vb = M.HATCH_B["v"]
    v2.rect(M.PANEL_Y[0], zz(M.BOARD_V0_Z + va + 1), M.PANEL_Y[1], zz(M.BOARD_V0_Z + vb - 1), fill="#6d8fc7", lw=0.3)
    for (cu, cv) in M.PANEL_COLS:
        v2.rect(M.PANEL_Y[1], zz(M.BOARD_V0_Z + cv) - 3.5, M.TRAY_FLOOR_Y, zz(M.BOARD_V0_Z + cv) + 3.5, fill="#6d8fc7", lw=0.3)
    v2.rect(-8.9 * 0 + M.BOARD_T / 2, zz(M.BOARD_V0_Z + t["v0"]), 13.5, zz(M.BOARD_V0_Z + t["v1"]), lw=0.3, c="#2e7d4f")
    v2.dim((M.TRAY_FLOOR_Y, zz(M.DISC_Z[1]) - 2), (-M.BOARD_T / 2, zz(M.DISC_Z[1]) - 2), -4, fmt(abs(M.TRAY_FLOOR_Y) - M.BOARD_T / 2))
    v2.dim((M.PANEL_Y[0], zz(M.BOARD_V0_Z + va + 1)), (M.PANEL_Y[0], zz(M.BOARD_V0_Z + vb - 1)), 5, f"Schalterbrett {fmt(vb - va - 2)}")
    v2.text(-M.FLANGE_OD / 2, 16, "Ansicht von +x (Luke B links, Luke A rechts)", fontsize=6.5, weight="bold")
    # Ansicht 3: Draufsicht auf den Spant (von +z)
    v3 = sh.view(250, 105, 0.72)
    v3.circle(0, 0, M.FLANGE_OD, fill="#cfdcf0"); v3.circle(0, 0, M.SPIGOT_OD, lw=0.3, ls=(0, (3, 2)))
    v3.circle(0, 0, M.SPIGOT_ID, lw=0.3, ls=(0, (3, 2)))
    cc = M.CHARGE_CUP
    v3.circle(cc["x"], cc["y"], cc["d"] + 6); v3.circle(cc["x"], cc["y"], cc["d"])
    v3.leader((cc["x"] + 6, cc["y"] + 3), (2, 30), f"Ladungsbecher Ø {fmt(cc['d'])} × {fmt(cc['h'])}")
    for (x, y) in M.FEEDTHRU:
        v3.hole(x, y, M.FEEDTHRU_D)
    v3.leader(M.FEEDTHRU[0], (-12, 24), "Zünder-Klemmen 2 × M2 Messing")
    v3.hole(M.EYE_BOLT["x"], M.EYE_BOLT["y"], M.EYE_BOLT["d"])
    v3.leader((M.EYE_BOLT["x"], M.EYE_BOLT["y"]), (-22, -14), "Ringschraube M4 (Ø 4,3)")
    for phi in M.SCREW_PHI:
        x, y = (M.SPIGOT_OD / 2 - 2) * math.cos(math.radians(phi)), (M.SPIGOT_OD / 2 - 2) * math.sin(math.radians(phi))
        v3.hole(x, y, 2.0, c="#2471a3")
        v3.text(x * 1.32, y * 1.32, deg(phi), ha="center", va="center", fontsize=5.5, color="#2471a3")
    v3.rect(-M.BOARD_W / 2, -M.BOARD_T / 2, M.BOARD_W / 2, M.BOARD_T / 2, lw=0.3, c="#2e7d4f", ls=(0, (3, 2)))
    v3.center([(-42, 0), (42, 0)]); v3.center([(0, -42), (0, 42)])
    v3.dim((M.FEEDTHRU[0][0], M.FEEDTHRU[0][1]), (M.FEEDTHRU[1][0], M.FEEDTHRU[1][1]), 4, fmt(M.FEEDTHRU[1][0] - M.FEEDTHRU[0][0]))
    v3.dim((0, 0), (0, cc["y"]), -26, fmt(cc["y"]))
    v3.dim((0, 0), (0, M.FEEDTHRU[0][1]), -34, fmt(M.FEEDTHRU[0][1]))
    v3.dim((0, 0), (0, M.EYE_BOLT["y"]), -26, fmt(abs(M.EYE_BOLT["y"])))
    v3.text(-40, -46, "Draufsicht Spant (von der Spitze)\nAugen mit Einschmelzmutter bei 0°/135°/225°,\nBohrung radial in Höhe A − "
            f"{fmt(A - M.JOINT_SCREW_Z)}", fontsize=6)
    sh.save(pdf, "Z5_schlitten.png")


# --------------------------------------------------------------------------- Z6 Kleinteile
def z6(pdf):
    sh = Sheet("Z6", "Untere Scheibe, Schalterbrett, Kolbenplatte, Ladungsbecher", "1:1",
               "PETG (Kolbenplatte und Becher besser ASA: sie sehen die Ausstoßgase). Die Scheibe zentriert das untere Ende des Schlittens im "
               "Kuppler; durch ihr Fenster stecken die Stecker J5/J6/J1, durch das Rundloch laufen die Kabel. Nach dem Einbau beides mit "
               "Schaumstoff stopfen (Barometer-Raum dicht gegen den Kardanraum).")
    # Untere Scheibe
    v = sh.view(55, 130, 1.0)
    v.circle(0, 0, M.DISC_OD, fill="#cfdcf0")
    v.circle(0, -4, M.DISC_CABLE_D, fill="white")
    x0, x1, y0, y1 = M.DISC_PLUG_WINDOW
    v.rect(x0, y0, x1, y1, fill="white")
    for (x, y) in M.TRAY_TO_DISC:
        v.hole(x, y, 3.4)
    for a in M.DISC_LIGHT_PHI:
        v.circle(M.DISC_LIGHT_R * math.cos(math.radians(a)), M.DISC_LIGHT_R * math.sin(math.radians(a)), M.DISC_LIGHT_D, fill="white", lw=0.4)
    v.center([(-40, 0), (40, 0)]); v.center([(0, -40), (0, 40)])
    v.dim((-M.DISC_OD / 2, 0), (M.DISC_OD / 2, 0), 40, f"Ø {fmt(M.DISC_OD)}")
    v.dim((x0, y1), (x1, y1), 4, fmt(x1 - x0)); v.dim((x1, y0), (x1, y1), -4, fmt(y1 - y0))
    v.dim((M.TRAY_TO_DISC[0][0], M.TRAY_TO_DISC[0][1]), (M.TRAY_TO_DISC[1][0], M.TRAY_TO_DISC[1][1]), -12, f"{fmt(2 * abs(M.TRAY_TO_DISC[0][0]))} (2 × Ø 3,4)")
    v.leader((0, -4 - M.DISC_CABLE_D / 2 + 1), (-8, -22), f"Kabelloch Ø {fmt(M.DISC_CABLE_D)}")
    v.text(-36, 48, f"Untere Scheibe, {fmt(M.DISC_Z[1] - M.DISC_Z[0])} dick (Blick von oben)", fontsize=7, weight="bold")
    # Schalterbrett (v ab Brettunterkante)
    va, vb = M.HATCH_B["v"]
    b0 = va + 1
    v2 = sh.view(128, 125, 1.5)
    v2.rect(-M.PANEL_W / 2, 0, M.PANEL_W / 2, vb - 1 - b0, fill="#cfdcf0")
    for name, u, a, b, w in M.PANEL_PARTS:
        v2.rect(u - w / 2 - 0.2, a - b0, u + w / 2 + 0.2, b - b0, fill="white", lw=0.5)
    for (cu, cv) in M.PANEL_COLS:
        v2.circle(cu, cv - b0, M.PANEL_COL_D, lw=0.4, ls=(0, (2, 1)))
    v2.dim((-M.PANEL_W / 2, vb - 1 - b0), (M.PANEL_W / 2, vb - 1 - b0), 4, fmt(M.PANEL_W))
    v2.dim((M.PANEL_W / 2, 0), (M.PANEL_W / 2, vb - 1 - b0), -5, fmt(vb - va - 2))
    v2.text(-M.PANEL_W / 2 - 10, vb - b0 + 8, "Schalterbrett (Luke B), Blick von außen", fontsize=6.5, weight="bold")
    rows = [["Ausbruch", "u-Mitte", "v von … bis", "Breite"]]
    for name, u, a, b, w in M.PANEL_PARTS:
        rows.append([name, fmt(u), f"{fmt(a - b0)} … {fmt(b - b0)}", fmt(w + 0.4)])
    rows.append(["2 Säulen Ø 7 (M3 von innen)", " / ".join(fmt(cu) for cu, _ in M.PANEL_COLS),
                 " / ".join(fmt(cv - b0) for _, cv in M.PANEL_COLS), "–"])
    sh.table(100, 108, rows, [42, 13, 20, 12], row_h=4.0, fs=5.4)
    sh.text(100, 110, "v ab Brettunterkante (TVC-Seite), u ab Brettmitte", fontsize=5.6)
    # Kolbenplatte
    v3 = sh.view(208, 165, 1.0)
    D = P.COUPLER_ID - 0.2
    v3.rect(-D / 2, 0, D / 2, 3.0, fill="#cfdcf0")
    v3.rect(-D / 2, 3.0, -D / 2 + 1.6, 8.0, fill="#cfdcf0"); v3.rect(D / 2 - 1.6, 3.0, D / 2, 8.0, fill="#cfdcf0")
    v3.rect(-3, -0.2, 3, 3.2, fill="white", lw=0.4)
    v3.dim((-D / 2, 0), (D / 2, 0), -5, f"Ø {fmt(D)}")
    v3.dim((D / 2, 0), (D / 2, 8), -5, "8")
    v3.dim((D / 2, 0), (D / 2, 3), 5, "3")
    v3.dim((-3, 3.2), (3, 3.2), 9, "Ø 6")
    v3.text(-D / 2, 16, "Kolbenplatte (Schnitt), in Kuppler-Stück 40 geklebt\nKragen 1,6 Wand; Schnur läuft mittig durch", fontsize=6.5, weight="bold")
    # Kolben-Kuppler
    v3b = sh.view(208, 110, 0.6)
    v3b.rect(-P.COUPLER_OD / 2, 0, P.COUPLER_OD / 2, P.PISTON_L, lw=0.5)
    v3b.dim((P.COUPLER_OD / 2, 0), (P.COUPLER_OD / 2, P.PISTON_L), -5, fmt(P.PISTON_L))
    v3b.text(-P.COUPLER_OD / 2, P.PISTON_L + 6, "Kuppler-Stück 72,4 × 40 (vom 2. Klima-Kuppler)", fontsize=6.2)
    # Ladungsbecher
    v4 = sh.view(265, 165, 2.0)
    cc = M.CHARGE_CUP
    v4.rect(-cc["d"] / 2, 0, cc["d"] / 2, 1.2, fill="#cfdcf0")
    v4.rect(-cc["d"] / 2, 1.2, -cc["d"] / 2 + 1.2, cc["h"], fill="#cfdcf0"); v4.rect(cc["d"] / 2 - 1.2, 1.2, cc["d"] / 2, cc["h"], fill="#cfdcf0")
    v4.dim((-cc["d"] / 2, 0), (cc["d"] / 2, 0), -5, f"Ø {fmt(cc['d'])}")
    v4.dim((cc["d"] / 2, 0), (cc["d"] / 2, cc["h"]), -5, fmt(cc["h"]))
    v4.text(-cc["d"] / 2 - 6, cc["h"] + 7, "Ladungsbecher\n(steckt im Sockel)", fontsize=6.5, weight="bold")
    sh.save(pdf, "Z6_kleinteile.png")


# --------------------------------------------------------------------------- Z7 Schlüsselring und Kardanflansch
def z7(pdf):
    sh = Sheet("Z7", "Schlüsselring mit Kabelgitter, Lochbild Kardanflansch", "1:1",
               "Schlüsselring: dünnwandig, im unteren Rohr verklebt (Unterkante h = "
               f"{fmt(zl(M.KEY_RING_Z[0]))} ab Rohrunterkante). Vor dem Kleben den Schlüsselschalter von außen durch Rohr und Ring stecken, "
               "Mutter in die Tasche: der Schalter selbst richtet den Ring aus. Kardan-Außenrahmen: die 4 alten Ø-3,2-Bohrungen bei 45° entfallen, "
               "dafür 3 Einschmelzmuttern bei 0°/135°/225° (Bohrung Ø 4,0 × 5).")
    v = sh.view(70, 115, 1.15)
    ro = M.KEY_RING_OD / 2
    v.circle(0, 0, M.KEY_RING_OD, fill="#dfe8f5"); v.circle(0, 0, M.KEY_RING_OD - 2 * M.KEY_RING_WALL, fill="#f6f9fd")
    for k in range(8):
        a = 22.5 + 45 * k
        v.circle(15 * math.cos(math.radians(a)), 15 * math.sin(math.radians(a)), 10.0, fill="white", lw=0.4)
    bw, bd = M.KEY_BOSS
    for k in range(12):
        a = 15 + 30 * k
        x, y = 27 * math.cos(math.radians(a)), 27 * math.sin(math.radians(a))
        if not (x + 3.5 > ro - bd and abs(y) - 3.5 < bw / 2):
            v.circle(x, y, 7.0, fill="white", lw=0.4)
    v.rect(ro - bd, -bw / 2, ro - 0.3, bw / 2, fill="#cfdcf0")
    v.rect(ro - bd - 0.5, -M.KEY_HOLE_D / 2, ro + 2, M.KEY_HOLE_D / 2, fill="white", lw=0.5, c=C_HOLE)
    sw, nh = M.KEY_NUT
    r_nut = ro - bd + 3.0
    v.rect(r_nut - nh / 2, -sw / 2, r_nut + nh / 2, sw / 2, lw=0.5, ls=(0, (2, 1)))
    for phi in (90, 270):
        a = math.degrees(6.0 / (ro - 4))
        v.rect(-6, ro - 9 if phi == 90 else -ro + M.KEY_RING_WALL, 6, ro - M.KEY_RING_WALL if phi == 90 else -ro + 9, fill="white", lw=0.5, c=C_CUT)
        v.text(0, (ro + 4) * (1 if phi == 90 else -1), f"Servokabel {deg(phi)}", ha="center", va="center", fontsize=5.5, color=C_CUT)
    v.center([(-44, 0), (44, 0)]); v.center([(0, -44), (0, 44)])
    v.dim((-ro, 0), (ro, 0), 40, f"Ø {fmt(M.KEY_RING_OD)}")
    v.dim((ro - bd, bw / 2), (ro, bw / 2), 4, fmt(bd))
    v.dim((ro + 1, -M.KEY_HOLE_D / 2), (ro + 1, M.KEY_HOLE_D / 2), -6, f"Ø {fmt(M.KEY_HOLE_D)}")
    v.dim((r_nut - nh / 2, -sw / 2), (r_nut - nh / 2, sw / 2), 6, f"SW {fmt(sw)}")
    v.text(-ro, ro + 9, f"Schlüsselring, Blick von oben, Höhe {fmt(M.KEY_RING_Z[1] - M.KEY_RING_Z[0])}, Wand {fmt(M.KEY_RING_WALL)}, Gitter 1,6",
           fontsize=7, weight="bold")
    v.text(ro + 4, 4, "0°", fontsize=6)
    # Kardanflansch
    v2 = sh.view(205, 115, 1.15)
    v2.circle(0, 0, P.OUTER_RING_OD, fill="#dfe8f5"); v2.circle(0, 0, P.OUTER_RING_ID, fill="white")
    ro2 = P.OUTER_RING_OD / 2
    for phi in (45, 135, 225, 315):
        x, y = (ro2 - 3) * math.cos(math.radians(phi)), (ro2 - 3) * math.sin(math.radians(phi))
        v2.line([(x - 2, y - 2), (x + 2, y + 2)], c="#999", lw=0.5); v2.line([(x - 2, y + 2), (x + 2, y - 2)], c="#999", lw=0.5)
    for phi in M.SCREW_PHI:
        a = math.radians(phi)
        v2.rect(0, 0, 0, 0)
        p0 = ((ro2 - M.INSERT_HOLE[1]) * math.cos(a), (ro2 - M.INSERT_HOLE[1]) * math.sin(a))
        p1 = (ro2 * math.cos(a), ro2 * math.sin(a))
        v2.line([p0, p1], c=C_HOLE, lw=M.INSERT_HOLE[0] * 1.15 * 2.83)
        v2.text(1.18 * p1[0], 1.18 * p1[1], deg(phi), ha="center", va="center", fontsize=6, color=C_HOLE)
    v2.text(0, -ro2 + 7, "Servotasche (270°)", ha="center", fontsize=5.5)
    v2.text(0, ro2 - 9, "Lagerohr (90°)", ha="center", fontsize=5.5)
    v2.center([(-44, 0), (44, 0)]); v2.center([(0, -44), (0, 44)])
    v2.dim((-ro2, 0), (ro2, 0), 40, f"Ø {fmt(P.OUTER_RING_OD)}")
    v2.text(-ro2, ro2 + 9, f"Kardan-Außenrahmen, Flansch (Blick von oben), Bohrungen in Flanschmitte h = {fmt(P.OUTER_FLANGE_H / 2)}",
            fontsize=7, weight="bold")
    v2.text(-ro2, -ro2 - 10, "rot: neu, Einschmelzmutter M3 radial (Ø 4,0 × 5)\ngrau ×: alte Bohrungen bei 45° entfallen", fontsize=6)
    sh.save(pdf, "Z7_ring_kardan.png")


# --------------------------------------------------------------------------- Bohrschablonen 1:1
def template(pdf, nr, title, C, feats, h_range, ref, note):
    """Abwicklung im Maßstab 1:1. ref = 'unten' (Blattkante an der Rohrunterkante) oder 'oben' (an der Oberkante)."""
    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, A4[0]); ax.set_ylim(0, A4[1]); ax.set_aspect("equal"); ax.axis("off")
    h0, h1 = h_range
    H = h1 - h0
    x_off, y_off = 18.0, (A4[1] - H) / 2 - 6
    def P_(s, h):
        return x_off + s, y_off + (h - h0)
    # Streifen mit Klebelasche
    ax.add_patch(Rectangle(P_(0, h0), C, H, fill=False, lw=0.6, ec="#000"))
    ax.add_patch(Rectangle(P_(C, h0), 12, H, fill=True, fc="#eee", ec="#999", lw=0.4, hatch="..."))
    ax.text(*P_(C + 6, h0 + H / 2), "Klebelasche: unter den Streifenanfang (0°) legen", rotation=90, ha="center", va="center", fontsize=5.5)
    # Bezugskante
    ky = h0 if ref == "unten" else h1
    xa, ya = P_(0, ky); xb, _ = P_(C, ky)
    ax.plot([xa, xb], [ya, ya], lw=2.2, c="#c0392b")
    ax.text(xa, ya + (-4 if ref == "unten" else 7.5), f"Bezugskante = Rohr{'unter' if ref == 'unten' else 'ober'}kante: bündig anlegen",
            fontsize=6.5, color="#c0392b", va="bottom" if ref == "oben" else "top")
    # Winkelteilung ab der Naht bei 330°
    for k in range(0, 360, 15):
        x, _ = P_(sx(k, C), h0)
        major = k % 45 == 0
        ax.plot([x, x], [P_(0, h0)[1], P_(0, h1)[1]], lw=0.35 if major else 0.15, c="#666" if major else "#bbb", ls=(0, (3, 3)))
        if major:
            ax.text(x, P_(0, h1)[1] + 1.2, f"{k}°", ha="center", va="bottom", fontsize=6)
    ax.text(*P_(0, h1), "Naht\n330°", ha="center", va="bottom", fontsize=5, color="#777")
    xg, _ = P_(sx(0, C), h0)
    ax.plot([xg, xg], [P_(0, h0)[1], P_(0, h1)[1]], lw=1.4, c="#2a7")
    ax.text(xg + 1, P_(0, h1)[1] - 3, "Längslinie 0°\n(auf die Bleistiftlinie)", fontsize=5.5, color="#2a7", va="top")
    # Führungen
    half = math.degrees(math.atan(10.0 / (M.TUBE_OD / 2 + M.RAMP_GUIDE_GAP)))
    if "unten" in title.lower() and h0 < M.RAMP_GUIDE_H:
        for g in M.RAMP_GUIDE_PHI:
            a, b = sx(g - half, C), sx(g + half, C)
            top = min(M.RAMP_GUIDE_H, h1)
            ax.add_patch(Rectangle(P_(a, h0), b - a, top - h0, fc=C_WARN, ec="none", alpha=0.35))
            ax.text(*P_((a + b) / 2, (h0 + top) / 2), "Führung Startrampe: nichts hervorstehen lassen", rotation=90, ha="center",
                    va="center", fontsize=5, color="#a55")
    # Löcher und Fenster
    for kind, phi, a, b, d, txt in feats:
        s = sx(phi, C)
        if kind == "hole" and h0 <= a <= h1:
            x, y = P_(s, a)
            ax.add_patch(Circle((x, y), d / 2, fill=False, ec="#c0392b", lw=0.5))
            ax.plot([x - 6, x + 6], [y, y], lw=0.3, c="#c0392b"); ax.plot([x, x], [y - 6, y + 6], lw=0.3, c="#c0392b")
            ax.add_patch(Circle((x, y), 0.35, fc="#000"))
            ax.text(x + 2.5, y + 2.5, f"{txt}\nØ {fmt(d)}", fontsize=5.2, color="#c0392b")
        elif kind == "win":
            lo, hi = max(a, h0), min(b, h1)
            if hi > lo:
                ax.add_patch(Rectangle(P_(s - d / 2, lo), d, hi - lo, fill=True, fc="#fbe3cf", ec="#e67e22", lw=0.7, hatch="////"))
                ax.text(*P_(s, (lo + hi) / 2), f"{txt}\nausschneiden\n{fmt(d)} × {fmt(b - a)}", ha="center", va="center", fontsize=5.2,
                        color="#8a4a12", bbox=dict(fc="white", ec="none", pad=0.4))
    # Höhenmaßstab links
    for h in range(int(math.ceil(h0 / 10) * 10), int(h1) + 1, 10):
        x, y = P_(0, h)
        ax.plot([x - 3, x], [y, y], lw=0.3, c="#000")
        ax.text(x - 3.5, y, str(h), fontsize=4.8, ha="right", va="center")
    # Prüfmaß
    ax.plot([20, 120], [12, 12], lw=1.0, c="#000")
    for x in (20, 120):
        ax.plot([x, x], [10, 14], lw=1.0, c="#000")
    ax.text(70, 14.5, "Prüfmaß 100 mm: nach dem Druck nachmessen", ha="center", fontsize=6)
    ax.text(130, 15.5, f"{nr}  {title}", fontsize=7.5, va="bottom", weight="bold")
    ax.text(130, 9.5, f"A4 quer drucken, „Tatsächliche Größe / 100 %“, nicht „An Seite anpassen“. Umfang {fmt(C)} mm.",
            fontsize=6.2, va="bottom")
    ax.text(18, A4[1] - 8, "\n".join(textwrap.wrap(note, 160)), fontsize=6.2, va="top", linespacing=1.3)
    pdf.savefig(fig)
    fig.savefig(IMG / f"{nr}_schablone.png", dpi=110)
    plt.close(fig)


def templates():
    out = HERE / "Bohrschablonen_1zu1.pdf"
    lf, uf = lower_features(), upper_features()
    with PdfPages(out) as pdf:
        template(pdf, "S1", "Rohr unten, Unterkante (Kardan, Schlüsselschalter)", M.CIRC_TUBE, lf, (0.0, 120.0), "unten",
                 "Streifen ausschneiden, um das untere Rohr legen (Bezugskante bündig an der Unterkante, 0° auf der Längslinie), mit Klebeband fixieren. "
                 "Mitten mit Vorstecher durchstechen, dann Ø 2 vor- und auf Endmaß bohren. Schalterloch mit Stufenbohrer. Bohrränder mit dünnem Sekundenkleber härten.")
        template(pdf, "S2", "Rohr unten, Oberkante (Luken A1 und B, Barometer)", M.CIRC_TUBE, lf, (115.0, 200.0), "oben",
                 "ERST NACH dem Einkleben des Kupplers verwenden: Bezugskante an die Stufe Rohr/Kuppler. Fenster mit Cutter durch Rohr UND Kuppler schneiden "
                 "(mehrere Züge, Stahllineal), das ausgeschnittene Stück als Deckel aufheben. Barometer-Löcher Ø 2 durch beide Wände.")
        template(pdf, "S3", "Rohr oben, Unterkante (Stoßschrauben, Kerbe A2)", M.CIRC_TUBE, uf, (0.0, 70.0), "unten",
                 "Oberes Rohr auf den Kuppler stecken, Längslinien beider Rohre fluchten lassen. Bezugskante an die Unterkante des oberen Rohrs. Stoßschrauben "
                 "Ø 3,4 durch Rohr und Kuppler bohren; Kerbe A2 im Rohr ausschneiden, das Fenster dahinter im Kuppler gleich mit.")
        template(pdf, "S4", "Rohr oben, Oberkante (Abscherstifte der Spitze)", M.CIRC_TUBE, uf, (440.0, 500.0), "oben",
                 "Spitze einsetzen. Bezugskante an die Oberkante des oberen Rohrs. Ø 2 durch Rohr und Schulter der Spitze; M2-Nylonschraube schneidet ihr Gewinde "
                 "selbst. Abscherstifte nur einsetzen, wenn der Bodentest zeigt, dass die Ladung sie sicher abschert.")
    return out


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    out = HERE / "Zeichnungen_Kartonaut1.pdf"
    with PdfPages(out) as pdf:
        for f in (z1, z2, z3, z4, z5, z6, z7):
            f(pdf)
    t = templates()
    print("wrote", out.relative_to(ROOT), "and", t.relative_to(ROOT))


if __name__ == "__main__":
    main()
