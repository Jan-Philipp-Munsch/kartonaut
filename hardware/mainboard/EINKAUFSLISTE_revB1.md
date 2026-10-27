# Einkaufsliste Mainboard rev B1: alles, was JLCPCB nicht liefert

Stand 24.10.2026. JLCPCB bestückt nur die SMD-Oberseite (`kicad/fab/`, Economic PCBA). Alles andere kommt von hier:
die 16 THT-Teile zum Selbstlöten, die Gegenstecker und Kabel, Module und Zubehör, Akkus, Werkzeug, und die Breakouts
für den Tisch. Preise sind Richtwerte aus Händlerseiten (Oktober 2026), keine Angebote. Ausführlicher Hintergrund in
`ORDER.md` §7; diese Liste ist die bestellfertige Kurzfassung, sortiert nach Händler.

Schon vorhanden laut `docs/BUILD.md` §1.3 (nicht noch einmal kaufen, nur prüfen): Teensy 4.1, Breakouts ICM-20948,
BMP280, INA219, 2× HC-12, SG90-Servos, WS2812B, aktiver Summer, Lader HTRC H4AC (2 bis 4S, **kein 1S**), 4S-Akku für
den Prüfstand, FrSky W5652H bestellt.

## 1. Was auf die Platine gelötet wird (16 THT-Teile)

| Ref | Teil | Genaue Bezeichnung | Stück | Händler |
|---|---|---|---|---|
| A1 | Teensy 4.1 | PJRC Teensy 4.1 (ohne Stifte) + 2× Stiftleiste 1×24 zum Einlöten; dazu 2× **Buchsenleiste 1×24, 2,54 mm, 8,5 mm** auf der Platine | 1 (+1 Reserve) | Watterott, Berrybase, Eckstein (Teensy); Reichelt (Leisten) |
| J1 | 2S-Akku | AMASS **XT30PW-M** (liegend, Platine) | 3 | Hobbyking, AliExpress, Berrybase |
| J2 | 1S-Akku | JST **B2B-PH-K-S** (PH 2,0 mm, 2-polig, stehend) | 5 | Reichelt, Mouser |
| J3 | Schalterbrett | JST **B4B-PH-K-S** (4-polig, stehend) | 3 | Reichelt, Mouser |
| J17 | USB-C-Lader 1S | JST **B3B-PH-K-S** (3-polig, stehend) | 3 | Reichelt, Mouser |
| J18 | 2S-Ladebuchse | JST **B2B-PH-K-S** (wie J2) | s. o. | |
| J4, J8 | Arming, Rollmotor | JST **B2B-XH-A** (XH 2,5 mm, 2-polig, stehend) | 5 | Reichelt, Mouser |
| J9, J10 | Pyro 1, 2 | JST **S2B-XH-A** (2-polig, liegend) | 5 | Reichelt, Mouser |
| J5, J6 | TVC-Servos | JST **S3B-XH-A** (3-polig, liegend) | 5 | Reichelt, Mouser |
| J7, J16 | Fallschirm, Beine | JST **B3B-XH-A** (3-polig, stehend) | 5 | Reichelt, Mouser |
| J15 | Stapelstecker | Stiftleiste **2×10, 2,54 mm**, gerade | 3 | Reichelt |
| BZ1 | Summer | aktiver Summer 5 V, Ø 12 mm, THT, Rastermaß 7,6 mm | 2 | Reichelt (vorhandener prüfen) |

Reichelt hat JST-XH und -PH als Originale; Mouser/DigiKey ebenso (dort mit Mindermengenzuschlag unter 50 €).
Billig-Sortimente von Amazon/AliExpress passen meist, die Kontakte sind aber weicher.

## 2. Gegenstecker und Kabel (Gegenstück je Buchse, `ORDER.md` §7.1a)

