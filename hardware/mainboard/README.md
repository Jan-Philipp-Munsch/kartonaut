# Mainboard rev B – Spezifikation

Stand 2026-10-21. Rev B ersetzt rev A (`rev_a_2026-10-15.md`, dort stehen die Begründungen,
die hier unverändert gelten). Die Planungsrunde vom 21.10.2026 (`docs/Plan_2026-10-21.md`, §2)
hat die Sensorik, den Funk, die Servos und vor allem die Versorgung neu entschieden. Ziel bleibt:
ein Board, das den Teensy 4.1 trägt und alles enthält, was heute als Breakout mit Dupont-Kabeln
am Teensy hängt. Schaltplan und Layout gibt es noch nicht; das ist die Vorgabe für KiCad.

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
- **Barometer** oben im rechten Streifen (v ≈ 80), Schaum darüber, 3 bis 4 Bohrungen Ø 2 mm im Rohr
  auf dieser Höhe. Die Avionik-Sektion ist gegen den Fallschirmraum dicht (Ausstoßdruck).
- **Funk** im linken Streifen am Spitzen-Ende, IPEX-Buchse zeigt zur Spitze, Pigtail (10 cm) zu einer
  λ/4-Antenne (17 cm Draht oder Stab) in der Klima-Spitze, frei von Kupfer und Akku.
- **GPS** nicht auf dem Board: Modul (u-blox M9/M10) in der Spitze, Patchantenne nach oben,
  mindestens 10 cm von der LoRa-Antenne, Kabel über J_GPS.

## 3. Stromversorgung

```
1S LiPo (3,0–4,2 V) ─ J_BAT1 (JST-PH 2) ─ Q2 Verpolschutz AO3401A ─ SW1a (J_SW) ─ VSYS_IN
   ├─ 100 k / 33 k → Pin 41 (VBAT1_SENSE)
   └─ U2 TPS63070 Buck-Boost (2–16 V ein, 5 V / 2 A, 1,5 µH) → 5V_SYS, 1000 µF Polymer
         ├─ D1 Schottky SS14 → Teensy VIN (USB darf gleichzeitig stecken)
         ├─ 2× WS2812B über 74AHCT1G125, Summer über AO3400A
         └─ U3 AP2112K-3.3 → 3V3_RF (100 µF): LoRa E22, GPS (J_GPS)
   Teensy 3V3 (≤ 250 mA) → ICM-42688-P, BMP390, INA219, I²C-Pull-ups

2S LiPo (6,0–8,4 V) ─ J_BAT2 (XT30) ─ Q1 Verpolschutz AO3401A ─ SW1b (J_SW) ─ VBAT_PROT
   ├─ 100 k / 33 k → Pin 40 (VBAT2_SENSE)
   ├─ J_ARM (Arming-Schalter) ─ VBAT_ARMED ─ Pyro 1/2 (+), TVS, 100 k / 33 k → Pin 24 (ARM_SENSE)
   └─ R_SHUNT 20 mΩ 2512 (INA219, Kelvin) ─ VBAT_MEAS
         ├─ F1 Polyfuse 3 A → VSERVO (= Akku direkt), 1000 µF Low-ESR: J_SERVO1/2 (W5652H)
         └─ U1 TPS563201 Buck → 5V_SERVO (3 A), 470 µF: J_SERVO3 (Fallschirm, Reserve), DRV8833 (Rollmotor)

GND beider Akkus an einem Sternpunkt am 2S-Minus neben dem Shunt.
```

- **J_SW** ist ein vierpoliger JST-PH für einen zweipoligen Schiebeschalter am Rumpf. Zwei
  Lötbrücken **JP1 (1S)** und **JP2 (2S)** überbrücken ihn auf dem Tisch.
- **TPS63070** statt eines reinen Boosts, weil er 2 bis 16 V nimmt: Ein versehentlich an J_BAT1
  gesteckter 2S-Akku zerstört nichts. Falls JLC ihn nicht bestücken kann: TPS63020 (1,8–5,5 V ein,
  2 A) als 1S-Variante.
