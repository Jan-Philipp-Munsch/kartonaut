import math

import numpy as np

from tvcsim.controller import FirmwareController, SimulinkController, moments_to_commands
from tvcsim.dynamics import eom
from tvcsim.params import ControlParams, FirmwareParams, VehicleParams


def test_moments_to_commands_inverts_dynamics():
    """Das Kommando aus Moments2Commands erzeugt in der Dynamik das geforderte Moment.

    Exakt je Achse einzeln. Bei beiden Achsen zugleich sitzt der cos-Faktor in Moments2Commands
    auf der anderen Achse als in der Dynamik (My = -l T sin(th_y) cos(th_z), der Block nimmt
    cos(th_y) fuer th_z); bis +-5 Grad ist der Fehler unter 1 Prozent, das Modell ist 1:1 uebernommen."""
    v = VehicleParams()
    T = 12.0
    for My, Mz in ((0.3, 0.0), (0.0, -0.4), (-0.5, 0.0)):
        th_y, th_z = moments_to_commands(T, 0.0, My, Mz, v.l)
        _, _, _, Mb, _, _ = eom(v.as_eom_params(), 0.0, th_y, th_z, T, np.array([1.0, 0, 0, 0]), np.zeros(3))
        assert math.isclose(Mb[1], My, abs_tol=1e-9)
        assert math.isclose(Mb[2], Mz, abs_tol=1e-9)
    for My, Mz in ((0.2, 0.25), (-0.3, 0.1)):
        th_y, th_z = moments_to_commands(T, 0.0, My, Mz, v.l)
        assert abs(th_y) < 5.0 and abs(th_z) < 5.0
        _, _, _, Mb, _, _ = eom(v.as_eom_params(), 0.0, th_y, th_z, T, np.array([1.0, 0, 0, 0]), np.zeros(3))
        assert math.isclose(Mb[1], My, rel_tol=0.01)
        assert math.isclose(Mb[2], Mz, rel_tol=0.01)


def test_moments_to_commands_clamps():
    th_y, th_z = moments_to_commands(1.0, 0.0, 100.0, 0.0, 0.3)
    assert math.isclose(th_y, -90.0)


def test_simulink_and_firmware_same_moments():
    """Simulink: u = kp*(-0,01 rot) + ki*int(-0,01 rot) + kd*(-w) [w in Grad/s].
    Firmware:  M = Kp*rot/-100 + Ki*int(rot)/-100 + Kd*w/-100.
    Mit kp = Kp, ki = Ki, kd = Kd/100 muessen beide dasselbe Moment liefern (bis auf die
    Integrationsdetails: die Firmware addiert den aktuellen Schritt, Simulink integriert exakt)."""
    dt = 0.01
    Kp, Ki, Kd = 5.0, 2.0, 1.0
    sim = SimulinkController(ControlParams(kp=Kp, ki=Ki, kd=Kd / 100.0, dt=dt), l_ctrl=0.3)
    fw = FirmwareController(FirmwareParams(PY_KP=Kp, PY_KI=Ki, PY_KD=Kd), dt)
    rng = np.random.default_rng(0)
    w = np.zeros(3)
    max_diff = 0.0
    for k in range(300):
        t = k * dt
        w = w + rng.standard_normal(3) * 2.0     # Drehrate in Grad/s, Zufallsweg
        u_sim = sim.moments(t, w)
        u_fw = fw.moments(t, w)
        # Firmware kennt rot nach dem aktuellen Schritt, Simulink vor ihm: um w*dt verschoben
        rot_shift = -0.01 * Kp * w * dt
        diff = np.abs((u_sim[1:] + rot_shift[1:]) - u_fw[1:])
        max_diff = max(max_diff, diff.max())
    # verbleibender Unterschied nur aus der I-Integration (Trapez vs. Rechteck), klein gegen |u|
    assert max_diff < 0.02 * max(1.0, np.abs(u_sim[1:]).max())


def test_firmware_vs_simulink_without_integral_exact():
    """Mit Ki = 0 ist der einzige Unterschied der eine Integrationsschritt von rot."""
    dt = 0.01
    Kp, Kd = 5.0, 1.0
    sim = SimulinkController(ControlParams(kp=Kp, ki=0.0, kd=Kd / 100.0, dt=dt), l_ctrl=0.3)
    fw = FirmwareController(FirmwareParams(PY_KP=Kp, PY_KI=0.0, PY_KD=Kd), dt)
    w_seq = [np.array([0.0, 10.0, -5.0])] * 50
    for k, w in enumerate(w_seq):
        u_sim = sim.moments(k * dt, w)
        u_fw = fw.moments(k * dt, w)
        # Firmware: rot = (k+1)*w*dt, Simulink: rot = k*w*dt
        expected_gap = -0.01 * Kp * w * dt
        assert np.allclose(u_fw[1:], u_sim[1:] + expected_gap[1:], atol=1e-12)


def test_firmware_servo_mapping_and_window():
    """Servo-Grad = delta_deg*GAIN + OFFSET, Fenster 70-115 / 60-105, Rundung wie lroundf."""
    fwp = FirmwareParams()
    fw = FirmwareController(fwp, 0.01)
    fw.a_norm_filt = 20.0
    # grosse Drehrate -> Saettigung am Fenster
    fw.step(0.0, [0.0, 500.0, -500.0], None, 10.0)
    assert fw.last["yaw_servo_deg"] in (fwp.SERVO_YAW_MIN_DEG, fwp.SERVO_YAW_MAX_DEG)
    assert fw.last["pitch_servo_deg"] in (fwp.SERVO_PITCH_MIN_DEG, fwp.SERVO_PITCH_MAX_DEG)
    # ohne Fehler bleibt der Servo in der Mitte (gerundet)
    fw2 = FirmwareController(fwp, 0.01)
    fw2.step(0.0, [0.0, 0.0, 0.0], None, 10.0)
    assert fw2.last["yaw_servo_deg"] == round(fwp.SERVO_YAW_OFFSET + 0.0) or \
        abs(fw2.last["yaw_servo_deg"] - fwp.SERVO_YAW_OFFSET) <= 0.5


def test_firmware_command_sign_stabilizes():
    """Positive Drehrate um die Simulink-y-Achse muss ein negatives My fordern und mit der
    Standard-Vorzeichenwahl ein Kommando ergeben, das in der Dynamik My < 0 erzeugt."""
    fwp = FirmwareParams(quantize_servo=False, apply_window=False)
    fw = FirmwareController(fwp, 0.01)
    fw.a_norm_filt = 15.0
    th_y, th_z = fw.step(0.0, [0.0, 50.0, 0.0], None, 10.0)
    assert fw.last["u"][1] < 0
    v = VehicleParams()
    _, _, _, Mb, _, _ = eom(v.as_eom_params(), 0.0, th_y, th_z, 10.0, np.array([1.0, 0, 0, 0]), np.zeros(3))
    assert Mb[1] < 0 and abs(Mb[2]) < 1e-9
