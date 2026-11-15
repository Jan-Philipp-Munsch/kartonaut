"""Punktlandung mit TVC: Monte-Carlo über Flugprofil, Wind, Drossel, Regelung und Sensorik (15.11.2026).

    python scripts/pinpoint_study.py                     # alle Blöcke, 300 Läufe je Szenario, ca. 5 Minuten
    python scripts/pinpoint_study.py --blocks A F --runs 500
    python scripts/pinpoint_study.py --list              # Szenarien nur auflisten

Blöcke:
  A  Flugprofil × Wind            (bps, langsam, wechsel, huepfer)
  B  Schubdrossel                 (f_min × Masse, Geschwindigkeit und Kennlinie der Pads)
  C  Stabilisierung               (Kardanbereich, Servo-Totzeit, Nullfehler, Reglerbandbreite, Vibration)
  D  Sensorik und Navigation      (GPS-Typ, Kamera, Laser, Kurs, Kalibrierung, Zielpunkt neben dem Start)
  E  Unsicherheitsbudget          (je eine Gruppe von Streuungen abgeschaltet)
  F  Erstflug Kartonaut 1         (nur Aufstieg: Windgrenze mit aerodynamischem Moment)
  G  Hebel für die Profile mit freiem Fall (Seitenfläche auf den Schwerpunkt legen)
  H  Zwei Motoren: Einbauvarianten (koaxial, nebeneinander, schräg, hintereinander mit Schublücke)

Modell und Annahmen: ``tvcsim/pinpoint.py``. Erfolg = aufgesetzt mit Sinkrate ≤ 3 m/s, seitlich ≤ 1 m/s,
Kippwinkel ≤ 10°, kein Wiederabheben, und im genannten Radius um den Zielpunkt.
Ausgabe: Tabellen, ``out/pinpoint_study.csv``, ``out/pinpoint_*.png``.
"""
import argparse
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import _path  # noqa: F401
from tvcsim.params import OUT_DIR
from tvcsim.pinpoint import GPS_PRESETS, profile, run, success, summarize, uncalibrated

WINDS = [0.0, 1.5, 3.0, 5.0]
BASE = "wechsel"       # Bezugsprofil für die Blöcke C, D, E
BASE_WIND = 3.0


