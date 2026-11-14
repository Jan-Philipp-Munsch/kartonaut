"""Verbindung zur Testkonsole revb_test: ein Lesefaden, Befehlswarteschlange, Rückfragen, Live-Daten.

Protokoll: examples/revb_test/Proto.h (TEST/CAL/INFO/WAIT/ASK/CONFIRM/END/READY) und Stream.h (HDR/D).
Die Zeilen wertet derselbe Parser aus wie tools/bench_test.py; dessen Session sammelt Prüfungen und
Kalibrierwerte für den Bericht.

Ablauf: Befehle laufen einzeln. Ein Befehl gilt als beendet, wenn die Konsole wieder READY meldet
(help, status und "cal show" enden ohne END-Zeile). Solange nichts ansteht und Live-Daten gewünscht
sind, läuft "stream"; vor jedem Befehl beendet der Faden den Strom mit q und startet ihn danach neu.
"""
import copy
import csv
import math
import queue
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bench_test as bt          # noqa: E402  (Parser und Bericht der Testkonsole)

from . import calmath as cm      # noqa: E402
from .sim import SimBoard        # noqa: E402

FIELDS = "t_ms ax ay az gx gy gz ti mx my mz p tb v1 v2 varm py1 py2 py3 py4 ia vbus rh ts n".split()
FIT_RE = re.compile(r"^bestückt: (.*)$")
PARTS_RE = re.compile(r"^Bausteine: IMU (\d) Baro (\d) Baro2 (\d) INA (\d) Mag (\d) SHT (\d) ADXL (\d) \(IMU-Treiber (.*)\)$")
SUPPLY_RE = re.compile(r"^1S ([-\d.]+) V, 2S ([-\d.]+) V, ARM ([-\d.]+) V, nFAULT (\S+), Kalibrierung (.*), gültig 0x([0-9A-Fa-f]+)$")
SIM_PORT = "sim"
# Befehle, die ohne END-Zeile enden (main.cpp: help, status, cal show kehren vorher zurück)
NO_END = ("help", "?", "status", "cal", "cal show", "tvc help")


