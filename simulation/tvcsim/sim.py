"""Ein Simulationslauf: Regelschleife alle dt (ZOH), dazwischen RK4 mit festen Teilschritten.

Zustand ``x = [r(3), rd(3), w(3), q(4), servo_y(2), servo_z(2)]``; die Quaternion wird nach
jedem Teilschritt normiert. Ablauf je Takt ``t_k``:

1. Avionics tastet ``q``, ``w`` (Grad/s) und ``rdd`` ab und verrauscht sie.
2. Estimator: ``w_est, q_est, T_est``.
3. Regler liefert ``th_y_com, th_z_com`` (Grad), ZOH haelt sie bis ``t_{k+1}``.
4. Integration ``t_k -> t_{k+1}``.

Mit ``SimParams.ground`` (Vorgabe) sitzt die Rakete auf der Rampe, bis der Schub das Gewicht
uebersteigt, und der Lauf endet bei der Landung (Hoehe 0); ``extra["t_land"]`` nennt den Zeitpunkt,
``extra["v_land"]`` die Vertikalgeschwindigkeit und ``extra["tilt_land_deg"]`` den Kippwinkel dabei.

Landemodus (``MotorParams.second_mode = "landing"``): nach dem Gipfel entscheidet
``tvcsim.landing.IgnitionTable`` aus (verrauschter) Hoehe und Sinkgeschwindigkeit, wann der
zweite Motor gezuendet wird; der Schub kommt ``igniter_delay`` spaeter. ``extra["t_ignite2"]``
ist der Zuendzeitpunkt (Kommando), ``extra["h_ignite2"]`` die Hoehe dabei.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .actuator import Actuator
from .controller import make_controller
from .dynamics import eom, tilt_deg
from .estimator import estimate
from .landing import LandingPlanner
from .motors import ThrustModel
from .params import SimParams
from .sensors import Avionics


@dataclass
class SimResult:
    params: SimParams
    t: np.ndarray
    r: np.ndarray          # Position inertial (x = Hoehe, y Downrange, z Crossrange)
    rd: np.ndarray
    rdd: np.ndarray
    w_dps: np.ndarray      # Drehrate Koerper, Grad/s
    q: np.ndarray
    m: np.ndarray
    T: np.ndarray          # Gesamtschub N
    th_y: np.ndarray       # tatsaechliche TVC-Winkel (Grad)
    th_z: np.ndarray
    th_y_com: np.ndarray   # Reglerkommando (Grad, vor Saettigung)
    th_z_com: np.ndarray
    u: np.ndarray          # geforderte Momente [Mx, My, Mz]
    rot: np.ndarray        # integrierter Winkel des Reglers (Grad)
    tilt_deg: np.ndarray
    T_est: np.ndarray
    extra: dict = field(default_factory=dict)

    @property
    def max_height(self) -> float:
        """``maxHeight`` wie der Block MinMax Running Resettable auf der Hoehe."""
        return float(np.max(self.r[:, 0]))

    @property
    def servo_y_deg(self) -> np.ndarray:
        """Servowinkel-Aequivalent der Kommandos (Grad, relativ zur Mitte)."""
        return self.params.servo.servo_deg_per_tvc_deg * np.clip(self.th_y_com, -self.params.servo.sat_deg, self.params.servo.sat_deg)

    @property
    def servo_z_deg(self) -> np.ndarray:
        return self.params.servo.servo_deg_per_tvc_deg * np.clip(self.th_z_com, -self.params.servo.sat_deg, self.params.servo.sat_deg)


def simulate(p: SimParams) -> SimResult:
    dt = p.control.dt
    n_steps = int(round(p.t_end / dt))
    h = dt / p.substeps
    rng = np.random.default_rng(p.seed)

    thrust = ThrustModel(p.motor)
    act = Actuator(p.servo, p.vehicle, dt)
    avionics = Avionics(p.noise, rng)
    ctrl = make_controller(p.controller, p.control, p.firmware, p.vehicle.l_ctrl)
    eom_params = p.vehicle.as_eom_params()
    rad2deg = 57.2957  # Gain "rad to deg" im Modell

    landing = None
    if p.motor.second_motor and p.motor.second_mode == "landing":
        # Masse bei der Landung: trocken plus voller zweiter Motor (fuel_model "impulse")
        fuel = p.motor.fuel_mass_g / 1000.0 if p.motor.fuel_model == "impulse" else 0.0
        landing = LandingPlanner(p.motor.curve, p.vehicle.m_dry + fuel, p.vehicle.cd_a, p.vehicle.rho, fuel,
                                 p.motor.igniter_delay, dt)
    t_ignite2 = None
    h_ignite2 = None
    v_ignite2 = None
    apogee_seen = False
    contacts: list[tuple[float, float]] = []    # (t, v) jedes Aufsetzen (Landemodus: auch Huepfer)
    on_ground = False

    # Zustand
    r = np.zeros(3); rd = np.zeros(3); w = np.zeros(3); q = np.array([1.0, 0.0, 0.0, 0.0])
    xy = np.zeros(2); xz = np.zeros(2)
    lifted = False
    t_land = None
    k_last = n_steps

    def derivs(t, r, rd, w, q, xy, xz):
        T = thrust.thrust(t, dt)
        m_fuel = thrust.fuel_mass_g(t, dt)
        th_y, th_z = act.angles(t, xy, xz)
        rdd, wd, qd, Mb, Tb, m = eom(eom_params, m_fuel, th_y, th_z, T, q, w, rd)
        return rd, rdd, wd, qd, act.y.deriv(t, xy), act.z.deriv(t, xz), (T, m, th_y, th_z, Tb)

    N = n_steps + 1
    log = {k: np.zeros((N, 3)) for k in ("r", "rd", "rdd", "w_dps", "u", "rot")}
    log["q"] = np.zeros((N, 4))
    for k in ("m", "T", "th_y", "th_z", "th_y_com", "th_z_com", "tilt", "T_est"):
        log[k] = np.zeros(N)
    t_arr = np.arange(N) * dt

    for k in range(N):
        t = k * dt
        # Werte zum Abtastzeitpunkt
        _, rdd, _, _, _, _, aux = derivs(t, r, rd, w, q, xy, xz)
        T, m, th_y, th_z, Tb = aux
        accel = rdd if p.noise.accel_model == "rdd" else Tb / m
        q_n, w_n, a_n = avionics.sample(q, w * rad2deg, accel)
        w_est, q_est, T_est = estimate(a_n, w_n, q_n, m)
        th_y_com, th_z_com = ctrl.step(t, w_est, q_est, T_est, a_norm=float(np.linalg.norm(a_n)))
        if p.controller == "firmware" and p.firmware.coast_center and T < 0.5:
            th_y_com, th_z_com = 0.0, 0.0      # Firmware: ohne Schub stehen die Servos auf Mitte
        act.push_command(th_y_com, th_z_com)

        # Landemodus: Zuendentscheidung nach dem Gipfel aus (verrauschter) Hoehe und Sinkrate
        if landing is not None and t_ignite2 is None and lifted:
            if rd[0] < 0.0:
                apogee_seen = True
            if apogee_seen and thrust.thrust_single(t) <= 0.0:
                h_est = r[0] + rng.standard_normal() * p.motor.landing_alt_sigma
                v_est = rd[0] + rng.standard_normal() * p.motor.landing_vz_sigma
                if landing.should_ignite(h_est, v_est):
                    t_ignite2 = t
                    h_ignite2 = float(r[0])
                    v_ignite2 = float(rd[0])
                    thrust.ignite_second(t + p.motor.igniter_delay)

        log["r"][k] = r; log["rd"][k] = rd; log["rdd"][k] = rdd; log["w_dps"][k] = w * rad2deg
        log["q"][k] = q; log["m"][k] = m; log["T"][k] = T; log["th_y"][k] = th_y; log["th_z"][k] = th_z
        log["th_y_com"][k] = th_y_com; log["th_z_com"][k] = th_z_com
        log["u"][k] = ctrl.last.get("u", np.zeros(3)); log["rot"][k] = ctrl.last.get("rot", np.zeros(3))
        log["tilt"][k] = tilt_deg(q); log["T_est"][k] = T_est
        if k == n_steps:
            break
        if p.ground and lifted and r[0] <= 0.0 and landing is None:
            # Landung: letzter Takt geloggt (Hoehe auf 0 geklemmt), Lauf endet hier
            log["r"][k, 0] = 0.0
            t_land = t
            k_last = k
            break
        if p.ground and lifted and landing is not None and on_ground and T <= 0.0:
            # Landemodus: am Boden und ausgebrannt -> Ruhe, Lauf endet
            t_land = t
            k_last = k
            break

        # Integration bis t + dt (RK4 mit festen Teilschritten)
        for s in range(p.substeps):
            ts = t + s * h
            k1 = derivs(ts, r, rd, w, q, xy, xz)[:6]
            a = [v + 0.5 * h * d for v, d in zip((r, rd, w, q, xy, xz), k1)]
            k2 = derivs(ts + 0.5 * h, *a)[:6]
            b = [v + 0.5 * h * d for v, d in zip((r, rd, w, q, xy, xz), k2)]
            k3 = derivs(ts + 0.5 * h, *b)[:6]
            c = [v + h * d for v, d in zip((r, rd, w, q, xy, xz), k3)]
            k4 = derivs(ts + h, *c)[:6]
            r, rd, w, q, xy, xz = [v + h / 6.0 * (d1 + 2 * d2 + 2 * d3 + d4)
                                   for v, d1, d2, d3, d4 in zip((r, rd, w, q, xy, xz), k1, k2, k3, k4)]
            q = q / np.linalg.norm(q)
            if p.ground and not lifted:
                if r[0] > 1e-6:
                    lifted = True
                else:   # auf der Rampe: kein Sinken, keine Drehung
                    r[:] = 0.0; rd[:] = 0.0; w[:] = 0.0
            elif p.ground and landing is not None:
                # Bodenkontakt im Landemodus: Aufsetzen festhalten, liegen bleiben, solange der
                # Schub nicht traegt; sonst hebt die Rakete wieder ab (Huepfer)
                if r[0] <= 0.0 and not on_ground:
                    if rd[0] < 0.0:
                        contacts.append((ts + h, float(rd[0])))
                    on_ground = True
                if on_ground:
                    r[0] = 0.0
                    rd[:] = 0.0; w[:] = 0.0
                    T_now = thrust.thrust(ts + h, dt)
                    m_now = p.vehicle.m_dry + thrust.fuel_mass_g(ts + h, dt) / 1000.0
                    if T_now / m_now > p.vehicle.g:
                        on_ground = False
                        r[0] = 1e-6

    n = k_last + 1
    t_arr = t_arr[:n]
    for key in log:
        log[key] = log[key][:n]

    if landing is not None:
        v_land = (min(v for _, v in contacts) if contacts else None)
    else:
        v_land = float(log["rd"][n - 1, 0]) if t_land is not None else None
    extra = {"t_land": t_land, "landed": t_land is not None, "t_ignite2": t_ignite2, "h_ignite2": h_ignite2,
             "v_ignite2": v_ignite2, "contacts": contacts, "v_land": v_land,
             "tilt_land_deg": float(log["tilt"][n - 1]) if t_land is not None else None,
             "landing_planner": landing}
    return SimResult(params=p, t=t_arr, r=log["r"], rd=log["rd"], rdd=log["rdd"], w_dps=log["w_dps"],
                     q=log["q"], m=log["m"], T=log["T"], th_y=log["th_y"], th_z=log["th_z"],
                     th_y_com=log["th_y_com"], th_z_com=log["th_z_com"], u=log["u"], rot=log["rot"],
                     tilt_deg=log["tilt"], T_est=log["T_est"], extra=extra)
