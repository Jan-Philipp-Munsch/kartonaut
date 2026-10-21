# Mainboard rev A – Spezifikation

Stand 2026-10-15. Ziel: ein einziges Board, das den Teensy 4.1 trägt und alles enthält, was heute
als Breakout mit Dupont-Kabeln am Teensy hängt. Es ist als **Längs-Schlitten** ausgelegt, der im
Rumpf entlang der Rollachse liegt. Das ist die Schaltungs- und Mechanik-Vorgabe für den
KiCad-Entwurf. Schaltplan und Layout gibt es noch nicht.

![Platzierungsplan](mainboard_placement.svg)

`outline.py` erzeugt zwei Dateien:

- `mainboard_outline.dxf`: Edge.Cuts für KiCad, ein Rechteck mit 2 mm Eckradius und 4 M3-Bohrungen.
- `mainboard_placement.svg`: Draufsicht und Querschnitt.

Dabei prüft das Skript, dass alle Bauteil-Hüllen im Rohr bleiben und die M2-Stangen nicht berühren.

Die erste Variante war eine runde Scheibe mit Ø 68 mm im Ring-Stack. Sie ist am 15.10.2026
verworfen worden: Sie bot nur ~36 cm² Fläche, davon 11 cm² unter dem Teensy, und alle Stecker
hätten am Rand gesessen. Der Grund für die Scheibe war, dass die IMU waagerecht und auf der
Achse liegen sollte. Das ist nicht nötig, siehe §2.

## 1. Entwurfsentscheidungen

| Frage | Entscheidung | Grund |
|---|---|---|
| Bauform | Längs-Schlitten 54 × 120 mm, Platinenebene durch die Rollachse | Knapp doppelte Fläche wie die Scheibe. Die Stecker sitzen an den Stirnseiten, wo die Kabel ohnehin hinlaufen: Servos und Rollmotor nach unten zum TVC, Pyro, Funk und GPS nach oben zur Spitze. Die IMU liegt trotzdem genau auf der Achse. |
| Mikrocontroller | Teensy 4.1 bleibt als Modul auf 2× 1×24 Buchsenleisten | Firmware, SDIO-SD-Slot und USB bleiben unverändert. Der i.MX RT1062 ist BGA und für ein Hobby-Board nicht sinnvoll selbst zu bestücken. |
| Sensoren | ICM-20948 und BMP280 als Chips direkt aufs Board, INA219 ebenso | Gleiche Bauteile wie bisher, also gleicher Code. |
| IMU-Bus | ICM-20948 an **SPI1** statt I²C | I²C ist beim ICM-20948 bis 400 kHz spezifiziert. Der DMP-FIFO-Drain kostet daran pro Frame rund 1 ms und damit einen guten Teil der 10-ms-Schleife (Commit „loop time problems“). SPI bis 7 MHz ist etwa 15× schneller. Ein früherer Testsketch (Git-Historie, `sketches/side.cpp` bis Commit `3b152c9`) hatte SPI schon einmal ausprobiert. |
| Pinbelegung | Alle heute benutzten Pins bleiben, wo sie sind | `Config.h` gilt weiter, nur die IMU-Anbindung und neue Funktionen kommen dazu. |
| Versorgung | 2S-LiPo, zwei getrennte 5-V-Buck-Wandler | Servo- und Motor-Stromspitzen sollen den Teensy nicht in den Brownout ziehen. |
| Bergung | Servo-Ausgang **und** 2 Pyro-Kanäle | Der Piston-Ejection-Bulkhead (Joe Barnard, `Space Mission/files`) hat zwei Pyro-Ladungen. |
| Fertigung | JLCPCB, 4 Lagen, 1,6 mm, SMD-Bestückung durch JLC | ICM-20948 (LGA-24, 3×3 mm) und BMP280 (LGA-8, 2×2,5 mm) lassen sich ohne Heißluft und Schablone nicht von Hand löten. Lage 2 als durchgehende Masse. |

## 2. Mechanik