def scenarios() -> list[tuple[str, str, str, dict]]:
    """(Block, Bezeichnung, Profil, Abweichungen von der Vorgabe)."""
    S = []
    for prof in ("bps", "langsam", "wechsel", "huepfer"):
        for w in WINDS:
            S.append(("A", f"{prof}, Wind {w:g} m/s", prof, dict(wind10=w)))
    for prof in ("wechsel", "huepfer"):
        for m in (0.6, 0.8, 1.0):
            for f in (0.2, 0.35, 0.5, 0.65, 0.8):
                S.append(("B", f"{prof}, {m:.1f} kg, f_min {f:g}", prof, dict(m_land=m, f_min=f, wind10=1.5)))
    for m in (0.6, 0.8):
        for f in (1.0, 0.5, 0.35):
            S.append(("B", f"bps, {m:.1f} kg, f_min {f:g}, windstill", "bps", dict(m_land=m, f_min=f, wind10=0.0)))
    for wn, dead in ((15.0, 0.03), (36.7, 0.03), (80.0, 0.03), (36.7, 0.08)):
        S.append(("B", f"{BASE}, Pads {wn:g} rad/s, Totzeit {dead * 1000:g} ms", BASE, dict(thr_wn=wn, thr_dead=dead, wind10=1.5)))
    b = dict(wind10=BASE_WIND)
    S.append(("C", "Bezug", BASE, dict(b)))
    for g in (3.0, 8.0, 12.0):
        S.append(("C", f"Kardan ±{g:g}°", BASE, dict(b, gim_max=g)))
    for d in (0.004, 0.03, 0.05, 0.08):
        S.append(("C", f"Servo-Totzeit {d * 1000:g} ms", BASE, dict(b, gim_dead_lo=d, gim_dead_hi=d)))
    for o in (0.2, 1.0, 2.0):
        S.append(("C", f"Nullfehler Kardan {o:g}°", BASE, dict(b, sig_gim_off=o)))
    for wn in (4.0, 11.0):
        S.append(("C", f"Lageregler {wn:g} rad/s", BASE, dict(b, att_wn=wn)))
    for vib in (1.0, 3.0):
        S.append(("C", f"Gyro-Vibration {vib:g} °/s", BASE, dict(b, gyro_vib=vib)))
    S.append(("C", "Servo-Rate 50 °/s am Kardan", BASE, dict(b, gim_rate=50.0, gim_slew=50.0)))
    for tl in (8.0, 25.0):
        S.append(("C", f"Kippgrenze Landung {tl:g}°", BASE, dict(b, tilt_max_land=tl)))
    S.append(("C", "Motoren nebeneinander (12,5 mm), Kardan ±5°", BASE, dict(b, motor_offset=0.0125)))
    S.append(("C", "Motoren nebeneinander (12,5 mm), Kardan ±12°", BASE, dict(b, motor_offset=0.0125, gim_max=12.0)))
    for ov in (0.2, 0.5, 0.7):
        S.append(("C", f"Überlappung {ov:g} s", BASE, dict(b, overlap=ov)))
    S.append(("C", "Kippgrenze Aufstieg 5°", BASE, dict(b, tilt_max_ascent=5.0)))

    def gps(kind, **kw):
        return dict(b, gps=kind, **GPS_PRESETS[kind], **kw)

    S.append(("D", "nur IMU und Barometer", BASE, gps("none")))
    S.append(("D", "GPS NEO-6M (5 Hz)", BASE, gps("neo6m")))
    S.append(("D", "GPS M10 (10 Hz)", BASE, gps("m10")))
    S.append(("D", "GPS RTK", BASE, gps("rtk")))
    S.append(("D", "Kamera, kein GPS", BASE, gps("none", cam=True)))
    S.append(("D", "Kamera und NEO-6M", BASE, gps("neo6m", cam=True)))
    S.append(("D", "Kamera und NEO-6M, Marke im Abgas verdeckt ab Motor 2", BASE, gps("neo6m", cam=True, cam_blind_burn=True)))
    S.append(("D", "NEO-6M und Laser-Höhe", BASE, gps("neo6m", lidar=True)))
    S.append(("D", "Kamera, NEO-6M und Laser-Höhe", BASE, gps("neo6m", cam=True, lidar=True)))
    S.append(("D", "ideale Sensoren", BASE, dict(b, noise=0.0)))
    S.append(("D", "NEO-6M, Sensoren unkalibriert", BASE, None))
    S.append(("D", "Kamera und NEO-6M, Sensoren unkalibriert", BASE, None))
    for h in (10.0, 30.0, 60.0):
        S.append(("D", f"NEO-6M, Kursfehler {h:g}° (1 σ)", BASE, gps("neo6m", mag_decl=h)))
    S.append(("D", "Kamera und NEO-6M, Kursfehler 30° (1 σ)", BASE, gps("neo6m", cam=True, mag_decl=30.0)))
    for ab in (0.3, 1.0):
        S.append(("D", f"NEO-6M, Beschleunigungs-Nullpunkt {ab:g} m/s²", BASE, gps("neo6m", acc_bias=ab)))
    for d in (2.0, 5.0, 10.0):
        S.append(("D", f"NEO-6M, Zielpunkt {d:g} m neben dem Start", BASE, gps("neo6m", target_e=d)))
    for prof in ("langsam", "huepfer"):
        S.append(("D", f"{prof}: nur IMU und Barometer", prof, gps("none")))
        S.append(("D", f"{prof}: NEO-6M", prof, gps("neo6m")))
        S.append(("D", f"{prof}: Kamera und NEO-6M", prof, gps("neo6m", cam=True)))
    S.append(("E", "alles an", BASE, dict(b)))
    S.append(("E", "ohne Wind", BASE, dict(b, wind10=0.0)))
    S.append(("E", "ohne Motorstreuung", BASE, dict(b, sc_motor=0.0)))
    S.append(("E", "ohne Stellgliedfehler", BASE, dict(b, sc_act=0.0)))
    S.append(("E", "ohne Massen- und Schwerpunktfehler", BASE, dict(b, sc_mass=0.0)))
    S.append(("E", "ohne Streuung der Aerodynamik", BASE, dict(b, sc_aero=0.0)))
    S.append(("E", "ideale Sensoren", BASE, dict(b, noise=0.0)))
    S.append(("E", "nur Wind (sonst alles nominal)", BASE, dict(b, scatter=0.0, noise=0.0)))
    S.append(("E", "alles nominal, windstill", BASE, dict(b, scatter=0.0, noise=0.0, wind10=0.0)))
    for w in (0.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
        S.append(("F", f"Erstflug, Wind {w:g} m/s", "erstflug", dict(wind10=w)))
    for w in (2.0, 3.0, 4.0, 5.0):
        S.append(("F", f"Erstflug, Wind {w:g} m/s, Kardan ±3,75°", "erstflug", dict(wind10=w, gim_max=3.75)))
    S.append(("F", "Erstflug, Wind 4 m/s, Kardan ±8°", "erstflug", dict(wind10=4.0, gim_max=8.0)))
    S.append(("F", "Erstflug, Wind 4 m/s, ohne aerodynamisches Moment", "erstflug", dict(wind10=4.0, cna_nose=0.0, cna_base=0.0,
                                                                                         cna_base_lo=0.0, cna_base_hi=0.0, z_cp_cross=0.26)))
    for prof in ("langsam", "bps"):
        S.append(("G", f"{prof}, Wind 3 m/s, wie gebaut", prof, dict(wind10=3.0)))
        S.append(("G", f"{prof}, Wind 3 m/s, Seitenfläche auf dem Schwerpunkt", prof, dict(wind10=3.0, z_cp_cross=0.27, sig_cp=0.01)))
        S.append(("G", f"{prof}, Wind 3 m/s, Seitenfläche 5 cm unter dem Schwerpunkt", prof, dict(wind10=3.0, z_cp_cross=0.22, sig_cp=0.01)))
    d = 0.0125
    for w in (1.5, 3.0):
        hw = dict(wind10=w)
        tag = f"Wind {w:g} m/s: "
        S.append(("H", tag + "Schubachsen auf der Kardanachse (Bezug)", BASE, dict(hw)))
        S.append(("H", tag + "nebeneinander, Kardan ±5°", BASE, dict(hw, motor_offset=d)))
        for g in (5.0, 8.0, 12.0):
            S.append(("H", tag + f"nebeneinander, Trimm vorgesteuert, Kardan ±{g:g}°", BASE, dict(hw, motor_offset=d, motor_ff=True, gim_max=g)))
        S.append(("H", tag + "nebeneinander, Trimm vorgesteuert, Kardan ±12°, Stellrate 300 °/s", BASE,
                  dict(hw, motor_offset=d, motor_ff=True, gim_max=12.0, gim_rate=300.0, gim_slew=200.0)))
        S.append(("H", tag + "nebeneinander, schräg durch den Schwerpunkt (3,6°), Kardan ±5°", BASE, dict(hw, motor_offset=d, motor_cant=True)))
        S.append(("H", tag + "nebeneinander, schräg durch den Schwerpunkt, Kardan ±8°", BASE, dict(hw, motor_offset=d, motor_cant=True, gim_max=8.0)))
        for gap in (0.0, 0.2):
            S.append(("H", tag + f"hintereinander, Zündung {gap:g} s nach Nenn-Brennschluss", BASE, dict(hw, overlap=-gap)))
        S.append(("H", tag + "hintereinander, Zündung 0 s nach Nenn-Brennschluss, Schweben in 9 m", BASE, dict(hw, overlap=0.0, h_apo=9.0)))
    return S


def _work(job):
    block, label, prof, kw, n, seed, keep = job
    if kw is None:      # die beiden "unkalibriert"-Fälle
        cfg = uncalibrated(profile(prof, wind10=BASE_WIND, cam="Kamera" in label))
    else:
        cfg = profile(prof, **kw)
    res = run(cfg, n=n, seed=seed, keep=keep)
    row = summarize(res)
    row.update(block=block, label=label, profile=prof)
    row["boost_lost"] = float(np.mean(res["tilt_boost"] > 30.0))
    extra = {}
    if block == "A":
        extra = {"x": res["x"], "y": res["y"], "ok": success(res, 1e9), "wind": cfg.wind10}
    if keep:
        extra["traj"] = res["traj"]; extra["ok_traj"] = success(res, 1e9)[:keep]
    return row, extra


def fmt(x, d=2):
    return "–" if not np.isfinite(x) else f"{x:.{d}f}".replace(".", ",")


def table(rows, cols, head):
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(c(r) if callable(c) else str(r[c]) for c in cols) + " |")
    print()


