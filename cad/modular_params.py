"""Modulbauweise Kartonaut 1 (Erstflug), Stand 2 vom 22.10.2026 abends: Maße nach dem gebauten Kardan.

Grundlage sind Jans Messungen am gebauten Teil (Bilder und Maße vom 22.10.2026):
  Rohr A 125 mm mit dem Kardan (Schubstangen-Kardan mit 2 × W5652H, Servos flach über dem Außenrahmen, Hebel 15 mm,
  Stangen 2 mm Stahl), Kardanschrauben 4 × bei 90° auf 44 mm, zwei Servofenster ca. 20 × 20 bei 60 mm, Motor 93 mm
  bündig mit der Rohrunterkante; Rohr B 176 mm mit 4 alten Löchern bei 90° auf 44 mm; Kuppler 75 mm (halber Klima-
  Kuppler), bisher nur gesteckt. Schirm gepackt 100 × Ø 70. Die Klima-Spitze hat 25 mm über dem Schulterende eine
  Holzplatte mit Haken; der Schirm passt also nicht in die Spitze.

Entscheidungen (Jan, 22.10.2026): kein Rollmotor; Ausstoß mit CO₂-Kapsel (Aufbau ca. 10 g, ca. 2 l Gas) statt
Schwarzpulver; Schraubschalter statt Schlüsselschalter; GPS oben unter dem Spant, LoRa-Wendel unten am Schlitten.

Koordinaten: z längs ab der Düsenebene = Rohrunterkante (der Motor steht bündig), +z zur Spitze. Winkel phi am Rohr
ab der Längslinie 0° (eine Kardanschraube, von Jan markiert), von außen gesehen nach rechts wachsend. h = Abstand
von der Unterkante des jeweiligen Rohrs. Alle Radialschrauben liegen wie bei Jan auf 0°/90°/180°/270°.
"""
import math
import params as P

# --------------------------------------------------------------------------- Rohre und Stöße (gebaut bzw. geplant)
TUBE_OD, TUBE_ID = P.TUBE_OD, P.TUBE_ID
CIRC_TUBE = math.pi * TUBE_OD
TUBE_A = (0.0, 125.0)            # [Jan] Kardanrohr, Motor bündig unten
TUBE_B = (125.0, 301.0)          # [Jan] 176 mm, Avionikraum
J1_COUPLER = (125.0 - 37.5, 125.0 + 37.5)    # [Jan] Kuppler 75 mm (halber Klima-Kuppler), je 37,5 in A und B; wird in B verklebt
SCREW_PHI = (0.0, 90.0, 180.0, 270.0)        # [Jan] alle Radialschrauben
SCREW_HOLE_PAPER = 3.4
INSERT_HOLE = (4.0, 5.0)         # nicht mehr benutzt (Stand 2b: Muttern statt Einschmelzmuttern)
NUT = dict(sw=5.5, h=2.4, clear=0.25)   # M3-Mutter DIN 934 in einer Sechskant-Tasche, von innen eingedrückt (Tropfen Sekundenkleber)
TAP_HOLE = 2.6                   # Kernloch für M3 direkt im Druck (Platine, Scheibe, Schalterbrett: selten gelöst)

