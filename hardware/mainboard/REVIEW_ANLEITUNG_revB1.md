# Prüfanleitung Mainboard rev B1 (für das Review vor der Bestellung)

Stand 24.10.2026, Branch `main` (PR #5 gemergt). Dieses Dokument sagt, **wie** geprüft wird; **was** sich seit dem
Review vom 21.10. geändert hat und worauf es besonders ankommt, steht im Review-Brief `review_brief_2026-10-23.md`.
Zeitbedarf: etwa zwei bis drei Stunden für alles, eine Stunde für Teil A bis C.

Bestellt wird erst nach dieser Durchsicht. Rückmeldungen am liebsten als Kommentare im
[Pull Request #5](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/5) (auch nach dem Merge möglich), sonst als
Liste mit Datei, Stelle, Befund. Bitte wie beim letzten Mal einstufen:
**A** = muss vor der Bestellung geändert werden, **B** = sollte, kann aber auch in rev B2, **C** = Hinweis.

## 0. Werkzeuge und Unterlagen

| Was | Wo |
|---|---|
| KiCad 10 | Projekt `kicad/mainboard.kicad_pro` öffnen (Schaltplan- und Platineneditor) |
| Schaltplan als PDF (7 Blätter) | `kicad/out/mainboard_schematic.pdf` |
| Lagenbilder, Renders | `kicad/img/layers.pdf`, `kicad/img/layer_*.png`, `kicad/img/render_top.png`, `render_bottom.png`, `render_iso.png` |
| Bebilderter Rundgang über die Platine | `kicad/RUNDGANG_PLATINE.pdf` |
| Spezifikation (Soll) | `README.md` in diesem Ordner: §4 Pinbelegung, §6 Bauteile, §8 Layoutregeln |
| Entscheidungen und bewusste Abweichungen | `kicad/README.md` §5 und §6 (jede Abweichung von der Spezifikation mit Grund), `Komponenten_2026-10-22.md` |
| Netzliste als Text | `kicad/out/mainboard.net` (Netznamen sind in Schaltplan, Platine und Spezifikation dieselben) |
| Bestelldateien | `kicad/fab/`: Gerber-ZIP, `mainboard_bom.csv`, `mainboard_cpl.csv`, `FAB.md` |
| Bestellplan, Teileverfügbarkeit | `ORDER.md` §3 |
| Letztes Review und Netzlistenprüfung | `review_kicad_2026-10-21.md`, `review_netlist_2026-10-21.md` |

Die Prüfungen selbst laufen lassen (Git Bash im Ordner `kicad/`, KiCads Python unter
`%LOCALAPPDATA%\Programs\KiCad\10.0\bin\python.exe`):

```bash
./make.sh drc
```

erwartet: `nicht verbunden: 0 | Paritaet Schaltplan: 0`, 0 Fehler (Warnungen zum Bestückungsdruck sind bekannt).

```bash
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" ../review_check_layout.py mainboard.kicad_pcb
```

erwartet: keine 2S-Netze auf In2, um die IMU nur ihre fünf GND-Vias, Sense-Netze nur am Shunt.

```bash
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" check_design.py
```

erwartet: `OK: Netzliste entspricht README.md §4 mit den B1-Aenderungen`.

## A. Schaltplan (Blatt für Blatt, etwa 45 Minuten)

Im Schaltplaneditor oder im PDF. Je Blatt: stimmt die Schaltung gegen das Datenblatt des Hauptbauteils, sind die
Werte plausibel, fehlt etwas? Die Blätter und worauf zu achten ist:

| Blatt | Prüfen | Soll |
|---|---|---|
| 1 Versorgung | 1S-Pfad: Verpolschutz Q2, Polyfuse F2, Lastschalter Q7 (AO3401A, Gate über 100 k/1 k), TPS63070 Buck-Boost mit FB-Teiler 680 k/130 k (4,98 V), EN-Teiler 330 k/115 k (ein 3,1 V, aus 2,7 V), L1 und Ausgangskapazität 470 µF, D1 und 1000 µF an TEENSY_VIN; Lader MCP73831 mit Prog-Widerstand; 3V3_SENS über Ferrit FB1 + 10 µF; LDO 3V3_EXP; LDO 3V3_RF | TPS63070-Datenblatt Tab. „Recommended“; A1/A2/A3 aus dem Review vom 21.10. |
| 1 Versorgung, 2S | Verpolschutz Q1, Polyfuse F1, Lastschalter Q6, Shunt R_SH1 20 mΩ mit Kelvin-Abgriff (ISENS_P/N nur über R6/R7 zum INA239), VSERVO-Puffer C35–C38, Lade-Stecker J_CHG2 | A4/A5; INA239-Datenblatt (VBUS am Kelvin-Abgriff, siehe `kicad/README.md` §6) |
| 2 Teensy | Alle 42 Pins belegt wie `README.md` §4 (E10/E11); 74HC138 mit SEL0..2 (Pins 38/25/30), /E1 = CS_EN mit 10 k Pull-up; 74HC4051 mit denselben Selects, Z an Pin 24, Messteiler 100 k/33 k + 100 nF; J_STACK Pinfolge 1–20 | Pin-Tabelle im README; `check_design.py` grün |
| 3 Sensorik | LSM6DSV16X: SPI 4-Draht, CS aus dem Decoder Y0, INT1 an Pin 4, Vdd/Vdd_IO an 3V3_SENS, 100 n + 2,2 µ + 10 n, Pins 2/3 an GND, 9–11 offen; BMP390 ×2 (zweiter DNP) an SPI1, CS Y1/Y2; INA239 CS Y3; LIS3MDL 0x1E, SHT40 0x44, ADXL375 0x53 (DNP) an Wire mit 4,7 k Pull-ups; J_QWIIC | AN5763 Tab. 1; Bosch BMP390 DS; TI INA239 DS |
| 4 Funk | E22-400T22S: TXD/RXD an Serial8 (Pins 34/35), M0/M1 an 16/32, AUX an 36, NRST mit 10 k nach 3V3_RF an Pin 6, 3V3_RF-Versorgung; ANT-Pad offen, Antenne über IPEX; GPS an Serial1 (0/1) | E22-Handbuch (Pegel 3,3 V, Stromspitzen beim Senden) |
| 5 Aktoren | Vier Servostecker (Signal über 220 Ω, Pins 28/29/9/10) am VSERVO; DRV8833 mit nSLEEP an Pin 40, nFAULT an 8, IN1/IN2 an 2/3, ISEN ans Wärmepad, VM mit 10 µF + 100 nF | DRV8833-Datenblatt (E9: Motor am 2S) |
| 6 Pyro | Vier Kanäle low-side (FETs Q3/Q4 für Kanal 1/2, Q8/Q9 für 3/4 als DNP; Gate-Widerstände, Pull-downs); Durchgangsprüfung über Spannungsteiler auf den Mux (PYRO1..4_SENSE); Arming über Schlüsselschalter J_ARM, ARM_SENSE auf Mux und über 10 k auf J_STACK; TVS SMAJ12CA; Pyro-Minus als eigene Netze | Spezifikation §5; Review C3 |
| 7 Signal | WS2812B-Kette hinter Pegelwandler SN74LV1T34 (5 V), Summer über Transistor an 5V_SYS (Pin 37), Kamera-Trigger Pin 7, Status-LEDs | |

Außerdem auf jedem Blatt: ERC-Marker (sollten keine da sein), Bauteilwerte und Spannungsfestigkeiten (2S-Seite:
Kondensatoren ≥ 16 V, TVS 12 V), DNP-Markierungen (ADXL375, BMP390 #2, Pyro 3/4).

## B. Netzliste und Pinbelegung (15 Minuten)

1. `check_design.py` und `./make.sh drc` laufen lassen (oben). Beides muss grün sein.
2. Stichproben in KiCad: im Platineneditor ein Netz markieren (Taste `` ` `` oder Inspektion → Netz hervorheben) und
   verfolgen. Empfohlene Stichproben: `VBAT_PROT` (XT30 → Q1 → F1 → Q6 → Shunt → VSERVO), `3V3_SENS`, `SPI1_MISO`
   (IMU, BMP390, INA239, Pin 39), `GND_PWR` (nur über NT1 mit GND verbunden), `ISENS_P/ISENS_N` (nur Shunt, R6/R7, INA239).
3. Firmware gegen Schaltung: `python firmware/tools/check_board_pins.py` im Repo-Wurzelverzeichnis muss `OK` melden
   (die CI tut das bei jedem Push).

## C. Layout (45 bis 60 Minuten)

Im Platineneditor, Lagen einzeln einblenden (Lagenverwaltung rechts), oder mit `kicad/img/layers.pdf`.

| Prüfung | Wie | Erwartung |
|---|---|---|
| Strompfade 2S | F.Cu einblenden, Zonen „… Strompfad“ ansehen: XT30 → Q1 → F1 → Q6 → Shunt → VSERVO-Schiene → Servostecker; VBAT_PROT / VBAT_ARMED an der rechten Kante zu den Pyro-FETs; VSYS_IN | durchgehend ≥ 1,0 mm (Spitze der Pyro-Pfade 1,0 mm, 5 A für 20 ms), VSYS_IN ≥ 0,6 mm, keine Engstellen an Steckerpins |
| Klasse Strom nur außen | `review_check_layout.py` meldet keine 2S-Netze auf In2 | Review A6 |
| Massekonzept | In1 ist durchgehende GND-Fläche; B.Cu geteilt: GND_PWR unter allem am 2S, 5V_SYS unter der 1S-Seite; Sternpunkt NT1 am XT30-Minus (einziger Übergang GND ↔ GND_PWR) | B.Cu und In1 einblenden, NT1 suchen |
| Schlitze in B.Cu | B.Cu einblenden: 13 kurze Signalstücke (SPI0_MISO, SPI0_MOSI, LORA_M0, PYRO3_FIRE, PWM_EXT, MOT_NSLEEP, dazu die älteren CS_EXT2, LORA_RXD, MOT_A/B). Zerschneiden sie einen Rückstromweg, der dir wichtig ist? | Flächen bleiben zusammenhängend; Rückstrom des Rollmotors und der 5-V-Schiene laufen um die Schlitze herum. Bewertung erbeten (Reviewpunkt 7 im Brief) |
| GND_PWR am DRV8833 | Pin 13 des DRV8833 (x 144,5 / y 114,9): 0,15 mm × 1,9 mm, Rest über das Wärmepad mit Vias | reicht das für ≤ 1 A? (Reviewpunkt 2) |
| MOT_A / MOT_B | zwei Vias auf B.Cu zum Motorstecker J8, schneiden die GND_PWR-Fläche unter den Aktoren an | vertretbar oder umlegen? (Reviewpunkt 3) |
| IMU-Umfeld | U4 bei x 127,0 / y 109,5 auf der Rollachse unter dem Teensy; 5-mm-Zone: nur die fünf GND-Vias der IMU, keine In2-Bahnen; Massepfad der Pads 2/3/6/7 über eine 0,2-mm-Bahn zu C26 | `review_check_layout.py`, Abschnitt „Umfeld der IMU“ |
| LoRa-Modul | Sperrflächen unter dem Modul auf F.Cu und In2, Antenne über IPEX nach außen, Abstand Modul ↔ IMU | Reviewpunkt 5 |
| Zusatzsensoren | Magnetometer LIS3MDL in der linken Spitzenecke (12 mm von Pyro-FETs und J_PYRO1), SHT40 neben J_QWIIC, ADXL375 hinter dem USB-Ende | Störung im Flug ist eingeplant; alle an 3V3 statt 3V3_SENS (`kicad/README.md` §6) |
| Abstände | DRC-Regeln: 0,15 mm Standard, 0,2 mm zur Stromklasse, Rand 0,2 mm, Via 0,6/0,3, Loch-zu-Loch 0,5 mm; JLC 4-Lagen JLC04161H-7628 | `./make.sh drc` 0 Fehler |
| Stecker und Mechanik | Alle Buchsen am Rand erreichbar (Servos, Pyro, XT30, J_CHG2, J_ARM an der Spitze; USB des Teensy am Heck); J5/J6 ragen bewusst über den Rand; Schlitz 54 × 120 mm, Befestigungslöcher | 3D-Ansicht (Alt+3) und `render_iso.png`; Papierausdruck 1:1 (`layers.pdf`, Seite F.Cu) in den Kuppler legen |
| Bestückungsdruck | Referenzen lesbar, Pin-1-Markierungen, Polarität der Elkos und Dioden, Beschriftung der Stecker | `img/layer_Bestueckung.png`; bekannte Warnungen: Teensy-Umriss über den LoRa-Pads, JLC-Platzhalter über C17 (der Fertiger schneidet Druck auf Pads weg) |

## D. Bestückung und Beschaffung (20 Minuten)

1. `kicad/fab/FAB.md` lesen: welche Teile ohne LCSC-Nummer sind (werden am Bestelltag zugeordnet), welche THT-Teile
   selbst gelötet werden (Teensy-Buchsenleisten, XT30, JST-Buchsen, Schlüsselschalter), welche DNP sind.
2. `ORDER.md` §3.3: die kritischen Teile mit LCSC-Nummer (TPS63070, LSM6DSV16X C5267406, BMP390, E22-Modul, DRV8833,
   AO3401A, INA239) auf Bestand und Hersteller prüfen; BMP390 war zuletzt knapp (Rückfall BMP388 pinkompatibel).
3. Gehäuse-Stichprobe: drei Footprints gegen das Datenblatt (empfohlen: LSM6DSV16X LGA-14 2,5 × 3 mm, TPS63070 VQFN-15,
   DRV8833 HTSSOP-16 mit Wärmepad), dazu die Polarität des XT30 und der JST-Buchsen.
4. BOM-Mengen und Werte gegen den Schaltplan (Bauteilliste in `README.md` §6).

## E. Bekannte Schwachstellen (bitte bewusst bewerten, nicht neu entdecken)

- 13 Signalstücke auf B.Cu (Schlitze in 5V_SYS und GND_PWR), SPI0_MISO 114 mm mit 16 Vias → SPI0 zur Zusatzplatine
  höchstens 8 MHz.
- GND_PWR-Stück 0,15 mm an DRV8833 Pin 13; MOT_A/MOT_B auf B.Cu.
- Lastschalter AO3401A bei −3 V Gate knapp spezifiziert (Review B5); am Bestelltag Typ mit −2,5 V prüfen.
- Anlauf des TPS63070 mit 940 µF hinter D1 (Inrush, Softstart).
- 108 Positionen ohne LCSC-Nummer (Passive, Stecker, Polyfuses, Polymer-Elkos, INA239, SN74LV1T34, 74HC138/4051).
- Firmware: der Treiber für den LSM6DSV16X fehlt noch; die Pinbelegung ist abgeglichen.

## F. Rückmeldung

Pro Befund: Datei oder Blatt, Stelle (Referenz oder x/y in mm), was, Einstufung A/B/C, Vorschlag. Am Ende bitte ein
Satz: „bestellen“ oder „erst ändern: …“. Danach werden A-Punkte eingearbeitet (Schaltung über `circuit.py`, Layout
direkt in KiCad), DRC und Prüfskript laufen erneut, dann Bestellung nach `ORDER.md` §3 (JLCPCB, 5 Platinen, 2 bestückt).
