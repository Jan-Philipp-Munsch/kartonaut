"""IMU- und Barometer-Rauschen aus dem CSV-Strom von examples/calib_imu ('s') auswerten.

  python scripts/analyze_imu_noise.py ../logs/imu_still_2026-10-30.csv

Erwartet die Spalten t_ms, ax_ms2, ay_ms2, az_ms2, gx_dps, gy_dps, gz_dps, p_pa, alt_m
(100 Hz, Gerät in Ruhe, mindestens 2 Minuten für eine brauchbare Allan-Kurve). Ausgabe:

* Mittel und Standardabweichung je Kanal,
* Allan-Abweichung des Gyros über Mittelungszeiten 0,01 .. 100 s mit dem Minimum
  (Bias-Instabilität) und der Winkel-Zufallswanderung (Wert bei 1 s),
* Vorschläge für ``Config.h`` (``KALMAN_MEAS_STD_M``, ``GYRO_BIAS_DPS_*``) und für
  ``tvcsim.NoiseParams`` (``w_sigma``, ``rdd_sigma``) in Firmware-Einheiten.

Mit ``--plot`` entsteht ``out/imu_noise_allan.png``.
"""
import argparse
from pathlib import Path

import numpy as np

import _path  # noqa: F401
from tvcsim.params import OUT_DIR


def allan_deviation(x: np.ndarray, fs: float, taus: np.ndarray) -> np.ndarray:
    """Überlappende Allan-Abweichung einer Rate x (Abtastrate fs) für Mittelungszeiten taus."""
    theta = np.cumsum(x) / fs
    out = np.full(len(taus), np.nan)
    n = len(theta)
    for i, tau in enumerate(taus):
        m = int(round(tau * fs))
        if m < 1 or 2 * m >= n:
            continue
        d = theta[2 * m:] - 2 * theta[m:-m] + theta[:-2 * m]
        out[i] = np.sqrt(0.5 * np.mean(d ** 2)) / tau
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    d = np.genfromtxt(args.csv, delimiter=",", names=True)
    t = d["t_ms"] * 1e-3
    fs = 1.0 / np.median(np.diff(t))
    print(f"{len(t)} Zeilen, {t[-1] - t[0]:.1f} s, {fs:.1f} Hz")

    gyro = np.column_stack([d["gx_dps"], d["gy_dps"], d["gz_dps"]])
    acc = np.column_stack([d["ax_ms2"], d["ay_ms2"], d["az_ms2"]])
    print("\nGyro  Mittel [°/s]   ", np.round(gyro.mean(0), 4), "  Std ", np.round(gyro.std(0), 4))
    print("Accel Mittel [m/s²]  ", np.round(acc.mean(0), 4), "  Std ", np.round(acc.std(0), 4), f"  |a| = {np.linalg.norm(acc.mean(0)):.4f}")
    alt = d["alt_m"]
    print(f"Baro  Höhe Std {alt.std():.3f} m, Drift {alt[-1] - alt[0]:+.2f} m")

    taus = np.logspace(-2, np.log10((t[-1] - t[0]) / 5), 40)
    adev = np.column_stack([allan_deviation(gyro[:, k] - gyro[:, k].mean(), fs, taus) for k in range(3)])
    ok = ~np.isnan(adev[:, 0])
    i1 = int(np.argmin(np.abs(taus - 1.0)))
    print("\nAllan-Abweichung Gyro [°/s]:")
    for i in np.where(ok)[0][::4]:
        print(f"  tau {taus[i]:7.2f} s   {adev[i, 0]:.4f}  {adev[i, 1]:.4f}  {adev[i, 2]:.4f}")
    imin = np.nanargmin(adev, axis=0)
    print("Bias-Instabilität (Minimum) [°/s]:", np.round(adev[imin, range(3)], 5), " bei tau", np.round(taus[imin], 1), "s")
    print("Winkel-Zufallswanderung (tau = 1 s) [°/√s]:", np.round(adev[i1], 5))

    print("\nVorschläge:")
    print(f"constexpr float GYRO_BIAS_DPS_X  = {gyro[:, 0].mean():+.3f}f;")
    print(f"constexpr float GYRO_BIAS_DPS_Y  = {gyro[:, 1].mean():+.3f}f;")
    print(f"constexpr float GYRO_BIAS_DPS_Z  = {gyro[:, 2].mean():+.3f}f;")
    print(f"constexpr float KALMAN_MEAS_STD_M    = {2 * alt.std():.2f}f;")
    print(f"tvcsim NoiseParams(w_sigma={gyro.std(0).max():.3f}, rdd_sigma={acc.std(0).max():.3f})")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        OUT_DIR.mkdir(exist_ok=True)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for k, lab in enumerate("xyz"):
            ax.loglog(taus[ok], adev[ok, k], label=f"Gyro {lab}")
        ax.set_xlabel("Mittelungszeit tau [s]"); ax.set_ylabel("Allan-Abweichung [°/s]")
        ax.grid(True, which="both", alpha=0.3); ax.legend()
        ax.set_title(args.csv.name)
        fig.tight_layout()
        fig.savefig(OUT_DIR / "imu_noise_allan.png", dpi=130)
        print(f"-> {OUT_DIR / 'imu_noise_allan.png'}")


if __name__ == "__main__":
    main()
