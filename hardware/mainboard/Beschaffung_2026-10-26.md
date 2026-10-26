# Beschaffung der Selbstlöt-Teile, Mainboard rev B1 (26.10.2026)

Stand: 26.10.2026, Händlerseiten an diesem Tag abgefragt (Reichelt-Suche, DigiKey-Produktseiten per Abruf; Mouser-Seiten
liefen beim Abruf jedes Mal in einen Timeout, dort nur Suchmaschinen-Auszüge). Quelle der Positionen:
`Bestellung_JLCPCB_2026-10-26.md` §2.2 (SMD, Module, LEDs) und `EINKAUFSLISTE_revB1.md` §1 und §2 (THT, Gegenstecker,
Kabel). Der vorhandene Reichelt-Warenkorb war von hier aus nicht einsehbar; die Liste unten ist zum Abgleich gedacht.

Mengen: **2 Platinen + 1 Reserve** = 2 × (Stück je Platine) + 1, bei Gegensteckern die Mengen aus der Einkaufsliste.
Preise: Reichelt **brutto** (inkl. 19 % MwSt.), DigiKey **netto** (MwSt. kommt dazu), Stückpreis bei der genannten Menge.

## 1. Reichelt (eine Bestellung)

### 1.1 SMD-Teile aus §2.2

| Ref | Teil (Soll) | Reichelt-Art.-Nr. | Hersteller / Typ | Stückpreis | Menge | Verfügbarkeit |
|---|---|---|---|---|---|---|
| C20 | 100 µF/6,3 V 1210 | GRM32EC70J107ME1 | Murata, X7S | 0,94 € | 3 | ab Lager, 1–2 Werktage |
| D2, D3 | SMAJ12CA | P4SMAJ12CA | Diotec, 400 W, 12 V bidir., SMA (gleiche Daten) | 0,10 € | 5 | ab Lager |
| F2 | Polyfuse 2 A 1812 (BSMD1812-200-16V) | PTC FSMD200R | Fuzetec, 2 A, 8 V, 1812 | 0,76 € | 3 | ab Lager |
| FB1 | BLM18KG601SN1D | BLM18KG601SN1D | Murata, Original | 0,10 € | 3 | ab Lager |
| R14 | 680 k 0603 1 % | SMD-0603 680K | Yageo RC0603, 1 % | 0,02 € (ab 10: 0,01 €) | 10 | ab Lager |
| R15 | 130 k 0603 1 % | ERJPA3F1303 | Panasonic, 1 %, Anti-Surge | 0,27 € | 3 | ab Lager |
| R17 | 115 k 0603 1 % | SPR-0603 115K | Panasonic, **0,1 %** | 0,22 € | 3 | ab Lager |
| U11 | MCP73831T-2ACI/OT | MCP 73831T-2ACI | Microchip, SOT-23-5, Original | 0,65 € | 3 | ab Lager |

Ersatztypen: P4SMAJ12CA ist die Diotec-Bezeichnung für die 400-W-SMA-TVS mit 12 V Sperrspannung, bidirektional, also
dieselbe Klasse wie SMAJ12CA. FSMD200R hat 2 A Haltestrom wie das Original; 8 V reichen für den 1S-Zweig (max. 4,2 V).
Für 130 k gibt es bei Reichelt sonst nur `SPR-0603 130K` (0,1 %, 0,36 €) oder `RND 155HP03 AT` (Restposten); für 115 k
nur die 0,1-%-Ausführung, die für den Spannungsteiler eher besser passt. Kein Treffer bei Reichelt: AP2112K,
SN74LV1T34, 74HC138/4051 im TSSOP (nur SO-16 und DIP), BSMD1812, Polyfuse 3 A mit ≥ 9 V in 1812, 1,5 µH in 5040,
JST GH/SH-SMD-Buchsen, INA239, E22, WS2812B-2020, Polymer 7343.

### 1.2 THT-Teile (§1 der Einkaufsliste)

| Ref | Teil (Soll) | Reichelt-Art.-Nr. | Stückpreis | Menge | Verfügbarkeit |
|---|---|---|---|---|---|
| J2, J18 | JST B2B-PH-K-S | JST PH2P ST | 0,14 € | 5 | ab Lager |
| J3 | JST B4B-PH-K-S | JST PH4P ST | 0,17 € | 3 | **begrenzte Stückzahl** |
| J17 | JST B3B-PH-K-S | JST PH3P ST | 0,20 € | 3 | ab Lager |
| J4, J8 | JST B2B-XH-A | JST XH2P ST | 0,17 € | 5 | ab Lager |
| J9, J10 | JST S2B-XH-A (liegend) | JST XH2P ST90 | 0,23 € | 5 | ab Lager |
| J5, J6 | JST S3B-XH-A (liegend) | JST XH3P ST90 | 0,15 € | 5 | ab Lager |
| J7, J16 | JST B3B-XH-A | JST XH3P ST | 0,21 € | 5 | **erst ab 28.11.2026** → bei DigiKey (§2) |
| J15 | Stiftleiste 2×10, 2,54 mm, gerade | SL 2X10G 2,54 (oder MPE 087-2-020, 0,39 €) | 0,13 € | 3 | ab Lager |
| BZ1 | aktiver Summer 5 V, Ø 12 mm, RM 7,6 mm | SUMMER TDB 05 (Ekulit, 4–6,5 V DC, 85 dB, 2,3 kHz) | 0,99 € | 3 | ab Lager |
| A1 | Buchsenleiste 1×24, 8,5 mm | kein 1×24 in 8,5 mm; Ersatz je Seite MPE 094-1-016 + MPE 094-1-008 | 0,43 € + 0,31 € | je 6 | ab Lager; Empfehlung trotzdem DigiKey (§2) |

