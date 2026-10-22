"""Experiment E01 auswerten: Servo-Soll -> Kardanwinkel aus der CSV von ``servo_ident``.

    python scripts/ident_servo.py messung.csv                 # alle Läufe der Datei
    python scripts/ident_servo.py messung.csv --gyro-axis y --gyro-sign -1
    python scripts/ident_servo.py --synthetic                 # Probelauf ohne Hardware

Ausgabe je Lauf: Bericht auf der Konsole, ``out/ident_<name>_<achse>.png`` (Zeitverlauf,
Kennlinie, Sprungantworten, Frequenzgang) und ``out/ident_<name>_<achse>.json`` mit allen
Kennwerten, dazu ein ``ServoParams``-Block zum Eintragen in ``tvcsim/params.py``.
Anleitung zum Versuch: ``docs/experiments/E01_servo_ident.md``.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import _path  # noqa: F401
from tvcsim.ident import (SEG_ALT, SEG_NAMES, SEG_STEPS, analyze, format_report, load_ident_csv, pt2_bode,
                          synthesize_run, write_ident_csv)
from tvcsim.params import OUT_DIR, ServoParams


def plot(res: dict, path: Path, title: str) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run, ang, st, fit, s = res["run"], res["angle"], res["static"], res["fit"], res["summary"]
    fig, axs = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    fig.suptitle(title, fontsize=12)

    # 1 Zeitverlauf
    a = axs[0, 0]
    a.plot(run.t, run.cmd * fit["K"], color="0.6", lw=0.8, label=f"Soll · K ({fit['K']:.4f})")
    a.plot(run.t, ang.angle, "k", lw=0.8, label=f"Kardan aus Gyro ({'xyz'[ang.gyro_axis]}, Vorz. {ang.gyro_sign:+.0f})")
    a.plot(run.t, res["y_full"], "r", lw=0.7, alpha=0.8, label=f"PT2+Totzeit, RMS {s['pt2']['rms_full_run_deg']:.2f}°")
    if ang.acc_angle is not None:
        a.plot(run.t, ang.acc_angle, color="tab:blue", lw=0.4, alpha=0.5, label="aus Beschleunigung (Anker)")
    for seg in np.unique(run.seg):
        i = np.flatnonzero(run.seg == seg)[0]
        a.axvline(run.t[i], color="0.85", lw=0.6)
        a.text(run.t[i], a.get_ylim()[1] if False else ang.angle.max(), SEG_NAMES.get(int(seg), ""), fontsize=6,
               rotation=90, va="top", color="0.4")
    a.set_xlabel("Zeit (s)"); a.set_ylabel("Kardan (Grad)"); a.legend(fontsize=8); a.grid(alpha=0.3)
    a.set_title("Zeitverlauf", fontsize=10)

    # 2 Statische Kennlinie
    a = axs[0, 1]
    if st.get("ok"):
        cmd, y, d = np.array(st["cmd"]), np.array(st["angle"]), np.array(st["direction"])
        a.plot(cmd[d > 0], y[d > 0], "o-", color="tab:red", ms=4, label="aufwärts")
        a.plot(cmd[d < 0], y[d < 0], "s-", color="tab:blue", ms=4, label="abwärts")
        xx = np.array([cmd.min(), cmd.max()])
        a.plot(xx, st["K_deg_per_servo_deg"] * xx + st["offset_deg"], "k--", lw=1,
               label=f"K = {st['K_deg_per_servo_deg']:.4f} (1/{st['servo_deg_per_tvc_deg']:.2f}), "
                     f"Offset {st['offset_deg']:+.2f}°, Hyst. {st['hysteresis_mean_deg']:.2f}°")
        a.plot(xx, ServoParams().K * xx, ":", color="0.5", lw=1, label="SG90 2025 (1/6,0)")
    a.set_xlabel("Servo-Soll relativ zur Mitte (Grad)"); a.set_ylabel("Kardan (Grad)")
    a.legend(fontsize=8); a.grid(alpha=0.3); a.set_title("Statische Kennlinie (Treppe)", fontsize=10)

    # 3 Sprungantworten normiert
    a = axs[1, 0]
    dt = run.dt
    for stp in s["steps"]:
        i = int(round((stp["t0_s"] - run.t[0]) / dt))
        n = int(0.6 / dt)
        if i + n > len(run.t):
            continue
        y0 = ang.angle[max(0, i - int(0.1 / dt)):i].mean()
        yy = (ang.angle[i:i + n] - y0) / stp["dy_deg"]
        a.plot(np.arange(n) * dt * 1000, yy, lw=0.8, alpha=0.7,
               color="tab:orange" if stp["seg"] == SEG_ALT else "tab:green")
    tt = np.arange(-0.2, 0.6, dt)
    from tvcsim.ident import simulate_pt2_delay
    ym = simulate_pt2_delay(tt, (tt >= 0).astype(float), fit["K"], fit["wn"], fit["zeta"], fit["tau"]) / fit["K"]
    a.plot(tt[tt >= 0] * 1000, ym[tt >= 0], "k--", lw=1.2,
           label=f"PT2: wn {fit['wn']:.1f} rad/s, zeta {fit['zeta']:.2f}, tau {fit['tau']*1000:.0f} ms")
    a.plot([], [], color="tab:green", label=f"Sprünge aus der Mitte ({SEG_NAMES[SEG_STEPS]})")
    a.plot([], [], color="tab:orange", label=f"Wechselsprünge ({SEG_NAMES[SEG_ALT]})")
    a.axhline(1, color="0.7", lw=0.5)
    a.set_xlabel("Zeit nach dem Sprung (ms)"); a.set_ylabel("Antwort / Endwert")
    a.legend(fontsize=8); a.grid(alpha=0.3)
    a.set_title(f"Sprungantworten: Totzeit {s['step_summary']['dead_time_s_median']*1000:.0f} ms, "
                f"Anstieg {s['step_summary']['rise_10_90_s_median']*1000:.0f} ms, "
                f"max {s['step_summary']['peak_rate_dps_max']:.0f} °/s", fontsize=10)

    # 4 Frequenzgang
    a = axs[1, 1]
    a2 = a.twinx()
    for name, d in res["frequency"].items():
        if len(d["f_hz"]) == 0:
            continue
        a.semilogx(d["f_hz"], d["mag_db"] - 20 * np.log10(fit["K"]), "o-", ms=3, lw=0.8, label=f"{name}: |G|/K")
        a2.semilogx(d["f_hz"], d["phase_deg"], "x--", ms=3, lw=0.6, alpha=0.6, label=f"{name}: Phase")
    f = np.logspace(np.log10(0.3), np.log10(12), 200)
    G = pt2_bode(f, fit["K"], fit["wn"], fit["zeta"], fit["tau"])
    a.semilogx(f, 20 * np.log10(np.abs(G) / fit["K"]), "k", lw=1, label="PT2+Totzeit (Fit)")
    a2.semilogx(f, np.degrees(np.unwrap(np.angle(G))), "k:", lw=1)
    a.axhline(-3, color="0.7", lw=0.5)
    a.set_xlabel("Frequenz (Hz)"); a.set_ylabel("Betrag (dB, auf K bezogen)"); a2.set_ylabel("Phase (Grad)")
    a.set_ylim(-30, 8); a2.set_ylim(-270, 10)
    a.legend(fontsize=8, loc="lower left"); a.grid(alpha=0.3, which="both")
    a.set_title("Frequenzgang aus den Chirps", fontsize=10)

    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="CSV aus servo_ident (ein oder mehrere Läufe)")
    ap.add_argument("--synthetic", action="store_true", help="künstliche Messung erzeugen und auswerten")
    ap.add_argument("--gyro-axis", choices=["x", "y", "z"], help="Gyro-Achse der Kardanbewegung (sonst automatisch)")
    ap.add_argument("--gyro-sign", type=float, choices=[1.0, -1.0], help="Vorzeichen der Gyro-Achse (sonst automatisch)")
    ap.add_argument("--name", help="Name für die Ausgabedateien (Vorgabe: Dateiname)")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    if args.synthetic:
        run = synthesize_run()
        path = write_ident_csv(run, OUT_DIR / "servo_ident_synthetic.csv")
        print(f"künstliche Messung: {path}")
        runs = load_ident_csv(path)
        name = args.name or "synthetic"
    else:
        if not args.csv:
            ap.error("CSV-Datei angeben oder --synthetic")
        runs = load_ident_csv(args.csv)
        name = args.name or Path(args.csv).stem

    gyro_axis = "xyz".index(args.gyro_axis) if args.gyro_axis else None
    for run in runs:
        res = analyze(run, gyro_axis=gyro_axis, gyro_sign=args.gyro_sign)
        s = res["summary"]
        print("=" * 78)
        print(format_report(s))
        base = OUT_DIR / f"ident_{name}_{run.axis}"
        with open(base.with_suffix(".json"), "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False, default=float)
        title = (f"E01 Servo-Identifikation, Achse {run.axis}: {s['meta'].get('note', '')} "
                 f"({s['meta'].get('servo_volt', '?')} V, {s['meta'].get('frame_hz', '?')} Hz)")
        png = plot(res, base.with_suffix(".png"), title)
        print(f"\ngeschrieben: {png}, {base.with_suffix('.json')}")


if __name__ == "__main__":
    main()
