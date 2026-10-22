"""Fallschirm des Erstflugs: Sinkgeschwindigkeit, Drift, Öffnungsstoß, Schnurlast.

Rein aerodynamisch und mechanisch (Schirm, Schnüre); zur Ausstoßladung rechnet dieses Skript nichts.

  python scripts/recovery.py                         # Tabellen mit den Vorgaben (Erstflug, Klima-Schirm 125 cm)
  python scripts/recovery.py --from-sil              # Auslösehöhe und -geschwindigkeit aus einem SIL-Flug
  python scripts/recovery.py --drop-test 0.75 6.0 1.9   # Cd aus einem Fallversuch: Masse kg, Strecke m, Zeit s
  python scripts/recovery.py --diameter 0.9 --plot   # anderen Schirm prüfen, Plot nach out/recovery.png

Formeln:
  Sinkgeschwindigkeit   v = sqrt(2 m g / (rho Cd A)),  A = pi D² / 4 (Nennfläche, flach ausgelegt)
  Aufprall              E = m v² / 2, entspricht einem Fall aus h = v² / (2 g)
  Drift                 Wind × Sinkzeit (Höhe bei Öffnung / v) + seitlicher Abstand bei der Auslösung
  Öffnungsstoß          F = Ck · rho/2 · v_open² · Cd · A, Ck = Öffnungsstoßfaktor (flacher Rundkappenschirm
                        bei kleiner Last ca. 1,5–2; hier 1,8 als vorsichtiger Wert)
  Schnur                Bruchlast ≥ Sicherheitsfaktor × F (Vorgabe 4, weil Ck und Knoten unsicher sind)

Cd des Klima-Schirms ist nicht bekannt: flache Rund- und Sechseckschirme aus Folie liegen bei 0,6 bis 0,9
bezogen auf die Nennfläche. Ein Fallversuch (--drop-test) ersetzt die Annahme.
"""
import argparse
import math

import numpy as np

import _path  # noqa: F401
from tvcsim.params import OUT_DIR

G = 9.81


def descent_speed(m, cd, d, rho):
    return math.sqrt(2.0 * m * G / (rho * cd * math.pi * d * d / 4.0))


def opening_force(v, cd, d, rho, ck):
    return ck * 0.5 * rho * v * v * cd * math.pi * d * d / 4.0


def cd_from_drop(m, dist, t, d, rho):
    v = dist / t
    return 2.0 * m * G / (rho * math.pi * d * d / 4.0 * v * v), v


