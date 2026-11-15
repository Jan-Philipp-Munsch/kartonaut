"""Motorwechsel im Magazin ("Kugelschreiber-Logik"): zwei Motoren hintereinander in einem Rohr.

Motor 1 sitzt unten in Brennstellung, Motor 2 darueber, eine Feder drueckt den Stapel nach unten. Solange
Motor 1 schiebt, haelt sein Schub den Stapel am oberen Anschlag; faellt der Schub unter die Federkraft,
schiebt die Feder die leere Huelse hinaus und Motor 2 in die Brennstellung.

Hier steht nur die Zeitrechnung dieses Nachrutschens (1D, entlang des Rohrs). Die Rakete ist waehrenddessen
praktisch im freien Fall, das Gewicht des Stapels hilft also nicht mit; das ist die vorsichtige Annahme.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .motors import load_thrust_curve

M_MOTOR = 0.064      # kg, TSP E12-0 voll
M_CASE = 0.036       # kg, leere Huelse
L_MOTOR = 0.095      # m


@dataclass
class SwapResult:
    t_release: float     # s nach Zuendung von Motor 1: Schub faellt unter die Federkraft
    t_seated: float      # s nach Zuendung: Motor 2 sitzt in Brennstellung
    t_burnout: float     # s nach Zuendung: Schub von Motor 1 unter ``thrust_off``
    v_seat: float        # m/s, Geschwindigkeit des Stapels am Anschlag

    @property
    def swap_time(self) -> float:
        """Zeit vom Brennschluss (Schub < thrust_off) bis Motor 2 sitzt; das ist ``PinpointConfig.swap_time``."""
        return self.t_seated - self.t_burnout

    @property
    def slide_time(self) -> float:
        return self.t_seated - self.t_release


def swap_kinematics(spring_n: float = 5.0, friction_n: float = 1.0, travel: float = L_MOTOR + 0.003,
                    m_extra: float = 0.008, thrust_scale: float = 1.0, thrust_off: float = 0.5,
                    curve: str = "E12", dt: float = 2e-4) -> SwapResult:
    """Nachrutschen des Stapels (leere Huelse + voller Motor 2 + Kolben) unter einer Feder konstanter Kraft.

    spring_n    Federkraft (Rollfeder: ueber den Weg konstant)
    friction_n  Reibung des Stapels im Rohr
    travel      Weg bis zur Brennstellung (eine Motorlaenge plus Hub der Verriegelung)
    m_extra     Kolben und Hitzeschild
    """
    tc, fc = load_thrust_curve(curve)
    fc = fc * thrust_scale
    i_end = np.nonzero(fc)[0][-1] + 1
    t_peak = tc[np.argmax(fc)]
    tt = np.arange(t_peak, tc[i_end] + 2.0, dt)
    thrust = np.interp(tt, tc, fc, left=0.0, right=0.0)
    below = np.nonzero(thrust < spring_n)[0]
    off = np.nonzero(thrust < thrust_off)[0]
    t_rel = tt[below[0]]
    m = M_CASE + M_MOTOR + m_extra
    x = 0.0; v = 0.0; t_seat = np.nan
    for k in range(below[0], len(tt)):
        a = (spring_n - thrust[k] - friction_n) / m
        if v <= 0.0 and a < 0.0:
            a = 0.0
        v += a * dt; x += v * dt
        if x >= travel:
            t_seat = tt[k]
            break
    return SwapResult(float(t_rel), float(t_seat), float(tt[off[0]]), float(v))
