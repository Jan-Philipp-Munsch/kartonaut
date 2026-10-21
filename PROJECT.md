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
| Masse | 981 g im Massenmodell (ein Motor, Landesystem 200 g, zwei Akkus, Kolben-Ausstoß); Budget vom Juni 2025 war 902 g. Gewogen ist noch nichts. | `cad/mass_properties.md`, `Gewicht.csv` |
| TVC | Kardan mit 2× SG90 (Servofenster Yaw 70–115°, Pitch 60–105°). Ersatz bestellt: FrSky Xact W5652H (10 g, 3,7–8,4 V, Hall-Sensor, 15-Zahn-Abtrieb), Kardan muss dafür angepasst werden. | `dual_tvc.blend`, `Control.cpp`, `docs/Plan_2026-10-21.md` §2.2 |
| Hebelarm TVC–Schwerpunkt | 0,37 m im Massenmodell (Start), 0,38 m bei Brennschluss; Firmware und Simulink rechnen noch mit 0,30 m | `cad/mass_properties.md`, `Config.h`, `TVC6DOF.m` |
| Trägheitsmomente | Ixx = Iyy = 0,110 kg·m², Izz = 0,0011 kg·m² (Start). Die Simulation hatte 0,1 auf allen Achsen, das Roll-Moment ist also hundertmal kleiner. | `cad/mass_properties.json` |
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
| Simulation | `simulation/` (dieses Repo, seit 21.10.2026) | Python-Paket `tvcsim`: 1:1-Port des Simulink-6DOF (Dynamik, Schub, Rauschen, Regler, Servo-PT2), zweiter Regler wie `Control.cpp`, Monte-Carlo, PID-Raster, Servo-Fit, 21 Tests. Doku: `simulation/README.md`. Das MATLAB-Original `6DOF_model` bleibt lokal (Simulink, `tf5.mat`, Sprungantworten). |
| Simulation (Vorlage) | lokal, MATLAB-Projekt `BPS_TVC` (nicht im Repo) | MathWorks-Beispiel „simpleTVCRocketModel“ |
| CAD (eigen) | `cad/` (dieses Repo, seit 21.10.2026) | Parametrisches CadQuery-Modell (`params.py`, Module Rumpf/Kardan/Flugcomputer/Kolben/Beine, `build.py` mit STEP/STL-Export, Kollisionsprüfung und Renderbildern), Massenmodell `mass_model.py` → `mass_properties.md/.json`, Inventur der Blender-Dateien `blender_inventory.md`. Doku: `cad/README.md` |
| CAD (Blender, abgelöst) | lokal, Blender-Dateien (nicht im Repo) | `model_rocket` (Gesamtmodell), `flight_computer` (+ `_obj`), `TVC`, `TVC_V2`, `Inner_gimbal(_V2)`, `dual_tvc`, `inner/outer_gimbal_dual_TVC`, `LegConnectors`, `rocket nose`, `flywheel(V2)`, `untitled`/`test123` (Gimbal-Zwischenstände) |
| CAD/Doku (fremd) | lokal, Ordner „Space Mission“ (nicht im Repo) | BPS.space Scout F STEP/OBJ (TVC, Beine, Reaction Wheel, Throttle), BPS-Blip-Platine (Schaltplan, Layout, Code), Piston-Ejection-Bulkheads, `battery7.stl`, `Gewicht.csv`, `Übersicht.ods` (Strombudget) |

Die Blender-Dateien sind in Millimetern modelliert, obwohl die Szene auf „Meter“ steht.
`docs/render_blend.py` rendert eine Ansicht aus einer .blend-Datei, so ist `docs/img/model_rocket.png` entstanden.

## 4. Fortschritt

Status: ✅ fertig · 🟡 in Arbeit · ⬜ offen

