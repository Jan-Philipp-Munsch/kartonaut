# Bewertung der Reviewfragen und der Verschaltung, Mainboard rev B1 (26.10.2026)

Antworten auf die zehn Bewertungsfragen aus `review_brief_2026-10-23.md` §4 und Prüfung der Verschaltung Pin für
Pin gegen die Datenblätter. Grundlage: Netzliste frisch aus dem Schaltplan exportiert (26.10.), Kupferbreiten in der
Platinendatei gemessen (Kupfer eines Netzes schrittweise abgetragen, bis die Verbindung zwischen zwei Pads reißt),
TPS63070-Datenblatt SLVSC58B, E22-T-Handbuch von Ebyte, JLCPCB-Grenzen. Ergänzt `Abschlusspruefung_2026-10-26.md`
(Herstellbarkeit) und `REVIEW_PAKET_2026-10-26.md`.

**Ergebnis: kein A-Punkt. Die Platine kann so bestellt werden.** Sechs B-Punkte (Breiten unter der Vorgabe der
Spezifikation, für den Erstflug ausreichend) und einige C-Hinweise. **B1 bis B3 und B6 sind am 26.10. nachmittags
eingearbeitet** (§5), DRC danach 0 Fehler, Fertigungsdaten in `kicad/fab/` neu erzeugt (26.10. 11:52).

Zur Messmethode: Das Abtragen findet die breiteste *einzelne* Engstelle. Läuft ein Netz über mehrere parallele Wege
(eine Fläche durch die Lücken einer Stiftreihe, die vier Speichen einer Wärmefalle), zählt die Methode nur einen davon
und unterschätzt die wirkliche Breite. Für die Strompfade der Tabelle ist das konservativ.

## 1. Gemessene Breiten der Strompfade

Tragfähigkeit nach IPC-2221 (1 oz außen, 10 K Erwärmung): 0,3 mm ≈ 1,0 A, 0,6 mm ≈ 1,7 A, 1,0 mm ≈ 2,4 A,
1,4 mm ≈ 3,0 A. Pyro-Puls 5 A / 20 ms auf 1,0 mm: Erwärmung ≈ 2 K (adiabatisch).

| Pfad | von → nach | Lage | min. Breite | Strom | Urteil |
|---|---|---|---|---|---|
| 2S Eingang | J1 XT30 → Q1 | F.Cu | 1,20 mm | Servos + Pyro, ≤ 3 A (Polyfuse 3 A hold) | ✓ |
| 2S Verpolschutz → Sicherung | Q1 → F1 | F.Cu | 1,00 mm | | ✓ |
| 2S Sicherung → Lastschalter | F1 → Q6 | F.Cu | 1,00 mm | | ✓ |
| 2S Lastschalter → Shunt | Q6 → R_SH1 | F.Cu | 1,10 mm | | ✓ |
| VBAT_PROT → Arming | Q6 → J4 | F.Cu | 1,03 mm | Pyro-Pulse | ✓ |
| VBAT_ARMED → Pyro 1 / 2 | J4 → J9 / J10 | F.Cu | 1,60 mm | 5 A / 20 ms | ✓ |
| Pyro-Rückleitung | J9 → Q3, J10 → Q4 | F.Cu | 1,00 mm | 5 A / 20 ms | ✓ |
| Pyro-FET-Source → GND_PWR-Fläche | Q3.2 / Q4.2 → J1.2 | F.Cu + Via + B.Cu | 1,13 mm | | ✓ |
| VSERVO → TVC-Servos | R_SH1 → J5 / J6 | F.Cu | 1,22 mm | je ≤ 1 A Spitze | ✓ |
| VSERVO → Fallschirm-Servo | R_SH1 → J7 | F.Cu | 0,72 mm | ≤ 1 A Spitze | ✓ (Vorgabe 1,0; **B5**) |
| VSERVO → Beine-Servo | R_SH1 → J16 | F.Cu | 0,61 mm | nicht im Erstflug | **B5** |
| VSERVO → DRV8833 VM | R_SH1 → U7.12 | F.Cu | 0,30 mm | Rollmotor ≤ 1 A, nicht im Erstflug | **B2** |
| GND_PWR-Rückweg Servos | J1.2 → J5.3 / J6.3 | B.Cu | 2,30 / 2,96 mm | trotz der 13 Schlitze | ✓ |
| GND_PWR-Rückweg J7 / J16 | J1.2 → J7.3 / J16.3 | B.Cu | 0,70 / 0,62 mm | | **B5** |
| GND_PWR → Sternpunkt | J1.2 → NT1.1 | B.Cu | 2,96 mm | | ✓ |
| GND_PWR → DRV8833 AISEN / BISEN | J1.2 → U7.3 / U7.6 | | 1,05 / 0,40 mm | Motorstrom halbiert (Parallelbetrieb) | ✓ / **B4** |
| GND_PWR → DRV8833 Pin 13 | | F.Cu | 0,15 × 1,9 mm | nur Logikmasse, Strom läuft über ISEN und Wärmepad | ✓ |
| 1S Akku → Verpolschutz | J2 → Q2 | F.Cu | 0,60 mm | ≤ 1 A | ✓ (Vorgabe 0,6) |
| 1S Verpolschutz → Sicherung → Lastschalter | Q2 → F2 → Q7 | | 0,60 mm | | ✓ |
| VSYS_IN Lastschalter → Wandler | Q7 → U2.12 / C10 | F.Cu + In2 | **0,45 mm**, davon 3,3 mm auf In2 (0,5 oz) | ≈ 0,9 A bei 3,3 V (0,5 A an 5 V) | **B1** (A7 verlangt 0,6) |
| 5V_SYS Wandler → Fläche | U2.7 → C13 | F.Cu | 1,95 mm | | ✓ |
| 5V_SYS Fläche → D1 | → D1.2 | F.Cu-Stich | **0,34 mm** | Teensy ≈ 0,3 A | **B3** |
| TEENSY_VIN D1 → Teensy / Hold-up | D1.1 → A1.25 / C16 | | 0,60 mm | ≈ 0,3 A | ✓ |
| 1S-Masse → PGND / Sternpunkt | J2.2 → U2.10 / NT1.2 | In1 | 2,26 / 3,00 mm | | ✓ |

