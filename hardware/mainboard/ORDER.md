# Mainboard rev B – Bestellplan

Stand 2026-10-21, abends ergänzt um den KiCad-Stand, die Tor-1-Prüfung und die Fertigerübersicht. Gehört zur
Spezifikation `README.md` (rev B) und zum Design Guide `docs/DesignGuide_Mainboard_revB.md`; der Vergleich
der Fertiger steht in `Fertiger_2026-10-21.md`, die Netzlistenprüfung in `review_netlist_2026-10-21.md`. Dieser Plan sagt, **was in welcher Reihenfolge bestellt wird,
welche Tore vorher passiert sein müssen und was es kostet**. Der Schaltplan existiert seit dem Abend des 21.10. als KiCad-Projekt
(`kicad/`, aus `circuit.py` erzeugt, ERC sauber), das Layout ist im Entwurf; die Platine kann also erst nach den
Toren 1 und 2 bestellt werden. Einiges lässt sich aber jetzt
schon kaufen, damit Firmware und Mechanik nicht auf die Platine warten.

![Weg zur Platine](img/order_flow.svg)

## 1. Was jetzt schon bestellt werden kann (Tor 0)

Diese Teile hängen nicht vom Layout ab. Sie machen den Breakout-Aufbau zum Testträger für die
rev-B-Firmware und sparen später Wartezeit.

| Nr. | Teil | Stück | Wofür | Quelle (Vorschlag) | ca. |
|---|---|---|---|---|---|
| 0.1 | LSM6DSV16X-Breakout (SPI herausgeführt; seit 23.10. statt ICM-42688-P, E12) | 1 | IMU-Treiber und Gyro-Quaternion am Tisch entwickeln, bevor die Platine da ist | Adafruit 4692 (über Berrybase/Eckstein), SparkFun, AliExpress | 10–20 € |
| 0.2 | BMP390-Breakout (Adafruit 4816 oder Clone) | 1 | `BMP3XX`-Treiber und Kalman-Rauschwert vorab | Berrybase, Eckstein | 10–15 € |
| 0.3 | LoRa **E22-400T22D** (DIP, SMA) | 2 | eins für die Bodenstation (bleibt dort), eins als Gegenstelle für den Tisch, bis das SMD-Modul auf der Platine ist | Ebyte über AliExpress/eBay/Tindie | 2 × 8–12 € |
| 0.4 | 433-MHz-Antenne SMA (Stab, λ/4) | 2 | Bodenstation und Tischtest | dieselbe Bestellung wie 0.3 | 2 × 2–4 € |
| 0.5 | IPEX/u.FL → SMA-Buchse Pigtail, 10 cm | 2 | Rakete: vom E22-400T22S zur Antenne in der Spitze; ein Reserve | Berrybase, AliExpress | 2 × 2–3 € |
| 0.6 | 1S-LiPo 450–600 mAh, 20 C, JST-PH 2.0 | 2 | Elektronik-Akku; zwei, damit einer lädt | Hobbyking, Modellbau-Händler | 2 × 5–8 € |
| 0.7 | 2S-LiPo 450–850 mAh, 50 C, XT30 | falls nicht vorhanden `[?]` | Aktoren und Pyro | Modellbau-Händler | 12–20 € |
| 0.8 | Ladegerät-Adapter 1S JST-PH (falls das Ladegerät nur XT60/Balancer kann) | 1 | | | 3–5 € |
| 0.9 | Zweipoliger Schiebeschalter (DPDT, ≥ 3 A), kleine Bauform | 2 | Hauptschalter am Rumpf, einer Reserve | Reichelt | 2 × 1–2 € |
| 0.10 | Schlüsselschalter oder Kippschalter mit Sicherung für Arming | 1 | J_ARM, von außen bedienbar | Reichelt | 3–6 € |
| 0.11 | JST-XH 2- und 3-polig: Platinenstecker liegend, Gehäuse, Crimpkontakte; JST-PH 2- und 4-polig ebenso; JST-GH 3/4 und JST-SH 4 **konfektioniert** (Kabel mit Stecker, 10–15 cm) | Sortiment | Servos, Pyro, Akku 1S, Schalter, GPS, Kamera, Qwiic | Reichelt, Eckstein, AliExpress-Sortiment | 15–25 € |
| 0.12 | Crimpzange für JST-XH/PH (z. B. Engineer PA-09 oder IWISS SN-01BM) | 1 | die W5652H-Kabel und die Pyro-Kabel bekommen XH-Gehäuse | | 20–45 € |
| 0.13 | XT30PW-M liegend (Platinenstecker) | 3 | J_BAT2 plus Reserve | Reichelt, Hobbyking | 3 × 1 € |
| 0.14 | Buchsenleiste 1×24, 2,54 mm, 8,5 mm hoch | 4 | Teensy-Sockel (zwei je Platine) | Reichelt | 4 × 0,5 € |
| 0.15 | Stiftleiste 2×7, 2,54 mm | 2 | J_EXP | Reichelt | 1 € |
| 0.16 | Aktiver Summer 5 V, 12 mm, THT | 2 | BZ1 | Reichelt | 2 × 1 € |
| 0.17 | Polymer-Elko 1000 µF/10 V stehend ≤ 12 mm, Low-ESR-Elko 1000 µF/16 V, 470 µF/10 V | je 2 | C_BULK; nur wenn JLC sie nicht bestückt | Reichelt (Panasonic, Nichicon) | 5–8 € |
| 0.18 | Taster 6 × 6 mm SMD (falls nicht aus JLC) | 5 | SW_RST | Reichelt | 1 € |
| 0.19 | W25Q128JVSIQ (SOIC-8) | 2 | Flash unter den Teensy | Reichelt, LCSC | 2 × 1,5 € |
| 0.20 | GPS-Modul u-blox MAX-M10S oder NEO-M9N (Breakout mit Patchantenne) | 1, optional | nur Komfort für den ersten Flug | Berrybase, Mateksys-Händler | 17–30 € |
| 0.21 | Silikonlitze AWG 20 (rot/schwarz), AWG 22, AWG 26 | je 2 m | Akku-, Servo-, Signalkabel | Reichelt | 8–10 € |
| 0.22 | E-Matches / Zünder für den Pyro-Test und Glühlämpchen 6 V als Dummy-Last | | Pyro-Test am Tisch nur mit Lämpchen | Modellbau | |

