# Mainboard rev B – KiCad-Projekt

Stand 2026-10-21. Schaltplan und Platine von rev B werden hier **aus Code erzeugt**, nicht von Hand
gezeichnet. Die Quelle der Wahrheit ist `circuit.py`; Schaltplan, Platine und Prüfungen werden daraus
abgeleitet. Die Vorgabe ist die Spezifikation `../README.md` (rev B). Dieses Dokument beschreibt,
wie das Projekt entstanden ist, was fertig ist, was offen ist und wo bewusst von der Spezifikation
abgewichen wurde.

## 1. Stand auf einen Blick

| Schritt | Stand |
|---|---|
| KiCad 10.0.6 installiert | erledigt (Benutzerinstallation, siehe §2) |
| Bibliotheken (Teensy 4.1, LCSC-Teile) | erledigt, `lib/` |
| Schaltung als Daten | erledigt, `circuit.py`: 134 Bauteile, 89 Netze, 7 Blätter |
| Schaltplan | erledigt, `mainboard.kicad_sch` + 7 Unterblätter, PDF in `out/` |
| ERC | **0 Fehler, 0 Warnungen**, 4 begründete Ausschlüsse (DRV8833, §5) |
| Platine: Umriss, Footprints, Netze, Lagen, Flächen | Generator fertig (`gen_pcb.py`) |
| Platine: Platzierung | **Entwurf, nicht fertig**: 12 Überschneidungen fest platzierter Teile, 9 Teile ohne Platz (§6) |
| Routing (Freerouting) | vorbereitet (DSN-Export, SES-Import im Generator), noch nicht gelaufen |
| DRC, Gerber, BOM/CPL | offen |

## 2. Werkzeuge und Installation

