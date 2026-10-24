"""Tests der Parser und der Befehlssteuerung von bench_test.py, ohne Hardware.

    python -m pytest firmware/tools/test_bench_test.py

Die Beispielzeilen in testdata/revb_test_sample.log sind im Format der Testkonsole
(examples/revb_test/Proto.h) aufgezeichnet; sie decken TEST, CAL, END, INFO, READY ab.
"""
from pathlib import Path

import pytest

import bench_test as bt

SAMPLE = Path(__file__).parent / "testdata" / "revb_test_sample.log"


# ---------------------------------------------------------------- parse_line
@pytest.mark.parametrize("line, expected", [
    ("TEST mux_gnd OK 0.002 V am ADC (Y7)", {"kind": "test", "name": "mux_gnd", "result": "OK", "detail": "0.002 V am ADC (Y7)"}),
    ("TEST baro2 SKIP nicht bestückt (DNP), Chip-ID 0x00", {"kind": "test", "name": "baro2", "result": "SKIP", "detail": "nicht bestückt (DNP), Chip-ID 0x00"}),
    ("TEST sd_init FEHL", {"kind": "test", "name": "sd_init", "result": "FEHL", "detail": ""}),
    ("TEST cal_gyro OK Nullpunkt 0.3 dps\r\n", {"kind": "test", "name": "cal_gyro", "result": "OK", "detail": "Nullpunkt 0.3 dps"}),
    ("CAL gyro_bias_dps 0.3120 -0.1980 0.0470", {"kind": "cal", "name": "gyro_bias_dps", "values": [0.312, -0.198, 0.047]}),
    ("CAL imu_axis_map 1 0 2", {"kind": "cal", "name": "imu_axis_map", "values": [1, 0, 2]}),
    ("CAL valid 7", {"kind": "cal", "name": "valid", "values": [7]}),
    ("END cal gyro 10 OK", {"kind": "end", "cmd": "cal gyro 10", "result": "OK"}),
    ("END mux SKIP", {"kind": "end", "cmd": "mux", "result": "SKIP"}),
    ("END watchdog fire OK", {"kind": "end", "cmd": "watchdog fire", "result": "OK"}),
    ("ASK Kanal 4 VBAT1_F: Teensy misst 3.981 V. Multimeter an VBAT1_F gegen GND, Wert in V", {"kind": "prompt", "prompt": "ASK", "text": "Kanal 4 VBAT1_F: Teensy misst 3.981 V. Multimeter an VBAT1_F gegen GND, Wert in V"}),
    ("WAIT Lage 1/6: Platine flach. Ruhig halten, dann Enter", {"kind": "prompt", "prompt": "WAIT", "text": "Lage 1/6: Platine flach. Ruhig halten, dann Enter"}),
    ("CONFIRM Pyro 1 zünden, 500 ms. Tippe JA", {"kind": "prompt", "prompt": "CONFIRM", "text": "Pyro 1 zünden, 500 ms. Tippe JA"}),
    ("INFO reset_cause Watchdog", {"kind": "info", "text": "reset_cause Watchdog"}),
    ("READY", {"kind": "ready"}),
    ("# Befehle (q bricht ab)", {"kind": "comment", "text": "Befehle (q bricht ab)"}),
    ("irgendein freier Text", None),
    ("TESTER foo OK", None),
    ("TEST foo MAYBE detail", None),
    ("ENDE mux OK", None),
    ("", None),
])
def test_parse_line(line, expected):
    assert bt.parse_line(line) == expected


def test_parse_values_mixed():
    assert bt.parse_values("1 -2.5 abc 0x10 3e2") == [1, -2.5, "abc", "0x10", 300.0]
    assert bt.parse_values("") == []


