"""Board outline (DXF for KiCad Edge.Cuts) and placement plan (SVG) of the mainboard rev B, sled version.

The board is a sled lying lengthwise in the airframe, its plane through the roll axis, between the
end rings of the existing flight-computer stack (flight_computer.blend, not in this repo: rings of
69 mm diameter, eight 2 mm threaded rods at (+-29.5, +-7) and (+-7, +-29.5) mm), which sits inside a
Klima 75-mm coupler (ID 70.2 mm). The rods run past the board edges; the 2S LiPo (actuators) and the
1S LiPo (electronics, rev B) lie one behind the other in the printed carrier underneath the board.

Coordinates: u across the board (mm, 0 on the roll axis), v along the rocket axis (mm, 0 at the
TVC end, growing towards the nose). In the cross-section y is the board normal (component side +).

Run:  python hardware/mainboard/outline.py   (writes next to this file, no dependencies)
"""
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

TUBE_ID = 70.2            # mm, inner diameter of the Klima 75-mm coupler the flight computer sits in (rings 69 mm, tube itself 72.6 mm)
BOARD_W, BOARD_L = 54.0, 120.0
BOARD_T = 1.6
CORNER_R = 2.0
HOLE_D = 3.2              # M3 to the printed carrier
HOLES = [(-23.5, 3.5), (23.5, 3.5), (-23.5, 116.5), (23.5, 116.5)]
RODS = [(29.5, 7.0), (29.5, -7.0), (-29.5, 7.0), (-29.5, -7.0),
        (7.0, 29.5), (-7.0, 29.5), (7.0, -29.5), (-7.0, -29.5)]
ROD_D = 2.0
TEENSY = dict(u0=-8.9, u1=8.9, v0=30.0, v1=91.0)          # SD card at v0, USB at v1
IMU = (0.0, 60.5)                                          # under the Teensy, on the roll axis

# Placement zones (label, u0, u1, v0, v1, colour, items)
ZONES = [
    ("AKKUS / SCHALTER", -27, 0, 0, 22, "#f4d6a0", ["XT30 (2S), JST-PH (1S)", "J_SW, J_CHG1/2, JP1/JP2", "Verpolschutz, Polyfuse,", "Lastschalter, Lader"]),
    ("SERVOS / MOTOR", 0, 27, 0, 22, "#f6c4c4", ["2x TVC-Servo (90°-Leiste)", "Shunt, INA239"]),
    ("WANDLER", -27, -10, 22, 92, "#f4d6a0",
     ["Buck-Boost", "5V_SYS (1S)", "", "Elkos", "", "LoRa E22", "(links)", "", "Teensy", "mittig,", "IMU auf", "der Achse"]),
    ("SENSOR /", 10, 27, 22, 92, "#c9e4c5",
     ["LOGIK", "", "BMP390", "DRV8833", "Servo 3/4", "J_MOT", "", "74HC138", "74HC4051", "2x AP2112", "", "J_STACK 2x10"]),
    ("FUNK", -27, -9, 92, 120, "#c9e4c5", ["E22-400T22S", "(SMD, IPEX)", "Pigtail zur", "Spitze, J_GPS"]),
    ("SIGNAL", -8, 8, 103, 120, "#cfd8f0", ["2x LED, LIS3MDL", "Qwiic, CAM"]),
    ("PYRO", 9, 27, 92, 120, "#cfd8f0", ["4x J_PYRO", "(3/4 DNP)", "J_ARM, Summer", "SHT40"]),
]
KEEPOUTS = [("SD", -8, 8, 24, 30), ("USB-Stecker", -8, 8, 91, 103)]

# Cross-section envelopes (name, x0, x1, y0, y1) in mm, checked against tube and rods
ENVELOPES = [
    ("Teensy auf Buchsenleisten", -8.9, 8.9, BOARD_T / 2, 13.5),
    ("Elko 470 uF stehend", -24.0, -16.0, BOARD_T / 2, 11.8),
    ("LoRa E22-400T22S SMD", -26.0, -10.0, BOARD_T / 2, 4.5),
    ("Pyro-Klemmen / Summer", 12.0, 25.0, BOARD_T / 2, 11.0),
    ("Servo-Stecker liegend", 4.0, 26.0, BOARD_T / 2, 7.0),
    ("LiPo 2S im Traeger", -12.75, 12.75, -12.5, -3.5),
    ("LiPo 1S im Traeger (hinter dem 2S)", -15.0, 15.0, -11.0, -3.5),
]