- **KiCad 10.0.6** (aktuelle Version in winget, nicht 9 wie im Plan). Die winget-Installation für alle
  Benutzer blieb an der Administrator-Abfrage hängen. Deshalb wurde der signierte Installer
  (KiCad Services Corp.) als **Benutzerinstallation** ausgeführt: `/S /CurrentUser`, Ziel
  `%LOCALAPPDATA%\Programs\KiCad\10.0`. Die globalen Bibliothekstabellen (`sym-lib-table`,
  `fp-lib-table`) wurden aus dem KiCad-Template nach `%APPDATA%\kicad\10.0\` kopiert. Das macht die
  GUI sonst beim ersten Start; `kicad-cli` braucht sie.
- **easyeda2kicad** (pip) für die vier Teile, die die KiCad-Bibliothek nicht hat. Symbol, Footprint und
  3D-Modell kommen direkt aus der LCSC/EasyEDA-Datenbank, also genau die Footprints, mit denen JLC bestückt:
  ICM-42688-P (C1850418), BMP390 (C5124834), TPS63070RNMR (C109322), E22-400T22S (C2903765).
- **Freerouting CLI 2.5.0** (offizielles GitHub-Release, Prüfsumme kontrolliert) unter
  `%LOCALAPPDATA%\Programs\freerouting-cli\freerouting-cli.exe`, eigenständig, ohne Java.
- Datenblätter für die eigenen Entscheidungen: TPS63070 (SLVSC58B: Pinbelegung, Teiler-Tabelle 4,
  Kondensatoren) und ICM-42688-P (DS-000347: RESV-Pins, Abblockung, Tabelle 9/10).

## 3. Aufbau und Ablauf

```
circuit.py          Schaltung als Daten: Bauteile, Werte, Footprints, LCSC-Nummern, Netze, Blätter, Blöcke
build_lib.py        lib/mainboard.kicad_sym + Teensy41_Socket.kicad_mod; setzt die Pin-Typen der LCSC-Symbole
gen_schematic.py    Projektdatei (Regeln, Netzklassen, ERC-Ausschlüsse), Wurzelblatt + 7 Unterblätter
gen_pcb.py          Platine: Umriss, Footprints mit Netzen, Platzierung, GND-Flächen, Sperrflächen, Bestückungsdruck
sexpr.py            kleiner S-Ausdruck-Leser/-Schreiber für die KiCad-Dateien
lib/                lcsc.* (easyeda2kicad), mainboard.* (Teensy)
out/                erzeugte PDFs, DSN/SES, Berichte
```

Neu erzeugen:

```bash
python build_lib.py
python gen_schematic.py
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/kicad-cli.exe" sch erc --format report -o out/erc.rpt mainboard.kicad_sch
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/kicad-cli.exe" sch export pdf -o out/mainboard_schematic.pdf mainboard.kicad_sch
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py place
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py dsn
"$LOCALAPPDATA/Programs/freerouting-cli/freerouting-cli.exe" -de out/mainboard.dsn -do out/mainboard.ses -mp 30
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py ses
```

Die letzten drei Zeilen (Routing) sind vorbereitet, aber noch nicht gelaufen (§6).

Warum Code statt GUI: Schaltung, Schaltplan und Platine können nicht auseinanderlaufen, jede Änderung ist
ein Diff in `circuit.py`, und ERC, DRC und Netzlistenprüfung laufen auf Knopfdruck. Die erzeugten Dateien
lassen sich trotzdem normal in KiCad öffnen und von Hand weiterbearbeiten. Ab dem Moment, in dem von Hand
geroutet oder geschoben wird, ist der Generator für die Platine allerdings nicht mehr die Quelle.

### Schaltplan

Jedes Pin bekommt einen kurzen Draht und ein Netzlabel: lokal, wenn das Netz auf seinem Blatt bleibt,
global, wenn es Blätter verbindet. Jedes Blatt ist in umrahmte Funktionsblöcke gegliedert, etwa
„2S: Buck U1 → 5V_SERVO“ oder „IMU ICM-42688-P, SPI1“. Die Blätter heißen Versorgung, Teensy, Sensorik,
Funk, Aktoren, Pyro und Signal. Die Symbole stammen aus der KiCad-10-Standardbibliothek, abgeleitete
Symbole werden flach kopiert. Die UUIDs werden aus Blatt und Referenz berechnet und sind deshalb bei
jedem Lauf gleich, die Diffs bleiben klein.

### Platine

- Umriss 54 × 120 mm, R 2 mm, aus den Konstanten von `../outline.py` gezeichnet; geometrisch identisch
  mit `mainboard_outline.dxf`. Die 4 M3-Bohrungen sind Footprints H1 bis H4.
- 4 Lagen. In1 ist als *power plane* markiert und bleibt reine GND-Fläche, Freerouting meidet sie. GND-Füllung
  liegt auf allen vier Lagen.
- Netzklassen: *Strom* 1,2 mm (VBAT-Pfade, VSERVO, Pyro, GND_PWR), *Versorgung* 0,6 mm (1S-Pfad, 5V_SYS,
  5V_SERVO, 3V3, Motor), Signale 0,2 mm. Dazu JLC-Mindestwerte im Projekt: 0,127 mm Bahn und Abstand,
  Via 0,45/0,3 mm.
- Sperrflächen: um die IMU keine Vias, darunter auf In2/B.Cu keine Bahnen; unter dem LoRa-Modul keine
  Bahnen und Vias auf F.Cu/In2.
- Platzierung: Stecker, ICs, Spulen und Elkos sind fest gesetzt (`ANCHORS`, `EDGE` mit bündiger
  Steckeröffnung an der Stirnseite). Die Passiven setzt eine gierige Suche je Funktionsblock in dessen
  Region, so nah wie möglich an das Pad des Bauteils, mit dem sie ein Netz teilen. Abblockkondensatoren
  landen so am richtigen Pin.
- Bestückungsdruck: Steckerbeschriftungen, IMU-Achsenpfeile (X quer, Y zur Spitze), Revision, Platzhalter
  `JLCJLCJLCJLC` für die Auftragsnummer unter dem Teensy. Die Referenzen der Passiven stehen nur auf F.Fab.

## 4. Entscheidungen, die die Spezifikation offen ließ oder die von ihr abweichen

| Punkt | Entscheidung | Grund |
|---|---|---|
| Referenzen | Standard (J1 bis J15, U1 bis U10, Q1 bis Q5, A1 = Teensy); der Name aus der Spezifikation steht im Feld `Funktion` | KiCad-Annotation braucht Präfix plus Zahl; Zuordnung in §7 |
| Stecker an der TVC-Stirnseite | nur XT30 (14,4 mm) und die zwei TVC-Servos (je 11 mm) liegend; J_BAT1, J_SW, J_SERVO3, J_MOT **stehend** (Top-Entry) | nutzbar sind wegen der Bohrungen nur 41 mm, alle liegend bräuchten 62 mm |
| Stecker an der Spitze | J_PYRO1/2 und J_ARM liegend an der Kante; GPS, Kamera, LED, Qwiic als stehende JST-GH/SH | gleicher Grund |
| Sternpunkt | eigenes Netz **GND_PWR** für alle 2S-Rückströme, Netzbrücke NT1 am 2S-Minus | macht die Masseführung aus §3/§8 im Layout prüfbar |
| Teensy-Pin 8 | war in der Spezifikation nicht vergeben; jetzt **MOT_FAULT** (DRV8833 nFAULT, 10 k nach 3V3) | Fehlermeldung des Motortreibers kostenlos mitnehmen |
| Reset-Taster SW_RST | **entfallen** | der Teensy 4.1 hat am Sockel keinen Reset; der Program-Taster sitzt auf dem Teensy und ist durch die Luke erreichbar |
| TVS | SMBJ12**CA** (bidirektional) statt SMBJ12A | keine Polaritätsfrage beim Bestücken |
| TPS63070 | FB 680 k / 130 k (4,98 V, TI-Tabelle 4); EN-Teiler 330 k / 100 k als Unterspannungsschutz des 1S-Akkus: an ab 3,44 V, aus unter 3,01 V; PS/SYNC hoch | Tiefentladeschutz ohne Zusatzteil |
| TPS563201 | FB 56 k / 10 k → 5,07 V, EN über 100 k an VIN | |
| ICM-42688-P | RESV (2, 3, 7, 10, 11) und FSYNC an GND, VDD 100 n + 2,2 µ, VDDIO 10 n (DS-000347 Tab. 9/10); CS mit 10 k nach 3V3 | CS bleibt beim Booten inaktiv |
| Servo-Signale | 220 Ω in Reihe | Schutz der Teensy-Pins bei Kurzschluss im Kabel |
| E22 | RESET und ANT-Pad offen, Antenne über die IPEX-Buchse des Moduls | |
| Bahnbreiten | 1,2 mm statt 2 mm für die Stromnetze | 2 mm passen nicht zwischen 2,0/2,5-mm-Steckerpins; 1,2 mm tragen ca. 3 A außen; für die Pyro-Spitze (5 A, 20 ms) reicht das, beim Layout-Review prüfen |
| LCSC-Nummern | nur bei den Teilen aus `../ORDER.md` §3.3 eingetragen | Passive beim Bestellen mit dem JLC-Plugin zuordnen, keine geratenen Nummern |
| W25Q128 | nicht auf der Platine | kommt laut Spezifikation unter den Teensy |

## 5. ERC

`kicad-cli sch erc`: 0 Fehler, 0 Warnungen. Vier Befunde sind im Projekt als Ausschluss mit Begründung
eingetragen. Zwei davon: Die Brückenausgänge des DRV8833 sind gewollt parallel geschaltet (AOUT1/BOUT1,
AOUT2/BOUT2). Die anderen zwei: AISEN/BISEN liegen ohne Strommessung direkt auf GND_PWR. Unterwegs gelernt:
KiCad 10 speichert ERC-Ausschlüsse als `typ|x|y|uuid1|uuid2|blatt|blatt1|blatt2`, Positionen in 100 nm.

## 6. Wo die Platzierung steht

Der erste Lauf von `gen_pcb.py place` setzt 125 von 134 Footprints. Er meldet noch
12 Überschneidungen fester Teile, unter anderem:

- J1 mit J3, NT1 und H1;
- A1 mit U6 und U10: INA219 und LoRa-Modul ragen in den Sockelstreifen, die Streifen links und rechts
  sind nur 16 mm breit;
- C3 mit J7, L1/C11/U7 im rechten Streifen, J15 mit dem Summer, J11/J13/J14 untereinander.

Für 9 Teile (D1, C23–C25, R14, D3, Q5, R34, R35) findet die Suche keinen Platz. Die Courtyard-Maße aller
fest gesetzten Teile sind ermittelt. Die nächste Runde verschiebt die Anker danach und erweitert die
Regionen. Danach folgen Routing und DRC.

Ehrliche Einschätzung: Die Fläche ist knapp. 134 Teile, drei stehende Elkos und das 16 × 26 mm große
Funkmodul müssen in zwei 16-mm-Streifen neben dem Teensy. Wahrscheinlich müssen dafür einige 0603-Teile
auf 0402 schrumpfen oder unter den Teensy wandern.

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

1. **Platzierung fertigstellen**: die Überschneidungen aus §6 beheben, alle Teile setzen, danach
   Freerouting laufen lassen, Flächen füllen und den DRC mit den JLC-Regeln fahren.
2. **Schöne Abbildungen der Platine**: Raytracing-Render von oben und unten und schräg
   (`kicad-cli pcb render`, mit den 3D-Modellen der LCSC-Teile), dazu Lagenbilder (F.Cu, In2, B.Cu,
   Bestückungsdruck) als SVG/PDF. Vergleich mit `mainboard_placement.svg` und den Hüllen aus
   `outline.py`. Die Abbildungen gehen in den Design Guide.
3. **Wo fertigen lassen**: Die bisherige Planung (`../ORDER.md`) geht von JLCPCB aus. Das ist
   naheliegend, weil die LCSC-Footprints direkt passen und die Bestückung dort günstig ist. Zu vergleichen
   wären europäische Fertiger mit Bestückung, etwa Aisler (DE), Eurocircuits (BE), Multi-CB (DE), und
   PCBWay als zweite Option aus China. Kriterien: 4 Lagen, ENIG, Bestückung von LGA-14/LGA-10/VQFN,
   Teileverfügbarkeit (ICM-42688-P, BMP390, TPS63070, E22), Lieferzeit, Zoll und Einfuhrumsatzsteuer,
   Gesamtpreis für 5 Platinen davon 2 bestückt. Preise und Bestand am Tag der Entscheidung prüfen.
4. Tor-1-Prüfung aus `../ORDER.md`: ein Skript, das die Netzliste gegen die Pin-Tabelle in `../README.md` §4
   vergleicht; dann Review durch den Kollegen anhand des Schaltplan-PDFs.
5. Fertigungsdaten: Gerber, Bohrdaten, BOM und CPL im JLC-Format über `kicad-cli`. Die LCSC-Nummern
   der Passiven ergänzen.