Reichelt nennt bei den JST-Artikeln keine Herstellernummern (Hersteller JST, Serie PH 2,0 mm bzw. XH 2,5 mm, „ST“ =
gerade, „ST90“ = 90°). Die Zuordnung zu B·B-/S·B-Typen ist aus Bauform und Polzahl geschlossen; Rastermaß und
Pinabstand passen zum Footprint. Beim Summer steht auf der Reichelt-Seite nicht ausdrücklich „mit Elektronik“; der
DC-Spannungsbereich spricht für einen aktiven Typ, vor dem Bestellen im Datenblatt prüfen (oder den vorhandenen nehmen).
Die einzige echte 1×24-Leiste bei Reichelt ist `EA B-24` (Display Visions, 7,1 mm hoch, 6,25 €), zu teuer und zu niedrig.

### 1.3 Gegenstecker und Kabel (§2 der Einkaufsliste)

| Für | Teil | Reichelt-Art.-Nr. | Stückpreis | Menge | Verfügbarkeit |
|---|---|---|---|---|---|
| J2, J18 | PHR-2 | JST PH2P BU | 0,06 € | 10 | begrenzte Stückzahl |
| J17 | PHR-3 | JST PH3P BU | 0,05 € | 3 | ab Lager |
| J3 | PHR-4 | JST PH4P BU | 0,05 € | 3 | ab Lager |
| PH alle | SPH-002T-P0.5S (24–30 AWG) | JST PH CKS (30–24 AWG) | 0,05 € | 50 | ab Lager |
| J4, J8, J9, J10 | XHP-2 | JST XH2P BU | 0,05 € | 10 | ab Lager |
| J5, J6, J7, J16 | XHP-3 | JST XH3P BU | 0,09 € | 8 | ab Lager |
| XH alle | SXH-001T-P0.6 (22–28 AWG) | JST XH1 CKS (28–22 AWG) | 0,04 € | 70 | ab Lager |
| J15 | Buchsenleiste 2×10, 8,5 mm | MPE 094-2-020 (oder BL 2X10G8 2,54, 0,31 €) | 0,67 € | 2 | ab Lager |
| U10 | Pigtail U.FL → SMA-Einbaubuchse, 0,2 m | DELOCK 88747 | 7,95 € | 2 | ab Lager (AliExpress deutlich billiger) |
| U10 | 433-MHz-Stabantenne, SMA-Stecker, 108 mm | DELOCK 88914 | 4,95 € | 2 | ab Lager |

Bei Reichelt nicht vorhanden: konfektionierte JST-GH-Kabel (nur `JST GHR-06V-S` und GH-Kontakte; GH crimpen braucht
Spezialwerkzeug) und Qwiic/Stemma-QT-Kabel. XH-Alternative `JST XH2 CKS` ist für 26–30 AWG, für Servolitze 22–26 AWG
also `XH1 CKS` nehmen.

## 2. DigiKey (eine Bestellung, deckt alles ab, was Reichelt nicht hat)

