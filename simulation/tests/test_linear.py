"""Linearmodell, LQR-Entwurf und Zustandsregler im 6DOF-Modell."""
import math
from dataclasses import replace

import numpy as np
from scipy.linalg import expm

from tvcsim.controller import LQRController, make_controller
from tvcsim.linear import (RAD, AxisPlant, LQRWeights, closed_loop, control_params_to_gains, decay_rate,
                           delay_margin, design_lqr, design_pd, gain_margin, gains_to_control_params,
                           lqr_lti, pid_lti, spectral_radius, zoh)
from tvcsim.params import (ControlParams, LQRParams, MotorParams, NoiseParams, ServoParams, SimParams,
                           VehicleParams)
from tvcsim.sim import simulate

I_CAD, L_CAD = 0.11, 0.372
W = LQRWeights(M_max=L_CAD * 11.0 * math.sin(math.radians(5)))


def test_zoh_matches_series_for_double_integrator():
    A = np.array([[0.0, 1.0], [0.0, 0.0]]); B = np.array([[0.0], [1.0]])
    Ad, Bd = zoh(A, B, 0.01)
    assert np.allclose(Ad, [[1, 0.01], [0, 1]])
    assert np.allclose(Bd, [[0.5e-4], [0.01]])


def test_fractional_delay_chain_is_consistent():
    """Totzeit 25 ms = 2 Takte + 5 ms: Kette mit 3 Gliedern, Summe der Eingangsanteile wie ohne Totzeit."""
    pl = AxisPlant(I=I_CAD, tau=0.025)
    Ad, Bd, idx = pl.discretize(with_theta=False)
    assert len(idx["chain"]) == 3 and not idx["u_direct"]
    A, B, _ = pl.continuous(with_theta=False)
    _, B_full = zoh(A, B, 0.01)
    # Anteile von u(k-2) (Spalte z_2) und u(k-3) (Spalte z_3) auf die Streckenzustaende
    nc = A.shape[0]
    share = Ad[:nc, idx["chain"][1]] + Ad[:nc, idx["chain"][2]]
    # Gleicher Eingang auf beiden Teilintervallen = ein ganzer ZOH-Schritt
    assert np.allclose(share, B_full[:, 0], rtol=1e-9, atol=1e-12)
    # exakt ganzzahlig: 30 ms -> 3 Glieder, Eingang nur ueber z_3
    Ad3, Bd3, idx3 = AxisPlant(I=I_CAD, tau=0.030).discretize(with_theta=False)
    assert len(idx3["chain"]) == 3
    assert np.allclose(Ad3[:nc, idx3["chain"][2]], B_full[:, 0])


def test_pd_from_lqr_matches_analytic_poles_without_actuator():
    """Ohne Servo und Totzeit sind die Pole des PD-Kreises die des Doppelintegrators mit K_theta, K_omega
    (bis auf den halben Takt Verzug der rot-Integration)."""
    K_theta, K_omega, _ = design_pd(I_CAD, W)
    ideal = AxisPlant(I=I_CAD, wn=1e4, zeta=0.7, tau=0.0)
    eig = np.linalg.eigvals(closed_loop(ideal, pid_lti(K_theta, K_omega, 0.0, 0.01)))
    slow = sorted(eig, key=lambda z: -abs(z))[:2]
    expected = np.exp(np.roots([I_CAD, K_omega, K_theta]) * 0.01)
    assert np.allclose(sorted(slow, key=np.angle), sorted(expected, key=np.angle), atol=5e-3)
    # Umrechnung in Simulink-/Firmware-Gewinne und zurueck
    cp = gains_to_control_params(K_theta, K_omega, 0.0)
    assert np.allclose(control_params_to_gains(cp), (K_theta, K_omega, 0.0))


def test_firmware_gains_are_a_pd_with_wn_5_zeta_05():
    """Kp 5, Kd 1 (Skala -100) auf I = 0,11: wn 5,1 rad/s, zeta 0,5 (Befund 11 in Zahlen)."""
    K_theta, K_omega, _ = control_params_to_gains(ControlParams(kp=5.0, ki=0.0, kd=0.01))
    wn = math.sqrt(K_theta / I_CAD)
    zeta = K_omega / (2 * math.sqrt(K_theta * I_CAD))
    assert 4.5 < wn < 5.5 and 0.4 < zeta < 0.6


