"""Raster ueber kp, ki, kd mit maxHeight als Zielgroesse (Port von pid_tuner.m).

  python scripts/tune_pid.py                                  # kleines Raster um 3,1 / 5 / 0,385
  python scripts/tune_pid.py --kp 1 3.1 5 --ki 0 5 --kd 0.01 0.1 0.385 --vehicle preload
"""
import argparse

import numpy as np

import _path  # noqa: F401
from run_nominal import add_common_args, build_params, describe
from tvcsim.params import OUT_DIR
from tvcsim.tuning import tune_grid


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap)
    ap.add_argument("--kp-values", type=float, nargs="+", default=[2.0, 3.1, 5.0])
    ap.add_argument("--ki-values", type=float, nargs="+", default=[0.0, 5.0])
    ap.add_argument("--kd-values", type=float, nargs="+", default=[0.01, 0.1, 0.385])
    ap.add_argument("--out", default="tune_pid.csv")
    args = ap.parse_args()
    base = build_params(args)
    base = base.with_(controller="simulink")
    print(describe(base))
    rows = tune_grid(base, args.kp_values, args.ki_values, args.kd_values, seed=args.seed)
    OUT_DIR.mkdir(exist_ok=True)
    np.savetxt(OUT_DIR / args.out, rows, delimiter=",", header="kp,ki,kd,maxHeight_m,tilt_end_deg", comments="")
    best = rows[np.argmax(rows[:, 3])]
    print(f"bestes maxHeight: {best[3]:.3f} m bei kp={best[0]:g}, ki={best[1]:g}, kd={best[2]:g}")
    print(f"geschrieben: {OUT_DIR / args.out}")


if __name__ == "__main__":
    main()
