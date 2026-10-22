"""Simulierten Flug als Sensordatei für die nativen Firmware-Tests exportieren.

Erzeugt, was die Flug-Firmware in jedem 10-ms-Takt sieht: spezifische Kraft und Drehrate im
**Firmware-Körpersystem** (x, y quer, z Rollachse), dazu wahre Höhe und Vertikalgeschwindigkeit
und eine verrauschte Barometerhöhe. Damit prüft ``firmware/test/test_flightcore`` den
Flugzustandsautomaten (Start, Brennschluss, Apogäum, Landung) und die Quaternion gegen die
Simulation.

  python scripts/export_flight_csv.py                       # Erstflug, E12, ein Motor -> ../firmware/test/data/flight_e12.csv
  python scripts/export_flight_csv.py --out /tmp/f.csv --vehicle cad --no-noise

Achsentausch Simulink -> Firmware: sim x (längs) -> fw z, sim y -> fw x, sim z -> fw y.
Auf der Rampe misst der Beschleunigungssensor die Stützkraft (+1 g entlang z), nicht die
negative Netto-Beschleunigung, die die Dynamik vor dem Abheben rechnet.
"""
import argparse
import csv
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

import _path  # noqa: F401
from run_nominal import VEHICLES, build_params, add_common_args
from tvcsim.sim import simulate

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "firmware" / "test" / "data" / "flight_e12.csv"


def sim_to_fw(v):
    """(x längs, y, z) -> (y, z, x): Firmware x = Yaw-Achse, y = Pitch-Achse, z = Rollachse."""
    v = np.asarray(v)
    return np.stack([v[..., 1], v[..., 2], v[..., 0]], axis=-1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--gyro-noise", type=float, default=0.1, help="Grad/s, Std je Achse")
    ap.add_argument("--accel-noise", type=float, default=0.05, help="m/s², Std je Achse")
    ap.add_argument("--baro-noise", type=float, default=0.3, help="m, Std der Barometerhöhe")
    ap.set_defaults(vehicle="erstflug", controller="firmware", single_motor=True, t_end=30.0)
    args = ap.parse_args()

    p = build_params(args)
    # Firmware-Konstanten auf den Erstflug (Config.h): Masse und Hebelarm
    p = replace(p, firmware=replace(p.firmware, MASS_KG=p.vehicle.m_dry + 0.028, MOMENT_ARM_M=p.vehicle.l))
    res = simulate(p)
    rng = np.random.default_rng(args.seed)
    g = p.vehicle.g

    # spezifische Kraft: inertial rdd + g x̂, auf der Rampe die Stützkraft g x̂
    lifted = res.r[:, 0] > 1e-6
    k_lift = int(np.argmax(lifted)) if lifted.any() else len(res.t)
    f_inertial = res.rdd + np.array([g, 0.0, 0.0])
    f_inertial[:k_lift] = np.array([g, 0.0, 0.0])
    # nach der Landung (Lauf endet dort) ergänzen wir 5 s Ruhe, damit LANDED erkannt wird
    rot = Rotation.from_quat(np.column_stack([res.q[:, 1], res.q[:, 2], res.q[:, 3], res.q[:, 0]]))
    f_body = rot.inv().apply(f_inertial)
    w_body = res.w_dps
    n_rest = int(round(5.0 / p.control.dt))
    t = np.concatenate([res.t, res.t[-1] + p.control.dt * np.arange(1, n_rest + 1)])
    f_body = np.vstack([f_body, np.repeat(rot[-1].inv().apply([[g, 0, 0]]), n_rest, axis=0)])
    w_body = np.vstack([w_body, np.zeros((n_rest, 3))])
    alt = np.concatenate([res.r[:, 0], np.zeros(n_rest)])
    vz = np.concatenate([res.rd[:, 0], np.zeros(n_rest)])
    tilt = np.concatenate([res.tilt_deg, np.full(n_rest, res.tilt_deg[-1])])

    noise = 0.0 if args.no_noise else 1.0
    f_fw = sim_to_fw(f_body) + noise * rng.normal(0, args.accel_noise, (len(t), 3))
    w_fw = sim_to_fw(w_body) + noise * rng.normal(0, args.gyro_noise, (len(t), 3))
    baro = alt + noise * rng.normal(0, args.baro_noise, len(t))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# tvcsim export: vehicle={args.vehicle} controller={args.controller} motor={p.motor.curve} "
                 f"single_motor={args.single_motor} seed={args.seed} liftoff_s={res.t[k_lift] if k_lift < len(res.t) else -1:.2f} "
                 f"apogee_s={res.t[int(np.argmax(res.r[:, 0]))]:.2f} max_alt_m={res.max_height:.1f} "
                 f"land_s={res.extra.get('t_land')}\n")
        w = csv.writer(fh)
        w.writerow(["t_s", "fx_ms2", "fy_ms2", "fz_ms2", "wx_dps", "wy_dps", "wz_dps", "alt_m", "vz_ms", "baro_alt_m", "tilt_deg"])
        for i in range(len(t)):
            w.writerow([f"{t[i]:.3f}", *(f"{v:.4f}" for v in f_fw[i]), *(f"{v:.4f}" for v in w_fw[i]),
                        f"{alt[i]:.3f}", f"{vz[i]:.3f}", f"{baro[i]:.3f}", f"{tilt[i]:.3f}"])
    print(f"{args.out}: {len(t)} Zeilen, Start {res.t[k_lift]:.2f} s, Gipfel {res.max_height:.1f} m bei "
          f"{res.t[int(np.argmax(res.r[:, 0]))]:.2f} s, Landung {res.extra.get('t_land')} s")


if __name__ == "__main__":
    main()