## 2. Die zehn Bewertungsfragen

| Nr. | Frage | Bewertung |
|---|---|---|
| 1 | Strompfade | **Vertretbar.** Der 2S-Pfad liegt durchgehend bei ≥ 1,0 mm (Tabelle). Dauerstrom 2S im Erstflug: zwei TVC-Servos und der Fallschirm-Servo, zusammen < 3 A; Polyfuse 3 A / 6 A, Shunt 20 mΩ 1 W (7 A). Pyro-Pulse erwärmen 1,0 mm um ≈ 2 K. |
| 2 | GND_PWR 0,15 mm an DRV8833 Pin 13 | **Reicht.** Pin 13 ist die Logikmasse; der Brückenstrom fließt über AISEN (1,05 mm) und BISEN (0,40 mm) auf das Wärmepad und die 12 Vias (1,13 mm zur Fläche). Beide Brücken sind parallel geschaltet (AIN=BIN, AOUT=BOUT), also ≤ 0,5 A je ISEN. Der Rollmotor fliegt in *Kartonaut 1* nicht mit. BISEN in rev B2 auf 0,6 mm (B4). |
| 3 | MOT_A / MOT_B über B.Cu | **Vertretbar.** Trotz der Schlitze bleibt die GND_PWR-Fläche zu jedem Servo-Rückweg ≥ 2,3 mm breit (gemessen, Tabelle); ≤ 1 A PWM bei 20 kHz stört auf 2S nichts, was im Flug zählt. |
| 4 | Sternpunkt NT1 | **Richtig.** In der Netzliste ist NT1 das einzige Bauteil zwischen GND und GND_PWR; die 1S-Masse erreicht den Sternpunkt über In1 mit 3,0 mm, die 2S-Masse über B.Cu mit 2,96 mm. Der Hauptschalter schaltet die beiden Gates gegen die jeweils eigene Masse (SW1_G → GND, SW2_G → GND_PWR), richtig für getrennte Massen. |
| 5 | Anlauf TPS63070 mit 940 µF hinter D1 | **Unkritisch.** Datenblatt §8.4.4: während des Softstarts ist der Eingangsstrom auf typ. 1 A begrenzt, „the device ramps up the output voltage in a controlled manner, even if a large capacitor is connected“. Mit ≈ 1 mF (66 µF am Ausgang + 940 µF hinter D1) dauert der Anlauf ≈ 10 ms statt < 1 ms, kein Hiccup. Direkt am VOUT liegen nur 3 × 22 µF (Datenblatt: 15–470 µF, Tabelle 3 empfiehlt 47 µF bei 1,5 µH) ✓; die 940 µF sieht die Regelschleife nur durch D1. EN-Teiler 330 k / 115 k mit den Schwellen 0,8 V / 0,7 V: ein ab 3,10 V, aus unter 2,71 V ✓ (A2); der Wandler braucht zum Start ≥ 3,0 V am VIN ✓. FB 680 k / 130 k ist exakt TIs Tabellenwert für 5,0 V ✓. VSEL an GND, FB2 offen ✓, VAUX 100 nF ✓. D1 SS14 (1 A): Teensy-Pfad ≈ 0,3 A, Inrush durch den Wandler begrenzt ✓. |
| 6 | LoRa-Modul ↔ IMU | **Unkritisch.** 8 mm von der Modulkante zur IMU-Mitte; der Strahler ist die Antenne in der Spitze (Pigtail), nicht das Modul. Sendestrom 100–140 mA in Bursts (Handbuch §2.2). Sperrflächen unter dem Modul auf F.Cu und In2 vorhanden (Prüfskript). |
| 7 | Lastschalter AO3401A bei −3 V Gate | **So lassen.** Gate liegt über den Schalter an Masse, also V_GS = −V_Bat = −2,7 … −4,2 V (1S) bzw. −6 … −8,4 V (2S). Der AO3401A ist bei −2,5 V spezifiziert (≈ 70–100 mΩ); bei ≤ 1 A sind das < 0,1 V und < 0,1 W. Kein Typwechsel nötig. |
| 8 | SPI0 auf J_STACK, Schlitze in B.Cu, IMU-Masse | **Vertretbar.** Signal-Rückströme laufen über die durchgehende In1-Masse, die Schlitze liegen in den Versorgungsflächen auf B.Cu; deren Restbreiten sind gemessen (5V_SYS ab Wandler 1,95 mm, GND_PWR ≥ 2,3 mm zu den Servos). SPI0_MISO 114 mm mit 16 Vias: ≤ 8 MHz zur Zusatzplatine, wie vorgesehen. IMU-Masse über 0,2 mm zu C26: die IMU zieht < 1 mA, ihre fünf GND-Vias liegen im 5-mm-Umfeld. LSM6DSV16X-Beschaltung: SDx/SCx an GND ist richtig (ST verlangt für Mode 1 GND oder Vdd_IO, nicht offen), INT2 und Aux-Pins offen ✓, Vdd/Vdd_IO an 3V3_SENS ✓, CS aus Y0 ✓. |
| 9 | Zusatzsensoren | **In Ordnung.** LIS3MDL: SA1 und CS an 3V3 → I²C 0x1E, Res-Pins 2/12 an GND wie im Datenblatt, C1 100 nF ✓. SHT40 0x44 ✓. ADXL375 (DNP): CS an 3V3, SDO an GND → 0x53 ✓; **C1:** Pin 3 (RESERVED) liegt an GND, das Datenblatt der ADXL34x/375-Familie sagt „an VS oder offen“; vor einer Bestückung in rev B2 prüfen. Pull-ups 4,7 k an 3V3 ✓. Das Magnetometer ist im Flug durch die 2S-Ströme gestört (45 mm: ≈ 9 µT bei 2 A), es regelt nichts. |
| 10 | Bestückung | wie in `Abschlusspruefung_2026-10-26.md` §5: LCSC-Spalte füllen, LED1/2, E22 und ggf. BMP390 aus der BOM, Bestand am Bestelltag. |

