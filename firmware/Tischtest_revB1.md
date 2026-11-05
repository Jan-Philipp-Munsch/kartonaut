# Tischtest und Kalibrierung Mainboard rev B1

Stand 2026-11-05: Platine von JLCPCB bestückt, IMU-Treiber LSM6DSV16X und Bestückungsliste neu
(Abschnitt 3a). Zuerst 2026-10-23, Ergebnis des Auftrags `Testauftrag_Agent_2026-10-23.md`. Ohne
Hardware so weit geprüft, wie es geht (Abschnitt 6). Hardwarestand: `hardware/mainboard/kicad/circuit.py`
(auf `main` mit CS-Decoder). Die Versuchsanleitungen mit Geräten, Aufbau, Sollwerten und
Protokollfeldern stehen in `Versuche_revB1.md`.

Bestückt geliefert und geprüft wird: IMU **LSM6DSV16X** (U4), Barometer **BMP388** (U5, Chip-ID 0x50),
LIS3MDL (U16), SHT40 (U18). Noch nicht bestückt: **INA239** (U6, nachbestellt, ca. 11.11.), **LoRa E22**
(U10), **GPS** an J11; DNP: Baro 2 (U15), ADXL375 (U17). Diese Teile melden `NICHT_ERKANNT`, nicht `FEHL`.

## 1. Was es gibt

| Teil | Ort | Aufgabe |
|---|---|---|
| Treiber | `lib/mainboard_revb/` | `Imu.h` (schmale IMU-Schnittstelle), `LSM6DSV16X` (rev B1, Selbsttest nach AN5763), `ICM42688` (ältere Platinen, Werksselbsttest), `ImuAuto.h` (Wahl nach WHO_AM_I), `FitRevB.h` (Bestückungsliste), `BMP390` (auch BMP388), `INA239`, `LIS3MDL`, `SHT40`, `ADXL375` (nur erkennen), `I2cRevB.h` |
| Kalibrierung | `lib/calstore/` | `CalData.h` (Block mit Version und CRC-32), `CalStore` (EEPROM-Emulat), `EllipsoidFit.h`, `AxisFit.h` |
| Testkonsole | `examples/revb_test/` | PlatformIO-Umgebung `revb_test`: Befehlsmenü über USB-Serial, feste Ausgabezeilen (`Proto.h`) |
| Inbetriebnahme | `examples/revb_bringup/` | Selbsttest aller Bausteine beim Start (jetzt auch LIS3MDL, SHT40, ADXL375), danach Messwerte |
| PC-Werkzeug | `tools/bench_test.py` | führt durch Versorgung, Flashen, Befehle und Rückfragen; Bericht in `test_reports/` |
| Tests ohne Hardware | `tools/test_bench_test.py`, `test/host/` | Parser der Konsolenzeilen (pytest), CRC/Ellipsoid/Achsen/NMEA (g++); laufen in der CI |

## 2. Versorgung und Lötbrücken

- **VIN-VUSB-Brücke auf dem Teensy bleibt geschlossen** (B11, `hardware/mainboard/README.md`): D1 trennt
  5V_SYS vom USB. Der Teensy (und mit seinem 3,3-V-Regler IMU, Barometer, Magnetometer, SHT40, Decoder
  und Mux) läuft daher auch am USB allein; 5V_SYS, 3V3_RF, 3V3_EXP, LEDs, Summer und LoRa brauchen aber
  den 1S-Zweig: Akku oder Labornetzteil (2–16 V, Strombegrenzung zuerst 100 mA, mit Teensy ca. 300 mA)
  an **J_BAT1**, dazu **JP1** gebrückt oder der Schalter an **J_SW** (Pins 1–2).
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
2. **Pinabgleich vor dem Flashen**: `python tools/check_board_pins.py` (vergleicht `BoardRevB.h` mit
   `hardware/mainboard/kicad/circuit.py`; `main` hat seit dem Merge den Decoder, Stand 05.11.:
   42 Teensy-Pins, 8 Chip-Selects, 8 Analogkanäle stimmen überein).
3. **Flashen**: `pio run -e revb_test -t upload` (oder `bench_test.py --flash`).
   `pio device monitor` zeigt das Banner mit Neustartursache, Kalibrierstatus und Menü, dann `READY`.
4. **Prüfungen ohne Bewegung** (`all`): Mux (alle 8 Kanäle), IMU (LSM6DSV16X: WHO_AM_I 0x70,
   Konfiguration, Datenrate 960 Hz, Ruhe, Selbsttest), Barometer 1 (BMP388) und 2 (DNP →
   `NICHT_ERKANNT`), Magnetometer (mit Selbsttest), SHT40, ADXL375 (DNP → `NICHT_ERKANNT`), INA239
   (bis zum Einlöten `NICHT_ERKANNT`), Loop-Timing. `python tools/bench_test.py --skip-rails`.