def sil_deploy():
    """Auslösung aus einem SIL-Flug mit den Vorgaben von run_sil.py."""
    from dataclasses import replace
    from tvcsim.params import MotorParams, NoiseParams, ServoParams, SimParams, VehicleParams
    from tvcsim.sil import SilParams, trace_arrays
    from tvcsim.sim import simulate
    p = SilParams.from_config_h()
    sp = SimParams(vehicle=replace(VehicleParams.erstflug(), static_error_y=1.0, static_error_z=0.6),
                   motor=MotorParams(fuel_model="impulse", second_motor=False),
                   servo=ServoParams(sat_deg=p.values["tvc_max_deg"]), noise=NoiseParams(accel_model="specific_force"),
                   controller="sil", sil=p, t_end=30.0, seed=0)
    res = simulate(sp)
    tr = trace_arrays(res.extra["trace"])
    k = int(np.argmax(tr["fire"][:len(res.t)] > 0))
    return float(res.r[k, 0]), float(np.linalg.norm(res.rd[k])), float(np.hypot(res.r[k, 1], res.r[k, 2])), float(res.r[:, 0].max())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mass", type=float, default=0.733, help="kg am Schirm (Erstflug nach Brennschluss, cad/mass_properties.json)")
    ap.add_argument("--diameter", type=float, default=1.25, help="m, Nenndurchmesser (Klima 8594: 125 cm)")
    ap.add_argument("--cd", type=float, default=0.75, help="Nennwert für die Tabellen; die Spanne 0,6–0,9 steht immer daneben")
    ap.add_argument("--rho", type=float, default=1.20, help="kg/m³ (ca. 20 °C, 200 m ü. NN)")
    ap.add_argument("--ck", type=float, default=1.8, help="Öffnungsstoßfaktor")
    ap.add_argument("--safety", type=float, default=4.0, help="Sicherheitsfaktor für Schnüre und Ösen")
    ap.add_argument("--deploy-alt", type=float, default=54.5, help="m, Höhe bei der Auslösung")
    ap.add_argument("--deploy-speed", type=float, default=8.0, help="m/s, Geschwindigkeit bei der Auslösung")
    ap.add_argument("--deploy-lateral", type=float, default=4.4, help="m, seitlich vom Pad bei der Auslösung")
    ap.add_argument("--from-sil", action="store_true", help="Auslösung aus einem SIL-Flug übernehmen")
    ap.add_argument("--drop-test", nargs=3, type=float, metavar=("MASSE_KG", "STRECKE_M", "ZEIT_S"))
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    if args.drop_test:
        m, dist, t = args.drop_test
        cd, v = cd_from_drop(m, dist, t, args.diameter, args.rho)
        print(f"Fallversuch: {m:.3f} kg, {dist:.2f} m in {t:.2f} s -> v = {v:.2f} m/s, Cd = {cd:.2f} (Nennfläche Ø {args.diameter} m)")
        print("  Der Schirm muss vor der Messstrecke offen sein; 3 Würfe, Mittel nehmen, windstill.")
        args.cd = cd

    if args.from_sil:
        args.deploy_alt, args.deploy_speed, args.deploy_lateral, apogee = sil_deploy()
        print(f"SIL-Flug: Gipfel {apogee:.1f} m, Auslösung bei {args.deploy_alt:.1f} m mit {args.deploy_speed:.1f} m/s, "
              f"{args.deploy_lateral:.1f} m seitlich")

    A = math.pi * args.diameter ** 2 / 4.0
    print(f"\nSchirm Ø {args.diameter:.2f} m (Nennfläche {A:.3f} m²), Masse {args.mass * 1000:.0f} g, rho {args.rho} kg/m³")

    print("\n1. Sinkgeschwindigkeit und Aufprall")
    print(f"   {'Cd':>5s} {'v [m/s]':>8s} {'E [J]':>6s} {'wie Fall aus':>13s}")
    for cd in (0.6, 0.75, 0.9):
        v = descent_speed(args.mass, cd, args.diameter, args.rho)
        print(f"   {cd:5.2f} {v:8.2f} {0.5 * args.mass * v * v:6.1f} {v * v / (2 * G):10.2f} m")
    v0 = descent_speed(args.mass, args.cd, args.diameter, args.rho)
    print(f"   Ziel für Modellraketen: 3,5–5 m/s. Mit Cd {args.cd:.2f}: {v0:.2f} m/s.")
    for d in (0.9, 1.0, 1.1):
        print(f"   zum Vergleich Ø {d:.1f} m: {descent_speed(args.mass, args.cd, d, args.rho):.2f} m/s")

    print("\n2. Drift (ohne Thermik, Wind über die ganze Höhe gleich)")
    t_desc = args.deploy_alt / v0
    print(f"   Sinkzeit von {args.deploy_alt:.0f} m: {t_desc:.0f} s")
    for w in (2, 4, 6, 8):
        print(f"   Wind {w} m/s: {w * t_desc + args.deploy_lateral:5.0f} m vom Pad")

    print("\n3. Öffnungsstoß und Schnurlast")
    print(f"   {'v_open [m/s]':>12s} {'F (Cd 0,6)':>11s} {'F (Cd 0,75)':>12s} {'F (Cd 0,9)':>11s} {'Bruchlast ≥':>12s}")
    speeds = sorted({4.0, 6.0, 8.0, 10.0, 15.0, 20.0, round(args.deploy_speed, 1)})
    for v in speeds:
        f = [opening_force(v, cd, args.diameter, args.rho, args.ck) for cd in (0.6, 0.75, 0.9)]
        mark = "  <- Auslösung" if abs(v - round(args.deploy_speed, 1)) < 1e-9 else ""
        print(f"   {v:12.1f} {f[0]:9.0f} N {f[1]:10.0f} N {f[2]:9.0f} N {args.safety * f[2]:10.0f} N{mark}")
    f_dep = opening_force(args.deploy_speed, 0.9, args.diameter, args.rho, args.ck)
    print(f"   Bei der Auslösung ({args.deploy_speed:.1f} m/s, Cd 0,9, Ck {args.ck}): {f_dep:.0f} N "
          f"= {f_dep / (args.mass * G):.1f} g auf die Rakete. Schnüre, Knoten, Öse der Spitze und Öse am Spant "
          f"brauchen ≥ {args.safety * f_dep:.0f} N Bruchlast.")
    print("   Elastikschnur dämpft die Spitze; die Kevlarschnur parallel dazu nimmt die volle Last.")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        OUT_DIR.mkdir(exist_ok=True)
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
        ds = np.linspace(0.6, 1.4, 50)
        for cd in (0.6, 0.75, 0.9):
            ax[0].plot(ds, [descent_speed(args.mass, cd, d, args.rho) for d in ds], label=f"Cd {cd}")
        ax[0].axhspan(3.5, 5.0, color="g", alpha=0.1, label="Ziel 3,5–5 m/s")
        ax[0].axvline(args.diameter, color="k", ls=":")
        ax[0].set_xlabel("Schirmdurchmesser [m]"); ax[0].set_ylabel("Sinkgeschwindigkeit [m/s]")
        ax[0].legend(); ax[0].grid(alpha=0.3)
        vs = np.linspace(0, 25, 100)
        for cd in (0.6, 0.75, 0.9):
            ax[1].plot(vs, [opening_force(v, cd, args.diameter, args.rho, args.ck) for v in vs], label=f"Cd {cd}")
        ax[1].axvline(args.deploy_speed, color="r", ls="--", label="Auslösung (SIL)")
        ax[1].set_xlabel("Geschwindigkeit beim Öffnen [m/s]"); ax[1].set_ylabel(f"Öffnungsstoß [N] (Ck {args.ck})")
        ax[1].legend(); ax[1].grid(alpha=0.3)
        fig.suptitle(f"Fallschirm Ø {args.diameter} m, {args.mass * 1000:.0f} g")
        fig.savefig(OUT_DIR / "recovery.png", dpi=120)
        print(f"-> {OUT_DIR / 'recovery.png'}")


if __name__ == "__main__":
    main()
