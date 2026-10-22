"""Aufnahme für Experiment E01: Befehle an den Teensy (servo_ident) senden und die CSV speichern.

    python firmware/tools/capture_serial.py --port COM5 --out messung_sg90_5V.csv --run Y \\
        --note "SG90, alter Kardan, Yaw" --volt 5.0

Ohne --run wird nur mitgeschrieben (Befehle dann von Hand in einem zweiten Fenster, oder
--cmd mehrfach). Die Aufnahme endet mit der Zeile "# END" des letzten Laufs (bei B nach dem
zweiten) oder mit Strg+C. Braucht pyserial: pip install pyserial
"""
import argparse
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial fehlt: pip install pyserial")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="z. B. COM5 oder /dev/ttyACM0 (ohne Angabe: erster Teensy)")
    ap.add_argument("--out", required=True, help="Zieldatei (CSV)")
    ap.add_argument("--run", choices=["Y", "P", "B"], help="Lauf starten: Yaw, Pitch oder beide")
    ap.add_argument("--note", help="Notiz für den Dateikopf (Servo, Kardan, Datum)")
    ap.add_argument("--volt", type=float, help="Servospannung für den Dateikopf")
    ap.add_argument("--amplitude", type=float, help="Amplitude in Servo-Grad (A)")
    ap.add_argument("--frame-hz", type=int, help="Pulsrate der Servos (F)")
    ap.add_argument("--cmd", action="append", default=[], help="beliebiger weiterer Befehl vor dem Start, mehrfach möglich")
    ap.add_argument("--timeout", type=float, default=240.0, help="Abbruch nach s ohne END (Vorgabe 240)")
    args = ap.parse_args()

    port = args.port
    if not port:
        for p in list_ports.comports():
            if (p.vid == 0x16C0) or "Teensy" in (p.description or "") or "USB Serial" in (p.description or ""):
                port = p.device
                break
        if not port:
            sys.exit("kein Teensy gefunden, --port angeben. Gefunden: " + ", ".join(p.device for p in list_ports.comports()))

    ser = serial.Serial(port, 115200, timeout=0.2)
    time.sleep(0.5)
    ser.reset_input_buffer()

    def send(line):
        ser.write((line + "\n").encode())
        time.sleep(0.15)

    if args.note:
        send("N " + args.note)
    if args.volt is not None:
        send(f"V {args.volt}")
    if args.amplitude is not None:
        send(f"A {args.amplitude}")
    if args.frame_hz is not None:
        send(f"F {args.frame_hz}")
    for c in args.cmd:
        send(c)
    runs_expected = {"Y": 1, "P": 1, "B": 2}.get(args.run or "", 0)
    if args.run:
        send(args.run)

    ends = 0
    rows = 0
    t0 = time.time()
    try:
        with open(args.out, "w", encoding="utf-8", newline="") as f:
            while True:
                raw = ser.readline()
                if not raw:
                    if time.time() - t0 > args.timeout:
                        print("Zeitüberschreitung ohne END", file=sys.stderr)
                        break
                    continue
                line = raw.decode("utf-8", errors="replace")
                f.write(line)
                if line.startswith("#"):
                    print(line.rstrip())
                    if line.startswith("# END"):
                        ends += 1
                        if runs_expected and ends >= runs_expected:
                            break
                else:
                    rows += 1
                    if rows % 5000 == 0:
                        print(f"  {rows} Zeilen ...")
    except KeyboardInterrupt:
        send("S")
        print("abgebrochen, Servos auf Mitte")
    finally:
        ser.close()
    print(f"{rows} Messzeilen nach {args.out}")
    print("Auswertung: python simulation/scripts/ident_servo.py " + args.out)


if __name__ == "__main__":
    main()
