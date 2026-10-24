"""Reglervergleich im Parameterraum: Wie viel Fehler in Fahrzeug und Servo vertraegt jeder Regler?

Alle Regler sind fest auf das CAD-Fahrzeug (I quer 0,11 kg m2, l 0,372 m) und den SG90-Servofit
(wn 36,7 rad/s, zeta 0,60, Totzeit 30 ms) ausgelegt; variiert werden die *wahren* Parameter der
Strecke. Drei Sichten:

1. **Lineare Stabilitaetskarten** (``tvcsim.linear``): Abklingrate des langsamsten Pols ueber
   Verstaerkungsfehler kappa und Totzeit sowie ueber Servobandbreite und kappa; dazu die
   klassischen Reserven (Verstaerkung nach oben/unten, Totzeit) je Regler.
2. **Sweeps im 6DOF-Modell**: je ein Parameter ueber seinen plausiblen Bereich (Traegheit,
   Hebelarm, Schub, Totzeit, Servobandbreite, Servoverstaerkung, statischer Fehler,
   Gyro-Rauschen), Kennzahlen Kippwinkel in der Brennphase und Saettigungsanteil.
3. **Monte-Carlo** mit breiter Streuung aller Parameter zugleich.

Rechnet ohne Boden (``ground=False``), damit ein Schub unter dem Gewicht nicht die
Lagedynamik ausblendet; Beschleunigungssensor als spezifische Kraft, ein Motor, Rauschen an,
statischer Servofehler 1 / 0,6 Grad als Grundlast. Ausgaben in out/robustness_*.png,
out/robustness_summary.md und out/robustness_results.json.

    python scripts/robustness.py            # alles, etwa 15 min auf 4 Kernen
    python scripts/robustness.py --quick    # grobe Raster zum Ausprobieren
    python scripts/robustness.py --skip-mc --skip-sweeps   # nur die lineare Analyse
"""
import argparse
import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import _path  # noqa: F401
from tvcsim.controller import design_plant, design_weights, model_pd_params  # noqa: E402
from tvcsim.linear import (RAD, AxisPlant, closed_loop, control_params_to_gains, decay_rate, delay_margin,  # noqa: E402
                           design_lqr, gain_margin, gain_margin_low, lqr_lti, pid_lti)
from tvcsim.params import (FirmwareParams, LQRParams, MotorParams, NoiseParams, OUT_DIR, ServoParams,  # noqa: E402
                           SimParams, VehicleParams)
from tvcsim.sim import simulate  # noqa: E402

BURNOUT = 3.55
CAD = VehicleParams.cad()
I_CAD, L_CAD = CAD.Iy, CAD.l
M_LIFTOFF = CAD.m_dry + 0.060          # kg, Signal-Builder-Treibstoff beim Start
BELIEF = LQRParams(I_ctrl=I_CAD, servo_wn=36.7, servo_zeta=0.598, servo_tau=0.030, T_design=11.0)
FW_CONFIG = FirmwareParams()
FW_FIXED = FirmwareParams(MASS_KG=0.98, MOMENT_ARM_M=L_CAD, SERVO_YAW_GAIN=-6.0, SERVO_PITCH_GAIN=6.0)
KAPPA_FW = L_CAD * M_LIFTOFF / (FW_CONFIG.MOMENT_ARM_M * FW_CONFIG.MASS_KG)   # Fehler der Modellinversion
KAPPA_FW_FIXED = L_CAD * M_LIFTOFF / (FW_FIXED.MOMENT_ARM_M * FW_FIXED.MASS_KG)

CONTROLLERS = [
    ("Firmware (Config.h)", dict(controller="firmware", firmware=FW_CONFIG)),
    ("Firmware, m/l/Gain korrigiert", dict(controller="firmware", firmware=FW_FIXED)),
    ("PD modellbasiert", dict(controller="pd_model")),
    ("LQR (Servozustand)", dict(controller="lqr")),
    ("LQI (LQR + Integral)", dict(controller="lqi")),
]
COLORS = ["0.45", "#d62728", "#1f77b4", "#2ca02c", "#9467bd"]
OK_TILT_MAX, OK_TILT_BURNOUT = 10.0, 5.0


def base_params(seed: int = 0) -> SimParams:
    veh = replace(CAD, l_meas=L_CAD, static_error_y=1.0, static_error_z=0.6)
    return SimParams(vehicle=veh, noise=NoiseParams(enabled=True, accel_model="specific_force"),
                     motor=MotorParams(second_motor=False), t_end=4.0, seed=seed, ground=False, lqr=BELIEF)


