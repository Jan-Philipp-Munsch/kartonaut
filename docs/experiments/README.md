# Experimente

Vorgefertigte Versuche: Jan baut auf und fährt sie, die Auswertung läuft als Skript und liefert
Zahlen, die direkt in Firmware (`Config.h`), Simulation (`tvcsim/params.py`) oder CAD gehören.
Jedes Experiment hat eine Nummer, eine Anleitung hier, einen Sketch unter `firmware/examples/`
(eigene PlatformIO-Umgebung) und ein Auswerteskript unter `simulation/scripts/`.

| # | Experiment | Sketch | Auswertung | Ergebnis landet in | Stand |
|---|---|---|---|---|---|
| E01 | [Servo → Kardan: Übertragungsfunktion](E01_servo_ident.md) | `servo_ident` | `ident_servo.py` | `ServoParams`, `SERVO_*_GAIN`, Befund 13 | bereit, nicht gefahren |
| E02 | TVC-Prüfstand: geschlossener Regelkreis mit Propeller (`cad/testrig.py`) | – | – | `PY_K*`, Meilenstein M4 | offen |
| E03 | Funkreichweite E22 (S3 in `Schnittstellen_Bodensystem_2026-10-22.md`) | – | – | LoRa-Parameter | offen |
| E04 | Ausstoßtest Kolben und Fallschirm | – | – | Ladungsmenge, Checkliste | offen |

Ablauf für jedes Experiment:

1. Anleitung lesen, Aufbau nach der Checkliste, Sketch flashen (`pio run -e <name> -t upload`).
2. Fahren, Messdatei mit sprechendem Namen speichern (`<experiment>_<was>_<datum>.csv`).
3. Datei an Claude geben oder selbst auswerten (`python simulation/scripts/<skript> <datei>`).
4. Ergebnis mit Datum in die Zieldatei eintragen und in `PROJECT.md` §7 vermerken.

Messdaten liegen nicht im Repo (`simulation/out/` ist ausgeschlossen), außer sie sind klein und
werden als Referenz gebraucht wie `simulation/data/servo_step_response.csv` von 2025.
