"""Tests der Werkbank (tools/bench_gui) ohne Hardware: Rechenteil, Verbindung gegen die simulierte Platine, Webserver.

    python -m pytest firmware/tools/test_bench_gui.py

Die simulierte Platine (bench_gui/sim.py) hat bekannte Sensorfehler (SIM_TRUTH); die Fits müssen sie wiederfinden.
"""
import json
import math
import queue
import time
import urllib.error
import urllib.request

import numpy as np
import pytest

from bench_gui import calmath as cm
from bench_gui.link import FIELDS, BoardLink, Hub
from bench_gui.server import App, serve
from bench_gui.sim import HDR, SIM_TRUTH, SimBoard


# ---------------------------------------------------------------- Rechenteil
def _random_dirs(n, seed=0):
    v = np.random.default_rng(seed).normal(size=(n, 3))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_fit_ellipsoid_recovers_hard_and_soft_iron():
    soft = np.array(SIM_TRUTH["mag_soft_iron"]).reshape(3, 3)
    offset = np.array(SIM_TRUTH["mag_offset_gauss"])
    raw = (0.48 * _random_dirs(800)) @ np.linalg.inv(soft).T + offset
    r = cm.fit_ellipsoid(raw + np.random.default_rng(1).normal(scale=0.002, size=raw.shape))
    assert r["ok"] and r["octants"] == 8 and r["coverage"] > 0.9
    assert np.allclose(r["offset"], offset, atol=0.004)
    assert r["residual_pct"] < 2.0
    # die Korrektur macht aus den rohen Punkten wieder eine Kugel mit dem Feldbetrag
    corr = (raw - np.array(r["offset"])) @ np.array(r["soft_iron"]).reshape(3, 3).T
    assert np.allclose(np.linalg.norm(corr, axis=1), r["field"], rtol=0.01)


def test_fit_ellipsoid_rejects_flat_data():
    d = _random_dirs(300)
    d[:, 2] = np.abs(d[:, 2])                      # nur die obere Halbkugel: nicht alle Oktanten
    r = cm.fit_ellipsoid(0.5 * d)
    assert not r["ok"]
    assert not cm.fit_ellipsoid(np.zeros((10, 3)))["ok"]


def test_fit_accel_recovers_offset_and_scale():
    b, s = np.array(SIM_TRUTH["acc_offset_ms2"]), np.array(SIM_TRUTH["acc_scale"])
    dirs = np.vstack([np.eye(3), -np.eye(3), _random_dirs(6, seed=4)])     # sechs Flächen und sechs schiefe Lagen
    raw = dirs * cm.G / s + b                                              # korrigiert = (roh - b) * s
    r = cm.fit_accel(raw)
    assert r["ok"]
    assert np.allclose(r["offset"], b, atol=1e-6) and np.allclose(r["scale"], s, atol=1e-6)
    assert r["rms_after"] < 1e-6 < r["rms_before"]


def test_fit_accel_needs_all_axes_up_and_down():
    assert not cm.fit_accel(np.eye(3) * cm.G)["ok"]                        # zu wenig Lagen
    up_only = np.vstack([np.eye(3), np.eye(3) * 0.99]) * cm.G
    r = cm.fit_accel(up_only)
    assert not r["ok"] and "nach unten" in r["reason"]


def test_apply_matches_firmware_formulas():
    cal = cm.default_cal()
    cal.update(acc_offset_ms2=[0.1, 0.2, -0.3], acc_scale=[1.01, 0.99, 1.0], gyro_bias_dps=[1.0, -1.0, 0.5],
               mag_offset_gauss=[0.1, 0.0, -0.1], mag_soft_iron=[2.0, 0, 0, 0, 1.0, 0, 0, 0, 0.5])
    assert cm.apply_acc(cal, [1.1, 1.2, 0.7]) == pytest.approx([1.01, 0.99, 1.0])
    assert cm.apply_gyro(cal, [1.0, 1.0, 1.0]) == pytest.approx([0.0, 2.0, 0.5])
    assert cm.apply_mag(cal, [0.2, 0.3, 0.1]) == pytest.approx([0.2, 0.3, 0.1])
    assert cm.map_axes([1, 0, 2], [1, -1, 1], [10, 20, 30]) == [20, -10, 30]
    assert cm.right_handed([1, 0, 2], [1, -1, 1]) and not cm.right_handed([1, 0, 2], [1, 1, 1])


