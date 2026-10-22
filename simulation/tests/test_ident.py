import math

import numpy as np

from tvcsim.ident import (SEG_ALT, SEG_CHIRP_L, SEG_HOLD1, SEG_STAIR, analyze, build_sequence, command_at,
                          fit_pt2_delay, format_report, load_ident_csv, pick_gyro_axis, servo_params_snippet,
                          simulate_pt2_delay, synthesize_run, write_ident_csv)


def test_sequence_matches_sketch_layout():
    pieces = build_sequence(22.0)
    total = sum(p.dur_s for p in pieces)
    assert 70 < total < 85
    t = np.arange(0, total, 0.002)
    cmd, seg = command_at(pieces, t)
    assert abs(cmd).max() <= 22.0 + 1e-9
    assert set(np.unique(seg)) >= {SEG_STAIR, SEG_ALT, SEG_CHIRP_L, SEG_HOLD1}
    # Treppe erreicht +A und -A, Chirp endet bei 0
    assert math.isclose(cmd[seg == SEG_STAIR].max(), 22.0) and math.isclose(cmd[seg == SEG_STAIR].min(), -22.0)
    assert abs(cmd[seg == SEG_HOLD1]).max() == 0.0


def test_pt2_delay_simulation_step():
    t = np.arange(0, 1.0, 0.002)
    u = np.where(t >= 0.1, 35.0, 0.0)
    y = simulate_pt2_delay(t, u, 0.1662, 36.7, 0.6, 0.03)
    assert abs(y[t < 0.128]).max() < 1e-6            # Totzeit
    assert math.isclose(y[-1], 0.1662 * 35.0, rel_tol=2e-3)


def test_fit_recovers_fractional_delay():
    t = np.arange(0, 6.0, 0.002)
    u = np.zeros_like(t)
    for k, a in enumerate((10, -10, 20, -20, 5)):
        u[t >= 1.0 * k + 0.5] = a
    y = simulate_pt2_delay(t, u, 0.2, 50.0, 0.5, 0.041) + np.random.default_rng(1).normal(0, 0.01, len(t))
    f = fit_pt2_delay(t, u, y)
    assert math.isclose(f["K"], 0.2, rel_tol=0.02)
    assert math.isclose(f["wn"], 50.0, rel_tol=0.05)
    assert math.isclose(f["zeta"], 0.5, rel_tol=0.1)
    assert abs(f["tau"] - 0.041) < 0.003


def test_analyze_synthetic_run_recovers_parameters():
    run = synthesize_run(K=0.17, wn=40.0, zeta=0.6, tau=0.025, gyro_axis=2, gyro_sign=1.0, seed=3)
    assert pick_gyro_axis(run) == (2, 1.0)
    res = analyze(run)
    s = res["summary"]
    assert s["anchor"] == "accel"
    assert math.isclose(s["static"]["K_deg_per_servo_deg"], 0.17, rel_tol=0.02)
    assert s["static"]["hysteresis_mean_deg"] < 0.05
    assert math.isclose(s["pt2"]["K"], 0.17, rel_tol=0.02)
    assert math.isclose(s["pt2"]["wn"], 40.0, rel_tol=0.05)
    assert math.isclose(s["pt2"]["zeta"], 0.6, rel_tol=0.1)
    assert abs(s["pt2"]["tau"] - 0.025) < 0.004
    assert abs(s["step_summary"]["dead_time_s_median"] - 0.025) < 0.015
    fr = s["frequency"]["chirp_small"]
    assert 5.0 < fr["f_3db_hz"] < 10.0          # PT2 mit 6,4 Hz, zeta 0,6: -3 dB nahe 7,5 Hz
    assert "ServoParams(" in servo_params_snippet(s)
    assert "Statische Kennlinie" in format_report(s)


def test_analyze_without_imu_still_runs():
    run = synthesize_run(seed=5)
    run.gyro[:] = 0.0
    run.acc[:] = 0.0
    res = analyze(run)
    assert res["summary"]["has_imu"] is False


def test_hysteresis_and_rate_limit_are_detected():
    run = synthesize_run(K=0.17, rate_limit_dps=70.0, hysteresis_deg=0.6, seed=7)
    s = analyze(run)["summary"]
    assert 0.3 < s["static"]["hysteresis_mean_deg"] < 0.9
    assert s["step_summary"]["peak_rate_dps_alternate"] < 80.0


def test_csv_roundtrip(tmp_path):
    run = synthesize_run(seed=11, axis="P")
    path = write_ident_csv(run, tmp_path / "m.csv")
    # zweiter Lauf angehängt, dazu Echo-Zeilen des Sketches und eine abgeschnittene Zeile
    text = path.read_text(encoding="utf-8")
    text += "# amplitude_deg: 10.00\n" + text.replace('# axis: P', '# axis: Y').replace(',P,', ',Y,') + "12345,3,Y,92.0"
    path.write_text(text, encoding="utf-8")
    runs = load_ident_csv(path)
    assert [r.axis for r in runs] == ["P", "Y"]
    assert runs[0].meta["center_deg"] == 92.5 and runs[0].meta["note"].startswith("synthetisch")
    assert len(runs[0].t) == len(run.t)
    assert np.allclose(runs[0].cmd, run.cmd, atol=1e-3)
    s = analyze(runs[0])["summary"]
    assert math.isclose(s["pt2"]["K"], 0.17, rel_tol=0.03)
