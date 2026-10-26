# Flug-Firmware

PlatformIO-Projekt für den Teensy 4.1. Die Firmware liest die Sensoren, schätzt Lage und
Höhe, führt den Flugzustandsautomaten, regelt den Schubvektor, zündet die Bergung, funkt
Telemetrie und loggt jeden Durchlauf auf die SD-Karte. Die Regler sind in `Config.h`
abgeschaltet, bis der Prüfstand (Experiment E02) sie freigibt. Nichts davon ist bisher am
Gerät gelaufen; die Logik ist in den nativen Tests geprüft (`pio test -e native`, 42 Tests).
Für *Kartonaut 1* (Modulbauweise Stand 2b/2c) entfällt der Rollmotor; der Rollregler bleibt aus, die Lage
kommt als Quaternion aus dem Gyro (`Attitude.*`). Masse 0,705 kg und Hebelarm 0,190 m aus
`cad/mass_stand2b.md` gehören nach dem Wiegen in `Config.h` (`MASS_KG`, `MOMENT_ARM_M`), und mit ihnen
kleinere Gewinne (Kp 2, Ki 1, Kd 0,45 statt 5, 0 und 1, `docs/Gewicht_und_Landung_2026-10-23.md` §4b;
I-Anteil erst ab der Starterkennung); der Fallschirm-Servo an `J_SERVO3` löst die CO₂-Kapsel aus.

```bash
pio run                        # Flug-Firmware für den Breakout-Aufbau bauen
pio run -e teensy41_revb       # dieselbe Firmware für das Mainboard rev B
pio run -t upload              # flashen (teensy-cli)
pio device monitor             # 115200 Bd, Teleplot-kompatibel; ? c r a s als Befehle
pio test -e native             # 42 Tests ohne Hardware (oder: python tools/run_native_tests.py)
pio run -e i2c_scanner -t upload   # einen Test-Sketch flashen
```

## Module

