# Mainboard rev B – Bestellplan

Stand 2026-10-21. Gehört zur Spezifikation `README.md` (rev B) und zum Design Guide
`docs/DesignGuide_Mainboard_revB.md`. Dieser Plan sagt, **was in welcher Reihenfolge bestellt wird,
welche Tore vorher passiert sein müssen und was es kostet**. Schaltplan und Layout gibt es noch nicht,
die Platine selbst kann also erst nach den Toren 1 und 2 bestellt werden. Einiges lässt sich aber jetzt
schon kaufen, damit Firmware und Mechanik nicht auf die Platine warten.

![Weg zur Platine](img/order_flow.svg)

## 1. Was jetzt schon bestellt werden kann (Tor 0)

Diese Teile hängen nicht vom Layout ab. Sie machen den Breakout-Aufbau zum Testträger für die
rev-B-Firmware und sparen später Wartezeit.

| Nr. | Teil | Stück | Wofür | Quelle (Vorschlag) | ca. |
|---|---|---|---|---|---|
| 0.1 | ICM-42688-P-Breakout (SPI herausgeführt) | 1 | IMU-Treiber ohne DMP und Gyro-Quaternion am Tisch entwickeln, bevor die Platine da ist | Berrybase, Eckstein, AliExpress | 8–15 € |
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

- KiCad 9 installiert, Projekt `hardware/mainboard/kicad/` angelegt, Bibliotheken: KiCad-Standard plus
  Footprints/Symbole aus dem JLCPCB-Plugin (`kicad-jlcpcb-tools`) oder von Ultra Librarian für
  ICM-42688-P, BMP390, TPS63070 und E22-400T22S.
- Jede Schiene mit Testpunkt (TP1–6) und Sicherung (F1 3 A VSERVO; 5V_SYS und 3V3_RF bekommen eine
  Polyfuse 1 A bzw. 0,5 A, wenn Platz ist).
- Jeder Stecker mit Pin-1-Markierung und Netznamen im Schaltplan, Lötbrücken JP1/JP2 eingezeichnet.
- ERC ohne Fehler; Netzliste gegen die Pin-Tabelle in `README.md` §4 geprüft (Skript oder von Hand).
- **Review durch den Kollegen** anhand des Design Guides, Punkte eingearbeitet oder begründet abgelehnt.

### Tor 2: Layout fertig

- `mainboard_outline.dxf` als Edge.Cuts importiert, Bohrungen und Zonen wie `mainboard_placement.svg`.
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
| ICM-42688-P | C1850418 | Extended | ca. 5500 Stück, ab 2,1 USD bei 1000 (Einzelpreis höher) | keine Alternative auf der Achse; dann warten oder ICM-42605 (gleiches Gehäuse, prüfen) |
| BMP390 | C5124834 | Extended | **0 Stück** in der letzten Momentaufnahme, 6,7 USD | **BMP388 (C779278, gleiches LGA-10, gleiche Bibliothek)**, war bei LCSC gelistet, aber bei JLC nicht bestellbar; sonst Breakout per Qwiic anschließen |
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
| SMBJ12A | prüfen | | | SMAJ12A |
| 20 mΩ 2512 1 % 1 W | prüfen | | | 2× 40 mΩ 2512 parallel |
| Polyfuse 3 A 1812 | prüfen | | | |
| W25Q128JVSIQ | C97521 (prüfen) | Basic | | kommt unter den Teensy, nicht auf die Platine |
| Passive 0402/0603, 4,7 k, 100 k, 33 k, 100 Ω, 100 n, 10 n, 10 µ | Basic | | | |

Zählung: etwa **8 bis 10 Extended-Typen**, also 12 bis 30 USD Rüstgebühr. Wer sparen will, ersetzt den
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
| **Summe Platinenlauf** | **ca. 120–180 EUR** | für 5 Platinen, 2 bestückt |

Dazu die Teile aus §1 (90–140 €) und der Teensy (vorhanden). Die ganze Elektronik rev B liegt damit
bei **ca. 210–320 EUR**, was die Planungsrunde (170–280 €) um den BMP390-Preis und den zweiten Akku
übertrifft.

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
| BMP390 bei JLC nicht lieferbar | kein Barometer auf der Platine | Footprint LGA-10 bleibt; BMP388 ist pinkompatibel; sonst Breakout an J_QWIIC |
| TPS63070 nicht lieferbar | kein 5V_SYS aus 1S | Footprint zusätzlich für TPS63020 vorsehen? Nein, zu viel Fläche; Bestand vor dem Layout prüfen und notfalls 10 Stück bei LCSC vorbestellen |
| E22-400T22S falsch gedreht oder Pads unter dem Modul nicht benetzt | Funk tot | CPL-Vorschau prüfen; das Modul hat nur Randpads, Nachlöten ist möglich |
| WS2812B erzwingt Standard-PCBA | +17 USD Setup | LEDs als DNP, selbst löten (2020-Gehäuse, Heißluft) oder 5050-Gehäuse nehmen |
| Teensy-Sockelreihen 0,1 mm versetzt | Teensy klemmt | Footprint aus der offiziellen Teensy-KiCad-Bibliothek, Papierausdruck mit echtem Teensy |
| Drehung der VQFN-15 (TPS63070) in der CPL | Wandler kaputt beim ersten Einschalten | Pin-1-Punkt in der JLC-Vorschau, erster Start am Netzteil mit 100 mA |
| Servo-Achsenlage zum Schlitten noch offen (`README.md` §11) | Achsentausch in der Firmware | kein Platinenrisiko, Stecker sind gleich |

## 6. Wer macht was, Reihenfolge der nächsten Wochen

1. Jetzt: §1 bestellen (0.1 bis 0.6, 0.9 bis 0.16 mindestens). Parallel Firmware auf dem Breakout.
2. KiCad installieren, Schaltplan zeichnen (ein bis zwei Wochen Abende), Design Guide an den Kollegen,
   Review einarbeiten → Tor 1.
3. Layout (ein bis zwei Wochen), DRC, Papierprobe → Tor 2.
4. Am Bestelltag §3.3 durchgehen, dann hochladen → Tor 3. Während der Lieferzeit: Träger drucken, Kabel
   konfektionieren, Antenne in die Spitze.
5. Tor 4 und Testplan. Erst danach die Firmware auf die Platine.