- **Pyro** liegt vor dem Shunt, Zündströme laufen nicht durch den INA219. Die Firmware begrenzt den
  Zündpuls auf ≤ 1 s. Bei 20 mΩ Shunt und PGA 320 mV misst der INA219 bis 16 A mit 2 mA Auflösung;
  `INA219_WE::setShuntSizeInOhms(0.02)` (Funktion beim Bibliotheks-Update prüfen).
- **Was die Firmware loggt und meldet:** beide Akkuspannungen (ADC), Strom und Spannung des
  2S-Pfads (INA219), ARM-Zustand. Warnton bei 1S < 3,5 V oder 2S < 6,6 V; kein Start-Freigabeton
  ohne beide Akkus.

**Strombudget**

| Akku / Schiene | Verbraucher | Dauer | Spitze |
|---|---|---|---|
| 1S → 5V_SYS | Teensy 600 MHz 0,1 A, 2× WS2812B 0,12 A, Summer 0,03 A, 3V3_RF 0,15 A | 0,4 A an 5 V (0,6 A aus dem 1S) | 0,8 A (LoRa-Sendepuls 110 mA an 3,3 V plus Summer) |
| 2S → VSERVO | 2× W5652H, Blockierstrom je ca. 1 A bei 8,4 V | 0,2 A | 2 A |
| 2S → 5V_SERVO | Fallschirm-Servo 0,65 A, Rollmotor ca. 1 A | 0,3 A | 1,7 A |
| 2S → Pyro | E-Match 3–5 A für 20 ms | – | 5 A |

Akku-Vorschlag: 1S 450–600 mAh 20 C mit JST-PH (10–12 g), 2S 450–850 mAh 50 C mit XT30 (30–55 g).

## 4. Pinbelegung Teensy 4.1

Alle Pins aus `Config.h` bleiben. ★ = neu gegenüber `Config.h`, ☆ = anders als rev A.

| Pin | Signal | Ziel | Status |
|---|---|---|---|
| 0 / 1 | RX1 / TX1 | GPS (J_GPS, JST-GH 4: 3V3_RF, GND, TX, RX) | ★ |
| 2 / 3 | MOT_IN1 / MOT_IN2 | DRV8833 AIN1=BIN1 / AIN2=BIN2 (Brücken parallel) | wie bisher |
| 4 | IMU_INT | ICM-42688-P INT1 | ★ |
| 5 / 6 | LED1 / LED2 | 74AHCT1G125 → WS2812B auf dem Board und J_LED | wie bisher |
| 7 | CAM_TRIG | 1 kΩ → J_CAM (JST-GH 3) | ★ |
| 8 | MOT_FAULT | DRV8833 nFAULT, 10 kΩ nach 3V3 | ★ (KiCad-Projekt 21.10.2026) |
| 9 | SERVO_CHUTE | J_SERVO3 (5V_SERVO) | wie bisher, Reserve |
| 13 | BUZZER | AO3400A → aktiver 5-V-Summer | wie bisher |
| 18 / 19 | SDA0 / SCL0 | BMP390 (0x77), INA219 (0x40), J_QWIIC | wie bisher, 4,7 kΩ Pull-ups |
| 20 (A6) | PYRO1_SENSE | Teiler am Drain Pyro 1 | ★ |
| 21 (A7) | PYRO2_SENSE | Teiler am Drain Pyro 2 | ★ |
| 22 | PYRO2_FIRE | Gate Q_P2 | ★ |
| 23 | PYRO1_FIRE | Gate Q_P1 | wie `PIN_PYRO1` |
| 24 (A10) | ARM_SENSE | 100 k / 33 k von VBAT_ARMED | ★ ☆ (rev A: 41) |
| 26 / 27 / 39 / 38 | MOSI1 / SCK1 / MISO1 / CS1 | ICM-42688-P SPI, `SPI1.setMISO(39)`, bis 24 MHz | ★ |
| 28 / 29 | SERVO_YAW / SERVO_PITCH | J_SERVO1 / J_SERVO2 (VSERVO) | wie bisher |
| 32 / 33 | LORA_M1 / LORA_M0 | E22 Betriebsart (00 = Normal, 11 = Konfiguration) | ★ ☆ (33 war HC12_SET) |
| 34 / 35 | RX8 / TX8 | E22 TXD / RXD | wie bisher (Serial8) |
| 36 | LORA_AUX | E22 AUX (Sendepuffer frei, Modul bereit) | ★ |
| 40 (A16) | VBAT2_SENSE | 100 k / 33 k von VBAT_PROT (2S) | ★ |
| 41 (A17) | VBAT1_SENSE | 100 k / 33 k von VSYS_IN (1S) | ★ ☆ |
| 10, 11, 12, 14, 15, 16, 17, 25, 30, 31, 37 | frei | J_EXP 2×7 mit 3V3, 5V_SYS, GND | – |