Zusammen ohne GPS und Crimpzange etwa **90–140 €**, mit beiden **130–215 €**. Die meisten Teile
hält man ohnehin für den Breakout-Aufbau vor. Position 0.1 ist die wichtigste: Der IMU-Treiber ist der
größte Firmware-Brocken, und er lässt sich ohne Platine fertig machen.

## 2. Tore vor der Platinenbestellung

### Tor 1: Schaltplan fertig

Stand 21.10.2026 abends: KiCad 10.0.6 installiert, Projekt `hardware/mainboard/kicad/` angelegt, Schaltung als
Code in `circuit.py` (134 Bauteile, 89 Netze, 7 Blätter), Symbole und Footprints der vier LCSC-Teile über
easyeda2kicad, **ERC 0 Fehler / 0 Warnungen**. Die Netzliste ist gegen die Pin-Tabelle in `README.md` §4 geprüft
(`review_netlist_2026-10-21.md`: konform, vier Hinweise). Offen für Tor 1:

- Die Hinweise aus der Prüfung einarbeiten: TPS63070 FB2 (Pin 6) offen lassen statt GND; Kommentar zu den
  zusammengefassten Doppelpins 7/8 und 12/13 im Footprint; E22 NRST über 10 k an 3V3_RF oder an einen
  Teensy-Pin; IMU-Pins gegen das Datenblatt halten (seit 23.10. LSM6DSV16X, AN5763 Tabelle 1: 9–11 offen).
- **Zweitmeinung-Review vom 21.10.2026** (`review_kicad_2026-10-21.md`): die Punkte A1 bis A5 in `circuit.py`
  einarbeiten (Hold-up-Elko hinter D1, EN-Teiler des TPS63070 auf 2,7 V, Hauptschalter über FETs, Sicherung je
  Akku, Kelvin-Shunt), dazu die B-Punkte nach Aufwand; Jan entscheidet A3 (FET-Schalter) und B6 (BMP390 an SPI).
- **Review durch den Kollegen** anhand des Design Guides, der Blockbilder und der Lagenbilder (der erzeugte
  Schaltplan ist ein Label-Netz ohne gezeichnete Verbindungen, Review-Punkt B15), Punkte eingearbeitet oder
  begründet abgelehnt.

### Tor 2: Layout fertig

- Umriss und Bohrungen kommen aus `gen_pcb.py` (geometrisch gleich `mainboard_outline.dxf`), Zonen wie
  `mainboard_placement.svg`. Stand 21.10.: Platzierung im Entwurf, 12 Überschneidungen und 9 Teile ohne Platz
  (`kicad/README.md` §6); die Fläche in den 16-mm-Streifen neben dem Teensy ist knapp.
