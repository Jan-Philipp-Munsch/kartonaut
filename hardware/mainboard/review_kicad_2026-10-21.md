# Review des KiCad-Projekts rev B (zweite Meinung, 21.10.2026)

Geprüft wurde der Arbeitsstand des KiCad-Projekts `kicad/` am Abend des 21.10.2026 (Schaltung
`circuit.py`, Generator `gen_pcb.py`, Netzklassen in `mainboard.kicad_pro`, `kicad/README.md`,
`review_netlist_2026-10-21.md`) gegen die Spezifikation `README.md` (rev B), den Plan
`docs/Plan_2026-10-21.md` §2 und den Design Guide. Die Schaltungsentscheidungen wurden gegen die
Datenblätter gehalten: TPS63070 (SLVSC58B), TPS563201 (SLVSCG8), ICM-42688-P (DS-000347, Pintabelle),
E22-400T22S (Ebyte-Pintabelle). Der Schaltungsteil (§1 bis §4) gilt unabhängig vom Layoutstand; der
Layoutteil (§5) bezieht sich auf den Stand nach dem Routing-Lauf vom selben Abend.

**Gesamturteil.** Die Schaltung ist sauber und entspricht der Spezifikation; die Tor-1-Prüfung hat die
Pinbelegungen richtig verifiziert. Der Ansatz „Schaltung als Code“ ist für dieses Projekt die richtige
Wahl. Vor der Bestellung sollten die fünf Punkte unter **A** geändert werden; drei davon betreffen den
Stromversorgungspfad (Ausgangskapazität des Buck-Boost, Hauptschalter im Hochstrompfad, Absicherung),
einer die Strommessung (Kelvin) und einer die Unterspannungsabschaltung des 1S-Akkus im Flug.

Prioritäten: **A** vor der Bestellung ändern · **B** sollte, kostet wenig · **C** Vorschlag, Entscheidung Jan.

## 1. Versorgung

### A1. TPS63070: 1066 µF am Ausgang, Datenblatt erlaubt 470 µF

`circuit.py` hängt an `5V_SYS` 3 × 22 µF plus den 1000-µF-Polymer-Elko C19. Das Datenblatt gibt unter
*Recommended Operating Conditions* „Total capacitance connected to VOUT pin: 15 min / 47 nom / 470 max µF“.
Mit 1066 µF liegt der Regler außerhalb seiner Spezifikation (Regelschleife, Soft-Start läuft in die
Strombegrenzung, Anlauf aus dem leeren 1S-Akku).

Vorschlag: **den 1000-µF-Elko hinter die Schottky D1 an `TEENSY_VIN`** setzen, am Reglerausgang nur
3 × 22 µF (bei Bedarf plus ein 100-µF-Polymer, zusammen unter 300 µF). Das ist genau die Anordnung aus
dem Plan §2.5 („Energiespeicher hinter dem Wandler plus Schottky zum Teensy-VIN“): Hinter der Diode kann
der Speicher nicht in die anderen 5V_SYS-Verbraucher zurückfließen und hält nur den Teensy. Rechnung:
1000 µF von 4,6 V auf 3,6 V (VIN-Minimum des Teensy) bei 0,15 A tragen 6,7 ms; das reicht für jeden
Regler-Aussetzer, den der 1S-Pfad überhaupt sehen kann. Der LoRa-Sendepuls (110 mA an 3V3_RF) wird vom
Regler selbst getragen (2 A), dafür braucht es keinen Elko.

### A2. Unterspannungsabschaltung des 1S-Akkus schaltet im Flug den Rechner ab

Der EN-Teiler 330 k / 100 k ist richtig gerechnet (präzise EN-Schwelle 0,8 V steigend / 0,7 V fallend
laut Datenblatt, Tabelle *Logic Signals* und §8.4.2): an ab 3,44 V, **aus unter 3,01 V**. Eine 1S-Zelle
sackt unter Last und in der Kälte kurzzeitig unter 3,0 V, bevor sie leer ist; dann schaltet der
Flugcomputer mitten im Flug ab, die Servos laufen weiter. Der Schutz der 6-€-Zelle ist weniger wert als
der Flug.

Vorschlag: Schwelle tiefer legen, **330 k / 115 k: an ab 3,1 V, aus unter 2,7 V** (der TPS63070 arbeitet
ab 2,0 V). Oder gar keine Abschaltung (EN über 1 MΩ an VIN, Warnung nur per Firmware und Summer vor
dem Start). Die Firmware warnt ohnehin bei 1S < 3,5 V (Spezifikation §3), das ist die richtige Stelle.

### A3. Hauptschalter im Hochstrompfad über JST-PH und zwei Kabel durch den Rumpf

`J3` (JST-PH 4-polig, 2 A je Kontakt) führt den gesamten 2S-Strom hinaus zum Schiebeschalter am Rumpf
und wieder zurück: Servospitzen 2 A, Buck 1,7 A, Pyro-Puls 5 A. Dazu kommen 2 × 15 cm Kabel als
Schleife in Reihe mit dem Akku (Spannungsabfall, Induktivität, Vibration, und der Schalter muss ≥ 3 A
können; kleine Schiebeschalter sind für 0,3 bis 0,5 A gebaut).

