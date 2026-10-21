"""Aktuatorpfad: Kommando -> ZOH -> Saettigung +-5 Grad -> tf5 -> Gain 6 -> statischer Fehler.

``tf5`` (ein ``idtf`` aus der System Identification Toolbox) ist ohne MATLAB nicht lesbar und
wird hier durch ein PT2-Glied mit Totzeit ersetzt, das ``scripts/fit_servo.py`` aus den
Sprungantworten in ``data/servo_step_response.csv`` fittet (Servo-Soll in Grad, Mitte 95,
-> Kardanwinkel in Grad).

Zustand je Achse: ``x = [theta, theta_dot]`` mit
``theta_ddot = wn^2 (K u(t - tau) - theta) - 2 zeta wn theta_dot``.
Der Kommandoverlauf ist stueckweise konstant (ZOH), deshalb reicht fuer die Totzeit ein
Nachschlagen im Kommandoverlauf.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .params import ServoParams, VehicleParams


def static_error_profile_y(t: float) -> float:
    """Step1 (t=2: 1 -> 0) + Step2 (t=7: 0 -> 1) + Step3 (t=9: 0 -> -1) aus dem Root-System."""
    return (1.0 if t < 2.0 else 0.0) + (1.0 if t >= 7.0 else 0.0) + (-1.0 if t >= 9.0 else 0.0)


@dataclass
class ServoChannel:
    """Eine TVC-Achse: PT2 mit Totzeit, Eingang in Grad (Kommando nach Saettigung)."""

    servo: ServoParams
    tau: float
    dt: float

    def __post_init__(self) -> None:
        self.cmd_hist: list[float] = []
        self.x = np.zeros(2)

    def push_command(self, cmd_deg: float) -> float:
        cmd = max(-self.servo.sat_deg, min(self.servo.sat_deg, cmd_deg))
        self.cmd_hist.append(cmd)
        return cmd

    def delayed_input(self, t: float) -> float:
        k = int(math.floor((t - self.tau) / self.dt + 1e-9))
        if k < 0 or not self.cmd_hist:
            return 0.0
        return self.cmd_hist[min(k, len(self.cmd_hist) - 1)]

    def deriv(self, t: float, x) -> np.ndarray:
        u = self.delayed_input(t)
        wn, zeta, K = self.servo.wn, self.servo.zeta, self.servo.K
        return np.array([x[1], wn * wn * (K * u - x[0]) - 2.0 * zeta * wn * x[1]])

    def output(self, x) -> float:
        """Kardanwinkel in Grad nach dem Gain-Block (6 bzw. 23)."""
        return self.servo.servo_deg_per_tvc_deg * x[0]


class Actuator:
    """Beide Achsen plus statische Fehler, wie das Root-System verdrahtet ist."""

    def __init__(self, servo: ServoParams, vehicle: VehicleParams, dt: float):
        tau = servo.tau if vehicle.servo_delay is None else vehicle.servo_delay
        tau = max(0.0, tau)
        self.y = ServoChannel(servo, tau, dt)
        self.z = ServoChannel(servo, tau, dt)
        self.vehicle = vehicle

    def push_command(self, th_y_com: float, th_z_com: float) -> tuple[float, float]:
        return self.y.push_command(th_y_com), self.z.push_command(th_z_com)

    def angles(self, t: float, xy, xz) -> tuple[float, float]:
        """Tatsaechliche TVC-Winkel (Grad): Add-Block ``-static_error_y*profil + 6*tf5`` und
        ``6*tf5 + static_error_z``."""
        th_y = self.y.output(xy) - self.vehicle.static_error_y * static_error_profile_y(t)
        th_z = self.z.output(xz) + self.vehicle.static_error_z
        return th_y, th_z


# ---------------------------------------------------------------------------
# Identifikation aus den Sprungantworten
# ---------------------------------------------------------------------------

def simulate_servo_response(t: np.ndarray, u: np.ndarray, K: float, wn: float, zeta: float,
                            tau: float) -> np.ndarray:
    """PT2 mit Totzeit auf ein Eingangssignal (gleichmaessig abgetastet) anwenden, RK4."""
    n = len(t)
    h = float(t[1] - t[0])
    shift = int(round(tau / h))
    u_del = np.concatenate([np.zeros(shift), u[: n - shift]]) if shift > 0 else u.copy()
    x = np.zeros(2)
    y = np.zeros(n)

    def f(x, ui):
        return np.array([x[1], wn * wn * (K * ui - x[0]) - 2.0 * zeta * wn * x[1]])

    for i in range(n - 1):
        ui, ui1 = u_del[i], u_del[i + 1]
        um = 0.5 * (ui + ui1)
        k1 = f(x, ui)
        k2 = f(x + 0.5 * h * k1, um)
        k3 = f(x + 0.5 * h * k2, um)
        k4 = f(x + h * k3, ui1)
        x = x + h / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
        y[i + 1] = x[0]
    return y


def fit_servo_model(t: np.ndarray, u: np.ndarray, y: np.ndarray,
                    x0=(0.16, 25.0, 1.0, 0.03)) -> dict:
    """Least-Squares-Fit von (K, wn, zeta, tau) auf Soll (relativ zur Mitte) -> Kardan."""
    from scipy.optimize import least_squares

    def resid(p):
        return simulate_servo_response(t, u, *p) - y

    res = least_squares(resid, x0, bounds=([0.01, 1.0, 0.1, 0.0], [1.0, 200.0, 5.0, 0.3]))
    K, wn, zeta, tau = res.x
    y_fit = simulate_servo_response(t, u, K, wn, zeta, tau)
    return {"K": float(K), "wn": float(wn), "zeta": float(zeta), "tau": float(tau),
            "rms_deg": float(np.sqrt(np.mean((y_fit - y) ** 2))), "y_fit": y_fit}