- Stand 21.10. nachts: alle 134 Teile platziert und geroutet, DRC 0 Fehler, 3 offene Verbindungen. Vor den
  Fertigungsdaten die Layout-Punkte A6 bis A8 des Reviews: Stromnetze nur auf den Außenlagen (heute zur Hälfte auf
  In2 mit 0,5 oz und 4,5 mm an der IMU vorbei), `VSYS_IN` ≥ 0,6 mm statt 0,25 mm, `5V_SERVO` ohne 0,15-mm-Stücke,
  Kelvin-Weg des INA219, Sperrfläche 5 mm um die IMU, Funkmodul 0,5 mm vom Rand. Prüfung mit
  `review_check_layout.py` wiederholen.
- DRC mit den JLC-Regeln für 4 Lagen (0,09 mm Bahn/Abstand minimal, hier 0,127 mm; Via 0,3/0,45 mm),
  Bahnbreiten nach `README.md` §8.
- 3D-Ansicht gegen die Hüllen aus `outline.py`; nichts höher als 5 mm bei |u| > 25 mm; unten nur
  Lötstifte unter 2 mm.
- Bestückungsdruck: Steckerbelegung (S / + / −), IMU-Achsenpfeile, Revision „rev B 2026-xx“, Platz für die
  JLC-Auftragsnummer festgelegt (Option *Specify a location*), sonst landet sie irgendwo.
- 1:1-Papierausdruck mit Teensy und Steckern in den Kuppler gehalten; Luke und Pigtail-Weg geprüft.
- Alle LCSC-Nummern in der Stückliste am Bestelltag auf Lagerbestand geprüft (§3).

## 3. Die Platinenbestellung bei JLCPCB (Tor 3)

### 3.1 Fertigungsparameter

| Parameter | Wert | Bemerkung |
|---|---|---|
| Lagen | 4 | Stackup JLC04161H-7628 (Standard), Lage 2 GND, Lage 3 Versorgung |
| Maße | 54 × 120 mm, Eckradius 2 mm | aus dem DXF |
| Dicke | 1,6 mm | |
| Kupfer | 1 oz außen, 0,5 oz innen | Standard; Hochstrom läuft außen |
| Oberfläche | **ENIG** | plane Pads für LGA-14 und LGA-10 |
| Lötstopp | grün oder schwarz | schwarz sieht besser aus, grün lässt Fehler leichter erkennen |
| Stückzahl | 5 Platinen | Mindestmenge; 2 bestückt, 3 blank als Reserve |
| Bestückung | **Economic PCBA**, nur Oberseite, 2 Stück | Economic ist einseitig, passt zur Spezifikation „Bestückung nur oben“ |
| THT | selbst löten | Stecker, Buchsenleisten, Elkos, Summer; JLC-THT-Bestückung ist teurer und braucht Standard-PCBA |
| Auftragsnummer | *Specify a location* | im Layout unter dem Teensy |
| Sonstiges | kein Impedanz-Control, keine Castellations, kein Gold-Finger | |

### 3.2 Dateien, die hochgeladen werden

Seit 23.10.2026 erzeugt `./make.sh fab` im KiCad-Ordner alle drei Dateien nach `kicad/fab/` (`mainboard_gerber.zip`, `mainboard_bom.csv`, `mainboard_cpl.csv`) und eine Übersicht `FAB.md`, welche Teile noch keine LCSC-Nummer haben, welche von Hand gelötet werden und welche DNP sind. Die Punkte unten gelten weiter für die Prüfung beim Upload.

1. **Gerber + Drill** als ZIP: in KiCad über das Plugin *Fabrication Toolkit* (erzeugt gleich alles) oder
   *Plot* mit Protel-Endungen, Lagen F/B.Cu, In1/In2.Cu, F/B.Mask, F/B.Silkscreen, F.Paste, Edge.Cuts,
   dazu die Bohrdatei (Excellon, PTH und NPTH zusammen).
2. **BOM** (CSV): Spalten `Comment, Designator, Footprint, LCSC Part #`. Jedes bestückte Bauteil hat eine
   LCSC-Nummer in seinem Symbolfeld `LCSC`; THT-Teile sind als *DNP* markiert oder fehlen in der BOM.
3. **CPL** (Pick-and-Place, CSV): `Designator, Mid X, Mid Y, Layer, Rotation`. Nach dem Upload in der
   Vorschau jede Drehung prüfen, besonders SOT-23-5, VQFN-15 (TPS63070), LGA und das E22-Modul; JLC
   dreht anders als KiCad. Korrekturen im Plugin eintragen, nicht im Layout.
4. Beim Upload prüfen: Pin 1 der ICs in der Vorschau, keine Bauteile über Pads, Lötpaste auf allen LGA-Pads.

### 3.3 Bestückte Bauteile und ihr Status bei LCSC/JLC

Geprüft am 2026-10-21 per Websuche, nicht per Angebot. **Am Bestelltag im JLC-Teileprogramm erneut
prüfen**, der Bestand schwankt. *Basic* kostet keine Rüstgebühr, *Extended* 3 USD je Typ (laut einer
Quelle seit Dezember 2025 1,50 USD).

