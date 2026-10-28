"""Bestückungsplan der Handlöt-Teile auf dem Mainboard rev B1 (für docs/Platine_revB1_Bestueckung_Pruefung.md).

    python docs/platine/bestueckungsplan.py      # schreibt docs/img/platine/bestueckungsplan.png

Positionen: SMD-Handlöt-Teile aus hardware/mainboard/kicad/fab/mainboard_cpl.csv (y dort negiert),
THT-Teile, Lötbrücken und Testpunkte aus hardware/mainboard/kicad/mainboard.kicad_pcb. Platine 54 × 120 mm
(x 100 … 154, y 50 … 170 in KiCad), Blick von oben auf die Bestückseite, Spitze (J_STACK, GPS) oben.
"""
import csv
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                         # noqa: E402
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PCB = ROOT / "hardware/mainboard/kicad/mainboard.kicad_pcb"
CPL = ROOT / "hardware/mainboard/kicad/fab/mainboard_cpl.csv"
OUT = ROOT / "docs/img/platine/bestueckungsplan.png"

X0, X1, Y0, Y1 = 100.0, 154.0, 50.0, 170.0

# Handlöt-Teile nach Stufen (Bestellung_JLCPCB_2026-10-26.md §2.2 und EINKAUFSLISTE §1), Farbe je Stufe
STAGES = {
    "A": ("#c0392b", "Stufe A: Versorgung (U3, U14, U11, R14, R15, R17, L2, C20, FB1, F1, F2, C4, C5)",
          "U3 U14 U11 R14 R15 R17 L2 C20 FB1 F1 F2 C4 C5".split()),
    "B": ("#2471a3", "Stufe B: Logik und Messung (U12, U13, U6, U8, LED1, LED2, D2, D3)",
          "U12 U13 U6 U8 LED1 LED2 D2 D3".split()),
    "C": ("#1e8449", "Stufe C: Funk und SMD-Stecker (U10, J11, J12, J13, J14)", "U10 J11 J12 J13 J14".split()),
    "D": ("#7d3c98", "Stufe D: THT (Teensy-Sockel A1, BZ1, J1–J10, J15–J18)",
          "A1 BZ1 J1 J2 J3 J4 J5 J6 J7 J8 J9 J10 J15 J16 J17 J18".split()),
}
JUMPERS = ["JP1", "JP2"]
TESTPOINTS = {"TP1": "VBAT_PROT", "TP2": "VSYS_IN", "TP3": "5V_SYS", "TP4": "VSERVO", "TP5": "3V3_RF",
              "TP6": "3V3_EXP", "TP7": "GND"}
# grobe Umrisse (mm) für die Zeichnung, (Breite, Höhe) vor der Drehung
SIZES = {
    "A1": (18.0, 61.0), "BZ1": (12.0, 12.0), "U10": (16.0, 26.0), "J15": (5.1, 25.4),
    "J1": (10.0, 8.0), "J2": (8.0, 4.5), "J3": (12.0, 4.5), "J17": (10.0, 4.5), "J18": (8.0, 4.5),
    "J4": (7.5, 5.8), "J8": (7.5, 5.8), "J7": (10.0, 5.8), "J16": (10.0, 5.8),
    "J5": (10.0, 7.0), "J6": (10.0, 7.0), "J9": (7.5, 7.0), "J10": (7.5, 7.0),
    "J11": (8.0, 4.0), "J12": (7.0, 4.0), "J13": (6.8, 4.0), "J14": (6.8, 4.0),
    "C4": (7.3, 4.3), "C5": (7.3, 4.3), "C20": (3.2, 2.5), "F1": (4.5, 3.2), "F2": (4.5, 3.2),
    "L2": (5.0, 5.0), "U6": (3.0, 3.0), "U12": (5.0, 4.4), "U13": (5.0, 4.4),
    "U3": (3.0, 2.0), "U14": (3.0, 2.0), "U8": (3.0, 2.0), "U11": (3.0, 2.0),
    "D2": (4.3, 2.6), "D3": (4.3, 2.6), "LED1": (2.0, 2.0), "LED2": (2.0, 2.0),
    "R14": (1.6, 0.8), "R15": (1.6, 0.8), "R17": (1.6, 0.8), "FB1": (1.6, 0.8),
}


def read_pcb():
    s = PCB.read_text(encoding="utf-8")
    pat = re.compile(r'\(footprint "([^"]+)"\s*\(layer "F\.Cu"\)\s*\(uuid "[^"]+"\)\s*\(at ([-\d.]+) ([-\d.]+)'
                     r'(?: ([-\d.]+))?\)(.*?)\(property "Reference" "([^"]+)"', re.S)
    out = {}
    for m in pat.finditer(s):
        _, x, y, rot, _, ref = m.groups()
        out[ref] = (float(x), float(y), float(rot or 0))
    return out


