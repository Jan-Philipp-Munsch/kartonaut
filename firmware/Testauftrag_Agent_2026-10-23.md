# Auftrag an den Firmware-Agenten: Tischtest und Kalibrierung Mainboard rev B1

Stand 2026-10-23. Diesen Text als Prompt an die Session geben, die `firmware/` betreut.

---

Du übernimmst Inbetriebnahme, Funktionstest und Kalibrierung der Firmware für das **Mainboard rev B1**.
Die Platine ist noch nicht gefertigt. Bau alles so, dass es am ersten Tag auf der echten Platine läuft, und
teste ohne Hardware so viel wie möglich (Build, Simulation, Parser-Tests).

## Ausgangslage, bitte zuerst lesen

- **Hardware-Stand:** Branch `claude/rev-b1` (Worktree `.claude/worktrees/rev-b1`), Quelle der Wahrheit ist
  `hardware/mainboard/kicad/circuit.py`. `main` enthält noch ein älteres Layout (INA219, ohne 74HC138);
  das gilt nicht. Im rev-b1-Worktree arbeitet eventuell eine andere Session: dort nur lesen, nichts ändern.
- **Firmware:** `firmware/lib/mainboard_revb/` (BoardRevB.h, BusRevB, ICM42688, BMP390, INA239),
  `firmware/examples/revb_bringup/main.cpp` (Selbsttest), `firmware/tools/check_board_pins.py` (Pinabgleich
  gegen circuit.py), `firmware/tools/bench_test.py` (geführter Tischtest am PC, liest die Ausgabe von
  revb_bringup).
- **Neu in rev B1 und in der Firmware noch nicht enthalten:** Magnetometer LIS3MDL (I²C 0x1E), Feuchte und
  Temperatur SHT40 (I²C 0x44), ADXL375 ±200 g als DNP-Footprint (I²C 0x53), Schiene 3V3_EXP. Prüfe mit
  `check_board_pins.py`, ob BoardRevB.h noch zu circuit.py auf `claude/rev-b1` passt.
- **IMU kann sich ändern:** Zur Diskussion steht der Wechsel vom ICM-42688-P auf den LSM6DSV16X (gleiches
  Gehäuse LGA-14, Rakete unter 4 g). Kapsle die IMU deshalb hinter einer schmalen Schnittstelle
  (`begin`, `read`, `whoAmI`, Selbsttest), damit ein zweiter Treiber ohne Umbau des Rests dazukommt.
  Schreib den LSM6DSV16X-Treiber noch nicht, außer Jan entscheidet das.

## Versorgung am Tisch

- **VIN ist am Teensy vom USB getrennt.** Der Teensy läuft nur, wenn der 1S-Zweig versorgt ist: Akku oder
  Labornetzteil an J_BAT1 (der TPS63070 nimmt 2–16 V), dazu JP1 gebrückt oder der Schalter an J_SW
  gesteckt. USB liefert dann nur die Daten. Der Teensy lässt sich über USB nicht neu starten.
- **Ohne 2S** (XT30 plus JP2 oder Schalter) gibt es keine Servos, keinen Rollmotor, kein Pyro und keine
  INA239-Busspannung. Jeder Test muss ohne 2S sauber „übersprungen“ melden statt fehlzuschlagen.
- **Testpunkte rev B1:** VBAT_PROT, VSYS_IN, 5V_SYS, VSERVO, 3V3_RF, 3V3_EXP, GND.

## Sicherheit, nicht verhandelbar

- Pyro-Ausgänge nur mit Glühlämpchen oder 2-Ω-Widerstand als Last, **nie mit Ladung**. Zünden nur nach
  ausdrücklicher Bestätigung auf der Konsole und bei ARM_SENSE scharf, Puls ≤ 1 s, danach sofort tief.
- Beim Start immer zuerst die sicheren Zustände wie in `safeOutputs()`: Pyro tief, DRV8833 schlafend,
  Servos ohne Puls, alle Chip-Selects hoch.
- Servos nur innerhalb der Grenzen aus `Config.h` bewegen, Motor nur kurze Pulse, nFAULT überwachen.

