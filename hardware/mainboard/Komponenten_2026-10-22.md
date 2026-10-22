# Mainboard rev B – Bauteile nach Spannung und Schnittstelle

Stand 2026-10-22. Übersicht aller Verbraucher und Signale des Mainboards: welche Schiene sie
versorgt, über welche Schnittstelle sie am Teensy hängen und was sich mit den Entscheidungen vom
22.10.2026 ändert. Grundlage: Spezifikation `README.md` (rev B), `kicad/circuit.py` (Stand 21.10.),
Review `review_kicad_2026-10-21.md`. Spalte **Änderung** zeigt den Zielzustand nach dieser Runde;
„bleibt“ heißt wie heute im KiCad-Projekt.

## 1. Entscheidungen vom 22.10.2026 (Jan)

| Nr. | Entscheidung | Folge |
|---|---|---|
| E1 | **Hauptschalter mechanisch** (Review A3): der Schalter am Rumpf bleibt, aber er schaltet nur noch das Gate eines P-FET-Lastschalters je Akku. Der Akkustrom bleibt auf der Platine. | Zwei AO3401A anti-seriell zu Q1/Q2, vier Widerstände; `J_SW` führt nur noch Mikroampere, jeder Mini-Schiebeschalter taugt. Von außen weiter ein mechanischer Schalter. |
| E2 | **Akkus bleiben beim Laden in der Rakete.** | 1S: USB-C-Lader auf der Platine (BQ24075 oder MCP73831, 500 mA), Buchse an der Luke. 2S: Ladebuchse am Rumpf (XT30 + JST-XH-3-Balancer, parallel zu `J_BAT2`) für den Modellbaulader; ein 2S-Balancer-Lader auf der Platine lohnt nicht. Beide Ladeanschlüsse liegen **vor** dem Lastschalter, laden also bei ausgeschalteter Rakete. §4. |
| E3 | **SPI, wo es den Sensor mit SPI gibt** (Review B6, Jans Frage). | BMP390 an SPI1 mit eigenem CS; INA219 (nur I²C) durch **INA239** (SPI) ersetzen; I²C bleibt nur für `J_QWIIC`. §3. |
| E4 | **Servos direkt am 2S-Akku**, nicht an 5 V (Reaktionszeit). | TVC-Servos sind schon an `VSERVO`. Zusätzlich: `J_SERVO3` (Fallschirm/Reserve) und ein vierter Stecker ebenfalls an `VSERVO`. Die 5-V-Schiene `5V_SERVO` versorgt dann nur noch den Rollmotor (DRV8833). |
| E5 | **Zukunftsfähigkeit vor Kosten** (Review C1). | Vier Pyro-Kanäle (3 und 4 als DNP), vierter Servo-Stecker, DRV8833 `nSLEEP` an einen Teensy-Pin, zweiter BMP390 als DNP-Footprint, `J_EXP` mit vollständigem SPI0 (Summer von Pin 13 auf 37), E22-NRST an einen Pin. |
| E6 | **Motor bleibt TSP E12** (vier vorhanden). Ziel ist Stabilisierung und Landung, nicht Höhe. Masse senken: Platine statt Breakouts, Verbundrohr statt Papprohr prüfen. | Beschleunigungsbereich ±16 g des ICM-42688-P reicht ohnehin. Massenmodell `cad/` nachziehen, sobald das Rohr entschieden ist. |
| E7 | **Reihenfolge: erst die Platine**, Firmware parallel nur dort, wo das Design keine Rolle spielt. | Design-unabhängig: Flugzustandsautomat, Gyro-Quaternion, Watchdog und Zustandsspeicher, Telemetrieprotokoll. Design-abhängig (warten): Pinbelegung, Treiber ICM/BMP/INA über SPI, Lader-Status, Pyro-Kanäle 3/4. |
| E8 | **Kollegen-Review** hat keine Eile. Repo und Doku werden mit dem Hardwarestand synchron gehalten. | Review B15 (lesbarer Schaltplan) bleibt sinnvoll, aber ohne Termin. |

## 2. Spannungsschienen