def pc(key):
    return lambda r: f"{100 * r[key]:.0f} %"


def pair(a, b, d=2):
    return lambda r: f"{fmt(r[a], d)} / {fmt(r[b], d)}"


LAND_COLS = (["label", pc("ok_1m"), pc("ok_2m"), pc("soft"), pair("miss_p50", "miss_p95"), pair("vz_p50", "vz_p95", 1),
              lambda r: fmt(r["vh_p95"], 1), lambda r: fmt(r["tilt_p95"], 0), pair("nav_p50", "nav_p95"),
              lambda r: f"{100 * r['sat_land']:.0f} %"],
             ["Szenario", "Erfolg ≤ 1 m", "≤ 2 m", "weich", "Ablage 50 / 95 % (m)", "Sinkrate 50 / 95 % (m/s)",
              "seitlich 95 % (m/s)", "Kipp 95 % (°)", "Navigationsfehler 50 / 95 % (m)", "Kardan am Anschlag"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blocks", nargs="+", default=list("ABCDEFGH"))
    ap.add_argument("--runs", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")       # Windows-Konsole: sonst scheitern ≤ und σ
    S = [s for s in scenarios() if s[0] in args.blocks]
    if args.list:
        for s in S:
            print(s[0], s[1])
        return
    jobs = [(b, lab, prof, kw, args.runs, args.seed, 40 if (b == "A" and abs((kw or {}).get("wind10", -1) - 3.0) < 1e-9) else 0)
            for b, lab, prof, kw in S]
    t0 = time.time()
    if args.workers > 1:
        with ProcessPoolExecutor(args.workers) as ex:
            results = list(ex.map(_work, jobs))
    else:
        results = [_work(j) for j in jobs]
    print(f"{len(jobs)} Szenarien × {args.runs} Läufe in {time.time() - t0:.0f} s\n")
    rows = [r for r, _ in results]
    OUT_DIR.mkdir(exist_ok=True)
    keys = ["block", "label", "profile"] + [k for k in rows[0] if k not in ("block", "label", "profile")]
    with open(OUT_DIR / "pinpoint_study.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)

    titles = {"A": "A. Flugprofil × Wind", "B": "B. Schubdrossel", "C": f"C. Stabilisierung (Profil {BASE}, Wind {BASE_WIND:g} m/s)",
              "D": f"D. Sensorik und Navigation (Profil {BASE}, Wind {BASE_WIND:g} m/s)",
              "E": f"E. Unsicherheitsbudget (Profil {BASE}, Wind {BASE_WIND:g} m/s)", "F": "F. Erstflug Kartonaut 1: Aufstieg im Wind",
              "G": "G. Freier Fall: Seitenfläche und Schwerpunkt",
              "H": f"H. Zwei Motoren: Einbauvarianten (Profil {BASE})"}
    for b in args.blocks:
        sel = [r for r in rows if r["block"] == b]
        if not sel:
            continue
        print(f"### {titles[b]}\n")
        if b == "F":
            table(sel, ["label", lambda r: fmt(r["apogee"], 0), lambda r: fmt(r["v_bo"], 0), lambda r: fmt(r["tilt_boost_p95"], 1),
                        pc("boost_lost")],
                  ["Szenario", "Gipfel (m)", "v Brennschluss (m/s)", "Kipp im Brennen 95 % (°)", "Läufe mit Kipp > 30°"])
        elif b in ("A", "G"):
            table(sel, ["label", lambda r: fmt(r["apogee"], 0), lambda r: fmt(r["tilt_boost_p95"], 0),
                        pair("tilt_ign_p50", "tilt_ign_p95", 0), pair("off_ign_p50", "off_ign_p95", 1)] + LAND_COLS[0][1:8],
                  ["Szenario", "Gipfel (m)", "Kipp im Aufstieg 95 % (°)", "Kipp bei Landezündung 50 / 95 % (°)",
                   "Ablage bei Landezündung 50 / 95 % (m)"] + LAND_COLS[1][1:8])
        elif b == "B":
            table(sel, ["label", pc("soft"), pair("vz_p50", "vz_p95", 1), pc("relift"), lambda r: fmt(r["apogee"], 0),
                        pair("miss_p50", "miss_p95"), lambda r: f"{100 * r['sat_land']:.0f} %"],
                  ["Szenario", "weich", "Sinkrate 50 / 95 % (m/s)", "hebt wieder ab", "Gipfel (m)", "Ablage 50 / 95 % (m)", "Kardan am Anschlag"])
        else:
            table(sel, *LAND_COLS)

    if not args.no_plots:
        plots(results, args)


def plots(results, args):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [r for r, _ in results]
    names = {"bps": "frei steigen, fallen, Landebrennen", "langsam": "gedrosselt auf 25 m, kurzer Fall",
             "wechsel": "Schweben in 6 m, Motorwechsel ohne Schublücke", "huepfer": "Hüpfer mit einem Motor (3 m)"}
    A = [(r, e) for r, e in results if r["block"] == "A"]
    if A:
        fig, axs = plt.subplots(2, 2, figsize=(11, 11), layout="constrained")
        fig.suptitle(f"Aufsetzpunkte relativ zum Ziel, Wind 3 m/s in 10 m Höhe, {args.runs} Läufe je Profil\n"
                     "grün: weich aufgesetzt (≤ 3 m/s senkrecht, ≤ 1 m/s seitlich, ≤ 10° Kipp), rot: nicht", fontsize=11)
        for ax, prof in zip(axs.flat, names):
            hit = [(r, e) for r, e in A if r["profile"] == prof and abs(e["wind"] - 3.0) < 1e-9]
            if not hit:
                continue
            r, e = hit[0]
            ok = e["ok"]
            ax.scatter(e["x"][~ok], e["y"][~ok], s=10, c="#c0392b", alpha=0.7, lw=0)
            ax.scatter(e["x"][ok], e["y"][ok], s=10, c="#1e8449", alpha=0.8, lw=0)
            lim = max(2.5, 1.15 * np.nanpercentile(np.hypot(e["x"], e["y"]), 97))
            th = np.linspace(0, 2 * np.pi, 200)
            for rad in (1, 2, 5, 10, 20, 40):
                if rad < lim:
                    ax.plot(rad * np.cos(th), rad * np.sin(th), color="0.6", lw=0.7)
                    ax.text(rad * 0.71, rad * 0.71, f"{rad} m", fontsize=7, color="0.4")
            ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_aspect("equal"); ax.grid(alpha=0.2)
            ax.set_title(f"{prof}: {names[prof]}\nErfolg im 1-m-Kreis {100 * r['ok_1m']:.0f} %, Ablage Median "
                         f"{fmt(r['miss_p50'])} m, 95 % {fmt(r['miss_p95'])} m", fontsize=9)
            ax.set_xlabel("Ost (m)"); ax.set_ylabel("Nord (m)")
        fig.savefig(OUT_DIR / "pinpoint_profiles.png", dpi=110)

        fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), layout="constrained")
        for prof in names:
            sel = [r for r, e in A if r["profile"] == prof]
            w = [e["wind"] for r, e in A if r["profile"] == prof]
            axs[0].plot(w, [100 * r["ok_1m"] for r in sel], "o-", label=prof)
            axs[1].plot(w, [r["miss_p95"] for r in sel], "o-", label=prof)
            axs[2].plot(w, [r["tilt_ign_p50"] if prof in ("bps", "langsam") else np.nan for r in sel], "o-", label=prof)
        axs[0].set_ylabel("Erfolg im 1-m-Kreis (%)"); axs[0].set_ylim(0, 102)
        axs[1].set_ylabel("Ablage, 95 % der Läufe (m)"); axs[1].set_yscale("log")
        axs[2].set_ylabel("Kippwinkel bei der Landezündung, Median (°)")
        for ax in axs:
            ax.set_xlabel("Wind in 10 m Höhe (m/s)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
        fig.suptitle("Punktlandung nach Flugprofil und Wind", fontsize=11)
        fig.savefig(OUT_DIR / "pinpoint_wind.png", dpi=110)

        tr = [(r, e) for r, e in A if "traj" in e and r["profile"] == BASE]
        if tr:
            r, e = tr[0]
            T = e["traj"]; ok = e["ok_traj"]
            fig, axs = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
            fig.suptitle(f"Profil {BASE} ({names[BASE]}), Wind 3 m/s: 40 Läufe (rot: nicht weich aufgesetzt)", fontsize=11)
            for i in range(T["p"].shape[1]):
                c = "#1e8449" if ok[i] else "#c0392b"
                last = np.nonzero(np.any(np.diff(T["p"][:, i], axis=0) != 0, axis=1))[0]
                k = (last[-1] + 2) if len(last) else len(T["t"])
                axs[0, 0].plot(T["t"][:k], T["p"][:k, i, 2], color=c, lw=0.7, alpha=0.7)
                axs[0, 1].plot(T["p"][:k, i, 0], T["p"][:k, i, 1], color=c, lw=0.7, alpha=0.7)
                axs[1, 0].plot(T["t"][:k], T["tilt"][:k, i], color=c, lw=0.6, alpha=0.6)
                axs[1, 1].plot(T["t"][:k], 1 - (1 - 0.35) * T["thr"][:k, i], color=c, lw=0.6, alpha=0.6)
            axs[0, 0].set_ylabel("Höhe (m)"); axs[0, 1].set_xlabel("Ost (m)"); axs[0, 1].set_ylabel("Nord (m)")
            axs[0, 1].set_aspect("equal"); axs[1, 0].set_ylabel("Kippwinkel (°)"); axs[1, 1].set_ylabel("Schubfaktor der Drossel (Nennkennlinie)")
            for ax in (axs[0, 0], axs[1, 0], axs[1, 1]):
                ax.set_xlabel("Zeit (s)")
            for ax in axs.flat:
                ax.grid(alpha=0.3)
            fig.savefig(OUT_DIR / "pinpoint_flight.png", dpi=110)

    B = [r for r in rows if r["block"] == "B" and "kg, f_min" in r["label"] and not r["label"].startswith("bps")]
    if B:
        fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained")
        for ax, prof in zip(axs, ("wechsel", "huepfer")):
            for m in ("0.6", "0.8", "1.0"):
                sel = [r for r in B if r["profile"] == prof and f"{m} kg" in r["label"]]
                f = [float(r["label"].split("f_min ")[1]) for r in sel]
                ax.plot(f, [100 * r["soft"] for r in sel], "o-", label=f"{m.replace('.', ',')} kg")
            ax.set_title(f"{prof}: {names[prof]}", fontsize=9)
            ax.set_xlabel("kleinster Schubfaktor der Drossel f_min"); ax.set_ylabel("weich aufgesetzt (%)")
            ax.set_ylim(0, 102); ax.grid(alpha=0.3); ax.legend(title="Masse")
        fig.suptitle("Welche Drosselspanne braucht die Landung? (Wind 1,5 m/s)", fontsize=11)
        fig.savefig(OUT_DIR / "pinpoint_throttle.png", dpi=110)

    D = [r for r in rows if r["block"] == "D" and ":" not in r["label"]]
    if D:
        fig, ax = plt.subplots(figsize=(11, 0.34 * len(D) + 1.6), layout="constrained")
        y = np.arange(len(D))[::-1]
        ax.barh(y, [r["miss_p95"] for r in D], color="#aec6e8", label="95 % der Läufe")
        ax.barh(y, [r["miss_p50"] for r in D], color="#1f5fa8", label="Median")
        for yy, r in zip(y, D):
            ax.text(r["miss_p95"] + 0.03, yy, f"Erfolg im 1-m-Kreis {100 * r['ok_1m']:.0f} %", va="center", fontsize=7)
        ax.set_yticks(y, [r["label"] for r in D], fontsize=8)
        ax.set_xlabel("Ablage vom Zielpunkt beim Aufsetzen (m)"); ax.grid(axis="x", alpha=0.3); ax.legend(fontsize=8)
        ax.set_title(f"Sensorik: Ablage beim Aufsetzen (Profil {BASE}, Wind {BASE_WIND:g} m/s)", fontsize=10)
        fig.savefig(OUT_DIR / "pinpoint_sensors.png", dpi=110)
    print("Bilder:", ", ".join(sorted(p.name for p in OUT_DIR.glob("pinpoint_*.png"))))


if __name__ == "__main__":
    main()
