# Kartonaut

<img src="docs/brand/kartonaut_patch.svg" width="150" align="right" alt="Kartonaut-Abzeichen">

[![Lizenz: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Firmware: PlatformIO / Teensy 4.1](https://img.shields.io/badge/firmware-PlatformIO%20%C2%B7%20Teensy%204.1-orange.svg)](firmware/)
[![Simulation: Python 6DOF](https://img.shields.io/badge/simulation-Python%206DOF-3776AB.svg)](simulation/)
[![CI](https://github.com/Jan-Philipp-Munsch/kartonaut/actions/workflows/ci.yml/badge.svg)](https://github.com/Jan-Philipp-Munsch/kartonaut/actions/workflows/ci.yml)

*English version: [README.md](README.md).*

**Kartonaut** aus Karton und Astronaut: Der Rumpf ist ein Klima-Papprohr. Die Flüge zählen hoch, der Erstflug ist *Kartonaut 1*. Abzeichen und Logo in [`docs/brand/`](docs/brand/).

Eine Modellrakete mit Schubvektorsteuerung (TVC) und selbst entwickeltem Flugcomputer, aufgebaut
nach dem Vorbild der „Scout F“ von [BPS.space](https://bps.space). Der Motor hängt in einem Kardan
mit zwei Servos; ein Teensy 4.1 mit IMU, Barometer, Strommonitor, SD-Logger und 433-MHz-LoRa-Funk
hält die Lage und spricht mit einer Bodenstation, die vom Handy aus bedient wird. Das Gesamtsystem wird
vor dem Flug in einem 6DOF-Modell simuliert. *Kartonaut 1* fliegt auf einer TSP E12, hält während des
Brennens die Lage und kommt am Fallschirm zurück, den eine CO₂-Kartusche ausstößt. Landebeine,
Landebrennen mit zweitem Motor, Rollmotor und Pyro-Kanäle bleiben späteren Flügen vorbehalten und sind
auf der Platine schon vorgesehen.

*Stand: 24.10.2026.*

<img src="docs/img/cad/rocket_overall.png" width="200" align="right" alt="Parametrisches CAD-Modell (CadQuery)">

## Auf einen Blick: *Kartonaut 1*

| | |
|---|---|
| Rumpf | Klima-Papprohr Ø 75 mm (innen 72,6 mm) in drei Modulen (Kardan, Avionik, Bergung), verbunden über halbe Kuppler mit M3-Schrauben, Klima-Kunststoffspitze; 731 mm lang |
| Motor | TSP E12-0, 24 mm, 39 Ns, 12 N mittlerer Schub, 3,5 s Brenndauer, ohne Ausstoßladung; vier vorhanden |
| Startmasse | **705 g** im Massenbudget (Stand 2c), Schwerpunkt 259 mm über der Düse, Hebelarm Kardan–Schwerpunkt 190 mm, Schub-Gewicht 1,7; Ziel unter 750 g erreicht. Noch nichts gewogen |
| Flugcomputer | Teensy 4.1 auf Mainboard **rev B1** (KiCad aus Code, fertig geroutet, DRC sauber, im Review vor der Bestellung): IMU ICM-42688-P, Barometer BMP390, Strommonitor INA239, alle an SPI1; Magnetometer LIS3MDL und SHT40 an I²C; LoRa E22-400T22S, microSD, vier Pyro-Kanäle (zwei bestückt), Stapelstecker |
| Versorgung | zwei Akkus: 1S-LiPo für die Elektronik (Buck-Boost), 2S-LiPo für die Servos; FET-Lastschalter hinter einem mechanischen Schalter, beide in der Rakete ladbar |
| Aktorik | Schubstangen-Kardan mit 2 × FrSky Xact W5652H direkt an 2S (gebaut); ein Servo löst die CO₂-Kartusche aus. Kein Rollmotor beim Erstflug |
| Bergung | 8-g-CO₂-Kartusche drückt die Spitze ab, Fallschirm 125 cm |
| Regelung | Lage aus dem Gyro (Quaternion), PID auf Nick/Gier → Moment → Kardanwinkel über `M = l · T · sin δ`; 100 Hz. Rollen bleibt ungeregelt |
| Simulation | Python-6DOF: mit 705 g trägt eine E12 die Rakete auf etwa 74 m (ohne Luftwiderstand); mit Kp 2 / Ki 1 / Kd 0,45 bleibt die Neigung unter 2,5°, ohne dass der Kardan anschlägt |
| Bodensystem | ESP32-S3-Bodenstation mit Weboberfläche fürs Handy, Zündung über 15 m Leitung mit Schlüssel und ARM-Schalter; Startrampe 600 × 600 mm auf drei verstellbaren Beinen |
| Stand | Kardan und zwei Rohrmodule gebaut, Platine rev B1 bestellfertig, Tischtest-Konsole für rev B1 gemergt; **noch kein Flug** |

## Projektstand

**Erledigt**

- Konzept, Massen- und Strombudget; Rumpfteile, Fallschirm, Motoren, CO₂-Kartuschen und Antrieb des Prüfstands gekauft; Schubstangen-Kardan mit den W5652H gebaut.
- 6DOF-Simulation: MATLAB/Simulink-Modell nach Python portiert, mit 1:1-Kopie des Flugreglers; Fahrzeugsätze aus den CAD-Massenmodellen.
- Firmware-Grundlage: Sensoren, Höhen-Kalman, SD-Logger mit CSV-Export, Regler, Timing, Anzeigen; SPI-Treiber und Pinbelegung für rev B.
- **Firmware für den Tischtest rev B1** ([PR #6](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/6), gemergt 23.10.): Treiber für LIS3MDL, SHT40 und ADXL375, IMU-Selbsttest, Testkonsole `revb_test` mit einem Befehl je Funktion, geführte Kalibrierung (Gyro, sechs Lagen, Magnetometer-Ellipsoid, Achszuordnung, ADC, INA239, Servo-Trimm) mit CRC im EEPROM-Emulat, `bench_test.py` zur Steuerung vom PC, zwölf Versuchsanleitungen.
- CI auf GitHub Actions: alle PlatformIO-Umgebungen, Simulationstests, Host-Tests, Pin-Abgleich gegen die Platine.
- Mainboard rev B: Spezifikation, Design Guide, Datenblatt, KiCad-Projekt aus Code, Zweitmeinungs-Review, Fertigerentscheidung (JLCPCB), Bestellplan, Entscheidungen E1–E10.
- Parametrisches CAD (CadQuery) mit Massenmodell, Prüfstand, Erstflug-Konfiguration; die 16 Blender-Dateien inventarisiert und abgelöst.

**Wartet auf Review und Merge** (Arbeit auf einem Branch fertig, noch nicht in `main`)

| Was | Wo |
|---|---|
| **Mainboard rev B1**: alle Review-Punkte eingearbeitet, Zusatzsensoren, fertig geroutet (DRC 0 Fehler, 0 offen), Gerber/BOM/CPL für JLCPCB, Review-Brief für eine Zweitmeinung | [PR #5](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/5) |
| **Flug-Firmware** B1–B8: Gyro-Quaternion, Zustandsautomat `SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED`, Pyro-Logik, Telemetrieprotokoll, Watchdog mit Zustandsspeicher, Sensor-Backends für Breakouts und rev B, 32 native Tests inkl. Software-in-the-Loop gegen die Simulation | [PR #3](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/3) |
| **Physik-Durchsicht und Landebrennen**: Luftwiderstand, Bodenkontakt, Landebrennen mit zweiter E12, Schubdrossel nach Scout F, in Simulation und Firmware (für den Erstflug abgeschaltet) | [PR #4](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/4) |
| **Versuch E01**: Übertragungsfunktion Servo → Kardan als fertiger Versuch mit Auswerteskript | [PR #2](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/2) |
| **Zusammenführung vom 22.10.**: Bauanleitung *Kartonaut 1* in Modulbauweise (Zeichnungen, Bohrschablonen 1:1, Stückliste), Massenbudget Stand 2b/2c (705 g), Reglergewinne per Bayes-Optimierung, Bodenstation (Konzept, Schaltung, ESP32-S3-Firmware), Startrampe, Budgetplan | Branch [`claude/konsolidierung`](https://github.com/Jan-Philipp-Munsch/kartonaut/tree/claude/konsolidierung) |

**Als Nächstes**

1. Platine prüfen und bestellen: Zweitmeinung zu rev B1, Messbereich der IMU klären (der ICM-42688-P sättigt bei ±16 g, Alternative LSM6DSO32 mit ±32 g), JLCPCB-Angebot mit den rev-B1-Dateien wiederholen und bestellen. Ein Testangebot mit den älteren rev-B-Dateien lag bei etwa 165 $ für zwei bestückte Platinen.
2. Die offenen PRs und die Zusammenführung nach `main` mergen.
3. Rakete nach der Anleitung bauen, wiegen, Schwerpunkt auspendeln, Messwerte in `Config.h`.
4. Tischtest rev B1 mit `revb_test`, dann Bodentests: CO₂-Ausstoß, TVC-Prüfstand mit Propellermotor, Funkreichweite, Startfreigabe vom Handy.
5. Bodenstation und Startrampe bauen.
6. *Kartonaut 1*: geregelter Aufstieg auf einem Motor, Bergung am Fallschirm.

Arbeitspakete, Befunde und Änderungsverlauf stehen in [PROJECT.md](PROJECT.md), das Baulog in
[docs/BUILD.md](docs/BUILD.md), der Plan bis zum Erstflug in [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md).

## Was die Simulation sagt

Das Simulink-Modell (Starrkörper mit Quaternionen, Schubkurve TSP E12, aus Sprungantworten
identifizierte Servo-Übertragungsfunktion, Sensorrauschen, statischer Versatz) liegt in
[`simulation/`](simulation/README.md) als Python-Paket `tvcsim`. Es hat zwei Regler, den aus Simulink
und eine zeilengenaue Portierung von `Control.cpp` aus der Firmware, damit beide im selben Modell
vergleichbar sind.

![Reglervergleich](docs/img/sim/compare_gains_preload.png)

Befunde, die das Projekt verändert haben:

- **Die 1-kg-Rakete war zu schwer für eine E12** (Schub-Gewicht 1,1, Gipfel 20 m). Statt eines
  stärkeren Motors wurde die Rakete leichter: von 981 g (21.10.) über 761 g auf **705 g** für
  *Kartonaut 1*, die im Modell etwa 74 m erreicht.
- **Die leichte Rakete braucht kleinere Gewinne.** Hebelarm und Querträgheit schrumpften auf die Hälfte
  und ein Fünftel. Mit den echten Werten fahren die alten Firmware-Gewinne Kp 5 / Kd 1 den Kardan zwei
  Drittel des Brennens in den Anschlag; Kp 2 / Ki 1 / Kd 0,45 aus einer Bayes-Optimierung regeln sauber.
- **Die Gewinne der MATLAB-Gittersuche waren falsch** (D-Anteil 40-mal zu groß, Kardan im Anschlag,
  Schwingung mit 3 bis 4 Hz).
- **Das Verhältnis Servo zu Kardan entscheidet über die Stellreserve.** Am gebauten Kardan zu messen
  (Versuch E01).
- **Ohne Rollregelung muss die Lage ein Quaternion sein.** Komponentenweise integrierte Winkel legen
  einen Neigungsfehler in die falsche Servoachse, sobald die Rakete rollt. Das ist die Bedingung für den
  Verzicht auf den Rollmotor; die Flug-Firmware in PR #3 setzt es um.

<p>
<img src="docs/img/sim/montecarlo_preload.png" width="48%" alt="Monte-Carlo-Bahnen">
<img src="docs/img/sim/servo_fit.png" width="48%" alt="Servo-Sprungantwort und Fit">
</p>

```bash
cd simulation
python -m pytest tests                 # Tests, auch in der CI
python scripts/run_nominal.py          # Nominalflug -> out/
python scripts/run_montecarlo.py       # 100 Läufe
python scripts/compare_gains.py --vehicle preload
```

## Hardware: Mainboard rev B / B1

Heute hängen alle Sensoren als Breakout-Boards mit Steckbrücken am Teensy, das größte Ausfallrisiko im
Flug. [hardware/mainboard/](hardware/mainboard/README.md) spezifiziert das Mainboard: einen Schlitten
54 × 120 mm mit Teensy-Sockel, der IMU genau auf der Rollachse und allen Steckern an den Stirnseiten.

<img src="hardware/mainboard/kicad/img/render_top.png" width="100%" alt="Mainboard rev B, geroutet, Ansicht von oben">

Das KiCad-Projekt in [hardware/mainboard/kicad/](hardware/mainboard/kicad/README.md) entsteht aus einer
einzigen Python-Beschreibung der Schaltung (`circuit.py`): sieben Schaltplanblätter, ERC ohne Fehler,
ein Platinengenerator mit Umriss, vier Lagen, Netzklassen, Sperrflächen und Freerouting
([Schaltplan-PDF](hardware/mainboard/kicad/out/mainboard_schematic.pdf)). Der
[Design Guide](docs/DesignGuide_Mainboard_revB.md) ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) stellt
den Entwurf mit Abbildungen vor, der [Bestellplan](hardware/mainboard/ORDER.md) listet Teile, Schranken
und Kosten.

Ein [Zweitmeinungs-Review](hardware/mainboard/review_kicad_2026-10-21.md) von rev B fand acht Punkte
(Ausgangskapazität am Buck-Boost, 1S-Unterspannungsschwelle, Hauptschalter im Strompfad, Sicherung je
Akku, Kelvin-Shunt, 2S-Ströme auf der Innenlage). Zusammen mit zehn Entscheidungen
([Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md)) sind sie in **rev B1**
eingeflossen ([PR #5](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/5)):

- **Mechanischer Hauptschalter, Strom über FETs**; Polyfuse je Akku; Kelvin-Shunt mit INA239.
- **Laden in der Rakete**: 1S über USB-C auf der Platine, 2S über eine Balancer-Buchse.
- **Alle Flugsensoren an SPI1** hinter einem CS-Decoder 74HC138, Analogkanäle über einen Mux 74HC4051;
  I²C nur noch für Magnetometer, SHT40 und die Qwiic-Erweiterung.
- **Alle Servos direkt an 2S**, kein 5-V-Wandler.
- **Platz für spätere Flüge**: vier Pyro-Kanäle, vierter Servostecker, ADXL375 (±200 g) als Footprint,
  Stapelstecker `J_STACK`.
- Leistungspfade als Kupferflächen auf der Außenlage, 5-mm-Sperrzone um die IMU; geroutet mit
  Freerouting, eigenem Gitter-Router und von Hand.

Die Firmware passt dazu: [`firmware/lib/mainboard_revb/`](firmware/README.md) enthält Pins, Decoder, Mux
und die Treiber; `check_board_pins.py` vergleicht die Pins mit `circuit.py`, auch in der CI. Rev A und
die Begründung für das Schlittenlayout stehen in [`rev_a_2026-10-15.md`](hardware/mainboard/rev_a_2026-10-15.md).

## CAD-Modell

Die Blender-Dateien sind in [`cad/blender_inventory.md`](cad/blender_inventory.md) inventarisiert und
durch ein parametrisches Modell in CadQuery abgelöst ([`cad/`](cad/README.md)): jedes Maß in
`cad/params.py` mit Quelle, STEP und STL je Baugruppe, Kollisionsprüfung des Kardans bei ±7°, Renders
über Blender headless. Dieselben Parameter speisen ein Massenmodell
([`cad/mass_properties.md`](cad/mass_properties.md)). Die Modulbauweise von *Kartonaut 1* mit ihrem
Massenbudget liegt auf dem Zusammenführungs-Branch.

<p>
<img src="docs/img/cad/rocket_section.png" width="24%" alt="Schnitt: Motor, Kardan, Flugcomputer, Fallschirm, Spitze">
<img src="docs/img/cad/rocket_tvc.png" width="37%" alt="Kardan mit den zwei W5652H, ausgelenkt um 5° und 4°">
<img src="docs/img/cad/rocket_avionics.png" width="37%" alt="Flugcomputer-Modul">
</p>

```bash
python -m pip install --user cadquery
python cad/build.py              # STEP/STL nach cad/export/, Renders nach docs/img/cad/
python cad/mass_model.py         # mass_properties.md und .json
```

## Bodentests

Bevor etwas fliegt, wird die Lageregelung am Boden mit echtem Schub und ohne Raketenmotor getestet: Die
Rakete hängt in einem Gestell, das Nicken und Gieren um den Schwerpunkt erlaubt, und ein Brushless-Motor
(Racerstar BR2814, 1000 KV, 11-Zoll-Propeller, 4S-LiPo) sitzt anstelle des Raketenmotors im Kardan. In
Teillast liefert er die 12 N der E12. Der Antrieb ist gekauft, das Gestell in
[`cad/testrig.py`](cad/README.md) konstruiert und auf Kollisionen geprüft. Dazu kommen der Test des
CO₂-Ausstoßes, die Funkreichweite mit zwei E22-Modulen und der Freigabetest vom Handy bis zu einem
Lämpchen an der Zündleitung. Die Versuche für die Platine stehen in
[`firmware/Versuche_revB1.md`](firmware/Versuche_revB1.md).

<p>
<img src="docs/img/cad/testrig.png" width="40%" alt="Prüfstand: Rakete im zweiachsigen Rahmen">
<img src="docs/img/cad/testrig_drive.png" width="52%" alt="Antriebsseite: Propellermotor im Kardan mit Schutzkäfig">
</p>

## Firmware

PlatformIO-Projekt für den Teensy 4.1 in [`firmware/`](firmware/README.md). Die Hauptschleife läuft mit
festen 100 Hz: Sensoren lesen, Lage aus dem Gyro integrieren, Höhe mit einem Kalman-Filter mit zwei
Zuständen schätzen (Barometer und Vertikalbeschleunigung), Nick und Gier über den Kardan regeln, je
Durchlauf einen Rahmen auf die SD-Karte schreiben.

```bash
cd firmware
pio run                            # Flug-Firmware bauen
pio run -t upload                  # Teensy 4.1 flashen
pio device monitor                 # serielle Konsole, 115200 Baud, Teleplot-kompatibel
pio run -e revb_test -t upload     # Tischtest-Konsole für Mainboard rev B1
python tools/bench_test.py         # Konsole vom PC aus steuern, Bericht als Markdown + JSON
python tools/check_board_pins.py   # Firmware-Pins gegen circuit.py
```

Der Tischtest Schritt für Schritt steht in [`firmware/Tischtest_revB1.md`](firmware/Tischtest_revB1.md).
Alle Pins, Gewinne, Filterkonstanten und Debug-Schalter liegen in
[`firmware/src/Config.h`](firmware/src/Config.h); die Regler bleiben dort bis zum ersten Flugtest aus.
Quaternion-Lage, Zustandsautomat, Pyro-Logik, Telemetrie und Watchdog sind in
[PR #3](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/3).

## Aufbau des Repositorys

```
firmware/               Flug-Firmware (PlatformIO, Teensy 4.1)                -> firmware/README.md
  src/                  Module: Sensors, KalmanZ, Control, SDLogger, Timing, Indicators
  lib/mainboard_revb/   Pins, CS-Decoder, Mux, Treiber ICM-42688-P, BMP390, INA239, LIS3MDL, SHT40, ADXL375
  lib/calstore/         Kalibrierdaten mit CRC, Ellipsoid-Fit, Achszuordnung
  examples/             Testprogramme (revb_test, revb_bringup, Funkbake, I2C-Scan, Pyro-MOSFET)
  tools/                bench_test.py, capture_tvc.py, check_board_pins.py
  test/host/            Host-Tests (g++), laufen in der CI
simulation/             6DOF-Simulation in Python, Paket tvcsim               -> simulation/README.md
hardware/mainboard/     Mainboard: Spezifikation, Entscheidungen, KiCad aus Code, Datenblatt, Reviews, Bestellplan
cad/                    parametrisches CAD, Prüfstand, Massenmodell           -> cad/README.md
docs/                   Design Guide, Baulog, Pläne, Recherchen, Bilder, Abzeichen
.github/workflows/      CI: PlatformIO-Umgebungen, Simulationstests, Host-Tests, Pin-Abgleich
PROJECT.md              Projektdatei: Eckdaten, Arbeitspakete, Befunde, Änderungsverlauf
```

Die alte Bodenstation (Arduino Nano mit HC-12) ist ein eigenes Repository,
[kartonaut-ground](https://github.com/Jan-Philipp-Munsch/kartonaut-ground); ihr Nachfolger auf dem
ESP32-S3 liegt auf dem Zusammenführungs-Branch. Das MATLAB/Simulink-Original der Simulation und die
Blender-Dateien bleiben außerhalb dieses Repositorys; ihr Inhalt ist hierher portiert.

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [PROJECT.md](PROJECT.md) | Eckdaten, Arbeitspakete mit Stand, Befunde, nächste Schritte, Änderungsverlauf |
| [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md) | Plan bis zum Erstflug: Arbeitsstränge Platine, Firmware, Mechanik, Bodensysteme, Meilensteine |
| [docs/BUILD.md](docs/BUILD.md) | Ist-Stand: gekaufte und gedruckte Teile, Mechanik, Verkabelung, Tests, Baulog |
| [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md) | Schnittstellen Rakete/Rampe, Zündleitung, Funk, Handy |
| [docs/Rohrmaterial_2026-10-22.md](docs/Rohrmaterial_2026-10-22.md) | Faserverbundrohre gegen Pappe: Pappe bleibt |
| [docs/Plan_2026-10-21.md](docs/Plan_2026-10-21.md) | Planungsrunde vom 21.10.: Platinen-Review, Versorgungsarchitektur, Portierungsplan |
| [hardware/mainboard/README.md](hardware/mainboard/README.md) | Spezifikation des Mainboards |
| [hardware/mainboard/Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md) | Entscheidungen E1–E10, Bauteile nach Schiene und Schnittstelle, Pinbudget |
| [docs/DesignGuide_Mainboard_revB.md](docs/DesignGuide_Mainboard_revB.md) | der Entwurf rev B mit Abbildungen ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) |
| [hardware/mainboard/datasheet/](hardware/mainboard/datasheet/) | Datenblatt MS-MB-B (LaTeX, Stückliste aus `circuit.py`) |
| [hardware/mainboard/ORDER.md](hardware/mainboard/ORDER.md) | Bestellplan: jetzt zu kaufende Teile, Schranken, JLCPCB-Parameter, Kosten |
| [hardware/mainboard/review_kicad_2026-10-21.md](hardware/mainboard/review_kicad_2026-10-21.md) | Zweitmeinungs-Review von rev B |
| [hardware/mainboard/Fertiger_2026-10-21.md](hardware/mainboard/Fertiger_2026-10-21.md) | Fertigervergleich und Entscheidung |
| [firmware/README.md](firmware/README.md) | Firmware-Module, Logformat, Testprogramme, rev-B-Bibliothek |
| [firmware/Tischtest_revB1.md](firmware/Tischtest_revB1.md) | Tischtest rev B1: Ablauf, Befehle, offene Fragen |
| [firmware/Versuche_revB1.md](firmware/Versuche_revB1.md) | zwölf Versuchsanleitungen mit Geräten, Aufbau, Sollwerten |
| [simulation/README.md](simulation/README.md) | Modell, Koordinaten, Annahmen, Ergebnisse |
| [cad/README.md](cad/README.md) | parametrisches Modell, Prüfstand, Pflegekonzept |
| [cad/mass_properties.md](cad/mass_properties.md) | Massenmodell der früheren Konfigurationen |
| [cad/blender_inventory.md](cad/blender_inventory.md) | was die 16 Blender-Dateien enthalten |

## Lizenz

[MIT](LICENSE). Die BPS.space-Scout-F-Dateien, die als Vorlage dienten, sind nicht Teil dieses Repositorys.