| Schiene | Quelle | Bereich | Versorgt | Änderung 22.10. |
|---|---|---|---|---|
| `VBAT1` / `VSYS_IN` | 1S LiPo, `J_BAT1` (JST-PH 2) → Q2 Verpolschutz → Sicherung 2 A → **FET-Lastschalter** | 3,0 – 4,2 V | TPS63070, Teiler Pin 41 | Sicherung (A4), FET-Schalter (E1), USB-C-Lader davor (E2), EN-Teiler 330 k / 115 k (A2) |
| `5V_SYS` | U2 TPS63070 Buck-Boost | 5,0 V, 2 A | WS2812B (2×, Kette), Summer, U3 LDO, über D1 Teensy VIN | Hinter D1 1000 µF Hold-up, am Reglerausgang ≤ 300 µF (A1); Elkos als Polymer 7343 (B3) |
| `TEENSY_VIN` | `5V_SYS` über D1 SS14 | 4,6 V | Teensy 4.1 (eigener 3,3-V-LDO, 250 mA frei) | Hold-up-Elko hierhin (A1) |
| `3V3` | Teensy-LDO | 3,3 V, ≤ 250 mA | `3V3_SENS` (Ferrit + 10 µF, B4): ICM-42688-P, BMP390 (1 + DNP 2), INA239-Logik; Pull-ups `J_QWIIC`; `J_EXP` | Sensor-Insel neu (B4) |
| `3V3_RF` | U3 AP2112K-3.3 aus `5V_SYS` | 3,3 V, 600 mA | LoRa E22-400T22S (110 mA Sendepuls), GPS an `J_GPS` | bleibt |
| `VBAT2` / `VBAT_PROT` | 2S LiPo, `J_BAT2` (XT30) → Q1 Verpolschutz → Sicherung 3 A/6 A → **FET-Lastschalter** | 6,0 – 8,4 V | Shunt → `VBAT_MEAS`; `J_ARM` → `VBAT_ARMED`; Teiler Pin 40 | Sicherung (A4), FET-Schalter (E1), Ladebuchse mit Balancer davor (E2); Stromnetze nur auf den Außenlagen als Flächen (A6, B13) |
| `VBAT_ARMED` | `VBAT_PROT` über `J_ARM` (JST-XH 2, Schlüsselschalter) | 6,0 – 8,4 V | Pyro 1 – 4 (+), TVS, Teiler Pin 24 | Vier Kanäle (E5); `J_ARM` als XH, Schalter ≥ 5 A (A3) |
| `VSERVO` | `VBAT_MEAS` über F1 (kann entfallen, A4) | 6,0 – 8,4 V, Akku direkt | **J_SERVO1 Yaw, J_SERVO2 Pitch, J_SERVO3 Fallschirm/Reserve, J_SERVO4 Beine** (alle W5652H-Klasse) | J_SERVO3 und J_SERVO4 hierher (E4, E5); 2 × 330 µF Polymer |
| `5V_SERVO` | U1 TPS563201 Buck aus `VBAT_MEAS` | 5,0 V, 3 A | **nur noch DRV8833 (Rollmotor)** | Servo-Stecker weg von dieser Schiene (E4); Mindestbreite 0,4 mm (A8). Falls der Rollmotor 2S verträgt (DRV8833 bis 10,8 V), kann U1 später entfallen: als Lötbrücke `5V_SERVO`/`VSERVO` am DRV8833 vorsehen. |
| `GND` / `GND_PWR` | Sternpunkt am 2S-Minus neben dem Shunt (NT1) | – | Logik / Aktoren und Pyro | bleibt |

## 3. Bauteile nach Schnittstelle

### 3.1 SPI1 (Pins 26 MOSI1, 27 SCK1, 39 MISO1; ein CS je Gerät)

| Bauteil | Funktion | Versorgung | CS / INT | Takt | Änderung 22.10. |
|---|---|---|---|---|---|
| U4 ICM-42688-P | IMU, Gyro ±2000 °/s, Accel ±16 g, 1 kHz | `3V3_SENS` | CS Pin 38, INT1 Pin 4 | 7 MHz (bis 24) | bleibt |
| U5 BMP390 | Barometer, Apogäum | `3V3_SENS` | CS Pin 25 | ≤ 10 MHz | **von I²C nach SPI** (B6, E3); SDO wird MISO, SDI MOSI, CSB an Pin 25 |
| U5b BMP390 (DNP) | zweites Barometer, Plausibilität | `3V3_SENS` | CS Pin 30 | | **neu als Footprint** (C2, E5) |
| U6 INA239 | Strom/Spannung 2S-Pfad, 20 mΩ Kelvin-Shunt, 16 bit | `3V3_SENS` (VS), misst `VBAT_PROT` bis 85 V | CS Pin 31, ALERT frei | ≤ 10 MHz | **statt INA219** (E3). Nicht in der 100-Hz-Schleife lesen, nur Telemetrie (B6). Sense-Netze über NetTie (A5). |