5. **Mit 2S und Rückfragen** (`all full` oder einzeln): LEDs rot/grün/blau/weiß, Summer, Kamera-Trigger,
   Servos 1–4 (`servo <n> center|min|max|sweep|us <wert>`, nur im Fenster aus `Config.h`), Rollmotor
   (zwei 300-ms-Pulse 30 %, nFAULT), LoRa (Parameter lesen, `KARTONAUT PING` an die Bodenstation,
   RSSI; ohne Modul `NICHT_ERKANNT`), GPS (NMEA, Fix, Satelliten; ohne Modul `NICHT_ERKANNT`),
   SD (1 MiB schreiben, lesen, Datenrate).
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

## 3a. Bestückungsliste: fehlende Teile ein- und austragen

Was auf der Platine fehlt, steht in `lib/mainboard_revb/FitRevB.h` auf „aus“. Ein Teil auf „aus“ wird
nicht als Fehler gewertet und blockiert nichts: die Prüfung meldet

```
TEST ina_id NICHT_ERKANNT nicht bestückt oder keine Antwort (Bestückungsliste: fit ina off)
END ina NICHT_ERKANNT
```

Ein Teil auf „an“, das nicht antwortet, ist `FEHL` (mit dem Hinweis „nicht bestückt? dann 'fit … off'“).
Antwortet ein Teil auf „aus“ trotzdem, hängt die Zeile „antwortet aber: mit 'fit on' prüfen“ an.
Kein Teil bricht den Lauf ab; `all` läuft immer bis `timing` durch.

| Teil | Name | Standard (05.11.2026) | Prüfungen |
|---|---|---|---|
| IMU LSM6DSV16X (U4) | `imu` | an | `imu`, `cal gyro/acc/axes` |
| Barometer BMP388 (U5) | `baro` | an | `baro` (`baro1`), `cal baro` |
| Barometer 2 (U15, DNP) | `baro2` | aus | `baro` (`baro2`) |
| INA239 (U6, nachbestellt) | `ina` | aus | `ina`, `ina load`, `cal ina` |
| LIS3MDL (U16) | `mag` | an | `mag`, `cal mag` |
| SHT40 (U18) | `sht` | an | `sht` |
| ADXL375 (U17, DNP) | `adxl` | aus | `adxl` |
| LoRa E22 (U10) | `lora` | aus | `lora`; M0/M1/AUX bleiben im Ruhezustand, Serial8 aus |
| GPS an J11 | `gps` | aus | `gps` (ohne 10 s Wartezeit) |

Umschalten in der Konsole (gilt bis zum Neustart):

```
fit                 Liste zeigen: INFO bestückt: imu an, baro an, baro2 aus, ina aus, ...
fit ina on          INA239 eingelötet -> ina wird wieder geprüft, fehlende Antwort = FEHL
fit baro off        BMP388 aus dem Test nehmen -> baro1 NICHT_ERKANNT
fit lora on         E22 eingelötet (treibt M0 = M1 = 0)
fit all on | fit all off | fit default
```

Vom PC aus: `python tools/bench_test.py --skip-rails --fit "ina=on,lora=on"` schickt die `fit`-Befehle vor
der Befehlsfolge. Dauerhaft (auch für `revb_bringup`, das keine Konsole hat) beim Bauen, z. B. in
`platformio.ini` unter `[env:revb_test]`: `build_flags = ${env.build_flags} -DREVB_FIT_INA239=1`
(Makros `REVB_FIT_IMU`, `_BARO`, `_BARO2`, `_INA239`, `_MAG`, `_SHT`, `_ADXL`, `_LORA`, `_GPS`).
`revb_bringup` zeigt nicht bestückte Teile als `[ -- ] … nicht bestückt oder keine Antwort (REVB_FIT_…=0)`
und zählt sie nicht zum Ergebnis.

Erwartete Ausgabe von `all` mit den Standardwerten (INA239, LoRa, GPS fehlen; nur 1S):

```
TEST imu_whoami OK 0x70 soll 0x70 (LSM6DSV16X)
TEST imu_config OK Flugkonfiguration zurückgelesen
TEST imu_rate OK 960 Hz soll 960
TEST imu_rest OK |a| 9.80 m/s2 a=[...] |w| 0.30 dps T 26.0 C
TEST imu_selftest_gyro OK Antwort ... dps, Grenzen 150..700, Offset ...
TEST imu_selftest_acc OK Antwort ... g, Grenzen 0.050..1.700
TEST baro1 OK Chip-ID 0x50 (BMP388), 98712 Pa, 25.1 C
TEST baro2 NICHT_ERKANNT nicht bestückt oder keine Antwort (Bestückungsliste: fit baro2 off)
TEST mag_whoami OK ...   TEST sht_serial OK ...
TEST adxl_present NICHT_ERKANNT nicht bestückt oder keine Antwort (Bestückungsliste: fit adxl off)
TEST ina_id NICHT_ERKANNT nicht bestückt oder keine Antwort (Bestückungsliste: fit ina off)
TEST timing_loop OK ...
END all SKIP                             (SKIP wegen der 2S-Zeilen der Mux; mit 2S: NICHT_ERKANNT)
```

