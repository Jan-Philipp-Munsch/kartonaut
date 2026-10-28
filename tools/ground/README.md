# Laptop-Werkzeug für den Motorstart an Bord

Seit dem 27.10.2026 zündet *Kartonaut 1* seinen Motor selbst über Pyro-Kanal 1. Bodenstation ist ein
Laptop mit einer **Funkbrücke aus Raspberry Pi Pico und E22-400T22S** am USB (`docs/Plan_Bordzuendung_2026-10-27.md`). Protokoll:
`firmware/src/Telemetry.h`, Ablauf am Pad: Bauanleitung §6.1.

| Datei | Zweck |
|---|---|
| `launch.py` | Telemetrie anzeigen, Kommandos senden, ARM und LAUNCH mit MAC, Heartbeat, ABORT mit der Leertaste; schreibt alles als CSV nach `logs/` |
| `bridge_pico/` | Firmware der Funkbrücke (PlatformIO, Raspberry Pi Pico): reicht Rahmen durch, stellt ihr E22 ein; Verdrahtung in [`bridge_pico/README.md`](bridge_pico/README.md) |
| `kartonaut_radio.py` | Protokoll in Python: Rahmen, CRC, Parser, Dekoder, MAC, `Config.h` lesen |
| `test_kartonaut_radio.py` | Tests gegen `firmware/test/data/radio_vectors.csv` (dieselben Bytes prüfen die nativen Firmware-Tests) |
| `secrets.example.json` | Vorlage für `secrets.json` (nicht im Repo) |

```bash
pip install pyserial
python tools/ground/launch.py --new-key                 # einmal: secrets.json und firmware/src/Secrets.h
pio run -d tools/ground/bridge_pico -t upload          # einmal: Funkbrücke flashen
python tools/ground/launch.py --port COM5 --config      # einmal: E22 der Brücke wie die Rakete einstellen
python tools/ground/launch.py --port COM5               # am Startplatz
python -m pytest -q tools/ground                        # Tests (laufen auch in der CI)
```

Nach `--new-key` die Firmware neu bauen und flashen, damit die Rakete den Schlüssel kennt. Ohne
`Secrets.h` baut sie mit `LAUNCH_ENABLED = false` und verweigert ARM.

## Tasten in `launch.py`

| Taste | Kommando |
|---|---|
| `p` | PING |
| `c` | CALIBRATE (Nullpunkte neu, nur in SAFE/PAD_READY) |
| `r` | PAD_READY (danach testen sich die Kardanservos 1,5 s) |
| `a` | ARM: holt per PING die nonce, sendet ARM mit MAC; bei Ablehnung stehen die fehlenden Vorbedingungen da |
| `l` | LAUNCH: erst nach Eingabe von `START` und Enter; Countdown 5 s |
| `s` | SAFE |
| Leertaste | ABORT, jederzeit, fünfmal gesendet |
| `q` | Ende |

Ab ARM sendet das Skript den Heartbeat mit 4 Hz, solange die Rakete ARMED oder COUNTDOWN meldet. Fehlt er
länger als 1 s (Laptop zu, USB-Kabel der Brücke abgezogen), geht die Rakete selbst nach SAFE.

## Sicherheit des Protokolls

ARM und LAUNCH tragen die ersten 8 Byte von HMAC-SHA256(Schlüssel, Typ ‖ seq ‖ nonce ‖ Raketen-ID). Die
nonce ist eine Zufallszahl aus dem TRNG der Rakete und gilt genau einmal, auch bei einem abgelehnten
Befehl. Ein anderes 433-MHz-Gerät, ein Bitfehler, den die CRC nicht findet, oder ein aufgezeichneter Befehl
kann deshalb weder schärfen noch zünden. ABORT hat keinen MAC, damit ein Abbruch nie an der
Authentisierung scheitert. Zusätzlich trennt der Arming-Schalter an der Rakete den Zündstrom in Hardware.