def metrics(res, sat_deg: float) -> dict:
    burn = res.t <= BURNOUT
    ib = int(np.argmin(np.abs(res.t - BURNOUT)))
    late = (res.t > 2.5) & (res.t <= BURNOUT)
    tilt_max = float(res.tilt_deg[burn].max())
    tilt_bo = float(res.tilt_deg[ib])
    sat = float(np.mean((np.abs(res.th_y_com[burn]) >= sat_deg - 1e-6) | (np.abs(res.th_z_com[burn]) >= sat_deg - 1e-6)))
    unrest = float(np.std(res.th_y[late])) if late.any() else float("nan")
    return {"tilt_max": tilt_max, "tilt_burnout": tilt_bo, "sat_frac": sat, "servo_std": unrest,
            "ok": bool(tilt_max < OK_TILT_MAX and tilt_bo < OK_TILT_BURNOUT)}


def _run(job):
    key, p = job
    return key, metrics(simulate(p), p.servo.sat_deg)


# ---------------------------------------------------------------------------
# 1. lineare Analyse
# ---------------------------------------------------------------------------

def controller_ltis(dt: float = 0.01):
    """(Name, ControllerLTI, nominales kappa) je Regler."""
    plant = design_plant(BELIEF, CAD, ServoParams(), dt)
    w = design_weights(BELIEF, L_CAD)
    K_fw = control_params_to_gains(gains_fw())
    pd = control_params_to_gains(model_pd_params(BELIEF, replace(CAD, l_meas=L_CAD), ServoParams(), dt))
    return [
        (CONTROLLERS[0][0], pid_lti(K_fw[0], K_fw[1], 0.0, dt, "firmware"), KAPPA_FW),
        (CONTROLLERS[1][0], pid_lti(K_fw[0], K_fw[1], 0.0, dt, "firmware"), KAPPA_FW_FIXED),
        (CONTROLLERS[2][0], pid_lti(pd[0], pd[1], 0.0, dt, "simulink"), 1.0),
        (CONTROLLERS[3][0], lqr_lti(design_lqr(plant, w, False)), 1.0),
        (CONTROLLERS[4][0], lqr_lti(design_lqr(plant, w, True)), 1.0),
    ]


def gains_fw():
    from tvcsim.params import ControlParams
    return ControlParams(kp=FW_CONFIG.PY_KP, ki=FW_CONFIG.PY_KI, kd=FW_CONFIG.PY_KD / 100.0)


def linear_analysis(n_grid: int, out_png):
    dt = 0.01
    ltis = controller_ltis(dt)
    nominal = AxisPlant(I=I_CAD, wn=36.7, zeta=0.598, tau=0.030, dt=dt)
    table = []
    kappas = np.logspace(math.log10(0.25), math.log10(6.0), n_grid)
    taus = np.linspace(0.0, 0.15, n_grid)
    wns = np.linspace(0.3, 2.0, n_grid)
    fig, axes = plt.subplots(2, len(ltis), figsize=(3.2 * len(ltis), 6.4), layout="constrained", sharey="row")
    vmax = 12.0
    for j, (name, lti, kap) in enumerate(ltis):
        pl = replace(nominal, kappa=kap)
        A = closed_loop(pl, lti)
        gm_up = gain_margin(pl, lti); gm_lo = gain_margin_low(pl, lti); dm = delay_margin(pl, lti)
        table.append({"name": name, "kappa_nominal": kap, "decay_rate": decay_rate(A, dt),
                      "gain_margin_up": gm_up * kap, "gain_margin_low": gm_lo * kap, "delay_margin": dm})
        Z1 = np.array([[decay_rate(closed_loop(replace(nominal, kappa=k, tau=t), lti), dt) for k in kappas] for t in taus])
        Z2 = np.array([[decay_rate(closed_loop(replace(nominal, kappa=k, wn=36.7 * s), lti), dt) for k in kappas] for s in wns])
        for row, (Z, yv, ylabel) in enumerate(((Z1, taus * 1000, "Totzeit (ms)"), (Z2, wns, "Servobandbreite x (wn / 36,7)"))):
            ax = axes[row, j]
            im = ax.pcolormesh(kappas, yv, np.clip(Z, -vmax, vmax), cmap="RdBu", vmin=-vmax, vmax=vmax, shading="auto")
            ax.contour(kappas, yv, Z, levels=[0.0], colors="k", linewidths=1.2)
            ax.set_xscale("log")
            ax.set_xticks([0.3, 0.5, 1, 2, 3, 5]); ax.set_xticklabels(["0,3", "0,5", "1", "2", "3", "5"])
            ax.minorticks_off()
            ax.plot([kap], [30.0 if row == 0 else 1.0], marker="o", color="k", ms=5, mfc="w")
            if row == 0:
                ax.set_title(name, fontsize=9)
            if j == 0:
                ax.set_ylabel(ylabel)
            ax.set_xlabel("kappa = l T / (l_ctrl T_est)")
            ax.grid(alpha=0.2)
    fig.colorbar(im, ax=axes, shrink=0.6, label="Abklingrate des langsamsten Pols (1/s); schwarz: Stabilitaetsgrenze")
    fig.suptitle("Lineare Stabilitaet je Querachse: Verstaerkungsfehler, Totzeit und Servobandbreite "
                 "(Kreis: Nominalpunkt des Reglers)", fontsize=11)
    fig.savefig(out_png, dpi=150, facecolor="white"); plt.close(fig)
    return table