| Bauteil | LCSC | Klasse | Stand 21.10. | Falls nicht lieferbar |
|---|---|---|---|---|
| LSM6DSV16X (23.10., E12; davor ICM-42688-P C1850418: bei JLC 21,5 USD, 453 Stück) | C5267406 | Extended | über 7000 Stück, ca. 3,4 USD bei JLC; ST-Original | LSM6DSO (C5267404-Familie, gleicher Footprint, Pin 9–11 ebenso offen) oder ICM-42688-P zurück |
| BMP390 | C5124834 | Extended | LCSC am 21.10. nachts: **„Not available now“**, kein Bestand, kein Preis | **BMP388 (C779278, gleiches LGA-10, gleiche Bibliothek): 7362 Stück auf Lager, 7,67 USD (ab 10: 7,06)**, bei Bosch abgekündigt, für einen Lauf von 5 Platinen egal; ob JLC ihn bestückt, am Bestelltag prüfen, sonst Breakout an J_QWIIC oder BMP390 bei Mouser/DigiKey (Lieferzeit 4 bis 13 Wochen) |
| INA219AIDR | C138706 | prüfen | ca. 1200–4400 Stück, 0,76 USD | INA219BIDR |
| TPS63070RNMR | C109322 | Extended | Bestand schwankte zwischen 0 und 18 000, 1,37 USD | TPS63020DSJR (1,8–5,5 V ein, 2 A; dann kein Schutz gegen versehentlich 2S) |
| TPS563201DDCR | C116592 | Basic | bewährt | TPS562201 |
| AP2112K-3.3TRG1 | C51118 | Basic | | ME6211C33 |
| DRV8833PWPR | C50506 | Extended | | DRV8833RTYR (QFN) |
| 74AHCT1G125DBVTG4 | C2870384 | Extended | 126 Stück, 1,31 USD | SN74LV1T34DBVR (C100024, Pegelwandler 3,3 → 5 V, Basic) oder 74AHCT1G125W5-7 von Diodes |
| E22-400T22S | C2903765 | Extended | ca. 590 Stück, 4,2 USD | E22-400T22S beim Hersteller kaufen und selbst auflöten (Pads am Rand, mit dem Kolben machbar) |
| WS2812B-2020 | C965555 | Extended | | WS2812B-2020 von LCSC-Zweitherstellern (C52917434); **Achtung:** WS2812 kann Standard-PCBA erzwingen, dann die LEDs selbst löten oder XL-2020RGBC prüfen |
| AO3401A | C15127 | Basic | | |
| AO3400A | C20917 | Basic | | |
| SS14 | C2480 | Basic | | |
| SMBJ12CA (bidirektional, Entscheidung KiCad-Projekt) | prüfen | | | SMBJ12A |
| 20 mΩ 2512 1 % 1 W | prüfen | | | 2× 40 mΩ 2512 parallel |
| Polyfuse 3 A 1812 (2S) und 2 A 1812 (1S), Review A4 | prüfen | Extended | | Nano2-Schmelzsicherung mit Halter |
| Polymer-Elko 7343: 470 µF/6,3 V (2×), 330 µF/16 V (2×), 470 µF/10 V (1×), Review B3 | prüfen | meist Extended | | THT-Elkos selbst löten |
| AO3401A ×2 zusätzlich als FET-Hauptschalter, Review A3 | C15127 | Basic | | |
| SN74LV1T34DBVR statt 2× 74AHCT1G125, Review B8 | C100024 | Basic | | |
| Shunt 20 mΩ 2512 mit Kelvin-Footprint (vier Pads), Review A5 | prüfen | | | 2-Pad-Shunt mit Netzbrücken an den Pads |
| Ferritperle 0603 600 Ω + 10 µF (3V3_SENS), Review B4 | Basic | | | |
| W25Q128JVSIQ | C97521 (prüfen) | Basic | | kommt unter den Teensy, nicht auf die Platine |
| LIS3MDLTR (Magnetometer, 23.10.) | C478483 | Extended | ca. 9500 Stück, 2,6–5 USD; manche Händler führen ihn als abgekündigt, ST und DigiKey als aktiv: am Bestelltag prüfen | BMM350 oder MMC5983MA (I²C, anderer Footprint) |
| SHT40-AD1B-R3 (Feuchte/Temperatur, 23.10.) | C2848306 | Extended | lieferbar, ca. 1,7 USD | SHT40-AD1B-R2 C2909890 |
| ADXL375BCCZ (±200 g, DNP) | C579466 | Extended | nur Footprint, wird nicht bestückt | – |
| Passive 0402/0603, 4,7 k, 100 k, 33 k, 100 Ω, 100 n, 10 n, 10 µ | Basic | | | |

