"""Regeltakt 100 Hz gegen 250 Hz, Reaktionsmoment des Kardans, Servo-Ratenbegrenzung und D-Tiefpass.

    python scripts/rate_study.py                 # alles: Tabellen auf der Konsole, out/rate_study.csv
    python scripts/rate_study.py --part sim      # nur die Flugsimulationen
    python scripts/rate_study.py --part linear   # nur die Frequenzgang-Rechnung (Sekunden)

Fahrzeug: Stand 2b aus ``cad/mass_stand2b.json`` (Abschnitt ``levers``, wie ``tune_bayes.py``), Firmware-Regler mit
den Bayes-Gewinnen Kp 2 / Ki 1 / Kd 0,45, wahre Masse und wahrer Hebelarm, Servo-Umrechnung 6, ein Motor, Boden,
Rauschen, statischer Fehler 1°/0,6°, spezifische Kraft. Faelle: die vier Robustheitsfaelle von ``tune_bayes.py``
(Seeds 0..3, Servo-Totzeit 30/50 ms) mit 705 g, dazu die Gewichtspakete P1..P3 und zwei Stoerfaelle
(statischer Fehler 2°/2°, Schwerpunkt 3 mm seitlich).

100 Hz heisst: Momentanwert des Gyros zum Takt (Firmware bis Oktober 2026). 250 Hz: Mittel ueber den 4-ms-Takt
(Gruppenlaufzeit 2 ms). Der |a|-Filter ist zeitbasiert (``A_NORM_TAU_S`` 95 ms, wie main.cpp seit 11/2026).

Kennzahlen in der Brennphase (0,05..3,55 s): Kipp max, Anteil am Kardanfenster, Servo-Kommandorate (Servo-Grad/s,
99-%-Quantil und RMS) und RMS des Servokommandos um seinen Mittelwert, dazu die wirkliche Kardanrate.

Linearer Teil: offener Kreis L(jw) = Regler (diskret, mit Integration rot += omega dt) * Halteglied * IMU-Mittelung
* Totzeit * Servo-PT2 * Rumpf. Rumpf mit Reaktionsmoment: I s^2 phi = -(l T + I_g s^2) delta, also ein Nullstellenpaar
bei w_z = sqrt(l T / I_g): darueber dreht das Reaktionsmoment das Vorzeichen der Strecke um. Ausgabe: Durchtritts-
frequenz, Phasenreserve, Amplitudenreserve (kleinste ueber alle -180°-Durchgaenge).
"""
import argparse
import csv
import json
import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

import _path  # noqa: F401
from tvcsim.params import (FUEL_PER_MOTOR_KG, GIMBAL_INERTIA_STAND2B, STAND2B_MASS_FILE, FirmwareParams, MotorParams,
                           NoiseParams, OUT_DIR, ServoParams, SimParams, VehicleParams)
from tvcsim.actuator import static_error_profile_y
from tvcsim.sim import simulate

BURN_END = 3.55
GAIN = 6.0
GAINS = (2.0, 1.0, 0.45)


def levers():
    return json.loads(STAND2B_MASS_FILE.read_text(encoding="utf-8"))["levers"]


def build(cfg, rate_hz, seed=0, tau=0.030, kp=GAINS[0], ki=GAINS[1], kd=GAINS[2], servo="sg90", I_g=0.0,
          d_lpf=0.0, slew=0.0, se=(1.0, 0.6), mis=(None, None), servo_rate=None):
    I = cfg["inertia_kgm2"]
    lat = cfg.get("cg_lateral_m", [0.0, 0.0])
    veh = VehicleParams(Ix=I["Izz"], Iy=I["Ixx"], Iz=I["Iyy"], l=cfg["lever_arm_m"], l_meas=cfg["lever_arm_m"],
                        m_dry=cfg["mass_kg"] - FUEL_PER_MOTOR_KG,
                        mis_y=float(lat[0]) if mis[0] is None else mis[0], mis_z=float(lat[1]) if mis[1] is None else mis[1],
                        static_error_y=se[0], static_error_z=se[1], servo_delay=tau, gimbal_inertia=I_g)
    fw = replace(FirmwareParams(), PY_KP=kp, PY_KI=ki, PY_KD=kd, MASS_KG=cfg["mass_kg"], MOMENT_ARM_M=cfg["lever_arm_m"],
                 SERVO_YAW_GAIN=-GAIN, SERVO_PITCH_GAIN=GAIN,
                 D_LPF_HZ=d_lpf, SERVO_SLEW_DPS=slew)
    sp = ServoParams.w5652h(servo_deg_per_tvc_deg=GAIN) if servo == "w5652h" else ServoParams(servo_deg_per_tvc_deg=GAIN)
    if servo_rate is not None:
        sp = replace(sp, rate_limit_dps=servo_rate)
    p = SimParams(vehicle=veh, firmware=fw, motor=MotorParams(second_motor=False, fuel_model="impulse"), servo=sp,
                  noise=NoiseParams(enabled=True, accel_model="specific_force"), controller="firmware", t_end=4.0,
                  seed=seed, ground=True)
    return p.at_rate(rate_hz)


