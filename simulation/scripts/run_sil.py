"""Software-in-the-Loop: Flug mit dem echten C++-Flugkern der Firmware (tvcsim.sil).

Der Regler, die Lageschätzung, der Höhen-Kalman, der Zustandsautomat und die Pyro-Logik sind der
Code aus firmware/lib/flightcore, mit den Konstanten aus firmware/src/Config.h. Die Simulation
liefert Drehrate, spezifische Kraft und Barometer, der Kern liefert Servokommandos und Zündzeitpunkt.

  python scripts/run_sil.py                         # ein Erstflug, Tabelle + out/sil_flight.png
  python scripts/run_sil.py --no-control            # dasselbe ohne Regler (zeigt, warum es ihn braucht)
  python scripts/run_sil.py --runs 50               # Monte-Carlo: Fehlstellungen, Masse, Servo-Totzeit streuen
  python scripts/run_sil.py --apogee-sweep          # Apogäum-Schwellen gegen Auslöseverzug und -geschwindigkeit
  python scripts/run_sil.py --kp 4 --kd 1.5 --static-error-y 1.5

Vorgaben: Fahrzeug erstflug (cad/mass_properties.json), TSP E12 mit 28 g Treibstoff (fuel impulse),
ein Motor, Kardan ±TVC_MAX_DEG aus Config.h, Beschleunigungssensor misst die spezifische Kraft,
Servo-Modell aus dem SG90-Fit (bis die W5652H vermessen sind). Kein Luftwiderstand im Modell, also
fällt die Rakete nach dem Gipfel ohne Schirm; die Rechnung zeigt, wann und wie schnell der Kern auslöst.
"""
import argparse
import csv
from dataclasses import replace

import numpy as np

import _path  # noqa: F401
from tvcsim.params import MotorParams, NoiseParams, OUT_DIR, ServoParams, SimParams, VehicleParams
from tvcsim.sil import PHASES, SilParams, trace_arrays
from tvcsim.sim import simulate

VEHICLES = {"erstflug": VehicleParams.erstflug, "cad": VehicleParams.cad,
            "preload": VehicleParams.preload, "nominal": VehicleParams.nominal}


def build(args, seed: int, vehicle_upd: dict | None = None, sil_upd: dict | None = None, servo_delay=None) -> SimParams:
    sil_over = {k: getattr(args, k) for k in ("kp", "ki", "kd") if getattr(args, k) is not None}
    sil_over.update(sil_upd or {})
    sil = SilParams.from_config_h(control_enabled=not args.no_control, **sil_over)
    veh = VEHICLES[args.vehicle]()
    veh = replace(veh, static_error_y=args.static_error_y, static_error_z=args.static_error_z,
                  servo_delay=servo_delay, **(vehicle_upd or {}))
    return SimParams(vehicle=veh, motor=MotorParams(fuel_model="impulse", second_motor=False),
                     servo=ServoParams(sat_deg=sil.values["tvc_max_deg"]),
                     noise=NoiseParams(enabled=not args.no_noise, accel_model="specific_force"),
                     controller="sil", sil=sil, t_end=args.t_end, seed=seed)


def analyze(res) -> dict:
    tr = trace_arrays(res.extra["trace"])
    n = len(res.t)
    for k in tr:
        tr[k] = tr[k][:n]
    events = {PHASES[ph]: float(t) for t, ph, e in zip(tr["t"], tr["phase"], tr["event"]) if e}
    k_ap = int(np.argmax(res.r[:, 0]))
    lifted = np.where(res.r[:, 0] > 1e-6)[0]
    burn = (res.T > 0.0)
    m = {
        "liftoff_true_s": float(res.t[lifted[0]]) if len(lifted) else np.nan,
        "burnout_true_s": float(res.t[np.where(burn)[0][-1]]) if burn.any() else np.nan,
        "apogee_true_s": float(res.t[k_ap]), "apogee_m": float(res.r[k_ap, 0]),
        "tilt_max_burn_deg": float(res.tilt_deg[burn].max()) if burn.any() else np.nan,
        "tilt_burnout_deg": float(res.tilt_deg[np.where(burn)[0][-1]]) if burn.any() else np.nan,
        "tilt_est_err_max_deg": float(np.abs(tr["tilt_deg"] - res.tilt_deg).max()),
        "sat_share_burn": float(tr["sat"][burn].mean()) if burn.any() else np.nan,
        "landed_s": res.extra.get("t_land"),
        "abort": "ABORT" in events,
    }
    for ph in ("BOOST", "COAST", "APOGEE", "DESCENT", "ABORT"):
        m[f"t_{ph.lower()}_s"] = events.get(ph, np.nan)
    fire = np.where(tr["fire"] > 0)[0]
    if len(fire):
        k = int(fire[0])
        m.update(deploy_s=float(res.t[k]), deploy_delay_s=float(res.t[k] - res.t[k_ap]),
                 deploy_alt_m=float(res.r[k, 0]), deploy_speed_ms=float(np.linalg.norm(res.rd[k])),
                 deploy_vz_ms=float(res.rd[k, 0]), deploy_lateral_m=float(np.hypot(res.r[k, 1], res.r[k, 2])))
    else:
        m.update(deploy_s=np.nan, deploy_delay_s=np.nan, deploy_alt_m=np.nan, deploy_speed_ms=np.nan,
                 deploy_vz_ms=np.nan, deploy_lateral_m=np.nan)
    m["_trace"] = tr
    return m


