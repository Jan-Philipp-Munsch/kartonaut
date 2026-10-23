#!/usr/bin/env python3
"""Aufnahme für Versuch E02 (Servo -> Kardan auf dem Mainboard rev B1): schickt die tvc-Befehle an
die Testkonsole revb_test und schreibt die CSV eines Laufs in eine Datei.

    python tools/capture_tvc.py --out E02_w5652h_2S_yaw.csv --run Y --note "W5652H, Kardan v2, Yaw" --volt 7.9
    python tools/capture_tvc.py --out E02_both.csv --run B --amplitude 18 --frame-hz 100

Die Datei enthält alles ab "# kartonaut servo_ident v1" bis "# END" (bei B zwei Läufe) und ist
mit simulation/scripts/ident_servo.py (Branch experiments/servo-ident) auswertbar. Die Rumpf-IMU
steht als "#body,..."-Zeilen dazwischen; die Auswertung überliest sie. Strg+C bricht ab und
stellt die Servos auf Mitte. Braucht pyserial.
"""
import argparse
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial fehlt: pip install pyserial")


def find_port(port):
    if port:
        return port
    for p in list_ports.comports():
        if p.vid == 0x16C0:
            return p.device
    sys.exit("kein Teensy gefunden, --port angeben")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port")
    ap.add_argument("--out", required=True, help="Zieldatei (CSV)")
    ap.add_argument("--run", choices=["Y", "P", "B"], default="Y", help="Yaw, Pitch oder beide")
    ap.add_argument("--note", help="Notiz für den Dateikopf (Servo, Kardan, Datum)")
    ap.add_argument("--volt", type=float, help="Servospannung (Multimeter) für den Dateikopf")
    ap.add_argument("--amplitude", type=float, help="Amplitude in Servo-Grad um die Mitte")
    ap.add_argument("--frame-hz", type=int, help="Pulsrate der Servos (50 wie im Flug)")
    ap.add_argument("--cmd", action="append", default=[], help="weiterer tvc-Befehl vor dem Start, mehrfach möglich")
    ap.add_argument("--timeout", type=float, default=300.0)
    a = ap.parse_args()

    ser = serial.Serial(find_port(a.port), 115200, timeout=0.2)
    time.sleep(0.5)
    ser.reset_input_buffer()

    def send(line):
        ser.write((line + "\n").encode("utf-8"))
        time.sleep(0.2)

    send("")
    if a.note:
        send("tvc note " + a.note)
    if a.volt is not None:
        send(f"tvc volt {a.volt}")
    if a.amplitude is not None:
        send(f"tvc amp {a.amplitude}")
    if a.frame_hz is not None:
        send(f"tvc frame {a.frame_hz}")
    for c in a.cmd:
        send(c)
    send("tvc imu")
    send(f"tvc run {a.run}")

    expected = 2 if a.run == "B" else 1
    ends = rows = 0
    t0 = time.time()
    try:
        with open(a.out, "w", encoding="utf-8", newline="") as f:
            while True:
                raw = ser.readline()
                if not raw:
                    if time.time() - t0 > a.timeout:
                        print("Zeitüberschreitung ohne END", file=sys.stderr)
                        break
                    continue
                line = raw.decode("utf-8", errors="replace")
                if line.startswith(("#", "t_us")) or line[:1].isdigit():
                    f.write(line)
                if line.startswith(("#", "TEST", "INFO", "CAL", "END")):
                    if not line.startswith("#body"):
                        print(line.rstrip())
                    if line.startswith("# END"):
                        ends += 1
                        if ends >= expected:
                            break
                elif line[:1].isdigit():
                    rows += 1
                    if rows % 5000 == 0:
                        print(f"  {rows} Zeilen ...")
                if line.startswith("TEST tvc_run") and "SKIP" in line:
                    break
    except KeyboardInterrupt:
        send("S")
        print("abgebrochen, Servos auf Mitte")
    finally:
        ser.close()
    print(f"{rows} Messzeilen nach {a.out}")
    print("Auswertung (Branch experiments/servo-ident): python simulation/scripts/ident_servo.py " + a.out)


if __name__ == "__main__":
    main()