def metrics(res):
    t = res.t
    dt = res.params.control.dt
    burn = (t > 0.05) & (t <= BURN_END)
    lim = 22.5 / GAIN - 1e-3
    sat = float(np.mean((np.abs(res.th_y_com[burn]) >= lim) | (np.abs(res.th_z_com[burn]) >= lim)))
    sy, sz = res.servo_y_deg, res.servo_z_deg            # Servo-Grad relativ zur Mitte
    ry, rz = np.diff(sy) / dt, np.diff(sz) / dt
    b1 = burn[1:]
    rate = np.concatenate([np.abs(ry[b1]), np.abs(rz[b1])])
    act = np.concatenate([sy[burn] - sy[burn].mean(), sz[burn] - sz[burn].mean()])
    # wirkliche Kardanrate (TVC-Grad/s), ohne den Sprung des statischen Fehlerprofils bei 2 s
    se_y = res.params.vehicle.static_error_y * np.array([static_error_profile_y(tt) for tt in t])
    gy, gz = np.diff(res.th_y + se_y) / dt, np.diff(res.th_z) / dt
    grate = np.concatenate([np.abs(gy[b1]), np.abs(gz[b1])])
    k = min(int(np.searchsorted(t, BURN_END)), len(t) - 1)
    return dict(tilt=float(res.tilt_deg[burn].max()), sat=sat, rate_p99=float(np.quantile(rate, 0.99)),
                rate_rms=float(np.sqrt(np.mean(rate ** 2))), cmd_rms=float(np.sqrt(np.mean(act ** 2))),
                gimbal_rate_max=float(grate.max()), lateral=float(np.hypot(res.r[k, 1], res.r[k, 2])),
                apogee=res.max_height)


def run_one(job):
    name, kw = job
    cfg = levers()[kw.pop("config", "base")]
    return name, kw, metrics(simulate(build(cfg, **kw)))


CASES = [("base s0 30ms", dict(seed=0, tau=0.030)), ("base s1 50ms", dict(seed=1, tau=0.050)),
         ("base s2 30ms", dict(seed=2, tau=0.030)), ("base s3 50ms", dict(seed=3, tau=0.050)),
         ("P1 672 g", dict(config="P1")), ("P2 631 g", dict(config="P2")), ("P3 593 g", dict(config="P3")),
         ("stat. Fehler 2/2°", dict(se=(2.0, 2.0))), ("Schwerpunkt 3 mm", dict(mis=(0.003, 0.003)))]


def fmt(name, m):
    return (f"{name:34s} {m['tilt']:5.2f}° {100 * m['sat']:4.0f} % {m['rate_p99']:7.0f} {m['rate_rms']:6.0f} "
            f"{m['cmd_rms']:5.2f} {m['gimbal_rate_max']:6.0f} {m['lateral']:5.2f} m")


HEAD = (f"{'Fall':34s} {'Kipp':>6s} {'Ansch':>6s} {'Rate99':>7s} {'RateRMS':>6s} {'KmdRMS':>5s} {'KardR':>6s} "
        f"{'seitl':>7s}\n{'':34s} {'max':>6s} {'':>6s} {'Srv°/s':>7s} {'Srv°/s':>6s} {'Srv°':>5s} {'°/s':>6s}")


