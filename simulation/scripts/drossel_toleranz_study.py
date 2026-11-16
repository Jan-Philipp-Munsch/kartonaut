"""Wie viel Querablenkung des Schubs durch ungleiches Abblocken verträgt die Landung? Dazu drei Bauformen der Drossel.

    python scripts/drossel_toleranz_study.py        # 1 Minute, schreibt out/drossel_toleranz.png und .csv

Die Simulation (tvcsim/pinpoint.py) lenkt den Schub proportional zur Drosselstellung um einen Winkel ab, der je Lauf
und Achse normalverteilt gezogen wird (sig_pad_side, Grad bei voll eingeschwenkten Pads). Hier wird dieser Wert von
0 bis 8° durchgefahren. Der Zusammenhang zwischen Kantenfehler und Ablenkung ist eine Abschätzung (siehe unten),
gemessen wird er in Versuch E05.
"""
from __future__ import annotations

import csv
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tvcsim.pinpoint import profile, run, success  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[1] / "out"
SIGMAS = (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0)
CASES = (("huepfer", 1.5), ("huepfer", 3.0), ("wechsel", 1.5), ("wechsel", 3.0))
JET_R = 5.5          # mm, Strahlradius in der Pad-Ebene
LEVER = 190.0        # mm, Düse bis Schwerpunkt


def edge_error_to_deg(eps_mm: float, tab_gain: float) -> float:
    """Schubablenkung (Grad, bezogen auf den Restschub bei halb abgedecktem Strahl) für einen Kantenfehler eps.

    Zwei Anteile: (1) der Restschub greift um etwa eps neben der Achse an (Moment wie eine Ablenkung eps / Hebel);
    (2) Strahlruder-Effekt: sitzt die Kante dicht an der Düse, staut sie den Strahl einseitig, und die Düsenwand
    bekommt eine Querkraft von etwa tab_gain × der einseitig mehr abgedeckten Schubanteil. tab_gain = 0 heißt
    freier Strahl auf eine ebene Platte (nur Axialkraft), 1 heißt Platte dicht an der Düse [Annahme].
    """
    offset = math.degrees(eps_mm / LEVER)
    d_frac = 2.0 * (2.0 * JET_R) / (math.pi * JET_R ** 2) * eps_mm      # Unterschied der abgedeckten Anteile beider Seiten
    return offset + math.degrees(math.atan(tab_gain * d_frac / 0.5))    # bezogen auf 50 % Restschub


