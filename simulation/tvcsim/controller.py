"""Zwei Regler mit derselben Schnittstelle.

``SimulinkController`` ist der Port des Teilsystems ``Controller`` (system_83 + chart_64):
``rot = int(w_est)`` in Grad (Integrator auf Root-Ebene), ``e = -0,01 * rot`` je Achse,
``u_i = kp e_i + ki int(e_i) + kd (-w_est_i)``, Integratoren werden bei ``secondburn/100`` s
zurueckgesetzt, dann ``Moments2Commands``.

``FirmwareController`` rechnet wie ``firmware/src/main.cpp`` + ``Control.cpp``:
``rot_deg += omega * dt``, PID auf ``rot/-100``, ``delta = asin(M / (l m |a|))``,
Servo-Grad = delta_deg * GAIN + OFFSET, mechanisches Fenster, Rundung auf ganze Grad.

``LQRController`` ist ein Zustandsregler mit Servopraediktor (``tvcsim.linear``): Zustand je
Querachse ``[rot, omega, M^, M^_dot, verzoegerte Kommandos, int(rot)]`` im Momentenbereich,
``M_c = -K x``; den Servozustand kennt er nur aus seinem Modell (kein Kardansensor), die
Saettigung (``sat_deg``) steckt im Praediktor. ``pd_model``/``pid_model`` sind der
Simulink-Regler mit Gewinnen aus derselben Kostenfunktion ohne Aktuatormodell.

Alle liefern das Kommando ``(th_y_com, th_z_com)`` in Grad in der Simulink-Konvention.
Zuordnung der Achsen: Firmware x (Yaw) <-> Simulink-Koerperachse y,
Firmware y (Pitch) <-> Simulink z, Firmware z (Roll) <-> Simulink x (Laengsachse).
"""
from __future__ import annotations

import math

import numpy as np

from .linear import (RAD, AxisPlant, LQRWeights, design_lqr, design_pd, gains_to_control_params)
from .params import ControlParams, FirmwareParams, LQRParams, ServoParams, VehicleParams


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


def design_plant(lqr: LQRParams, vehicle: VehicleParams, servo: ServoParams, dt: float) -> AxisPlant:
    """Entwurfsmodell des Reglers: ``None``-Felder von ``LQRParams`` kommen aus Fahrzeug und Servo."""
    tau_true = servo.tau if vehicle.servo_delay is None else vehicle.servo_delay
    return AxisPlant(I=lqr.I_ctrl if lqr.I_ctrl is not None else vehicle.Iy,
                     kappa=1.0,
                     wn=lqr.servo_wn if lqr.servo_wn is not None else servo.wn,
                     zeta=lqr.servo_zeta if lqr.servo_zeta is not None else servo.zeta,
                     tau=lqr.servo_tau if lqr.servo_tau is not None else tau_true,
                     dt=dt)


def design_weights(lqr: LQRParams, l_ctrl: float) -> LQRWeights:
    return LQRWeights(theta_max_deg=lqr.theta_max_deg, omega_max_dps=lqr.omega_max_dps,
                      M_max=l_ctrl * lqr.T_design * math.sin(math.radians(lqr.tvc_max_deg)),
                      int_max_deg_s=lqr.int_max_deg_s)


def model_pd_params(lqr: LQRParams, vehicle: VehicleParams, servo: ServoParams, dt: float,
                    integral: bool = False) -> ControlParams:
    """Gewinne des modellbasierten PD/PID als ``ControlParams`` (Simulink-Konvention)."""
    plant = design_plant(lqr, vehicle, servo, dt)
    K_theta, K_omega, K_int = design_pd(plant.I, design_weights(lqr, vehicle.l_ctrl), dt, integral)
    cp = gains_to_control_params(K_theta, K_omega, K_int, dt)
    return ControlParams(kp=cp.kp, ki=cp.ki, kd=cp.kd, dt=dt, secondburn=10 ** 9)   # kein Reset der I-Anteile


