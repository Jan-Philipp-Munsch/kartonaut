"""Regeltakt 250 Hz, IMU-Mittelung, Reaktionsmoment des Kardans, D-Tiefpass und Slew (seit 05.11.2026)."""
import math

import numpy as np

from tvcsim.actuator import ServoChannel
from tvcsim.controller import FirmwareController
from tvcsim.motors import ThrustModel
from tvcsim.params import (DT_CONTROL, FirmwareParams, MotorParams, NoiseParams, ServoParams, SimParams,
                           VehicleParams)
from tvcsim.sim import simulate


def test_default_rate_is_250_hz_and_at_rate_100_restores_old_setup():
    p = SimParams()
    assert math.isclose(p.control.dt, 0.004) and math.isclose(DT_CONTROL, 0.004)
    assert p.noise.imu_average and p.n_substeps == 4
    old = p.at_rate(100)
    assert math.isclose(old.control.dt, 0.01) and not old.noise.imu_average and old.n_substeps == 10


def test_second_motor_time_independent_of_control_rate():
    tm = ThrustModel(MotorParams())
    assert math.isclose(tm.t_second(0.004), 7.3) and math.isclose(tm.t_second(0.01), 7.3)


def test_imu_average_delays_rate_by_half_a_step():
    """Konstante Winkelbeschleunigung: das Mittel ueber [t - dt, t] ist der Wert bei t - dt/2."""
    veh = VehicleParams(mis_y=0.01, static_error_y=0.0)      # Querversatz -> konstantes Moment um z
    base = SimParams(vehicle=veh, controller="firmware", noise=NoiseParams(enabled=False), t_end=0.4, ground=False,
                     motor=MotorParams(second_motor=False),
                     firmware=FirmwareParams(PY_KP=0.0, PY_KI=0.0, PY_KD=0.0))
    r_inst = simulate(base.at_rate(250, imu_average=False))
    r_avg = simulate(base.at_rate(250, imu_average=True))
    # rot der Firmware integriert das gemessene omega: mit Mittelung hinkt es um ~dt/2 * omega hinterher
    k = len(r_avg.t) - 1
    w_inst = r_inst.w_dps[k, 2]
    lag = (r_inst.rot[k, 1] - r_avg.rot[k, 1]) / w_inst
    assert 0.0015 < abs(lag) < 0.0025


def test_gimbal_reaction_conserves_angular_momentum():
    """Ohne Schub dreht ein Kardanschwenk den Rumpf um -I_g/I * Schwenkwinkel."""
    I_g = 5e-4
    veh = VehicleParams(Ix=0.001, Iy=0.02, Iz=0.02, gimbal_inertia=I_g)
    p = SimParams(vehicle=veh, controller="simulink", noise=NoiseParams(enabled=False), t_end=0.5, ground=False,
                  motor=MotorParams(curve="E12", second_motor=False))
    # Schub aus, Ersatzregler kommandiert einen Sprung von 3 Grad auf th_z
    from tvcsim import sim as simmod

    class Step:
        last = {}

        def step(self, t, *a, **k):
            return 0.0, (3.0 if t > 0.05 else 0.0)

    orig_t, orig_c = simmod.ThrustModel.thrust, simmod.make_controller
    simmod.ThrustModel.thrust = lambda self, t, dt=None: 0.0
    simmod.make_controller = lambda *a, **k: Step()
    try:
        res = simulate(p)
    finally:
        simmod.ThrustModel.thrust, simmod.make_controller = orig_t, orig_c
    # Drehimpuls um z: I w_z + I_g * th_z_dot = 0  ->  Rumpfwinkel = -I_g/I * th_z (beides ab 0)
    phi_z = np.concatenate([[0.0], np.cumsum(0.5 * (res.w_dps[1:, 2] + res.w_dps[:-1, 2])) * p.control.dt])
    th = res.th_z - res.th_z[0]
    assert th[-1] > 2.9
    h_body = res.w_dps[:, 2] * veh.Iz
    h_gimbal = I_g * np.gradient(th, p.control.dt)          # Differenzenquotient: an den Knicken ~2 % daneben
    assert np.max(np.abs(h_body + h_gimbal)) < 0.05 * np.max(np.abs(h_body))
    assert math.isclose(phi_z[-1], -I_g / veh.Iz * th[-1], rel_tol=0.02)


def test_servo_rate_limit():
    sp = ServoParams.w5652h(rate_s_per_60=0.1)       # 600 Servo-Grad/s -> 100 Kardan-Grad/s bei Gain 6
    ch = ServoChannel(sp, tau=0.0, dt=0.004)
    ch.push_command(5.0)
    x = np.zeros(2)
    h = 1e-4
    vmax = 0.0
    for i in range(1000):
        x = ch.clip_rate(x + h * ch.deriv(i * h, x))
        vmax = max(vmax, abs(ch.rate_dps(x)))
    assert vmax <= 100.0 + 1e-6 and vmax > 99.0
    assert math.isclose(ch.output(x), 5.0, rel_tol=0.02)


def test_d_lowpass_and_slew_in_firmware_controller():
    fw = FirmwareParams(PY_KP=0.0, PY_KI=0.0, PY_KD=1.0, SERVO_YAW_GAIN=-6, SERVO_PITCH_GAIN=6, apply_window=False,
                        D_LPF_HZ=0.0, SERVO_SLEW_DPS=0.0)
    plain = FirmwareController(fw, 0.004)
    lpf = FirmwareController(FirmwareParams(**{**fw.__dict__, "D_LPF_HZ": 30.0}), 0.004)
    lpf.step(0.0, [0, 0, 0], None, 10.0, a_norm=10.0)        # Filter auf 0 starten
    plain.step(0.0, [0, 0, 0], None, 10.0, a_norm=10.0)
    m_plain = plain.moments_fw([10.0, 0.0, 0.0])[0]
    m_lpf = lpf.moments_fw([10.0, 0.0, 0.0])[0]
    a = 1.0 - math.exp(-2 * math.pi * 30.0 * 0.004)
    assert math.isclose(m_lpf, a * m_plain, rel_tol=1e-9)
    slew = FirmwareController(FirmwareParams(**{**fw.__dict__, "PY_KP": 50.0, "SERVO_SLEW_DPS": 600.0}), 0.004)
    slew.step(0.0, [0.0, 100.0, 0.0], None, 10.0, a_norm=10.0)
    assert abs(slew.last["yaw_servo_deg"] - fw.SERVO_YAW_OFFSET) <= 600.0 * 0.004 + 1e-9


def test_a_norm_filter_is_time_based():
    fw = FirmwareParams()
    for dt in (0.01, 0.004):
        c = FirmwareController(fw, dt)
        c.a_norm_filt = 0.0
        for _ in range(int(round(0.095 / dt))):
            c.update_a_norm(1.0)
        assert 0.6 < c.a_norm_filt < 0.67      # ~1 - 1/e nach einer Zeitkonstante, unabhaengig vom Takt