## 5. Pyro-Kanäle

Wie rev A §5: je Kanal ein AO3400A low-side mit 100 Ω Gate-Widerstand und 100 kΩ Pull-down, Plus an
VBAT_ARMED, Durchgangsprüfung über 100 k / 33 k am Drain, SMBJ12A über dem Ausgang. Stecker
**JST-XH 2-polig** statt Schraubklemme, Kabel mit Kabelbinder an der Platine gesichert.
Firmware: Zünden nur im Zustand *Apogäum* bzw. *Landung*, Puls ≤ 1 s, jeder Kanal höchstens einmal,
ohne ARM_SENSE keine Freigabe, Durchgang vor dem Start per Summer gemeldet.

## 6. Sensorik und Funk

**ICM-42688-P (LGA-14, 2,5 × 3 mm).** SPI1 mit 7 MHz (bis 24 MHz möglich), VDD und VDDIO an Teensy-3V3,
100 nF + 10 nF an jedem Versorgungspin, INT1 an Pin 4. Betrieb: Gyro ±2000 °/s, Accel ±16 g, ODR
1 kHz, interner Tiefpass (UI-Filter) auf ca. 50 Hz, Firmware mittelt auf die 100-Hz-Schleife.
Bibliothek: `finani/ICM42688` (Arduino, SPI) oder eigener Registertreiber. Kein DMP, keine
Quaternion vom Chip; die Lage entsteht in der Firmware aus dem Gyro (Plan, Befund 3).

**BMP390 (LGA-10, 2 × 2 mm).** I²C 0x77 (SDO an VDDIO), VDD/VDDIO an Teensy-3V3, Oversampling
Druck ×8, Temperatur ×1, IIR-Koeffizient 3, ODR 50 Hz. Bibliothek: Adafruit `BMP3XX`.

**LoRa E22-400T22S (SMD, 16 × 26 mm, SX1268).** VCC an 3V3_RF mit 100 µF, TXD/RXD an Serial8 (3,3-V-Pegel,
keine Widerstände nötig), M0/M1/AUX an Pins 33/32/36, IPEX-Buchse zum Pigtail. Konfiguration
(Adresse, Kanal 433 MHz, 9600 Bd UART, Luftrate 2,4 kbps, 22 dBm) einmalig per M0=M1=1 aus der
Firmware. Die Bodenstation bekommt das DIP-Modul E22-400T22D mit SMA-Antenne.

**INA219 (SOIC-8)** mit 20-mΩ-Shunt (2512, 1 %, 1 W), Kelvin-Anschluss, Adresse 0x40.

## 7. Stückliste rev B (Entwurf)

LCSC-Nummern mit „prüfen“ beim Bestellen verifizieren; Verfügbarkeit bei JLC schwankt.