| Ref | Teil | DigiKey-Nr. | Stückpreis (netto) | Menge | Bestand / Lieferung |
|---|---|---|---|---|---|
| U6 | INA239AIDGSR | 296-INA239AIDGSRCT-ND | 3,77 € (ab 10: 2,857 €) | 3 (besser 10, s. §4) | **0 Stück**; 2 500 erwartet am 02.11.2026; Herstellerlieferzeit 20 Wochen |
| C4, C5 | 330 µF/16 V Polymer 7343 | 478-13307-1-ND (Kyocera AVX TCJE337M016R0050E) | 4,13 € (ab 10: 2,914 €) | 5 | 38 020 |
| F1 | Polyfuse 3 A/6 A, 1812 | 18-1812L300/24SLERCT-ND (Littelfuse 1812L300/24SLER) | 2,33 € | 3 | 6 280 |
| J11 | BM04B-GHS-TBT | 455-BM04B-GHS-TBTCT-ND | 0,34 € | 3 | **0 Stück**; 2 500 erwartet am 02.11.2026 |
| J12 | BM04B-SRSS-TB | 455-BM04B-SRSS-TBCT-ND | 0,47 € | 3 | 111 081 |
| J13, J14 | BM03B-GHS-TBT | 455-BM03B-GHS-TBTCT-ND | 0,32 € | 5 | 103 025 |
| L2 | 1,5 µH, 5040 | 587-NRS5040T1R5NMGJCT-ND (Taiyo Yuden NRS5040T1R5NMGJ) | 0,21 € | 3 | 23 805 |
| U3, U14 | AP2112K-3.3TRG1 | AP2112K-3.3TRG1DICT-ND | 0,25 € | 5 | 417 326 |
| U8 | SN74LV1T34DBVR | 296-37176-1-ND | 0,36 € | 3 | 127 548 |
| U12 | 74HC138PW,118 (Nexperia) | 1727-4065-1-ND | 0,29 € | 3 | 7 219 |
| U13 | 74HC4051PW → **CD74HC4051PWR** (TI) | 296-13031-1-ND | 0,52 € | 3 | 27 309 (Nexperia 74HC4051PW,118: 0 Stück, Nachschub 30.11.) |
| LED1, LED2 | WS2812B-2020 | 1528-4684-ND (Adafruit 4684, NeoPixel Nano 2020, **10er-Streifen**) | 3,51 € je 10 | 1 Pack | 1 527 |
| A1 | Buchsenleiste 1×24, 2,54 mm, 8,5 mm | S7022-ND (Sullins PPTC241LFBN-RC) | 1,19 € | 6 | 25 466 |
| J7, J16 | JST B3B-XH-A | 455-2248-ND | 0,12 € | 5 | 64 595 |
| J12-Kabel | Qwiic/Stemma-QT SH-4, 100 mm | 1528-4210-ND (Adafruit 4210) | 0,84 € | 2 (eins für offenes Ende abschneiden) | 17 592 |
| J12-Kabel | Qwiic/Stemma-QT SH-4, 50 mm | Adafruit 4399 (DigiKey-Nr. nicht angezeigt) | 0,84 € | 1 | Bestand nicht angezeigt |

Warum die Ersatztypen passen:

- **C4, C5:** TCJE337M016R0050E ist 330 µF/16 V Polymer-Tantal im E-Gehäuse 7343-43 (7,3 × 4,3 × 4,3 mm), ESR
  50 mΩ wie der Kemet T521X337M016ATE050 aus dem JLC-Angebot (bei DigiKey 7,12 €, 20 659 Stück); 3 € je Stück günstiger.
  Billig-Notlösung: Reichelt `SVP 330/16` (Panasonic, radial-SMD Ø 10 × 12,6 mm, 0,99 €), passt nicht auf den
  7343-Footprint und muss mit gebogenen Anschlüssen aufgesetzt werden.
- **F1:** 1812L300/24SLER hat genau 3 A Halte- und 6 A Auslösestrom wie BSMD1812-300-16V, dazu 24 V statt 16 V. Die
  Reichelt-Typen in 1812 sind entweder 3 A/6 V (`PTC FSMD300R`, zu wenig Spannung für 2S mit 8,4 V) oder
  2,6 A/16 V (`PTC FSMD26016R`, 0,99 €, Notlösung mit 13 % weniger Haltestrom).
- **L2:** NRS5040T1R5NMGJ: 1,5 µH ± 20 %, 4,5 A Nennstrom, 6,4 A Sättigung, 22 mΩ, 4,9 × 4,9 × 4,1 mm. Original
  FNR5040S1R5MT: 4,85 A, 6,8 A Sättigung, 15 mΩ, 5 × 5 mm. Für den TPS63070 ausreichend; Pads vor dem Löten mit dem
  Footprint vergleichen (0,1 mm kleiner). Bourns SRN5040TA-1R5M (4,5 A, 15 mΩ, 0,41 €) wäre die zweite Wahl.
- **U13:** CD74HC4051PWR ist derselbe 8:1-Analogmux im TSSOP-16 mit identischer Pinbelegung (TI-Fassung der 4051).
- **LED1, LED2:** Adafruit beschreibt Artikel 4684 als WS2812B im 2020-Gehäuse (Datenblatt WS2812B-2020); Pinbelegung
  vor dem Löten am Adafruit-Datenblatt gegen den Footprint prüfen (Pin 1 DOUT, 2 GND, 3 DIN, 4 VDD bei Worldsemi).
- **A1:** einteilige 1×24-Leiste in 8,5 mm statt zwei gestoßener Reichelt-Stücke; 2,70 € Mehrpreis für 6 Stück.

Die DigiKey-Teile mit Bestand 0 (INA239, BM04B-GHS-TBT) kann man trotzdem bestellen. Sie kommen als Rückstand und
werden laut Seite ab 02.11.2026 nachgeliefert. DigiKey liefert dann eine Teillieferung; je nach Einstellung beim
Bestellen gibt es dafür keinen zweiten Versandkostenbetrag. Beim Bezahlen prüfen.

## 3. Mouser

Keine verlässlichen Daten: Jeder Abruf von mouser.de/mouser.com lief in einen Timeout. Aus Suchmaschinen-Auszügen
(ohne Datum, wahrscheinlich veraltet):