def print_single(m: dict, args) -> None:
    print(f"Fahrzeug {args.vehicle}, Regler {'aus' if args.no_control else 'an'}, statischer Fehler "
          f"{args.static_error_y}/{args.static_error_z}°, Rauschen {'aus' if args.no_noise else 'an'}")
    rows = [
        ("Abheben (Simulation)", f"{m['liftoff_true_s']:.2f} s"),
        ("BOOST erkannt", f"{m['t_boost_s']:.2f} s"),
        ("Brennschluss (Simulation)", f"{m['burnout_true_s']:.2f} s"),
        ("COAST erkannt", f"{m['t_coast_s']:.2f} s"),
        ("Gipfel (Simulation)", f"{m['apogee_true_s']:.2f} s, {m['apogee_m']:.1f} m"),
        ("APOGEE erkannt", f"{m['t_apogee_s']:.2f} s"),
        ("ABORT", f"{m['t_abort_s']:.2f} s" if m["abort"] else "nein"),
        ("Zündung Kanal 1", f"{m['deploy_s']:.2f} s, {m['deploy_delay_s']:+.2f} s zum Gipfel"),
        ("  Höhe / Geschwindigkeit", f"{m['deploy_alt_m']:.1f} m, |v| {m['deploy_speed_ms']:.1f} m/s (vz {m['deploy_vz_ms']:+.1f})"),
        ("  seitlich vom Pad", f"{m['deploy_lateral_m']:.1f} m"),
        ("Kippwinkel max im Boost", f"{m['tilt_max_burn_deg']:.2f}°"),
        ("Kippwinkel bei Brennschluss", f"{m['tilt_burnout_deg']:.2f}°"),
        ("Regler in Sättigung (Boost)", f"{100 * m['sat_share_burn']:.0f} % der Takte"),
        ("Lagefehler der Firmware max", f"{m['tilt_est_err_max_deg']:.2f}°"),
    ]
    for k, v in rows:
        print(f"  {k:30s} {v}")