# ---------------------------------------------------------------- Session mit aufgezeichneten Zeilen
def test_session_from_sample_log():
    s = bt.Session()
    cmd = None
    for line in SAMPLE.read_text(encoding="utf-8").splitlines():
        ev = s.feed(line)
        # Befehlszuordnung wie in run_command: die END-Zeile nennt den Befehl, die TEST-Zeilen davor gehören dazu
        if ev and ev["kind"] == "end":
            for t in s.tests:
                if t["cmd"] is None:
                    t["cmd"] = ev["cmd"]
    names = [t["name"] for t in s.tests]
    assert names[:3] == ["mux_gnd", "mux_vbat1", "mux_vbat2"]
    assert len(s.tests) == 21
    assert [t["name"] for t in s.failed()] == ["timing_loop"]
    assert len(s.skipped()) == 7
    assert s.overall() == "FEHL"
    assert [e["cmd"] for e in s.ends] == ["mux", "imu", "baro", "cal gyro 10", "cal save", "timing"]
    assert s.cals["gyro_bias_dps"] == [0.312, -0.198, 0.047]
    assert s.cals["gyro_bias_temp_c"] == [24.31]
    assert s.cals["adc_gain[4]"] == [1.0021]
    assert s.cals["servo_us[1]"] == [1480, 1120, 1860]
    assert "reset_cause Einschalten" in s.infos
    assert [t["cmd"] for t in s.tests if t["name"] == "cal_gyro"] == ["cal gyro 10"]
    assert len(s.log) == SAMPLE.read_text(encoding="utf-8").count("\n")


def test_session_overall_levels():
    s = bt.Session()
    assert s.overall() == "LEER"
    s.feed("TEST a OK")
    assert s.overall() == "OK"
    s.feed("TEST b SKIP ohne 2S")
    assert s.overall() == "SKIP"
    s.feed("END x FEHL")
    assert s.overall() == "FEHL"


# ---------------------------------------------------------------- Befehlssteuerung mit nachgebildetem Port
class FakePort:
    """Spielt Konsolenzeilen ab; Zeilen, die mit '?' beginnen, erwarten vorher eine Antwort vom PC."""

    def __init__(self, script):
        self.script = list(script)
        self.sent = []
        self.pending_answer = False

    def write(self, data):
        self.sent.append(data.decode("utf-8").rstrip("\n"))
        self.pending_answer = False

    def readline(self):
        if not self.script:
            return b""
        nxt = self.script[0]
        if nxt.startswith("?"):        # Firmware wartet auf eine Antwort, erst dann geht es weiter
            if self.pending_answer:
                return b""
            self.pending_answer = True
            self.script.pop(0)
            return (nxt[1:] + "\n").encode("utf-8")
        self.script.pop(0)
        return (nxt + "\n").encode("utf-8")


def test_run_command_with_prompts():
    port = FakePort([
        "INFO Gyro-Nullpunkt",
        "?WAIT Lage 1/6: Platine flach, Enter",
        "INFO Lage 1: a = [0 0 9.8]",
        "?ASK Multimeter Wert in V",
        "CAL adc_gain 4 1.0021",
        "TEST cal_adc4 OK gemessen 3.981 V",
        "END cal adc 4 OK",
        "READY",
    ])
    io = bt.ScriptedIO(["", "3.989"])
    s = bt.Session()
    res = bt.run_command(port, s, "cal adc 4", io, echo=None, timeout_s=2)
    assert res == "OK"
    assert port.sent == ["cal adc 4", "", "3.989"]
    assert io.seen == [("WAIT", "Lage 1/6: Platine flach, Enter"), ("ASK", "Multimeter Wert in V")]
    assert s.cals["adc_gain[4]"] == [1.0021]
    assert s.tests == [{"cmd": "cal adc 4", "name": "cal_adc4", "result": "OK", "detail": "gemessen 3.981 V"}]
    assert s.ends == [{"cmd": "cal adc 4", "result": "OK"}]


def test_run_command_ignores_other_end_lines():
    port = FakePort(["END mux OK", "TEST imu_whoami OK 0x47", "END imu OK"])
    s = bt.Session()
    assert bt.run_command(port, s, "imu", bt.ScriptedIO([]), echo=None, timeout_s=2) == "OK"
    assert [e["cmd"] for e in s.ends] == ["mux", "imu"]


