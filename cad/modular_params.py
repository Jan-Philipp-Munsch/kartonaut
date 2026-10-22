"""Modulbauweise Kartonaut 1 (Erstflug), Stand 22.10.2026: Maße für Bauanleitung, Zeichnungen und Bohrschablonen.

Ersetzt für den Erstflug den Ring-Stack mit acht M2-Gewindestangen. Der Flugcomputer ist jetzt eine Platine
(Mainboard rev B1, 54 × 120 mm, 4 × M3); sie sitzt auf einem gedruckten Schlitten, der an seinem oberen Ende,
dem Ausstoßspant, im Avionik-Kuppler hängt. Unverändert übernommen aus params.py: Rohr, Kuppler, Spitze,
Kardan, Motor, Platine. Begründungen: docs/Bauanleitung_Kartonaut1.md §1 und §2.

Koordinaten wie params.py: z längs ab der Düsenebene (+z zur Spitze). Winkel phi am Rohr von +x (Längslinie 0°,
Schlüsselschalter) zu +y (Luke A, Bestückungsseite der Platine), also phi = 90° Luke A, 270° Luke B.
h = Abstand von der Unterkante des jeweiligen Rohrs (für die Bohrschablonen).
"""
import math
import params as P

# --------------------------------------------------------------------------- Rumpf: 200 + 500 mm
# Unteres Rohr 200 mm (aus einem 500er abgelängt), oberes Rohr 500 mm unverändert. Der Stoß liegt im
# Avionik-Kuppler, nicht im Fallschirmraum: der Kolben läuft frei durch das obere Rohr bis zur Spitze.
TUBE_BOTTOM_Z = P.TUBE_BOTTOM_Z                  # 20
LOWER_L = 200.0
UPPER_L = 500.0
JOINT_Z = TUBE_BOTTOM_Z + LOWER_L                # 220
TOP_Z = JOINT_Z + UPPER_L                        # 720 = Basis der Spitze
TUBE_OD, TUBE_ID = P.TUBE_OD, P.TUBE_ID
CIRC_TUBE = math.pi * TUBE_OD                    # 235,6 mm Abwicklung
CIRC_COUPLER = math.pi * P.COUPLER_OD            # 227,5 mm

# --------------------------------------------------------------------------- Lochbild, für alle Radialschrauben gleich
# Drei Schrauben bei 0°, 135°, 225°: drehsymmetrisch nur in einer Lage, also passt jedes Modul nur richtig herum.
# Frei von den Führungen der Startrampe (Stützen bei 60°, 180°, 300°, 20 mm breit: belegt 45,6 … 74,4° usw.).
SCREW_PHI = (0.0, 135.0, 225.0)
SCREW_HOLE_PAPER = 3.4          # Bohrung im Papprohr / Kuppler (M3 mit Spiel, Rand mit dünnem Sekundenkleber härten)
INSERT_HOLE = (4.0, 5.0)        # Einschmelzmutter M3 kurz (Außen ca. 4,5, Länge 4): Bohrung Ø × Tiefe im Druckteil
RAMP_GUIDE_PHI = (60.0, 180.0, 300.0)   # cad/landingpad.py (Branch landepad), Führungen bis h = 160 über der Rohrunterkante
RAMP_GUIDE_H = 160.0
RAMP_GUIDE_GAP = 1.5

# --------------------------------------------------------------------------- Antriebsmodul (Kardan), wie params.py
TVC_SCREW_Z = P.TVC_RING_Z + P.OUTER_FLANGE_H / 2       # 51
MOTOR_CLAMP_Z = P.MOTOR_TUBE_Z[0] + 6.0                  # 51: Klemmschraube unten am Motorrohr, von unten mit Inbus erreichbar