| # | Arbeitspaket | Status | Stand / Nachweis |
|---|---|---|---|
| 1 | Konzept, Massen- und Strombudget | ✅ | `Gewicht.csv` (Juni 2025), `Übersicht.ods` (März 2025) |
| 2 | 6DOF-Simulation und PID-Auslegung | 🟡 | MATLAB (Mai/Juni 2025) nach Python portiert (21.10.2026, `simulation/`). Ergebnis: Firmware-Gewinne stabilisieren, Tuner-Gewinne schwingen (Befund 11). Offen: `tf5` aus MATLAB exportieren, W5652H vermessen, Trägheitsmomente aus `cad/`. |
| 3 | TVC-Kardan (CAD) | 🟡 | Mehrere Generationen bis `dual_tvc` (Juni 2025), seit 21.10.2026 parametrisch in `cad/tvc.py` mit W5652H-Taschen, Gegenlager und Ringspiel für ±7°. Druck- und Funktionstest nicht dokumentiert; Servo-Datenblatt (Wellenlage) prüfen. |
| 4 | Rumpf, Spitze, Landebeine (CAD) | 🟡 | `model_rocket.blend` (Juni 2025), seit 21.10.2026 parametrisch in `cad/` mit Klima-Rohr, Kuppler, Klima-Spitze, Kolben und Beinen. Carbonstäbe für die Beine gekauft (2× 5 mm, 4× 3 mm, je 1 m; Conrad Juni 2025). Offen: Einklappmechanismus der Beine. |
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
| 15 | Bodentests (TVC-Prüfstand, Pyro-Test, Funkreichweite) | 🟡 | **TVC-Prüfstand (Idee Jan, Teile seit Juni 2025 da):** Die Rakete hängt dreh- und schwenkbar in einem Gestell, der Drehpunkt liegt im Schwerpunkt. An Stelle des Raketenmotors sitzt ein Brushless-Motor Racerstar BR2814 (1000 KV, Ø 28 mm, passt in den 29-mm-Adapter) mit 11×7- oder 12×6-Propeller im Kardan, ESC 60 A, 4S-LiPo. Der Propeller liefert bei 4S über 15 N, die 12 N des E12 also bei Teilgas; der Teensy kann das Gas über einen freien PWM-Pin fahren und sogar die E12-Schubkurve nachfahren. Damit lässt sich die Lageregelung mit echtem Schubvektor testen, ohne Treibsatz. Zu beachten: Das Reaktionsmoment des Propellers dreht die Rakete um die Rollachse (Rollregler testen oder Rollachse im Gestell sperren), der Beschleunigungssensor sieht im Gestell nur g (die Firmware rechnet `M = l·m·|a|·sin δ` dann mit |a| = g, also wie bei 1 g Schub), Propellerschutz und Abstand sind Pflicht. **Gestell konstruiert (21.10.2026, `cad/testrig.py`):** Sperrholzplatte, zwei Alu-Stützen mit 608-Lagern, Rahmen 20 × 20 auf Achsstummeln (Nicken), zweiteiliger Klemmkragen am Schwerpunkt mit Zapfen in Lagerböcken (Gieren, Rollen gesperrt), Prop-Adapter mit Ø-29-Zapfen und Motorflansch, Schutzkäfig am Rohr; Kollisionsprüfung bei ±20° Rig und ±7° Kardan frei. Bilder `docs/img/cad/testrig*.png`, STEP `cad/export/testrig.step`. Offen: Gurt-Anschläge, Kabel, Gas-Ausgang in der Firmware, BR2814 nachmessen. Pyro-Test mit ca. 1 g Schwarzpulver erfolgreich. Funkreichweite offen. |
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
11. **Reglergewinne, aufgelöst (21.10.2026, Simulation):** Firmware (Kp 5, Ki 0, Kd 1 auf Skala −100) entspricht im Simulink-Regler kp 5, ki 0, kd 0,01 und **stabilisiert** die Rakete in der Brennphase (Kipp < 10°). Die Tuner-Gewinne kp 3,1, ki 5, kd 0,385 haben einen 40-mal größeren D-Anteil: 1 °/s fordert 7° TVC, also sofort die ±5°-Sättigung, und mit Servo-Totzeit und ZOH entsteht ein Grenzzyklus bei 3 bis 4 Hz. Befund 2 ist damit zugunsten der Firmware entschieden; ein kleines Ki (Simulink-ki um 1) würde den statischen Servo-Fehler ausregeln. Warum `pid_tuner.m` 0,385 fand, klärt nur ein Export von `tf5` aus MATLAB.
12. **Schub-Gewichts-Verhältnis (21.10.2026, Simulation):** Mit 0,94 kg Trockenmasse hebt der TSP E12 (12 N mittel, 39 Ns) kaum ab: Gipfel 10 m, Verhältnis 1,2. Mit 0,7 kg sind es 48 m. Das Massenbudget (`Gewicht.csv`: 902 g) muss am Gerät gewogen und gesenkt werden, oder der Motor wird eine Klasse stärker (F). Das Papprohr (240 g für 1 m) ist der größte Posten. [Nachtrag 21.10.2026: mit dem CAD-Massenmodell (1,013 kg Start, Hebelarm 0,37 m, I quer 0,11) kommt `--vehicle cad` auf 9 m Gipfel bei 2 m/s am Brennschluss, Schub-Gewichts-Verhältnis 1,1. Die Brennphase bleibt mit den Firmware-Gewinnen geregelt (Kipp unter 4°), ein Flug ist das aber nicht. Stärkerer Motor (F35) oder weniger Masse.] [Korrektur 21.10.2026 abends: Das Simulink-Modell hat keinen Boden; die Rakete sank in den ersten 0,3 s und nahm ein Geschwindigkeitsdefizit mit. Mit Rampe (`SimParams.ground`) erreicht die 1,0-kg-Rakete **20 m** (Landung 6,3 s), die 0,7-kg-Rakete 62 m. Immer noch knapp: Schub-Gewicht 1,1, Brennschluss bei etwa 10 m/s. Die Entscheidung Masse oder Motor bleibt.]
13. **Servo-Umrechnung (21.10.2026, Simulation):** Mit `SERVO_*_GAIN = 23` und dem Fenster 70 bis 115 Servo-Grad hat die Firmware nur ±0,98° TVC; die Identifikation von 2025 sagt 6 Servo-Grad je TVC-Grad (±3,75°). Am neuen Kardan mit den W5652H messen.
14. **Eigenheiten des Simulink-Modells (21.10.2026):** zwei verschiedene Nominalsätze (`TVC6DOF.m`: I 0,1, l 0,3, m 0,94; PreLoadFcn der `.slx`: I 0,045, l 0,5, m 0,7, kd 0,004), der Beschleunigungssensor misst dort `rdd` statt der spezifischen Kraft, kein Boden, zweite Zündung bei 7,3 s trifft die fallende Rakete. Alles im Python-Port als Schalter nachgebildet und dokumentiert. [erledigt 21.10.2026 abends: Boden eingebaut (Rampe hält, Lauf endet bei der Landung, Plots enden dort); ohne Boden per `--no-ground`. Die Zündung nach Zeit bleibt eine Eigenheit; ein Landebrennen muss aus der Höhe zünden.]
15. **Massenmodell (21.10.2026, CAD):** Stabmodell aus `cad/params.py`: Start 981 g, Schwerpunkt 448 mm über der Düse, Hebelarm Kardan–Schwerpunkt 0,37 m (nicht 0,30), Ixx = Iyy = 0,110 kg·m², **Izz = 0,0011 kg·m²**, also hundertmal kleiner als der Platzhalter 0,1. Für die Rollregelung mit dem Platzhalter wäre die Dynamik um zwei Größenordnungen falsch; `ROLL_K*` in `Config.h` und die Simulation müssen auf den echten Wert. Landesystem (200 g) und Flugcomputer (100 g) sind Vorgaben ohne Konstruktion, alles andere Schätzung; nach dem Zusammenbau wiegen, auswiegen, Bifilarpendel.