def test_update_cal_from_console_lines():
    cal = cm.default_cal()
    assert cm.update_cal(cal, "gyro_bias_dps", [0.3, -0.2, 0.05]) and cal["gyro_bias_dps"] == [0.3, -0.2, 0.05]
    assert cm.update_cal(cal, "adc_gain", [4, 1.002]) and cal["adc_gain"][4] == 1.002
    assert cm.update_cal(cal, "servo_us", [2, 1480, 1120, 1860]) and cal["servo_us"][1] == [1480, 1120, 1860]
    assert cm.update_cal(cal, "valid", [7]) and cal["valid"] == 7
    assert not cm.update_cal(cal, "mag_fit", [1, 2, 3, 4])                 # Diagnosezeile, kein Feld
    assert not cm.update_cal(cal, "acc_scale", [1.0, 1.0])                 # falsche Anzahl


def test_position_collector_takes_each_still_pose_once():
    col = cm.PositionCollector(hold_s=0.5)
    t = 0.0
    rng = np.random.default_rng(2)
    for up in ([0, 0, 1], [0, 0, 1], [1, 0, 0], [0, -1, 0]):               # zweimal dieselbe Lage: nur einmal zählen
        for _ in range(100):                                               # 2 s ruhig bei 50 Hz
            col.feed(t, np.array(up) * cm.G + rng.normal(scale=0.02, size=3), rng.normal(scale=0.05, size=3))
            t += 0.02
        for _ in range(30):                                                # dazwischen bewegt
            col.feed(t, rng.normal(scale=3.0, size=3), rng.normal(scale=60.0, size=3))
            t += 0.02
    assert len(col.positions) == 3
    assert col.faces() == [True, False, False, True, True, False]         # +x, -y, +z


def test_rotation_check_measures_full_turn():
    rc = cm.RotationCheck()
    bias = np.array([0.3, -0.2, 0.1])
    t, state = 0.0, None
    for rate in [0.0] * 100 + [90.0] * 200 + [0.0] * 100:                  # 2 s Ruhe, 4 s mit 90 °/s um z, 2 s Ruhe
        state = rc.feed(t, np.array([0, 0, cm.G]), bias + np.array([0, 0, rate]))
        t += 0.02
    assert state == "fertig"
    assert rc.result["axis"] == "z" and rc.result["reference_deg"] == 360.0
    assert abs(rc.result["scale_error_pct"]) < 1.0


def test_attitude_starts_from_gravity_and_follows_gyro():
    att = cm.Attitude()
    att.update([0, 0, cm.G], [0, 0, 0], 0.02)
    assert att.tilt_deg() == pytest.approx(0.0, abs=1e-6)
    for _ in range(100):                                                   # 1 s mit 90 °/s um x, Schwerkraft dreht mit
        ang = math.radians(att.tilt_deg())
        att.update([0, math.sin(ang) * cm.G, math.cos(ang) * cm.G], [90.0, 0, 0], 0.01)
    assert att.tilt_deg() == pytest.approx(90.0, abs=3.0)
    assert cm.altitude_m(101325.0 - 120.0, 101325.0) == pytest.approx(10.0, abs=0.3)


