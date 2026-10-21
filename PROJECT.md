# Mission Space – Projektdatei

Die zentrale Übersicht über das Raketenprojekt: was es gibt, wo es liegt, wie weit es ist
und was als Nächstes kommt. **Bei jedem Arbeitsschritt hier den Fortschritt und das
Änderungsprotokoll nachtragen.**

Stand: 2026-10-21

<img src="docs/img/model_rocket.png" width="260" align="right" alt="model_rocket.blend">

## 1. Ziel

Eine Modellrakete mit Schubvektorsteuerung (TVC), aufgebaut nach dem Vorbild von BPS.space
„Scout F“. Sie fliegt mit kardanisch aufgehängtem Motor, Rollregelung über ein Schwungrad
bzw. einen Rollmotor, Fallschirmbergung und Landebeinen. An Bord sitzt ein selbst
programmierter Flugcomputer (Teensy 4.1) mit Funk-Telemetrie zur Bodenstation.

## 2. Eckdaten (Ist-Stand aus Modellen und Code)

| Größe | Wert | Quelle |
|---|---|---|
| Rumpf | Klima-Rohr Ø 75 mm außen, **72,6 mm innen**, 120 g je 0,5 m; 1000 mm lang (2× 0,5 m + Kuppler 72,4/70,2 × 150 mm) | Bestellungen Klima/SRT 2025, `docs/BUILD.md` §1 |
| Spitze | Klima-Kunststoffspitze 75 mm (Artikel 8539), lose aufgesteckt, Fallschirm darin; ersetzt die gedruckte, federgelagerte Spitze (Ø 80 mm, 99 mm) aus `rocket nose.blend` | Klima 23.10.2025, Jan 21.10.2026 |
| Motor | **TSP E12-0** (24 mm, 39 Ns, 28 g Treibstoff, 64 g, Brennschluss 3,55 s, ohne Ausstoßladung), 4 Stück vorhanden, im 29→24-mm-Adapter. Die E12-Schubkurve der Simulation ist diese TSP-Kurve; F35 liegt daneben. | SRT 28.04.2025, thrustcurve.org, `TVC.blend`, MATLAB `6DOF_model` |
| Masse | 902 g geplant (2× E12, Landesystem 200 g) | `Gewicht.csv` |
| TVC | Kardan mit 2× SG90 (Servofenster Yaw 70–115°, Pitch 60–105°). Ersatz bestellt: FrSky Xact W5652H (10 g, 3,7–8,4 V, Hall-Sensor, 15-Zahn-Abtrieb), Kardan muss dafür angepasst werden. | `dual_tvc.blend`, `Control.cpp`, `docs/Plan_2026-10-21.md` §2.2 |
| Hebelarm TVC–Schwerpunkt | 0,30 m | `Config.h`, `TVC6DOF.m` |
| Flugcomputer | Ring-Stack Ø 69 mm, 8 M2-Stangen, **im Kuppler (innen 70,2 mm)**, als Modul herausziehbar. Mainboard rev B als Längs-Schlitten 54 × 120 mm | `flight_computer.blend`, `hardware/mainboard/` |
| Akku | **Zwei Akkus (entschieden 21.10.2026):** 2S LiPo für Servos, Rollmotor und Pyro; 1S LiPo für Teensy, Sensorik, Funk und GPS über einen Buck-Boost. Ein zweipoliger Hauptschalter schaltet beide. | `docs/Plan_2026-10-21.md` §2.5, `flight_computer.blend` („Battery 7.4V“) |
| Funk | HC-12 (433 MHz), 9600 Bd | `Config.h`, `Radio_test.cpp` |

## 3. Wo liegt was

