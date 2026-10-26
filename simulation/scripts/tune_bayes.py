"""Reglergewinne (Kp, Ki, Kd des Firmware-Reglers) per Bayes-Optimierung statt Raster.

    python scripts/tune_bayes.py --config base                     # Ausgangslage 705 g aus cad/mass_stand2b.json
    python scripts/tune_bayes.py --config P2 --iters 40 --workers 6
    python scripts/tune_bayes.py --config base --no-ki             # nur Kp und Kd
    python scripts/tune_bayes.py --eval 2 1 0.45 --configs base P1 P2 P3   # einen festen Satz Kp Ki Kd prüfen

Jede Auswertung der Zielfunktion ist ein kleines Monte-Carlo: mehrere Flüge mit verschiedenen Rausch-Seeds und
Servo-Totzeiten (30 und 50 ms, weil die W5652H am gebauten Kardan noch nicht vermessen sind), parallel gerechnet.
Gesucht wird also ein robuster Satz, nicht das Optimum für genau einen simulierten Flug. Ziel (kleiner ist besser):

    J = mittlerer Kipp max in der Brennphase + 0,5 · schlechtester Kipp max + 20 · Anteil der Brennzeit am Anschlag
        + 0,5 · mittlerer seitlicher Versatz bei Brennschluss  (Grad, Grad, -, m)

Der Optimierer (``tvcsim/bayesopt.py``) ist ein Gauß-Prozess mit Expected Improvement; Kp und Kd laufen auf
logarithmischen Achsen. Ausgabe: Verlauf auf der Konsole, ``out/tune_bayes_<config>.csv`` mit allen Punkten.
Die Firmware rechnet wie in ``check_stand2b_levers.py`` mit wahrer Masse und wahrem Hebelarm, Servo-Umrechnung 6.
"""
import argparse
import csv
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

import _path  # noqa: F401
from tvcsim.bayesopt import BayesOpt
from tvcsim.params import (FUEL_PER_MOTOR_KG, STAND2B_MASS_FILE, FirmwareParams, MotorParams, NoiseParams, OUT_DIR,
                           ServoParams, SimParams, VehicleParams)
from tvcsim.sim import simulate

BURN_END = 3.55
SERVO_GAIN = 6.0
CASES = [(0, 0.030), (1, 0.050), (2, 0.030), (3, 0.050)]     # (Seed, Servo-Totzeit s)


def one_flight(args):
    cfg, kp, ki, kd, seed, tau = args
    I = cfg["inertia_kgm2"]
    lat = cfg.get("cg_lateral_m", [0.0, 0.0])
    veh = VehicleParams(Ix=I["Izz"], Iy=I["Ixx"], Iz=I["Iyy"], l=cfg["lever_arm_m"], l_meas=cfg["lever_arm_m"],
                        m_dry=cfg["mass_kg"] - FUEL_PER_MOTOR_KG, mis_y=float(lat[0]), mis_z=float(lat[1]),
                        static_error_y=1.0, static_error_z=0.6, servo_delay=tau)
    fw = replace(FirmwareParams(), PY_KP=kp, PY_KI=ki, PY_KD=kd, MASS_KG=cfg["mass_kg"], MOMENT_ARM_M=cfg["lever_arm_m"],
                 SERVO_YAW_GAIN=-SERVO_GAIN, SERVO_PITCH_GAIN=SERVO_GAIN)
    p = SimParams(vehicle=veh, firmware=fw, motor=MotorParams(second_motor=False, fuel_model="impulse"),
                  servo=ServoParams(servo_deg_per_tvc_deg=SERVO_GAIN), noise=NoiseParams(enabled=True, accel_model="specific_force"),
                  controller="firmware", t_end=5.0, seed=seed, ground=True)
    res = simulate(p)
    burn = (res.t > 0.05) & (res.t <= BURN_END)
    lim = 22.5 / SERVO_GAIN - 1e-3
    sat = float(np.mean((np.abs(res.th_y_com[burn]) >= lim) | (np.abs(res.th_z_com[burn]) >= lim)))
    k = min(int(np.searchsorted(res.t, BURN_END)), len(res.t) - 1)
    return float(res.tilt_deg[burn].max()), sat, float(np.hypot(res.r[k, 1], res.r[k, 2]))


