"""Auswertung von Experiment E01: Servo-Soll -> Kardanwinkel (``firmware/examples/servo_ident``).

Eingang ist die CSV des Sketches (Kopfzeilen ``# key: value``, dann Spalten
``t_us,seg,axis,servo_deg,cmd_rel_deg,pulse_us,gx_dps,gy_dps,gz_dps,ax_g,ay_g,az_g``).
Die IMU sitzt auf dem Motorrohr; der Kardanwinkel wird aus der Drehrate um die Kardanachse
integriert und an den Haltephasen mit dem Schwerkraftvektor des Beschleunigungssensors gegen
Drift verankert. Daraus kommen

* die statische Kennlinie (Kardan-Grad je Servo-Grad, Nullpunktfehler, Hysterese) aus der Treppe,
* Kennwerte der Sprungantworten (Totzeit, Anstiegszeit, Maximalrate, Überschwingen),
* ein PT2-Modell mit Totzeit (``ServoParams``), gefittet an Sprünge und Wechselsprünge,
* der Frequenzgang aus den Chirps mit Bandbreite und Phasenverlust.

Die Anregungsfolge ist hier in ``build_sequence``/``command_at`` nachgebildet, damit
``synthesize_run`` eine künstliche Messung mit bekannten Parametern erzeugen kann (Tests).
"""
from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.optimize import least_squares

from .params import ServoParams

# Segmentkennungen wie im Sketch (Spalte ``seg``)
SEG_IDLE, SEG_HOLD0, SEG_STAIR, SEG_STEPS, SEG_ALT, SEG_CHIRP_S, SEG_CHIRP_L, SEG_HOLD1 = range(8)
SEG_NAMES = {SEG_IDLE: "idle", SEG_HOLD0: "hold_start", SEG_STAIR: "staircase", SEG_STEPS: "steps",
             SEG_ALT: "alternate", SEG_CHIRP_S: "chirp_small", SEG_CHIRP_L: "chirp_large", SEG_HOLD1: "hold_end"}

# Versuchsparameter, identisch zu den Konstanten in main.cpp
STAIR_HOLD_S, STAIR_LEVELS = 0.8, 5
STEP_HOLD_S, ALT_HOLD_S = 1.0, 0.8
CHIRP_F0_HZ, CHIRP_F1_HZ, CHIRP_T_S, CHIRP_FADE_S = 0.3, 12.0, 20.0, 0.5
HOLD_START_S, HOLD_END_S = 2.0, 2.0


# ---------------------------------------------------------------------------
# Anregungsfolge (Spiegel von buildSequence/chirpValue im Sketch)
# ---------------------------------------------------------------------------

@dataclass
class Piece:
    seg: int
    kind: str          # "hold" | "chirp"
    a: float
    dur_s: float


def build_sequence(A: float) -> list[Piece]:
    p: list[Piece] = [Piece(SEG_HOLD0, "hold", 0.0, HOLD_START_S)]
    for i in range(1, STAIR_LEVELS + 1):
        p.append(Piece(SEG_STAIR, "hold", A * i / STAIR_LEVELS, STAIR_HOLD_S))
    for i in range(STAIR_LEVELS - 1, -STAIR_LEVELS - 1, -1):
        p.append(Piece(SEG_STAIR, "hold", A * i / STAIR_LEVELS, STAIR_HOLD_S))
    for i in range(-STAIR_LEVELS + 1, 1):
        p.append(Piece(SEG_STAIR, "hold", A * i / STAIR_LEVELS, STAIR_HOLD_S))
    for s in (1.0, -1.0):
        for frac in (0.25, 0.5, 1.0):
            p.append(Piece(SEG_STEPS, "hold", s * A * frac, STEP_HOLD_S))
            p.append(Piece(SEG_STEPS, "hold", 0.0, STEP_HOLD_S))
    for a in (A, -A, A, -A, 0.0):
        p.append(Piece(SEG_ALT, "hold", a, ALT_HOLD_S))
    p.append(Piece(SEG_CHIRP_S, "chirp", 0.25 * A, CHIRP_T_S))
    p.append(Piece(SEG_HOLD0, "hold", 0.0, 1.0))
    p.append(Piece(SEG_CHIRP_L, "chirp", 0.5 * A, CHIRP_T_S))
    p.append(Piece(SEG_HOLD1, "hold", 0.0, HOLD_END_S))
    return p


def chirp_value(a: float, t: np.ndarray) -> np.ndarray:
    T = CHIRP_T_S
    t = np.clip(t, 0.0, T)
    k = math.log(CHIRP_F1_HZ / CHIRP_F0_HZ)
    phase = 2 * np.pi * CHIRP_F0_HZ * T / k * (np.exp(t * k / T) - 1.0)
    env = np.ones_like(t)
    env = np.where(t < CHIRP_FADE_S, t / CHIRP_FADE_S, env)
    env = np.where(t > T - CHIRP_FADE_S, (T - t) / CHIRP_FADE_S, env)
    return a * env * np.sin(phase)