**Maße und Lage**
- **54 × 120 mm, 1,6 mm.** Die Platinenebene geht durch die Rollachse. Koordinaten: u quer (0 auf der Achse), v längs (0 am TVC-Ende).
- **Einbau:** Der Schlitten liegt zwischen zwei Endringen des bestehenden Stacks (Ø 69 mm, `flight_computer.blend`). Die 8 M2-Stangen laufen an den Platinenkanten vorbei. Die Kante bei u = ±27 mm hat 5,7 mm Abstand zur nächsten Stange.
- **Träger:** Die Platine ist mit 4× M3 (bei u = ±23,5, v = 3,5 / 116,5) auf einen gedruckten Träger geschraubt, der zwischen den Endringen sitzt. Der Träger hält den 2S-LiPo (56 × 25,5 × 8 mm) unter der Platine.
- **Bestückung nur oben.** Unten stehen nur THT-Lötstifte (≤ 2 mm), darunter liegt der Akku.
- **Bauhöhe:** Mitten auf der Platine passen über 30 mm. Am Rand (|u| > 25 mm) sind es wegen der Stangen höchstens 5 mm.
- **Hüllen im Querschnitt:** Der größte Radius liegt bei 28,5 mm (HC-12 auf Abstandshalter). Bis Ø 69 mm bleibt also Luft, auch wenn das Rohr innen knapper ausfällt.

**Teensy und IMU**
- Der **Teensy** liegt mittig in Längsrichtung (v = 30 bis 91). Der SD-Slot zeigt zum TVC, USB zur Spitze. Vor beiden bleibt eine Freifläche: 6 mm vor dem SD-Slot, 12 mm für den USB-Stecker. Eine Luke im Rumpf auf Höhe v ≈ 25 bis 100 mm macht beide erreichbar.
- Die **IMU (ICM-20948)** sitzt unter der Teensy-Mitte (u = 0, v = 60,5), also genau auf der Rollachse. Unter dem Teensy ist Platz für maximal ~3 mm Bauhöhe, bei 8,5 mm hohen Buchsenleisten reicht das.

**Wo die Kabel hinlaufen**
- **TVC-Ende:** XT30 und Servo-Stecker (90°-Stiftleisten) liegen flach und zeigen axial nach unten.
- **Spitzen-Ende:** Pyro-Klemmen, HC-12 und GPS. Die Antenne zeigt in die gedruckte Spitze, die kein Funkschatten ist (beim Pappe- oder CFK-Rumpf wichtig).

**Barometer**
- Der BMP280 sitzt oben im rechten Streifen (v ≈ 80). Auf dieser Höhe kommen 3 bis 4 Druckausgleichsbohrungen (Ø 2 mm) gleichmäßig um den Rumpf. Die Avionik-Sektion muss sonst dicht sein.

**IMU-Einbaulage.** Die IMU muss weder waagerecht liegen noch die Schwerkraft „unten“ sehen. Es reicht, dass sie fest sitzt und ihre Lage einmal als fester Achsentausch in der Firmware steht. Der Gyro misst an jedem Punkt eines starren Körpers dieselbe Drehrate. Der Beschleunigungssensor ist ohnehin genau auf der Achse.

Den Chip so drehen, dass seine X-Achse quer liegt (+u) und seine Y-Achse zur Spitze zeigt (+v). Seine Z-Achse steht dann senkrecht auf der Platine. Die Firmware rechnet mit z = Rollachse. Jeder Gyro- und Beschleunigungsvektor wird darum direkt nach dem Lesen umgesetzt:

```cpp
// Chip (X quer, Y zur Spitze, Z aus der Platine) -> Körper (x, y quer, z = Rollachse)
inline Vec3 chipToBody(const Vec3& c) { return Vec3(c.x, -c.z, c.y); }   // rechtshändig
```

Körper-x ist damit die Querrichtung der Platine, Körper-y die Plattennormale. Der Schlitten wird so eingebaut, dass diese beiden Achsen zu den Kippachsen der TVC-Servos passen. Sonst kommt noch eine feste Drehung um z dazu.

**Offen:** Den Innendurchmesser des echten Rumpfrohrs nachmessen. Gerechnet ist mit 69 mm, das ist der Ring-Durchmesser. Das Blender-Rohr hat 75 mm außen. Außerdem fehlt die Länge der Avionik-Sektion: Der Schlitten braucht etwa 120 mm plus die Endringe.

## 3. Stromversorgung

```
2S LiPo (6,0–8,4 V) ─ XT30 ─ J_SW (externer Schalter, JP1 brückt ihn auf dem Tisch)
   └─ Q1 Verpolschutz (P-FET, AO3401A) ─ VBAT_PROT
         ├─ J_ARM (externer Arming-Schalter) ─ VBAT_ARMED ─ Pyro 1/2 (+)
         └─ R_SHUNT 0,1 Ω (INA219) ─ VBAT_MEAS
               ├─ U1 Buck TPS563201 → 5V_SERVO (3 A): 3 Servos, DRV8833, 470 µF Bulk
               └─ U2 Buck TPS563201 → 5V_SYS  (3 A): Teensy VIN (über Schottky D1), LEDs, Summer
                     └─ U3 LDO AP2112K-3.3 → 3V3_RF (600 mA): HC-12, GPS
Teensy 3V3 (≤ 250 mA) → ICM-20948, BMP280, INA219, I²C-Pull-ups
```