Hinweis: Mehr als zwei Geräte an einem SPI-Bus sind unkritisch, solange die Leitungen kurz bleiben
(alle drei sitzen rechts neben dem Teensy). Ein hängender SPI-Slave blockiert die anderen nicht,
das ist der Grund für E3.

### 3.2 I²C (Wire, Pins 18 SDA0, 19 SCL0, 4,7 kΩ nach `3V3`)

| Bauteil | Funktion | Versorgung | Adresse | Änderung 22.10. |
|---|---|---|---|---|
| `J_QWIIC` (JST-SH 4) | Erweiterung: ToF/Lidar für die Landung, Magnetometer, Display | `3V3` | frei | bleibt; der Bus trägt nach E3 **kein Flugsensor** mehr, ein hängendes Zubehör stört den Regler nicht |
| ~~BMP390~~, ~~INA219~~ | | | | nach SPI (E3) |

### 3.3 UART

| Bauteil | Serial | Pins | Versorgung | Pegel | Zusatzsignale | Änderung 22.10. |
|---|---|---|---|---|---|---|
| U10 E22-400T22S LoRa | Serial8 | 34 RX8, 35 TX8 | `3V3_RF` | 3,3 V | M0 Pin 33, M1 Pin 32, AUX Pin 36, **NRST Pin 37 → verschoben, siehe Summer** | NRST an Teensy-Pin mit 10 k Pull-up (B9) |
| GPS u-blox M9/M10 an `J_GPS` (JST-GH 4) | Serial1 | 0 RX1, 1 TX1 | `3V3_RF` | 3,3 V | – | bleibt; Modul in der Spitze |
| `J_EXP`: Serial3 (14/15), Serial4 (16/17) | | | `3V3` | 3,3 V | | frei (B7) |

### 3.4 PWM und Digital-Ausgänge

| Bauteil | Pin | Versorgung des Verbrauchers | Signalpegel | Änderung 22.10. |
|---|---|---|---|---|
| J_SERVO1 Yaw (W5652H) | 28 | `VSERVO` 6,0 – 8,4 V | 3,3 V PWM über 220 Ω | bleibt |
| J_SERVO2 Pitch (W5652H) | 29 | `VSERVO` | 3,3 V PWM | bleibt |
| J_SERVO3 Fallschirm / Reserve | 9 | **`VSERVO`** (war `5V_SERVO`) | 3,3 V PWM | E4 |
| J_SERVO4 Landebeine | 10 | **`VSERVO`** | 3,3 V PWM | neu (E5); Pin 10 von `J_EXP` |
| U7 DRV8833 Rollmotor, IN1/IN2 | 2 / 3 | `5V_SERVO` (Motorspannung), `VINT` intern | 3,3 V, 20 kHz PWM | nSLEEP an **Pin 11** statt fest an `5V_SERVO` (C1); nFAULT Pin 8 bleibt |
| Q_P1 … Q_P4 Pyro-Kanäle, Gate | 23, 22, **12, 14** | `VBAT_ARMED` | 3,3 V, Puls 50 – 100 ms | Kanäle 3/4 neu, DNP (E5); Pulsdauer kürzer (A4) |
| LED1 → LED2 WS2812B (Kette) → `J_LED` | 5 | `5V_SYS` | 3,3 → 5 V über einen SN74LV1T34 | eine Kette, ein Pegelwandler (B8); Pin 6 frei |
| BZ1 Summer über Q_BZ | **37** (war 13) | `5V_SYS` | 3,3 V Gate | B7: SPI0 auf `J_EXP` frei. E22-NRST dann auf **Pin 6** (durch B8 frei). |
| `J_CAM` Kameraauslöser | 7 | 3,3 V oder 5 V (offen, README §12) | 1 kΩ | bleibt |