| Ref | Bauteil | Gehäuse | Anz. | LCSC | Funktion |
|---|---|---|---|---|---|
| U_TEENSY | Teensy 4.1 + 2× Buchsenleiste 1×24 | THT | 1 | – | MCU (vorhanden) |
| U4 | TDK ICM-42688-P | LGA-14 | 1 | C1850418 | IMU |
| U5 | Bosch BMP390 | LGA-10 | 1 | prüfen | Barometer |
| U6 | TI INA219AIDR | SOIC-8 | 1 | prüfen | Strom/Spannung 2S |
| R_SHUNT | 20 mΩ 1 % 1 W | 2512 | 1 | prüfen | Shunt |
| U1 | TI TPS563201DDCR + 2,2 µH (≥ 4 A) | SOT-23-6 | 1 | C116592 | 5V_SERVO |
| U2 | TI TPS63070RNMR + 1,5 µH (≥ 3 A) | VQFN-15 | 1 | prüfen | 5V_SYS aus 1S |
| U3 | Diodes AP2112K-3.3 | SOT-23-5 | 1 | C51118 | 3V3_RF |
| U7 | TI DRV8833PWPR | HTSSOP-16 | 1 | C50506 | Rollmotor |
| U8, U9 | 74AHCT1G125 | SOT-23-5 | 2 | prüfen | Pegel 3,3 → 5 V für WS2812B |
| U10 | Ebyte E22-400T22S | SMD-Modul | 1 | C2903765 | LoRa |
| LED1, LED2 | WS2812B-2020 | 2020 | 2 | prüfen | Status |
| Q1, Q2 | AO3401A | SOT-23 | 2 | C15127 | Verpolschutz 2S / 1S |
| Q_P1, Q_P2, Q_BZ | AO3400A | SOT-23 | 3 | C20917 | Pyro 1/2, Summer |
| D1 | SS14 | SMA | 1 | C2480 | VIN-Entkopplung |
| D_TVS | SMBJ12A | SMB | 2 | prüfen | Pyro-Ausgänge |
| F1 | Polyfuse 3 A | 1812 | 1 | prüfen | VSERVO |
| BZ1 | aktiver Summer 5 V, 12 mm | THT | 1 | – | Signalgeber |
| C_BULK | 1000 µF/10 V Polymer (5V_SYS), 1000 µF/16 V Low-ESR (VSERVO), 470 µF/10 V (5V_SERVO) | Elko stehend ≤ 12 mm | 3 | prüfen | Puffer |
| J_BAT2 | XT30PW-M liegend | THT | 1 | prüfen | 2S |
| J_BAT1 | JST-PH 2 liegend | THT | 1 | prüfen | 1S |
| J_SW | JST-PH 4 | THT | 1 | prüfen | zweipoliger Hauptschalter |
| J_ARM | JST-PH 2 | THT | 1 | prüfen | Arming |
| J_SERVO1..3 | JST-XH 3 liegend (S / + / −) | THT | 3 | prüfen | Servos; Servokabel auf XH umcrimpen |
| J_MOT | JST-PH 2 | THT | 1 | prüfen | Rollmotor |
| J_PYRO1, J_PYRO2 | JST-XH 2 | THT | 2 | prüfen | E-Matches |
| J_GPS, J_QWIIC | JST-GH 4 / JST-SH 4 | SMD | 1+1 | prüfen | GPS, I²C |
| J_CAM, J_LED | JST-GH 3 | SMD | 1+1 | prüfen | Kamera, externe LEDs |
| J_EXP | Stiftleiste 2×7 | THT | 1 | – | freie Pins |
| JP1, JP2 | Lötbrücke | – | 2 | – | Schalter überbrücken (Tisch) |
| TP1..6 | Testpunkte VBAT2, VSYS_IN, 5V_SYS, VSERVO, 5V_SERVO, 3V3_RF | – | 6 | – | Inbetriebnahme |
| ~~SW_RST~~ | Taster 6 × 6 mm | SMD | 0 | – | entfallen (KiCad 21.10.2026): der Teensy 4.1 hat am Sockel keinen Reset-Pin, der Program-Taster auf dem Teensy ist durch die Luke erreichbar |

Dazu die üblichen Abblock- und Teiler-Bauteile (0402/0603) und ein W25Q128 (SOIC-8) unter dem Teensy.

## 8. Layout-Regeln

Die vollständige Prüfliste steht in `docs/Plan_2026-10-21.md` §2.6. Kurzfassung:

- Lage 2 durchgehend GND, Lage 3 Versorgungsflächen. Sternpunkt der beiden Akku-Massen am
  2S-Minus neben dem Shunt; Servo- und Pyro-Rückleitungen als breite Bahn auf Lage 1 dorthin, nicht
  durch die Fläche unter IMU und Barometer.
- VBAT, VSERVO, Pyro 2 mm auf beiden Außenlagen mit ≥ 4 Vias je Übergang; 5V_SYS 0,8 mm; 3V3 0,5 mm.
- Wandler und Spulen im Streifen WANDLER links neben dem Teensy, mindestens 15 mm von der IMU;
  5 mm Freiraum um die IMU auf allen Lagen, ruhige Massefläche darunter.