| Ref | Teil | Mouser-Nr. | Preis | Bestand lt. Auszug |
|---|---|---|---|---|
| U6 | INA239AIDGSR | 595-INA239AIDGSR | 3,75 USD (1 Stück) | 0, Bestellungen mit Termin 25.06./09.07.2026 (veraltet) |
| U6 | INA239AIDGST (250er-Rolle, laut TI und DigiKey **obsolet**) | 595-INA239AIDGST | Preis nicht lesbar | 5 307 laut Auszug, nicht überprüfbar |

Mouser bringt gegenüber DigiKey keinen Vorteil, solange der Bestand nicht im Browser bestätigt ist. Einzige
Ausnahme: Wenn Mouser die INA239AIDGST noch ab Lager hat, wäre das die schnellste Quelle für U6 (gleicher Chip, nur
kleinere Rolle). Das bitte von Hand auf mouser.de nachsehen.

## 4. Sonstige Quellen

| Ref | Teil | Quelle, Artikel | Preis | Menge | Verfügbarkeit |
|---|---|---|---|---|---|
| U10 | E22-400T22S | LCSC C2903765 | ca. 4,21 USD (1), 3,27 USD (100) lt. Suchauszug | 3 | 588 Stück lt. Suchauszug; LCSC-Seite selbst ohne Preis/Bestand abrufbar |
| U10 | E22-400T22S-V2 | Ebyte-Shop ebyteiot.com | 6,96 USD | 3 | „Out of stock“, Knopf „Pre-order“ |
| U10 | E22-400T22S | RobotShop | 6,56 USD | 3 | 92 Stück lt. Suchauszug |
| LED1, LED2 | WS2812B-2020-V6 (Worldsemi) | LCSC C52917434 | nicht lesbar | 5 | nicht lesbar (C965555: Seite nennt ca. 35 000 Stück, JLC-Angebot 23.10. sagt ausverkauft) |
| J1 | AMASS XT30PW-M | LCSC C431092 | ca. 0,25–0,36 USD lt. Suchauszug | 3 | widersprüchlich (267 bzw. 41 299) |
| J1 | AMASS XT30PW-M | electrokit.com (Schweden), Art. 41033203 | 10,50 SEK (ca. 0,95 €) | 3 | 82 Stück, 1–3 Werktage |
| J11, J13, J14 | JST-GH-Kabel 4- und 3-polig, offenes Ende | AliExpress, Berrybase, Eckstein (nicht geprüft) | – | 2 + 3 | DigiKey hat vorgecrimpte GH-Litzen (AGHGH28K152), aber 0 Stück bis 03/2027 |
| U10 | Pigtail U.FL → SMA, Antenne 433 MHz | AliExpress (Billig-Alternative zu §1.3) | – | je 2 | nicht geprüft |

AliExpress und Amazon direkt waren per Abruf nicht durchsuchbar; die Suchmaschine fand dort keinen E22-400T22S.
XT30PW-M führen weder Reichelt noch DigiKey; Berrybase hat nur die Kabelausführung `A-XT30`.

Nicht recherchiert (nur genannt): Akkus 1S/2S, 1S-Lader, Crimpzange, Litze, Flussmittel, Schalter, GPS, Kamera,
Zünder, Breakouts (Einkaufsliste §3 und §5).

## 5. Was nirgends sofort lieferbar ist

| Ref | Teil | Lage | Vorschlag |
|---|---|---|---|
| U6 | INA239AIDGSR | DigiKey 0 (2 500 am 02.11.2026), TI-Store „Out of stock“, Mouser unklar, LCSC ohne Angabe. INA239AQDGSRQ1 (Auto-Version, pinkompatibel) 0, erst 18.02.2027; INA229 0, erst 07.01.2027 | **Jetzt bei DigiKey als Rückstand bestellen**; Platinen kommen ohnehin erst in etwa 2 Wochen. Parallel auf mouser.de nach INA239AIDGST/-DGSR sehen. Fällt der Termin, läuft die Platine ohne U6 (nur Strommessung VSERVO fehlt) |
| J11 | BM04B-GHS-TBT | DigiKey 0 (2 500 am 02.11.2026), LCSC 0 | Als Rückstand mit der DigiKey-Bestellung; GPS ist optional, notfalls Litzen direkt anlöten |
| J7, J16 | B3B-XH-A | Reichelt erst ab 28.11.2026 | bei DigiKey (455-2248-ND) |
| U13 | 74HC4051PW (Nexperia) | DigiKey 0 bis 30.11. | TI CD74HC4051PWR (pinkompatibel), ab Lager |
| U10 | E22-400T22S | Ebyte-Shop nur Vorbestellung | LCSC (mit XT30PW-M zusammen) oder RobotShop; bei LCSC vor dem Bezahlen Bestand prüfen |

## 6. Empfehlung: drei Bestellungen