## 6. Nächste Schritte

1. Design Guide an den Kollegen, Review-Fragen (§13 dort) klären; Vorab-Bestellung nach `hardware/mainboard/ORDER.md` §1 (ICM-42688-P-Breakout, 1S-Akku, LoRa-DIP für die Bodenstation, Stecker, Pigtail). Dann KiCad installieren und ein Projekt `hardware/mainboard/kicad/` anlegen. `mainboard_outline.dxf` als Edge.Cuts importieren.
2. Die offenen Fragen aus `hardware/mainboard/README.md` §9 klären: Länge der Avionik-Sektion, IMU-Bus und die Lage der TVC-Servoachsen zum Schlitten. Der Rohr-Innendurchmesser ist seit dem 21.10.2026 bekannt (72,6 mm). Dazu die Fragen in `docs/Plan_2026-10-21.md` §6.
3. Schaltplan nach der Spezifikation zeichnen, Review, dann Layout und Bestellung bei JLCPCB mit SMD-Bestückung.
4. Parallel in der Firmware: Pinbelegung in `Config.h` übernehmen, IMU auf SPI1 umstellen, Flugzustandsautomat und Pyro-Logik mit Arming.
5. Befunde 1–4 aus §5 angehen, bevor das erste Mal mit aktiver Regelung geflogen wird.
6. Firmware für rev B: Treiber ICM-42688-P (SPI, ohne DMP), Gyro-Quaternion, BMP390, LoRa-Konfiguration, zwei Akkuspannungen, Watchdog und Zustandsspeicher, Pyro-Logik mit Arming.
7. Parametrisches CAD in `cad/` mit Trägheitsmomenten (Session vom 21.10.2026), danach Kardan für die W5652H anpassen und die Servo-Übertragungsfunktion neu messen.
8. Rakete wiegen und das Massenbudget gegen Befund 12 prüfen, bevor der Motor festgelegt wird.
9. TVC-Prüfstand bauen nach `cad/testrig.py` (konstruiert 21.10.2026): Teile drucken und kaufen (Sperrholz, 2 × Alu 40 × 40, 20 × 20-Profil, 4 × 608, Achsstummel Ø 8, 8-mm-Alurohr für den Käfig), BR2814 nachmessen, Gurt-Anschläge; Gas-Ausgang in der Firmware.

## 7. Änderungsprotokoll

