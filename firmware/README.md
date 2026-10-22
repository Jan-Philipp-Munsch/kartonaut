# Flug-Firmware

PlatformIO-Projekt für den Teensy 4.1. Die Firmware liest die Sensoren, schätzt Lage (Quaternion
aus dem Gyro) und Höhe (Kalman), führt den Flugzustandsautomaten, zündet die Bergung, regelt den
Schubvektor im Boost, funkt Telemetrie und loggt jeden Durchlauf auf die SD-Karte. Sie läuft auf
zwei Hardwareständen: den heutigen Breakouts und dem Mainboard rev B (`Board.h`).

```bash
pio run                            # Flug-Firmware für die Breakouts bauen
pio run -e teensy41_revb           # dieselbe Firmware für das Mainboard rev B
pio run -e teensy41 -t upload      # flashen (teensy-cli)
pio device monitor                 # 115200 Bd, 'h' zeigt die Tasten; Teleplot-kompatibel
pio test -e native                 # Tests des Flugkerns ohne Hardware
tools/run_native_tests.sh          # dieselben Tests mit g++, ohne PlatformIO
python ../simulation/scripts/run_sil.py   # Software-in-the-Loop: dieser Code in der 6DOF-Simulation
pio run -e calib_imu -t upload     # einen Kalibrier-Sketch flashen
```

## Aufbau

```
lib/flightcore/      hardwareunabhängig, nativ getestet: Lage, Höhen-Kalman, Zustandsautomat, Pyro, Protokoll, Regler
sil/                 C-Schnittstelle des Flugkerns für die Simulation (Software-in-the-Loop)
lib/mainboard_revb/  Pins und SPI-Treiber des Mainboards rev B (ICM-42688-P, BMP390, INA239, Decoder, Mux)
src/                 Flug-Firmware: Schleife und alles, was Hardware anfasst
examples/            Test- und Kalibrier-Sketches, je eine PlatformIO-Umgebung
test/                Unity-Tests (test_flightcore), Testdaten (simulierter Erstflug), Unity-Shim für g++
tools/               run_native_tests.sh, check_board_pins.py
```

### Flugkern (`lib/flightcore/`, ohne Arduino)

| Datei | Aufgabe |
|---|---|
| `Attitude.*` | Quaternion rein aus dem Gyro, `q̇ = ½ q ⊗ ω`, auf der Rampe aus dem Beschleunigungssensor initialisiert. Regelfehler aus dem Oben-Vektor `u = R(q)ᵀ ẑ`: Yaw = atan2(u.y, u.z), Pitch = atan2(−u.x, u.z), stetig und in Servoachsen auch bei Rollen (Befund 3). |
| `FlightState.*` | `SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED`, dazu `ABORT`. Start > 2 g für 50 ms, Brennschluss < 0,5 g für 100 ms (Rückfall 4,5 s), Apogäum vz < −0,5 m/s für 300 ms **und** Barometer 1 m unter Maximum (Rückfall 6 s), Landung ruhig für 3 s. Jeder Übergang ist ein Ereignis mit Grund. |
| `Pyro.*` | Vier Regeln je Zündung: Zustand erlaubt, ARM und Durchgang, höchstens einmal, Puls 80 ms mit Abbruch bei Durchgangsverlust. Schaltet nichts selbst. |
| `KartonautProtocol.h` | Rahmen `A5 5A, Typ, Länge, Nutzlast, CRC-16/CCITT`; Telemetrie 22 Byte bei 10 Hz, GPS, Status, Ereignis, Kommando/ACK. Reines C, wird in die Bodenstation kopiert. |
| `Telemetry.*`, `Crc16.*` | Rahmen bauen, byteweise zerlegen, nach Müll neu synchronisieren. |
| `KalmanZ.*` | 2-Zustands-Kalman (Höhe, vz), `predict()` jeden Takt, `update()` bei frischer Barometermessung. Seit 22.10.2026 ohne Matrixbibliothek (2 × 2 von Hand), damit er nativ und im SIL läuft. Stationärer vz-Fehler ≈ 1,4 s × Accel-Bias (Test). |
| `TvcController.*` | PID Pitch/Yaw → Moment → `δ = asin(M/(l·m·|a|))` → Servo-Grad, wie bisher `Control.cpp`, mit Anti-Windup und Kardanbegrenzung ±7°. |
| `MathTypes.h` | `Vec3`, `Quaternion`, Drehung. |

### Flug-Firmware (`src/`)

