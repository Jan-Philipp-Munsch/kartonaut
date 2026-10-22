"""Landestudie mit Schubdrossel (Scout-F-Pads): Masse × Drosselspanne, Monte-Carlo (Jan, 23.10.2026).

    python scripts/throttle_study.py                    # Massen 0,5..0,9 kg, f_min 0,3/0,5/0,7, 40 Läufe
    python scripts/throttle_study.py --runs 100 --sixdof 0.7

1D (senkrecht, Cd·A 0,003 m², Pads als PT2 wie der Kardan-Servo mit 30 ms Totzeit), Aufstieg mit
derselben E12. Streuung: Schub ±10 %, Zündverzug 50–200 ms, Masse ±20 g, Höhe ±0,3 m, Sinkrate
±0,3 m/s. Erfolg = härtestes Aufsetzen ≤ 2 m/s (Beine). Ausgabe: Tabelle, ``out/throttle_study.png``,
``out/throttle_study.csv``; mit ``--sixdof`` ein 6DOF-Plot je genannter Masse (f_min 0,5).
"""
import argparse
import csv

import numpy as np

import _path  # noqa: F401
from landing_study import ascent_apogee, FUEL
from tvcsim.params import OUT_DIR, ThrottleParams
from tvcsim.throttle import simulate_landing_1d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--masses", type=float, nargs="+", default=[0.5, 0.6, 0.7, 0.8, 0.9])
    ap.add_argument("--fmin", type=float, nargs="+", default=[0.3, 0.5, 0.7])
    ap.add_argument("--runs", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sixdof", type=float, nargs="*", default=None, help="6DOF-Läufe für diese Massen (f_min 0,5)")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    OUT_DIR.mkdir(exist_ok=True)

    rows = []
    mc = {}
    print(f"{'Masse':>6} {'f_min':>5} {'Gipfel':>7} {'Zuendung h/v':>14} {'nominal':>8} {'MC Median':>9} {'MC 90%':>7} {'<=2 m/s':>8} {'Huepfer':>7}")
    for m in args.masses:
        apogee = ascent_apogee(m - FUEL)
        for fmin in args.fmin:
            tp = ThrottleParams(enabled=True, f_min=fmin)
            nom = simulate_landing_1d(apogee, m, tp)
            Js, hops = [], 0
            for _ in range(args.runs):
                scale = rng.uniform(0.9, 1.1); mass = m + rng.uniform(-0.02, 0.02); delay = rng.uniform(0.05, 0.2)
                ap_mc = ascent_apogee(mass - FUEL, scale)
                res = simulate_landing_1d(ap_mc, m, tp, truth_mass=mass, truth_scale=scale, truth_delay=delay,
                                          rng=rng, alt_sigma=0.3, vz_sigma=0.3)
                Js.append(-res["v_land"])
                hops += len(res["contacts"]) > 1
            Js = np.array(Js)
            mc[(m, fmin)] = Js
            rows.append([m, fmin, apogee, nom["h_ign"], nom["v_ign"], -nom["v_land"], np.median(Js),
                         np.percentile(Js, 90), np.mean(Js <= 2.0), hops / args.runs])
            print(f"{m:6.2f} {fmin:5.2f} {apogee:6.1f} m {nom['h_ign']:6.1f}/{nom['v_ign']:6.1f} {-nom['v_land']:8.1f} "
                  f"{np.median(Js):9.1f} {np.percentile(Js, 90):7.1f} {100 * np.mean(Js <= 2.0):7.0f} % {100 * hops / args.runs:6.0f} %")

    with open(OUT_DIR / "throttle_study.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["m_kg", "f_min", "apogee_m", "h_ign_m", "v_ign_ms", "nominal_ms", "mc_median_ms", "mc_p90_ms",
                    "share_le_2ms", "share_hops"])
        w.writerows(rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    fig.suptitle("Landebrennen mit Schubdrossel (zweite E12, Pads nach Scout F): Aufsetzen nach Masse und Drosselspanne", fontsize=11)
    r = np.array(rows)
    for fmin in args.fmin:
        sel = r[:, 1] == fmin
        axs[0].plot(r[sel, 0], r[sel, 5], "o-", label=f"nominal, f_min = {fmin:.1f}")
        axs[0].plot(r[sel, 0], r[sel, 6], "s--", alpha=0.7, label=f"Monte-Carlo Median, f_min = {fmin:.1f}")
    axs[0].axhline(2, color="0.6", lw=0.8)
    axs[0].set_xlabel("Masse bei der Landung (kg)"); axs[0].set_ylabel("härtestes Aufsetzen (m/s)")
    axs[0].set_ylim(0, 12); axs[0].grid(alpha=0.3); axs[0].legend(fontsize=7)
    for fmin in args.fmin:
        sel = r[:, 1] == fmin
        axs[1].plot(r[sel, 0], 100 * r[sel, 8], "o-", label=f"≤ 2 m/s, f_min = {fmin:.1f}")
    axs[1].set_xlabel("Masse bei der Landung (kg)"); axs[1].set_ylabel("Anteil der Läufe (%)")
    axs[1].set_ylim(0, 105); axs[1].grid(alpha=0.3); axs[1].legend(fontsize=8)
    axs[1].set_title(f"Monte-Carlo, {args.runs} Läufe: Schub ±10 %, Zündverzug 50–200 ms, Masse ±20 g, Rauschen", fontsize=8)
    fig.savefig(OUT_DIR / "throttle_study.png", dpi=130)
    print(f"geschrieben: {OUT_DIR / 'throttle_study.png'}, {OUT_DIR / 'throttle_study.csv'}")

    if args.sixdof is not None:
        from tvcsim.params import MotorParams, NoiseParams, SimParams, VehicleParams
        from tvcsim.sim import simulate
        from tvcsim.plots import plot_landing
        for m in (args.sixdof or [0.7]):
            p = SimParams(vehicle=VehicleParams.light(m), controller="firmware",
                          motor=MotorParams(fuel_model="impulse", second_mode="landing"),
                          throttle=ThrottleParams(enabled=True, f_min=0.5),
                          noise=NoiseParams(accel_model="specific_force"), t_end=30.0, seed=args.seed)
            p.firmware.MASS_KG = m; p.firmware.MOMENT_ARM_M = 0.242
            res = simulate(p)
            e = res.extra
            print(f"6DOF {m:.2f} kg, f_min 0,5: Gipfel {res.max_height:.1f} m, Zündung {e['h_ignite2']:.1f} m / {e['v_ignite2']:.1f} m/s, "
                  f"Kontakte {[(round(t - e['t_ignite2'], 2), round(v, 1)) for t, v in e['contacts']]}, Kipp {e['tilt_land_deg']:.1f}°")
            plot_landing(res, OUT_DIR / f"throttle_6dof_{m:.2f}.png")


if __name__ == "__main__":
    main()
