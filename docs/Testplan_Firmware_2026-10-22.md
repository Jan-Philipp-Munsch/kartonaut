# Testplan Firmware: Bodentests, Kalibrierungen, Messdaten für die Simulation

Stand 2026-10-22. Was Jan am Tisch, am Prüfstand und auf dem Pad durchgeht, in welcher Reihenfolge,
mit welchem Sketch, und was davon in `Config.h` und in `simulation/` landet. Ergebnisse kommen mit
Datum in `docs/BUILD.md` §5 (Regel 4). Die Firmware-Stände: `firmware/README.md`.

Reihenfolge der Meilensteine (`docs/Plan_2026-10-22.md` §3): M3 Firmware in der Simulation (fertig,
`pio test -e native`), dann §1–§3 am heutigen Aufbau, §4 für die Simulation, §5 am Prüfstand (M4),
§6 Funk und Bergung (M5), §7 Flugbereitschaft (M6).

Legende: **Sketch** = PlatformIO-Umgebung, `_revb` für das Mainboard. **Ergebnis →** wohin der Wert geht.

## 1. Tisch: Sensoren und Achsen (heute mit den Breakouts, später rev B)

| # | Test | Sketch, Taste | Erwartung | Ergebnis → |
|---|---|---|---|---|
| 1.1 | Sensoren da | `teensy41`, Start | `Sensoren: IMU ok, Barometer ok`; rev B zuerst `revb_bringup` alles OK | `BUILD.md` §4 (Commit, Umgebung) |
| 1.2 | Achsen und `chipToBody()` | `calib_imu`, `l` | Spitze oben: Neigung ≈ 0, `a ≈ (0, 0, +9,8)`. Um +x kippen → Yaw-Fehler positiv, um +y → Pitch-Fehler positiv, um z drehen → Roll. Stimmt eine Richtung nicht: `chipToBody()` in `Board.h` anpassen, nicht die Regler. | `Board.h` |
| 1.3 | Gyro-Bias und Rauschen | `calib_imu`, `g` (30 s ruhig) | Std bei 100 Hz < 0,2 °/s (ICM-42688-P: ca. 0,05); Std der 1-s-Mittel < 0,02 °/s; Bias stabil ±0,05 zwischen zwei Läufen | `GYRO_BIAS_DPS_*` (Rückfall), `GYRO_CAL_MAX_STD_DPS` |
| 1.4 | Sechs-Lagen-Accel | `calib_imu`, `6` | Skalierung 0,98–1,02, Bias < 0,2 m/s² | `ACCEL_BIAS_MS2`, `ACCEL_SCALE` |
| 1.5 | Barometer-Rauschen | `calib_imu`, `b` (30 s, Fenster zu) | BMP390 ×8/IIR 3: Std ≈ 0,2–0,4 m; BMP280 ×4: ≈ 0,5–1 m; Drift < 1 m | `KALMAN_MEAS_STD_M` = 2 × Std |
| 1.6 | Allan-Kurve (Pflicht einmal je IMU) | `calib_imu`, `s` 3 min, Datei speichern; `python simulation/scripts/analyze_imu_noise.py <csv> --plot` | Bias-Instabilität < 0,01 °/s. Drift über 10 s Boost < 0,1° | `tvcsim.NoiseParams(w_sigma, rdd_sigma)`, Plot in `BUILD.md` |
| 1.7 | Rampenkalibrierung | `teensy41`, `c`, dann `p` | `Kalibrierung: Bias …, Neigung < 1°` auf ebenem Tisch; bei Bewegung `nicht ruhig` | – |
| 1.8 | Lage-Drift | `teensy41`, `c`, 60 s liegen lassen, `p` | Neigung < 0,5° nach 60 s (sonst Bias-Instabilität zu groß oder Tisch vibriert) | – |
| 1.9 | Höhen-Kalman | `PLOT_KALMAN`, Teensy 1 m heben und senken | Kalman folgt dem Barometer ohne Überschwingen > 0,5 m, vz-Vorzeichen richtig | `KALMAN_SIGMA_ACC_MS2` |
| 1.10 | Loop-Timing | `p` nach 1 min | `Loop max` < 5000 µs (Breakout mit I²C ca. 2 ms); keine `Loop overrun` | – |
| 1.11 | Watchdog | `teensy41`, im Betrieb USB-Serial zumüllen hilft nicht: `WATCHDOG_TIMEOUT_S` auf 0,5 setzen und in `loop()` testweise `delay(600)` nach `l` einbauen | Neustart, `Watchdog-Neustart im Zustand BOOST` bzw. `Zustandsspeicher: … übernommen`; `Boot 1 (Watchdog)` bei `p` | `BUILD.md` §5 |

