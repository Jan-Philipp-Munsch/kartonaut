"""Rechenteil der Oberfläche: Kalibrierung anwenden, Fits, Lage. Nur numpy, keine Hardware.

Die Formeln sind dieselben wie in der Firmware (lib/calstore/CalData.h, EllipsoidFit.h):

    Beschleunigung   korrigiert = (roh - acc_offset) * acc_scale          je Chip-Achse
    Drehrate         korrigiert = roh - gyro_bias
    Magnetfeld       korrigiert = soft_iron · (roh - mag_offset)          Chip-Achsen
    Körperachsen     body[i] = sign[i] * chip[map[i]]

Verfahren:
  * fit_accel     N ruhende Lagen (mindestens 6, jede Achse einmal nach oben und unten): Offset und
                  Skalierung je Achse so, dass |a| in jeder Lage 1 g ist. Verallgemeinert das
                  6-Lagen-Verfahren (ST DT0053); die Lagen müssen nicht genau ausgerichtet sein.
  * fit_ellipsoid Hard-/Soft-Iron des Magnetometers: Ellipsoid durch die Messpunkte, wie
                  EllipsoidFit.h in der Firmware und MotionCal (PJRC).
  * RotationCheck Skalenprüfung des Gyros: Platine um eine Achse um einen bekannten Winkel drehen
                  (z. B. 360° an einer Tischkante), die integrierte Drehrate muss ihn ergeben.
"""
import math
from collections import deque

import numpy as np

G = 9.80665

VALID_BITS = {"gyro": 1, "acc": 2, "mag": 4, "axes": 8, "baro": 16, "adc": 32, "ina": 64, "servo": 128}


def default_cal():
    """Standardwerte wie cal::defaults() in CalData.h."""
    return {
        "valid": 0,
        "gyro_bias_dps": [0.0, 0.0, 0.0], "gyro_bias_temp_c": 0.0, "gyro_noise_dps": [0.0, 0.0, 0.0],
        "acc_offset_ms2": [0.0, 0.0, 0.0], "acc_scale": [1.0, 1.0, 1.0],
        "mag_offset_gauss": [0.0, 0.0, 0.0], "mag_soft_iron": [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0], "mag_field_gauss": 0.5,
        "imu_axis_map": [0, 1, 2], "imu_axis_sign": [1, 1, 1], "mag_axis_map": [0, 1, 2], "mag_axis_sign": [1, 1, 1],
        "baro_ground_pa": 101325.0, "baro_noise_pa": 0.0, "baro_ground_temp_c": 15.0,
        "adc_gain": [1.0] * 8, "ina_offset_a": 0.0, "ina_gain": 1.0,
        "servo_us": [[1500, 1000, 2000] for _ in range(4)],
    }


def update_cal(cal, name, values):
    """Eine CAL-Zeile der Konsole in das Kalibrier-Dict übernehmen. True, wenn der Name bekannt ist."""
    if name == "adc_gain" and len(values) == 2:
        cal["adc_gain"][int(values[0])] = float(values[1])
    elif name == "servo_us" and len(values) == 4:
        cal["servo_us"][int(values[0]) - 1] = [int(v) for v in values[1:]]
    elif name in cal and name not in ("adc_gain", "servo_us"):
        cur = cal[name]
        if isinstance(cur, list):
            if len(values) != len(cur):
                return False
            cal[name] = [type(cur[0])(v) for v in values]
        else:
            cal[name] = type(cur)(values[0])
    else:
        return False
    return True


def map_axes(amap, sign, chip):
    return [sign[i] * chip[amap[i]] for i in range(3)]


def apply_acc(cal, raw):
    return [(raw[i] - cal["acc_offset_ms2"][i]) * cal["acc_scale"][i] for i in range(3)]


def apply_gyro(cal, raw):
    return [raw[i] - cal["gyro_bias_dps"][i] for i in range(3)]


def apply_mag(cal, raw):
    c = [raw[i] - cal["mag_offset_gauss"][i] for i in range(3)]
    w = cal["mag_soft_iron"]
    return [w[3 * i] * c[0] + w[3 * i + 1] * c[1] + w[3 * i + 2] * c[2] for i in range(3)]


def right_handed(amap, sign):
    m = np.zeros((3, 3))
    for i in range(3):
        m[i, amap[i]] = sign[i]
    return np.linalg.det(m) > 0


