"""Alle Maße und Massen der Rakete an einer Stelle.

Einheiten: mm und g. Koordinaten wie in der Firmware: z ist die Längsachse, z = 0 die Düsenebene
(Austrittsebene des Motors), +z zeigt zur Spitze. x zeigt zum Servo des Innenrahmens, y zum Lagerohr
des Außenrahmens (Servo des Außenrahmens bei -y). Welche Achse Pitch und welche Yaw ist, steht in
`Config.h` noch nicht fest (offene Frage in hardware/mainboard/README.md §9).

Jeder Wert nennt seine Quelle:
  [Klima]    Shop raketenmodellbau-klima.de, abgerufen 21.10.2026
  [BUILD]    docs/BUILD.md (Bestellungen, Entscheidungen 21.10.2026)
  [Blender]  aus den Blender-Dateien nachgemessen, siehe cad/blender_inventory.md
  [HW]       hardware/mainboard/outline.py und README.md
  [Annahme]  eigene Schätzung, am Gerät nachmessen
  [Vorgabe]  Massenvorgabe aus dem Auftrag vom 21.10.2026 (Jan)
Geänderte Maße gegenüber Blender sind mit "geändert:" markiert.
"""

# --------------------------------------------------------------------------- Rumpf
TUBE_OD = 75.0            # [Klima] Körperrohr 207550000
TUBE_ID = 72.6            # [Klima]
TUBE_L = 500.0            # [Klima] Lieferlänge eines Rohrs
TUBE_M = 120.0            # [Klima] je Rohr (500 mm)
TUBE_G_PER_MM = TUBE_M / TUBE_L   # 0,24 g/mm [Klima]
TUBE_BOTTOM_Z = 20.0      # [Annahme] Unterkante des unteren Rohrs über der Düsenebene: der Motor ragt 20 mm heraus

COUPLER_OD = 72.4         # [BUILD] Kuppler 207315000; der Klima-Shop nennt 72,6 mm, nachmessen
COUPLER_ID = 70.2         # [Klima]
COUPLER_L = 150.0         # [Klima]
COUPLER_M = 34.0          # [Klima]

# Spitze: Klima 8539, Spritzguss-ABS, "Länge 230 mm, Außen Ø 75, Schulter Ø 72,6, ca. 100 g" [Klima]
NOSE_L = 230.0            # [Klima] sichtbare Länge über dem Rohr (Annahme: ohne Schulter)
NOSE_SHOULDER_D = 72.4    # [Klima] 72,6 laut Shop; geändert: 0,2 mm Spiel, die Spitze soll lose sitzen
NOSE_SHOULDER_L = 75.0    # [Annahme] mitgelieferter Kuppler, Länge nachmessen
NOSE_WALL = 2.0           # [Annahme]
NOSE_M = 100.0            # [Klima] ca., davon [Annahme] 80 g Kegel, 17 g Schulterkuppler, 3 g Spant/Öse

# --------------------------------------------------------------------------- Motor und Adapter
MOTOR_D = 24.0            # [BUILD] TSP E12-0
MOTOR_L = 95.0            # [BUILD]
MOTOR_M = 64.0            # [BUILD] gesamt
GRAIN_M = 28.0             # [BUILD] Treibstoff
GRAIN_Z = (10.0, 60.0)     # [Annahme] Lage des Treibsatzes im Gehäuse (über der Düse, unter dem Verzögerungs-/Deckelbereich)
GRAIN_D = 20.0             # [Annahme]
MOTOR_Z = (0.0, MOTOR_L)

ADAPTER_OD = 29.0         # [Blender] 29→24-Adapter, Außen wie ein 29-mm-Motor; geändert: Blender-Teil war Ø 35 × 100
ADAPTER_ID = 24.2         # [Annahme] 0,2 mm Spiel
ADAPTER_L = 85.0          # [Annahme] endet 10 mm über der Düse, der Motor steht unten heraus
ADAPTER_M = 15.0          # [Annahme] PLA, geschlitzt
ADAPTER_Z = (MOTOR_L - ADAPTER_L, MOTOR_L)