### 3.5 Analog-Eingänge (Teiler 100 k / 33 k, Vollausschlag 13,3 V)

| Signal | Pin | Misst | Änderung 22.10. |
|---|---|---|---|
| VBAT1_SENSE | 41 (A17) | 1S vor dem Lastschalter | bleibt |
| VBAT2_SENSE | 40 (A16) | 2S vor dem Lastschalter | bleibt |
| ARM_SENSE | 24 (A10) | `VBAT_ARMED` | bleibt |
| PYRO1_SENSE … PYRO4_SENSE | 20, 21, **15, 16** | Drain je Kanal (Durchgang der E-Match) | Kanäle 3/4 neu (E5) |
| ~~CHG_STAT~~ | – | entfällt (§7.1): der Lader zeigt den Zustand mit einer LED an der Luke | – |

### 3.6 Ohne Teensy-Anschluss (reine Versorgung)

| Bauteil | Schiene | Funktion |
|---|---|---|
| U2 TPS63070 | `VSYS_IN` → `5V_SYS` | Buck-Boost 1S → 5 V; EN-Teiler 330 k / 115 k (A2), FB2 offen, VSEL GND |
| U1 TPS563201 | `VBAT_MEAS` → `5V_SERVO` | Buck 2S → 5 V, nur Rollmotor |
| U3 AP2112K-3.3 | `5V_SYS` → `3V3_RF` | LDO Funk und GPS |
| U11 MCP73831T-2ACI/OT (neu) | USB-C → `VBAT1` | 1S-Lader 500 mA (R_PROG 2 kΩ), STAT → LED an der Luke; Lader hängt vor dem Lastschalter, lädt nur bei Aus (§7.3) |
| Q1, Q2 AO3401A | Akku-Eingänge | Verpolschutz; 1S-Pfad auf einen bei −2,5 V spezifizierten Typ prüfen (B5) |
| Q3, Q4 AO3401A (neu) | hinter Q1/Q2 | Lastschalter, Gate über 100 k an Source und über `J_SW` auf GND (E1) |
| F_BAT1 2 A, F_BAT2 3 A/6 A (neu) | je Akku | Polyfuse 1812 direkt hinter dem Verpolschutz (A4) |
| D1 SS14 | `5V_SYS` → `TEENSY_VIN` | USB und Akku gleichzeitig; Brücke auf dem Teensy nicht trennen (B11) |
| D_TVS SMBJ12CA (4×) | Pyro-Ausgänge | Schutz |
| W25Q128 | `3V3` | Flash unter dem Teensy (SPI0 oder QSPI-Pads des Teensy, wie bisher) |

## 4. Laden in der Rakete (E2)

```
USB-C (Luke) ─ U11 BQ24075 ─────────────┐
1S LiPo ─ J_BAT1 ─ Q2 Verpol ─ F_BAT1 ──┴─ Q4 Lastschalter ─ VSYS_IN ─ TPS63070 …
                                         └─ Teiler → Pin 41 (VBAT1_SENSE, auch beim Laden)

Ladebuchse 2S (Luke): XT30 + JST-XH 3 Balancer ─┐
2S LiPo ─ J_BAT2 ─ Q1 Verpol ─ F_BAT2 ──────────┴─ Q3 Lastschalter ─ VBAT_PROT ─ Shunt …
```

- Beide Lader greifen **vor** dem Lastschalter an: Laden bei ausgeschalteter Rakete, keine Rückspeisung
  in die Wandler. Die Teiler an Pin 40/41 liegen ebenfalls vor dem Schalter, der Teensy kann also
  am USB hängend beide Akkuspannungen sehen.
- Der 1S-Lader sitzt auf der Platine, weil 1S-Laden ohne Balancer trivial ist (BQ24075: 4,2 V, 500 mA
  aus USB, Thermistor-Eingang frei). Ein 2S-Balancer-Lader auf der Platine braucht Boost und zwei
  Zellenmessungen; dafür genügt eine Buchse zum Modellbaulader.
- Die Ladebuchse für den 2S liegt parallel zu `J_BAT2` auf der Platine (XT30 am Spitzen-Ende, XH-3
  Balancer daneben) und wird mit zwei Kabeln an die Luke geführt. Kein Strom bei Nichtgebrauch, kein
  Ladestrom über den Shunt.