Zählung nach dem Review: etwa **10 bis 13 Extended-Typen** (dazu kommen Polyfuse und Polymer-Elkos, der
74AHCT1G125 entfällt), also 15 bis 40 USD Rüstgebühr. Wer sparen will, ersetzt den
74AHCT1G125 durch den SN74LV1T34 (Basic) und lässt die WS2812B selbst löten; die IMU, der Baro, der
Buck-Boost und das Funkmodul bleiben Extended.

### 3.4 Kostenschätzung Platinenlauf

| Posten | Schätzung | Grundlage |
|---|---|---|
| 5 Platinen 4 Lagen 54 × 120 mm, ENIG | 30–45 USD | über 100 mm Kante, ENIG-Aufschlag |
| Economic PCBA: Setup 8 USD, Schablone 1,5 USD, ca. 2 × 250 Lötstellen × 0,0017 USD | ca. 11 USD | JLC-Preistabelle |
| Rüstgebühr Extended, 8–10 Typen | 12–30 USD | |
| SMD-Bauteile für 2 Platinen (IMU ca. 4, BMP390 ca. 7, E22 ca. 4, Rest ca. 8 je Platine) | 40–55 USD | LCSC-Preise vom 21.10., Mindestabnahme je Rolle eingerechnet |
| Versand (Euro-Packet/DHL) | 15–25 USD | |
| Einfuhrumsatzsteuer 19 % auf Ware plus Versand | 20–30 EUR | |
| Zoll seit 01.07.2026: 3 € je Warenposition (HS-Code), die 150-€-Freigrenze ist entfallen | 5–15 EUR | `Fertiger_2026-10-21.md` |
| **Summe Platinenlauf** | **ca. 150–220 EUR** | für 5 Platinen, 2 bestückt; nach dem Review etwa 15 USD mehr (Sicherungen, Polymer-Elkos, zwei FETs); Röntgen der LGA/QFN und Versandart können dazukommen |

`Fertiger_2026-10-21.md` vergleicht JLCPCB mit PCBWay, Aisler, Eurocircuits, Multi-CB und Beta Layout und
kommt für den JLC-Auftrag auf 320–380 €, also deutlich mehr als diese Tabelle; die Differenz steckt in den
Annahmen zu Bauteilpreisen, Röntgen, Versandart und Abgaben. Beides sind keine Angebote. Verbindlich wird es am
Bestelltag mit BOM und CPL im JLC-Kalkulator; Aisler (Aachen, kein Zoll, Beistellung des E22) ist der Rückfall in
der EU, etwa 100 € teurer.

Dazu die Teile aus §1 (90–140 €) und der Teensy (vorhanden). Die ganze Elektronik rev B liegt damit
bei **ca. 220–340 EUR**, was die Planungsrunde (170–280 €) um den BMP390-Preis, den zweiten Akku und den
neuen Zoll übertrifft.

### 3.5 Lieferzeit

Economic PCBA mit 4 Lagen: 4 bis 7 Arbeitstage Fertigung, dazu 7 bis 14 Tage Versand nach Deutschland,
also **2 bis 3 Wochen** ab Upload. Die DHL-Option ist eine Woche schneller und 10 USD teurer.

## 4. Nach der Lieferung (Tor 4)

1. Wareneingang: Lagenzahl (Kante anschauen), Maße gegen das DXF, M3-Bohrungen, Bestückungsfotos von JLC
   mit der CPL vergleichen, unter der Lupe LGA-Gehäuse auf Brücken, Teensy-Sockel-Lochreihen auf Fluchtung.
2. Mit dem Multimeter: kein Kurzschluss zwischen GND und VSYS_IN, 5V_SYS, 3V3_RF, VBAT_PROT, VSERVO, 5V_SERVO.
3. THT löten in dieser Reihenfolge: Buchsenleisten (mit gestecktem Teensy als Lehre, ohne ihn zu löten),
   Stecker, Elkos, Summer, Taster, zuletzt JP1/JP2 schließen.
4. Dann der Testplan aus `README.md` §9, beginnend am Labornetzteil mit 100 mA Begrenzung, ohne Teensy.

## 5. Risiken und Entscheidungen, die offen sind