| Datei | Aufgabe | ohne Hardware testbar |
|---|---|---|
| `src/main.cpp` | `setup()` und die 100-Hz-Schleife: Sensoren, Kalibrierung, Lage, Kalman, Zustandsautomat, Regler, Pyro, Telemetrie, Log, Zustandsspeicher, Watchdog | – |
| `src/Config.h` | Alle Pins (je Board), physikalischen Parameter, Reglergewinne, Schwellen des Automaten, Pyro, Telemetrie, Watchdog, Schalter | – |
| `src/Sensors.h` | Schnittstelle: `SensorSample` (spezifische Kraft, Drehrate im Körpersystem, Druck, Höhe, Akkus, ARM, Durchgang), Kalibrierung | – |
| `src/Sensors_breakout.cpp` | Rückende Breakouts: ICM-20948 roh ohne DMP (±4 g, ±2000 °/s, DLPF 50 Hz), BMP280, INA219. Kein ARM, kein Durchgang: Pyro gesperrt. | – |
| `src/Sensors_revb.cpp` | Rückende Mainboard rev B: ICM-42688-P, BMP390, INA239 an SPI1, Akkus/ARM/Durchgang über die Mux (`lib/mainboard_revb/`) | – |
| `src/Attitude.*` | Lage als Gyro-Quaternion, Init aus der Beschleunigung auf dem Pad, Oben-Vektor, Kippwinkel in Servoachsen, Rollwinkel | ✅ |
| `src/KalmanZ.*` | 2-Zustands-Kalman (Höhe, Vertikalgeschwindigkeit) mit Beschleunigung als Eingang und Barometer als Messung | – |
| `src/FlightState.*` | Flugzustandsautomat SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED, ABORT; Ereignisse mit Zeitstempel | ✅ |
| `src/ControlLaw.*` | Reglergleichungen Pitch/Yaw (PID, Moment → TVC-Winkel → Servo-Grad, Fenster) und Roll; identisch zu `tvcsim` | ✅ (SIL) |
| `src/Control.*` | Servos als 16-Bit-PWM mit `SERVO_FRAME_HZ`, H-Brücke, Fallschirm-Servo | – |
| `src/Pyro.*` | Zündlogik je Kanal: Zustand, Flugzeit, ARM, Durchgang; Puls, Abbruch bei Durchgangsverlust, Reservekanal (Fallschirm) oder Anzünder des Landemotors | ✅ |
| `src/LandingBurn.*`, `src/ThrustCurveE12.h` | Zündentscheidung für das Landebrennen: Aufsetzkosten aus einer 1D-Simulation der E12-Kurve mit Bodenkontakt, Zündung im Minimum (Port von `tvcsim.landing`) | ✅ |
| `src/ThrottleLaw.*` | Schubdrossel (Scout-F-Pads): Zündung mit Reserve, Schubschätzung in der Spitze, zeitbasierte Führung auf Höhe 0 zum Brennschluss, Schubabbruch beim Aufsetzen (Port von `tvcsim.throttle`) | ✅ |
| `src/Telemetry.*`, `src/Crc16.h` | Funkprotokoll (Rahmen, TLM/EVT/ACK, Kommandos, Parser, CRC-16/CCITT) | ✅ |
| `src/StateMemory.*`, `src/StateStore.*` | Zustandsspeicher (Magic + CRC) und seine Ablage in DMAMEM für den Neustart im Flug | ✅ / – |
| `src/Watchdog.*` | RTWDOG mit `WDT_TIMEOUT_MS`, Reset-Ursache | – |
| `src/SDLogger.*` | Binär-Logger mit Vorallokation, Seitenpuffer, slack-bewusstem Flush/Sync, TMP-Recovery und CSV-Export | – |
| `src/Timing.*` | Nicht blockierender Loop-Takt auf `micros()`, gemessenes dt, Slack bis zur Deadline, Overrun-Warnung | – |
| `src/Indicators.*` | WS2812B und Summer: Start, Zustandsfarbe, Warnung | – |
| `src/MathTypes.h` | `Vec3`, `Quaternion`, Vektorrotation (ohne Arduino) | ✅ |

## Ablauf im Flug

1. **Einschalten → SAFE.** Die Firmware misst 4 s den Gyro-Nullpunkt und den Bodendruck
   (Rakete ruhig halten; Bewegung über 2 °/s startet die Messung neu) und initialisiert die
   Lage aus der Schwerkraft. Blau.
2. **Kommando PAD_READY** (Bodenstation oder `r` auf USB) → **PAD_READY**, nur wenn kalibriert
   und IMU und Barometer da sind. Log beginnt. Grün. `CALIBRATE` (`c`) wiederholt die
   Nullpunkte, `SAFE` (`s`) geht zurück.
3. **Start** erkannt bei |a| > 2 g für 50 ms → **BOOST**: Pitch/Yaw-Regler aktiv (wenn
   `PY_CONTROL_ACTIVE`). Weiß.
4. **Brennschluss**: axiale spezifische Kraft unter 3 m/s² für 100 ms, Rückfall 4,5 s →
   **COAST**: Servos auf Mitte, Rollregler weiter.
5. **Apogäum**: Kalman-vz < −0,5 m/s und Barometer 1 m unter seinem Maximum, beides 200 ms,
   frühestens 0,5 s nach Brennschluss, Rückfall 6 s → **APOGEE**: Pyro zündet, wenn ARM und
   Durchgang da sind und seit dem Start mindestens 2 s vergangen sind (80 ms Puls, Abbruch
   bei Durchgangsverlust, zweiter Versuch nach 0,5 s, Kanal 2 als Reserve 1,5 s später).
   Magenta.
6. **DESCENT** 1 s nach der Zündung; **LANDED** bei |vz| < 0,5 m/s und Höhe < 5 m für 2 s,
   Rückfall 2 min. Log wird geschlossen, Zustandsspeicher gelöscht.
