"""Software-in-the-Loop: der echte C++-Flugkern der Firmware als Regler in der Simulation.

``firmware/sil/kartonaut_sil.cpp`` verpackt ``firmware/lib/flightcore`` (Attitude, KalmanZ,
FlightState, PyroLogic, TvcController) in eine C-Schnittstelle. ``build_library()`` übersetzt sie mit
dem vorhandenen C++-Compiler (g++, clang++) in eine gemeinsam ladbare Bibliothek unter
``simulation/out/sil/``, ``SilController`` hängt sie über ctypes in ``sim.simulate`` ein. Damit rechnet
die Simulation mit genau dem Code, der auf dem Teensy läuft: Lage aus dem Gyro, Kalman aus
Beschleunigung und Barometer, Zustandsautomat, Pyro-Zeitpunkt, Regler, Servo-Rundung.

Was der Kern sieht, entsteht hier wie am Gerät:

* Drehrate: ``w_est`` aus dem Avionics-Block (verrauscht wie bisher), in Firmware-Achsen.
* Spezifische Kraft im Körpersystem: ``Tb / m`` im Flug, ``g`` entlang der Rollachse auf der Rampe,
  plus eigenes Rauschen (``accel_sigma``).
* Barometer: wahre Höhe plus Rauschen (``baro_sigma``), mit 50 Hz (jeder zweite Takt).

Alle Parameter liest ``SilParams.from_config_h()`` aus ``firmware/src/Config.h``; was dort steht, gilt
auch hier. Nur ``control_enabled`` ist in der Simulation standardmäßig an (im Config.h bis zum
Prüfstand aus).

Achsen: Simulink x (längs) = Firmware z, Simulink y = Firmware x (Yaw), Simulink z = Firmware y
(Pitch). Das Vorzeichen Firmware-TVC -> Simulink-Kommando ist dasselbe wie beim Python-Port
(``FirmwareParams.axis_sign_*``, Vorgabe −1/−1).
"""
from __future__ import annotations

import ctypes
import math
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field, fields
from pathlib import Path

import numpy as np

from .params import OUT_DIR, REPO_DIR

FIRMWARE_DIR = REPO_DIR / "firmware"
CORE_DIR = FIRMWARE_DIR / "lib" / "flightcore"
SIL_SOURCE = FIRMWARE_DIR / "sil" / "kartonaut_sil.cpp"
CONFIG_H = FIRMWARE_DIR / "src" / "Config.h"
LIB_DIR = OUT_DIR / "sil"

PHASES = ["SAFE", "PAD_READY", "BOOST", "COAST", "APOGEE", "DESCENT", "LANDED", "ABORT"]


class SilBuildError(RuntimeError):
    pass


def _lib_name() -> str:
    system = platform.system()
    if system == "Windows":
        return "kartonaut_sil.dll"
    if system == "Darwin":
        return "libkartonaut_sil.dylib"
    return "libkartonaut_sil.so"


def find_compiler() -> str | None:
    for cand in (os.environ.get("CXX"), "g++", "clang++", "c++"):
        if cand and shutil.which(cand):
            return cand
    return None