class Hub:
    """Verteilt Ereignisse an alle offenen Browserfenster (je eine Warteschlange)."""

    def __init__(self):
        self._subs = []
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=4000)
        with self._lock:
            self._subs.append(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def publish(self, etype, /, **data):
        ev = {"type": etype, **data}
        with self._lock:
            for q in self._subs:
                try:
                    q.put_nowait(ev)
                except queue.Full:
                    pass                    # ein hängendes Fenster darf den Lesefaden nicht aufhalten


def _r(x, n=4):
    """Runden für JSON; NaN/inf werden None (JSON kennt sie nicht)."""
    return round(x, n) if isinstance(x, (int, float)) and math.isfinite(x) else None


class BoardLink:
    def __init__(self, hub, report_dir):
        self.hub = hub
        self.report_dir = Path(report_dir)
        self.lock = threading.RLock()
        self.port = None
        self.port_name = None
        self._thread = None
        self._stop = threading.Event()
        self._reset()

    def _reset(self):
        self.session = bt.Session()
        self.cal = cm.default_cal()
        self.cal_saved = None            # Stand im EEPROM, soweit bekannt (für "ungespeichert")
        self.cal_check = ""
        self.fit, self.parts, self.supply, self.imu_driver = {}, {}, {}, ""
        self.queue = deque()
        self.running = None              # laufender Befehl
        self.end_result = None
        self.end_seen = False
        self.ready = False
        self.syncing = True              # nach dem Verbinden: warten, bis die Konsole READY meldet und still ist
        self.sync_ready = False
        self.t_sync = time.time()
        self.prompt = None
        self.context = deque(maxlen=6)   # letzte INFO-Zeilen des laufenden Befehls (für den Rückfrage-Dialog)
        self.streaming = False
        self.stop_sent = False
        self.want_stream = True
        self.hz = 50
        self.last_rx = time.time()
        self.t_cmd = 0.0
        # Live-Daten
        self.attitude = cm.Attitude()
        self.p0 = None
        self._t_prev = None
        self._batch = []
        self._slow = {}
        self._t_flush = 0.0
        self.samples = 0
        # Aufnahme für Kalibrierung am PC
        self.capture = None              # {"kind": acc|mag|rot, ...}
        self.fit_result = None
        self._t_capture = 0.0
        self.recorder = None             # (Datei, csv.writer, Pfad)
        self._after_show_saved = False
        self._stream_n0 = 0

    # ------------------------------------------------------------ Verbindung
    @staticmethod
    def list_ports():
        out = [{"device": SIM_PORT, "description": "Simulierte Platine (ohne Hardware)", "teensy": False}]
        if bt.serial is not None:
            for p in bt.serial.tools.list_ports.comports():
                out.append({"device": p.device, "description": p.description or "", "teensy": p.vid == bt.TEENSY_VID})
        return out

    def connect(self, name):
        self.disconnect()
        with self.lock:
            self._reset()
            if name == SIM_PORT:
                self.port = SimBoard()
            else:
                if bt.serial is None:
                    raise RuntimeError("pyserial fehlt: pip install pyserial")
                self.port = bt.serial.Serial(name, 115200, timeout=0.1, write_timeout=2.0)
            self.port_name = name
            self._stop = threading.Event()
            self.queue.extend(["status", "cal show"])
            self._thread = threading.Thread(target=self._run, args=(self.port, self._stop), daemon=True, name="boardlink")
            self._thread.start()
        self.publish_state()

    def disconnect(self, reason=None):
        with self.lock:
            port, thread = self.port, self._thread
            if port is None:
                return
            self._stop.set()
            try:
                if self.streaming or self.running:
                    port.write(b"q\n")
            except Exception:
                pass
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with self.lock:
            try:
                port.close()
            except Exception:
                pass
            self._close_recorder()
            self.port, self.port_name, self._thread = None, None, None
            self.running, self.prompt, self.streaming = None, None, False
            self.queue.clear()
        if reason:
            self.hub.publish("line", kind="error", text=reason)
        self.publish_state()

    @property
    def is_sim(self):
        return self.port_name == SIM_PORT

    # ------------------------------------------------------------ Aufrufe aus der Oberfläche
    def send_command(self, cmd):
        cmd = " ".join(cmd.split())
        if not cmd:
            return
        with self.lock:
            if self.port is None:
                raise RuntimeError("nicht verbunden")
            if len(cmd) > 190:
                raise RuntimeError("Befehl zu lang (190 Zeichen)")
            self.queue.append(cmd)

    def answer(self, text):
        with self.lock:
            if self.port is None or self.prompt is None:
                raise RuntimeError("keine Rückfrage offen")
            self._write(text.strip())
            self.hub.publish("line", kind="tx", text=text.strip() or "(Enter)")
            self.prompt = None
            self.last_rx = time.time()
        self.publish_state()

    def abort(self):
        with self.lock:
            if self.port is None:
                return
            self.queue.clear()
            if self.running and not self.streaming:
                self._write("q")
                self.hub.publish("line", kind="tx", text="q")
                if self.prompt:
                    self.prompt = None
        self.publish_state()

    def set_stream(self, on, hz=None):
        with self.lock:
            self.want_stream = bool(on)
            if hz:
                hz = int(min(max(float(hz), 1), 200))
                if hz != self.hz and self.streaming:
                    self._stop_stream()         # Neustart mit der neuen Rate
                self.hz = hz
        self.publish_state()

    def set_sim_motion(self, mode):
        with self.lock:
            if not self.is_sim:
                raise RuntimeError("nur im Simulator")
            self.port.set_motion(mode)

    # ------------------------------------------------------------ Lesefaden
    def _write(self, text):
        self.port.write((text + "\n").encode("utf-8"))

    def _run(self, port, stop):
        try:
            self._write("")                     # leere Zeile: Konsole antwortet READY (siehe _resync)
            while not stop.is_set():
                raw = port.readline()
                if raw:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    with self.lock:
                        self.last_rx = time.time()
                        if line.startswith("D "):
                            self._sample(line)
                        else:
                            self._line(line)
                with self.lock:
                    self._tick(time.time())
        except Exception as e:                  # Kabel gezogen, Teensy neu gestartet
            if not stop.is_set():
                threading.Thread(target=self.disconnect, args=(f"Verbindung getrennt: {e}",), daemon=True).start()

    def _start(self, cmd):
        self.running, self.end_result, self.end_seen, self.ready = cmd, None, False, False
        self.t_cmd = self.last_rx = time.time()
        self.context.clear()
        self.session.current_cmd = cmd
        self._write(cmd)
        if cmd.startswith("stream"):
            self.streaming, self.stop_sent = True, False
            self._t_prev, self.p0, self._stream_n0 = None, None, self.samples
        else:
            self.hub.publish("line", kind="tx", text=cmd)
        self.publish_state()

    def _stop_stream(self):
        if self.streaming and not self.stop_sent:
            self._write("q")
            self.stop_sent = True

    def _resync(self, now):
        """Gleichlauf mit der Konsole herstellen: leere Zeile schicken, auf READY und Ruhe warten."""
        self.syncing, self.sync_ready, self.ready, self.t_sync = True, False, False, now
        self._write("")

    def _tick(self, now):
        if self.syncing:
            if self.sync_ready and now - self.last_rx > 0.3:
                self.syncing, self.ready = False, True
            elif now - self.t_sync > 3.0:
                self.hub.publish("line", kind="error", text="Keine Antwort (READY) von der Konsole. Läuft revb_test auf dem Teensy "
                                 "(pio run -e revb_test -t upload) und ist der richtige Port gewählt?")
                self._resync(now)
            return
        if self.running is None and self.ready:
            if self.queue:
                self._start(self.queue.popleft())
            elif self.want_stream:
                self._start(f"stream {self.hz}")
        elif self.streaming and (self.queue or not self.want_stream):
            self._stop_stream()
        if self.running and self.prompt is None:
            limit = 3.0 if self.streaming else bt.timeout_for(self.running)
            if now - self.last_rx > limit:
                self.hub.publish("line", kind="error", text=f"Zeitlimit: {limit:.0f} s keine Antwort auf '{self.running}'")
                if not self.streaming:
                    self.session.tests.append({"cmd": self.running, "name": "timeout", "result": "FEHL", "detail": f"keine Antwort in {limit:.0f} s"})
                    self.hub.publish("test", cmd=self.running, name="timeout", result="FEHL", detail=f"keine Antwort in {limit:.0f} s")
                self._finish("FEHL", timed_out=True)
                self._resync(now)
        if self._batch and now - self._t_flush >= 0.05:
            self._flush(now)

    def _finish(self, result, timed_out=False):
        cmd, self.running = self.running, None
        was_stream, self.streaming, self.prompt = self.streaming, False, None
        if cmd is None:
            return
        if was_stream and (timed_out or result == "FEHL" or (self.samples == self._stream_n0 and not self.stop_sent)):
            # ältere Firmware ohne "stream" oder Strom abgerissen: nicht in einer Schleife neu starten
            self.want_stream = False
            self.hub.publish("line", kind="error", text="Live-Daten: die Konsole liefert keinen Strom. Kennt die Firmware 'stream'? "
                             "Sonst revb_test neu flashen: pio run -e revb_test -t upload")
        if not was_stream:
            self.hub.publish("done", cmd=cmd, result=result)
            if cmd.startswith("cal ") and cmd.split()[1] not in ("show",):
                if (cmd in ("cal save", "cal load") and result == "OK") or cmd == "cal erase":
                    self._after_show_saved = True
                self.queue.appendleft("cal show")     # gültig-Bits und alle Werte neu lesen
            elif cmd == "cal show":
                if self.cal_saved is None or self._after_show_saved:
                    self.cal_saved = copy.deepcopy(self.cal)
                self._after_show_saved = False
        self.publish_state()

    def _line(self, line):
        if line.startswith("HDR "):
            return
        ev = self.session.feed(line)
        kind = ev["kind"] if ev else "text"
        if self.streaming and kind in ("info", "test", "end"):
            # Rahmenzeilen des Live-Stroms nicht ins Protokoll und nicht in den Bericht
            if kind == "test" and self.session.tests and self.session.tests[-1]["name"] == "stream":
                self.session.tests.pop()
            if kind == "end" and ev["cmd"] == self.running:
                self.end_result, self.end_seen = ev["result"], True
            return
        if (line or kind != "text") and kind != "ready":
            self.hub.publish("line", kind=kind, text=line, result=ev.get("result") if ev else None)
        if not ev:
            return
        if kind == "ready":
            if self.syncing:
                self.sync_ready = True
            elif self.running is None:
                self.ready = True
            elif self.end_seen or self.running in NO_END:
                self.ready = True
                self._finish(self.end_result)
        elif kind == "end":
            if ev["cmd"] == self.running:
                self.end_result, self.end_seen = ev["result"], True
        elif kind == "comment" and "Testkonsole (revb_test)" in ev["text"] and self.running:
            # Banner mitten im Befehl: der Teensy hat neu gestartet (watchdog fire, Reset, Flashen)
            self.hub.publish("line", kind="error", text=f"Neustart der Platine während '{self.running}'")
            self._finish(self.end_result)
            self._resync(time.time())
        elif kind == "prompt":
            self.prompt = {"kind": ev["prompt"], "text": ev["text"], "context": list(self.context)}
            self.publish_state()
        elif kind == "test":
            self.hub.publish("test", cmd=self.running, name=ev["name"], result=ev["result"], detail=ev["detail"])
        elif kind == "cal":
            cm.update_cal(self.cal, ev["name"], ev["values"])
        elif kind == "info":
            self.context.append(ev["text"])
            self._info(ev["text"])

    def _info(self, text):
        m = FIT_RE.match(text)
        if m:
            self.fit = {a: b == "an" for a, b in (item.split() for item in m.group(1).split(", "))}
            return
        m = PARTS_RE.match(text)
        if m:
            names = ("imu", "baro", "baro2", "ina", "mag", "sht", "adxl")
            self.parts = {n: m.group(i + 1) == "1" for i, n in enumerate(names)}
            self.imu_driver = m.group(8)
            return
        m = SUPPLY_RE.match(text)
        if m:
            self.supply = {"v1": float(m.group(1)), "v2": float(m.group(2)), "varm": float(m.group(3)), "nfault": m.group(4)}
            self.cal_check = m.group(5)
        elif text.startswith("kalibrierung "):
            self.cal_check = text.split(" ", 1)[1]

    # ------------------------------------------------------------ Live-Daten
    def _sample(self, line):
        parts = line.split()
        if len(parts) != len(FIELDS) + 1:
            return
        try:
            f = [float(x) for x in parts[1:]]
        except ValueError:
            return
        self.samples += 1
        t = f[0] / 1000.0
        acc, gyro, mag = f[1:4], f[4:7], f[8:11]
        dt = 0.0 if self._t_prev is None else min(max(t - self._t_prev, 0.0), 0.2)
        self._t_prev = t
        c = self.cal
        imu_ok = all(math.isfinite(x) for x in acc + gyro)
        mag_ok = all(math.isfinite(x) for x in mag)
        acc_b = cm.map_axes(c["imu_axis_map"], c["imu_axis_sign"], cm.apply_acc(c, acc)) if imu_ok else [math.nan] * 3
        gyro_b = cm.map_axes(c["imu_axis_map"], c["imu_axis_sign"], cm.apply_gyro(c, gyro)) if imu_ok else [math.nan] * 3
        mag_b = cm.map_axes(c["mag_axis_map"], c["mag_axis_sign"], cm.apply_mag(c, mag)) if mag_ok else [math.nan] * 3
        if imu_ok:
            self.attitude.update(acc_b, gyro_b, dt, mag_b if mag_ok and c["valid"] & cm.VALID_BITS["mag"] else None)
        p = f[11]
        if self.p0 is None and math.isfinite(p):
            self.p0 = p
        alt = cm.altitude_m(p, self.p0) if self.p0 else math.nan
        self._batch.append([_r(t, 3)] + [_r(x) for x in acc + gyro] + [_r(x, 5) for x in mag]
                           + [_r(x) for x in acc_b + gyro_b] + [_r(x, 5) for x in mag_b] + [_r(alt, 3)])
        self._slow = dict(zip(FIELDS[11:], f[11:]))
        self._slow["ti"] = f[7]
        if self.capture and imu_ok:
            self._feed_capture(t, acc, gyro, mag if mag_ok else None)
        if self.recorder:
            self.recorder[1].writerow(parts[1:])

    def _flush(self, now):
        q = self.attitude.q
        last = {k: _r(v, 3) for k, v in self._slow.items()}
        last.update(q=[_r(float(x), 5) for x in q], tilt=_r(self.attitude.tilt_deg(), 2), heading=_r(self.attitude.heading_deg(), 1),
                    mag_cal=bool(self.cal["valid"] & cm.VALID_BITS["mag"]))
        self.hub.publish("data", rows=self._batch, last=last)
        self._batch, self._t_flush = [], now
        if self.capture and now - self._t_capture >= 0.25:
            self._t_capture = now
            self.hub.publish("capture", **self.capture_status(new_points=True))

    # ------------------------------------------------------------ Kalibrierung am PC
    def capture_start(self, kind):
        with self.lock:
            if self.port is None:
                raise RuntimeError("nicht verbunden")
            if kind == "acc":
                self.capture = {"kind": "acc", "obj": cm.PositionCollector()}
            elif kind == "mag":
                self.capture = {"kind": "mag", "points": [], "sent": 0}
            elif kind == "rot":
                self.capture = {"kind": "rot", "obj": cm.RotationCheck()}
            else:
                raise RuntimeError(f"unbekannte Aufnahme {kind}")
            self.fit_result = None
            self.want_stream = True
        self.publish_state()

    def capture_stop(self):
        with self.lock:
            self.capture = None
        self.publish_state()

    def _feed_capture(self, t, acc, gyro, mag):
        cap = self.capture
        if cap["kind"] == "acc":
            cap["obj"].feed(t, np.array(acc), np.array(gyro))
        elif cap["kind"] == "rot":
            cap["obj"].feed(t, np.array(acc), np.array(gyro))
        elif cap["kind"] == "mag" and mag is not None and len(cap["points"]) < 6000:
            pts = cap["points"]
            if not pts or max(abs(mag[i] - pts[-1][i]) for i in range(3)) > 0.008:   # in Ruhe nicht denselben Punkt stapeln
                pts.append(list(mag))

    def capture_status(self, new_points=False):
        cap = self.capture
        if not cap:
            return {"kind": None}
        if cap["kind"] == "acc":
            o = cap["obj"]
            return {"kind": "acc", "n": len(o.positions), "faces": o.faces(), "still": o.is_still,
                    "positions": [[_r(x, 3) for x in q] for q in o.positions]}
        if cap["kind"] == "rot":
            o = cap["obj"]
            return {"kind": "rot", "state": o.state, "angle": [_r(float(x), 1) for x in o.angle], "result": o.result}
        pts = cap["points"]
        out = {"kind": "mag", "n": len(pts)}
        if pts:
            a = np.array(pts)
            mid = (a.max(axis=0) + a.min(axis=0)) / 2
            out["coverage"] = _r(cm.sphere_coverage(a - mid), 3)
        if new_points:
            out["points"] = [[_r(x, 4) for x in q] for q in pts[cap["sent"]:]]
            cap["sent"] = len(pts)
        return out

    def capture_fit(self):
        with self.lock:
            cap = self.capture
            if not cap:
                raise RuntimeError("keine Aufnahme aktiv")
            if cap["kind"] == "acc":
                r = cm.fit_accel(cap["obj"].positions)
                r["kind"] = "acc"
            elif cap["kind"] == "mag":
                r = cm.fit_ellipsoid(cap["points"])
                r["kind"] = "mag"
                if "offset" in r:                 # korrigierte Punkte für das Bild (ausgedünnt)
                    step = max(1, len(cap["points"]) // 600)
                    a = (np.array(cap["points"][::step]) - np.array(r["offset"])) @ np.array(r["soft_iron"]).reshape(3, 3).T
                    r["corrected"] = [[_r(float(x), 4) for x in q] for q in a]
            else:
                raise RuntimeError("für diese Aufnahme gibt es keinen Fit")
            self.fit_result = r
            return r

    def capture_apply(self):
        """Das Ergebnis des letzten Fits mit "cal set" an die Platine schicken (RAM; speichern mit cal save)."""
        with self.lock:
            r = self.fit_result
            if not r or "offset" not in r:
                raise RuntimeError("kein Fit vorhanden")
            fmt = lambda v: " ".join(f"{x:.5f}" for x in v)       # noqa: E731
            if r["kind"] == "acc":
                cmds = [f"cal set acc_offset_ms2 {fmt(r['offset'])}", f"cal set acc_scale {fmt(r['scale'])}"]
            else:
                cmds = [f"cal set mag_offset_gauss {fmt(r['offset'])}", f"cal set mag_soft_iron {fmt(r['soft_iron'])}",
                        f"cal set mag_field_gauss {r['field']:.4f}"]
            for c in cmds:
                self.send_command(c)
            self.capture = None
        self.publish_state()
        return cmds

    # ------------------------------------------------------------ Aufzeichnung und Bericht
    def record(self, on):
        with self.lock:
            self._close_recorder()
            if on:
                self.report_dir.mkdir(parents=True, exist_ok=True)
                path = self.report_dir / f"stream_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
                fh = open(path, "w", newline="", encoding="utf-8")
                w = csv.writer(fh)
                w.writerow(FIELDS)
                self.recorder = (fh, w, path)
        self.publish_state()
        return str(self.recorder[2]) if self.recorder else None

    def _close_recorder(self):
        if self.recorder:
            self.recorder[0].close()
            self.recorder = None

    def write_report(self):
        with self.lock:
            if not self.session.tests and not self.session.cals:
                raise RuntimeError("noch keine Prüfungen oder Kalibrierwerte")
            return str(bt.write_report(self.report_dir, self.session, []))

    # ------------------------------------------------------------ Zustand
    def state(self):
        with self.lock:
            return {
                "connected": self.port is not None, "port": self.port_name, "sim": self.is_sim,
                "busy": self.running is not None and not self.streaming, "cmd": None if self.streaming else self.running,
                "queued": len(self.queue), "prompt": self.prompt, "streaming": self.streaming, "want_stream": self.want_stream,
                "hz": self.hz, "fit": self.fit, "parts": self.parts, "supply": self.supply, "imu_driver": self.imu_driver,
                "cal": self.cal, "cal_check": self.cal_check,
                "cal_dirty": self.cal_saved is not None and self.cal != self.cal_saved,
                "capture": self.capture["kind"] if self.capture else None,
                "recording": str(self.recorder[2]) if self.recorder else None,
            }

    def publish_state(self):
        self.hub.publish("state", state=self.state())
