"""Monte-Carlo wie TVC6DOF.m: 100 Laeufe a 7 s, 3D-Plot der Trajektorien in out/.

  python scripts/run_montecarlo.py                       # TVC6DOF.m-Nominalwerte und -Gewinne
  python scripts/run_montecarlo.py --vehicle preload --gains tuner
  python scripts/run_montecarlo.py --controller firmware --runs 30
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np

import _path  # noqa: F401
from run_nominal import add_common_args, build_params, describe
from tvcsim.montecarlo import run_montecarlo, summarize
from tvcsim.params import MonteCarloParams, OUT_DIR
from tvcsim.plots import plot_montecarlo_3d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap)
    ap.add_argument("--runs", type=int, default=100)
    ap.add_argument("--mc-t-end", type=float, default=7.0, help="Simulationsdauer je Lauf (TVC6DOF.m: 7 s)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--replot", default=None, metavar="NPZ",
                    help="nur neu plotten aus einer frueher geschriebenen out/montecarlo_*.npz")
    args = ap.parse_args()
    base = build_params(args)
    mc = MonteCarloParams(runs=args.runs, t_end=args.mc_t_end)
    if args.replot:
        d = np.load(args.replot)
        path = plot_montecarlo_3d(list(d["positions"]), OUT_DIR / (args.out or (Path(args.replot).stem + ".png")),
                                  title=f"{len(d['positions'])} Monte-Carlo-Trajektorien, {float(d['t_end']):g} s je Lauf",
                                  subtitle=str(d["subtitle"]))
        print(f"geschrieben: {path}")
        return
    print(describe(base))
    t0 = time.time()

    def progress(k, n, res):
        if k % 10 == 0 or k == n:
            print(f"  Lauf {k}/{n}: maxHeight {res.max_height:.1f} m, Kippwinkel Ende {res.tilt_deg[-1]:.1f} Grad "
                  f"({time.time() - t0:.0f} s)")

    results = run_montecarlo(base, mc, seed=args.seed, progress=progress)
    s = summarize(results)
    print("Zusammenfassung:", ", ".join(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}" for k, v in s.items()))
    tag = f"{base.controller}_{args.gains if base.controller == 'simulink' else 'fw'}_{args.vehicle}"
    OUT_DIR.mkdir(exist_ok=True)
    np.savez_compressed(OUT_DIR / f"montecarlo_{tag}.npz", positions=np.array([r.r for r in results]),
                        t=results[0].t, t_end=mc.t_end, subtitle=describe(base))
    path = plot_montecarlo_3d(results, OUT_DIR / (args.out or f"montecarlo_{tag}.png"),
                              title=f"{len(results)} Monte-Carlo-Trajektorien, {mc.t_end:g} s je Lauf",
                              subtitle=describe(base))
    with open(OUT_DIR / f"montecarlo_{tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run", "maxHeight_m", "tilt_end_deg", "lateral_end_m", "Ix", "m_dry", "l", "servo_delay",
                    "mis_y", "mis_z", "static_error_y", "static_error_z"])
        for i, r in enumerate(results):
            v = r.params.vehicle
            w.writerow([i, r.max_height, r.tilt_deg[-1], (r.r[-1, 1] ** 2 + r.r[-1, 2] ** 2) ** 0.5,
                        v.Ix, v.m_dry, v.l, v.servo_delay, v.mis_y, v.mis_z, v.static_error_y, v.static_error_z])
    print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
