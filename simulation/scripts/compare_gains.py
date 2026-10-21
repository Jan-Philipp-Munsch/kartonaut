"""Firmware-Gewinne (Kp=5, Ki=0, Kd=1 auf rot/-100) gegen pid_tuner.m (kp=3,1 ki=5 kd=0,385).

Drei Sichten je Fahrzeugsatz:
 1. Simulink-Regler mit den Firmware-Gewinnen umgerechnet (kp=5, ki=0, kd=0,01)
 2. Simulink-Regler mit den Tuner-Gewinnen (kp=3,1, ki=5, kd=0,385)
 3. Firmware-Regler 1:1 (Masse 0,70 kg, Servo-Gain 23, Fenster, Rundung)
jeweils mit Rauschen und mit einem Stoerfall (statischer Fehler 1 / 0,6 Grad), 12 s.
Ergebnis als Tabelle und Plot out/compare_gains_<vehicle>.png.
"""
import argparse
from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import _path  # noqa: F401
from tvcsim.params import (ControlParams, FirmwareParams, NoiseParams, OUT_DIR, ServoParams, SimParams,  # noqa: E402
                           VehicleParams)
from tvcsim.sim import simulate  # noqa: E402


def cases(veh: VehicleParams, seed: int, accel: str):
    sim = SimParams(vehicle=veh, noise=NoiseParams(enabled=True, accel_model=accel), t_end=12.0, seed=seed)
    yield "Simulink, Firmware-Gewinne (kp5 ki0 kd0,01)", replace(sim, control=ControlParams(kp=5, ki=0, kd=0.01))
    yield "Simulink, Tuner (kp3,1 ki5 kd0,385)", replace(sim, control=ControlParams.tuner())
    yield "Simulink, TVC6DOF.m (kp1 ki1 kd0,1)", replace(sim, control=ControlParams())
    yield "Firmware 1:1 (m 0,70, Gain 23)", replace(sim, controller="firmware")
    yield "Firmware, Servo-Gain 6", replace(sim, controller="firmware",
                                           firmware=FirmwareParams(SERVO_YAW_GAIN=-6, SERVO_PITCH_GAIN=6))
    yield "Firmware, Gain 6, Kd=38,5", replace(sim, controller="firmware",
                                              firmware=FirmwareParams(SERVO_YAW_GAIN=-6, SERVO_PITCH_GAIN=6, PY_KD=38.5))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vehicle", choices=["nominal", "preload"], default="nominal")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--static-error-y", type=float, default=1.0)
    ap.add_argument("--static-error-z", type=float, default=0.6)
    ap.add_argument("--accel", choices=["rdd", "specific_force"], default="rdd",
                    help="was der Beschleunigungssensor misst (rdd = wie Simulink)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    veh = VehicleParams.nominal() if args.vehicle == "nominal" else VehicleParams.preload()
    veh = replace(veh, static_error_y=args.static_error_y, static_error_z=args.static_error_z)

    fig, ax = plt.subplots(3, 1, figsize=(10.7, 11), sharex=True, layout="constrained")
    print(f"Fahrzeug {args.vehicle}: m_dry={veh.m_dry} kg, I={veh.Ix:.4f}, l={veh.l} m, "
          f"static_error y/z = {veh.static_error_y}/{veh.static_error_z} Grad, Rauschen an, "
          f"Beschleunigung = {args.accel}, 12 s")
    print("Brennphase 1 = 0 bis 3,55 s (Brennschluss), danach Freiflug ohne Stellmoeglichkeit.")
    print(f"{'Fall':40s} {'maxHeight':>9s} {'Kipp max':>9s} {'Kipp 3,5s':>9s} {'seitl 3,5s':>10s} "
          f"{'Kipp max':>9s} {'Kipp Ende':>9s} {'|th| max':>9s}")
    print(f"{'':40s} {'':>9s} {'Brenn 1':>9s} {'':>9s} {'':>10s} {'0-12 s':>9s} {'12 s':>9s} {'Brenn 1':>9s}")
    for name, p in cases(veh, args.seed, args.accel):
        res = simulate(p)
        burn = res.t <= 3.55
        ib = int(np.argmin(np.abs(res.t - 3.55)))
        lateral_b = float(np.hypot(res.r[ib, 1], res.r[ib, 2]))
        thmax = float(max(np.abs(res.th_y[burn]).max(), np.abs(res.th_z[burn]).max()))
        print(f"{name:40s} {res.max_height:7.1f} m {res.tilt_deg[burn].max():7.1f}° {res.tilt_deg[ib]:7.1f}° "
              f"{lateral_b:8.2f} m {res.tilt_deg.max():7.1f}° {res.tilt_deg[-1]:7.1f}° {thmax:7.2f}°")
        ax[0].plot(res.t, res.r[:, 0], label=name)
        ax[1].plot(res.t, res.tilt_deg, label=name)
        ax[2].plot(res.t, res.th_y, label=name)
    ax[0].set_ylabel("Hoehe (m)"); ax[1].set_ylabel("Kippwinkel (Grad)"); ax[2].set_ylabel("th_y Kardan (Grad)")
    ax[2].set_xlabel("Zeit (s)")
    ax[1].set_ylim(0, 90)
    for a in ax:
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=8)
    fig.suptitle("Reglervergleich: Firmware-Gewinne gegen pid_tuner.m", fontsize=13)
    ax[0].set_title(f"Fahrzeug {args.vehicle} (m_dry {veh.m_dry:g} kg, I {veh.Ix:.3g} kg m2, l {veh.l:g} m), "
                    f"statischer Fehler {veh.static_error_y:g}/{veh.static_error_z:g} Grad, Rauschen an, "
                    f"Beschleunigungssensor: {args.accel}", fontsize=8.5, color="0.35")
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / (args.out or f"compare_gains_{args.vehicle}_{args.accel}.png")
    fig.savefig(path, dpi=150, facecolor="white")
    print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