| Für | Teil | Stück | Händler |
|---|---|---|---|
| J2, J18 | JST **PHR-2** Gehäuse + **SPH-002T-P0.5S** Crimpkontakte (RC-1S-Zellen haben PH 2.0 schon dran) | 10 Gehäuse, 40 Kontakte | Reichelt, Mouser |
| J3 | JST **PHR-4** + Kontakte | 3 | Reichelt |
| J17 | JST **PHR-3** + Kontakte | 3 | Reichelt |
| J4, J8, J9, J10 | JST **XHP-2** + **SXH-001T-P0.6** Kontakte | 10 Gehäuse, 40 Kontakte | Reichelt |
| J5, J6, J7, J16 | JST **XHP-3** + Kontakte; die Servostecker (JR, 2,54 mm) passen nicht in XH: Servoleitung umcrimpen oder Adapterkabel XH-3 → Servobuchse | 8 Gehäuse, 30 Kontakte | Reichelt |
| J11 (GPS) | konfektioniertes JST-**GH 4-polig** Kabel 10–15 cm (GHR-04V-S, offenes Ende) | 2 | Berrybase, Eckstein, AliExpress |
| J13, J14 (Kamera, LEDs) | konfektioniertes JST-**GH 3-polig** Kabel | 3 | wie oben |
| J12 (Qwiic) | **Qwiic/Stemma-QT-Kabel** SH-4 1,0 mm, 5 und 10 cm; eins mit offenem Ende | 3 | Berrybase, Eckstein, Adafruit |
| J15 | **Buchsenleiste 2×10, 2,54 mm** für die Zusatzplatine (Stapelhöhe nach Bedarf, 8,5 oder 11 mm) | 2 | Reichelt |
| U10 (LoRa) | **Pigtail IPEX/u.FL → SMA-Buchse**, 10 cm, und **433-MHz-Stabantenne SMA** (für den Flug λ/4-Draht 17 cm in der Spitze) | je 2 | Berrybase, AliExpress |
| Teensy | microSD-Karte 8–32 GB (Class 10), USB-Kabel Micro-B | 1 | überall |
| Akku 2S | Ladekabel XT30 → Balancer/Lader, Balancer-Verlängerung | 1 | Modellbau |

## 3. Module, Akkus, Schalter, Zünder

| Nr. | Teil | Genaue Bezeichnung | Stück | ca. | Händler |
|---|---|---|---|---|---|
| 3.1 | 1S-Flugakku | LiPo 450–600 mAh, 25–30 C, **JST-PH 2.0, ohne Schutzschaltung** (BetaFPV/HappyModel 1S 450–550 mAh; E-flite 500 mAh 25 C). Keine Elektronik-Zellen mit PCM (Berrybase LP503035): deren 1–1,5-A-Schutz löst beim Buck-Boost aus | 2 | 2 × 5–11 € | Modellbau (Hobbyking, Drone-Shops), Amazon |
| 3.2 | 2S-Flugakku | LiPo 450–850 mAh, 50 C, XT30 | 1–2 | 12–20 € | Modellbau |
| 3.3 | 1S-Lader | USB-Lader für 1S mit JST-PH (BetaFPV 1S 6-fach oder einfacher PH-2.0-Lader); der HTRC H4AC kann kein 1S | 1 | 10–20 € | Modellbau, Berrybase |
| 3.4 | Hauptschalter | Mini-Schiebeschalter DPDT (führt nur Gate-Strom, Review A3) | 2 | 2 × 1–2 € | Reichelt |
| 3.5 | Arming | Schlüsselschalter oder Kippschalter mit Schutzkappe, ≥ 3 A (führt den Pyro-Puls) | 1 | 3–8 € | Reichelt |
| 3.6 | Schalterbrett 1S-Laden | USB-C-Buchse mit 5,1-k-CC-Widerständen auf kleiner Platine (Breakout „USB-C power only“) + Lade-LED mit Vorwiderstand | 1 | 2–4 € | Berrybase, Eckstein |
| 3.7 | GPS | u-blox **MAX-M10S**-Breakout (Matek M10-5883 ohne Kompass nutzen, oder Berrybase/Sparkfun MAX-M10S), UART 3,3 V | 1, optional | 17–30 € | Berrybase, Matek-Händler (Drone-Shops) |
| 3.8 | Kamera | Runcam/Caddx mit externem Auslöser (3,3-V-Trigger an J_CAM) | 1, optional | 20–40 € | Drone-Shops |
| 3.9 | Zünder | Elektrozünder (E-Matches) + Glühlämpchen 6 V als Dummy-Last für den Tischtest | 10 + 5 | 10–15 € | Raketenmodellbau Klima, Modellbau |
| 3.10 | Rollmotor | Bürsten-DC-Motor ≤ 1 A am 2S (z. B. N20 mit Getriebe oder Außenläufer-Schwungrad nach CAD); DRV8833 verträgt 1,5 A Spitze | 1 | 5–15 € | Berrybase, Pololu-Händler |
| 3.11 | Antenne Flug | isolierter Draht 2 mm oder Stab, 17 cm, in der Spitze | – | – | vorhanden |
| 3.12 | Isolierung | Kapton- oder PE-Schaumplatte 1 mm zwischen Platine und Akkuträger (Review B18) | 1 | 3–5 € | Amazon, Baumarkt |