Vorschlag: **den Schalter nur das Gate schalten lassen.** Ein zweiter P-FET (AO3401A) anti-seriell zu Q1
(Source an Source) als Lastschalter, Gate über 100 k an die Source und über den externen Schalter auf
GND. Dann trägt `J3` Mikroampere, jeder Mini-Schalter oder sogar ein Reed-Kontakt mit Magnet von außen
taugt, und die Kabel führen keinen Servostrom. Q1 bleibt als Verpolschutz, weil die Body-Diode des
Lastschalters sonst im Aus-Zustand leitet. Gleiches für den 1S-Pfad mit Q2. Kosten: zwei SOT-23, vier
Widerstände. Wenn der Schalter im Strompfad bleiben soll: `J3` als JST-XH (3 A) und ein Schalter mit
≥ 3 A Nennstrom.

Gleiches Argument in kleinerem Maßstab: `J4` (Arming, JST-PH 2) trägt den Pyro-Puls (5 A, 20 ms) über
einen 2-A-Kontakt und den externen Arming-Schalter. Als JST-XH ausführen oder ebenfalls über einen
FET schalten (dann wäre die Arming-Information nur noch ein Logikpegel, das widerspricht dem Konzept
„ohne Arming kann die Firmware nichts zünden“; deshalb hier XH und ein kräftiger Schlüsselschalter).
`J8` (Rollmotor, JST-PH 2): bei Blockierstrom über 2 A ebenfalls XH.

### A4. Absicherung: F1 schützt nur die Servo-Schiene

F1 (3 A Polyfuse) sitzt hinter dem Shunt und vor `VSERVO`. Unabgesichert bleiben: der Pyro-Pfad
(`VBAT_ARMED`, J4, J9, J10 und ihre Kabel), der Buck U1, der Schalterweg J3 und der ganze 1S-Pfad.
Ein Kabelscheuer am Arming-Kabel oder am 1S-Kabel ist ein Kurzschluss eines 50-C-LiPo (über 40 A) ohne
Sicherung im Rumpf.

Vorschlag: **je Akku eine Sicherung direkt hinter dem Verpolschutz**, also vor J3:
2S 1812-Polyfuse 3 A Halte- / 6 A Auslösestrom (ein 5-A-Puls von 20 ms geht durch, ein Kurzschluss
löst in Sekunden aus; Widerstand ca. 30 mΩ, 0,1 V bei 3 A), 1S 1812-Polyfuse 2 A (Spitze am Eingang des
Buck-Boost bei 3,0 V und 0,8 A Ausgang: 1,6 A). F1 kann dann entfallen oder bleiben. Wer die 30 mΩ
nicht will, nimmt eine flinke 5-A-Schmelzsicherung (Nano2, 0453-Serie) mit Halter; Polyfuse ist
leichter und braucht keinen Halter.

Dazu ein Firmware-Punkt, der an der Schaltung hängt: Eine E-Match wird beim Durchbrennen gelegentlich
zum Kurzschluss. Dann liegt der 2S-Akku über den AO3400A (SOA: 30 A nur für Mikrosekunden) kurz, und
die Spezifikation erlaubt einen Zündpuls von bis zu 1 s. Vorschlag: **Puls 50 bis 100 ms** und
Abschalten, sobald `PYRO_SENSE` den Durchgang verliert (E-Match offen, also gezündet). Die Polyfuse
reagiert dafür zu langsam; den FET rettet nur die kurze Pulsdauer.

### B1. TPS563201 EN: in Ordnung

Zur Sicherheit nachgesehen, weil EN über 100 k an VIN (bis 8,4 V) liegt: Absolute Maximum am EN ist
19 V, empfohlen bis 17 V, interner Pull-down 1,5 MΩ, Einschaltschwelle 1,6 V. Die 100 k sind richtig,
nichts zu ändern. Ein Teiler als Unterspannungsabschaltung für den 2S-Akku ist hier **nicht**
sinnvoll: Bei einer Servo-Spitze darf der Rollmotor-Treiber nicht abschalten.

### B2. TPS63070: FB2 offen lassen, VSEL schon richtig

FB2 (Pin 6) laut Datenblatt „Leave the pin open or connect to GND if not used“; beides ist zulässig,
der Hinweis aus der Netzlistenprüfung (NC) kann so umgesetzt werden, muss aber nicht. VSEL (Pin 15) liegt
in `circuit.py` bereits an GND, PG (Pin 2) offen: korrekt. PS/SYNC an VIN (PFM bei Teillast) ist für
diese Last (0,4 A) richtig; forced PWM kostet nur Ruhestrom.

### B3. Elkos als THT stehend: Vibration und Bestückung

Drei stehende Radialelkos (1000 µF/10 V, 1000 µF/16 V, 470 µF/10 V, 10 bis 12,5 mm hoch) sind bei den
50 bis 300 Hz der Servos und des Motors die Bauteile mit dem größten Hebel auf ihren Lötstellen. Der
Plan §2.2 hatte schon Polymer in 7343 vorgeschlagen, rev B ist bei THT geblieben.