1. **Reichelt** (Warenkorb ergänzen): §1.1, §1.2 ohne J7/J16 und A1, §1.3. Abgleich mit dem bestellfertigen Korb in
   `EINKAUFSLISTE_revB1.md` §7.1 (26.10., andere Session): dieselben JST-Artikelnummern; dort fehlen nur die acht
   SMD-Positionen aus §1.1 (C20, D2/D3, F2, FB1, R14, R15, R17, U11), die kommen dazu. Dort steht für A1 die trennbare
   `FIS BL1 36 G` (auf 24 kürzen) statt der DigiKey-Leiste, für J7/J16 ersatzweise die liegende `JST XH3P ST90`;
   die Footprints von J7/J16 sind stehend ausgelegt, liegend nur nehmen, wenn in Kabelrichtung Platz ist.
   Summe brutto: SMD ca. 9,40 €, THT ca. 7,90 €, Gegenstecker ca. 8,80 € → **ca. 26 €**; mit Delock-Pigtails und
   -Antennen ca. **52 €**. Versand laut Drittseite (Juni 2026) **ab 5,95 €**, ein Forum meldet im August 2026 knapp
   1 € mehr; kostenlosen Standardversand gibt es nicht. Die offizielle Versandkostenseite war per Abruf nicht erreichbar.
2. **DigiKey** (eine Bestellung): Tabelle §2 kommt auf ca. **62 € netto** (ca. 74 € brutto). Die Schwelle ist
   **nicht 50 €**: DigiKey zeigt am 26.10.2026 „Kostenlose Lieferung nach Deutschland für Bestellungen im Wert von
   75 EUR oder mehr“, darunter **25 € Versand**. Vorschlag zum Auffüllen: U6 auf **10 Stück** (Staffel 2,857 € statt
   3,77 €, +17,26 €; deckt die Reserveteile aus Einkaufsliste §4 mit ab) → ca. **79 € netto, versandkostenfrei**.
   Alternativ C4/C5 auf 10 Stück (+8,49 €). Lieferung per UPS mit Zoll inklusive (DDP), 1–3 Tage ab Versand.
3. **LCSC** (oder RobotShop/Ebyte): E22-400T22S ×3, XT30PW-M ×3, optional WS2812B-2020-V6 als Reserve. Versand aus
   China ca. 10 € plus Einfuhrumsatzsteuer, 1–2 Wochen. Konfektionierte GH-Kabel bei AliExpress oder Berrybase dazu.

**Mouser entfällt.** Die Schwelle dort ist ebenfalls unklar: ältere mouser.de-Seiten nennen 50 €, ein undatierter
mikrocontroller.net-Beitrag 75 € bei 25 € Versand darunter. Eine Mouser-Bestellung lohnt nur, falls sie die
INA239AIDGST tatsächlich ab Lager hat.

Gesamt ohne Akkus, Werkzeug und Module: Reichelt ca. 32–58 € inkl. Versand, DigiKey ca. 94 € brutto (79 € netto),
LCSC ca. 25–35 € inkl. Versand und Steuer (Teile ca. 14 USD, Rest Versand und Einfuhrumsatzsteuer).

## 6a. Stand der Warenkörbe (26.10.2026, abends)

Entscheidung 26.10. abends: **eine Bestellung bei DigiKey statt Reichelt + DigiKey.** Die 26 Reichelt-Positionen
wurden mit Herstellernummern in den DigiKey-Korb übernommen, INA239 von 10 auf 3 Stück gesetzt.

| Händler | Inhalt | Summe | Status |
|---|---|---|---|
| JLCPCB | 5 Platinen + Standard-PCBA 2 Stück (`Bestellung_JLCPCB_2026-10-26.md`) | 175,93 USD + 26,84 USD Versand − 10 USD Gutschein = 192,77 USD | Checkout geöffnet, Lieferadresse und Zahlung offen; Versand voraussichtlich ab 1.11. |
| DigiKey | **40 Positionen** (Tabelle unten): §2 mit INA239 ×3 plus die bisherigen Reichelt-Positionen | **92,60 € netto** (ca. 110 € brutto), Versand kostenlos (≥ 75 €) | Gast-Warenkorb im eingebauten Browser, nicht bestellt; beim Anmelden übernehmen |
| Reichelt | 26 Positionen (alter Stand, 35,17 € + 5,95 €) | – | **hinfällig**, Korb kann geleert werden |
| LCSC / AliExpress | E22-400T22S ×3, XT30PW-M ×3, GH-Kabel, Pigtail, Antenne (`EINKAUFSLISTE_revB1.md` §7.2) | ca. 25–35 € | noch offen |

Mouser (26.10. im Browser geprüft): INA239AIDGSR 0 Stück, 2303 erwartet am 25.03.2027; INA239AQDGSRQ1 0 Stück,
erwartet 01.02.2027. Mouser entfällt damit.

### DigiKey-Korb (40 Positionen, Preise netto, 26.10.2026)

