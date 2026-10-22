"""Schubkurve und Prüfvektoren für das Landebrennen in die Firmware exportieren.

    python scripts/export_landing_firmware.py

* ``firmware/src/ThrustCurveE12.h``: die TSP-E12-Kurve (data/E12_thrustcurve.csv) als Tabelle
  für ``LandingBurn.cpp`` (gleiche Stützpunkte wie die Simulation).
* ``firmware/test/data/landing_cost_E12.csv``: Aufsetzkosten J(h, v) aus ``tvcsim.landing``
  für mehrere Massen; ``test_landing.cpp`` muss dieselben Werte liefern (gleicher Algorithmus,
  gleiche Schrittweite 5 ms).
* ``firmware/test/data/landing_profile_tvcsim.csv``: ein 6DOF-Flug mit Landebrennen (Masse 0,7 kg)
  für den Zustandsautomaten: Zeit, |a|, axiale Kraft, Höhe, vz, Barometerhöhe, Schub.
"""
import csv

import numpy as np

import _path  # noqa: F401
from tvcsim.landing import impact_cost, load_thrust_curve
from tvcsim.params import MotorParams, NoiseParams, REPO_DIR, SimParams, VehicleParams
from tvcsim.sim import simulate

FW = REPO_DIR / "firmware"


def export_curve() -> None:
    t, f = load_thrust_curve("E12")
    keep = t <= 4.0                                  # der (100 s, 0)-Punkt ist überflüssig
    t, f = t[keep], f[keep]
    if f[-1] != 0.0:
        t = np.append(t, t[-1] + 0.01); f = np.append(f, 0.0)
    lines = ["#pragma once",
             "// ThrustCurveE12.h – TSP E12 (thrustcurve.org, data/E12_thrustcurve.csv) für LandingBurn.cpp.",
             "// Erzeugt von simulation/scripts/export_landing_firmware.py, nicht von Hand ändern.",
             "#include <stddef.h>", "",
             "namespace thrustcurve {", f"constexpr size_t E12_N = {len(t)};",
             "constexpr float E12_T_S[E12_N] = {" + ", ".join(f"{x:.3f}f" for x in t) + "};",
             "constexpr float E12_F_N[E12_N] = {" + ", ".join(f"{x:.3f}f" for x in f) + "};",
             f"constexpr float E12_IMPULSE_NS = {np.trapezoid(f, t):.3f}f;",
             f"constexpr float E12_BURN_S = {t[np.nonzero(f)[0][-1] + 1]:.3f}f;",
             "}  // namespace thrustcurve", ""]
    (FW / "src" / "ThrustCurveE12.h").write_text("\n".join(lines), encoding="utf-8")
    print(f"ThrustCurveE12.h: {len(t)} Punkte")


def export_costs() -> None:
    t, f = load_thrust_curve("E12")
    rows = []
    for m in (0.6, 0.7, 0.8):
        for h in (2.0, 10.0, 25.0, 40.0, 60.0):
            for v in (-5.0, -15.0, -25.0, -35.0):
                J, _ = impact_cost(t, f, m, h, v, cd_a=0.003, rho=1.2, fuel_kg=0.028, dt=5e-3)
                rows.append([m, h, v, 0.003, f"{J:.4f}"])
    with open(FW / "test" / "data" / "landing_cost_E12.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["m_kg", "h_m", "v_ms", "cd_a", "J_ms"]); w.writerows(rows)
    print(f"landing_cost_E12.csv: {len(rows)} Zeilen")


def export_profile(m: float = 0.7) -> None:
    from scipy.spatial.transform import Rotation as R
    p = SimParams(vehicle=VehicleParams.light(m), controller="firmware",
                  motor=MotorParams(fuel_model="impulse", second_mode="landing", landing_alt_sigma=0, landing_vz_sigma=0),
                  noise=NoiseParams(accel_model="specific_force", enabled=False), t_end=30.0, seed=0)
    p.firmware.MASS_KG = m; p.firmware.MOMENT_ARM_M = 0.242
    res = simulate(p)
    g = 9.81
    f_in = res.rdd.copy(); f_in[:, 0] += g
    q = res.q
    rot = R.from_quat(np.column_stack([q[:, 1], q[:, 2], q[:, 3], q[:, 0]]))
    f_body = rot.inv().apply(f_in)
    rng = np.random.default_rng(0)
    rows = [[k * 0.01, g, g, 0.0, 0.0, float(rng.normal(0, 0.3)), 0.0] for k in range(200)]
    for k in range(len(res.t)):
        rows.append([2.0 + res.t[k], np.linalg.norm(f_body[k]), f_body[k, 0], res.r[k, 0], res.rd[k, 0],
                     res.r[k, 0] + rng.normal(0, 0.3), res.T[k]])
    t_end = 2.0 + res.t[-1]
    rows += [[t_end + k * 0.01, g, g, 0.0, 0.0, float(rng.normal(0, 0.3)), 0.0] for k in range(1, 501)]
    with open(FW / "test" / "data" / "landing_profile_tvcsim.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "a_norm_ms2", "a_axial_ms2", "alt_m", "vz_ms", "baro_alt_m", "thrust_N"])
        for r in rows:
            w.writerow([f"{r[0]:.3f}"] + [f"{v:.4f}" for v in r[1:]])
    e = res.extra
    print(f"landing_profile_tvcsim.csv: {len(rows)} Zeilen, Gipfel {res.max_height:.1f} m, Zündung bei "
          f"{e['h_ignite2']:.1f} m / {e['v_ignite2']:.1f} m/s (t = {e['t_ignite2'] + 2:.2f} s), Aufsetzen {e['v_land']:.1f} m/s")


if __name__ == "__main__":
    export_curve()
    export_costs()
    export_profile()
