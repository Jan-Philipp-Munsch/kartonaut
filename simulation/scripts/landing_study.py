"""Landestudie: Landebrennen mit dem zweiten TSP E12 (Jan, 23.10.2026).

    python scripts/landing_study.py                     # Massen 0,5..0,9 kg, Monte-Carlo, Plots
    python scripts/landing_study.py --masses 0.6 0.7 --runs 100 --sixdof

Fragen: Wie weich kann die Rakete mit der E12 landen, wenn sie mit derselben E12 gestartet ist
(Gipfel und Fallgeschwindigkeit haengen an der Masse)? Welcher Gipfel waere ideal? Wie empfindlich
ist das Ergebnis gegen Schubtoleranz, Zuendverzug, Masse und Sensorrauschen? Alles in 1D
(senkrecht, Luftwiderstand Cd·A = 0,003 m^2), dazu auf Wunsch je Masse ein 6DOF-Lauf mit Regler.

Ausgabe: Tabelle auf der Konsole, ``out/landing_study.png`` (J entlang des Falls, Zuendhoehen,
Monte-Carlo-Verteilungen), ``out/landing_study.csv``.
"""
import argparse
import csv

import numpy as np

import _path  # noqa: F401
from tvcsim.landing import G, LandingPlanner, impact_cost, load_thrust_curve, net_braking_dv
from tvcsim.params import OUT_DIR

CURVE = "E12"
FUEL = 0.028
CD_A = 0.003
RHO = 1.2


def ascent_apogee(m_dry: float, scale: float = 1.0, dt: float = 1e-3) -> float:
    """1D-Aufstieg mit Motor 1 (beide Motoren an Bord), Gipfelhoehe."""
    t_c, f_c = load_thrust_curve(CURVE)
    imp = np.concatenate([[0.0], np.cumsum(0.5 * (f_c[1:] + f_c[:-1]) * np.diff(t_c))]); tot = imp[-1]
    h = v = t = 0.0
    m0 = m_dry + 2 * FUEL
    while True:
        T = scale * np.interp(t, t_c, f_c, left=0, right=0)
        m = m0 - FUEL * np.interp(t, t_c, imp, left=0, right=tot) / tot
        D = 0.5 * RHO * CD_A * v * v * (1 if v < 0 else -1)
        a = (T + D) / m - G
        if h <= 0 and a < 0 and v <= 0:
            v = 0.0; t += dt; continue
        v += a * dt; h += v * dt; t += dt
        if v < 0 and h > 0:
            return h


def free_fall(apogee: float, m: float, dt: float = 0.01):
    """(h, v)-Folge des freien Falls aus dem Gipfel (mit Luftwiderstand)."""
    h, v = apogee, 0.0
    while h > 0:
        v += (-G + 0.5 * RHO * CD_A * v * v / m) * dt
        h += v * dt
        yield h, v


