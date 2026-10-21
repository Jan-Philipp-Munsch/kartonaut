"""Nominallauf: Hoehe, Lage und Servowinkel ueber der Zeit als PNG in out/.

Beispiele:
  python scripts/run_nominal.py                         # Simulink-Regler, TVC6DOF.m-Gewinne, mit Rauschen
  python scripts/run_nominal.py --gains tuner           # kp=3,1 ki=5 kd=0,385
  python scripts/run_nominal.py --controller firmware   # Control.cpp-Regler (Kp=5 Ki=0 Kd=1)
  python scripts/run_nominal.py --vehicle preload --no-noise --static-error-y 1 --static-error-z 0.6
"""
import argparse
from dataclasses import replace

import numpy as np

import _path  # noqa: F401
from tvcsim.params import (ControlParams, FirmwareParams, MotorParams, NoiseParams, OUT_DIR, ServoParams,
                           SimParams, VehicleParams)
from tvcsim.plots import plot_nominal
from tvcsim.sim import simulate


def add_common_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--controller", choices=["simulink", "firmware"], default="simulink")
    ap.add_argument("--vehicle", choices=["nominal", "preload", "cad"], default="nominal",
                    help="nominal = TVC6DOF.m, preload = PreLoadFcn der .slx, cad = cad/mass_properties.json")
    ap.add_argument("--gains", choices=["nominal", "tuner", "preload"], default="nominal",
                    help="Simulink-Regler: nominal = kp1/ki1/kd0,1, tuner = 3,1/5/0,385, preload = 2/1/0,004")
    ap.add_argument("--kp", type=float); ap.add_argument("--ki", type=float); ap.add_argument("--kd", type=float)
    ap.add_argument("--fw-kp", type=float, default=None); ap.add_argument("--fw-ki", type=float, default=None)
    ap.add_argument("--fw-kd", type=float, default=None)
    ap.add_argument("--fw-mass", type=float, default=None, help="MASS_KG der Firmware (Config.h: 0,70)")
    ap.add_argument("--fw-servo-gain", type=float, default=None,
                    help="Betrag von SERVO_*_GAIN (Config.h: 23); Vorzeichen bleiben")
    ap.add_argument("--no-noise", action="store_true")
    ap.add_argument("--accel", choices=["rdd", "specific_force"], default="rdd")
    ap.add_argument("--fuel", choices=["signalbuilder", "impulse"], default="signalbuilder")
    ap.add_argument("--servo-gain", type=float, default=6.0, help="servo_deg_per_tvc_deg (Simulink-Gain 6)")
    ap.add_argument("--static-error-y", type=float, default=None)
    ap.add_argument("--static-error-z", type=float, default=None)
    ap.add_argument("--mis-y", type=float, default=None); ap.add_argument("--mis-z", type=float, default=None)
    ap.add_argument("--t-end", type=float, default=12.0)
    ap.add_argument("--no-ground", action="store_true", help="ohne Boden rechnen (wie Simulink)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--substeps", type=int, default=10)


VEHICLES = {"nominal": VehicleParams.nominal, "preload": VehicleParams.preload, "cad": VehicleParams.cad}


def build_params(args) -> SimParams:
    veh = VEHICLES[args.vehicle]()
    upd = {}
    for name in ("static_error_y", "static_error_z", "mis_y", "mis_z"):
        if getattr(args, name) is not None:
            upd[name] = getattr(args, name)
    veh = replace(veh, **upd)
    ctrl = {"nominal": ControlParams(), "tuner": ControlParams.tuner(), "preload": ControlParams.preload()}[args.gains]
    for name in ("kp", "ki", "kd"):
        if getattr(args, name) is not None:
            ctrl = replace(ctrl, **{name: getattr(args, name)})
    fw = FirmwareParams()
    if args.fw_kp is not None: fw = replace(fw, PY_KP=args.fw_kp)
    if args.fw_ki is not None: fw = replace(fw, PY_KI=args.fw_ki)
    if args.fw_kd is not None: fw = replace(fw, PY_KD=args.fw_kd)
    if args.fw_mass is not None: fw = replace(fw, MASS_KG=args.fw_mass)
    if args.fw_servo_gain is not None:
        fw = replace(fw, SERVO_YAW_GAIN=-abs(args.fw_servo_gain), SERVO_PITCH_GAIN=abs(args.fw_servo_gain))
    return SimParams(vehicle=veh, control=ctrl, firmware=fw,
                     motor=MotorParams(fuel_model=args.fuel),
                     servo=ServoParams(servo_deg_per_tvc_deg=args.servo_gain),
                     noise=NoiseParams(enabled=not args.no_noise, accel_model=args.accel),
                     controller=args.controller, t_end=args.t_end, seed=args.seed, substeps=args.substeps,
                     ground=not args.no_ground)


def describe(p: SimParams) -> str:
    if p.controller == "simulink":
        g = f"kp={p.control.kp:g} ki={p.control.ki:g} kd={p.control.kd:g}"
    else:
        g = f"Kp={p.firmware.PY_KP:g} Ki={p.firmware.PY_KI:g} Kd={p.firmware.PY_KD:g} (Skala {p.firmware.PY_ERROR_SCALE:g})"
    return (f"Regler {p.controller}, {g}; m_dry={p.vehicle.m_dry:g} kg, I={p.vehicle.Ix:.4g}, l={p.vehicle.l:g} m, "
            f"static_error y/z={p.vehicle.static_error_y:g}/{p.vehicle.static_error_z:g} Grad, "
            f"Rauschen {'an' if p.noise.enabled else 'aus'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common_args(ap)
    ap.add_argument("--out", default=None, help="Dateiname des PNG in out/")
    args = ap.parse_args()
    p = build_params(args)
    print(describe(p))
    res = simulate(p)
    name = args.out or f"nominal_{p.controller}_{args.gains if p.controller == 'simulink' else 'fw'}_{args.vehicle}.png"
    path = plot_nominal(res, OUT_DIR / name, title=f"Nominallauf, Regler {p.controller}", subtitle=describe(p))
    print(f"maxHeight = {res.max_height:.2f} m, Kippwinkel max {res.tilt_deg.max():.1f} Grad, "
          f"Ende {res.tilt_deg[-1]:.1f} Grad, seitlich {np.hypot(res.r[-1, 1], res.r[-1, 2]):.1f} m, "
          f"|th_com| max {max(np.abs(res.th_y_com).max(), np.abs(res.th_z_com).max()):.2f} Grad")
    print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