# ---------------------------------------------------------------- Magnetometer: Ellipsoid
def sphere_coverage(dirs, bands=4, sectors=8):
    """Anteil belegter, gleich großer Felder der Kugel (bands × sectors) für Einheitsrichtungen."""
    d = np.asarray(dirs, float)
    if len(d) == 0:
        return 0.0
    d = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    band = np.clip(((d[:, 2] + 1) / 2 * bands).astype(int), 0, bands - 1)       # gleiche Fläche je z-Band
    sector = np.clip(((np.arctan2(d[:, 1], d[:, 0]) + math.pi) / (2 * math.pi) * sectors).astype(int), 0, sectors - 1)
    return len(set(zip(band.tolist(), sector.tolist()))) / (bands * sectors)


def fit_ellipsoid(points):
    """Ellipsoid a x² + b y² + c z² + 2h xy + 2g xz + 2f yz + 2p x + 2q y + 2r z = 1 durch die Punkte.

    Liefert dict(ok, offset[3], soft_iron[9], field, residual_pct, axis_ratio, n, octants, coverage)
    mit korrigiert = soft_iron · (roh - offset); ok = False mit "reason", wenn der Fit nicht trägt.
    """
    p = np.asarray(points, float)
    n = len(p)
    if n < 50:
        return {"ok": False, "reason": f"nur {n} Punkte (mindestens 50)", "n": n}
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    d = np.column_stack([x * x, y * y, z * z, 2 * x * y, 2 * x * z, 2 * y * z, 2 * x, 2 * y, 2 * z])
    v, *_ = np.linalg.lstsq(d, np.ones(n), rcond=None)
    a = np.array([[v[0], v[3], v[4]], [v[3], v[1], v[5]], [v[4], v[5], v[2]]])
    b = v[6:9]
    try:
        c = -np.linalg.solve(a, b)
    except np.linalg.LinAlgError:
        return {"ok": False, "reason": "Fit nicht lösbar (zu wenig Drehung)", "n": n}
    k = 1.0 + c @ a @ c
    if k <= 0:
        return {"ok": False, "reason": "kein Ellipsoid (zu wenig Drehung)", "n": n}
    w, vecs = np.linalg.eigh(a / k)
    if np.any(w <= 0):
        return {"ok": False, "reason": "kein Ellipsoid (zu wenig Drehung)", "n": n}
    radius = 1.0 / np.sqrt(w)
    field = float(np.cbrt(np.prod(radius)))
    soft = vecs @ np.diag(np.sqrt(w) * field) @ vecs.T
    corr = (p - c) @ soft.T
    rad = np.linalg.norm(corr, axis=1)
    residual = float(np.sqrt(np.mean((rad - field) ** 2)) / field * 100.0)
    dd = p - c
    octants = len(set(((dd[:, 0] > 0).astype(int) | ((dd[:, 1] > 0).astype(int) << 1) | ((dd[:, 2] > 0).astype(int) << 2)).tolist()))
    coverage = sphere_coverage(corr)
    ratio = float(radius.max() / radius.min())
    # dieselben Annahmegrenzen wie "cal mag" in der Firmware (Calib.cpp)
    ok = octants == 8 and residual < 10.0 and 0.15 < field < 1.2 and ratio < 2.0
    out = {"ok": bool(ok), "offset": c.tolist(), "soft_iron": soft.reshape(9).tolist(), "field": field,
           "residual_pct": residual, "axis_ratio": ratio, "n": n, "octants": octants, "coverage": coverage}
    if not ok:
        out["reason"] = "Abdeckung, Residuum oder Feldbetrag außerhalb der Grenzen (alle 8 Oktanten, Residuum < 10 %, 0,15..1,2 gauss, Achsverhältnis < 2)"
    return out


# ---------------------------------------------------------------- Beschleunigung: N Lagen
def fit_accel(positions, g=G):
    """Offset und Skalierung je Achse aus ruhenden Lagen (Mittelwerte der rohen Beschleunigung).

    Modell: Σ_i (s_i (a_i - b_i))² = g² in jeder Lage. Mit α_i = s_i²/C, β_i = s_i² b_i/C wird daraus
    die lineare Gleichung Σ α_i a_i² - 2 β_i a_i = 1 (C = g² - Σ s_i² b_i²), gelöst mit kleinsten Quadraten.
    """
    p = np.asarray(positions, float)
    n = len(p)
    if n < 6:
        return {"ok": False, "reason": f"{n} Lagen, mindestens 6", "n": n}
    lo, hi = p.min(axis=0), p.max(axis=0)
    if np.any(hi < 0.5 * g) or np.any(lo > -0.5 * g):
        return {"ok": False, "reason": "jede Achse muss einmal nach oben und einmal nach unten zeigen", "n": n}
    d = np.column_stack([p[:, 0] ** 2, p[:, 1] ** 2, p[:, 2] ** 2, -2 * p[:, 0], -2 * p[:, 1], -2 * p[:, 2]])
    v, *_ = np.linalg.lstsq(d, np.ones(n), rcond=None)
    alpha, beta = v[:3], v[3:]
    if np.any(alpha <= 0):
        return {"ok": False, "reason": "Fit nicht lösbar (Lagen zu ähnlich)", "n": n}
    b = beta / alpha
    c = g * g / (1.0 + np.sum(alpha * b * b))
    s = np.sqrt(alpha * c)
    before = np.linalg.norm(p, axis=1) - g
    after = np.linalg.norm((p - b) * s, axis=1) - g
    plausible = bool(np.all(np.abs(b) < 1.0) and np.all(np.abs(s - 1) < 0.05))
    out = {"ok": plausible, "offset": b.tolist(), "scale": s.tolist(), "n": n,
           "rms_before": float(np.sqrt(np.mean(before ** 2))), "rms_after": float(np.sqrt(np.mean(after ** 2)))}
    if not plausible:
        out["reason"] = "Offset über 1 m/s² oder Skalierung mehr als 5 % von 1 entfernt (wie cal acc in der Firmware)"
    return out