# ---------------------------------------------------------------------------
# 2. Sweeps im 6DOF-Modell
# ---------------------------------------------------------------------------

def sweeps(n_values: int):
    lin = lambda a, b: np.linspace(a, b, n_values)
    log = lambda a, b: np.logspace(math.log10(a), math.log10(b), n_values)
    return [
        ("Traegheit quer x (I / 0,11)", log(0.4, 2.5), lambda p, v: replace(p, vehicle=replace(p.vehicle, Iy=I_CAD * v, Iz=I_CAD * v))),
        ("Hebelarm l (m), Regler glaubt 0,372", lin(0.24, 0.50), lambda p, v: replace(p, vehicle=replace(p.vehicle, l=float(v)))),
        ("Schub x", lin(0.7, 1.3), lambda p, v: replace(p, motor=replace(p.motor, thrust_scale=float(v)))),
        ("Servo-Totzeit (s), Regler glaubt 0,03", lin(0.0, 0.10), lambda p, v: replace(p, vehicle=replace(p.vehicle, servo_delay=float(v)))),
        ("Servobandbreite x (wn / 36,7)", lin(0.5, 1.5), lambda p, v: replace(p, servo=replace(p.servo, wn=36.7 * float(v)))),
        ("Servoverstaerkung x (Kardan je Soll)", lin(0.6, 1.6), lambda p, v: replace(p, servo=replace(p.servo, K=0.1662 * float(v)))),
        ("statischer Servofehler y (Grad), z = 0,6 y", lin(0.0, 3.0), lambda p, v: replace(p, vehicle=replace(p.vehicle, static_error_y=float(v), static_error_z=0.6 * float(v)))),
        ("Gyro-Rauschen sigma (Grad/s)", lin(0.0, 3.0), lambda p, v: replace(p, noise=replace(p.noise, w_sigma=float(v)))),
    ]


def run_jobs(jobs, workers):
    out = {}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, (key, m) in enumerate(ex.map(_run, jobs, chunksize=2)):
            out[key] = m
            if (i + 1) % 25 == 0 or i + 1 == len(jobs):
                print(f"  {i + 1}/{len(jobs)} Laeufe, {time.time() - t0:.0f} s", flush=True)
    return out