7. **ABORT** vom Boden (`a`): auf dem Pad zurück nach SAFE (mit `s`); im Flug Regler aus,
   die Bergung läuft über die Zeitrückfälle weiter.

**Landebrennen** (`RECOVERY_MODE = LANDING_BURN`, Studie in `docs/Physik_Review_2026-10-23.md`):
APOGEE geht ohne Zündung in **DESCENT** (freier Fall, Servos Mitte). `LandingBurn.cpp` rechnet
jeden Takt die Aufsetzkosten für eine Zündung jetzt und einen Takt später und zündet im Minimum →
**LANDING_BURN**: Pyro-Kanal 2 (Anzünder des zweiten Motors, 1 s Puls bis zum Durchbrennen),
Pitch/Yaw-Regler aktiv, **LANDED** wenn die Rakete ruhig am Boden liegt oder spätestens nach
`LANDING_BURN_MAX_MS`. Hat der Anzünder keinen Durchgang, ist nicht scharf oder kommt ABORT,
fällt die Bergung auf den Fallschirm (Kanal 1 in APOGEE) zurück. Für den Erstflug steht
`RECOVERY_MODE = CHUTE`.

**Schubdrossel** (`THROTTLE_ENABLED`, Pads nach BPS Scout F am dritten Servokanal
`PIN_SERVO_THROTTLE`, rev B J_SERVO4): im Landemodus zündet `ThrottleLaw` früher (Reserve für
einen schwachen Motor), lässt in der Schubspitze die Pads draußen und schätzt dabei den wahren
Schub aus |a|, führt dann zeitbasiert auf Höhe 0 und −0,5 m/s zum Brennschluss und schwenkt die
Pads beim Aufsetzen ganz ein. Kennlinie und Mindestschub `THROTTLE_F_MIN` misst Experiment E05;
bis dahin bleibt die Drossel aus. Studie: `docs/Physik_Review_2026-10-23.md` §4.

Jeder Übergang geht als EVT-Rahmen über Funk, auf USB-Serial und ins Log. Alle Schwellen
stehen in `Config.h` (`FS_*`, `PYRO_*`).

**Neustart im Flug:** der Watchdog (250 ms) startet einen hängenden Teensy neu. Der
Flugzustand liegt jeden Takt im Zustandsspeicher (DMAMEM, Magic + CRC). Meldet `SRC_SRSR`
einen Watchdog-Reset und ist der Block gültig und in einer Flugphase, nimmt die Firmware
Zustand, Zeiten, Nullpunkte, Lage und Kalman-Zustand wieder auf (Flag `RESTORED` in der
Telemetrie, Reset-Ursache im Log); sonst beginnt sie in SAFE.

## Telemetrie (Serial8, HC-12 heute, E22 auf rev B)

Protokoll in `src/Telemetry.h`, das ist die Definition für die Bodenstation: Rahmen
`A5 5A | Typ | Länge | Nutzlast | CRC-16/CCITT` (CRC über Typ, Länge, Nutzlast; `Crc16.h`,
Prüfwert `"123456789"` → `0x29B1`), alle Werte little-endian.

| Typ | Richtung | Takt | Nutzlast |
|---|---|---|---|
| `TLM 0x01` | Rakete → Boden | 10 Hz | 16 Byte: Zustand, Flags (ARM, Durchgang 1/2, Log, kalibriert, Sensoren ok, Pyro gezündet, wiederaufgenommen), Zeit seit Start in 0,1 s, Höhe in 0,1 m, vz in cm/s, Kippwinkel x/y in 0,5°, Roll in 2°, Kardan Yaw/Pitch in 0,1°, 1S in 0,02 V, 2S in 0,05 V, Folgenummer |
| `EVT 0x02` | Rakete → Boden | bei Übergang | Zeit (ms), von, nach, Grund |
| `ACK 0x10` | Rakete → Boden | auf Kommando | Kommandotyp, Folgenummer, Ergebnis (0 ok, 1 abgelehnt, 2 unbekannt), Zustand |
| `CMD_PING 0x20`, `CMD_CALIBRATE 0x21`, `CMD_PAD_READY 0x22`, `CMD_ABORT 0x23`, `CMD_SAFE 0x24` | Boden → Rakete | | 1 Byte Folgenummer |