# --------------------------------------------------------------------------- Rohr A: Kardan (gebaut, nur Bestand)
GIMBAL_SCREW_Z = 44.0            # [Jan] 4 × bei 90°
GIMBAL_WINDOW = dict(w=20.0, z=(60.0, 80.0), phi=None)   # [Jan] ca. 20 × 20 ab 60 mm; Winkel noch offen (Servos zeigen nach außen)
MOTOR_L = 93.0                   # [Jan]
GIMBAL_TOP_Z = 93.0              # Oberkante Motorrohr (Druckdatei: 38 + 54,6); Rahmen enden bei 86,4
# Gedruckter Kardan = Blender-Dateien vom 12.06.2025 (E:\Archiv_Projekte\Blender\Dateien\): outer_gimbal_dual_TVC.blend
# ('Outer Gimbal (1).001', 'MotorTube.003'), inner_gimbal_dual_TVC.blend ('Inner Gimbal.002'), STL in cad/export/asbuilt/.
# Flanschbohrungen dort bei 45/135/225/315° in Flanschmitte (6 mm): Grundfläche bei z = 44 − 6 = 38, Drehung −45°.
GIMBAL_BASE_Z = GIMBAL_SCREW_Z - 6.0
GIMBAL_ROT_DEG = -45.0
GIMBAL_STL = ("Outer_Gimbal_1.001.stl", "Inner_Gimbal.002.stl", "MotorTube.003.stl")
GIMBAL_SERVO_PHI = (270.0 + GIMBAL_ROT_DEG, 0.0 + GIMBAL_ROT_DEG + 360.0)   # Servotaschen außen (-y) und innen (+x) der Druckdatei → 225°, 315°
# Servos und Gestänge (schematisch, im Bezugssystem der Druckdatei, vor Drehung und Verschiebung): Servokörper aus den
# Taschen '5600' der Blender-Dateien, W5652H 23 (tangential) × 19 (axial) × 8 (radial). Welle radial nach außen auf Höhe
# 7,5 mm über dem Kardanpunkt (Hebel liegt dann in Jans Fenstern bei 60 … 80 mm), 11 mm neben der Drehachse
# [Annahme]; Hebel 15 mm, hängt in Neutralstellung nach unten [Jan, Foto]; Draht Ø 2 vom Hebelende 30 mm senkrecht nach
# oben [Jan], dann als Bügel radial nach innen an das angetriebene Teil [Annahme].
SERVOS = [  # (Name, Mitte des Körpers (x, y, z), radiale Richtung, tangentiale Lage der Welle, Ziel-Radius des Bügels)
    ("W5652H Außenrahmen (treibt Innenrahmen)", (-5.2, -28.97, 31.5), (0.0, -1.0), -11.0, 24.0),
    ("W5652H Innenrahmen (treibt Motorrohr)", (25.02, 4.0, 31.5), (1.0, 0.0), 11.0, 17.5),
]
SERVO_BODY = (23.0, 19.0, 8.0)
SERVO_SHAFT_Z = 39.0            # Hebel hängt von 39 bis 24 (Rohr: 77 … 62), also im Fenster 60 … 80
HORN_R = 15.0                    # [Jan]
WIRE_D, WIRE_DROP = 2.0, 30.0     # [Jan] Drahtstärke, senkrechte Länge
SERVO_HORN_R = 15.0              # [Jan] Gestänge 15 mm von der Servoachse
PUSHROD = dict(d=2.0, l=(29.0, 30.0))   # [Jan]

# Stoß J1: Kuppler in B verklebt, 4 × M3 durch Rohr A und Kuppler in einen Schraubring im Kuppler
J1_SCREW_Z = TUBE_A[1] - 15.0    # 110: 15 mm unter der Oberkante von A
J1_RING = dict(z=(J1_SCREW_Z - 6.0, J1_SCREW_Z + 6.0), od=P.COUPLER_ID - 0.2, id=58.0)   # gedruckt, im Kuppler verklebt

# --------------------------------------------------------------------------- Rohr B: Avionik-Schlitten
OLD_HOLES_B_Z = TUBE_B[0] + 44.0     # [Jan] 169: 4 alte Löcher bei 90° vom Ring-Stack, werden Druckausgleich fürs Barometer
BAND_Z = (TUBE_B[1], TUBE_B[1] + 5.0)   # gedruckter Ring zwischen B und C, Außen-Ø wie das Rohr (sichtbares Band)
BAND_OD = TUBE_OD
PLATE_T = 5.0                     # Spantplatte = Band, 5 mm (CO₂-Druck, siehe CO2)
SPIGOT_B = dict(z=(TUBE_B[1] - 18.0, TUBE_B[1]), od=TUBE_ID - 0.4, id=64.0)   # Zapfen nach unten in B
SPIGOT_C = dict(z=(BAND_Z[1], BAND_Z[1] + 15.0), od=TUBE_ID - 0.4, id=66.0)   # Zapfen nach oben in C
SPIGOT_B_SCREW_Z = TUBE_B[1] - 8.0    # 293
SPIGOT_C_SCREW_Z = BAND_Z[1] + 7.5    # 313,5
SPIGOT_C_PHI = (45.0, 135.0, 225.0, 315.0)   # Rohr C liegt über den Rampenführungen; so bleibt 0°–180° frei für die quer liegende CO₂-Kapsel
BOSS_D = 10.0