## Aufgaben

1. **Abgleich:** BoardRevB.h und die Treiber auf den Stand von circuit.py (`claude/rev-b1`) bringen, LIS3MDL
   und SHT40 als Treiber ergänzen, ADXL375 nur erkennen (DNP). Der Selbsttest in revb_bringup prüft alle
   Bausteine einschließlich der neuen.
2. **Testmodus:** Eine Testumgebung mit einem Befehlsmenü über USB-Serial, z. B. als neuer PlatformIO-Env
   `revb_test` oder als Erweiterung von revb_bringup. Je Funktion ein Befehl mit klarem OK, FEHL oder
   ÜBERSPRUNGEN:
   - Analogmux: alle 8 Kanäle, Akkuspannungen, ARM, Durchgang Pyro 1–4
   - IMU, Barometer (1 und 2, falls bestückt), Magnetometer, SHT40, INA239 einschließlich Strom unter Last
   - LEDs (rot, grün, blau, weiß), Summer, Kamera-Auslöser
   - Servos einzeln: Mitte, ±Grenze, langsamer Durchlauf
   - Rollmotor: kurze Pulse in beide Richtungen, nFAULT
   - Pyro mit Lämpchen wie oben
   - LoRa: Konfiguration lesen, Ping zur Bodenstation mit RSSI
   - GPS: NMEA, Fix, Satelliten
   - SD-Karte: schreiben, lesen, Datenrate
   - Loop-Timing und Watchdog
3. **Kalibrierung**, jeweils geführt über die Konsole:
   - Gyro-Offset in Ruhe mit Temperatur, über eine einstellbare Dauer
   - Beschleunigung mit 6 Lagen, Offset und Skalierung je Achse
   - Magnetometer: Hard- und Soft-Iron per Ellipsoid-Fit, während man die Platine dreht
   - Achszuordnung IMU und Magnetometer zum Raketenkörper
   - Barometer: Bodenreferenz und Rauschen
   - ADC-Teiler je Kanal gegen einen Wert, den der Nutzer mit dem Multimeter misst
   - INA239: Offset ohne Last, Verstärkung gegen eine bekannte Last
   - Servo-Mitte und -Grenzen (Trimm)

   Die Werte landen mit Versionsnummer und CRC im EEPROM-Emulat. Die Flug-Firmware lädt sie beim Start und
   fällt bei falscher CRC auf Standardwerte zurück, mit Warnung im Log.
4. **Maschinenlesbare Ausgabe:** Jede Prüfung und jeder Kalibrierwert als eigene Zeile in einem festen
   Format, z. B. `TEST <name> OK|FEHL|SKIP <detail>` und `CAL <name> <werte>`. Erweitere
   `firmware/tools/bench_test.py` so, dass es diese Zeilen auswertet, die Befehle nacheinander anstößt und
   den Bericht schreibt (bisher wertet es das `[ OK ]`/`[FEHL]`-Format von revb_bringup aus). Teste die
   Parser mit aufgezeichneten Beispielzeilen, ohne Hardware.
5. **CI:** Alle PlatformIO-Umgebungen müssen weiter bauen, auch die neuen, und die Simulationstests müssen
   grün bleiben (`.github/workflows/ci.yml`). Die Parser-Tests für bench_test.py kommen in die CI.

## Arbeitsweise und Ergebnis

- Eigener Branch von `main` (z. B. `firmware/revb1-test`), kleine Commits, Commit-Texte auf Deutsch wie im
  Repo. Keine Änderungen unter `hardware/`.
- Am Ende ein kurzer Bericht in `firmware/README.md` oder einer eigenen Datei: Ablauf des Tischtests Schritt
  für Schritt (welche Versorgung, welche Lötbrücken, welche Befehle), was ohne Hardware geprüft ist und was
  erst auf der Platine geprüft werden kann.
- Offene Hardwarefragen (zum Beispiel Pin-Abweichungen zu circuit.py) nicht selbst „reparieren“, sondern
  auflisten und Jan fragen.