class LQRController:
    """Zustandsregler mit Servopraediktor, siehe Modulkopf und ``tvcsim.linear``."""

    def __init__(self, lqr: LQRParams, vehicle: VehicleParams, servo: ServoParams, dt: float,
                 integral: bool | None = None):
        self.p = lqr
        self.dt = dt
        self.l = vehicle.l_ctrl
        self.integral = lqr.integral if integral is None else integral
        self.plant = design_plant(lqr, vehicle, servo, dt)
        self.design = design_lqr(self.plant, design_weights(lqr, self.l), self.integral)
        self.A_pred, self.B_pred, self.sel = self.design.predictor()
        K = self.design.K[0]
        idx = self.design.idx
        self.k_theta = K[idx["theta"]]
        self.k_omega = K[idx["omega"]]
        self.k_pred = K[self.sel]
        self.k_int = K[idx["integ"]] if self.integral else 0.0
        # Zustand je Simulink-Querachse (Index 1 = y, 2 = z); Index 0 (Rollachse) nur mitgefuehrt
        self.rot = np.zeros(3)                      # rad, int(omega), Takt wie SimulinkController
        self.x_pred = np.zeros((3, len(self.sel)))  # Praediktorzustand [M^, M^_dot, Kette]
        self.s_int = np.zeros(3)                    # rad s
        self.last = {}

    def moments(self, t: float, w_est_dps) -> np.ndarray:
        """``[Mx, My, Mz]`` in N m (Mx = 0), vor Saettigung."""
        w = np.asarray(w_est_dps, dtype=float) * RAD
        u = np.zeros(3)
        for ax in (1, 2):
            u[ax] = -(self.k_theta * self.rot[ax] + self.k_omega * w[ax]
                      + float(self.k_pred @ self.x_pred[ax]) + self.k_int * self.s_int[ax])
        self._w = w
        self.last = {"rot": self.rot / RAD, "u": u.copy(), "s_int": self.s_int / RAD,
                     "M_pred": self.x_pred[:, 0].copy()}
        return u

    def step(self, t: float, w_est_dps, q_est, T_est: float, **_) -> tuple[float, float]:
        u = self.moments(t, w_est_dps)
        T_use = max(float(T_est), self.p.T_min)
        th_y, th_z = moments_to_commands(T_use, u[0], u[1], u[2], self.l)
        sat = self.p.sat_deg
        th_sat = (max(-sat, min(sat, th_y)), max(-sat, min(sat, th_z)))
        saturated = (abs(th_y) > sat + 1e-9, abs(th_z) > sat + 1e-9)
        # Praediktor: das Servo bekommt das gesaettigte Kommando, als Moment M = -l T sin(th)
        for ax, th, is_sat in zip((1, 2), th_sat, saturated):
            M_sat = -self.l * T_use * math.sin(math.radians(th))
            self.x_pred[ax] = self.A_pred @ self.x_pred[ax] + self.B_pred[:, 0] * M_sat
            if self.integral and not is_sat:
                lim = self.p.int_limit_deg_s * RAD
                self.s_int[ax] = max(-lim, min(lim, self.s_int[ax] + self.dt * self.rot[ax]))
        self.rot = self.rot + self._w * self.dt
        self.last.update({"th_y_com": th_y, "th_z_com": th_z, "T_est": T_est})
        return th_y, th_z


def make_controller(name: str, control: ControlParams, firmware: FirmwareParams, l_ctrl: float,
                    lqr: LQRParams | None = None, vehicle: VehicleParams | None = None,
                    servo: ServoParams | None = None):
    if name == "simulink":
        return SimulinkController(control, l_ctrl)
    if name == "firmware":
        return FirmwareController(firmware, control.dt)
    if name in ("pd_model", "pid_model", "lqr", "lqi"):
        if lqr is None or vehicle is None or servo is None:
            raise ValueError(f"Regler {name!r} braucht lqr, vehicle und servo")
        if name in ("pd_model", "pid_model"):
            cp = model_pd_params(lqr, vehicle, servo, control.dt, integral=(name == "pid_model"))
            return SimulinkController(cp, l_ctrl)
        return LQRController(lqr, vehicle, servo, control.dt, integral=(name == "lqi"))
    raise ValueError(f"unbekannter Regler {name!r}")
