# Mainboard rev B1 – Spezifikation

Stand 2026-10-22. Rev B ersetzt rev A (`rev_a_2026-10-15.md`, dort stehen die Begründungen,
die hier unverändert gelten). Die Planungsrunde vom 21.10.2026 (`docs/Plan_2026-10-21.md`, §2)
hat die Sensorik, den Funk, die Servos und vor allem die Versorgung neu entschieden. Ziel bleibt:
ein Board, das den Teensy 4.1 trägt und alles enthält, was heute als Breakout mit Dupont-Kabeln
am Teensy hängt. Das ist die Vorgabe für das KiCad-Projekt in `kicad/`.

**Rev B1** ist die Bestellfassung. Sie enthält das Zweitmeinung-Review (`review_kicad_2026-10-21.md`,
Punkte A1 bis A8 und die B-Punkte, die wenig kosten) und die Entscheidungen vom 22.10.2026
(`Komponenten_2026-10-22.md`, E1 bis E10). Was sich gegenüber rev B ändert, steht in §0; §3 bis §7 beschreiben
den Stand B1. Abweichungen von dieser Spezifikation und ihre Gründe stehen in `kicad/README.md` §6,
die Fertigerwahl in `Fertiger_2026-10-21.md`.

## 0. Was sich gegenüber rev B ändert (B1, 22.10.2026)

| Nr. | Änderung |
|---|---|
| A1 | 2 × 470 µF Polymer (7343) als Hold-up hinter D1 an TEENSY_VIN; am Ausgang des TPS63070 nur 3 × 22 µF |
| A2 | EN-Teiler 330 k / 115 k: an ab 3,1 V, aus unter 2,7 V |
| A3, E1 | Hauptschalter schaltet nur die Gates zweier P-FET-Lastschalter (Q6 2S, Q7 1S); J_SW trägt Mikroampere. J_ARM und J_MOT als JST-XH |
| A4 | Polyfuse je Akku direkt hinter dem Verpolschutz (F1 2S 3 A/6 A, F2 1S 2 A); Zündpuls 50 bis 100 ms |
| A5 | Shunt mit geteilten Kelvin-Pads, INA-Eingang mit 2 × 10 Ω und 100 nF |
| A6 bis A8 | 2S-Pfad als Kupferflächen auf F.Cu, nie auf In2; VSYS_IN 0,6 mm; 5V_SERVO entfällt (E9) |
| E2 | 1S-Lader MCP73831 auf der Platine, USB-C und Lade-LED am Schalterbrett; 2S-Ladeanschluss J_CHG2 parallel zu J_BAT2 |
| E3 | BMP390 an SPI1, **INA239** (SPI) statt INA219; I²C nur noch für J_QWIIC und J_STACK |
| E4, E9 | Alle Servos und der Rollmotor an VSERVO (2S direkt); TPS563201 und 5V_SERVO entfallen |
| E5 | Vier Pyro-Kanäle (3 und 4 DNP), vierter Servo-Stecker, DRV8833 nSLEEP an Pin 11, zweites BMP390 als DNP, E22 NRST an Pin 6 |
| E10 | Stapelstecker J_STACK (2 × 10) statt J_EXP; 74HC138 für die SPI-Chip-Selects, 74HC4051 für die Analogeingänge, eigener LDO 3V3_EXP |
| B3 | Polymer-Elkos 7343 statt stehender THT-Elkos |
| B4 | Ferrit + 10 µF: eigene Sensor-Versorgung 3V3_SENS für IMU und Barometer |
| B7, B8 | Summer auf Pin 37; eine WS2812B-Kette hinter einem SN74LV1T34 (Pin 5) |
| B16, B17 | 5 mm ohne fremde Vias und ohne In2-Bahnen um die IMU; Funkmodul 0,5 mm vom Rand |

![Platzierungsplan](mainboard_placement.svg)

`outline.py` erzeugt `mainboard_outline.dxf` (Edge.Cuts) und `mainboard_placement.svg` und prüft,
dass alle Bauteil-Hüllen im Kuppler bleiben und die M2-Stangen nicht berühren.

## 1. Was sich gegenüber rev A ändert