def sweep_analysis(n_values, workers, out_png, seed=0):
    sw = sweeps(n_values)
    base = base_params(seed)
    jobs = []
    for si, (label, values, apply) in enumerate(sw):
        for vi, v in enumerate(values):
            for ci, (cname, kw) in enumerate(CONTROLLERS):
                p = apply(replace(base, **kw), v)
                jobs.append(((si, vi, ci), p))
    print(f"Sweeps: {len(jobs)} Laeufe")
    res = run_jobs(jobs, workers)
    ncol = 4
    nrow = math.ceil(len(sw) / ncol)
    fig, axes = plt.subplots(2 * nrow, ncol, figsize=(3.4 * ncol, 2.6 * 2 * nrow), layout="constrained")
    summary = []
    for si, (label, values, _) in enumerate(sw):
        r, c = divmod(si, ncol)
        ax_t = axes[2 * r, c]; ax_s = axes[2 * r + 1, c]
        for ci, (cname, _) in enumerate(CONTROLLERS):
            tm = [res[(si, vi, ci)]["tilt_max"] for vi in range(len(values))]
            sf = [res[(si, vi, ci)]["sat_frac"] for vi in range(len(values))]
            oks = [res[(si, vi, ci)]["ok"] for vi in range(len(values))]
            ax_t.plot(values, tm, marker="o", ms=3, color=COLORS[ci], label=cname)
            ax_s.plot(values, sf, marker="o", ms=3, color=COLORS[ci])
            summary.append({"sweep": label, "controller": cname, "values": [float(x) for x in values],
                            "tilt_max": tm, "sat_frac": sf, "ok": oks,
                            "tilt_burnout": [res[(si, vi, ci)]["tilt_burnout"] for vi in range(len(values))]})
        ax_t.axhline(OK_TILT_MAX, color="0.5", lw=0.8, ls="--")
        ax_t.set_yscale("log"); ax_t.set_ylim(0.3, 100)
        ax_t.set_title(label, fontsize=8.5); ax_t.set_ylabel("Kipp max Brennphase (Grad)", fontsize=8)
        ax_s.set_ylabel("Saettigungsanteil", fontsize=8); ax_s.set_ylim(-0.02, 1.02)
        if "Traegheit" in label or "Schub" in label or "bandbreite" in label or "verstaerkung" in label:
            ax_t.set_xscale("log" if "Traegheit" in label else "linear")
        for a in (ax_t, ax_s):
            a.grid(alpha=0.3); a.tick_params(labelsize=8)
    for k in range(len(sw), nrow * ncol):
        r, c = divmod(k, ncol)
        axes[2 * r, c].axis("off"); axes[2 * r + 1, c].axis("off")
    axes[0, 0].legend(fontsize=7, loc="upper left")
    fig.suptitle("Robustheit im 6DOF-Modell: ein Parameter je Spalte, Regler fest auf CAD-Nominal ausgelegt "
                 "(gestrichelt: 10 Grad)", fontsize=11)
    fig.savefig(out_png, dpi=150, facecolor="white"); plt.close(fig)
    return summary


# ---------------------------------------------------------------------------
# 3. Monte-Carlo mit breiter Streuung
# ---------------------------------------------------------------------------

MC_SIGMA = {"I_scale": 0.20, "l": 0.03, "m_dry": 0.03, "tau": 0.015, "wn_scale": 0.20, "K_scale": 0.15,
            "static_error": 1.0, "thrust_scale": 0.10, "mis": 0.001}


def mc_draw(base: SimParams, rng: np.random.Generator) -> SimParams:
    rn = rng.standard_normal
    s = MC_SIGMA
    veh = replace(base.vehicle,
                  Iy=I_CAD * max(0.3, 1 + rn() * s["I_scale"]), Iz=I_CAD * max(0.3, 1 + rn() * s["I_scale"]),
                  l=max(0.15, L_CAD + rn() * s["l"]), m_dry=max(0.5, CAD.m_dry + rn() * s["m_dry"]),
                  servo_delay=max(0.0, 0.030 + rn() * s["tau"]),
                  static_error_y=rn() * s["static_error"], static_error_z=rn() * s["static_error"],
                  mis_y=rn() * s["mis"], mis_z=rn() * s["mis"])
    servo = replace(base.servo, wn=36.7 * max(0.3, 1 + rn() * s["wn_scale"]), K=0.1662 * max(0.3, 1 + rn() * s["K_scale"]))
    motor = replace(base.motor, thrust_scale=max(0.5, 1 + rn() * s["thrust_scale"]))
    return replace(base, vehicle=veh, servo=servo, motor=motor, seed=int(rng.integers(0, 2 ** 31 - 1)))