| # | DigiKey-Nr. | Teil | Für | Menge | Stück | Summe | Lieferung |
|---|---|---|---|---|---|---|---|
| 1 | 296-INA239AIDGSRCT-ND | INA239AIDGSR | U6 | 3 | 3,770 | 11,31 | Rückstand, 02.11.2026 |
| 2 | 478-13307-1-ND | TCJE337M016R0050E 330 µF/16 V | C4, C5 | 5 | 4,130 | 20,65 | sofort |
| 3 | 18-1812L300/24SLERCT-ND | Polyfuse 3 A/24 V 1812 | F1 | 3 | 2,330 | 6,99 | sofort |
| 4 | 455-BM04B-GHS-TBTCT-ND | JST GH 4 | J11 | 3 | 0,340 | 1,02 | Rückstand, 02.11.2026 |
| 5 | 455-BM04B-SRSS-TBCT-ND | JST SH 4 | J12 | 3 | 0,470 | 1,41 | sofort |
| 6 | 455-BM03B-GHS-TBTCT-ND | JST GH 3 | J13, J14 | 5 | 0,320 | 1,60 | sofort |
| 7 | 587-NRS5040T1R5NMGJCT-ND | 1,5 µH 5040 | L2 | 3 | 0,210 | 0,63 | sofort |
| 8 | AP2112K-3.3TRG1DICT-ND | AP2112K-3.3 | U3, U14 | 5 | 0,250 | 1,25 | sofort |
| 9 | 296-37176-1-ND | SN74LV1T34DBVR | U8 | 3 | 0,360 | 1,08 | sofort |
| 10 | 1727-4065-1-ND | 74HC138PW | U12 | 3 | 0,290 | 0,87 | sofort |
| 11 | 296-13031-1-ND | CD74HC4051PWR | U13 | 3 | 0,520 | 1,56 | sofort |
| 12 | 1528-4684-ND | Adafruit 4684 WS2812B-2020 (10er) | LED1, LED2 | 1 | 3,510 | 3,51 | sofort |
| 13 | S7022-ND | Buchsenleiste 1×24 | A1 | 6 | 1,190 | 7,14 | sofort |
| 14 | 455-2248-ND | B3B-XH-A | J7, J16 | 5 | 0,120 | 0,60 | sofort |
| 15 | 1528-4210-ND | Adafruit 4210 SH-4-Kabel | J12 | 2 | 0,840 | 1,68 | sofort |
| 16 | 455-1704-ND | B2B-PH-K-S | J2, J18 | 5 | 0,110 | 0,55 | sofort |
| 17 | 455-1705-ND | B3B-PH-K-S | J17 | 3 | 0,140 | 0,42 | sofort |
| 18 | 455-1706-ND | B4B-PH-K-S | J3 | 3 | 0,180 | 0,54 | sofort |
| 19 | 455-1165-ND | PHR-2 Gehäuse | | 10 | 0,048 | 0,48 | sofort |
| 20 | 455-1126-ND | PHR-3 Gehäuse | | 3 | 0,090 | 0,27 | sofort |
| 21 | 455-1164-ND | PHR-4 Gehäuse | | 3 | 0,090 | 0,27 | sofort |
| 22 | 455-B2B-XH-A-ND | B2B-XH-A | J4, J8 | 5 | 0,090 | 0,45 | sofort |
| 23 | 455-S2B-XH-A-ND | S2B-XH-A | J9, J10 | 5 | 0,120 | 0,60 | sofort |
| 24 | 455-S3B-XH-A-ND | S3B-XH-A | J5, J6 | 5 | 0,160 | 0,80 | **Rückstand, 14.12.2026** |
| 25 | 455-2266-ND | XHP-2 Gehäuse | | 10 | 0,052 | 0,52 | sofort |
| 26 | 455-2219-ND | XHP-3 Gehäuse | | 8 | 0,090 | 0,72 | sofort |
| 27 | 35-PRPC010DAAN-RC-ND | Stiftleiste 2×10 | J15 | 3 | 0,310 | 0,93 | sofort |
| 28 | S7078-ND | Buchsenleiste 2×10, 8,5 mm | Zusatzplatine | 2 | 1,170 | 2,34 | sofort |
| 29 | 490-10530-1-ND | GRM32EC70J107ME15L 100 µF | C20 | 3 | 0,550 | 1,65 | sofort |
| 30 | F11449CT-ND | Polyfuse 2 A/16 V 1812 | F2 | 3 | 1,100 | 3,30 | sofort |
| 31 | 490-5258-1-ND | BLM18KG601SN1D | FB1 | 3 | 0,120 | 0,36 | sofort |
| 32 | 311-680KHRCT-ND | 680 k 0603 | R14 | 10 | 0,022 | 0,22 | **Rückstand, 21.12.2026** |
| 33 | 311-130KHRCT-ND | 130 k 0603 | R15 | 3 | 0,090 | 0,27 | Rückstand, 09.11.2026 |
| 34 | 311-115KHRCT-ND | 115 k 0603 | R17 | 3 | 0,090 | 0,27 | sofort |
| 35 | MCP73831T-2ACI/OTCT-ND | MCP73831T-2ACI/OT | U11 | 3 | 0,670 | 2,01 | sofort |
| 36 | EG1942-ND | EG2208A Schiebeschalter DPDT | SW | 2 | 0,820 | 1,64 | sofort |
| 37 | EG2350-ND | 100SP1T1B1M1QEH Kippschalter 5 A | Hauptschalter | 1 | 2,730 | 2,73 | sofort |
| 38 | SMAJ12CALFCT-ND | SMAJ12CA | D2, D3 | 5 | 0,430 | 2,15 | sofort |
| 39 | 455-1127-100-ND | SPH-002T-P0.5S PH-Crimpkontakte, 100er-Streifen | | 100 | 0,036 | 3,63 | sofort |
| 40 | 455-1135-100-ND | SXH-001T-P0.6 XH-Crimpkontakte, 100er-Streifen | | 100 | 0,042 | 4,18 | sofort |

