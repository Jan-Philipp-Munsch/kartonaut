"""Schubkurven und Treibstoffmasse.

Im Simulink-Modell: ``Clock -> Lookup(time, thrust)`` fuer den ersten Motor, fuer den zweiten
``Clock -> Delay(secondburn) -> Lookup``; die Summe geht als ``T`` in die Dynamik. Die Tabellen
``E12time.mat``/``E12thrust.mat`` sind die CSV-Kurve mit (0, 0) als erstem und (20 s, 0) als
letztem Punkt. Hier wird die CSV geladen, (0, 0) vorangestellt und ausserhalb der Tabelle 0
angenommen (``np.interp`` haelt die Randwerte, beide sind 0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .params import DATA_DIR, MotorParams


def load_thrust_curve(name: str) -> tuple[np.ndarray, np.ndarray]:
    """Liest ``data/<name>_thrustcurve.csv`` (Semikolon, Zeit s; Schub N)."""
    arr = np.loadtxt(DATA_DIR / f"{name}_thrustcurve.csv", delimiter=";")
    t, f = arr[:, 0], arr[:, 1]
    if t[0] > 0:
        t = np.concatenate([[0.0], t])
        f = np.concatenate([[0.0], f])
    return t, f


def load_fuel_signalbuilder() -> tuple[np.ndarray, np.ndarray]:
    """Treibstoffmasse in g aus dem Signal Builder der .slx (``data/m_fuel_signalbuilder.csv``)."""
    arr = np.loadtxt(DATA_DIR / "m_fuel_signalbuilder.csv", delimiter=",", skiprows=1)
    return arr[:, 0], arr[:, 1]


@dataclass
class ThrustModel:
    params: MotorParams

    def __post_init__(self) -> None:
        self.t_curve, self.f_curve = load_thrust_curve(self.params.curve)
        self.burn_time = float(self.t_curve[np.nonzero(self.f_curve)[0][-1] + 1])
        # Impuls bis zu jedem Stuetzpunkt (fuer den Abbrand proportional zum Impuls)
        self.impulse_curve = np.concatenate(
            [[0.0], np.cumsum(0.5 * (self.f_curve[1:] + self.f_curve[:-1]) * np.diff(self.t_curve))])
        self.total_impulse = float(self.impulse_curve[-1])
        self.t_fuel_sb, self.m_fuel_sb = load_fuel_signalbuilder()

    def t_second(self, dt: float) -> float:
        """Zuendzeitpunkt des zweiten Motors in s (``secondburn`` Schritte zu ``dt``)."""
        return self.params.secondburn * dt

    def thrust_single(self, t: float) -> float:
        return float(np.interp(t, self.t_curve, self.f_curve, left=0.0, right=0.0))

    def thrust(self, t: float, dt: float) -> float:
        """Gesamtschub in N zur Zeit t (Summe beider Motoren)."""
        T = self.thrust_single(t)
        if self.params.second_motor:
            T += self.thrust_single(t - self.t_second(dt))
        return T

    def _burnt_fraction(self, t: float) -> float:
        return float(np.interp(t, self.t_curve, self.impulse_curve, left=0.0,
                               right=self.total_impulse)) / self.total_impulse

    def fuel_mass_g(self, t: float, dt: float) -> float:
        """Treibstoffmasse in g zur Zeit t (Eingang ``m_fuel`` des EOM-Blocks)."""
        if self.params.fuel_model == "signalbuilder":
            return float(np.interp(t, self.t_fuel_sb, self.m_fuel_sb, left=self.m_fuel_sb[0], right=0.0))
        if self.params.fuel_model == "impulse":
            m = self.params.fuel_mass_g * (1.0 - self._burnt_fraction(t))
            if self.params.second_motor:
                m += self.params.fuel_mass_g * (1.0 - self._burnt_fraction(t - self.t_second(dt)))
            return m
        raise ValueError(f"unbekanntes fuel_model {self.params.fuel_model!r}")