22 Byte je TLM-Rahmen ergeben 2200 bit/s, das passt in die 2,4 kbit/s Luftrate des E22.
Abweichung vom Vorschlag in `docs/Schnittstellen_Bodensystem_2026-10-22.md`: statt der
Quaternion gehen die Kippwinkel und der Rollwinkel über Funk (3 statt 8 Byte); GPS kommt als
eigener Rahmen, sobald es ein Modul gibt.

## Koordinaten und Vorzeichen

- Körpersystem: x und y quer, z entlang der Rollachse (+z zur Spitze). Die IMU-Chipachsen
  werden über `IMU_AXIS_MAP/SIGN` in `Config.h` darauf abgebildet (rev B: nach der
  Platzierung eintragen).
- Die Lage ist eine Quaternion Körper → Navigation (z nach oben), rein aus dem Gyro, auf dem
  Pad aus der Schwerkraft initialisiert. Der Regelfehler kommt aus dem Oben-Vektor im
  Körpersystem `u = R(q)ᵀ ẑ`: Kippwinkel um x (Yaw-Servo) = atan2(u_y, u_z), um y
  (Pitch-Servo) = atan2(−u_x, u_z). Für kleine Winkel ist das die alte Integration
  `rot_deg += ω·dt`, aber ohne den Fehler bei Rollen (Befund 3).
- Servo-Grad = TVC-Grad · `SERVO_*_GAIN` + `SERVO_*_OFFSET`, danach auf das mechanische
  Fenster des Kardans geklemmt (`SERVO_*_MIN/MAX_DEG`). Die Servos bekommen den Puls als
  16-Bit-PWM mit `SERVO_FRAME_HZ` (50 Hz SG90, 250 Hz W5652H auf rev B), ohne Rundung auf
  ganze Grad.

## Schalter in `Config.h`

| Schalter | Wirkung |
|---|---|
| `RECOVERY_MODE` | `CHUTE` (Ausstoßladung in APOGEE, Kanal 2 Reserve) oder `LANDING_BURN` (Kanal 2 = Anzünder des zweiten Motors, `LANDING_*`-Parameter) |
| `THROTTLE_ENABLED`, `THROTTLE_F_MIN`, `THROTTLE_*` | Schubdrossel im Landebrennen (dritter Servokanal, Kennlinie aus E05) |
| `PY_CONTROL_ACTIVE`, `ROLL_CONTROL_ACTIVE` | Regler freigeben. Ohne Freigabe bleiben die Servos auf Mitte und der Motor aus. |
| `LOG_DATA`, `LOG_EVERY_N_LOOPS`, `LOG_STOP_AFTER_FRAMES` | SD-Log an; jeden N-ten Takt; nach N Frames stoppen und einmal als CSV exportieren (Tischtest, 0 = nie). |
| `WDT_ENABLED`, `WDT_TIMEOUT_MS` | Watchdog |
| `PLOT_KALMAN`, `PLOT_ROLL`, `PLOT_PY`, `PLOT_ELECTRICS`, `PLOT_STATE` | Teleplot-Zeilen (`>Name:Wert`) auf USB-Serial |
| `LOOP_WARNING`, `VERBOSE` | Overrun-Meldungen, Kalibrierausgaben |
| `SILENT`, `DARK` | Summer bzw. LEDs stumm |
| `BOARD_REVB` (Build-Flag der Umgebung `teensy41_revb`) | Pins, Sensor-Rückende, Servo-Pulsrate und LED-Kette des Mainboards rev B |