Vorschlag: **Polymer-Elkos in 7343 (D-Case, 4,3 mm hoch)**, von JLC bestückt: 2 × 470 µF/6,3 V hinter
D1 (A1), 2 × 330 µF/16 V an `VSERVO`, 1 × 470 µF/10 V an `5V_SERVO`. Das senkt die Bauhöhe, spart drei
Handlötstellen und hält Vibration. Wenn THT bleibt: liegend bestücken und verkleben.

### B4. 3,3-V-Insel für IMU und Barometer

IMU und BMP390 hängen direkt an den 3,3 V des Teensy, die derselbe LDO auch für die 600-MHz-CPU liefert
(Laststufen der CPU landen als Ripple auf der Sensorversorgung). Billige Abhilfe: **Ferritperle (z. B.
600 Ω bei 100 MHz, 0603) plus 10 µF** als eigenes Netz `3V3_SENS` für U4, U5 und die beiden
Abblockgruppen. Ein Bauteil und ein Kondensator, kein Platzproblem.

### B5. Verpolschutz 1S mit AO3401A

Bei 3,0 V Zellspannung hat der AO3401A nur Vgs = −3 V, also ca. 80 bis 100 mΩ (Datenblattkurve); bei 1,6 A
Spitze 0,15 V und 0,25 W. Funktioniert, aber knapp. Für den 1S-Pfad lohnt ein Blick auf einen P-FET,
der bei −1,8 V oder −2,5 V spezifiziert ist (SOT-23, LCSC Basic, z. B. DMG2305UX oder AO3407A); am
Bestelltag die Rds(on)-Zeile bei −2,5 V vergleichen. Kein Muss.

## 2. Sensorik, Funk, Signale

### B6. Barometer an SPI statt I²C (Jans Frage „alle Sensoren über SPI“)

Heute: IMU an SPI1, BMP390 und INA219 an I²C (Wire). I²C hat einen Fehlermodus, den SPI nicht hat: Ein
gestörter Slave hält SDA tief und der Bus hängt. Die Teensy-4-Bibliothek (`WireIMXRT.cpp`) fängt das
zwar ab (16 ms Wartezeit, dann Bus-Recovery per Takten, 50 ms Timeout je Transfer), aber jeder solche
Fall kostet bis zu 50 ms, also fünf Regelzyklen, und beide Sensoren am Bus fallen gleichzeitig aus. Das
Barometer liefert die Apogäumserkennung, also den Zündzeitpunkt.

Vorschlag: **BMP390 an SPI1** (4-Draht-Modus: CSB an einen freien Teensy-Pin, z. B. 25; SCK, SDI, SDO mit
der IMU teilen; Adafruit `BMP3XX` kann SPI). Kosten: zwei Leiterbahnen, ein Pin. Der **INA219 bleibt an
I²C** (es gibt ihn nicht mit SPI; SPI-Alternativen wären INA229/INA239, teurer und nicht nötig), aber:
nur Telemetrie, in der Firmware mit Timeout und außerhalb der 100-Hz-Schleife lesen. `J_QWIIC` bleibt
für Erweiterungen. Beides im Design Guide so begründen.

### B7. Summer von Pin 13 auf Pin 37: SPI0 frei für die Erweiterungsleiste

Pin 13 ist SCK0 des Teensy; mit dem Summer dort ist auf `J_EXP` kein vollständiger SPI-Bus mehr
möglich (10, 11, 12 liegen auf der Leiste, 13 fehlt; der Ersatz-SCK0 auf 27 ist von SPI1 belegt). Mit
dem **Summer auf Pin 37** bietet `J_EXP` SPI0 (10/11/12/13), Serial3 (14/15), Serial4 und Wire1 (16/17),
CAN3 (30/31) und vier ADC-Pins (14 bis 17): alles, was ein späterer Sensor für die Landung (ToF/Lidar) oder ein
zweiter IMU-Breakout braucht. Eine Zeile in `Config.h` und `circuit.py`.

### B8. LEDs in Kette, ein Pegelwandler

LED1 und LED2 haben je einen 74AHCT1G125 und je einen Teensy-Pin. **LED1 DOUT an LED2 DIN**, danach
`J_LED`: ein Pegelwandler (dann gleich der SN74LV1T34, Basic bei JLC, statt des Extended-Typs), ein Pin
(6) frei, zwei Bauteile und 3 USD Rüstgebühr weniger. Firmware: eine Kette mit zwei Pixeln statt zwei
Ketten.

### B9. E22 NRST an einen Teensy-Pin

NRST ist laut Ebyte-Tabelle „Low resets the module“, ohne Angabe eines internen Pull-ups. Vorschlag:
**NRST über 10 k an `3V3_RF` und zusätzlich an Teensy-Pin 31** (Open-Drain-Betrieb in der Firmware), damit
ein hängendes Funkmodul im Flug neu gestartet werden kann. Die Pins 20 (M0) und 21 (M1) haben laut
Tabelle schwache interne Pull-ups: während des Teensy-Boots ist das Modul im Konfigurationsmodus,
unkritisch.

