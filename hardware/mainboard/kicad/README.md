# Mainboard rev B – KiCad-Projekt

Stand 2026-10-21. Schaltplan und Platine von rev B werden hier **aus Code erzeugt**, nicht von Hand
gezeichnet. Die Quelle der Wahrheit ist `circuit.py`: Schaltplan, Platine und Prüfungen werden daraus
abgeleitet. Die Vorgabe ist die Spezifikation `../README.md` (rev B). Dieses Dokument beschreibt, wie das
Projekt entstanden ist, was fertig ist, was offen ist und wo bewusst von der Spezifikation abgewichen wurde.
Die Fertigerwahl steht in `../Fertiger_2026-10-21.md`.

![Platine schräg](img/render_iso.png)

## 1. Stand auf einen Blick

| Schritt | Stand |
|---|---|
| Schaltung als Daten (`circuit.py`) | 134 Bauteile, 89 Netze, 7 Schaltplanblätter |
| ERC | **0 Fehler, 0 Warnungen**, 4 begründete Ausschlüsse (§6) |
| Netzliste gegen Spezifikation §4 (`check_design.py`) | **OK**: alle 42 Teensy-Pins und 6 Schienen |
| Platzierung | **alle 134 Footprints**, keine Überschneidung, Regeln aus dem Platzierungsplan eingehalten |
| Routing | 1620 Bahnsegmente (3,65 m), 231 Vias, vier Lagen |
| DRC (JLC-Regeln) | **0 Fehler**, Schaltplan-Parität **0 Abweichungen** |
| Offene Verbindungen | **3**, jede unter 2 mm, von Hand zu ziehen (§5.4) |
| Abbildungen | Renders oben, unten und schräg, Lagenbilder (`img/`) |
| Fertigungsdaten (Gerber, BOM, CPL) | offen, nach den 3 Verbindungen und dem Review (§8) |

| Oben | Unten |
|---|---|
| ![oben](img/render_top.png) | ![unten](img/render_bottom.png) |

Die Lagen einzeln: `img/layers.pdf` (F.Cu, In1 GND, In2, B.Cu Versorgung, Bestückungsdruck) und
`img/layer_*.png`.

## 2. Werkzeuge