## 4. Reserveteile zum Nachlöten (optional, eine LCSC-Bestellung, ca. 10 € Versand)

2× LSM6DSV16X (C5267406), 2× E22-400T22S (C2903765), 2× TPS63070RNMR (C109322), 2× BMP388 (C779278) oder BMP390,
2× DRV8833PWPR, 2× INA239AIDGSR, 2× AO3401A, 2× AO3400A, 1× Polyfuse 1812 je Wert. Nur, wenn die zweite bestückte
Platine nicht als Reserve reicht. Der INA239 (MSOP-10) ist bei DigiKey/Mouser einfacher zu haben als bei LCSC.

## 5. Breakouts und Werkzeug für den Tisch (unabhängig von der Platine)

| Teil | Zweck | Stück | ca. | Händler |
|---|---|---|---|---|
| SparkFun **6DoF IMU Breakout - LSM6DSV16X** (Qwiic; auch Micro-Version) | IMU-Treiber vor der Platine entwickeln; später zweite IMU auf dem TVC-Mount über J_QWIIC | 1 | 10–20 € | Berrybase, Eckstein, The Pi Hut, SparkFun |
| Adafruit **BMP390** Breakout (4816) | Barometer-Treiber; Rückfall an J_QWIIC | 1 | 12–17 € | Berrybase, Eckstein, Kiwi Electronics |
| Ebyte **E22-400T22D** (DIP, SMA) | Bodenstation und Tisch-Gegenstelle | 2 | 2 × 8–12 € | AliExpress (Ebyte-Shop), eBay |
| Crimpzange JST-XH/PH | Engineer PA-09 (ca. 45 €) oder IWISS SN-01BM (20–25 €) | 1 | 20–45 € | Amazon, Reichelt |
| Silikonlitze AWG 20 (Akku), 22 (Servo), 26 (Signale), rot/schwarz | Kabel | je 2 m | 8–10 € | Reichelt |
| Lötzubehör für LGA/QFN-Nacharbeit | Flussmittel-Gel, Lötpaste bleifrei (Rückfall), Heißluft | – | – | Reichelt |

## 6. Wo bestellen (Vorschlag, vier Bestellungen)

1. **Reichelt** (eine Bestellung, 40–60 €): alle JST-Buchsen und -Gehäuse mit Kontakten (1, 2), Buchsen- und
   Stiftleisten, Summer, Schalter (3.4, 3.5), Litze, Flussmittel. Originale JST, Versand 1–2 Tage.
2. **Berrybase oder Eckstein** (eine Bestellung, 60–100 €): LSM6DSV16X- und BMP390-Breakout, Qwiic- und GH-Kabel,
   Pigtails und Antennen, USB-C-Breakout, Teensy-Reserve, ggf. GPS und Rollmotor.
3. **Modellbau / Drone-Shop** (40–70 €): 1S- und 2S-Akkus, 1S-Lader, XT30PW-M, Ladekabel; Zünder beim
   Raketenmodellbau (Klima).
4. **AliExpress / eBay** (20–30 €, 2–4 Wochen, deshalb zuerst): E22-400T22D ×2 mit Antennen; optional Pigtails und XT30
   günstiger als bei 2.

Summe ohne GPS, Kamera und Crimpzange etwa **150–220 €**, mit allem **230–320 €**. Reihenfolge: 4 und 2 sofort
(Lieferzeit, Treiberarbeit am Breakout), 1 und 3 bis zur Lieferung der Platinen (JLC etwa 2 Wochen nach Bestellung).

## 7. Bestellfertige Körbe (Stand 26.10.2026)

### 7.1 Reichelt (Schnellerfassung im Warenkorb: Artikelnummer, Menge)

