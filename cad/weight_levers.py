"""Gewicht sparen beim Erstflug: jeder Hebel einzeln und in Paketen, mit Folgen für Schwerpunkt und Flug.

    python cad/weight_levers.py            Tabelle aus dem Massenmodell (schnell)
    python cad/weight_levers.py --sil      zusätzlich je Zeile ein SIL-Flug (Gipfel, Kippwinkel), ca. 6 s je Zeile
    python cad/weight_levers.py --md       Tabelle als Markdown nach cad/weight_levers.md

Ausgangspunkt ist die Erstflug-Konfiguration aus mass_model.py (Rohr 700 mm, 761 g). Ein Hebel ändert
entweder Parameter aus params.py (Längen, Massen, die die Geometrie bestimmen) oder die Masse einzelner
Teile der Teileliste (Trägheit skaliert mit, Lage bleibt). Massen mit [Schätzung] sind Annahmen, keine
Wägung; sie zeigen die Größenordnung. Die Waage ersetzt sie.

Für den SIL-Flug rechnet die Firmware jeweils mit der neuen Masse und dem neuen Hebelarm (so, als wäre
Config.h nachgezogen); alles andere wie simulation/scripts/run_sil.py.
"""
import argparse
import contextlib
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mass_model as M  # noqa: E402
import params as P      # noqa: E402

FUEL_G = 28.0
STEEL, ALU = 7.85, 2.70


@contextlib.contextmanager
def override(**kw):
    """params.py-Konstanten vorübergehend ändern (layout() liest sie zur Laufzeit)."""
    old = {k: getattr(P, k) for k in kw}
    try:
        for k, v in kw.items():
            setattr(P, k, v)
        yield
    finally:
        for k, v in old.items():
            setattr(P, k, v)


def set_mass(ps, prefix, new_m):
    """Masse eines Teils (erstes mit diesem Namensanfang) setzen; Trägheit skaliert mit."""
    for p in ps:
        if p.name.startswith(prefix):
            f = new_m / p.m
            p.m = new_m
            p.I = tuple(v * f for v in p.I)
            return p
    raise KeyError(prefix)


def part_mass(ps, prefix):
    return next(p.m for p in ps if p.name.startswith(prefix))