def _work(job):
    kind, wind, sig, n = job
    res = run(profile(kind, wind10=wind, sig_pad_side=sig), n=n, seed=0)
    vz = np.abs(res["vz"])
    return dict(kind=kind, wind=wind, sig=sig, ok=float(success(res, 1.0).mean()),
                soft=float((res["landed"] & (vz <= res["cfg"].ok_vz)).mean()),
                miss50=float(np.nanmedian(res["miss"])), miss95=float(np.nanpercentile(res["miss"], 95)),
                tilt95=float(np.nanpercentile(res["tilt"], 95)), sat=float(np.nanmean(res["sat_land"])))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(sys.argv[sys.argv.index("--runs") + 1]) if "--runs" in sys.argv else 300
    OUT_DIR.mkdir(exist_ok=True)
    jobs = [(k, w, s, n) for k, w in CASES for s in SIGMAS]
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(_work, jobs))
    with open(OUT_DIR / "drossel_toleranz.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader(); wr.writerows(rows)
    R = {(r["kind"], r["wind"], r["sig"]): r for r in rows}
    print("## Erfolg im 1-m-Kreis je nach Querablenkung bei voller Drosselung (1 σ je Achse)\n")
    print("| Ablenkung | " + " | ".join(f"{k}, Wind {w:g} m/s" for k, w in CASES) + " |")
    print("|---|" + "---|" * len(CASES))
    for s in SIGMAS:
        print(f"| {s:g}° | " + " | ".join(f"{100 * R[k, w, s]['ok']:.0f} % (Ablage 95 %: {R[k, w, s]['miss95']:.1f} m)" for k, w in CASES) + " |")
    print("\n## Kantenfehler → Ablenkung (Abschätzung)\n")
    print("| Kantenfehler | freier Strahl, ebene Platte | Platte dicht an der Düse (Strahlruder-Effekt halb / voll) |")
    print("|---|---|---|")
    for eps in (0.2, 0.5, 1.0):
        print(f"| {eps:g} mm | {edge_error_to_deg(eps, 0):.2f}° | {edge_error_to_deg(eps, 0.5):.1f}° / {edge_error_to_deg(eps, 1.0):.1f}° |")
    plot(R)


def plot(R):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Polygon, Rectangle, Wedge

    fig = plt.figure(figsize=(15, 8.6), layout="constrained")
    gs = fig.add_gridspec(2, 4, height_ratios=[1.0, 1.05])
    jet = dict(fc="#f4a259", ec="#e76f51", lw=1.2, alpha=0.85)

    def base(ax, title):
        ax.add_patch(Circle((0, 0), 12, fc="#ead9bd", ec="#8d6e4a", lw=0.8, zorder=0))
        ax.set_xlim(-34, 34); ax.set_ylim(-34, 34); ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(title, fontsize=10)

    # A Scherenpads mit Gestänge (Stand 15.11.)
    ax = fig.add_subplot(gs[0, 0]); base(ax, "A  Zwei Pads mit Koppelstange\n(Stand 15.11.)")
    ax.add_patch(Rectangle((-9, 1.2), 18, 13, fc="#bc4749", ec="k", lw=0.8)); ax.add_patch(Rectangle((-9, -15.5), 18, 13, fc="#e07a5f", ec="k", lw=0.8))
    ax.add_patch(Circle((0, 0), 5.5, zorder=0.5, **jet))
    for x in (-20, 20):
        ax.plot(x, 0, "o", color="k", ms=6)
    ax.plot([20, 9], [0, 3], color="#666", lw=4); ax.plot([-20, -9], [0, -3], color="#666", lw=4)
    ax.add_patch(Wedge((0, -8), 23, 180, 360, width=5, fc="#777", ec="k", lw=0.6, alpha=0.5))
    ax.annotate("Kanten ungleich:\nSpiel in 4 Gelenken", (0, 0.2), (2, 24), fontsize=8, ha="center", arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(0, -33, "Symmetrie hängt am Gestänge.\nPads 1,5 mm unter der Düse: wirken wie Strahlruder.", ha="center", fontsize=8, color="#bc4749")

    # B Schlitzscheibe
    ax = fig.add_subplot(gs[0, 1]); base(ax, "B  Schlitzscheibe: ein Teil,\nkeilförmiger Schlitz")
    piv = (0.0, -22.0)
    th = np.radians(np.linspace(40, 140, 80))
    outer = [(piv[0] + 34 * math.cos(t), piv[1] + 34 * math.sin(t)) for t in th]
    inner = [(piv[0] + 10 * math.cos(t), piv[1] + 10 * math.sin(t)) for t in th[::-1]]
    ax.add_patch(Polygon(outer + inner, fc="#8f8f8f", ec="k", lw=0.8))
    ts = np.radians(np.linspace(52, 128, 60))
    hw = np.interp(np.degrees(ts), [52, 128], [1.5, 7.5])          # halbe Schlitzbreite, keilförmig
    slot = [(piv[0] + (22 + h) * math.cos(t), piv[1] + (22 + h) * math.sin(t)) for t, h in zip(ts, hw)] + \
           [(piv[0] + (22 - h) * math.cos(t), piv[1] + (22 - h) * math.sin(t)) for t, h in zip(ts[::-1], hw[::-1])]
    ax.add_patch(Polygon(slot, fc="w", ec="k", lw=0.8))
    ax.add_patch(Circle((0, 0), 5.5, zorder=0.5, **jet)); ax.add_patch(Circle((0, 0), 5.5, fill=False, ec="#e76f51", lw=1.0, ls=":"))
    ax.plot(*piv, "o", color="k", ms=6)
    ax.annotate("", (-17, 3), (-9, 9.5), arrowprops=dict(arrowstyle="<->", lw=1.2, connectionstyle="arc3,rad=0.25"))
    ax.text(-25, 12, "drehen =\ndrosseln", fontsize=8, ha="center")
    ax.text(0, -33, "Beide Kanten in einem Blech: Spiel im Gestänge ändert nur\ndie Stärke. Es bleibt, wie mittig die Düse sitzt.", ha="center", fontsize=8, color="#2a7f62")

    # C Lochscheibe (rotationssymmetrisch, in Stufen)
    ax = fig.add_subplot(gs[0, 2]); base(ax, "C  Lochscheibe: runde Blenden\nin Stufen (Revolver)")
    ax.add_patch(Polygon(outer + inner, fc="#8f8f8f", ec="k", lw=0.8))
    for ang, r in ((58, 7.5), (78, 5.0), (96, 4.0), (112, 3.2), (126, 2.5)):
        c = (piv[0] + 22 * math.cos(math.radians(ang)), piv[1] + 22 * math.sin(math.radians(ang)))
        ax.add_patch(Circle(c, r, fc="w", ec="k", lw=0.8))
    ax.add_patch(Circle((0, 0), 5.5, zorder=0.5, **jet)); ax.add_patch(Circle((0, 0), 5.5, fill=False, ec="#e76f51", lw=1.0, ls=":"))
    ax.plot(*piv, "o", color="k", ms=6)
    ax.text(0, -33, "Rundum gleich, aber nur Stufen, und beim\nWeiterdrehen fährt ein Steg durch den Strahl.", ha="center", fontsize=8, color="#555")

    # D Irisblende
    ax = fig.add_subplot(gs[0, 3]); base(ax, "D  Irisblende (Optik)")
    for k in range(8):
        a = k * 45
        ax.add_patch(Wedge((0, 0), 20, a + 8, a + 80, width=14.5, fc="#3a3a3a", ec="#aaa", lw=0.6, alpha=0.8))
    ax.add_patch(Circle((0, 0), 20, fill=False, ec="k", lw=1.2)); ax.add_patch(Circle((0, 0), 5.5, zorder=3, **jet))
    ax.text(0, -33, "Ideal symmetrisch, aber Lamellen 0,1 mm:\nglühen in Zehntelsekunden durch, Schlacke verklebt sie.", ha="center", fontsize=8, color="#bc4749")

    # unten links: Ergebnis der Simulation
    ax = fig.add_subplot(gs[1, :2])
    cols = {("huepfer", 1.5): ("#2a6f97", "-"), ("huepfer", 3.0): ("#2a6f97", "--"), ("wechsel", 1.5): ("#bc4749", "-"), ("wechsel", 3.0): ("#bc4749", "--")}
    names = {"huepfer": "Hüpfer", "wechsel": "Zwei Motoren"}
    for (k, w), (c, ls) in cols.items():
        ax.plot(SIGMAS, [100 * R[k, w, s]["ok"] for s in SIGMAS], "o" + ls, color=c, label=f"{names[k]}, Wind {w:g} m/s".replace(".", ","))
    ax.axvspan(0, 1.0, color="#2a9d8f", alpha=0.12); ax.text(0.5, 40, "bisher\nangenommen", ha="center", fontsize=8)
    ax.set_xlabel("Querablenkung des Schubs bei voller Drosselung (°, 1 σ je Achse, von Flug zu Flug zufällig)")
    ax.set_ylabel("Landungen im 1-m-Kreis (%)"); ax.set_ylim(0, 102); ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="upper right")
    ax.set_title("Was die Landung verträgt (6DOF, 300 Flüge je Punkt)", fontsize=10)

    # unten rechts: Kantenfehler -> Ablenkung
    ax = fig.add_subplot(gs[1, 2:])
    eps = np.linspace(0, 1.2, 50)
    ax.plot(eps, [edge_error_to_deg(x, 1.0) for x in eps], color="#bc4749", lw=2, label="Platte dicht an der Düse (Strahlruder-Effekt voll)")
    ax.plot(eps, [edge_error_to_deg(x, 0.5) for x in eps], color="#e9a23b", lw=2, label="halb")
    ax.plot(eps, [edge_error_to_deg(x, 0.0) for x in eps], color="#2a7f62", lw=2, label="freier Strahl auf ebene Platte (nur Versatz)")
    ax.axvspan(0.5, 1.0, color="k", alpha=0.07); ax.text(0.75, 13.2, "A zusätzlich:\nSpiel im Gestänge", ha="center", fontsize=8)
    ax.axvspan(0.2, 0.5, color="#2a9d8f", alpha=0.15); ax.text(0.35, 13.2, "alle Bauformen:\nDüse außermittig", ha="center", fontsize=8)
    ax.set_xlabel("Unterschied der beiden Kanten zur Düsenachse (mm)"); ax.set_ylabel("Querablenkung des Restschubs (°)")
    ax.set_ylim(0, 15); ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="center right")
    ax.set_title("Was ein Kantenfehler ausmacht (Abschätzung bei halb abgedecktem Strahl, nicht gemessen)", fontsize=10)
    fig.savefig(OUT_DIR / "drossel_toleranz.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
