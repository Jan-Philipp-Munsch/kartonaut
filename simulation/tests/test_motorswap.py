import numpy as np

from tvcsim.motorswap import swap_kinematics
from tvcsim.pinpoint import profile, run


def test_swap_takes_about_a_tenth_of_a_second():
    r = swap_kinematics(spring_n=5.0, friction_n=1.0)
    assert 0.08 < r.slide_time < 0.20
    assert r.t_release < r.t_burnout < r.t_seated
    assert 1.0 < r.v_seat < 4.0


def test_stronger_spring_releases_earlier_and_friction_slows():
    assert swap_kinematics(8.0).t_release < swap_kinematics(3.0).t_release
    assert swap_kinematics(3.0, 1.5).slide_time > swap_kinematics(3.0, 0.5).slide_time


def test_short_thrust_gap_lands_long_gap_does_not():
    def soft(swap):
        res = run(profile("wechsel", wind10=1.5, swap_time=swap), n=60, seed=1)
        return np.mean(res["landed"] & (np.abs(res["vz"]) <= 3.0))

    assert soft(0.1) > 0.9
    assert soft(0.5) < 0.5