- **KiCad 10.0.6.** Die winget-Installation für alle Benutzer blieb an der Administrator-Abfrage
  hängen. Deshalb wurde der signierte Installer (KiCad Services Corp.) als Benutzerinstallation
  ausgeführt: `/S /CurrentUser` nach `%LOCALAPPDATA%\Programs\KiCad\10.0`. Die globalen
  Bibliothekstabellen (`sym-lib-table`, `fp-lib-table`) wurden aus dem Template nach
  `%APPDATA%\kicad\10.0\` kopiert; das macht die GUI sonst beim ersten Start.
- **easyeda2kicad** (pip) für die vier Teile, die nicht in der KiCad-Bibliothek sind: ICM-42688-P (C1850418),
  BMP390 (C5124834), TPS63070RNMR (C109322) und E22-400T22S (C2903765). Symbol, Footprint und
  3D-Modell kommen direkt aus der LCSC/EasyEDA-Datenbank, also genau die Footprints, mit denen JLC bestückt.
- **Freerouting 2.5.0** als JAR mit einer portablen **Temurin-25-JRE** (Zip, keine Installation), beides
  unter `%LOCALAPPDATA%\Programs\freerouting\`, Prüfsummen kontrolliert. Die native
  `freerouting-cli.exe` derselben Version stürzt mit einem GraalVM-Fehler ab; die JAR braucht Java 25.
- **CadQuery** für zwei 3D-Modelle, die fehlen: Teensy 4.1 (vereinfacht, auf 8,5-mm-Sockeln) und
  XT30PW-M (die KiCad-Bibliothek nennt das Modell, liefert es aber nicht).
- Datenblätter für die eigenen Entscheidungen: TPS63070 (SLVSC58B: Pinbelegung, Teiler-Tabelle 4,
  Kondensatoren) und ICM-42688-P (DS-000347: RESV-Pins, Abblockung).

## 3. Aufbau und Ablauf

```
circuit.py          Schaltung als Daten: Bauteile, Werte, Footprints, LCSC-Nummern, Netze, Blätter, Blöcke, Netzklassen
build_lib.py        lib/mainboard.*: Teensy-Symbol, Sockel-Footprint, 3D-Modelle Teensy und XT30; Pin-Typen der LCSC-Symbole
gen_schematic.py    Projektdatei (JLC-Regeln, Netzklassen, ERC-Ausschlüsse), Wurzelblatt und 7 Unterblätter
check_design.py     Tor 1: Netzliste aus dem Schaltplan gegen die Pin-Tabelle der Spezifikation
gen_pcb.py          Platine: Umriss, Footprints, Platzierung, Flächen, Sperrflächen, Plane-Vias, DSN/SES, Nachbesserung
render.py           Lagenbilder zuschneiden und zusammenfügen, Renders auf die Platine zuschneiden
make.sh             ganze Kette: ./make.sh [sch|pcb|drc|img]
snapshot.py         schnelles Bild einzelner Lagen beim Entwickeln
lib/                lcsc.* (easyeda2kicad), mainboard.* (eigene)
out/                Schaltplan-PDF, ERC- und DRC-Bericht (alles andere dort ist Zwischenstand)
img/                Renders und Lagenbilder
```

Neu erzeugen (Git Bash):

```bash
./make.sh
```

`make.sh` ruft `kicad-cli` aus der Bash auf und nicht aus Python. Aus der Microsoft-Store-Python gestartet,
findet `kicad-cli` die globalen Bibliothekstabellen nicht, denn der App-Container der Store-Python
verdeckt sie. Der ERC meldet dann 265 Bibliotheksfehler, und die Renders haben keine Modelle.

Warum Code statt GUI: Schaltung, Schaltplan und Platine können nicht auseinanderlaufen, jede Änderung ist
ein Diff in `circuit.py`, und ERC, Netzlistenprüfung und DRC laufen auf Knopfdruck. Die Dateien lassen sich
normal in KiCad öffnen. Sobald dort von Hand geroutet wird (§5.4), ist die Platinendatei die Quelle und
`./make.sh pcb` darf nicht mehr laufen. `./make.sh sch` und `./make.sh drc` bleiben nutzbar.

## 4. Schaltplan

Jedes Pin bekommt einen kurzen Draht und ein globales Netzlabel. So sind die Netznamen in Netzliste,
Platine, Netzklassen und Spezifikation dieselben (`VBAT_MEAS`, nicht `/Versorgung/VBAT_MEAS`). Jedes Blatt
ist in umrahmte Funktionsblöcke gegliedert. Die Blätter heißen Versorgung, Teensy, Sensorik, Funk,
Aktoren, Pyro und Signal. Die UUIDs werden aus Blatt und Referenz berechnet und sind deshalb bei jedem
Lauf gleich. PDF: `out/mainboard_schematic.pdf`.

## 5. Platine

### 5.1 Lagen

| Lage | Inhalt |
|---|---|
| F.Cu | alle Bauteile, Signale, GND-Füllung |
| In1.Cu | **durchgehende GND-Fläche** (Lagentyp *power*, wird nicht geroutet) |
| In2.Cu | Signale, GND-Füllung |
| B.Cu | **geteilte Versorgungsfläche**: GND_PWR unter den Aktoren (TVC-Ende, rechter Streifen bis zum Motortreiber) und als Streifen an der rechten Kante bis zu den Pyro-FETs an der Spitze; **5V_SYS** auf der übrigen Fläche |

Die Spezifikation sah die Versorgungsflächen auf Lage 3 vor. B.Cu ist gleichwertig und trägt ohnehin
keine Bauteile. In2 bleibt so als zweite Signallage frei; ohne sie war die Platine nicht zu entflechten.
Jedes SMD-Pad von GND, GND_PWR und 5V_SYS bekommt ein eigenes Via zu seiner Fläche, insgesamt 109. Das
Via sitzt nur dort, wo Pad und Via über dem eigenen Teil der Teilung liegen.

### 5.2 Netzklassen

| Klasse | Bahn | Netze |
|---|---|---|
| Strom | 1,0 mm | VBAT2_RAW, VBAT2_REV, VBAT_PROT, VBAT_MEAS, VSERVO, VBAT_ARMED, PYRO1/2_NEG |
| Rückstrom | 0,8 mm | GND_PWR (wo es nicht auf der Fläche läuft) |
| Versorgung | 0,5 mm | 1S-Pfad, 5V_SERVO, 3V3_RF, TEENSY_VIN, MOT_A/B, U1_SW |
| Wandler | 0,25 mm | VSYS_IN, U2_L1, U2_L2 (Pins des TPS63070 mit 0,5 mm Raster) |
| Default | 0,2 mm | Signale, 3V3, GND (GND läuft über die Flächen) |

JLC-Regeln im Projekt: 0,127 mm Abstand, Bahn mindestens 0,09 mm (Freerouting verjüngt an Pins auf
0,10 bis 0,12 mm), Via 0,45/0,2 mm, 0,2 mm zum Rand.

### 5.3 Platzierung

Platziert wird nach `mainboard_placement.svg`. Die Stecker sind bündig an den Stirnseiten fest gesetzt,
ebenso ICs, Spulen und Elkos (`ANCHORS`, `EDGE` in `gen_pcb.py`). Die Passiven setzt eine gierige Suche
je Funktionsblock in dessen Region an das Pad, mit dem sie ein Netz teilen, mit 0,35 mm Abstand für
Routingkanäle. Gemessene Regeln:

- IMU genau auf der Rollachse unter dem Teensy, Chip-X quer, Chip-Y zur Spitze (Footprint gegen DS-000347
  geprüft). Darunter keine Vias, auf In2 keine Bahnen. Die Spulen liegen mehr als 25 mm entfernt.
- LoRa-Modul im linken Streifen, Antennenseite zur Spitze. Die Randpads des Moduls ragen 0,9 mm über den
  Körper hinaus; es hat 0,2 mm zum Rand und 0,53 mm zu den Teensy-Pads.
- Die Spulen der Wandler liegen so, dass SW, L1 und L2 ohne Kreuzung an ihre Pins gehen.
- SD- und USB-Freiraum gilt nur für hohe THT-Teile. Karte und Stecker sitzen auf Teensy-Höhe, flache
  SMD-Teile dürfen darunter.

### 5.4 Routing und was offen ist

Freerouting entflechtet den Großteil. Zwei Nachläufe exportieren die vorhandenen Bahnen als *fix* und
routen nur das Offene; das Ergebnis wird in die Platine übernommen. Ein gewöhnlicher zweiter Lauf reißt
alles neu auf und endet schlechter. Zuletzt schließt `gen_pcb.py patch` Bahnenden, die knapp vor ihrem Pad
aufhören, mit kollisionsgeprüften Stummeln.

**Drei Verbindungen fehlen und sind in KiCad von Hand zu ziehen** (interaktiver Router, wenige Minuten):

| Netz | Wo | Warum |
|---|---|---|
| MOT_A | DRV8833 Pin 2 ↔ Pin 7 | parallele Brücken: MOT_A umschließt MOT_B (Pins 4/5), braucht ein Via und einen Bogen über In2 |
| MOT_IN2 | DRV8833 Pin 10 ↔ Pin 15 | dasselbe auf der Eingangsseite |
| SDA | BMP390 Pin 4, 0,7 mm Bahnende | LGA mit 0,5 mm Raster, Bahn endet vor dem Pad |

Freerouting ist zwischen Läufen nicht vollständig reproduzierbar. Ein neuer `./make.sh pcb` kann eine
andere Handvoll offener Verbindungen hinterlassen. Die eingecheckte Platine ist der beste Lauf.

### 5.5 Bestückungsdruck

Steckerbeschriftung (S/+/−), IMU-Achsen, Revision, Platzhalter `JLCJLCJLCJLC` unter dem Teensy. Die
Referenzen der Passiven stehen nur auf F.Fab, die Zusatzfelder (LCSC, Funktion, Datenblatt) sind
unsichtbar. Der DRC meldet noch 167 Bestückungsdruck-Warnungen. Ursachen sind Elko-Kreise, die
Nachbarumrisse schneiden, und Siebdrucklinien der EasyEDA-Footprints über Pads (JLC schneidet diese
automatisch weg). Das ist kosmetisch und wird beim Review bereinigt.

## 6. Entscheidungen, die die Spezifikation offen ließ oder die von ihr abweichen

| Punkt | Entscheidung | Grund |
|---|---|---|
| Referenzen | Standard (J1 bis J15, U1 bis U10, Q1 bis Q5, A1 = Teensy); der Name aus der Spezifikation steht im Feld `Funktion` | KiCad-Annotation braucht Präfix plus Zahl; Zuordnung in §7 |
| Stecker an der TVC-Stirnseite | nur XT30 und die zwei TVC-Servos liegend; J_BAT1, J_SW, J_SERVO3, J_MOT stehend | nutzbar sind 41 mm Kante, alle liegend bräuchten 62 mm |
| Stecker an der Spitze | Pyro und Arming liegend an der Kante, GPS/Kamera/LED/Qwiic als stehende JST-GH/SH | gleicher Grund |
| Sternpunkt | eigenes Netz **GND_PWR**, eine Netzbrücke NT1 am 2S-Minus, als Fläche auf B.Cu | macht §3/§8 im Layout prüfbar |
| Versorgungsflächen | auf B.Cu statt In2 (§5.1) | In2 wird als Signallage gebraucht |
| Bahnbreiten | Strom 1,0 mm statt 2 mm; dafür GND_PWR und 5V_SYS als Fläche | 2 mm passen nicht an 2,0/2,5-mm-Steckerpins; beim Review die Pyro-Spitze (5 A, 20 ms) prüfen |
| Teensy-Pin 8 | **MOT_FAULT** (nFAULT des DRV8833, 10 k nach 3V3) | war in der Spezifikation nicht vergeben |
| Reset-Taster SW_RST | entfallen | der Teensy 4.1 hat am Sockel keinen Reset; der Program-Taster ist durch die Luke erreichbar |
| TVS | SMBJ12CA (bidirektional) | keine Polaritätsfrage |
| TPS63070 | FB 680 k / 130 k (4,98 V); EN-Teiler 330 k / 100 k: an ab 3,44 V, aus unter 3,01 V; PS/SYNC hoch | Tiefentladeschutz für den 1S-Akku ohne Zusatzteil |
| TPS563201 | FB 56 k / 10 k → 5,07 V | |
| ICM-42688-P | RESV und FSYNC an GND, VDD 100 n + 2,2 µ, VDDIO 10 n; CS mit 10 k nach 3V3 | DS-000347 Tab. 9/10 |
| Servo-Signale | 220 Ω in Reihe | Schutz der Teensy-Pins |
| E22 | RESET und ANT-Pad offen, Antenne über die IPEX-Buchse | |
| LCSC-Nummern | nur bei den Teilen aus `../ORDER.md` §3.3 | Passive beim Bestellen mit dem JLC-Plugin zuordnen |
| ERC-Ausschlüsse | DRV8833: Brückenausgänge parallel; AISEN/BISEN direkt an GND_PWR | gewollt |

## 7. Referenzen ↔ Namen der Spezifikation

| Ref | Spezifikation | Ref | Spezifikation |
|---|---|---|---|
| A1 | U_TEENSY | J8 | J_MOT |
| J1 | J_BAT2 (XT30) | J9, J10 | J_PYRO1, J_PYRO2 |
| J2 | J_BAT1 | J11 | J_GPS |
| J3 | J_SW | J12 | J_QWIIC |
| J4 | J_ARM | J13 | J_CAM |
| J5, J6, J7 | J_SERVO1, 2, 3 | J14 | J_LED |
| R_SH1 | R_SHUNT | J15 | J_EXP |
| Q3, Q4 | Q_P1, Q_P2 | Q5 | Q_BZ |
| D2, D3 | D_TVS | NT1 | Sternpunkt GND_PWR/GND |

## 8. Nächste Schritte

0. **Review-Punkte A1 bis A8 aus `../review_kicad_2026-10-21.md` einarbeiten**, bevor von Hand
   geroutet wird. Die Punkte A1 bis A5 ändern die Schaltung, A6 bis A8 die Art, wie die Strompfade
   geroutet werden. Danach wird die Platine mit `./make.sh` neu erzeugt und mit
   `../review_check_layout.py` nachgemessen.
   - **A1 ist ein Datenblattverstoß**: 1066 µF am Ausgang des TPS63070, erlaubt sind 470 µF. Der
     1000-µF-Elko kommt hinter D1 an TEENSY_VIN.
   - A2: Unterspannungsschwelle des 1S-Akkus tiefer legen.
   - A3: Hauptschalter schaltet über FETs statt im Strompfad.
   - A4: Sicherungen je Akku.
   - A5: Kelvin-Abgriff am Shunt, etwa mit Netzbrücken, sodass nur der INA219 die Sense-Netze sieht.
   - A6: 2S-Netze nur auf den Außenlagen, nicht auf In2 (0,5 oz), und mit Abstand zur IMU.
   - A7: VSYS_IN nach dem Pin-Austritt auf ≥ 0,6 mm aufweiten.
   - A8: keine 0,15-mm-Stücke in 5V_SERVO.

   Für A6 bis A8 genügt der Autorouter mit Netzklassen nicht. Der Generator legt den 2S-Pfad, VSYS_IN
   und 5V_SERVO vorab als F.Cu-Flächen an (Review B13). Freerouting routet danach nur noch die Signale.
   Die B-Punkte nach Aufwand.

   In derselben Runde gehen die Punkte aus `../review_netlist_2026-10-21.md` mit:
   - TPS63070 FB2 (Pin 6) offen statt an GND.
   - E22 NRST (Pin 1) über 10 k an 3V3_RF, zusätzlich an einen freien Teensy-Pin (Review B9 nennt Pin 31).
   - Am Bestelltag prüfen, dass die LCSC-Nummer C1850418 wirklich ein TDK-InvenSense-Teil ist. LCSC
     verlinkt ein Datenblatt der Marke Tokmas.

   Die RESV-Belegung des ICM-42688-P ist gegen DS-000347 Tab. 9 bestätigt: Pin 7 „Connect to GND“,
   Pins 2, 3, 10, 11 „No Connect or Connect to GND“, FSYNC an GND, wenn unbenutzt.
1. In KiCad die dann noch offenen Verbindungen ziehen (heute drei, §5.4) und den Bestückungsdruck
   bereinigen. Danach `./make.sh drc`.
2. Review mit dem Kollegen anhand von Schaltplan-PDF, `img/layers.pdf` und Design Guide (Tor 1 und 2 in
   `../ORDER.md`). Dabei besonders auf diese Punkte schauen:
   - Breite und Lage der Strompfade;
   - Masseführung um den Sternpunkt;
   - der Abstand LoRa ↔ IMU.
3. 1:1-Papierausdruck mit Teensy und Steckern in den Kuppler halten.
4. Fertigungsdaten über `kicad-cli`: Gerber, Bohrdaten, BOM und CPL im JLC-Format. Die LCSC-Nummern der
   Passiven ergänzen. Fertiger nach `../Fertiger_2026-10-21.md`: JLCPCB Economic; das BMP390 ist dort
   zurzeit nicht lieferbar.
