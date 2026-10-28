"""Startwerkzeug am Laptop: Telemetrie, Kommandos und Motorstart über die Funkbrücke (Pico + E22, USB).

    python tools/ground/launch.py --port COM5          (Windows)
    python tools/ground/launch.py --port /dev/ttyACM0  (Linux)
    python tools/ground/launch.py --port COM5 --config E22 der Brücke passend zur Rakete einstellen
    python tools/ground/launch.py --new-key            Schlüssel erzeugen (secrets.json und Secrets.h)

Tasten:  p PING   c CALIBRATE   r PAD_READY   s SAFE   a ARM   l LAUNCH   q Ende
         Leertaste  ABORT, jederzeit (ohne MAC, wird fünfmal gesendet)

Ablauf (docs/Plan_Bordzuendung_2026-10-27.md, Bauanleitung §6.1): PAD_READY, warten bis der
Servo-Selbsttest durch ist, ARM (holt per PING die nonce, sendet ARM mit MAC; bei Ablehnung stehen die
fehlenden Vorbedingungen im Klartext da), LAUNCH (erst nach Eingabe von START). Ab ARM sendet das
Skript den Heartbeat mit 4 Hz, solange die Rakete ARMED oder COUNTDOWN meldet; fehlt er länger als 1 s,
geht die Rakete selbst nach SAFE. Alles Empfangene und Gesendete landet als CSV in tools/ground/logs/.

Die Funkbrücke (tools/ground/bridge_pico) reicht Rahmen unverändert durch; --config stellt Kanal, Adresse,
Luftrate und Sendeleistung ihres E22 auf die Werte aus firmware/src/Config.h und schaltet das RSSI-Byte ein.

Abhängigkeiten: Python 3.9+, pyserial.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import secrets
import sys
import threading
import time

import kartonaut_radio as kr

HEARTBEAT_PERIOD_S = 0.25          # 4 Hz, die Rakete verlangt mindestens 2 Hz
ACK_TIMEOUT_S = 1.2
ABORT_REPEATS = 5
LOG_DIR = os.path.join(kr.HERE, "logs")
SECRETS_H = os.path.join(kr.REPO, "firmware", "src", "Secrets.h")


# ---------------------------------------------------------------- Tastatur ohne Enter
class Keyboard:
    def __enter__(self):
        if os.name == "nt":
            import msvcrt
            self._msvcrt = msvcrt
        else:
            import termios
            import tty
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, *exc):
        if os.name != "nt":
            import termios
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def get(self) -> str | None:
        if os.name == "nt":
            return self._msvcrt.getwch() if self._msvcrt.kbhit() else None
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return os.read(self._fd, 1).decode(errors="ignore")
        return None


# ---------------------------------------------------------------- Funkstrecke
class Link:
    def __init__(self, port: str, baud: int, key: bytes | None, rocket_id: int, rssi: bool):
        import serial
        self.ser = serial.Serial(port, baud, timeout=0.05)
        self.key, self.rocket_id = key, rocket_id
        self.parser = kr.Parser(rssi_byte=rssi)
        self.lock = threading.Lock()
        self.seq = 0
        self.tlm: dict | None = None
        self.tlm_time = 0.0
        self.tlm_lost = 0
        self.acks: dict[tuple[int, int], dict] = {}
        self.nonce: int | None = None
        self.hb_grace_until = 0.0
        self.running = True
        self.t0 = time.time()
        os.makedirs(LOG_DIR, exist_ok=True)
        name = dt.datetime.now().strftime("launch_%Y%m%d_%H%M%S.csv")
        self.csv_path = os.path.join(LOG_DIR, name)
        self._csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_file)
        self._csv.writerow(["zeit", "t_s", "richtung", "typ", "hex", "felder"])
        self.messages: list[str] = []
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._heartbeat, daemon=True).start()

    # -- Protokoll
    def log(self, direction: str, ftype: int, frame: bytes, fields: dict):
        now = time.time()
        with self.lock:
            self._csv.writerow([dt.datetime.now().isoformat(timespec="milliseconds"), f"{now - self.t0:.3f}",
                                direction, kr.TYPE_NAMES.get(ftype, hex(ftype)), frame.hex(), json.dumps(fields)])
            self._csv_file.flush()

    def say(self, text: str):
        with self.lock:
            self.messages.append(text)

    def _write(self, ftype: int, frame: bytes, fields: dict):
        with self.lock:
            self.ser.write(frame)
        self.log("tx", ftype, frame, fields)

    def _next_seq(self) -> int:
        with self.lock:                     # Heartbeat-Thread und Tasten teilen die Folgenummer
            self.seq = (self.seq + 1) & 0xFF
            return self.seq

    def send(self, ftype: int) -> int:
        seq = self._next_seq()
        self._write(ftype, kr.cmd(ftype, seq), {"seq": seq})
        return seq

    def send_auth(self, ftype: int, nonce: int) -> int:
        seq = self._next_seq()
        frame = kr.auth_cmd(ftype, seq, nonce, self.key, self.rocket_id)
        self._write(ftype, frame, {"seq": seq, "nonce": nonce})
        return seq

    def state(self) -> int | None:
        if self.tlm is None or time.time() - self.tlm_time > 2.0:
            return None
        return self.tlm["state"]

    # -- Threads
    def _reader(self):
        while self.running:
            data = self.ser.read(256)
            if not data:
                continue
            for ftype, payload in self.parser.feed(data):
                fields = kr.decode(ftype, payload)
                self.log("rx", ftype, kr.encode(ftype, payload), fields)
                self._handle(ftype, fields)

    def _handle(self, ftype: int, d: dict):
        if ftype == kr.TLM:
            if self.tlm is not None:
                self.tlm_lost += (d["seq"] - self.tlm["seq"] - 1) & 0xFF
            self.tlm, self.tlm_time = d, time.time()
        elif ftype == kr.EVT:
            text = f"EREIGNIS {kr.state_name(d['from'])} -> {kr.state_name(d['to'])} ({kr.reason_name(d['reason'])})"
            if d["to"] == kr.MISFIRE:
                text += ("\n  FEHLZÜNDUNG: 60 s warten, dann SAFE (Taste s), erst dann hingehen und den "
                         "Arming-Schalter ausschalten.")
            self.say(text)
        elif ftype == kr.ACK:
            if "nonce" in d:
                self.nonce = d["nonce"] or None
            with self.lock:
                self.acks[(d["cmd"], d["seq"])] = d
        elif ftype == kr.IGN:
            self.say("ZÜNDUNG: " + kr.ign_text(d))

    def _heartbeat(self):
        while self.running:
            if time.time() < self.hb_grace_until or self.state() in (kr.ARMED, kr.COUNTDOWN):
                self.send(kr.CMD_HEARTBEAT)
            time.sleep(HEARTBEAT_PERIOD_S)

    def wait_ack(self, ftype: int, seq: int, keys: Keyboard, timeout: float = ACK_TIMEOUT_S) -> dict | None:
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                ack = self.acks.pop((ftype, seq), None)
            if ack is not None:
                return ack
            if keys.get() == " ":
                self.abort()
                return None
            time.sleep(0.02)
        return None

    def abort(self):
        for _ in range(ABORT_REPEATS):
            self.send(kr.CMD_ABORT)
            time.sleep(0.1)
        self.say("ABORT gesendet")

    def close(self):
        self.running = False
        time.sleep(0.1)
        self.ser.close()
        self._csv_file.close()


# ---------------------------------------------------------------- Abläufe
def fetch_nonce(link: Link, keys: Keyboard) -> int | None:
    for _ in range(3):
        ack = link.wait_ack(kr.CMD_PING, link.send(kr.CMD_PING), keys)
        if ack is not None:
            return ack.get("nonce") or None
    return None


def do_arm(link: Link, keys: Keyboard):
    if link.key is None:
        link.say("Kein Schlüssel: secrets.json fehlt (python tools/ground/launch.py --new-key)")
        return
    if link.state() not in (None, kr.PAD_READY):
        link.say(f"ARM nur aus PAD_READY (Rakete meldet {kr.state_name(link.state())})")
        return
    nonce = fetch_nonce(link, keys)
    if nonce is None:
        link.say("Keine nonce von der Rakete (keine Antwort auf PING oder nicht in PAD_READY)")
        return
    link.hb_grace_until = time.time() + 2.0
    ack = link.wait_ack(kr.CMD_ARM, link.send_auth(kr.CMD_ARM, nonce), keys)
    if ack is None:
        link.say("ARM: keine Antwort; Zustand in der Telemetrie prüfen, ggf. noch einmal a")
    elif ack["result"] == kr.ACK_OK:
        link.say("SCHARF (ARMED). Heartbeat läuft. LAUNCH mit l, Abbruch mit Leertaste.")
    elif ack["result"] == kr.ACK_AUTH:
        link.say("ARM abgelehnt: MAC falsch. Schlüssel in secrets.json und firmware/src/Secrets.h vergleichen.")
    else:
        missing = kr.missing_preconds(ack.get("precond", 0))
        link.say("ARM verweigert, es fehlt:\n  - " + "\n  - ".join(missing or ["(nichts gemeldet)"]))


def read_word(link: Link, keys: Keyboard, prompt: str) -> str | None:
    """Wort mit Enter abschließen; Leertaste bricht ab (und sendet ABORT)."""
    sys.stdout.write("\n" + prompt)
    sys.stdout.flush()
    word = ""
    while True:
        k = keys.get()
        if k is None:
            if link.state() not in (None, kr.ARMED):
                print("\n(Rakete nicht mehr ARMED)")
                return None
            time.sleep(0.02)
            continue
        if k == " ":
            print()
            link.abort()
            return None
        if k in ("\r", "\n"):
            print()
            return word
        if k in ("\x08", "\x7f"):
            word = word[:-1]
            sys.stdout.write("\b \b")
        elif k.isprintable():
            word += k
            sys.stdout.write(k)
        sys.stdout.flush()


def do_launch(link: Link, keys: Keyboard):
    if link.state() != kr.ARMED:
        link.say(f"LAUNCH nur aus ARMED (Rakete meldet {kr.state_name(link.state()) if link.state() is not None else 'nichts'})")
        return
    word = read_word(link, keys, "Zum Start START eingeben und Enter drücken (Leertaste = ABORT): ")
    if word != "START":
        if word is not None:
            link.say("Kein Start (Eingabe war nicht START)")
        return
    nonce = link.nonce or fetch_nonce(link, keys)
    if nonce is None:
        link.say("Keine nonce für LAUNCH (PING ohne Antwort)")
        return
    link.nonce = None
    ack = link.wait_ack(kr.CMD_LAUNCH, link.send_auth(kr.CMD_LAUNCH, nonce), keys)
    if ack is None:
        link.say("LAUNCH: keine Antwort; Zustand in der Telemetrie prüfen (COUNTDOWN?)")
    elif ack["result"] == kr.ACK_OK:
        link.say(f"COUNTDOWN läuft: {ack.get('countdown_ms', 0) / 1000:.1f} s. Leertaste = ABORT.")
    elif ack["result"] == kr.ACK_AUTH:
        link.say("LAUNCH abgelehnt: MAC falsch (neue nonce ist da, l noch einmal)")
    else:
        link.say("LAUNCH abgelehnt; fehlt: " + (", ".join(kr.missing_preconds(ack.get("precond", 0))) or "-"))


def status_line(link: Link) -> str:
    t = link.tlm
    if t is None:
        return "keine Telemetrie"
    age = time.time() - link.tlm_time
    stale = f" (seit {age:.0f} s still)" if age > 2 else ""
    rssi = f"{link.parser.rssi_dbm} dBm" if link.parser.rssi_dbm is not None else "-"
    return (f"{kr.state_name(t['state']):<10} t {t['t_s']:6.1f} s | 1S {t['vbat1_V']:.2f} V 2S {t['vbat2_V']:.2f} V | "
            f"Kipp {t['tilt_x_deg']:+.1f}/{t['tilt_y_deg']:+.1f} Roll {t['roll_deg']:+d} | h {t['alt_m']:+.1f} m "
            f"vz {t['vz_ms']:+.1f} | {kr.flags_text(t['flags'])} | RSSI {rssi} | verloren {link.tlm_lost}{stale}")


def run(args):
    cfg = kr.read_config_h()
    key = None
    try:
        key = kr.load_key(args.secrets)
    except FileNotFoundError:
        print(f"Hinweis: {args.secrets} fehlt, ARM und LAUNCH gesperrt (--new-key)")
    except ValueError as e:
        print(f"Hinweis: {e}; ARM und LAUNCH gesperrt")
    link = Link(args.port, args.baud or cfg["RADIO_BAUD"], key, cfg["ROCKET_ID"], not args.no_rssi)
    print(__doc__.split("\n\n")[1])
    print(f"Log: {link.csv_path}\n")
    actions = {"p": kr.CMD_PING, "c": kr.CMD_CALIBRATE, "r": kr.CMD_PAD_READY, "s": kr.CMD_SAFE}
    last_status = 0.0
    try:
        with Keyboard() as keys:
            while True:
                k = keys.get()
                if k == " ":
                    link.abort()
                elif k == "q":
                    break
                elif k in actions:
                    seq = link.send(actions[k])
                    ack = link.wait_ack(actions[k], seq, keys)
                    link.say(f"{kr.TYPE_NAMES[actions[k]]}: "
                             + (kr.ACK_NAMES.get(ack["result"], "?") + f", Zustand {kr.state_name(ack['state'])}"
                                if ack else "keine Antwort"))
                elif k == "a":
                    do_arm(link, keys)
                elif k == "l":
                    do_launch(link, keys)
                with link.lock:
                    msgs, link.messages = link.messages, []
                for m in msgs:
                    sys.stdout.write("\r\x1b[K" + m + "\n")
                if time.time() - last_status > 0.3 or msgs:
                    sys.stdout.write("\r\x1b[K" + status_line(link)[:160])
                    sys.stdout.flush()
                    last_status = time.time()
                time.sleep(0.02)
    finally:
        print()
        link.close()


def configure_bridge(args) -> int:
    import serial
    want = kr.e22_registers(kr.read_config_h(), rssi_byte=True)
    with serial.Serial(args.port, 115200, timeout=0.1) as ser:
        time.sleep(0.2)
        ser.reset_input_buffer()
        ser.write(kr.encode(kr.BRIDGE_CONFIG))
        parser = kr.Parser()
        end = time.time() + 5.0
        while time.time() < end:
            for ftype, payload in parser.feed(ser.read(64)):
                if ftype != kr.BRIDGE_ACK:
                    continue                      # Telemetrie der Rakete, die noch unterwegs war
                d = kr.decode_bridge_ack(payload)
                print("Brücke: " + kr.BRIDGE_RESULTS.get(d["result"], str(d["result"])))
                if d["result"] != 1:
                    print("Modul:  " + kr.describe_e22(d["regs"]))
                print("Soll:   " + kr.describe_e22(want))
                return 0 if d["result"] == 0 and d["regs"] == want else 2
    print("Keine Antwort der Funkbrücke (Port richtig? Firmware tools/ground/bridge_pico geflasht?)")
    return 2


def new_key(args):
    if os.path.exists(args.secrets) or os.path.exists(SECRETS_H):
        print(f"Abbruch: {args.secrets} oder {SECRETS_H} gibt es schon (nicht überschreiben).")
        return 1
    key = secrets.token_bytes(16)
    with open(args.secrets, "w", encoding="utf-8") as f:
        json.dump({"key": key.hex()}, f, indent=2)
        f.write("\n")
    body = ",\n  ".join(", ".join(f"0x{b:02X}" for b in key[i:i + 8]) for i in (0, 8))
    with open(SECRETS_H, "w", encoding="utf-8") as f:
        f.write("#pragma once\n// Startschlüssel, erzeugt von tools/ground/launch.py --new-key. Nicht ins Repo.\n"
                f"#include <stdint.h>\n\nconstexpr uint8_t LAUNCH_KEY[16] = {{\n  {body},\n}};\n")
    print(f"Schlüssel geschrieben: {args.secrets} und {SECRETS_H} (beide in .gitignore).")
    print("Firmware neu bauen und flashen, damit die Rakete ihn kennt.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Startwerkzeug Kartonaut (Laptop + Funkbrücke Pico/E22)")
    ap.add_argument("--port", help="serielle Schnittstelle der Funkbrücke (USB)")
    ap.add_argument("--baud", type=int, default=0, help="UART-Baudrate (Standard: RADIO_BAUD aus Config.h)")
    ap.add_argument("--secrets", default=kr.SECRETS_JSON, help="Schlüsseldatei (Standard: tools/ground/secrets.json)")
    ap.add_argument("--no-rssi", action="store_true", help="E22 der Brücke hängt kein RSSI-Byte an")
    ap.add_argument("--config", action="store_true", help="E22 der Funkbrücke passend zur Rakete einstellen und beenden")
    ap.add_argument("--new-key", action="store_true", help="neuen Schlüssel erzeugen und beenden")
    args = ap.parse_args(argv)
    if args.new_key:
        return new_key(args)
    if not args.port:
        ap.error("--port fehlt")
    if args.config:
        return configure_bridge(args)
    run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
