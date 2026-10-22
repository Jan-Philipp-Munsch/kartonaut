"""Technische Zeichnungen und 1:1-Bohrschablonen für die Modulbauweise von Kartonaut 1 (Erstflug).

    python docs/bauanleitung/zeichnungen.py

Schreibt
  docs/bauanleitung/Zeichnungen_Kartonaut1.pdf    Blatt Z1 … Z6 (A4 quer, maßstäblich, Maße in mm)
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
SEAM = -60.0     # Abwicklung und Schablonen beginnen bei 300°: dort liegt kein Loch und kein Fenster, die Längslinie 0° liegt 60° rechts der Naht
import textwrap  # noqa: E402


def sx(phi, C):
    """Bogenlänge ab der Naht (300°) für den Winkel phi."""
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
        ax.text(x0 + 2, y0 + 12, "Kartonaut 1 · Modulbauweise, Stand 2 (Erstflug)", va="center")
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
# Art: "hole" neu bohren, "old" schon vorhanden (Bestand), "win" ausschneiden. h ab der Unterkante des Rohrs.
def feats_a():
    z0 = M.TUBE_A[0]
    f = [("old", p, M.GIMBAL_SCREW_Z - z0, None, M.SCREW_HOLE_PAPER, "Kardan (Bestand)") for p in M.SCREW_PHI]
    f += [("hole", p, M.J1_SCREW_Z - z0, None, M.SCREW_HOLE_PAPER, "Stoß J1 M3") for p in M.SCREW_PHI]
    f += [("oldwin", p, M.GIMBAL_WINDOW["z"][0] - z0, M.GIMBAL_WINDOW["z"][1] - z0, M.GIMBAL_WINDOW["w"], "Servofenster (Bestand)")
          for p in M.servo_window_phi()]
    return f


def feats_b():
    z0 = M.TUBE_B[0]
    f = [("old", p, M.OLD_HOLES_B_Z - z0, None, M.SCREW_HOLE_PAPER, "alt: Baro-Ausgleich") for p in M.SCREW_PHI]
    f += [("hole", p, M.SPIGOT_B_SCREW_Z - z0, None, M.SCREW_HOLE_PAPER, "Spant M3") for p in M.SCREW_PHI]
    sw = M.ARM_SCREW_SWITCH
    f.append(("hole", sw["phi"] + 12.0, M.v_to_z(sw["v"]) - z0, None, sw["d"], "Schraubschalter"))
    for nm, hd in (("Luke A1 (SD)", M.HATCH_A1), ("Luke A2 (USB)", M.HATCH_A2), ("Luke B (Schalter)", M.HATCH_B)):
        f.append(("win", hd["phi"], M.v_to_z(hd["v"][0]) - z0, M.v_to_z(hd["v"][1]) - z0, hd.get("w", M.HATCH_W), nm))
    return f


def feats_c():
    z0 = M.TUBE_C[0]
    f = [("hole", p, M.SPIGOT_C_SCREW_Z - z0, None, M.SCREW_HOLE_PAPER, "Spant M3") for p in M.SPIGOT_C_PHI]
    f += [("hole", p, M.SHEAR_PIN_Z - z0, None, M.SHEAR_PIN_D, "Abscherstift M2") for p in M.SHEAR_PIN_PHI]
    return f


def guide_h(tube):
    """Höhe der Rampenführung über der Unterkante dieses Rohrs (0 = keine)."""
    return max(0.0, M.RAMP_GUIDE_H - tube[0])


def guide_half():
    return math.degrees(math.atan(M.RAMP_GUIDE_W / 2 / (M.TUBE_OD / 2 + M.RAMP_GUIDE_GAP)))


def draw_development(v, C, L, feats, title, zones=(), gh=0.0):
    v.rect(0, 0, C, L, lw=LW)
    for k in range(8):
        x = sx(45 * k, C)
        v.line([(x, 0), (x, L)], lw=0.25, c="#bbb", ls=(0, (3, 3)))
        v.text(x, L + 2.5 / v.s, deg(45 * k), ha="center", fontsize=5.8, color="#555")
    x0 = sx(0, C)
    v.line([(x0, 0), (x0, L)], lw=1.1, c="#2a7")
    v.text(x0, -5 / v.s, "Längslinie 0°", ha="center", fontsize=5.6, color="#2a7")
    v.text(0, -9 / v.s, "Naht 300°", ha="center", fontsize=5.2, color="#777")
    if gh > 0:
        for g in M.RAMP_GUIDE_PHI:
            a, b = sx(g - guide_half(), C), sx(g + guide_half(), C)
            hg = min(gh, L)
            v.rect(a, 0, b, hg, lw=0.3, c="#c99", fill=C_WARN, alpha=0.45)
            v.text((a + b) / 2, hg / 2, "Führung Rampe", ha="center", va="center", fontsize=4.6, color="#a55", rotation=90)
    for (h0, h1, txt) in zones:
        v.rect(0, h0, C, h1, lw=0.3, c="#7a9", ls=(0, (2, 2)), fill="#e8f3ec", alpha=0.6)
        v.text(C + 2 / v.s, (h0 + h1) / 2, txt, va="center", fontsize=5.4, color="#386")
    for kind, phi, h0, h1, d, txt in feats:
        x = sx(phi, C)
        if kind in ("hole", "old"):
            v.hole(x, h0, d, c=C_HOLE if kind == "hole" else "#888", label=f"Ø{fmt(d)}" if kind == "hole" else "alt")
        elif kind == "oldwin":
            v.rect(x - d / 2, h0, x + d / 2, h1, lw=0.6, c="#888", fill="#e6e6e6", hatch="..")
            v.text(x, (h0 + h1) / 2, "Servo (Bestand)", ha="center", va="center", fontsize=4.6, color="#555")
        else:
            v.rect(x - d / 2, h0, x + d / 2, h1, lw=0.7, c=C_CUT, fill="#fbe3cf", hatch="////")
            v.text(x, (h0 + h1) / 2, txt, ha="center", va="center", fontsize=5.0, rotation=90, color="#8a4a12")
    v.text(C / 2, L + 8 / v.s, title, ha="center", fontsize=7, weight="bold")


def feature_table(feats, C):
    rows = [["Nr", "Art", "Winkel", "Bogen ab Naht", "h ab Kante", "Maß"]]
    for k, (kind, phi, h0, h1, d, txt) in enumerate(sorted(feats, key=lambda f: (f[2], f[1])), 1):
        s = sx(phi, C)
        if kind in ("win", "oldwin"):
            rows.append([k, txt, deg(phi), f"{fmt(s - d / 2)} … {fmt(s + d / 2)}", f"{fmt(h0)} … {fmt(h1)}", f"{fmt(d)} × {fmt(h1 - h0)}"])
        else:
            rows.append([k, txt, deg(phi), fmt(s), fmt(h0), f"Ø {fmt(d)}"])
    return rows


# --------------------------------------------------------------------------- Z1 Übersicht
def z1(pdf):
    sh = Sheet("Z1", "Übersicht, Module und Trennstellen (Stand 2)", "1:4",
               "Längsschnitt in der Ebene der Platine. z = Abstand von der Rohrunterkante (= Düse, der Motor steht bündig). "
               "M1 Antrieb (Rohr A mit dem gebauten Kardan), M2 Avionik (Rohr B, Kuppler J1 darin verklebt, Schlitten mit Spant), "
               "M3 Bergung (Rohr C mit CO₂-Modul und Schirm), M4 Spitze. Alle Radialschrauben bei 0°/90°/180°/270° (Rohr C: 45°-versetzt).")
    s = 0.25
    v = sh.view(28, 150, s)

    def zr(z0, z1, r0, r1, **kw):
        v.rect(z0, r0, z1, r1, **kw)
        v.rect(z0, -r1, z1, -r0, **kw)
    R, Ri = M.TUBE_OD / 2, M.TUBE_ID / 2
    for t in (M.TUBE_A, M.TUBE_B, M.TUBE_C):
        zr(*t, Ri, R, fill="#efe6cf", lw=0.5)
    zr(*M.J1_COUPLER, P.COUPLER_ID / 2, P.COUPLER_OD / 2, fill="#c9ad86", lw=0.4)
    zr(*M.J1_RING["z"], M.J1_RING["id"] / 2, M.J1_RING["od"] / 2, fill="#6d8fc7", lw=0.3)
    v.rect(0, -P.MOTOR_D / 2, M.MOTOR_L, P.MOTOR_D / 2, fill="#b9775a", lw=0.4)
    v.rect(3, -P.COUPLER_ID / 2 + 1, M.GIMBAL_TOP_Z, P.COUPLER_ID / 2 - 1, lw=0.4, c="#345", ls=(0, (3, 2)))
    v.text(M.GIMBAL_TOP_Z / 2, P.COUPLER_ID / 2 - 6, "Kardan\n(gebaut)", ha="center", va="top", fontsize=5)
    v.rect(*[M.DISC_Z[0], -M.DISC_OD / 2, M.DISC_Z[1], M.DISC_OD / 2], fill="#8fb1e0", lw=0.4)
    v.rect(M.BOARD_V0_Z, -M.BOARD_W / 2, M.BOARD_V0_Z + M.BOARD_L, M.BOARD_W / 2, fill="#2e7d4f", lw=0.4, alpha=0.85)
    zr(*M.SPIGOT_B["z"], M.SPIGOT_B["id"] / 2, M.SPIGOT_B["od"] / 2, fill="#8fb1e0", lw=0.4)
    zr(*M.SPIGOT_C["z"], M.SPIGOT_C["id"] / 2, M.SPIGOT_C["od"] / 2, fill="#8fb1e0", lw=0.4)
    v.rect(M.BAND_Z[0], -M.BAND_OD / 2, M.BAND_Z[1], M.BAND_OD / 2, fill="#2471a3", lw=0.4)
    c = M.CO2
    v.rect(M.CO2_Z0, -c["l"] / 2, M.CO2_Z0 + c["d"], c["l"] / 2, fill="#999", lw=0.4)
    v.rect(M.CHUTE_Z[0], -M.CHUTE["d"] / 2, M.CHUTE_Z[1], M.CHUTE["d"] / 2, fill="#e8a49c", lw=0.4)
    zr(*M.NOSE_COUPLER_Z, P.COUPLER_ID / 2, P.COUPLER_OD / 2, fill="#c9ad86", lw=0.3)
    hz = M.NOSE_COUPLER_Z[1]
    v.rect(hz, -P.COUPLER_ID / 2, hz + 4, P.COUPLER_ID / 2, fill="#a0784c", lw=0.3)
    import airframe
    prof = airframe.nose_profile()
    pts = [(M.TOP_Z + dz, r) for r, dz in prof] + [(M.TOP_Z + dz, -r) for r, dz in reversed(prof)]
    sh.ax.add_patch(Polygon([v.P(*p) for p in pts], closed=True, fc="#f4f4f4", ec="#111", lw=0.5))
    v.center([(-10, 0), (M.NOSE_TIP_Z + 10, 0)])
    stations = [(0, "Düse"), (M.GIMBAL_SCREW_Z, ""), (M.J1_SCREW_Z, "T1"), (M.TUBE_B[0], ""), (M.BOARD_V0_Z, ""),
                (M.OLD_HOLES_B_Z, ""), (M.SPIGOT_B_SCREW_Z, "T2"), (M.TUBE_B[1], ""), (M.SPIGOT_C_SCREW_Z, "T3"),
                (M.CHUTE_Z[0], ""), (M.CHUTE_Z[1], ""), (M.NOSE_SHOULDER_Z0, ""), (M.SHEAR_PIN_Z, "T4"), (M.TOP_Z, ""),
                (M.NOSE_TIP_Z, "")]
    for i, (z, lab) in enumerate(stations):
        x, y = v.P(z, -R)
        yy = y - 6 - (i % 3) * 4.2
        sh.ax.plot([x, x], [y, yy + 2], lw=0.25, c="#888")
        sh.ax.text(x, yy, fmt(z), fontsize=5.2, ha="center", va="top", color=C_DIM)
        if lab:
            sh.ax.text(x, v.P(z, R)[1] + 2.5, lab, fontsize=6, ha="center", color="#a33", weight="bold")
    mods = [("M1 Antrieb (Rohr A)", *M.TUBE_A), ("M2 Avionik (Rohr B, Kuppler, Schlitten mit Spant)", M.J1_COUPLER[0], M.BAND_Z[1]),
            ("M3 Bergung (Rohr C)", M.TUBE_C[0], M.TOP_Z), ("M4 Spitze", M.NOSE_SHOULDER_Z0, M.NOSE_TIP_Z)]
    cols = ["#d35400", "#2471a3", "#b7950b", "#7d3c98"]
    for i, (nm, a, b) in enumerate(mods):
        y = 150 + R * s + 12 + i * 5.0
        x0, x1 = v.P(a, 0)[0], v.P(b, 0)[0]
        sh.ax.add_patch(Rectangle((x0, y), x1 - x0, 3.2, fc=cols[i], ec="none", alpha=0.85))
        sh.ax.text(x0 + 1, y + 1.6, nm, fontsize=5.6, va="center", color="white", weight="bold")
    rows = [["Trennstelle", "Wo", "Wie", "Lösen für"],
            ["T1", f"z {fmt(M.J1_SCREW_Z)}, Stoß A/B", "4 × M3 durch Rohr A und Kuppler in den Schraubring", "Kardan/Motorraum, Servo"],
            ["T2", f"z {fmt(M.SPIGOT_B_SCREW_Z)}, oben in B", "4 × M3 durch Rohr B in den Spant", "Schlitten heraus"],
            ["T3", f"z {fmt(M.SPIGOT_C_SCREW_Z)}, unten in C", "4 × M3 (45°) durch Rohr C in den Spant", "Bergung, CO₂-Kapsel"],
            ["T4", f"z {fmt(M.SHEAR_PIN_Z)}, Spitze", "Passung (Abscherstifte nur nach Test)", "trennt beim Ausstoß"],
            ["T5", "Platine", "Stecker J5, J6 (Servos), CO₂-Servo, Akkus", "Kabel"]]
    sh.table(12, 100, rows, [20, 40, 78, 50], row_h=4.4)
    sh.text(12, 103, "Trennstellen", fontsize=8, weight="bold")
    v2 = sh.view(255, 76, 0.42)
    v2.circle(0, 0, M.TUBE_OD); v2.circle(0, 0, M.TUBE_ID, lw=0.3)
    for phi in M.SCREW_PHI:
        v2.hole(36.3 * math.cos(math.radians(phi)), 36.3 * math.sin(math.radians(phi)), 3.4, label=None, cross=2)
    for g in M.RAMP_GUIDE_PHI:
        a = math.radians(g)
        v2.rect(0, 0, 0, 0)
        cx, cy = 49 * math.cos(a), 49 * math.sin(a)
        sh.ax.add_patch(Polygon([v2.P(cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a))
                                 for dx, dy in ((-10, -10), (10, -10), (10, 10), (-10, 10))], closed=True, fc=C_WARN, ec="#a55", lw=0.4))
    for phi in (0, 90, 180, 270):
        v2.text(62 * math.cos(math.radians(phi)), 62 * math.sin(math.radians(phi)) - 2, deg(phi), ha="center", fontsize=5.5, color="#555")
    v2.text(-110, -72, "Querschnitt Rohr A, Blick von oben: Schrauben bei 0/90/180/270°,\nRampenführungen (rot) bei 45/135/225/315°", fontsize=5.6)
    sh.save(pdf, "Z1_uebersicht.png")


# --------------------------------------------------------------------------- Z2–Z4 Abwicklungen
def dev_sheet(pdf, nr, title, tube, feats, zones, png, note, scale):
    C, L = M.CIRC_TUBE, tube[1] - tube[0]
    sh = Sheet(nr, title, f"1:{fmt(scale)}", note)
    v = sh.view(24, 50, 1 / scale)
    draw_development(v, C, L, feats, f"{title.split(':')[0]}, Abwicklung von außen", zones=zones, gh=guide_h(tube))
    v.dim((C, 0), (C, L), -36, fmt(L))
    v.dim((0, 0), (C, 0), -9, f"Umfang {fmt(C)}")
    v.dim((0, L), (sx(0, C), L), 12, fmt(sx(0, C)))
    for kind, phi, h0, h1, d, txt in feats:
        if kind == "hole":
            v.dim((sx(phi, C) + 5, 0), (sx(phi, C) + 5, h0), -2, fmt(h0), fs=5.0)
    sh.table(206, 192, feature_table(feats, C), [6, 24, 10, 18, 13, 12], row_h=4.0, fs=5.1)
    sh.text(206, 192 - 4.0 * (len(feats) + 1) - 5, "rot = neu bohren/schneiden, grau = vorhanden", fontsize=5.6)
    sh.save(pdf, png)


def z2(pdf):
    dev_sheet(pdf, "Z2", "Rohr A 75 × 125: Kardanrohr", M.TUBE_A, feats_a(),
              [(M.GIMBAL_SCREW_Z - 6, M.GIMBAL_SCREW_Z + 6, "Kardanflansch (Bestand)"),
               (M.GIMBAL_WINDOW["z"][0], M.GIMBAL_WINDOW["z"][1], "Servofenster (Bestand, Winkel lt. Rohr)"),
               (M.J1_COUPLER[0], M.TUBE_A[1], "Kuppler J1 steckt")],
              "Z2_rohr_a.png",
              "Gebaut: Kardan mit 4 Schrauben bei 0/90/180/270° auf h = 44, zwei Servofenster ca. 20 × 20 ab h = 60. Neu: nur die 4 Löcher T1 "
              "15 mm unter der Oberkante, gebohrt durch Rohr A UND den aufgesteckten Kuppler (Schablone S1). Die Servofenster dürfen nicht "
              "unter einer Rampenführung liegen; laut Druckdatei liegen sie bei ca. 207° und 336°, die Führungen deshalb bei 45/135/250°.", 1.4)


def z3(pdf):
    dev_sheet(pdf, "Z3", "Rohr B 75 × 176: Avionikrohr", M.TUBE_B, feats_b(),
              [(0, M.J1_COUPLER[1] - M.TUBE_B[0], "Kuppler J1 verklebt"),
               (M.SPIGOT_B["z"][0] - M.TUBE_B[0], M.TUBE_B[1] - M.TUBE_B[0], "Zapfen des Spants")],
              "Z3_rohr_b.png",
              "Die 4 alten Löcher auf h = 44 (vom Ring-Stack) bleiben offen: sie sind der Druckausgleich für das Barometer. Luken mit Cutter "
              "ausschneiden, Stücke als Deckel aufheben. Spantschrauben T2 8 mm unter der Oberkante. Schraubschalter-Loch Ø 3 neben Luke B. "
              "Schablonen S2 (unten) und S3 (oben).", 1.4)


def z4(pdf):
    dev_sheet(pdf, "Z4", "Rohr C 75 × " + fmt(M.TUBE_C[1] - M.TUBE_C[0]) + ": Bergungsrohr", M.TUBE_C, feats_c(),
              [(0, M.SPIGOT_C["z"][1] - M.TUBE_C[0], "Zapfen des Spants"),
               (M.CO2_Z0 - M.TUBE_C[0], M.CO2_Z0 + M.CO2["h"] - M.TUBE_C[0], "CO₂-Modul"),
               (M.CHUTE_Z[0] - M.TUBE_C[0], M.CHUTE_Z[1] - M.TUBE_C[0], "Schirm 100 × Ø 70"),
               (M.NOSE_COUPLER_Z[0] - M.TUBE_C[0], M.TOP_Z - M.TUBE_C[0], "Kuppler der Spitze (in der Spitze verklebt)")],
              "Z4_rohr_c.png",
              "Rohr aus dem vorhandenen Reststück, Länge aus dem Stapel: Zapfen 15, CO₂-Modul 24, Schirm 100, dann der zweite halbe Kuppler (75), "
              "25 mm in der Spitze bis zur Holzplatte verklebt, 50 mm im Rohr C; die Schnur liegt im Kuppler. Spantschrauben T3 um 45° versetzt (Kapsel liegt quer zwischen ihnen). Abscherstifte nur, "
              "wenn der CO₂-Test zeigt, dass sie sicher abscheren. Schablone S4.", 2.0)


# --------------------------------------------------------------------------- Z5 Schlitten mit Spant
def z5(pdf):
    sh = Sheet("Z5", "Avionik-Schlitten mit Spant (ein Druckteil)", "1:1,25",
               "Stehend gedruckt, Band auf dem Bett, PETG, 3 Wände, 25 % Gyroid. Bezugsebene A = Unterseite des Bands (liegt auf der Oberkante "
               "von Rohr B). M3-Muttern in Sechskant-Taschen, von innen eingedrückt: 4 Augen unten (T2), 4 Augen oben (T3, 45° versetzt). Platinensäulen und Stirnaugen: M3 direkt ins Kernloch Ø 2,6. "
               "Platte 3,5 mm mit 5-mm-Rand für den CO₂-Druck (Stand 2c), Zapfen 2 mm, Ringschraube M4 und Kabeldurchführung Ø 6 für das CO₂-Servo.")
    s = 1 / 1.25
    A = M.BAND_Z[0]

    def zz(z):
        return z - A
    bw = M.BOARD_W / 2
    v = sh.view(62, 166, s)
    sb, sc = M.SPIGOT_B, M.SPIGOT_C
    v.rect(-M.BAND_OD / 2, 0, M.BAND_OD / 2, zz(M.BAND_Z[1]), fill="#cfdcf0")
    v.rect(-sc["od"] / 2, zz(sc["z"][0]), sc["od"] / 2, zz(sc["z"][1]), fill="#dfe8f5")
    v.rect(-sb["od"] / 2, zz(sb["z"][0]), sb["od"] / 2, zz(sb["z"][1]), fill="#dfe8f5")
    v.rect(-bw, zz(M.DISC_Z[1]), bw, zz(sb["z"][0]), lw=0.5, c="#2471a3")
    v.rect(-bw, zz(M.BOARD_V0_Z), bw, zz(M.BOARD_V0_Z + M.BOARD_L), lw=0.5, c="#2e7d4f", ls=(0, (4, 2)))
    v.rect(-M.DISC_OD / 2, zz(M.DISC_Z[0]), M.DISC_OD / 2, zz(M.DISC_Z[1]), fill="#cfdcf0")
    t = P.TEENSY
    v.rect(t["u0"], zz(M.BOARD_V0_Z + t["v0"]), t["u1"], zz(M.BOARD_V0_Z + t["v1"]), lw=0.4, c="#2e7d4f", ls=(0, (2, 2)))
    for (u, vv) in M.BOARD_HOLES:
        v.hole(u, zz(M.BOARD_V0_Z + vv), M.INSERT_HOLE[0])
    v.hole(0, zz(M.SPIGOT_B_SCREW_Z), M.INSERT_HOLE[0], label="Auge 0°")
    v.center([(0, zz(M.DISC_Z[0]) - 6), (0, zz(sc["z"][1]) + 6)])
    v.dim((-M.BAND_OD / 2, zz(sc["z"][1])), (M.BAND_OD / 2, zz(sc["z"][1])), 5, f"Band Ø {fmt(M.BAND_OD)}, Zapfen Ø {fmt(sc['od'])}")
    v.dim((-M.DISC_OD / 2, zz(M.DISC_Z[0])), (M.DISC_OD / 2, zz(M.DISC_Z[0])), -5, f"Ø {fmt(M.DISC_OD)} (Scheibe)")
    xr = M.BAND_OD / 2
    for i, (zv, lab) in enumerate(((sc["z"][1], None), (M.SPIGOT_C_SCREW_Z, None))):
        v.dim((xr, 0), (xr, zz(zv)), -6 * (i + 1), fmt(zv - A))
    for i, zv in enumerate((sb["z"][0], M.SPIGOT_B_SCREW_Z, M.BOARD_V0_Z + M.BOARD_L, M.BOARD_V0_Z, M.DISC_Z[0])):
        v.dim((xr, zz(zv)), (xr, 0), -6 * (i + 1), fmt(A - zv))
    v.dim((-bw, zz(M.BOARD_V0_Z)), (bw, zz(M.BOARD_V0_Z)), -12, f"{fmt(M.BOARD_W)} (Platine)")
    u0, v0 = M.BOARD_HOLES[0]
    v.dim((M.BOARD_HOLES[0][0], zz(M.BOARD_V0_Z + v0)), (M.BOARD_HOLES[1][0], zz(M.BOARD_V0_Z + v0)), 6, fmt(2 * abs(u0)))
    v.dim((-bw, zz(M.BOARD_V0_Z + M.BOARD_HOLES[2][1])), (-bw, zz(M.BOARD_V0_Z + M.BOARD_HOLES[0][1])), -5, fmt(M.BOARD_HOLES[2][1] - M.BOARD_HOLES[0][1]))
    v.text(-M.BAND_OD / 2 - 5, 0, "A", fontsize=8, weight="bold", color="#a33", va="center")
    v.text(-M.BAND_OD / 2, zz(sc["z"][1]) + 10, "Ansicht von +y (Bestückungsseite)", fontsize=6.5, weight="bold")
    # Seitenansicht
    v2 = sh.view(172, 166, s)
    v2.rect(-M.BAND_OD / 2, 0, M.BAND_OD / 2, zz(M.BAND_Z[1]), fill="#cfdcf0")
    v2.rect(-sc["od"] / 2, zz(sc["z"][0]), sc["od"] / 2, zz(sc["z"][1]), fill="#dfe8f5")
    v2.rect(-sb["od"] / 2, zz(sb["z"][0]), sb["od"] / 2, zz(sb["z"][1]), fill="#dfe8f5")
    v2.rect(-M.DISC_OD / 2, zz(M.DISC_Z[0]), M.DISC_OD / 2, zz(M.DISC_Z[1]), fill="#cfdcf0")
    v2.rect(-M.BOARD_T / 2, zz(M.BOARD_V0_Z), M.BOARD_T / 2, zz(M.BOARD_V0_Z + M.BOARD_L), fill="#2e7d4f", lw=0.3)
    v2.rect(M.TRAY_FLOOR_Y, zz(M.DISC_Z[1]), -M.BOARD_T / 2, zz(sb["z"][0]), lw=0.5, c="#2471a3")
    for nm, bat in (("2S", M.BAT2S), ("1S", M.BAT1S)):
        y0 = M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3
        v2.rect(y0, zz(M.BOARD_V0_Z + bat["v0"]), y0 + bat["h"], zz(M.BOARD_V0_Z + bat["v0"] + bat["l"]), fill="#e9c46a", lw=0.3)
        v2.text(y0 + bat["h"] / 2, zz(M.BOARD_V0_Z + bat["v0"] + bat["l"] / 2), nm, ha="center", va="center", fontsize=5.5, rotation=90)
    va, vb = M.HATCH_B["v"]
    v2.rect(M.PANEL_Y[0], zz(M.BOARD_V0_Z + va + 1), M.PANEL_Y[1], zz(M.BOARD_V0_Z + vb - 1), fill="#6d8fc7", lw=0.3)
    g = M.GPS
    v2.rect(g["y"][0], zz(g["z_top"] - g["h"]), g["y"][1], zz(g["z_top"]), fill="#3c9a62", lw=0.3)
    v2.leader((g["y"][1], zz(g["z_top"] - g["h"] / 2)), (14, -6), "GPS, Patch nach oben")
    lh = M.LORA_HELIX
    v2.rect(lh["y"] - lh["d"] / 2, zz(lh["z_top"] - lh["l"]), lh["y"] + lh["d"] / 2, zz(lh["z_top"]), fill="#bbb", lw=0.3)
    v2.leader((lh["y"] + lh["d"] / 2, zz(lh["z_top"] - lh["l"] / 2)), (16, 0), "LoRa-Wendel 433 MHz")
    v2.dim((M.TRAY_FLOOR_Y, zz(M.DISC_Z[1]) - 2), (-M.BOARD_T / 2, zz(M.DISC_Z[1]) - 2), -4, fmt(abs(M.TRAY_FLOOR_Y) - M.BOARD_T / 2))
    v2.text(-M.BAND_OD / 2, zz(sc["z"][1]) + 10, "Ansicht von +x (Luke B links, Luke A rechts)", fontsize=6.5, weight="bold")
    # Draufsicht
    v3 = sh.view(250, 100, 0.72)
    v3.circle(0, 0, M.BAND_OD, fill="#cfdcf0"); v3.circle(0, 0, sc["od"], lw=0.3, ls=(0, (3, 2))); v3.circle(0, 0, sc["id"], lw=0.3, ls=(0, (3, 2)))
    v3.hole(0, -16, 4.3); v3.leader((0, -16), (-22, -14), "Ringschraube M4")
    v3.hole(-18, 8, 6.0); v3.leader((-18, 8), (-24, 18), "Kabel CO₂-Servo Ø 6")
    for phi in M.SPIGOT_C_PHI:
        x, y = (sc["od"] / 2 - 2) * math.cos(math.radians(phi)), (sc["od"] / 2 - 2) * math.sin(math.radians(phi))
        v3.hole(x, y, 2.0, c="#2471a3")
        v3.text(x * 1.34, y * 1.34, deg(phi), ha="center", va="center", fontsize=5.5, color="#2471a3")
    v3.rect(-M.CO2["l"] / 2, 4 - M.CO2["d"] / 2, M.CO2["l"] / 2, 4 + M.CO2["d"] / 2, lw=0.4, ls=(0, (2, 2)), c="#666")
    v3.text(0, 4, "CO₂-Kapsel (quer)", ha="center", va="center", fontsize=5)
    v3.center([(-44, 0), (44, 0)]); v3.center([(0, -44), (0, 44)])
    v3.text(-40, -50, "Draufsicht Spant (von der Spitze)\nobere Augen bei 45°/135°/225°/315°", fontsize=6)
    sh.save(pdf, "Z5_schlitten.png")


# --------------------------------------------------------------------------- Z6 Kleinteile
def z6(pdf):
    sh = Sheet("Z6", "Untere Scheibe, Schalterbrett, Schraubring J1", "1:1",
               "PETG. Die Scheibe zentriert das untere Ende des Schlittens im Kuppler J1; durch ihr Fenster stecken J5/J6/J1, durch das Rundloch "
               "laufen die Kabel und ragt die LoRa-Wendel. Danach mit Schaumstoff stopfen. Schraubring J1 wird im Kuppler verklebt, 25 mm über "
               "dessen Unterkante (Lage = Bohrungen T1 in Rohr A).")
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
    v.text(-36, 48, f"Untere Scheibe, {fmt(M.DISC_Z[1] - M.DISC_Z[0])} dick", fontsize=7, weight="bold")
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
    v2.text(-M.PANEL_W / 2 - 10, vb - b0 + 8, "Schalterbrett (Luke B), von außen", fontsize=6.5, weight="bold")
    rows = [["Ausbruch", "u-Mitte", "v von … bis", "Breite"]]
    for name, u, a, b, w in M.PANEL_PARTS:
        rows.append([name, fmt(u), f"{fmt(a - b0)} … {fmt(b - b0)}", fmt(w + 0.4)])
    rows.append(["2 Säulen Ø 7 (M3 von innen)", " / ".join(fmt(cu) for cu, _ in M.PANEL_COLS), " / ".join(fmt(cv - b0) for _, cv in M.PANEL_COLS), "–"])
    sh.table(100, 108, rows, [42, 13, 20, 12], row_h=4.0, fs=5.4)
    v3 = sh.view(235, 130, 1.0)
    rg = M.J1_RING
    v3.circle(0, 0, rg["od"], fill="#cfdcf0"); v3.circle(0, 0, rg["id"], fill="white")
    for phi in M.SCREW_PHI:
        a = math.radians(phi)
        v3.circle((rg["id"] / 2 - 0.5) * math.cos(a), (rg["id"] / 2 - 0.5) * math.sin(a), 9.0, fill="#cfdcf0", lw=0.4)
        p0 = ((rg["od"] / 2 - M.INSERT_HOLE[1]) * math.cos(a), (rg["od"] / 2 - M.INSERT_HOLE[1]) * math.sin(a))
        v3.line([p0, (rg["od"] / 2 * math.cos(a), rg["od"] / 2 * math.sin(a))], c=C_HOLE, lw=M.INSERT_HOLE[0] * 2.83)
    v3.circle(0, 0, rg["id"] - 0.01, lw=0.6)
    v3.dim((-rg["od"] / 2, 0), (rg["od"] / 2, 0), 40, f"Ø {fmt(rg['od'])}")
    v3.dim((-rg["id"] / 2, -8), (rg["id"] / 2, -8), -4, f"Ø {fmt(rg['id'])}")
    v3.text(-38, 48, f"Schraubring J1, {fmt(rg['z'][1] - rg['z'][0])} hoch, 4 Augen 90° mit M3-Mutterntasche innen", fontsize=7, weight="bold")
    sh.save(pdf, "Z6_kleinteile.png")


# --------------------------------------------------------------------------- Bohrschablonen 1:1
def template(pdf, nr, title, C, feats, h_range, ref, note, gh):
    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, A4[0]); ax.set_ylim(0, A4[1]); ax.set_aspect("equal"); ax.axis("off")
    h0, h1 = h_range
    H = h1 - h0
    x_off, y_off = 18.0, (A4[1] - H) / 2 - 6

    def P_(s, h):
        return x_off + s, y_off + (h - h0)
    ax.add_patch(Rectangle(P_(0, h0), C, H, fill=False, lw=0.6, ec="#000"))
    ax.add_patch(Rectangle(P_(C, h0), 12, H, fill=True, fc="#eee", ec="#999", lw=0.4, hatch="..."))
    ax.text(*P_(C + 6, h0 + H / 2), "Klebelasche", rotation=90, ha="center", va="center", fontsize=5.5)
    ky = h0 if ref == "unten" else h1
    xa, ya = P_(0, ky); xb, _ = P_(C, ky)
    ax.plot([xa, xb], [ya, ya], lw=2.2, c="#c0392b")
    ax.text(xa, ya + (-4 if ref == "unten" else 7.5), f"Bezugskante = Rohr{'unter' if ref == 'unten' else 'ober'}kante: bündig anlegen",
            fontsize=6.5, color="#c0392b", va="bottom" if ref == "oben" else "top")
    for k in range(0, 360, 15):
        x, _ = P_(sx(k, C), h0)
        major = k % 45 == 0
        ax.plot([x, x], [P_(0, h0)[1], P_(0, h1)[1]], lw=0.35 if major else 0.15, c="#666" if major else "#bbb", ls=(0, (3, 3)))
        if major:
            ax.text(x, P_(0, h1)[1] + 1.2, f"{k}°", ha="center", va="bottom", fontsize=6)
    ax.text(*P_(0, h1), "Naht\n300°", ha="center", va="bottom", fontsize=5, color="#777")
    xg, _ = P_(sx(0, C), h0)
    ax.plot([xg, xg], [P_(0, h0)[1], P_(0, h1)[1]], lw=1.4, c="#2a7")
    ax.text(xg + 1, P_(0, h1)[1] - 3, "Längslinie 0°\n(Kardanschraube)", fontsize=5.5, color="#2a7", va="top")
    if gh > h0:
        for g in M.RAMP_GUIDE_PHI:
            a, b = sx(g - guide_half(), C), sx(g + guide_half(), C)
            top = min(gh, h1)
            ax.add_patch(Rectangle(P_(a, h0), b - a, top - h0, fc=C_WARN, ec="none", alpha=0.35))
            ax.text(*P_((a + b) / 2, (h0 + top) / 2), "Führung Rampe: nichts hervorstehen", rotation=90, ha="center", va="center", fontsize=5, color="#a55")
    for kind, phi, a, b, d, txt in feats:
        s = sx(phi, C)
        if kind in ("hole", "old") and h0 <= a <= h1:
            x, y = P_(s, a)
            col = "#c0392b" if kind == "hole" else "#888"
            ax.add_patch(Circle((x, y), d / 2, fill=False, ec=col, lw=0.5))
            ax.plot([x - 6, x + 6], [y, y], lw=0.3, c=col); ax.plot([x, x], [y - 6, y + 6], lw=0.3, c=col)
            ax.add_patch(Circle((x, y), 0.35, fc="#000"))
            ax.text(x + 2.5, y + 2.5, f"{txt}\nØ {fmt(d)}" + (" (vorhanden: Lage prüfen)" if kind == "old" else ""), fontsize=5.0, color=col)
        elif kind in ("win", "oldwin"):
            lo, hi = max(a, h0), min(b, h1)
            if hi > lo:
                ax.add_patch(Rectangle(P_(s - d / 2, lo), d, hi - lo, fill=True, fc="#fbe3cf", ec="#e67e22", lw=0.7, hatch="////"))
                ax.text(*P_(s, (lo + hi) / 2), f"{txt}\nausschneiden\n{fmt(d)} × {fmt(b - a)}", ha="center", va="center", fontsize=5.0,
                        color="#8a4a12", bbox=dict(fc="white", ec="none", pad=0.4))
    for h in range(int(math.ceil(h0 / 10) * 10), int(h1) + 1, 10):
        x, y = P_(0, h)
        ax.plot([x - 3, x], [y, y], lw=0.3, c="#000")
        ax.text(x - 3.5, y, str(h), fontsize=4.8, ha="right", va="center")
    ax.plot([20, 120], [12, 12], lw=1.0, c="#000")
    for x in (20, 120):
        ax.plot([x, x], [10, 14], lw=1.0, c="#000")
    ax.text(70, 14.5, "Prüfmaß 100 mm: nach dem Druck nachmessen", ha="center", fontsize=6)
    ax.text(130, 15.5, f"{nr}  {title}", fontsize=7.5, va="bottom", weight="bold")
    ax.text(130, 9.5, f"A4 quer drucken, „Tatsächliche Größe / 100 %“, nicht „An Seite anpassen“. Umfang {fmt(C)} mm.", fontsize=6.2, va="bottom")
    ax.text(18, A4[1] - 8, "\n".join(textwrap.wrap(note, 160)), fontsize=6.2, va="top", linespacing=1.3)
    pdf.savefig(fig)
    fig.savefig(IMG / f"{nr}_schablone.png", dpi=110)
    plt.close(fig)


def templates():
    out = HERE / "Bohrschablonen_1zu1.pdf"
    C = M.CIRC_TUBE
    LB = M.TUBE_B[1] - M.TUBE_B[0]
    LC = M.TUBE_C[1] - M.TUBE_C[0]
    with PdfPages(out) as pdf:
        template(pdf, "S1", "Rohr A, Oberkante (Stoß J1)", C, feats_a(), (M.TUBE_A[1] - M.TUBE_A[0] - 45.0, M.TUBE_A[1] - M.TUBE_A[0]), "oben",
                 "Zuerst den Kuppler J1 in Rohr B kleben und Rohr A aufstecken. Streifen um Rohr A, rote Kante an die Oberkante von A (Stoß), grüne "
                 "Linie auf die Kardanschraube 0°. Die 4 Löcher T1 Ø 3,4 durch Rohr A und Kuppler bohren. Danach den Schraubring (Muttern innen eingedrückt) in den "
                 "Kuppler schieben, mit M3 durch die Löcher ausrichten und erst dann einkleben.", guide_h(M.TUBE_A) - 0)
        template(pdf, "S2", "Rohr B, Unterkante (Luken A1 und B, Schraubschalter)", C, feats_b(), (0.0, 110.0), "unten",
                 "Rohr B mit verklebtem Kuppler, Bezugskante an die Unterkante von B (Stoß), Längslinie von Rohr A über den Stoß verlängert. "
                 "Grau = alte Löcher (bleiben als Druckausgleich offen). Luken mit Cutter, Schalterloch Ø 3.", guide_h(M.TUBE_B))
        template(pdf, "S3", "Rohr B, Oberkante (Luke A2, Spant T2)", C, feats_b(), (LB - 75.0, LB), "oben",
                 "Bezugskante an die Oberkante von B. Löcher T2 Ø 3,4, Luke A2 ausschneiden. Danach Schlitten einsetzen: die Augen fluchten in "
                 "4 Lagen, die richtige ist die mit Luke A über dem USB-Stecker.", 0.0)
        template(pdf, "S4", "Rohr C, beide Enden (Spant T3, Abscherstifte)", C, feats_c(), (0.0, 30.0), "unten",
                 "Unteres Ende: Löcher T3 Ø 3,4 bei 45°/135°/225°/315°, 7,5 mm über der Unterkante. Für die Abscherstifte (optional, h = "
                 f"{fmt(M.SHEAR_PIN_Z - M.TUBE_C[0])}) denselben Streifen an der Oberkante anlegen: Stifte bei 45° und 225°, 15 mm unter der Kante.", 0.0)
    return out


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    for f in list(IMG.glob("Z*.png")) + list(IMG.glob("S*_schablone.png")):
        f.unlink()
    out = HERE / "Zeichnungen_Kartonaut1.pdf"
    with PdfPages(out) as pdf:
        for f in (z1, z2, z3, z4, z5, z6):
            f(pdf)
    t = templates()
    print("wrote", out.relative_to(ROOT), "and", t.relative_to(ROOT))


if __name__ == "__main__":
    main()
