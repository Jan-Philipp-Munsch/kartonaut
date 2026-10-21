import math

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from tvcsim.dynamics import (body_to_inertial, body_x_axis_inertial, conjugate, eom, hamilton,
                             thrust_body, tilt_deg)
from tvcsim.params import NoiseParams, SimParams, VehicleParams
from tvcsim.sim import simulate


def _std_mul(p, q):
    """Uebliches Hamilton-Produkt p (x) q (Skalar zuerst)."""
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
                     w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def test_hamilton_is_standard_product():
    """hamilton(q, r) des Blocks ist das uebliche Produkt q (x) r (trotz der r-zuerst-Schreibweise)."""
    rng = np.random.default_rng(1)
    for _ in range(20):
        q, r = rng.standard_normal(4), rng.standard_normal(4)
        assert np.allclose(hamilton(q, r), _std_mul(q, r))


def test_body_to_inertial_matches_scipy():
    """q des Blocks dreht Koerper -> inertial (aktiv, wie scipy Rotation.apply)."""
    rng = np.random.default_rng(2)
    for _ in range(20):
        rv = rng.standard_normal(3)
        rot = Rotation.from_rotvec(rv)
        x, y, z, w = rot.as_quat()
        q = np.array([w, x, y, z])       # Skalar zuerst
        v = rng.standard_normal(3)
        assert np.allclose(body_to_inertial(q, v), rot.apply(v))
        assert np.allclose(hamilton(hamilton(conjugate(q), [0, *v]), q)[1:], rot.inv().apply(v))


def test_kinematics_constant_rate_matches_scipy():
    """qd = 0.5*hamilton(q,[0;w]) mit konstantem w ueber 1 s integriert, gegen Rotation verglichen."""
    w = np.array([0.3, -0.5, 0.8])
    q = np.array([1.0, 0.0, 0.0, 0.0])
    h = 1e-4
    for _ in range(int(1 / h)):
        f = lambda q_: 0.5 * hamilton(q_, np.array([0.0, *w]))
        k1 = f(q); k2 = f(q + 0.5 * h * k1); k3 = f(q + 0.5 * h * k2); k4 = f(q + h * k3)
        q = q + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        q /= np.linalg.norm(q)
    # Koerperachse x im Inertialsystem nach 1 s Drehung mit Koerperrate w
    expected = Rotation.from_rotvec(w).apply([1.0, 0.0, 0.0])
    assert np.allclose(body_x_axis_inertial(q), expected, atol=1e-6)


def test_tvc_rotation_identity_and_direction():
    T = 10.0
    assert np.allclose(thrust_body(T, 0, 0), [T, 0, 0])
    Tb = thrust_body(T, 5.0, 0.0)
    assert Tb[0] > 0 and Tb[2] < 0 and abs(Tb[1]) < 1e-12   # th_y > 0 kippt den Schub nach -z
    Tb = thrust_body(T, 0.0, 5.0)
    assert Tb[0] > 0 and Tb[1] > 0 and abs(Tb[2]) < 1e-12   # th_z > 0 kippt nach +y
    assert math.isclose(np.linalg.norm(thrust_body(T, 3.0, -4.0)), T)


def test_hover_equilibrium():
    """T = m g, keine Fehlausrichtung, keine Auslenkung: rdd = 0, wd = 0, qd = 0."""
    v = VehicleParams()
    m_fuel_g = 60.0
    m = v.m_dry + m_fuel_g / 1000
    q = np.array([1.0, 0, 0, 0])
    rdd, wd, qd, Mb, Tb, m_out = eom(v.as_eom_params(), m_fuel_g, 0.0, 0.0, m * v.g, q, np.zeros(3))
    assert math.isclose(m_out, m)
    assert np.allclose(rdd, 0, atol=1e-12)
    assert np.allclose(wd, 0, atol=1e-12)
    assert np.allclose(qd, 0, atol=1e-12)
    assert np.allclose(Mb, 0, atol=1e-12)


def test_moment_signs():
    """Mb = cross([-l, mis_y, mis_z], Tb): th_y > 0 -> My < 0, th_z > 0 -> Mz < 0,
    mis_y > 0 -> Mz < 0, mis_z > 0 -> My > 0."""
    v = VehicleParams()
    q = np.array([1.0, 0, 0, 0]); w = np.zeros(3); T = 10.0
    _, wd, _, Mb, _, _ = eom(v.as_eom_params(), 0.0, 5.0, 0.0, T, q, w)
    assert Mb[1] < 0 and abs(Mb[0]) < 1e-12 and abs(Mb[2]) < 1e-12 and wd[1] < 0
    assert math.isclose(Mb[1], -v.l * T * math.sin(math.radians(5.0)))
    _, wd, _, Mb, _, _ = eom(v.as_eom_params(), 0.0, 0.0, 5.0, T, q, w)
    assert Mb[2] < 0 and abs(Mb[1]) < 1e-12 and wd[2] < 0
    p = VehicleParams(mis_y=0.01).as_eom_params()
    _, _, _, Mb, _, _ = eom(p, 0.0, 0.0, 0.0, T, q, w)
    assert math.isclose(Mb[2], -0.01 * T) and abs(Mb[1]) < 1e-12
    p = VehicleParams(mis_z=0.01).as_eom_params()
    _, _, _, Mb, _, _ = eom(p, 0.0, 0.0, 0.0, T, q, w)
    assert math.isclose(Mb[1], 0.01 * T) and abs(Mb[2]) < 1e-12


def test_gravity_only_free_fall():
    v = VehicleParams()
    rdd, *_ = eom(v.as_eom_params(), 0.0, 0.0, 0.0, 0.0, np.array([1.0, 0, 0, 0]), np.zeros(3))
    assert np.allclose(rdd, [-v.g, 0, 0])


def test_tilt_from_quaternion():
    rot = Rotation.from_rotvec([0, math.radians(20), 0])
    x, y, z, w = rot.as_quat()            # q im Block dreht Koerper -> inertial
    assert math.isclose(tilt_deg(np.array([w, x, y, z])), 20.0, abs_tol=1e-9)


@pytest.mark.parametrize("controller", ["simulink", "firmware"])
def test_quaternion_norm_stays_one(controller):
    p = SimParams(vehicle=VehicleParams(static_error_y=1.0, static_error_z=0.5, mis_y=0.002),
                  noise=NoiseParams(enabled=True), controller=controller, t_end=3.0, seed=3, substeps=5)
    res = simulate(p)
    assert np.max(np.abs(np.linalg.norm(res.q, axis=1) - 1.0)) < 1e-12
    assert np.all(np.isfinite(res.r))


def test_ground_contact_ends_run_at_landing():
    """Mit Boden sinkt die Rakete nie unter 0 und der Lauf endet bei der Landung, vor t_end."""
    from tvcsim.params import SimParams, VehicleParams
    from tvcsim.sim import simulate
    p = SimParams(vehicle=VehicleParams.preload(), t_end=12.0, seed=1, substeps=5)
    res = simulate(p)
    assert res.r[:, 0].min() >= -1e-9
    assert res.extra["landed"] and res.t[-1] < 12.0
    assert res.max_height > 5.0
    res2 = simulate(p.with_(ground=False))
    assert res2.t[-1] == 12.0 and res2.r[-1, 0] < 0.0