## 3. Verschaltung Pin für Pin (aus der frischen Netzliste)

| Baustein | Geprüft | Befund |
|---|---|---|
| U2 TPS63070 (VQFN-15) | alle 15 Pins gegen SLVSC58B: PS/SYNC, PG, VAUX, GND, FB, FB2, VOUT, L2, PGND, L1, VIN, EN, VSEL | ✓; **C2:** PS/SYNC hängt direkt an VSYS_IN, TI empfiehlt 1 kΩ–1 MΩ in Reihe (kann mit R16 geteilt werden); elektrisch harmlos bei ≤ 4,2 V |
| U4 LSM6DSV16X (LGA-14) | SDO→MISO, SDx/SCx→GND, INT1→Pin 6, Vdd_IO/Vdd→3V3_SENS, GND 6/7, INT2/Aux offen, CS→Y0, SCL→SCK, SDA→MOSI | ✓ |
| U5 / U15 BMP390 (LGA-10) | VDDIO/VDD→3V3_SENS, SCK, SDI→MOSI, SDO→MISO, CSB→Y1 / Y2, VSS 3/8/9, INT offen | ✓ (SPI 4-Draht) |
| U6 INA239 (VSSOP-10) | CS→Y3, MOSI, ALERT offen, MISO, SCLK, VS→3V3, GND, VBUS→ISENS_N (Lastseite des Shunts, Kelvin), IN−/IN+ über R6/R7 10 Ω + C2 100 nF | ✓ (Kelvin-Abgriff nur R_SH1.2/.3) |
| U7 DRV8833 (HTSSOP-16) | nSLEEP→Pin 40, AOUT1+BOUT1=MOT_A, AOUT2+BOUT2=MOT_B, AIN1=BIN1, AIN2=BIN2 (Parallelbetrieb), AISEN/BISEN→GND_PWR, nFAULT→Pin 8 mit 10 k Pull-up, VCP 10 nF nach VM, VM=VSERVO (2S, 2,7–10,8 V ✓), VINT 2,2 µF, GND+Pad→GND_PWR | ✓ |
| U8 SN74LV1T34 | A→Pin 7, Y→LED-Kette über 330 Ω, VCC 5V_SYS, GND | ✓ |
| U10 E22-400T22S (26 Pads) | gegen Ebyte E22-T-Handbuch §3.1: 1 RESET (10 k nach 3V3_RF, Pin 8), 2/8/11/13–16/19/26 GND, 3–7 NC, 12 ANT offen (IPEX), 20 M0→Pin 16, 21 M1→Pin 32, 22 RXD→Serial8 TX, 23 TXD→Serial8 RX, 24 AUX→Pin 36 (nur lesen, Handbuch: nicht extern nach unten ziehen ✓), 25 VCC→3V3_RF mit 100 µF | ✓; **C3:** Handbuch: „≥ 3,3 V sichert die volle Sendeleistung“, der AP2112K liefert nominal 3,3 V; allenfalls ein paar Zehntel dB weniger |
| U11 MCP73831 | STAT→J_CHG1, VSS, VBAT→VBAT1_F (hinter Polyfuse, vor dem Lastschalter; Laden durch Q2 rückwärts möglich, Gate fest an GND), VDD→VBUS_CHG, PROG 2 k = 500 mA | ✓; **C4:** bei 5 V USB und 3,7 V Zelle ≈ 0,65 W im SOT-23-5, die Thermoregelung des Laders drosselt den Strom, kein Schaden |
| U12 74HC138 | A0–A2=SEL0–2, E0n=CS_EN (10 k Pull-up), E1n=GND, E2=3V3, Y0–Y6 = CS_IMU, CS_BARO, CS_BARO2, CS_INA, CS_EXT0–2, Y7 offen | ✓ (CS_EN hoch → alle CS hoch) |
| U13 74HC4051 | A=MUX_OUT→Pin 16, Ē=GND, VEE=GND, VCC=3V3, S0–S2=SEL0–2, A0–A3 Pyro 1–4, A4 VBAT1, A5 VBAT2, A6 ARM, A7 GND | ✓ |
| U16 LIS3MDL, U18 SHT40, U17 ADXL375 | s. Frage 9 | ✓ (C1 für U17) |
| Q1 / Q2 Verpolschutz | P-FET: D am Akku-Plus, S zur Schiene, Gate über 100 k an die eigene Masse | ✓ |
| Q6 / Q7 Lastschalter | S an VBAT2_F / VBAT1_F, D an VBAT_PROT / VSYS_IN, Gate 100 k nach Source, 1 k zum Schalter; Body-Diode sperrt vom Akku zur Last | ✓ |
| Q3 / Q4 Pyro | Low-side, Gate 100 Ω + 100 k Pull-down, TVS SMAJ12CA über dem Zünder, Sense-Teiler 100 k / 33 k + 100 nF auf den Mux | ✓ |
| R_SH1 Kelvin, NT1, J3 J_SW, JP1/JP2, J4 J_ARM, J5–J7/J16 (S / + / −), J9/J10, J15 J_STACK (20 Pins nach §4), J11–J14, J17/J18 | | ✓ |
| Teensy VIN/VUSB-Brücke (B11, geschlossen) | 5V_SYS → D1 → TEENSY_VIN = VUSB; am USB liegt dann 4,7 V an, der Host kann nicht zurückspeisen, D1 sperrt in die andere Richtung | ✓; **C5:** beim Einstecken des USB lädt der PC-Port die 940 µF (USB-Norm sieht 10 µF vor; PC-Ports vertragen das, bei einem schwachen Hub kann der Port kurz abschalten) |
| Teensy-Pins, CS, Mux, Schienen | `check_design.py` gegen `README.md` §4 | ✓ |