def part_sim(workers, rows):
    jobs = []
    for rate in (100.0, 250.0):
        for name, kw in CASES:
            jobs.append((f"{rate:.0f} Hz | {name}", dict(kw, rate_hz=rate)))
    # 250 Hz: Servo, Reaktionsmoment, Kd, Tiefpass, Slew (Fall base s1 50 ms = schwierigster der vier)
    var = [("SG90, I_g 0", {}), ("SG90, I_g 5e-4", dict(I_g=GIMBAL_INERTIA_STAND2B)),
           ("SG90, I_g 1,5e-3 (3x)", dict(I_g=3 * GIMBAL_INERTIA_STAND2B)),
           ("W5652H, I_g 0", dict(servo="w5652h")),
           ("W5652H, I_g 5e-4", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B)),
           ("W5652H, I_g 1,5e-3 (3x)", dict(servo="w5652h", I_g=3 * GIMBAL_INERTIA_STAND2B)),
           ("W5652H, I_g 5e-3 (10x)", dict(servo="w5652h", I_g=10 * GIMBAL_INERTIA_STAND2B)),
           ("W5652H 0,10 s/60°, I_g 5e-4", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, servo_rate=600.0)),
           ("W5652H, I_g 5e-4, Kd 0,30", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, kd=0.30)),
           ("W5652H, I_g 5e-4, Kd 0,60", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, kd=0.60)),
           ("W5652H, I_g 5e-4, D-TP 30 Hz", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, d_lpf=30.0)),
           ("W5652H, I_g 5e-4, D-TP 15 Hz", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, d_lpf=15.0)),
           ("W5652H, I_g 5e-4, Slew 600°/s", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, slew=600.0)),
           ("W5652H, I_g 5e-4, Slew 300°/s", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, slew=300.0)),
           ("W5652H, I_g 5e-4, TP 30 + Slew 600", dict(servo="w5652h", I_g=GIMBAL_INERTIA_STAND2B, d_lpf=30.0, slew=600.0))]
    for vname, vkw in var:
        for s, tau in ((0, 0.030), (1, 0.050), (2, 0.030), (3, 0.050)):
            jobs.append((f"250 Hz var | {vname} | s{s}", dict(vkw, rate_hz=250.0, seed=s, tau=tau if "servo" not in vkw else 0.004 + (tau - 0.030))))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        out = list(pool.map(run_one, jobs))
    res = {n: m for n, _, m in out}
    print("\nA) 100 Hz (Momentanwert) gegen 250 Hz (Mittel 4 ms), SG90-Fit, ohne Reaktionsmoment, Kp 2 / Ki 1 / Kd 0,45")
    print(HEAD)
    for name, _ in CASES:
        for rate in ("100", "250"):
            n = f"{rate} Hz | {name}"
            print(fmt(n, res[n])); rows.append(dict(case=n, **res[n]))
    print("\nB) 250 Hz: Servo-Modell, Reaktionsmoment, Kd, D-Tiefpass, Slew (Mittel ueber 4 Seeds/Totzeiten; "
          "W5652H-Totzeit 4 ms bzw. 24 ms)")
    print(HEAD)
    for vname, _ in var:
        ms = [res[f"250 Hz var | {vname} | s{s}"] for s in range(4)]
        agg = {k: float(np.mean([m[k] for m in ms])) for k in ms[0]}
        agg["tilt"] = float(max(m["tilt"] for m in ms))
        print(fmt(vname, agg)); rows.append(dict(case=f"250 Hz var | {vname} (max Kipp, Mittel Rest)", **agg))


# ---------------------------------------------------------------------------
# linear
# ---------------------------------------------------------------------------

def loop(w, rate_hz, T, I_g, kd=GAINS[2], kp=GAINS[0], ki=GAINS[1], servo="sg90", tau=0.030, avg=None, d_lpf=0.0,
         I=0.0211, l=0.190):
    dt = 1.0 / rate_hz
    avg = rate_hz >= 200 if avg is None else avg
    s = 1j * w
    z = np.exp(s * dt)
    integ = dt / (1.0 - 1.0 / z)                       # rot_k = rot_{k-1} + omega_k dt
    dterm = kd
    if d_lpf > 0:
        a = 1.0 - math.exp(-2 * math.pi * d_lpf * dt)
        dterm = kd * a / (1.0 - (1.0 - a) / z)
    C = 0.573 / (l * T) * (kp * integ + ki * integ * integ + dterm)    # rad Kardan je rad/s Drehrate
    zoh = (1.0 - np.exp(-s * dt)) / (s * dt)
    meas = (1.0 - np.exp(-s * dt)) / (s * dt) if avg else 1.0
    if servo == "w5652h":
        sp = ServoParams.w5652h(); tau = 0.004 + (tau - 0.030)
    else:
        sp = ServoParams()
    S = sp.wn ** 2 / (s * s + 2 * sp.zeta * sp.wn * s + sp.wn ** 2) * np.exp(-s * tau)
    P = (l * T + I_g * s * s) / (I * s)               # Drehrate je Kardanwinkel (Betrag, Vorzeichen in der Gegenkopplung)
    return C * zoh * meas * S * P