# --------------------------------------------------------------------------- TVC-Kardan (BPS-Scout-F-Prinzip, dual_tvc)
TVC_RING_ABOVE_TUBE_END = 25.0            # [Annahme] Grundfläche des Außenrahmens über der Rohrunterkante
TVC_RING_Z = TUBE_BOTTOM_Z + TVC_RING_ABOVE_TUBE_END   # = 45 mm über der Düse
PIVOT_H = 31.5            # [Blender] Servomitte über der Rahmen-Grundfläche (outer/inner_gimbal_dual_TVC)
PIVOT_Z = TVC_RING_Z + PIVOT_H            # Kardanpunkt über der Düsenebene (76,5 mm)

GIMBAL_MAX_DEG = 7.0      # [Annahme] Auslenkung je Achse; daraus folgen die Ring-Spiele
import math as _m
GIMBAL_CLEAR = PIVOT_H * _m.tan(_m.radians(GIMBAL_MAX_DEG)) + 0.5   # radiales Spiel an der Ring-Unterkante (4,4 mm)

OUTER_RING_OD = TUBE_ID - 0.4             # geändert: Blender 73,0, passt nicht ins 72,6-Rohr
OUTER_FLANGE_H = 12.0     # [Blender] Grundring mit 4 Radialbohrungen
OUTER_H = 47.35           # [Blender] Gesamthöhe (Tasche und Lagerohr)
OUTER_WALL_T = 4.0        # [Annahme] Lagerohr-Wand
OUTER_SCREW_D = 3.2       # [Annahme] 4 × M3 radial durch das Rohr
OUTER_M = 22.0            # [Vorgabe] Kardan gesamt 50 g, Aufteilung [Annahme]

INNER_RING_OD = 49.5      # [Blender]
INNER_FLANGE_H = 12.0     # [Blender]
INNER_H = 48.4            # [Blender]
INNER_WALL_T = 4.0        # [Annahme] Lagerohr-Wand
INNER_HOUSING_Z0 = INNER_FLANGE_H + 5.0   # Servogehäuse des Innenrahmens beginnt über dem Außenflansch (Kippfreiheit)
INNER_ENVELOPE_R = TUBE_ID / 2 - 2.8      # Hüllradius des Innenrahmens: bei ±7° Kippung bleibt 1 mm Luft zum Rohr
INNER_M = 16.0            # [Annahme] Anteil der 50 g

MOTOR_TUBE_OD = 33.5      # [Blender] MotorTube.003
MOTOR_TUBE_ID = 29.2      # geändert: Blender 28,6; 29-mm-Adapter braucht 29,2
MOTOR_TUBE_L = 58.0       # [Blender] 58,6
MOTOR_TUBE_Z = (TVC_RING_Z, TVC_RING_Z + MOTOR_TUBE_L)   # Motoroberkante (95) liegt 8 mm unter dem Rohrende
MOTOR_TUBE_M = 12.0       # [Annahme] Anteil der 50 g
MOTOR_CLAMP_SCREW_D = 3.2 # [Annahme] Klemmschraube im Motorrohr

# geändert: Blender hat Außenrahmen innen 51,3 und Innenrahmen innen 37,2, also 0,9 bzw. 1,85 mm radiales Spiel.
# Bei 31,5 mm Hebel zur Ring-Unterkante sind das 1,6° bzw. 3,4° Kippwinkel. Hier aus GIMBAL_MAX_DEG abgeleitet:
OUTER_RING_ID = INNER_RING_OD + 2 * GIMBAL_CLEAR      # 58,3 mm statt 51,3
INNER_RING_ID = MOTOR_TUBE_OD + 2 * GIMBAL_CLEAR      # 42,3 mm statt 37,2

PIVOT_PIN_D = 3.0         # [Annahme] M3 als Lagerbolzen auf der Gegenseite des Servos
PIVOT_BOSS_D = 8.0        # [Annahme]