DISC_Z = (TUBE_B[1] - 146.0, TUBE_B[1] - 143.0)   # untere Scheibe 155 … 158 (unter den alten Löchern bei 169)
DISC_OD = P.COUPLER_ID - 0.6           # sitzt noch im Kuppler J1 (endet bei 162,5)
DISC_CABLE_D = 22.0
DISC_PLUG_WINDOW = (-19.0, 15.0, -2.0, 10.0)
DISC_LIGHT_PHI, DISC_LIGHT_R, DISC_LIGHT_D = (230.0, 260.0, 280.0, 310.0), 24.0, 9.0
BOARD_V0_Z = TUBE_B[1] - 134.0   # 167
BOARD_W, BOARD_L, BOARD_T = P.BOARD_W, P.BOARD_L, P.BOARD_T
BOARD_HOLES = P.BOARD_HOLES
POST_D = 7.0
TRAY_FLOOR_Y = -14.5
TRAY_WALL = 1.6
BAT2S = dict(l=55.0, w=30.0, h=10.0, v0=6.0)   # [reichelt LRC 2S 450] LemonRC 2S 450 mAh 35C, XT30, 29 g
BAT1S = dict(l=50.0, w=30.0, h=7.0, v0=64.0)   # endet bei v = 114, unter dem Steg im Zapfenring
STRAP_SLOT = (2.5, 16.0)
TRAY_TO_DISC = [(-20.0, -9.0), (20.0, -9.0)]
PLUGS_TVC_END = [("Servo Gieren J5", -14.4), ("Servo Nicken J6", -2.8), ("XT30 2S J1", 10.2)]
PLUG_REACH = 12.0

# Antennen (Stand 2): GPS flach unter dem Spant, Patch nach oben; LoRa-Wendel axial am unteren Ende
GPS = dict(w=20.0, l=20.0, h=7.0, y=(9.0, 29.0), z_top=SPIGOT_B["z"][1] - 0.5)   # [Annahme] M10-Modul 20 × 20 mit Patch
LORA_HELIX = dict(d=8.0, l=30.0, z_top=DISC_Z[0] - 1.0, x=0.0, y=-8.0)           # [Annahme] 433-MHz-Wendel, ragt aus der Scheibe nach unten

# Luken in Rohr B (eine Wand, der Kuppler J1 endet bei 162,5)
HATCH_W = 20.0
HATCH_A1 = dict(phi=90.0, v=(14.0, 40.0))      # SD
HATCH_A2 = dict(phi=90.0, v=(87.0, 113.0))     # USB (gerader Stecker bis v ≈ 113)
HATCH_B = dict(phi=270.0, v=(22.0, 66.0), w=22.0)   # Schalterbrett
PANEL_W, PANEL_T = 18.0, 2.0
PANEL_Y = (-33.0, -31.0)
PANEL_PARTS = [  # Name, u-Mitte, v0, v1, Breite
    ("Hauptschalter 2-polig (J_SW)", -4.5, 31.0, 43.0, 6.0),
    ("USB-C Laden 1S (J_CHG1)", -4.5, 47.0, 56.0, 9.0),
    ("Lade-LED", -4.5, 59.0, 62.0, 3.0),
    ("XT30 Laden 2S (J_CHG2)", 4.5, 31.0, 41.2, 5.2),
    ("XH-3 Balancer 2S", 4.5, 45.0, 52.5, 7.5),
]
PANEL_COLS = [(0.0, 26.5), (4.5, 60.0)]
PANEL_COL_D = 7.0
ARM_SCREW_SWITCH = dict(phi=270.0, v=70.0, d=3.0)   # Schraubschalter für ARM (heute ohne Pyro: Brücke), Zugang Ø 3 neben Luke B

# --------------------------------------------------------------------------- Rohr C: Bergung
CO2 = dict(l=65.0, d=18.0, h=24.0, m_aufbau=10.0, m_kapsel=25.0, gas_l=2.0)   # [Jan] Aufbau 10 g, 2 l; Kapsel 8 g CO₂ 18 × 65 [Annahme] liegt quer
CHUTE = dict(d=70.0, l=100.0)        # [Jan] gepackt
CORD_BAY = 0.0                        # Stand 2b: Schnur liegt im Spitzen-Kuppler
NOSE_COUPLER_L = 75.0                 # [Jan] Spitze außen bündig mit dem Rohr, innen passt der Kuppler: zweiter halber Kuppler
NOSE_COUPLER_IN_NOSE = 25.0           # [Jan] bis zur Holzplatte mit Haken; dort in der Spitze verklebt
NOSE_HOOK_DEPTH = NOSE_COUPLER_IN_NOSE
CO2_Z0 = SPIGOT_C["z"][1] + 1.0      # Kapsel liegt quer über dem Zapfenring (im Rohr C ist Platz für 65 mm)
CHUTE_Z = (CO2_Z0 + CO2["h"] + 3.0, CO2_Z0 + CO2["h"] + 3.0 + CHUTE["l"])
NOSE_COUPLER_Z = (CHUTE_Z[1] + 2.0, CHUTE_Z[1] + 2.0 + NOSE_COUPLER_L)   # Schnur liegt im Kuppler (innen 70,2)
TOP_Z = NOSE_COUPLER_Z[1] - NOSE_COUPLER_IN_NOSE   # Rohr C endet an der Spitzenbasis
NOSE_SHOULDER_Z0 = NOSE_COUPLER_Z[0]                # Name aus Stand 2: Unterkante des Spitzen-Kupplers
TUBE_C = (BAND_Z[1], TOP_Z)
NOSE_TIP_Z = TOP_Z + P.NOSE_L
SHEAR_PIN_Z = TOP_Z - 15.0
SHEAR_PIN_PHI = (45.0, 225.0)
SHEAR_PIN_D = 2.0