## 2. Tisch: Zustandsautomat und Bergung (ohne Treibsatz)

| # | Test | Sketch, Taste | Erwartung | Ergebnis → |
|---|---|---|---|---|
| 2.1 | Übergänge von Hand | `teensy41`, `c` `r` `l` `a` `s` | Serial zeigt `SAFE -> PAD_READY`, `PAD_READY -> BOOST (Grund 1)`, nach 4,5 s `BOOST -> COAST (Grund 5)`, nach 6 s `COAST -> APOGEE`, `-> DESCENT`, nach 3 s ruhig `-> LANDED`. LEDs grün / weiß / magenta / gelb. | – |
| 2.2 | Start durch Beschleunigung | `r`, dann die Rakete kräftig nach oben rucken (> 2 g für 50 ms geht nur mit Schwung: fallen lassen und abfangen geht nicht, das ist −1 g) | Entweder `-> BOOST (Grund 3)` oder nichts; ein Stoß auf den Tisch darf **nicht** starten | `FS_LIFTOFF_G`, `FS_LIFTOFF_HOLD_MS` |
| 2.3 | Apogäum durch Barometer | Nach `l` und 4,5 s (COAST): Teensy 2 m heben, 1 s halten, 2 m senken | `COAST -> APOGEE (Grund 4)` beim Senken, nicht beim Heben | `apogee_baro_drop_m` in `FlightState.h` |
| 2.4 | Pyro-Regeln mit Lämpchen (rev B) oder MOSFET-Modul (Breakout, Kanal 1) | 12-V-Lämpchen oder 2-Ω-Widerstand am Pyro-Ausgang, **nie eine Ladung**. `PLOT_ELECTRICS` an. Rev B: Schlüssel aus → `p` zeigt `sicher`, `cont 00`; Schlüssel ein → `scharf`, `cont 10`. Dann `c` `r` `l` und warten. Breakout: `PYRO_NO_SENSE_ASSUME_OK = true` (nur für diesen Test, danach zurück), `c` `r` `l`. | Lämpchen blitzt 80 ms bei APOGEE (rev B: Kanal 2 eine Sekunde später); `p` zeigt danach `fired`. Rev B mit Schlüssel aus: kein Blitz, kein PAD_READY. Breakout mit `PYRO_NO_SENSE_ASSUME_OK = false`: kein Blitz. | `PYRO_PULSE_MS`, `BUILD.md` §5 |
| 2.5 | Zustandsspeicher | wie 1.11 aus COAST | Nach dem Neustart `COAST` wiederhergestellt, gezündete Kanäle bleiben gezündet (kein zweiter Blitz) | – |
| 2.6 | SD-Log | `L` … `S` `x` | CSV mit 44 Spalten, `phase`-Spalte zeigt die Übergänge, `loop_us` plausibel | `BUILD.md` §5 |
| 2.7 | Servos im Automaten | `PY_CONTROL_ACTIVE = true`, `c` `r` `l`, Rakete im BOOST kippen | Servos folgen nur im BOOST, danach Mitte. Richtung: Spitze nach +x kippen → der Schubvektor muss **unter** die Spitze wandern (Düse nach −x). Stimmt es nicht: Vorzeichen von `SERVO_*_GAIN` | `Config.h` |

## 3. Tisch: Servos und Kardan (W5652H, neuer Kardan aus `cad/tvc.py`)