### B10. ICM-42688-P RESV-Pins: offener Punkt geschlossen

Die TDK-Pintabelle (DS-000347) sagt: Pin 7 „Connect to GND“, Pins 2, 3, 10, 11 „No Connect or Connect to
GND“. `circuit.py` legt alle fünf an GND: **richtig.** FSYNC (Pin 9) an GND ist für den unbenutzten
Fall ebenfalls korrekt. Abblockung VDD 100 n + 2,2 µ, VDDIO 10 n: wie Datenblatt.

### B11. Teensy VIN und VUSB

Die SS14 von `5V_SYS` nach `TEENSY_VIN` ist genau die Diode, die PJRC für gleichzeitigen USB- und
Fremdbetrieb empfiehlt; die VIN–VUSB-Brücke auf dem Teensy muss **nicht** getrennt werden (USB 5,0 V
gewinnt gegen 4,6 V am VIN, die Diode sperrt rückwärts). Das in `README.md` §9 (Inbetriebnahme) als
Hinweis aufnehmen, damit niemand die Brücke trennt.

### B15. Der Schaltplan ist für das Kollegen-Review nicht lesbar

Der Generator setzt an jeden Pin ein Netzlabel und zeichnet keine Verbindungen; jedes Blatt ist eine
Reihe einzeln stehender Bauteile mit Etiketten (siehe `out/mainboard_schematic.pdf`, Blatt Versorgung).
Für ERC und Netzliste ist das vollwertig, aber ein Reviewer kann keinen Strompfad verfolgen und keinen
Fehler sehen, den die Netzliste nicht schon kennt. Die Tore in `ORDER.md` verlangen genau dieses Review
„anhand des Schaltplan-PDFs“.

Vorschlag: Entweder die Kernblöcke (Versorgung 2S und 1S, ein Pyro-Kanal, IMU) im Generator mit
echten Drähten setzen (Zweipoler neben ihr Zielpad, Verbindung als Draht, Labels nur für Blattgrenzen;
derselbe Ansatz wie `place_passives` auf der Platine), oder das Review auf die Blockbilder des Design
Guides (`power_tree.svg`, `pyro_channel.svg`) plus die Netzlistenprüfung stützen und das sagen. Die
erste Variante ist ein Nachmittag Arbeit und zahlt sich bei jeder späteren Änderung aus.

## 3. Leiterbahnen und Masse (Vorgaben, unabhängig vom Routing-Ergebnis)

### B12. Bahnbreiten: drei Dokumente, drei Zahlen

Spezifikation §8: 2 mm für VBAT/VSERVO/Pyro; `kicad/README.md` §4: 1,2 mm; `mainboard.kicad_pro`:
Klasse *Strom* 1,0 mm, *Rueckstrom* 0,8, *Versorgung* 0,5, *Wandler* 0,25. Nach IPC-2221 (1 oz außen,
10 K Erwärmung) trägt 1,0 mm ca. 2,4 A, 0,5 mm ca. 1,4 A, 0,25 mm ca. 0,9 A. Für den 2S-Pfad reichen
1,0 mm thermisch (Dauerstrom 0,5 A, Spitzen kurz), der Spannungsabfall ist 0,5 mΩ/mm, also 30 mΩ auf
60 mm Weg: so viel wie der Stecker. Akzeptabel, aber die Dokumente müssen eine Zahl nennen.

Nicht akzeptabel ist die Klasse *Wandler*: `VSYS_IN`, `U2_L1`, `U2_L2` mit **0,25 mm** führen den
Spulenstrom des Buck-Boost (im Boost-Betrieb aus 3 V: ca. 1 A Mittelwert, 2,5 A Spitze) und den gesamten
1S-Eingangsstrom. Die 0,25 mm sind nur für den Pin-Austritt am VQFN (0,5 mm Raster) nötig; nach 1 mm
**auf ≥ 0,6 mm aufweiten**, die Spule L2 mit kurzen, breiten Bahnen direkt an die Pins 9/11 (TI-Layout-
Hinweis: Spulen- und Eingangsschleife so klein wie möglich). Im Generator: `VSYS_IN` in die Klasse
*Versorgung*, für L1/L2 Neck-down-Regel oder von Hand.

### B13. Hochstrompfad nicht dem Autorouter überlassen

Freerouting setzt pro Lagenwechsel ein Via und führt Stromnetze als Einzelbahn. Die Checkliste verlangt
≥ 4 Vias je Übergang und beide Außenlagen. Vorschlag: den 2S-Pfad (XT30 → Q1 → Sicherung → J3 → Shunt →
F1 → Servo-Stecker, dazu `VBAT_ARMED` zu J9/J10) im Generator als **F.Cu-Flächen** (Zonen auf den
Netzen `VBAT_PROT`, `VSERVO`, `VBAT_ARMED`) im TVC-Bereich anlegen und die Via-Felder mit `add_plane_vias`
setzen. Ein 0,8/0,4-mm-Via trägt etwa 2 A; der Pyro-Puls will drei.

### A5. Shunt ohne Kelvin-Footprint