# --------------------------------------------------------------------------- Startrampe: Führungen zwischen die Schrauben
RAMP_GUIDE_PHI = (45.0, 135.0, 250.0)   # zwischen Schrauben (0/90/180/270) und Servofenstern (207°, 336° laut Druckdatei)
RAMP_GUIDE_H = 160.0
RAMP_GUIDE_GAP = 1.5
RAMP_GUIDE_W = 20.0

def servo_window_phi():
    """Winkel der Servofenster in Rohr A aus der Wellenlage der Servos (Druckdatei gedreht um GIMBAL_ROT_DEG)."""
    out = []
    for name, (cx, cy, cz), (rx, ry), s_tan, r_t in SERVOS:
        rad = math.hypot(cx, cy) + SERVO_BODY[2] / 2
        sx, sy = rx * rad - ry * s_tan, ry * rad + rx * s_tan
        out.append((math.degrees(math.atan2(sy, sx)) + GIMBAL_ROT_DEG) % 360)
    return out


PRINT_RHO, PRINT_FILL = 1.27, 0.75

# Masse: Teile, die gegenüber dem 761-g-Modell (cad/mass_properties.md, Erstflug 700 mm) wegfallen oder sich ändern
MASS_BASE_ERSTFLUG = 761.0
MASS_REMOVED = [
    ("Rohr unten + oben 700 mm (wird 125 + 176 + C)", 168.0),
    ("Kuppler Flugcomputer 150 mm (wird 75 mm)", 34.0),
    ("Stoßkuppler 80 mm", 18.0),
    ("8 Gewindestangen M2", 30.0),
    ("Endring unten, Endplatte oben, Träger", 40.0),
    ("Schlüsselschalter + Kragen", 28.0),
    ("Schalterbrett", 6.0),
    ("Kolben (Kuppler-Stück, Platte, Ladungsschale)", 31.0),
    ("Spitze Spant + Öse (Klima-Holzplatte ist schon drin)", 3.0),
    ("Spitze Schulterkuppler (ersetzt durch den zweiten halben Kuppler, siehe unten)", 17.0),
]
MASS_ADDED_HW = [
    ("Kuppler J1 75 mm", P.COUPLER_M / 2),
    ("Kuppler Spitze 75 mm", P.COUPLER_M / 2),
    ("CO₂-Aufbau (Jan)", CO2["m_aufbau"]),
    ("CO₂-Kapsel 8 g, gefüllt [Annahme]", CO2["m_kapsel"]),
    ("2S-Akku: LemonRC 450 statt Modellwert 30 g", -1.0),
    ("Schraubschalter", 2.0),
    ("GPS-Modul 20 × 20 [Annahme]", 6.0),
    ("M3-Muttern und -Schrauben (ca. 20)", 8.0),
    ("Moosgummi, Schaum, Kabelverschraubung", 2.0),
]


def tube_mass(z0, z1):
    return (z1 - z0) * P.TUBE_G_PER_MM


def v_to_z(v):
    return BOARD_V0_Z + v


def mass_estimate(printed_g):
    tubes = tube_mass(*TUBE_A) + tube_mass(*TUBE_B) + tube_mass(*TUBE_C)
    return (MASS_BASE_ERSTFLUG - sum(m for _, m in MASS_REMOVED) + tubes + printed_g + sum(m for _, m in MASS_ADDED_HW))


def co2_pressure_bar():
    """Überdruck, wenn das ganze Gas im freien Raum von Rohr C bliebe (Obergrenze, die Spitze geht vorher ab)."""
    r = TUBE_ID / 2
    v_free = math.pi * r ** 2 * (TUBE_C[1] - SPIGOT_C["z"][0]) / 1e6 - math.pi * (CHUTE["d"] / 2) ** 2 * CHUTE["l"] / 1e6 * 0.6
    return CO2["gas_l"] / v_free, v_free