- USB-C am Teensy (Micro-B) bleibt für Programmierung und Logs; der USB-C des Laders ist ein
  zweiter Port an der Luke, nur Power (CC1/CC2 je 5,1 k nach GND).

Alternative, falls die Luke zu klein wird: der XT30-Ladeanschluss und der USB-C-Lader entfallen,
statt dessen eine **Buchse am Rumpf mit beiden Akkus** (JST-XH 2+3 und JST-PH 2) und der Lader
bleibt extern. Dann ist E2 nur Verkabelung. Entscheidung beim Platzieren.

## 5. Pin-Belegung nach dieser Runde (Teensy 4.1)

| Pin | Signal | Status |
|---|---|---|
| 0 / 1 | RX1 / TX1 GPS | bleibt |
| 2 / 3 | MOT_IN1 / MOT_IN2 | bleibt |
| 4 | IMU_INT | bleibt |
| 5 | LED_DATA (Kette LED1 → LED2 → J_LED) | B8, war LED1 |
| 6 | LORA_NRST | neu (B9), war LED2 |
| 7 | CAM_TRIG | bleibt |
| 8 | MOT_FAULT | bleibt |
| 9 | SERVO_CHUTE (VSERVO) | E4 |
| 10 | SERVO4 Landebeine (VSERVO) | neu (E5) |
| 11 | MOT_nSLEEP | neu (C1) |
| 12 | PYRO3_FIRE | neu, DNP (E5) |
| 13 | frei (SCK0 für `J_EXP`) | B7 |
| 14 | PYRO4_FIRE | neu, DNP (E5) |
| 15 (A1) | PYRO3_SENSE | neu, DNP |
| 16 (A2) | PYRO4_SENSE | neu, DNP |
| 17 (A3) | frei, auf `J_EXP` | §7.1 |
| 18 / 19 | SDA0 / SCL0 nur `J_QWIIC` | E3 |
| 20 / 21 | PYRO1_SENSE / PYRO2_SENSE | bleibt |
| 22 / 23 | PYRO2_FIRE / PYRO1_FIRE | bleibt |
| 24 (A10) | ARM_SENSE | bleibt |
| 25 | BARO_CS | neu (B6) |
| 26 / 27 / 39 | MOSI1 / SCK1 / MISO1 | bleibt |
| 28 / 29 | SERVO_YAW / SERVO_PITCH | bleibt |
| 30 | BARO2_CS (DNP) | neu (C2) |
| 31 | INA_CS | neu (E3) |
| 32 / 33 | LORA_M1 / LORA_M0 | bleibt |
| 34 / 35 | RX8 / TX8 LoRa | bleibt |
| 36 | LORA_AUX | bleibt |
| 37 | BUZZER | B7, war 13 |
| 38 | IMU_CS | bleibt |
| 40 / 41 | VBAT2_SENSE / VBAT1_SENSE | bleibt |
| `J_EXP` | 1×4: 13 (SCK0), 17 (A3), 3V3, GND | verkleinert, §7.1 |

**Konflikt `J_EXP` (B7 gegen E5), aufgelöst in §7.1:** Vier Pyro-Kanäle, nSLEEP, Servo 4 und die drei
neuen CS-Pins verbrauchen die bisher freien Pins 10 bis 16, 25, 30, 31 und 37. Die Unterseitenpads des
Teensy (48 bis 54) sind bei gestecktem Modul nicht nutzbar. Erweiterungen laufen über `J_QWIIC` (I²C).

## 6. Was die Firmware daraus lernt (`Config.h`, design-abhängig, wartet auf die Platine)

- `PIN_BUZZER 37`, `PIN_LED_DATA 5` (eine Kette, 2 + n Pixel), `PIN_LORA_NRST 6`,
  `PIN_BARO_CS 25`, `PIN_INA_CS 31`, `PIN_MOT_NSLEEP 11`, `PIN_SERVO_LEGS 10`, Pyro 3/4.
- Treiber: ICM-42688-P (SPI, vorhanden geplant), BMP390 über `BMP3XX` im SPI-Modus, INA239 über
  `INA239` (TI-Registerkarte, 16-bit Shunt, `SHUNT_CAL` aus 20 mΩ).
