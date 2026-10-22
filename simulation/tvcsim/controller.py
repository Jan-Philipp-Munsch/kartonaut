"""Zwei Regler mit derselben Schnittstelle.

``SimulinkController`` ist der Port des Teilsystems ``Controller`` (system_83 + chart_64):
``rot = int(w_est)`` in Grad (Integrator auf Root-Ebene), ``e = -0,01 * rot`` je Achse,
``u_i = kp e_i + ki int(e_i) + kd (-w_est_i)``, Integratoren werden bei ``secondburn/100`` s
zurueckgesetzt, dann ``Moments2Commands``.

``FirmwareController`` rechnet wie ``firmware/src/main.cpp`` + ``Control.cpp``:
``rot_deg += omega * dt``, PID auf ``rot/-100``, ``delta = asin(M / (l m |a|))``,
Servo-Grad = delta_deg * GAIN + OFFSET, mechanisches Fenster, Rundung auf ganze Grad.

Beide liefern das Kommando ``(th_y_com, th_z_com)`` in Grad in der Simulink-Konvention.
Zuordnung der Achsen: Firmware x (Yaw) <-> Simulink-Koerperachse y,
Firmware y (Pitch) <-> Simulink z, Firmware z (Roll) <-> Simulink x (Laengsachse).
"""
from __future__ import annotations

import math

import numpy as np

from .params import ControlParams, FirmwareParams


def moments_to_commands(T_est: float, Mx: float, My: float, Mz: float, l: float) -> tuple[float, float]:
    """Port von ``Moments2Commands`` (chart_64). ``Mx`` wird dort nicht benutzt."""
    T_est = T_est if T_est != 0.0 else 1e-12
    Tb = np.array([0.0, Mz / l, -My / l])
    y_clamped = min(max(Tb[2] / T_est, -1.0), 1.0)
    th_y = math.degrees(math.asin(y_clamped))
    denom = -T_est * math.cos(math.radians(th_y))
    denom = denom if denom != 0.0 else -1e-12
    z_clamped = min(max(Tb[1] / denom, -1.0), 1.0)
    th_z = math.degrees(math.asin(z_clamped))
    return th_y, th_z


class SimulinkController:
    def __init__(self, params: ControlParams, l_ctrl: float):
        self.p = params
        self.l = l_ctrl
        self.rot = np.zeros(3)        # Integrator1 (Root): int w_est, Grad
        self.e_int = np.zeros(3)      # Integratoren im Controller: int e
        self._w_prev = np.zeros(3)
        self._e_prev = np.zeros(3)
        self._reset_done = False
        self.last = {}

    def reset_time(self) -> float:
        return self.p.secondburn / 100.0 if self.p.dt == 0.01 else self.p.secondburn * self.p.dt

    def moments(self, t: float, w_est_dps) -> np.ndarray:
        """Momentenforderung ``[Mx, My, Mz]`` zum Takt t (vor Moments2Commands)."""
        dt = self.p.dt
        if t > 0.0:
            # rot ist das Integral des ZOH-Signals w_est: exakt stueckweise linear
            self.rot = self.rot + self._w_prev * dt
            # int e ueber ein stueckweise lineares rot: Trapez ist exakt
            self.e_int = self.e_int + self.p.error_scale * (self._rot_prev + 0.5 * self._w_prev * dt) * dt
        if (not self._reset_done) and t >= self.reset_time() - 1e-9:
            self.e_int = np.zeros(3)
            self._reset_done = True
        w = np.asarray(w_est_dps, dtype=float)
        e = self.p.error_scale * self.rot
        u = self.p.kp * e + self.p.ki * self.e_int + self.p.kd * (-w)
        self._w_prev = w
        self._rot_prev = self.rot.copy()
        self.last = {"rot": self.rot.copy(), "e_int": self.e_int.copy(), "u": u.copy()}
        return u

    _rot_prev = np.zeros(3)

    def step(self, t: float, w_est_dps, q_est, T_est: float, **_) -> tuple[float, float]:
        u = self.moments(t, w_est_dps)
        th_y, th_z = moments_to_commands(T_est, u[0], u[1], u[2], self.l)
        self.last.update({"th_y_com": th_y, "th_z_com": th_z, "T_est": T_est})
        return th_y, th_z


