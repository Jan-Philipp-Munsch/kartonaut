import math

import numpy as np

from tvcsim.actuator import ServoChannel, simulate_servo_response, static_error_profile_y
from tvcsim.motors import ThrustModel
from tvcsim.params import MotorParams, ServoParams


def test_e12_total_impulse_and_second_burn():
    tm = ThrustModel(MotorParams())
    assert 37.0 < tm.total_impulse < 41.0          # TSP E12: 39 Ns
    assert math.isclose(tm.burn_time, 3.545, abs_tol=1e-9)
    dt = 0.01
    assert tm.thrust(0.0, dt) == 0.0
    assert tm.thrust(0.535, dt) > 28.0
    assert tm.thrust(5.0, dt) == 0.0
    assert math.isclose(tm.thrust(7.3 + 0.535, dt), tm.thrust_single(0.535))
    assert tm.thrust(20.0, dt) == 0.0


def test_fuel_models():
    dt = 0.01
    sb = ThrustModel(MotorParams(fuel_model="signalbuilder"))
    assert sb.fuel_mass_g(0.0, dt) == 60.0 and sb.fuel_mass_g(3.5, dt) == 0.0 and sb.fuel_mass_g(8.0, dt) == 0.0
    im = ThrustModel(MotorParams(fuel_model="impulse", fuel_mass_g=28.0))
    assert math.isclose(im.fuel_mass_g(0.0, dt), 56.0)
    assert math.isclose(im.fuel_mass_g(5.0, dt), 28.0, abs_tol=1e-9)
    assert math.isclose(im.fuel_mass_g(12.0, dt), 0.0, abs_tol=1e-9)
    assert im.fuel_mass_g(1.0, dt) < im.fuel_mass_g(0.5, dt)


def test_static_error_profile():
    assert static_error_profile_y(0.0) == 1 and static_error_profile_y(2.0) == 0
    assert static_error_profile_y(7.5) == 1 and static_error_profile_y(9.5) == 0


def test_servo_dc_gain_and_delay():
    sp = ServoParams(servo_deg_per_tvc_deg=6.0)
    ch = ServoChannel(sp, tau=0.03, dt=0.01)
    for _ in range(300):
        ch.push_command(10.0)                      # wird auf +-5 gesaettigt
    assert ch.cmd_hist[0] == 5.0
    assert ch.delayed_input(0.0) == 0.0 and ch.delayed_input(0.029) == 0.0 and ch.delayed_input(0.031) == 5.0
    # stationaerer Endwert: x1 = K*u, Ausgang = 6*K*u
    x = np.array([sp.K * 5.0, 0.0])
    assert np.allclose(ch.deriv(1.0, x), 0.0)
    assert math.isclose(ch.output(x), 6.0 * sp.K * 5.0)


def test_simulate_servo_response_step():
    t = np.arange(0, 1.0, 0.002)
    u = np.where(t >= 0.1, 35.0, 0.0)
    y = simulate_servo_response(t, u, 0.1662, 36.7, 0.6, 0.03)
    assert abs(y[t < 0.13]).max() < 1e-9           # Totzeit
    assert math.isclose(y[-1], 0.1662 * 35.0, rel_tol=1e-3)