| Thema | rev A | rev B | Grund |
|---|---|---|---|
| Versorgung | ein 2S-LiPo, zwei 5-V-Bucks | **zwei Akkus**: 1S für die Elektronik über Buck-Boost, 2S für Servos, Rollmotor, Pyro | Servo- und Pyro-Spitzen dürfen den Teensy nie in den Neustart ziehen (Plan §2.5) |
| IMU | ICM-20948 an SPI1 | **ICM-42688-P** an SPI1 | ICM-20948 ist *Not For New Designs*; der 42688-P rauscht weniger, misst ±16 g, braucht keinen DMP |
| Barometer | BMP280 | **BMP390** | halbes Rauschen, gleiche Bibliotheksfamilie |
| Funk | HC-12 gesteckt | **LoRa E22-400T22S** (SMD, SX1268, 433 MHz, 22 dBm) auf dem Board, IPEX-Pigtail zur Spitze | Reichweite; die SMD-Variante passt in den Funk-Streifen, die DIP-Variante (24 × 43 mm) nicht |
| TVC-Servos | SG90 an 5V_SERVO | **FrSky Xact W5652H direkt am 2S-Akku** (bis 8,4 V) | bestellt; am Akku doppelt so schnell wie an 5 V |
| Shunt | 0,1 Ω | **20 mΩ** | spart 0,24 V Einbruch bei 3 A; INA219 misst damit bis 16 A |
| Schalter | ein Hauptschalter, ein Arming | **zweipoliger Hauptschalter** (beide Akkus), Arming getrennt | kein Akku wird vergessen |
| Stecker | Stiftleisten für Servos, Klemmen für Pyro | alle verriegelt (XT30, JST-PH/GH/XH), Pyro als JST-XH 2 mit Zugentlastung | Vibration |
| Bergung | Servo und Pyro | **Pyro** (beide Kanäle), Servo-Ausgang bleibt als Reserve | Pyro-Tests mit ca. 1 g Schwarzpulver erfolgreich |
| Einbau | Rohr-Innenmaß unbekannt (69 mm angenommen) | **Kuppler, innen 70,2 mm**; die Platine bleibt 54 × 120 mm | der Flugcomputer sitzt im Kuppler und ist als Modul herausziehbar |

Unverändert aus rev A: Teensy 4.1 als gestecktes Modul, Längs-Schlitten mit der Platinenebene durch
die Rollachse, IMU auf der Achse unter dem Teensy, Stecker an den Stirnseiten, 4 Lagen bei JLCPCB
mit SMD-Bestückung, Pyro-Konzept mit Low-Side-FETs, externem Arming und Durchgangsprüfung,
zwei WS2812B und Summer, W25Q128 unter dem Teensy.

## 2. Mechanik

- **54 × 120 mm, 1,6 mm, 4 Lagen, ENIG.** Koordinaten wie rev A: u quer (0 auf der Achse), v längs
  (0 am TVC-Ende). Platinenebene durch die Rollachse.
- **Einbau** zwischen den Endringen des Ring-Stacks (Ø 69 mm) im Kuppler (innen 70,2 mm, 150 mm
  lang). Die 8 M2-Stangen laufen an den Längskanten vorbei (5,7 mm Abstand). Die Platine sitzt mit
  4× M3 (u = ±23,5, v = 3,5 / 116,5) auf dem gedruckten Träger.
- **Akkus im Träger unter der Platine, hintereinander:** 2S (56 × 25,5 × 8 mm) bei v ≈ 8 bis 64,
  1S (ca. 50 × 30 × 7 mm, 450–600 mAh) bei v ≈ 68 bis 118. Beide liegen in Fächern des Trägers mit
  Klettband, Kabel nach unten (2S, zum XT30 am TVC-Ende) bzw. zur Seite (1S, JST-PH).
- **Bestückung nur oben.** Unten nur THT-Lötstifte unter 2 mm.
- **Bauhöhe:** mittig über 30 mm, am Rand (|u| > 25 mm) höchstens 5 mm.
- **Teensy** mittig (v = 30 bis 91), SD-Slot zum TVC, USB zur Spitze; Freiflächen 6 mm vor dem SD-Slot,
  12 mm vor USB. Luke im Kuppler und Rohr auf Höhe v ≈ 25 bis 100 mm.
- **IMU** bei (u = 0, v = 60,5) unter der Teensy-Mitte, maximal 3 mm hoch, Chip so gedreht, dass X quer
  (+u) und Y zur Spitze (+v) zeigt. Firmware: `chipToBody(c) = (c.x, -c.z, c.y)` wie rev A §2.
  Pfeile im Bestückungsdruck.
- **Barometer** im rechten Streifen (B1: v ≈ 60, neben dem DRV8833; für das Review: weiter zur Spitze
  rücken, falls Wärme oder Luftzug vom Motortreiber stören), Schaum darüber, 3 bis 4 Bohrungen Ø 2 mm im
  Rohr auf dieser Höhe. Die Avionik-Sektion ist gegen den Fallschirmraum dicht (Ausstoßdruck).