## 4. Liste der Punkte

| Nr. | Klasse | Was | Aufwand |
|---|---|---|---|
| B1 | B | VSYS_IN zwischen Q7 und U2: 0,45–0,5 mm, davon 3,3 mm auf In2 (0,5 oz); A7 verlangt ≥ 0,6 mm außen. Bei ≈ 0,9 A ein paar Kelvin wärmer, funktional ok | Bahn auf F.Cu verbreitern und das In2-Stück ersetzen, 10 min |
| B2 | B | VSERVO-Stich zum DRV8833 VM 0,30 mm | 0,6–1,0 mm, 5 min; nicht im Erstflug |
| B3 | B | 5V_SYS-Stich zur Anode von D1 0,34 mm (≈ 0,3 A) | 0,6 mm, 5 min |
| B4 | B | GND_PWR an DRV8833 BISEN 0,40 mm | 0,6 mm; nicht im Erstflug |
| B5 | B | VSERVO / GND_PWR zu J7 (0,72 / 0,70) und J16 (0,61 / 0,62) statt 1,0 mm | nur rev B2 |
| B6 | B | Netzliste `kicad/out/mainboard.net` stammt vom 22.10. (rev B); `make.sh sch` sollte sie mit exportieren, Prüfanleitung verweist darauf | `kicad-cli sch export netlist`, 2 min |
| C1 | C | ADXL375 (DNP) Pin 3 RESERVED an GND statt VS/offen | vor Bestückung prüfen |
| C2 | C | TPS63070 PS/SYNC ohne Vorwiderstand an VIN | rev B2 |
| C3 | C | E22 an 3,3 V nominal, Handbuch „≥ 3,3 V“ | hinnehmen |
| C4 | C | MCP73831 500 mA, Thermoregelung | hinnehmen |
| C5 | C | 940 µF am USB-Port | hinnehmen |
| C6 | C | JLC-Auftragsnummer-Platzhalter über C17 | kosmetisch |