class StillDetector:
    """Erkennt Ruhe aus der Streuung von Drehrate und Beschleunigung über ein Zeitfenster.

    Arbeitet auf rohen Werten: es zählt die Spanne im Fenster, nicht der Betrag, damit ein
    unkalibrierter Nullpunkt nicht als Bewegung gilt.
    """

    def __init__(self, window_s=0.5, gyro_span_dps=3.0, acc_span_ms2=0.6):
        self.window_s, self.gyro_span, self.acc_span = window_s, gyro_span_dps, acc_span_ms2
        self.buf = deque()

    def feed(self, t, acc, gyro):
        self.buf.append((t, acc, gyro))
        while self.buf and t - self.buf[0][0] > self.window_s:
            self.buf.popleft()
        if len(self.buf) < 5 or self.buf[-1][0] - self.buf[0][0] < 0.8 * self.window_s:
            return False
        a = np.array([b[1] for b in self.buf])
        w = np.array([b[2] for b in self.buf])
        return bool(np.all(np.ptp(w, axis=0) < self.gyro_span) and np.all(np.ptp(a, axis=0) < self.acc_span))


class PositionCollector:
    """Sammelt ruhende Lagen für fit_accel: jede neue Richtung, die mindestens hold_s ruhig war."""

    def __init__(self, hold_s=1.0, min_angle_deg=25.0):
        self.still = StillDetector()
        self.hold_s, self.min_cos = hold_s, math.cos(math.radians(min_angle_deg))
        self.positions = []
        self._t0, self._sum, self._n, self._taken = None, np.zeros(3), 0, False
        self.is_still = False

    def feed(self, t, acc, gyro):
        """True, wenn mit diesem Wert eine neue Lage dazugekommen ist."""
        self.is_still = self.still.feed(t, acc, gyro)
        if not self.is_still:
            self._t0, self._n, self._taken = None, 0, False
            self._sum = np.zeros(3)
            return False
        if self._t0 is None:
            self._t0 = t
        self._sum += acc
        self._n += 1
        if self._taken or t - self._t0 < self.hold_s:
            return False
        mean = self._sum / self._n
        u = mean / max(np.linalg.norm(mean), 1e-9)
        for q in self.positions:
            if float(np.dot(u, np.asarray(q) / np.linalg.norm(q))) > self.min_cos:
                self._taken = True          # diese Lage gibt es schon
                return False
        self.positions.append(mean.tolist())
        self._taken = True
        return True

    def faces(self):
        """Welche der sechs Richtungen +x -x +y -y +z -z (Chip-Achse nach oben) schon dabei sind."""
        seen = [False] * 6
        for q in self.positions:
            i = int(np.argmax(np.abs(q)))
            if abs(q[i]) > 0.8 * np.linalg.norm(q):
                seen[2 * i + (0 if q[i] > 0 else 1)] = True
        return seen


