"""E22-400T22U (USB-Funkmodul am Laptop) passend zur Rakete einstellen.

    python tools/ground/e22_config.py --port COM5            lesen, bei Abweichung schreiben
    python tools/ground/e22_config.py --port COM5 --read     nur lesen

Adresse, Netz-ID, Kanal, Luftrate und Sendeleistung kommen aus firmware/src/Config.h (E22_*); die Rakete
stellt ihr E22-400T22S beim Start auf dieselben Werte (main.cpp, e22Configure). Zusätzlich schaltet das
Skript am USB-Modul das RSSI-Byte ein: es hängt an jedes empfangene Paket die Empfangsstärke, launch.py
zeigt sie an (--no-rssi schaltet es aus).

Vorher das Modul in den Konfigurationsmodus bringen: M0 = 0, M1 = 1 (Schalter bzw. Steckbrücken am Stick,
siehe Ebyte-Handbuch der gelieferten Version), dann einstecken. Danach zurück auf M0 = M1 = 0
(transparent) und neu einstecken. Im Konfigurationsmodus spricht das Modul immer 9600 Bd 8N1.
Registerlage nach Ebyte-Handbuch E22-400T22S; vor dem ersten Einsatz mit dem Datenblatt abgleichen.

Abhängigkeiten: Python 3.9+, pyserial.
"""
from __future__ import annotations

import argparse
import sys
import time

import kartonaut_radio as kr

AIR_RATES = {0: "0,3", 1: "1,2", 2: "2,4", 3: "4,8", 4: "9,6", 5: "19,2", 6: "38,4", 7: "62,5"}
POWERS = {0: "22 dBm", 1: "17 dBm", 2: "13 dBm", 3: "10 dBm"}


def describe(regs: bytes) -> str:
    return (f"Adresse 0x{regs[0]:02X}{regs[1]:02X}, Netz-ID {regs[2]}, Kanal {regs[5]} = {410.125 + regs[5]:.3f} MHz, "
            f"Luftrate {AIR_RATES[regs[3] & 7]} kbit/s, Leistung {POWERS[regs[4] & 3]}, "
            f"RSSI-Byte {'an' if regs[6] & 0x80 else 'aus'}")


def transact(ser, request: bytes, timeout: float = 1.0) -> bytes:
    ser.reset_input_buffer()
    ser.write(request)
    end = time.time() + timeout
    reply = b""
    while len(reply) < 12 and time.time() < end:
        reply += ser.read(12 - len(reply))
    return reply


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", required=True)
    ap.add_argument("--read", action="store_true", help="nur lesen, nichts schreiben")
    ap.add_argument("--no-rssi", action="store_true", help="kein RSSI-Byte anhängen")
    args = ap.parse_args(argv)

    import serial
    want = kr.e22_registers(kr.read_config_h(), rssi_byte=not args.no_rssi)
    with serial.Serial(args.port, 9600, timeout=0.2) as ser:
        reply = transact(ser, bytes([0xC1, 0x00, 0x09]))
        if len(reply) != 12 or reply[0] != 0xC1:
            print(f"Keine gültige Antwort ({reply.hex() or 'nichts'}). Steht das Modul auf M0 = 0, M1 = 1?")
            return 2
        have = reply[3:]
        print("Modul:  " + describe(have))
        print("Soll:   " + describe(want))
        if have == want:
            print("Register stimmen.")
            return 0
        if args.read:
            print("Abweichung (nur gelesen, nichts geschrieben).")
            return 1
        reply = transact(ser, bytes([0xC0, 0x00, 0x09]) + want)   # dauerhaft speichern
        if len(reply) == 12 and reply[0] == 0xC1 and reply[3:] == want:
            print("Geschrieben. Jetzt M0 = M1 = 0 setzen und neu einstecken.")
            return 0
        print(f"Schreiben fehlgeschlagen ({reply.hex() or 'keine Antwort'}).")
        return 2


if __name__ == "__main__":
    sys.exit(main())