def command_at(pieces: list[Piece], t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Kommando (relativ zur Mitte) und Segmentkennung zu den Zeiten ``t``."""
    cmd = np.zeros_like(t)
    seg = np.zeros(len(t), dtype=int)
    t0 = 0.0
    for p in pieces:
        m = (t >= t0) & (t < t0 + p.dur_s)
        if p.kind == "hold":
            cmd[m] = p.a
        else:
            cmd[m] = chirp_value(p.a, t[m] - t0)
        seg[m] = p.seg
        t0 += p.dur_s
    return cmd, seg


def chirp_frequency(t_in_chirp: np.ndarray) -> np.ndarray:
    k = math.log(CHIRP_F1_HZ / CHIRP_F0_HZ)
    return CHIRP_F0_HZ * np.exp(np.clip(t_in_chirp, 0, CHIRP_T_S) * k / CHIRP_T_S)


# ---------------------------------------------------------------------------
# Daten
# ---------------------------------------------------------------------------

@dataclass
class IdentRun:
    meta: dict
    t: np.ndarray
    seg: np.ndarray
    servo_deg: np.ndarray
    cmd: np.ndarray            # Servo-Grad relativ zur Mitte
    gyro: np.ndarray           # (n, 3) Grad/s
    acc: np.ndarray            # (n, 3) g
    axis: str = "?"
    source: str = ""

    @property
    def dt(self) -> float:
        return float(np.median(np.diff(self.t)))

    @property
    def has_imu(self) -> bool:
        return bool(np.any(self.gyro != 0) or np.any(self.acc != 0))

    def resampled(self, hz: float | None = None) -> "IdentRun":
        """Auf ein gleichmäßiges Zeitraster bringen (die Schleife im Sketch hat Jitter)."""
        hz = hz or float(self.meta.get("sample_hz", round(1 / self.dt)))
        tn = np.arange(self.t[0], self.t[-1], 1.0 / hz)
        idx = np.searchsorted(self.t, tn, side="right") - 1
        return IdentRun(
            meta=self.meta, t=tn, seg=self.seg[idx], servo_deg=self.servo_deg[idx], cmd=self.cmd[idx],
            gyro=np.column_stack([np.interp(tn, self.t, self.gyro[:, k]) for k in range(3)]),
            acc=np.column_stack([np.interp(tn, self.t, self.acc[:, k]) for k in range(3)]),
            axis=self.axis, source=self.source)


def _parse_meta_value(v: str):
    parts = v.split()
    try:
        nums = [float(x) for x in parts]
        return nums[0] if len(nums) == 1 else nums
    except ValueError:
        return v


def load_ident_csv(path: str | Path) -> list[IdentRun]:
    """Alle Läufe einer Datei (bei ``B`` stehen zwei hintereinander)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    runs: list[IdentRun] = []
    meta: dict = {}
    rows: list[list[str]] = []
    axis = "?"

    def flush():
        nonlocal rows, meta
        if rows:
            runs.append(_rows_to_run(meta, rows, axis, str(path)))
        rows, meta = [], {}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# kartonaut servo_ident"):
            flush()
            meta["format"] = line[2:]
            continue
        if line.startswith("#"):
            body = line[1:].strip()
            if ":" in body and not body.startswith("END"):
                k, v = body.split(":", 1)
                k = k.strip()
                if k == "note":
                    meta[k] = v.strip()
                elif k == "chirp" or k == "stair":
                    meta[k] = dict(kv.split("=") for kv in v.split() if "=" in kv)
                else:
                    meta[k] = _parse_meta_value(v.strip())
            continue
        if line.startswith("t_us"):
            continue
        f = line.split(",")
        if len(f) != 12:
            continue          # abgeschnittene Zeile am Ende der Aufnahme
        try:
            float(f[0]); float(f[3])
        except ValueError:
            continue
        axis = f[2]
        rows.append(f)
    flush()
    if not runs:
        raise ValueError(f"{path}: keine Messzeilen gefunden")
    return runs


def _rows_to_run(meta: dict, rows: list[list[str]], axis: str, source: str) -> IdentRun:
    a = np.array([[float(x) for x in (r[0], r[1], r[3], r[4], r[6], r[7], r[8], r[9], r[10], r[11])] for r in rows])
    t = a[:, 0] * 1e-6
    keep = np.concatenate([[True], np.diff(t) > 0])
    a = a[keep]
    return IdentRun(meta=meta, t=a[:, 0] * 1e-6, seg=a[:, 1].astype(int), servo_deg=a[:, 2], cmd=a[:, 3],
                    gyro=a[:, 4:7], acc=a[:, 7:10], axis=axis, source=source)


# ---------------------------------------------------------------------------
# Kardanwinkel aus der IMU
# ---------------------------------------------------------------------------

def pick_gyro_axis(run: IdentRun) -> tuple[int, float]:
    """Welche Gyro-Achse dreht mit dem Servo? Korrelation von Drehrate und Kommandoänderung
    in den Sprungsegmenten; das Vorzeichen macht positives Kommando zu positiver Rate."""
    m = np.isin(run.seg, (SEG_STEPS, SEG_ALT, SEG_STAIR))
    if m.sum() < 10:
        m = np.ones(len(run.t), bool)
    du = np.gradient(run.cmd[m], run.t[m])
    # Servo folgt verzögert: Kreuzkorrelation bis 100 ms Verschiebung, Maximum zählt
    best = (0.0, 0, 1.0)
    n_lag = int(0.1 / run.dt)
    for k in range(3):
        g = run.gyro[m, k] - np.median(run.gyro[m, k])
        if np.std(g) < 1e-9:
            continue
        for lag in range(0, n_lag + 1, max(1, n_lag // 25)):
            c = np.corrcoef(du[: len(du) - lag] if lag else du, g[lag:])[0, 1]
            if abs(c) > abs(best[0]):
                best = (c, k, 1.0 if c > 0 else -1.0)
    return best[1], best[2]


def plateaus(run: IdentRun, min_len_s: float = 0.4, tail_s: float = 0.25) -> list[tuple[int, int, float, int]]:
    """Fenster (i0, i1, cmd, seg) am Ende jeder Haltephase mit konstantem Kommando."""
    edges = np.flatnonzero(np.diff(run.cmd) != 0) + 1
    starts = np.concatenate([[0], edges])
    ends = np.concatenate([edges, [len(run.cmd)]])
    out = []
    for s, e in zip(starts, ends):
        if run.t[e - 1] - run.t[s] < min_len_s:
            continue
        i0 = np.searchsorted(run.t, run.t[e - 1] - tail_s)
        out.append((int(max(i0, s)), int(e), float(run.cmd[s]), int(run.seg[s])))
    return out


def gravity_angle(acc: np.ndarray, a0: np.ndarray, axis_unit: np.ndarray) -> np.ndarray:
    """Vorzeichenbehafteter Winkel zwischen Schwerkraftvektor und Referenz um die Achse (Grad)."""
    a0 = a0 / np.linalg.norm(a0)
    an = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-9)
    cross = np.cross(np.broadcast_to(a0, an.shape), an)
    return np.degrees(np.arctan2(cross @ axis_unit, an @ a0))


@dataclass
class AngleResult:
    angle: np.ndarray          # Kardanwinkel in Grad (positiv in Kommandorichtung)
    rate: np.ndarray           # Drehrate um die Kardanachse in Grad/s, nullpunktkorrigiert
    gyro_axis: int
    gyro_sign: float
    bias_dps: float
    drift_dps: float
    anchor: str                # "accel" oder "holds"
    acc_angle: np.ndarray | None = None
    anchors: list = field(default_factory=list)


def gimbal_angle(run: IdentRun, gyro_axis: int | None = None, gyro_sign: float | None = None) -> AngleResult:
    if gyro_axis is None or gyro_sign is None:
        k, s = pick_gyro_axis(run)
        gyro_axis = k if gyro_axis is None else gyro_axis
        gyro_sign = s if gyro_sign is None else gyro_sign
    rate_raw = gyro_sign * run.gyro[:, gyro_axis]

    # Nullpunkt aus den Haltephasen an der Mitte (Anfang, Ende)
    hold = np.isin(run.seg, (SEG_HOLD0, SEG_HOLD1))
    bias = float(np.mean(rate_raw[hold])) if hold.sum() > 10 else float(np.mean(rate_raw[: int(1 / run.dt)]))
    rate = rate_raw - bias
    theta_g = np.concatenate([[0.0], np.cumsum(0.5 * (rate[1:] + rate[:-1]) * np.diff(run.t))])

    pl = plateaus(run)
    acc_angle = None
    anchors = []
    use_acc = run.has_imu and np.all(np.abs(np.linalg.norm(run.acc, axis=1) - 1.0) < 0.3)
    h0 = run.seg == SEG_HOLD0
    a0 = run.acc[h0].mean(axis=0) if h0.sum() > 10 else run.acc[: int(1 / run.dt)].mean(axis=0)
    u = np.zeros(3); u[gyro_axis] = gyro_sign
    # Die Schwerkraft sieht die Drehung nur, wenn sie quer zur Kardanachse steht (Rakete senkrecht).
    observable = np.linalg.norm(np.cross(a0 / max(np.linalg.norm(a0), 1e-9), u)) > 0.5
    if use_acc and observable and pl:
        acc_angle = gravity_angle(run.acc, a0, u)
        # Vorzeichen des Accel-Winkels am Gyro-Winkel ausrichten
        ref = np.array([acc_angle[i0:i1].mean() for i0, i1, _, _ in pl])
        gy = np.array([theta_g[i0:i1].mean() for i0, i1, _, _ in pl])
        if np.dot(ref - ref.mean(), gy - gy.mean()) < 0:
            acc_angle = -acc_angle
            ref = -ref
        tk = np.array([run.t[i0:i1].mean() for i0, i1, _, _ in pl])
        anchors = list(zip(tk, ref, gy))
        anchor = "accel"
    else:
        tk, ref, gy = [], [], []
        for i0, i1, cmd, seg in pl:
            if seg in (SEG_HOLD0, SEG_HOLD1):
                tk.append(run.t[i0:i1].mean()); ref.append(0.0); gy.append(theta_g[i0:i1].mean())
        tk, ref, gy = np.array(tk), np.array(ref), np.array(gy)
        anchors = list(zip(tk, ref, gy))
        anchor = "holds"

    # Drift (Rest-Nullpunkt) und Offset: theta_g - ref = c0 + c1 t
    if len(tk) >= 2:
        c1, c0 = np.polyfit(tk, gy - ref, 1)
    elif len(tk) == 1:
        c1, c0 = 0.0, float(gy[0] - ref[0])
    else:
        c1, c0 = 0.0, 0.0
    angle = theta_g - c0 - c1 * run.t
    return AngleResult(angle=angle, rate=rate - c1, gyro_axis=gyro_axis, gyro_sign=gyro_sign, bias_dps=bias,
                       drift_dps=float(c1), anchor=anchor, acc_angle=acc_angle, anchors=anchors)


# ---------------------------------------------------------------------------
# Statische Kennlinie
# ---------------------------------------------------------------------------

def static_characteristic(run: IdentRun, angle: np.ndarray) -> dict:
    pl = [p for p in plateaus(run) if p[3] == SEG_STAIR]
    if len(pl) < 4:
        return {"ok": False}
    cmd = np.array([p[2] for p in pl])
    y = np.array([angle[p[0]:p[1]].mean() for p in pl])
    direction = np.sign(np.diff(np.concatenate([[0.0], cmd])))     # +1 aufwärts, -1 abwärts
    K, off = np.polyfit(cmd, y, 1)
    resid = y - (K * cmd + off)
    # Hysterese: gleiche Stufe, einmal von unten und einmal von oben erreicht
    hyst = []
    for level in np.unique(np.round(cmd, 6)):
        up = y[(np.round(cmd, 6) == level) & (direction > 0)]
        dn = y[(np.round(cmd, 6) == level) & (direction < 0)]
        if len(up) and len(dn):
            hyst.append(float(up.mean() - dn.mean()))
    return {
        "ok": True, "cmd": cmd.tolist(), "angle": y.tolist(), "direction": direction.tolist(),
        "K_deg_per_servo_deg": float(K), "servo_deg_per_tvc_deg": float(1 / K) if K else float("inf"),
        "offset_deg": float(off), "rms_linearity_deg": float(np.sqrt(np.mean(resid ** 2))),
        "hysteresis_mean_deg": float(np.mean(np.abs(hyst))) if hyst else float("nan"),
        "hysteresis_max_deg": float(np.max(np.abs(hyst))) if hyst else float("nan"),
        "K_pos": float(np.polyfit(cmd[cmd >= 0], y[cmd >= 0], 1)[0]) if (cmd >= 0).sum() > 2 else float("nan"),
        "K_neg": float(np.polyfit(cmd[cmd <= 0], y[cmd <= 0], 1)[0]) if (cmd <= 0).sum() > 2 else float("nan"),
    }


# ---------------------------------------------------------------------------
# Sprungantworten
# ---------------------------------------------------------------------------

def step_metrics(run: IdentRun, angle: np.ndarray, rate: np.ndarray, segs=(SEG_STEPS, SEG_ALT),
                 pre_s: float = 0.1, final_s: float = 0.2) -> list[dict]:
    edges = np.flatnonzero(np.diff(run.cmd) != 0) + 1
    out = []
    dt = run.dt
    for j, i in enumerate(edges):
        if run.seg[i] not in segs:
            continue
        i_end = edges[j + 1] if j + 1 < len(edges) else len(run.cmd)
        if (i_end - i) * dt < 0.4:
            continue
        du = float(run.cmd[i] - run.cmd[i - 1])
        y0 = float(angle[max(0, i - int(pre_s / dt)):i].mean())
        y1 = float(angle[i_end - int(final_s / dt):i_end].mean())
        dy = y1 - y0
        if abs(dy) < 1e-6:
            continue
        seg_y = (angle[i:i_end] - y0) / dy            # normiert 0..1
        tt = run.t[i:i_end] - run.t[i]
        noise = float(np.std(angle[max(0, i - int(pre_s / dt)):i] - y0))
        thr = max(0.05, 3 * noise / abs(dy))
        k_dead = np.argmax(seg_y > thr) if np.any(seg_y > thr) else len(seg_y) - 1
        k10 = np.argmax(seg_y > 0.1) if np.any(seg_y > 0.1) else len(seg_y) - 1
        k90 = np.argmax(seg_y > 0.9) if np.any(seg_y > 0.9) else len(seg_y) - 1
        r = rate[i:i_end] * np.sign(dy)
        band = np.abs(seg_y - 1.0) > 0.05
        k_settle = (np.flatnonzero(band)[-1] + 1) if np.any(band) else 0
        out.append({
            "t0_s": float(run.t[i]), "seg": int(run.seg[i]), "du_servo_deg": du, "dy_deg": dy,
            "gain": dy / du, "dead_time_s": float(tt[k_dead]), "t10_s": float(tt[k10]), "t90_s": float(tt[k90]),
            "rise_10_90_s": float(tt[k90] - tt[k10]), "overshoot_pct": float(max(0.0, seg_y.max() - 1.0) * 100),
            "peak_rate_dps": float(r.max()), "settle_5pct_s": float(tt[min(k_settle, len(tt) - 1)]),
        })
    return out


# ---------------------------------------------------------------------------
# PT2 mit Totzeit
# ---------------------------------------------------------------------------

def simulate_pt2_delay(t: np.ndarray, u: np.ndarray, K: float, wn: float, zeta: float, tau: float,
                       y0: float = 0.0) -> np.ndarray:
    """G(s) = K wn^2 / (s^2 + 2 zeta wn s + wn^2) e^(-s tau), ZOH-diskretisiert, gleichmäßiges t.
    Die Totzeit wird durch Interpolation des Eingangs gebrochen, damit sie fitbar ist."""
    h = float(t[1] - t[0])
    u_del = np.interp(t - tau, t, u, left=u[0])
    A = np.array([[0.0, 1.0], [-wn * wn, -2 * zeta * wn]])
    B = np.array([[0.0], [K * wn * wn]])
    C = np.array([[1.0, 0.0]])
    Ad, Bd, Cd, Dd, _ = signal.cont2discrete((A, B, C, np.zeros((1, 1))), h, method="zoh")
    # Zustandsraum als lfilter: Übertragungsfunktion z-Bereich
    num, den = signal.ss2tf(Ad, Bd, Cd, Dd)
    zi = signal.lfiltic(num[0], den, [y0, y0], [u[0], u[0]])
    y, _ = signal.lfilter(num[0], den, u_del, zi=zi)
    return y


def fit_pt2_delay(t: np.ndarray, u: np.ndarray, y: np.ndarray, K0: float | None = None,
                  tau_starts=(0.01, 0.03, 0.06)) -> dict:
    """Least-Squares-Fit von (K, wn, zeta, tau) mit mehreren Startwerten für die Totzeit."""
    K0 = K0 if (K0 is not None and np.isfinite(K0)) else (np.polyfit(u, y, 1)[0] if np.std(u) > 0 else 0.2)
    K0 = float(np.clip(K0, 0.01, 4.0))
    best = None
    for tau0 in tau_starts:
        x0 = (K0, 30.0, 0.7, tau0)
        res = least_squares(lambda p: simulate_pt2_delay(t, u, *p, y0=y[0]) - y, x0,
                            bounds=([0.005, 2.0, 0.05, 0.0], [5.0, 400.0, 5.0, 0.3]),
                            x_scale=(0.1, 10.0, 0.5, 0.01), diff_step=1e-4)
        if best is None or res.cost < best.cost:
            best = res
    K, wn, zeta, tau = best.x
    y_fit = simulate_pt2_delay(t, u, K, wn, zeta, tau, y0=y[0])
    return {"K": float(K), "wn": float(wn), "zeta": float(zeta), "tau": float(tau),
            "fn_hz": float(wn / 2 / np.pi), "rms_deg": float(np.sqrt(np.mean((y_fit - y) ** 2))),
            "n": int(len(t)), "y_fit": y_fit}


def pt2_bode(f_hz: np.ndarray, K: float, wn: float, zeta: float, tau: float) -> np.ndarray:
    w = 2 * np.pi * f_hz
    return K * wn ** 2 / (-(w ** 2) + 2j * zeta * wn * w + wn ** 2) * np.exp(-1j * w * tau)


def segment_window(run: IdentRun, segs) -> slice:
    idx = np.flatnonzero(np.isin(run.seg, segs))
    return slice(int(idx[0]), int(idx[-1]) + 1)


# ---------------------------------------------------------------------------
# Frequenzgang aus dem Chirp
# ---------------------------------------------------------------------------

def frequency_response(run: IdentRun, angle: np.ndarray, seg: int, nperseg_s: float = 4.0) -> dict:
    w = segment_window(run, (seg,))
    u = run.cmd[w] - run.cmd[w].mean()
    y = angle[w] - angle[w].mean()
    fs = 1.0 / run.dt
    nper = int(nperseg_s * fs)
    f, Puu = signal.welch(u, fs, nperseg=nper)
    _, Puy = signal.csd(u, y, fs, nperseg=nper)
    _, coh = signal.coherence(u, y, fs, nperseg=nper)
    H = Puy / np.maximum(Puu, 1e-18)
    m = (f >= CHIRP_F0_HZ) & (f <= CHIRP_F1_HZ) & (coh > 0.6)
    mag_db = 20 * np.log10(np.abs(H[m]) + 1e-12)
    ph = np.degrees(np.unwrap(np.angle(H[m])))
    out = {"f_hz": f[m], "H": H[m], "mag_db": mag_db, "phase_deg": ph, "coherence": coh[m],
           "amplitude_servo_deg": float(np.max(np.abs(run.cmd[w])))}
    if m.sum() > 3:
        k_dc = np.abs(H[m][:3]).mean()
        out["K_lowfreq"] = float(k_dc)
        rel_db = mag_db - 20 * np.log10(k_dc)
        below = np.flatnonzero(rel_db < -3.0)
        out["f_3db_hz"] = float(f[m][below[0]]) if len(below) else float("nan")
        p90 = np.flatnonzero(ph < -90.0)
        out["f_phase90_hz"] = float(f[m][p90[0]]) if len(p90) else float("nan")
        p45 = np.flatnonzero(ph < -45.0)
        out["f_phase45_hz"] = float(f[m][p45[0]]) if len(p45) else float("nan")
    return out


# ---------------------------------------------------------------------------
# Gesamtauswertung
# ---------------------------------------------------------------------------

def analyze(run: IdentRun, gyro_axis: int | None = None, gyro_sign: float | None = None) -> dict:
    run = run.resampled()
    ang = gimbal_angle(run, gyro_axis, gyro_sign)
    stat = static_characteristic(run, ang.angle)
    steps = step_metrics(run, ang.angle, ang.rate)

    w = segment_window(run, (SEG_STEPS, SEG_ALT))
    fit_steps = fit_pt2_delay(run.t[w] - run.t[w][0], run.cmd[w], ang.angle[w],
                              K0=stat.get("K_deg_per_servo_deg"))
    y_full = simulate_pt2_delay(run.t - run.t[0], run.cmd, fit_steps["K"], fit_steps["wn"], fit_steps["zeta"],
                                fit_steps["tau"], y0=ang.angle[0])
    rms_full = float(np.sqrt(np.mean((y_full - ang.angle) ** 2)))

    fr = {}
    for seg in (SEG_CHIRP_S, SEG_CHIRP_L):
        if np.any(run.seg == seg):
            fr[SEG_NAMES[seg]] = frequency_response(run, ang.angle, seg)

    ref = ServoParams()
    big = [s for s in steps if s["seg"] == SEG_ALT]
    summary = {
        "source": run.source, "axis": run.axis, "meta": run.meta,
        "gyro_axis": "xyz"[ang.gyro_axis], "gyro_sign": ang.gyro_sign, "gyro_bias_dps": ang.bias_dps,
        "gyro_drift_dps": ang.drift_dps, "anchor": ang.anchor, "has_imu": run.has_imu,
        "static": {k: v for k, v in stat.items() if k not in ("cmd", "angle", "direction")},
        "steps": steps,
        "step_summary": {
            "dead_time_s_median": float(np.median([s["dead_time_s"] for s in steps])) if steps else float("nan"),
            "rise_10_90_s_median": float(np.median([s["rise_10_90_s"] for s in steps])) if steps else float("nan"),
            "overshoot_pct_max": float(max(s["overshoot_pct"] for s in steps)) if steps else float("nan"),
            "peak_rate_dps_max": float(max(s["peak_rate_dps"] for s in steps)) if steps else float("nan"),
            "peak_rate_dps_alternate": float(np.median([s["peak_rate_dps"] for s in big])) if big else float("nan"),
        },
        "pt2": {k: v for k, v in fit_steps.items() if k != "y_fit"} | {"rms_full_run_deg": rms_full},
        "frequency": {name: {k: v for k, v in d.items() if k not in ("f_hz", "H", "mag_db", "phase_deg", "coherence")}
                      for name, d in fr.items()},
        "reference_sg90_2025": {"K": ref.K, "wn": ref.wn, "zeta": ref.zeta, "tau": ref.tau,
                                "servo_deg_per_tvc_deg": ref.servo_deg_per_tvc_deg},
    }
    return {"summary": summary, "run": run, "angle": ang, "static": stat, "fit": fit_steps,
            "y_full": y_full, "frequency": fr}


def servo_params_snippet(summary: dict) -> str:
    p, s = summary["pt2"], summary["static"]
    K = s.get("K_deg_per_servo_deg", p["K"])
    return (
        "ServoParams(\n"
        f"    K={p['K']:.4f},          # Kardan-Grad je Servo-Grad (statisch {K:.4f}, 1/{1 / K:.2f})\n"
        f"    wn={p['wn']:.1f},           # rad/s ({p['fn_hz']:.1f} Hz)\n"
        f"    zeta={p['zeta']:.3f},\n"
        f"    tau={p['tau']:.3f},          # s Totzeit\n"
        f"    servo_deg_per_tvc_deg={1 / K:.2f},\n"
        ")"
    )


def format_report(summary: dict) -> str:
    s, p, st, fq = summary["static"], summary["pt2"], summary["step_summary"], summary["frequency"]
    ref = summary["reference_sg90_2025"]
    lines = [
        f"Lauf {summary['source']} Achse {summary['axis']}: Gyro-Achse {summary['gyro_axis']} "
        f"(Vorzeichen {summary['gyro_sign']:+.0f}), Nullpunkt {summary['gyro_bias_dps']:.3f} Grad/s, "
        f"Rest-Drift {summary['gyro_drift_dps']:.4f} Grad/s, Verankerung: {summary['anchor']}",
        f"Notiz: {summary['meta'].get('note', '')}  Servospannung: {summary['meta'].get('servo_volt', '?')} V  "
        f"Pulsrate: {summary['meta'].get('frame_hz', '?')} Hz",
        "",
        "Statische Kennlinie (Treppe):",
    ]
    if s.get("ok"):
        lines += [
            f"  K = {s['K_deg_per_servo_deg']:.4f} Kardan-Grad je Servo-Grad  ->  {s['servo_deg_per_tvc_deg']:.2f} Servo-Grad je TVC-Grad"
            f"  (2025: {ref['servo_deg_per_tvc_deg']:.1f}; Config.h: 23)",
            f"  Nullpunktfehler {s['offset_deg']:+.2f} Grad, Linearität RMS {s['rms_linearity_deg']:.3f} Grad, "
            f"K+ {s['K_pos']:.4f} / K- {s['K_neg']:.4f}",
            f"  Hysterese Mittel {s['hysteresis_mean_deg']:.3f} Grad, max {s['hysteresis_max_deg']:.3f} Grad",
        ]
    else:
        lines.append("  nicht auswertbar (zu wenige Plateaus)")
    lines += [
        "",
        "Sprungantworten:",
        f"  Totzeit Median {st['dead_time_s_median'] * 1000:.0f} ms, Anstieg 10-90 % Median {st['rise_10_90_s_median'] * 1000:.0f} ms, "
        f"Überschwingen max {st['overshoot_pct_max']:.0f} %",
        f"  Maximalrate am Kardan {st['peak_rate_dps_max']:.0f} Grad/s (Wechselsprünge {st['peak_rate_dps_alternate']:.0f} Grad/s; 2025: etwa 70)",
        "",
        "PT2 mit Totzeit (Fit an Sprünge und Wechselsprünge):",
        f"  K = {p['K']:.4f}, wn = {p['wn']:.1f} rad/s ({p['fn_hz']:.1f} Hz), zeta = {p['zeta']:.3f}, tau = {p['tau'] * 1000:.0f} ms, "
        f"RMS {p['rms_deg']:.3f} Grad (ganzer Lauf {p['rms_full_run_deg']:.3f} Grad)",
        f"  2025 SG90: K = {ref['K']:.4f}, wn = {ref['wn']:.1f} rad/s, zeta = {ref['zeta']:.2f}, tau = {ref['tau'] * 1000:.0f} ms",
        "",
        "Frequenzgang (Chirps):",
    ]
    for name, d in fq.items():
        if "f_3db_hz" in d:
            lines.append(f"  {name} (Amplitude {d['amplitude_servo_deg']:.1f} Servo-Grad): -3 dB bei {d['f_3db_hz']:.1f} Hz, "
                         f"-45 Grad bei {d['f_phase45_hz']:.1f} Hz, -90 Grad bei {d['f_phase90_hz']:.1f} Hz, "
                         f"K(niedrig) {d['K_lowfreq']:.4f}")
        else:
            lines.append(f"  {name}: Kohärenz zu niedrig")
    lines += ["", "Vorschlag für tvcsim/params.py:", servo_params_snippet(summary)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Künstliche Messung (Tests, Probelauf der Auswertung)
# ---------------------------------------------------------------------------

def synthesize_run(K: float = 0.17, wn: float = 40.0, zeta: float = 0.6, tau: float = 0.025, A: float = 22.0,
                   center: float = 92.5, hz: float = 500.0, gyro_axis: int = 1, gyro_sign: float = -1.0,
                   bias_dps: float = 0.35, noise_dps: float = 0.05, acc_noise_g: float = 0.003,
                   rate_limit_dps: float | None = None, hysteresis_deg: float = 0.0, seed: int = 0,
                   axis: str = "Y") -> IdentRun:
    """Kardan als PT2 mit Totzeit (optional Ratenbegrenzung und Hysterese), IMU auf dem Motorrohr."""
    rng = np.random.default_rng(seed)
    pieces = build_sequence(A)
    T = sum(p.dur_s for p in pieces)
    t = np.arange(0.0, T, 1.0 / hz)
    cmd, seg = command_at(pieces, t)
    u = cmd.copy()
    if hysteresis_deg > 0:   # Spiel: der Kardan folgt dem Servo erst nach dem halben Spiel
        out = np.zeros_like(u); pos = 0.0; hb = hysteresis_deg / 2 / K
        for i, ui in enumerate(u):
            if ui > pos + hb: pos = ui - hb
            elif ui < pos - hb: pos = ui + hb
            out[i] = pos
        u = out
    if rate_limit_dps is None:
        theta = simulate_pt2_delay(t, u, K, wn, zeta, tau)
    else:
        h = 1.0 / hz
        u_del = np.interp(t - tau, t, u, left=u[0])
        x = np.zeros(2); theta = np.zeros_like(t)
        for i in range(1, len(t)):
            acc = wn * wn * (K * u_del[i] - x[0]) - 2 * zeta * wn * x[1]
            x[1] = np.clip(x[1] + acc * h, -rate_limit_dps, rate_limit_dps)
            x[0] += x[1] * h
            theta[i] = x[0]
    rate = np.gradient(theta, t)
    gyro = rng.normal(0, noise_dps, (len(t), 3)) + np.array([0.1, 0.2, -0.15])
    gyro[:, gyro_axis] = gyro_sign * rate + bias_dps + rng.normal(0, noise_dps, len(t))
    # Schwerkraft: Rakete steht, IMU beliebig verdreht; der Kardan dreht sie um die Gyro-Achse
    uax = np.zeros(3); uax[gyro_axis] = gyro_sign
    a0 = np.array([0.15, 0.25, 0.95]) + 0.0
    a0 -= (a0 @ uax) * uax            # Rakete steht: g quer zur Kardanachse
    a0 += 0.1 * uax                   # kleine Schieflage des Aufbaus
    a0 /= np.linalg.norm(a0)
    th = np.radians(theta)
    acc = (np.outer(np.cos(th), a0) + np.outer(np.sin(th), np.cross(uax, a0) * -1.0)
           + np.outer(1 - np.cos(th), uax * (uax @ a0)))
    acc += rng.normal(0, acc_noise_g, acc.shape)
    meta = {"format": "kartonaut servo_ident v1 (synthetisch)", "axis": axis, "center_deg": center,
            "amplitude_deg": A, "sample_hz": hz, "frame_hz": 50, "servo_volt": 5.0,
            "note": f"synthetisch K={K} wn={wn} zeta={zeta} tau={tau}"}
    return IdentRun(meta=meta, t=t, seg=seg, servo_deg=center + cmd, cmd=cmd, gyro=gyro, acc=acc,
                    axis=axis, source="synthetisch")


def write_ident_csv(run: IdentRun, path: str | Path) -> Path:
    """Einen Lauf im Dateiformat des Sketches schreiben (für Tests und Beispiele)."""
    buf = io.StringIO()
    buf.write("# kartonaut servo_ident v1\n")
    for k in ("axis", "center_deg", "amplitude_deg", "sample_hz", "frame_hz", "servo_volt", "note"):
        if k in run.meta:
            buf.write(f"# {k}: {run.meta[k]}\n")
    buf.write("t_us,seg,axis,servo_deg,cmd_rel_deg,pulse_us,gx_dps,gy_dps,gz_dps,ax_g,ay_g,az_g\n")
    w = csv.writer(buf, lineterminator="\n")
    for i in range(len(run.t)):
        w.writerow([int(round(run.t[i] * 1e6)), int(run.seg[i]), run.axis, f"{run.servo_deg[i]:.3f}",
                    f"{run.cmd[i]:.3f}", f"{760 + (2300 - 760) * run.servo_deg[i] / 180:.1f}",
                    *(f"{v:.3f}" for v in run.gyro[i]), *(f"{v:.4f}" for v in run.acc[i])])
    buf.write(f"# END rows={len(run.t)} reason=done\n")
    Path(path).write_text(buf.getvalue(), encoding="utf-8")
    return Path(path)