def read_cpl():
    out = {}
    with CPL.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["Designator"]] = (float(r["Mid X"].replace("mm", "")), -float(r["Mid Y"].replace("mm", "")),
                                    float(r["Rotation"]))
    return out


# Versatz Footprint-Ursprung -> Mitte (mm, lokal vor der Drehung): KiCad setzt THT-Stecker auf Pin 1
OFFSETS = {
    "J2": (1.0, 0), "J18": (1.0, 0), "J17": (2.0, 0), "J3": (3.0, 0),           # JST PH, Raster 2,0
    "J4": (1.25, 0), "J8": (1.25, 0), "J7": (2.5, 0), "J16": (2.5, 0),         # JST XH stehend, Raster 2,5
    "J9": (1.25, 3.0), "J10": (1.25, 3.0), "J5": (2.5, 3.0), "J6": (2.5, 3.0),  # JST XH liegend, Körper hinter den Pins
    "J1": (1.25, -3.0), "BZ1": (3.8, 0), "J15": (1.27, 11.43),   # 2×10: Pin 2 bei +x, Reihen entlang +y
}


def rotate(dx, dy, rot):
    import math
    a = math.radians(rot)
    return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)


def main():
    pos = read_cpl()
    pos.update({k: v for k, v in read_pcb().items() if k not in pos})
    for ref, (dx, dy) in OFFSETS.items():
        if ref in pos:
            x, y, rot = pos[ref]
            ox, oy = rotate(dx, dy, rot)
            pos[ref] = (x + ox, y + oy, rot)
    fig, ax = plt.subplots(figsize=(7.2, 12.4))
    ax.add_patch(FancyBboxPatch((X0, Y0), X1 - X0, Y1 - Y0, boxstyle="round,pad=0,rounding_size=2",
                                fc="#eaf2e3", ec="#333", lw=1.2))
    for mx, my in [(103.5, 53.5), (150.5, 53.5), (103.5, 166.5), (150.5, 166.5)]:
        ax.add_patch(Circle((mx, my), 1.6, fc="white", ec="#333", lw=0.8))
    for stage, (color, _, refs) in STAGES.items():
        for ref in refs:
            if ref not in pos:
                print("fehlt:", ref, file=sys.stderr)
                continue
            x, y, rot = pos[ref]
            w, h = SIZES.get(ref, (2.0, 2.0))
            if abs(rot) % 180 == 90:
                w, h = h, w
            ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=color, ec="black", lw=0.5, alpha=0.75))
            fs = 7 if max(w, h) > 6 else 5.5
            ax.text(x, y, ref, ha="center", va="center", fontsize=fs, color="white", weight="bold",
                    path_effects=None)
    for ref in JUMPERS:
        if ref in pos:
            x, y, _ = pos[ref]
            ax.add_patch(Rectangle((x - 1.5, y - 1.0), 3.0, 2.0, fc="#f39c12", ec="black", lw=0.5))
            ax.text(x, y - 2.3, ref, ha="center", va="top", fontsize=6, color="#7e5109")
    for ref, net in TESTPOINTS.items():
        if ref in pos:
            x, y, _ = pos[ref]
            ax.add_patch(Circle((x, y), 0.9, fc="#f1c40f", ec="black", lw=0.6))
            ax.text(x - 1.6, y, f"{ref} {net}", ha="right", va="center", fontsize=5.5, color="#5d4037")
    ax.text((X0 + X1) / 2, Y0 + 1.5, "Spitze: J_STACK, GPS, LEDs", ha="center", va="top", fontsize=7, color="#555")
    ax.text((X0 + X1) / 2, Y1 - 1.5, "Düse: Akkus, Servos, Schalterbrett", ha="center", va="bottom", fontsize=7,
            color="#555")
    handles = [Rectangle((0, 0), 1, 1, fc=c, alpha=0.75) for c, _, _ in STAGES.values()]
    handles += [Rectangle((0, 0), 1, 1, fc="#f39c12"), Circle((0, 0), 1, fc="#f1c40f")]
    labels = [t for _, t, _ in STAGES.values()] + ["Lötbrücken JP1 (1S), JP2 (2S)", "Testpunkte TP1–TP7"]
    ax.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, -0.02), fontsize=6.5, frameon=False, ncol=1)
    ax.set_xlim(X0 - 3, X1 + 3)
    ax.set_ylim(Y1 + 3, Y0 - 3)          # KiCad: y wächst nach unten; Spitze oben
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Mainboard rev B1: Handlöt-Teile, Blick auf die Bestückseite", fontsize=10)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
