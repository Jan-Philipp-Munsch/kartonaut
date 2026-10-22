import math

import numpy as np

from tvcsim.landing import load_thrust_curve
from tvcsim.params import ThrottleParams
from tvcsim.throttle import ThrottleLandingController, simulate_landing_1d, stop_height, throttle_factor


def test_throttle_factor_linear_and_clamped():
    assert throttle_factor(0.0, 0.5) == 1.0
    assert throttle_factor(1.0, 0.5) == 0.5
    assert math.isclose(throttle_factor(0.5, 0.3), 0.65)
    assert throttle_factor(-1.0, 0.5) == 1.0 and throttle_factor(2.0, 0.5) == 0.5


def test_stop_height_monotone_and_lag_aware():
    t, f = load_thrust_curve("E12")
    hs_fast = stop_height(t, f, 0.7, 40.0, -20.0, 0.003, 1.2, 0.028)
    hs_slow = stop_height(t, f, 0.7, 40.0, -10.0, 0.003, 1.2, 0.028)
    assert hs_slow > hs_fast > 0
    # mit gedrosselten Pads (f_now 0,5) kommt der Schub spaeter: Stopp tiefer
    hs_lag = stop_height(t, f, 0.7, 40.0, -20.0, 0.003, 1.2, 0.028, f_now=0.5, act_tau=0.15)
    assert hs_lag < hs_fast
    # zu schnell: kein Stopp
    assert stop_height(t, f, 0.7, 10.0, -40.0, 0.003, 1.2, 0.028) <= 0


def test_controller_phases():
    tp = ThrottleParams(enabled=True, f_min=0.5)
    c = ThrottleLandingController("E12", 0.7, tp, 0.003, 1.2, 0.028, 0.1, 0.01)
    # vor dem Schub und in der Spitze: Pads draussen
    assert c.throttle_command(0.05, 30.0, -20.0) == 0.0
    assert c.throttle_command(0.5, 25.0, -18.0) == 0.0
    # im Schwanz, langsam und hoch (viel Zeit, wenig Weg): drosseln
    u = c.throttle_command(1.5, 30.0, -3.0, a_meas=15.0)
    assert u > 0.5
    # im Schwanz, tief und schnell: voller Schub
    assert c.throttle_command(1.5, 5.0, -15.0, a_meas=15.0) == 0.0
    # knapp am Boden: Schubabbruch
    assert c.throttle_command(2.0, 0.1, -0.6) == 1.0
    # Endphase: Sinkrate halten liefert Werte zwischen den Grenzen
    c2 = ThrottleLandingController("E12", 0.7, tp, 0.003, 1.2, 0.028, 0.1, 0.01)
    u2 = c2.throttle_command(2.0, 0.6, -0.5)
    assert 0.0 <= u2 <= 1.0


def test_ignition_with_reserve_before_cost_minimum():
    tp = ThrottleParams(enabled=True, f_min=0.5)
    c = ThrottleLandingController("E12", 0.7, tp, 0.003, 1.2, 0.028, 0.1, 0.01)
    h, v = 60.8, 0.0
    h_ign = None
    for _ in range(3000):
        v += (-9.81 + 0.5 * 1.2 * 0.003 * v * v / 0.7) * 0.01
        h += v * 0.01
        if h <= 0:
            break
        if h_ign is None and c.should_ignite(h, v):
            h_ign = h
            break
    # 0,7 kg aus dem E12-Gipfel: der geplante schwache Motor kann nie stoppen -> Rueckfall auf das
    # Kostenminimum wie ohne Drossel (37,6 m); bei 0,6 kg greift die Reserve und zuendet hoeher
    assert h_ign is not None and 39 < h_ign < 43
    c6 = ThrottleLandingController("E12", 0.6, tp, 0.003, 1.2, 0.028, 0.1, 0.01)
    h, v = 88.3, 0.0
    h6 = None
    for _ in range(3000):
        v += (-9.81 + 0.5 * 1.2 * 0.003 * v * v / 0.6) * 0.01
        h += v * 0.01
        if h <= 0:
            break
        if c6.should_ignite(h, v):
            h6 = h
            break
    assert h6 is not None and 48 < h6 < 54                 # ohne Drossel: 44,3 m


def test_landing_1d_robust_at_06kg():
    # 0,6 kg aus dem E12-Gipfel (88 m): mit Drossel f_min 0,5 bleibt das Aufsetzen bei +-10 % Schub um 2 m/s
    for scale in (0.9, 1.0, 1.1):
        res = simulate_landing_1d(88.3, 0.6, ThrottleParams(enabled=True, f_min=0.5), truth_scale=scale)
        assert res["landed"]
        assert len(res["contacts"]) == 1
        assert -2.6 < res["v_land"] <= 0.0
    # schwache Drossel (f_min 0,7) kann einen starken Motor nicht wegnehmen: Stopp in der Luft, Fall
    res = simulate_landing_1d(88.3, 0.6, ThrottleParams(enabled=True, f_min=0.7), truth_scale=1.1)
    assert res["v_land"] < -5.0