`R_SH1` ist ein 2512 mit zwei Pads, die INA219-Eingänge liegen auf denselben Netzen `VBAT_PROT` /
`VBAT_MEAS`. Freerouting schließt IN+ und IN− irgendwo an diese Netze an, etwa am J3-Pin oder am
Polyfuse-Pad, und misst dann Bahn plus Shunt: 5 mm Bahn von 1 mm Breite sind 2,5 mΩ, also 12 % Fehler
bei 20 mΩ, lastabhängig und temperaturabhängig. Die Spezifikation verlangt „Kelvin, vier Pads“.

Vorschlag: **Kelvin-Footprint** (z. B. `Resistor_SMD:R_Shunt_Vishay_WSK2512` oder ein 2512-Footprint
mit zwei zusätzlichen schmalen Sense-Pads) **oder** zwei Netzbrücken (`NetTie_2`) direkt an den
Shunt-Pads, die Sense-Netze `VBAT_PROT_S` / `VBAT_MEAS_S` erzeugen, auf denen nur der INA219 hängt. Dann
kann der Autorouter die Messleitungen nur noch am Shunt abgreifen. Dazu 100 nF zwischen IN+ und IN−
nahe am INA219 (Datenblatt-Empfehlung gegen Servo-PWM-Ripple auf der Messung, derzeit nicht bestückt).

### B14. GND-Konzept: in Ordnung, ein Hinweis

`GND` / `GND_PWR` mit Netzbrücke NT1 am 2S-Minus und die geteilte Lage B.Cu (GND_PWR unter den Aktoren,
5V_SYS sonst) setzen die Vorgabe prüfbar um; In1 durchgehend GND unter der IMU ist richtig. Hinweis:
Die Servo-Signale (`SERVO_*_S`) werden gegen `GND` erzeugt, der Servo sieht sie gegen `GND_PWR`; der
Versatz ist der Spannungsabfall auf der Rückleitung bis NT1, bei 2 A und einer 3,3-mm-Fläche aus 1 oz
unter 20 mV: unkritisch für ein 3,3-V-PWM-Signal. Die Sperrfläche „IMU ohne Vias“ ist nur so groß wie
der Chip (±1,9 × 3 mm); die Spezifikation nennt 5 mm Umkreis. Auf 5 mm vergrößern, soweit die
Buchsenleisten es zulassen.

## 4. Zukunft, Redundanz, Kosten, Fertigung

### C1. Zweiter Antrieb und Landung: was die Platine jetzt schon vorsehen sollte

Für die Landung mit zweitem Motor braucht die Elektronik: einen Zündkanal für Motor 2 (heute: Kanal 2
ist die Reserve für den Fallschirm, danach gibt es keine Reserve), einen Auslöser für die Landebeine
(Servo oder Pyro), einen Höhenmesser über Grund (ToF oder Lidar an I²C oder UART) und Servos, die bei
der Landung an voller Spannung laufen. Vorschlag, alles billig und schon heute im Layout:

- **Vier Pyro-Kanäle** statt zwei (je Kanal ca. 1,5 cm² mit JST-XH; Teensy-Pins sind da). Kanäle 3 und 4
  als DNP bestückbar, die Stecker nur als Footprint.
- `J_SERVO3` per **Lötbrücke zwischen `5V_SERVO` und `VSERVO`** wählbar (ein W5652H-Klasse-Servo für
  die Beine will 8 V) und ein **vierter Servo-Stecker** an `VSERVO`.
- `J_EXP` wie in B7 mit freiem SPI0, zwei UARTs, Wire1 und ADC; `J_QWIIC` für den ToF-Sensor.
- DRV8833 `nSLEEP` an einen Teensy-Pin statt fest an 5V_SERVO: Dann kann die Firmware den Rollmotor
  hart abschalten (Landung, Fehlerfall), heute bleibt er allein an den PWM-Pins.
- Strombudget 2S bei der Landung: zwei TVC-Servos unter Last, Beine, Zündung; das 850-mAh-50-C-Paket
  schafft das, 450 mAh nicht. In `ORDER.md` 0.7 festlegen.

### C2. Redundanz und mehrere Sensoren gleichen Typs

- **IMU:** Ein zweiter ICM auf der Platine bringt wenig: Zwei Sensoren gemittelt senken das weiße
  Rauschen um √2, aber der Fehler im 100-Hz-Regelkreis kommt aus Vibration (Aliasing) und Gyro-Bias,
  nicht aus dem Sensorrauschen; der 42688-P mit 50-Hz-Filter liegt weit unter dem, was der Regler
  auflöst. Und nur ein Sensor kann auf der Achse liegen. Redundanz an der richtigen Stelle sind der
  Watchdog und der Zustandsspeicher (Spezifikation §10), die Trennung der Versorgungen (erledigt) und
  die Rampenkalibrierung.
- **Barometer:** Das ist der Sensor, dessen Ausfall die Zündung verfehlt. Ein **zweiter BMP390 als
  DNP-Footprint** (2 × 2 mm, an SPI1 mit eigenem CS, oder an I²C unter Adresse 0x76 über SDO an GND)
  kostet nichts im Layout und erlaubt später Mittelung oder Plausibilitätsprüfung. Zweite Quelle für
  das Apogäum ist ohnehin die integrierte Vertikalgeschwindigkeit aus der IMU (Kalman); die Firmware
  sollte beide verlangen.
