# Baudokumentation (as-built)

Was physisch existiert, wie es verdrahtet ist, was darauf läuft und was damit schon getestet
wurde. Diese Datei beschreibt den **Ist-Zustand am Basteltisch**; die Planung steht in
`PROJECT.md`, die Platinen-Spezifikation in `hardware/mainboard/README.md`.
Angelegt am 21.10.2026 aus Bestelllisten, Code, CAD und Git. Alles, was ich nicht belegen
konnte, steht als `[?]` und wartet auf einen Abend mit Messschieber und Handy.

Fotos liegen unter `docs/img/build/` und heißen `JJJJ-MM-TT_<thema>.jpg`.

## 1. Inventar

### 1.1 Rumpf und Bergung (gekauft)

| Teil | Stück | Maße / Daten | Quelle, Datum | Verbaut? |
|---|---|---|---|---|
| Körperrohr 75 mm / 500 mm (Klima 207550000) | 3 | außen 75,0 mm, **innen 72,6 mm**, 120 g | SRT 28.04.2025 (1), Klima 09.06.2025 (1), Klima 23.10.2025 (1, als Ersatz/Verlängerung?) `[?]` | `[?]` |
| Kuppler 75 mm / 150 mm (Klima 207315000) | 3 | außen 72,4 mm, innen 70,2 mm | Klima 09.06.2025 (1), Klima 23.10.2025 (2) | `[?]` |
| Körperrohr 50 mm / 500 mm (Klima 205050000) | 1 | vermutlich als Motorhalterung gedacht (Jan, 21.10.2026) | Klima 23.10.2025 | `[?]` |
| Spitze komplett 75 mm weiß (Klima 8539) | 1 | Kunststoff. **Ersetzt die gedruckte Spitze.** Der Fallschirm liegt in der Spitze, die lose sitzt und per Pyro-Kolben (Kuppler) abgestoßen wird | Klima 23.10.2025 | `[?]` |
| Fallschirm 125 cm (Klima 8594) | 1 | | Klima 09.06.2025 | `[?]` |
| Kevlarschnur geflochten 2,0 mm | 1 m | Schockschnur | Klima 23.10.2025 | `[?]` |
| Elastische Schnur 1,5 mm / 1,8 m | 1 | | Klima 23.10.2025 | `[?]` |
| CO₂-Kapseln 8 g | 5 | für den Fallschirmausstoß (Entscheidung 22.10.2026, statt Schwarzpulver) | `[?]` | nein |

**Zuschnitt (Jan, 22.10.2026, Modulbauweise):** Rohr A 125 mm mit dem Kardan (Kardanschrauben bei 44 mm, zwei
Servofenster ca. 20 × 20 ab 60 mm), Rohr B 176 mm (vier alte Löcher bei 44 mm vom Ring-Stack, werden Druckausgleich),
ein Kuppler in zwei Hälften à 75 mm (eine als Kuppler J1 in Rohr B, eine als Spitzen-Kuppler), Reststück für Rohr C
(195 mm ablängen). Die Klima-Spitze hat 25 mm über der Unterkante eine Holzplatte mit Haken; der Schirm (gepackt
100 × Ø 70) passt nicht hinein und liegt in Rohr C.

### 1.2 Antrieb (gekauft)

| Teil | Stück | Daten | Quelle, Datum |
|---|---|---|---|
| TSP E12-0 (Piotr Tendera Rocket Motors), 24 mm, 2er-Pack | 2 Packs = 4 Motoren | 39 Ns, 12 N mittel, Brenndauer 3,2 s, 28 g Treibstoff, 64 g gesamt, 95 mm lang, **ohne Verzögerung und ohne Ausstoßladung** (−0) | SRT 28.04.2025 |

Hinweis: Die Schubkurve `E12_thrustcurve.csv` im MATLAB-Projekt ist punktgleich mit der
RASP-Datei des **TSP** E12 auf thrustcurve.org (Maximum 28,3 N bei 0,535 s, Ende 3,545 s), die
Simulation rechnet also schon mit dem richtigen Motor. Die Estes-E12-Kurve (27 Ns, 2,4 s,
Maximum 33 N) ist ein anderer Motor und kommt nur zum Vergleich in die Python-Simulation.

### 1.3 Elektronik (vorhanden laut Code und Projektdatei)

