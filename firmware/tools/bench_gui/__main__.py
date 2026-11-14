"""Werkbank: grafische Oberfläche für das Mainboard rev B1 am USB-Anschluss des Teensy.

Voraussetzung auf der Platine: die Testkonsole revb_test (pio run -e revb_test -t upload).
Die Oberfläche läuft im Browser, das Programm dahinter ist Python: es liest die serielle
Schnittstelle, wertet die Zeilen aus und schickt Befehle und Kalibrierwerte an den Teensy.

    pip install pyserial numpy
    cd firmware/tools
    python -m bench_gui                 # Teensy automatisch suchen
    python -m bench_gui --port COM7
    python -m bench_gui --sim           # ohne Hardware: simulierte Platine
"""
import argparse
import sys
import time
import webbrowser
from pathlib import Path

from .link import SIM_PORT, BoardLink
from .server import App, serve

FIRMWARE_DIR = Path(__file__).resolve().parent.parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m bench_gui", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serieller Port (z. B. COM7); ohne Angabe wird ein Teensy gesucht")
    ap.add_argument("--sim", action="store_true", help="simulierte Platine statt Hardware")
    ap.add_argument("--http-port", type=int, default=8765, help="Port der Oberfläche auf 127.0.0.1 (Standard 8765)")
    ap.add_argument("--no-browser", action="store_true", help="Browser nicht automatisch öffnen")
    ap.add_argument("--out", type=Path, default=FIRMWARE_DIR / "test_reports", help="Ordner für Berichte und Aufzeichnungen")
    a = ap.parse_args(argv)

    app = App(a.out)
    port = SIM_PORT if a.sim else a.port
    if port is None:
        teensy = [p["device"] for p in BoardLink.list_ports() if p["teensy"]]
        port = teensy[0] if len(teensy) == 1 else None
    if port:
        try:
            app.link.connect(port)
            print(f"Verbunden mit {port}")
        except Exception as e:
            print(f"Verbindung zu {port} fehlgeschlagen: {e}\nIn der Oberfläche einen Port wählen.")
    else:
        print("Kein (eindeutiger) Teensy gefunden: in der Oberfläche einen Port wählen oder mit --sim starten.")

    httpd, url = serve(app, a.http_port)
    print(f"Oberfläche: {url}\nBeenden mit Strg+C")
    if not a.no_browser:
        webbrowser.open(url)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        app.link.disconnect()
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