def build_library(force: bool = False) -> Path:
    """Bibliothek bauen, wenn eine Quelle neuer ist als sie. Liefert den Pfad."""
    sources = sorted(CORE_DIR.glob("*.cpp")) + [SIL_SOURCE]
    headers = sorted(CORE_DIR.glob("*.h"))
    lib = LIB_DIR / _lib_name()
    newest = max(p.stat().st_mtime for p in sources + headers)
    if lib.exists() and not force and lib.stat().st_mtime >= newest:
        return lib
    cxx = find_compiler()
    if cxx is None:
        raise SilBuildError("kein C++-Compiler gefunden (g++ oder clang++ installieren oder CXX setzen)")
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    tmp = lib.with_suffix(lib.suffix + ".tmp")
    cmd = [cxx, "-std=c++17", "-O2", "-shared", "-fPIC", f"-I{CORE_DIR}", *map(str, sources), "-o", str(tmp)]
    if platform.system() == "Windows":
        cmd.remove("-fPIC")
        cmd += ["-static-libgcc", "-static-libstdc++"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise SilBuildError(f"Übersetzen fehlgeschlagen:\n{' '.join(cmd)}\n{res.stderr}")
    os.replace(tmp, lib)
    return lib


# --------------------------------------------------------------------------- ctypes-Strukturen
_F, _U, _I = ctypes.c_float, ctypes.c_uint32, ctypes.c_int32


class SilConfig(ctypes.Structure):
    _fields_ = [
        ("g_ms2", _F),
        ("kp", _F), ("ki", _F), ("kd", _F), ("error_scale", _F), ("mass_kg", _F), ("moment_arm_m", _F),
        ("a_norm_min", _F), ("a_norm_alpha", _F), ("tvc_max_deg", _F), ("i_max_deg_s", _F),
        ("yaw_gain", _F), ("yaw_offset", _F), ("yaw_min", _F), ("yaw_max", _F),
        ("pitch_gain", _F), ("pitch_offset", _F), ("pitch_min", _F), ("pitch_max", _F),
        ("liftoff_g", _F), ("liftoff_hold_ms", _U),
        ("burnout_g", _F), ("burn_max_ms", _U), ("coast_max_ms", _U),
        ("abort_tilt_deg", _F),
        ("apogee_vz_ms", _F), ("apogee_hold_ms", _U), ("apogee_baro_drop_m", _F),
        ("min_flight_alt_m", _F),
        ("kalman_meas_std_m", _F), ("kalman_sigma_acc", _F), ("kalman_init_var", _F),
        ("pyro_pulse_ms", _U), ("pyro_backup_delay_ms", _U),
        ("chute_channel", _I), ("backup_channel", _I),
        ("control_enabled", _I), ("quantize_servo", _I),
    ]


class SilOutput(ctypes.Structure):
    _fields_ = [
        ("phase", _I), ("event", _I), ("event_reason", _I),
        ("tilt_deg", _F), ("yaw_err_deg", _F), ("pitch_err_deg", _F), ("roll_deg", _F),
        ("q", _F * 4),
        ("alt_m", _F), ("vz_ms", _F),
        ("yaw_moment_nm", _F), ("pitch_moment_nm", _F),
        ("tvc_yaw_deg", _F), ("tvc_pitch_deg", _F),
        ("servo_yaw_deg", _F), ("servo_pitch_deg", _F),
        ("yaw_saturated", _I), ("pitch_saturated", _I),
        ("pyro_fire_mask", _I), ("pyro_fired_mask", _I),
        ("accel_norm_filt", _F),
    ]


_LIB = None


def load_library() -> ctypes.CDLL:
    global _LIB
    if _LIB is not None:
        return _LIB
    lib = ctypes.CDLL(str(build_library()))
    lib.sil_create.restype = ctypes.c_void_p
    lib.sil_create.argtypes = [ctypes.POINTER(SilConfig)]
    lib.sil_destroy.argtypes = [ctypes.c_void_p]
    lib.sil_config_size.restype = ctypes.c_int32
    lib.sil_output_size.restype = ctypes.c_int32
    lib.sil_init_pad.restype = ctypes.c_int32
    lib.sil_init_pad.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float)]
    lib.sil_step.restype = None
    lib.sil_step.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_float, ctypes.POINTER(ctypes.c_float),
                             ctypes.POINTER(ctypes.c_float), ctypes.c_float, ctypes.POINTER(SilOutput)]
    if lib.sil_config_size() != ctypes.sizeof(SilConfig) or lib.sil_output_size() != ctypes.sizeof(SilOutput):
        raise SilBuildError("SilConfig/SilOutput in sil.py und kartonaut_sil.cpp passen nicht zusammen")
    _LIB = lib
    return lib


# --------------------------------------------------------------------------- Parameter aus Config.h
_CONST_RE = re.compile(r"constexpr\s+(?:float|double|int|long|bool|uint8_t|uint16_t|uint32_t)\s+(\w+)\s*=\s*([^;]+);")


def parse_config_h(path: Path = CONFIG_H) -> dict[str, float]:
    """Alle einfachen ``constexpr``-Zahlen aus Config.h (Ausdrücke und Vec3 werden übersprungen;
    in ``#ifdef``-Zweigen gilt der erste Treffer)."""
    out: dict[str, float] = {}
    for name, raw in _CONST_RE.findall(path.read_text(encoding="utf-8")):
        if name in out:
            continue
        v = raw.strip()
        if v in ("true", "false"):
            out[name] = 1.0 if v == "true" else 0.0
            continue
        v = re.sub(r"(?<=[0-9.])[fF]$", "", v)
        try:
            out[name] = float(v)
        except ValueError:
            pass
    return out