| Teil | Stück | Stand | Quelle |
|---|---|---|---|
| Teensy 4.1 | 1 | mit Buchsenleisten? `[?]` | `platformio.ini` |
| ICM-20948 Breakout (SparkFun oder Clone) `[?]` | 1 | an Wire, 0x68/0x69 | `Sensors.cpp` |
| BMP280 Breakout | 1 | 0x76 | `Sensors.cpp` |
| INA219 Breakout | 1 | 0x40, 0,1-Ω-Shunt | `Sensors.cpp` |
| HC-12 (433 MHz) | 2 (Rakete + Boden) `[?]` | Serial8, 9600 Bd | `Config.h`, `eLab` 14.10.2025 |
| Arduino Nano (Bodenstation) | 1 | | Repo `kartonaut-ground` |
| microSD-Karte | 1 | Größe `[?]` | `SDLogger.cpp` |
| 2× WS2812B, aktiver Summer | | Pins 5, 6, 13 | `Indicators.cpp` |
| Servo SG90 | 3 `[?]` | 2× TVC, 1× Fallschirm; Pulsbreite 760–2300 µs gemessen | `Config.h` |
| **Servo FrSky Xact W5652H** | 2, im Kardan verbaut | 10 g, 19 × 8 × 23 mm, 3,7–8,4 V, 2,4 kg·cm / 0,10 s bei 4,2 V, 4,8 kg·cm / 0,05 s bei 8,4 V, Hall-Sensor, 15-Zahn-Abtrieb 4 mm | geliefert, im Schubstangen-Kardan verbaut (Jan, 22.10.2026) |
| Rollmotor + H-Brücke | 1 | Motor-Typ `[?]`, Brücke `[?]` (Code: zwei PWM-Pins 2/3, 20 kHz). **Entfällt für *Kartonaut 1*** (22.10.2026) | `Control.cpp` |
| Schwungrad | `[?]` | `flywheelV2.blend` | CAD |
| MOSFET-Modul für Pyro-Test | 1 `[?]` | Pin 23 | `examples/pyro_mosfet_test` |
| Akku 2S LiPo 7,4 V (Servos, Rollmotor, Pyro) | `[?]` | Kapazität, Stecker `[?]`; CAD rechnet mit 56 × 25,5 × 8 mm | `flight_computer.blend` |
| Akku 1S LiPo 3,7 V (Elektronik) | 1 | 600 mAh, JST-PH; Maße gegen das Fach 50 × 30 × 7 prüfen, Schutzschaltung `[?]` | Bauanleitung §3.5 |
| Akku 2S LemonRC 450 mAh 35C, XT30 (55 × 30 × 10, 29 g) | 0 | zu bestellen (2 Stück, Reichelt `LRC 2S 450`); der vorhandene 2S 1200 mAh ist zu groß und zu schwer | Bauanleitung §3.1 |
| Servo SG90 für die CO₂-Auslösung | 1 (aus Bestand) | an `J_SERVO3` | Bauanleitung §3.5 |
| GPS-Modul | 1 | u-blox **NEO-6M** auf Breakout GY-GPS6MV2 (Berrybase, Kennung 24221903263): Platine 36 × 26 × 5 mm mit 4 Löchern Ø 3, Keramik-Patch 25 × 25 × 9 mm am Kabel, 3–5 V (eigener Regler, an 3V3_RF reicht es), UART ab Werk 9600 Bd NMEA 1 Hz (bis 5 Hz einstellbar). An J11: VCC → Pin 1 (3V3_RF), GND → 2, TX → 3 (GPS_TX), RX → 4 (GPS_RX). Patch passt nicht in den 20 × 20 × 7-Halter unter dem Spant (Bauanleitung §3.6) | Jan, 27.10.2026 |
| Stiftleisten für den Teensy, Schalter, einige Elkos | vorhanden | Teensy-Stiftleisten müssen nicht gekauft werden | Jan, 27.10.2026 |
| Epoxid | `[?]` | Jan sieht nach; gebraucht für Kuppler J1, Schraubring und die Kabeldurchführung im Band | Jan, 27.10.2026 |
| 1S-Lader (JST-PH), microSD, Arming-Schalter, Zünder, 4 Motoren (Space Rocket Technologies), Fallschirm | je vorhanden | | Jan, 26.10.2026 |

### 1.4 Gedruckte Teile