- **Pyro:** Beide Kanäle auf denselben Kolben (zwei E-Matches in einer Ladung) ist die übliche
  Redundanz; mit C1 bleibt dafür Platz.

### C3. Kosten und Fertigung bei JLCPCB

- 4 Lagen und ENIG sind durch die LGA-Gehäuse und die Masseführung gerechtfertigt; 2 Lagen wären
  ca. 25 USD billiger und würden das Massekonzept kosten. Bleibt so.
- Extended-Teile senken: B8 (ein SN74LV1T34 Basic statt zwei 74AHCT1G125), SMBJ12CA und Polyfuse am
  Bestelltag auf Basic-Alternativen prüfen (SMAJ-Serie, Bourns MF-MSMF). Die vier Kernteile (IMU,
  Baro, TPS63070, E22) bleiben Extended.
- Polymer-Elkos (B3) sind bei JLC meist Extended (3 USD je Typ), sparen aber drei THT-Lötstellen und
  die Elko-Bestellung in Deutschland; netto etwa gleich teuer, mechanisch besser.
- WS2812B-2020 kann Standard-PCBA erzwingen (ORDER.md kennt das Risiko): Am Bestelltag prüfen; sonst
  5050-Gehäuse (Basic) nehmen, Platz ist am Spitzen-Ende vorhanden.
- Die Stückzahl 5/2 ist richtig; eine dritte bestückte Platine kostet nur Bauteile (ca. 25 USD) und
  ist die billigste Versicherung gegen einen Bestückungsfehler.

### C4. Logo

KiCad kann Bitmaps und SVGs als Footprint auf den Bestückungsdruck oder als Kupfer/Lötstopp-Öffnung
(bei ENIG also als Goldfläche) bringen: *Image Converter* (bitmap2component) in der KiCad-GUI erzeugt
aus einer PNG/SVG einen Footprint, den `gen_pcb.py` wie jedes andere Bauteil laden und platzieren kann
(`lib/mainboard.pretty/Logo.kicad_mod`, Referenz unsichtbar, von BOM und CPL ausgeschlossen). Platz:
am Spitzen-Ende rechts, wo heute „MISSION SPACE / MAINBOARD REV B / 2026-10“ steht, ca. 10 × 10 mm; die
Fläche unter dem Teensy ist nur bei gezogenem Modul sichtbar. Für den Druck: Linien ≥ 0,15 mm, keine
Fläche über Pads. Das Logo selbst gibt es noch nicht; bis dahin ein Platzhalter-Rechteck im Generator,
damit die Fläche frei bleibt.

### C5. Dokumentation nachziehen

- `README.md` §8 (2 mm) und `kicad/README.md` §4 (1,2 mm) auf den Wert aus dem Projekt bringen (B12).
- `README.md` §7 Stückliste: SMBJ12CA statt SMBJ12A, die Sicherungen aus A4, 220 Ω Servo-Widerstände,
  NT1.
- `ORDER.md` 0.18 führt noch den Taster SW_RST, der entfallen ist; 0.17 die THT-Elkos (B3).
- Design Guide §13: Frage 9 (Sicherung im 1S-Pfad) mit A4 beantworten, Frage 10 mit B2/B9/B10.

## 5. Layout (Stand Commit `7acdfd2`, 21.10.2026 17:50)

Geprüft mit einem eigenen Skript auf einer Kopie der Platine (`review_check_layout.py`, läuft mit
KiCads Python: Bahnbreiten, Lagen und Vias je Stromnetz, Bahnweg der INA219-Messleitungen zum Shunt,
Umfeld der IMU, Bauteile am Rand und unter dem Teensy, Zonen) sowie `kicad-cli pcb drc` mit den
Projektregeln. Eigener DRC-Lauf: **0 Fehler, 3 offene Verbindungen** (wie im `kicad/README.md` §5.4
beschrieben), 176 Warnungen (125 Bestückungsdruck-Überlappungen, 42 Druck über Kupfer, 5
Bibliotheks-Footprints, 3 Schriftstärken, 1 Via ohne zweite Verbindung). Platzierung: alle 134
Teile, keine Überschneidung, am Rand (|u| > 25) nur flache SMD-Teile, unter dem Teensy nur der IMU-Block.
Das Gerüst stimmt: Teensy mittig, IMU auf der Achse, Stecker an den Stirnseiten, Wandler links,
Sensorik rechts, Funkmodul am Spitzen-Ende, In1 als durchgehende Masse. Die Mängel liegen im
Autorouting der Stromnetze.

### A6. Die 2S-Stromnetze laufen zur Hälfte auf der Innenlage In2 (0,5 oz)

