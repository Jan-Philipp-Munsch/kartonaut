"""Bewegungsgleichungen: Port des MATLAB-Function-Blocks *Equations of Motion* (chart_44).

Koordinaten wie im Simulink-Modell: Koerperachse x ist die Laengsachse (Schubrichtung),
inertiale x-Achse zeigt nach oben (Hoehe), y ist Downrange, z Crossrange.

Die Quaternion-Konvention ist die des Blocks: ``hamilton(q, r)`` ist dort zwar mit ``r``
zuerst hingeschrieben, ergibt aber das uebliche Produkt ``q (x) r``. Damit ist
``qd = 0.5 * q (x) [0; w]`` die Standard-Kinematik fuer eine Quaternion, die Koerper -> inertial
dreht (Skalar zuerst), und ``Ti = q (x) [0; Tb] (x) q*`` die aktive Drehung des Schubvektors
ins Inertialsystem, gleich ``scipy Rotation.apply``. ``tests/test_dynamics.py`` prueft das.
"""
from __future__ import annotations

import math

import numpy as np


def hamilton(q, r):
    """Exakt die Funktion aus dem Simulink-Block (ergibt das uebliche Produkt q (x) r)."""
    return np.array([
        r[0] * q[0] - r[1] * q[1] - r[2] * q[2] - r[3] * q[3],
        r[0] * q[1] + r[1] * q[0] - r[2] * q[3] + r[3] * q[2],
        r[0] * q[2] + r[1] * q[3] + r[2] * q[0] - r[3] * q[1],
        r[0] * q[3] - r[1] * q[2] + r[2] * q[1] + r[3] * q[0],
    ])


def conjugate(q):
    return np.array([q[0], -q[1], -q[2], -q[3]])


def tvc_rotation(th_y_deg: float, th_z_deg: float) -> np.ndarray:
    """``gCb = Rz(th_z) * Ry(th_y)`` mit den Matrizen aus dem Block (Winkel in Grad)."""
    cy, sy = math.cos(math.radians(th_y_deg)), math.sin(math.radians(th_y_deg))
    cz, sz = math.cos(math.radians(th_z_deg)), math.sin(math.radians(th_z_deg))
    Rz = np.array([[cz, sz, 0.0], [-sz, cz, 0.0], [0.0, 0.0, 1.0]])
    Ry = np.array([[cy, 0.0, -sy], [0.0, 1.0, 0.0], [sy, 0.0, cy]])
    return Rz @ Ry


def thrust_body(T: float, th_y_deg: float, th_z_deg: float) -> np.ndarray:
    """Schubvektor im Koerpersystem ``Tb = gCb' * [T; 0; 0]``."""
    return tvc_rotation(th_y_deg, th_z_deg).T @ np.array([T, 0.0, 0.0])


def body_to_inertial(q, v):
    """Koerpervektor ins Inertialsystem (Konvention des Blocks)."""
    return hamilton(hamilton(q, np.array([0.0, v[0], v[1], v[2]])), conjugate(q))[1:]


def eom(params, m_fuel_g, th_y, th_z, T, q_in, w, rd=None):
    """``[rdd, wd, qd, Mb, Tb, m] = EOM(params, m_fuel, th_y, th_z, T, q_in, w1, w2, w3)``.

    params = (Ix, Iy, Iz, g, l, mis_y, mis_z, m_dry[, cd_a, rho]); Winkel in Grad, w in rad/s.
    Mit ``cd_a > 0`` und ``rd`` (inertiale Geschwindigkeit) kommt der Luftwiderstand
    ``D = -1/2 rho cd_a |rd| rd`` dazu (Erweiterung gegenueber Simulink, kein Moment).
    """
    Ix, Iy, Iz, g, l, mis_y, mis_z, m_dry = params[:8]
    cd_a, rho = (params[8], params[9]) if len(params) > 8 else (0.0, 1.2)
    m = m_dry + m_fuel_g / 1000.0
    wx, wy, wz = w

    Tb = thrust_body(T, th_y, th_z)
    r = np.array([-l, mis_y, mis_z])
    Mb = np.cross(r, Tb)

    Ti = body_to_inertial(q_in, Tb)
    rdd = np.array([Ti[0] / m - g, Ti[1] / m, Ti[2] / m])
    if cd_a > 0.0 and rd is not None:
        v = np.asarray(rd, dtype=float)
        rdd = rdd - 0.5 * rho * cd_a * np.linalg.norm(v) * v / m

    wd = np.array([
        (Mb[0] + (Iy - Iz) * wy * wz) / Ix,
        (Mb[1] + (Iz - Ix) * wx * wz) / Iy,
        (Mb[2] + (Ix - Iy) * wx * wy) / Iz,
    ])
    qd = 0.5 * hamilton(q_in, np.array([0.0, wx, wy, wz]))
    return rdd, wd, qd, Mb, Tb, m


def body_x_axis_inertial(q) -> np.ndarray:
    """Richtung der Laengsachse im Inertialsystem (Einheitsvektor)."""
    return body_to_inertial(q, np.array([1.0, 0.0, 0.0]))


def tilt_deg(q) -> float:
    """Winkel zwischen Laengsachse und Lotrechter in Grad."""
    x = body_x_axis_inertial(q)
    return math.degrees(math.acos(max(-1.0, min(1.0, x[0]))))


def rotation_matrix_body_to_inertial(q) -> np.ndarray:
    return np.column_stack([body_to_inertial(q, e) for e in np.eye(3)])


def euler_deg(q) -> tuple[float, float, float]:
    """Kippwinkel der Laengsachse um die inertialen y- und z-Achsen sowie Rollwinkel, in Grad.

    pitch_y: Drehung der Laengsachse in der x-z-Ebene (positiv: Spitze nach +z),
    pitch_z: in der x-y-Ebene (positiv: Spitze nach -y), roll: um die Laengsachse.
    """
    R = rotation_matrix_body_to_inertial(q)
    x = R[:, 0]
    pitch_y = math.degrees(math.atan2(-x[2], x[0]))
    pitch_z = math.degrees(math.atan2(x[1], x[0]))
    roll = math.degrees(math.atan2(R[2, 1], R[1, 1]))
    return pitch_y, pitch_z, roll