| Teil | CAD | Gedruckt? | Material / Parameter |
|---|---|---|---|
| TVC-Kardan: Schubstangen-Kardan, Außen-/Innenrahmen, Motorrohr | `inner/outer_gimbal_dual_TVC.blend` (12.06.2025), STL in `cad/export/asbuilt/` | **ja, gebaut und in Rohr A eingepasst** (Jan, 22.10.2026): 2 × W5652H flach über dem Außenrahmen, Hebel 15 mm, Stangen 2 mm | `[?]` |
| Flugcomputer-Ring-Stack (Ø 69 mm, 8× M2-Stangen) | `flight_computer.blend` | verworfen (22.10.2026: Schlitten mit Spant) | – |
| Schlitten mit Spant, untere Scheibe, Schalterbrett, Schraubring J1 (Stand 2b) | `cad/modular.py` → `cad/export/modular/*.stl` | nein | PETG, 3 Wände, 25 % Gyroid; nach dem Druck wiegen (Modell 74 / 8 / 2 / 14 g) |
| CO₂-Modul (Anstecher, Kapselhalter) | eigene Konstruktion (Bauanleitung O6) | nein | PETG (PLA wird am kalten CO₂ spröde) |
| Spitze (federgelagert, M2,5-Gewindestange) | `rocket nose.blend` | verworfen (Klima-Spitze 8539) | – |
| Landebeine und Beinanbindung | `LegConnectors.blend`, `model_rocket.blend` | `[?]` | `[?]` |
| Piston-Ejection-Bulkheads (Joe Barnard, 74 mm) | `Space Mission/files/*.stl` | `[?]` | `[?]` |
| Akkuhalter | `battery7.stl` | `[?]` | `[?]` |
| 29→24-mm-Motoradapter | `TVC.blend` | `[?]` | `[?]` |

### 1.5 Landebeine und Prüfstand (gekauft)

| Teil | Stück | Daten | Zweck | Quelle, Datum |
|---|---|---|---|---|
| Carbonrundstab 5,0 × 1000 mm (Conrad 275230) | 2 | | Landebeine, Hauptstreben | Conrad 10.06.2025 |
| Carbonrundstab 3,0 × 1000 mm (Conrad 275228) | 4 | | Landebeine, obere Streben | Conrad 10.06.2025 (2), 24.06.2025 (2) |
| Reely V-Charge Eco NiMH 1000 | 1 | NiMH-Ladegerät | `[?]` (Bodenstation, Startbox?) | Conrad 24.06.2025 |
| Racerstar BR2814 1000KV, 3–4S | 1 | Brushless-Außenläufer, Ø 28 mm | **Prüfstand:** ersetzt den Raketenmotor im Kardan, liefert den Schub elektrisch und regelbar | Banggood 23.06.2025 |
| keyiuav Brushless-ESC 60 A, Two-Way, T-Stecker | 1 | | Prüfstand, Drehzahlsteller | Banggood 23.06.2025 |
| GEMFAN 11 × 7 APC-Form CCW | 2 | | Prüfstand, Propeller | Banggood 23.06.2025 |
| GEMFAN PFGN 12 × 6 Glasfaser, CW + CCW | 1 Paar | | Prüfstand, Propeller (gegenläufiges Paar) | Banggood 23.06.2025 |
| ZOP Power 4S 1500 mAh 100 C, XT60 | 1 | 14,8 V | Prüfstand, Antriebsakku | Banggood 23.06.2025 |
| HTRC H4AC 20 W / 2 A Balancer-Lader 2–4S | 1 | LiPo/LiFe/LiHV | Prüfstand- und Flugakkus laden | Banggood 23.06.2025 |
| Amass XT60/T-Adapter | – | erstattet, nicht geliefert | | Banggood 23.06.2025 |

**Prüfstand, Idee (Jan, 21.10.2026):** Die Rakete hängt dreh- und schwenkbar in einem Gestell,
der Propellermotor sitzt an Stelle des Raketenmotors im Kardan und liefert den Schub. So lässt
sich die Lageregelung mit TVC am Boden testen, ohne Treibsatz. Siehe `PROJECT.md` §4, Paket 15.

## 2. Mechanik

**Stand 22.10.2026, Modulbauweise (`docs/Bauanleitung_Kartonaut1.md`):** vier Module, Rohr A 125 (Kardan, gebaut),
Rohr B 176 (Avionik: Kuppler J1 mit Schraubring, Schlitten mit Spant, Platine, Akkus, GPS, LoRa-Wendel, Schalterbrett),
Rohr C 195 (CO₂-Modul, Schirm, Schnur), Klima-Spitze über dem zweiten halben Kuppler; Gesamtlänge 731 mm; Trennstellen
T1–T3 mit je vier M3 in Muttern-Taschen bei 0°/90°/180°/270° (Rohr C 45° versetzt). Massenbudget 705 g (Druckteile Stand 2c), Schwerpunkt
259 mm, Hebelarm Kardan–Schwerpunkt 190 mm (`cad/mass_stand2b.md`), alles ungewogen. Die folgenden Absätze beschreiben
den Stand vom 21.10. (Ring-Stack im Kuppler, Pyro-Kolben), der damit überholt ist.