Die IMU dafür am Innenrahmen bzw. Motorträger befestigen (Breakout mit Klebeband, oder das ganze
Mainboard, wenn es da ist), eine Achse parallel zur Kardanachse. Rakete senkrecht einspannen.

| # | Test | Sketch, Taste | Erwartung | Ergebnis → |
|---|---|---|---|---|
| 3.1 | Pulsbreiten | Datenblatt W5652H, dann `calib_servo` `0` und jogen bis zum Anschlag | 0° und 180° ohne Brummen am Anschlag; sonst `SERVO_PULSE_MIN/MAX_US` enger | `SERVO_PULSE_*` |
| 3.2 | Mitte | `calib_servo`, jogen bis die Düse in der Rohrachse steht (Lineal), `w` | | `SERVO_YAW_OFFSET`, `SERVO_PITCH_OFFSET` |
| 3.3 | Servo-Grad je TVC-Grad und Polung | `calib_servo` `s y` `a <Achse>` `m`, dann `s p` | Ausgleichsgerade ca. 6 Servo-Grad je TVC-Grad (Befund 13); Vorzeichen übernehmen | `SERVO_YAW_GAIN`, `SERVO_PITCH_GAIN`; Fenster `SERVO_*_MIN/MAX_DEG` aus der Ausgabe |
| 3.4 | Fenster mechanisch | jogen bis der Kardan anschlägt, beide Achsen, beide Richtungen | ±7° TVC laut CAD; wenn weniger: `TVC_MAX_DEG` und Fenster | `Config.h` |
| 3.5 | Sprungantwort | `calib_servo` `r`, Ausgabe ab `t_ms` als `simulation/data/servo_step_response_w5652h.csv`; `python simulation/scripts/fit_servo.py` auf die Datei (Pfad im Skript oder Kopie) | PT2 + Totzeit: W5652H bei 8,4 V ca. 0,05 s/60° → wn deutlich über 36 rad/s, Totzeit < 30 ms | `ServoParams` in `simulation/tvcsim/params.py` |
| 3.6 | Stromspitze (rev B) | Servo blockieren, `PLOT_ELECTRICS` | INA-Strom bis ca. 1 A je Servo; `VBAT2` bricht < 0,3 V ein; Teensy startet **nicht** neu (`Boot` bleibt 0) | Spezifikation §9 Punkt 4 |

## 4. Messdaten für die Simulation (`simulation/`)

Was `tvcsim` heute noch rät und was eine Messung ersetzt. Reihenfolge nach Nutzen.

| # | Größe | Heute | Messung | Ergebnis → |
|---|---|---|---|---|
| 4.1 | Servo-Übertragungsfunktion W5652H | SG90-Fit von 2025 (`K 0,166, wn 36,7, zeta 0,6, tau 30 ms`) | 3.5 | `ServoParams`; `compare_gains.py --vehicle erstflug` neu laufen lassen |
| 4.2 | Servo-Grad je TVC-Grad | 6 (Sim) gegen 23 (alte Config) | 3.3 | `ServoParams.servo_deg_per_tvc_deg`, `FirmwareParams.SERVO_*_GAIN` |
| 4.3 | Masse, Schwerpunkt, Hebelarm | CAD 761 g, Schwerpunkt 318 mm, Hebelarm 0,242 m | Küchenwaage (±1 g); Schwerpunkt: auf einer Kante balancieren, Abstand zur Düse messen; Hebelarm = Schwerpunkt − 76,5 mm (Kardanpunkt) | `cad/params.py` Massen nachziehen → `mass_properties.json`; `MASS_KG`, `MOMENT_ARM_M` |
| 4.4 | Trägheitsmoment quer Ixx | CAD 0,046 kg m² | **Bifilarpendel:** Rakete waagerecht an zwei parallelen Fäden (Länge L, Abstand 2d, symmetrisch um den Schwerpunkt) aufhängen, um die Hochachse auslenken, Periode T über 10 Schwingungen stoppen. `I = m g d² T² / (4 π² L)`. Dreimal, Mittel. | `INERTIA_XX`, `cad/mass_properties.json` (Feld von Hand ergänzen), `VehicleParams.erstflug()` |
| 4.5 | Trägheitsmoment längs Izz | CAD 0,00057 kg m² | Bifilarpendel um die Längsachse (Rakete senkrecht hängend, zwei Fäden an der Spitze); kleiner Wert, Fäden eng (d ≈ 2 cm) | `INERTIA_ZZ`, `ROLL_K*` neu einstellen (Befund 15) |
| 4.6 | Sensorrauschen | `w_sigma 0,4 °/s`, `rdd_sigma 1 m/s²` (Simulink-Platzhalter) | 1.6 | `NoiseParams` |
| 4.7 | Schubkurve E12 | thrustcurve.org (TSP) | Schubstand mit Wägezelle, falls ein Motor übrig bleibt; sonst bleibt die Kurve | `simulation/data/E12_thrustcurve.csv` |
| 4.8 | Prüfstand-Schub gegen Gas | linear angenommen, `TESTRIG_THRUST_MAX_N 15` | 5.2 | `Testrig.cpp` (Kennlinie), `TESTRIG_THRUST_MAX_N` |
| 4.9 | `tf5` aus MATLAB | unbekannt | `tf5.Numerator, tf5.Denominator, tf5.IODelay` ausgeben und in `simulation/README.md` Abweichung 1 eintragen | klärt den Widerspruch zu `pid_tuner.m` (Befund 11) |