- BMP390 weg von Spulen und Teensy-CPU. LoRa-Modul auf einer Massefläche, keine Signale darunter.
- Stecker nur oben, verriegelt, Pin 1 und S/+/− im Bestückungsdruck, Steckrichtung axial.
- DRC mit JLC-Regeln (0,127 mm, Via 0,3 mm), 3D-Ansicht gegen die Hüllen aus `outline.py`,
  1:1-Papierausdruck in den Kuppler halten.

## 9. Inbetriebnahme (Testplan)

1. Ohne Teensy, beide Akkupfade am Labornetzteil mit 100 mA Begrenzung: 1S-Pfad mit 3,7 V →
   5V_SYS und 3V3_RF messen; 2S-Pfad mit 7,4 V → VSERVO und 5V_SERVO messen. Verpolung testen.
2. Teensy stecken, nur USB: I²C-Scan findet 0x40 und 0x77; ICM-42688-P per SPI (WHO_AM_I = 0x47).
3. 1S-Akku, Flug-Firmware: Loop-Timing, Teleplot IMU/Baro, beide Akkuspannungen, INA219.
4. 2S-Akku dazu: Servos einzeln bis zum Blockieren, Rollmotor; der Teensy darf nicht neu starten
   (Watchdog-Zähler im Log muss 0 bleiben). Einbruch von VBAT2 und 5V_SYS mit dem Oszilloskop.
5. Pyro nur mit Glühlämpchen oder 2-Ω-Widerstand: ohne ARM keine Zündung, ARM_SENSE, Durchgang,
   Pulsdauer. **Nie mit Ladung auf dem Tisch.**
6. LoRa-Strecke zur Bodenstation im Freien (Reichweite, Paketverlust), GPS-Fix in der Spitze.

## 10. Firmware-Änderungen für rev B

- `Config.h`: neue Pins (§4), `INA_SHUNT_OHM = 0.02`, Akkugrenzen, `SERVO_PULSE_*` für die W5652H.
- `Sensors.cpp`: Treiber ICM-42688-P über SPI1, ohne DMP; Gyro-Quaternion und Oben-Vektor für den
  Regler (Plan, Befund 3); BMP390 über `BMP3XX`; beide Akkuspannungen über ADC.
- Neu `Radio.cpp`: E22-Konfiguration über M0/M1, einfaches Telemetrieprotokoll mit AUX-Flusskontrolle.
- Neu `FlightState.cpp`: Pad → Boost → Coast → Apogäum → Bergung → Landung, Pyro-Logik mit Arming.
- Watchdog (WDT1 des i.MX RT) und Zustandsspeicher im EEPROM-Emulat, damit ein Neustart im Flug
  in der laufenden Phase weitermacht.
- Rampenkalibrierung des Gyro-Bias (Befund 5).

## 11. KiCad-Projekt und Tor-1-Prüfung

Seit dem 21.10.2026 liegt die Schaltung als KiCad-Projekt in `kicad/` (Schaltplan und Platine aus
`circuit.py`, siehe `kicad/README.md`). Abweichungen von dieser Spezifikation, die das Projekt
begründet trifft, stehen dort in §4; die Prüfung der Netzliste gegen §4 dieser Datei steht in
`review_netlist_2026-10-21.md` (Ergebnis: konform; Hinweise zu TPS63070-Doppelpins, FB2, ICM-Hersteller und E22-NRST).

## 12. Offen

- Lage der TVC-Servoachsen zum Schlitten (Achsentausch in der Firmware). Der Kardan wird für die
  W5652H neu konstruiert (`cad/`), dabei festlegen.
- Länge der Avionik-Sektion: Schlitten 120 mm plus Endringe im 150-mm-Kuppler. Passt, wenn die
  Endringe ≤ 15 mm hoch sind.
- Wo genau die Luke im Kuppler und im Rohr sitzt (USB, SD, Reset, Schalter).
- Ob der Fallschirm-Servo-Ausgang bestückt wird oder nur als Footprint bleibt.
- Kamera: 3,3 V oder 5 V am Auslöser.
- TPS63070 bei JLC verfügbar? Sonst TPS63020.
