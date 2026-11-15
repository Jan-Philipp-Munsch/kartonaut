"""Motorwechsel im Magazin, Schubluecke, Drosseltiefe gegen Masse, Massenbilanz der Landeversion.

    python scripts/motorwechsel_study.py            # rechnet alles, schreibt out/motorwechsel_*.png und .csv
    python scripts/motorwechsel_study.py --runs 150 # schneller

Vier Fragen:
  1. Wie schnell rutscht Motor 2 nach (tvcsim/motorswap.py)?
  2. Wie lang darf die Schubluecke beim Wechsel sein, und wie hoch muss die Rakete dafuer schweben (6DOF)?
  3. Welche Drosseltiefe braucht der Huepfer mit einem Motor bei welcher Masse (6DOF)?
  4. Was wiegt die Landeversion ohne Fallschirm?
"""
from __future__ import annotations

import argparse
import csv
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tvcsim.motorswap import swap_kinematics  # noqa: E402
from tvcsim.pinpoint import profile, run, success  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "out"
IGN_MEAN = 0.125          # s, mittlerer Zuendverzug im Modell (0,05 bis 0,20 s)
SWAPS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
HEIGHTS = (6.0, 7.5, 9.0)
WINDS = (1.5, 3.0)
MASSES = (0.75, 0.85, 0.95, 1.05)
FMINS = (0.35, 0.5, 0.65, 0.8)

# Massenbilanz in g; [Annahme] = noch nicht konstruiert oder gewogen
BASE = 546                # Stand 2c ohne Motor (640 g), ohne Fallschirm und CO2-Modul (94 g)
# Pads + 1 Servo: 26 g aus cad/throttle.py (vorher 60 g mit zwei Servos angenommen)
BUDGET = {
    "Kartonaut 1\n(Erstflug, Fallschirm)": [("Rakete ohne Bergung", BASE), ("Fallschirm + CO₂", 94), ("Motor(en)", 64)],
    "Hüpfer\n(ein Motor)": [("Rakete ohne Bergung", BASE), ("Motor(en)", 64), ("Pads + 1 Servo", 26), ("Beine + Antrieb", 90)],
    "Zwei Motoren\nim Magazin": [("Rakete ohne Bergung", BASE), ("Motor(en)", 128), ("Pads + 1 Servo", 26),
                                 ("Beine + Antrieb", 90), ("Magazin, Feder", 35)],
}
COLORS = {"Rakete ohne Bergung": "#9aa5b1", "Fallschirm + CO₂": "#e07a5f", "Motor(en)": "#c9a26b",
          "Pads + 1 Servo": "#3d5a80", "Beine + Antrieb": "#81b29a", "Magazin, Feder": "#f2cc8f"}