- **D1 Schottky von 5V_SYS nach Teensy-VIN.** USB und Board können gleichzeitig stecken, ohne dass USB rückwärts ins Board speist. Die VUSB-VIN-Brücke am Teensy muss deshalb nicht aufgetrennt werden. Am USB allein laufen Teensy und Sensoren, Servos, Funk und GPS nicht.
- **Pyro hinter dem Verpolschutz, aber vor dem Shunt.** Zündströme von einigen Ampere laufen nicht durch den INA219, dessen Messbereich mit 0,1 Ω bei 3,2 A endet. Die Firmware-Kalibrierung (0,1 Ω, PGA 320 mV) bleibt damit gültig.
- **Brownout beim Zünden:** Eine durchgebrannte E-Match kann kurzschließen. Die Firmware begrenzt den Zündpuls deshalb auf ≤ 1 s. Zusätzlich puffern 220 µF an 5V_SYS.

**Strombudget (Spitze):**

| Schiene | Verbraucher | Spitze |
|---|---|---|
| 5V_SERVO | 2× TVC-SG90 + Fallschirm-SG90 (Blockierstrom je ~0,65 A), Rollmotor ~1 A | ~2,9 A, nur kurzzeitig |
| 5V_SYS | Teensy 600 MHz ~0,1 A, 2× WS2812B 0,12 A, Summer 0,03 A, 3V3_RF ~0,15 A | ~0,4 A |
| 3V3_RF | HC-12 Senden mit 20 dBm ~0,1 A, GPS ~0,03 A | ~0,13 A |
| Teensy 3V3 | ICM-20948, BMP280, INA219 | < 10 mA |

Das Strombudget in `Übersicht.ods` kommt auf 780 mA. Das passt zum Normalbetrieb, die Blockierströme der Servos sind darin aber nicht enthalten.

## 4. Pinbelegung Teensy 4.1

Alle Pins aus dem heutigen `Config.h` bleiben gleich. Neu sind die mit ★ markierten.

| Pin | Signal | Ziel | Status |
|---|---|---|---|
| 0 / 1 | RX1 / TX1 | GPS (JST-GH 4-polig) | ★ (ein früherer GPS-Testsketch nutzte schon 0/1) |
| 2 / 3 | MOT_IN1 / MOT_IN2 | DRV8833 AIN1=BIN1 / AIN2=BIN2 (Brücken parallel) | wie bisher |
| 4 | IMU_INT | ICM-20948 INT1 | ★ für späteres Lesen per Interrupt |
| 5 / 6 | LED1 / LED2 | über 74AHCT1G125 (5 V) → WS2812B auf dem Board und Stiftleiste | wie bisher |
| 7 | CAM_TRIG | 1 kΩ → J_CAM | ★ (Kamera-Test) |
| 9 | SERVO_CHUTE | J_SERVO3 | wie bisher |
| 13 | BUZZER | AO3400A → aktiver 5-V-Summer | wie bisher. Die Teensy-LED blinkt mit. |
| 18 / 19 | SDA0 / SCL0 | BMP280 (0x76), INA219 (0x40), Qwiic-Buchse | wie bisher, 4,7 kΩ Pull-ups |
| 20 (A6) | PYRO1_SENSE | Spannungsteiler am Drain von Pyro 1 | ★ |
| 21 (A7) | PYRO2_SENSE | Spannungsteiler am Drain von Pyro 2 | ★ |
| 22 | PYRO2_FIRE | Gate Q_P2 | ★ |
| 23 | PYRO1_FIRE | Gate Q_P1 | ★ `PIN_PYRO1 = 23` in `Config.h` ist schon dieser Kanal. |
| 26 / 27 / 39 / 38 | MOSI1 / SCK1 / MISO1 / CS1 | ICM-20948 SPI | ★ ersetzt die IMU an Wire |
| 28 / 29 | SERVO_YAW / SERVO_PITCH | J_SERVO1 / J_SERVO2 | wie bisher |
| 33 | HC12_SET | HC-12 SET (Konfigurationsmodus) | ★ |
| 34 / 35 | RX8 / TX8 | HC-12 TXD / RXD | wie bisher |
| 40 (A16) | VBAT_SENSE | 100 k / 33 k von VBAT_PROT | ★ redundant zum INA219 |
| 41 (A17) | ARM_SENSE | 100 k / 33 k von VBAT_ARMED | ★ |
| 10, 11, 12, 14, 15, 16, 17, 24, 25 | frei | Erweiterungsleiste 2×7 mit 3V3, 5V_SYS, GND | – |

