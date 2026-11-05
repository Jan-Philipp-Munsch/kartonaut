"""Zeichnungen zur LoRa-Antenne in Kartonaut 1 (docs/Bauanleitung_LoRa_Antenne.md), Stand 05.11.2026.

    python docs/img/antenne/antenne_zeichnungen.py

Erzeugt A1_lage_im_rohr.png (Längsschnitt, ganze Rakete und Ausschnitt Rohr B) und A2_aufbau_querschnitt.png
(Drahtmaße und Querschnitt auf Höhe des E22). Lagen und Längen aus cad/modular_params.py und cad/params.py;
Lage des E22 aus hardware/mainboard/kicad/gen_pcb.py (U10 bei u = -17,6, v = 61,5, ANT-Ende zur Spitze).
Der Antennenweg ist schematisch: genaue Lage am Schlitten anzeichnen.
"""
import math, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "cad"))
import modular_params as M
import params as P

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, Wedge, FancyArrowPatch

# --------------------------------------------------------------------------- Antenne (Rechnung wie im Text)
C0 = 299.792458                     # m·MHz
F_MHZ = 433.125                     # Kanal 0x17 (groundstation/firmware/src/Config.h, E22-Werksvorgabe)
K_WIRE = 0.95                       # [Annahme] Verkürzung dünner Draht, wie cad/groundbridge.py
L4 = C0 / F_MHZ / 4 * 1000          # 173,0 mm
L_ANT = round(L4 * K_WIRE)          # 164 → geschnitten wird 165
L_CUT = 165

R_IN = M.TUBE_ID_MEASURED / 2       # 36,25
V0 = M.BOARD_V0_Z                   # 167
E22_U, E22_V = -17.6, 61.5          # Platinenkoordinaten Modulmitte
E22 = dict(x0=E22_U - 8, x1=E22_U + 8, z0=V0 + E22_V - 13, z1=V0 + E22_V + 13)
Z_FEED = V0 + E22_V + 10.0          # ANT-Pad (Pin 12) am spitzenseitigen Ende, ≈ 238,5
PHI_ANT, R_ANT = 128.0, 30.0        # Drahtlage an der Wand (Querschnitt)
ANT_X, ANT_Y = R_ANT * math.cos(math.radians(PHI_ANT)), R_ANT * math.sin(math.radians(PHI_ANT))
Z_TIP_MIN = M.GIMBAL_TOP_Z + 10.0   # 103: Abstand zum Kardan
LIFT = math.hypot(ANT_X - E22_U, ANT_Y - 3.0)       # vom Pad zur Wandlage, ≈ 21
RUN = Z_FEED - Z_TIP_MIN                              # Längsteil bis z = 103
HOOK = L_CUT - LIFT - RUN

COL = dict(paper="#e9dcc0", printed="#dfe8f4", board="#2e7d4f", bat="#e8c46a", metal="#9a9a9a", ant="#c62828",
           gps="#3b9e63", chute="#f3e3ef", dim="#2350a0", text="#222222", keep="#c62828", wood="#c9a26b")
plt.rcParams.update({"font.size": 8.5, "font.family": "DejaVu Sans", "axes.linewidth": 0.6})


def rect(ax, x0, x1, y0, y1, fc, ec="#333333", lw=0.6, **kw):
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec=ec, lw=lw, **kw))


def dim_h(ax, x0, x1, y, txt, off=2.5, col=COL["dim"]):
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", color=col, lw=0.7, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2, y + off, txt, color=col, ha="center", va="bottom", fontsize=8)


def dim_v(ax, x, y0, y1, txt, off=2.5, col=COL["dim"], side="right"):
    ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", color=col, lw=0.7, shrinkA=0, shrinkB=0))
    ha = "left" if side == "right" else "right"
    ax.text(x + (off if side == "right" else -off), (y0 + y1) / 2, txt, color=col, ha=ha, va="center", fontsize=8,
            rotation=90)


