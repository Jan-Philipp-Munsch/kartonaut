"""Plots: Nominallauf (Hoehe, Lage, Servowinkel) und Monte-Carlo-Trajektorien in 3D."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .dynamics import euler_deg  # noqa: E402
from .sim import SimResult  # noqa: E402


def plot_nominal(res: SimResult, path: Path, title: str = "") -> Path:
    t = res.t
    fig, ax = plt.subplots(4, 1, figsize=(9, 12), sharex=True)
    fig.suptitle(title or f"Nominallauf, Regler {res.params.controller}")

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
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_montecarlo_3d(results: list[SimResult], path: Path, title: str | None = None) -> Path:
    fig = plt.figure(figsize=(9, 10))
    ax = fig.add_subplot(111, projection="3d")
    for res in results:
        ax.plot(res.r[:, 1], res.r[:, 2], res.r[:, 0], lw=0.8)
    ax.set_title(title or f"{len(results)} Simulated Monte-Carlo Flight Trajectories")
    ax.set_xlabel("Downrange (m)")
    ax.set_ylabel("Crossrange (m)")
    ax.set_zlabel("Altitude (m)")
    # Achsen am 90. Perzentil der seitlichen Auslenkung, damit Ausreisser das Bild nicht plattdruecken
    lim = max(1.0, float(np.percentile([np.abs(r.r[:, 1:]).max() for r in results], 90)))
    zmax = max(float(r.r[:, 0].max()) for r in results)
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(0, max(zmax, 1.0))
    try:
        ax.set_box_aspect((1, 1, max(zmax, 1.0) / (2 * lim)))
    except Exception:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_servo_fit(t, u, y, y_fit, fit: dict, path: Path) -> Path:
    fig, ax = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    ax[0].plot(t, u, color="0.5", label="Servo-Soll - 95 (Grad)")
    ax[0].set_ylabel("Soll (Grad)")
    ax[0].legend()
    ax[1].plot(t, y, "k", label="Kardan gemessen")
    ax[1].plot(t, y_fit, "r", lw=1, label=f"PT2+Totzeit: K={fit['K']:.4f}, wn={fit['wn']:.1f} rad/s, "
                                        f"zeta={fit['zeta']:.2f}, tau={fit['tau']*1000:.0f} ms, RMS {fit['rms_deg']:.2f} Grad")
    ax[1].set_ylabel("Kardan (Grad)")
    ax[1].set_xlabel("Zeit (s)")
    ax[1].legend()
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