# --------------------------------------------------------------------------- Schlüsselring (geklebt, unteres Rohr)
KEY_RING_Z = P.KEY_COLLAR_Z                    # (107, 125)
KEY_RING_OD = P.COUPLER_OD                     # 72,4 im Rohr 72,6, geklebt
KEY_RING_ID = 48.0                             # Gitter und Kabelraum; der Ring selbst ist dünnwandig
KEY_RING_WALL = 2.5
KEY_BOSS = (22.0, 15.0)                        # Auge für den Schalter: tangentiale Breite, radiale Tiefe
KEY_Z = sum(KEY_RING_Z) / 2                    # 116
KEY_PHI = 0.0
KEY_HOLE_D = P.KEY_HOLE_D                      # 12,4
KEY_NUT = (16.5, 3.5)                          # [Annahme] Mutter des Schlüsselschalters: Schlüsselweite, Höhe; Tasche von innen
GRID_SLOTS = ((270.0, 9.0, 7.0), (0.0, 9.0, 7.0))   # Kabelgitter: (phi, Breite tangential, Tiefe radial) für die Servokabel

# --------------------------------------------------------------------------- Avionik-Kuppler (Klima 150, im unteren Rohr verklebt)
COUPLER_Z = (KEY_RING_Z[1] + 2.0, KEY_RING_Z[1] + 2.0 + P.COUPLER_L)   # 127 … 277
COUPLER_GLUE = JOINT_Z - COUPLER_Z[0]          # 93 mm im unteren Rohr verklebt
COUPLER_FREE = COUPLER_Z[1] - JOINT_Z          # 57 mm ragt heraus, darauf steckt das obere Rohr

# --------------------------------------------------------------------------- Avionik-Schlitten
DISC_Z = (COUPLER_Z[0] + 4.0, COUPLER_Z[0] + 7.0)       # untere Scheibe 131 … 134, 3 mm mit Erleichterungslöchern
DISC_OD = P.COUPLER_ID - 0.6                             # 69,6
DISC_CABLE_D = 22.0                                      # Kabeldurchlass, nach dem Einbau mit Schaumstopfen dicht
DISC_PLUG_WINDOW = (-19.0, 15.0, -2.0, 10.0)             # x0, x1, y0, y1: Fenster für J5, J6 (Servos) und J1 (XT30)
DISC_LIGHT_PHI, DISC_LIGHT_R, DISC_LIGHT_D = (230.0, 260.0, 280.0, 310.0), 24.0, 9.0   # Erleichterungslöcher
BOARD_V0_Z = DISC_Z[1] + 9.0                             # 143: v = 0 der Platine; die Stecker der TVC-Stirnseite (12 mm) stecken im Fenster der Scheibe
BOARD_W, BOARD_L, BOARD_T = P.BOARD_W, P.BOARD_L, P.BOARD_T
BOARD_HOLES = P.BOARD_HOLES                              # (u, v) 4 × M3
POST_D = 7.0                                             # Säulen mit Einschmelzmutter unter den Platinenlöchern
TRAY_FLOOR_Y = -14.5                                     # Unterkante des Trägerbodens (Querschnitt, y = Platinennormale)
TRAY_WALL = 1.6
BAT2S = dict(l=56.0, w=25.5, h=8.0, v0=8.0)              # rev B1 §2: 2S bei v 8 … 64
BAT1S = dict(l=50.0, w=30.0, h=7.0, v0=68.0)             # rev B1 §2: 1S ca. 50 × 30 × 7 bei v 68 … 118
STRAP_SLOT = (2.5, 16.0)                                 # Klettband-Schlitze im Boden (Breite längs, Länge quer)

# Ausstoßspant = oberes Ende des Schlittens: Zapfenring im Kuppler + Flansch auf der Kupplerkante
SPIGOT_Z = (BOARD_V0_Z + BOARD_L + 2.0, COUPLER_Z[1])    # 259 … 277
SPIGOT_OD = P.COUPLER_ID - 0.4                           # 69,8
SPIGOT_ID = 62.0                                         # Wand 3,9 mm, an den Schrauben Augen nach innen
FLANGE_Z = (COUPLER_Z[1], COUPLER_Z[1] + 4.0)            # 277 … 281, liegt mit Moosgummi-Dichtring auf der Kupplerkante; 4 mm PETG
                                                         # tragen 0,7 bar Ausstoßdruck mit ca. 7 MPa Biegespannung (frei aufliegende Kreisplatte)