def checks():
    out = []
    def chk(ok, txt):
        out.append((bool(ok), txt))
    chk(J1_COUPLER[0] >= GIMBAL_TOP_Z - 10.0, f"Kuppler J1 reicht bis z = {J1_COUPLER[0]:.1f} in Rohr A (heute schon so gesteckt; Servos bis ca. {GIMBAL_TOP_Z:.0f} [Annahme])")
    chk(J1_RING["z"][0] > GIMBAL_TOP_Z, f"Schraubring J1 ab z = {J1_RING['z'][0]:.0f} über dem Kardan ({GIMBAL_TOP_Z:.0f} [Annahme])")
    chk(DISC_Z[0] > J1_COUPLER[1] - 10 and DISC_OD < P.COUPLER_ID, f"untere Scheibe z {DISC_Z[0]:.0f} … {DISC_Z[1]:.0f} passt auch in den Kuppler (Ø {DISC_OD:.1f} < {P.COUPLER_ID})")
    chk(DISC_Z[1] < OLD_HOLES_B_Z - 3, f"alte Löcher bei z = {OLD_HOLES_B_Z:.0f} liegen über der Scheibe, also im Avionikraum (Druckausgleich)")
    chk(BOARD_V0_Z - PLUG_REACH >= DISC_Z[0], f"Stecker J5/J6/J1 enden bei z = {BOARD_V0_Z - PLUG_REACH:.0f}, im Fenster der Scheibe")
    chk(BOARD_V0_Z + BOARD_L + 0.5 <= SPIGOT_B_SCREW_Z - BOSS_D / 2, f"Platine endet bei z = {BOARD_V0_Z + BOARD_L:.0f}, Schraubenauge ab {SPIGOT_B_SCREW_Z - BOSS_D / 2:.0f}")
    chk(GPS["y"][1] ** 2 + (GPS["w"] / 2) ** 2 < (SPIGOT_B["id"] / 2) ** 2, f"GPS 20 × 20 passt in den Zapfenring (Ecke r = {math.hypot(GPS['w'] / 2, GPS['y'][1]):.1f} < {SPIGOT_B['id'] / 2:.0f})")
    for nm, hd in (("A1", HATCH_A1), ("A2", HATCH_A2), ("B", HATCH_B)):
        z0, z1 = v_to_z(hd["v"][0]), v_to_z(hd["v"][1])
        chk(J1_COUPLER[1] + 3 < z0 and z1 <= SPIGOT_B["z"][0] - 3, f"Luke {nm} z {z0:.0f} … {z1:.0f}: nur Rohr B, über dem Kuppler ({J1_COUPLER[1]:.1f}), unter dem Zapfen ({SPIGOT_B['z'][0]:.0f})")
    chk(math.hypot(CO2["l"] / 2, 4.0 + CO2["d"] / 2) < TUBE_ID / 2, f"CO₂-Kapsel {CO2['l']:.0f} mm liegt quer im Rohr C über dem Zapfenring")
    chk(CHUTE["d"] < TUBE_ID, f"Schirm Ø {CHUTE['d']:.0f} im Rohr C (innen {TUBE_ID})")
    half = math.degrees(math.atan(RAMP_GUIDE_W / 2 / (TUBE_OD / 2 + RAMP_GUIDE_GAP))) + 4.5
    for s in SCREW_PHI:
        for g in RAMP_GUIDE_PHI:
            if abs((s - g + 180) % 360 - 180) < half:
                out.append((False, f"Schraube bei {s:.0f}° an der Führung {g:.0f}°"))
    chk(True, f"Schraubköpfe bei 0/90/180/270° frei von Führungen bei {', '.join(f'{g:.0f}°' for g in RAMP_GUIDE_PHI)} (±{half - 4.5:.1f}°)")
    p, v = co2_pressure_bar()
    chk(True, f"CO₂ {CO2['gas_l']} l in {v * 1000:.0f} ml freiem Raum: höchstens {p:.1f} bar Überdruck, wenn die Spitze klemmt (ohne Abscherstifte geht sie bei < 0,1 bar)")
    return out


if __name__ == "__main__":
    for ok, txt in checks():
        print("ok  " if ok else "FEHLER", txt)
    print(f"Rohr C = {TUBE_C[1] - TUBE_C[0]:.0f} mm, Gesamtlänge {NOSE_TIP_Z:.0f} mm")