# --------------------------------------------------------------------------- A1 Längsschnitt (Rakete liegt, Spitze rechts)
def rocket_section(ax, z_lo, z_hi, detail):
    """Längsschnitt in der y-z-Ebene (Blick von +x): oben = +y = Bestückungsseite/Luke A, unten = -y = Akkus/Luke B."""
    ro, ri = P.TUBE_OD / 2, R_IN
    tubes = [("Rohr A", M.TUBE_A), ("Rohr B", M.TUBE_B), ("Rohr C", M.TUBE_C)]
    for name, (a, b) in tubes:
        for s in (1, -1):
            rect(ax, a, b, s * ri, s * ro, COL["paper"], lw=0.5)
        if detail or name != "":
            ax.text((max(a, z_lo) + min(b, z_hi)) / 2, ro + 3, name, ha="center", va="bottom", fontsize=8)
    # Luken (Lücke in der Wand)
    for hd, s in ((M.HATCH_A1, 1), (M.HATCH_A2, 1), (M.HATCH_B, -1)):
        a, b = M.v_to_z(hd["v"][0]), M.v_to_z(hd["v"][1])
        rect(ax, a, b, s * ri, s * ro, "white", ec="#888888", lw=0.4, ls="--")
    # Kuppler J1 und Spitzenkuppler
    for (a, b) in (M.J1_COUPLER, M.NOSE_COUPLER_Z):
        for s in (1, -1):
            rect(ax, a, b, s * (P.COUPLER_ID / 2), s * ri, "#d9c9a3", lw=0.4)
    # Spitze
    zn0, zn1 = M.TUBE_C[1], M.TUBE_C[1] + P.NOSE_L
    ax.add_patch(Polygon([(zn0, ro), (zn1, 0), (zn0, -ro)], closed=True, fc="#f4f4f4", ec="#333333", lw=0.6))
    rect(ax, zn0 + M.NOSE_HOOK_DEPTH - 2, zn0 + M.NOSE_HOOK_DEPTH + 2, -30, 30, COL["wood"], lw=0.4)
    # Kardan und Motor
    rect(ax, 3, M.GIMBAL_TOP_Z, -(P.COUPLER_ID / 2 - 1), P.COUPLER_ID / 2 - 1, "#cfd8e3", lw=0.5)
    rect(ax, 0, M.MOTOR_L, -P.MOTOR_D / 2, P.MOTOR_D / 2, "#b0a48a", lw=0.5)
    for zc in (31.5,):
        for s in (1, -1):
            rect(ax, zc - 9.5, zc + 9.5, s * 22, s * 33, COL["metal"], lw=0.4)
    # Schraubring, untere Scheibe, Spant/Band
    for s in (1, -1):
        rect(ax, *M.J1_RING["z"], s * 33.0, s * 34.9, COL["printed"], lw=0.4)
    rect(ax, *M.DISC_Z, -M.DISC_OD / 2, M.DISC_OD / 2, COL["printed"], lw=0.5)
    rect(ax, M.BAND_Z[0] - M.PLATE_T + 5, M.BAND_Z[1], -ro, ro, COL["printed"], lw=0.5)
    rect(ax, M.SPIGOT_B["z"][0], M.BAND_Z[0], -36.0, -34.0, COL["printed"], lw=0.3)
    rect(ax, M.SPIGOT_B["z"][0], M.BAND_Z[0], 34.0, 36.0, COL["printed"], lw=0.3)
    # Platine, Teensy, E22, Akkus, GPS, Schalterbrett
    rect(ax, V0, V0 + P.BOARD_L, -P.BOARD_T / 2, P.BOARD_T / 2, COL["board"], lw=0.4)
    rect(ax, V0 + P.TEENSY["v0"], V0 + P.TEENSY["v1"], 0.8, 12.8, "#4a7bb7", lw=0.4, alpha=0.35)
    rect(ax, E22["z0"], E22["z1"], 0.8, 3.6, "#1f4e79", lw=0.4)
    y0 = M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3
    for bat in (M.BAT2S, M.BAT1S):
        rect(ax, V0 + bat["v0"], V0 + bat["v0"] + bat["l"], y0, y0 + bat["h"], COL["bat"], lw=0.4)
    rect(ax, V0, V0 + P.BOARD_L, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + M.TRAY_WALL, COL["printed"], lw=0.3)
    rect(ax, M.GPS["z_top"] - M.GPS["h"], M.GPS["z_top"], M.GPS["y"][0], M.GPS["y"][1], COL["gps"], lw=0.4)
    rect(ax, V0 + 20, V0 + 70, M.PANEL_Y[0], M.PANEL_Y[1], COL["printed"], lw=0.3)
    for pname, u in M.PLUGS_TVC_END:
        rect(ax, V0 - M.PLUG_REACH, V0, 0.8, 7.8, COL["metal"], lw=0.3)
    # CO2, Schirm
    rect(ax, M.CO2_Z0, M.CO2_Z0 + M.CO2["d"], -M.CO2["l"] / 2, M.CO2["l"] / 2, COL["metal"], lw=0.5)
    rect(ax, *M.CHUTE_Z, -M.CHUTE["d"] / 2, M.CHUTE["d"] / 2, COL["chute"], lw=0.4)
    # Antenne (Projektion in die y-z-Ebene)
    pts = [(Z_FEED, 3.0), (Z_FEED, ANT_Y), (Z_TIP_MIN, ANT_Y), (Z_TIP_MIN, ANT_Y - 9)]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=COL["ant"], lw=2.0 if detail else 1.6, solid_capstyle="round")
    ax.plot([Z_FEED], [3.0], "o", color=COL["ant"], ms=4 if detail else 3)
    # Trennstellen
    for z, txt, ls in ((M.TUBE_A[1], "T1 lösbar", ":"), (M.BAND_Z[0], "", ":"),
                       (M.BAND_Z[1], "T2/T3 lösbar", ":"), (M.TUBE_C[1], "T4 trennt im Flug", "-")):
        if z_lo <= z <= z_hi:
            ax.plot([z, z], [-46, 46], color="#555555" if ls == ":" else COL["keep"], lw=0.8, ls=ls)
            if detail or ls == "-":
                ax.text(z, -48, txt, ha="center", va="top", fontsize=7.5,
                        color=COL["keep"] if ls == "-" else "#555555")
    ax.set_xlim(z_lo, z_hi)
    ax.set_aspect("equal")
    ax.axis("off")