| Bereich | Ort | Inhalt |
|---|---|---|
| Flug-Firmware | `spacecode/` (dieses Repo) | PlatformIO, Teensy 4.1. `src/` ist modular: main, Config, Sensors, KalmanZ, Control, SDLogger, Timing, Indicators. `examples/` enthält Test-Sketches als eigene PlatformIO-Umgebungen (Funk-Beacon, I²C-Scan, Pyro-MOSFET). Die alten Monolithe (`sketches/`) sind seit dem 20.10.2026 nur noch in der Git-Historie (bis Commit `3b152c9`). Doku: `spacecode/README.md`. |
| Bodenstation | `groundcode/` | Eigenes Repo (`git.rwth-aachen.de:jan_philipp.munsch/space`), hier per `.gitignore` ausgeklammert. Arduino Nano mit HC-12-Empfänger, MPU6050-Test, Fan-ESC-Test. |
| Mainboard | `hardware/mainboard/` | Spezifikation rev B (`README.md`), Bestellplan mit Teilestatus, Toren und Kosten (`ORDER.md`), Umriss-DXF, Platzierungsplan, Abbildungen (`figures.py` → `img/`). Design Guide mit Abbildungen für Review und GitHub: `docs/DesignGuide_Mainboard_revB.md` (+ PDF, `docs/build_design_guide.py`). Rev A: `rev_a_2026-10-15.md`, Review: `docs/Plan_2026-10-21.md` §2 |
| Baudokumentation | `docs/BUILD.md` | Inventar (Bestellungen, Elektronik, Drucke), Mechanik, Verdrahtung as-built, Software-Stand, Tests, Bautagebuch, Regeln. Angelegt 21.10.2026, viele `[?]` |
| Planung 21.10.2026 | `docs/Plan_2026-10-21.md` | Platinen-Review mit Kosten, Portierung der Simulation nach Python, Baudokumentation, offene Fragen |
| Elektronik-Notizen | `eLab/` (lokal, per `.gitignore` ausgeklammert) | OneNote-Abschnitt (HC-12-Modul, 14.10.2025) |
| Simulation | lokal, MATLAB-Projekt `6DOF_model` (nicht im Repo) | Simulink-6DOF mit Monte-Carlo (`TVC6DOF.m`), PID-Suche (`pid_tuner.m`), Servo-Systemidentifikation, Schubkurven E12/F35 |
| Simulation (Vorlage) | lokal, MATLAB-Projekt `BPS_TVC` (nicht im Repo) | MathWorks-Beispiel „simpleTVCRocketModel“ |
| CAD (eigen) | lokal, Blender-Dateien (nicht im Repo) | `model_rocket` (Gesamtmodell), `flight_computer` (+ `_obj`), `TVC`, `TVC_V2`, `Inner_gimbal(_V2)`, `dual_tvc`, `inner/outer_gimbal_dual_TVC`, `LegConnectors`, `rocket nose`, `flywheel(V2)`, `untitled`/`test123` (Gimbal-Zwischenstände) |
| CAD/Doku (fremd) | lokal, Ordner „Space Mission“ (nicht im Repo) | BPS.space Scout F STEP/OBJ (TVC, Beine, Reaction Wheel, Throttle), BPS-Blip-Platine (Schaltplan, Layout, Code), Piston-Ejection-Bulkheads, `battery7.stl`, `Gewicht.csv`, `Übersicht.ods` (Strombudget) |

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
| 5 | Bergung (Piston Ejection) | 🟡 | Entschieden 21.10.2026: Pyro-Ausstoß, Kolben aus einem Kuppler, Fallschirm in der Klima-Spitze. Pyro-Tests mit ca. 1 g Schwarzpulver erfolgreich. Fallschirm (125 cm), Kevlar- und Gummischnur gekauft. Pyro-Logik in der Firmware fehlt. |
| 6 | Flugcomputer-Mechanik (Ring-Stack) | 🟡 | `flight_computer.blend` (13.10.2025), `battery7.stl` |
| 7 | Sensorik: IMU (DMP), Barometer, INA219 | ✅ | `Sensors.cpp` (Okt. 2025) |
| 8 | Höhenschätzung (Kalman z/vz) | ✅ | `KalmanZ.cpp`, Commit „kalman filter optimization“ |
| 9 | SD-Logger (Binär → CSV) | ✅ | `SDLogger.cpp`, Commit „Logger Implementation“ |
| 10 | Regler Pitch/Yaw und Roll | 🟡 | Commit „Controls under control“ (21.10.2025). In `Config.h` sind beide aus. Ein Flugtest steht aus. |
| 11 | Funkstrecke HC-12 | 🟡 | Beacon-Test Teensy → Nano (Okt. 2025). Ein echtes Telemetrieprotokoll fehlt. |
| 12 | GPS | ⬜ | Nur ein früherer Testsketch (TinyGPSPlus-Beispiel, Git-Historie bis `3b152c9`) |
| 13 | Flugzustandsautomat (Pad → Boost → Coast → Apogäum → Bergung → Landung) | ⬜ | Gibt es noch nicht. Die Flugschleife in `main.cpp` läuft wieder (seit 20.10.2026), der MOSFET-Test ist nach `examples/pyro_mosfet_test/` gewandert. |
| 14 | **Mainboard rev B (Platine statt Breakouts)** | 🟡 | Rev A spezifiziert 15.10.2026 (Längs-Schlitten 54 × 120 mm, Akku im Träger darunter). Rev B entschieden 21.10.2026: zwei Akkus (1S Elektronik über TPS63070, 2S Aktoren und Pyro), ICM-42688-P an SPI1, BMP390, LoRa E22-400T22D, W5652H direkt am 2S, 20-mΩ-Shunt, beide Pyro-Kanäle → `hardware/mainboard/README.md`. 21.10. abends: Design Guide (`docs/DesignGuide_Mainboard_revB.md`, PDF) mit Blockschaltbild, Versorgungsbaum, Pyro-Kanal, Pinbelegung, Einbau-Längsschnitt; Bestellplan `hardware/mainboard/ORDER.md` (Vorab-Bestellliste, Tore, JLCPCB-Parameter, LCSC-Status: BMP390 zuletzt ohne Bestand → BMP388 pinkompatibel, TPS63070 schwankt, ca. 8–10 Extended-Typen; Platinenlauf ca. 120–180 €). Als Nächstes: Review durch Kollegen, Vorab-Bestellung (ORDER §1), KiCad. |
| 15 | Bodentests (Servo-Schubstand, Pyro-Test, Funkreichweite) | ⬜ | |
| 16 | Erstflug | ⬜ | Entschieden 21.10.2026: erst geregelter Aufstieg mit einem Motor und Fallschirm; Landung mit zweitem Motor danach. |

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