def shortest_tube(min_mm):
    """Kürzestes zulässiges Rohr, auf 5 mm aufgerundet. Neben dem Stapelmaß (TUBE_MIN) muss der Stoßkuppler am
    Rohrstoß (z = 520) unterhalb des Spitzenspants enden, sonst stößt die Schulter der Spitze auf ihn."""
    joint = P.TUBE_BOTTOM_Z + P.TUBE_L
    lo = joint + P.CHUTE_COUPLER_L / 2 + P.NOSE_BULKHEAD_BELOW_BASE + 1.0 - P.TUBE_BOTTOM_Z
    t = max(min_mm, lo)
    return float(5 * int(-(-t // 5)))


# ----------------------------------------------------------------------------- Hebel
# Jeder Hebel: (Kurzname, Beschreibung, params-Overrides, Funktion auf die Teileliste, Rohr: None = 700 / "min" = kürzestes)
def _rods_alu(ps):
    set_mass(ps, "8 Gewindestangen", part_mass(ps, "8 Gewindestangen") * ALU / STEEL)


def _arm_plug(ps):
    set_mass(ps, "Schlüsselschalter-Kragen", 10.0)


def _bat_300(ps):
    set_mass(ps, "Akku 2S", 20.0)


def _prints_light(ps):
    for name in ("Adapter 29", "Motorrohr", "Innenrahmen", "Außenrahmen", "Endring unten", "Endplatte oben", "Träger (gedruckt)",
                 "Kolbenplatte"):
        set_mass(ps, name, part_mass(ps, name) * 0.8)


def _chute_100(ps):
    # Kappe und Leinen skalieren mit der Fläche (0,64), die Schockschnur (15 g [Schätzung]) nicht
    set_mass(ps, "Fallschirm", (P.CHUTE_M - 15.0) * 0.64 + 15.0)


def _nose_light(ps):
    set_mass(ps, "Spitze Kegel", 45.0)


LEVERS = [
    ("rohr675", "Rohr 675 statt 700 mm (kürzestes mit 125-cm-Schirm)", {}, None, "min"),
    ("kuppler50", "Stoßkuppler 50 statt 80 mm", {"CHUTE_COUPLER_L": 50.0, "CHUTE_COUPLER_M": P.COUPLER_M * 50 / P.COUPLER_L}, None, None),
    ("stangen_alu", "8 Gewindestangen M2 aus Aluminium statt Stahl", {}, _rods_alu, None),
    ("druck_leicht", "Druckteile 20 % leichter (Wände/Füllung) [Schätzung]", {}, _prints_light, None),
    ("akku_300", "2S-Akku 300 statt 450 mAh, 20 statt 30 g [Schätzung]", {}, _bat_300, None),
    ("arm_stecker", "Arming-Stecker statt Schlüsselschalter, 10 statt 28 g [Schätzung]", {}, _arm_plug, None),
    ("schirm100", "Fallschirm Ø 100 statt 125 cm, gepackt 150 statt 230 mm [Schätzung], Rohr kürzer", {"CHUTE_L": 150.0}, _chute_100, "min"),
    ("spitze_druck", "Spitze gedruckt, dünnwandig, Kegel 45 statt 80 g [Schätzung]", {}, _nose_light, None),
]

PACKAGES = [
    ("A: Konstruktion", "Rohr, Stoßkuppler, Alu-Stangen, leichtere Druckteile; kein Zukauf außer Stangen",
     ["rohr675", "kuppler50", "stangen_alu", "druck_leicht"]),
    ("B: A + Zukauf", "A + 300-mAh-Akku + Arming-Stecker + 100-cm-Schirm",
     ["kuppler50", "stangen_alu", "druck_leicht", "akku_300", "arm_stecker", "schirm100"]),
    ("C: B + Spitze", "B + gedruckte Spitze", ["kuppler50", "stangen_alu", "druck_leicht", "akku_300", "arm_stecker", "schirm100",
                                               "spitze_druck"]),
]


def evaluate(keys):
    """Teileliste mit den gewählten Hebeln; Rückgabe (Kennwerte Start, Kennwerte Brennschluss, Rohrlänge)."""
    lev = {k: (o, f, t) for k, _, o, f, t in LEVERS}
    ov = {}
    tube_mode = None
    for k in keys:
        o, _, t = lev[k]
        ov.update(o)
        tube_mode = t or tube_mode
    with override(**ov):
        L = P.layout("erstflug", 2 * P.TUBE_L)          # nur für TUBE_MIN; 1000 mm ist immer zulässig
        tube = 700.0 if tube_mode is None else shortest_tube(L["TUBE_MIN"])
        ps = copy.deepcopy(M.parts(config="erstflug", tube_total=tube))
    for k in keys:
        f = lev[k][1]
        if f:
            f(ps)
    lift = M.properties(ps)
    burn = M.properties([p for p in ps if p.group != "propellant"])
    for pr in (lift, burn):
        pr["lever_arm_m"] = (pr["cg_mm"][2] - P.PIVOT_Z) / 1000
    return lift, burn, tube


def sil_flight(lift):
    """Ein SIL-Flug mit den Kennwerten (wie run_sil.py, Firmware-Masse und -Hebelarm angepasst)."""
    sim = HERE.parent / "simulation"
    sys.path.insert(0, str(sim))
    from dataclasses import replace
    import numpy as np
    from tvcsim.params import MotorParams, NoiseParams, ServoParams, SimParams, VehicleParams
    from tvcsim.sil import SilParams, trace_arrays
    from tvcsim.sim import simulate
    I = lift["inertia_kgm2"]
    veh = VehicleParams(Ix=I["Izz"], Iy=I["Ixx"], Iz=I["Iyy"], l=lift["lever_arm_m"], l_meas=lift["lever_arm_m"],
                        m_dry=lift["mass_kg"] - FUEL_G / 1000, static_error_y=1.0, static_error_z=0.6)
    sp = SilParams.from_config_h(mass_kg=lift["mass_kg"], moment_arm_m=lift["lever_arm_m"])
    res = simulate(SimParams(vehicle=veh, motor=MotorParams(fuel_model="impulse", second_motor=False),
                             servo=ServoParams(sat_deg=sp.values["tvc_max_deg"]), noise=NoiseParams(accel_model="specific_force"),
                             controller="sil", sil=sp, t_end=30.0, seed=0))
    burn = res.T > 0
    tr = trace_arrays(res.extra["trace"])
    return float(res.r[:, 0].max()), float(res.tilt_deg[burn].max()), float(tr["sat"][:len(res.t)][burn].mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sil", action="store_true")
    ap.add_argument("--md", action="store_true")
    args = ap.parse_args()

    base_l, base_b, _ = evaluate([])
    rows = [("Ausgangslage", "Erstflug, Rohr 700 mm", [])]
    rows += [(k, desc, [k]) for k, desc, *_ in LEVERS]
    rows += [(name, desc, keys) for name, desc, keys in PACKAGES]

    hdr = ["Hebel", "Rohr", "Start", "Δ", "Schwerpunkt", "Hebelarm", "Ixx", "Schub/Gewicht"]
    if args.sil:
        hdr += ["Gipfel (SIL)", "Kipp max Boost", "Sättigung"]
    out = []
    for name, desc, keys in rows:
        lift, burn, tube = evaluate(keys)
        m = lift["mass_kg"] * 1000
        line = [f"{name}: {desc}" if keys else f"{name} ({desc})", f"{tube:.0f} mm", f"{m:.0f} g",
                f"{m - base_l['mass_kg'] * 1000:+.0f} g", f"{lift['cg_mm'][2]:.0f} mm", f"{lift['lever_arm_m'] * 1000:.0f} mm",
                f"{lift['inertia_kgm2']['Ixx']:.4f}", f"{10.9 / (lift['mass_kg'] * 9.81):.2f}"]
        if args.sil:
            apo, tilt, sat = sil_flight(lift)
            line += [f"{apo:.0f} m", f"{tilt:.1f}°", f"{100 * sat:.0f} %"]
        out.append(line)
        print(" | ".join(line), flush=True)

    if args.md:
        md = ["# Gewicht sparen beim Erstflug (aus `cad/weight_levers.py`)", "",
              "Ausgangslage: Erstflug-Konfiguration aus `mass_model.py`. Δ gegen die Ausgangslage. Schub/Gewicht mit 10,9 N "
              "mittlerem Schub des TSP E12. Werte mit [Schätzung] sind Annahmen, keine Wägung."
              + (" SIL: ein Flug je Zeile, Firmware mit angepasster Masse und angepasstem Hebelarm, statischer Kardanfehler 1°/0,6°."
                 if args.sil else ""), "",
              "| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
        md += ["| " + " | ".join(r) + " |" for r in out]
        (HERE / "weight_levers.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print(f"-> {HERE / 'weight_levers.md'}")


if __name__ == "__main__":
    main()