## Log-Format

Ein Record pro Durchlauf, 88 Byte, little-endian:

```
uint32  ts_us           micros() beim Schreiben
uint16  write_us_prev   Dauer des vorigen physischen Writes
uint16  _pad
int16   v[40]           skalierte Kanäle, siehe mapFrameToI16() in SDLogger.cpp
```

| Kanal | Inhalt | Skalierung |
|---|---|---|
| 0–2 | Kalman-Höhe, Kalman-vz, Baro-Höhe | ×100 |
| 3–5 | a_nav x/y/z [m/s²] | ×100 |
| 6–8 | Drehrate x/y/z [°/s] | ×100 |
| 9–10 | Roll-Winkel, Roll-Rate | ×100 |
| 11–12 | Servo Yaw, Pitch [°] (seit 22.10.2026 nicht mehr auf ganze Grad gerundet) | ×100 |
| 13–14 | Roll-PWM (0..4095), Roll-Richtung | ×1, ×1000 |
| 15–19 | Bus-V, Last-V, Strom mA, Leistung mW, INA-Overflow | ×1000, ×1000, ×1, ×1, ×1 |
| 20–24 | Flugzustand (Zahl), Kippwinkel x, Kippwinkel y, 1S-Spannung, \|a\| | ×100 |
| 25–32 | Flugzeit in 0,1 s, Flags (`tlm::Flag`), Pyro (Zündungen Kanal 1 Bits 0–3, Kanal 2 Bits 4–7, Puls aktiv Bits 8/9), axiale spezifische Kraft ×100, Kardan Yaw ×100, Kardan Pitch ×100, Reset-Ursache, frei | 1:1 |
| 33–39 | frei | 0 |

Die Datei wird als `LOGxxxxx.TMP` mit 8 MB Vorallokation geschrieben und beim Stop auf die
genutzte Länge gekürzt und in `.BIN` umbenannt. Liegengebliebene `.TMP` (Stromausfall)
repariert `SDLogger_setup()` beim nächsten Start. `SDLogger_exportLatestCSVx(true)` schreibt
die jüngste `.BIN` als `.CSV` mit physikalischen Einheiten daneben.

## Test-Sketches (`examples/`)

Jeder Ordner enthält ein eigenes `main.cpp` und ist eine PlatformIO-Umgebung
(`build_src_filter` in `platformio.ini`). `src/` liegt im Include-Pfad, die Sketches
nutzen also dieselben Pins aus `Config.h`.

| Umgebung | Zweck |
|---|---|
| `radio_beacon` | Sendet 1×/s eine `BEACON,<seq>,<millis>`-Zeile über den HC-12 an Serial8. Gegenstück: Empfänger im Repo `kartonaut-ground`. |
| `i2c_scanner` | Listet alle I²C-Adressen auf Wire. Erwartet 0x40, 0x68/0x69 und 0x76. |
| `pyro_mosfet_test` | Warnblinken, dann ein 1-s-Puls auf `PIN_PYRO1` (23). Nur mit Lämpchen oder Widerstand als Last. |
| `servo_ident` | **Experiment E01** (`docs/experiments/E01_servo_ident.md`): fährt je TVC-Achse Treppe, Sprünge, Wechselsprünge und zwei Chirps auf den Servo und loggt mit 500 Hz Kommando, Drehrate und Beschleunigung einer ICM-20948 auf dem Motorrohr als CSV über USB. Befehle `?`, `Y`, `P`, `B`, `S`, `A`, `C`, `W`, `F`, `M`, `Z`, `V`, `N`. Aufnahme: `tools/capture_serial.py`, Auswertung: `simulation/scripts/ident_servo.py`. |
| `revb_bringup` | Inbetriebnahme des Mainboards rev B1: sichere Ausgänge, dann Mux (Akkus, ARM, Pyro-Durchgang), IMU, BMP390 (×2), INA239, LoRa-Parameter, GPS, LIS3MDL, SHT40, ADXL375; je Baustein OK/FEHL, danach Messwerte im Sekundentakt. Nutzt `lib/mainboard_revb/`, nicht `Config.h`. |
| `revb_test` | Testkonsole und Kalibrierung rev B1: Befehlsmenü über USB-Serial, je Funktion ein Befehl mit `TEST <name> OK/FEHL/SKIP`, geführte Kalibrierung mit `CAL`-Zeilen, Ablage im EEPROM-Emulat. Ablauf in `Tischtest_revB1.md`, PC-Seite `tools/bench_test.py`. `tvc ...` fährt Versuch E02 (Servo → Kardan, `docs/experiments/E02_TVC_Charakterisierung_revB1.md`, Aufnahme `tools/capture_tvc.py`). |

