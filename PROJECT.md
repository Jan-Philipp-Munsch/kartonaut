# Mission Space – Projektdatei

Die zentrale Übersicht über das Raketenprojekt: was es gibt, wo es liegt, wie weit es ist
und was als Nächstes kommt. **Bei jedem Arbeitsschritt hier den Fortschritt und das
Änderungsprotokoll nachtragen.**

Stand: 2026-10-20

<img src="docs/img/model_rocket.png" width="260" align="right" alt="model_rocket.blend">

## 1. Ziel

Eine Modellrakete mit Schubvektorsteuerung (TVC), aufgebaut nach dem Vorbild von BPS.space
„Scout F“. Sie fliegt mit kardanisch aufgehängtem Motor, Rollregelung über ein Schwungrad
bzw. einen Rollmotor, Fallschirmbergung und Landebeinen. An Bord sitzt ein selbst
programmierter Flugcomputer (Teensy 4.1) mit Funk-Telemetrie zur Bodenstation.

## 2. Eckdaten (Ist-Stand aus Modellen und Code)

| Größe | Wert | Quelle |
|---|---|---|
| Rumpf | Ø 75 mm außen, 1000 mm lang (2× 0,5 m + Koppler) | `model_rocket.blend`, `Gewicht.csv` |
| Spitze | Ø 80 mm, 99 mm hoch, federgelagert, Gewindestange M2,5 | `rocket nose.blend` |
| Motor | Estes E12 (24 mm) im 29→24-mm-Adapter. Schubkurven E12 und F35 liegen vor. | `TVC.blend`, MATLAB `6DOF_model` |
| Masse | 902 g geplant (2× E12, Landesystem 200 g) | `Gewicht.csv` |
| TVC | Kardan mit 2× SG90, Servofenster Yaw 70–115°, Pitch 60–105° | `dual_tvc.blend`, `Control.cpp` |
| Hebelarm TVC–Schwerpunkt | 0,30 m | `Config.h`, `TVC6DOF.m` |
| Flugcomputer | Ring-Stack Ø 69 mm, 8 M2-Stangen, Ringe für Teensy, Sensorik, Akku und Roll | `flight_computer.blend` |
| Akku | 2S LiPo 7,4 V | `flight_computer.blend` („Battery 7.4V“) |
| Funk | HC-12 (433 MHz), 9600 Bd | `Config.h`, `Radio_test.cpp` |

## 3. Wo liegt was

| Bereich | Ort | Inhalt |
|---|---|---|
| Flug-Firmware | `spacecode/` (dieses Repo) | PlatformIO, Teensy 4.1. `src/` ist modular: main, Config, Sensors, KalmanZ, Control, SDLogger, Timing, Indicators. `examples/` enthält Test-Sketches als eigene PlatformIO-Umgebungen (Funk-Beacon, I²C-Scan, Pyro-MOSFET). Die alten Monolithe (`sketches/`) sind seit dem 20.10.2026 nur noch in der Git-Historie (bis Commit `3b152c9`). Doku: `spacecode/README.md`. |
| Bodenstation | `groundcode/` | Eigenes Repo (`git.rwth-aachen.de:jan_philipp.munsch/space`), hier per `.gitignore` ausgeklammert. Arduino Nano mit HC-12-Empfänger, MPU6050-Test, Fan-ESC-Test. |
| Mainboard | `hardware/mainboard/` | Spezifikation rev A, Umriss-DXF, Platzierungsplan |
| Elektronik-Notizen | `eLab/` (lokal, per `.gitignore` ausgeklammert) | OneNote-Abschnitt (HC-12-Modul, 14.10.2025) |
| Simulation | `OneDrive/Dokumente/MATLAB/Projects/6DOF_model` | Simulink-6DOF mit Monte-Carlo (`TVC6DOF.m`), PID-Suche (`pid_tuner.m`), Servo-Systemidentifikation, Schubkurven E12/F35 |
| Simulation (Vorlage) | `OneDrive/Dokumente/MATLAB/Projects/BPS_TVC` | MathWorks-Beispiel „simpleTVCRocketModel“ |
| CAD (eigen) | `D:/Krams_aktuell_2026-08-16/Krams/Blender/Dateien/` | `model_rocket` (Gesamtmodell), `flight_computer` (+ `_obj`), `TVC`, `TVC_V2`, `Inner_gimbal(_V2)`, `dual_tvc`, `inner/outer_gimbal_dual_TVC`, `LegConnectors`, `rocket nose`, `flywheel(V2)`, `untitled`/`test123` (Gimbal-Zwischenstände) |
| CAD/Doku (fremd) | `D:/Krams_aktuell_2026-08-16/Krams/Space Mission/` | BPS.space Scout F STEP/OBJ (TVC, Beine, Reaction Wheel, Throttle), BPS-Blip-Platine (Schaltplan, Layout, Code), Piston-Ejection-Bulkheads, `battery7.stl`, `Gewicht.csv`, `Übersicht.ods` (Strombudget) |