# Servo FrSky Xact W5652H: 19 × 8 × 23 mm, 10 g, 15-Zahn-Abtrieb Ø 4 mm [BUILD]
# Flächenservo: die Abtriebswelle steht senkrecht auf der 19 × 23-Fläche, also entlang der 8-mm-Dicke.
# Einbau wie das "5600" in den Blender-Dateien: flach in der Rahmenwand, Welle radial nach innen auf der
# Rahmenachse. Das Servo wird von außen in die Tasche gesetzt und mit den Laschen an die Taschenwand geschraubt.
SERVO_L = 23.0            # tangential (entlang der Ringwand)   [BUILD]; welche Seite 19 und welche 23 ist: Datenblatt
SERVO_H = 19.0            # axial (z)
SERVO_T = 8.0             # radial (Wellenrichtung)
SERVO_SHAFT_D = 4.0
SERVO_SHAFT_L = 2.0       # [Annahme] Wellenüberstand über die Gehäusefläche
SERVO_SHAFT_OFFSET = 5.0  # [Annahme] Welle 5 mm aus der Mitte der Längsseite; Datenblatt prüfen
SERVO_TAB_L = 3.0         # [Annahme] Befestigungslaschen je Seite
SERVO_M = 10.0            # [BUILD]
POCKET_CLEAR = 0.3        # [Annahme] Spiel in der Tasche
HORN_D, HORN_T = 12.0, 2.0   # [Annahme] Servohebel als Scheibe, in einer Vertiefung des Lagerzapfens
POCKET_WALL_IN = 1.0      # [Annahme] Wand zwischen Servo und dem bewegten Teil (Welle geht hindurch)
POCKET_WALL_OUT = 1.2     # [Annahme] Außenwand der Tasche (Außenrahmen: zum Rohr hin)
SERVO_OUTER_R = OUTER_RING_OD / 2 - POCKET_WALL_OUT - SERVO_T / 2      # 30,9 mm (Blender 29)
SERVO_INNER_R = MOTOR_TUBE_OD / 2 + 1.75 + POCKET_WALL_IN + SERVO_T / 2   # 23,5 mm (Blender 25)

# --------------------------------------------------------------------------- Flugcomputer im Kuppler
FC_RING_D = 69.0          # [HW] Ring-Stack Ø 69 im Kuppler (Innen 70,2)
FC_RING_T = 6.0           # [Annahme] Endringe
FC_ROD_D = 2.0            # [HW] 8 × M2
FC_RODS = [(29.5, 7.0), (29.5, -7.0), (-29.5, 7.0), (-29.5, -7.0),
           (7.0, 29.5), (-7.0, 29.5), (7.0, -29.5), (-7.0, -29.5)]   # [HW]
BOARD_W, BOARD_L, BOARD_T = 54.0, 120.0, 1.6   # [HW]
BOARD_HOLES = [(-23.5, 3.5), (23.5, 3.5), (-23.5, 116.5), (23.5, 116.5)]   # [HW] (u, v)
TEENSY = dict(u0=-8.9, u1=8.9, v0=30.0, v1=91.0, h=12.0)   # [HW] Teensy auf Buchsenleisten, Höhe [Annahme]
SD_V = (24.0, 30.0)       # [HW] Freifläche vor dem SD-Slot
USB_V = (91.0, 103.0)     # [HW] Freifläche für den USB-Stecker
IMU_V = 60.5              # [HW]
CARRIER_WALL = 2.0        # [Annahme] gedruckter Träger unter der Platine
CARRIER_DEPTH = 14.5      # [Annahme] Trägerboden bei y = -14,5 (Akku 8 mm + Platine)
BAT2S = dict(l=56.0, w=25.5, h=8.0, m=45.0, v0=10.0)     # [BUILD] 56 × 25,5 × 8, Masse [Vorgabe]
BAT1S = dict(l=35.0, w=25.0, h=7.0, m=12.0, v0=72.0)     # [Annahme] 450–600 mAh 1S, Masse [Vorgabe]
FC_M_BOARD = 40.0         # [Annahme] Platine + Teensy + Bauteile
FC_M_RINGS = 25.0         # [Annahme] 2 Endringe, davon oben die Spant-/Ladungsplatte
FC_M_RODS = 20.0          # [Annahme] 8 × M2 × 150 Stahl wären 30 g; hier 20 g (4 Stangen reichen vermutlich)
FC_M_CARRIER = 15.0       # [Annahme] gedruckter Träger
FC_M = FC_M_BOARD + FC_M_RINGS + FC_M_RODS + FC_M_CARRIER   # = 100 g [Vorgabe]