Nach 4.1–4.5: `python scripts/run_nominal.py --vehicle erstflug --controller firmware --single-motor`
und `export_flight_csv.py` neu, damit `test/data/flight_e12.csv` den gemessenen Werten folgt.

## 5. Prüfstand (M4, `cad/testrig.py`)

Vor dem ersten Lauf: Propellerschutz, Gurt-Anschläge ±20°, Rollachse gesperrt, 4S-Akku extern,
ESC-Signal auf `PIN_THROTTLE` (rev B: `PWM_EXT` am Stapelstecker, Breakout: Pin 10), `TESTRIG_MODE = true`,
`TESTRIG_THRUST_MAX_N` vorerst 10 N, Rakete im Rahmen ausgewuchtet (Drehpunkt im Schwerpunkt).

| # | Test | Erwartung | Ergebnis → |
|---|---|---|---|
| 5.1 | ESC armen | nach dem Boot 2 s Minimalpuls, ESC piept; `t3` → Propeller läuft an, `t0` aus | – |
| 5.2 | Schub gegen Gas | Rahmen auf eine Waage drücken lassen (Rakete senkrecht, Propeller nach oben, Waage unter der Düse) oder Federwaage am Rohr; `t2` … `t15` in 1-N-Schritten | Tabelle Gas → Schub; 12 N (E12 mittel) erreichbar? | `Testrig.cpp`, `TESTRIG_THRUST_MAX_N` |
| 5.3 | Reaktionsmoment Roll | bei 10 N: Rollachse freigeben, Rakete dreht sich | Drehrate notieren; wenn der Rollmotor das halten soll: `ROLL_CONTROL_ACTIVE` und Gewinne (Befund 15) | `ROLL_K*` |
| 5.4 | Offener Kreis | `PY_CONTROL_ACTIVE = false`, `c` `r` `l` | E12-Kurve läuft 3,5 s ab (`thrust_cmd_n` im Log), Rakete kippt an den Anschlag und bleibt dort | Log als Referenz |
| 5.5 | Geschlossener Kreis | `PY_CONTROL_ACTIVE = true`, `c` `r` `l` | Rakete bleibt in der Brennphase senkrecht (< 5°); Störung durch Antippen wird in < 1 s ausgeregelt, kein Dauerschwingen. Schwingt es mit 3–4 Hz: `PY_KD` halbieren (Befund 11). Im Gestell sieht die Firmware |a| = g, rechnet also wie bei 1 g Schub: bei 10 N und 0,761 kg stimmt das zufällig gut (1,3 g). | Log mit Störung und Ausregelung = **M4** |
| 5.6 | Statischer Fehler | Kardan-Mitte um 1° verstellen (Offset ±6 Servo-Grad) | bleibende Neigung ≈ 1° bei `PY_KI = 0`; mit `PY_KI = 1` verschwindet sie ohne Schwingen | `PY_KI` |
| 5.7 | Vibration | Propeller bei 10 N, `calib_imu` `s` 30 s | Accel-Std < 2 m/s², Gyro-Std < 2 °/s; sonst IMU weicher lagern oder `GYRO_FILT` | `GYRO_FILT_ALPHA` |

