# Tischtest und Kalibrierung Mainboard rev B1

Stand 2026-10-23, Ergebnis des Auftrags `Testauftrag_Agent_2026-10-23.md`. Die Platine ist noch
nicht gefertigt; alles hier ist so gebaut, dass es am ersten Tag auf der echten Platine läuft, und
ohne Hardware so weit geprüft, wie es geht (Abschnitt 6). Hardwarestand: `circuit.py` auf dem
Branch `claude/rev-b1`. Die Versuchsanleitungen mit Geräten, Aufbau, Sollwerten und Protokollfeldern
stehen in `Versuche_revB1.md`.

## 1. Was es gibt

| Teil | Ort | Aufgabe |
|---|---|---|
| Treiber | `lib/mainboard_revb/` | `Imu.h` (schmale IMU-Schnittstelle), `ICM42688` (mit Werksselbsttest), `BMP390`, `INA239`, neu `LIS3MDL`, `SHT40`, `ADXL375` (nur erkennen), `I2cRevB.h` |
| Kalibrierung | `lib/calstore/` | `CalData.h` (Block mit Version und CRC-32), `CalStore` (EEPROM-Emulat), `EllipsoidFit.h`, `AxisFit.h` |
| Testkonsole | `examples/revb_test/` | PlatformIO-Umgebung `revb_test`: Befehlsmenü über USB-Serial, feste Ausgabezeilen (`Proto.h`) |
| Inbetriebnahme | `examples/revb_bringup/` | Selbsttest aller Bausteine beim Start (jetzt auch LIS3MDL, SHT40, ADXL375), danach Messwerte |
| PC-Werkzeug | `tools/bench_test.py` | führt durch Versorgung, Flashen, Befehle und Rückfragen; Bericht in `test_reports/` |
| Tests ohne Hardware | `tools/test_bench_test.py`, `test/host/` | Parser der Konsolenzeilen (pytest), CRC/Ellipsoid/Achsen/NMEA (g++); laufen in der CI |

## 2. Versorgung und Lötbrücken

- **VIN des Teensy ist vom USB getrennt.** Der Teensy läuft nur bei versorgtem 1S-Zweig: Akku oder
  Labornetzteil (2–16 V, Strombegrenzung zuerst 100 mA, später ca. 500 mA) an **J_BAT1**, dazu **JP1**
  gebrückt oder der Schalter an **J_SW** (Pins 1–2). USB liefert dann nur die Daten. Der Teensy
  lässt sich über USB nicht neu starten: zum Neustart 1S aus und wieder ein.
- **2S-Zweig** (Servos, Rollmotor, Pyro, INA239-Busspannung): 2S-Akku oder Netzteil 6–8,4 V an
  **J_BAT2 (XT30)**, dazu **JP2** gebrückt oder der Schalter an J_SW (Pins 3–4). Ohne 2S melden
  die betroffenen Prüfungen `SKIP`, nie `FEHL`.
- **Testpunkte** (gegen GND): VBAT_PROT, VSYS_IN, 5V_SYS, VSERVO, 3V3_RF, 3V3_EXP, GND.
  Sollwerte stehen in `bench_test.py` (`RAILS`): 5V_SYS 4,85–5,15 V, 3V3_RF und 3V3_EXP 3,2–3,4 V,
  VBAT_PROT und VSERVO 6,0–8,6 V (nur mit 2S).
- **Pyro**: J_ARM mit dem Schlüsselschalter (oder Brücke) verbinden, an J_PYRO1/2 ein Glühlämpchen
  oder 2 Ω. **Nie eine Ladung.** Kanäle 3 und 4 sind DNP.

## 3. Ablauf Schritt für Schritt

1. **Ohne Teensy**: 1S anlegen (100 mA Begrenzung), Testpunkte messen. `python tools/bench_test.py`
   fragt die Werte ab und prüft die Bereiche. Erst wenn alles stimmt, Teensy stecken.
2. **Pinabgleich vor dem Flashen**:
   `python tools/check_board_pins.py <pfad/zu/circuit.py von claude/rev-b1>`
   (auf `main` liegt noch das alte Layout ohne Decoder; die CI meldet das als Warnung).
3. **Flashen**: `pio run -e revb_test -t upload` (oder `bench_test.py --flash`).
   `pio device monitor` zeigt das Banner mit Neustartursache, Kalibrierstatus und Menü, dann `READY`.
