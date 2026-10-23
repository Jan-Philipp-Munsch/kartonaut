#!/usr/bin/env python3
"""Geführter Tischtest des Mainboards rev B1 am PC.

Ablauf (jede Stufe einzeln abschaltbar):

  1. Versorgung ohne Teensy: Spannungen an den Testpunkten abfragen und prüfen.
  2. Optional revb_bringup flashen (pio run -e revb_bringup -t upload).
  3. Selbsttest von revb_bringup über USB mitlesen und die [ OK ]/[FEHL]-Zeilen auswerten.
  4. Messwerte eine Weile in Ruhe aufzeichnen: Gyro-Offset, |a|, Druckrauschen, Akkuspannungen.
  5. Bericht als Markdown und JSON in firmware/test_reports/.

Wichtig: VIN und USB sind am Teensy getrennt. Der Teensy läuft nur, wenn am 1S-Eingang
(J_BAT1) Spannung anliegt (Akku oder Netzteil 2-16 V) und JP1 gebrückt oder der Schalter
an J_SW gesteckt ist. USB liefert dann nur die Daten.

    pip install pyserial
    python tools/bench_test.py                 # alles, Port automatisch
    python tools/bench_test.py --flash         # vorher revb_bringup flashen
    python tools/bench_test.py --skip-rails --seconds 60 --port COM7
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
except ImportError:
    sys.exit("pyserial fehlt: pip install pyserial")

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

RESULT_RE = re.compile(r"\[( OK |FEHL)\]\s+(.+?)\s{2,}(.*)$")
LIVE_RE = {
    "acc": re.compile(r"a=\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\]"),
    "gyro": re.compile(r"w=\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\]"),
    "p": re.compile(r"p=([-\d.]+) Pa"),
    "v2s": re.compile(r"2S ([-\d.]+) V ([-\d.]+) mA"),
    "v1s": re.compile(r"1S ([-\d.]+) V"),
    "arm": re.compile(r"ARM ([-\d.]+) V"),
}


def ask_float(prompt):
    while True:
        s = input(prompt).strip().replace(",", ".")
        if s == "":
            return None
        try:
            return float(s)
        except ValueError:
            print("  Zahl in Volt eingeben oder leer lassen zum Überspringen.")


def check_rails(have_2s):
    print("\n== 1. Versorgung (ohne Teensy, Netzteil mit 100 mA Strombegrenzung) ==")
    print("Spannung gegen GND messen und eintragen, leer = übersprungen.")
    results = []
    for net, cond, lo, hi in RAILS:
        if cond == "2S" and not have_2s:
            continue
        v = ask_float(f"  {net:10s} ({lo:.2f}..{hi:.2f} V): ")
        ok = None if v is None else lo <= v <= hi
        results.append({"net": net, "volt": v, "min": lo, "max": hi, "ok": ok})
        if ok is False:
            print(f"  -> FEHLER: {net} außerhalb. Erst klären, dann den Teensy stecken.")
    return results


def flash():
    print("\n== 2. revb_bringup flashen ==")
    r = subprocess.run(["pio", "run", "-e", "revb_bringup", "-t", "upload"], cwd=FIRMWARE_DIR)
    if r.returncode != 0:
        sys.exit("Flashen fehlgeschlagen.")
    time.sleep(2.0)   # Teensy meldet sich nach dem Neustart neu am USB an


def find_port(port):
    if port:
        return port
    for _ in range(20):
        for p in serial.tools.list_ports.comports():
            if p.vid == TEENSY_VID:
                return p.device
        time.sleep(0.5)
    sys.exit("Kein Teensy am USB gefunden. Läuft der 1S-Zweig (VIN ist vom USB getrennt)?")


def read_selftest(ser, timeout_s=30.0):
    """Liest bis zur Ergebniszeile; liefert (Zeilen, Einzelergebnisse, Gesamtergebnis)."""
    print("\n== 3. Selbsttest revb_bringup ==")
    lines, checks, section = [], [], ""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace").rstrip()
        lines.append(line)
        print("  " + line)
        if re.match(r"^\d\. ", line):
            section = line
        m = RESULT_RE.search(line)
        if m:
            checks.append({"section": section, "what": m.group(2).strip(),
                           "ok": m.group(1) == " OK ", "detail": m.group(3).strip()})
        if line.startswith("Ergebnis:"):
            return lines, checks, "alles da" in line
    print("  (Keine Ergebniszeile. Läuft revb_bringup? Sonst mit --flash starten.)")
    return lines, checks, False


def record_live(ser, seconds):
    print(f"\n== 4. Ruhemessung {seconds} s: Platine flach liegen lassen, nicht berühren ==")
    samples = {k: [] for k in LIVE_RE}
    t0 = time.time()
    while time.time() - t0 < seconds:
        raw = ser.readline()
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace")
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


def write_report(outdir, rails, checks, overall, st, notes, lines):
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    data = {"time": stamp, "rails": rails, "selftest_ok": overall, "checks": checks,
            "rest": st, "notes": notes, "log": lines}
    (outdir / f"bench_{stamp}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    md = [f"# Tischtest Mainboard rev B1, {stamp}", ""]
    if rails:
        md += ["## Versorgung", "", "| Netz | gemessen | Bereich | |", "|---|---|---|---|"]
        for r in rails:
            v = "–" if r["volt"] is None else f"{r['volt']:.3f} V"
            mark = {True: "ok", False: "**FEHLER**", None: "übersprungen"}[r["ok"]]
            md.append(f"| {r['net']} | {v} | {r['min']:.2f}..{r['max']:.2f} V | {mark} |")
        md.append("")
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serieller Port, sonst automatisch (Teensy-VID)")
    ap.add_argument("--flash", action="store_true", help="revb_bringup vorher flashen")
    ap.add_argument("--skip-rails", action="store_true", help="Spannungsabfrage überspringen")
    ap.add_argument("--no-2s", action="store_true", help="2S-Zweig ist nicht versorgt")
    ap.add_argument("--seconds", type=float, default=30.0, help="Dauer der Ruhemessung")
    ap.add_argument("--out", type=Path, default=FIRMWARE_DIR / "test_reports")
    a = ap.parse_args()

    rails = [] if a.skip_rails else check_rails(not a.no_2s)
    if any(r["ok"] is False for r in rails) and input("\nTrotz Fehler weiter? [j/N] ").lower() != "j":
        sys.exit(1)
    if not a.skip_rails:
        input("\nJetzt Teensy stecken, Strombegrenzung auf ca. 500 mA, USB verbinden. Enter ...")
    if a.flash:
        flash()
    else:
        # Der Teensy lässt sich über USB nicht neu starten, und revb_bringup wartet nach dem
        # Einschalten nur 4 s auf die Konsole. Deshalb neu einschalten und sofort verbinden.
        input("\n1S-Versorgung aus, Enter drücken, dann sofort wieder einschalten ...")

    with serial.Serial(find_port(a.port), 115200, timeout=0.5) as ser:
        lines, checks, overall = read_selftest(ser)
        st = stats(record_live(ser, a.seconds))

    notes = judge(st)
    if a.no_2s:
        notes.append("2S nicht versorgt: INA239- und 2S-Prüfungen schlagen erwartungsgemäß fehl")
    path = write_report(a.out, rails, checks, overall, st, notes, lines)
    failed = [c for c in checks if not c["ok"]]
    print(f"\nSelbsttest: {'ok' if overall else 'FEHLER'}, {len(failed)} Einzelprüfungen fehlgeschlagen")
    for n in notes:
        print("  ! " + n)
    print(f"Bericht: {path}")
    sys.exit(0 if overall and not failed else 1)


if __name__ == "__main__":
    main()