Keiner der Punkte betrifft Kartonaut 1 funktional: Rollmotor und Beine-Servo fliegen nicht mit, der 1S-Pfad trägt
seinen Strom auch mit 0,45 mm.

## 5. Eingearbeitet am 26.10.2026 (nachmittags)

| Nr. | Änderung in `mainboard.kicad_pcb` | Ergebnis (nachgemessen) |
|---|---|---|
| B1 | Die beiden F.Cu-Stücke von Q7 zum Via auf 0,6 mm; das In2-Stück zum Wandler von 0,5 auf 1,2 mm, nur die ersten 0,9 mm am Via bleiben bei 0,78 mm, weil die SERVO_CHUTE-Bahn auf In2 dort mit 0,2 mm Abstand vorbeiläuft (1,2 mm gab einen DRC-Fehler, 0,8 mm lag 0,8 µm darunter) | F.Cu 0,60 mm; In2 0,77 mm auf 0,9 mm Länge, sonst 1,2 mm (0,5 oz: entspricht 0,39 bzw. 0,6 mm in 1 oz). Vollständig auf F.Cu ging nicht, dort liegen VBAT1_SENSE und R9 im Weg |
| B2 | Zusätzliche VSERVO-Zone „VSERVO Stich DRV8833 VM“ (147,15–149,9 × 115,3–116,4 mm, Priorität 3, gleiche Abstände wie die Stromfläche) als Korridor zum VM-Pin | 0,30 → **0,40 mm**; mehr geht am HTSSOP nicht, der Pin selbst ist 0,4 mm breit, daneben liegen VCP, GND und die Vias von MOT_IN2 und VCP |
| B3 | Stich von der Anode von D1 zum Via auf 0,6 mm | 0,59 mm. **Korrektur zu §1:** die dort genannten 0,34 mm für „5V_SYS → D1“ waren die Messmethode, nicht die Platine: die 5V_SYS-Fläche auf B.Cu tritt durch 21 bzw. 20 Lücken der beiden Teensy-Stiftreihen (je 0,34 mm) hindurch, zusammen ≈ 7 mm. Die einzige echte Engstelle war der 0,3-mm-Stich |
| B6 | `make.sh sch` exportiert jetzt `out/mainboard.net`; Datei neu erzeugt (26.10.) | Netzliste zeigt rev B1 |

Danach: `./make.sh drc` 0 Fehler, 0 offen, Parität 0, 17 Druckwarnungen wie vorher; `review_check_layout.py` ohne
Befund; `./make.sh fab` und `./make.sh img` neu. Offen für rev B2: B4, B5, C1, C2.