def test_run_command_timeout(monkeypatch):
    port = FakePort(["TEST sd_init OK Karte erkannt"])
    clock = [0.0]
    monkeypatch.setattr(bt.time, "time", lambda: clock.__setitem__(0, clock[0] + 0.5) or clock[0])
    s = bt.Session()
    assert bt.run_command(port, s, "sd", bt.ScriptedIO([]), echo=None, timeout_s=3) == "FEHL"
    assert s.tests[-1]["name"] == "timeout"
    assert s.overall() == "FEHL"


def test_wait_ready():
    port = FakePort(["# Banner", "INFO reset_cause Watchdog", "TEST watchdog_reset OK Neustart erkannt", "READY"])
    s = bt.Session()
    assert bt.wait_ready(port, s, 2.0, echo=None)
    assert s.tests[0]["name"] == "watchdog_reset"
    assert not bt.wait_ready(FakePort(["INFO nichts"]), bt.Session(), 0.01, echo=None)


def test_timeouts():
    assert bt.timeout_for("cal mag 60") == bt.TIMEOUTS["cal mag"]
    assert bt.timeout_for("all full") == bt.TIMEOUTS["all full"]
    assert bt.timeout_for("all") == bt.TIMEOUTS["all"]
    assert bt.timeout_for("servo 2 sweep") == bt.DEFAULT_TIMEOUT


# ---------------------------------------------------------------- Bericht
def test_report_markdown(tmp_path):
    s = bt.Session()
    s.current_cmd = "mux"
    s.feed("TEST mux_gnd OK 0.002 V")
    s.feed("TEST mux_vbat2 SKIP 2S fehlt")
    s.feed("END mux SKIP")
    s.current_cmd = "cal save"
    s.feed("CAL servo_us 1 1480 1120 1860")
    s.feed("END cal save OK")
    rails = [{"net": "5V_SYS", "volt": 5.01, "min": 4.85, "max": 5.15, "ok": True},
             {"net": "3V3_RF", "volt": None, "min": 3.2, "max": 3.4, "ok": None}]
    path = bt.write_report(tmp_path, s, rails, notes=["Hinweis"])
    md = path.read_text(encoding="utf-8")
    assert "| 5V_SYS | 5.010 V | 4.85..5.15 V | ok |" in md
    assert "| 3V3_RF | – | 3.20..3.40 V | übersprungen |" in md
    assert "| mux | mux_vbat2 | übersprungen | 2S fehlt |" in md
    assert "| servo_us[1] | 1480 1120 1860 |" in md
    assert "**SKIP**" in md
    assert "- Hinweis" in md
    js = path.with_suffix(".json").read_text(encoding="utf-8")
    assert '"overall": "SKIP"' in js


# ---------------------------------------------------------------- alter Ablauf (revb_bringup)
def test_bringup_parser():
    c = bt.parse_bringup_line("  [ OK ] GND-Kanal (Y7)               0.003 V am ADC", "1. Analogmux 74HC4051")
    assert c == {"section": "1. Analogmux 74HC4051", "what": "GND-Kanal (Y7)", "ok": True, "detail": "0.003 V am ADC"}
    c = bt.parse_bringup_line("  [FEHL] Konfiguration                ", "2. IMU")
    assert c["ok"] is False and c["what"] == "Konfiguration" and c["detail"] == ""
    assert bt.parse_bringup_line("IMU a=[  0.12  -0.05   9.79] m/s²", "") is None


def test_bringup_stats_and_judge():
    samples = {k: [] for k in bt.LIVE_RE}
    for i in range(10):
        samples["acc"].append((0.1, -0.05, 9.75 + 0.01 * i))
        samples["gyro"].append((0.3, -0.2, 0.05 + 0.001 * i))
        samples["p"].append((98712.0 + i,))
    samples["v1s"].append((3.98,))
    st = bt.stats(samples)
    assert abs(st["acc_norm_err_ms2"]) < 0.1
    assert st["gyro_bias_dps"][0] == pytest.approx(0.3)
    assert st["p_std_m"] < 0.5
    assert bt.judge(st) == []
    st["gyro_bias_dps"] = [3.0, 0, 0]
    assert any("Gyro-Offset" in n for n in bt.judge(st))