| Datei | Aufgabe |
|---|---|
| `main.cpp` | `setup()` und die 100-Hz-Schleife: Sensoren, Lage, Kalman, Kommandos, Automat, Pyro, Regler, Telemetrie, Anzeigen, Zustandsspeicher, Log |
| `Config.h` | Physik (Erstflug 0,761 kg, 0,242 m), Gewinne, Servo-Umsetzung, Schwellen des Automaten, Pyro, Akkugrenzen, Funk, Schalter. Keine Pins. |
| `Board.h` | Pins und Eigenschaften je Rückende: ohne Flag Breakouts, mit `-DBOARD_REVB` das Mainboard aus `BoardRevB.h`. Auch `chipToBody()` für die IMU-Lage. |
| `Sensors.h`, `SensorsBreakout.cpp`, `SensorsRevB.cpp` | Gemeinsame Schnittstelle: spezifische Kraft und Drehrate im Körpersystem (bias-korrigiert), Barometerhöhe, Versorgung (Akkus, ARM, Durchgang). Gyro-Bias-Kalibrierung, Bodendruck. |
| `Control.*` | Servos (PWMServo, alle drei), Rollmotor-H-Brücke mit nSLEEP (rev B), Rollregler |
| `Radio.*` | E22 (rev B: Konfiguration über M0/M1, AUX-Flusskontrolle) bzw. HC-12 an Serial8; sendet Rahmen, parst Kommandos |
| `Persist.*` | Watchdog WDOG1 (1 s) und Zustandsspeicher im DMAMEM: nach einem Watchdog-Neustart im Flug geht es in der laufenden Phase weiter |
| `Gps.*` | GGA-Leser für das Modul an Serial1 (rev B) |
| `Testrig.*` | Gas-Ausgang für den Prüfstand (ESC), fährt die E12-Kurve nach (`TESTRIG_MODE`) |
| `SDLogger.*` | Binär-Logger mit Vorallokation, slack-bewusstem Flush/Sync, TMP-Recovery und CSV-Export |
| `Timing.*` | Loop-Takt auf `micros()`, gemessenes dt, Slack, Overrun-Warnung |
| `Indicators.*` | LEDs und Summer: blockierende Muster für den Start, nicht blockierend je Flugzustand |

## Ablauf eines Flugs

1. **Einschalten → SAFE.** Sensoren starten, Funk konfigurieren, Gyro-Bias und Lage am Tisch bestimmen (2 s ruhig).
2. **Auf der Rampe:** Kommando `CALIBRATE` (Bodenstation oder Taste `c`): Gyro-Bias, Startlage, Bodendruck neu. Danach prüft der Automat eine Sekunde lang: kalibriert, Schlüsselschalter scharf (ARM), Durchgang des Zünders, beide Akkus über der Grenze, Neigung < 10°, ruhig → **PAD_READY**, das Log startet, grüne LED, Piep jede Sekunde. Die Bodenstation zündet nur, wenn sie PAD_READY sieht (S3).
3. **Start:** > 2 g entlang der Rollachse für 50 ms → **BOOST**. Regler-Integratoren auf null, Kamera-Auslöser, TVC-Regler stellt (wenn `PY_CONTROL_ACTIVE`).
4. **Brennschluss** → **COAST**, Servos auf Mitte.
5. **Apogäum** → **APOGEE**: Kanal 1 zündet (Kolben), nach 1 s Kanal 2 als Reserve; nach 100 ms **DESCENT**.
6. **Landung** (3 s ruhig) → **LANDED**: Ortungspiepen, Log stoppt nach 10 s.
7. **ABORT** (Kommando, > 70° Kippen im Boost, Sensorausfall im Flug): Regler aus, Servos Mitte; nach dem Start wird die Bergung weiter gezündet.

Ohne ARM-Messung (Breakouts) oder im `TESTRIG_MODE` verlangt der Automat kein ARM und keinen
Durchgang; am Tisch erzwingen `r` (PAD_READY) und `l` (Start) die Übergänge.

## Koordinaten und Vorzeichen

- Körpersystem: x und y quer, z entlang der Rollachse zur Spitze. Navigationssystem: z nach oben.
  Der ruhende Beschleunigungssensor misst +g entlang z (spezifische Kraft).
- `yawErrDeg()` ist die Neigung um die Körper-x-Achse, `pitchErrDeg()` um y. Für kleine Winkel ohne
  Rollen entsprechen sie den früher integrierten `rot_deg.x/.y`; mit Rollen wandern sie in die
  richtige Servoachse (`test_attitude_error_follows_body_axis_after_roll`).
- Servo-Grad = TVC-Grad · `SERVO_*_GAIN` + `SERVO_*_OFFSET`, geklemmt auf `SERVO_*_MIN/MAX_DEG`
  und ±`TVC_MAX_DEG`. Gain, Offset und Polung am Kardan mit `calib_servo` messen (Befund 13).
