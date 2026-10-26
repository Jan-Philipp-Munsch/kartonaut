"""Plots: Nominallauf (Hoehe, Lage, Servowinkel) und Monte-Carlo-Trajektorien in 3D."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .dynamics import euler_deg  # noqa: E402
from .sim import SimResult  # noqa: E402

DPI = 150
WIDTH_IN = 10.7   # etwa 1600 px bei 150 dpi


def _titles(fig, ax0, title: str, subtitle: str = "") -> None:
    """Titel in einer Zeile, Parameter darunter in kleinerer Schrift."""
    fig.suptitle(title, fontsize=13)
    if subtitle:
        ax0.set_title(subtitle, fontsize=8.5, color="0.35", wrap=True)


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    return path


def plot_nominal(res: SimResult, path: Path, title: str = "", subtitle: str = "") -> Path:
    t = res.t
    fig, ax = plt.subplots(4, 1, figsize=(WIDTH_IN, 12), sharex=True, layout="constrained")
    _titles(fig, ax[0], title or f"Nominallauf, Regler {res.params.controller}", subtitle)

    ax[0].plot(t, res.r[:, 0], label="Hoehe x")
    ax[0].plot(t, res.r[:, 1], label="Downrange y")
    ax[0].plot(t, res.r[:, 2], label="Crossrange z")
    ax[0].set_ylabel("Position (m)")
    ax[0].legend(loc="upper left")
    ax0b = ax[0].twinx()
    ax0b.plot(t, res.T, color="0.6", lw=0.8, label="Schub")
    ax0b.set_ylabel("Schub (N)")

    eul = np.array([euler_deg(q) for q in res.q])
    ax[1].plot(t, res.tilt_deg, "k", label="Kippwinkel")
    ax[1].plot(t, eul[:, 0], label="Neigung um y")
    ax[1].plot(t, eul[:, 1], label="Neigung um z")
    ax[1].plot(t, eul[:, 2], ":", label="Roll")
    ax[1].set_ylabel("Lage (Grad)")
    ax[1].legend(loc="upper left")

    ax[2].plot(t, res.w_dps[:, 1], label="w_y")
    ax[2].plot(t, res.w_dps[:, 2], label="w_z")
    ax[2].plot(t, res.w_dps[:, 0], ":", label="w_x (Roll)")
    ax[2].set_ylabel("Drehrate (Grad/s)")
    ax[2].legend(loc="upper left")

    ax[3].plot(t, res.th_y_com, "--", color="C0", lw=0.8, label="th_y Kommando")
    ax[3].plot(t, res.th_y, color="C0", label="th_y Kardan")
    ax[3].plot(t, res.th_z_com, "--", color="C1", lw=0.8, label="th_z Kommando")
    ax[3].plot(t, res.th_z, color="C1", label="th_z Kardan")
    ax[3].set_ylabel("TVC-Winkel (Grad)")
    ax[3].set_xlabel("Zeit (s)")
    ax[3].legend(loc="upper left")
    ax3b = ax[3].twinx()
    ax3b.plot(t, res.servo_y_deg, color="C0", lw=0.5, alpha=0.4)
    ax3b.plot(t, res.servo_z_deg, color="C1", lw=0.5, alpha=0.4)
    ax3b.set_ylabel(f"Servo (Grad, x{res.params.servo.servo_deg_per_tvc_deg:g})")

    for a in ax:
        a.grid(alpha=0.3)
    return _save(fig, path)


def plot_montecarlo_3d(results, path: Path, title: str | None = None, subtitle: str = "") -> Path:
    """3D-Plot wie in TVC6DOF.m. ``results``: SimResult-Liste oder Liste von Positionsarrays (N, 3)."""
    positions = [r.r if isinstance(r, SimResult) else np.asarray(r) for r in results]
    fig = plt.figure(figsize=(WIDTH_IN, 10.5), layout="constrained")
    ax = fig.add_subplot(111, projection="3d")
    # Achsen am 90. Perzentil der seitlichen Auslenkung, damit Ausreisser das Bild nicht plattdruecken,
    # und gleiche Skalierung aller drei Achsen (wie "axis equal" in MATLAB)
    lim = max(1.0, float(np.percentile([np.abs(r[:, 1:]).max() for r in positions], 90)))
    zmax = max(1.0, max(float(r[:, 0].max()) for r in positions))
    for r in positions:
        r = r.copy()
        outside = (np.abs(r[:, 1]) > lim) | (np.abs(r[:, 2]) > lim) | (r[:, 0] < 0)
        r[outside] = np.nan          # Ausreisser enden am Kastenrand statt ausserhalb weiterzulaufen
        ax.plot(r[:, 1], r[:, 2], r[:, 0], lw=0.8)
    _titles(fig, ax, title or f"{len(positions)} Monte-Carlo-Trajektorien", subtitle)
    ax.set_xlabel("Downrange (m)", labelpad=12)
    ax.set_ylabel("Crossrange (m)", labelpad=12)
    ax.set_zlabel("Altitude (m)", labelpad=8)
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(0, zmax)
    ax.set_box_aspect((2 * lim, 2 * lim, zmax), zoom=0.9)
    ax.view_init(elev=18, azim=-55)
    return _save(fig, path)


def plot_servo_fit(t, u, y, y_fit, fit: dict, path: Path) -> Path:
    fig, ax = plt.subplots(2, 1, figsize=(WIDTH_IN, 7), sharex=True, layout="constrained")
    _titles(fig, ax[0], "Servo-Identifikation: SG90 im Kardan, Sprungantworten",
            "Eingang Servo-Soll relativ zur Mitte (95 Grad), Ausgang gemessener Kardanwinkel; Fit PT2 mit Totzeit")
    ax[0].plot(t, u, color="0.5", label="Servo-Soll - 95 (Grad)")
    ax[0].set_ylabel("Soll (Grad)")
    ax[0].legend()
    ax[1].plot(t, y, "k", label="Kardan gemessen")
    ax[1].plot(t, y_fit, "r", lw=1, label=f"Fit: K={fit['K']:.4f} (1/{1 / fit['K']:.1f}), wn={fit['wn']:.1f} rad/s, "
                                        f"zeta={fit['zeta']:.2f}, Totzeit {fit['tau']*1000:.0f} ms, RMS {fit['rms_deg']:.2f} Grad")
    ax[1].set_ylabel("Kardan (Grad)")
    ax[1].set_xlabel("Zeit (s)")
    ax[1].legend()
    for a in ax:
        a.grid(alpha=0.3)
    return _save(fig, path)


def plot_landing(res: SimResult, path: Path) -> Path:
    """Landebrennen: Hoehe, Sinkrate, Schub und Drossel, Kippwinkel/Kardan ueber der Zeit."""
    e = res.extra
    t_ign = e.get("t_ignite2")
    fig, ax = plt.subplots(4, 1, figsize=(WIDTH_IN, 10), sharex=True, layout="constrained")
    sub = f"Zuendung {e.get('h_ignite2', 0):.1f} m / {e.get('v_ignite2', 0):.1f} m/s" if t_ign else "ohne Zuendung"
    if e.get("contacts"):
        sub += "; Aufsetzen " + ", ".join(f"{v:.1f} m/s" for _, v in e["contacts"])
    _titles(fig, ax[0], f"Landebrennen mit dem zweiten Motor, m = {res.params.vehicle.m_dry + 0.028:.2f} kg", sub)
    ax[0].plot(res.t, res.r[:, 0], "k"); ax[0].set_ylabel("Hoehe (m)")
    ax[1].plot(res.t, res.rd[:, 0], "k", label="vz")
    if res.v_ref is not None and np.any(res.v_ref != 0):
        ax[1].plot(res.t, res.v_ref, "r:", lw=1, label="Soll (Endphase)")
    ax[1].set_ylabel("Sinkrate (m/s)"); ax[1].legend(fontsize=8)
    ax[2].plot(res.t, res.T, "k", label="Schub wirksam (N)")
    if res.throttle_f is not None and res.params.throttle.enabled:
        ax2 = ax[2].twinx()
        ax2.plot(res.t, res.throttle_u, color="tab:orange", lw=0.8, label="Drossel u")
        ax2.plot(res.t, res.throttle_f, color="tab:blue", lw=0.8, label="Schubfaktor f")
        ax2.set_ylim(-0.05, 1.05); ax2.legend(fontsize=8, loc="upper right")
    ax[2].set_ylabel("Schub (N)"); ax[2].legend(fontsize=8, loc="upper left")
    ax[3].plot(res.t, res.tilt_deg, "k", label="Kippwinkel")
    ax[3].plot(res.t, res.th_y, color="tab:green", lw=0.8, label="Kardan y")
    ax[3].plot(res.t, res.th_z, color="tab:purple", lw=0.8, label="Kardan z")
    ax[3].set_ylabel("Grad"); ax[3].set_xlabel("Zeit (s)"); ax[3].legend(fontsize=8)
    for a in ax:
        a.grid(alpha=0.3)
        if t_ign:
            a.axvline(t_ign, color="0.6", lw=0.8, ls="--")
    return _save(fig, path)