HATCH_W = 16.0            # [Annahme] Luke für USB (Breite quer), in Kuppler und Rohr
HATCH_V = (USB_V[0] - 2.0, USB_V[1] + 2.0)   # Luke deckt nur den USB-Stecker; SD-Karte durch Herausziehen des Moduls
HATCH_SD = False          # True: zweite Luke vor dem SD-Slot (liegt im unteren Rohr, 35–41 mm unter dem Stoß)
HATCH_SIDE_Y = +1         # Luke auf der Bestückungsseite (+y)

# --------------------------------------------------------------------------- Kolben-Ausstoß (BPS-Prinzip)
# Die obere Endplatte des Flugcomputer-Moduls ist der feste Spant mit der Ladungsschale. Der Kolben
# (Stück Kuppler + Platte) sitzt darüber im oberen Rohr und schiebt Fallschirm und Spitze heraus.
CHARGE_WELL_D = 12.0      # [Annahme] Schwarzpulver-Schale
CHARGE_WELL_H = 8.0       # [Annahme]
EMATCH_HOLE_D = 2.0
PISTON_GAP = 11.0         # geändert: war 5; Ladungsschale (8 mm) und Öse der Endplatte (bis 8,5 mm) ragen über die Platte, der Kolben braucht 2,5 mm Luft darüber
PISTON_L = 40.0           # [Annahme] Kuppler-Abschnitt
PISTON_PLATE_T = 6.0      # [Annahme]
PISTON_M = 31.0           # [Annahme] 9 g Kuppler-Stück + 10 g Platte + 12 g Ladungsschale/Spantaufbau
CHUTE_D = 60.0            # [Annahme] gepackter Klima-Fallschirm 125 cm
CHUTE_L = 230.0           # [Annahme]
CHUTE_M = 50.0            # [Vorgabe] mit Schockschnur
SHOCK_CORD_EYE_D = 6.0

# --------------------------------------------------------------------------- Landebeine (model_rocket.blend, ausgefahren)
LEG_SLEEVE_OD = 82.5      # [Blender] Base Extension 1
LEG_SLEEVE_ID = TUBE_OD + 0.2   # geändert: Blender 77,0 (2 mm Luft), hier 0,1 mm Spiel
LEG_SLEEVE_H = 12.5       # [Blender]
LEG_SLEEVE_Z0 = TUBE_BOTTOM_Z - 5.5   # [Blender] Ring ragt 5,5 mm unter die Rohrunterkante
LEG_UPPER_RING_Z = (TUBE_BOTTOM_Z + 70.0, TUBE_BOTTOM_Z + 79.0)   # [Blender] Airframe Mount.002
LEG_UPPER_RING_OD = 106.0 # [Blender]
LEG_UPPER_RING_ID = TUBE_OD + 0.2   # geändert: Blender 75,0 (ohne Spiel)
LEG_HINGE_R = 48.0        # [Blender] Gelenk der Hauptstrebe (LegEnd) auf r = 48, z = Rohrunterkante
LEG_HINGE_Z = TUBE_BOTTOM_Z
LEG_TOP_HINGE_R = 53.0    # [Blender] Gelenk der oberen Strebe (TopStrut Mount)
LEG_TOP_HINGE_Z = TUBE_BOTTOM_Z + 67.0
LEG_MAIN_L = 286.0        # [Blender] Hauptstrebe (FusionComponent001)
LEG_MAIN_W, LEG_MAIN_T = 20.0, 5.0   # [Blender] 22,9 breit (mit Gelenkaugen), hier Flachprofil
LEG_TOP_D = 5.0           # [Blender] obere Strebe Ø 5
LEG_FOOT = (35.0, 35.0, 18.0)        # [Blender]
LEG_DEPLOY_DEG = 18.3     # [Blender] Hauptstrebe 18,3° unter der Waagerechten (Fuß auf r ≈ 320, z ≈ -72)
LEG_STOW_DEG = 90.0       # eingeklappt: Hauptstrebe senkrecht am Rohr
LEG_DEPLOYED = True       # Darstellung im Gesamtmodell
LEG_N = 4
LEG_M_SLEEVE = 25.0       # [Annahme] Anteile der 200 g Landesystem [Vorgabe]
LEG_M_UPPER_RING = 25.0
LEG_M_MAIN = 20.0         # je Bein
LEG_M_TOP = 10.0          # je Bein
LEG_M_FOOT = 7.5          # je Bein
LEG_M = LEG_M_SLEEVE + LEG_M_UPPER_RING + LEG_N * (LEG_M_MAIN + LEG_M_TOP + LEG_M_FOOT)   # = 200 g

