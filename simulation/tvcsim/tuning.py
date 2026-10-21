"""Port von ``pid_tuner.m``: Raster ueber kp, ki, kd mit ``maxHeight`` als Zielgroesse.

``pid_tuner.m`` setzt nur kp/ki/kd und simuliert das Modell mit den Werten, die gerade im
Workspace stehen (StopTime 12 s, also beide Motoren). Welche Fahrzeugparameter das waren,
haengt davon ab, ob vorher ``TVC6DOF.m`` lief (``VehicleParams.nominal()``) oder nur das
Modell geoeffnet wurde (``VehicleParams.preload()``).
"""
from __future__ import annotations

import itertools
from dataclasses import replace

import numpy as np

from .params import SimParams
from .sim import simulate


def tune_grid(base: SimParams, kp_values, ki_values, kd_values, seed: int | None = 0,
              printer=print) -> np.ndarray:
    """Liefert ein Array mit Zeilen ``[kp, ki, kd, maxHeight, tilt_end_deg]``."""
    rows = []
    n = 0
    for kp, ki, kd in itertools.product(kp_values, ki_values, kd_values):
        n += 1
        p = replace(base, control=replace(base.control, kp=kp, ki=ki, kd=kd), seed=seed)
        res = simulate(p)
        rows.append([kp, ki, kd, res.max_height, res.tilt_deg[-1]])
        if printer:
            printer(f"Sim {n}: kp={kp:.3f}, ki={ki:.3f}, kd={kd:.4f} -> maxHeight: {res.max_height:.3f} m, "
                    f"Kippwinkel Ende {res.tilt_deg[-1]:.1f} Grad")
    return np.array(rows)