# ---------------------------------------------------------------- Verbindung gegen die simulierte Platine
class Client:
    """Hängt an der Ereignisverteilung wie ein Browserfenster."""

    def __init__(self, tmp_path):
        self.hub = Hub()
        self.q = self.hub.subscribe()
        self.link = BoardLink(self.hub, tmp_path)
        self.events = []

    def wait(self, pred, timeout=15.0):
        """Ereignisse lesen, bis pred(ev) wahr ist; liefert dieses Ereignis."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                ev = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            self.events.append(ev)
            if pred(ev):
                return ev
        raise AssertionError("Zeitlimit beim Warten auf ein Ereignis")

    def run(self, cmd, answers=(), timeout=20.0):
        """Befehl ausführen, Rückfragen der Reihe nach beantworten, Ergebnis der END-Zeile liefern."""
        answers = list(answers)
        self.link.send_command(cmd)
        while True:
            ev = self.wait(lambda e: (e["type"] == "done" and e["cmd"] == cmd)
                           or (e["type"] == "state" and e["state"]["prompt"] is not None), timeout)
            if ev["type"] == "done":
                return ev["result"]
            if self.link.prompt is not None:               # Zustand kann schon überholt sein
                self.link.answer(answers.pop(0) if answers else "")


@pytest.fixture
def client(tmp_path):
    c = Client(tmp_path)
    c.link.connect("sim")
    c.wait(lambda e: e["type"] == "done" and e["cmd"] == "cal show")       # Anfangsabfrage status + cal show
    yield c
    c.link.disconnect()


def test_connect_reads_status_and_starts_stream(client):
    st = client.link.state()
    assert st["connected"] and st["sim"] and st["imu_driver"] == "LSM6DSV16X"
    assert st["fit"]["imu"] and not st["fit"]["ina"] and st["parts"]["baro"]
    assert st["supply"]["v1"] == pytest.approx(3.98, abs=0.05)
    ev = client.wait(lambda e: e["type"] == "data")
    row = ev["rows"][0]
    assert len(row) == 20                                                  # t, 9 roh, 9 kalibriert, Höhe
    assert math.hypot(*row[1:4]) == pytest.approx(cm.G, abs=0.5)
    assert ev["last"]["v1"] == pytest.approx(3.98, abs=0.05) and len(ev["last"]["q"]) == 4
    assert HDR.split()[1:] == FIELDS                                       # Spaltenliste von Firmware und PC gleich


def test_command_interrupts_stream_and_collects_tests(client):
    client.wait(lambda e: e["type"] == "data")
    assert client.run("imu") == "OK"
    names = [t["name"] for t in client.link.session.tests]
    assert names == ["imu_whoami", "imu_config", "imu_rate", "imu_rest", "imu_selftest_gyro", "imu_selftest_acc"]
    client.wait(lambda e: e["type"] == "data")                             # der Strom läuft danach wieder
    assert client.run("ina") == "NICHT_ERKANNT"
    assert client.run("gibtsnicht") == "FEHL"
    assert "stream" not in [t["name"] for t in client.link.session.tests]  # Rahmenzeilen des Stroms nicht im Bericht


def test_prompts_are_answered(client):
    assert client.run("led", answers=["", "", "n", ""]) == "FEHL"          # blau "nicht gesehen"
    res = {t["name"]: t["result"] for t in client.link.session.tests}
    assert res == {"led_rot": "OK", "led_gruen": "OK", "led_blau": "FEHL", "led_weiss": "OK"}
    assert client.run("cal erase", answers=["nein"]) == "SKIP"             # nur das Wort JA löscht


def test_guided_calibration_and_save(client):
    assert client.run("cal gyro 2") == "OK"
    client.wait(lambda e: e["type"] == "done" and e["cmd"] == "cal show")
    assert client.link.cal["gyro_bias_dps"] == pytest.approx(SIM_TRUTH["gyro_bias_dps"], abs=0.02)
    assert client.link.cal["valid"] & 1 and client.link.state()["cal_dirty"]
    assert client.run("cal acc", answers=[""] * 6) == "OK"
    client.wait(lambda e: e["type"] == "done" and e["cmd"] == "cal show")
    assert client.link.cal["acc_offset_ms2"] == pytest.approx(SIM_TRUTH["acc_offset_ms2"], abs=0.02)
    assert client.run("cal save") == "OK"
    client.wait(lambda e: e["type"] == "done" and e["cmd"] == "cal show")
    assert not client.link.state()["cal_dirty"]
    assert client.link.write_report().endswith(".md")


def test_cal_set_validates(client):
    assert client.run("cal set gyro_bias_dps 0.1 -0.2 0.05") == "OK"
    assert client.run("cal set gyro_bias_dps 50 0 0") == "FEHL"            # außerhalb der Grenze
    assert client.run("cal set imu_axis 1 0 2 1 -1 1") == "OK"
    assert client.run("cal set imu_axis 1 0 2 1 1 1") == "FEHL"            # linkshändig
    assert client.run("cal set unbekannt 1") == "FEHL"
    client.wait(lambda e: e["type"] == "done" and e["cmd"] == "cal show")
    assert client.link.cal["gyro_bias_dps"] == [0.1, -0.2, 0.05]
    assert client.link.cal["imu_axis_map"] == [1, 0, 2] and client.link.cal["valid"] == 1 | 8


def test_pc_side_fits_find_the_simulated_errors(client):
    link = client.link
    link.set_stream(True, 100)
    link.set_sim_motion("taumeln")
    link.capture_start("mag")
    client.wait(lambda e: e["type"] == "capture" and e["kind"] == "mag" and e["n"] > 700 and e.get("coverage", 0) > 0.85, timeout=90)
    r = link.capture_fit()
    assert r["ok"], r
    assert r["offset"] == pytest.approx(SIM_TRUTH["mag_offset_gauss"], abs=0.01)
    assert r["field"] == pytest.approx(SIM_TRUTH["field_gauss"], abs=0.02)
    cmds = link.capture_apply()
    assert [c.split()[2] for c in cmds] == ["mag_offset_gauss", "mag_soft_iron", "mag_field_gauss"]
    client.wait(lambda e: e["type"] == "done" and e["cmd"] == cmds[-1])
    client.wait(lambda e: e["type"] == "done" and e["cmd"] == "cal show")
    assert link.cal["valid"] & 4 and link.cal["mag_offset_gauss"] == pytest.approx(r["offset"], abs=1e-4)

    link.capture_start("acc")
    client.wait(lambda e: e["type"] == "capture" and e["kind"] == "acc" and e["n"] >= 12, timeout=90)
    r = link.capture_fit()
    assert r["ok"], r
    assert r["offset"] == pytest.approx(SIM_TRUTH["acc_offset_ms2"], abs=0.03)
    assert r["scale"] == pytest.approx(SIM_TRUTH["acc_scale"], abs=0.003)


def test_record_writes_csv(client, tmp_path):
    path = client.link.record(True)
    client.wait(lambda e: e["type"] == "data")
    time.sleep(0.5)
    client.link.record(False)
    lines = open(path, encoding="utf-8").read().splitlines()
    assert lines[0].split(",") == FIELDS and len(lines) > 5 and len(lines[1].split(",")) == len(FIELDS)


def test_old_firmware_without_stream_does_not_loop(tmp_path):
    class OldBoard(SimBoard):                      # Konsole vor der Ergänzung: kennt "stream" nicht
        def _c_stream(self, hz):
            self._info("unbekannter Befehl: stream (help)")
            return "FEHL"

    c = Client(tmp_path)
    c.link.connect("sim")
    c.link.disconnect()
    c.link._reset()
    c.link.port, c.link.port_name = OldBoard(), "sim"
    import threading
    c.link._stop = threading.Event()
    c.link._thread = threading.Thread(target=c.link._run, args=(c.link.port, c.link._stop), daemon=True)
    c.link._thread.start()
    ev = c.wait(lambda e: e["type"] == "line" and e["kind"] == "error")
    assert "stream" in ev["text"] and not c.link.want_stream
    c.link.send_command("imu")                     # Befehle gehen weiter
    c.wait(lambda e: e["type"] == "done" and e["cmd"] == "imu")
    c.link.disconnect()


# ---------------------------------------------------------------- Webserver
def _post(url, action, token, body=None, host=None):
    req = urllib.request.Request(url + "api/" + action, data=json.dumps(body or {}).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Token": token, **({"Host": host} if host else {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_server_needs_token_and_local_host(tmp_path):
    app = App(tmp_path)
    httpd, url = serve(app, 8790)
    try:
        page = urllib.request.urlopen(url, timeout=5).read().decode()
        assert app.token in page and "{{TOKEN}}" not in page
        assert _post(url, "ports", "falsch")[0] == 403
        assert _post(url, "ports", app.token, host="evil.example")[0] == 403
        code, j = _post(url, "ports", app.token)
        assert code == 200 and j["ok"] and j["ports"][0]["device"] == "sim"
        assert _post(url, "cmd", app.token, {"cmd": "imu"})[1] == {"ok": False, "error": "nicht verbunden"}
        assert _post(url, "gibtsnicht", app.token)[0] == 404
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url + "events?token=falsch", timeout=5)
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url + "static/../link.py", timeout=5)
        assert _post(url, "connect", app.token, {"port": "sim"})[1]["ok"]
        assert _post(url, "state", app.token)[1]["state"]["connected"]
    finally:
        app.link.disconnect()
        httpd.shutdown()
