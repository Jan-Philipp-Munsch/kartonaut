"""Regelgüte der Gewichtspakete aus cad/mass_stand2b.json (Abschnitt "levers") mit dem Firmware-Regler.

    python scripts/check_stand2b_levers.py                  # base, P1, P2, P3 mit einem Raster Kp/Kd, 3 Seeds
    python scripts/check_stand2b_levers.py --configs base P2 --kp 2 5 --kd 0.5 1 --seeds 5

Frage: Eine leichtere Rakete hat einen kürzeren Hebelarm und ein kleineres Quer-Trägheitsmoment. Dasselbe
Stellmoment dreht sie schneller, die Reglergewinne aus Config.h (Kp 5, Kd 1, gefunden für 0,7 bis 1,0 kg und
I = 0,045 bis 0,11 kg m²) wirken also stärker. Bleibt die Brennphase geregelt, und wie oft steht der Kardan am
Anschlag? Die Firmware rechnet hier mit der wahren Masse und dem wahren Hebelarm (so wird Config.h nach dem
Wiegen gesetzt), Servo-Umrechnung 6 Servo-Grad je Kardan-Grad (±3,75°), ein Motor, Boden, Rauschen, statischer
Fehler 1°/0,6°, Beschleunigung als spezifische Kraft.
"""
import argparse
import csv
import json
from dataclasses import replace

import numpy as np

import _path  # noqa: F401
from tvcsim.params import (FUEL_PER_MOTOR_KG, STAND2B_MASS_FILE, FirmwareParams, MotorParams, NoiseParams, OUT_DIR,
                           ServoParams, SimParams, VehicleParams)
from tvcsim.sim import simulate

BURN_END = 3.55


def vehicle(cfg):
    I = cfg["inertia_kgm2"]
    lat = cfg.get("cg_lateral_m", [0.0, 0.0])
    return VehicleParams(Ix=I["Izz"], Iy=I["Ixx"], Iz=I["Iyy"], l=cfg["lever_arm_m"], l_meas=cfg["lever_arm_m"],
                         m_dry=cfg["mass_kg"] - FUEL_PER_MOTOR_KG, mis_y=float(lat[0]), mis_z=float(lat[1]),
                         static_error_y=1.0, static_error_z=0.6)


def run(cfg, kp, kd, seed, servo_gain=6.0):
    veh = vehicle(cfg)
    fw = replace(FirmwareParams(), PY_KP=kp, PY_KI=0.0, PY_KD=kd, MASS_KG=cfg["mass_kg"], MOMENT_ARM_M=cfg["lever_arm_m"],
                 SERVO_YAW_GAIN=-servo_gain, SERVO_PITCH_GAIN=servo_gain)
    p = SimParams(vehicle=veh, firmware=fw, motor=MotorParams(second_motor=False, fuel_model="impulse"),
                  servo=ServoParams(servo_deg_per_tvc_deg=servo_gain), noise=NoiseParams(enabled=True, accel_model="specific_force"),
                  controller="firmware", t_end=12.0, seed=seed, ground=True)
    res = simulate(p)
    burn = (res.t > 0.05) & (res.t <= BURN_END)
    lim = 22.5 / servo_gain - 1e-3
    sat = np.mean((np.abs(res.th_y_com[burn]) >= lim) | (np.abs(res.th_z_com[burn]) >= lim))
    k_bo = int(np.searchsorted(res.t, BURN_END))
    return dict(apogee=res.max_height, tilt_burn=float(res.tilt_deg[burn].max()), tilt_bo=float(res.tilt_deg[min(k_bo, len(res.t) - 1)]),
                lateral_bo=float(np.hypot(res.r[min(k_bo, len(res.t) - 1), 1], res.r[min(k_bo, len(res.t) - 1), 2])), sat=float(sat))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--configs", nargs="+", default=["base", "P1", "P2", "P3"])
    ap.add_argument("--kp", type=float, nargs="+", default=[1.0, 2.0, 3.5, 5.0])
    ap.add_argument("--kd", type=float, nargs="+", default=[0.25, 0.5, 1.0])
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    levers = json.loads(STAND2B_MASS_FILE.read_text(encoding="utf-8"))["levers"]
    OUT_DIR.mkdir(exist_ok=True)
    rows = []
    print(f"{'Konfig':6s} {'Masse':>6s} {'Arm':>5s} {'Kp':>4s} {'Kd':>5s} {'Gipfel':>7s} {'Kipp Brenn':>10s} {'Kipp BS':>8s} {'seitl BS':>8s} {'Anschlag':>8s}")
    for c in args.configs:
        cfg = levers[c]
        for kp in args.kp:
            for kd in args.kd:
                rs = [run(cfg, kp, kd, s) for s in range(args.seeds)]
                agg = {k: float(np.mean([r[k] for r in rs])) for k in rs[0]}
                agg["tilt_burn_max"] = float(max(r["tilt_burn"] for r in rs))
                rows.append(dict(config=c, mass_g=cfg["mass_kg"] * 1000, arm_mm=cfg["lever_arm_m"] * 1000, kp=kp, kd=kd, **agg))
                print(f"{c:6s} {cfg['mass_kg'] * 1000:5.0f}g {cfg['lever_arm_m'] * 1000:4.0f}mm {kp:4.1f} {kd:5.2f} {agg['apogee']:6.1f}m "
                      f"{agg['tilt_burn_max']:9.1f}° {agg['tilt_bo']:7.1f}° {agg['lateral_bo']:7.2f}m {100 * agg['sat']:7.0f}%", flush=True)
    path = OUT_DIR / "check_stand2b_levers.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