4. **Prüfungen ohne Bewegung** (`all`): Mux (alle 8 Kanäle), IMU (WHO_AM_I, Konfiguration, Datenrate,
   Ruhe, Werksselbsttest), Barometer 1 und 2, Magnetometer (mit Selbsttest), SHT40, ADXL375 (DNP →
   SKIP), INA239, Loop-Timing. `python tools/bench_test.py --skip-rails`.
5. **Mit 2S und Rückfragen** (`all full` oder einzeln): LEDs rot/grün/blau/weiß, Summer, Kamera-Trigger,
   Servos 1–4 (`servo <n> center|min|max|sweep|us <wert>`, nur im Fenster aus `Config.h`), Rollmotor
   (zwei 300-ms-Pulse 30 %, nFAULT), LoRa (Parameter lesen, `KARTONAUT PING` an die Bodenstation,
   RSSI), GPS (NMEA, Fix, Satelliten), SD (1 MiB schreiben, lesen, Datenrate).
   `python tools/bench_test.py --skip-rails --full`.
6. **Pyro** nur einzeln: `pyro 1 500` prüft 2S, ARM scharf und Durchgang, fragt `CONFIRM`, zündet
   nur nach dem Wort `JA`, Puls höchstens 1000 ms, misst den Sense-Pegel während des Pulses und
   danach. `bench_test.py --commands "pyro 1 500"`.
7. **Watchdog**: `watchdog` bedient einen 2-s-Watchdog 3 s lang und schaltet ihn ab;
   `watchdog fire` lässt ihn auslösen, nach dem Neustart meldet das Banner `TEST watchdog_reset OK`
   (`bench_test.py` verbindet neu).
8. **Kalibrierung** (`--cal` oder einzeln, Werte landen im RAM, `cal save` schreibt sie mit Version
   und CRC ins EEPROM-Emulat):
   - `cal gyro [s]` Nullpunkt und Rauschen in Ruhe mit Temperatur, Bewegung startet neu
   - `cal acc` sechs Lagen, Offset und Skalierung je Chip-Achse
   - `cal mag [s]` Platine drehen, Ellipsoid-Fit → Hard-Iron, Soft-Iron, Feldbetrag, Residuum, Oktanten
   - `cal axes` Spitze nach oben, dann +x nach oben (IMU), dann 20 s drehen (Magnetometer gegen
     die Drehrate, 24 rechtshändige Zuordnungen, Eindeutigkeit als Verhältnis)
   - `cal baro [s]` Bodenreferenz und Rauschen
   - `cal adc [kanal]` Teensy-Wert gegen Multimeter, Faktor je Kanal (Standard: 1S, 2S, ARM)
   - `cal ina` Offset ohne Last, Verstärkung gegen einen bekannten Strom
   - `cal servo <n>` Mitte und Grenzen interaktiv (`+ - ++ -- <zahl> c a b ok`)
   - `cal show | save | load | defaults | erase`
9. **Bericht**: `test_reports/bench_<datum>.md` und `.json` mit allen `TEST`- und `CAL`-Zeilen.

Die Flug-Firmware (`src/main.cpp`) lädt den Block beim Start; bei leerem oder beschädigtem Block
(CRC, Version, Layout) meldet sie `WARNUNG: Kalibrierung ...` und nimmt die Standardwerte.

## 4. Ausgabeformat

```
TEST <name> OK|FEHL|SKIP <detail>     eine Zeile je Prüfung
CAL <name> <wert> [<wert> ...]        ein Kalibrierwert je Zeile (Punkt als Dezimalzeichen)
END <befehl> OK|FEHL|SKIP             Befehl beendet
ASK <text> / WAIT <text> / CONFIRM <text>   Rückfrage (Zahl / Enter,n,q / JA)
INFO <text>, # <text>, READY
```

## 5. Was eine andere IMU bräuchte

`ImuDriver` (`lib/mainboard_revb/Imu.h`) hat `begin`, `whoAmI`, `dataReady`, `read`, `selfTest`,
`name`, `expectedWhoAmI`, `sampleRateHz`. Ein LSM6DSV16X-Treiber leitet davon ab und wird in
`examples/revb_test/Board.cpp` und `examples/revb_bringup/main.cpp` an einer Stelle eingehängt;
Konsole, Kalibrierung und Bericht bleiben unverändert. Der Treiber ist nicht geschrieben (laut
Auftrag erst nach Entscheidung).