| Risiko | Folge | Vorsorge |
|---|---|---|
| BMP390 bei JLC nicht lieferbar (21.10.: LCSC „Not available now“) | kein Barometer auf der Platine | **Entscheidung: BMP388 (C779278, 7362 auf Lager) für diesen Lauf**, gleicher Footprint und gleiche Bibliothek; sonst Breakout an J_QWIIC oder an SPI1 (Review B6) |
| TPS63070 nicht lieferbar | kein 5V_SYS aus 1S | Footprint zusätzlich für TPS63020 vorsehen? Nein, zu viel Fläche; Bestand vor dem Layout prüfen und notfalls 10 Stück bei LCSC vorbestellen |
| E22-400T22S falsch gedreht oder Pads unter dem Modul nicht benetzt | Funk tot | CPL-Vorschau prüfen; das Modul hat nur Randpads, Nachlöten ist möglich |
| WS2812B erzwingt Standard-PCBA | +17 USD Setup | LEDs als DNP, selbst löten (2020-Gehäuse, Heißluft) oder 5050-Gehäuse nehmen |
| Teensy-Sockelreihen 0,1 mm versetzt | Teensy klemmt | Footprint `Teensy41_Socket` aus `build_lib.py`, Papierausdruck mit echtem Teensy |
| LSM6DSV16X von einem Zweithersteller | anderes Rauschen, andere Register | Hersteller im JLC-Teileprogramm prüfen (nur ST), sonst Chip selbst beschaffen |
| Drehung der VQFN-15 (TPS63070) in der CPL | Wandler kaputt beim ersten Einschalten | Pin-1-Punkt in der JLC-Vorschau, erster Start am Netzteil mit 100 mA |
| Servo-Achsenlage zum Schlitten noch offen (`README.md` §11) | Achsentausch in der Firmware | kein Platinenrisiko, Stecker sind gleich |

## 6. Wer macht was, Reihenfolge der nächsten Wochen

1. Jetzt: §1 bestellen (0.1 bis 0.6, 0.9 bis 0.16 mindestens). Parallel Firmware auf dem Breakout.
2. Schaltplan und Layout stehen (`kicad/`, ERC und DRC sauber). Review-Punkte A1 bis A8 einarbeiten
   (`review_kicad_2026-10-21.md` §6 nennt die Reihenfolge), Platine neu erzeugen → Tor 1.
3. Letzte Verbindungen schließen, `review_check_layout.py` und DRC, Papierprobe, Kollegen-Review → Tor 2.
4. Am Bestelltag §3.3 durchgehen, dann hochladen → Tor 3. Während der Lieferzeit: Träger drucken, Kabel
   konfektionieren, Antenne in die Spitze.
5. Tor 4 und Testplan. Erst danach die Firmware auf die Platine.

## 7. Bestellliste nach Händlern (Stand 21.10.2026 nachts)

Konkrete Fassung von §1 nach dem Review (`review_kicad_2026-10-21.md`) und dem Inventar in `docs/BUILD.md` §1.3.
Preise sind aus Händlerseiten und Suchtreffern vom 21.10.2026, **keine Angebote**; beim Bestellen prüfen. Was schon da
ist: Teensy 4.1, Breakouts ICM-20948, BMP280, INA219, 2× HC-12, SG90, WS2812B, Summer, HTRC-H4AC-Lader (2 bis 4S,
**kein 1S**), 4S-Akku für den Prüfstand, W5652H bestellt. Der 2S-Flugakku steht in `BUILD.md` mit `[?]`.

### 7.1 Jetzt bestellen (Tischaufbau und Firmware, unabhängig von der Platine)