Für zwei bestückte Platinen plus Reserve. Preise vom 24.10.2026, Summe 25,75 € zzgl. 5,95 € Versand.

| Artikel-Nr. | Was | Für | Stück |
|---|---|---|---|
| JST PH2P ST | PH 2-polig stehend | J2 (1S-Akku), J18 (2S-Laden) | 5 |
| JST PH3P ST | PH 3-polig stehend | J17 (USB-C-Lader) | 3 |
| JST PH4P ST | PH 4-polig stehend | J3 (Schalterbrett) | 3 |
| JST PH2P BU / PH3P BU / PH4P BU | PH-Crimpgehäuse (Kabelseite) | | 10 / 3 / 3 |
| JST PH CKL | PH-Crimpkontakte 28–24 AWG | | 60 |
| JST XH2P ST | XH 2-polig stehend | J4 (Arming), J8 (Motor) | 5 |
| JST XH2P ST90 | XH 2-polig liegend | J9, J10 (Pyro) | 5 |
| JST XH3P ST90 | XH 3-polig liegend | J5, J6 (TVC); ersatzweise auch J7, J16 (stehend „JST XH3P ST“ erst ab 28.11. lieferbar) | 10 |
| JST XH2P BU / XH3P BU | XH-Crimpgehäuse (Kabelseite) | | 10 / 8 |
| JST XH1 CKS | XH-Crimpkontakte 28–22 AWG | | 70 |
| SL 2X10G 2,54 | Stiftleiste 2×10 | J15 (J_STACK) | 3 |
| BL 2X10G8 2,54 | Buchsenleiste 2×10, 8,5 mm | Zusatzplatine | 2 |
| FIS BL1 36 G | Buchsenleiste 1×36 trennbar, vergoldet (auf 24 kürzen) | A1 (Teensy) | 2 |
| T 217 | Miniatur-Schiebeschalter 2×UM, Lötanschluss | Hauptschalter am Schalterbrett | 2 |
| MS 500A | Kippschalter 6 A, M6×0,75 | Arming (statt Schlüsselschalter; CAD-Kragen in `cad/avionics.py` von Ø 12 auf Ø 6,2 ändern) | 1 |

Nicht bei Reichelt: XT30PW-M, Pigtail, GH-/SH-Kabel (7.2). Summer, Litze und Crimpzange sind vorhanden.

### 7.2 AliExpress (eine Bestellung, „Versand aus EU“ filtern)

Stand 27.10. abends: **nur noch E22-400T22S ×3** (CDEBYTE Official Store, 28,72 € mit Abgaben; zwei Platinen, eins Bodenstation); alle anderen Positionen
unten entfallen oder kommen aus dem Bestand, Begründung in `Beschaffung_2026-10-26.md` §6c.

| Teil | Suche | Worauf achten | Stück |
|---|---|---|---|
| XT30PW-M (J1) | XT30PW-M | AMASS, PW-M = liegend, Platinenmontage | 5 |
| Pigtail IPEX → SMA-Buchse 10 cm | IPEX SMA female pigtail 10cm | u.FL/IPEX-1 (nicht MHF4), SMA female mit Gehäusegewinde | 2 |
| 433-MHz-Stabantenne | 433MHz SMA antenna 3dBi | SMA male, nicht RP-SMA | 2 |
| JST-GH 4-polig, 15 cm, ein Ende offen (GPS, J11) | JST GH 1.25mm 4 pin cable | Raster 1,25 mm mit Verriegelung | 3 |
| JST-GH 3-polig (Kamera J13, LEDs J14) | JST GH 1.25mm 3 pin cable | wie oben | 3 |
| Qwiic / JST-SH 4-polig, 5 und 10 cm (J12) | JST SH 1.0mm 4 pin Qwiic cable | Raster 1,0 mm, einmal offenes Ende | 4 |

Berrybase lohnt nicht (Qwiic-Kabel ausverkauft, Pigtail/GH/XT30PW nicht im Programm); Eckstein als schnellere
Alternative für Pigtail und Qwiic-Kabel. GPS: vorhandenes u-blox-Modul an J_GPS, Befestigung mit Schaumklebepad
oben auf dem Träger, Antenne zur Spitze, andere Rohrseite als die LoRa-Antenne.