def check_geometry():
    R = TUBE_ID / 2 - 0.5
    report = []
    for name, x0, x1, y0, y1 in ENVELOPES + [("Platine", -BOARD_W / 2, BOARD_W / 2, -BOARD_T / 2, BOARD_T / 2)]:
        r = max(math.hypot(x, y) for x in (x0, x1) for y in (y0, y1))
        assert r < R, f"{name} reaches r={r:.1f} mm > {R} mm"
        for rx, ry in RODS:   # distance from rod centre to the box
            dx = max(x0 - rx, 0, rx - x1)
            dy = max(y0 - ry, 0, ry - y1)
            gap = math.hypot(dx, dy) - ROD_D / 2
            assert gap > 0.5, f"{name} touches rod ({rx},{ry}): gap {gap:.2f} mm"
        report.append((name, r))
    t = TEENSY
    assert t["v0"] - 6 >= 22 and t["v1"] + 12 <= BOARD_L, "Teensy keepouts leave the board"
    return report


def write_dxf(path):
    ents = []
    hw, L, cr = BOARD_W / 2, BOARD_L, CORNER_R

    def line(p, q):
        ents.append(f"0\nLINE\n8\nEdge.Cuts\n10\n{p[0]:.4f}\n20\n{p[1]:.4f}\n30\n0.0\n"
                    f"11\n{q[0]:.4f}\n21\n{q[1]:.4f}\n31\n0.0\n")

    def arc(cx, cy, a0, a1):
        ents.append(f"0\nARC\n8\nEdge.Cuts\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n40\n{cr:.4f}\n50\n{a0}\n51\n{a1}\n")

    def circle(x, y, r):
        ents.append(f"0\nCIRCLE\n8\nEdge.Cuts\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n40\n{r:.4f}\n")

    line((-hw + cr, 0), (hw - cr, 0))
    line((hw, cr), (hw, L - cr))
    line((hw - cr, L), (-hw + cr, L))
    line((-hw, L - cr), (-hw, cr))
    arc(-hw + cr, cr, 180, 270)
    arc(hw - cr, cr, 270, 360)
    arc(hw - cr, L - cr, 0, 90)
    arc(-hw + cr, L - cr, 90, 180)
    for x, y in HOLES:
        circle(x, y, HOLE_D / 2)
    path.write_text("0\nSECTION\n2\nENTITIES\n" + "".join(ents) + "0\nENDSEC\n0\nEOF\n")


