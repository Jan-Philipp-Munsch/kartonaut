"""Avionics-Block: Zero-Order Hold mit dt und Rauschen auf Quaternion, Drehrate und Beschleunigung.

* ``quat_corrupt`` (chart_76): zufaellige Kleinstdrehung, Achse zufaellig normiert,
  Winkel ~ N(0, 0,01 rad), ``q_n = hamilton(q, q_rot)``.
* ``w_corrupt`` (chart_83): ``w_n = w + randn * 0,4`` - ein Skalar auf alle drei Komponenten.
  ``w`` kommt in Grad/s an (Gain ``rad to deg`` vor dem Block).
* Beschleunigung: ``rdd + Random Number`` (Varianz 1, Abtastzeit dt, ebenfalls ein Skalar).
"""
from __future__ import annotations

import math

import numpy as np

from .dynamics import hamilton
from .params import NoiseParams


class Avionics:
    def __init__(self, noise: NoiseParams, rng: np.random.Generator):
        self.noise = noise
        self.rng = rng

    def quat_corrupt(self, q):
        axis = self.rng.standard_normal(3)
        axis /= np.linalg.norm(axis)
        angle = self.rng.standard_normal() * self.noise.q_angle_sigma
        s = math.sin(angle / 2)
        q_rot = np.array([math.cos(angle / 2), axis[0] * s, axis[1] * s, axis[2] * s])
        return hamilton(q, q_rot)

    def sample(self, q, w_dps, accel):
        """Messwerte zum Abtastzeitpunkt: (q_n, w_n in Grad/s, rdd_n in m/s^2)."""
        if not self.noise.enabled:
            return np.array(q, dtype=float), np.array(w_dps, dtype=float), np.array(accel, dtype=float)
        q_n = self.quat_corrupt(q)
        w_n = np.asarray(w_dps, dtype=float) + self.rng.standard_normal() * self.noise.w_sigma
        a_n = np.asarray(accel, dtype=float) + self.rng.standard_normal() * self.noise.rdd_sigma
        return q_n, w_n, a_n
