#!/usr/bin/env python3
"""Geführter Tischtest des Mainboards rev B1 am PC.

Treibt die Testkonsole `revb_test` (examples/revb_test) über USB-Serial: stößt die Befehle
nacheinander an, beantwortet Rückfragen (WAIT/ASK/CONFIRM) über die Tastatur, wertet die
Zeilen `TEST <name> OK|FEHL|SKIP <detail>` und `CAL <name> <werte>` aus und schreibt den
Bericht als Markdown und JSON nach firmware/test_reports/.

Ablauf (jede Stufe einzeln abschaltbar):

  1. Versorgung ohne Teensy: Spannungen an den Testpunkten abfragen und prüfen (--skip-rails).
  2. Optional flashen (--flash: pio run -e revb_test -t upload).
  3. Verbinden, READY abwarten, Befehlsfolge ausführen:
       Standard      all                     (nichts bewegt sich, keine Rückfragen)
       --full        all full                (LEDs, Summer, Kamera, Servos, Motor, LoRa, GPS, SD, mit Rückfragen)
       --cal         cal gyro, cal baro, cal acc, cal mag, cal axes, cal adc, cal ina, cal save
       --commands    eigene Folge, Komma-getrennt, z. B. "mux,imu,cal gyro 20,cal save"
     Pyro wird nie automatisch angestoßen (nur --commands "pyro 1", mit Lämpchen).
  4. Bericht.

Mit --bringup wird stattdessen die Ausgabe von revb_bringup ([ OK ]/[FEHL]-Zeilen) mitgelesen
und eine Ruhemessung ausgewertet (alter Ablauf).

Wichtig: VIN und USB sind am Teensy getrennt. Der Teensy läuft nur, wenn am 1S-Eingang
(J_BAT1) Spannung anliegt (Akku oder Netzteil 2-16 V) und JP1 gebrückt oder der Schalter
an J_SW gesteckt ist. USB liefert dann nur die Daten. Ohne 2S melden Servos, Motor, Pyro
und INA239 "SKIP".

    pip install pyserial
    python tools/bench_test.py                       # Versorgung abfragen, dann "all"
    python tools/bench_test.py --skip-rails --full   # alles inklusive Aktoren
    python tools/bench_test.py --skip-rails --cal    # Kalibrierung, am Ende "cal save"
    python tools/bench_test.py --commands "imu,cal gyro 20,cal show" --port COM7
    python -m pytest tools/test_bench_test.py        # Parser ohne Hardware
"""
import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import serial
    import serial.tools.list_ports
except ImportError:          # die Parser-Tests brauchen pyserial nicht
    serial = None

FIRMWARE_DIR = Path(__file__).resolve().parent.parent
TEENSY_VID = 0x16C0

# Testpunkte rev B1 (circuit.py: VBAT_PROT, VSYS_IN, 5V_SYS, VSERVO, 3V3_RF, 3V3_EXP).
# (Netz, Bedingung, min, max). "1S" = nur 1S-Eingang versorgt, "2S" = auch 2S versorgt.
RAILS = [
    ("VSYS_IN", "1S", 2.0, 16.0),   # was am 1S-Eingang anliegt, hinter Verpolschutz und Schalter
    ("5V_SYS", "1S", 4.85, 5.15),
    ("3V3_RF", "1S", 3.2, 3.4),
    ("3V3_EXP", "1S", 3.2, 3.4),
    ("VBAT_PROT", "2S", 6.0, 8.6),
    ("VSERVO", "2S", 6.0, 8.6),
]

# Befehlsfolgen
PLAN_ALL = ["all"]
PLAN_FULL = ["all full"]
PLAN_CAL = ["cal gyro 10", "cal baro 20", "cal acc", "cal mag 40", "cal axes", "cal adc", "cal ina", "cal show", "cal save"]
# Zeitlimit je Befehl in Sekunden (ohne Rückfragen); Rückfragen setzen die Uhr zurück
TIMEOUTS = {"all": 60, "all full": 120, "cal mag": 240, "cal gyro": 150, "cal baro": 150, "cal axes": 60,
            "gps": 20, "sd": 60, "lora": 15, "imu": 20, "timing": 20, "watchdog": 10}
DEFAULT_TIMEOUT = 30