Hinweise zum Korb:

- Die Crimpkontakte gibt es bei DigiKey nur als 100er-Streifen (kleinste Einheit), nicht einzeln; 100 Stück reichen
  für alle Stecker mit Reserve.
- Vier Positionen sind Rückstand. INA239, GH-4 und 130 k kommen Anfang November; S3B-XH-A (J5/J6) erst Mitte Dezember
  und 680 k (R14) erst 21.12. Beim Bestellen „Teillieferung“ wählen, oder vorher ersetzen: 680 k durch einen anderen
  Hersteller (DigiKey „Ersatzartikel anzeigen“ in Zeile 32), S3B-XH-A durch die gerade Ausführung B3B-XH-A (Zeile 14,
  dann Menge 10) oder den liegenden Reichelt-Typ `JST XH3P ST90`.
- Damit ist alles aus §1 und `EINKAUFSLISTE_revB1.md` §7.1 abgedeckt (Reichelt-Artikel durch die JST-Originale
  und Sullins-Leisten ersetzt). Summer, Litze und Crimpzange sind laut Einkaufsliste vorhanden.

## 7. Quellen (abgerufen 26.10.2026)

Reichelt-Suchen (Muster `https://www.reichelt.de/index.html?ACTION=446&LA=0&nbc=1&q=…`), Suchbegriffe: `SMAJ12CA`,
`SMD-0603 680K`, `SMD-0603 130K` (0 Treffer), `0603 130 kOhm`, `SMD-0603 115K` (0), `0603 115 kOhm`, `AP2112K-3.3` (0),
`AP2112` (0), `MIC5219` (0), `LDO 3,3 V SOT-23-5`, `MCP73831`, `74HC138PW` (0), `74HC138`, `74HC138 TSSOP` (0),
`74HC4051`, `SN74LV1T34` (0), `1G34` (0), `BLM18KG601`, `BSMD1812` (0), `PTC Sicherung 1812`, `PTC FSMD2`,
`PTC FSMD3`, `FNR5040S1R5MT` (0), `SRN5040`, `1,5µH SMD Induktivität`, `100µF 1210`, `BM04B-GHS-TBT` (0),
`BM03B-GHS` (0), `GHS-TBT` (0), `BM04B-SRSS` (0), `SRSS` (0), `JST GH`, `GHR-04V-S` (0), `JST PH`, `JST PH2P`,
`JST PH3P ST`, `JST PH4P ST`, `JST PH CK`, `JST XH`, `JST XH2P ST`, `JST XH3P ST`, `JST XH CK`, `JST XH1 CKS`,
`JST XH2 CKS`, `Buchsenleiste 1x24`, `MPE 094-1`, `Buchsenleiste 2x10`, `Stiftleiste 2x10 gerade`,
`Summer 12 mm 5 V`, `SUMMER TDB 05`, `XT30PW` (0), `XT30`, `Polymer 330µF 16V`, `SVP 330/16`, `NeoPixel Nano` (0),
`Qwiic Kabel`, `Stemma QT`, `U.FL SMA Buchse`, `Antenne 433 MHz SMA`.