- **Rohr:** Klima 75 mm, innen 72,6 mm. **Der Flugcomputer sitzt im Kuppler** (innen 70,2 mm,
  150 mm lang), daher der Ring-Stack mit Ø 69 mm und 0,6 mm Luft je Seite. Der Platinenschlitten
  (54 × 120 mm) bleibt bei diesem Maß. Vorteil: Der Kuppler mit dem Flugcomputer lässt sich als
  Modul herausziehen, das passt zu Jans Ziel einer leicht wartbaren Rakete.
- **Bergung:** Fallschirm in der Klima-Spitze, Spitze lose aufgesteckt, Ausstoß durch einen
  Kolben aus einem Kuppler mit Schwarzpulver-Ladung (BPS-Prinzip). Pyro-Tests mit etwa 1 g
  Schwarzpulver haben funktioniert (Datum `[?]`).
- **Gesamtlänge:** 2 × 500 mm Rohr + Spitze (99 mm gedruckt oder Klima-Spitze `[?]`) `[?]`
- **Sektionen von unten:** TVC-Kardan mit Motor `[?]` mm, Flugcomputer `[?]` mm, Fallschirmraum `[?]` mm, Spitze.
- **Schwerpunkt:** gemessen `[?]`; Massenmodell (`cad/mass_properties.md`): 448 mm ab Düse mit vollem Motor, 477 mm ohne. Hebelarm Kardan–Schwerpunkt 0,37 m (bisher 0,30 m angenommen).
- **Masse:** Massenmodell 981 g mit einem Motor (`cad/mass_properties.md`; Budget Juni 2025: 902 g), gewogen `[?]`. Laut Simulation zu schwer für einen E12 (PROJECT.md Befund 12).
- **Luke** für USB und SD-Karte: `[?]`
- **Druckausgleichsbohrungen** für das Barometer: `[?]`

## 3. Elektronik as-built (Breakout-Aufbau)

Verdrahtung nach `Config.h` (Stand Commit `5a24e78`). Bitte am Gerät gegenprüfen und
Abweichungen hier eintragen.

| Teensy-Pin | Signal | Modul / Pin | Kabel |
|---|---|---|---|
| 18 / 19 | SDA0 / SCL0 | BMP280, INA219, ICM-20948 (Wire) | Dupont `[?]` |
| 34 / 35 | RX8 / TX8 | HC-12 TXD / RXD | |
| 28 | SERVO_YAW | TVC-Servo 1 Signal | |
| 29 | SERVO_PITCH | TVC-Servo 2 Signal | |
| 9 | SERVO_CHUTE | Fallschirm-Servo Signal | |
| 2 / 3 | MOT_IN1 / MOT_IN2 | H-Brücke IN1 / IN2 | |
| 5 / 6 | LED1 / LED2 | WS2812B DIN | |
| 13 | BUZZER | Summer (über Transistor? `[?]`) | |
| 23 | PYRO1 | MOSFET-Modul Gate | nur im Testsketch |
| VIN / GND | 5 V | Quelle `[?]` (UBEC? Buck-Modul? USB?) | |

Servo- und Motorversorgung: `[?]` (direkt aus dem LiPo, UBEC, Buck-Modul?). Hauptschalter: `[?]`.

## 4. Software-Stand auf dem Gerät

| Datum | Commit auf dem Teensy | Umgebung | Config-Schalter |
|---|---|---|---|
| `[?]` | `[?]` (zuletzt am Gerät getestet war ein Stand vor `5a24e78`; die Aufräumrunde vom 20.10.2026 ist **nicht** geflasht) | `teensy41` | `[?]` |

## 5. Durchgeführte Tests

| Datum | Test | Ergebnis | Nachweis |
|---|---|---|---|
| 2025-10 | Servo-Pulsbreiten SG90 gemessen | 760–2300 µs | `Config.h` |
| 2025-10 | Gyro-Offsets am Tisch | +12,1 / −7,96 / +2,44 LSB | `Config.h` |
| 2025-10 | I²C-Scan | 0x40, 0x68/0x69, 0x76 `[?]` | `examples/i2c_scanner` |
| 2025-10 | HC-12-Beacon Teensy → Nano | funktioniert, Reichweite `[?]` | Commit „Gyro integration and radio test“ |
| 2025-10 | Kalman-Höhe am Tisch, SD-Log mit CSV-Export | funktioniert | Commits „kalman filter optimization“, „Logger Implementation“ |
| `[?]` | Pyro-MOSFET mit Lämpchen | `[?]` | `examples/pyro_mosfet_test` |
| `[?]` | Pyro-Ausstoß mit ca. 1 g Schwarzpulver | hat gut funktioniert (Jan, 21.10.2026); Aufbau, Zünder und Ladungsmenge `[?]` | – |
| `[?]` | Kardan-Fenster Yaw 70–115°, Pitch 60–105° | aus CAD oder gemessen? `[?]` | `Config.h` |
| – | Schubstand, Flug | nicht durchgeführt | |