- `INA_SHUNT_OHM 0.02`, Servo-Pulsgrenzen W5652H, Pyro-Puls 50 – 100 ms mit Abschaltung bei
  Durchgangsverlust (A4).

Design-unabhängig und jetzt schon möglich (E7): Flugzustandsautomat, Gyro-Quaternion mit Oben-Vektor,
Watchdog und Zustandsspeicher, Telemetrieprotokoll mit AUX-Flusskontrolle, Rampenkalibrierung.

## 7. Designlücken, geklärt am 22.10.2026

1. **`J_EXP`-Konflikt (§5): Erweiterungsleiste wird kleiner, keine Unterseitenpads.** Der Teensy 4.1
   hat nur sieben Unterseitenpads (48 bis 54, [PJRC](https://www.pjrc.com/store/teensy41.html)); 42 bis 47
   gehören dem SD-Sockel. Die Pads liegen unter dem gesteckten Modul und sind von der Platine aus nicht
   erreichbar. Deshalb: `CHG_STAT` entfällt (Pin 17 frei, der Lader zeigt den Zustand mit einer LED an der
   Luke), `J_EXP` wird eine 1×4 mit **13 (SCK0), 17 (A3), 3V3, GND** plus `J_QWIIC` (I²C). Künftige
   Landesensoren (VL53L1X-ToF, TF-Luna) sind I²C und hängen an `J_QWIIC`; ein zweiter UART ist nicht
   nötig, Serial1 (GPS) und Serial8 (LoRa) reichen. Pyro 3/4, nSLEEP, Servo 4 und die drei CS-Pins
   bleiben wie in §5.
2. **INA239 bleibt gesetzt, Beschaffung über Mouser/DigiKey.** Bei LCSC war nur der I²C-Bruder
   INA237 (C2864837) gelistet, ohne Bestand; eine LCSC-Nummer für den INA239AIDGSR gibt es nach der
   Suche nicht. Der VSSOP-10 lässt sich von Hand löten (0,5 mm Raster), JLC bestückt ihn also nicht,
   das ist bei einem Bauteil vertretbar. Bezug: [DigiKey 296-INA239AIDGSRTR-ND](https://www.digikey.com/en/products/detail/texas-instruments/INA239AIDGSR/15857275),
   ca. 2 €. Rückfall, falls ausverkauft: INA238 (I²C, gleiches Gehäuse, **anderes Pinout**, kein
   gemeinsamer Footprint) an `J_QWIIC`-Bus; die Firmware kapselt die Strommessung in einer Klasse,
   damit der Tausch eine Datei bleibt.
3. **1S-Lader: MCP73831T-2ACI/OT** (SOT-23-5, LCSC [C424093](https://jlcpcb.com/partdetail/MicrochipTech-MCP73831T_2ACIOT/C424093),
   ca. 0,75 USD, 10 k auf Lager). Ladestrom 500 mA über R_PROG 2 kΩ, STAT an eine LED, kein Teensy-Pin.
   Der BQ24075 (VQFN-16, Power-Path) ist für „laden bei ausgeschalteter Rakete“ zu viel.
4. **Rollmotor: TPS563201 bleibt, Lötbrücke `5V_SERVO`/`VSERVO` am DRV8833 vorsehen.** Die
   Nennspannung des Motors ist nicht dokumentiert (BUILD.md Inventar); bis sie gemessen ist, läuft er an
   5 V. Der DRV8833 selbst verträgt 2S (2,7 bis 10,8 V).
5. **Rohrmaterial (E6): Pappe bleibt**, Ergebnis in `docs/Rohrmaterial_2026-10-22.md`. Käufliche
   Verbundrohre mit 75 mm sind 3- bis 4-mal schwerer als das Klima-Rohr. Masse kommt aus kürzerem Rohr,
   Erstflug ohne Landesystem und Platine statt Breakouts; selbst laminieren nur als letzter Schritt.
6. **Luke: in die CAD-Session.** An der Luke liegen Teensy-USB, SD, Hauptschalter, Arming, USB-C-Lader
   mit LED und die 2S-Ladebuchse (XT30 + XH-3). Vorschlag: zwei Luken im Kuppler, eine auf der
   Teensy-Seite (USB, SD, Program-Taster), eine gegenüber (Schalter, Arming, Laden); `cad/` prüft den
   Platz zwischen den M2-Stangen.