- Reichelt Summer TDB 05: https://www.reichelt.de/de/de/shop/produkt/elektromagnetischer_summer-35918
- Reichelt PTC FSMD200R: https://www.reichelt.de/de/de/shop/produkt/ptc-sicherung_smd_1812_8v_2a_rueckstellend-279378
- Reichelt PTC FSMD26016R: https://www.reichelt.de/de/de/shop/produkt/ptc-sicherung_smd_1812_16v_2_6a_rueckstellend-279381
- Reichelt JST XH3P ST: https://www.reichelt.de/de/de/shop/produkt/jst_-_stiftleiste_gerade_1x3-polig_-_xh-185074
- DigiKey INA239AIDGSR: https://www.digikey.de/de/products/detail/texas-instruments/INA239AIDGSR/15857275
- DigiKey INA239AQDGSRQ1: https://www.digikey.de/de/products/detail/texas-instruments/INA239AQDGSRQ1/14641456
- DigiKey INA229AIDGSR: https://www.digikey.de/de/products/detail/texas-instruments/INA229AIDGSR/13636666
- DigiKey INA239AIDGST (obsolet): https://www.digikey.de/de/products/result?keywords=INA239AIDGST
- DigiKey AP2112K-3.3TRG1: https://www.digikey.de/de/products/result?keywords=AP2112K-3.3TRG1
- DigiKey SN74LV1T34DBVR: https://www.digikey.de/de/products/detail/texas-instruments/SN74LV1T34DBVR/4555575
- DigiKey 74HC138PW,118: https://www.digikey.de/de/products/detail/nexperia-usa-inc/74HC138PW-118/1230077
- DigiKey 74HC4051PW,118: https://www.digikey.de/de/products/detail/nexperia-usa-inc/74HC4051PW-118/946649
- DigiKey CD74HC4051PWR: https://www.digikey.de/de/products/detail/texas-instruments/CD74HC4051PWR/480147
- DigiKey BM04B-GHS-TBT: https://www.digikey.de/de/products/result?keywords=BM04B-GHS-TBT
- DigiKey BM03B-GHS-TBT: https://www.digikey.de/de/products/detail/jst-sales-america-inc/BM03B-GHS-TBT/807801
- DigiKey BM04B-SRSS-TB: https://www.digikey.de/de/products/detail/jst-sales-america-inc/BM04B-SRSS-TB/926696
- DigiKey B3B-XH-A: https://www.digikey.de/de/products/detail/jst-sales-america-inc/B3B-XH-A/1651046
- DigiKey NRS5040T1R5NMGJ: https://www.digikey.de/de/products/detail/taiyo-yuden/NRS5040T1R5NMGJ/7404150
- DigiKey SRN5040TA-1R5M: https://www.digikey.de/de/products/result?keywords=SRN5040TA-1R5M
- DigiKey 1812L300/24SLER: https://www.digikey.de/de/products/result?keywords=1812L300%2F24SLER
- DigiKey Polymer 330 µF/16 V 2917 (Übersicht): https://www.digikey.de/de/products/result?keywords=CAP%20TANT%20POLY%20330UF%2016V%202917
- DigiKey TCJE337M016R0050E: https://www.digikey.de/de/products/result?keywords=TCJE337M016R0050E
- DigiKey T521X337M016ATE050: https://www.digikey.de/de/products/detail/kemet/T521X337M016ATE050/3760640
- DigiKey Adafruit 4684: https://www.digikey.de/de/products/result?keywords=4684%20adafruit
- DigiKey Sullins PPTC241LFBN-RC: https://www.digikey.de/de/products/result?keywords=PPTC241LFBN-RC
- DigiKey Adafruit 4210/4399: https://www.digikey.de/de/products/result?keywords=adafruit%204210
- DigiKey AGHGH28K152: https://www.digikey.de/de/products/result?keywords=AGHGH28K152
- DigiKey XT30PW-M (0 Treffer): https://www.digikey.de/de/products/result?keywords=XT30PW-M
- DigiKey Versandschwelle 75 €: https://www.digikey.de/de/maker/search-results?pn=4156446
- Adafruit 4684 (WS2812B-2020): https://www.adafruit.com/product/4684
- TI INA239AIDGSR: https://www.ti.com/product/INA239/part-details/INA239AIDGSR
- Mouser INA239AIDGSR (nicht abrufbar, nur Suchauszug): https://www.mouser.com/ProductDetail/Texas-Instruments/INA239AIDGSR?qs=DRkmTr78QASO8y6Kfjsnog%3D%3D
- Mouser INA239AIDGST (Suchauszug): https://eu.mouser.com/ProductDetail/Texas-Instruments/INA239AIDGST?qs=DRkmTr78QAThtxJud4ehZg%3D%3D
- Mouser-Schwelle 75 € (Forum, undatiert): https://www.mikrocontroller.net/topic/584808
- LCSC BSMD1812-300-16V: https://lcsc.com/product-detail/C883162.html
- LCSC FNR5040S1R5MT: https://www.lcsc.com/product-detail/C167955.html
- LCSC WS2812B-2020: https://www.lcsc.com/product-detail/C965555.html
- LCSC WS2812B-2020-V6: https://www.lcsc.com/product-detail/C52917434.html
- LCSC E22-400T22S: https://fat.lcsc.com/product-detail/image/E22-400T22S_C2903765.html
- LCSC XT30PW-M: https://fat.lcsc.com/product-detail/image/XT30PW-M_C431092.html
- JLCPCB E22-400T22S: https://jlcpcb.com/partdetail/Chengdu_Ebyte_ElecTech-E22400T22S/C2903765
- Ebyte-Shop E22-400T22S-V2: https://ebyteiot.com/products/ebyte-e22-400t22s-semtech-sx1268-uart-5km-range-433mhz-22dbm-smd-16-26mm-ce-rohs-fcc-tcxo-external-and-ufl-antenna-lora-wireless
- RobotShop E22-400T22S: https://www.robotshop.com/products/ebyte-e22-400t22s-lora-spread-spectrum-uart-lora-solution-rf-low-power-consumption
- electrokit XT30PW-M: https://www.electrokit.com/en/xt30-power-connector-angled-2-pin-1530a-pcb-male
- Berrybase XT30-Suche: https://www.berrybase.de/search?search=XT30PW
- Reichelt-Versand ab 5,95 € (Drittseite): https://www.mydealz.de/gutscheine/reichelt-de