## 6. Funk und Bergung (M5)

| # | Test | Erwartung | Ergebnis → |
|---|---|---|---|
| 6.1 | Rahmen am Tisch | Bodenstation zeigt Telemetrie 10 Hz, `p` zeigt `verworfen 0`; `KN_CMD_PING` kommt mit ACK zurück | – |
| 6.2 | Kommandos | `CALIBRATE` vom Handy → `Kalibrierung: …` auf Serial und ACK OK; `ABORT` → ABORT; `SAFE` aus PAD_READY → SAFE | – |
| 6.3 | Startsperre Ende zu Ende | Rakete auf dem Pad (ohne Motor), Schlüssel, Zünder-Lämpchen an der Bodenstation: Countdown nur bei PAD_READY; Schlüssel ziehen → SAFE → Countdown bricht ab | **M5** |
| 6.4 | Reichweite | zwei E22, Rakete auf 2 m, Bodenstation entfernen: Paketverlust bei 100 / 300 / 500 m | `BUILD.md` §5; wenn > 10 % bei 300 m: Luftrate 1,2 k und Telemetrie 5 Hz |
| 6.5 | Ausstoß am Boden | Kolben, E-Match, Fallschirm gepackt, Rakete liegend in der Wiese, 10 m Abstand; Zündung über `c` `r` `l` und Automat (Rückfallzeiten) oder zur Sicherheit `pyro_mosfet_test` | Spitze fliegt 2–4 m, Schirm kommt frei, Kolben bleibt im Rohr (Schnur) | Video, `BUILD.md` §5, Ladungsmenge |
| 6.6 | Pyro-Störfestigkeit | 6.5 mit Servos unter Last im BOOST (5.5) | kein Neustart, keine Fehlzündung | – |

## 7. Flugbereitschaft (M6, Checkliste für den Starttag)

1. Firmware-Stand: Commit-Hash in `BUILD.md` §4, `PY_CONTROL_ACTIVE` wie am Prüfstand getestet,
   `TESTRIG_MODE = false`, `LOG_DATA = true`, `WATCHDOG_ENABLE = true`, `PLOT_* = false`.
2. Akkus voll (1S > 4,1 V, 2S > 8,2 V), SD-Karte leer, Pyro-Kanäle mit Lämpchen durchgetestet.
3. Masse und Schwerpunkt gewogen und in `BUILD.md`; Schwerpunkt vor dem Kardanpunkt wie im CAD.
4. Kalibrierung auf dem Pad (`CALIBRATE`), PAD_READY auf der Bodenstation, Piepen hörbar.
5. Zünder erst am Pad einstecken, Schlüssel erst nach dem Rückzug, Countdown vom Handy.
6. Nach dem Flug: Schlüssel ziehen, `x` am USB oder SD-Karte lesen, Log und Video sichern.

## 8. Offen in der Firmware (nicht am Gerät prüfbar, am Rechner weiter)

- Software-in-the-loop: `TvcController` und `Attitude` als Python-Erweiterung oder über eine
  C-Schnittstelle in `tvcsim` einhängen, dann rechnet die Simulation mit dem echten Code
  (heute: `FirmwareController` als Port).
- Bodenstation: `KartonautProtocol.h` übernehmen, `KnEvent` und `KnStatus` anzeigen.
- Zweites Barometer (DNP) und Kanal 3/4 in `SensorsRevB.cpp`, wenn bestückt.
- GPS: Baudrate des Moduls (9600/38400) und ggf. UBX statt NMEA.