def _work(job):
    kind, kw, n, seed = job
    res = run(profile(kind, **kw), n=n, seed=seed)
    vz = np.abs(res["vz"])
    soft = res["landed"] & (vz <= res["cfg"].ok_vz)
    return dict(kind=kind, **kw, ok=float(success(res, 1.0).mean()), soft=float(soft.mean()),
                vz50=float(np.nanmedian(vz)), vz95=float(np.nanpercentile(vz, 95)),
                miss50=float(np.nanmedian(res["miss"])), miss95=float(np.nanpercentile(res["miss"], 95)),
                apogee=float(np.nanmedian(res["apogee"])))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(exist_ok=True)

    print("## 1. Nachrutschen von Motor 2 (Stapel 108 g, Weg 98 mm, Rakete im freien Fall)\n")
    print("| Federkraft (N) | Reibung (N) | Feder gewinnt bei (s) | Rutschzeit (s) | sitzt nach Brennschluss (s) | Aufprall (m/s) |")
    print("|---|---|---|---|---|---|")
    mech = []
    for mu in (0.5, 1.5):
        for f in (2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
            r = swap_kinematics(f, mu)
            mech.append((f, mu, r))
            print(f"| {f:g} | {mu:g} | {r.t_release:.2f} | {r.slide_time:.2f} | {r.swap_time:.2f} | {r.v_seat:.1f} |".replace(".", ","))

    jobs = [("wechsel", dict(wind10=w), args.runs, args.seed) for w in WINDS]
    jobs += [("wechsel", dict(wind10=w, h_apo=h, swap_time=s), args.runs, args.seed) for w in WINDS for h in HEIGHTS for s in SWAPS]
    jobs += [("huepfer", dict(wind10=1.5, m_land=m, f_min=f), args.runs, args.seed) for m in MASSES for f in FMINS]
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(_work, jobs))
    keys = sorted({k for r in rows for k in r})
    with open(OUT_DIR / "motorwechsel_study.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader(); wr.writerows(rows)

    ref = {r["wind10"]: r for r in rows if r["kind"] == "wechsel" and "swap_time" not in r}
    gap = {(r["wind10"], r["h_apo"], r["swap_time"]): r for r in rows if "swap_time" in r}
    hop = {(r["m_land"], r["f_min"]): r for r in rows if r["kind"] == "huepfer"}

    print("\n## 2. Schublücke beim Motorwechsel (Erfolg im 1-m-Kreis / weich aufgesetzt)\n")
    for w in WINDS:
        print(f"Wind {w:g} m/s; ohne Lücke (Motor 2 zündet 0,35 s vor Brennschluss, 6 m): "
              f"{100 * ref[w]['ok']:.0f} % / {100 * ref[w]['soft']:.0f} %\n")
        print("| mittlere Schublücke (s) | " + " | ".join(f"Schweben in {h:g} m" for h in HEIGHTS) + " |")
        print("|---|" + "---|" * len(HEIGHTS))
        for s in SWAPS:
            print(f"| {1.1 * s + IGN_MEAN:.2f} | ".replace(".", ",")
                  + " | ".join(f"{100 * gap[w, h, s]['ok']:.0f} % / {100 * gap[w, h, s]['soft']:.0f} %" for h in HEIGHTS) + " |")
        print()

    print("## 3. Hüpfer mit einem Motor: weich aufgesetzt je nach Masse und Drosseltiefe (Wind 1,5 m/s)\n")
    print("| Landemasse (kg) | " + " | ".join(f"f_min {f:g}" for f in FMINS) + " |")
    print("|---|" + "---|" * len(FMINS))
    for m in MASSES:
        print(f"| {m:g} | " + " | ".join(f"{100 * hop[m, f]['soft']:.0f} % ({hop[m, f]['vz50']:.1f} m/s)" for f in FMINS) + " |")

    print("\n## 4. Massenbilanz am Start (g)\n")
    for name, parts in BUDGET.items():
        print(f"- {name.replace(chr(10), ' ')}: {sum(v for _, v in parts)} g  (" + ", ".join(f"{k} {v}" for k, v in parts) + ")")

    if not args.no_plots:
        plots(mech, ref, gap, hop)


def _motor(ax, x0, y0, full=True, w=2.6, h=9.5):
    from matplotlib.patches import Rectangle, Polygon
    ax.add_patch(Rectangle((x0, y0), w, h, fc="#d8b98a", ec="k", lw=1.0, zorder=3))
    if full:
        ax.add_patch(Rectangle((x0 + 0.45, y0 + 1.3), w - 0.9, h - 2.1, fc="#4a4a4a", ec="none", zorder=4))
    ax.add_patch(Polygon([(x0 + 0.9, y0), (x0 + w - 0.9, y0), (x0 + w - 1.15, y0 + 1.0), (x0 + 1.15, y0 + 1.0)],
                         fc="white", ec="k", lw=0.8, zorder=5))


def _flame(ax, xc, y0):
    from matplotlib.patches import Polygon
    ax.add_patch(Polygon([(xc - 0.7, y0), (xc + 0.7, y0), (xc, y0 - 4.5)], fc="#f4a259", ec="#e76f51", lw=1.0, zorder=2))


def _spring(ax, xc, y0, y1, n=9):
    ys = np.linspace(y0, y1, 2 * n + 1)
    xs = xc + 1.0 * np.array([0] + [(-1) ** k for k in range(2 * n - 1)] + [0])
    ax.plot(xs, ys, color="#2a6f97", lw=1.6, zorder=3)


def _panel(ax, step):
    from matplotlib.patches import Rectangle, Polygon
    xl, xr, top, bot = 3.55, 6.45, 29.0, 2.5
    for x in (xl - 0.35, xr):
        ax.add_patch(Rectangle((x, bot), 0.35, top - bot, fc="#b0b7bf", ec="k", lw=0.8, zorder=1))
    ax.add_patch(Rectangle((xl - 0.35, top), xr - xl + 0.7, 0.4, fc="#b0b7bf", ec="k", lw=0.8))
    # Anschlag oben (nimmt den Schub von Motor 1 auf)
    for x in (xl, xr - 0.5):
        ax.add_patch(Rectangle((x, 22.75), 0.5, 0.35, fc="k", zorder=6))
    # Pads
    for x in (1.9, 7.0):
        ax.add_patch(Rectangle((x, 0.3), 1.1, 0.7, fc="#3d5a80", ec="k", lw=0.6, zorder=6))
    lift = 0.3 if step == 1 else 0.0
    if step in (0, 1):
        y1 = 2.0 + lift
        _motor(ax, 3.7, y1, full=(step == 0))
        if step == 1:
            ax.add_patch(Rectangle((4.15, y1 + 5.7), 1.7, 3.0, fc="#4a4a4a", ec="none", zorder=4))
        ax.add_patch(Rectangle((3.7, y1 + 9.5), 2.6, 0.45, fc="#6c757d", ec="k", lw=0.6, zorder=5))      # Hitzeschild
        _motor(ax, 3.7, y1 + 9.95)
        yp = y1 + 19.45
    elif step == 2:
        _motor(ax, 3.7, -7.5, full=False)
        ax.add_patch(Rectangle((3.7, 2.0), 2.6, 0.45, fc="#6c757d", ec="k", lw=0.6, zorder=5))
        _motor(ax, 3.7, 6.5)
        yp = 16.0
    else:
        _motor(ax, 3.7, 2.0)
        yp = 11.5
    ax.add_patch(Rectangle((xl, yp), xr - xl, 0.8, fc="#2a6f97", ec="k", lw=0.8, zorder=6))               # Kolben
    _spring(ax, 5.0, yp + 0.8, top)
    # Riegel unten
    if step == 0:
        ax.add_patch(Polygon([(xl - 0.35, 2.5), (xl - 0.35, 1.6), (4.3, 1.6), (4.3, 2.0), (xl, 2.0), (xl, 2.5)], fc="#bc4749", ec="k", lw=0.8, zorder=7))
    else:
        ax.add_patch(Polygon([(xl - 0.35, 2.5), (xl - 1.5, 1.5), (xl - 1.2, 1.2), (xl, 2.2)], fc="#bc4749", ec="k", lw=0.8, zorder=7))
    # Sperrklinken in Brennstellung
    for x, s in ((xl, 1), (xr, -1)):
        if step == 3:
            ax.add_patch(Polygon([(x, 13.4), (x + s * 0.7, 12.35), (x, 12.35)], fc="#6a994e", ec="k", lw=0.8, zorder=7))
    if step == 1:
        _flame(ax, 5.0, 2.3)
        ax.annotate("", (8.3, 16), (8.3, 12), arrowprops=dict(arrowstyle="-|>", color="#e76f51", lw=2))
        ax.text(8.6, 14, "Schub 11 N\n> Feder 5 N", fontsize=8, va="center")
    if step == 2:
        ax.annotate("", (8.3, 8), (8.3, 12), arrowprops=dict(arrowstyle="-|>", color="#2a6f97", lw=2))
        ax.text(8.6, 10, "Feder\nschiebt", fontsize=8, va="center")
    if step == 3:
        _flame(ax, 5.0, 2.0)
        ax.text(8.0, 12.6, "Klinken halten\nden Schub", fontsize=8, va="center")
        ax.plot([xr + 0.35, 7.8], [12.8, 12.8], color="k", lw=0.6)
    if step == 0:
        ax.text(-0.3, 2.6, "Riegel zu", fontsize=8, color="#bc4749", va="center")
        ax.text(7.2, 11.9, "Hitzeschild", fontsize=8, va="center"); ax.plot([6.3, 7.1], [11.7, 11.9], color="k", lw=0.6)
        ax.text(7.2, 25.5, "Feder", fontsize=8, color="#2a6f97", va="center")
        ax.text(7.2, 22.9, "Anschlag", fontsize=8, va="center")
        ax.text(8.3, 0.6, "Pads", fontsize=8, color="#3d5a80", va="center")
        ax.text(5.0, 6.8, "1", color="w", fontsize=13, ha="center", va="center", zorder=9, weight="bold")
        ax.text(5.0, 16.8, "2", color="w", fontsize=13, ha="center", va="center", zorder=9, weight="bold")
    ax.set_xlim(0, 11.5); ax.set_ylim(-8.5, 30.5); ax.set_aspect("equal"); ax.axis("off")


def plots(mech, ref, gap, hop):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ---- Bild 1: Prinzip und Zeitablauf ----
    fig = plt.figure(figsize=(13, 8.2), layout="constrained")
    gs = fig.add_gridspec(2, 4, height_ratios=[4.2, 1.0])
    titles = ["1  Vor dem Start\nFeder gespannt, Riegel hält den Stapel",
              "2  Motor 1 brennt\nSchub hebt den Stapel 3 mm an den\nAnschlag, der Riegel springt auf",
              "3  Brennschluss\nFeder wirft die Hülse aus,\nMotor 2 rutscht nach (0,1 s)",
              "4  Motor 2 sitzt\nKlinken rasten ein, Kontakt schließt,\nder Anzünder zündet"]
    for k in range(4):
        ax = fig.add_subplot(gs[0, k])
        _panel(ax, k)
        ax.set_title(titles[k], fontsize=10)
    ax = fig.add_subplot(gs[1, :])
    r = swap_kinematics(5.0, 1.0)
    t0 = r.t_burnout
    segs = [("Schub fällt unter die Federkraft", r.t_release - t0, r.t_burnout - t0, "#f4a259"),
            ("Motor 2 rutscht nach", r.t_release - t0, r.t_seated - t0, "#2a6f97"),
            ("Zündverzug des Anzünders (0,05 bis 0,2 s angenommen, nicht gemessen)", r.t_seated - t0, r.t_seated - t0 + 0.2, "#bc4749")]
    for i, (lab, a, b, c) in enumerate(segs):
        ax.barh(2 - i, b - a, left=a, color=c, height=0.6)
        ax.text(b + 0.008, 2 - i, lab, va="center", fontsize=9)
    ax.axvspan(0.0, r.t_seated - t0 + 0.05, color="k", alpha=0.07)
    ax.axvline(0.0, color="k", lw=0.8)
    ax.set_yticks([]); ax.set_xlim(-0.1, 0.62); ax.set_xlabel("Zeit nach dem Brennschluss von Motor 1 (s); grau: Schublücke im günstigen Fall")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    fig.suptitle("Motorwechsel im Magazin: zwei Motoren hintereinander, Feder 5 N", fontsize=12)
    fig.savefig(OUT_DIR / "motorwechsel_konzept.png", dpi=110)
    plt.close(fig)

    # ---- Bild 2: Rutschzeit und erlaubte Schubluecke ----
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), layout="constrained")
    ax = axs[0]
    for mu, ls in ((0.5, "-"), (1.5, "--")):
        sel = [(f, r) for f, m, r in mech if m == mu]
        ax.plot([f for f, _ in sel], [r.slide_time for _, r in sel], "o" + ls, color="#2a6f97", label=f"Rutschzeit, Reibung {mu:g} N".replace(".", ","))
        ax.plot([f for f, _ in sel], [max(r.swap_time, 0.0) for _, r in sel], "s" + ls, color="#bc4749",
                label=f"sitzt nach Brennschluss, Reibung {mu:g} N".replace(".", ","))
    ax.set_xlabel("Federkraft (N)"); ax.set_ylabel("Zeit (s)"); ax.set_title("Wie schnell rutscht Motor 2 nach?")
    ax.set_ylim(0, 0.3); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    cols = {6.0: "#e76f51", 7.5: "#e9c46a", 9.0: "#2a9d8f"}
    for ax, w in zip(axs[1:], WINDS):
        x = [1.1 * s + IGN_MEAN for s in SWAPS]
        for h in HEIGHTS:
            ax.plot(x, [100 * gap[w, h, s]["ok"] for s in SWAPS], "o-", color=cols[h], label=f"Schweben in {h:g} m: im 1-m-Kreis".replace(".", ","))
            ax.plot(x, [100 * gap[w, h, s]["soft"] for s in SWAPS], ":", color=cols[h], label="   nur weich aufgesetzt")
        ax.axhline(100 * ref[w]["ok"], color="k", lw=0.8, ls="--")
        ax.text(0.66, 100 * ref[w]["ok"] + 1.5, "ohne Lücke", fontsize=8, ha="right")
        ax.axvspan(0.15, 0.35, color="k", alpha=0.07)
        ax.text(0.25, 45, "Magazin\nerwartet", fontsize=8, ha="center")
        ax.set_xlabel("mittlere Schublücke (s)"); ax.set_ylim(0, 102); ax.set_xlim(0.1, 0.7); ax.grid(alpha=0.3)
        ax.set_title(f"Erfolg bei Wind {w:g} m/s".replace(".", ","))
    axs[1].set_ylabel("Anteil der Flüge (%)"); axs[1].legend(fontsize=7.5, loc="lower left")
    fig.savefig(OUT_DIR / "motorwechsel_luecke.png", dpi=110)
    plt.close(fig)

    # ---- Bild 3: Drosseltiefe gegen Masse, Massenbilanz ----
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), layout="constrained")
    ax = axs[0]
    z = np.array([[100 * hop[m, f]["soft"] for f in FMINS] for m in MASSES])
    im = ax.imshow(z, cmap="RdYlGn", vmin=0, vmax=100, origin="lower", aspect="auto")
    for i, m in enumerate(MASSES):
        for j, f in enumerate(FMINS):
            ax.text(j, i, f"{z[i, j]:.0f} %", ha="center", va="center", fontsize=11)
    ax.set_xticks(range(len(FMINS)), [f"{f:g}\n({11.4 * f:.0f} N)".replace(".", ",") for f in FMINS])
    ax.set_yticks(range(len(MASSES)), [f"{m:g}".replace(".", ",") for m in MASSES])
    ax.set_xlabel("kleinster Schubfaktor f_min der Pads (Restschub im Plateau)"); ax.set_ylabel("Landemasse (kg)")
    ax.set_title("Hüpfer mit einem Motor: Anteil weicher Landungen (≤ 3 m/s)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax = axs[1]
    for i, (name, parts) in enumerate(BUDGET.items()):
        left = 0
        for k, v in parts:
            ax.barh(i, v, left=left, color=COLORS[k], edgecolor="w", label=k)
            if v >= 55:
                ax.text(left + v / 2, i, str(v), ha="center", va="center", fontsize=9)
            left += v
        ax.text(left + 8, i, f"{left} g", va="center", fontsize=10, weight="bold")
    hs, ls = ax.get_legend_handles_labels()
    uniq = dict(zip(ls, hs))
    ax.legend(uniq.values(), uniq.keys(), fontsize=8, loc="center right")
    ax.set_yticks(range(len(BUDGET)), list(BUDGET)); ax.invert_yaxis(); ax.set_xlim(0, 1350)
    ax.set_xlabel("Startmasse (g); Drossel aus dem CAD, Beine und Magazin sind Annahmen"); ax.set_title("Ohne Fallschirm und CO₂ werden 94 g frei")
    ax.grid(axis="x", alpha=0.3)
    fig.savefig(OUT_DIR / "motorwechsel_drossel_masse.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