def test_lqr_nominal_stable_and_more_margin_than_pd():
    plant = AxisPlant(I=I_CAD)
    des = design_lqr(plant, W)
    assert spectral_radius(des.Ad - des.Bd @ des.K) < 1.0
    c_lqr = lqr_lti(des)
    c_pd = pid_lti(*design_pd(I_CAD, W)[:2], 0.0, 0.01)
    assert spectral_radius(closed_loop(plant, c_lqr)) < 1.0
    assert spectral_radius(closed_loop(plant, c_pd)) < 1.0
    # gleiche Kostenfunktion: der LQR mit Servowissen klingt schneller ab und vertraegt mehr Verstaerkung und Totzeit
    assert decay_rate(closed_loop(plant, c_lqr), 0.01) > decay_rate(closed_loop(plant, c_pd), 0.01)
    assert gain_margin(plant, c_lqr) > gain_margin(plant, c_pd)
    assert delay_margin(plant, c_lqr) > delay_margin(plant, c_pd)


def test_lqi_has_integral_state_and_rejects_constant_disturbance():
    plant = AxisPlant(I=I_CAD)
    des = design_lqr(plant, W, integral=True)
    assert "integ" in des.idx and des.K.shape[1] == des.Ad.shape[0]
    A = closed_loop(plant, lqr_lti(des))
    assert spectral_radius(A) < 1.0


def test_lqr_controller_in_6dof_keeps_tilt_small():
    veh = replace(VehicleParams.cad(), static_error_y=1.0, static_error_z=0.6)
    base = SimParams(vehicle=veh, noise=NoiseParams(enabled=False, accel_model="specific_force"),
                     motor=MotorParams(second_motor=False), t_end=4.0, lqr=LQRParams(I_ctrl=I_CAD))
    for name in ("lqr", "lqi", "pd_model", "pid_model"):
        res = simulate(replace(base, controller=name))
        burn = res.t <= 3.5
        assert res.tilt_deg[burn].max() < 5.0, name
        assert res.tilt_deg[burn][-1] < 1.5, name
    # Integralanteil regelt den statischen Servofehler aus
    r_lqr = simulate(replace(base, controller="lqr"))
    r_lqi = simulate(replace(base, controller="lqi"))
    ib = int(np.argmin(np.abs(r_lqr.t - 3.4)))
    assert r_lqi.tilt_deg[ib] < r_lqr.tilt_deg[ib]


def test_lqr_predictor_tracks_actuator_moment():
    """Der Servopraediktor des Reglers sagt das wirkliche Kardanmoment voraus (Entwurf = Wahrheit):
    Regler und Servomodell (``ServoChannel``) laufen mit einem vorgegebenen Drehratenverlauf."""
    from tvcsim.actuator import ServoChannel
    veh = VehicleParams.cad()
    servo = ServoParams()
    dt = 0.01
    ctrl = LQRController(LQRParams(I_ctrl=I_CAD), veh, servo, dt)
    ch = ServoChannel(servo, servo.tau, dt)
    T = 11.0
    x = np.zeros(2)
    err = []
    for k in range(200):
        t = k * dt
        w = np.array([0.0, 20.0 * math.sin(2 * math.pi * 0.7 * t), 0.0])   # Grad/s
        M_pred_before = float(ctrl.x_pred[1, 0])     # Praediktion fuer diesen Takt (nach dem letzten Update)
        th_true = servo.servo_deg_per_tvc_deg * x[0]
        M_true = -veh.l * T * math.sin(math.radians(th_true))
        if k > 5:
            err.append(M_pred_before - M_true)
        th_y, th_z = ctrl.step(t, w, None, T)
        ch.push_command(th_y)
        # Servo einen Takt integrieren (RK4 mit 1 ms)
        h = dt / 10
        for s_ in range(10):
            ts = t + s_ * h
            k1 = ch.deriv(ts, x); k2 = ch.deriv(ts + h / 2, x + h / 2 * k1)
            k3 = ch.deriv(ts + h / 2, x + h / 2 * k2); k4 = ch.deriv(ts + h, x + h * k3)
            x = x + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    err = np.array(err)
    assert np.abs(err).max() < 0.01      # N m; Kommandos liegen bei einigen Zehntel N m (DC-Gain 6 K = 0,997)