Firmware-Änderungen für die IMU:

- `Sensors.cpp`: `ICM_20948_SPI imu;`
- `SPI1.setMISO(39);`
- `imu.begin(PIN_IMU_CS, SPI1, 7000000);`
- `Config.h` bekommt die neuen ★-Pins.

Teensy 4.1 nutzt für SPI1 standardmäßig MISO = Pin 1. Pin 1 ist hier aber TX1 für das GPS, deshalb wird MISO auf Pin 39 umgelegt.

## 5. Pyro-Kanäle (Sicherheitskonzept)

- Low-Side-N-FET pro Kanal: AO3400A (30 V, 5,7 A, Ansteuerung mit 3,3 V am Gate). 100 Ω Gate-Widerstand und 100 kΩ Pull-down. Beim Booten sind die Teensy-Pins hochohmig, dann hält der Pull-down den FET sicher aus.
- Pyro (+) liegt an **VBAT_ARMED**. Spannung kommt dort nur an, wenn der externe Arming-Schalter (J_ARM) geschlossen ist. Ohne Arming kann die Firmware also nichts zünden.
- Durchgangsprüfung: Drain über 100 k / 33 k an den ADC. Mit Arming und eingesteckter E-Match liegt der Drain auf VBAT, ohne E-Match ziehen ihn 100 kΩ nach GND. Durchgang lässt sich so nur im scharfen Zustand prüfen. Das ist bei Hobby-Flugcomputern üblich und wird über den Summer gemeldet.
- Pro Kanal eine TVS-Diode (SMBJ12A) über dem Ausgang. Schraubklemme 3,5 mm, zweipolig.
- Firmware-Regeln: Zünden nur in einem expliziten Flugzustand, Puls ≤ 1 s, jeder Kanal höchstens einmal.

## 6. Stückliste rev A (Entwurf)

LCSC-Nummern und Verfügbarkeit erst beim Bestellen bei JLC prüfen. Hier stehen nur Hersteller-Teilenummern.

| Ref | Bauteil | Gehäuse | Anz. | Funktion |
|---|---|---|---|---|
| U_TEENSY | Teensy 4.1 + 2× Buchsenleiste 1×24, 2,54 mm | THT | 1 | MCU (vorhanden) |
| U4 | TDK ICM-20948 | LGA-24 3×3 | 1 | IMU 9-Achsen + DMP |
| U5 | Bosch BMP280 | LGA-8 2×2,5 | 1 | Barometer. Zum Schutz vor Licht und Fahrtwind mit Schaumstoff abdecken. |
| U6 | TI INA219AID | SOIC-8 | 1 | Strom- und Spannungsmessung |
| R_SHUNT | 0,1 Ω 1 % 1 W | 2512 | 1 | Shunt |
| U1, U2 | TI TPS563201 + 2,2 µH (≥ 4 A Sättigung) | SOT-23-6 | 2 | 5 V / 3 A Buck |
| U3 | Diodes AP2112K-3.3 | SOT-23-5 | 1 | 3V3_RF |
| U7 | TI DRV8833 | HTSSOP-16 | 1 | Rollmotor-H-Brücke, beide Kanäle parallel |
| U8, U9 | 74AHCT1G125 | SOT-23-5 | 2 | 3,3 → 5 V Pegelwandler für die WS2812B |
| LED1, LED2 | WS2812B-2020 | 2020 | 2 | Status-LEDs auf dem Board |
| Q1 | AO3401A | SOT-23 | 1 | Verpolschutz |
| Q_P1, Q_P2, Q_BZ | AO3400A | SOT-23 | 3 | Pyro 1/2, Summer |
| D1 | SS14 oder B5819W | SMA / SOD-123 | 1 | VIN-Entkopplung |
| D_TVS | SMBJ12A | SMB | 2 | Pyro-Ausgänge |
| BZ1 | Aktiver Summer 5 V, 12 mm | THT | 1 | Signalgeber |
| C_BULK | 470 µF / 16 V Low-ESR (8 × 10,5 mm), 220 µF / 10 V | Elko stehend | 1+1 | 5V_SERVO, 5V_SYS, im Streifen WANDLER |
| J_BAT | XT30PW-M (liegend) | THT | 1 | Akku |
| J_SW, J_ARM | JST-XH 2-polig | THT | 2 | Hauptschalter, Arming |
| J_SERVO1..3 | Stiftleiste 1×3, 2,54 mm, 90° gewinkelt | THT | 3 | Servos (S / + / –), Stecker liegen axial zum TVC |
| J_MOT | JST-PH 2-polig | THT | 1 | Rollmotor |
| J_PYRO1, J_PYRO2 | Schraubklemme 2-polig, 3,5 mm | THT | 2 | E-Matches |
| J_HC12 | Buchsenleiste 1×5 + Abstandshalter M2 | THT | 1 | HC-12 liegend gesteckt, Antenne zur Spitze |
| J_GPS, J_QWIIC | JST-GH 4-polig / JST-SH 4-polig | SMD | 1+1 | GPS, I²C-Erweiterung |
| J_CAM, J_LED | JST-GH 3-polig | SMD | 1+1 | Kamera-Trigger, externe LEDs |
| J_EXP | Stiftleiste 2×7 | THT | 1 | freie Pins |
| JP1 | Lötbrücke | – | 1 | Hauptschalter überbrücken, nur auf dem Tisch |