| Nr. | Teil | Stück | Quelle | ca. | Hinweis |
|---|---|---|---|---|---|
| 0.1 | LSM6DSV16X-Breakout (SPI herausgeführt) | 1 | Adafruit 4692 über Berrybase/Eckstein, SparkFun, AliExpress | 10–20 € | wichtigstes Teil: IMU-Treiber am Tisch; seit 23.10. statt ICM-42688-P (E12) |
| 0.2 | BMP390-Breakout Adafruit 4816 | 1 | Kiwi Electronics (NL) 9,99 € netto, eBay paradisetronic 16,97 €; Berrybase/Eckstein prüfen | 12–17 € | auch als Rückfall an J_QWIIC, falls der Chip nicht bestückt wird |
| 0.3 | LoRa E22-400T22D (DIP, SMA) | 2 | Ebyte über AliExpress, eBay (Ebyte-Shop) oder Tindie | 2 × 8–12 € | Bodenstation und Tisch-Gegenstelle |
| 0.4 | 433-MHz-Stabantenne SMA | 2 | dieselbe Bestellung | 2 × 2–4 € | |
| 0.5 | Pigtail IPEX (u.FL) → SMA-Buchse, 10 cm | 2 | Berrybase, AliExpress | 2 × 2–3 € | Rakete; Review B17: Lage der IPEX-Buchse am Modul prüfen |
| 0.6 | **1S-LiPo 450–600 mAh mit JST-PH 2.0, ohne Schutzschaltung** (RC-Zelle, 25–30 C) | 2 | Modellbau (E-flite 500 mAh 25 C ca. 11 €; BetaFPV/HappyModel 1S 450–550 mAh mit PH2.0 ca. 5–7 €) | 2 × 5–11 € | **nicht** die Elektronik-Zellen mit PCM (Berrybase LP503035): deren Überstromschutz liegt bei 1 bis 1,5 A, der Buck-Boost zieht bei 3,0 V bis 1,6 A |
| 0.7 | 2S-LiPo 450–850 mAh 50 C, XT30 | 1–2, falls nicht vorhanden | Modellbau-Händler | 12–20 € | für die Landung mit zweitem Motor eher 850 mAh (Review C1) |
| 0.8 | 1S-USB-Lader für JST-PH (der HTRC H4AC kann kein 1S) | 1 | Modellbau (BetaFPV 1S-Lader) oder Berrybase | 10–20 € | |
| 0.9 | Zweipoliger Mini-Schiebeschalter (DPDT) | 2 | Reichelt | 2 × 1–2 € | mit Review A3 (FET-Schalter) genügt ein kleiner Schalter, kein 3-A-Typ |
| 0.10 | Schlüsselschalter oder Kippschalter mit Schutzkappe für Arming, ≥ 3 A | 1 | Reichelt | 3–8 € | führt den Pyro-Puls (Review A3: Arming bleibt im Strompfad) |
| 0.11 | JST-XH 2-, 3- und 4-polig: Platinenstecker liegend und stehend, Gehäuse, Crimpkontakte; JST-PH 2-polig ebenso; JST-GH 3/4 und JST-SH 4 **konfektioniert** (10–15 cm) | Sortiment | Reichelt (einzeln), AliExpress/Amazon (Sortiment) | 15–25 € | Review A3: J_SW als XH 4-polig, J_ARM und J_MOT als XH 2-polig |
| 0.12 | Crimpzange JST-XH/PH (Engineer PA-09 ca. 45 €, IWISS SN-01BM ca. 20–25 €) | 1 | Amazon, Reichelt | 20–45 € | |
| 0.13 | XT30PW-M liegend | 3 | Hobbyking, AliExpress | 3 × 1 € | |
| 0.14 | Buchsenleiste 1×24, 2,54 mm, 8,5 mm | 4 | Reichelt | 4 × 0,5 € | Stifte nach dem Löten kürzen (Review B18) |
| 0.15 | Stiftleiste 2×10, 2,54 mm (J_STACK) und Buchsenleiste 2×10 für die Zusatzplatine | je 2 | Reichelt | 2 € | war 2×7; rev B1 hat 20 Pole |
| 0.16 | Aktiver Summer 5 V, 12 mm, THT | 2 | Reichelt | 2 × 1 € | |
| 0.17 | Polymer-Elkos: nur noch als Rückfall, wenn JLC die 7343-Typen nicht bestückt (Review B3: 2× 470 µF/6,3 V, 2× 330 µF/16 V, 1× 470 µF/10 V, SMD) | – | Reichelt | – | THT-Elkos entfallen |
| 0.19 | W25Q128JVSIQ (SOIC-8) | 2 | Reichelt, LCSC | 2 × 1,5 € | unter den Teensy |
| 0.20 | GPS-Modul u-blox MAX-M10S oder NEO-M9N (Breakout) | 1, optional | Berrybase, Mateksys-Händler | 17–30 € | |
| 0.21 | Silikonlitze AWG 20, 22, 26 (rot/schwarz) | je 2 m | Reichelt | 8–10 € | |
| 0.22 | Elektrozünder (E-Matches) und Glühlämpchen 6 V als Dummy-Last | 10 + 5 | Raketenmodellbau Klima, Modellbau | 10–15 € | Tischtest nur mit Lämpchen |
| 0.23 | Isolierplatte 1 mm (Kapton oder PE-Schaum) zwischen Platine und Akkuträger | 1 | Baumarkt, Amazon | 3–5 € | Review B18 |
| 0.24 | Isolierter 2-mm-Draht oder Stab für die λ/4-Antenne, 17 cm | – | vorhanden? | – | in der Spitze |

Summe ohne GPS und Crimpzange etwa **110–170 €**, mit beiden **150–245 €**. Entfallen gegenüber §1: 0.18 (Taster
SW_RST, der Reset ist entfallen), die THT-Elkos unter 0.17.

### 7.1a Gegenstecker und Kabel je Buchse (Stand rev B1, 23.10.2026)

Alle Buchsen der Platine und was dazu auf die Liste gehört. JST-GH, JST-SH und Qwiic am besten konfektioniert
kaufen; XH und PH werden selbst gecrimpt (0.11, 0.12).