# --------------------------------------------------------------------------- Sonstiges
MISC_M = 20.0             # [Annahme] Kabel, Schrauben, Schockschnur-Anker, Kleber

# --------------------------------------------------------------------------- Farben für Export und Render (RGB 0..1)
COLORS = {
    "tube": (0.93, 0.90, 0.82), "coupler": (0.72, 0.60, 0.45), "nose": (0.95, 0.95, 0.95),
    "printed": (0.25, 0.45, 0.75), "printed2": (0.35, 0.65, 0.85), "motor": (0.65, 0.35, 0.20),
    "servo": (0.15, 0.15, 0.15), "board": (0.10, 0.45, 0.25), "teensy": (0.20, 0.55, 0.35),
    "battery": (0.90, 0.75, 0.20), "chute": (0.90, 0.30, 0.25), "steel": (0.6, 0.6, 0.65),
    "leg": (0.30, 0.30, 0.32), "foot": (0.80, 0.20, 0.15),
}

# --------------------------------------------------------------------------- Prüfstand (TVC-Testrig, 21.10.2026)
# Die Rakete hängt dreh- und schwenkbar in einem Gestell, Drehpunkt im Schwerpunkt. An Stelle des E12
# sitzt ein Brushless-Motor mit Propeller im Kardan (Teile: docs/BUILD.md §1.5). Rig-Achsen: Achse der
# Stützen = x (Nicken), Zapfen des Kragens = y (Gieren); die Rakete behält ihre Koordinaten (z ab Düse).
RIG_PIVOT_Z = 448.0        # [cad] Schwerpunkt Start aus mass_properties.md; nach dem Auswiegen setzen
RIG_PIVOT_ABOVE_FLOOR = 800.0   # [Annahme] Propeller etwa 330 mm über dem Boden (ein Durchmesser Bodenabstand)
RIG_TILT_MAX_DEG = 20.0    # [Annahme] Auslenkung je Achse, Begrenzung per Gurt/Schnur zwischen Rohr und Rahmen
RIG_FLOOR_Z = RIG_PIVOT_Z - RIG_PIVOT_ABOVE_FLOOR