FLANGE_OD = TUBE_ID - 0.4                                # 72,2
JOINT_SCREW_Z = SPIGOT_Z[1] - 8.0                        # 269: 3 × M3 durch oberes Rohr + Kuppler in den Zapfenring, 8 mm unter der Kupplerkante
BOSS_D = 10.0                                            # Schraubenauge im Zapfenring; bei 0° liegt es über der Platinenkante
CHARGE_CUP = dict(x=0.0, y=14.0, d=P.CHARGE_WELL_D, h=P.CHARGE_WELL_H)   # Ladungsschale wie params.py
FEEDTHRU = [(-7.0, 25.0), (7.0, 25.0)]                   # 2 × M2 Messing als Zünder-Klemmen (unten Kabel zum Pyro-Stecker)
FEEDTHRU_D = 2.2
EYE_BOLT = dict(x=0.0, y=-16.0, d=4.3)                   # Ringschraube M4 mit Mutter und Scheibe (Schockschnur)
TRAY_TO_SPIGOT = [(-20.0, -9.0), (20.0, -9.0)]           # 2 × M3 axial: Träger an den Zapfenring (x = u, y)
TRAY_TO_DISC = [(-20.0, -9.0), (20.0, -9.0)]             # 2 × M3 axial: untere Scheibe an den Träger

# Platinen-Lage längs (rev B1): Stecker an den Stirnseiten
PLUGS_TVC_END = [("Servo Gieren J5", -14.4), ("Servo Nicken J6", -2.8), ("XT30 2S J1", 10.2)]   # v = 0, Stecker zeigen nach -v
PLUGS_NOSE_END = [("Pyro 1 J9", -13.0), ("Pyro 2 J10", -3.5), ("Pyro 3 J19 (DNP)", 6.0), ("Pyro 4 J20 (DNP)", 15.5)]
PLUG_REACH = 12.0                                        # XH-Stecker mit Knickschutz ragen ca. 12 mm über die Stirnkante

# --------------------------------------------------------------------------- Luken (ohne Stangen frei wählbar)
# Platinenmaße v: Teensy 30 … 91, SD-Karte am TVC-Ende (Auswurf nach -v bis v ≈ 18), Micro-USB-Stecker v 91 … 113.
# Luke A ist zweigeteilt, damit kein Fenster den Rohrstoß kreuzt: A1 (SD) im unteren Rohr, A2 (USB) als Kerbe im oberen.
HATCH_W = 20.0
HATCH_A1 = dict(phi=90.0, v=(14.0, 40.0))     # z 151 … 177
HATCH_A2 = dict(phi=90.0, v=(87.0, 116.0))    # z 224 … 253; im oberen Rohr als Kerbe ab der Unterkante (h' 0 … 33)
HATCH_B = dict(phi=270.0, v=(22.0, 66.0), w=22.0)   # z 165 … 209, Schalterbrett

# Schalterbrett (Luke B) jetzt zweispaltig, 18 mm breit statt 11 mm zwischen den Stangen
PANEL_W, PANEL_T = 18.0, 2.0
PANEL_Y = (-33.0, -31.0)
PANEL_PARTS = [  # Name, u-Mitte, v0, v1, Breite u (v wie die Platine)
    ("Hauptschalter 2-polig (J_SW)", -4.5, 31.0, 43.0, 6.0),
    ("USB-C Laden 1S (J_CHG1)", -4.5, 47.0, 56.0, 9.0),
    ("Lade-LED", -4.5, 59.0, 62.0, 3.0),
    ("XT30 Laden 2S (J_CHG2)", 4.5, 31.0, 41.2, 5.2),
    ("XH-3 Balancer 2S", 4.5, 45.0, 52.5, 7.5),
]
PANEL_COLS = [(0.0, 26.5), (4.5, 60.0)]   # (u, v) zwei Säulen Ø 7 zum Trägerboden, M3 von innen; frei von den Bauteilen
PANEL_COL_D = 7.0
# Druckausgleich für das Barometer (BMP390 bei v ≈ 80): 4 × Ø 2 durch Rohr und Kuppler, unter dem Rohrstoß
BARO_Z = 210.0
BARO_PHI = (45.0, 135.0, 225.0, 315.0)
BARO_D = 2.0

