"""Simuliertes Mainboard rev B1: spricht das Zeilenprotokoll der Testkonsole revb_test (Proto.h, Stream.h).

Damit läuft die Oberfläche ohne Hardware (python -m bench_gui --sim) und die Tests prüfen den ganzen Weg
Befehl -> Zeilen -> Auswertung. Das Objekt verhält sich wie ein pyserial-Port (write, readline, close).

Die simulierte Platine hat bekannte Sensorfehler (SIM_TRUTH); eine Kalibrierung über die Oberfläche muss
sie wiederfinden. Die Bewegung wählt set_motion(): "ruhe", "wackeln", "taumeln" (alle Lagen nacheinander,
für Beschleunigungs- und Magnetometer-Fit) und "drehen" (einmal 360° um die Chip-z-Achse).

Die Texte der TEST-Zeilen sind denen der Firmware nachgebildet, die Messwerte sind erfunden.
"""
import copy
import math
import queue
import random
import threading
import time

import numpy as np

from . import calmath as cm

SIM_TRUTH = {
    "gyro_bias_dps": [0.312, -0.198, 0.047],
    "acc_offset_ms2": [0.12, -0.08, 0.21],
    "acc_scale": [1.004, 0.997, 1.012],
    "mag_offset_gauss": [0.118, -0.052, 0.207],
    "mag_soft_iron": [1.06, 0.03, -0.02, 0.03, 0.95, 0.01, -0.02, 0.01, 0.99],
    "imu_axis_map": [1, 0, 2], "imu_axis_sign": [1, -1, 1],     # body x = +chip y, body y = -chip x, body z = +chip z
    "field_gauss": 0.48, "inclination_deg": 66.0,
}

FIT_NAMES = ["imu", "baro", "baro2", "ina", "mag", "sht", "adxl", "lora", "gps"]
SERVO_NAMES = ["yaw", "pitch", "chute", "legs"]
SERVO_LIMITS = [(1359, 1744), (1273, 1658), (760, 2300), (760, 2300)]    # Fenster aus Config.h in µs
HDR = "HDR t_ms ax ay az gx gy gz ti mx my mz p tb v1 v2 varm py1 py2 py3 py4 ia vbus rh ts n"


def _quat_exp(w, dt):
    """Quaternion der Drehung mit Körper-Drehrate w (rad/s) über dt."""
    ang = float(np.linalg.norm(w)) * dt
    if ang < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    axis = np.asarray(w) / np.linalg.norm(w)
    return np.array([math.cos(ang / 2), *(math.sin(ang / 2) * axis)])


def _rotvec_between(q_from, q_to):
    """Drehvektor (Körpersystem, rad), der q_from in q_to überführt."""
    conj = q_from * np.array([1, -1, -1, -1])
    d = cm.quat_mul(conj, q_to)
    if d[0] < 0:
        d = -d
    s = float(np.linalg.norm(d[1:]))
    if s < 1e-9:
        return np.zeros(3)
    return d[1:] / s * 2.0 * math.atan2(s, d[0])


def _tumble_targets():
    """Lagen, die jede Chip-Achse nach oben und unten bringen, dazu die acht Ecken."""
    ups = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]
    ups += [(sx, sy, sz) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)]
    out = []
    for k, u in enumerate(ups):
        q = cm.quat_from_up(np.array(u, float))
        yaw = k * 1.1                                    # zusätzlich um die Senkrechte drehen: mehr Kurs für den Magnetometer-Fit
        out.append(cm.quat_mul(np.array([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]), q))
    return out