_CONFIG_MAP = {
    "g_ms2": "G_MS2",
    "kp": "PY_KP", "ki": "PY_KI", "kd": "PY_KD", "error_scale": "PY_ERROR_SCALE",
    "mass_kg": "MASS_KG", "moment_arm_m": "MOMENT_ARM_M", "a_norm_min": "A_NORM_MIN", "a_norm_alpha": "A_NORM_ALPHA",
    "tvc_max_deg": "TVC_MAX_DEG", "i_max_deg_s": "PY_I_MAX_DEG_S",
    "yaw_gain": "SERVO_YAW_GAIN", "yaw_offset": "SERVO_YAW_OFFSET",
    "yaw_min": "SERVO_YAW_MIN_DEG", "yaw_max": "SERVO_YAW_MAX_DEG",
    "pitch_gain": "SERVO_PITCH_GAIN", "pitch_offset": "SERVO_PITCH_OFFSET",
    "pitch_min": "SERVO_PITCH_MIN_DEG", "pitch_max": "SERVO_PITCH_MAX_DEG",
    "liftoff_g": "FS_LIFTOFF_G", "liftoff_hold_ms": "FS_LIFTOFF_HOLD_MS", "burnout_g": "FS_BURNOUT_G",
    "burn_max_ms": "FS_BURN_MAX_MS", "coast_max_ms": "FS_COAST_MAX_MS", "abort_tilt_deg": "FS_ABORT_TILT_DEG",
    "apogee_vz_ms": "FS_APOGEE_VZ_MS", "apogee_hold_ms": "FS_APOGEE_HOLD_MS", "apogee_baro_drop_m": "FS_APOGEE_BARO_DROP_M",
    "min_flight_alt_m": "FS_MIN_FLIGHT_ALT_M",
    "kalman_meas_std_m": "KALMAN_MEAS_STD_M", "kalman_sigma_acc": "KALMAN_SIGMA_ACC_MS2",
    "kalman_init_var": "KALMAN_INIT_PZ_VAR",
    "pyro_pulse_ms": "PYRO_PULSE_MS", "pyro_backup_delay_ms": "PYRO_BACKUP_DELAY_MS",
    "chute_channel": "PYRO_CHUTE_CHANNEL", "backup_channel": "PYRO_BACKUP_CHANNEL",
}


@dataclass
class SilParams:
    """Konstanten des Flugkerns. Vorgaben = ``firmware/src/Config.h`` (``from_config_h``)."""

    values: dict[str, float] = field(default_factory=dict)
    control_enabled: bool = True     # Config.h: PY_CONTROL_ACTIVE = false bis zum Prüfstand
    quantize_servo: bool = True      # ganze Servo-Grad wie Control.cpp
    axis_sign_yaw: float = -1.0      # wie FirmwareParams
    axis_sign_pitch: float = -1.0
    accel_sigma: float = 0.05        # m/s², Rauschen der spezifischen Kraft je Achse
    baro_sigma: float = 0.3          # m, Rauschen der Barometerhöhe (BMP390 ×8, IIR 3)
    baro_every: int = 2              # Barometer jeden n-ten Takt (100 Hz / 2 = 50 Hz)
    gyro_sigma_pad: float = 0.1      # °/s je Achse, Gyro-Rauschen in der Wartezeit auf der Rampe
    pad_seconds: float = 5.0         # Wartezeit zwischen CALIBRATE und Zündung: Kalman und Lage laufen ein
    cal_samples: int = 100           # Rampenkalibrierung mittelt so viele Werte (wie calibrate() in main.cpp)
    boot_offset_ms: int = 20000      # Zeit seit dem Einschalten beim Start der Simulation

    @classmethod
    def from_config_h(cls, path: Path = CONFIG_H, **overrides) -> "SilParams":
        cfg = parse_config_h(path)
        missing = [c for c in _CONFIG_MAP.values() if c not in cfg]
        if missing:
            raise KeyError(f"in {path} fehlen: {', '.join(missing)}")
        values = {k: cfg[c] for k, c in _CONFIG_MAP.items()}
        p = cls(values=values)
        for k, v in overrides.items():
            if k in values:
                p.values[k] = float(v)
            elif k in {f.name for f in fields(cls)}:
                setattr(p, k, v)
            else:
                raise KeyError(f"unbekannter Parameter {k!r}")
        return p

    def to_struct(self) -> SilConfig:
        c = SilConfig()
        for name, ctype in SilConfig._fields_:
            if name == "control_enabled":
                c.control_enabled = int(self.control_enabled)
            elif name == "quantize_servo":
                c.quantize_servo = int(self.quantize_servo)
            else:
                v = self.values[name]
                setattr(c, name, int(round(v)) if ctype in (_U, _I) else float(v))
        return c


def _sim_to_fw(v) -> tuple[float, float, float]:
    """Simulink (x längs, y, z) -> Firmware (x = Yaw, y = Pitch, z = Rollachse)."""
    return float(v[1]), float(v[2]), float(v[0])