Gemessene Bahnlängen je Lage (mm): `VBAT_PROT` 57 außen / **82 innen**, `VBAT_MEAS` 57 / 51, `VSERVO`
26 / 15, `VBAT_ARMED` 29 / 30, `PYRO1_NEG` 9 / 9, `PYRO2_NEG` 15 / 11, `VBAT2_REV` 3 / 19. Die
Spezifikation §8 verlangt die Stromnetze auf beiden Außenlagen (1 oz); In2 hat 0,5 oz, eine 1-mm-Bahn
trägt dort ca. 1,4 A bei 10 K und hat 1 mΩ/mm. Die 82 mm `VBAT_PROT` auf In2 sind 80 mΩ, bei einem
Pyro-Puls 0,4 V. Thermisch überlebt das, die Vorgabe ist aber verfehlt, und jede Lagenwechsel-Stelle
hat genau **ein** Via (0,8/0,4 mm, ca. 2 A) statt der geforderten vier.

Dazu kommt der Weg: `VBAT_PROT` wechselt bei (4,6 | 47,5) auf In2 und bei (4,4 | 79,5) zurück, läuft also
**32 mm lang in 4,5 mm Abstand an der IMU (0 | 60,5) vorbei**, mit dem Pyro- und Servostrom darauf. Die
Checkliste verlangt 5 mm Freiraum von Hochstrombahnen auf allen Lagen.

Vorschlag: Stromnetze für Freerouting auf F.Cu beschränken (Netzklasse mit Lagenregel im DSN, oder im
Generator als F.Cu-Flächen vorab ziehen, B13) und die Verbindung zur Spitze (`VBAT_PROT` → J4 Arming) als
breite Bahn am rechten Rand neben der GND_PWR-Rückleitung führen, nicht durch die Mitte.

### A7. 1S-Zuleitung: 77 mm mit 0,19 bis 0,25 mm

`VSYS_IN` (J3 → Eingangskondensatoren → U2) ist 54 mm auf F.Cu und 22 mm auf In2 lang, überall 0,19 bis
0,25 mm breit: ca. 150 mΩ. Bei 1 A Eingangsstrom (Dauerlast aus 3,3 V) fallen 0,15 V und 0,15 W in der
Bahn, bei 1,6 A Spitze 0,24 V; der Buck-Boost muss das aus dem Akku nachholen. Das ist der Punkt aus B12,
jetzt mit Zahlen: `VSYS_IN` in die Klasse *Versorgung* (≥ 0,6 mm), nur die letzten Millimeter am
VQFN-Pin schmal. `U2_L1` / `U2_L2` sind kurz (je 4,3 mm), dort reicht es, die Spulenpads breit
anzubinden.

### A8. 5V_SERVO mit 0,15-mm-Stücken

`5V_SERVO` (Rollmotor bis 1 A, Fallschirm-Servo 0,65 A) hat 30 mm unter 0,45 mm, darunter 7 mm mit
0,15 mm am 470-µF-Elko (12,5 | 41,5) und zwei weitere 0,15-mm-Stücke am Buck. 0,15 mm tragen 0,6 A bei
10 K; bei 1,7 A Spitze sind das über 50 K Erwärmung auf dieser Strecke. Freerouting verjüngt an Pads
auf die Mindestbreite; die Mindestbreite der Klasse *Versorgung* im Projekt auf 0,4 mm setzen (nicht
die globale 0,09) und die Elko-Pads direkt anbinden.

### A5 (Layout-Befund). Kelvin-Abgriff: der Minus-Eingang erreicht den Shunt nach 58 mm Bahn

Bahnweg von U6 Pin 8 (IN+) zum Shunt-Pad 1: 16 mm; von U6 Pin 7 (IN−) zum Shunt-Pad 2: **58 mm**, bei
10 mm Luftlinie. Die Messleitung hängt also irgendwo am `VBAT_MEAS`-Netz (nächste Pads: F1 in 12 mm, die
Buck-Eingangskondensatoren) und misst Bahn plus Shunt. Das bestätigt A5: Kelvin-Footprint oder
Sense-Netze mit Netzbrücken, dann kann der Autorouter nichts falsch machen.

### B16. Umfeld der IMU

Im Radius 5 mm um die IMU liegen 14 Vias, darunter die Signal-Vias `IMU_MISO`, `IMU_CS`, `MOT_FAULT`,
`MOT_IN1`; auf In2 laufen dort `EXP_D25` und `EXP_D12` (je 22 mm), `MOT_FAULT`, `LED1/2_DATA` und
`MOT_IN1` (20-kHz-PWM des Rollmotors, 2 mm vom Chip). Die Sperrflächen „IMU ohne Vias“ (±1,9 × 3 mm)
und „IMU ruhige Masse“ (±2,4 × 4 mm) decken nur den Chip ab. Logikpegel stören einen MEMS-Sensor kaum,
aber die Checkliste sagt 5 mm, und die Durchleitungen fremder Signale (Erweiterungsleiste, Motor, LEDs)
unter dem Sensor sind unnötig: Sperrfläche auf 5 mm Radius für Vias und für In2/B.Cu-Bahnen, nur die
vier SPI-Leitungen und INT dürfen hinein (sie gehen direkt zu den Teensy-Pins daneben).

### B17. Funkmodul: Randabstand und IPEX-Buchse