class RotationCheck:
    """Gyro-Skala: ruhig halten, um eine Achse drehen, wieder ruhig halten; integriert die Drehrate."""

    def __init__(self):
        self.still = StillDetector()
        self.state = "warte auf Ruhe"       # -> bereit -> dreht -> fertig
        self.bias = np.zeros(3)
        self._bias_sum, self._bias_n = np.zeros(3), 0
        self.angle = np.zeros(3)
        self._t_last = None
        self._quiet_since = None
        self.result = None

    def feed(self, t, acc, gyro):
        gyro = np.asarray(gyro, float)
        still = self.still.feed(t, acc, gyro)
        dt = 0.0 if self._t_last is None else min(t - self._t_last, 0.1)
        self._t_last = t
        if self.state in ("warte auf Ruhe", "bereit"):
            if still:
                self._bias_sum += gyro
                self._bias_n += 1
                if self._bias_n >= 25:
                    self.bias = self._bias_sum / self._bias_n
                    self.state = "bereit"
            elif self.state == "bereit" and np.max(np.abs(gyro - self.bias)) > 8.0:
                self.state = "dreht"
                self.angle = (gyro - self.bias) * dt
            elif self.state == "warte auf Ruhe":
                self._bias_sum, self._bias_n = np.zeros(3), 0
        elif self.state == "dreht":
            self.angle += (gyro - self.bias) * dt
            # Ende der Drehung am Betrag über dem Nullpunkt erkennen, nicht an der Streuung:
            # eine gleichmäßige Drehung hat keine Streuung und sähe sonst wie Ruhe aus.
            if np.max(np.abs(gyro - self.bias)) > 3.0:
                self._quiet_since = None
            elif self._quiet_since is None:
                self._quiet_since = t
            if self._quiet_since is not None and t - self._quiet_since >= 0.5:
                axis = int(np.argmax(np.abs(self.angle)))
                ang = float(self.angle[axis])
                turns = max(1, round(abs(ang) / 360.0)) if abs(ang) > 270 else 0
                ref = 360.0 * turns if turns else round(abs(ang) / 90.0) * 90.0
                self.result = {"axis": "xyz"[axis], "angle_deg": ang, "all_deg": self.angle.tolist(), "reference_deg": ref,
                               "scale_error_pct": (abs(ang) / ref - 1.0) * 100.0 if ref > 0 else None,
                               "bias_dps": self.bias.tolist()}
                self.state = "fertig"
        return self.state


# ---------------------------------------------------------------- Lage (Mahony)
class Attitude:
    """Lage als Quaternion Körper -> Navigation (z nach oben): Gyro integriert, Beschleunigung
    (und kalibriertes Magnetometer) stützen. Nur für die Anzeige; die Flug-Firmware rechnet selbst."""

    def __init__(self, kp=1.5):
        self.q = np.array([1.0, 0.0, 0.0, 0.0])
        self.kp = kp
        self.started = False

    def update(self, acc, gyro_dps, dt, mag=None):
        a = np.asarray(acc, float)
        an = np.linalg.norm(a)
        w = np.radians(np.asarray(gyro_dps, float))
        if not np.all(np.isfinite(w)) or not np.isfinite(an):
            return self.q
        q0, q1, q2, q3 = self.q
        if 0.5 * G < an < 1.5 * G:
            a = a / an
            if not self.started:                 # Start: direkt aus der Schwerkraft
                self.q = quat_from_up(a)
                self.started = True
                return self.q
            v = np.array([2 * (q1 * q3 - q0 * q2), 2 * (q0 * q1 + q2 * q3), q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3])
            e = np.cross(a, v)
            if mag is not None and np.all(np.isfinite(mag)) and np.linalg.norm(mag) > 1e-6:
                m = np.asarray(mag, float) / np.linalg.norm(mag)
                r = quat_matrix(self.q)
                h = r @ m
                bref = np.array([math.hypot(h[0], h[1]), 0.0, h[2]])
                e += np.cross(m, r.T @ bref)
            w = w + self.kp * e
        dq = 0.5 * quat_mul(self.q, np.array([0.0, *w]))
        self.q = self.q + dq * dt
        self.q /= np.linalg.norm(self.q)
        return self.q

    def tilt_deg(self):
        r = quat_matrix(self.q)
        return math.degrees(math.acos(max(-1.0, min(1.0, r[2, 2]))))     # Winkel Körper-z gegen die Senkrechte

    def heading_deg(self):
        r = quat_matrix(self.q)
        return math.degrees(math.atan2(r[1, 0], r[0, 0])) % 360.0


def quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def quat_matrix(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def quat_from_up(up_body):
    """Kürzeste Drehung, die die Körperrichtung up_body auf Navigation +z legt."""
    u = np.asarray(up_body, float)
    u = u / np.linalg.norm(u)
    c = float(u[2])
    if c < -0.9999:
        return np.array([0.0, 1.0, 0.0, 0.0])
    axis = np.cross(u, [0.0, 0.0, 1.0])
    q = np.array([1.0 + c, *axis])
    return q / np.linalg.norm(q)


def altitude_m(p_pa, p0_pa):
    """Barometrische Höhe über dem Referenzdruck (Normatmosphäre), wie BMP390::altitude_m."""
    if not (p_pa > 0 and p0_pa > 0):
        return float("nan")
    return 44330.0 * (1.0 - (p_pa / p0_pa) ** 0.1903)