- **Funk** im linken Streifen (B1: v ≈ 48 bis 74), IPEX-Buchse zeigt zur Spitze, Pigtail (10 cm) zu einer
  λ/4-Antenne (17 cm Draht oder Stab) in der Klima-Spitze, frei von Kupfer und Akku.
- **GPS** nicht auf dem Board: Modul (u-blox M9/M10) in der Spitze, Patchantenne nach oben,
  mindestens 10 cm von der LoRa-Antenne, Kabel über J_GPS.

## 3. Stromversorgung

```
1S LiPo (3,0–4,2 V) ─ J_BAT1 (JST-PH 2) ─ Q2 Verpolschutz ─ F2 Polyfuse 2 A ─ VBAT1_F ─ Q7 Lastschalter ─ VSYS_IN
   ├─ VBAT1_F: 100 k / 33 k → Mux-Kanal 4 (VBAT1_SENSE, auch bei ausgeschalteter Rakete)
   ├─ VBAT1_F: U11 MCP73831 1S-Lader 500 mA ← J_CHG1 (USB-C VBUS und Lade-LED am Schalterbrett)
   └─ VSYS_IN: U2 TPS63070 Buck-Boost (2–16 V ein, 5 V / 2 A, 1,5 µH, EN an ab 3,1 V) → 5V_SYS, 3 × 22 µF
         ├─ D1 Schottky SS14 → TEENSY_VIN, 2 × 470 µF Polymer Hold-up (USB darf gleichzeitig stecken)
         ├─ WS2812B-Kette über SN74LV1T34, Summer über AO3400A
         ├─ U3 AP2112K-3.3 → 3V3_RF (100 µF): LoRa E22, GPS (J_GPS)
         └─ U14 AP2112K-3.3 → 3V3_EXP: Zusatzplatinen an J_STACK
   Teensy 3V3 (≤ 250 mA) → INA239, 74HC138, 74HC4051, I²C-Pull-ups
         └─ Ferrit FB1 + 10 µF → 3V3_SENS: ICM-42688-P, BMP390 (und das zweite, DNP)

2S LiPo (6,0–8,4 V) ─ J_BAT2 (XT30) ─ Q1 Verpolschutz ─ F1 Polyfuse 3 A/6 A ─ VBAT2_F ─ Q6 Lastschalter ─ VBAT_PROT
   ├─ VBAT2_RAW: J_CHG2 (JST-PH 2) parallel zum Akku, Kabel zur XT30-Ladebuchse am Schalterbrett
   ├─ VBAT2_F: 100 k / 33 k → Mux-Kanal 5 (VBAT2_SENSE)
   ├─ J_ARM (JST-XH 2, Schlüsselschalter ≥ 5 A) ─ VBAT_ARMED ─ Pyro 1–4 (+), TVS, 100 k / 33 k → Mux-Kanal 6
   └─ R_SHUNT 20 mΩ 2512 (INA239, Kelvin) ─ VSERVO (= Akku direkt), 2 × 330 µF Polymer
         └─ J_SERVO1..4 (W5652H-Klasse), DRV8833 (Rollmotor, PWM begrenzt), J_STACK (Reserve)

Hauptschalter J_SW: Pol a zieht das Gate von Q7 auf GND, Pol b das Gate von Q6 auf GND_PWR.
GND beider Akkus an einem Sternpunkt (NT1) am 2S-Minus.
```

- **J_SW** ist ein vierpoliger JST-PH zum Schalterbrett an Luke B. Der zweipolige Schiebeschalter schaltet
  nur die Gates der Lastschalter (je 100 k nach Source, 1 k zum Stecker), der Akkustrom bleibt auf der
  Platine (E1). Zwei Lötbrücken **JP1 (1S)** und **JP2 (2S)** ersetzen den Schalter auf dem Tisch.
  Ohne gesteckten Schalter ist die Rakete aus.
- **Laden in der Rakete (E2):** beide Ladeanschlüsse liegen vor den Lastschaltern, laden also bei
  ausgeschalteter Rakete. Die Teiler für beide Akkuspannungen liegen ebenfalls davor; der Teensy am USB
  sieht beide Akkus.
- **TPS63070** statt eines reinen Boosts, weil er 2 bis 16 V nimmt: Ein versehentlich an J_BAT1
  gesteckter 2S-Akku zerstört nichts. Falls JLC ihn nicht bestücken kann: TPS63020 (1,8–5,5 V ein,
  2 A) als 1S-Variante. Am Ausgang höchstens 470 µF (Datenblatt); der Hold-up sitzt deshalb hinter D1 (A1).
