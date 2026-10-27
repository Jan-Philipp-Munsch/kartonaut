"""Massenbudget der Modulbauweise Kartonaut 1, Stand 2b (22.10.2026): Masse, Schwerpunkt, Hebelarm, Trägheit.

    python cad/mass_stand2b.py        schreibt cad/mass_stand2b.md und cad/mass_stand2b.json

Dasselbe Stabmodell wie mass_model.py (Zylinderschalen, Quader, Kegelschale, Stäbe, Punktmassen), aber mit den
Maßen der Modulbauweise aus modular_params.py (Rohr A 125 + B 176 + C 195, Kuppler J1 75, Schlitten mit Spant,
CO₂-Ausstoß, Schirm in Rohr C, kein Rollmotor, kein Schlüsselschalter, keine Gewindestangen) und den Druckteil-
Massen aus export/modular/masses.json (75 % des CAD-Volumens, PETG). Koordinaten wie modular_params.py: z ab der
Rohrunterkante von Rohr A (= Düsenebene, der Motor steht bündig), +z zur Spitze; x zum Servo des Innenrahmens.

Gegenüber der Schätzung in modular.py (689 g) sind hier Teile ergänzt, die dort fehlten: LoRa-Wendel mit Pigtail,
das Servo der CO₂-Auslösung, die Bauteile auf dem Schalterbrett, die Ringschraube, Servohebel und Drahtbügel.
Die JSON hat dasselbe Format wie mass_properties.json, damit die Simulation sie lesen kann (--vehicle stand2b).

Seit dem 23.10.2026 (Stand 2c): Druckteile im Leichtbau (Spantplatte 3,5 mm mit 5-mm-Rand, Zapfen 2 mm, U-Profil statt
Klotz, Bodenfenster, Scheibe 2 mm, Schraubring 2 mm) und Massen mit einem Slicer-Modell statt 75 % des Volumens
(Oberfläche × 1 mm voll, Rest 25 %). Dazu eine Hebeltabelle (LEVERS, PACKAGES): jede weitere Maßnahme mit Masse,
Schwerpunkt, Hebelarm und Trägheit; die Pakete liegen in der JSON unter "levers" für scripts/check_stand2b_levers.py.
"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import params as P
import modular_params as M
from mass_model import Part, shell, box, cone_shell, rod, point, properties

PIVOT_Z = M.GIMBAL_BASE_Z + P.PIVOT_H          # Kardanpunkt der gebauten Druckdatei: 38 + 31,5 = 69,5 mm
PRINTED = {d["teil"]: d["g"] for d in json.loads((HERE / "export" / "modular" / "masses.json").read_text(encoding="utf-8"))["druckteile"]}
SG90_M = 9.0                                   # [Annahme] Servo der CO₂-Auslösung (SG90 vorhanden, BUILD §1.3)
LORA_M = 5.0                                   # [Annahme] 433-MHz-Wendel + U.FL-Pigtail 200 mm
PANEL_HW_M = 8.0                               # [Annahme] Schiebeschalter, USB-C-Breakout, XT30, XH-3, LED, Kabel am Schalterbrett
BAT1S_M = 14.0                                 # [Annahme] 1S 600 mAh mit JST-PH (Modell "voll": 12 g für 450–600 mAh)
NOSE_M = 83.0                                  # [Klima] Kegel ca. 80 g + Holzplatte mit Haken 3 g [Annahme]; Schulter ist der zweite halbe Kuppler
SCREWS_M = 8.0                                 # [Annahme] ca. 20 × M3 mit Muttern
MISC_M = P.MISC_M + 2.0                        # [Annahme] Kabel, Kleber 20 g + Moosgummi, Schaum, Durchführung 2 g
HORN_M = 1.5                                   # [Annahme] je Servo: Hebel + Drahtbügel
BAND_SHARE = 0.62                              # [CAD] Volumenanteil von Rand, Spantplatte und Zapfen am Schlitten (Stand 2d: ca. 29 von 46,6 cm³, Zapfen mit Fenstern)
MASS_2B = 723.0                                # Startmasse Stand 2b (Druckteile 98 g nach der 75-%-Regel), zum Vergleich


def _rot(x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return x * c - y * s, x * s + y * c


def parts():
    ps = []
    # --- M1 Antrieb: Rohr A mit dem gebauten Kardan, Motor bündig
    ps.append(shell("Motorgehäuse E12 (ohne Treibstoff)", P.MOTOR_M - P.GRAIN_M, P.MOTOR_D / 2 - 1.5, P.MOTOR_D / 2,
                    0.0, M.MOTOR_L, "motor", "[BUILD] 64 g gesamt, 28 g Treibstoff; bündig mit Rohr A [Jan]"))
    ps.append(shell("Treibstoff E12", P.GRAIN_M, 0, P.GRAIN_D / 2, *P.GRAIN_Z, "propellant", "[Annahme] Treibsatz bei z = 10…60 mm"))
    ps.append(shell("Adapter 29→24", P.ADAPTER_M, P.ADAPTER_ID / 2, P.ADAPTER_OD / 2, 8.0, M.MOTOR_L, "tvc", "[Annahme] 15 g PLA"))
    ps.append(shell("Motorrohr (gedruckt, Blender 12.06.2025)", P.MOTOR_TUBE_M, P.MOTOR_TUBE_ID / 2, P.MOTOR_TUBE_OD / 2,
                    M.GIMBAL_BASE_Z, M.GIMBAL_TOP_Z, "tvc", "[Vorgabe] Kardan 50 g, Aufteilung [Annahme]"))
    ps.append(shell("Innenrahmen", P.INNER_M, P.INNER_RING_ID / 2, P.INNER_RING_OD / 2, M.GIMBAL_BASE_Z, 86.4, "tvc", "Anteil der 50 g"))
    ps.append(shell("Außenrahmen mit Flansch", P.OUTER_M, P.OUTER_RING_ID / 2, P.OUTER_RING_OD / 2, M.GIMBAL_BASE_Z, 86.4, "tvc", "Anteil der 50 g"))
    L, H, T = M.SERVO_BODY
    for name, (cx, cy, cz), (rx, ry), *_ in M.SERVOS:
        x, y = _rot(cx, cy, M.GIMBAL_ROT_DEG)
        ps.append(box(f"Servo {name}", P.SERVO_M, L, T, H, x, y, M.GIMBAL_BASE_Z + cz, "tvc", "[BUILD] W5652H 10 g, Lage aus der Druckdatei"))
        ps.append(point(f"Hebel + Drahtbügel ({name.split(' ')[1]})", HORN_M, x * 0.9, y * 0.9, M.GIMBAL_BASE_Z + M.SERVO_SHAFT_Z + M.HORN_R / 2, "tvc",
                        "[Annahme] 1,5 g je Servo, Hebel nach oben (Jans Fotos)"))
    ps.append(shell("Rohr A 125 (Kardan)", M.tube_mass(*M.TUBE_A), P.TUBE_ID / 2, P.TUBE_OD / 2, *M.TUBE_A, "airframe", "[Klima] 0,24 g/mm, Länge [Jan]"))
    # --- Stoß J1
    ps.append(shell("Kuppler J1 75 mm (in B verklebt)", P.COUPLER_M / 2, P.COUPLER_ID / 2, P.COUPLER_OD / 2, *M.J1_COUPLER, "airframe", "[Klima] halber Kuppler 17 g"))
    ps.append(shell("Schraubring J1 (gedruckt)", PRINTED["Schraubring J1"], M.J1_RING["id"] / 2, M.J1_RING["od"] / 2, *M.J1_RING["z"], "printed", "masses.json, 75 % Volumen PETG"))
    # --- M2 Avionik: Rohr B
    ps.append(shell("Rohr B 176 (Avionik)", M.tube_mass(*M.TUBE_B), P.TUBE_ID / 2, P.TUBE_OD / 2, *M.TUBE_B, "airframe", "[Klima] 0,24 g/mm, Länge [Jan]"))
    ps.append(shell("Untere Scheibe (gedruckt)", PRINTED["Untere Scheibe"], 0, M.DISC_OD / 2, *M.DISC_Z, "printed", "masses.json"))
    sled = PRINTED["Schlitten mit Spant"]
    band_m = BAND_SHARE * sled
    ps.append(shell("Schlitten: Band, Spantplatte, beide Zapfen", band_m, 33.0, P.TUBE_OD / 2, M.SPIGOT_B["z"][0], M.SPIGOT_C["z"][1], "printed",
                    f"[CAD] {100 * BAND_SHARE:.0f} % der {sled:.0f} g (Volumenanteil Stand 2d, Slicer-Modell)"))
    ps.append(box("Schlitten: Träger, Säulen, Fächer, GPS-Leisten", sled - band_m, P.BOARD_W, 14.0, M.SPIGOT_B["z"][0] - M.DISC_Z[1],
                  0.0, -7.0, (M.DISC_Z[1] + M.SPIGOT_B["z"][0]) / 2, "printed", "Rest der Schlittenmasse, unter der Platine"))
    ps.append(box("Platine rev B1 + Teensy + Bauteile", P.ERSTFLUG_BOARD_M, P.BOARD_W, P.BOARD_T, P.BOARD_L, 0.0, 0.0,
                  M.BOARD_V0_Z + P.BOARD_L / 2, "fc", "[Vorgabe] 45 g"))
    b = M.BAT2S
    ps.append(box("Akku 2S LemonRC 450 mAh", 29.0, b["w"], b["h"], b["l"], 0.0, M.TRAY_FLOOR_Y + b["h"] / 2,
                  M.v_to_z(b["v0"]) + b["l"] / 2, "fc", "[reichelt] 29 g"))
    b = M.BAT1S
    ps.append(box("Akku 1S 600 mAh", BAT1S_M, b["w"], b["h"], b["l"], 0.0, M.TRAY_FLOOR_Y + b["h"] / 2,
                  M.v_to_z(b["v0"]) + b["l"] / 2, "fc", "[Annahme] 14 g, vorhanden (BUILD §1.3)"))
    g = M.GPS
    ps.append(box("GPS NEO-6M (GY-GPS6MV2) mit Patch 25 × 25", g["m"], g["w"], g["h"], g["l"], 0.0, sum(g["y"]) / 2, g["z_top"] - g["h"] / 2, "fc", "[Annahme] 12 g, wiegen"))
    h = M.LORA_HELIX
    ps.append(rod("LoRa-Wendel + Pigtail", LORA_M, (h["x"], h["y"], h["z_top"] - h["l"]), (h["x"], h["y"], h["z_top"] + 20), "fc", "[Annahme] 5 g"))
    ps.append(box("Schalterbrett (gedruckt)", PRINTED["Schalterbrett"], M.PANEL_W, M.PANEL_T, M.HATCH_B["v"][1] - M.HATCH_B["v"][0],
                  0.0, sum(M.PANEL_Y) / 2, M.v_to_z(sum(M.HATCH_B["v"]) / 2), "printed", "masses.json"))
    ps.append(box("Schalterbrett: Schalter, USB-C, XT30, XH-3, LED, Kabel", PANEL_HW_M, M.PANEL_W, 8.0, 40.0, 0.0, M.PANEL_Y[0] + 4.0,
                  M.v_to_z(45.0), "fc", "[Annahme] 8 g"))
    ps.append(point("ARM-Brücke / Schraubschalter", 2.0, 0.0, -30.0, M.v_to_z(M.ARM_SCREW_SWITCH["v"]), "fc", "[Annahme] 2 g"))
    ps.append(point("Ringschraube M4 mit Mutter", 4.0, 0.0, 12.0, M.BAND_Z[0] + 2.5, "misc", "[Annahme] 4 g"))
    # --- M3 Bergung: Rohr C
    ps.append(shell("Rohr C 195 (Bergung)", M.tube_mass(*M.TUBE_C), P.TUBE_ID / 2, P.TUBE_OD / 2, *M.TUBE_C, "airframe", "[Klima] 0,24 g/mm"))
    c = M.CO2
    zc = M.CO2_Z0 + c["h"] / 2
    ps.append(box("CO₂-Modul: Aufbau (gedruckt, Anstecher)", c["m_aufbau"], c["l"], c["d"] + 6, c["h"], 0.0, 0.0, zc, "ejection", "[Jan] ca. 10 g"))
    ps.append(rod("CO₂-Kapsel 8 g, gefüllt (quer)", c["m_kapsel"], (-c["l"] / 2, 0.0, zc), (c["l"] / 2, 0.0, zc), "ejection", "[Annahme] 25 g, Stahl 18 × 65"))
    ps.append(point("Servo CO₂-Auslösung (SG90)", SG90_M, 0.0, 18.0, zc, "ejection", "[Annahme] 9 g, Auslösung über Servo (Bauanleitung §1.1)"))
    ps.append(shell("Fallschirm 125 cm mit Schockschnur, gepackt", P.CHUTE_M, 0, M.CHUTE["d"] / 2, *M.CHUTE_Z, "recovery", "[Vorgabe] 50 g"))
    ps.append(shell("Kuppler Spitze 75 mm (in der Spitze verklebt)", P.COUPLER_M / 2, P.COUPLER_ID / 2, P.COUPLER_OD / 2, *M.NOSE_COUPLER_Z, "nose", "[Klima] halber Kuppler 17 g"))
    ps.append(cone_shell("Spitze Klima 8539 mit Holzplatte und Haken", NOSE_M, P.TUBE_OD / 2, P.NOSE_L, M.TOP_Z, "nose", "[Klima] ca. 100 g inkl. Schulter; hier ohne Schulter"))
    # --- Kleinteile
    ps.append(point("M3-Schrauben und Muttern (ca. 20)", SCREWS_M, 0.0, 0.0, 200.0, "misc", "[Annahme] 8 g"))
    ps.append(point("Kabel, Kleber, Moosgummi, Schaum", MISC_M, 0.0, 0.0, 230.0, "misc", "[Annahme] 22 g"))
    return ps


def configurations():
    base = parts()
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
        pr["lever_arm_m"] = (pr["cg_mm"][2] - PIVOT_Z) / 1000
        out[key] = pr
    return out, base


# ----------------------------------------------------------------------------- Hebel
def _scaled(p, m, note):
    f = m / p.m
    q = Part(p.name, m, p.cg, tuple(i * f for i in p.I), p.group, p.src + f"; Hebel: {note}")
    if getattr(p, "I_full", None):
        q.I_full = [[v * f for v in row] for row in p.I_full]
    return q


def _shifted(p, dz):
    q = Part(p.name, p.m, (p.cg[0], p.cg[1], p.cg[2] + dz), p.I, p.group, p.src)
    if getattr(p, "I_full", None):
        q.I_full = p.I_full
    return q


def _set_mass(name_part, m, note):
    def f(ps):
        hit = [p for p in ps if name_part in p.name]
        assert hit, name_part
        return [_scaled(p, m, note) if name_part in p.name else p for p in ps]
    return f


def _shorten_c(dl, note):
    """Rohr C um dl kürzer: alles darüber (Kuppler der Spitze, Spitze) rückt um dl nach unten."""
    def f(ps):
        out = []
        z_cut = M.CHUTE_Z[1]
        for p in ps:
            if p.name.startswith("Rohr C"):
                z0, z1 = M.TUBE_C[0], M.TUBE_C[1] - dl
                out.append(shell(p.name, M.tube_mass(z0, z1), P.TUBE_ID / 2, P.TUBE_OD / 2, z0, z1, p.group, p.src + f"; Hebel: {note}"))
            elif p.cg[2] > z_cut:
                out.append(_shifted(p, -dl))
            else:
                out.append(p)
        return out
    return f


def _chain(*fs):
    def f(ps):
        for g in fs:
            ps = g(ps)
        return ps
    return f


# Jeder Hebel: (Schlüssel, Beschreibung, Funktion auf der Teileliste, Bewertung). Massen mit [Annahme] sind Händler- oder
# Schätzwerte, keine Wägung.
LEVERS = [
    ("akku300", "2S-Akku 300 statt 450 mAh (ca. 20 statt 29 g) [Annahme]", _set_mass("Akku 2S", 20.0, "2S 300 mAh"),
     "reicht für 2 Servos und das CO₂-Servo über Stunden; 35C × 0,3 Ah = 10 A Spitze"),
    ("adapter", "Motoradapter 29→24 als drei Ringe statt Vollrohr (7 statt 15 g) [Annahme]", _set_mass("Adapter 29", 7.0, "Ringadapter"),
     "neu drucken; der Motor sitzt weiter im gebauten Motorrohr"),
    ("mikroservo", "Mikroservo 4,5 g statt SG90 (9 g) für die CO₂-Auslösung [Annahme]", _set_mass("Servo CO₂", 4.5, "Mikroservo"),
     "Stellkraft für den Anstecher prüfen"),
    ("kuppler50", "Spitzen-Kuppler 50 statt 75 mm (25 in der Spitze, 25 in Rohr C), Rohr C 170 statt 195 mm",
     _chain(_set_mass("Kuppler Spitze", P.COUPLER_M / 3, "Kuppler 50 mm"), _shorten_c(25.0, "Kuppler 50 mm")),
     "Schnurraum 97 statt 194 cm³; 1 m Kevlar und 1,8 m Gummischnur brauchen ca. 30 cm³"),
    ("schirm100", "Fallschirm 100 statt 125 cm (ca. 35 statt 50 g, gepackt 80 statt 100 mm) [Annahme]",
     _chain(_set_mass("Fallschirm", 35.0, "Schirm 100 cm"), _shorten_c(20.0, "Schirm 100 cm")),
     "Sinkrate 3,4 → 4,3 m/s (Cd 0,75), Aufprallenergie +60 %; muss gekauft werden"),
    ("feder", "Federausstoß mit Servoriegel statt CO₂ (Feder 5 g + Riegel 3 g + Mikroservo 4,5 g statt 44 g) [Konzept]",
     lambda ps: [(_scaled(p, {"CO₂-Modul: Aufbau (gedruckt, Anstecher)": 8.0, "CO₂-Kapsel 8 g, gefüllt (quer)": 0.01,
                              "Servo CO₂-Auslösung (SG90)": 4.5}[p.name], "Feder") if p.group == "ejection" else p) for p in ps],
     "Konzeptänderung (Jan 22.10.: CO₂); Feder muss Spitze und Schirm 100 mm weit schieben, am Tisch beliebig testbar"),
    ("spitze_druck", "Spitze gedruckt, dünnwandig (45 statt 83 g) [Annahme]", _set_mass("Spitze Klima", 45.0, "gedruckte Spitze"),
     "nimmt Masse ganz oben weg: Schwerpunkt und Hebelarm sinken deutlich"),
]
PACKAGES = [
    ("P1", "ohne Konzeptänderung: Akku, Adapter, Mikroservo, kurzer Spitzen-Kuppler", ["akku300", "adapter", "mikroservo", "kuppler50"]),
    ("P2", "P1 + Federausstoß + 100-cm-Schirm", ["akku300", "adapter", "kuppler50", "feder", "schirm100"]),
    ("P3", "P2 + gedruckte Spitze", ["akku300", "adapter", "kuppler50", "feder", "schirm100", "spitze_druck"]),
]


def _props(ps):
    pr = properties(ps)
    return dict(mass_g=pr["mass_kg"] * 1000, cg_mm=pr["cg_mm"][2], arm_mm=pr["cg_mm"][2] - PIVOT_Z,
                Ixx=pr["inertia_kgm2"]["Ixx"], Izz=pr["inertia_kgm2"]["Izz"], pr=pr)


def lever_table(base):
    funcs = {k: f for k, _, f, _ in LEVERS}
    rows = [("base", "Stand 2d (Druckteile Leichtbau, GPS NEO-6M), Ausgangslage", _props(base), "")]
    for k, txt, f, note in LEVERS:
        rows.append((k, txt, _props(f(list(base))), note))
    for k, txt, keys in PACKAGES:
        ps = list(base)
        for kk in keys:
            ps = funcs[kk](ps)
        rows.append((k, txt, _props(ps), "+".join(keys)))
    return rows


def write_json(confs, path, levers=None):
    data = {
        "source": "cad/mass_stand2b.py aus cad/modular_params.py und export/modular/masses.json, Stabmodell wie mass_model.py",
        "date": "2026-10-22",
        "config": "Modulbauweise Kartonaut 1, Stand 2b (Rohr A 125 + B 176 + C 195, CO₂-Ausstoß, kein Rollmotor)",
        "axes": "z Längsachse (+z zur Spitze), Ursprung Rohrunterkante = Düsenebene; x zum Servo des Innenrahmens",
        "pivot_from_nozzle_m": PIVOT_Z / 1000,
        "length_mm": M.NOSE_TIP_Z,
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
    if levers:
        data["levers"] = {k: {"label": txt, "mass_kg": round(r["mass_g"] / 1000, 4), "cg_from_nozzle_m": round(r["cg_mm"] / 1000, 4),
                              "cg_lateral_m": [round(r["pr"]["cg_mm"][0] / 1000, 5), round(r["pr"]["cg_mm"][1] / 1000, 5)],
                              "inertia_kgm2": {kk: round(vv, 6) for kk, vv in r["pr"]["inertia_kgm2"].items()},
                              "lever_arm_m": round(r["arm_mm"] / 1000, 4)} for k, txt, r, _ in levers}
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


GROUPS = [("motor", "Motor"), ("propellant", "Treibstoff"), ("tvc", "Kardan, Servos, Adapter"), ("airframe", "Rohre und Kuppler"),
          ("printed", "neue Druckteile"), ("fc", "Flugcomputer, Akkus, Antennen, Schalterbrett"), ("ejection", "CO₂-Ausstoß"),
          ("recovery", "Fallschirm"), ("nose", "Spitze"), ("misc", "Kleinteile")]


def write_md(confs, base, path, levers=None):
    m = sum(p.m for p in base)
    v = confs["liftoff"]
    twr = 12.0 / (m / 1000 * 9.81)
    L = []
    L.append("# Massenbudget Kartonaut 1, Modulbauweise Stand 2b mit Druckteilen Stand 2c\n")
    L.append("Erzeugt von `cad/mass_stand2b.py` am 22.10.2026 aus `modular_params.py` und `export/modular/masses.json`. "
             "Nicht von Hand ändern, Skript laufen lassen. Methode wie `mass_properties.md` (Stabmodell, Steiner), "
             "Koordinaten z ab der Rohrunterkante von Rohr A (Motor bündig, also Düsenebene).\n")
    L.append(f"Kardanpunkt der gebauten Druckdatei: **{PIVOT_Z:.1f} mm** (Grundfläche {M.GIMBAL_BASE_Z:.0f} + Servomitte {P.PIVOT_H:.1f}). "
             f"Gesamtlänge mit Spitze {M.NOSE_TIP_Z:.0f} mm.\n")
    L.append("## Ergebnis\n")
    L.append("| Zustand | Masse | Schwerpunkt ab Düse | Hebelarm Kardan–Schwerpunkt | Ixx = Iyy | Izz (Roll) |")
    L.append("|---|---|---|---|---|---|")
    for k, c in confs.items():
        I = c["inertia_kgm2"]
        L.append(f"| {c['label']} | **{c['mass_kg'] * 1000:.0f} g** | {c['cg_mm'][2]:.0f} mm | {c['lever_arm_m'] * 1000:.0f} mm "
                 f"| {I['Ixx']:.4f} kg·m² | {I['Izz']:.5f} kg·m² |")
    L.append("")
    L.append(f"Schub-Gewichts-Verhältnis mit 12 N mittlerem Schub des TSP E12: **{twr:.2f}** (Spitzenschub 28,3 N: {28.3 / (m / 1000 * 9.81):.1f}). "
             f"Ziel unter 750 g: **{'erreicht' if m < 750 else 'verfehlt'}**, Reserve {750 - m:.0f} g. "
             f"Seitlicher Schwerpunktversatz beim Start x = {v['cg_mm'][0]:.1f} mm, y = {v['cg_mm'][1]:.1f} mm.\n")
    L.append("## Nach Baugruppen\n")
    L.append("| Baugruppe | Masse | Anteil |")
    L.append("|---|---|---|")
    for key, label in GROUPS:
        gm = sum(p.m for p in base if p.group == key)
        L.append(f"| {label} | {gm:.0f} g | {100 * gm / m:.0f} % |")
    L.append(f"| **Start gesamt** | **{m:.0f} g** | |")
    L.append("")
    L.append("## Was sich gegenüber den Vorgängern geändert hat\n")
    L.append("| Modell | Start | Hebelarm | Bemerkung |")
    L.append("|---|---|---|---|")
    L.append("| `voll` (21.10.), 1000 mm Rohr, Beine, Ring-Stack | 981 g | 372 mm | Simulation: 20 m Gipfel, Schub-Gewicht 1,1 |")
    L.append("| `erstflug` (22.10.), 700 mm Rohr, Kolben, Schlüsselschalter | 761 g | 242 mm | Ziel 750 g um 11 g verfehlt |")
    L.append("| Stand 2b, Schätzung in `modular.py` | 689 g | – | Differenz zu 761 g aus Listen MASS_REMOVED / MASS_ADDED_HW |")
    L.append(f"| Stand 2b, Stabmodell (22.10. nachts) | {MASS_2B:.0f} g | 186 mm | mit LoRa-Wendel, CO₂-Servo, Schalterbrett-Bauteilen, Ringschraube, Hebeln; Druckteile 98 g (75-%-Regel) |")
    L.append(f"| **Stand 2d, dieses Modell** | **{m:.0f} g** | {v['lever_arm_m'] * 1000:.0f} mm | Druckteile Leichtbau, {sum(p.m for p in base if p.group == 'printed'):.0f} g nach dem Slicer-Modell ({m - MASS_2B:+.0f} g) |")
    L.append("")
    L.append("Die großen Hebel gegenüber 761 g: keine Gewindestangen (−30 g), Rohr 496 statt 700 mm (−49 g), kein Kolben (−31 g), "
             "kein Schlüsselschalter mit Kragen (−28 g), halbe Kuppler (−34 g); dagegen CO₂-Modul mit Kapsel und Servo (+44 g) und "
             "der Schlitten mit Spant als ein großes Druckteil (+74 g gegen Endringe und Träger 40 g).\n")
    L.append("Der Hebelarm Kardan–Schwerpunkt ist kurz: die schwere Spitze (83 g) und der Schirm sitzen zwar oben, aber Motor, Kardan "
             "und Rohr A liegen dicht am Kardanpunkt. Für die Firmware (`MOMENT_ARM_M`, `MASS_KG`) gelten nach dem Wiegen die gemessenen Werte.\n")
    if levers:
        L.append("## Druckteile Stand 2c: was sich geändert hat\n")
        L.append("| Teil | Stand 2b | Stand 2c | Änderung |")
        L.append("|---|---|---|---|")
        L.append("| Schlitten mit Spant | 77,9 cm³, 71 g | 53,0 cm³, 64 g | Spantplatte 3,5 statt 5 mm (außen 5-mm-Rand), Zapfen 2 statt 4,1/3,1 mm, U-Profil statt Klotz zwischen Träger und Zapfen (11,5 cm³), Fenster im Boden unter den Akkus, Augen weiter innen (≥ 2,9 mm hinter der Mutter) |")
        L.append("| Untere Scheibe | 8,7 cm³, 10 g | 5,8 cm³, 7 g | 2 statt 3 mm |")
        L.append("| Schalterbrett | 2,1 cm³, 3 g | unverändert | |")
        L.append("| Schraubring J1 | 14,6 cm³, 12 g | 4,5 cm³, 6 g | Wand 2 statt 6 mm, 10 statt 12 mm hoch, vier Augen mit Muttern |")
        L.append("| **Summe** | **96 g** | **80 g** | Massen nach dem Slicer-Modell (Oberfläche × 1 mm voll, Rest 25 %); nach der alten 75-%-Regel 98 → 62 g |")
        L.append("")
        L.append("Das Volumen sinkt um 36 %, die Druckmasse nur um 17 %: dünne Wände druckt der Slicer mit drei Perimetern voll, dicke "
                 "Wände waren innen schon zu 75 % hohl. Mehr spart nur Material, das ganz wegfällt. Weitere Fenster lohnen kaum "
                 "(der Schlitten besteht jetzt fast nur aus Hülle, Masse ∝ Oberfläche); zwei statt drei Perimeter ändern an 2-mm-Wänden nichts. "
                 "Festigkeit: Spantplatte bei 2,6 bar (Spitze klemmt, Obergrenze) 21 bis 34 MPa, PETG 45 bis 50 MPa; bei < 0,1 bar "
                 "(Spitze geht ab) unter 2 MPa. Der Träger hängt mit Boden und Wänden an der Platte und mit dem Boden als Sehne an der Zapfenwand.\n")
        L.append("## Gewichtshebel über die ganze Rakete\n")
        L.append("Jeder Hebel einzeln gegen die Ausgangslage, dann drei Pakete. Masse, Schwerpunkt, Hebelarm und Trägheit aus dem "
                 "Stabmodell; Schub-Gewicht mit 12 N. Regelgüte und Gipfel der Pakete: `simulation/README.md` (Nachtrag 23.10.).\n")
        L.append("| Hebel | Start | Δ | Schwerpunkt | Hebelarm | Ixx | Schub/Gewicht | Bewertung |")
        L.append("|---|---|---|---|---|---|---|---|")
        b = levers[0][2]
        for k, txt, r, note in levers:
            d = r["mass_g"] - b["mass_g"]
            L.append(f"| {('**' + k + '** ') if k.startswith('P') else ''}{txt} | {r['mass_g']:.0f} g | {d:+.0f} g | {r['cg_mm']:.0f} mm | "
                     f"{r['arm_mm']:.0f} mm | {r['Ixx']:.4f} | {12.0 / (r['mass_g'] / 1000 * 9.81):.2f} | {note} |")
        L.append("")
        L.append("Was nicht in der Tabelle steht, weil es fest oder schon minimal ist: Motor 64 g, Platine mit Teensy 45 g (Schätzung), "
                 "Rohre A/B 72 g (gebaut), Kardan mit Servos 73 g (gebaut, wiegen), GPS 6 g und LoRa 5 g (für die Suche in "
                 "abgelegenem Gelände nötig), 1S 14 g.\n")
    L.append("## Teileliste (Startzustand)\n")
    L.append("| Teil | Masse | z Schwerpunkt | Quelle / Annahme |")
    L.append("|---|---|---|---|")
    for p in base:
        L.append(f"| {p.name} | {p.m:.1f} g | {p.cg[2]:.0f} mm | {p.src} |")
    L.append(f"| **Summe** | **{m:.0f} g** | | |")
    L.append("")
    L.append("## Nachzumessen\n")
    L.append("- Jedes Druckteil nach dem Druck wiegen (hier Slicer-Modell: Oberfläche × 1 mm voll, Rest 25 % Gyroid; die Slicer-Vorschau nennt die Masse genauer).")
    L.append("- Spitze mit Holzplatte, beide halben Kuppler, Rohre A/B/C, Kardan mit Servos und Gestänge auf die Waage.")
    L.append("- CO₂-Modul mit gefüllter Kapsel und Servo; 1S-Akku; LoRa-Wendel mit Pigtail.")
    L.append("- Nach dem Zusammenbau: Schwerpunkt auswiegen, Quer-Trägheitsmoment per Bifilarpendel; `Config.h` und die Simulation (`--vehicle stand2b`) damit korrigieren.")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    confs, base = configurations()
    levers = lever_table(base)
    write_md(confs, base, HERE / "mass_stand2b.md", levers)
    write_json(confs, HERE / "mass_stand2b.json", levers)
    for k, txt, r, _ in levers:
        print(f"  {k:12s} {r['mass_g']:5.0f} g  CG {r['cg_mm']:4.0f} mm  Arm {r['arm_mm']:4.0f} mm  Ixx {r['Ixx']:.4f}")
    v = confs["liftoff"]
    print(f"Start {v['mass_kg'] * 1000:.0f} g, Schwerpunkt {v['cg_mm'][2]:.0f} mm, Hebelarm {v['lever_arm_m'] * 1000:.0f} mm, "
          f"Ixx {v['inertia_kgm2']['Ixx']:.4f}, Izz {v['inertia_kgm2']['Izz']:.5f} kg·m²; Länge {M.NOSE_TIP_Z:.0f} mm")
