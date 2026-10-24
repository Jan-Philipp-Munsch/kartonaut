"""Nominalvergleich der Regler: Firmware (Config.h), Firmware mit korrigierten Parametern,
modellbasierter PD, LQR mit Servozustand, LQI.

Alle modellbasierten Regler sind mit denselben Bryson-Gewichten entworfen (``LQRParams``), das
Entwurfsmodell ist das CAD-Fahrzeug (I quer 0,11 kg m2, l 0,372 m) mit dem SG90-Servofit.
Beschleunigungssensor als spezifische Kraft, ein Motor, Rauschen an, statischer Servofehler
1 / 0,6 Grad, bis zur Landung. Ergebnis als Tabelle und out/compare_controllers_<vehicle>.png.
"""
import argparse
from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import _path  # noqa: F401
from tvcsim.controller import model_pd_params  # noqa: E402
from tvcsim.params import (FirmwareParams, LQRParams, MotorParams, NoiseParams, OUT_DIR, SimParams,  # noqa: E402
                           VehicleParams)
from tvcsim.sim import simulate  # noqa: E402

BURNOUT = 3.55   # s, Brennschluss E12


def controller_cases(base: SimParams):
    cad = VehicleParams.cad()
    fw_fixed = FirmwareParams(MASS_KG=0.98, MOMENT_ARM_M=cad.l, SERVO_YAW_GAIN=-6.0, SERVO_PITCH_GAIN=6.0)
    yield "Firmware (Config.h: m 0,70, l 0,30, Gain 23)", replace(base, controller="firmware")
    yield "Firmware, m 0,98, l 0,372, Gain 6", replace(base, controller="firmware", firmware=fw_fixed)
    yield "PD modellbasiert (gleiche Kosten, kein Servomodell)", replace(base, controller="pd_model")
    yield "LQR mit Servozustand", replace(base, controller="lqr")
    yield "LQI (LQR + Integral)", replace(base, controller="lqi")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vehicle", choices=["nominal", "preload", "cad"], default="cad")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--static-error-y", type=float, default=1.0)
    ap.add_argument("--static-error-z", type=float, default=0.6)
    ap.add_argument("--no-noise", action="store_true")
    ap.add_argument("--t-end", type=float, default=7.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    veh = {"nominal": VehicleParams.nominal, "preload": VehicleParams.preload, "cad": VehicleParams.cad}[args.vehicle]()
    veh = replace(veh, static_error_y=args.static_error_y, static_error_z=args.static_error_z)
    cad = VehicleParams.cad()
    lqr = LQRParams(I_ctrl=cad.Iy, servo_wn=36.7, servo_zeta=0.598, servo_tau=0.030)
    base = SimParams(vehicle=veh, noise=NoiseParams(enabled=not args.no_noise, accel_model="specific_force"),
                     motor=MotorParams(second_motor=False), t_end=args.t_end, seed=args.seed, lqr=lqr)

    pd = model_pd_params(lqr, veh, base.servo, base.control.dt)
    print(f"Fahrzeug {args.vehicle}: m_dry={veh.m_dry:.3f} kg, I quer={veh.Iy:.4g} kg m2, l={veh.l:.4g} m; "
          f"Entwurf: I={lqr.I_ctrl:.3g}, T_design={lqr.T_design:g} N, theta_max={lqr.theta_max_deg:g} Grad, "
          f"omega_max={lqr.omega_max_dps:g} Grad/s, TVC_max={lqr.tvc_max_deg:g} Grad")
    print(f"PD modellbasiert: kp={pd.kp:.2f} kd={pd.kd:.4f} (Firmware-Skala: Kp={pd.kp:.2f}, Kd={100 * pd.kd:.2f})")
    print(f"{'Regler':52s} {'Kipp max':>9s} {'Kipp BS':>8s} {'|th| max':>9s} {'Saett.':>7s} {'Hoehe':>6s} {'Landung':>8s}")
    print(f"{'':52s} {'Brennph.':>9s} {'':>8s} {'Brennph.':>9s} {'Anteil':>7s} {'m':>6s} {'s':>8s}")
    fig, ax = plt.subplots(3, 1, figsize=(10.7, 11), sharex=True, layout="constrained")
    for name, p in controller_cases(base):
        res = simulate(p)
        burn = res.t <= BURNOUT
        ib = int(np.argmin(np.abs(res.t - BURNOUT)))
        thmax = float(max(np.abs(res.th_y[burn]).max(), np.abs(res.th_z[burn]).max()))
        sat = float(np.mean((np.abs(res.th_y_com[burn]) >= p.servo.sat_deg - 1e-6)
                            | (np.abs(res.th_z_com[burn]) >= p.servo.sat_deg - 1e-6)))
        print(f"{name:52s} {res.tilt_deg[burn].max():7.2f}° {res.tilt_deg[ib]:6.2f}° {thmax:7.2f}° {sat:7.2f} "
              f"{res.max_height:6.1f} {(res.extra.get('t_land') or float('nan')):8.2f}")
        ax[0].plot(res.t, res.r[:, 0], label=name)
        ax[1].plot(res.t, res.tilt_deg, label=name)
        ax[2].plot(res.t, res.th_y, label=name)
    ax[0].set_ylabel("Hoehe (m)"); ax[1].set_ylabel("Kippwinkel (Grad)"); ax[2].set_ylabel("th_y Kardan (Grad)")
    ax[2].set_xlabel("Zeit (s)")
    ax[0].set_ylim(bottom=0); ax[1].set_ylim(0, 12)
    for a in ax:
        a.grid(alpha=0.3)
        a.axvline(BURNOUT, color="0.6", lw=0.8, ls="--")
    ax[0].legend(fontsize=8)
    fig.suptitle("Reglervergleich: Firmware-PID, modellbasierter PD, LQR, LQI", fontsize=13)
    ax[0].set_title(f"Fahrzeug {args.vehicle} (m_dry {veh.m_dry:.3g} kg, I quer {veh.Iy:.3g} kg m2, l {veh.l:.3g} m), "
                    f"statischer Servofehler {veh.static_error_y:g}/{veh.static_error_z:g} Grad, "
                    f"{'ohne' if args.no_noise else 'mit'} Rauschen, spezifische Kraft, ein Motor; "
                    f"gestrichelt: Brennschluss", fontsize=8.5, color="0.35")
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / (args.out or f"compare_controllers_{args.vehicle}.png")
    fig.savefig(path, dpi=150, facecolor="white")
    print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