Die früheren Monolith-Sketches und kopierten Bibliotheksbeispiele (`sketches/` bis Commit
`3b152c9`) sind entfernt; sie stehen in der Git-Historie.

## Mainboard rev B1 (vorbereitet, Platine noch nicht gefertigt)

`lib/mainboard_revb/` enthält Pinbelegung und Treiber für die Platine (Stand `circuit.py` auf
`claude/rev-b1`). Die Flug-Firmware in `src/` bindet die Treiber noch nicht ein; PlatformIO baut die
Bibliothek nur in Umgebungen, die sie benutzen (`revb_bringup`, `revb_test`).

| Datei | Aufgabe |
|---|---|
| `BoardRevB.h` | Teensy-Pins, Chip-Selects (74HC138, `revb::Cs`), Analogkanäle (74HC4051, `revb::Mux`), I²C-Adressen, Teiler und Shunt |
| `BusRevB.*` | SPI1 auf 26/27/39, Chip-Select über den Decoder, Analogmessung über die Mux |
| `Imu.h` | Schmale IMU-Schnittstelle (`begin`, `whoAmI`, `dataReady`, `read`, `selfTest`); ein zweiter Treiber (LSM6DSV16X) käme ohne Umbau des Rests dazu |
| `ICM42688.*` | IMU über SPI, ±2000 °/s, ±16 g, 1 kHz, INT1 Daten bereit, Werksselbsttest. **Offen:** die Platine rev B1 trägt seit 23.10. einen LSM6DSV16X (E12, WHO_AM_I 0x70, gleiche Pins); der Treiber hinter `Imu.h` ist noch zu schreiben |
| `BMP390.*` | Barometer über SPI, Bosch-Kompensation, erkennt auch den BMP388 |
| `INA239.*` | Strom und Spannung im 2S-Pfad über SPI |
| `I2cRevB.h`, `LIS3MDL.*`, `SHT40.*`, `ADXL375.*` | I²C an Wire (18/19): Magnetometer 0x1E mit Selbsttest, Feuchte/Temperatur 0x44, ±200 g 0x53 (DNP, nur erkennen) |

`lib/calstore/` hält die Kalibrierwerte: `CalData.h` (Block mit Version und CRC-32, reines C++),
`CalStore.*` (EEPROM-Emulat des Teensy), `EllipsoidFit.h` (Hard-/Soft-Iron), `AxisFit.h`
(Achszuordnung aus einer Drehung). `src/main.cpp` lädt den Block beim Start und warnt bei
falscher CRC. Tests ohne Hardware: `test/host/` (g++) und `tools/test_bench_test.py` (pytest).

Decoder und Mux teilen sich die Select-Leitungen. Deshalb: kein SPI aus einer ISR, und keine
Analogmessung zwischen `select()` und `deselect()` (Details in `BusRevB.h`). Die IMU-Werte kommen
in Chip-Achsen; die Drehung ins Körpersystem wird eingetragen, wenn die Platzierung feststeht.

Solange sich die Platine ändert, vor dem Flashen die Pins gegen die Schaltung prüfen:

```bash
python firmware/tools/check_board_pins.py            # circuit.py auf diesem Branch
python firmware/tools/check_board_pins.py <circuit.py von claude/rev-b1>
```

Tischtest am PC (Versorgung, Flashen, Befehle, Bericht): `python tools/bench_test.py`, Ablauf und
Befehle in `Tischtest_revB1.md`, Versuchsanleitungen je Messung in `Versuche_revB1.md`.

## Werkzeuge (`tools/`)

| Skript | Zweck |
|---|---|
| `check_board_pins.py` | vergleicht `BoardRevB.h` mit `kicad/circuit.py` |
| `bench_test.py` | treibt die Testkonsole `revb_test`, wertet `TEST`/`CAL` aus, schreibt Markdown + JSON |
| `capture_tvc.py` | Aufnahme für Versuch E02 (`tvc ...` in `revb_test`) |
| `capture_serial.py` | schickt dem Sketch `servo_ident` die Befehle und speichert die CSV (`pip install pyserial`) |

## Tests ohne Hardware (`test/test_native/`)

`pio test -e native` baut die reinen Module (`Attitude`, `FlightState`, `Pyro`, `Telemetry`,
`ControlLaw`, `StateMemory`, `LandingBurn`) mit dem System-Compiler und lässt 42 Tests laufen; ohne
PlatformIO tut `python tools/run_native_tests.py` dasselbe mit g++. Das Testgerüst ist
`minitest.h` (Ausgabe im Unity-Format, Runner `test/test_custom_runner.py`), damit keine
Bibliothek aus der Registry nötig ist.

| Datei | Prüft |
|---|---|
| `test_attitude.cpp` | Drehung um x/y gegen die Integration, Rollen verschiebt den Kippwinkel in die andere Servoachse, Init aus schiefer Beschleunigung, Normierung |
| `test_flightstate.cpp` | volle Zustandsfolge auf einem synthetischen Flug und auf dem Flug aus `tvcsim` (`test/data/flight_profile_tvcsim.csv`), kein Start ohne PAD_READY, kurzer Stoß, Zeitrückfälle, Abbruch auf dem Pad und im Flug, Wiederaufnahme |
| `test_pyro.cpp` | alle vier Bedingungen einzeln, Pulslänge, Abbruch bei Durchgangsverlust, Versuche und Reservekanal, Entschärfen während des Pulses |
| `test_telemetry.cpp` | CRC-Prüfwert, Rahmen hin und zurück, Resynchronisation nach Müll und Bitfehler, Längen, Skalierung |
| `test_statememory.cpp` | Magic und CRC, Zufallsinhalt wird abgelehnt |
| `test_throttle.cpp` | Drosselkennlinie, Stopphöhen und Kommandofolge gegen Python-Vektoren, Zündung mit Reserve, Phasen des Reglers |
| `test_landing.cpp` | Aufsetzkosten gegen 60 Python-Werte, Minimum entlang des freien Falls, Zündbedingungen, Zustandsautomat auf dem simulierten Landeflug (`test/data/landing_profile_tvcsim.csv`), Rückfall auf den Fallschirm |
| `test_controllaw.cpp` | Mitte, Vorzeichen, Fenster, Integrator-Grenze, Roll-Totband; **Software-in-the-Loop**: dieselben Eingänge wie `tvcsim.controller.FirmwareController` liefern dieselben Momente und Servo-Grad (`test/data/sil_controller_ki*.csv` aus `simulation/scripts/export_firmware_vectors.py`) |

## Bibliotheken

Werden von PlatformIO über `lib_deps` geholt: Adafruit BMP280, SparkFun ICM-20948,
INA219_WE, BasicLinearAlgebra, SdFat (Adafruit-Fork), FastLED, Servo (nur noch für den
Fallschirm-Servo; die TVC-Servos laufen über `analogWrite`).