Die Blender-Dateien sind in Millimetern modelliert, obwohl die Szene auf „Meter“ steht.
`docs/render_blend.py` rendert eine Ansicht aus einer .blend-Datei, so ist `docs/img/model_rocket.png` entstanden.

## 4. Fortschritt

Status: ✅ fertig · 🟡 in Arbeit · ⬜ offen

| # | Arbeitspaket | Status | Stand / Nachweis |
|---|---|---|---|
| 1 | Konzept, Massen- und Strombudget | ✅ | `Gewicht.csv` (Juni 2025), `Übersicht.ods` (März 2025) |
| 2 | 6DOF-Simulation und PID-Auslegung | ✅ | Monte-Carlo und PID-Raster (Mai/Juni 2025), Servo-Systemidentifikation |
| 3 | TVC-Kardan (CAD) | 🟡 | Mehrere Generationen bis `dual_tvc` (Juni 2025). Druck- und Funktionstest nicht dokumentiert. |
| 4 | Rumpf, Spitze, Landebeine (CAD) | 🟡 | `model_rocket.blend` (Juni 2025) |
| 5 | Bergung (Piston Ejection) | 🟡 | Bulkheads heruntergeladen (Juni 2025). Fallschirm-Servo im Code. Pyro-Auslösung fehlt. |
| 6 | Flugcomputer-Mechanik (Ring-Stack) | 🟡 | `flight_computer.blend` (13.10.2025), `battery7.stl` |
| 7 | Sensorik: IMU (DMP), Barometer, INA219 | ✅ | `Sensors.cpp` (Okt. 2025) |
| 8 | Höhenschätzung (Kalman z/vz) | ✅ | `KalmanZ.cpp`, Commit „kalman filter optimization“ |
| 9 | SD-Logger (Binär → CSV) | ✅ | `SDLogger.cpp`, Commit „Logger Implementation“ |
| 10 | Regler Pitch/Yaw und Roll | 🟡 | Commit „Controls under control“ (21.10.2025). In `Config.h` sind beide aus. Ein Flugtest steht aus. |
| 11 | Funkstrecke HC-12 | 🟡 | Beacon-Test Teensy → Nano (Okt. 2025). Ein echtes Telemetrieprotokoll fehlt. |
| 12 | GPS | ⬜ | Nur ein früherer Testsketch (TinyGPSPlus-Beispiel, Git-Historie bis `3b152c9`) |
| 13 | Flugzustandsautomat (Pad → Boost → Coast → Apogäum → Bergung → Landung) | ⬜ | Gibt es noch nicht. Die Flugschleife in `main.cpp` läuft wieder (seit 20.10.2026), der MOSFET-Test ist nach `examples/pyro_mosfet_test/` gewandert. |
| 14 | **Mainboard rev A (Platine statt Breakouts)** | 🟡 | Spezifikation, Pinbelegung, Stückliste und Umriss fertig (15.10.2026) → `hardware/mainboard/`. Bauform: Längs-Schlitten 54 × 120 mm zwischen den Endringen des Stacks, Akku im Träger darunter. Die runde Ø-68-Variante ist verworfen. Als Nächstes: Schaltplan in KiCad. |
| 15 | Bodentests (Servo-Schubstand, Pyro-Test, Funkreichweite) | ⬜ | |
| 16 | Erstflug | ⬜ | |