def fig_a1():
    fig = plt.figure(figsize=(11.0, 7.3))
    ax1 = fig.add_axes([0.03, 0.74, 0.94, 0.22])
    rocket_section(ax1, -5, M.TUBE_C[1] + P.NOSE_L + 5, detail=False)
    ax1.set_ylim(-58, 50)
    ax1.set_title("Kartonaut 1, Längsschnitt (Blick von +x, Spitze rechts): LoRa-λ/4-Draht rot", fontsize=10, loc="left")
    ax1.text(M.TUBE_C[1] + 70, 22, "Spitze geht am Gipfel ab:\nkeine Antenne über T4", fontsize=7.5, color=COL["keep"])
    ax1.add_patch(Rectangle((85, -46), 230, 92, fill=False, ec=COL["dim"], lw=0.8, ls="--"))
    ax1.text(87, -55, "Ausschnitt unten", color=COL["dim"], fontsize=7.5, va="top")

    ax = fig.add_axes([0.03, 0.0, 0.94, 0.74])
    rocket_section(ax, 66, 318, detail=True)
    ax.set_ylim(-62, 62)
    # Beschriftungen
    lab = dict(fontsize=8, color=COL["text"])
    ax.text(E22["z0"] + 1, 5.5, "E22 (U10)", **lab)
    ax.annotate("ANT-Pad (Pin 12)\nSpeisepunkt z ≈ %.0f" % Z_FEED, (Z_FEED, 3.0), (Z_FEED + 6, 12),
                fontsize=7.5, color=COL["ant"], arrowprops=dict(arrowstyle="-", color=COL["ant"], lw=0.6))
    ax.text(V0 + 66, 8.5, "Teensy", **lab)
    ax.text(V0 + 8, -10.2, "2S", **lab)
    ax.text(V0 + 68, -10.2, "1S", **lab)
    ax.text(M.GPS["z_top"] - M.GPS["h"] + 1, 30.5, "GPS", **lab)
    ax.text(V0 + 22, -30, "Schalterbrett (Luke B)", fontsize=7.5, color=COL["text"])
    ax.text(M.DISC_Z[0] - 1, -40, "untere\nScheibe", fontsize=7.5, ha="right")
    ax.text(M.GIMBAL_TOP_Z - 2, -12, "Kardan\n(Oberkante %d)" % M.GIMBAL_TOP_Z, fontsize=7.5, ha="right")
    ax.text(110, -28, "Schraubring J1", fontsize=7.5, ha="center")
    ax.text(M.BAND_Z[1] + 2, -20, "Spant\n(Druckschott)", fontsize=7.5)
    ax.text(V0 + 2, -3.5, "Platine (Masse = Gegengewicht)", fontsize=7, color="white",
            bbox=dict(fc=COL["board"], ec="none", pad=0.5))
    for hd, nm in ((M.HATCH_A1, "Luke A1"), (M.HATCH_A2, "Luke A2")):
        a, b = M.v_to_z(hd["v"][0]), M.v_to_z(hd["v"][1])
        ax.text((a + b) / 2, R_IN + 4.5, nm, ha="center", fontsize=7.5, color="#666666")
    # Maße der Antenne
    dim_h(ax, Z_TIP_MIN, Z_FEED, ANT_Y + 6, "Längsteil ≈ %.0f mm (z = %.0f … %.0f)" % (RUN, Z_TIP_MIN, Z_FEED))
    dim_h(ax, M.GIMBAL_TOP_Z, Z_TIP_MIN, ANT_Y - 4, "≥ 10", off=1.0)
    ax.text(Z_TIP_MIN + 2, ANT_Y - 13, "Haken ≈ %.0f mm\nquer an der Wand" % HOOK, fontsize=7.5, color=COL["ant"])
    ax.text(128, 13, "Gesamtlänge ab Lötstelle %d mm\n(λ/4 · 0,95 bei %s MHz)" % (L_CUT, str(F_MHZ).replace(".", ",")),
            fontsize=8.5, color=COL["ant"], weight="bold")
    # Abstand GPS
    ax.annotate("", (Z_FEED, 24), (M.GPS["z_top"] - M.GPS["h"], 24),
                arrowprops=dict(arrowstyle="<->", color=COL["dim"], lw=0.7))
    ax.text((Z_FEED + M.GPS["z_top"] - M.GPS["h"]) / 2, 25.5, "%.0f" % (M.GPS["z_top"] - M.GPS["h"] - Z_FEED),
            color=COL["dim"], ha="center", fontsize=7.5)
    ax.text(70, -58, "Maße in mm, z ab Düse. Lagen aus cad/modular_params.py, E22 aus kicad/gen_pcb.py; "
            "Draht in die Schnittebene projiziert (liegt bei φ ≈ %d°, siehe A2). Schematisch, am Schlitten anzeichnen." % PHI_ANT,
            fontsize=7, color="#555555")
    fig.savefig(HERE / "A1_lage_im_rohr.png", dpi=170, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


# --------------------------------------------------------------------------- A2 Aufbau und Querschnitt
def fig_a2():
    fig = plt.figure(figsize=(11.0, 5.2))
    # links: gestreckter Draht
    ax = fig.add_axes([0.01, 0.02, 0.57, 0.88])
    ax.set_title("Aufbau λ/4-Draht (gestreckt gezeichnet)", fontsize=10, loc="left")
    segs = [("Abheben", LIFT), ("Längsteil an der Wand, parallel zur Rohrachse", RUN), ("Haken", HOOK)]
    x = 0
    ax.plot([0, L_CUT], [0, 0], color=COL["ant"], lw=3, solid_capstyle="butt")
    for i, (nm, l) in enumerate(segs):
        ax.plot([x, x], [-4, 4], color="#444444", lw=0.6)
        yd = 10 if i != 2 else 16
        dim_h(ax, x, x + l, yd, ("%.0f  %s" % (l, nm)) if i == 1 else "%.0f" % l, off=1)
        if i != 1:
            ax.text(x + l / 2, yd + 5.5, nm, ha="center", va="bottom", fontsize=7.5, color=COL["dim"])
        x += l
    ax.plot([x, x], [-4, 4], color="#444444", lw=0.6)
    dim_h(ax, 0, L_CUT, 30, "%d mm ab der Lötstelle (nicht kürzer als 160 schneiden)" % L_CUT, off=1.5)
    # Pad, Schrumpfschlauch, Klebepunkte
    rect(ax, -3, 0, -2.5, 2.5, "#bbbbbb", lw=0.5)
    ax.text(-4, 3, "Pad 12 (ANT):\n2 mm abisoliert,\nverzinnt", ha="right", va="bottom", fontsize=7.5)
    rect(ax, 0, 12, -1.7, 1.7, "#333333", lw=0, alpha=0.40)
    xg1 = 6
    ax.add_patch(Circle((xg1, 0), 2.6, fc="#fff2a8", ec="#b59a00", lw=0.6, alpha=0.9))
    ax.annotate("Schrumpfschlauch über der Lötstelle;\nHeißkleber 1: Draht 5 mm hinter dem Pad\nauf der Platine festlegen (Zugentlastung)",
                (xg1, -2.6), (-28, -30), fontsize=7.5, arrowprops=dict(arrowstyle="-", lw=0.5))
    for xk in (LIFT + 22, LIFT + 55):
        rect(ax, xk - 3, xk + 3, -2.2, 2.2, "#c58b3a", lw=0.3, alpha=0.6)
    ax.annotate("Kapton-Streifen an Säule/Träger des Schlittens\n(nicht ans Rohr kleben: der Draht gehört zum Schlitten)",
                (LIFT + 55, -2.2), (40, -18), fontsize=7.5, arrowprops=dict(arrowstyle="-", lw=0.5))
    xd = LIFT + (Z_FEED - M.DISC_Z[1])       # Durchtritt untere Scheibe
    ax.add_patch(Circle((xd, 0), 2.6, fc="#fff2a8", ec="#b59a00", lw=0.6, alpha=0.9))
    ax.annotate("Heißkleber 2: Loch Ø 2 in der\nunteren Scheibe (z = %d … %d)" % M.DISC_Z, (xd, -2.6), (xd - 10, -32),
                fontsize=7.5, arrowprops=dict(arrowstyle="-", lw=0.5))
    rect(ax, L_CUT - 5, L_CUT + 1, -1.8, 1.8, "#333333", lw=0, alpha=0.45)
    ax.annotate("Ende: 5 mm Schrumpf-\nschlauch als Kappe", (L_CUT - 2, 1.8), (L_CUT - 42, 40),
                fontsize=7.5, arrowprops=dict(arrowstyle="-", lw=0.5))
    ax.text(-28, -50, "Draht: Kupfer massiv 0,6 … 0,8 mm mit Isolierung (Schalt-/Klingeldraht) oder versilberter Draht.\n"
                      "λ = c/f = %s mm, λ/4 = %s mm, × 0,95 = %d mm; 1 mm länger schneiden (Isolierung und Kleber kürzen mit)."
            % (("%.1f" % (C0 / F_MHZ * 1000)).replace(".", ","), ("%.1f" % L4).replace(".", ","), L_ANT),
            fontsize=7.5, color="#444444")
    ax.set_xlim(-30, L_CUT + 6)
    ax.set_ylim(-56, 46)
    ax.set_aspect("equal")
    ax.axis("off")

    # rechts: Querschnitt auf Höhe E22, Blick von der Spitze
    ax = fig.add_axes([0.60, 0.02, 0.39, 0.88])
    ax.set_title("Querschnitt bei z ≈ 230, Blick von der Spitze", fontsize=10, loc="left")
    ax.add_patch(Circle((0, 0), P.TUBE_OD / 2, fc=COL["paper"], ec="#333333", lw=0.6))
    ax.add_patch(Circle((0, 0), R_IN, fc="white", ec="#333333", lw=0.6))
    for phi, w in ((90.0, M.HATCH_W), (270.0, M.HATCH_B["w"])):
        hw = math.degrees(w / 2 / R_IN)
        ax.add_patch(Wedge((0, 0), P.TUBE_OD / 2 + 0.2, phi - hw, phi + hw, width=P.TUBE_OD / 2 - R_IN + 0.4,
                           fc="white", ec="#888888", lw=0.5, ls="--"))
    ax.text(8, R_IN + 4, "Luke A (90°)", ha="left", fontsize=7.5, color="#666666")
    ax.text(8, -R_IN - 7, "Luke B (270°)", ha="left", fontsize=7.5, color="#666666")
    rect(ax, -P.BOARD_W / 2, P.BOARD_W / 2, -P.BOARD_T / 2, P.BOARD_T / 2, COL["board"], lw=0.4)
    rect(ax, P.TEENSY["u0"], P.TEENSY["u1"], 0.8, 12.8, "#4a7bb7", lw=0.4, alpha=0.35)
    ax.text(0, 6, "Teensy", ha="center", fontsize=7)
    rect(ax, E22["x0"], E22["x1"], 0.8, 3.6, "#1f4e79", lw=0.4)
    ax.text(E22_U, 5, "E22", ha="center", fontsize=7)
    y0 = M.TRAY_FLOOR_Y + M.TRAY_WALL + 0.3
    rect(ax, -15, 15, y0, y0 + M.BAT1S["h"], COL["bat"], lw=0.4)
    ax.text(0, y0 + 1.5, "1S (2S darunter)", ha="center", fontsize=7)
    rect(ax, -24, 24, M.TRAY_FLOOR_Y, M.TRAY_FLOOR_Y + M.TRAY_WALL, COL["printed"], lw=0.3)
    rect(ax, -14, 14, M.PANEL_Y[0], M.PANEL_Y[1], COL["printed"], lw=0.3)
    ax.text(0, M.PANEL_Y[1] + 1, "Schalterbrett", ha="center", fontsize=7)
    # Antenne
    ax.plot([E22_U, ANT_X], [3.0, ANT_Y], color=COL["ant"], lw=1.8)
    ax.add_patch(Circle((ANT_X, ANT_Y), 1.6, fc=COL["ant"], ec="none"))
    ax.add_patch(Circle((ANT_X, ANT_Y), 20, fill=False, ec=COL["keep"], lw=0.7, ls="--"))
    ax.text(-82, 46, "λ/4-Draht bei φ ≈ %d°, r ≈ %d:\n%.0f mm vor der Platinenebene,\nneben Luke A, nicht davor" %
            (PHI_ANT, R_ANT, ANT_Y), fontsize=7.5, color=COL["ant"], va="center")
    ax.annotate("", (ANT_X - 1, ANT_Y + 1), (-60, 40), arrowprops=dict(arrowstyle="-", color=COL["ant"], lw=0.6))
    ax.text(-82, 12, "Kreis: 20 mm frei\nvon Kabeln und Litzen", fontsize=7.5, color=COL["keep"], va="center")
    xw0, xw1, yw0, yw1 = M.DISC_PLUG_WINDOW
    rect(ax, xw0, xw1, yw0, yw1, "none", ec="#555555", lw=0.6, ls=":")
    ax.text(-82, -40, "gepunktet: Steckerfenster der unteren\nScheibe (z = 155), Servo- und Akkukabel", fontsize=7,
            va="center", color="#444444")
    ax.annotate("Zünd-, Servo- und Akku-\nleitungen auf diese Seite,\nZündleitung verdrillt", (24, -14), (30, -50),
                fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5), ha="center", va="center")
    ax.plot([-46, 46], [0, 0], color="#bbbbbb", lw=0.4, ls="-.")
    ax.plot([0, 0], [-46, 46], color="#bbbbbb", lw=0.4, ls="-.")
    ax.text(46, 1, "0° (+x)", fontsize=7, ha="right", va="bottom", color="#777777")
    ax.set_xlim(-84, 52)
    ax.set_ylim(-60, 56)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(HERE / "A2_aufbau_querschnitt.png", dpi=170, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


if __name__ == "__main__":
    print(f"f = {F_MHZ} MHz, λ/4 = {L4:.1f} mm, × {K_WIRE} = {L_ANT} mm, geschnitten {L_CUT} mm")
    print(f"Speisepunkt z = {Z_FEED:.1f}, Abheben {LIFT:.1f}, Längsteil {RUN:.1f} (bis z = {Z_TIP_MIN:.0f}), Haken {HOOK:.1f}")
    print(f"Draht bei x = {ANT_X:.1f}, y = {ANT_Y:.1f}; GPS-Unterkante z = {M.GPS['z_top'] - M.GPS['h']:.1f}")
    fig_a1()
    fig_a2()
    print("geschrieben:", HERE / "A1_lage_im_rohr.png", HERE / "A2_aufbau_querschnitt.png")
