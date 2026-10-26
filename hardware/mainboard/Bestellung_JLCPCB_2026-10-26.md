# Bestellung JLCPCB, Mainboard rev B1 (26.10.2026)

Stand: **bestellt am 26.10.2026 um 16:08 als Auftrag W2026102623077325** (251,40 USD mit DHL Express DDP), Status „File Review“; Option Selbstbestückung siehe `Beschaffung_2026-10-26.md` §6b. Fertigungsdaten aus `kicad/fab/` vom 26.10.
(Commit `b8260a4`, Thermovias 0,3 mm). Upload-Kopien von BOM und CPL: `kicad/fab/mainboard_bom_jlc.csv`,
`kicad/fab/mainboard_cpl_jlc.csv` (ohne LED1, LED2, U10; LCSC-Nummern aus dem Angebot vom 23.10. eingetragen).
Alle Preise USD ohne Versand und Einfuhrumsatzsteuer.

## 1. Platine (Auftrag Y2-13908548A)

| Parameter | Wert |
|---|---|
| Stückzahl | 5 |
| Lagen, Maße | 4, 120 × 54 mm erkannt; mit Randstreifen für Standard-PCBA 70 × 120 mm |
| Material, Dicke | FR-4 TG135, 1,6 mm |
| Lötstopp, Druck | grün, weiß |
| Oberfläche | HASL mit Blei (0 USD; ENIG hätte 17,30 USD gekostet, blau 5 USD) |
| Kupfer | 1 oz außen, 0,5 oz innen |
| Vias | tented, Option 0,3 mm / 0,4–0,45 mm (Standard) |
| Mark | kein Auftragsnummern-Mark (JLCPCB-Standard seit 2026) |
| Test | Flying Probe |
| Preis | **30,20 USD** (Engineering 25,00, Board 5,20) |

## 2. Bestückung (Auftrag SMT026102663131-13908548A)

| Parameter | Wert |
|---|---|
| Art | **Standard PCBA** (Economic bestückt keine LGA-Gehäuse: LSM6DSV16X, LIS3MDL, BMP388) |
| Seite, Stückzahl | nur Oberseite, 2 Platinen |
| Bauteilauswahl | durch Kunden (Self-Service) |
| Platzierungsbestätigung | ja (0,45 USD): JLCPCB schickt vor der Fertigung ein Bild, Antwort innerhalb 72 h |
| Röntgen | ja (6,60 USD), für die LGA- und QFN-Lötstellen |
| Randstreifen abtrennen | nicht gewählt (Standard: Platinen kommen mit Streifen, selbst abbrechen) |
| Preis | **145,73 USD**: Setup 25,75, Schablone 8,27, Bauteile (30 Positionen) 55,76, Feeder-Gebühr 46,50, Bestückung 1,89, Bestätigung 0,45, Röntgen 6,60, Verpackung 0,50 |

**Summe 175,93 USD** plus Versand und Einfuhrumsatzsteuer, siehe §2.3.

### 2.3 Versand und Zoll (Checkout 26.10. abends, Lieferadresse Einhausen)

| Option | Laufzeit | Versand | Abgaben | Gesamt |
|---|---|---|---|---|
| DHL Express (CPT) | 2–4 Werktage | 26,84 USD | 19 % EUSt auf Ware + Versand (ca. 38 USD) plus DHL-Vorlageprovision (ca. 12–15 €) **bei Zustellung** | ca. 255 USD |
| FedEx Express (CPT) | 5–7 Werktage | 28,49 USD | wie oben, beim Boten | ca. 257 USD |
| UPS Express Saver (CPT) | 3–5 Werktage | 31,64 USD | wie oben | ca. 260 USD |
| Global Standard Direct Line | 9–13 Werktage | ca. 28 USD | wie oben | ca. 257 USD |
| **DHL Express (DDP)** | 2–4 Werktage | 28,39 USD | 38,83 USD Abgaben + 8,27 USD Gebühr, **im Voraus bei JLCPCB** | **251,42 USD** |

Entscheidung: **DHL Express (DDP)**, Abgaben jetzt mitbezahlen. Das kostet nichts mehr als die Zahlung an der Haustür,
erspart die DHL-Vorlageprovision und die Zollverzögerung; seit 1.7.2026 gibt es in der EU keine 150-€-Zollfreigrenze
mehr, so dass bei CPT zusätzlich zur EUSt Zoll anfallen kann. Zweitwahl bei knapper Kasse: DHL Express CPT, dann
EUSt und Gebühr an den DHL-Boten (Vorkasse-Link per SMS/E-Mail).

### 2.1 Von JLCPCB bestückt (30 Positionen)