RIG_BASE = (820.0, 500.0, 18.0)   # [Annahme] Sperrholz-Grundplatte x × y × Dicke
RIG_UPRIGHT_X = 350.0      # [Annahme] Stützen bei ±x; Prop reicht bei 20° Gieren bis x = 304 (Prop Ø 305)
RIG_PROFILE = 40.0         # [Annahme] Alu-Profil 40 × 40 (Stützen, Streben)
RIG_UPRIGHT_TOP = RIG_PIVOT_Z + 60.0
RIG_BEARING = (22.0, 8.0, 7.0)    # [Annahme] Kugellager 608: Außen Ø 22, Bohrung 8, Breite 7
RIG_AXLE_D = 8.0           # [Annahme] zwei Achsstummel Ø 8 Stahl (keine durchgehende Welle, die Rakete steht dazwischen), in den Rahmenbossen geklemmt
RIG_FRAME_BAR = 20.0       # [Annahme] Rahmen aus Alu-Profil 20 × 20
RIG_FRAME_X = (58.0, 78.0) # Innen-/Außenkante der x-Stäbe; der Kragen (Ø 95, 40 hoch) reicht bei 20° Gieren bis x = 51,5
RIG_FRAME_Y = (67.5, 87.5) # Innen-/Außenkante der y-Stäbe (Kragen Ø 95 + Zapfen)
RIG_FRAME_H = 20.0
RIG_BEARING_BLOCK = (30.0, 20.0, 30.0)   # [Annahme] gedruckter Lagerbock auf den y-Stäben
RIG_COLLAR_OD = 95.0       # [Annahme] gedruckter Klemmkragen, zweiteilig, Teilung in der Ebene x = 0 (Ohren an ±y)
RIG_COLLAR_ID = TUBE_OD + 0.2
RIG_COLLAR_H = 40.0
RIG_COLLAR_FLANGE = (14.0, 16.0)   # Ohren an ±y: radiale Länge, Breite (x); je Seite 2 × M4 über und unter dem Zapfen
RIG_STUD_D = 8.0           # Zapfen Ø 8 auf der y-Achse, zwischen den Ohrenhälften geklemmt, läuft in den Lagerböcken
RIG_ESC_BOX = (75.0, 35.0, 25.0)   # [Annahme] ESC + 4S-Akku als Klotz auf dem Rahmen (−y)

# Brushless-Motor Racerstar BR2814 1000 KV [BUILD]; Maße [Annahme] typischer 2814-Außenläufer, am Teil nachmessen
PM_CAN_D = 35.0
PM_CAN_L = 36.0
PM_SHAFT_D = 4.0
PM_MOUNT_CROSS = (16.0, 19.0)   # [Annahme] Kreuz-Lochbild M3
PM_M = 75.0                # [Annahme] g
PM_FLANGE_D = 44.0         # Adapterflansch unter dem Motorrohr
PM_FLANGE_T = 5.0
PM_SPIGOT_D = ADAPTER_OD   # Zapfen wie der 29-mm-Adapter, Klemmschraube des Motorrohrs greift
PM_SPIGOT_L = 54.0         # Zapfen im Motorrohr (Motorrohr 45 … 103, Klemmschraube bei 95)
PM_FLANGE_Z = (MOTOR_TUBE_Z[0] - PM_FLANGE_T, MOTOR_TUBE_Z[0])   # Flansch direkt unter dem Motorrohr (40 … 45)
PM_CAN_Z = (PM_FLANGE_Z[0] - PM_CAN_L, PM_FLANGE_Z[0])           # Glocke hängt darunter (4 … 40), Welle nach unten
PROP_DIA = 305.0           # [BUILD] 12 × 6 (11 × 7 wäre 279)
PROP_CHORD = 28.0          # [Annahme]
PROP_T = 8.0               # [Annahme] Nabendicke
PROP_HUB_D = 16.0
PROP_Z = PM_CAN_Z[0] - 3.0 - PROP_T / 2   # Propellerebene unter der Glocke (≈ −3)
PROP_M = 15.0              # [Annahme] g

# Propellerschutz: Käfig aus zwei Ringen, Stäben und Speichen zu einem Klemmring am unteren Rohrende
GUARD_R = PROP_DIA / 2 + 16.0   # Mitte des Ringrohrs: 12 mm radiales Spiel zur Propellerspitze
GUARD_TUBE_D = 8.0
GUARD_RING_Z = (PROP_Z - 32.0, 40.0)   # unterer und oberer Ring; die Spitze steigt bei 10° Kardanneigung bis z = 24
GUARD_BARS = 12
GUARD_SPOKES = 4
GUARD_COLLAR_Z = (TUBE_BOTTOM_Z + 25.0, TUBE_BOTTOM_Z + 45.0)   # Klemmring am Rohr über dem Außenrahmen-Flansch
GUARD_COLLAR_OD = 90.0
GUARD_M = 90.0             # [Annahme] g, Alu-Rohr 8 mm und Druckteile
COLORS.update({"alu": (0.75, 0.76, 0.78), "wood": (0.82, 0.70, 0.50), "prop": (0.20, 0.20, 0.22)})


