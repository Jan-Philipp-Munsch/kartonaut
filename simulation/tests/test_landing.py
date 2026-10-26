import math

import numpy as np

from tvcsim.dynamics import eom
from tvcsim.landing import (IgnitionTable, LandingPlanner, burn_1d, impact_cost, ignition_altitude,
                            load_thrust_curve, net_braking_dv)
from tvcsim.motors import ThrustModel
from tvcsim.params import MotorParams, NoiseParams, SimParams, VehicleParams
from tvcsim.sim import simulate


def test_drag_decelerates_in_direction_of_motion():
    v = VehicleParams.light(0.7)
    params = v.as_eom_params()
    q = np.array([1.0, 0, 0, 0])
    rdd_no, *_ = eom(params[:8], 28.0, 0.0, 0.0, 0.0, q, np.zeros(3), np.array([-20.0, 0, 0]))
    rdd, *_ = eom(params, 28.0, 0.0, 0.0, 0.0, q, np.zeros(3), np.array([-20.0, 0, 0]))
    assert math.isclose(rdd_no[0], -9.81)
    assert rdd[0] > rdd_no[0]                       # Fall wird gebremst
    expected = 0.5 * 1.2 * 0.003 * 400 / 0.7
    assert math.isclose(rdd[0] - rdd_no[0], expected, rel_tol=1e-6)
    rdd_up, *_ = eom(params, 28.0, 0.0, 0.0, 0.0, q, np.zeros(3), np.array([20.0, 0, 0]))
    assert rdd_up[0] < rdd_no[0]                    # Steigen wird gebremst


def test_net_braking_and_table_consistency():
    assert 15 < net_braking_dv("E12", 0.761) < 17
    assert net_braking_dv("E12", 0.6) > net_braking_dv("E12", 0.7)
    tab = IgnitionTable("E12", 0.6, cd_a=0.003, fuel_kg=0.028)
    # Gegenprobe: aus der Tabellenhoehe gezuendet kommt die Rakete mit |v| <= v_tol an
    for v0 in (-10.0, -25.0):
        v_td, _, _ = burn_1d(tab.t_curve, tab.f_curve, 0.6, tab.h_ign(v0), v0, cd_a=0.003, fuel_kg=0.028)
        assert -0.6 < v_td <= 0.0
    assert tab.feasible_speed() >= 30


def test_impact_cost_hop_and_free_fall():
    t, f = load_thrust_curve("E12")
    # knapp ueber dem Boden gezuendet: Aufsetzen, der Schwanz hebt die Rakete wieder, harter Fall
    J_low, contacts = impact_cost(t, f, 0.7, 1.0, -5.0, cd_a=0.003, fuel_kg=0.028)
    assert len(contacts) >= 2 and J_low > 15
    # sehr hoch gezuendet: Stopp in der Luft, dann freier Fall
    J_high, contacts = impact_cost(t, f, 0.7, 120.0, -5.0, cd_a=0.003, fuel_kg=0.028)
    assert len(contacts) == 1 and J_high > 20
    # dazwischen gibt es ein Minimum
    Js = [impact_cost(t, f, 0.7, h, -20.0, cd_a=0.003, fuel_kg=0.028)[0] for h in (20, 30, 35, 40, 50)]
    assert min(Js) < Js[0] and min(Js) < Js[-1]


def test_planner_ignites_near_cost_minimum():
    pl = LandingPlanner("E12", 0.7, cd_a=0.003, fuel_kg=0.028, igniter_delay=0.1, dt_ctrl=0.01)
    h, v = 60.8, 0.0
    best = (1e9, 0)
    h_ign = None
    for _ in range(3000):
        v += (-9.81 + 0.5 * 1.2 * 0.003 * v * v / 0.7) * 0.01
        h += v * 0.01
        if h <= 0:
            break
        if v < -2:
            J = pl.cost(*pl.predicted(h, v, 0.1))
            if J < best[0]:
                best = (J, h)
            if h_ign is None and pl.should_ignite(h, v):
                h_ign = h
    assert h_ign is not None
    assert abs(h_ign - best[1]) < 1.5
    assert 3 < best[0] < 6                           # Studie: ~4,8 m/s bei 0,7 kg aus dem E12-Gipfel


def test_sixdof_landing_mode_runs_and_hops_are_recorded():
    m = 0.7
    p = SimParams(vehicle=VehicleParams.light(m), controller="firmware",
                  motor=MotorParams(fuel_model="impulse", second_mode="landing", landing_alt_sigma=0, landing_vz_sigma=0),
                  noise=NoiseParams(accel_model="specific_force", enabled=False), t_end=30.0, seed=0)
    p.firmware.MASS_KG = m
    p.firmware.MOMENT_ARM_M = 0.242
    res = simulate(p)
    e = res.extra
    assert e["landed"] and e["t_ignite2"] is not None
    assert 55 < res.max_height < 66
    assert 35 < e["h_ignite2"] < 40 and -22 < e["v_ignite2"] < -19
    assert len(e["contacts"]) >= 1
    assert -7 < e["v_land"] < -3                     # 1D-Studie: 4,8 m/s
    assert e["tilt_land_deg"] < 5
    # Motor 2 hat gebrannt: Schub nach der Zuendung, am Ende wieder 0
    k = np.searchsorted(res.t, e["t_ignite2"] + 0.6)
    assert res.T[k] > 5 and res.T[-1] == 0.0


def test_thrust_model_second_mode_landing_waits_for_ignition():
    tm = ThrustModel(MotorParams(second_mode="landing", fuel_model="impulse"))
    assert tm.thrust(7.3 + 0.5, 0.01) == 0.0          # keine Zuendung nach Zeit
    tm.ignite_second(10.0)
    assert tm.thrust(10.535, 0.01) > 28.0
    assert math.isclose(tm.fuel_mass_g(9.0, 0.01), 28.0)
