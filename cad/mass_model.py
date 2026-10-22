"""Massenmodell der Rakete als Stabmodell: Zylinder, Zylinderschalen, Kegelschale, Quader, Stäbe, Punktmassen.

    python cad/mass_model.py          schreibt cad/mass_properties.md und cad/mass_properties.json

Jedes Teil hat Masse, Schwerpunkt (x, y, z in mm, z ab Düsenebene) und einen eigenen Trägheitstensor
um den eigenen Schwerpunkt; der Gesamttensor um den Gesamtschwerpunkt folgt mit dem Satz von Steiner.
Maße und Massen kommen aus cad/params.py. Drei Zustände: Start (voller Motor), Brennschluss (ohne
Treibstoff), ohne Motor (Adapter bleibt in der Rakete). Landebeine eingeklappt (Flugzustand); die
ausgefahrene Lage steht als Vergleich dabei.
"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import params as P

HERE = Path(__file__).resolve().parent


# ----------------------------------------------------------------------------- Grundkörper
class Part:
    def __init__(self, name, m, cg, I, group, src):
        self.name, self.m, self.cg, self.I, self.group, self.src = name, m, cg, I, group, src

    def __repr__(self):
        return f"{self.name}: {self.m} g @ z={self.cg[2]:.1f}"


def shell(name, m, ri, ro, z0, z1, group, src, x=0.0, y=0.0):
    """Zylinderschale um z (ri = 0: Vollzylinder)."""
    L = z1 - z0
    Izz = m * (ri * ri + ro * ro) / 2
    Ixx = m * ((ri * ri + ro * ro) / 4 + L * L / 12)
    return Part(name, m, (x, y, (z0 + z1) / 2), (Ixx, Ixx, Izz), group, src)


def box(name, m, lx, ly, lz, cx, cy, cz, group, src):
    return Part(name, m, (cx, cy, cz),
                (m * (ly * ly + lz * lz) / 12, m * (lx * lx + lz * lz) / 12, m * (lx * lx + ly * ly) / 12), group, src)


def cone_shell(name, m, r, h, z_base, group, src):
    """Dünne Kegelmantelfläche, Basis bei z_base, Spitze bei z_base + h. Schwerpunkt bei h/3 über der Basis."""
    Izz = m * r * r / 2
    Ixx = m * (r * r / 4 + h * h / 18)
    return Part(name, m, (0.0, 0.0, z_base + h / 3), (Ixx, Ixx, Izz), group, src)


def rod(name, m, p0, p1, group, src):
    """Dünner Stab von p0 nach p1 (beliebige Richtung)."""
    L = math.dist(p0, p1)
    d = [(b - a) / L for a, b in zip(p0, p1)]
    # Tensor eines Stabs: I = m L^2/12 (E - d d^T)
    k = m * L * L / 12
    I = [[k * ((1.0 if i == j else 0.0) - d[i] * d[j]) for j in range(3)] for i in range(3)]
    p = Part(name, m, tuple((a + b) / 2 for a, b in zip(p0, p1)), (I[0][0], I[1][1], I[2][2]), group, src)
    p.I_full = I
    return p


def point(name, m, cx, cy, cz, group, src):
    return Part(name, m, (cx, cy, cz), (0.0, 0.0, 0.0), group, src)


# ----------------------------------------------------------------------------- Teileliste
def parts(legs_deployed=False, config=None, tube_total=None):
    L = P.layout_ns(config, tube_total)
    ps = []
    # Motor
    ps.append(shell("Motorgehäuse E12 (ohne Treibstoff)", P.MOTOR_M - P.GRAIN_M, P.MOTOR_D / 2 - 1.5, P.MOTOR_D / 2,
                    *P.MOTOR_Z, "motor", "[BUILD] 64 g gesamt, 28 g Treibstoff"))
    ps.append(shell("Treibstoff E12", P.GRAIN_M, 0, P.GRAIN_D / 2, *P.GRAIN_Z, "propellant",
                    "[Annahme] Treibsatz bei z = 10…60 mm"))
    ps.append(shell("Adapter 29→24", P.ADAPTER_M, P.ADAPTER_ID / 2, P.ADAPTER_OD / 2, *P.ADAPTER_Z, "tvc",
                    "[Annahme] 15 g PLA"))
    # Kardan
    ps.append(shell("Motorrohr", P.MOTOR_TUBE_M, P.MOTOR_TUBE_ID / 2, P.MOTOR_TUBE_OD / 2, *P.MOTOR_TUBE_Z, "tvc",
                    "[Vorgabe] Kardan 50 g, Aufteilung [Annahme]"))
    ps.append(shell("Innenrahmen", P.INNER_M, P.INNER_RING_ID / 2, P.INNER_RING_OD / 2,
                    P.TVC_RING_Z, P.TVC_RING_Z + P.INNER_H, "tvc", "Anteil der 50 g"))
    ps.append(shell("Außenrahmen", P.OUTER_M, P.OUTER_RING_ID / 2, P.OUTER_RING_OD / 2,
                    P.TVC_RING_Z, P.TVC_RING_Z + P.OUTER_H, "tvc", "Anteil der 50 g"))
    ps.append(box("Servo Außenrahmen (y-Achse)", P.SERVO_M, P.SERVO_L, P.SERVO_T, P.SERVO_H,
                  0.0, -P.SERVO_OUTER_R, P.PIVOT_Z, "tvc", "[BUILD] W5652H 10 g"))
    ps.append(box("Servo Innenrahmen (x-Achse)", P.SERVO_M, P.SERVO_T, P.SERVO_L, P.SERVO_H,
                  P.SERVO_INNER_R, 0.0, P.PIVOT_Z, "tvc", "[BUILD] W5652H 10 g"))
    # Rumpf
    for nm, zz in (("Rohr unten", L.LOWER_TUBE_Z), ("Rohr oben", L.UPPER_TUBE_Z)):
        ps.append(shell(nm, (zz[1] - zz[0]) * P.TUBE_G_PER_MM, P.TUBE_ID / 2, P.TUBE_OD / 2, *zz, "airframe",
                        "[Klima] 240 g/m"))
    ps.append(shell("Kuppler Flugcomputer", P.COUPLER_M, P.COUPLER_ID / 2, P.COUPLER_OD / 2, *L.FC_COUPLER_Z,
                    "airframe", "[Klima] 34 g"))
    # Spitze
    ps.append(cone_shell("Spitze Kegel (ABS)", 80.0, P.TUBE_OD / 2, P.NOSE_L, L.NOSE_BASE_Z, "nose",
                         "[Klima] ca. 100 g gesamt; Aufteilung [Annahme]"))
    ps.append(shell("Spitze Schulterkuppler", 17.0, P.NOSE_SHOULDER_D / 2 - 1.2, P.NOSE_SHOULDER_D / 2,
                    L.NOSE_BASE_Z - P.NOSE_SHOULDER_L, L.NOSE_BASE_Z, "nose", "[Annahme]"))
    ps.append(shell("Spitze Spant + Öse", 3.0, 0, P.NOSE_SHOULDER_D / 2, L.NOSE_BASE_Z - 6, L.NOSE_BASE_Z - 3, "nose",
                    "[Annahme]"))
    # Flugcomputer
    zc = (L.FC_COUPLER_Z[0] + L.FC_COUPLER_Z[1]) / 2
    ps.append(box("Platine + Teensy + Bauteile", L.FC_M_BOARD, P.BOARD_W, 12.0, P.BOARD_L,
                  0.0, 4.0, L.BOARD_V0_Z + P.BOARD_L / 2, "fc", "[Annahme] Anteil der 100 g"))
    ps.append(shell("Endring unten", P.FC_M_RINGS * 0.3, 0, P.FC_RING_D / 2, L.FC_COUPLER_Z[0],
                    L.FC_COUPLER_Z[0] + P.FC_RING_T, "fc", "[Annahme]"))
    ps.append(shell("Endplatte oben (Spant mit Ladungsschale)", P.FC_M_RINGS * 0.7, 0, P.FC_RING_D / 2,
                    L.FC_COUPLER_Z[1] - P.FC_RING_T, L.FC_COUPLER_Z[1], "fc", "[Annahme]"))
    ps.append(shell("8 Gewindestangen M2", P.FC_M_RODS, 30.3, 30.3, *L.FC_COUPLER_Z, "fc", "[Annahme] als Ring auf r = 30,3"))
    ps.append(box("Träger (gedruckt)", P.FC_M_CARRIER, P.BOARD_W, P.CARRIER_DEPTH, P.BOARD_L,
                  0.0, -P.CARRIER_DEPTH / 2, L.BOARD_V0_Z + P.BOARD_L / 2, "fc", "[Annahme]"))
    b = L.BAT2S
    ps.append(box("Akku 2S", b["m"], b["w"], b["h"], b["l"], 0.0, -(P.BOARD_T / 2 + 2 + b["h"] / 2),
                  L.BOARD_V0_Z + b["v0"] + b["l"] / 2, "fc", "[Vorgabe] 45 g, Maße [BUILD]"))
    b = P.BAT1S
    ps.append(box("Akku 1S", b["m"], b["w"], b["h"], b["l"], 0.0, -(P.BOARD_T / 2 + 2 + b["h"] / 2),
                  L.BOARD_V0_Z + b["v0"] + b["l"] / 2, "fc", "[Vorgabe] 12 g, Maße [Annahme]"))
    # Bergung
    ps.append(shell("Kolben Kuppler-Stück", 9.0, P.COUPLER_ID / 2, P.COUPLER_OD / 2, L.PISTON_Z0,
                    L.PISTON_Z0 + P.PISTON_L, "recovery", "[Annahme] 34 g/150 mm × 40 mm"))
    ps.append(shell("Kolbenplatte", 10.0, 0, P.COUPLER_ID / 2, L.PISTON_Z0, L.PISTON_Z0 + P.PISTON_PLATE_T, "recovery",
                    "[Annahme]"))
    ps.append(shell("Ladungsschale + E-Match + Anker", 12.0, 0, 15.0, L.FC_COUPLER_Z[1], L.FC_COUPLER_Z[1] + 8,
                    "recovery", "[Annahme]"))
    ps.append(shell("Fallschirm 125 cm mit Schockschnur", P.CHUTE_M, 0, P.CHUTE_D / 2, L.CHUTE_Z0,
                    L.CHUTE_Z0 + P.CHUTE_L, "recovery", "[Vorgabe] 50 g"))
    if L.HATCH_HW_M:
        z0 = P.KEY_COLLAR_Z
        ps.append(shell("Schlüsselschalter-Kragen + Schlüsselschalter", 14.0, 24.0, P.COUPLER_OD / 2, *z0, "fc",
                        "[Annahme] Kragen 8 g, Schalter 6 g"))
        ps.append(box("Schalterbrett (Schalter, USB-C, XT30, XH-3, LED)", L.HATCH_HW_M - 14.0, P.PANEL_W, 8.0, 66.0,
                      0.0, -33.0, L.BOARD_V0_Z + 57.0, "fc", "[Annahme] Anteil von ERSTFLUG_HATCH_HW_M"))
    if not L.LEGS:
        ps.append(point("Kabel, Schrauben, Kleber", P.MISC_M, 0.0, 0.0, L.MISC_Z, "misc", "[Annahme] 20 g"))
        return ps
    # Landebeine
    ps.append(shell("Beinring unten (Hülse)", P.LEG_M_SLEEVE, P.LEG_SLEEVE_ID / 2, P.LEG_SLEEVE_OD / 2,
                    P.LEG_SLEEVE_Z0, P.LEG_SLEEVE_Z0 + P.LEG_SLEEVE_H, "legs", "[Vorgabe] 200 g gesamt, Aufteilung [Annahme]"))
    ps.append(shell("Beinring oben", P.LEG_M_UPPER_RING, P.LEG_UPPER_RING_ID / 2, P.LEG_UPPER_RING_OD / 2,
                    *P.LEG_UPPER_RING_Z, "legs", "Anteil der 200 g"))
    ang = math.radians(-P.LEG_DEPLOY_DEG if legs_deployed else P.LEG_STOW_DEG)
    for i in range(P.LEG_N):
        phi = math.radians(90 * i)
        c, s = math.cos(phi), math.sin(phi)
        h0 = (P.LEG_HINGE_R * c, P.LEG_HINGE_R * s, P.LEG_HINGE_Z)
        foot = ((P.LEG_HINGE_R + P.LEG_MAIN_L * math.cos(ang)) * c,
                (P.LEG_HINGE_R + P.LEG_MAIN_L * math.cos(ang)) * s,
                P.LEG_HINGE_Z + P.LEG_MAIN_L * math.sin(ang))
        t0 = (P.LEG_TOP_HINGE_R * c, P.LEG_TOP_HINGE_R * s, P.LEG_TOP_HINGE_Z)
        ps.append(rod(f"Bein {i + 1} Hauptstrebe", P.LEG_M_MAIN, h0, foot, "legs", "Anteil der 200 g"))
        ps.append(rod(f"Bein {i + 1} obere Strebe", P.LEG_M_TOP, t0, foot, "legs", "Anteil der 200 g"))
        ps.append(point(f"Bein {i + 1} Fuß", P.LEG_M_FOOT, *foot, "legs", "Anteil der 200 g"))
    ps.append(point("Kabel, Schrauben, Kleber", P.MISC_M, 0.0, 0.0, L.MISC_Z, "misc", "[Annahme] 20 g"))
    return ps


# ----------------------------------------------------------------------------- Auswertung
def properties(ps):
    m = sum(p.m for p in ps)
    cg = [sum(p.m * p.cg[i] for p in ps) / m for i in range(3)]
    I = [[0.0] * 3 for _ in range(3)]
    for p in ps:
        own = getattr(p, "I_full", None) or [[p.I[0], 0, 0], [0, p.I[1], 0], [0, 0, p.I[2]]]
        d = [p.cg[i] - cg[i] for i in range(3)]
        d2 = sum(x * x for x in d)
        for i in range(3):
            for j in range(3):
                I[i][j] += own[i][j] + p.m * ((d2 if i == j else 0.0) - d[i] * d[j])
    # g·mm² -> kg·m²: 1e-3 kg · 1e-6 m² = 1e-9
    I_si = [[v * 1e-9 for v in row] for row in I]
    return dict(mass_kg=m / 1000, cg_mm=cg, I_gmm2=I, inertia_kgm2=dict(Ixx=I_si[0][0], Iyy=I_si[1][1], Izz=I_si[2][2],
                                                                         Ixy=I_si[0][1], Ixz=I_si[0][2], Iyz=I_si[1][2]))


def configurations(config="voll", tube_total=None):
    base = parts(legs_deployed=False, config=config, tube_total=tube_total)
    confs = {
        "liftoff": ("Start, voller Motor", base),
        "burnout": ("Brennschluss, Treibstoff verbraucht", [p for p in base if p.group != "propellant"]),
        "no_motor": ("Ohne Motor (Adapter bleibt)", [p for p in base if p.group not in ("propellant", "motor")]),
    }
    out = {}
    for key, (label, ps) in confs.items():
        pr = properties(ps)
        pr["label"] = label
        pr["cg_from_nozzle_m"] = pr["cg_mm"][2] / 1000
        pr["lever_arm_m"] = (pr["cg_mm"][2] - P.PIVOT_Z) / 1000
        out[key] = pr
    return out, base


def write_json(confs, path):
    data = {
        "source": "cad/mass_model.py aus cad/params.py, Stabmodell (Zylinderschalen, Kegelschale, Quader, Stäbe, Punktmassen)",
        "date": "2026-10-21",
        "axes": "z Längsachse (+z zur Spitze), Ursprung Düsenebene; x zum Servo des Innenrahmens, y zum Lagerohr des Außenrahmens",
        "pivot_from_nozzle_m": P.PIVOT_Z / 1000,
        "legs": "eingeklappt (Flugzustand)",
        "configurations": {
            k: {
                "label": v["label"],
                "mass_kg": round(v["mass_kg"], 4),
                "cg_from_nozzle_m": round(v["cg_from_nozzle_m"], 4),
                "cg_lateral_m": [round(v["cg_mm"][0] / 1000, 5), round(v["cg_mm"][1] / 1000, 5)],
                "inertia_kgm2": {kk: round(vv, 6) for kk, vv in v["inertia_kgm2"].items()},
                "lever_arm_m": round(v["lever_arm_m"], 4),
            } for k, v in confs.items()
        },
    }
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(confs, base, path):
    L = []
    L.append("# Massenmodell und Trägheitsmomente\n")
    L.append("Erzeugt von `cad/mass_model.py` aus `cad/params.py` am 21.10.2026. Nicht von Hand ändern, Skript laufen lassen.\n")
    L.append("## Methode\n")
    L.append("Stabmodell: jedes Teil ist eine Zylinderschale, ein Vollzylinder, eine Kegelmantelfläche, ein Quader, "
             "ein dünner Stab oder eine Punktmasse mit bekannter Masse und Lage. Für jedes Teil wird der Trägheitstensor "
             "um den eigenen Schwerpunkt gebildet und mit dem Satz von Steiner auf den Gesamtschwerpunkt umgerechnet. "
             "Koordinaten wie in der Firmware: z ist die Längsachse, z = 0 die Düsenebene, +z zur Spitze; "
             "x zeigt zum Servo des Innenrahmens, y zum Lagerohr des Außenrahmens. Die Blender-Dateien lieferten nur "
             "Längen und Lagen (siehe `blender_inventory.md`), keine Massen.\n")
    L.append(f"Kardanpunkt (Schnittpunkt der beiden Kipp-Achsen): **{P.PIVOT_Z:.1f} mm** über der Düsenebene "
             f"(Rahmen-Grundfläche {P.TVC_RING_Z:.0f} mm + Servomitte {P.PIVOT_H:.1f} mm aus Blender). "
             f"Rohrunterkante {P.TUBE_BOTTOM_Z:.0f} mm, Stoß der Rohre {P.JOINT_Z:.0f} mm, Rohroberkante {P.UPPER_TUBE_Z[1]:.0f} mm, "
             f"Spitze {P.NOSE_TIP_Z:.0f} mm. Landebeine eingeklappt (Flugzustand).\n")
    L.append("## Ergebnis\n")
    L.append("| Zustand | Masse | Schwerpunkt ab Düse | Hebelarm Kardan–Schwerpunkt | Ixx | Iyy | Izz |")
    L.append("|---|---|---|---|---|---|---|")
    for k, v in confs.items():
        I = v["inertia_kgm2"]
        L.append(f"| {v['label']} | {v['mass_kg'] * 1000:.0f} g | {v['cg_mm'][2]:.0f} mm | {v['lever_arm_m'] * 1000:.0f} mm "
                 f"| {I['Ixx']:.4f} kg·m² | {I['Iyy']:.4f} kg·m² | {I['Izz']:.5f} kg·m² |")
    L.append("")
    v = confs["liftoff"]
    L.append(f"Seitlicher Schwerpunktversatz beim Start: x = {v['cg_mm'][0]:.1f} mm, y = {v['cg_mm'][1]:.1f} mm "
             "(Servos, Akkus unter der Platine, Teensy darüber). Die Deviationsmomente stehen in der JSON.\n")
    L.append("Zum Vergleich die bisherigen Platzhalter der Simulation: m = 0,94 kg, Ix = Iy = Iz = 0,1 kg·m², Hebelarm 0,30 m. "
             "Das Quer-Trägheitsmoment Ixx = Iyy trifft den Platzhalter nahezu, aber Izz (Rollachse) ist "
             "hundertmal kleiner, denn fast alle Masse liegt innerhalb von r = 37 mm. Der Hebelarm ist länger als 0,30 m, "
             "weil Flugcomputer, Akkus und Kuppler im Rohrstoß 500 mm über der Düse sitzen und die Spitze 100 g wiegt. "
             "Für die Rollregelung mit dem Platzhalter 0,1 kg·m² wäre die Dynamik also um zwei Größenordnungen falsch.\n")
    dep = properties(parts(legs_deployed=True))
    L.append(f"Mit ausgefahrenen Beinen (Landung, ohne Motor-Treibstoff wäre es entsprechend weniger): "
             f"Schwerpunkt {dep['cg_mm'][2]:.0f} mm, Ixx = {dep['inertia_kgm2']['Ixx']:.4f} kg·m², "
             f"Izz = {dep['inertia_kgm2']['Izz']:.4f} kg·m² (Startmasse).\n")
    L.append("## Teileliste (Startzustand)\n")
    L.append("| Teil | Masse | z Schwerpunkt | Quelle / Annahme |")
    L.append("|---|---|---|---|")
    for p in base:
        L.append(f"| {p.name} | {p.m:.1f} g | {p.cg[2]:.0f} mm | {p.src} |")
    m = sum(p.m for p in base)
    L.append(f"| **Summe** | **{m:.0f} g** | | |")
    L.append("")
    L.append("## Abweichung vom Massenbudget `Gewicht.csv` (902 g)\n")
    L.append("Das Budget vom Juni 2025 rechnet mit zwei Motoren (128 g), aber ohne Servos, Adapter, Kolben-Ausstoß, "
             "zweiten Akku und Kleinteile. Mit einem Motor und den Teilen der Entscheidungen vom 21.10.2026 kommt das "
             f"Stabmodell auf {m:.0f} g. Die größten Unsicherheiten: Landesystem (200 g Vorgabe, keine Konstruktion), "
             "Flugcomputer 100 g (Platine rev B existiert noch nicht), Kolben-Ausstoß und Kleinteile (Schätzung).\n")
    L.append("## Nachzumessen\n")
    L.append("- Masse von Spitze, Kuppler, Rohr auf der Küchenwaage (Shop-Angaben: 100 / 34 / 120 g).")
    L.append("- Motor E12 wiegen; Lage des Treibsatzes aus dem Datenblatt (hier z = 10 bis 60 mm angenommen).")
    L.append("- Gedruckte Kardanteile wiegen (hier 50 g gesamt).")
    L.append("- Nach dem Zusammenbau: Schwerpunkt per Auswiegen (Rakete auf einer Kante balancieren) und Quer-Trägheitsmoment "
             "per Pendelversuch (bifilar). Beides gegen diese Tabelle halten und `params.py` anpassen.\n")
    path.write_text("\n".join(L), encoding="utf-8")


def erstflug_variants():
    """voll (1000 mm) gegen Erstflug mit 700 mm und mit dem kürzesten passenden Rohr."""
    tmin = math.ceil(P.layout("erstflug")["TUBE_MIN"])
    var = {}
    for key, (cfg, tl, label) in {
        "voll_1000": ("voll", None, "voll, Beine, 850-mAh-2S"),
        "erstflug_700": ("erstflug", 700.0, "Erstflug"),
        "erstflug_min": ("erstflug", float(tmin), "Erstflug, kürzestes Rohr"),
    }.items():
        confs, base = configurations(cfg, tl)
        var[key] = dict(label=label, config=cfg, layout=P.layout(cfg, tl), confs=confs, parts=base)
    return var


def write_erstflug_md(var):
    L = []
    d = var["erstflug_700"]["layout"]
    dm = var["erstflug_min"]["layout"]
    z = dm["FC_COUPLER_Z"]
    L.append("\n## Erstflug-Konfiguration (22.10.2026)\n")
    L.append("Entscheidung Jan 22.10.2026: Aufstieg mit einem Motor (TSP E12-0) und Fallschirm, kein Landesystem, Rohr aus Papier. "
             "Gegenüber der Konfiguration oben (`config=\"voll\"`) gilt bei `config=\"erstflug\"` (`MS_CONFIG=erstflug`, "
             "`layout()` in `params.py`):\n")
    L.append("- keine Beine, kein Beinring, kein Aktor (−200 g); der zweite Motor war im Modell schon nicht enthalten.")
    L.append(f"- 2S-Akku 450 mAh mit {P.ERSTFLUG_BAT2S_M:.0f} g statt 45 g (Abmessungen 56 × 25,5 × 8 der 850er zur Sicherheit "
             f"beibehalten); Mainboard 54 × 120 mit Teensy {P.ERSTFLUG_BOARD_M:.0f} g statt 40 g.")
    L.append(f"- Hardware der Luken (Schalterbrett, Schlüsselschalter, Kragen) {P.ERSTFLUG_HATCH_HW_M:.0f} g [Annahme], neu.")
    L.append(f"- Kolbenabstand {P.PISTON_GAP:.0f} statt 5 mm (auch bei \"voll\"): die Ladungsschale (8 mm) und die Öse (8,5 mm) der Endplatte "
             "durchdrangen sonst die Kolbenplatte.")
    L.append(f"- Das Rohr beginnt wie bisher bei z = 20 mm. Über dem Kardan folgt der Schlüsselschalter-Kragen "
             f"(z = {P.KEY_COLLAR_Z[0]:.0f} … {P.KEY_COLLAR_Z[1]:.0f}), dann der Kuppler. Der Kuppler steckt nur "
             f"{P.COUPLER_INTO_LOWER_EF:.0f} mm im unteren Rohr; der Stoß liegt bei z = {d['JOINT_Z']:.0f} mm, beide Luken liegen im oberen "
             "Rohr. Rohrmasse 0,24 g/mm.\n")
    L.append("### Kürzestes Rohr\n")
    L.append("Rohrlänge = Rohrunterkante (z = 20 mm) bis Spitzenbasis. Die Stapelhöhe über dem Kardan bestimmt das Minimum:\n")
    L.append("| Abschnitt | Länge | z von … bis |")
    L.append("|---|---|---|")
    L.append(f"| Kardan (Motorrohr endet bei 103, mit 7° bis 105) | | 20 … {P.KEY_COLLAR_Z[0]:.0f} |")
    L.append(f"| Schlüsselschalter-Kragen + 2 mm Luft | {z[0] - P.KEY_COLLAR_Z[0]:.0f} mm | {P.KEY_COLLAR_Z[0]:.0f} … {z[0]:.0f} |")
    L.append(f"| Flugcomputer-Kuppler | {P.COUPLER_L:.0f} mm | {z[0]:.0f} … {z[1]:.0f} |")
    L.append(f"| Gasraum + Kolben | {P.PISTON_GAP:.0f} + {P.PISTON_L:.0f} mm | {z[1]:.0f} … {dm['PISTON_Z0'] + P.PISTON_L:.0f} |")
    L.append(f"| Fallschirm 125 cm (Ø {P.CHUTE_D:.0f} × {P.CHUTE_L:.0f}) mit 5 mm Luft | {P.CHUTE_L + 5:.0f} mm | {dm['CHUTE_Z0']:.0f} … {dm['CHUTE_Z1']:.0f} |")
    L.append(f"| Schockschnur | {P.CORD_BAY_MIN:.0f} mm | {dm['CHUTE_Z1']:.0f} … {dm['CHUTE_Z1'] + P.CORD_BAY_MIN:.0f} |")
    L.append(f"| Schulter der Spitze bis Spant | {P.NOSE_BULKHEAD_BELOW_BASE:.0f} mm | … {dm['NOSE_BASE_Z']:.0f} (Rohrende) |")
    L.append(f"| **Rohr gesamt (Minimum)** | **{dm['TUBE_TOTAL']:.0f} mm** | |")
    L.append("")
    L.append("Das Minimum hängt an Annahmen: gepackter Fallschirm 230 mm (`CHUTE_L`), 50 mm Raum für die Schockschnur (`CORD_BAY_MIN`), "
             "Kolben 40 mm. Jede 10 mm weniger Schirm oder Schnurraum kürzen das Rohr um 10 mm (2,4 g). Beim Packen nachmessen. "
             f"Bei 700 mm bleiben {d['CORD_BAY']:.0f} mm Raum über dem Schirm.\n")
    L.append("### Ergebnis\n")
    L.append("| Konfiguration | Rohr | Start | Schwerpunkt ab Düse | Hebelarm Kardan–CG | Ixx = Iyy | Izz | Brennschluss | Hebelarm BS |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for v in var.values():
        lo, bo = v["confs"]["liftoff"], v["confs"]["burnout"]
        L.append(f"| {v['label']} | {v['layout']['TUBE_TOTAL']:.0f} mm | **{lo['mass_kg'] * 1000:.0f} g** | {lo['cg_mm'][2]:.0f} mm "
                 f"| {lo['lever_arm_m'] * 1000:.0f} mm | {lo['inertia_kgm2']['Ixx']:.4f} kg·m² | {lo['inertia_kgm2']['Izz']:.5f} kg·m² "
                 f"| {bo['mass_kg'] * 1000:.0f} g | {bo['lever_arm_m'] * 1000:.0f} mm |")
    L.append("")
    e7, em = var["erstflug_700"]["confs"]["liftoff"], var["erstflug_min"]["confs"]["liftoff"]
    L.append(f"Ziel unter 750 g: {'erreicht' if e7['mass_kg'] < 0.75 else 'verfehlt'} "
             f"({e7['mass_kg'] * 1000:.0f} g bei 700 mm, {em['mass_kg'] * 1000:.0f} g bei {dm['TUBE_TOTAL']:.0f} mm). "
             f"Schub-Gewicht mit 12 N mittlerem Schub bei 700 mm: {12 / (e7['mass_kg'] * 9.81):.2f}.\n")
    L.append("### Teileliste Erstflug, Rohr 700 mm (Start)\n")
    L.append("| Teil | Masse | z Schwerpunkt | Quelle / Annahme |")
    L.append("|---|---|---|---|")
    for p in var["erstflug_700"]["parts"]:
        L.append(f"| {p.name} | {p.m:.1f} g | {p.cg[2]:.0f} mm | {p.src} |")
    L.append(f"| **Summe** | **{sum(p.m for p in var['erstflug_700']['parts']):.0f} g** | | |")
    L.append("")
    return "\n".join(L)


def write_erstflug_json(var, path):
    js = json.loads(path.read_text(encoding="utf-8"))
    js["erstflug_2026-10-22"] = {
        "note": "config erstflug: ohne Beine, 2S 450 mAh 30 g, Mainboard 54x120 45 g; Details in mass_properties.md",
        "variants": {k: {
            "label": v["label"], "tube_mm": v["layout"]["TUBE_TOTAL"], "tube_min_mm": round(v["layout"]["TUBE_MIN"], 1),
            "coupler_z_mm": list(v["layout"]["FC_COUPLER_Z"]), "joint_z_mm": v["layout"]["JOINT_Z"],
            "total_length_mm": v["layout"]["TOTAL_LENGTH"], "cord_bay_mm": round(v["layout"]["CORD_BAY"], 1),
            "configurations": {kk: {"mass_kg": round(c["mass_kg"], 4), "cg_from_nozzle_m": round(c["cg_from_nozzle_m"], 4),
                                    "lever_arm_m": round(c["lever_arm_m"], 4),
                                    "inertia_kgm2": {n: round(x, 6) for n, x in c["inertia_kgm2"].items()}}
                               for kk, c in v["confs"].items()}} for k, v in var.items()}}
    path.write_text(json.dumps(js, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if P.CONFIG != "voll":
        sys.exit("mass_model.py schreibt alle Varianten selbst; MS_CONFIG nicht setzen")
    confs, base = configurations("voll")
    write_json(confs, HERE / "mass_properties.json")
    write_md(confs, base, HERE / "mass_properties.md")
    var = erstflug_variants()
    with open(HERE / "mass_properties.md", "a", encoding="utf-8") as f:
        f.write(write_erstflug_md(var))
    write_erstflug_json(var, HERE / "mass_properties.json")
    for k, v in confs.items():
        I = v["inertia_kgm2"]
        print(f"{k:9s} m={v['mass_kg']:.3f} kg  cg={v['cg_mm'][2]:.0f} mm  lever={v['lever_arm_m']:.3f} m  "
              f"Ixx={I['Ixx']:.4f} Iyy={I['Iyy']:.4f} Izz={I['Izz']:.5f} kg m^2")
    for k, v in var.items():
        c = v["confs"]["liftoff"]
        print(f"{k:13s} tube={v['layout']['TUBE_TOTAL']:.0f} m={c['mass_kg']:.3f} cg={c['cg_mm'][2]:.0f} "
              f"lever={c['lever_arm_m']:.3f} Ixx={c['inertia_kgm2']['Ixx']:.4f} Izz={c['inertia_kgm2']['Izz']:.5f}")