- **Pyro** liegt vor dem Shunt, Zündströme laufen nicht durch den INA239. Die Firmware begrenzt den
  Zündpuls auf **50 bis 100 ms** und schaltet ab, sobald der Durchgang verloren ist (A4). Der INA239
  misst mit 20 mΩ bis ±8 A (ADCRANGE 0, ±163,84 mV); `SHUNT_CAL` aus 20 mΩ.
- **Was die Firmware loggt und meldet:** beide Akkuspannungen und ARM über den Analogmux, Strom und
  Spannung von VSERVO (INA239), ARM-Zustand. Warnton bei 1S < 3,5 V oder 2S < 6,6 V; kein
  Start-Freigabeton ohne beide Akkus.

**Strombudget**

| Akku / Schiene | Verbraucher | Dauer | Spitze |
|---|---|---|---|
| 1S → 5V_SYS | Teensy 600 MHz 0,1 A, 2× WS2812B 0,12 A, Summer 0,03 A, 3V3_RF 0,15 A | 0,4 A an 5 V (0,6 A aus dem 1S) | 0,8 A (LoRa-Sendepuls 110 mA an 3,3 V plus Summer) |
| 2S → VSERVO | 2× W5652H (TVC), Blockierstrom je ca. 1 A bei 8,4 V | 0,2 A | 2 A |
| 2S → VSERVO | Servo 3 und 4 (Fallschirm, Beine), Rollmotor ca. 1 A (PWM begrenzt) | 0,3 A | 2 A |
| 2S → Pyro | E-Match 3–5 A für 20 ms | – | 5 A |

Akku-Vorschlag: 1S 450–600 mAh 20 C mit JST-PH (10–12 g), 2S 450–850 mAh 50 C mit XT30 (30–55 g).

## 4. Pinbelegung Teensy 4.1

Stand B1 (Komponenten §5 und §9). ★ = neu oder anders als rev B. Die Netzlistenprüfung
`kicad/check_design.py` prüft genau diese Tabelle.

| Pin | Signal | Ziel | Status |
|---|---|---|---|
| 0 / 1 | RX1 / TX1 | GPS (J_GPS, JST-GH 4: 3V3_RF, GND, TX, RX) | |
| 2 / 3 | MOT_IN1 / MOT_IN2 | DRV8833 AIN1=BIN1 / AIN2=BIN2 (Brücken parallel) | |
| 4 | IMU_INT | ICM-42688-P INT1 | |
| 5 | LED_DATA | SN74LV1T34 → LED1 → LED2 → J_LED (eine Kette) | ★ B8 |
| 6 | LORA_NRST | E22 NRST, 10 kΩ nach 3V3_RF, Open-Drain betreiben | ★ B9 |
| 7 | CAM_TRIG | 1 kΩ → J_CAM (JST-GH 3) | |
| 8 | MOT_FAULT | DRV8833 nFAULT, 10 kΩ nach 3V3 | |
| 9 | SERVO_CHUTE | J_SERVO3 (VSERVO) | ★ E4 |
| 10 | SERVO_LEGS | J_SERVO4 (VSERVO), Landebeine | ★ E5 |
| 11 | MOT_NSLEEP | DRV8833 nSLEEP (interner Pull-down: Motor aus beim Booten) | ★ C1 |
| 12 / 14 | PYRO3_FIRE / PYRO4_FIRE | Gate Pyro 3 / 4 (DNP) | ★ E5 |
| 13 | PWM_EXT | J_STACK Pin 18 | ★ E10 |
| 15 | NRST_EXT | J_STACK Pin 20 (Open-Drain) | ★ E10 |
| 16 | frei | – | Reserve |
| 17 | IRQ_EXT | J_STACK Pin 13 | ★ E10 |
| 18 / 19 | SDA0 / SCL0 | J_QWIIC und J_STACK, 4,7 kΩ Pull-ups; kein Flugsensor | ★ E3 |
| 20 / 21 | TX5 / RX5 | J_STACK Pin 17 / 16 (Serial5) | ★ E10 |
| 22 / 23 | PYRO2_FIRE / PYRO1_FIRE | Gate Pyro 2 / 1 über 100 Ω | |
| 24 (A10) | MUX_OUT | 74HC4051 Ausgang (alle langsamen Analogsignale) | ★ |
| 38 / 25 / 30 | SEL0 / SEL1 / SEL2 | Adresse für 74HC138 und 74HC4051 gemeinsam | ★ |
| 31 | CS_EN | 74HC138 Freigabe (aktiv tief, 10 kΩ nach 3V3: beim Booten alle CS hoch) | ★ |
| 26 / 27 / 39 | MOSI1 / SCK1 / MISO1 | IMU, BMP390, BMP390 (DNP), INA239, J_STACK; `SPI1.setMISO(39)` | ★ E3 |
| 28 / 29 | SERVO_YAW / SERVO_PITCH | J_SERVO1 / J_SERVO2 (VSERVO) | |
| 32 / 33 | LORA_M1 / LORA_M0 | E22 Betriebsart (00 = Normal, 11 = Konfiguration) | |
| 34 / 35 | RX8 / TX8 | E22 TXD / RXD | |
| 36 | LORA_AUX | E22 AUX (Sendepuffer frei, Modul bereit) | |
| 37 | BUZZER | AO3400A → aktiver 5-V-Summer | ★ B7 (war 13) |
| 40, 41 | frei | – | Reserve |

