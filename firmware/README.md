# Flug-Firmware

PlatformIO-Projekt für den Teensy 4.1. Die Firmware liest die Sensoren, schätzt Lage und
Höhe, regelt den Schubvektor und loggt jeden Durchlauf auf die SD-Karte. Ein
Flugzustandsautomat fehlt noch, die Regler sind in `Config.h` abgeschaltet. Für *Kartonaut 1* (Modulbauweise
Stand 2b, 22.10.2026) entfällt der Rollmotor; der Rollregler bleibt aus, dafür muss die Lage vor dem Erstflug als
Quaternion aus dem Gyro mit Oben-Vektor gerechnet werden (`PROJECT.md` Befund 3). Masse 0,705 kg und Hebelarm
0,190 m aus `cad/mass_stand2b.md` gehören nach dem Wiegen in `Config.h` (`MASS_KG`, `MOMENT_ARM_M`), und mit ihnen
kleinere Gewinne (Kp 2, Ki 1, Kd 0,45 statt 5, 0 und 1, `docs/Gewicht_und_Landung_2026-10-23.md` §4b; I-Anteil erst ab der Starterkennung); der
Fallschirm-Servo an `J_SERVO3` löst die CO₂-Kapsel aus.

```bash
pio run                        # Flug-Firmware bauen
pio run -t upload              # flashen (teensy-cli)
pio device monitor             # 115200 Bd, Teleplot-kompatibel
pio run -e i2c_scanner -t upload   # einen Test-Sketch flashen
```

## Module

| Datei | Aufgabe |
|---|---|
| `src/main.cpp` | `setup()` und die 100-Hz-Schleife: Sensoren, Integration, Kalman, Regler, Teleplot, Log |
| `src/Config.h` | Alle Pins, physikalischen Parameter, Reglergewinne, Filterkonstanten und Schalter |
| `src/Sensors.*` | BMP280 (Höhe gegen Bodendruck), ICM-20948 über DMP/FIFO (Quaternion, Beschleunigung, Drehrate), INA219. Accel-Bias-Kalibrierung im Stillstand. |
| `src/KalmanZ.*` | 2-Zustands-Kalman (Höhe, Vertikalgeschwindigkeit) mit Beschleunigung als Eingang und Barometer als Messung, `BasicLinearAlgebra` |
| `src/Control.*` | PID Pitch/Yaw mit Momenten-Umrechnung in den TVC-Winkel und Servo-Grad, PID Roll auf die H-Brücke, Servo-Ansteuerung |
| `src/SDLogger.*` | Binär-Logger mit Vorallokation, Seitenpuffer, slack-bewusstem Flush/Sync, TMP-Recovery und CSV-Export |
| `src/Timing.*` | Nicht blockierender Loop-Takt auf `micros()`, gemessenes dt, Slack bis zur Deadline, Overrun-Warnung |
| `src/Indicators.*` | Zwei WS2812B und Summer: Erfolg, Warten, Warnung |
| `src/MathTypes.h` | `Vec3`, `Quaternion`, Vektorrotation |

## Koordinaten und Vorzeichen

- Körpersystem: x und y quer, z entlang der Rollachse. Die integrierten Winkel
  `rot_deg` sind (x = Yaw, y = Pitch, z = Roll) in Grad.
- Die DMP-Quaternion (mit Magnetometer) dient nur dazu, die Beschleunigung ins
  Navigationssystem zu drehen und die Schwerkraft abzuziehen. Für die Regelung wird sie
  bewusst nicht benutzt, weil sie springt. Die Lage kommt rein aus dem Gyro.
- Servo-Grad = TVC-Grad · `SERVO_*_GAIN` + `SERVO_*_OFFSET`, danach auf das mechanische
  Fenster des Kardans geklemmt (`SERVO_*_MIN/MAX_DEG`).

## Schalter in `Config.h`

| Schalter | Wirkung |
|---|---|
| `PY_CONTROL_ACTIVE`, `ROLL_CONTROL_ACTIVE` | Regler freigeben. Ohne Freigabe bleiben die Servos auf Mitte und der Motor aus. |
| `LOG_DATA`, `LOG_STOP_AFTER_FRAMES` | SD-Log an; nach N Frames stoppen und einmal als CSV exportieren (Tischtest, 0 = nie). |
| `PLOT_KALMAN`, `PLOT_ROLL`, `PLOT_PY`, `PLOT_ELECTRICS` | Teleplot-Zeilen (`>Name:Wert`) auf USB-Serial |
| `LOOP_WARNING`, `VERBOSE` | Overrun-Meldungen, Kalibrierausgaben |
| `SILENT`, `DARK` | Summer bzw. LEDs stumm |
| `USE_WIRE1_FOR_IMU` (define) | IMU auf einem eigenen I²C-Bus mit 1 MHz |

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
| 11–12 | Servo Yaw, Pitch [°] | ×100 |
| 13–14 | Roll-PWM (0..4095), Roll-Richtung | ×1, ×1000 |
| 15–19 | Bus-V, Last-V, Strom mA, Leistung mW, INA-Overflow | ×1000, ×1000, ×1, ×1, ×1 |
| 20–24 | reserviert | ×100 |
| 25–32 | 8 rohe int16-Kanäle | 1:1 |
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
| `revb_bringup` | Inbetriebnahme des Mainboards rev B: sichere Ausgänge, dann Mux (Akkus, ARM, Pyro-Durchgang), ICM-42688-P, BMP390 (×2), INA239, LoRa-Parameter, GPS; je Baustein OK/FEHL, danach Messwerte im Sekundentakt. Nutzt `lib/mainboard_revb/`, nicht `Config.h`. |

Die früheren Monolith-Sketches und kopierten Bibliotheksbeispiele (`sketches/` bis Commit
`3b152c9`) sind entfernt; sie stehen in der Git-Historie.

## Mainboard rev B (vorbereitet, Platine noch nicht gefertigt)

`lib/mainboard_revb/` enthält Pinbelegung und SPI-Treiber für die Platine. Die Flug-Firmware in
`src/` bindet sie noch nicht ein; PlatformIO baut die Bibliothek nur in Umgebungen, die sie
benutzen (heute `revb_bringup`).

| Datei | Aufgabe |
|---|---|
| `BoardRevB.h` | Teensy-Pins, Chip-Selects (74HC138, `revb::Cs`), Analogkanäle (74HC4051, `revb::Mux`), Teiler und Shunt |
| `BusRevB.*` | SPI1 auf 26/27/39, Chip-Select über den Decoder, Analogmessung über die Mux |
| `ICM42688.*` | IMU über SPI, ±2000 °/s, ±16 g, 1 kHz, INT1 Daten bereit |
| `BMP390.*` | Barometer über SPI, Bosch-Kompensation, erkennt auch den BMP388 |
| `INA239.*` | Strom und Spannung im 2S-Pfad über SPI |

Decoder und Mux teilen sich die Select-Leitungen. Deshalb: kein SPI aus einer ISR, und keine
Analogmessung zwischen `select()` und `deselect()` (Details in `BusRevB.h`). Die IMU-Werte kommen
in Chip-Achsen; die Drehung ins Körpersystem wird eingetragen, wenn die Platzierung feststeht.

Solange sich die Platine ändert, vor dem Flashen die Pins gegen die Schaltung prüfen:

```bash
python firmware/tools/check_board_pins.py
```

## Bibliotheken

Werden von PlatformIO über `lib_deps` geholt: Adafruit BMP280, SparkFun ICM-20948,
INA219_WE, BasicLinearAlgebra, SdFat (Adafruit-Fork), FastLED, PWMServo, Servo.
