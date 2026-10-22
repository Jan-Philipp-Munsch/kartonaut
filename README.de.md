# Kartonaut

<img src="docs/brand/kartonaut_patch.svg" width="150" align="right" alt="Kartonaut-Abzeichen">

[![Lizenz: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Firmware: PlatformIO / Teensy 4.1](https://img.shields.io/badge/firmware-PlatformIO%20%C2%B7%20Teensy%204.1-orange.svg)](firmware/)
[![Simulation: Python 6DOF](https://img.shields.io/badge/simulation-Python%206DOF-3776AB.svg)](simulation/)
[![CI](https://github.com/Jan-Philipp-Munsch/kartonaut/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

*English version: [README.md](README.md).*

**Kartonaut** aus Karton und Astronaut: Der Rumpf ist ein Klima-Papprohr. Die Flüge zählen hoch, der Erstflug ist *Kartonaut 1*. Abzeichen und Logo in [`docs/brand/`](docs/brand/).

Eine Modellrakete mit Schubvektorsteuerung (TVC) und selbst entwickeltem Flugcomputer, aufgebaut
nach dem Vorbild der „Scout F“ von [BPS.space](https://bps.space). Der Motor hängt in einem Kardan
mit zwei Servos, ein Teensy 4.1 mit IMU, Barometer, Strommonitor, SD-Logger und 433-MHz-LoRa-Funk
regelt die Lage und spricht mit einer Bodenstation, die ein Handy bedient. Das Gesamtsystem wird
vor dem Flug in einem 6DOF-Modell simuliert. *Kartonaut 1* fliegt mit einem TSP E12, hält die Lage
in der Brennphase und kommt am Fallschirm zurück, den eine CO₂-Kapsel ausstößt. Landebeine, ein
zweiter Motor für das Landebrennen, Rollmotor und Pyro-Kanäle sind für spätere Flüge vorgesehen
und auf der Platine schon angelegt.

<img src="docs/img/bauanleitung/Z1_uebersicht.png" width="260" align="right" alt="Kartonaut 1 in Modulbauweise: Übersichtszeichnung">

## Auf einen Blick: *Kartonaut 1* (Stand 2b, 22.10.2026)

| | |
|---|---|
| Rumpf | Klima-Papprohr Ø 75 mm (innen 72,6 mm) in drei Modulen: Rohr A 125 mm (Kardan), Rohr B 176 mm (Avionik), Rohr C 195 mm (Bergung); zwei halbe Kuppler 75 mm, Klima-Kunststoffspitze. Gesamtlänge 731 mm. Alle Radialschrauben M3 auf 0°/90°/180°/270° |
| Motor | TSP E12-0, 24 mm, 39 Ns, 12 N mittel, 3,5 s Brenndauer, ohne Ausstoßladung; vier Stück vorhanden |
| Startmasse | **723 g** im Massenbudget Stand 2b ([`cad/mass_stand2b.md`](cad/mass_stand2b.md)), Schwerpunkt 256 mm über der Düse, Hebelarm Kardan–Schwerpunkt 186 mm, Schub-Gewicht 1,7; das 750-g-Ziel ist mit 27 g Reserve erreicht. Gewogen ist noch nichts |
| Flugcomputer | Teensy 4.1 auf dem Mainboard rev B (KiCad aus Code, geroutet, Review und Entscheidungen E1–E10 werden eingearbeitet): IMU ICM-42688-P, Barometer BMP390, Strommonitor INA239, alle an SPI1; LoRa E22-400T22S, microSD, vier Pyro-Kanäle (zwei bestückt), Stapelstecker für Zusatzplatinen |
| Versorgung | zwei Akkus: 1S-LiPo für die Elektronik (Buck-Boost), 2S LemonRC 450 mAh für Servos; FET-Lastschalter hinter einem mechanischen Schalter, beide Akkus werden in der Rakete geladen |
| Aktoren | Schubstangen-Kardan mit 2 × FrSky Xact W5652H direkt am 2S (gebaut und in Rohr A eingepasst); ein Servo löst die CO₂-Kapsel aus. Kein Rollmotor beim Erstflug |
| Bergung | CO₂-Kapsel 8 g (ca. 2 l) drückt die Spitze ab, Fallschirm 125 cm (gepackt 100 × Ø 70) liegt in Rohr C, Schockschnur im Spitzen-Kuppler |
| Regelung | Lage nur aus dem Gyro, PID auf Pitch/Yaw → Moment → Kardanwinkel über `M = l · T · sin δ`; 100 Hz. Roll bleibt ungeregelt, dafür muss die Lage als Quaternion gerechnet werden (TODO vor dem Erstflug) |
| Simulation | Python-6DOF (Port des Simulink-Modells): mit 723 g trägt der E12 die Rakete auf etwa 63 m, Kippwinkel in der Brennphase unter 2° mit den Firmware-Gewinnen |
| Bodensystem | Bodenstation ESP32-S3 mit Weboberfläche fürs Handy, Zündung über 15 m Leitung mit Schlüssel, ARM und Relais; Startrampe 600 × 600 mm mit drei verstellbaren Beinen, 6,5 kg, ca. 86 € |
| Status | Kardan, Rohr A und Rohr B gebaut; Platine in Arbeit, Druckteile und Bestellliste der Bauanleitung stehen; noch kein Flug |

## Projektstand

**Fertig**

- Konzept, Massen- und Strombudget; Rumpfteile, Fallschirm, Motoren, CO₂-Kapseln und Prüfstand-Antrieb gekauft; Kardan mit den W5652H gebaut.
- 6DOF-Simulation: MATLAB/Simulink-Modell nach Python portiert, mit 1:1-Kopie des Flugreglers, 25 Tests; Fahrzeugsätze aus beiden CAD-Massenmodellen.
- Firmware-Module: Sensorik, Höhen-Kalman, SD-Logger mit CSV-Export, Pitch/Yaw- und Rollregler, Takt, Signalgeber; SPI-Treiber, Pinbelegung und Inbetriebnahme-Programm für rev B; CI baut alle Umgebungen.
- Mainboard rev B: Spezifikation, Design Guide, Datenblatt (17 Seiten), KiCad-Projekt aus Code (ERC und DRC sauber, geroutet), Zweitmeinung-Review, Fertiger-Entscheidung, Bestellplan; Entscheidungen vom 22.10. (E1–E10) dokumentiert.
- Parametrisches CAD (CadQuery) mit Massenmodell für die Konfigurationen `voll` und `erstflug`; Modulbauweise Stand 2b mit Druckteilen, Gesamtmodell (STEP/GLB) und Massenbudget.
- **Bauanleitung *Kartonaut 1*** in Modulbauweise mit Zeichnungen, 1:1-Bohrschablonen, Teile-Checkliste, Bauschritten, Wartung und Kabelplan.
- **Bodenstation** (Konzept, Sicherheitskonzept, Schaltung, Stückliste, ESP32-S3-Firmware mit Weboberfläche) und **Startrampe** (CAD mit Prüfung gegen die Rakete, Stückliste) als eigenständige Teilprojekte; Schnittstellen Rakete/Pad/Station/Handy festgelegt; Budgetplan bis zum Erstflug.

**In Arbeit**

- Platine rev B1: Review-Punkte A1–A8 und Entscheidungen E1–E10 (FET-Lastschalter, Laden in der Rakete, BMP390 und INA239 an SPI, alle Servos am 2S, vier Pyro-Kanäle, kein 5-V-Buck, Stapelstecker, CS-Decoder und Analogmux) einarbeiten, neu routen, Fertigungsdaten.
- Bauanleitung: Druckteile drucken und wiegen, Bestellung (Reichelt, Berrybase, Ebyte, Schrauben), CO₂-Modul konstruieren, Servo-Umrechnung am gebauten Kardan messen.
- Firmware: Gyro-Quaternion mit Oben-Vektor, Flugzustandsautomat, Telemetrieprotokoll (gemeinsamer Header mit der Bodenstation), Watchdog.

**Als Nächstes**

1. Platine fertigstellen, Papierprobe im Kuppler, Bestellung bei JLCPCB nach Freigabe; parallel die Tischteile bestellen.
2. Rakete nach der Bauanleitung aufbauen, wiegen, Schwerpunkt auswiegen, `Config.h` auf die gemessenen Werte setzen.
3. Bodentests: CO₂-Ausstoß (dreimal, auch kalt), TVC-Prüfstand mit Propellermotor im Kardan, Funkreichweite mit zwei E22, Startsperre Ende zu Ende vom Handy.
4. Bodenstation und Startrampe bauen (ca. 80 € und 86 €, je ein Abend bis Wochenende).
5. *Kartonaut 1*: geregelter Aufstieg mit einem Motor, Fallschirmbergung. Startplatz, Erlaubnis und Versicherung vorher klären.

Die vollständige Liste der Arbeitspakete, die Befunde und das Änderungsprotokoll stehen in
[PROJECT.md](PROJECT.md), das Bautagebuch in [docs/BUILD.md](docs/BUILD.md), der Plan bis zum
Erstflug mit Meilensteinen in [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md), das Budget in
[docs/Budget_2026-10-22.md](docs/Budget_2026-10-22.md).

## Bauanleitung: *Kartonaut 1* in Modulbauweise

[docs/Bauanleitung_Kartonaut1.md](docs/Bauanleitung_Kartonaut1.md) (auch als
[PDF](docs/bauanleitung/Bauanleitung_Kartonaut1.pdf)) beschreibt, wie der Erstflieger aus dem gebauten
Kardan entsteht. Vier Module, drei Trennstellen mit je vier M3 in Muttern-Taschen:

| Modul | Inhalt |
|---|---|
| M1 Antrieb | Rohr A 125 mm mit dem Schubstangen-Kardan, zwei W5652H, Motor bündig unten |
| M2 Avionik | Rohr B 176 mm, Kuppler J1 mit Schraubring, gedruckter Schlitten mit Spant (Band zwischen B und C), Platine, 2S und 1S, GPS unter dem Spant, LoRa-Wendel unten, Schalterbrett hinter Luke B |
| M3 Bergung | Rohr C 195 mm, CO₂-Modul auf dem Spant, Fallschirm, Schockschnur |
| M4 Spitze | Klima 8539 mit Holzplatte und Haken, über den zweiten halben Kuppler aufgesteckt |

<p>
<img src="docs/img/bauanleitung/modular_section.png" width="22%" alt="Längsschnitt der Modulbauweise">
<img src="docs/img/bauanleitung/modular_avionik_rumpf.png" width="36%" alt="Avionik-Schlitten im Rohr B, Bestückungsseite">
<img src="docs/img/bauanleitung/Z5_schlitten.png" width="38%" alt="Zeichnung Z5: Schlitten mit Spant">
</p>

Entscheidungen, die der Stand 2b festhält: kein Ring-Stack und keine Gewindestangen (die Platine liegt
auf einem gedruckten Schlitten), **kein Rollmotor** (Masse, Vibration, ohne Flossen kaum Rollmoment),
**CO₂ statt Schwarzpulver** (kein Sprengstoffrecht, am Tisch beliebig testbar), Schraubschalter statt
Schlüsselschalter, GPS und LoRa-Antenne im Avionikraum statt in der abgesprengten Spitze. Die Zeichnungen
Z1–Z6 und die Bohrschablonen S1–S4 kommen aus [`docs/bauanleitung/zeichnungen.py`](docs/bauanleitung/zeichnungen.py),
die vier Druckteile aus [`cad/modular.py`](cad/modular.py).

```bash
MS_CONFIG=erstflug python cad/modular.py       # Druckteile, Kollisionsprüfung, Masse, Bilder
python docs/bauanleitung/zeichnungen.py        # Zeichnungen und 1:1-Schablonen
python cad/mass_stand2b.py                     # Massenbudget, Schwerpunkt, Trägheit
```

## Massenbudget

Drei Modelle in drei Tagen, jedes leichter als das vorige. Die Zahlen sind Modellwerte aus
[`cad/mass_properties.md`](cad/mass_properties.md) und [`cad/mass_stand2b.md`](cad/mass_stand2b.md);
gewogen wird nach dem Druck.

| Konfiguration | Start | Schwerpunkt ab Düse | Hebelarm Kardan–CG | Ixx = Iyy | Izz (Roll) | E12: Gipfel laut Simulation |
|---|---|---|---|---|---|---|
| `voll` (21.10.): 1000 mm, Beine, Ring-Stack, Kolben | 981 g | 449 mm | 372 mm | 0,110 kg·m² | 0,00105 kg·m² | 20 m, Schub-Gewicht 1,1 |
| `erstflug` (22.10.): 700 mm, ohne Beine, Kolben, Schlüsselschalter | 761 g | 318 mm | 242 mm | 0,046 kg·m² | 0,00057 kg·m² | – (Ziel 750 g um 11 g verfehlt) |
| **Stand 2b (22.10. abends): 496 mm in drei Modulen, CO₂, kein Rollmotor** | **723 g** | 256 mm | 186 mm | 0,021 kg·m² | 0,00047 kg·m² | **63 m**, Schub-Gewicht 1,7 |

Woher die 258 g gegenüber `voll` kommen: Landesystem (−200 g), Rohr 496 statt 1000 mm (−121 g),
keine Gewindestangen und Endringe, kein Kolben, kein Schlüsselschalter; dagegen der Schlitten mit
Spant als ein großes Druckteil (74 g), das CO₂-Modul mit Kapsel und Servo (44 g) und ein halber
Kuppler mehr. Die Schätzung in `modular.py` (689 g) vergaß LoRa-Wendel, CO₂-Servo, Schalterbrett-Bauteile,
Ringschraube und Servohebel; das Budget rechnet sie mit (+34 g). Nach Baugruppen: Rohre und Kuppler
19 %, Flugcomputer mit Akkus 15 %, Spitze 14 %, Druckteile 14 %, Kardan 12 %.

Der Hebelarm von 186 mm ist halb so lang wie bei `voll`; die Firmware (`MOMENT_ARM_M`, `MASS_KG`)
und die Simulation (`--vehicle stand2b`) rechnen damit. Das Roll-Trägheitsmoment liegt weiter
zwei Größenordnungen unter dem alten Platzhalter 0,1 kg·m².

## Was die Simulation sagt

Das Simulink-Modell (Starrkörper mit Quaternionen, Schubkurve des TSP E12, aus Sprungantworten
identifizierte Servo-Übertragungsfunktion, Sensorrauschen, statische Fehlausrichtung, Boden) liegt
als Python-Paket `tvcsim` in [`simulation/`](simulation/README.md). Es hat zwei Regler: den aus
Simulink und einen zeilengenauen Port von `Control.cpp` aus der Firmware, und vier Fahrzeugsätze,
darunter `cad` (981 g) und `stand2b` (723 g) aus den Massenmodellen.

![Reglervergleich](docs/img/sim/compare_gains_preload.png)

Vier Befunde, die das Projekt verändert haben:

- **Die Firmware-Gewinne sind die richtigen.** Kp 5, Ki 0, Kd 1 (auf der Skala −100 der Firmware)
  halten den Kippwinkel in der Brennphase klein. Die früher per MATLAB-Raster gefundenen
  Gewinne (kp 3,1, ki 5, kd 0,385) haben einen 40-mal größeren D-Anteil, treiben den Kardan sofort
  in die ±5°-Begrenzung und schwingen mit 3 bis 4 Hz.
- **Die 1-kg-Rakete war für einen E12 zu schwer** (Schub-Gewicht 1,1, Gipfel 20 m). Statt eines
  stärkeren Motors wurde die Rakete leichter: *Kartonaut 1* mit 723 g erreicht im Modell
  **63 m** (100 Läufe: 63,4 ± 0,4 m), Landung nach gut 9 s, Kippwinkel in der Brennphase höchstens 1,9°
  mit den Firmware-Gewinnen und 0,9 m seitlicher Versatz bei Brennschluss.
- **Die Servo-Kardan-Übersetzung entscheidet über die Stellreserve.** Mit den 23 Servo-Grad je
  Kardan-Grad aus `Config.h` erreicht der Kardan nur ±1°, mit den gemessenen 6 sind es ±3,75°.
  Wird am gebauten Schubstangen-Kardan gemessen.
- **Ohne Rollregelung muss die Lage als Quaternion gerechnet werden.** Die komponentenweise
  Integration `rot_deg += ω·dt` legt einen Neigungsfehler in die falsche Servoachse, sobald die
  Rakete rollt (Befund 3 in `PROJECT.md`). Das ist die Bedingung für den Verzicht auf den Rollmotor.

<p>
<img src="docs/img/sim/montecarlo_preload.png" width="48%" alt="Monte-Carlo-Trajektorien">
<img src="docs/img/sim/servo_fit.png" width="48%" alt="Servo-Sprungantwort und Fit">
</p>

```bash
cd simulation
python -m pytest tests                 # 25 Tests
python scripts/run_nominal.py --controller firmware --vehicle stand2b --single-motor
python scripts/run_montecarlo.py --controller firmware --vehicle stand2b --single-motor
python scripts/compare_gains.py --vehicle stand2b --single-motor --accel specific_force
```

## Hardware: Mainboard rev B

Heute hängen alle Sensoren als Breakouts mit Dupont-Kabeln am Teensy, im Flug das größte
Ausfallrisiko. [hardware/mainboard/](hardware/mainboard/README.md) spezifiziert deshalb das
**Mainboard rev B**: ein Schlitten 54 × 120 mm mit Teensy-Sockel, IMU genau auf der Rollachse und
allen Steckern an den Stirnseiten. In der Modulbauweise liegt er auf vier Säulen des gedruckten
Schlittens im Rohr B, die Luken für USB, SD und Schalterbrett sitzen in der Rohrwand.

<img src="hardware/mainboard/kicad/img/render_top.png" width="100%" alt="Mainboard rev B, geroutet, Render von oben">

Das KiCad-Projekt in [hardware/mainboard/kicad/](hardware/mainboard/kicad/README.md) wird aus einer
einzigen Python-Beschreibung der Schaltung erzeugt (`circuit.py`): sieben Schaltplanblätter, ERC ohne
Fehler, Platinen-Generator mit Umriss, vier Lagen, Netzklassen, Sperrflächen und Freerouting, alle 134
Teile platziert und geroutet, DRC ohne Fehler, Bestückungsdruck mit Missionsabzeichen, Lötstopp blau.
Der [Design Guide](docs/DesignGuide_Mainboard_revB.md) ([PDF](docs/DesignGuide_Mainboard_revB.pdf))
stellt den Entwurf mit Abbildungen vor, das [Datenblatt](hardware/mainboard/datasheet/) im
Industrieformat beschreibt Grenzwerte, Pinbelegung, Funktion und Stückliste.

Ein [Zweitmeinung-Review](hardware/mainboard/review_kicad_2026-10-21.md) hat acht A-Punkte gefunden
(Buck-Boost-Ausgangskapazität, 1S-Unterspannungsschwelle, Hauptschalter im Strompfad, Sicherung je Akku,
Kelvin-Shunt, 2S-Ströme auf der Innenlage). Die Fragerunde vom 22.10. hat sie zusammen mit zehn
Entscheidungen ([Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md)) festgelegt:

- **Hauptschalter mechanisch, Strom über FETs.** Der Schalter am Rumpf schaltet nur die Gates zweier
  P-FET-Lastschalter, der Akkustrom bleibt auf der Platine.
- **Laden in der Rakete.** 1S über einen MCP73831 mit USB-C auf der Platine, 2S über eine Ladebuchse mit
  Balancer am Schalterbrett; beides vor dem Lastschalter.
- **Alle Flugsensoren an SPI1.** BMP390 mit eigenem Chip-Select, INA239 statt INA219; I²C nur noch für
  die Qwiic-Erweiterung. Ein hängender I²C-Slave kann den Regelkreis nicht mehr blockieren.
- **Alle Servos und der Rollmotor direkt am 2S**, kein 5-V-Buck mehr; das PWM-Tastverhältnis begrenzt
  die Motorspannung.
- **Zukunft eingebaut:** vier Pyro-Kanäle, vierter Servo-Stecker, zweites Barometer als Footprint,
  Stapelstecker `J_STACK` für Zusatzplatinen mit Stromreserve. Weil die Teensy-Pins ausgingen, liefern
  ein 74HC138 die Chip-Selects und ein 74HC4051 die Analogkanäle (40 → 31 belegte Pins).
- **Zwei Akkus**, **IMU ohne DMP** (ICM-42688-P), **LoRa statt HC-12** (E22-400T22S, Antenne als
  433-MHz-Wendel am unteren Ende des Schlittens) bleiben aus rev B.

Die Firmware ist darauf vorbereitet: [`firmware/lib/mainboard_revb/`](firmware/README.md) enthält
Pinbelegung, Decoder und Mux, SPI-Treiber für ICM-42688-P, BMP390 und INA239 und das
Inbetriebnahme-Programm `revb_bringup`; `check_board_pins.py` vergleicht die Pins mit `circuit.py`,
auch in der CI. Rev A mit der Begründung des Schlitten-Layouts bleibt in
[`rev_a_2026-10-15.md`](hardware/mainboard/rev_a_2026-10-15.md).

## Bodenstation und Startrampe

<img src="docs/img/cad/landingpad.png" width="300" align="right" alt="Startrampe mit Kartonaut 1 (Erstflug-CAD)">

Die **Bodenstation** ([groundstation/](groundstation/README.md)) zündet den Motor über eine 15-m-Leitung,
empfängt die LoRa-Telemetrie und zeigt beides über einen eigenen WLAN-Zugangspunkt im Browser des
Handys an. Die Station entscheidet, das Handy zeigt an: Scharf schalten geht nur mit Schlüssel und
ARM-Schalter am Gerät, der Zündpfad läuft über Relais (Hardware) und MOSFET (Firmware), die Startsperre
prüft Durchgang des Anzünders, Telemetrie jünger als eine Sekunde und den Flugzustand `PAD_READY`;
ein Herzschlag vom Handy bricht den Countdown bei Verbindungsverlust ab. ESP32-S3-Firmware mit
Zustandsautomat, WebSocket und eingebetteter Weboberfläche liegt in `groundstation/firmware/`
([Schaltung](groundstation/Schaltung.md)). Sparvariante aus Modulen ca. 80 €, ein Abend Bauzeit.

Die **Startrampe** ([`cad/landingpad.py`](cad/README.md)) ist eine Siebdruckplatte 600 × 600 mm mit
einem Loch Ø 130 für den Strahl, Stahlblech darum, drei einzeln verstellbaren M10-Beinen (bis 23°
Bodenneigung) und drei abschraubbaren Führungen mit 1,5 mm Luft zum Rohr; dazu ein Zündkasten mit
XT30-Buchsen für Zündleitung und Shunt-Stecker. Das Skript prüft die Rampe gegen die Rakete (Kardan
±7°, Abheben, Strahlkegel, Kippsicherheit im Wind). 6,5 kg, ca. 86 € aus Baumarktteilen. Die
Landefläche für die Konfiguration mit Beinen wird ein eigenes Teil.

Die Schnittstellen zwischen Rakete, Rampe, Station und Handy (Führungen, Zündleitung, Funkprotokoll,
WebSocket) stehen in [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md).
Offen: das Telemetrieprotokoll gehört der Flug-Firmware und wird als gemeinsamer Header übernommen;
die Führungen der Rampe müssen zu den Schrauben und Servofenstern der Modulbauweise passen (0/90/180/270°
und 207/336°, Führungen bei 45/135/250°); Sendeleistung und Tastgrad im 433-MHz-Band sind zu klären.

## CAD-Modell

Die Blender-Dateien sind in [`cad/blender_inventory.md`](cad/blender_inventory.md) inventarisiert und
durch ein parametrisches Modell in CadQuery abgelöst ([`cad/`](cad/README.md)): jedes Maß in
`cad/params.py` mit Quelle, STEP- und STL-Export je Baugruppe, Kollisionsprüfung des Kardans bei ±7°,
Renderbilder über Blender headless, Konfigurationen `voll` (mit Beinen) und `erstflug`. Dieselben
Parameter speisen das Massenmodell. Die Modulbauweise liegt daneben in `cad/modular.py` mit eigenen
Maßen (`modular_params.py`), weil sie vom gebauten Kardan ausgeht; der gedruckte Kardan aus den
Blender-Dateien vom Juni 2025 ist als Netz im Gesamtmodell `cad/export/modular/Kartonaut1_Stand2b.step`.

<p>
<img src="docs/img/cad/rocket_section.png" width="24%" alt="Schnitt der Konfiguration voll: Motor, Kardan, Flugcomputer im Kuppler, Kolben, Fallschirm, Spitze">
<img src="docs/img/cad/rocket_tvc.png" width="37%" alt="Kardan mit den beiden W5652H, 5° und 4° ausgelenkt (Entwurf Direktantrieb)">
<img src="docs/img/cad/rocket_avionics.png" width="37%" alt="Flugcomputer-Modul der Konfiguration voll: Kuppler, Stangen, Schlitten, Akkus">
</p>

```bash
python -m pip install --user cadquery
python cad/build.py                      # Konfiguration voll: STEP/STL nach cad/export/, Bilder nach docs/img/cad/
python cad/build.py --config erstflug    # Erstflug-CAD vom 22.10. (Luken, Kolben, 700 mm)
python cad/mass_model.py                 # mass_properties.md und .json (voll und erstflug)
python cad/landingpad.py                 # Startrampe mit Prüfung gegen die Rakete
```

## Bodentests

Bevor etwas fliegt, wird die Lageregelung am Boden mit echtem Schub und ohne Treibsatz
getestet: Die Rakete hängt in einem Gestell, das sie um den Schwerpunkt nicken und gieren
lässt, und an Stelle des Raketenmotors sitzt ein Brushless-Motor (Racerstar BR2814, 1000 KV,
11-Zoll-Propeller, 4S-LiPo) im Kardan. Bei Teilgas liefert er die 12 N des E12, und der Teensy
kann den Regler sogar entlang der E12-Schubkurve fahren. Motor, Regler, Propeller, Akku und
Ladegeräte sind gekauft, das Gestell ist in [`cad/testrig.py`](cad/README.md) konstruiert und auf
Kollisionen geprüft. Dazu kommen der CO₂-Ausstoßtest (Rakete waagrecht, Spitze fliegt ab, Schirm
vollständig frei, dreimal, auch kalt), die Funkreichweite mit zwei E22 und der Startsperren-Test
vom Handy bis zu einem Lämpchen an der Zündleitung.

<p>
<img src="docs/img/cad/testrig.png" width="40%" alt="Prüfstand: Rakete im zweiachsigen Rahmen">
<img src="docs/img/cad/testrig_drive.png" width="52%" alt="Antriebsende: Propellermotor im Kardan mit Schutzkäfig">
</p>

## Firmware

PlatformIO-Projekt für den Teensy 4.1 in [`firmware/`](firmware/README.md). Die Hauptschleife
läuft mit festen 100 Hz:

1. **Sensoren lesen.** IMU (Drehrate, Beschleunigung), Barometer, Strommonitor.
2. **Lage integrieren.** Nur aus dem Gyro: Im Flug sind Kompass und Beschleunigungsstützung unbrauchbar.
3. **Höhe schätzen.** Ein Kalman-Filter mit zwei Zuständen fusioniert Barometer und Vertikalbeschleunigung.
4. **Regeln.** Ein PID auf Pitch und Yaw liefert ein Moment, das über `M = l · m · |a| · sin δ` in den
   Kardanwinkel und dann in Servo-Grad umgerechnet wird; der Rollregler bleibt für *Kartonaut 1* aus.
5. **Loggen.** Ein 88-Byte-Frame pro Durchlauf in einen Seitenpuffer; SD-Schreibzugriffe nur in der
   freien Zeit vor der nächsten Deadline. Am Boden wird das Binärlog als CSV exportiert.

```bash
cd firmware
pio run                      # Flug-Firmware bauen
pio run -t upload            # auf den Teensy 4.1 flashen
pio device monitor           # serielle Konsole, 115200 Bd, Teleplot-kompatibel
pio run -e revb_bringup      # Inbetriebnahme-Programm für das Mainboard rev B
python tools/check_board_pins.py   # Pins der Firmware gegen circuit.py
```

Alle Pins, Gewinne, Filterkonstanten und Debug-Schalter liegen in
[`firmware/src/Config.h`](firmware/src/Config.h). Die Regler sind dort abgeschaltet, bis der
erste Flugtest ansteht. Offen vor dem Erstflug: Quaternion-Lage mit Oben-Vektor, Gyro-Kalibrierung
auf der Rampe, Flugzustandsautomat (`SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED`),
CO₂-Auslösung aus dem Automaten, Telemetrieprotokoll, Watchdog mit Zustandsspeicher, Sensoren hinter
einer Schnittstelle für Breakouts und rev B.

## Aufbau des Repos

```
firmware/               Flug-Firmware (PlatformIO, Teensy 4.1)                 -> firmware/README.md
  src/                  Module: Sensors, KalmanZ, Control, SDLogger, Timing, Indicators
  lib/mainboard_revb/   Pins, CS-Decoder, Mux, SPI-Treiber ICM-42688-P / BMP390 / INA239
  examples/             Test-Sketches (Funk-Beacon, I2C-Scan, Pyro-MOSFET, revb_bringup)
  tools/                check_board_pins.py
groundstation/          Bodenstation: Konzept, Schaltung, ESP32-S3-Firmware   -> groundstation/README.md
simulation/             6DOF-Simulation in Python, Paket tvcsim                -> simulation/README.md
hardware/mainboard/     Mainboard rev B: Spezifikation, Entscheidungen, KiCad aus Code, Datenblatt, Reviews, Bestellplan
cad/                    parametrisches CAD, Modulbauweise, Startrampe, Prüfstand, Massenmodelle -> cad/README.md
docs/                   Bauanleitung (+ Zeichnungen, Schablonen, PDF), Design Guide, Bautagebuch, Pläne, Budget, Bilder
.github/workflows/      CI: PlatformIO-Umgebungen, Simulationstests, Pin-Abgleich
PROJECT.md              Projektdatei: Eckdaten, Arbeitspakete, Befunde, Änderungsprotokoll
```

Die alte Bodenstation (Arduino Nano mit HC-12) ist ein eigenes Repo:
[kartonaut-ground](https://github.com/Jan-Philipp-Munsch/kartonaut-ground); ihr Nachfolger ist
`groundstation/`. Das MATLAB/Simulink-Original der Simulation und die Blender-Dateien bleiben außerhalb
dieses Repos; ihr Inhalt ist hierher portiert.

## Dokumente

| Dokument | Inhalt |
|---|---|
| [PROJECT.md](PROJECT.md) | Eckdaten, Arbeitspakete mit Status, Befunde aus den Durchsichten, nächste Schritte, Änderungsprotokoll |
| [docs/Bauanleitung_Kartonaut1.md](docs/Bauanleitung_Kartonaut1.md) | Bauanleitung Stand 2b: Entscheidungen, Module, Stapel, Teileliste mit Bestell- und Druckstatus, Bauschritte, Wartung, Kabelplan, Zeichnungen ([PDF](docs/bauanleitung/Bauanleitung_Kartonaut1.pdf), [Zeichnungen](docs/bauanleitung/Zeichnungen_Kartonaut1.pdf), [Bohrschablonen 1:1](docs/bauanleitung/Bohrschablonen_1zu1.pdf)) |
| [cad/mass_stand2b.md](cad/mass_stand2b.md) | Massenbudget *Kartonaut 1* Stand 2b: Masse, Schwerpunkt, Hebelarm, Trägheit, Teileliste, Vergleich mit den Vorgängern |
| [cad/mass_properties.md](cad/mass_properties.md) | Massenmodell der Konfigurationen `voll` und `erstflug` |
| [docs/BUILD.md](docs/BUILD.md) | as-built: Inventar der gekauften und gedruckten Teile, Mechanik, Verdrahtung, Software auf dem Gerät, Tests, Bautagebuch |
| [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md) | Plan bis zum Erstflug: Arbeitsstränge Platine, Firmware, Mechanik, Bodensysteme, Meilensteine M1–M7 |
| [docs/Budget_2026-10-22.md](docs/Budget_2026-10-22.md) | Budgetplan bis zum Erstflug: offene Ausgaben nach Blöcken, Inventar, Zeitplan, Sparhebel, Unsicherheiten |
| [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md) | Schnittstellen S1–S4: Rakete/Pad, Zündleitung, Funk, Handy |
| [docs/Plan_2026-10-21.md](docs/Plan_2026-10-21.md) | Planungsrunde 21.10.: Platinen-Review, Versorgungsarchitektur, Layout-Checkliste, Portierungsplan |
| [docs/Rohrmaterial_2026-10-22.md](docs/Rohrmaterial_2026-10-22.md) | Recherche Verbundrohre gegen Pappe: Pappe bleibt |
| [hardware/mainboard/README.md](hardware/mainboard/README.md) | Spezifikation Mainboard rev B |
| [hardware/mainboard/Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md) | Entscheidungen E1–E10, Bauteile nach Schiene und Schnittstelle, Pinbelegung, Stapelstecker, Pin-Bilanz |
| [docs/DesignGuide_Mainboard_revB.md](docs/DesignGuide_Mainboard_revB.md) | der Entwurf rev B mit Abbildungen ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) |
| [hardware/mainboard/datasheet/](hardware/mainboard/datasheet/) | Datenblatt MS-MB-B rev B (LaTeX, Stückliste aus `circuit.py`) |
| [hardware/mainboard/ORDER.md](hardware/mainboard/ORDER.md) | Bestellplan: Vorab-Bestellung, Tore, JLCPCB-Parameter, Kosten, Bestellliste nach Händlern |
| [hardware/mainboard/review_kicad_2026-10-21.md](hardware/mainboard/review_kicad_2026-10-21.md) | Zweitmeinung-Review des KiCad-Projekts |
| [hardware/mainboard/Fertiger_2026-10-21.md](hardware/mainboard/Fertiger_2026-10-21.md) | Fertigervergleich und Entscheidung |
| [groundstation/README.md](groundstation/README.md) | Bodenstation: Konzept, Sicherheit, Ablauf am Startplatz, Firmware, Stückliste ([Schaltung](groundstation/Schaltung.md)) |
| [simulation/README.md](simulation/README.md) | Modell, Koordinaten, Annahmen, Fahrzeugsätze, Ergebnisse |
| [firmware/README.md](firmware/README.md) | Firmware-Module, Log-Format, Test-Sketches, rev-B-Bibliothek |
| [cad/README.md](cad/README.md) | parametrisches Modell, Konfigurationen, Modulbauweise, Prüfstand, Startrampe |
| [cad/blender_inventory.md](cad/blender_inventory.md) | was die 16 Blender-Dateien enthalten, was aktuell und was überholt ist |

## Lizenz

[MIT](LICENSE). Die BPS.space-Dateien der Scout F, die als Vorlage dienten, sind nicht Teil dieses
Repos.