# --------------------------------------------------------------------------- Bergung
PISTON_GAP = P.PISTON_GAP                                 # 11 über dem Flansch
PISTON_Z = (FLANGE_Z[1] + PISTON_GAP, FLANGE_Z[1] + PISTON_GAP + P.PISTON_L)   # 294 … 334
CHUTE_Z = (PISTON_Z[1] + 5.0, PISTON_Z[1] + 5.0 + P.CHUTE_L)                   # 339 … 569
NOSE_SHOULDER_Z = (TOP_Z - P.NOSE_SHOULDER_L, TOP_Z)                           # 645 … 720
NOSE_EYE_Z = TOP_Z - P.NOSE_BULKHEAD_BELOW_BASE                                # 638,5
CORD_BAY = NOSE_EYE_Z - CHUTE_Z[1]
SHEAR_PIN_Z = TOP_Z - 15.0                                # 2 × M2 Nylon als Abscherstifte durch Rohr und Schulter
SHEAR_PIN_PHI = (90.0, 270.0)
SHEAR_PIN_D = 2.0

# --------------------------------------------------------------------------- Massen
# Basis: cad/mass_properties.md, Erstflug 700 mm (761 g). Was entfällt, steht hier; was neu dazukommt, rechnet
# modular.py aus den CAD-Volumina (Druckteile) plus den Zukaufteilen unten.
MASS_BASE_ERSTFLUG = 761.0
# Das alte Modell setzt seine Druckteile mit 64 g an; mit derselben Regel wie hier (Volumen × 1,27 × 0,75) wären es
# 119 g (modular.py rechnet das bei jedem Lauf aus den alten Teilen nach). Der faire Vergleich steht in masses.json.
MASS_REMOVED = [  # (Teil im alten Massenmodell, Gramm)
    ("8 Gewindestangen M2", 30.0),
    ("Endring unten", 7.5),
    ("Endplatte oben (Spant mit Ladungsschale)", 17.5),
    ("Träger (gedruckt)", 15.0),
    ("Stoßkuppler 80 mm im Fallschirmraum", 18.0),
    ("Schlüsselschalter-Kragen", 8.0),
    ("Schalterbrett", 6.0),
    ("Kolbenplatte", 10.0),
    ("9 × M2 am Kuppler", 1.0),
    ("Spitze Spant + Öse", 3.0),
]
MASS_ADDED_HW = [  # Zukaufteile, die das alte Modell nicht hatte
    ("Ringschraube M4 mit Mutter und 2 Scheiben", 4.0),
    ("Einschmelzmuttern M3 (14) und Schrauben M3 (14)", 6.0),
    ("2 Zünder-Klemmen M2 Messing mit Muttern", 1.5),
    ("Moosgummi-Dichtring unter dem Flansch, Schaumstopfen", 1.0),
]
PRINT_RHO = 1.27            # g/cm³ PETG
PRINT_FILL = 0.75           # [Annahme] dünnwandige Teile: Wände fast voll, Rest 20 % Füllung


def h_lower(z):
    return z - TUBE_BOTTOM_Z


def h_upper(z):
    return z - JOINT_Z


def v_to_z(v):
    return BOARD_V0_Z + v


def mass_estimate(printed_g):
    """printed_g: Gramm der neuen Druckteile (aus modular.py)."""
    return MASS_BASE_ERSTFLUG - sum(m for _, m in MASS_REMOVED) + printed_g + sum(m for _, m in MASS_ADDED_HW)


def tube_min():
    """Kürzestes Rohr (Unterkante bis Spitzenbasis) mit dieser Stapelfolge."""
    return CHUTE_Z[1] + P.CORD_BAY_MIN + P.NOSE_BULKHEAD_BELOW_BASE - TUBE_BOTTOM_Z