## 5. Befunde aus der Durchsicht vom 15.10.2026

Das ist beim Einlesen aufgefallen. Was die Aufräumrunde vom 20.10.2026 davon erledigt hat, steht beim jeweiligen Punkt in eckigen Klammern.

1. **Masse uneinheitlich:** `Config.h` rechnet mit `MASS_KG = 0.70`, die Simulation mit 0,94 kg, `Gewicht.csv` mit 902 g. Die Masse geht direkt in den TVC-Winkel ein (`asin(M / (l·m·|a|))`).
2. **Reglerparameter weichen von der Simulation ab:** Die Firmware nutzt für Pitch/Yaw Kp = 5, Ki = 0, Kd = 1 auf skalierten Grad. `pid_tuner.m` hat zuletzt Kp = 3,1, Ki = 5, Kd = 0,385 gesucht. Die Einheiten beider Seiten sind noch nicht abgeglichen.
3. **Lage rein aus dem Gyro, aber komponentenweise aufsummiert:** Rein inertial ist für den Flug richtig. Die DMP-Quaternion (`Quat9`, mit Magnetometer) ist bewusst verworfen worden, weil sie sprang und den PID verrauschte. Im Flug sind Kompass und Beschleunigungs-Stützung ohnehin unbrauchbar. Schwach ist nur `rot_deg += omega·dt`: Das gilt nur ohne Rollen und bei kleinen Winkeln. Rollt die Rakete, landet ein Neigungsfehler in der falschen Servoachse. Besser wäre eine eigene Quaternion nur aus dem Gyro, auf der Rampe mit dem Beschleunigungssensor initialisiert. Der Regelfehler kommt dann aus dem Oben-Vektor im Körpersystem, `u = R(q)ᵀ·ẑ`, mit Pitch = atan2(u.x, u.z) und Yaw = atan2(u.y, u.z). Das ist stetig, hat keinen ±180°-Sprung und gilt in Servo-Achsen. Nebenbei: `Control_updatePY` integriert einen Schritt mehr als `loop()`. Und `a_nav` für den Kalman wird weiter mit der DMP-Quaternion gedreht, die beim Schub die Neigung falsch stützt. [erledigt 20.10.2026: der doppelte Integrationsschritt ist weg, die Regler bekommen den Winkel aus `main.cpp` und integrieren nur noch ihre I-Anteile. Quaternion aus dem Gyro und `a_nav` sind weiter offen.]
4. **Beschleunigungsbereich ±4 g:** Die E12-Schubkurve hat ihr Maximum bei 28,3 N. Bei 0,9 kg misst der Beschleunigungssensor dann 3,2 g, also knapp unter der Grenze. Mit der F35 (Maximum 55 N, 6,2 g) wäre er gesättigt. Wer den Motor wechselt, muss den DMP-Accel-Bereich vergrößern. Sonst sättigen Kalman und Schubschätzung.
5. **Gyro-Offsets fest im Code:** Die Werte (+12,1 / −7,96 / +2,44 LSB) stehen in `Sensors.cpp`. Besser wäre eine Kalibrierung auf der Startrampe, ähnlich wie `Accel_calibrate_body`. [20.10.2026: nach `Config.h` verschoben (`GYRO_BIAS_LSB_*`), Rampenkalibrierung weiter offen.]
6. **SDFrame-Felder** `load_V`, `power_mW` und `ina_overflow` werden nicht befüllt.
7. **Fallschirm-Servo** läuft über `Servo`, die TVC-Servos über `PWMServo`. Das funktioniert, aber zwei Bibliotheken teilen sich die Timer.
8. **Verkabelung** mit Breakouts und Dupont-Kabeln ist das größte Ausfallrisiko im Flug (Vibration). Das löst Paket 14.
9. **Gyro-Dekodierung am falschen FIFO-Bit** (gefunden 20.10.2026): `Read_IMU` prüfte `DMP_header_bitmap_Gyro_Calibr`, las aber `Raw_Gyro.Data`. Die SparkFun-Bibliothek füllt `Raw_Gyro` nur beim Gyro-Paket (Bit `0x4000`), das Calibr-Paket landet in `Gyro_Calibr`. Es hat bisher nur funktioniert, weil beide Pakete mit ODR 0 im selben Frame kommen. [erledigt 20.10.2026: Prüfung auf `DMP_header_bitmap_Gyro`, das Calibr-Paket wird nicht mehr angefordert. Am Gerät noch nicht gegengeprüft.]
10. **Logger ohne Slack** (gefunden 20.10.2026): `loop()` rief `SDLogger_logFrame(fr)` ohne Slack auf, damit gab es im Flug nie ein Sync und der vorab reservierte Platz wurde nur beim Stop gekürzt. Der unskalierte CSV-Export ließ außerdem den letzten der 40 Kanäle weg (`-Wformat-extra-args`). [erledigt 20.10.2026: `LoopTimer_slack_us()` liefert die Restzeit bis zur Deadline an den Logger, Formatstring korrigiert.]

