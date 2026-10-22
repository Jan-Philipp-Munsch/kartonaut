"""Software-in-the-Loop: der C++-Flugkern der Firmware in der Simulation (tvcsim.sil).

Braucht einen C++-Compiler (g++ oder clang++); ohne werden die Tests übersprungen.
"""
from dataclasses import replace

import numpy as np
import pytest

from tvcsim import sil
from tvcsim.params import MotorParams, NoiseParams, ServoParams, SimParams, VehicleParams
from tvcsim.sim import simulate

pytestmark = pytest.mark.skipif(sil.find_compiler() is None, reason="kein C++-Compiler für den SIL-Kern")


def _run(control: bool, seed: int = 0, **sil_over):
    p = sil.SilParams.from_config_h(control_enabled=control, **sil_over)
    veh = replace(VehicleParams.erstflug(), static_error_y=1.0, static_error_z=0.6)
    sp = SimParams(vehicle=veh, motor=MotorParams(fuel_model="impulse", second_motor=False),
                   servo=ServoParams(sat_deg=p.values["tvc_max_deg"]),
                   noise=NoiseParams(accel_model="specific_force"), controller="sil", sil=p, t_end=30.0, seed=seed)
    res = simulate(sp)
    tr = sil.trace_arrays(res.extra["trace"])
    n = len(res.t)
    return res, {k: v[:n] for k, v in tr.items()}


def _event_times(tr):
    return {sil.PHASES[ph]: t for t, ph, e in zip(tr["t"], tr["phase"], tr["event"]) if e}


def test_config_h_is_parsed_and_structs_match():
    p = sil.SilParams.from_config_h()
    raw = sil.parse_config_h()
    assert p.values["mass_kg"] == pytest.approx(raw["MASS_KG"])
    assert p.values["yaw_gain"] == pytest.approx(raw["SERVO_YAW_GAIN"])
    assert p.values["apogee_hold_ms"] == pytest.approx(raw["FS_APOGEE_HOLD_MS"])
    lib = sil.load_library()   # prüft die Strukturgrößen gegen die C++-Seite
    assert lib.sil_config_size() > 0


def test_sil_flight_with_control_follows_the_flight_sequence():
    res, tr = _run(control=True)
    ev = _event_times(tr)
    # Reihenfolge der Zustände und ihre Lage zur Simulation
    assert ev["BOOST"] < ev["COAST"] < ev["APOGEE"] < ev["DESCENT"]
    assert "ABORT" not in ev
    t_lift = res.t[np.argmax(res.r[:, 0] > 1e-6)]
    t_apogee = res.t[np.argmax(res.r[:, 0])]
    assert 0.0 < ev["BOOST"] - t_lift < 0.2
    assert abs(ev["COAST"] - 3.55) < 0.2
    assert 0.0 < ev["APOGEE"] - t_apogee < 1.5          # nie vor dem Gipfel, höchstens 1,5 s danach
    # Regelung: die Rakete bleibt in der Brennphase aufrecht
    burn = res.T > 0
    assert res.tilt_deg[burn].max() < 8.0
    # Lage aus der Firmware-Quaternion gegen die Wahrheit
    assert np.abs(tr["tilt_deg"] - res.tilt_deg).max() < 0.5
    # Kanal 1 zündet genau einmal, im Zustand APOGEE
    fire = np.where(tr["fire"] & 1)[0]
    assert len(fire) > 0 and tr["phase"][fire[0]] == sil.PHASES.index("APOGEE")
    assert np.all(np.diff(fire) == 1)                    # ein zusammenhängender Puls


def test_sil_without_control_tumbles_aborts_and_still_deploys():
    res, tr = _run(control=False)
    ev = _event_times(tr)
    assert "ABORT" in ev
    assert res.tilt_deg.max() > 70.0
    # nach dem Start zündet die Bergung auch im ABORT
    assert (tr["fire"] & 1).any()


def test_servo_quantisation_matches_control_cpp():
    res, tr = _run(control=True)
    # ganze Servo-Grad wie PWMServo::write(int) nach der Rundung in Control.cpp
    assert np.allclose(tr["servo_yaw_deg"], np.round(tr["servo_yaw_deg"]))
    assert np.allclose(tr["servo_pitch_deg"], np.round(tr["servo_pitch_deg"]))