# ---------------------------------------------------------------- Protokoll der Testkonsole (Proto.h)
RESULTS = ("OK", "FEHL", "SKIP")
TEST_RE = re.compile(r"^TEST (\S+) (OK|FEHL|SKIP)(?: (.*))?$")
CAL_RE = re.compile(r"^CAL (\S+)(?: (.*))?$")
END_RE = re.compile(r"^END (.+?) (OK|FEHL|SKIP)$")
PROMPT_RE = re.compile(r"^(ASK|WAIT|CONFIRM) (.*)$")
INFO_RE = re.compile(r"^INFO (.*)$")


def parse_line(line):
    """Eine Konsolenzeile in ein Ereignis übersetzen; None für freien Text.

    Ereignisse: {"kind": "test", "name", "result", "detail"}, {"kind": "cal", "name", "values": [...]},
    {"kind": "end", "cmd", "result"}, {"kind": "prompt", "prompt": ASK|WAIT|CONFIRM, "text"},
    {"kind": "info", "text"}, {"kind": "ready"}, {"kind": "comment", "text"}.
    """
    line = line.rstrip("\r\n")
    if line == "READY":
        return {"kind": "ready"}
    m = TEST_RE.match(line)
    if m:
        return {"kind": "test", "name": m.group(1), "result": m.group(2), "detail": (m.group(3) or "").strip()}
    m = CAL_RE.match(line)
    if m:
        return {"kind": "cal", "name": m.group(1), "values": parse_values(m.group(2) or "")}
    m = END_RE.match(line)
    if m:
        return {"kind": "end", "cmd": m.group(1).strip(), "result": m.group(2)}
    m = PROMPT_RE.match(line)
    if m:
        return {"kind": "prompt", "prompt": m.group(1), "text": m.group(2)}
    m = INFO_RE.match(line)
    if m:
        return {"kind": "info", "text": m.group(1)}
    if line.startswith("# "):
        return {"kind": "comment", "text": line[2:]}
    return None


def parse_values(text):
    """Leerzeichen-getrennte Werte: Zahlen als float/int, Rest als Text."""
    out = []
    for tok in text.split():
        try:
            out.append(int(tok))
        except ValueError:
            try:
                out.append(float(tok))
            except ValueError:
                out.append(tok)
    return out


class Session:
    """Sammelt die Ereignisse einer Konsolensitzung."""

    def __init__(self):
        self.tests = []       # [{"cmd", "name", "result", "detail"}]
        self.cals = {}        # name -> values (letzter Wert gewinnt; adc_gain/servo_us je Kanal)
        self.ends = []        # [{"cmd", "result"}]
        self.infos = []
        self.log = []
        self.current_cmd = None

    def feed(self, line):
        self.log.append(line.rstrip("\r\n"))
        ev = parse_line(line)
        if ev is None:
            return None
        if ev["kind"] == "test":
            self.tests.append({"cmd": self.current_cmd, **{k: ev[k] for k in ("name", "result", "detail")}})
        elif ev["kind"] == "cal":
            key = ev["name"]
            if key in ("adc_gain", "servo_us") and ev["values"]:
                key = f"{key}[{ev['values'][0]}]"
                ev = {**ev, "values": ev["values"][1:]}
            self.cals[key] = ev["values"]
        elif ev["kind"] == "end":
            self.ends.append({"cmd": ev["cmd"], "result": ev["result"]})
        elif ev["kind"] == "info":
            self.infos.append(ev["text"])
        return ev

    def failed(self):
        return [t for t in self.tests if t["result"] == "FEHL"]

    def skipped(self):
        return [t for t in self.tests if t["result"] == "SKIP"]

    def overall(self):
        if any(t["result"] == "FEHL" for t in self.tests) or any(e["result"] == "FEHL" for e in self.ends):
            return "FEHL"
        if any(t["result"] == "SKIP" for t in self.tests):
            return "SKIP"
        return "OK" if self.tests else "LEER"


class ConsoleIO:
    """Rückfragen der Firmware an den Menschen am PC."""

    def answer(self, prompt, text):
        if prompt == "ASK":
            return input(f"  ? {text}: ").strip().replace(",", ".")
        if prompt == "CONFIRM":
            return input(f"  !! {text} [JA/nein]: ").strip()
        return input(f"  > {text} [Enter/n/q]: ").strip()