Alle Basic-Passiven (100 n, 10 n, 1 µ, 2,2 µ, 4,7 µ, 10 µ, 22 µ, Widerstände 10 Ω bis 330 k außer 680 k/130 k/115 k),
SS14 (D1), 1N4148W (D4), AO3401A (Q1, Q2, Q6, Q7), AO3400A (Q3, Q4, Q5), Shunt RTT25R020FTE (R_SH1, C159174),
C16/C17 Kemet T520D477M006ATE030 (C232382), TPS63070 (U2), LSM6DSV16X (U4), **BMP388 statt BMP390** (U5, C779278;
BMP390 bei JLCPCB ohne Bestand, pinkompatibel, gleiche Bibliothek, CHIP_ID 0x50 statt 0x60), DRV8833 (U7),
LIS3MDL (U16), SHT40 (U18).

### 2.2 Selbst zu löten (Platine kommt ohne diese Teile)

Abgewählt, weil Extended-Teile je Position ca. 2,90 USD Feeder-Gebühr kosten und sie von Hand leicht gehen.
Ersparnis gegenüber Vollbestückung: 69,76 USD (245,69 → 175,93).

| Ref | Teil | LCSC (bei JLCPCB gefunden) | Gehäuse | Aufwand |
|---|---|---|---|---|
| C4, C5 | 330 µF/16 V Polymer (JLC: Kemet T521X337M016ATE050, 5,90 USD/Stück) | C696820 | 7343 | leicht; Alternative: eigener 1000 µF/25 V Elko mit gebogenen Beinen oder Panasonic SVP 330/16 (Reichelt 0,99 €) |
| C20 | 100 µF/6,3 V | C426103 | 1210 | leicht |
| D2, D3 | SMAJ12CA | C5249592 | SMA | leicht |
| F1 | Polyfuse 3 A/6 A BSMD1812-300-16V | C883162 | 1812 | leicht |
| F2 | Polyfuse 2 A BSMD1812-200-16V | C883156 | 1812 | leicht |
| FB1 | Ferrit BLM18KG601SN1D | C85833 | 0603 | fummelig |
| J11 | JST GH 4 BM04B-GHS-TBT | C161692 | SMD 1,25 mm | mittel, Flussmittel |
| J12 | JST SH 4 BM04B-SRSS-TB | C160390 | SMD 1,0 mm | mittel |
| J13, J14 | JST GH 3 BM03B-GHS-TBT | C161691 | SMD 1,25 mm | mittel |
| L2 | 1,5 µH FNR5040S1R5MT | C167955 | 5040 | leicht |
| R14, R15, R17 | 680 k, 130 k, 115 k | C25822, C22795, C22783 | 0603 | fummelig |
| U3, U14 | AP2112K-3.3 | C51118 | SOT-23-5 | leicht |
| U8 | SN74LV1T34DBVR | C100024 | SOT-23-5 | leicht |
| U11 | MCP73831T-2ACI/OT | C424093 | SOT-23-5 | leicht |
| U12 | 74HC138PW | C53552920 | TSSOP-16 | mittel, Schleppen |
| U13 | 74HC4051PW | C2943042 | TSSOP-16 | mittel |
| U6 | INA239AIDGSR (bei JLCPCB ohne Bestand) | C2876522 | VSSOP-10 | mittel; DigiKey/Mouser, Reichelt führt ihn nicht |
| U10 | E22-400T22S | C2903765 | SMD-Modul | leicht, 26 Randpads |
| LED1, LED2 | WS2812B-2020 (C965555 ausverkauft; Zweithersteller C52917434) | | 2020 | mittel, kleine Pads |
| THT | A1 Teensy-Buchsenleisten, BZ1, J1–J10, J15, J16, J17, J18 | | | leicht |

Reichelt (abgefragt 26.10.): kein BMP388/BMP390, kein INA239, kein E22, keine WS2812B-2020, keine 7343-Polymerelkos.
Passive, Polyfuses, TVS, 74HC und MCP73831 dort vermutlich erhältlich, nicht einzeln geprüft.

## 3. Nach der Bestellung

1. Platzierungsbild von JLCPCB prüfen (Pin 1 von U2, U4, U5, U7; Polarität D1, D4), innerhalb 72 h bestätigen.
2. DFM-Analyse im JLCPCB-Konto (4–8 h nach Bestellung) ansehen.
3. Parallel bestellen: INA239 (DigiKey/Mouser), E22-400T22S (Ebyte/AliExpress), WS2812B-2020, Polymerelkos oder
   eigene Elkos, die Teile aus §2.2 bei Reichelt/LCSC, dazu `EINKAUFSLISTE_revB1.md` (THT, Stecker, Akkus).
4. Firmware: BMP388 statt BMP390 (CHIP_ID 0x50), Treiber `BMP3XX` unterstützt beide.
