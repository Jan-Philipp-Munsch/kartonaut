"""Servo-Uebertragungsfunktion aus den Sprungantworten fitten (Ersatz fuer tf5.mat).

Eingang: ``data/servo_step_response.csv`` (t_ms, servo_soll_deg, kardan_ist_deg; Soll 95 = Mitte).
Ausgang: ``out/servo_fit.png`` und ``out/servo_fit.json``; die Werte gehoeren in
``tvcsim/params.py`` (``ServoParams``).
"""
import argparse
import json

import numpy as np

import _path  # noqa: F401
from tvcsim.actuator import fit_servo_model, simulate_servo_response
from tvcsim.params import DATA_DIR, OUT_DIR
from tvcsim.plots import plot_servo_fit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--center", type=float, default=95.0, help="Servo-Soll der Mittelstellung (Grad)")
    ap.add_argument("--t-max", type=float, default=None, help="nur bis zu dieser Zeit (s) fitten")
    args = ap.parse_args()

    arr = np.loadtxt(DATA_DIR / "servo_step_response.csv", delimiter=",", skiprows=1)
    t = arr[:, 0] / 1000.0
    u = arr[:, 1] - args.center
    y = arr[:, 2]
    sel = slice(None) if args.t_max is None else t <= args.t_max
    fit = fit_servo_model(t[sel], u[sel], y[sel])
    y_fit = simulate_servo_response(t, u, fit["K"], fit["wn"], fit["zeta"], fit["tau"])

    # Statische Gains aus den sauberen Spruengen der ersten 2,1 s
    print("Sprungantworten (Soll -> Kardan-Endwert):")
    for t0, t1, du in ((0.802, 1.2, 35), (1.602, 1.7, -15), (2.236, 2.282, 34), (2.55, 2.596, -35)):
        yy = y[(t > t1 - 0.02) & (t <= t1)].mean()
        print(f"  Soll {du:+d} Grad -> Kardan {yy:+.2f} Grad  ({yy / du:.4f} Kardan-Grad je Servo-Grad, 1/{du / yy:.1f})")
    print(f"Fit PT2+Totzeit: K={fit['K']:.4f} (1/{1 / fit['K']:.2f}), wn={fit['wn']:.2f} rad/s "
          f"({fit['wn'] / 2 / np.pi:.2f} Hz), zeta={fit['zeta']:.3f}, tau={fit['tau'] * 1000:.1f} ms, "
          f"RMS={fit['rms_deg']:.3f} Grad")
    print(f"  Zum Vergleich: servo_delay_n = 0,08 s in TVC6DOF.m; Simulink-Gain 6 * K = {6 * fit['K']:.3f}, "
          f"23 * K = {23 * fit['K']:.3f}")

    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / "servo_fit.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in fit.items() if k != "y_fit"}, f, indent=2)
    path = plot_servo_fit(t, u, y, y_fit, fit, OUT_DIR / "servo_fit.png")
    print(f"geschrieben: {path}, {OUT_DIR / 'servo_fit.json'}")


if __name__ == "__main__":
    main()