class SilController:
    """Regler-Schnittstelle von ``sim.simulate`` mit dem C++-Flugkern dahinter."""

    def __init__(self, params: SilParams | None, dt: float, seed: int | None = None):
        self.p = params or SilParams.from_config_h()
        self.dt = dt
        self.lib = load_library()
        self._cfg = self.p.to_struct()
        self.h = self.lib.sil_create(ctypes.byref(self._cfg))
        if not self.h:
            raise MemoryError("sil_create")
        self.rng = np.random.default_rng(None if seed is None else seed + 7919)
        self.k = 0
        self.out = SilOutput()
        self._f = (ctypes.c_float * 3)()
        self._w = (ctypes.c_float * 3)()
        self.trace: list[dict] = []
        self.last: dict = {}

    def __del__(self):
        h = getattr(self, "h", None)
        if h:
            self.lib.sil_destroy(h)
            self.h = None

    def step(self, t: float, w_est_dps, q_est, T_est: float, f_body=None, alt_true: float | None = None, **_) -> tuple[float, float]:
        if f_body is None:
            raise ValueError("SilController braucht f_body (spezifische Kraft im Körpersystem) von sim.simulate")
        f = np.array(_sim_to_fw(f_body)) + self.rng.normal(0.0, self.p.accel_sigma, 3)
        w = _sim_to_fw(w_est_dps)
        self._f[:] = f.tolist()
        self._w[:] = w
        if self.k == 0:
            self._pad_phase(np.array(_sim_to_fw(f_body)), float(alt_true or 0.0))
            self._f[:] = f.tolist()
            self._w[:] = w
        baro = math.nan
        if alt_true is not None and self.k % self.p.baro_every == 0:
            baro = float(alt_true + self.rng.normal(0.0, self.p.baro_sigma))
        t_ms = int(round(t * 1000.0)) + self.p.boot_offset_ms
        self._step(t_ms, baro)
        self.k += 1
        return self._result(t, baro)

    def _step(self, t_ms: int, baro: float) -> None:
        self.lib.sil_step(self.h, t_ms, ctypes.c_float(self.dt), self._f, self._w, ctypes.c_float(baro), ctypes.byref(self.out))

    def _pad_phase(self, f_pad, alt0: float) -> None:
        """Rampe vor der Zündung: Kalibrierung mit gemittelter Ruhemessung, dann pad_seconds Warten
        (Kalman und Quaternion laufen ein wie am Gerät, wo zwischen CALIBRATE und Zündung Sekunden vergehen)."""
        f_cal = f_pad + self.rng.normal(0.0, self.p.accel_sigma / math.sqrt(self.p.cal_samples), 3)
        self._f[:] = f_cal.tolist()
        self.lib.sil_init_pad(self.h, self._f)
        n = int(round(self.p.pad_seconds / self.dt))
        t0 = self.p.boot_offset_ms - int(round(self.p.pad_seconds * 1000.0))
        for i in range(n):
            self._f[:] = (f_pad + self.rng.normal(0.0, self.p.accel_sigma, 3)).tolist()
            self._w[:] = self.rng.normal(0.0, self.p.gyro_sigma_pad, 3).tolist()
            baro = float(alt0 + self.rng.normal(0.0, self.p.baro_sigma)) if i % self.p.baro_every == 0 else math.nan
            self._step(t0 + int(round(i * self.dt * 1000.0)), baro)

    def _result(self, t: float, baro: float) -> tuple[float, float]:
        o = self.out
        th_y = self.p.axis_sign_yaw * o.tvc_yaw_deg
        th_z = self.p.axis_sign_pitch * o.tvc_pitch_deg
        rec = {
            "t": t, "phase": o.phase, "event": o.event, "reason": o.event_reason,
            "tilt_deg": o.tilt_deg, "yaw_err_deg": o.yaw_err_deg, "pitch_err_deg": o.pitch_err_deg,
            "alt_m": o.alt_m, "vz_ms": o.vz_ms, "baro_m": baro,
            "tvc_yaw_deg": o.tvc_yaw_deg, "tvc_pitch_deg": o.tvc_pitch_deg,
            "servo_yaw_deg": o.servo_yaw_deg, "servo_pitch_deg": o.servo_pitch_deg,
            "fire": o.pyro_fire_mask, "fired": o.pyro_fired_mask,
            "sat": int(o.yaw_saturated or o.pitch_saturated),
        }
        self.trace.append(rec)
        self.last = {"u": np.array([0.0, o.yaw_moment_nm, o.pitch_moment_nm]),
                     "rot": np.array([o.yaw_err_deg, o.pitch_err_deg, o.roll_deg]),
                     "th_y_com": th_y, "th_z_com": th_z, "phase": PHASES[o.phase]}
        return th_y, th_z


def trace_arrays(trace: list[dict]) -> dict[str, np.ndarray]:
    """Liste der Schritt-Datensätze in Spalten-Arrays umformen."""
    if not trace:
        return {}
    return {k: np.array([r[k] for r in trace]) for k in trace[0]}