class ScriptedIO:
    """Vorgegebene Antworten, für Tests und unbeaufsichtigte Läufe."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.seen = []

    def answer(self, prompt, text):
        self.seen.append((prompt, text))
        return self.answers.pop(0) if self.answers else ""


def timeout_for(cmd):
    for key, t in sorted(TIMEOUTS.items(), key=lambda kv: -len(kv[0])):
        if cmd == key or cmd.startswith(key + " "):
            return t
    return DEFAULT_TIMEOUT


def read_line(port, timeout_s=0.5):
    """Eine Zeile als Text; "" bei Zeitablauf. port braucht readline() wie pyserial."""
    raw = port.readline()
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw


def send_line(port, text):
    port.write((text + "\n").encode("utf-8"))


def wait_ready(port, session, timeout_s=10.0, echo=print):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        line = read_line(port)
        if not line:
            continue
        ev = session.feed(line)
        if echo:
            echo("  " + line.rstrip())
        if ev and ev["kind"] == "ready":
            return True
    return False


def run_command(port, session, cmd, io, echo=print, timeout_s=None):
    """Einen Befehl ausführen, Rückfragen beantworten, bis END <cmd> lesen. Liefert das Ergebnis."""
    timeout_s = timeout_s or timeout_for(cmd)
    session.current_cmd = cmd
    send_line(port, cmd)
    if echo:
        echo(f"\n>> {cmd}")
    t_last = time.time()
    while True:
        line = read_line(port)
        if not line:
            if time.time() - t_last > timeout_s:
                session.ends.append({"cmd": cmd, "result": "FEHL"})
                session.tests.append({"cmd": cmd, "name": "timeout", "result": "FEHL", "detail": f"keine END-Zeile in {timeout_s} s"})
                if echo:
                    echo(f"  !! Zeitlimit {timeout_s} s ohne END {cmd}")
                return "FEHL"
            continue
        t_last = time.time()
        ev = session.feed(line)
        if echo:
            echo("  " + line.rstrip())
        if not ev:
            continue
        if ev["kind"] == "prompt":
            send_line(port, io.answer(ev["prompt"], ev["text"]))
            t_last = time.time()
        elif ev["kind"] == "end" and ev["cmd"] == cmd:
            return ev["result"]


def flash(env):
    print(f"\n== 2. {env} flashen ==")
    r = subprocess.run(["pio", "run", "-e", env, "-t", "upload"], cwd=FIRMWARE_DIR)
    if r.returncode != 0:
        sys.exit("Flashen fehlgeschlagen.")
    time.sleep(2.0)   # Teensy meldet sich nach dem Neustart neu am USB an


def find_port(port, wait_s=10.0):
    if port:
        return port
    if serial is None:
        sys.exit("pyserial fehlt: pip install pyserial")
    t0 = time.time()
    while time.time() - t0 < wait_s:
        for p in serial.tools.list_ports.comports():
            if p.vid == TEENSY_VID:
                return p.device
        time.sleep(0.5)
    sys.exit("Kein Teensy am USB gefunden. Läuft der 1S-Zweig (VIN ist vom USB getrennt)?")


# ---------------------------------------------------------------- Versorgung (vor dem Teensy)
def ask_float(prompt):
    while True:
        s = input(prompt).strip().replace(",", ".")
        if s == "":
            return None
        try:
            return float(s)
        except ValueError:
            print("  Zahl in Volt eingeben oder leer lassen zum Überspringen.")


def check_rails(have_2s, ask=ask_float):
    print("\n== 1. Versorgung (ohne Teensy, Netzteil mit 100 mA Strombegrenzung) ==")
    print("Spannung gegen GND messen und eintragen, leer = übersprungen.")
    results = []
    for net, cond, lo, hi in RAILS:
        if cond == "2S" and not have_2s:
            continue
        v = ask(f"  {net:10s} ({lo:.2f}..{hi:.2f} V): ")
        ok = None if v is None else lo <= v <= hi
        results.append({"net": net, "volt": v, "min": lo, "max": hi, "ok": ok})
        if ok is False:
            print(f"  -> FEHLER: {net} außerhalb. Erst klären, dann den Teensy stecken.")
    return results


# ---------------------------------------------------------------- alter Ablauf: revb_bringup
RESULT_RE = re.compile(r"\[( OK |FEHL)\]\s+(.+?)\s{2,}(.*)$")
LIVE_RE = {
    "acc": re.compile(r"a=\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\]"),
    "gyro": re.compile(r"w=\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\]"),
    "p": re.compile(r"p=([-\d.]+) Pa"),
    "v2s": re.compile(r"2S ([-\d.]+) V ([-\d.]+) mA"),
    "v1s": re.compile(r"1S ([-\d.]+) V"),
    "arm": re.compile(r"ARM ([-\d.]+) V"),
}


def parse_bringup_line(line, section=""):
    """[ OK ]/[FEHL]-Zeile von revb_bringup -> dict oder None."""
    m = RESULT_RE.search(line)
    if not m:
        return None
    return {"section": section, "what": m.group(2).strip(), "ok": m.group(1) == " OK ", "detail": m.group(3).strip()}


def read_selftest(ser, timeout_s=30.0):
    """Liest bis zur Ergebniszeile; liefert (Zeilen, Einzelergebnisse, Gesamtergebnis)."""
    print("\n== 3. Selbsttest revb_bringup ==")
    lines, checks, section = [], [], ""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        line = read_line(ser)
        if not line:
            continue
        line = line.rstrip()
        lines.append(line)
        print("  " + line)
        if re.match(r"^\d\. ", line):
            section = line
        c = parse_bringup_line(line, section)
        if c:
            checks.append(c)
        if line.startswith("Ergebnis:"):
            return lines, checks, "alles da" in line
    print("  (Keine Ergebniszeile. Läuft revb_bringup? Sonst mit --flash starten.)")
    return lines, checks, False


def record_live(ser, seconds):
    print(f"\n== 4. Ruhemessung {seconds} s: Platine flach liegen lassen, nicht berühren ==")
    samples = {k: [] for k in LIVE_RE}
    t0 = time.time()
    while time.time() - t0 < seconds:
        line = read_line(ser)
        if not line:
            continue
        for key, rx in LIVE_RE.items():
            m = rx.search(line)
            if m:
                samples[key].append(tuple(float(g) for g in m.groups()))
        print(f"\r  {time.time() - t0:5.1f} s, {len(samples['acc'])} IMU-Werte", end="")
    print()
    return samples


def stats(samples):
    out = {}

    def col(key, i):
        return [s[i] for s in samples[key]]

    if len(samples["gyro"]) >= 3:
        out["gyro_bias_dps"] = [statistics.mean(col("gyro", i)) for i in range(3)]
        out["gyro_std_dps"] = [statistics.stdev(col("gyro", i)) for i in range(3)]
    if len(samples["acc"]) >= 3:
        norm = [math.sqrt(sum(v * v for v in s)) for s in samples["acc"]]
        out["acc_mean_ms2"] = [statistics.mean(col("acc", i)) for i in range(3)]
        out["acc_norm_ms2"] = statistics.mean(norm)
        out["acc_norm_err_ms2"] = statistics.mean(norm) - 9.80665
    if len(samples["p"]) >= 3:
        p = col("p", 0)
        out["p_mean_pa"] = statistics.mean(p)
        out["p_std_pa"] = statistics.stdev(p)
        out["p_std_m"] = statistics.stdev(p) / 12.0   # ca. 12 Pa je Meter in Bodennähe
    for key in ("v1s", "arm"):
        if samples[key]:
            out[f"{key}_mean_v"] = statistics.mean(col(key, 0))
    if samples["v2s"]:
        out["v2s_mean_v"] = statistics.mean(col("v2s", 0))
        out["i2s_mean_ma"] = statistics.mean(col("v2s", 1))
    return out


def judge(st):
    """Grobe Plausibilität der Ruhemessung; Grenzen sind Erfahrungswerte, keine Datenblattwerte."""
    notes = []
    if "gyro_bias_dps" in st and max(abs(b) for b in st["gyro_bias_dps"]) > 2.0:
        notes.append("Gyro-Offset > 2 °/s auf einer Achse (bewegt? sonst Bauteil prüfen)")
    if "acc_norm_err_ms2" in st and abs(st["acc_norm_err_ms2"]) > 0.5:
        notes.append("|a| weicht mehr als 0,5 m/s² von 1 g ab (Skalierung oder Achsen prüfen)")
    if "p_std_m" in st and st["p_std_m"] > 0.5:
        notes.append("Druckrauschen > 0,5 m (Filter/OSR prüfen, Luftzug?)")
    if "acc_mean_ms2" in st and abs(st["acc_mean_ms2"][2]) < 8.0:
        notes.append("Z-Achse zeigt nicht ~1 g; liegt die Platine flach, Bestückseite oben?")
    return notes


# ---------------------------------------------------------------- Bericht
def rails_markdown(rails):
    md = ["## Versorgung", "", "| Netz | gemessen | Bereich | |", "|---|---|---|---|"]
    for r in rails:
        v = "–" if r["volt"] is None else f"{r['volt']:.3f} V"
        mark = {True: "ok", False: "**FEHLER**", None: "übersprungen"}[r["ok"]]
        md.append(f"| {r['net']} | {v} | {r['min']:.2f}..{r['max']:.2f} V | {mark} |")
    return md + [""]


def report_markdown(session, rails, stamp, notes=()):
    md = [f"# Tischtest Mainboard rev B1, {stamp}", ""]
    if rails:
        md += rails_markdown(rails)
    md += [f"## Prüfungen: **{session.overall()}**", "",
           f"{len(session.tests)} Prüfungen, {len(session.failed())} FEHL, {len(session.skipped())} SKIP", "",
           "| Befehl | Prüfung | Ergebnis | Detail |", "|---|---|---|---|"]
    for t in session.tests:
        res = {"OK": "ok", "FEHL": "**FEHL**", "SKIP": "übersprungen"}[t["result"]]
        md.append(f"| {t['cmd'] or ''} | {t['name']} | {res} | {t['detail']} |")
    md.append("")
    if session.cals:
        md += ["## Kalibrierwerte", "", "| Name | Werte |", "|---|---|"]
        for k, v in session.cals.items():
            md.append(f"| {k} | {' '.join(str(x) for x in v)} |")
        md.append("")
    if notes:
        md += ["## Auffällig", ""] + [f"- {n}" for n in notes] + [""]
    return "\n".join(md) + "\n"


def write_report(outdir, session, rails, notes=(), extra=None):
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    data = {"time": stamp, "rails": rails, "overall": session.overall(), "tests": session.tests,
            "cals": session.cals, "ends": session.ends, "notes": list(notes), "log": session.log}
    if extra:
        data.update(extra)
    (outdir / f"bench_{stamp}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    path = outdir / f"bench_{stamp}.md"
    path.write_text(report_markdown(session, rails, stamp, notes), encoding="utf-8")
    return path


def write_bringup_report(outdir, rails, checks, overall, st, notes, lines):
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    data = {"time": stamp, "rails": rails, "selftest_ok": overall, "checks": checks,
            "rest": st, "notes": notes, "log": lines}
    (outdir / f"bench_{stamp}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    md = [f"# Tischtest Mainboard rev B1 (revb_bringup), {stamp}", ""]
    if rails:
        md += rails_markdown(rails)
    md += ["## Selbsttest", "", f"Gesamt: **{'ok' if overall else 'FEHLER'}**", "",
           "| Abschnitt | Prüfung | | Detail |", "|---|---|---|---|"]
    for c in checks:
        md.append(f"| {c['section']} | {c['what']} | {'ok' if c['ok'] else '**FEHLER**'} | {c['detail']} |")
    md += ["", "## Ruhemessung", ""]
    for k, v in st.items():
        md.append(f"- {k}: {', '.join(f'{x:.4f}' for x in v) if isinstance(v, list) else f'{v:.4f}'}")
    if notes:
        md += ["", "## Auffällig", ""] + [f"- {n}" for n in notes]
    path = outdir / f"bench_{stamp}.md"
    path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------- Hauptablauf
def run_console(port_name, commands, io, out, rails, echo=print):
    """Testkonsole: verbinden, Befehle ausführen, Bericht. Liefert (Session, Berichtspfad)."""
    session = Session()
    ser = serial.Serial(port_name, 115200, timeout=0.5)
    try:
        send_line(ser, "")                      # leere Zeile: Konsole antwortet READY
        if not wait_ready(ser, session, 10.0, echo):
            echo("  (Kein READY. Läuft revb_test? Sonst mit --flash starten.)")
        for cmd in commands:
            res = run_command(ser, session, cmd, io, echo)
            echo(f"<< {cmd}: {res}")
            if cmd == "watchdog fire":
                ser.close()
                echo("  Neustart durch den Watchdog, warte auf den Teensy ...")
                time.sleep(3.0)
                ser = serial.Serial(find_port(None, 20.0), 115200, timeout=0.5)
                session.current_cmd = cmd
                wait_ready(ser, session, 10.0, echo)
                if not any(t["name"] == "watchdog_reset" for t in session.tests):
                    session.tests.append({"cmd": cmd, "name": "watchdog_reset", "result": "FEHL", "detail": "nach dem Neustart nicht gemeldet"})
    finally:
        ser.close()
    path = write_report(out, session, rails)
    return session, path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serieller Port, sonst automatisch (Teensy-VID)")
    ap.add_argument("--flash", action="store_true", help="Firmware vorher flashen (revb_test bzw. revb_bringup)")
    ap.add_argument("--skip-rails", action="store_true", help="Spannungsabfrage überspringen")
    ap.add_argument("--no-2s", action="store_true", help="2S-Zweig ist nicht versorgt")
    ap.add_argument("--full", action="store_true", help="'all full': auch LEDs, Summer, Kamera, Servos, Motor, LoRa, GPS, SD")
    ap.add_argument("--cal", action="store_true", help="Kalibrierfolge anhängen (endet mit 'cal save')")
    ap.add_argument("--commands", help="eigene Befehlsfolge, Komma-getrennt (ersetzt --full/--cal)")
    ap.add_argument("--bringup", action="store_true", help="alter Ablauf: revb_bringup mitlesen und Ruhemessung")
    ap.add_argument("--seconds", type=float, default=30.0, help="Dauer der Ruhemessung (--bringup)")
    ap.add_argument("--out", type=Path, default=FIRMWARE_DIR / "test_reports")
    a = ap.parse_args()

    if serial is None:
        sys.exit("pyserial fehlt: pip install pyserial")

    rails = [] if a.skip_rails else check_rails(not a.no_2s)
    if any(r["ok"] is False for r in rails) and input("\nTrotz Fehler weiter? [j/N] ").lower() != "j":
        sys.exit(1)
    if not a.skip_rails:
        input("\nJetzt Teensy stecken, Strombegrenzung auf ca. 500 mA, USB verbinden. Enter ...")
    if a.flash:
        flash("revb_bringup" if a.bringup else "revb_test")

    if a.bringup:
        # revb_bringup wartet nach dem Einschalten nur 4 s auf die Konsole: neu einschalten, sofort verbinden
        if not a.flash:
            input("\n1S-Versorgung aus, Enter drücken, dann sofort wieder einschalten ...")
        with serial.Serial(find_port(a.port), 115200, timeout=0.5) as ser:
            lines, checks, overall = read_selftest(ser)
            st = stats(record_live(ser, a.seconds))
        notes = judge(st)
        if a.no_2s:
            notes.append("2S nicht versorgt: INA239- und 2S-Prüfungen schlagen erwartungsgemäß fehl")
        path = write_bringup_report(a.out, rails, checks, overall, st, notes, lines)
        failed = [c for c in checks if not c["ok"]]
        print(f"\nSelbsttest: {'ok' if overall else 'FEHLER'}, {len(failed)} Einzelprüfungen fehlgeschlagen")
        for n in notes:
            print("  ! " + n)
        print(f"Bericht: {path}")
        sys.exit(0 if overall and not failed else 1)

    if a.commands:
        commands = [c.strip() for c in a.commands.split(",") if c.strip()]
    else:
        commands = list(PLAN_FULL if a.full else PLAN_ALL)
        if a.cal:
            commands += PLAN_CAL
    session, path = run_console(find_port(a.port), commands, ConsoleIO(), a.out, rails)
    print(f"\nErgebnis: {session.overall()}, {len(session.tests)} Prüfungen, {len(session.failed())} FEHL, {len(session.skipped())} SKIP")
    for t in session.failed():
        print(f"  ! {t['name']}: {t['detail']}")
    if a.no_2s:
        print("  (2S nicht versorgt: SKIP bei Servos, Motor, Pyro, INA239 ist erwartet)")
    print(f"Bericht: {path}")
    sys.exit(0 if session.overall() in ("OK", "SKIP") else 1)


if __name__ == "__main__":
    main()