def objective(pool, cfg, kp, ki, kd):
    out = list(pool.map(one_flight, [(cfg, kp, ki, kd, s, tau) for s, tau in CASES]))
    tilt = np.array([o[0] for o in out]); sat = np.array([o[1] for o in out]); lat = np.array([o[2] for o in out])
    J = tilt.mean() + 0.5 * tilt.max() + 20.0 * sat.mean() + 0.5 * lat.mean()
    return float(J), dict(tilt_mean=tilt.mean(), tilt_max=tilt.max(), sat=sat.mean(), lateral=lat.mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="base", help="Schlüssel in cad/mass_stand2b.json 'levers' (base, P1, P2, P3, ...)")
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-ki", action="store_true", help="Ki = 0 festhalten (wie Config.h)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--eval", type=float, nargs=3, metavar=("KP", "KI", "KD"), help="nur diesen Satz auswerten")
    ap.add_argument("--configs", nargs="+", help="mit --eval: mehrere Konfigurationen")
    args = ap.parse_args()
    if args.eval:
        levers = json.loads(STAND2B_MASS_FILE.read_text(encoding="utf-8"))["levers"]
        kp, ki, kd = args.eval
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for c in args.configs or [args.config]:
                J, m = objective(pool, levers[c], kp, ki, kd)
                print(f"{c:5s} Kp {kp:g} Ki {ki:g} Kd {kd:g}: J {J:5.2f}  Kipp {m['tilt_mean']:.1f}/{m['tilt_max']:.1f}°  "
                      f"Anschlag {100 * m['sat']:.0f} %  seitlich {m['lateral']:.2f} m", flush=True)
        return
    cfg = json.loads(STAND2B_MASS_FILE.read_text(encoding="utf-8"))["levers"][args.config]
    space = {"kp": (0.3, 8.0, "log"), "kd": (0.03, 2.0, "log")}
    if not args.no_ki:
        space["ki"] = (0.0, 1.5, "lin")
    opt = BayesOpt(space, seed=args.seed)
    rows = []
    OUT_DIR.mkdir(exist_ok=True)
    print(f"{args.config}: {cfg['mass_kg'] * 1000:.0f} g, Hebelarm {cfg['lever_arm_m'] * 1000:.0f} mm, {len(CASES)} Flüge je Punkt", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for it in range(args.iters):
            x = opt.ask()
            ki = x.get("ki", 0.0)
            J, m = objective(pool, cfg, x["kp"], ki, x["kd"])
            opt.tell(x, float(np.log(J)))          # log: Ausreißer (instabile Sätze, J ≈ 80) verzerren den GP sonst
            rows.append(dict(it=it, kp=x["kp"], ki=ki, kd=x["kd"], J=J, **m))
            print(f"  {it:2d}  Kp {x['kp']:5.2f}  Ki {ki:4.2f}  Kd {x['kd']:5.3f}  J {J:6.2f}  "
                  f"Kipp {m['tilt_mean']:4.1f}/{m['tilt_max']:4.1f}°  Anschlag {100 * m['sat']:3.0f} %  seitl {m['lateral']:4.2f} m", flush=True)
        xb, mu, sd = opt.best()
        ki = xb.get("ki", 0.0)
        J, m = objective(pool, cfg, xb["kp"], ki, xb["kd"])
    print(f"BESTER {args.config}: Kp {xb['kp']:.2f}  Ki {ki:.2f}  Kd {xb['kd']:.3f}  (GP exp({mu:.2f}) = {np.exp(mu):.2f}, nachgerechnet J {J:.2f}, "
          f"Kipp {m['tilt_mean']:.1f}/{m['tilt_max']:.1f}°, Anschlag {100 * m['sat']:.0f} %, seitlich {m['lateral']:.2f} m)", flush=True)
    path = OUT_DIR / f"tune_bayes_{args.config}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"geschrieben: {path}")


if __name__ == "__main__":
    main()