class SimBoard:
    def __init__(self, with_2s=True, armed=False, fast=True, seed=1):
        self.timeout = 0.1
        self.is_open = True
        self.with_2s, self.armed, self.fast = with_2s, armed, fast
        self.rng = random.Random(seed)
        self._in, self._out = queue.Queue(), queue.Queue()
        self._rx = b""
        self.fit = {n: n in ("imu", "baro", "mag", "sht") for n in FIT_NAMES}
        self.cal = cm.default_cal()
        self.eeprom = None
        self.saved_count = 0
        self.q = np.array([1.0, 0.0, 0.0, 0.0])          # Chip -> Navigation
        self.segments = []                               # [(dauer_s, drehrate_chip_rad_s)]
        self.motion = "ruhe"
        self._targets, self._target_i = _tumble_targets(), 0
        self._t_motion = 0.0
        self._t0 = time.time()
        self.servo_us = [1500, 1500, 1500, 1500]
        self._lock = threading.Lock()
        threading.Thread(target=self._main, daemon=True, name="simboard").start()

    # ------------------------------------------------------------ Port-Seite (wie pyserial)
    def write(self, data):
        self._rx += data
        while b"\n" in self._rx:
            line, self._rx = self._rx.split(b"\n", 1)
            self._in.put(line.decode("utf-8", errors="replace").strip())
        return len(data)

    def readline(self):
        try:
            return self._out.get(timeout=self.timeout)
        except queue.Empty:
            return b""

    def close(self):
        self.is_open = False
        self._in.put(None)

    def set_motion(self, mode):
        with self._lock:
            self.motion = mode
            self.segments = []
            if mode == "drehen":
                self.segments = [(1.5, np.zeros(3)), (4.0, np.array([0, 0, math.radians(90.0)])), (1.5, np.zeros(3))]
            self._t_motion = 0.0

    # ------------------------------------------------------------ Firmware-Seite
    def _p(self, line):
        self._out.put((line + "\n").encode("utf-8"))

    def _info(self, text): self._p("INFO " + text)
    def _test(self, name, res, detail=""): self._p(f"TEST {name} {res} {detail}".rstrip())
    def _cal(self, name, text): self._p(f"CAL {name} {text}")

    def _readline(self, timeout=None):
        try:
            line = self._in.get(timeout=timeout)
        except queue.Empty:
            return None
        if line is None:
            raise EOFError
        return line

    def _abort(self):
        try:
            while True:
                line = self._in.get_nowait()
                if line is None:
                    raise EOFError
                if line.lower().startswith("q"):
                    return True
        except queue.Empty:
            return False

    def _flush(self):
        try:
            while True:
                if self._in.get_nowait() is None:
                    raise EOFError
        except queue.Empty:
            pass

    def _wait(self, text):
        self._p("WAIT " + text)
        self._flush()
        line = self._readline()
        if line == "" or line[:1] in ("j", "J", "y"):
            return 1
        return 0 if line[:1] in ("n", "N") else -1

    def _ask(self, text):
        self._p("ASK " + text)
        self._flush()
        line = self._readline().replace(",", ".")
        try:
            return float(line)
        except ValueError:
            return None

    def _confirm(self, text):
        self._p("CONFIRM " + text)
        self._flush()
        return self._readline(60.0) == "JA"

    def _sleep(self, s):
        time.sleep(s * (0.25 if self.fast else 1.0))

    def _main(self):
        try:
            self._banner()
            self._p("READY")
            while self.is_open:
                line = self._readline()
                if line == "":
                    self._p("READY")
                    continue
                self._execute(line)
                self._p("READY")
        except EOFError:
            pass

    def _banner(self):
        self._p("")
        self._p("# Kartonaut Mainboard rev B1: Testkonsole (revb_test) [SIMULATOR]")
        self._info("reset_cause Einschalten")
        self._info("kalibrierung leer -> Standardwerte")
        self._status()
        self._p("# Befehle (q bricht laufende Messungen ab): siehe help")

    def _show_fit(self):
        self._info("bestückt: " + ", ".join(f"{n} {'an' if self.fit[n] else 'aus'}" for n in FIT_NAMES))

    def _status(self):
        f = self.fit
        self._show_fit()
        self._info(f"Bausteine: IMU {int(f['imu'])} Baro {int(f['baro'])} Baro2 0 INA {int(f['ina'])} Mag {int(f['mag'])} "
                   f"SHT {int(f['sht'])} ADXL 0 (IMU-Treiber LSM6DSV16X)")
        self._info(f"1S {self._v1():.2f} V, 2S {self._v2():.2f} V, ARM {self._varm():.2f} V, nFAULT hoch, "
                   f"Kalibrierung {'ok' if self.eeprom else 'leer'}, gültig 0x{self.cal['valid']:02X}")

    def _v1(self): return 3.98 * self.cal["adc_gain"][4] + self.rng.gauss(0, 0.003)
    def _v2(self): return (7.62 if self.with_2s else 0.02) * self.cal["adc_gain"][5] + self.rng.gauss(0, 0.004)
    def _varm(self): return (7.55 if self.armed and self.with_2s else 0.01) + self.rng.gauss(0, 0.003)

    # ------------------------------------------------------------ Bewegung und Sensoren
    def _advance(self, dt):
        """Lage um dt weiterdrehen; liefert die wahre Drehrate in Chip-Achsen (rad/s)."""
        with self._lock:
            self._t_motion += dt
            w = np.zeros(3)
            if self.segments:
                dur, w = self.segments[0]
                self.segments[0] = (dur - dt, w)
                if dur - dt <= 0:
                    self.segments.pop(0)
                    if not self.segments and self.motion == "drehen":
                        self.motion = "ruhe"
            elif self.motion == "wackeln":
                t = self._t_motion
                w = np.array([0.5 * math.sin(1.3 * t), 0.4 * math.sin(0.9 * t + 1.0), 0.25 * math.sin(0.6 * t + 2.0)])
            elif self.motion == "taumeln":
                target = self._targets[self._target_i % len(self._targets)]
                self._target_i += 1
                self.segments = [(1.2, _rotvec_between(self.q, target) / 1.2), (1.6, np.zeros(3))]
                dur, w = self.segments[0]
            self.q = cm.quat_mul(self.q, _quat_exp(w, dt))
            self.q /= np.linalg.norm(self.q)
            return w

    def _sensors(self, w_chip):
        """Rohwerte in Chip-Achsen bei der aktuellen Lage: (acc m/s², gyro °/s, mag gauss)."""
        r = cm.quat_matrix(self.q)
        g = self.rng.gauss
        f_true = r.T @ np.array([0.0, 0.0, cm.G])
        acc = [f_true[i] / SIM_TRUTH["acc_scale"][i] + SIM_TRUTH["acc_offset_ms2"][i] + g(0, 0.02) for i in range(3)]
        gyro = [math.degrees(w_chip[i]) + SIM_TRUTH["gyro_bias_dps"][i] + g(0, 0.04) for i in range(3)]
        inc = math.radians(SIM_TRUTH["inclination_deg"])
        b_nav = SIM_TRUTH["field_gauss"] * np.array([math.cos(inc), 0.0, -math.sin(inc)])
        soft_inv = np.linalg.inv(np.array(SIM_TRUTH["mag_soft_iron"]).reshape(3, 3))
        m = soft_inv @ (r.T @ b_nav) + np.array(SIM_TRUTH["mag_offset_gauss"])
        mag = [m[i] + g(0, 0.003) for i in range(3)]
        return acc, gyro, mag

    def _snap_up(self, chip_axis, sign):
        """Lage so setzen, dass die Chip-Achse (sign = +1/-1) nach oben zeigt."""
        u = np.zeros(3)
        u[chip_axis] = sign
        with self._lock:
            self.q = cm.quat_from_up(u)
            self.segments = []

    def _average(self, seconds, n=60):
        self._sleep(seconds)
        acc, gyro, mag = np.zeros(3), np.zeros(3), np.zeros(3)
        for _ in range(n):
            a, w, m = self._sensors(np.zeros(3))
            acc += a
            gyro += w
            mag += m
        return acc / n, gyro / n, mag / n

    # ------------------------------------------------------------ Befehle
    def _execute(self, line):
        a = line.split()
        cmd, res = a[0], "OK"
        if cmd in ("help", "?"):
            self._p("# Befehle wie revb_test: all | mux imu baro mag sht adxl ina | led buzzer cam | servo motor pyro | lora gps sd timing watchdog mem")
            self._p("#   cal gyro|acc|mag|axes|baro|adc|ina|servo|show|save|load|defaults|erase|set | stream [hz] | fit | status")
            return
        if cmd == "status":
            self._status()
            return
        if cmd == "cal" and (len(a) == 1 or a[1] == "show"):
            self._cal_show()
            return
        if cmd == "all":
            res = self._worst([self._t_mux(), self._t_imu(), self._t_baro(), self._t_mag(), self._t_sht(), self._t_adxl(),
                               self._t_ina(), self._t_timing(), self._t_mem()])
            if len(a) > 1 and a[1] == "full":
                res = self._worst([res, self._t_led(), self._t_seen("buzzer", "Hat der Summer dreimal gepiept"),
                                   self._t_seen("cam_trigger", "Hat die Kamera ausgelöst bzw. war der Pegel an J_CAM Pin 2 zu sehen")]
                                  + [self._t_servo(i, "center") for i in range(4)]
                                  + [self._t_motor(), self._t_lora(), self._t_gps(), self._t_sd()])
        elif cmd == "fit": res = self._c_fit(a[1:])
        elif cmd == "mux": res = self._t_mux()
        elif cmd == "imu": res = self._t_imu()
        elif cmd == "baro": res = self._t_baro()
        elif cmd == "mag": res = self._t_mag()
        elif cmd == "sht": res = self._t_sht()
        elif cmd == "adxl": res = self._t_adxl()
        elif cmd == "ina": res = self._t_ina()
        elif cmd == "led": res = self._t_led()
        elif cmd == "buzzer": res = self._t_seen("buzzer", "Hat der Summer dreimal gepiept")
        elif cmd == "cam": res = self._t_seen("cam_trigger", "Hat die Kamera ausgelöst bzw. war der Pegel an J_CAM Pin 2 zu sehen")
        elif cmd == "servo": res = self._t_servo(self._int(a, 1, 0) - 1, " ".join(a[2:]) or "center")
        elif cmd == "motor": res = self._t_motor()
        elif cmd == "pyro": res = self._t_pyro(self._int(a, 1, 0) - 1, self._int(a, 2, 500))
        elif cmd == "lora": res = self._t_lora()
        elif cmd == "gps": res = self._t_gps()
        elif cmd == "sd": res = self._t_sd()
        elif cmd == "timing": res = self._t_timing()
        elif cmd == "mem": res = self._t_mem()
        elif cmd == "watchdog": res = self._t_watchdog()
        elif cmd == "stream": res = self._c_stream(float(a[1]) if len(a) > 1 else 50.0)
        elif cmd == "cal": res = self._c_cal(a[1:])
        else:
            self._info(f"unbekannter Befehl: {cmd} (help)")
            res = "FEHL"
        self._p(f"END {line} {res}")

    @staticmethod
    def _int(a, i, default):
        try:
            return int(a[i])
        except (IndexError, ValueError):
            return default

    @staticmethod
    def _worst(results):
        for r in ("FEHL", "SKIP", "NICHT_ERKANNT"):
            if r in results:
                return r
        return "OK"

    def _not_fitted(self, test, part):
        self._test(test, "NICHT_ERKANNT", f"nicht bestückt oder keine Antwort (Bestückungsliste: fit {part} off)")
        return "NICHT_ERKANNT"

    def _c_fit(self, a):
        if a and a[0] == "default":
            self.fit = {n: n in ("imu", "baro", "mag", "sht") for n in FIT_NAMES}
        elif a:
            on = len(a) > 1 and a[1] in ("on", "an", "1")
            off = len(a) > 1 and a[1] in ("off", "aus", "0")
            if not on and not off:
                self._info(f"fit {a[0]}: on oder off fehlt (fit <teil> on|off)")
                return "FEHL"
            if a[0] == "all":
                self.fit = {n: on for n in FIT_NAMES}
            elif a[0] in self.fit:
                self.fit[a[0]] = on
            else:
                self._info(f"fit: unbekanntes Teil {a[0]} (imu baro baro2 ina mag sht adxl lora gps)")
                return "FEHL"
        self._show_fit()
        return "OK"

    def _t_mux(self):
        self._test("mux_gnd", "OK", "0.002 V am ADC (Y7)")
        self._test("mux_vbat1", "OK", f"{self._v1():.3f} V (1S, 3,0..4,35 V)")
        if not self.with_2s:
            self._test("mux_vbat2", "SKIP", "0.02 V, 2S nicht versorgt")
            self._test("mux_arm", "SKIP", "ohne 2S")
            for i in range(4):
                self._test(f"mux_pyro{i + 1}", "SKIP", "ohne 2S")
            return "SKIP"
        self._test("mux_vbat2", "OK", f"{self._v2():.3f} V (2S, 6,0..8,6 V)")
        self._test("mux_arm", "OK", f"{self._varm():.2f} V {'SCHARF' if self.armed else 'sicher'}")
        for i in range(4):
            if i > 1:
                self._test(f"mux_pyro{i + 1}", "SKIP", "0.00 V, Kanal DNP")
            elif not self.armed:
                self._test(f"mux_pyro{i + 1}", "SKIP", "0.00 V, ARM nicht scharf")
            else:
                self._test(f"mux_pyro{i + 1}", "OK", "7.52 V Durchgang")
        return "OK"

    def _t_imu(self):
        if not self.fit["imu"]:
            return self._not_fitted("imu_whoami", "imu")
        self._test("imu_whoami", "OK", "0x70 soll 0x70 (LSM6DSV16X)")
        self._test("imu_config", "OK", "Flugkonfiguration zurückgelesen")
        self._sleep(0.5)
        self._test("imu_rate", "OK", "961 Hz soll 960")
        acc, gyro, _ = self._average(0.3)
        an, wn = float(np.linalg.norm(acc)), float(np.linalg.norm(gyro))
        ok = abs(an - 9.81) < 0.8 and wn < 5.0
        self._test("imu_rest", "OK" if ok else "FEHL", f"|a| {an:.2f} m/s2 a=[{acc[0]:.2f} {acc[1]:.2f} {acc[2]:.2f}] |w| {wn:.2f} dps T 24.3 C")
        self._test("imu_selftest_gyro", "OK", "Antwort 312 -298 305 dps, Grenzen 150..700, Offset 0.3 -0.2 0.1")
        self._test("imu_selftest_acc", "OK", "Antwort 0.412 0.398 0.505 g, Grenzen 0.050..1.700")
        return "OK" if ok else "FEHL"

    def _t_baro(self):
        a = self._not_fitted("baro1", "baro") if not self.fit["baro"] else "OK"
        if a == "OK":
            self._test("baro1", "OK", "Chip-ID 0x50 (BMP388), 98712 Pa, 25.1 C")
        if self.fit["baro2"]:
            self._test("baro2", "FEHL", "keine Antwort, Chip-ID 0x00 (nicht bestückt? dann 'fit baro2 off')")
            return "FEHL"
        return self._worst([a, self._not_fitted("baro2", "baro2")])

    def _t_mag(self):
        if not self.fit["mag"]:
            return self._not_fitted("mag_whoami", "mag")
        self._test("mag_whoami", "OK", "0x3D soll 0x3D (LIS3MDL, 0x1E)")
        self._test("mag_config", "OK", "80 Hz, +-4 gauss, UHP")
        _, _, m = self._average(0.25)
        b = float(np.linalg.norm(cm.apply_mag(self.cal, m)))
        self._test("mag_read", "OK", f"20 Werte, roh [{m[0]:.3f} {m[1]:.3f} {m[2]:.3f}] gauss, |B| {b:.3f} "
                   f"{'kalibriert' if self.cal['valid'] & 4 else 'unkalibriert'}, T 24.8 C")
        self._test("mag_selftest", "OK", "Differenz 1.62 1.71 0.48 gauss (X/Y 1,0..3,0, Z 0,1..1,0)")
        return "OK"

    def _t_sht(self):
        if not self.fit["sht"]:
            return self._not_fitted("sht_serial", "sht")
        self._test("sht_serial", "OK", "Seriennummer 0F3A91C2 (0x44)")
        self._test("sht_read", "OK", "23.41 C, 41.5 %rF, CRC ok")
        return "OK"

    def _t_adxl(self):
        if not self.fit["adxl"]:
            return self._not_fitted("adxl_present", "adxl")
        self._test("adxl_present", "FEHL", "kein ACK auf 0x53 (nicht bestückt? dann 'fit adxl off')")
        return "FEHL"

    def _t_ina(self):
        if not self.fit["ina"]:
            return self._not_fitted("ina_id", "ina")
        self._test("ina_id", "OK", "Hersteller 0x5449 Gerät 0x2391")
        self._test("ina_config", "OK", "ADC_CONFIG zurückgelesen")
        if not self.with_2s:
            self._test("ina_bus", "SKIP", "0.02 V, 2S nicht versorgt")
            return "SKIP"
        self._test("ina_bus", "OK", f"VSERVO {self._v2():.3f} V, Mux 2S {self._v2():.3f} V, Strom 12.4 mA, Die 26.0 C")
        return "OK"

    def _t_seen(self, name, what):
        a = self._wait(f"{what}? (Enter = ja, n = nein, q = abbrechen)")
        if a < 0:
            self._test(name, "SKIP", "abgebrochen")
            return "SKIP"
        self._test(name, "OK" if a == 1 else "FEHL", "bestätigt" if a == 1 else "nicht gesehen")
        return "OK" if a == 1 else "FEHL"

    def _t_led(self):
        out = []
        for name, text in (("led_rot", "rot"), ("led_gruen", "grün"), ("led_blau", "blau"), ("led_weiss", "weiß")):
            out.append(self._t_seen(name, f"Leuchten beide LEDs {text}"))
            if out[-1] == "SKIP":
                break
        return self._worst(out)

    def _t_servo(self, i, mode):
        if not 0 <= i <= 3:
            self._test("servo", "FEHL", "Kanal 1..4")
            return "FEHL"
        name = f"servo{i + 1}_{SERVO_NAMES[i]}"
        if not self.with_2s:
            self._test(name, "SKIP", "2S nicht versorgt, VSERVO fehlt")
            return "SKIP"
        lo, hi = SERVO_LIMITS[i]
        c, mn, mx = (min(max(v, lo), hi) for v in self.cal["servo_us"][i])
        self._info(f"{name}: Fenster {lo}..{hi} us (Config.h), Mitte {c}, Grenzen {mn}..{mx} us (Kalibrierung)")
        m = mode.split()
        if m[0] == "us":
            us = min(max(self._int(m, 1, 1500), lo), hi)
            self._test(name, "OK", f"{us} us (geklemmt auf {lo}..{hi})")
        elif m[0] in ("min", "max"):
            self._test(name, "OK", f"Grenze {m[0]} {mn if m[0] == 'min' else mx} us")
        elif m[0] == "sweep":
            self._test(name, "OK", f"Durchlauf {c} -> {mx} -> {mn} -> {c} us")
        else:
            self._test(name, "OK", f"Mitte {c} us")
        self._sleep(0.6)
        a = self._wait(f"Hat sich Servo {i + 1} ({SERVO_NAMES[i]}) wie gemeldet bewegt? (Enter = ja, n = nein)")
        if a < 0:
            return "SKIP"
        if a == 0:
            self._test(name, "FEHL", "Bewegung nicht bestätigt")
            return "FEHL"
        return "OK"

    def _t_motor(self):
        self._test("motor_nfault_idle", "OK", "nFAULT hoch (schlafend)")
        if not self.with_2s:
            self._test("motor_pulse", "SKIP", "2S nicht versorgt")
            return "SKIP"
        if self._wait("Rollmotor: je ein 300-ms-Puls mit 30 % in beide Richtungen. Motor frei drehbar? Enter") != 1:
            self._test("motor_pulse", "SKIP", "abgebrochen")
            return "SKIP"
        self._sleep(1.4)
        self._test("motor_nfault_run", "OK", "nFAULT während der Pulse hoch")
        a = self._wait("Hat der Motor kurz vor und zurück gedreht? (Strom 0 / 0 mA) Enter = ja, n = nein")
        if a < 0:
            self._test("motor_pulse", "SKIP", "abgebrochen")
            return "SKIP"
        self._test("motor_pulse", "OK" if a == 1 else "FEHL", "bestätigt" if a == 1 else "nicht bestätigt")
        return "OK" if a == 1 else "FEHL"

    def _t_pyro(self, ch, pulse_ms):
        if not 0 <= ch <= 3:
            self._test("pyro", "FEHL", "Kanal 1..4")
            return "FEHL"
        name = f"pyro{ch + 1}_fire"
        if ch > 1:
            self._test(name, "SKIP", "Kanal DNP")
        elif not self.with_2s:
            self._test(name, "SKIP", "2S nicht versorgt")
        elif not self.armed:
            self._test(name, "SKIP", f"ARM nicht scharf ({self._varm():.2f} V), Schlüsselschalter")
        else:
            pulse_ms = min(max(pulse_ms, 20), 1000)
            if not self._confirm(f"Pyro {ch + 1} zünden, {pulse_ms} ms. NUR Lämpchen oder 2-Ohm-Widerstand, KEINE LADUNG. Tippe JA"):
                self._test(name, "SKIP", "nicht bestätigt")
                return "SKIP"
            time.sleep(pulse_ms / 1000.0)
            self._test(name, "OK", f"Puls {pulse_ms} ms, Sense bei Zündung 0.05 V (soll < 2.27), danach 7.52 V, Ausgang tief")
            return "OK"
        return "SKIP"

    def _t_lora(self):
        return self._not_fitted("lora_aux", "lora") if not self.fit["lora"] else self._fail("lora_aux", "AUX bleibt tief (nicht bestückt? dann 'fit lora off')")

    def _t_gps(self):
        return self._not_fitted("gps_nmea", "gps") if not self.fit["gps"] else self._fail("gps_nmea", "keine NMEA-Sätze bei 38400/9600 Bd")

    def _fail(self, name, detail):
        self._test(name, "FEHL", detail)
        return "FEHL"

    def _t_sd(self):
        self._test("sd_init", "OK", "Karte erkannt")
        self._sleep(1.0)
        self._test("sd_write", "OK", "1 MiB in 0.09 s = 11.21 MB/s, längster 4-KiB-Block 5120 us")
        self._test("sd_read", "OK", "1 MiB in 0.05 s = 19.80 MB/s, Inhalt stimmt")
        return "OK"

    def _t_timing(self):
        self._sleep(3.0)
        self._test("timing_loop", "OK", "750 Durchläufe bei 250 Hz: Mittel 612 us, Maximum 1105 us, Überläufe 0")
        return "OK"

    def _t_mem(self):
        self._test("psram", "OK", "8 MB (ein Chip), 1 MB Muster fehlerfrei, Schreiben 28 MB/s, Lesen 31 MB/s")
        self._test("qspi_flash", "OK", "JEDEC EF4018, 16384 KB")
        return "OK"

    def _t_watchdog(self):
        self._sleep(5.5)
        self._test("watchdog_feed", "OK", "2-s-Watchdog 3 s lang bedient, kein Neustart; danach abgeschaltet und 2,5 s ohne Bedienung überstanden")
        return "OK"

    # ------------------------------------------------------------ Live-Daten
    def _c_stream(self, hz):
        hz = min(max(hz, 1.0), 200.0)
        dt = 1.0 / hz
        self._info(f"stream {hz:.0f} Hz, q beendet. IMU und Magnetometer roh in Chip-Achsen (Format: Stream.h)")
        self._p(HDR)
        nan = float("nan")
        lines, t_next = 0, time.time()
        p_drift = 0.0
        while True:
            if self._abort():
                break
            now = time.time()
            if now < t_next:
                time.sleep(min(t_next - now, 0.005))
                continue
            t_next += dt
            if now - t_next > 4 * dt:
                t_next = now
            w = self._advance(dt)
            acc, gyro, mag = self._sensors(w)
            if not self.fit["imu"]:
                acc, gyro = [nan] * 3, [nan] * 3
            if not self.fit["mag"]:
                mag = [nan] * 3
            p_drift += self.rng.gauss(0, 0.05)
            p = 98712.0 + p_drift + self.rng.gauss(0, 1.5) if self.fit["baro"] else nan
            ia, vbus = (0.0124 + self.rng.gauss(0, 0.0005), self._v2()) if self.fit["ina"] else (nan, nan)
            rh, ts = (41.5, 23.41) if self.fit["sht"] else (nan, nan)
            py = 7.52 if self.armed and self.with_2s else 0.0
            vals = [int((now - self._t0) * 1000), *acc, *gyro, 24.3 + 0.02 * math.sin(now / 30), *mag, p, 25.1,
                    self._v1(), self._v2(), self._varm(), py, py, 0.0, 0.0, ia, vbus, rh, ts, 4 if self.fit["imu"] else 0]
            self._p("D " + " ".join(str(v) if isinstance(v, int) else f"{v:.5f}" for v in vals))
            lines += 1
        self._test("stream", "OK", f"{lines} Zeilen")
        return "OK"

    # ------------------------------------------------------------ Kalibrierung
    def _c_cal(self, a):
        sub = a[0] if a else "show"
        if sub == "gyro": return self._cal_gyro(float(a[1]) if len(a) > 1 else 10.0)
        if sub == "acc": return self._cal_acc()
        if sub == "mag": return self._cal_mag(float(a[1]) if len(a) > 1 else 40.0)
        if sub == "axes": return self._cal_axes()
        if sub == "baro": return self._cal_baro(float(a[1]) if len(a) > 1 else 20.0)
        if sub == "adc": return self._cal_adc(self._int(a, 1, -1))
        if sub == "ina": return self._not_fitted("cal_ina", "ina") if not self.fit["ina"] else "SKIP"
        if sub == "servo": return self._cal_servo(self._int(a, 1, 0) - 1)
        if sub == "set": return self._cal_set(a[1:])
        if sub == "save":
            self.saved_count += 1
            self.eeprom = copy.deepcopy(self.cal)
            self._test("cal_save", "OK", f"EEPROM 216 Byte, Version 1, CRC 0x1A2B3C4D, {self.saved_count}. Speicherung")
            return "OK"
        if sub == "load":
            if self.eeprom is None:
                self.cal = cm.default_cal()
                self._test("cal_load", "SKIP", "leer, Standardwerte geladen")
                return "SKIP"
            self.cal = copy.deepcopy(self.eeprom)
            self._test("cal_load", "OK", "ok")
            return "OK"
        if sub == "defaults":
            self.cal = cm.default_cal()
            self._test("cal_defaults", "OK", "Standardwerte im RAM (nicht gespeichert)")
            return "OK"
        if sub == "erase":
            if not self._confirm("Kalibrierung im EEPROM löschen? Tippe JA"):
                self._test("cal_erase", "SKIP", "nicht bestätigt")
                return "SKIP"
            self.eeprom, self.cal = None, cm.default_cal()
            self._test("cal_erase", "OK", "gelöscht, Standardwerte")
            return "OK"
        self._info(f"unbekannt: cal {sub}")
        return "FEHL"

    def _cal_gyro(self, seconds):
        seconds = min(max(seconds, 2.0), 120.0)
        self._info(f"Gyro-Nullpunkt: Platine {seconds:.0f} s ruhig liegen lassen (q bricht ab)")
        _, gyr, _ = self._average(min(seconds, 4.0), 400)
        self.cal["gyro_bias_dps"] = [float(x) for x in gyr]
        self.cal["gyro_noise_dps"] = [0.041, 0.040, 0.040]
        self.cal["gyro_bias_temp_c"] = 24.31
        self.cal["valid"] |= 1
        self._cal("gyro_bias_dps", f"{gyr[0]:.4f} {gyr[1]:.4f} {gyr[2]:.4f}")
        self._cal("gyro_bias_temp_c", "24.31")
        self._cal("gyro_noise_dps", "0.0410 0.0400 0.0400")
        self._test("cal_gyro", "OK", f"Nullpunkt {gyr[0]:.3f} {gyr[1]:.3f} {gyr[2]:.3f} dps bei 24.3 C")
        return "OK"

    def _cal_acc(self):
        pos = ["Platine flach, Bestückseite (Teensy) nach oben", "Platine flach, Bestückseite nach unten",
               "Platine hochkant auf die lange Kante mit dem Teensy-USB", "Platine hochkant auf die gegenüberliegende lange Kante",
               "Platine hochkant auf die kurze Kante mit der Spitze (GPS/J_STACK)", "Platine hochkant auf die gegenüberliegende kurze Kante"]
        faces = [(2, 1), (2, -1), (1, 1), (1, -1), (0, 1), (0, -1)]
        amin, amax = np.full(3, 1e9), np.full(3, -1e9)
        for k in range(6):
            if self._wait(f"Lage {k + 1}/6: {pos[k]}. Ruhig halten, dann Enter") != 1:
                self._test("cal_acc", "SKIP", "abgebrochen")
                return "SKIP"
            self._snap_up(*faces[k])
            acc, _, _ = self._average(1.5, 300)
            self._info(f"Lage {k + 1}: a = [{acc[0]:.3f} {acc[1]:.3f} {acc[2]:.3f}] m/s2")
            amin, amax = np.minimum(amin, acc), np.maximum(amax, acc)
        off, sc = 0.5 * (amax + amin), 2.0 * cm.G / (amax - amin)
        self.cal["acc_offset_ms2"], self.cal["acc_scale"] = off.tolist(), sc.tolist()
        self.cal["valid"] |= 2
        self._cal("acc_offset_ms2", f"{off[0]:.4f} {off[1]:.4f} {off[2]:.4f}")
        self._cal("acc_scale", f"{sc[0]:.5f} {sc[1]:.5f} {sc[2]:.5f}")
        self._test("cal_acc", "OK", f"Offset {off[0]:.3f} {off[1]:.3f} {off[2]:.3f} m/s2, Skalierung {sc[0]:.4f} {sc[1]:.4f} {sc[2]:.4f}")
        self._snap_up(2, 1)
        return "OK"

    def _cal_mag(self, seconds):
        if not self.fit["mag"]:
            return self._not_fitted("cal_mag", "mag")
        seconds = min(max(seconds, 10.0), 180.0)
        if self._wait(f"Magnetometer: Platine {seconds:.0f} s langsam um alle Achsen drehen (alle Richtungen, auch über Kopf). Enter zum Start") != 1:
            self._test("cal_mag", "SKIP", "abgebrochen")
            return "SKIP"
        pts = []
        rng = np.random.default_rng(3)
        for k in range(600):                         # gleichmäßig verteilte Lagen statt echter Wartezeit
            v = rng.normal(size=4)
            with self._lock:
                self.q = v / np.linalg.norm(v)
            pts.append(self._sensors(np.zeros(3))[2])
            if k % 150 == 149:
                self._sleep(1.0)
                self._info(f"{k + 1} Proben, noch {int(seconds * (1 - (k + 1) / 600))} s")
                if self._abort():
                    self._test("cal_mag", "SKIP", "abgebrochen")
                    return "SKIP"
        self._snap_up(2, 1)
        r = cm.fit_ellipsoid(pts)
        if "offset" not in r:
            self._test("cal_mag", "FEHL", "Fit nicht lösbar")
            return "FEHL"
        self.cal["mag_offset_gauss"], self.cal["mag_soft_iron"], self.cal["mag_field_gauss"] = r["offset"], r["soft_iron"], r["field"]
        if r["ok"]:
            self.cal["valid"] |= 4
        self._cal("mag_offset_gauss", " ".join(f"{v:.5f}" for v in r["offset"]))
        self._cal("mag_soft_iron", " ".join(f"{v:.5f}" for v in r["soft_iron"]))
        self._cal("mag_field_gauss", f"{r['field']:.4f}")
        self._cal("mag_fit", f"{r['n']} {r['residual_pct']:.2f} {r['octants']} {r['axis_ratio']:.3f}")
        self._test("cal_mag", "OK" if r["ok"] else "FEHL", f"{r['n']} Proben, Feld {r['field']:.3f} gauss, Residuum {r['residual_pct']:.1f} %, "
                   f"Oktanten {r['octants']}/8, Achsen {r['axis_ratio']:.2f}")
        return "OK" if r["ok"] else "FEHL"

    def _cal_axes(self):
        amap, sign = SIM_TRUTH["imu_axis_map"], SIM_TRUTH["imu_axis_sign"]
        if self._wait("Achsen 1/3: Rakete bzw. Platine mit der SPITZE nach oben halten (Rollachse senkrecht), Enter") != 1:
            self._test("cal_axes", "SKIP", "abgebrochen")
            return "SKIP"
        self._snap_up(amap[2], sign[2])
        self._sleep(1.0)
        if self._wait("Achsen 2/3: die Seite, die Körper +x sein soll, nach OBEN halten (Spitze waagerecht), Enter") != 1:
            self._test("cal_axes", "SKIP", "abgebrochen")
            return "SKIP"
        self._snap_up(amap[0], sign[0])
        self._sleep(1.0)
        self.cal["imu_axis_map"], self.cal["imu_axis_sign"] = list(amap), list(sign)
        self.cal["valid"] |= 8
        self._cal("imu_axis_map", " ".join(map(str, amap)))
        self._cal("imu_axis_sign", " ".join(map(str, sign)))
        ax = "xyz"
        self._test("cal_axes_imu", "OK", "body " + ", ".join(f"{ax[i]} = {'+' if sign[i] > 0 else '-'}{ax[amap[i]]}" for i in range(3)) + " (Chip-Achsen)")
        if self._wait("Achsen 3/3: Platine 20 s um alle Achsen drehen (zügig, alle Richtungen), Enter zum Start") != 1:
            self._test("cal_axes_mag", "SKIP", "abgebrochen")
            return "OK"
        self._sleep(3.0)
        self.cal["mag_axis_map"], self.cal["mag_axis_sign"] = list(amap), list(sign)
        self._cal("mag_axis_map", " ".join(map(str, amap)))
        self._cal("mag_axis_sign", " ".join(map(str, sign)))
        self._cal("mag_axis_fit", "1500 0.0123 8.4")
        self._test("cal_axes_mag", "OK", "Magnetometer wie IMU zugeordnet (Mag-Chip), 1500 Proben, Eindeutigkeit 8.4")
        self._snap_up(2, 1)
        return "OK"

    def _cal_baro(self, seconds):
        seconds = min(max(seconds, 5.0), 120.0)
        self._info(f"Bodenreferenz: {seconds:.0f} s, kein Luftzug")
        self._sleep(min(seconds, 4.0))
        self.cal["baro_ground_pa"], self.cal["baro_noise_pa"], self.cal["baro_ground_temp_c"] = 98712.4, 1.52, 25.1
        self.cal["valid"] |= 16
        self._cal("baro_ground_pa", "98712.4")
        self._cal("baro_noise_pa", "1.52")
        self._cal("baro_ground_temp_c", "25.10")
        self._test("cal_baro", "OK", "400 Messungen, 98712.4 Pa, Rauschen 1.52 Pa = 0.13 m, 25.1 C")
        return "OK"

    def _cal_adc(self, channel):
        nets = ["PYRO1_NEG", "PYRO2_NEG", "PYRO3_NEG", "PYRO4_NEG", "VBAT1_F", "VBAT2_F", "VBAT_ARMED", "GND"]
        true = {4: 3.98, 5: 7.62 if self.with_2s else 0.02, 6: 7.55 if self.armed and self.with_2s else 0.01}
        out = []
        for ch in ([channel] if channel >= 0 else [4, 5, 6]):
            name, meas = f"cal_adc{ch}", true.get(ch, 0.0) * 0.994          # der Teiler der Simulation misst 0,6 % zu wenig
            if meas < 0.5:
                self._test(name, "SKIP", f"{nets[ch]}: nur {meas:.3f} V, nicht versorgt")
                out.append("SKIP")
                continue
            user = self._ask(f"Kanal {ch} {nets[ch]}: Teensy misst {meas:.3f} V. Multimeter an {nets[ch]} gegen GND, Wert in V")
            if user is None:
                self._test(name, "SKIP", "übersprungen")
                out.append("SKIP")
                continue
            gain = user / meas
            ok = 0.9 < gain < 1.1
            if ok:
                self.cal["adc_gain"][ch] = gain
                self.cal["valid"] |= 32
            self._cal("adc_gain", f"{ch} {gain:.5f}")
            self._test(name, "OK" if ok else "FEHL", f"gemessen {meas:.3f} V, Multimeter {user:.3f} V, Faktor {gain:.4f}"
                       + ("" if ok else " (> 10 %: Teiler oder Eingabe prüfen, nicht übernommen)"))
            out.append("OK" if ok else "FEHL")
        return self._worst(out)

    def _cal_servo(self, i):
        if not 0 <= i <= 3:
            self._test("cal_servo", "FEHL", "Kanal 1..4")
            return "FEHL"
        name = f"cal_servo{i + 1}"
        if not self.with_2s:
            self._test(name, "SKIP", "2S nicht versorgt")
            return "SKIP"
        lo, hi = SERVO_LIMITS[i]
        c, mn, mx = (min(max(v, lo), hi) for v in self.cal["servo_us"][i])
        us = c
        self._info(f"Servo {i + 1} trimmen, Fenster {lo}..{hi} us. Befehle: + - (10 us), ++ -- (50 us), <zahl> us, c = Mitte, a = min, b = max, ok, q")
        while True:
            self._info(f"servo{i + 1} {us} us (Mitte {c}, min {mn}, max {mx})")
            self._p("WAIT Befehl")
            line = self._readline(120.0)
            if line is None or line[:1] == "q":
                self._test(name, "SKIP", "abgebrochen")
                return "SKIP"
            if line == "++": us += 50
            elif line == "--": us -= 50
            elif line[:1] == "+": us += 10
            elif line[:1] == "-": us -= 10
            elif line[:1] == "c": c = us
            elif line[:1] == "a": mn = us
            elif line[:1] == "b": mx = us
            elif line in ("ok", ""): break
            elif line[:1].isdigit(): us = int(float(line))
            us = min(max(us, lo), hi)
        mn, mx = min(mn, mx), max(mn, mx)
        c = min(max(c, mn), mx)
        self.cal["servo_us"][i] = [c, mn, mx]
        self.cal["valid"] |= 128
        self._cal("servo_us", f"{i + 1} {c} {mn} {mx}")
        self._test(name, "OK", f"Mitte {c}, min {mn}, max {mx} us")
        return "OK"

    def _cal_set(self, a):
        if not a:
            return self._fail("cal_set", "Name fehlt (cal set <name> <werte>)")
        name = a[0]
        try:
            v = [float(x) for x in a[1:]]
        except ValueError:
            return self._fail("cal_set", f"{name}: Wert nicht lesbar oder zu viele Werte")
        if any(not math.isfinite(x) for x in v):
            return self._fail("cal_set", f"{name}: Wert nicht lesbar oder zu viele Werte")
        rng = lambda lo, hi: all(lo <= x <= hi for x in v)    # noqa: E731
        c, err, bit = self.cal, None, 0
        if name == "gyro_bias_dps":
            if len(v) != 3 or not rng(-10, 10): err = "3 Werte, |Wert| <= 10 dps"
            else: c[name], bit = v, 1
        elif name == "acc_offset_ms2":
            if len(v) != 3 or not rng(-3, 3): err = "3 Werte, |Wert| <= 3 m/s2"
            else: c[name], bit = v, 2
        elif name == "acc_scale":
            if len(v) != 3 or not rng(0.8, 1.2): err = "3 Werte, 0.8..1.2"
            else: c[name], bit = v, 2
        elif name == "mag_offset_gauss":
            if len(v) != 3 or not rng(-4, 4): err = "3 Werte, |Wert| <= 4 gauss"
            else: c[name], bit = v, 4
        elif name == "mag_soft_iron":
            if len(v) != 9 or not rng(-5, 5) or min(v[0], v[4], v[8]) < 0.2: err = "9 Werte zeilenweise, |Wert| <= 5, Diagonale >= 0.2"
            else: c[name], bit = v, 4
        elif name == "mag_field_gauss":
            if len(v) != 1 or not rng(0.1, 1.5): err = "1 Wert, 0.1..1.5 gauss"
            else: c[name] = v[0]
        elif name in ("imu_axis", "mag_axis"):
            ok = len(v) == 6 and sorted(v[:3]) == [0, 1, 2] and all(abs(s) == 1 for s in v[3:])
            if not ok or not cm.right_handed([int(x) for x in v[:3]], [int(x) for x in v[3:]]):
                err = "6 Werte: map0 map1 map2 sign0 sign1 sign2, Permutation von 0 1 2, Vorzeichen +-1, rechtshaendig"
            else:
                c[name + "_map"], c[name + "_sign"] = [int(x) for x in v[:3]], [int(x) for x in v[3:]]
                bit = 8 if name == "imu_axis" else 0
        elif name == "baro_ground_pa":
            if len(v) != 1 or not rng(80000, 110000): err = "1 Wert, 80000..110000 Pa"
            else: c[name], bit = v[0], 16
        elif name == "adc_gain":
            if len(v) != 2 or v[0] not in range(8) or not 0.9 <= v[1] <= 1.1: err = "<kanal 0..7> <faktor 0.9..1.1>"
            else:
                c["adc_gain"][int(v[0])] = v[1]
                bit = 32
        elif name in ("ina_offset_a", "ina_gain"):
            lo, hi = (-0.2, 0.2) if name == "ina_offset_a" else (0.9, 1.1)
            if len(v) != 1 or not rng(lo, hi): err = f"1 Wert, {lo}..{hi}"
            else: c[name], bit = v[0], 64
        elif name == "servo_us":
            ch = int(v[0]) - 1 if len(v) == 4 else -1
            lo, hi = SERVO_LIMITS[ch] if 0 <= ch <= 3 else (0, 0)
            if not 0 <= ch <= 3 or not all(lo <= x <= hi for x in v[1:]) or not v[2] <= v[1] <= v[3]:
                err = "<kanal 1..4> <mitte> <min> <max> in us, min <= mitte <= max, im Fenster aus Config.h"
            else:
                c["servo_us"][ch] = [int(x) for x in v[1:]]
                bit = 128
        elif name == "valid":
            if len(v) != 1 or v[0] != int(v[0]) or not 0 <= v[0] <= 255: err = "Bitmaske 0..255"
            else: c["valid"] = int(v[0])
        else:
            return self._fail("cal_set", f"unbekannter Name {name}")
        if err:
            return self._fail("cal_set", f"{name} nicht uebernommen: {err}")
        c["valid"] |= bit
        self._cal("valid", str(c["valid"]))
        self._test("cal_set", "OK", f"{name} im RAM gesetzt ({len(v)} Werte), noch nicht gespeichert: cal save")
        return "OK"

    def _cal_show(self):
        d = self.cal
        f3 = lambda v, n=4: " ".join(f"{x:.{n}f}" for x in v)      # noqa: E731
        self._info(f"Kalibrierung: {'ok' if self.eeprom else 'leer'}, Version 1, gespeichert {self.saved_count} mal, gültig 0x{d['valid']:02X} "
                   "(GYRO 1 ACC 2 MAG 4 AXES 8 BARO 10 ADC 20 INA 40 SERVO 80)")
        self._cal("valid", str(d["valid"]))
        self._cal("gyro_bias_dps", f3(d["gyro_bias_dps"]))
        self._cal("gyro_bias_temp_c", f"{d['gyro_bias_temp_c']:.2f}")
        self._cal("gyro_noise_dps", f3(d["gyro_noise_dps"]))
        self._cal("acc_offset_ms2", f3(d["acc_offset_ms2"]))
        self._cal("acc_scale", f3(d["acc_scale"], 5))
        self._cal("mag_offset_gauss", f3(d["mag_offset_gauss"], 5))
        self._cal("mag_soft_iron", f3(d["mag_soft_iron"], 5))
        self._cal("mag_field_gauss", f"{d['mag_field_gauss']:.4f}")
        for k in ("imu_axis_map", "imu_axis_sign", "mag_axis_map", "mag_axis_sign"):
            self._cal(k, " ".join(str(int(x)) for x in d[k]))
        self._cal("baro_ground_pa", f"{d['baro_ground_pa']:.1f}")
        self._cal("baro_noise_pa", f"{d['baro_noise_pa']:.2f}")
        self._cal("baro_ground_temp_c", f"{d['baro_ground_temp_c']:.2f}")
        for i in range(8):
            self._cal("adc_gain", f"{i} {d['adc_gain'][i]:.5f}")
        self._cal("ina_offset_a", f"{d['ina_offset_a']:.5f}")
        self._cal("ina_gain", f"{d['ina_gain']:.5f}")
        for i in range(4):
            self._cal("servo_us", f"{i + 1} {d['servo_us'][i][0]} {d['servo_us'][i][1]} {d['servo_us'][i][2]}")