# --------------------------------------------------------------------------- Konfigurationen (22.10.2026)
# "voll":     Stand 21.10.: 2 × 500 mm Rohr (1000 mm), Landebeine, Flugcomputer um den Rohrstoß, 850-mAh-2S.
# "erstflug": Entscheidung Jan 22.10.: Aufstieg mit einem Motor, Fallschirm, kein Landesystem; Rohr gekürzt,
#             Platine 54 × 120 statt Breakouts, 2S 450 mAh. Gewählt über die Umgebungsvariable MS_CONFIG
#             (build.py --config erstflug) und optional MS_TUBE_L; mass_model.py rechnet alle Varianten.
import os as _os
import types as _types

CONFIG_DEFAULT_TUBE_L = {"voll": 1000.0, "erstflug": 700.0}
CONFIG = _os.environ.get("MS_CONFIG", "voll")
ERSTFLUG_BAT2S_M = 30.0       # [Vorgabe] 2S 450 mAh statt 45 g für 850 mAh; Abmessungen der 850er beibehalten (konservativ)
ERSTFLUG_BOARD_M = 45.0       # [Vorgabe] Mainboard 54 × 120 mit Teensy, ersetzt die Breakouts (40 g im Modell "voll")
ERSTFLUG_HATCH_HW_M = 20.0    # [Annahme] Schalterbrett (Schiebeschalter, USB-C, XT30, XH-3, LED), Schlüsselschalter, Kragen
CORD_BAY_MIN = 50.0           # [Annahme] Raum über dem Fallschirm für die Schockschnur (3 × Rumpf, gefaltet) vor dem Spant der Spitze
COUPLER_INTO_LOWER_EF = 25.0  # [Annahme] Erstflug: Kuppler steckt nur 25 mm im unteren Rohr, damit beide Luken im oberen liegen
KEY_COLLAR_Z = (106.0, 124.0) # Erstflug: Kragen für den Schlüsselschalter im unteren Rohr, 3 mm über dem Kardan (Motorrohr bis 103 + 2 bei 7°)
NOSE_BULKHEAD_BELOW_BASE = NOSE_SHOULDER_L - 2.0   # Spant der Spitze: Unterkante 73 mm unter der Spitzenbasis (Rohrende)

# Luken im Flugcomputer-Kuppler, Erstflug. Maße (u quer, v längs der Platine ab dem TVC-Ende), Koordinaten wie die Platine.
HATCH_A = dict(side=+1, w=12.0, v=(25.0, 100.0))    # Teensy: Micro-USB, Programmiertaste, SD; 14 mm Stangenabstand, 12 mm frei
HATCH_B = dict(side=-1, w=12.0, v=(24.0, 90.0))     # Schalterbrett gegenüber
PANEL_W, PANEL_T = 11.0, 2.0                         # Schalterbrett (gedruckt/Platine), zwischen den Stangen bei u = ±6
PANEL_Y = (-33.1, -31.1)                             # Brett im Freiraum zwischen Trägerboden (y = -14,5) und Kupplerwand (-35,1)
PANEL_FACE_Y = -35.0                                 # Steckflächen bündig an der Kupplerinnenwand
# Bauteile des Schalterbretts: (Name, v0, v1, u-Halbbreite); Steckflächen nach -y
PANEL_PARTS = [("Schiebeschalter 2-polig", 28.0, 40.0, 3.0), ("USB-C-Buchse", 44.0, 53.0, 1.7),
               ("Lade-LED", 56.0, 59.0, 1.5), ("XT30-Buchse (2S Laden)", 61.0, 71.2, 2.5),
               ("XH-3-Buchse (Balancer)", 76.0, 83.5, 2.9)]