## 6. Bautagebuch

Ein Eintrag je Arbeitssitzung am Gerät. Rekonstruiert, soweit möglich; ab jetzt direkt.

| Datum | Was | Fotos | Offen danach |
|---|---|---|---|
| 2025-03 | Projektstart, PlatformIO-Projekt, erste TVC- und Schwungrad-Modelle, Strombudget | – | |
| 2025-04-28 | Bestellung SRT: 1× Rohr 75/500, 2× 2er-Pack TSP E12-0 | – | |
| 2025-04 bis 06 | MATLAB-6DOF, PID-Tuning, Servo-Systemidentifikation (18.05.), TVC V2 und dual TVC, Landebeine, Gesamtmodell | `Images/Monte-Carlo*.png` (lokal) | |
| 2025-06-09 | Bestellung Klima: Rohr 75/500, Kuppler, Fallschirm 125 cm | – | |
| 2025-06-10 | Bestellung Conrad: 2× Carbonstab 5 mm, 2× Carbonstab 3 mm (Landebeine) | – | |
| 2025-06-23/24 | Bestellung Banggood (Prüfstand: BR2814, ESC 60 A, Propeller 11×7 und 12×6, 4S-LiPo, Lader) und Conrad (2× Carbonstab 3 mm, NiMH-Lader) | – | Prüfstand-Gestell konstruieren |
| 2025-10-12 bis 31 | Git-Repo, Firmware modularisiert, Kalman, SD-Logger, HC-12-Test, Regler; `flight_computer.blend` überarbeitet | – | |
| 2025-10-23 | Bestellung Klima: 2× Kuppler, Rohr 50/500, Spitze 75 mm, Kevlar- und Gummischnur | – | Zweck des 50-mm-Rohrs `[?]` |
| 2026-10-15 | Mainboard rev A spezifiziert (am Rechner) | – | |
| 2026-10-20 | Firmware-Aufräumrunde, Veröffentlichung (am Rechner, nicht geflasht) | – | flashen und am Gerät prüfen |
| 2026-10-21 | Planungsrunde, diese Datei angelegt; Servos FrSky W5652H bestellt. Rev B spezifiziert, Design Guide und Bestellplan, Simulation nach Python, Blender-Inventur und parametrisches CAD mit Massenmodell (alles am Rechner) | `docs/img/cad/` (Renders) | Inventar am Gerät prüfen, Fotos; Teile wiegen (Spitze, Kuppler, Rohr, Motor, Kardan-Drucke); Rohr-Innen- und Kuppler-Außenmaß messen |
| 2026-10-22 | **Kardan gebaut:** Schubstangen-Kardan mit 2 × W5652H in Rohr A 125 mm, Kardanschrauben 4 × M3 bei 44 mm, Servofenster ca. 20 × 20 ab 60 mm, Hebel 15 mm, Stangen Ø 2 mm; Rohr B 176 mm mit vier Löchern bei 44 mm; Kuppler halbiert (75 mm), gesteckt. Entscheidungen: kein Rollmotor, CO₂-Ausstoß, Schraubschalter, Schirm in Rohr C. Am Rechner: Bauanleitung Stand 2b, Bodenstation, Startrampe, Firmware rev B, Massenbudget 723 g | Fotos vom Kardan (Jan, 22.10.) `[?]` | Druckteile drucken und wiegen, Bestellliste §3.1 der Bauanleitung, Servofenster-Winkel am Rohr nachsehen (O1), Servo-Umrechnung messen (Befund 13), CO₂-Modul konstruieren |

## 7. Regeln

1. Jede Sitzung am Gerät bekommt einen Eintrag in §6, auch ein Dreizeiler, mit Fotos.
2. Jede Änderung an Verdrahtung oder Pins am selben Tag in `Config.h` **und** in §3.
3. Was auf dem Teensy läuft, ist ein Commit; §4 nennt den Hash und die Config-Schalter.
4. Messwerte (Pulsbreiten, Offsets, Massen, Schwerpunkt) stehen mit Datum und Methode in §5,
   `Config.h` verweist darauf.
5. Bestellungen kommen mit Datum, Händler und Stückzahl in §1.