**Chip-Selects (74HC138, Y0 bis Y7):** Y0 IMU, Y1 BMP390, Y2 BMP390 Nr. 2 (DNP), Y3 INA239,
Y4 bis Y6 CS_EXT0 bis 2 an J_STACK, Y7 frei. Die Firmware setzt die Adresse an SEL0 bis 2 und zieht
dann CS_EN auf tief; zwischen zwei Transfers bleibt CS_EN hoch.

**Analogmux (74HC4051, Kanal 0 bis 7):** 0 bis 3 PYRO1_SENSE bis PYRO4_SENSE, 4 VBAT1_SENSE,
5 VBAT2_SENSE, 6 ARM_SENSE, 7 GND (Nullpunkt). Gelesen wird bei CS_EN hoch, also ohne laufenden
SPI-Transfer. Alle Teiler 100 k / 33 k mit 100 nF am Mux-Eingang, Vollausschlag 13,3 V.

## 5. Pyro-Kanäle

Wie rev A §5: je Kanal ein AO3400A low-side mit 100 Ω Gate-Widerstand und 100 kΩ Pull-down, Plus an
VBAT_ARMED, Durchgangsprüfung über 100 k / 33 k am Drain (über den Analogmux), SMAJ12CA über dem
Ausgang. Vier Kanäle (E5): 1 und 2 bestückt, 3 und 4 nur als Footprint (FET, TVS, Stecker DNP, die
Teiler sind bestückt). Stecker **JST-XH 2-polig** liegend an der Spitzen-Kante, Kabel mit Kabelbinder
gesichert. Firmware: Zünden nur im Zustand *Apogäum* bzw. *Landung*, Puls **50 bis 100 ms** mit Abbruch,
sobald der Durchgang weg ist (A4), jeder Kanal höchstens einmal, ohne ARM_SENSE keine Freigabe,
Durchgang vor dem Start per Summer gemeldet.

## 6. Sensorik und Funk

**ICM-42688-P (LGA-14, 2,5 × 3 mm).** SPI1 mit 7 MHz (bis 24 MHz möglich), VDD und VDDIO an 3V3_SENS,
100 nF + 10 nF an jedem Versorgungspin, INT1 an Pin 4. Betrieb: Gyro ±2000 °/s, Accel ±16 g, ODR
1 kHz, interner Tiefpass (UI-Filter) auf ca. 50 Hz, Firmware mittelt auf die 100-Hz-Schleife.
Bibliothek: `finani/ICM42688` (Arduino, SPI) oder eigener Registertreiber. Kein DMP, keine
Quaternion vom Chip; die Lage entsteht in der Firmware aus dem Gyro (Plan, Befund 3).

**BMP390 (LGA-10, 2 × 2 mm).** SPI1 im 4-Draht-Modus (E3), CS aus dem Decoder (Y1), VDD/VDDIO an
3V3_SENS, Oversampling Druck ×8, Temperatur ×1, IIR-Koeffizient 3, ODR 50 Hz. Bibliothek: Adafruit
`BMP3XX` im SPI-Modus. Ein zweites BMP390 (Y2) ist als DNP-Footprint vorgesehen (Review C2).

**LoRa E22-400T22S (SMD, 16 × 26 mm, SX1268).** VCC an 3V3_RF mit 100 µF, TXD/RXD an Serial8 (3,3-V-Pegel,
keine Widerstände nötig), M0/M1/AUX an Pins 33/32/36, IPEX-Buchse zum Pigtail. Konfiguration
(Adresse, Kanal 433 MHz, 9600 Bd UART, Luftrate 2,4 kbps, 22 dBm) einmalig per M0=M1=1 aus der
Firmware. Die Bodenstation bekommt das DIP-Modul E22-400T22D mit SMA-Antenne.

**INA239 (VSSOP-10)** an SPI1 (CS Y3) mit 20-mΩ-Shunt (2512, 1 %, 1 W). Der Footprint teilt beide
Lötflächen des Shunts in Strom- und Messfläche (Kelvin). Je 10 Ω und 100 nF dazwischen filtern die
Servo-PWM. Nur Telemetrie, nicht in der 100-Hz-Schleife. Bezug DigiKey, Handlötung (bei LCSC nicht
gelistet); Rückfall INA238 (I²C, anderes Pinout).