1. Design Guide an den Kollegen, Review-Fragen (§13 dort) klären; Vorab-Bestellung nach `hardware/mainboard/ORDER.md` §1 (ICM-42688-P-Breakout, 1S-Akku, LoRa-DIP für die Bodenstation, Stecker, Pigtail). Dann KiCad installieren und ein Projekt `hardware/mainboard/kicad/` anlegen. `mainboard_outline.dxf` als Edge.Cuts importieren.
2. Die offenen Fragen aus `hardware/mainboard/README.md` §9 klären: Länge der Avionik-Sektion, IMU-Bus und die Lage der TVC-Servoachsen zum Schlitten. Der Rohr-Innendurchmesser ist seit dem 21.10.2026 bekannt (72,6 mm). Dazu die Fragen in `docs/Plan_2026-10-21.md` §6.
3. Schaltplan nach der Spezifikation zeichnen, Review, dann Layout und Bestellung bei JLCPCB mit SMD-Bestückung.
4. Parallel in der Firmware: Pinbelegung in `Config.h` übernehmen, IMU auf SPI1 umstellen, Flugzustandsautomat und Pyro-Logik mit Arming.
5. Befunde 1–4 aus §5 angehen, bevor das erste Mal mit aktiver Regelung geflogen wird.
6. Firmware für rev B: Treiber ICM-42688-P (SPI, ohne DMP), Gyro-Quaternion, BMP390, LoRa-Konfiguration, zwei Akkuspannungen, Watchdog und Zustandsspeicher, Pyro-Logik mit Arming.
7. Parametrisches CAD in `cad/` mit Trägheitsmomenten (Session vom 21.10.2026), danach Kardan für die W5652H anpassen und die Servo-Übertragungsfunktion neu messen.

## 7. Änderungsprotokoll