`bench_test.py` zählt die Zeilen getrennt („… FEHL, … SKIP, … nicht bestückt“), der Bericht schreibt
„nicht bestückt“, der Rückgabewert ist 0 wie bei OK und SKIP. Rangfolge für das Gesamtergebnis:
FEHL vor SKIP vor NICHT_ERKANNT vor OK.

## 4. Ausgabeformat

```
TEST <name> OK|FEHL|SKIP|NICHT_ERKANNT <detail>   eine Zeile je Prüfung
CAL <name> <wert> [<wert> ...]        ein Kalibrierwert je Zeile (Punkt als Dezimalzeichen)
END <befehl> OK|FEHL|SKIP|NICHT_ERKANNT           Befehl beendet
ASK <text> / WAIT <text> / CONFIRM <text>   Rückfrage (Zahl / Enter,n,q / JA)
INFO <text>, # <text>, READY
```

## 5. IMU: LSM6DSV16X und ICM-42688-P

`ImuDriver` (`lib/mainboard_revb/Imu.h`) hat `begin`, `whoAmI`, `dataReady`, `read`, `selfTest`,
`name`, `expectedWhoAmI`, `sampleRateHz`. Davon leiten `LSM6DSV16X` (rev B1) und `ICM42688` ab.
`ImuAuto` (`ImuAuto.h`) liest beim Start WHO_AM_I (0x70 in Register 0x0F → LSM6DSV16X, 0x47 in 0x75 →
ICM-42688-P) und reicht alles an den gewählten Treiber weiter; `revb_test`, `revb_bringup` und die
Flug-Firmware (`teensy41_revb`) benutzen ihn. Antwortet keiner, bleibt der LSM6DSV16X gewählt und
`imu_whoami` meldet „0x.. soll 0x70“.

LSM6DSV16X: SPI Modus 3, 8 MHz, ±2000 °/s (70 mdps/LSB), ±16 g (0,488 mg/LSB), 960 Hz High-Performance
(das ODR-Raster hat keine 1000 Hz), BDU und Adress-Inkrement, INT1 = Gyro-Daten bereit, Temperatur
256 LSB/K um 25 °C. Der Selbsttest hat keinen Werkswert: `imu_selftest_*` zeigt „Grenzen“ statt
„Verhältnis“. Konsole, Kalibrierung und Bericht sind unverändert.

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
- `tools/test_bench_test.py`: 39 Tests für `parse_line` (auch `NICHT_ERKANNT` und LSM6DSV16X-Zeilen),
  `Session`, `--fit`, Befehlssteuerung mit Rückfragen und Zeitlimit, Bericht, alter `[ OK ]`/`[ -- ]`-Parser.
- 05.11.2026: `pio run -e revb_test`, `-e revb_bringup`, `-e teensy41_revb`, `-e teensy41` bauen ohne Fehler.

Erst auf der Platine prüfbar:

- LSM6DSV16X (Stellen mit `PRUEFEN` in `LSM6DSV16X.cpp`): ODR-Code 0x09 = 960 Hz (zeigt `imu_rate`),
  FS-Codes (±2000 °/s in CTRL6, ±16 g in CTRL8; `imu_rest` muss |a| ≈ 9,8 m/s² zeigen), Selbsttest-Ablauf
  und Grenzen (Accel 50–1700 mg bei ±4 g, Gyro 150–700 °/s bei ±2000 °/s, 60 Hz, 100 ms, 5 Sätze) gegen
  DS13510/AN5763, Vorzeichen der Achsen und INT1-Pegel an Pin 4.
- Werksselbsttest des ICM-42688-P (nur ältere Platinen), Selbsttest des LIS3MDL (AN4602).
- LoRa-Pins ohne Modul: M0/M1/AUX mit Pull-down im Teensy, nichts getrieben (Multimeter: ca. 0 V).
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
5. ~~IMU-Wechsel~~ erledigt 05.11.: LSM6DSV16X ist bestückt, Treiber `LSM6DSV16X` mit Wahl nach WHO_AM_I.
6. ~~CI-Pinabgleich~~ erledigt: `main` hat den Decoder, `check_board_pins.py` meldet keine Abweichung.
7. **Keine Pin-Abweichungen** zwischen `BoardRevB.h` und `circuit.py` (rev B1) gefunden.