## 6. Nächste Schritte

1. KiCad installieren und ein Projekt `hardware/mainboard/kicad/` anlegen. `mainboard_outline.dxf` als Edge.Cuts importieren.
2. Die offenen Fragen aus `hardware/mainboard/README.md` §9 klären, vor allem Rohr-Innendurchmesser, Länge der Avionik-Sektion, IMU-Bus und die Lage der TVC-Servoachsen zum Schlitten.
3. Schaltplan nach der Spezifikation zeichnen, Review, dann Layout und Bestellung bei JLCPCB mit SMD-Bestückung.
4. Parallel in der Firmware: Pinbelegung in `Config.h` übernehmen, IMU auf SPI1 umstellen, Flugzustandsautomat und Pyro-Logik mit Arming.
5. Befunde 1–4 aus §5 angehen, bevor das erste Mal mit aktiver Regelung geflogen wird.

## 7. Änderungsprotokoll

| Datum | Was |
|---|---|
| 2025-03 | Projektstart: PlatformIO-Projekt `spacecode`, erste TVC- und Schwungrad-Modelle, Strombudget |
| 2025-04 bis 06 | MATLAB-6DOF und PID-Tuning, TVC V2 und dual TVC, Landebeine, Gesamtmodell, Massenbudget, Piston Ejection |
| 2025-10-12 bis 31 | Git-Repo angelegt, Firmware modularisiert, Kalman, SD-Logger, HC-12-Test, Regler. `flight_computer.blend` überarbeitet. |
| 2026-10-15 | `groundcode/` als eigenes Repo ausgeklammert. Projektdatei angelegt. Mainboard rev A spezifiziert (`hardware/mainboard/`), erst rund, dann als Längs-Schlitten neu ausgelegt. Befund 3 korrigiert: Lage nur aus dem Gyro ist richtig. |
| 2026-10-20 | Aufräumrunde für die Veröffentlichung. Repo: `README.md` angelegt, `eLab/` und die maschinenabhängige VS-Code-Datei aus dem Index genommen, PlatformIO-Platzhalter und die auskommentierten Monolithe in `sketches/` gelöscht. Firmware: `Main.ino` → `main.cpp` mit wiederhergestellter Flugschleife, alle Gewinne, Servo-Geometrie, Fenster und Gyro-Offsets in `Config.h`, Regler-Schnittstelle ohne doppelte Integration (`RollOutput`), Slack an den Logger, Gyro-Bit-Fix (Befund 9), CSV-Format-Fix (Befund 10), `lib_deps` auf die genutzten Bibliotheken gekürzt. Test-Sketches als Umgebungen unter `examples/` (`radio_beacon`, `i2c_scanner`, `pyro_mosfet_test`). Alle vier Umgebungen bauen warnungsfrei. Nicht am Gerät getestet. |