## 7. Stückliste rev B1

Die vollständige Stückliste mit Werten und Footprints entsteht aus `kicad/circuit.py` (Datenblatt
MS-MB-B, Abschnitt Stückliste). Hier die Bauteile, die man kennen muss. LCSC-Nummern mit „prüfen“ beim
Bestellen verifizieren; Verfügbarkeit bei JLC schwankt.

| Ref | Bauteil | Gehäuse | Anz. | LCSC | Funktion |
|---|---|---|---|---|---|
| A1 (U_TEENSY) | Teensy 4.1 + 2× Buchsenleiste 1×24 | THT | 1 | – | MCU (vorhanden) |
| U4 | TDK ICM-42688-P | LGA-14 | 1 | C1850418 | IMU |
| U5, U15 | Bosch BMP390 | LGA-10 | 1 + 1 DNP | C5124834 | Barometer, zweites als Footprint |
| U6 | TI INA239AIDGSR | VSSOP-10 | 1 | – (DigiKey) | Strom/Spannung VSERVO, SPI, Handlötung |
| R_SH1 | 20 mΩ 1 % 1 W | 2512, Kelvin-Pads | 1 | prüfen | Shunt |
| U2 | TI TPS63070RNMR + 1,5 µH (≥ 4 A) | VQFN-15 | 1 | C109322 | 5V_SYS aus 1S |
| U3, U14 | Diodes AP2112K-3.3 | SOT-23-5 | 2 | C51118 | 3V3_RF, 3V3_EXP |
| U11 | Microchip MCP73831T-2ACI/OT | SOT-23-5 | 1 | C424093 | 1S-Lader 500 mA |
| U7 | TI DRV8833PWPR | HTSSOP-16 | 1 | C50506 | Rollmotor an VSERVO |
| U8 | TI SN74LV1T34DBVR | SOT-23-5 | 1 | prüfen | Pegel 3,3 → 5 V für die WS2812B-Kette |
| U12 | 74HC138PW | TSSOP-16 | 1 | prüfen | SPI-Chip-Selects |
| U13 | 74HC4051PW | TSSOP-16 | 1 | prüfen | Analogmux |
| U10 | Ebyte E22-400T22S | SMD-Modul | 1 | C2903765 | LoRa |
| LED1, LED2 | WS2812B-2020 | 2020 | 2 | C965555 | Status |
| Q1, Q2 | AO3401A | SOT-23 | 2 | C15127 | Verpolschutz 2S / 1S |
| Q6, Q7 | AO3401A | SOT-23 | 2 | C15127 | Lastschalter 2S / 1S (E1) |
| Q3, Q4, Q8, Q9 | AO3400A | SOT-23 | 2 + 2 DNP | C20917 | Pyro 1 bis 4 |
| Q5 | AO3400A | SOT-23 | 1 | C20917 | Summer |
| D1 | SS14 | SMA | 1 | C2480 | VIN-Entkopplung |
| D2, D3, D5, D6 | SMAJ12CA | SMA | 2 + 2 DNP | prüfen | TVS Pyro-Ausgänge |
| F1, F2 | Polyfuse 3 A/6 A, 2 A | 1812 | 2 | prüfen | je Akku hinter dem Verpolschutz |
| FB1 | Ferrit 600 Ω bei 100 MHz | 0603 | 1 | prüfen | 3V3_SENS |
| C4, C5 / C16, C17 | 330 µF/16 V / 470 µF/6,3 V Polymer | 7343 | 2 + 2 | prüfen | Puffer VSERVO / Hold-up TEENSY_VIN |
| BZ1 | aktiver Summer 5 V, 12 mm | THT | 1 | – | Signalgeber |
| J1 (J_BAT2) | XT30PW-M liegend | THT | 1 | prüfen | 2S |
| J2 (J_BAT1) | JST-PH 2 stehend | THT | 1 | prüfen | 1S |
| J3 (J_SW) | JST-PH 4 stehend | THT | 1 | prüfen | Hauptschalter (nur Gates) |
| J17 (J_CHG1) | JST-PH 3 stehend | THT | 1 | prüfen | 1S-Laden: VBUS, GND, Lade-LED |
| J18 (J_CHG2) | JST-PH 2 stehend | THT | 1 | prüfen | 2S-Laden parallel zu J_BAT2 |
| J4 (J_ARM) | JST-XH 2 stehend | THT | 1 | prüfen | Arming, Schlüsselschalter ≥ 5 A |
| J5, J6 | JST-XH 3 liegend (S / + / −) | THT | 2 | prüfen | TVC-Servos |
| J7, J16 | JST-XH 3 stehend (S / + / −) | THT | 2 | prüfen | Servo 3 (Fallschirm), Servo 4 (Beine) |
| J8 (J_MOT) | JST-XH 2 stehend | THT | 1 | prüfen | Rollmotor |
| J9, J10, J19, J20 | JST-XH 2 liegend | THT | 2 + 2 DNP | prüfen | E-Matches |
| J11, J12 | JST-GH 4 / JST-SH 4 | SMD | 1 + 1 | prüfen | GPS, Qwiic |
| J13, J14 | JST-GH 3 | SMD | 1 + 1 | prüfen | Kamera, externe LEDs |
| J15 (J_STACK) | Stiftleiste 2×10, 2,54 mm | THT | 1 | – | Zusatzplatinen (Flachband) |
| JP1, JP2 | Lötbrücke | – | 2 | – | Schalter überbrücken (Tisch) |
| TP1..7 | Testpunkte VBAT_PROT, VSYS_IN, 5V_SYS, VSERVO, 3V3_RF, 3V3_EXP, GND | – | 7 | – | Inbetriebnahme |