def checks():
    """Geometrische Plausibilität der Zahlen oben; Rückgabe: Liste (ok, Text)."""
    out = []
    def chk(ok, txt):
        out.append((bool(ok), txt))
    chk(COUPLER_GLUE >= 0.75 * TUBE_OD, f"Kuppler im unteren Rohr verklebt: {COUPLER_GLUE:.0f} mm (≥ 0,75 D = {0.75 * TUBE_OD:.0f})")
    chk(COUPLER_FREE >= 0.75 * TUBE_OD, f"Kuppler im oberen Rohr: {COUPLER_FREE:.0f} mm (≥ 0,75 D = {0.75 * TUBE_OD:.0f})")
    chk(BOARD_V0_Z + BOARD_L + 0.5 <= JOINT_SCREW_Z - BOSS_D / 2, f"Platine endet bei z = {BOARD_V0_Z + BOARD_L:.0f} unter dem Schraubenauge bei 0° (ab {JOINT_SCREW_Z - BOSS_D / 2:.0f})")
    chk(BOARD_V0_Z - PLUG_REACH >= DISC_Z[0], f"Stecker der TVC-Stirnseite enden bei z = {BOARD_V0_Z - PLUG_REACH:.0f}, im Fenster der Scheibe ({DISC_Z[0]:.0f} … {DISC_Z[1]:.0f})")
    chk(BOARD_V0_Z + BOARD_L + PLUG_REACH <= FLANGE_Z[0], f"Pyro-Stecker bis z = {BOARD_V0_Z + BOARD_L + PLUG_REACH:.0f}, im Zapfenring (r < {SPIGOT_ID / 2:.0f}) bis zur Platte bei {FLANGE_Z[0]:.0f}")
    corner = math.hypot(BOARD_W / 2, 0.0)
    chk(corner < SPIGOT_ID / 2, f"Platinenecke r = {corner:.1f} < Zapfenring innen {SPIGOT_ID / 2:.1f} (Stecker passen hinein)")
    tray_corner = math.hypot(BOARD_W / 2, TRAY_FLOOR_Y)
    chk(tray_corner < P.COUPLER_ID / 2 - 0.5, f"Trägerecke r = {tray_corner:.1f} < Kuppler innen {P.COUPLER_ID / 2:.1f} − 0,5")
    pc = math.hypot(PANEL_W / 2, PANEL_Y[0])
    chk(pc < P.COUPLER_ID / 2 - 0.3, f"Schalterbrett-Ecke r = {pc:.2f} < {P.COUPLER_ID / 2 - 0.3:.2f}")
    for name, hd in (("A1", HATCH_A1), ("A2", HATCH_A2), ("B", HATCH_B)):
        z0, z1 = v_to_z(hd["v"][0]), v_to_z(hd["v"][1])
        crosses = z0 < JOINT_Z < z1
        chk(not crosses, f"Luke {name}: z {z0:.0f} … {z1:.0f}, Rohrstoß bei {JOINT_Z:.0f} {'gekreuzt' if crosses else 'nicht gekreuzt'}")
        chk(COUPLER_Z[0] + 5 < z0 and z1 < COUPLER_Z[1] - 5, f"Luke {name} liegt im Kuppler ({COUPLER_Z[0]:.0f} … {COUPLER_Z[1]:.0f})")
    for phi in SCREW_PHI + (KEY_PHI,):
        for g in RAMP_GUIDE_PHI:
            half = math.degrees(math.atan(10.0 / (TUBE_OD / 2 + RAMP_GUIDE_GAP))) + 5.0   # Führung 20 breit + Kopf
            d = abs((phi - g + 180) % 360 - 180)
            if d < half:
                out.append((False, f"Radialschraube/Schlüssel bei {phi:.0f}° liegt an der Führung {g:.0f}°"))
    chk(True, f"Schraubköpfe und Schlüssel frei von den Führungen bei {', '.join(f'{g:.0f}°' for g in RAMP_GUIDE_PHI)}")
    rot_unique = all(sorted(((p + r) % 360) for p in SCREW_PHI) != sorted(SCREW_PHI) for r in range(1, 360))
    chk(rot_unique, "Lochbild 0°/135°/225° passt nur in einer Drehlage")
    chk(tube_min() <= LOWER_L + UPPER_L, f"Rohr {LOWER_L + UPPER_L:.0f} mm ≥ Minimum {tube_min():.0f} mm (Schnurraum {CORD_BAY:.0f} mm)")
    chk(BARO_Z < JOINT_Z - 6, f"Barometer-Bohrungen bei z = {BARO_Z:.0f}, {JOINT_Z - BARO_Z:.0f} mm unter dem Rohrstoß")
    return out


if __name__ == "__main__":
    for ok, txt in checks():
        print("ok  " if ok else "FEHLER", txt)
    print("Masse: python cad/modular.py rechnet sie mit den Druckteilen")