def write_svg(path, report):
    s = 5.0                                   # px per mm
    W, H = 900, 760
    tx0, ty0 = 70, 60                         # top view: origin of u=-27 / v=120 corner
    hw = BOARD_W / 2

    def X(u): return tx0 + (u + hw) * s
    def Y(v): return ty0 + (BOARD_L - v) * s

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="{tx0}" y="28" font-size="15" font-weight="bold">Draufsicht (Bestückungsseite)</text>',
           f'<text x="{X(0)}" y="{ty0-10}" font-size="11" text-anchor="middle">↑ Spitze</text>',
           f'<text x="{X(0)}" y="{Y(0)+18}" font-size="11" text-anchor="middle">↓ TVC</text>',
           f'<rect x="{X(-hw)}" y="{Y(BOARD_L)}" width="{BOARD_W*s}" height="{BOARD_L*s}" rx="{CORNER_R*s}" '
           f'fill="#2f6b3a" fill-opacity="0.12" stroke="#2f6b3a" stroke-width="3"/>']
    for label, u0, u1, v0, v1, col, items in ZONES:
        out.append(f'<rect x="{X(u0)}" y="{Y(v1)}" width="{(u1-u0)*s}" height="{(v1-v0)*s}" fill="{col}" stroke="#777"/>')
        cx = X((u0 + u1) / 2)
        out.append(f'<text x="{cx}" y="{Y(v1)+(26 if v1 == BOARD_L else 14)}" font-size="11" font-weight="bold" text-anchor="middle">{label}</text>')
        for i, it in enumerate(items):
            out.append(f'<text x="{cx}" y="{Y(v1)+(39 if v1 == BOARD_L else 27)+i*12}" font-size="9.5" text-anchor="middle">{it}</text>')
    for label, u0, u1, v0, v1 in KEEPOUTS:
        out.append(f'<rect x="{X(u0)}" y="{Y(v1)}" width="{(u1-u0)*s}" height="{(v1-v0)*s}" fill="white" '
                   f'stroke="#c0392b" stroke-dasharray="4 3"/>')
        out.append(f'<text x="{X(0)}" y="{Y((v0+v1)/2)+4}" font-size="9.5" fill="#c0392b" text-anchor="middle">{label} frei</text>')
    t = TEENSY
    out.append(f'<rect x="{X(t["u0"])}" y="{Y(t["v1"])}" width="{(t["u1"]-t["u0"])*s}" height="{(t["v1"]-t["v0"])*s}" '
               f'fill="#3a6ea5" fill-opacity="0.35" stroke="#1d3d63" stroke-width="2"/>')
    out.append(f'<text x="{X(0)}" y="{Y(75)}" font-size="12" font-weight="bold" text-anchor="middle" '
               f'transform="rotate(-90 {X(0)} {Y(75)})">Teensy 4.1</text>')
    out.append(f'<rect x="{X(IMU[0])-7.5}" y="{Y(IMU[1])-7.5}" width="15" height="15" fill="#c0392b"/>')
    out.append(f'<text x="{X(0)}" y="{Y(IMU[1])+22}" font-size="10" fill="#c0392b" text-anchor="middle">IMU</text>')
    for x, y in HOLES:
        out.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{HOLE_D/2*s}" fill="white" stroke="black" stroke-width="1.5"/>')
    out.append(f'<text x="{X(hw)+8}" y="{Y(BOARD_L)+10}" font-size="10">{BOARD_W:.0f} × {BOARD_L:.0f} mm</text>')

    # cross-section
    cx0, cy0 = 620, 300
    out.append(f'<text x="{cx0-170}" y="28" font-size="15" font-weight="bold">Querschnitt (Blick von der Spitze)</text>')
    def CX(x): return cx0 + x * s
    def CY(y): return cy0 - y * s
    out.append(f'<circle cx="{cx0}" cy="{cy0}" r="{37.5*s}" fill="#eee" stroke="#999"/>')
    out.append(f'<circle cx="{cx0}" cy="{cy0}" r="{TUBE_ID/2*s}" fill="white" stroke="#555" stroke-dasharray="6 4"/>')
    for name, x0, x1, y0, y1 in ENVELOPES:
        col = "#3a6ea5" if "Teensy" in name else ("#f4d6a0" if "LiPo" in name else "#bbb")
        out.append(f'<rect x="{CX(x0)}" y="{CY(y1)}" width="{(x1-x0)*s}" height="{(y1-y0)*s}" fill="{col}" '
                   f'fill-opacity="0.6" stroke="#444"/>')
    out.append(f'<rect x="{CX(-hw)}" y="{CY(BOARD_T/2)}" width="{BOARD_W*s}" height="{BOARD_T*s}" fill="#2f6b3a"/>')
    for x, y in RODS:
        out.append(f'<circle cx="{CX(x)}" cy="{CY(y)}" r="{ROD_D/2*s+1}" fill="black"/>')
    out.append(f'<circle cx="{cx0}" cy="{cy0}" r="3" fill="#c0392b"/>')
    out.append(f'<text x="{cx0}" y="{CY(-16)}" font-size="10" text-anchor="middle">LiPo im Träger</text>')
    out.append(f'<text x="{cx0}" y="{CY(15.5)}" font-size="10" text-anchor="middle">Teensy</text>')
    ly = 520
    notes = [f"Gestrichelt: Rohr innen Ø {TUBE_ID:.0f} mm (Annahme), grau: außen Ø 75 mm.",
             "Schwarz: die 8 M2-Stangen, sie laufen an den Platinenkanten vorbei.",
             "Rot: Rollachse in der Platinenebene, die IMU sitzt darauf.",
             f"Größter Hüllradius {max(r for _, r in report):.1f} mm (Projektion aller Bauteile).",
             "Bauhöhe am Rand (|u| > 25 mm) höchstens 5 mm wegen der Stangen.",
             "Zonen sind Platzierungsvorgaben, kein Layout."]
    for i, n in enumerate(notes):
        out.append(f'<text x="{cx0-170}" y="{ly+i*18}" font-size="11.5">{n}</text>')
    out.append("</svg>")
    path.write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    rep = check_geometry()
    write_dxf(HERE / "mainboard_outline.dxf")
    write_svg(HERE / "mainboard_placement.svg", rep)
    for n, r in rep:
        print(f"  {n:28s} reaches r = {r:5.1f} mm")
    print(f"ok: sled {BOARD_W:.0f} x {BOARD_L:.0f} mm fits tube ID {TUBE_ID} mm, files written to {HERE}")
