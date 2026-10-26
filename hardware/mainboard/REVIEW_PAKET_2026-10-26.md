# Review-Paket Mainboard rev B1 (Durchsicht vor der Bestellung, 26.10.2026)

Übergabe für die eigene Durchsicht am 26.10.2026. Das Dokument sagt, **wo der aktuelle Stand liegt, was heute
schon maschinell geprüft ist, welche Unterlagen in welcher Reihenfolge gelesen werden und was vor der Bestellung
entschieden werden muss**. Die ausführliche Prüfanleitung (Blatt für Blatt, Lage für Lage) steht in
`REVIEW_ANLEITUNG_revB1.md`, der Review-Brief mit den zehn offenen Bewertungsfragen in `review_brief_2026-10-23.md`.

## 0. Wo der richtige Stand liegt

| Ort | Stand | Verwenden? |
|---|---|---|
| Haupt-Checkout `C:\Users\Janmu\Gitlab\mission_space` (Branch `main`) | seit 26.10. mittags identisch mit `github/main` (Commit `e774e59`: alle Branches gemergt, PR #2–#7) | **ja, hier arbeiten** (KiCad: `hardware\mainboard\kicad\mainboard.kicad_pro`) |
| `github/main` (GitHub, `Jan-Philipp-Munsch/kartonaut`) | wie oben | ja |
| Worktrees unter `.claude\worktrees\` (`rev-b1`, `konsolidierung`, …) | alle in `main` enthalten, hinter dem Stand | nein, nach dem Review aufräumen |

Die Platinendateien (`mainboard.kicad_pcb`, `kicad/fab/`) sind seit dem 24.10. 11:23 unverändert; die Merges vom 26.10.
betrafen Firmware, Simulation, CAD und Doku. Die losen Gerber vom 23.10. (Testangebot für den alten Stand rev B)
wurden am 26.10. aus dem Haupt-Checkout entfernt; eine Kopie liegt im Scratchpad der Session
(`main_checkout_backup_2026-10-26`). Das Angebot selbst (`Angebot_JLCPCB_2026-10-23.md`) ist noch uncommittet.

## 1. Heute maschinell geprüft (26.10.2026, Platinenstand vom 24.10.)

| Prüfung | Befehl (Git Bash in `hardware/mainboard/kicad/`) | Ergebnis |
|---|---|---|
| DRC mit Schaltplan-Parität | `./make.sh drc` | **0 Fehler**, 0 nicht verbunden, Parität 0; 17 Warnungen nur Bestückungsdruck (14 × Druck über Kupfer, 2 × Überlappung, 1 × Randabstand; bekannt, Fertiger schneidet Druck auf Pads weg) |
| Netzliste gegen Spezifikation | `python.exe check_design.py` (KiCad-Python) | `OK: Netzliste entspricht README.md §4 mit den B1-Aenderungen` (42 Teensy-Pins, 7 CS, 7 Mux-Kanäle, 11 Schienen) |
| Layoutregeln (Review A5–A8) | `python.exe ../review_check_layout.py mainboard.kicad_pcb` | kein 2S-Netz auf In2; Sense-Netze ISENS_P/N nur an Shunt und R6/R7; im 5-mm-Umfeld der IMU keine In2-Bahnen |
| Bestelldateien | `kicad/fab/` vom 26.10. 11:52, nach den Layoutpunkten B1–B3 (`Review_Bewertung_2026-10-26.md` §5) | **aktuell** |

Der Firmware-Pinabgleich (`firmware/tools/check_board_pins.py`) läuft in der CI bei jedem Push.

## 2. Unterlagen in Lesereihenfolge

Alle Pfade relativ zu `hardware\mainboard\` im Haupt-Checkout.

| Nr. | Datei | Wofür | Zeit |
|---|---|---|---|
| 1 | `review_brief_2026-10-23.md` | Was sich seit dem Review vom 21.10. geändert hat; **§4: die zehn Fragen, die nur ein Mensch bewerten kann** | 15 min |
| 2 | `REVIEW_ANLEITUNG_revB1.md` | Die eigentliche Prüfanleitung: A Schaltplan je Blatt, B Netzliste, C Layout je Lage, D Bestückung, E bekannte Schwachstellen | Leitfaden für alles Weitere |
| 3 | `kicad/out/mainboard_schematic.pdf` | Schaltplan, 7 Blätter (Versorgung, Teensy, Sensorik, Funk, Aktoren, Pyro, Signal) | 45 min mit Teil A |
| 4 | `kicad/RUNDGANG_PLATINE.pdf` | Bebilderter Rundgang über die Platine, 13 Seiten | 15 min |
| 5 | `kicad/img/layers.pdf`, `kicad/img/layer_*.png`, `render_top.png`, `render_bottom.png`, `render_iso.png` | Lagenbilder und Renders für Teil C; Seite F.Cu von `layers.pdf` 1:1 drucken | 45–60 min mit Teil C |
| 6 | `README.md` §4 (Pinbelegung), §6 (Bauteile), §8 (Layoutregeln) | Das Soll, gegen das geprüft wird | nachschlagen |
| 7 | `kicad/README.md` §5.5 und §6 | Routing-Geschichte und **jede bewusste Abweichung von der Spezifikation mit Grund** | nachschlagen |
| 8 | `Komponenten_2026-10-22.md` | Entscheidungen E1–E12 (Schalter, Laden, SPI1-Bus, Servos am 2S, J_STACK, LSM6DSV16X) | nachschlagen |
| 9 | `kicad/fab/FAB.md`, `kicad/fab/mainboard_bom.csv`, `mainboard_cpl.csv`, `mainboard_gerber.zip` | Bestelldateien; Liste der 111 Positionen ohne LCSC-Nummer, 16 THT-Teile, 12 DNP | 20 min mit Teil D |
| 10 | `ORDER.md` §3 | Fertigungsparameter, Upload-Ablauf, Teilestatus bei LCSC | 10 min |
| 11 | `Angebot_JLCPCB_2026-10-23.md` (uncommittet) | Preise und die am 23.10. gefundenen LCSC-Nummern für Passive, Polyfuse, TVS, Drosseln, JST-Buchsen: **für die BOM-Zuordnung wiederverwenden** | 10 min |
| 12 | `EINKAUFSLISTE_revB1.md` | Alles, was JLCPCB nicht liefert (THT, Gegenstecker, Module, Akkus) | nach der Platinenbestellung |
| 13 | `review_kicad_2026-10-21.md`, `review_netlist_2026-10-21.md` | Das letzte Review (A1–A8, B-Punkte) zum Nachsehen, ob alles eingearbeitet ist | bei Bedarf |
| 14 | `datasheet/MS-MB-B.pdf` (Version 0.2, rev B1, 26.10.), `../../docs/DesignGuide_Mainboard_revB.pdf` | Produktdatenblatt der Bestellfassung mit Pinbelegung, Kennwerten, Stückliste; der Design Guide beschreibt im Text noch rev B, seine Abbildungen sind seit 26.10. rev B1 | bei Bedarf |

## 3. Ablauf der Durchsicht (2 bis 3 Stunden)

Die Reihenfolge folgt der Prüfanleitung; hier steht nur, worauf es heute besonders ankommt.

### Schritt 1: Die zehn Bewertungsfragen aus dem Brief (§4) zuerst lesen

Sie sind die Stellen, an denen beim Handrouting Kompromisse entstanden sind. Für jede eine Entscheidung treffen
(vertretbar / ändern / in rev B2):

1. Breite und Lage der 2S-Strompfade auf F.Cu (XT30 → Q1 → F1 → Q6 → Shunt → VSERVO; Pyro 1,0 mm bei 5 A / 20 ms).
2. GND_PWR-Stück 0,15 × 1,9 mm an DRV8833 Pin 13 (Rollmotor ≤ 1 A). Hinweis: *Kartonaut 1* fliegt laut Stand 2c
   ohne Rollmotor, der Punkt ist für den Erstflug nicht kritisch.
3. MOT_A / MOT_B über zwei Vias auf B.Cu durch die GND_PWR-Fläche.
4. Sternpunkt NT1 (GND ↔ GND_PWR nur dort).
5. Anlauf des TPS63070 mit 940 µF hinter D1 (Inrush, Softstart; Datenblatt-Tabelle „Recommended“).
6. Abstand LoRa-Modul ↔ IMU, Sperrflächen unter dem Modul.
7. Lastschalter AO3401A bei −3 V Gate (B5): am Bestelltag Typ mit −2,5 V-Spezifikation prüfen oder bewusst so lassen.
8. 13 Schlitze in 5V_SYS / GND_PWR auf B.Cu durch die SPI0-Umlegung (E11); SPI0_MISO 114 mm, 16 Vias, Takt ≤ 8 MHz;
   IMU-Masse (Pads 2/3/6/7) über 0,2-mm-Bahn an C26.
9. Zusatzsensoren LIS3MDL, SHT40, ADXL375 (DNP) an 3V3 statt 3V3_SENS, Magnetometer 12 mm von den Pyro-FETs.
10. 111 Bauteile ohne LCSC-Nummer (siehe Schritt 5).

### Schritt 2: Schaltplan (Teil A der Anleitung, 45 min)

PDF Blatt für Blatt gegen die Tabelle in Teil A. Schwerpunkte: Blatt 1 (beide Akkupfade, Werte der Teiler des
TPS63070: FB 680 k/130 k, EN 330 k/115 k), Blatt 3 (LSM6DSV16X-Beschaltung nach AN5763: Pins 2/3 an GND, 9–11 offen,
100 n + 2,2 µ + 10 n; INA239 mit Kelvin-Abgriff), Blatt 6 (Pyro: Arming, TVS, Sense-Teiler). Spannungsfestigkeit der
Kondensatoren auf der 2S-Seite ≥ 16 V.

### Schritt 3: Netzliste (Teil B, 15 min)

Ist heute grün (§1). Nur noch Stichproben in KiCad: `VBAT_PROT`, `3V3_SENS`, `SPI1_MISO`, `GND_PWR`, `ISENS_P/N`
mit „Netz hervorheben“ verfolgen.

### Schritt 4: Layout (Teil C, 45–60 min)

Lage für Lage in KiCad oder mit `layers.pdf`. Dazu zwingend die Mechanik:

- **1:1-Papierausdruck** von `layers.pdf` Seite F.Cu, Teensy und Stecker auflegen, in den Kuppler halten; Luke B
  (J_SW, J_CHG1, J_CHG2), Schlüsselschalter J_ARM, USB am Heck, Pigtail-Weg zur Antenne, Höhe ≤ 5 mm bei |u| > 25 mm.
- 3D-Ansicht (Alt+3): Pin-1-Markierungen, Polarität Elkos/Dioden, Steckerbeschriftung lesbar.
- Freie Stelle für die JLC-Auftragsnummer ist im Layout vorgesehen (Text „JLCJLCJLCJLC“), beim Upload *Specify a location*.

### Schritt 5: Bestückung und Beschaffung (Teil D, 20 min)

1. `FAB.md`: 111 Positionen ohne LCSC-Nummer. Die Nummern aus `Angebot_JLCPCB_2026-10-23.md` (Widerstände, Kondensatoren,
   Polyfuse, TVS, Drosseln, JST GH/SH) gelten weiter; neu zuzuordnen sind INA239, SN74LV1T34, 74HC138PW, 74HC4051PW,
   Polymer-Elkos 330 µ/16 V und 470 µ/6,3 V, 100 µ/6,3 V, 115 k, 2 k, die 10-Ω-Kelvin-Widerstände, FB1.
2. Bestand und Hersteller am Bestelltag im JLC-Teileprogramm: TPS63070, LSM6DSV16X (C5267406), BMP390 (zuletzt knapp,
   Rückfall BMP388 pinkompatibel), E22-400T22S (zuletzt 3 Stück), DRV8833, AO3401A, INA239.
3. Drei Footprints gegen das Datenblatt: LSM6DSV16X LGA-14, TPS63070 VQFN-15, DRV8833 HTSSOP-16; Polarität XT30 und JST.
4. CPL-Drehungen in der JLCPCB-Vorschau: SOT-23-5, VQFN-15, LGA, E22.

### Schritt 6: Bekannte Schwachstellen bewusst abnicken (Teil E)

Nichts davon neu entdecken, nur bewerten: B.Cu-Schlitze, GND_PWR-Stück am DRV8833, AO3401A-Gate, Inrush
TPS63070, fehlender LSM6DSV16X-Treiber (Firmware, nicht Platine).

## 4. Entscheidungen vor der Bestellung

| Frage | Stand | Vorschlag |
|---|---|---|
| **IMU-Messbereich ±16 g reicht?** (offen aus dem Angebot vom 23.10.) | Spitzenschub TSP E12 28,3 N bei 0,54 s (`simulation/data/E12_thrustcurve.csv`); bei 705 g Startmasse 4,1 g netto, **ca. 5 g am Sensor**, bei 761 g 4,8 g | **erledigt**, LSM6DSV16X (±16 g) bleibt; ADXL375 (±200 g) nur als DNP-Reserve |
| Oberfläche | Spezifikation und KiCad-Stackup: ENIG (plane Pads für LGA-14/LGA-10); Testangebot nahm HASL grün, 17 USD billiger | **ENIG**, Farbe nach Geschmack (blau wie im Board oder grün für leichtere Fehlersuche) |
| Stückzahl | ORDER.md: 5 Platinen, 2 bestückt (Economic PCBA, nur oben) | so lassen; Fixkosten ca. 100 USD unabhängig von der Stückzahl |
| Selbst löten | E22 (Bestand), WS2812B-2020 (erzwingt Standard-PCBA), ggf. BMP390, alle 16 THT-Teile | wie im Angebot vom 23.10. §Entscheidung |
| INA239 | ohne LCSC-Nummer in der BOM; `kicad/README.md` §8 schlägt DigiKey vor | zuerst im JLC-Teileprogramm suchen, sonst DigiKey und selbst löten (MSOP-10, machbar) |
| JLCPCB-Angebot | das vom 23.10. beruht auf rev B | **mit den rev-B1-Dateien aus `kicad/fab/` wiederholen**, bevor bestellt wird |
| Lastschalter AO3401A | B5, −3 V Gate knapp | am Bestelltag Alternative mit −2,5 V prüfen (gleiches SOT-23) oder so lassen |

## 5. Rückmeldung und was danach passiert

Pro Befund: Blatt oder Lage, Stelle (Referenz oder x/y in mm), was, Einstufung **A** (vor der Bestellung ändern) /
**B** (rev B2) / **C** (Hinweis), Vorschlag. Am Ende ein Satz: „bestellen“ oder „erst ändern: …“.

Danach: A-Punkte einarbeiten (Schaltung über `circuit.py` und „Leiterplatte aus Schaltplan aktualisieren“, Layout
direkt in KiCad), `./make.sh drc`, Prüfskript, `./make.sh fab` neu, dann Upload nach `ORDER.md` §3.
