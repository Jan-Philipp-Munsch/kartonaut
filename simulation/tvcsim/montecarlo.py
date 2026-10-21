"""Port von ``TVC6DOF.m``: 100 Laeufe mit gestreuten Fahrzeugparametern."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from .params import MonteCarloParams, ServoParams, SimParams, VehicleParams
from .sim import SimResult, simulate


def draw_vehicle(nominal: VehicleParams, mc: MonteCarloParams, servo: ServoParams,
                 rng: np.random.Generator) -> VehicleParams:
    """``x_mc = x_n + randn * x_v`` wie in TVC6DOF.m (``_v`` ist dort die Abweichung je sigma)."""
    rn = rng.standard_normal
    tau_n = servo.tau if nominal.servo_delay is None else nominal.servo_delay
    return replace(
        nominal,
        Ix=nominal.Ix + rn() * mc.Ix_v,
        Iy=nominal.Iy + rn() * mc.Iy_v,
        Iz=nominal.Iz + rn() * mc.Iz_v,
        m_dry=nominal.m_dry + rn() * mc.m_dry_v,
        l=nominal.l + rn() * mc.l_v,
        servo_delay=tau_n + rn() * mc.servo_delay_v,
        mis_y=rn() * mc.mis_y_v,
        mis_z=rn() * mc.mis_z_v,
        static_error_y=rn() * mc.static_error_y_v,
        static_error_z=rn() * mc.static_error_z_v,
    )


def run_montecarlo(base: SimParams, mc: MonteCarloParams, seed: int | None = 0,
                   progress=None) -> list[SimResult]:
    rng = np.random.default_rng(seed)
    results = []
    for k in range(mc.runs):
        veh = draw_vehicle(base.vehicle, mc, base.servo, rng)
        p = replace(base, vehicle=veh, t_end=mc.t_end, seed=int(rng.integers(0, 2**31 - 1)))
        res = simulate(p)
        results.append(res)
        if progress:
            progress(k + 1, mc.runs, res)
    return results


def summarize(results: list[SimResult]) -> dict:
    maxh = np.array([r.max_height for r in results])
    tilt_end = np.array([r.tilt_deg[-1] for r in results])
    lateral = np.array([np.hypot(r.r[-1, 1], r.r[-1, 2]) for r in results])
    stable = tilt_end < 30.0
    return {"runs": len(results), "maxHeight_mean": float(maxh.mean()), "maxHeight_std": float(maxh.std()),
            "maxHeight_min": float(maxh.min()), "maxHeight_max": float(maxh.max()),
            "tilt_end_median": float(np.median(tilt_end)), "lateral_end_median": float(np.median(lateral)),
            "stable_fraction": float(stable.mean())}