| Datum | Was |
|---|---|
| 2025-03 | Projektstart: PlatformIO-Projekt `spacecode`, erste TVC- und Schwungrad-Modelle, Strombudget |
| 2025-04 bis 06 | MATLAB-6DOF und PID-Tuning, TVC V2 und dual TVC, Landebeine, Gesamtmodell, Massenbudget, Piston Ejection |
| 2025-10-12 bis 31 | Git-Repo angelegt, Firmware modularisiert, Kalman, SD-Logger, HC-12-Test, Regler. `flight_computer.blend` überarbeitet. |
| 2026-10-15 | `groundcode/` als eigenes Repo ausgeklammert. Projektdatei angelegt. Mainboard rev A spezifiziert (`hardware/mainboard/`), erst rund, dann als Längs-Schlitten neu ausgelegt. Befund 3 korrigiert: Lage nur aus dem Gyro ist richtig. |
| 2026-10-20 | Aufräumrunde für die Veröffentlichung. Repo: `README.md` angelegt, `eLab/` und die maschinenabhängige VS-Code-Datei aus dem Index genommen, PlatformIO-Platzhalter und die auskommentierten Monolithe in `sketches/` gelöscht. Firmware: `Main.ino` → `main.cpp` mit wiederhergestellter Flugschleife, alle Gewinne, Servo-Geometrie, Fenster und Gyro-Offsets in `Config.h`, Regler-Schnittstelle ohne doppelte Integration (`RollOutput`), Slack an den Logger, Gyro-Bit-Fix (Befund 9), CSV-Format-Fix (Befund 10), `lib_deps` auf die genutzten Bibliotheken gekürzt. Test-Sketches als Umgebungen unter `examples/` (`radio_beacon`, `i2c_scanner`, `pyro_mosfet_test`). Alle vier Umgebungen bauen warnungsfrei. Nicht am Gerät getestet. Danach: MIT-Lizenz, englisches `README.md` (deutsch als `README.de.md`), lokale Pfade aus dieser Datei entfernt, Repo auf GitHub öffentlich geschaltet. |
| 2026-10-21 | Planungsrunde: `docs/Plan_2026-10-21.md` (Review Mainboard rev A, Bauteilalternativen ICM-42688-P / BMP390 / LoRa E22-400T22D, Kostenschätzung, Portierungsplan der Simulink-Simulation nach Python, Konzept Baudokumentation, Fragen). `docs/BUILD.md` angelegt mit dem Inventar aus den Bestellungen bei Klima (09.06. und 23.10.2025) und Space Rocket Technology (28.04.2025). Dabei geklärt: Rohr innen 72,6 mm, Motor ist der TSP E12-0 (4 Stück), die E12-Schubkurve der Simulation ist die TSP-Kurve. Jan: Funk wird LoRa, Servos FrSky W5652H bestellt. Danach Plan §2.5 (Versorgung: ein 2S-Akku mit Buck-Boost, 20-mΩ-Shunt und Hold-up gegen Neustart im Flug, Platine lässt einen zweiten 1S-Akku zu; Watchdog und Zustandsspeicher in der Firmware) und §2.6 (Layout-Checkliste: Leiterbahnbreiten, verriegelte Stecker, IMU-Platzierung, Funk/GPS-Antennen, Kabel). Portierung der Simulation nach `simulation/` in eigener Session gestartet. Jan entscheidet Variante B: 1S-Akku für die Elektronik, 2S für Servos, Rollmotor und Pyro; Schaltungsstruktur und Strombudget in Plan §2.5. Weitere Entscheidungen: ICM-42688-P, erster Flug mit einem Motor, Pyro-Bergung mit Kolben und Klima-Spitze, Flugcomputer im Kuppler (70,2 mm), CAD-Neuaufbau in eigener Session (`cad/`). Abends: Design Guide `docs/DesignGuide_Mainboard_revB.md` (Markdown und PDF, Abbildungen aus `hardware/mainboard/figures.py`), Bestellplan `hardware/mainboard/ORDER.md` mit LCSC-Prüfung der Hauptbauteile, Elektronik-Zusammenfassung; READMEs auf rev B. |