| Buchse | Funktion | auf der Platine | Gegenstück |
|---|---|---|---|
| J1 | 2S-Akku | XT30PW-M liegend | XT30-Buchse am Akku (bei 2S-Packs meist schon dran) |
| J2 | 1S-Akku | JST-PH 2-polig stehend | PH-2.0-Stecker am 1S-Akku (RC-Zellen haben ihn) |
| J3 | Schalterbrett (Hauptschalter) | JST-PH 4-polig | PH-4-Gehäuse + 4 Crimpkontakte, Kabel zur Luke B |
| J17 | USB-C-Lader 1S am Schalterbrett | JST-PH 3-polig | PH-3-Gehäuse + Kontakte |
| J18 | 2S-Ladebuchse | JST-PH 2-polig | PH-2-Gehäuse + Kontakte, Ladekabel mit Balancer-Anschluss |
| J4 | Schlüsselschalter (Arming) | JST-XH 2-polig stehend | XH-2-Gehäuse + Kontakte |
| J8 | Rollmotor | JST-XH 2-polig stehend | XH-2-Gehäuse + Kontakte (entfällt ohne Rollmotor) |
| J9, J10 (J19, J20 DNP) | Pyro 1 und 2 | JST-XH 2-polig liegend | XH-2-Gehäuse + Kontakte, E-Match-Leitungen |
| J5, J6 | TVC-Servos | JST-XH 3-polig liegend | **XH-3-Gehäuse + Kontakte an die Servoleitungen crimpen**: die Servostecker der W5652H (2,54 mm, JR) passen nicht in XH-Buchsen; alternativ Adapterkabel XH-3 → Servobuchse |
| J7, J16 | Fallschirm, Beine | JST-XH 3-polig stehend | wie J5/J6 |
| J11 | GPS | JST-GH 4-polig | konfektioniertes GH-4-Kabel 10–15 cm |
| J13, J14 | Kamera, LEDs | JST-GH 3-polig | konfektionierte GH-3-Kabel |
| J12 | Qwiic | JST-SH 4-polig | Qwiic-Kabel (SH-4, 1,0 mm) |
| J15 | Stapelstecker | Stiftleiste 2×10, 2,54 mm | Buchsenleiste 2×10 auf der Zusatzplatine (0.15) |
| A1 | Teensy 4.1 | 2× Buchsenleiste 1×24 (0.14) | Teensy mit eingelöteten Stiftleisten |
| U10 | LoRa-Antenne | IPEX/u.FL auf dem Modul | Pigtail IPEX → SMA (0.5), Stabantenne (0.4) |

### 7.2 Mit der Platine (JLCPCB, Tor 3)

Die SMD-Teile kommen von JLC/LCSC über BOM und CPL (§3.2, §3.3). Neu nach dem Review: 2× Polyfuse 1812 (3 A und
2 A), 2 weitere AO3401A (FET-Hauptschalter) mit 4 Widerständen, 5 Polymer-Elkos 7343, SN74LV1T34 statt 2× 74AHCT1G125,
Kelvin-Shunt-Footprint, Ferritperle 0603 mit 10 µF für die Sensor-3,3-V, zwei weitere Pyro-Kanäle als DNP, 100 nF
am INA219-Eingang. Die Stückliste in `README.md` §7 wird beim Einarbeiten nachgezogen.

### 7.3 Reserve-Chips bei LCSC (eine Bestellung, ca. 10 € Versand)

Für Nachlöten und eine dritte Platine: 2× LSM6DSV16X (C5267406, ca. 3,4 USD), 2× E22-400T22S (C2903765, ca. 4,2 USD),
2× TPS63070RNMR (C109322, ca. 1,4 USD), 2× BMP388 (C779278, 7,67 USD, 7362 auf Lager am 21.10.) oder BMP390, sobald
wieder gelistet; dazu 2× DRV8833PWPR, 2× INA219AIDR. Zusammen etwa 40 USD plus Versand und Einfuhrabgaben. Lohnt nur,
wenn die zweite bestückte Platine nicht als Reserve reicht; sonst weglassen.

### 7.4 Reihenfolge

1. Heute: 7.1 bestellen, mindestens 0.1 bis 0.6, 0.8, 0.11, 0.12, 0.14. Lieferzeit aus China 2 bis 4 Wochen, deshalb zuerst.
2. Nach dem Einarbeiten des Reviews (Tor 1 und 2): BOM/CPL und §3.3 am Bestelltag im JLC-Teileprogramm prüfen, Platine
   bestellen (Tor 3, `Fertiger_2026-10-21.md`), gegebenenfalls 7.3.
3. Während der Lieferzeit: Träger drucken, Kabel crimpen, Antenne in die Spitze, Firmware am Breakout.