def margins(L, w):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L))
    i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    wc = w[i[0]] if len(i) else float("nan")
    pm = ((math.degrees(ph[i[0]]) + 180.0 + 180.0) % 360.0 - 180.0) if len(i) else float("nan")
    # Amplitudenreserve: |L| an allen Stellen mit Phase -180 (mod 360)
    phd = np.degrees(ph)
    k = np.where(np.floor((phd[:-1] + 180) / 360) != np.floor((phd[1:] + 180) / 360))[0]
    gm = min((1.0 / mag[j] for j in k if w[j] > wc), default=float("inf"))
    gm_w = min(((1.0 / mag[j], w[j]) for j in k if w[j] > wc), default=(float("inf"), float("nan")))[1]
    return wc, pm, 20 * math.log10(gm) if np.isfinite(gm) else float("inf"), gm_w


def part_linear(rows):
    w = np.logspace(0, math.log10(math.pi * 250), 6000)
    print("\nC) Linear, 705 g, I 0,0211 kg m², l 0,19 m, Kp 2 / Ki 1 / Kd 0,45. "
          "wc = Durchtritt, PM = Phasenreserve, GM = Amplitudenreserve (bei Frequenz)")
    print(f"{'Fall':44s} {'T':>4s} {'wc rad/s':>8s} {'PM':>6s} {'GM':>7s} {'bei':>8s}  {'w_z':>6s}")
    variants = [("100 Hz, SG90, I_g 0", dict(rate_hz=100, I_g=0.0)),
                ("250 Hz, SG90, I_g 0", dict(rate_hz=250, I_g=0.0)),
                ("100 Hz, SG90, I_g 5e-4", dict(rate_hz=100, I_g=5e-4)),
                ("250 Hz, SG90, I_g 5e-4", dict(rate_hz=250, I_g=5e-4)),
                ("250 Hz, SG90 50 ms, I_g 5e-4", dict(rate_hz=250, I_g=5e-4, tau=0.050)),
                ("250 Hz, W5652H, I_g 0", dict(rate_hz=250, I_g=0.0, servo="w5652h")),
                ("250 Hz, W5652H, I_g 5e-4", dict(rate_hz=250, I_g=5e-4, servo="w5652h")),
                ("250 Hz, W5652H, I_g 1,5e-3", dict(rate_hz=250, I_g=1.5e-3, servo="w5652h")),
                ("250 Hz, W5652H, I_g 1,5e-3, D-TP 30 Hz", dict(rate_hz=250, I_g=1.5e-3, servo="w5652h", d_lpf=30.0)),
                ("250 Hz, W5652H, I_g 5e-4, Kd 0,60", dict(rate_hz=250, I_g=5e-4, servo="w5652h", kd=0.60)),
                ("250 Hz, W5652H, I_g 5e-4, Kd 0,30", dict(rate_hz=250, I_g=5e-4, servo="w5652h", kd=0.30)),
                ("250 Hz, W5652H, I_g 5e-4, D-TP 30 Hz", dict(rate_hz=250, I_g=5e-4, servo="w5652h", d_lpf=30.0)),
                ("250 Hz, W5652H, I_g 5e-4, D-TP 15 Hz", dict(rate_hz=250, I_g=5e-4, servo="w5652h", d_lpf=15.0))]
    for name, kw in variants:
        for T in (25.0, 10.0, 3.0):
            wc, pm, gm, gw = margins(loop(w, T=T, **kw), w)
            wz = math.sqrt(0.19 * T / kw["I_g"]) if kw["I_g"] > 0 else float("inf")
            print(f"{name:44s} {T:4.0f} {wc:8.1f} {pm:5.1f}° {gm:6.1f}dB {gw:6.0f}/s  {wz:6.0f}")
            rows.append(dict(case=f"linear | {name} | T {T:g} N", wc=wc, pm=pm, gm_db=gm, gm_w=gw, w_z=wz))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--part", choices=["all", "sim", "linear"], default="all")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    rows = []
    if args.part in ("all", "linear"):
        part_linear(rows)
    if args.part in ("all", "sim"):
        part_sim(args.workers, rows)
    OUT_DIR.mkdir(exist_ok=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k != "case", k))
    with open(OUT_DIR / f"rate_study_{args.part}.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=keys); wr.writeheader(); wr.writerows(rows)
    print(f"geschrieben: {OUT_DIR / f'rate_study_{args.part}.csv'}")


if __name__ == "__main__":
    main()