def montecarlo_analysis(runs, workers, out_png, seed=1):
    rng = np.random.default_rng(seed)
    base = base_params()
    draws = [mc_draw(base, rng) for _ in range(runs)]
    jobs = [((k, ci), replace(d, **kw)) for k, d in enumerate(draws) for ci, (_, kw) in enumerate(CONTROLLERS)]
    print(f"Monte-Carlo: {len(jobs)} Laeufe")
    res = run_jobs(jobs, workers)
    fig, axes = plt.subplots(1, 2, figsize=(10.7, 4.6), layout="constrained")
    summary = []
    data = []
    for ci, (cname, _) in enumerate(CONTROLLERS):
        tm = np.array([res[(k, ci)]["tilt_max"] for k in range(runs)])
        tb = np.array([res[(k, ci)]["tilt_burnout"] for k in range(runs)])
        ok = np.array([res[(k, ci)]["ok"] for k in range(runs)])
        data.append(tm)
        summary.append({"name": cname, "runs": runs, "ok_fraction": float(ok.mean()),
                        "tilt_max_median": float(np.median(tm)), "tilt_max_p95": float(np.percentile(tm, 95)),
                        "tilt_max_max": float(tm.max()), "tilt_burnout_median": float(np.median(tb)),
                        "tilt_burnout_p95": float(np.percentile(tb, 95))})
        axes[1].scatter([d.vehicle.servo_delay for d in draws], tm, s=10, color=COLORS[ci], alpha=0.6, label=cname)
    bp = axes[0].boxplot(data, tick_labels=[c[0].replace(" (", "\n(").replace(", ", ",\n") for c in CONTROLLERS],
                         showfliers=True, patch_artist=True)
    for patch, col in zip(bp["boxes"], COLORS):
        patch.set_facecolor(col); patch.set_alpha(0.35)
    axes[0].set_yscale("log"); axes[0].set_ylabel("Kipp max Brennphase (Grad)")
    axes[0].axhline(OK_TILT_MAX, color="0.5", lw=0.8, ls="--"); axes[0].tick_params(axis="x", labelsize=7)
    axes[0].grid(alpha=0.3, axis="y")
    axes[1].set_yscale("log"); axes[1].set_xlabel("gestreute Servo-Totzeit (s)"); axes[1].set_ylabel("Kipp max Brennphase (Grad)")
    axes[1].axhline(OK_TILT_MAX, color="0.5", lw=0.8, ls="--"); axes[1].grid(alpha=0.3); axes[1].legend(fontsize=7)
    fig.suptitle(f"Monte-Carlo, {runs} gestreute Fahrzeuge/Servos je Regler (I +-20 %, l +-3 cm, Totzeit +-15 ms, "
                 f"wn +-20 %, Servogain +-15 %, Schub +-10 %, statischer Fehler sigma 1 Grad)", fontsize=9.5)
    fig.savefig(out_png, dpi=150, facecolor="white"); plt.close(fig)
    return summary


# ---------------------------------------------------------------------------

def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and (math.isnan(x))):
        return "-"
    if isinstance(x, float) and math.isinf(x):
        return "unbegrenzt"
    return f"{x:.{nd}f}".replace(".", ",")