Dazu kommen die üblichen Abblock- und Teiler-Bauteile (0402/0603).

Empfehlung ohne Platinenänderung: Auf die Unterseite des Teensy 4.1 einen W25Q128-Flash (SOIC-8) löten. LittleFS steht schon in `lib_deps`. Dann gibt es neben der SD-Karte ein erschütterungsfestes Log.

## 7. Layout-Regeln

- Lage 2 ist durchgehend GND, Lage 3 Versorgungsflächen.
- Die Buck-Wandler mit Spulen liegen im Streifen WANDLER links neben dem Teensy, mindestens 15 mm vom ICM-20948 und dessen Magnetometer entfernt. Die Spulen sitzen am TVC-Ende des Streifens, weg vom BMP280.
- Unter dem ICM-20948 keine schnellen Leitungen. Seine Entkopplung (100 nF + 10 nF auf REGOUT) direkt an den Pins.
- Der BMP280 kommt nicht neben die Spulen und den Teensy-Prozessor, denn Wärme verfälscht die Höhe.
- Hochstrompfade (VBAT, 5V_SERVO, Pyro) mindestens 1 mm breit und auf beiden Außenlagen.
- Steckverbinder an den Stirnseiten: Akku, Servos und Motor am TVC-Ende, Pyro, Funk, GPS und Signale am Spitzen-Ende. An den Längskanten sitzt nichts höher als 5 mm (Stangen).
- Strom fließt von unten (Akku) nach oben, und die Hochstromleitungen kreuzen nicht unter der IMU.

## 8. Inbetriebnahme rev A (Testplan)

1. Ohne Teensy am Labornetzteil mit 7,4 V und 100 mA Strombegrenzung starten: 5V_SERVO, 5V_SYS und 3V3_RF messen.
2. Teensy stecken, nur USB: I²C-Scan muss 0x40 und 0x76 finden. ICM-20948 per SPI (WHO_AM_I = 0xEA).
3. Akku, Flug-Firmware (`spacecode/`) im Normalbetrieb: Loop-Timing mit `LOOP_WARNING` prüfen, Teleplot Kalman und INA.
4. Servos und Rollmotor einzeln, dabei auf Brownout achten (Teensy darf nicht neu starten).
5. Pyro nur mit Glühlämpchen oder 2-Ω-Widerstand testen, **nie mit echter Ladung auf dem Tisch**. Prüfen: ohne ARM keine Zündung, ARM_SENSE, Durchgang, Pulsdauer.
6. HC-12-Reichweite und GPS-Fix im Freien.

## 9. Offen (vor dem Schaltplan zu klären)

- Rohr-Innendurchmesser und Länge der Avionik-Sektion nachmessen. Der Schlitten braucht 120 mm plus die Endringe. Ist das Rohr innen größer als 69 mm, kann die Platine breiter werden; dann wandern die Stangen mit.
- Wie liegen die TVC-Servoachsen relativ zum Schlitten? Davon hängt die Achsenumsetzung in §2 ab.
- Wo sitzt die Rumpf-Luke für USB und SD-Karte?
- Kommt die IMU an SPI1 (empfohlen) oder bleibt sie an I²C wie bisher?
- Ist der Rumpf aus Pappe oder CFK? Bei CFK muss die HC-12-Antenne sicher bis in die Spitze reichen.
- Wird die Kamera mit 3,3 V oder 5 V ausgelöst?
- Fallschirm über Servo oder Pyro? Das Board kann beides. Pyro bedeutet aber Schwarzpulver-Ladungen, und dafür gelten die örtlichen Regeln (in Deutschland Sprengstoffrecht).