KEY_SWITCH_D = 12.0                                  # [Annahme] Schlüsselschalter Ø 12 (Gewindekörper), passt nicht in 12 mm Stangenlücke
KEY_HOLE_D = 12.4
KEY_PHI = 0.0                                        # Winkel der Bohrung im Kragen (+x)


def layout(config=None, tube_total=None):
    """Abgeleitete Längen und Massen einer Konfiguration. Liefert ein dict; z ab Düsenebene."""
    config = config or CONFIG
    d = dict(CONFIG=config)
    if config == "voll":
        if tube_total not in (None, 1000.0):
            raise ValueError("voll ist fest 2 × 500 mm")
        d["TUBE_TOTAL"] = 1000.0
        d["JOINT_Z"] = TUBE_BOTTOM_Z + TUBE_L
        d["COUPLER_INTO_UPPER"] = 75.0
        d["FC_COUPLER_Z"] = (d["JOINT_Z"] + 75.0 - COUPLER_L, d["JOINT_Z"] + 75.0)
        d["LEGS"] = True
        d["BAT2S"] = dict(BAT2S)
        d["FC_M_BOARD"] = FC_M_BOARD
        d["HATCH_HW_M"] = 0.0
    elif config == "erstflug":
        d["FC_COUPLER_Z"] = (KEY_COLLAR_Z[1] + 2.0, KEY_COLLAR_Z[1] + 2.0 + COUPLER_L)
        d["JOINT_Z"] = d["FC_COUPLER_Z"][0] + COUPLER_INTO_LOWER_EF
        d["COUPLER_INTO_UPPER"] = COUPLER_L - COUPLER_INTO_LOWER_EF
        d["LEGS"] = False
        d["BAT2S"] = dict(BAT2S, m=ERSTFLUG_BAT2S_M)
        d["FC_M_BOARD"] = ERSTFLUG_BOARD_M
        d["HATCH_HW_M"] = ERSTFLUG_HATCH_HW_M
    else:
        raise ValueError(config)
    d["BOARD_V0_Z"] = d["FC_COUPLER_Z"][0] + FC_RING_T + 4.0   # [Annahme] v = 0 (TVC-Ende der Platine)
    d["PISTON_Z0"] = d["FC_COUPLER_Z"][1] + PISTON_GAP
    d["CHUTE_Z0"] = d["PISTON_Z0"] + PISTON_L + 5.0
    d["CHUTE_Z1"] = d["CHUTE_Z0"] + CHUTE_L
    d["TUBE_MIN"] = d["CHUTE_Z1"] + CORD_BAY_MIN + NOSE_BULKHEAD_BELOW_BASE - TUBE_BOTTOM_Z
    if config == "erstflug":
        d["TUBE_TOTAL"] = tube_total or CONFIG_DEFAULT_TUBE_L[config]
        if d["TUBE_TOTAL"] < d["TUBE_MIN"] - 1e-6:
            raise ValueError(f"Rohr {d['TUBE_TOTAL']} mm kürzer als das Minimum {d['TUBE_MIN']:.0f} mm")
    top = TUBE_BOTTOM_Z + d["TUBE_TOTAL"]
    d["LOWER_TUBE_Z"] = (TUBE_BOTTOM_Z, d["JOINT_Z"])
    d["UPPER_TUBE_Z"] = (d["JOINT_Z"], top)
    d["NOSE_BASE_Z"] = top
    d["NOSE_TIP_Z"] = top + NOSE_L
    d["TOTAL_LENGTH"] = d["NOSE_TIP_Z"]
    d["CORD_BAY"] = top - NOSE_BULKHEAD_BELOW_BASE - d["CHUTE_Z1"]
    d["MISC_Z"] = d["JOINT_Z"]
    d["FC_M"] = d["FC_M_BOARD"] + FC_M_RINGS + FC_M_RODS + FC_M_CARRIER
    return d


def layout_ns(config=None, tube_total=None):
    return _types.SimpleNamespace(**layout(config, tube_total))


globals().update(layout(CONFIG, float(_os.environ["MS_TUBE_L"]) if "MS_TUBE_L" in _os.environ else None))