Entfallen gegenüber rev B: U1 TPS563201 mit Spule und 470-µF-Elko (E9), INA219 (E3), zweiter
74AHCT1G125 (B8), Polyfuse vor VSERVO (A4), drei THT-Elkos (B3), J_EXP (E10), Testpunkte 5V_SERVO, SDA, SCL.
Dazu die üblichen Abblock- und Teiler-Bauteile (0402/0603) und ein W25Q128 (SOIC-8) unter dem Teensy.

## 8. Layout-Regeln

Die vollständige Prüfliste steht in `docs/Plan_2026-10-21.md` §2.6. Kurzfassung, Stand B1:

- In1 durchgehend GND; B.Cu geteilte Versorgungsfläche (GND_PWR unter allem, was am 2S hängt,
  5V_SYS unter der 1S-Seite). Sternpunkt NT1 der beiden Akku-Massen am 2S-Minus; Servo- und
  Pyro-Rückströme laufen über die GND_PWR-Fläche dorthin, nicht durch die Fläche unter IMU und Barometer.
- 2S-Pfad (VBAT_PROT, VBAT_ARMED, VSERVO) als Kupferflächen auf F.Cu, die der Generator vor dem Routing
  zieht; der Autorouter darf diese Netze nur auf F.Cu verlegen, nie auf In2 (Review A6, B13). Breite
  der Flächen 1,4 bis 4,2 mm, Stichbahnen 1,0 mm. VSYS_IN 0,6 mm, an den VQFN-Pins als Fläche (A7);
  5V_SYS als Fläche auf B.Cu.
- Wandler und Spule im linken Streifen, mindestens 25 mm von der IMU.
  Im Radius 5 mm um die IMU keine fremden Vias und keine Bahnen auf In2 (B16); unter dem Chip gar keine Vias.
- BMP390 weg von Spulen und Teensy-CPU. LoRa-Modul auf einer Massefläche, keine Signale darunter,
  0,5 mm vom Rand (B17).
- Stecker nur oben, verriegelt, Pin 1 und S/+/− im Bestückungsdruck, Steckrichtung axial.
- DRC mit JLC-Regeln (0,127 mm, Via 0,3 mm), 3D-Ansicht gegen die Hüllen aus `outline.py`,
  1:1-Papierausdruck in den Kuppler halten.

## 9. Inbetriebnahme (Testplan)

1. Ohne Teensy, beide Akkupfade am Labornetzteil mit 100 mA Begrenzung, Schalter über JP1/JP2:
   1S-Pfad mit 3,7 V → 5V_SYS, 3V3_RF und 3V3_EXP messen; 2S-Pfad mit 7,4 V → VSERVO messen.
   Verpolung testen. Lastschalter: ohne JP1/JP2 und ohne Schalterbrett muss alles aus sein.
   Beim ersten Einschalten des 1S-Pfads den Anlauf von 5V_SYS mit dem Oszilloskop ansehen: der
   TPS63070 lädt die 940 µF hinter D1 in der Strombegrenzung.
2. Teensy stecken, nur USB: beide Akkuspannungen über den Analogmux; ICM-42688-P (WHO_AM_I = 0x47),
   BMP390 (CHIP_ID = 0x60) und INA239 (Manufacturer-ID 0x5449) über SPI1 und den Decoder.
3. 1S-Akku, Flug-Firmware: Loop-Timing, Teleplot IMU/Baro, beide Akkuspannungen, INA239.
   Lader: USB-C am Schalterbrett, Rakete aus, Ladestrom 500 mA, Lade-LED.