def write_summary(path, lin_table, sweep_summary, mc_summary, args):
    lines = ["# Robustheit der Regler im Parameterraum (automatisch erzeugt von `scripts/robustness.py`)", "",
             f"Entwurf aller Regler: I quer {I_CAD:.3f} kg m2, l {L_CAD:.3f} m, Servo wn 36,7 rad/s, zeta 0,60, Totzeit 30 ms, "
             f"T_design {BELIEF.T_design:g} N, Bryson-Gewichte theta {BELIEF.theta_max_deg:g} Grad, omega {BELIEF.omega_max_dps:g} Grad/s, "
             f"TVC {BELIEF.tvc_max_deg:g} Grad. Firmware-Gewinne Kp 5, Ki 0, Kd 1 (Config.h). "
             f"Kriterium 'ok': Kipp max < {OK_TILT_MAX:g} Grad in der Brennphase und < {OK_TILT_BURNOUT:g} Grad bei Brennschluss.", ""]
    if lin_table:
        lines += ["## 1. Lineare Reserven je Querachse (Nominalpunkt des jeweiligen Reglers)", "",
                  "| Regler | kappa nominal | Abklingrate (1/s) | kappa max stabil | kappa min stabil | Totzeit max stabil (ms) |",
                  "|---|---|---|---|---|---|"]
        for r in lin_table:
            lines.append(f"| {r['name']} | {fmt(r['kappa_nominal'])} | {fmt(r['decay_rate'], 1)} | {fmt(r['gain_margin_up'])} | "
                         f"{fmt(r['gain_margin_low'])} | {fmt(r['delay_margin'] * 1000 if math.isfinite(r['delay_margin']) else r['delay_margin'], 0)} |")
        lines.append("")
        lines.append("kappa = l T / (l_ctrl T_est) ist der Verstaerkungsfehler der Modellinversion; die Firmware mit Config.h "
                     f"liegt wegen MASS_KG 0,70 und MOMENT_ARM_M 0,30 nominal bei kappa {KAPPA_FW:.2f}.")
        lines.append("")
    if sweep_summary:
        lines += ["## 2. Sweeps im 6DOF-Modell (max. Kippwinkel in der Brennphase in Grad; in Klammern: ok-Faelle)", ""]
        names = [c[0] for c in CONTROLLERS]
        lines.append("| Parameter (Bereich) | " + " | ".join(names) + " |")
        lines.append("|---|" + "---|" * len(names))
        labels = []
        for s in sweep_summary:
            if s["sweep"] not in labels:
                labels.append(s["sweep"])
        for lab in labels:
            row = [r for r in sweep_summary if r["sweep"] == lab]
            vals = row[0]["values"]
            cells = []
            for name in names:
                r = next(x for x in row if x["controller"] == name)
                cells.append(f"{fmt(max(r['tilt_max']), 1)} ({sum(r['ok'])}/{len(vals)})")
            lines.append(f"| {lab} ({fmt(vals[0])} .. {fmt(vals[-1])}) | " + " | ".join(cells) + " |")
        lines.append("")
    if mc_summary:
        lines += [f"## 3. Monte-Carlo ({mc_summary[0]['runs']} Laeufe je Regler, alle Parameter zugleich gestreut)", "",
                  "| Regler | ok-Anteil | Kipp max Median | Kipp max P95 | Kipp max Maximum | Kipp Brennschluss Median | P95 |",
                  "|---|---|---|---|---|---|---|"]
        for r in mc_summary:
            lines.append(f"| {r['name']} | {fmt(100 * r['ok_fraction'], 0)} % | {fmt(r['tilt_max_median'], 1)} | {fmt(r['tilt_max_p95'], 1)} | "
                         f"{fmt(r['tilt_max_max'], 1)} | {fmt(r['tilt_burnout_median'], 1)} | {fmt(r['tilt_burnout_p95'], 1)} |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="grobe Raster (5 Werte, 20 MC-Laeufe)")
    ap.add_argument("--skip-sweeps", action="store_true")
    ap.add_argument("--skip-mc", action="store_true")
    ap.add_argument("--skip-linear", action="store_true")
    ap.add_argument("--values", type=int, default=None, help="Werte je Sweep (Vorgabe 9)")
    ap.add_argument("--runs", type=int, default=None, help="Monte-Carlo-Laeufe je Regler (Vorgabe 100)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--prefix", default="robustness")
    args = ap.parse_args()
    n_values = args.values or (5 if args.quick else 9)
    runs = args.runs or (20 if args.quick else 100)
    n_grid = 25 if args.quick else 61
    OUT_DIR.mkdir(exist_ok=True)
    t0 = time.time()
    lin_table = sweep_summary = mc_summary = None
    # uebersprungene Teile aus einem frueheren Lauf uebernehmen, damit die Zusammenfassung vollstaendig bleibt
    prev_path = OUT_DIR / f"{args.prefix}_results.json"
    prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
    if args.skip_linear:
        lin_table = prev.get("linear")
    if args.skip_sweeps:
        sweep_summary = prev.get("sweeps")
    if args.skip_mc:
        mc_summary = prev.get("montecarlo")
    if not args.skip_linear:
        lin_table = linear_analysis(n_grid, OUT_DIR / f"{args.prefix}_linear_maps.png")
        for r in lin_table:
            print(f"{r['name']:32s} kappa {r['kappa_nominal']:.2f}  Abkling {r['decay_rate']:5.1f} 1/s  "
                  f"kappa stabil {r['gain_margin_low']:.2f}..{r['gain_margin_up']:.2f}  Totzeit max {r['delay_margin'] * 1000:.0f} ms")
    if not args.skip_sweeps:
        sweep_summary = sweep_analysis(n_values, args.workers, OUT_DIR / f"{args.prefix}_sweeps.png")
    if not args.skip_mc:
        mc_summary = montecarlo_analysis(runs, args.workers, OUT_DIR / f"{args.prefix}_montecarlo.png")
        for r in mc_summary:
            print(f"{r['name']:32s} ok {100 * r['ok_fraction']:5.1f} %  Kipp max Median {r['tilt_max_median']:5.2f}  "
                  f"P95 {r['tilt_max_p95']:5.2f}  Max {r['tilt_max_max']:5.1f}")
    write_summary(OUT_DIR / f"{args.prefix}_summary.md", lin_table, sweep_summary, mc_summary, args)
    with open(OUT_DIR / f"{args.prefix}_results.json", "w", encoding="utf-8") as f:
        json.dump({"linear": lin_table, "sweeps": sweep_summary, "montecarlo": mc_summary}, f, indent=1, default=float)
    print(f"fertig in {time.time() - t0:.0f} s, Ausgaben in {OUT_DIR}/{args.prefix}_*")


if __name__ == "__main__":
    main()