Die Randpads des E22 liegen **0,2 mm** von der Platinenkante; JLC fräst mit ±0,2 mm. Modul 0,3 bis 0,5 mm
nach innen (die Teensy-Pads auf der anderen Seite sind 0,53 mm entfernt; wenn das nicht reicht, das
Modul 1 mm zur Spitze schieben, dort ist Platz). Die IPEX-Buchse sitzt an der Ecke zur Teensy-Seite,
direkt neben der 8,5 mm hohen Buchsenleiste und unter dem 1,3 mm Überhang des Teensy: prüfen, ob der
u.FL-Stecker mit gestecktem Teensy noch aufgedrückt werden kann und das Pigtail nach oben wegkommt.
Sonst das Modul um 180° drehen (Buchse an der Außenkante, Pigtail läuft an der Kante zur Spitze).

### B18. Bauhöhe, Unterseite, Luke

- C19 (Ø 8 mm, 12 mm hoch) reicht bis u = −25,4, also 0,4 mm in die 5-mm-Zone am Rand. Abstand zur
  M2-Stange (−29,5 | 7): 3,1 mm, geht. `outline.py` rechnet mit −24; die Hülle dort auf den Ist-Stand
  setzen und die Prüfung erneut laufen lassen. Mit B3 (Polymer 7343) erledigt sich der Punkt.
- Unterseite: Die Lötstifte der Buchsenleisten, des XT30 und der XH-Stecker stehen 2 bis 3 mm vor und
  liegen über den LiPo-Pouches. Stifte kürzen und eine Isolierlage (1 mm Schaum oder Kapton-Platte)
  zwischen Platine und Akkuträger einplanen. Gehört in die CAD-Session (Träger).
- Der Summer BZ1 (Ø 12 mm) endet bei u = 7, der USB-Freiraum bei u = 8. Micro-B-Überformungen sind 10 bis
  12 mm breit; den Freiraum auf ±6,5 mm des Steckers plus Finger prüfen (1:1-Ausdruck mit echtem Kabel)
  und den Summer 2 mm nach außen rücken.

### B19. Bestückungsdruck und Fertigungsdaten

- 167 Druckwarnungen, darunter „MISSION SPACE / MAINBOARD REV B / 2026-10“ über J9 und D2; die
  Textgruppe an die Stelle des späteren Logos (C4) setzen, Schrift ≥ 0,15 mm Strich (DRC meldet 0,078
  und 0,091 mm bei „IMU Z+“, „X“, „Y“).
- Die EasyEDA-Footprints zeichnen Siebdruck über Pads (42 Warnungen); JLC schneidet das weg, in den
  Gerbern sieht es aber unsauber aus: in `build_lib.py` die Linien auf F.Fab verschieben.
- Pin-1-Marken der JST-Stecker und S/+/− sind da; bei J3 fehlt die Angabe, welches Paar 1S und welches
  2S ist, wenn der Text „SW 1S 1S 2S 2S“ über den Pins liegt (steht jetzt daneben, Reihenfolge prüfen).
- Vor den Gerbern: die drei offenen Verbindungen, A6 bis A8, dann `./make.sh drc` ohne Warnungen in
  den Kategorien Kupfer und Verbindungen; Druckwarnungen dürfen bleiben.

### Was im Layout gut gelöst ist

In1 als volle Masse ohne Bahnen; GND_PWR-Rückleitung zu den Pyro-FETs als 3,3-mm-Streifen auf B.Cu
(1 oz, reicht für den Puls); 109 Plane-Vias direkt an den Abblockpads; Abblockkondensatoren am
richtigen Pin; die Spulen ohne Kreuzung an SW/L1/L2; das Funkmodul auf Masse ohne Signale darunter;
Stecker bündig und axial, Beschriftung vorhanden; JLC-Auftragsnummer platziert. Das Freerouting-Ergebnis
ist für Signale brauchbar; für die Stromnetze ist der Generator-Ansatz mit vorgezogenen Flächen (B13)
der richtige nächste Schritt, nicht Handarbeit in der GUI, sonst verliert `make.sh pcb` seine
Gültigkeit (README §3).

## 6. Reihenfolge, die ich vorschlage

1. Schaltung (`circuit.py`): A1, A2, A4, A5, B2, B4, B7, B8, B9, C1 (vier Pyro-Kanäle, Jumper an J_SERVO3,
   nSLEEP), B6 (BMP390 an SPI) nach Jans Entscheidung; A3 nach Jans Entscheidung (FET-Schalter).
2. Generator (`gen_pcb.py`): Stromnetze als Flächen auf F.Cu mit Via-Feldern, Lagenbeschränkung für
   Freerouting, Mindestbreite je Klasse, Sperrflächen 5 mm um die IMU, Funkmodul 0,5 mm vom Rand,
   Logo-Platzhalter.
3. `./make.sh`, dann die Prüfungen von §5 wiederholen (`review_check_layout.py`), offene Verbindungen
   schließen, Papierausdruck.
4. Dokumente nachziehen (C5), Review mit dem Kollegen anhand von Blockbildern und Lagenbildern (B15).