| Datum | Was |
|---|---|
| 2025-03 | Projektstart: PlatformIO-Projekt `spacecode`, erste TVC- und Schwungrad-Modelle, Strombudget |
| 2025-04 bis 06 | MATLAB-6DOF und PID-Tuning, TVC V2 und dual TVC, Landebeine, Gesamtmodell, Massenbudget, Piston Ejection |
| 2025-10-12 bis 31 | Git-Repo angelegt, Firmware modularisiert, Kalman, SD-Logger, HC-12-Test, Regler. `flight_computer.blend` überarbeitet. |
| 2026-10-15 | `groundcode/` als eigenes Repo ausgeklammert. Projektdatei angelegt. Mainboard rev A spezifiziert (`hardware/mainboard/`), erst rund, dann als Längs-Schlitten neu ausgelegt. Befund 3 korrigiert: Lage nur aus dem Gyro ist richtig. |
| 2026-10-20 | Aufräumrunde für die Veröffentlichung. Repo: `README.md` angelegt, `eLab/` und die maschinenabhängige VS-Code-Datei aus dem Index genommen, PlatformIO-Platzhalter und die auskommentierten Monolithe in `sketches/` gelöscht. Firmware: `Main.ino` → `main.cpp` mit wiederhergestellter Flugschleife, alle Gewinne, Servo-Geometrie, Fenster und Gyro-Offsets in `Config.h`, Regler-Schnittstelle ohne doppelte Integration (`RollOutput`), Slack an den Logger, Gyro-Bit-Fix (Befund 9), CSV-Format-Fix (Befund 10), `lib_deps` auf die genutzten Bibliotheken gekürzt. Test-Sketches als Umgebungen unter `examples/` (`radio_beacon`, `i2c_scanner`, `pyro_mosfet_test`). Alle vier Umgebungen bauen warnungsfrei. Nicht am Gerät getestet. Danach: MIT-Lizenz, englisches `README.md` (deutsch als `README.de.md`), lokale Pfade aus dieser Datei entfernt, Repo auf GitHub öffentlich geschaltet. |
| 2026-10-21 | Planungsrunde: `docs/Plan_2026-10-21.md` (Review Mainboard rev A, Bauteilalternativen ICM-42688-P / BMP390 / LoRa E22-400T22D, Kostenschätzung, Portierungsplan der Simulink-Simulation nach Python, Konzept Baudokumentation, Fragen). `docs/BUILD.md` angelegt mit dem Inventar aus den Bestellungen bei Klima (09.06. und 23.10.2025) und Space Rocket Technology (28.04.2025). Dabei geklärt: Rohr innen 72,6 mm, Motor ist der TSP E12-0 (4 Stück), die E12-Schubkurve der Simulation ist die TSP-Kurve. Jan: Funk wird LoRa, Servos FrSky W5652H bestellt. Danach Plan §2.5 (Versorgung: ein 2S-Akku mit Buck-Boost, 20-mΩ-Shunt und Hold-up gegen Neustart im Flug, Platine lässt einen zweiten 1S-Akku zu; Watchdog und Zustandsspeicher in der Firmware) und §2.6 (Layout-Checkliste: Leiterbahnbreiten, verriegelte Stecker, IMU-Platzierung, Funk/GPS-Antennen, Kabel). Portierung der Simulation nach `simulation/` in eigener Session gestartet. Jan entscheidet Variante B: 1S-Akku für die Elektronik, 2S für Servos, Rollmotor und Pyro; Schaltungsstruktur und Strombudget in Plan §2.5. Weitere Entscheidungen: ICM-42688-P, erster Flug mit einem Motor, Pyro-Bergung mit Kolben und Klima-Spitze, Flugcomputer im Kuppler (70,2 mm), CAD-Neuaufbau in eigener Session (`cad/`). Abends: Design Guide `docs/DesignGuide_Mainboard_revB.md` (Markdown und PDF, Abbildungen aus `hardware/mainboard/figures.py`), Bestellplan `hardware/mainboard/ORDER.md` mit LCSC-Prüfung der Hauptbauteile, Elektronik-Zusammenfassung; READMEs auf rev B. Abends: Simulation nach Python portiert (`simulation/`, 21 Tests, Befunde 11–14), Blender-Inventur, Massenmodell und parametrisches CAD in `cad/` (Befund 15), README in beiden Sprachen neu gegliedert (Übersicht, Projektstand, Simulation, Hardware mit Design Guide, CAD, Firmware, Dokumente), Stand auf GitHub und RWTH gepusht. Bestellungen Conrad (Carbonstäbe für die Beine) und Banggood (Prüfstand-Antrieb) ins Inventar aufgenommen, Prüfstand-Idee in Paket 15. Prüfstand als `cad/testrig.py` konstruiert (Gestell, Rahmen, Kragen, Prop-Adapter, Käfig, Kollisionsprüfung, zwei Renderbilder). Simulation: Boden eingebaut, Plots enden bei der Landung; Befund 12 korrigiert (20 m statt 9 m). |