def land_from(apogee: float, m: float, planner_kw: dict, truth_kw: dict, rng=None, alt_sigma=0.0, vz_sigma=0.0):
    """Fall aus dem Gipfel, Planer zuendet, wahre Dynamik (truth_kw: scale, delay) entscheidet.
    Liefert (J_wahr, h_ign, v_ign)."""
    pl = LandingPlanner(CURVE, m, CD_A, RHO, FUEL, **planner_kw)
    t_c, f_c = pl.t_curve, pl.f_curve
    for h, v in free_fall(apogee, truth_kw.get("mass", m)):
        h_est = h + (rng.normal(0, alt_sigma) if rng is not None else 0.0)
        v_est = v + (rng.normal(0, vz_sigma) if rng is not None else 0.0)
        if pl.should_ignite(h_est, v_est):
            # wahrer Zuendverzug, dann wahres Brennen
            hd, vd = pl.predicted(h, v, truth_kw.get("delay", planner_kw.get("igniter_delay", 0.1)))
            J, _ = impact_cost(t_c, f_c, truth_kw.get("mass", m), hd, vd, CD_A, RHO, truth_kw.get("scale", 1.0), FUEL)
            return J, h, v
    return float("nan"), 0.0, 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--masses", type=float, nargs="+", default=[0.5, 0.6, 0.7, 0.75, 0.8, 0.9])
    ap.add_argument("--runs", type=int, default=60, help="Monte-Carlo-Laeufe je Masse")
    ap.add_argument("--sixdof", action="store_true", help="zusaetzlich je Masse ein 6DOF-Lauf (langsam)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    OUT_DIR.mkdir(exist_ok=True)

    rows = []
    curves = {}
    mc = {}
    print(f"{'Masse':>6} {'dv_brems':>8} {'Gipfel':>7} {'Zuendung h/v':>14} {'J nominal':>9} {'idealer Gipfel':>14} "
          f"{'MC Median':>9} {'MC 90%':>7} {'<=2 m/s':>7}")
    for m in args.masses:
        apogee = ascent_apogee(m - FUEL)
        base = dict(igniter_delay=0.10, dt_ctrl=0.01)
        J0, h0, v0 = land_from(apogee, m, base, {})
        # J entlang des Falls (Anschauung)
        pl = LandingPlanner(CURVE, m, CD_A, RHO, FUEL, **base)
        hv = [(h, v) for h, v in free_fall(apogee, m)][::5]
        curves[m] = [(h, v, pl.cost(*pl.predicted(h, v, 0.1))) for h, v in hv if v < -2]
        # idealer Gipfel fuer diese Masse
        best = min(((land_from(a, m, base, {})[0], a) for a in np.arange(10, 140, 4.0)), key=lambda x: x[0])
        # Monte-Carlo: Schub +-10 % (gleichverteilt), Zuendverzug 50..200 ms, Masse +-20 g, Rauschen
        Js = []
        for _ in range(args.runs):
            truth = dict(scale=rng.uniform(0.9, 1.1), delay=rng.uniform(0.05, 0.2), mass=m + rng.uniform(-0.02, 0.02))
            ap_mc = ascent_apogee(truth["mass"] - FUEL, truth["scale"])
            J, _, _ = land_from(ap_mc, m, base, truth, rng=rng, alt_sigma=0.3, vz_sigma=0.3)
            Js.append(J)
        Js = np.array(Js)
        mc[m] = Js
        rows.append([m, net_braking_dv(CURVE, m), apogee, h0, v0, J0, best[1], best[0], np.median(Js),
                     np.percentile(Js, 90), np.mean(Js <= 2.0)])
        print(f"{m:6.2f} {rows[-1][1]:7.1f}  {apogee:6.1f} m {h0:6.1f}/{v0:6.1f} {J0:8.1f}  {best[1]:6.0f} m -> {best[0]:4.1f}"
              f" {np.median(Js):8.1f} {np.percentile(Js, 90):7.1f} {100 * np.mean(Js <= 2.0):6.0f} %")

    with open(OUT_DIR / "landing_study.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["m_kg", "dv_brake_ms", "apogee_m", "h_ign_m", "v_ign_ms", "J_nominal_ms", "best_apogee_m",
                    "J_best_ms", "mc_median_ms", "mc_p90_ms", "mc_share_le_2ms"])
        w.writerows(rows)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(16, 5), layout="constrained")
    fig.suptitle("Landebrennen mit dem zweiten TSP E12: Aufsetzgeschwindigkeit nach Masse (1D, Cd·A = 0,003 m²)", fontsize=11)
    for m, c in curves.items():
        c = np.array(c)
        axs[0].plot(c[:, 0], c[:, 2], label=f"{m:.2f} kg")
    axs[0].set_xlabel("Zündhöhe im freien Fall (m)"); axs[0].set_ylabel("Aufsetzkosten J (m/s)")
    axs[0].set_ylim(0, 30); axs[0].invert_xaxis(); axs[0].grid(alpha=0.3); axs[0].legend(fontsize=8)
    axs[0].set_title("J entlang des Falls aus dem E12-Gipfel (Minimum = Zündung)", fontsize=9)
    r = np.array(rows)
    axs[1].plot(r[:, 0], r[:, 5], "o-", label="nominal, Fall aus dem E12-Gipfel")
    axs[1].plot(r[:, 0], r[:, 7], "s--", label="bester Gipfel für diese Masse")
    axs[1].plot(r[:, 0], r[:, 8], "^-", label="Monte-Carlo Median")
    axs[1].plot(r[:, 0], r[:, 9], "v:", label="Monte-Carlo 90 %")
    axs[1].axhline(2, color="0.6", lw=0.8); axs[1].text(r[0, 0], 2.2, "2 m/s: Beine", fontsize=8, color="0.4")
    axs[1].set_xlabel("Masse bei der Landung (kg)"); axs[1].set_ylabel("Aufsetzgeschwindigkeit (m/s)")
    axs[1].grid(alpha=0.3); axs[1].legend(fontsize=8); axs[1].set_title("Nominal und Streuung", fontsize=9)
    axs[2].boxplot([mc[m] for m in args.masses], tick_labels=[f"{m:.2f}" for m in args.masses])
    axs[2].axhline(2, color="0.6", lw=0.8)
    axs[2].set_xlabel("Masse (kg)"); axs[2].set_ylabel("Aufsetzgeschwindigkeit (m/s)")
    axs[2].set_title(f"Monte-Carlo ({args.runs} Läufe): Schub ±10 %, Zündverzug 50–200 ms, Masse ±20 g, Rauschen 0,3 m / 0,3 m/s", fontsize=8)
    axs[2].grid(alpha=0.3)
    fig.savefig(OUT_DIR / "landing_study.png", dpi=130)
    print(f"geschrieben: {OUT_DIR / 'landing_study.png'}, {OUT_DIR / 'landing_study.csv'}")

    if args.sixdof:
        from tvcsim.params import MotorParams, NoiseParams, SimParams, VehicleParams
        from tvcsim.sim import simulate
        from tvcsim.plots import plot_nominal
        for m in args.masses:
            p = SimParams(vehicle=VehicleParams.light(m), controller="firmware",
                          motor=MotorParams(fuel_model="impulse", second_mode="landing"),
                          noise=NoiseParams(accel_model="specific_force"), t_end=30.0, seed=args.seed)
            p.firmware.MASS_KG = m; p.firmware.MOMENT_ARM_M = 0.242
            res = simulate(p)
            e = res.extra
            print(f"6DOF {m:.2f} kg: Gipfel {res.max_height:.1f} m, Zündung {e['h_ignite2']:.1f} m / {e['v_ignite2']:.1f} m/s, "
                  f"Aufsetzen {e['v_land']:.1f} m/s, Kipp {e['tilt_land_deg']:.1f}°, Kontakte {len(e['contacts'])}")
            plot_nominal(res, OUT_DIR / f"landing_6dof_{m:.2f}.png", title=f"Landebrennen 6DOF, {m:.2f} kg",
                         subtitle=f"Zündung {e['h_ignite2']:.1f} m / {e['v_ignite2']:.1f} m/s, Aufsetzen {e['v_land']:.1f} m/s")


if __name__ == "__main__":
    main()