## 6. Ohne Hardware geprüft, auf der Platine zu prüfen

Geprüft ohne Hardware:

- Pinabgleich `BoardRevB.h` gegen `circuit.py` auf `claude/rev-b1`: 39 Teensy-Pins, 8 Chip-Selects,
  8 Mux-Kanäle stimmen überein (die Pins sind gegenüber rev B unverändert).
- Alle neuen und geänderten Quellen kompilieren für den Teensy 4.1 (arm-none-eabi-g++ 13 mit dem
  Teensy-Core und den Bibliotheken SPI, Wire, EEPROM, Servo, SD, FastLED). Der vollständige
  PlatformIO-Build läuft in der CI (in dieser Session war die PlatformIO-Registry nicht erreichbar).
- `test/host/test_calstore.cpp`: CRC-32-Referenzwert, Versions-/Layout-/CRC-Prüfung, Standardwerte
  neutral; Ellipsoid-Fit findet Hard-Iron auf 3 mG und bildet die Proben auf eine Kugel ab;
  Achszuordnung findet eine vorgegebene Drehung mit Eindeutigkeit > 20.
- `test/host/test_nmea.cpp`: GGA/RMC, Prüfsumme, leere Felder.
- `tools/test_bench_test.py`: 32 Tests für `parse_line`, `Session`, Befehlssteuerung mit Rückfragen
  und Zeitlimit, Bericht, alter `[ OK ]`-Parser.

Erst auf der Platine prüfbar:

- Werksselbsttest des ICM-42688-P (Ablauf nach dem TDK-Referenztreiber, die Grenzwerte 50–150 %
  des Werkswerts sind aus der Dokumentation, nicht gemessen), Selbsttest des LIS3MDL (AN4602).
- Watchdog-Abschaltung (`wdEnd`, RTWDOG mit UPDATE-Bit) und Neustarterkennung über SRC_SRSR.
- LoRa-Ping: Antwort `PONG` und RSSI-Byte hängen von der Bodenstation und der Moduleinstellung
  (REG3 Bit 7) ab.
- SD-Datenrate, Servo-Fenster, Motorstrom, Pyro-Sense-Pegel während des Pulses.
- Mux-Einschwingzeit (5 µs plus eine verworfene Wandlung) bei 100 nF am Teiler.

## 7. Offene Fragen an Jan (nichts davon selbst „repariert“)

1. **Körperachse +x**: `cal axes` fragt „die Seite, die Körper +x sein soll, nach oben“. Welche Seite
   der Rakete ist +x (z. B. Richtung J_SERVO1/Yaw)? Die Lagen in `cal acc` sind nur grob beschrieben
   („lange Kante mit dem Teensy-USB“); mit der fertigen Platine passe ich die Texte an.
2. **Bodenstation**: Der LoRa-Ping sendet `KARTONAUT PING <n>\n` und erwartet eine Zeile mit `PONG`.
   Gibt es in `kartonaut-ground` schon ein Protokoll, dem ich folgen soll?
3. **RSSI**: Soll `revb_test` das RSSI-Byte (REG3 Bit 7) im Modul dauerhaft einschalten? Heute wird nur
   gelesen, nichts im Modul geändert.
4. **Flug-Firmware**: `src/` lädt den Kalibrierblock, nutzt ihn aber noch nicht (Breakout-Sensorpfad
   mit `Config.h`-Konstanten). Die Zuweisung gehört in den rev-B-Sensorpfad auf `firmware/flight-core`
   (`Sensors_revb.cpp`), wenn der zusammengeführt wird. Soll ich das dort anschließen?
5. **IMU-Wechsel** auf den LSM6DSV16X: Schnittstelle ist vorbereitet, Treiber wartet auf die Entscheidung.
6. **CI-Pinabgleich**: läuft weiter gegen `circuit.py` auf `main` (alter Stand, Warnung). Soll der
   Job auf `claude/rev-b1` zeigen, bis die Hardware zusammengeführt ist?
7. **Keine Pin-Abweichungen** zwischen `BoardRevB.h` und `circuit.py` (rev B1) gefunden.
