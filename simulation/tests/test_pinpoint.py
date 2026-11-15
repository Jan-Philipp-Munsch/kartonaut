"""Tests der Punktlande-Simulation (tvcsim/pinpoint.py): Mathematik, Filter, Führung und Nominalflüge."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from tvcsim.pinpoint import (AxisKF, G, PinpointConfig, ignition_table, landing_1d, profile, qexp, qmul, quat_from_R,
                             rotmat, run, summarize, thrust_moments, vertical_law)


def test_rotmat_matches_scipy_and_roundtrip():
    rng = np.random.default_rng(0)
    q = rng.standard_normal((50, 4))
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    R = rotmat(q)
    ref = Rotation.from_quat(q[:, [1, 2, 3, 0]]).as_matrix()      # scipy: Skalar zuletzt
    assert np.allclose(R, ref, atol=1e-12)
    q2 = quat_from_R(R)
    sign = np.sign(np.sum(q * q2, axis=1, keepdims=True))
    assert np.allclose(q, sign * q2, atol=1e-9)


def test_quaternion_integration_constant_rate():
    """q <- q (x) exp(w dt) dreht mit einer Koerperrate um z in 1 s um genau den Winkel."""
    q = np.array([[1.0, 0.0, 0.0, 0.0]])
    w = np.array([[0.0, 0.0, 0.5]])
    for _ in range(250):
        q = qmul(q, qexp(w * 0.004))
    R = rotmat(q)[0]
    assert np.arctan2(R[1, 0], R[0, 0]) == pytest.approx(0.5, abs=1e-9)


def test_axis_kf_estimates_position_velocity_and_bias():
    """Wahre Bewegung mit konstanter Geschwindigkeit, Beschleunigungsmessung mit Nullpunktfehler, Position
    wird gemessen: der Filter findet Geschwindigkeit und Fehler."""
    cfg = PinpointConfig()
    kf = AxisKF(1, cfg)
    rng = np.random.default_rng(1)
    dt, v_true, bias = 0.004, 1.5, 0.4
    mask = np.ones((1, 3), bool)
    for k in range(5000):
        kf.predict(np.full((1, 3), bias), dt)
        if k % 5 == 0:
            z = v_true * (k + 1) * dt + 0.02 * rng.standard_normal((1, 3))
            kf.update_pos(z, 0.02 ** 2, mask)
    assert np.allclose(kf.v, v_true, atol=0.1)
    assert np.allclose(kf.b, bias, atol=0.1)
    assert np.all(kf.Ppp > 0) and np.all(kf.Pvv > 0) and np.all(kf.Pbb > 0)


def test_vertical_law_reduces_to_zem_zev_for_constant_thrust():
    """Mit konstantem Schub ist das geplante lineare Profil die Zero-Effort-Miss/-Velocity-Regel."""
    cfg = PinpointConfig(v_final=0.5)
    from types import SimpleNamespace
    tg = np.arange(0.0, 3.0 + 1e-9, 0.005)
    F = np.full_like(tg, 20.0)

    def rc(y):
        seg = 0.5 * (y[1:] + y[:-1]) * np.diff(tg)
        return np.concatenate([np.cumsum(seg[::-1])[::-1], [0.0]])

    mom = SimpleNamespace(t=tg, te=3.0, tb=3.15, F=F, M0=rc(F), M1=rc(tg * F), M2=rc(tg * tg * F))
    h, v, m, T = 20.0, -12.0, 1.0, 2.0                       # t_burn = 1 s, also noch 2 s
    f = float(vertical_law(cfg, mom, np.array(h), np.array(v), np.array(1.0), 1.0, m, 0.0))
    zem = -(h + v * T - 0.5 * G * T * T)
    zev = -cfg.v_final - (v - G * T)
    a_t = 6.0 * zem / T ** 2 - 2.0 * zev / T
    assert f == pytest.approx(m * a_t / 20.0, rel=1e-3)


def test_landing_1d_soft_with_throttle_hard_without():
    """Aus 6 m Hoehe und Stillstand setzt die 0,8-kg-Rakete mit Drossel weich auf, ohne Drossel nicht."""
    with_thr = PinpointConfig(m_land=0.8, f_min=0.35)
    without = PinpointConfig(m_land=0.8, f_min=1.0)
    assert float(landing_1d(with_thr, np.array(6.0), np.array(0.0))) < 2.5
    assert float(landing_1d(without, np.array(6.0), np.array(0.0))) > 6.0


def test_ignition_table_higher_for_faster_descent():
    v, h, j = ignition_table(PinpointConfig(m_land=0.6, f_min=0.5))
    sel = (v >= 10) & (v <= 30)
    assert np.all(np.diff(h[sel]) > 0)
    assert j[(v >= 8) & (v <= 16)].max() < 2.5      # in diesem Bereich reicht das Bremsvermoegen mit Reserve
    mom = thrust_moments(PinpointConfig())
    assert mom.M0[0] == pytest.approx(38.6, rel=0.03)     # Gesamtimpuls der E12 bis kurz vor Brennschluss


@pytest.mark.parametrize("name", ["wechsel", "huepfer"])
def test_nominal_flight_lands_on_target(name):
    """Ohne Streuung, Rauschen und Wind: weich, aufrecht und auf dem Punkt."""
    res = run(profile(name, scatter=0.0, noise=0.0, wind10=0.0), n=1, seed=0)
    assert res["landed"][0] and not res["relift"][0]
    assert res["vz"][0] < 2.5 and res["vh"][0] < 0.05
    assert res["tilt"][0] < 0.5 and res["miss"][0] < 0.05
    assert res["burning"][0]                      # aufgesetzt vor dem Brennschluss, nicht aus der Luft gefallen


def test_two_motors_side_by_side_need_cant_or_trim():
    """Zwei Motoren je 12,5 mm neben der Kardanachse: ohne Ausgleich reicht der Kardan nicht; schraeg durch
    den Schwerpunkt eingebaut oder mit vorgesteuertem Trimm landet die Rakete nominal auf dem Punkt."""
    base = dict(scatter=0.0, noise=0.0, wind10=0.0, motor_offset=0.0125)
    plain = run(profile("wechsel", **base), n=1, seed=0)
    cant = run(profile("wechsel", motor_cant=True, **base), n=1, seed=0)
    trim = run(profile("wechsel", motor_ff=True, gim_max=12.0, **base), n=1, seed=0)
    assert plain["tilt"][0] > 10.0 or plain["miss"][0] > 2.0
    for res in (cant, trim):
        assert res["miss"][0] < 0.1 and res["tilt"][0] < 3.0 and res["vz"][0] < 2.5


def test_guidance_flies_to_offset_target():
    """Zielpunkt 2 m oestlich des Starts, nominal: die seitliche Fuehrung bringt die Rakete dorthin."""
    res = run(profile("wechsel", scatter=0.0, noise=0.0, wind10=0.0, target_e=2.0), n=1, seed=0)
    assert res["miss"][0] < 0.3 and res["vz"][0] < 2.5 and res["tilt"][0] < 8.0


def test_crosswind_tips_the_nose_downwind_without_thrust():
    """Die Seitenflaeche liegt ueber dem Schwerpunkt: im antriebslosen Flug drueckt Seitenwind die Spitze
    mit dem Wind. Das ist der Grund, warum der freie Fall die Lage kostet."""
    cfg = profile("langsam", scatter=0.0, noise=0.0, wind10=3.0, gust_frac=0.0)
    res = run(cfg, n=4, seed=3)
    calm = run(cfg.with_(wind10=0.0), n=4, seed=3)
    assert np.all(res["tilt_ign"] > 15.0)
    assert np.all(calm["tilt_ign"] < 3.0)


def test_monte_carlo_is_reproducible_and_summarized():
    cfg = profile("huepfer", wind10=1.5)
    a = summarize(run(cfg, n=40, seed=5))
    b = summarize(run(cfg, n=40, seed=5))
    assert all(a[k] == b[k] or (np.isnan(a[k]) and np.isnan(b[k])) for k in a)
    assert a["soft"] > 0.7 and a["miss_p50"] < 0.6