- Rev B: `chipToBody(c) = (c.x, −c.z, c.y)` nach Spezifikation §2, am Gerät prüfen (Spitze oben → a.z ≈ +9,81).

## Schalter in `Config.h`

| Schalter | Wirkung |
|---|---|
| `PY_CONTROL_ACTIVE`, `ROLL_CONTROL_ACTIVE` | Regler freigeben (nur im BOOST aktiv). Ohne Freigabe bleiben die Servos auf Mitte und der Motor aus. |
| `LOG_DATA`, `LOG_FROM_BOOT`, `LOG_STOP_AFTER_FRAMES` | SD-Log ab PAD_READY; ab Boot; am Tisch nach N Frames stoppen und CSV exportieren |
| `TESTRIG_MODE`, `TESTRIG_THRUST_MAX_N` | Gas-Ausgang auf `PIN_THROTTLE`, Start per Kommando, E12-Kurve skaliert |
| `WATCHDOG_ENABLE`, `WATCHDOG_TIMEOUT_S` | WDOG1 |
| `PLOT_KALMAN`, `PLOT_ATTITUDE`, `PLOT_ROLL`, `PLOT_PY`, `PLOT_ELECTRICS`, `PLOT_STATE` | Teleplot-Zeilen (`>Name:Wert`) bzw. Zustandsübergänge auf USB-Serial |
| `LOOP_WARNING`, `VERBOSE`, `SILENT`, `DARK` | Overrun-Meldungen, Kalibrierausgaben, Summer und LEDs stumm |

Tasten am USB-Serial: `h` Hilfe, `c` kalibrieren, `r` PAD_READY erzwingen, `l` Start erzwingen,
`a` Abbruch, `s` SAFE, `L`/`S` Log an/aus, `x` CSV-Export, `p` Status, `t<N>` Prüfstand-Schub.

## Telemetrie (S3)

10 Hz `KnTelemetry` (Zeit, Zustand, Flags, Höhe, vz, Quaternion, TVC-Winkel, beide Akkus), 1 Hz
`KnStatus` (Loop-Maximum, Strom, Barometer, Neigung, Temperatur, Neustarts, Logfüllstand) und `KnGps`,
je Zustandsübergang `KnEvent` dreimal. Kommandos `PING`, `CALIBRATE`, `PAD_READY_QUERY`, `ABORT`,
`SAFE`, `LOG_START/STOP`, `TESTRIG_THRUST` mit `KnAck`. Alles in `lib/flightcore/KartonautProtocol.h`;
die Bodenstation (`kartonaut-ground`) übernimmt die Datei unverändert.

E22 wird beim Start auf Adresse 0, Kanal 0x17 (433,125 MHz), 9600 Bd UART, 2,4 kbit/s Luftrate,
22 dBm, transparent gesetzt (`Radio::configure()`), beide Seiten gleich.

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
| 0–2 | Kalman-Höhe, Kalman-vz, Baro-Höhe (über Pad) | ×100 |
| 3–5 | a_nav x/y/z [m/s²], ohne g | ×100 |
| 6–8 | Drehrate x/y/z [°/s], bias-korrigiert | ×100 |
| 9–11 | spezifische Kraft Körper x/y/z [m/s²] | ×100 |
| 12–15 | Quaternion w, x, y, z | ×32767 |
| 16–19 | Neigung, Yaw-Fehler, Pitch-Fehler, Roll [°] | ×100 |
| 20–21 | gefordertes Moment Yaw, Pitch [N m] | ×1000 |
| 22–23 | TVC-Winkel Yaw, Pitch [°] | ×100 |
| 24–25 | Servo Yaw, Pitch [°] | ×100 |
| 26–28 | Roll-Stellgröße (−1..1), Roll-PWM, Roll-Richtung | ×1000, ×1, ×1 |
| 29–33 | Flugzustand, Flags (KN_FLAG_*), Pyro (Bit 0–3 Durchgang, 4–7 Puls), Loop-Dauer [µs], Neustarts | ×1 |
| 34–37 | 1S-Akku, 2S-Akku, ARM [V], Strom [A] | ×1000 |
| 38–39 | IMU-Temperatur [°C], Prüfstand-Schub [N] | ×10, ×100 |

Die Datei wird als `LOGxxxxx.TMP` mit 8 MB Vorallokation geschrieben (≈ 15 min bei 100 Hz) und beim
Stop auf die genutzte Länge gekürzt und in `.BIN` umbenannt. Liegengebliebene `.TMP` (Stromausfall)
repariert `SDLogger_setup()` beim nächsten Start. `x` am USB-Serial exportiert die jüngste `.BIN`
als `.CSV` mit physikalischen Einheiten und den Spaltennamen oben.

## Test- und Kalibrier-Sketches (`examples/`)