def plot_single(res, m: dict, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tr = m["_trace"]
    t = res.t
    fig, ax = plt.subplots(4, 1, figsize=(10, 11), sharex=True, layout="constrained")
    ax[0].plot(t, res.r[:, 0], label="Höhe (Simulation)")
    ax[0].plot(t, tr["alt_m"], "--", label="Kalman (Firmware)")
    ok = ~np.isnan(tr["baro_m"])
    ax[0].plot(t[ok], tr["baro_m"][ok], ".", ms=1.5, alpha=0.4, label="Barometer")
    ax[0].set_ylabel("Höhe [m]")
    ax[1].plot(t, res.rd[:, 0], label="vz (Simulation)")
    ax[1].plot(t, tr["vz_ms"], "--", label="vz Kalman")
    ax[1].set_ylabel("vz [m/s]")
    ax[2].plot(t, res.tilt_deg, label="Kippwinkel (Simulation)")
    ax[2].plot(t, tr["tilt_deg"], "--", label="Kippwinkel (Firmware-Quaternion)")
    ax[2].set_ylabel("Kippwinkel [°]")
    ax[3].plot(t, tr["tvc_yaw_deg"], label="TVC Yaw (nach Servo-Rundung)")
    ax[3].plot(t, tr["tvc_pitch_deg"], label="TVC Pitch")
    ax[3].set_ylabel("TVC [°]")
    ax[3].set_xlabel("Zeit [s]")
    for a in ax:
        for name, key, col in (("BOOST", "t_boost_s", "g"), ("COAST", "t_coast_s", "b"),
                               ("APOGEE", "t_apogee_s", "m"), ("ABORT", "t_abort_s", "r")):
            if not np.isnan(m[key]):
                a.axvline(m[key], color=col, lw=0.8, ls=":")
        a.axvline(m["apogee_true_s"], color="k", lw=0.8, ls="-.")
        if not np.isnan(m["deploy_s"]):
            a.axvline(m["deploy_s"], color="r", lw=1.2)
        a.grid(alpha=0.3)
        a.legend(loc="best", fontsize=8)
    ax[0].set_title("SIL: Firmware-Flugkern in der 6DOF-Simulation  (gestrichelt = Firmware, schwarz = wahrer Gipfel, rot = Zündung)")
    fig.savefig(path, dpi=120)
    print(f"-> {path}")


def montecarlo(args) -> None:
    rng = np.random.default_rng(args.seed)
    base = VEHICLES[args.vehicle]()
    rows = []
    for i in range(args.runs):
        upd = {"mis_y": float(rng.normal(0, 0.001)), "mis_z": float(rng.normal(0, 0.001)),
               "m_dry": float(base.m_dry * (1 + rng.normal(0, 0.03))),
               "Ix": float(base.Ix * (1 + rng.normal(0, 0.1))), "Iy": float(base.Iy * (1 + rng.normal(0, 0.1))),
               "Iz": float(base.Iz * (1 + rng.normal(0, 0.1)))}
        a = argparse.Namespace(**vars(args))
        a.static_error_y = float(rng.normal(0, args.static_error_y))
        a.static_error_z = float(rng.normal(0, args.static_error_z))
        delay = float(np.clip(rng.normal(0.03, 0.01), 0.0, 0.08))
        res = simulate(build(a, seed=args.seed + 1000 + i, vehicle_upd=upd, servo_delay=delay))
        m = analyze(res)
        m.pop("_trace")
        m.update(run=i, static_error_y=a.static_error_y, static_error_z=a.static_error_z, servo_delay=delay, **upd)
        rows.append(m)
        print(f"  {i + 1:3d}/{args.runs}  Gipfel {m['apogee_m']:5.1f} m  Kipp {m['tilt_max_burn_deg']:5.2f}°  "
              f"Zündung {m['deploy_delay_s']:+.2f} s bei {m['deploy_speed_ms']:4.1f} m/s{'  ABORT' if m['abort'] else ''}")
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / "sil_montecarlo.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def stat(key):
        v = np.array([r[key] for r in rows], dtype=float)
        v = v[~np.isnan(v)]
        return f"Median {np.median(v):6.2f}   95 % {np.percentile(v, 95):6.2f}   max {v.max():6.2f}" if len(v) else "–"

    print(f"\nMonte-Carlo, {args.runs} Läufe (statischer Fehler σ {args.static_error_y}/{args.static_error_z}°, "
          f"Masse ±3 %, I ±10 %, Schwerpunkt ±1 mm, Servo-Totzeit 30 ± 10 ms):")
    print(f"  Kippwinkel max im Boost [°]   {stat('tilt_max_burn_deg')}")
    print(f"  Gipfelhöhe [m]                {stat('apogee_m')}")
    print(f"  Zündung nach dem Gipfel [s]   {stat('deploy_delay_s')}")
    print(f"  Geschwindigkeit bei Zündung   {stat('deploy_speed_ms')}")
    print(f"  ABORT                         {sum(r['abort'] for r in rows)} von {args.runs}")
    print(f"  Zündung vor dem Gipfel        {sum((r['deploy_delay_s'] < 0) for r in rows)} von {args.runs}")
    print(f"-> {path}")


def apogee_sweep(args) -> None:
    drops = [0.3, 0.5, 1.0, 1.5]
    holds = [100, 200, 300]
    seeds = range(args.seed, args.seed + args.sweep_seeds)
    print(f"Apogäum-Schwellen, je {len(seeds)} Läufe mit Rauschen (vz-Schwelle wie Config.h):")
    print(f"  {'Baro-Abfall':>11s} {'Haltezeit':>9s} {'Verzug Median':>14s} {'Verzug max':>10s} {'|v| Median':>10s} {'|v| max':>8s} {'zu früh':>8s}")
    for d in drops:
        for h in holds:
            delays, speeds, early = [], [], 0
            for s in seeds:
                m = analyze(simulate(build(args, seed=s, sil_upd={"apogee_baro_drop_m": d, "apogee_hold_ms": h})))
                delays.append(m["deploy_delay_s"]); speeds.append(m["deploy_speed_ms"])
                early += int(m["deploy_delay_s"] < 0)
            print(f"  {d:9.1f} m {h:7d} ms {np.median(delays):12.2f} s {np.max(delays):8.2f} s "
                  f"{np.median(speeds):8.1f} m/s {np.max(speeds):5.1f} {early:6d}/{len(seeds)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vehicle", choices=list(VEHICLES), default="erstflug")
    ap.add_argument("--no-control", action="store_true", help="Regler aus (PY_CONTROL_ACTIVE = false)")
    ap.add_argument("--kp", type=float); ap.add_argument("--ki", type=float); ap.add_argument("--kd", type=float)
    ap.add_argument("--static-error-y", type=float, default=1.0, help="Grad; bei --runs die Standardabweichung")
    ap.add_argument("--static-error-z", type=float, default=0.6)
    ap.add_argument("--no-noise", action="store_true")
    ap.add_argument("--t-end", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--runs", type=int, default=0, help="Monte-Carlo mit so vielen Läufen")
    ap.add_argument("--apogee-sweep", action="store_true")
    ap.add_argument("--sweep-seeds", type=int, default=5)
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()

    if args.runs:
        montecarlo(args)
        return
    if args.apogee_sweep:
        apogee_sweep(args)
        return
    res = simulate(build(args, seed=args.seed))
    m = analyze(res)
    print_single(m, args)
    if not args.no_plot:
        OUT_DIR.mkdir(exist_ok=True)
        plot_single(res, m, OUT_DIR / f"sil_flight{'_nocontrol' if args.no_control else ''}.png")


if __name__ == "__main__":
    main()
