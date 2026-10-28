"""Funkprotokoll Rakete <-> Laptop (Python-Seite von firmware/src/Telemetry.h).

Rahmen: A5 5A | Typ | Länge | Nutzlast | CRC-16/CCITT (little-endian, über Typ, Länge, Nutzlast).
MAC für ARM und LAUNCH wie firmware/src/LaunchAuth.h:
    erste 8 Byte von HMAC-SHA256(Schlüssel, Typ | seq | nonce (4 Byte LE) | Raketen-ID)

Nur Standardbibliothek; pyserial braucht erst launch.py.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CONFIG_H = os.path.join(REPO, "firmware", "src", "Config.h")
SECRETS_JSON = os.path.join(HERE, "secrets.json")

SYNC = b"\xA5\x5A"
MAX_PAYLOAD = 64

# Rahmentypen
TLM, EVT, GPS, IGN, ACK = 0x01, 0x02, 0x03, 0x04, 0x10
CMD_PING, CMD_CALIBRATE, CMD_PAD_READY, CMD_ABORT, CMD_SAFE = 0x20, 0x21, 0x22, 0x23, 0x24
CMD_ARM, CMD_LAUNCH, CMD_HEARTBEAT = 0x25, 0x26, 0x27
BRIDGE_CONFIG, BRIDGE_ACK = 0x70, 0x71          # Laptop <-> Funkbrücke (tools/ground/bridge_pico), nie über Funk

TYPE_NAMES = {
    TLM: "TLM", EVT: "EVT", GPS: "GPS", IGN: "IGN", ACK: "ACK",
    CMD_PING: "PING", CMD_CALIBRATE: "CALIBRATE", CMD_PAD_READY: "PAD_READY", CMD_ABORT: "ABORT",
    CMD_SAFE: "SAFE", CMD_ARM: "ARM", CMD_LAUNCH: "LAUNCH", CMD_HEARTBEAT: "HEARTBEAT",
    BRIDGE_CONFIG: "BRIDGE_CONFIG", BRIDGE_ACK: "BRIDGE_ACK",
}

BRIDGE_RESULTS = {0: "ok", 1: "E22 antwortet nicht im Konfigurationsmodus", 2: "Schreiben fehlgeschlagen"}

STATES = ["SAFE", "PAD_READY", "BOOST", "COAST", "APOGEE", "DESCENT", "LANDED", "ABORT", "LANDING_BURN",
          "ARMED", "COUNTDOWN", "IGNITION", "MISFIRE"]
ARMED, COUNTDOWN, IGNITION, MISFIRE = 9, 10, 11, 12
PAD_READY = 1

REASONS = ["NONE", "CMD", "ACCEL", "BURNOUT_ACCEL", "BURN_TIMEOUT", "APOGEE_SENSORS", "APOGEE_TIMEOUT",
           "PYRO_DONE", "LANDED_SENSORS", "FLIGHT_TIMEOUT", "RESTORED", "NOT_READY", "LANDING_FREEFALL",
           "IGNITION", "LANDING_FALLBACK", "BURN_END", "HEARTBEAT_LOST", "PRECOND_LOST", "ARM_TIMEOUT",
           "COUNTDOWN_END", "THRUST_TIMEOUT"]

ACK_OK, ACK_REFUSED, ACK_UNKNOWN, ACK_AUTH = 0, 1, 2, 3
ACK_NAMES = {ACK_OK: "OK", ACK_REFUSED: "ABGELEHNT", ACK_UNKNOWN: "UNBEKANNT", ACK_AUTH: "MAC FALSCH"}

FLAGS = [(0x01, "ARM"), (0x02, "Durchgang1"), (0x04, "Durchgang2"), (0x08, "Log"), (0x10, "kalibriert"),
         (0x20, "Sensoren"), (0x40, "Pyro gezündet"), (0x80, "Neustart")]

PRE_ALL = 0x7F
PRECONDS = [
    (0x01, "Arming-Schalter (keine Spannung an VBAT_ARMED)"),
    (0x02, "Durchgang am Anzünder (Pyro 1)"),
    (0x04, "Akkus (1S oder 2S unter der Schwelle)"),
    (0x08, "Rakete nicht ruhig oder nicht aufrecht (2 s ruhig, Kippung im Rampenwinkel)"),
    (0x10, "Sensoren, Kalibrierung oder Logging"),
    (0x20, "Servo-Selbsttest nicht bestanden"),
    (0x40, "kein Schlüssel in der Firmware (Secrets.h)"),
]

IGN_END = ["-", "Schub", "Durchgang weg", "300 ms", "Abbruch", "Arming-Spannung weg", "nicht begonnen"]
IGN_NO_TIME = 0xFFFF


# ---------------------------------------------------------------- Rahmen
def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode(ftype: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("Nutzlast zu lang")
    body = bytes([ftype, len(payload)]) + payload
    return SYNC + body + struct.pack("<H", crc16_ccitt(body))


class Parser:
    """Byteweiser Empfänger mit Resynchronisation, wie tlm::Parser in der Firmware.

    rssi_byte=True: das E22 der Funkbrücke hängt an jedes empfangene Paket ein RSSI-Byte an
    (launch.py --config schaltet es ein). Folgt auf einen Rahmen ein Byte, das kein Sync ist, gilt es als
    RSSI (Wert -(256 - Byte) dBm).
    """

    def __init__(self, rssi_byte: bool = False):
        self.rssi_byte = rssi_byte
        self.buf = bytearray()
        self.bad = 0
        self.rssi_dbm = None
        self._after_frame = False

    def feed(self, data: bytes):
        """Bytes einspeisen; liefert die Liste fertiger Rahmen [(Typ, Nutzlast)]."""
        out = []
        for b in data:
            if self._after_frame and not self.buf:
                self._after_frame = False
                if self.rssi_byte and b != SYNC[0]:
                    self.rssi_dbm = -(256 - b)
                    continue
            self.buf.append(b)
            frame = self._try()
            if frame:
                out.append(frame)
                self._after_frame = True
        return out

    def _try(self):
        buf = self.buf
        while True:
            while buf and buf[0] != SYNC[0]:
                del buf[0]
            if len(buf) >= 2 and buf[1] != SYNC[1]:
                del buf[0]
                continue
            if len(buf) < 4:
                return None
            n = buf[3]
            if n > MAX_PAYLOAD:
                self.bad += 1
                del buf[0]
                continue
            if len(buf) < 6 + n:
                return None
            body = bytes(buf[2:4 + n])
            crc = struct.unpack_from("<H", buf, 4 + n)[0]
            if crc16_ccitt(body) != crc:
                self.bad += 1
                del buf[0]
                continue
            del buf[:6 + n]
            return body[0], body[2:]


# ---------------------------------------------------------------- Authentisierung
def compute_mac(key: bytes, ftype: int, seq: int, nonce: int, rocket_id: int) -> bytes:
    msg = bytes([ftype, seq & 0xFF]) + struct.pack("<I", nonce & 0xFFFFFFFF) + bytes([rocket_id & 0xFF])
    return hmac.new(key, msg, hashlib.sha256).digest()[:8]


def cmd(ftype: int, seq: int) -> bytes:
    return encode(ftype, bytes([seq & 0xFF]))


def auth_cmd(ftype: int, seq: int, nonce: int, key: bytes, rocket_id: int) -> bytes:
    return encode(ftype, bytes([seq & 0xFF]) + compute_mac(key, ftype, seq, nonce, rocket_id))


# ---------------------------------------------------------------- Nutzlasten
def state_name(s: int) -> str:
    return STATES[s] if 0 <= s < len(STATES) else f"?{s}"


def reason_name(r: int) -> str:
    return REASONS[r] if 0 <= r < len(REASONS) else f"?{r}"


def decode_tlm(p: bytes) -> dict:
    (state, flags, t_ds, alt_dm, vz_cms, tx, ty, roll, tvy, tvp, v1, v2, seq) = struct.unpack("<BBHhhbbbbbBBB", p[:16])
    return {"state": state, "flags": flags, "t_s": t_ds / 10, "alt_m": alt_dm / 10, "vz_ms": vz_cms / 100,
            "tilt_x_deg": tx / 2, "tilt_y_deg": ty / 2, "roll_deg": roll * 2, "tvc_yaw_deg": tvy / 10,
            "tvc_pitch_deg": tvp / 10, "vbat1_V": v1 * 0.02, "vbat2_V": v2 * 0.05, "seq": seq}


def decode_evt(p: bytes) -> dict:
    t_ms, frm, to, reason = struct.unpack("<IBBB", p[:7])
    return {"t_ms": t_ms, "from": frm, "to": to, "reason": reason}


def decode_ack(p: bytes) -> dict:
    d = dict(zip(("cmd", "seq", "result", "state"), p[:4]))
    if len(p) >= 11:
        nonce, pre, left = struct.unpack_from("<IBH", p, 4)
        d.update(nonce=nonce, precond=pre, countdown_ms=left)
    return d


def decode_ign(p: bytes) -> dict:
    keys = ("t_pulse_on_ms", "t_cont_lost_ms", "t_thrust_ms", "t_pulse_off_ms", "arm_before_mv", "arm_min_mv",
            "vbat1_min_mv", "arm_samples", "end_reason")
    return dict(zip(keys, struct.unpack("<HHHHHHHHB", p[:17])))


def decode_bridge_ack(p: bytes) -> dict:
    return {"result": p[0], "regs": bytes(p[1:10])}


DECODERS = {TLM: decode_tlm, EVT: decode_evt, ACK: decode_ack, IGN: decode_ign, BRIDGE_ACK: decode_bridge_ack}


def decode(ftype: int, payload: bytes) -> dict:
    f = DECODERS.get(ftype)
    if f:
        return f(payload)
    if CMD_PING <= ftype <= CMD_HEARTBEAT and payload:
        return {"seq": payload[0]}
    return {}


def flags_text(flags: int) -> str:
    return " ".join(name for bit, name in FLAGS if flags & bit) or "-"


def missing_preconds(mask: int) -> list[str]:
    return [text for bit, text in PRECONDS if not mask & bit]


def ign_text(d: dict) -> str:
    def t(v):
        return "-" if v == IGN_NO_TIME else f"{v} ms"
    reason = IGN_END[d["end_reason"]] if d["end_reason"] < len(IGN_END) else str(d["end_reason"])
    return (f"Puls an {t(d['t_pulse_on_ms'])}, Durchgang weg {t(d['t_cont_lost_ms'])}, Schub {t(d['t_thrust_ms'])}, "
            f"Puls aus {t(d['t_pulse_off_ms'])} (Grund: {reason}); VBAT_ARMED {d['arm_before_mv'] / 1000:.2f} -> "
            f"{d['arm_min_mv'] / 1000:.2f} V ({d['arm_samples']} Messungen), 1S min {d['vbat1_min_mv'] / 1000:.2f} V")


# ---------------------------------------------------------------- Konfiguration
_CONST = re.compile(r"constexpr\s+[\w:]+\s+(\w+)\s*=\s*([^;]+);")


def read_config_h(path: str = CONFIG_H) -> dict:
    """Ganzzahlige constexpr-Werte aus firmware/src/Config.h (z. B. E22_CHANNEL, ROCKET_ID)."""
    values = {}
    with open(path, encoding="utf-8") as f:
        for m in _CONST.finditer(f.read()):
            text = m.group(2).strip()
            try:
                values[m.group(1)] = int(text.replace("'", ""), 0)
            except ValueError:
                continue
    return values


def e22_registers(cfg: dict, rssi_byte: bool) -> bytes:
    """Register 00H..08H wie firmware/src/E22Config.h."""
    return bytes([
        cfg["E22_ADDH"], cfg["E22_ADDL"], cfg["E22_NETID"],
        (0b011 << 5) | (0b00 << 3) | (cfg["E22_AIR_RATE"] & 0x07),
        cfg["E22_POWER"] & 0x03,
        cfg["E22_CHANNEL"],
        (0x80 if rssi_byte else 0x00) | 0x03,
        0x00, 0x00,
    ])


AIR_RATES = {0: "0,3", 1: "1,2", 2: "2,4", 3: "4,8", 4: "9,6", 5: "19,2", 6: "38,4", 7: "62,5"}
POWERS = {0: "22 dBm", 1: "17 dBm", 2: "13 dBm", 3: "10 dBm"}


def describe_e22(regs: bytes) -> str:
    return (f"Adresse 0x{regs[0]:02X}{regs[1]:02X}, Netz-ID {regs[2]}, Kanal {regs[5]} = {410.125 + regs[5]:.3f} MHz, "
            f"Luftrate {AIR_RATES[regs[3] & 7]} kbit/s, Leistung {POWERS[regs[4] & 3]}, "
            f"RSSI-Byte {'an' if regs[6] & 0x80 else 'aus'}")


def load_key(path: str = SECRETS_JSON) -> bytes:
    """16-Byte-Schlüssel aus secrets.json ({"key": "<32 Hex-Zeichen>"})."""
    with open(path, encoding="utf-8") as f:
        key = bytes.fromhex(json.load(f)["key"])
    if len(key) != 16:
        raise ValueError(f"{path}: Schlüssel muss 16 Byte (32 Hex-Zeichen) haben")
    if not any(key):
        raise ValueError(f"{path}: Schlüssel besteht nur aus Nullen (Vorlage nicht ausgefüllt)")
    return key