Jeder Ordner ist eine PlatformIO-Umgebung (`build_src_filter` in `platformio.ini`); `src/` und
`lib/flightcore` liegen im Include-Pfad. Die Kalibrier-Sketches gibt es je als `<name>` (Breakouts)
und `<name>_revb` (Mainboard). Ablauf und Auswertung: `docs/Testplan_Firmware_2026-10-22.md`.

| Umgebung | Zweck |
|---|---|
| `calib_imu`, `calib_imu_revb` | Gyro-Bias und Rauschen (30 s), Sechs-Lagen-Accel, Barometer-Rauschen, CSV-Strom für `simulation/scripts/analyze_imu_noise.py`, Lage live zum Achsencheck. Gibt fertige Zeilen für `Config.h` aus. |
| `calib_servo`, `calib_servo_revb` | Servos jogen, Mitte und Fenster, Servo-Grad je TVC-Grad mit der IMU am Kardan, Sprungantwort als CSV im Format von `simulation/data/servo_step_response.csv` (`fit_servo.py`). |
| `radio_beacon` | Sendet 1×/s eine `BEACON,<seq>,<millis>`-Zeile über Serial8 (HC-12-Test). |
| `i2c_scanner` | Listet alle I²C-Adressen auf Wire. Breakouts: 0x40, 0x68/0x69, 0x76. |
| `pyro_mosfet_test` | Warnblinken, dann ein 1-s-Puls auf `PIN_PYRO1`. Nur mit Lämpchen oder Widerstand als Last. |
| `revb_bringup` | Inbetriebnahme des Mainboards rev B: Mux, ICM-42688-P, BMP390, INA239, LoRa-Parameter, GPS; je Baustein OK/FEHL. |

## Tests ohne Hardware (`test/test_flightcore`)

`pio test -e native` (in der CI) oder `tools/run_native_tests.sh` (g++ mit `test/unity_shim`):
CRC-Prüfwert, Rahmen hin und zurück mit Resynchronisation, Quaternion (Init aus der Ruhelage,
reine Drehungen, Fehler folgt der Körperachse nach 90° Rollen, Norm nach 100 000 Schritten),
Zustandsautomat mit synthetischen Eingaben und auf dem simulierten Erstflug
`test/data/flight_e12.csv` (aus `simulation/scripts/export_flight_csv.py`: Start 0,4 s, Brennschluss
3,55 s, Gipfel 54 m bei 5,4 s, Landung 8,8 s; der Automat erkennt BOOST bei 0,51 s, COAST 3,56 s,
APOGEE 6,09 s, LANDED 11,8 s; die Quaternion liegt über den ganzen Flug unter 0,1° neben der Wahrheit),
Pyro-Regeln, TVC-Regler (Momente, Sättigung, Anti-Windup).

## Software-in-the-Loop (`sil/`, `simulation/tvcsim/sil.py`)

`sil/kartonaut_sil.cpp` verpackt den Flugkern (Attitude, KalmanZ, FlightState, PyroLogic,
TvcController) hinter eine C-Schnittstelle; ein Aufruf von `sil_step()` entspricht einem Durchlauf
von `loop()` ohne Hardware, mit derselben Servo-Rundung. `simulation/tvcsim/sil.py` übersetzt das
mit g++/clang++ beim ersten Aufruf selbst, lädt es über ctypes und hängt es als Regler in die
6DOF-Simulation; alle Konstanten liest es aus `src/Config.h`. Läufe, Monte-Carlo und die Untersuchung
der Apogäum-Schwellen: `simulation/scripts/run_sil.py`, Tests in `simulation/tests/test_sil.py`.

## Mainboard rev B

`lib/mainboard_revb/` enthält Pinbelegung und SPI-Treiber (`BoardRevB.h`, `BusRevB.*`, `ICM42688.*`,
`BMP390.*`, `INA239.*`). Decoder und Mux teilen sich die Select-Leitungen, deshalb: kein SPI aus
einer ISR, keine Analogmessung zwischen `select()` und `deselect()` (`BusRevB.h`). Solange sich die
Platine ändert, vor dem Flashen die Pins gegen die Schaltung prüfen:

```bash
python firmware/tools/check_board_pins.py
```

Die Flug-Firmware baut mit `-e teensy41_revb` dagegen; am Gerät noch nichts getestet, die Platine
ist nicht gefertigt.

## Bibliotheken

PlatformIO holt sie über `lib_deps`: SdFat (Adafruit-Fork), FastLED, PWMServo;
Breakouts zusätzlich Adafruit BMP280, SparkFun ICM-20948, INA219_WE. Rev B braucht keine
Sensorbibliotheken (eigene SPI-Treiber). BasicLinearAlgebra ist seit dem Kalman ohne Matrixbibliothek entfallen.