class FirmwareController:
    """Port von ``Control_updatePY`` mit der Winkelintegration aus ``main.cpp``."""

    def __init__(self, fw: FirmwareParams, dt: float):
        self.fw = fw
        self.dt = dt
        self.rot_deg = np.zeros(3)        # main.cpp: x = Yaw, y = Pitch, z = Roll
        self.rot_int_deg_s = np.zeros(3)  # Control.cpp: static Integrator
        self.a_norm_filt = fw.G_MS2       # main.cpp: init G_MS2
        self.last = {}

    @staticmethod
    def sim_to_fw(v_sim) -> np.ndarray:
        """Simulink-Achsen (x laengs, y, z) -> Firmware (x Yaw, y Pitch, z Roll)."""
        return np.array([v_sim[1], v_sim[2], v_sim[0]], dtype=float)

    def update_a_norm(self, a_norm: float) -> None:
        """Sensors.cpp: ``a_norm_filt += (|a| - a_norm_filt) * A_NORM_ALPHA``."""
        self.a_norm_filt += (a_norm - self.a_norm_filt) * self.fw.A_NORM_ALPHA

    def moments_fw(self, omega_fw_dps) -> np.ndarray:
        """Geforderte Momente ``[yaw, pitch]`` in N m, inkl. Integrationsschritt von main.cpp."""
        fw = self.fw
        omega = np.asarray(omega_fw_dps, dtype=float)
        self.rot_deg = self.rot_deg + omega * self.dt
        self.rot_int_deg_s = self.rot_int_deg_s + self.rot_deg * self.dt
        s = fw.PY_ERROR_SCALE
        m = (fw.PY_KP * (self.rot_deg / s) + fw.PY_KI * (self.rot_int_deg_s / s)
             + fw.PY_KD * (omega / s))
        return m[:2]

    def moments(self, t: float, w_est_dps) -> np.ndarray:
        """Wie ``SimulinkController.moments``: ``[Mx, My, Mz]`` in Simulink-Achsen."""
        yaw_m, pitch_m = self.moments_fw(self.sim_to_fw(w_est_dps))
        return np.array([0.0, yaw_m, pitch_m])

    def step(self, t: float, w_est_dps, q_est, T_est: float, a_norm: float | None = None, **_) -> tuple[float, float]:
        fw = self.fw
        if a_norm is not None:
            self.update_a_norm(a_norm)
        yaw_moment, pitch_moment = self.moments_fw(self.sim_to_fw(w_est_dps))

        denom = fw.MOMENT_ARM_M * fw.MASS_KG * max(self.a_norm_filt, fw.A_NORM_MIN)
        yaw_tvc_rad = math.asin(max(-0.99, min(0.99, yaw_moment / denom)))
        pitch_tvc_rad = math.asin(max(-0.99, min(0.99, pitch_moment / denom)))

        yaw_deg = math.degrees(yaw_tvc_rad) * fw.SERVO_YAW_GAIN + fw.SERVO_YAW_OFFSET
        pitch_deg = math.degrees(pitch_tvc_rad) * fw.SERVO_PITCH_GAIN + fw.SERVO_PITCH_OFFSET
        if fw.apply_window:
            yaw_deg = max(fw.SERVO_YAW_MIN_DEG, min(fw.SERVO_YAW_MAX_DEG, yaw_deg))
            pitch_deg = max(fw.SERVO_PITCH_MIN_DEG, min(fw.SERVO_PITCH_MAX_DEG, pitch_deg))
        if fw.quantize_servo:
            yaw_deg = float(max(0, min(180, round(yaw_deg))))
            pitch_deg = float(max(0, min(180, round(pitch_deg))))

        # zurueck in TVC-Grad (was der Kardan bei linearer Geometrie machen soll)
        yaw_tvc_deg = (yaw_deg - fw.SERVO_YAW_OFFSET) / fw.SERVO_YAW_GAIN
        pitch_tvc_deg = (pitch_deg - fw.SERVO_PITCH_OFFSET) / fw.SERVO_PITCH_GAIN
        th_y = fw.axis_sign_yaw * yaw_tvc_deg
        th_z = fw.axis_sign_pitch * pitch_tvc_deg
        self.last = {"rot": self.rot_deg.copy(), "u": np.array([0.0, yaw_moment, pitch_moment]),
                     "yaw_servo_deg": yaw_deg, "pitch_servo_deg": pitch_deg,
                     "a_norm_filt": self.a_norm_filt, "th_y_com": th_y, "th_z_com": th_z, "T_est": T_est}
        return th_y, th_z


def make_controller(name: str, control: ControlParams, firmware: FirmwareParams, l_ctrl: float,
                    sil=None, seed: int | None = None):
    if name == "simulink":
        return SimulinkController(control, l_ctrl)
    if name == "firmware":
        return FirmwareController(firmware, control.dt)
    if name == "sil":
        # C++-Flugkern der Firmware (tvcsim.sil); erst hier importiert, weil er einen Compiler braucht
        from .sil import SilController
        return SilController(sil, control.dt, seed=seed)
    raise ValueError(f"unbekannter Regler {name!r}")