4. 2S-Akku dazu: Servos einzeln bis zum Blockieren, Rollmotor mit begrenztem Tastverhältnis; der Teensy
   darf nicht neu starten (Watchdog-Zähler im Log muss 0 bleiben). Einbruch von VBAT2 und 5V_SYS mit
   dem Oszilloskop.
5. Pyro nur mit Glühlämpchen oder 2-Ω-Widerstand: ohne ARM keine Zündung, ARM_SENSE, Durchgang,
   Pulsdauer 50 bis 100 ms, Abbruch bei Durchgangsverlust. **Nie mit Ladung auf dem Tisch.**
6. LoRa-Strecke zur Bodenstation im Freien (Reichweite, Paketverlust), GPS-Fix in der Spitze.

Hinweis (B11): Die VIN-VUSB-Brücke auf dem Teensy bleibt geschlossen. D1 trennt 5V_SYS vom USB.

## 10. Firmware-Änderungen für rev B1

- `Config.h`: Pins nach §4 (`PIN_LED_DATA 5`, `PIN_LORA_NRST 6`, `PIN_SERVO_LEGS 10`, `PIN_MOT_NSLEEP 11`,
  Pyro 3/4 auf 12/14, `PIN_BUZZER 37`, `PIN_MUX 24`, `PIN_SEL0..2 38/25/30`, `PIN_CS_EN 31`), `INA_SHUNT_OHM = 0.02`,
  Akkugrenzen, `SERVO_PULSE_*` für die W5652H, `ROLL_PWM_MAX` (etwa 60 %, 5 V aus 8,4 V).
- Neu: Chip-Select über den 74HC138 (Adresse setzen, dann CS_EN tief) und Analogeingänge über den 74HC4051
  (nur bei CS_EN hoch umschalten, 10 µs Einschwingzeit).
- `Sensors.cpp`: Treiber ICM-42688-P über SPI1, ohne DMP; Gyro-Quaternion und Oben-Vektor für den
  Regler (Plan, Befund 3); BMP390 über `BMP3XX` im SPI-Modus; INA239 über SPI, außerhalb der 100-Hz-Schleife.
- Neu `Radio.cpp`: E22-Konfiguration über M0/M1, NRST bei hängendem Modul, Telemetrieprotokoll mit
  AUX-Flusskontrolle.
- Neu `FlightState.cpp`: Pad → Boost → Coast → Apogäum → Bergung → Landung, Pyro-Logik mit Arming,
  Zündpuls 50 bis 100 ms mit Abbruch bei Durchgangsverlust.
- Watchdog (WDT1 des i.MX RT) und Zustandsspeicher im EEPROM-Emulat, damit ein Neustart im Flug
  in der laufenden Phase weitermacht.
- Rampenkalibrierung des Gyro-Bias (Befund 5).

## 11. KiCad-Projekt und Tor-1-Prüfung

Seit dem 21.10.2026 liegt die Schaltung als KiCad-Projekt in `kicad/` (Schaltplan und Platine aus
`circuit.py`, siehe `kicad/README.md`). Abweichungen von dieser Spezifikation, die das Projekt
begründet trifft, stehen dort in §6. `kicad/check_design.py` prüft die Netzliste gegen §4 dieser Datei
(Teensy-Pins, Chip-Selects, Mux-Kanäle, Schienen, Kelvin-Abgriff). Die Prüfung von rev B steht in
`review_netlist_2026-10-21.md`, das Zweitmeinung-Review in `review_kicad_2026-10-21.md`; beide sind in
B1 eingearbeitet (§0).

## 12. Offen

- Lage der TVC-Servoachsen zum Schlitten (Achsentausch in der Firmware). Der Kardan wird für die
  W5652H neu konstruiert (`cad/`), dabei festlegen.
- Länge der Avionik-Sektion: Schlitten 120 mm plus Endringe im 150-mm-Kuppler. Passt, wenn die
  Endringe ≤ 15 mm hoch sind.
- Schalterbrett an Luke B (Schiebeschalter, USB-C mit CC-Widerständen 5,1 kΩ, Lade-LED mit Vorwiderstand,
  XT30- und XH-3-Ladebuchse): Platine oder gedruckt, Kabel zu J_SW, J_CHG1 und J_CHG2 (`cad/README.md`).
- Kamera: 3,3 V oder 5 V am Auslöser.
- TPS63070 bei JLC verfügbar? Sonst TPS63020.
- INA239 bei DigiKey bestellen (Handlötung); ICM-42688-P am Bestelltag auf TDK prüfen (LCSC C1850418).
