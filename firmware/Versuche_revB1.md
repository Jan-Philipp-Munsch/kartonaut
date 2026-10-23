# Versuchsanleitungen Mainboard rev B1: Vermessung und Kalibrierung

Stand 2026-10-23. Zwölf Versuche, die am Tisch nacheinander laufen, jeder nach derselben Gliederung
wie E02 (`docs/experiments/E02_TVC_Charakterisierung_revB1.md`): Ziel, Material, Aufbau, Vorbereitung
an der Konsole, was gefahren und gemessen wird, Läufe und Aufnahme, Auswertung, Protokoll, Grenzen.
Die Konsole `revb_test` stellt ihre Rückfragen selbst (`WAIT`, `ASK`, `CONFIRM`); die Anleitung sagt,
was du dabei in der Hand hältst. Zeilenformat und Gesamtablauf: `Tischtest_revB1.md`.
Steckerbelegungen stammen aus `circuit.py` (Branch `claude/rev-b1`).

**Aufnahme**: jeder Lauf ist ein Aufruf von `python tools/bench_test.py --skip-rails --commands "..."`
(oder die Befehle von Hand in `pio device monitor`). Der Bericht liegt danach in
`test_reports/bench_<datum>.md` und `.json` mit allen `TEST`- und `CAL`-Zeilen und dem ganzen
Konsolenmitschnitt. Was du mit dem Multimeter misst, gibst du bei `ASK` ein, es steht im Bericht.
Die Protokollfelder unten sind das, was du zusätzlich von Hand notierst.

## Grundausstattung

| Gerät / Material | Wofür |
|---|---|
| Labornetzteil, zwei Kanäle oder zwei Geräte, einstellbare Strombegrenzung | 1S-Zweig (3,7–4,2 V) und 2S-Zweig (7,4 V) |
| Multimeter (Spannung bis 20 V, Strom bis 2 A, Durchgang) | Testpunkte, ADC- und INA-Abgleich, Pyro-Durchgang |
| 1S-LiPo und 2S-LiPo (optional statt Netzteil) | Akkuspannungen wie im Flug, Magnetometer ohne Netzteilkabel |
| Kabel: JST-PH 2-polig (J_BAT1), XT30 (J_BAT2), JST-PH 4-polig (J_SW) oder Lötzinn für JP1/JP2 | Versorgung |
| Schlüsselschalter oder Drahtbrücke an JST-XH 2-polig | J_ARM |
| Glühlampe 12 V / 5 W (oder 6 V / 3 W) mit JST-XH 2-polig, ersatzweise 2 Ω / 10 W | Pyro-Last. **Nie eine Ladung.** |
| Leistungswiderstand 22 Ω / 5 W (oder 10 Ω / 10 W) mit JST-XH 3-polig | INA239 unter Last |
| Servos, die für die 2S-Spannung freigegeben sind (VSERVO liegt direkt am 2S-Akku, bis 8,4 V) | Servotest und Trimm |
| Rollmotor mit JST-XH 2-polig | Motortest |
| LoRa-Antenne (IPEX) **vor dem ersten Senden** anstecken, Bodenstation mit E22 auf demselben Kanal | LoRa |
| GPS-Modul (u-blox) an JST-GH 4-polig, Platz mit freier Sicht zum Himmel | GPS |
| microSD, FAT32 oder exFAT, im Teensy-Slot | SD |
| USB-Kabel zum Teensy, PC mit `pio` und `pyserial` | Konsole |
| Holztisch, Winkel oder Buch als Anschlag, Regalbrett (1 m), Schale zum Abdecken | Lagen, Höhenprobe, Luftzug |
| Raumthermometer, nach Möglichkeit Hygrometer | Vergleich für IMU-, BMP390-, SHT40-Temperatur und Feuchte |

Allgemeine Regeln:

- **Beim Einschalten erst 1S** (Netzteil 4,0 V, Strombegrenzung 100 mA; nach V01 500 mA). Der Teensy
  läuft nur bei versorgtem 1S-Zweig, USB liefert nur Daten.
- **2S nur, wenn der Versuch es braucht** (V06 bis V09): Netzteil 7,4 V, Strombegrenzung 1 A, für
  Motor und Pyro 3 A. Ohne 2S melden die betroffenen Prüfungen `SKIP`.
- **Neustart des Teensy**: 1S aus und wieder ein. Über USB geht es nicht.
- Vor jedem Flashen: `python tools/check_board_pins.py <circuit.py von claude/rev-b1>`.
- `q` in der Konsole bricht eine laufende Messung ab. Nach jedem Befehl stehen Servos ohne Puls,
  der Motortreiber schläft, Pyro ist tief.
- Kalibrierwerte liegen nach dem Befehl im RAM; erst `cal save` schreibt sie ins EEPROM. Jeder
  Kalibrierversuch endet deshalb mit `cal save`, und `cal show` nach einem Neustart zeigt, ob es da ist.

Protokollkopf für jeden Lauf: Datum, Platine (Nummer, Bestückungsstand), Firmware-Commit,
Versorgung (Akku oder Netzteil, eingestellte Spannung und Begrenzung), Raumtemperatur, Name.

---

## V01 Versorgung ohne Teensy

**Ziel**: alle Schienen und beide Lastschalter prüfen, bevor der Teensy gesteckt wird.

**Material**: Netzteil (zwei Kanäle), Multimeter, Versorgungskabel, Lötzinn für JP1/JP2 oder J_SW-Kabel.
**Teensy ausgesteckt.**

**Aufbau**:
1. Netzteil Kanal 1: 4,0 V, Strombegrenzung 100 mA, an **J_BAT1** (JST-PH, Pin 1 = Plus, Pin 2 = GND).
2. **JP1** („SJ 1S“) brücken oder an **J_SW** Pin 1 und 2 verbinden (Schalter 1S).
3. Netzteil Kanal 2: 7,4 V, 100 mA, an **J_BAT2** (XT30, Pin 1 = Plus), **JP2** brücken oder J_SW
   Pin 3 und 4 verbinden. Kanal 2 noch aus.
4. Multimeter mit Minus an TP GND.

**Vorbereitung an der Konsole**: keine (kein Teensy). `python tools/bench_test.py` startet mit der
Spannungsabfrage und fragt die Werte in der Reihenfolge der Tabelle unten ab; leer lassen = übersprungen.

**Was gemessen wird**: Kanal 1 ein, Strom ablesen, vier Testpunkte messen; dann Kanal 2 ein, Strom
ablesen, zwei Testpunkte; dann Schalterprobe: JP1 öffnen (bzw. J_SW 1-2 trennen), VSYS_IN muss auf
0 V fallen; dasselbe mit JP2 und VBAT_PROT; beide wieder schließen.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | nur 1S | `python tools/bench_test.py --no-2s` (Abfrage, dann Enter für den Teensy noch nicht drücken, Strg+C) |
| 2 | 1S und 2S | `python tools/bench_test.py` |

**Auswertung** (Sollwerte, `bench_test.py` prüft sie und schreibt sie in den Bericht):

| Messung | Soll | Hinweis |
|---|---|---|
| Strom 1S ohne Teensy | < 60 mA | mehr: Kurzschluss, verdrehtes SOT-23, falsches Bauteil; sofort aus |
| TP VSYS_IN | Netzteil minus < 0,1 V | hinter Verpolschutz Q2 und Lastschalter Q7 |
| TP 5V_SYS | 4,85–5,15 V | TPS63070, FB-Teiler 680 k / 130 k |
| TP 3V3_RF | 3,20–3,40 V | LDO U3 |
| TP 3V3_EXP | 3,20–3,40 V | LDO U14 |
| Strom 2S ohne Last | < 10 mA | nur Teiler und INA239 |
| TP VBAT_PROT | 2S minus < 0,1 V | hinter Q1, F1, Q6 |
| TP VSERVO | VBAT_PROT minus < 0,05 V | hinter dem 20-mΩ-Shunt |
| Schalterprobe | VSYS_IN bzw. VBAT_PROT auf 0 V | Lastschalter trennt |

Abbruch: ein Wert außerhalb → nicht weiter, Bauteil suchen.

**Protokoll**: acht Spannungen, zwei Ströme, Schalterprobe, Netzteiltyp.

**Grenzen**: Ohne Last sagt der Versuch nichts über das Verhalten unter Strom (Buck-Boost bei 1 A,
LDO bei LoRa-Sendepuls); das zeigen V10 (3V3_RF) und V12 (SD-Schreiben) am Netzteilstrom.

---

## V02 Analogmux und ADC-Teiler

**Ziel**: alle acht Mux-Kanäle, Akkuspannungen, ARM-Pegel, Durchgang Pyro 1–4; Teilerfaktor je Kanal
gegen das Multimeter.

**Material**: Netzteil 1S (500 mA) und 2S (1 A), Multimeter, J_ARM-Brücke oder Schlüsselschalter, zwei
Lämpchen mit XH-2-Stecker.

**Aufbau**: wie V01 mit Teensy, USB verbunden, `pio run -e revb_test -t upload`. J_ARM: XH, Pin 1
VBAT_PROT, Pin 2 VBAT_ARMED. Lämpchen an J_PYRO1 und J_PYRO2 (Pin 1 VBAT_ARMED, Pin 2 PYROn_NEG).

**Vorbereitung an der Konsole**:
```
status          1S-, 2S-, ARM-Spannung, Bausteine
mux             erste Übersicht aller acht Kanäle
```

**Was gemessen wird**: `mux` liest GND-Kanal (Y7), 1S, 2S, ARM und die vier Pyro-Sense-Kanäle über
den 74HC4051 (12 bit, 4-fach gemittelt, Teiler 100 k / 33 k, Vollausschlag 13,3 V). `cal adc` liest
einen Kanal 16-mal, nennt den Teensy-Wert und fragt nach dem Multimeter; Faktor = Multimeter / Teensy.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | nur 1S | `--commands "mux"` → 2S-, ARM-, Pyro-Zeilen `SKIP` |
| 2 | 2S, ARM aus, Lämpchen gesteckt | `--commands "mux"` → ARM „sicher“, Pyro `SKIP` „ARM nicht scharf“ |
| 3 | 2S, ARM ein, Lämpchen gesteckt | `--commands "mux"` → ARM „SCHARF“, Pyro 1/2 „Durchgang“, 3/4 `SKIP` DNP |
| 4 | wie 3, Lämpchen abgezogen | `--commands "mux"` → Pyro 1/2 „offen“ |
| 5 | 2S, ARM ein | `--commands "cal adc,cal save"`: Multimeter an J_BAT1 Pin 1 (Kanal 4), J_BAT2 Pin 1 (Kanal 5), J_ARM Pin 2 (Kanal 6), jeweils gegen GND |
| 6 | optional, ARM ein, ohne Lämpchen | `--commands "cal adc 0,cal adc 1,cal save"`: Multimeter an J_PYRO1/2 Pin 2 |

**Auswertung**:

| Zeile | Soll |
|---|---|
| `mux_gnd` | < 0,05 V (Nullpunkt des ADC) |
| `mux_vbat1` | Netzteil ± 0,05 V |
| `mux_vbat2` | Netzteil ± 0,05 V |
| `mux_arm` | ≈ 2S bei ARM ein, < 0,5 V bei ARM aus |
| `mux_pyro1/2` | „Durchgang“ bei Lämpchen und ARM ein (Sense > 80 % ARM), „offen“ ohne Lämpchen |
| `cal_adc4/5/6` | Faktor 0,98–1,02 (1-%-Widerstände); 0,9–1,1 wird übernommen, darüber nicht |

Faktor außerhalb 0,98–1,02 bei allen Kanälen gleich: Referenz des ADC (3,3 V vom Teensy) weicht ab,
das ist normal und wird so übernommen. Nur ein Kanal daneben: Widerstand prüfen.

**Protokoll**: Teensy- und Multimeterwert je Kanal, Faktoren, Durchgangsprobe mit und ohne Lämpchen,
welches Multimeter.

**Grenzen**: Der Faktor gilt für den Zustand ohne Last; die Teiler sitzen vor den Lastschaltern, Lastströme
ändern nichts. Mux-Einschwingzeit (5 µs plus verworfene Wandlung) ist auf der Platine noch nicht
bestätigt; zeigt `mux_gnd` nach einem hohen Kanal > 0,05 V, Wartezeit in `BusRevB.cpp` erhöhen.

---

## V03 IMU

**Ziel**: Erkennung, Datenrate, Werksselbsttest, Gyro-Nullpunkt mit Temperatur, Beschleunigungs-Offset
und -Skalierung aus sechs Lagen.

**Material**: nur 1S. Ebene, feste Unterlage (Tischplatte), Winkel oder Buch als Anschlag, Raumthermometer.

**Aufbau**: Platine flach auf dem Tisch, Bestückseite (Teensy) oben, USB-Kabel ohne Zug. Für die Lagen
die Platine an den Anschlag stellen, Kanten laut Ansage; Kabel so, dass es in keiner Lage zieht.

**Vorbereitung an der Konsole**:
```
imu             Erkennung, Konfiguration, Datenrate, Ruhe, Selbsttest
cal show        bestehende Werte (gyro_bias_dps, acc_offset_ms2, acc_scale)
```

**Was gemessen wird**: `imu`: WHO_AM_I, Flugkonfiguration zurückgelesen, neue Sätze in 500 ms (Soll 1 kHz),
300 ms Ruhe (|a|, |ω|), Werksselbsttest (Gyro ±250 °/s, Accel ±2 g, 200 Sätze mit und ohne
Testsignal, Vergleich mit dem Werkswert). `cal gyro <s>`: Mittel und Standardabweichung über die Dauer,
Neustart bei > 3 °/s Spanne. `cal acc`: sechs Lagen je 1,5 s, Offset = (max + min)/2, Skalierung =
2 g / (max − min) je Chip-Achse.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | flach, ruhig | `--commands "imu"` |
| 2 | flach, 30 s nicht berühren | `--commands "cal gyro 30,cal save"` |
| 3 | sechs Lagen nach Ansage | `--commands "cal acc,cal save"` |
| 4 | optional, Platine 10 min erwärmt (Handwärme, Lampe) | `--commands "cal gyro 20"` ohne save |
| 5 | Kontrolle | `--commands "imu"`: `imu_rest` mit kalibrierten Werten plausibel |

Lagen für Lauf 3, die Konsole sagt sie an: 1 flach, Bestückseite oben · 2 flach, Bestückseite unten ·
3 hochkant auf der langen Kante mit dem Teensy-USB · 4 gegenüberliegende lange Kante · 5 hochkant
auf der kurzen Kante mit der Spitze (GPS/J_STACK) · 6 gegenüberliegende kurze Kante. Jede Lage ruhig
halten, dann Enter; „bewegt, noch einmal“ wiederholt die Lage.

**Auswertung**:

| Zeile | Soll |
|---|---|
| `imu_whoami` | 0x47 |
| `imu_rate` | 900–1100 Hz |
| `imu_rest` | \|a\| 9,0–10,6 m/s², \|ω\| < 5 °/s |
| `imu_selftest_gyro` | Verhältnis 0,5–1,5 je Achse, Offset < 20 °/s |
| `imu_selftest_acc` | Verhältnis 0,5–1,5 je Achse |
| `cal_gyro` | Nullpunkt je Achse < 2 °/s (typisch < 1), Rauschen < 0,2 °/s |
| `cal_acc` | Offset je Achse < 0,3 m/s², Skalierung 0,98–1,02 |
| Lauf 4 gegen 2 | Nullpunktänderung je Grad notieren; > 0,05 °/s je K ist für den Flug relevant |

Selbsttest `FEHL` bei sonst guten Werten: wiederholen, die Platine darf während der 2 s nicht angestoßen
werden; bleibt es, Chip verdächtig. „Achse nicht nach oben und unten gesehen“: eine Lage war schief
oder doppelt.

**Protokoll**: WHO_AM_I, Datenrate, Selbsttestwerte, Nullpunkt mit Temperatur, sechs Lagenwerte (aus den
`INFO`-Zeilen), Offset und Skalierung, Raumtemperatur.

**Grenzen**: Die Grenzwerte des Selbsttests (50–150 % des Werkswerts) sind aus dem TDK-Referenztreiber,
nicht an dieser Platine bestätigt. Ein Nullpunkt bei einer Temperatur; der Temperaturgang wird nur
protokolliert, die Firmware kompensiert ihn noch nicht. Die Skalierung aus sechs Lagen trifft nur die
Hauptachsen, keine Querempfindlichkeit.

---

## V04 Magnetometer und Achszuordnung

**Ziel**: LIS3MDL erkennen und selbsttesten, Hard- und Soft-Iron, Achsen von IMU und Magnetometer zum
Raketenkörper.

**Material**: 1S-Akku (statt Netzteilkabel), Holztisch, 1 m Abstand zu Netzteil, Monitor, Lautsprecher,
Stahl; keine Werkzeuge in der Nähe. Für die Gegenprobe ein Kompass oder Smartphone-Kompass.

**Aufbau**: Platine am USB-Kabel frei in der Hand drehbar, Kabel lang genug für alle Drehungen,
Akku mit Klebeband auf der Platine (bewegt sich mit, sonst verfälscht das Akkukabel nichts, der Akku
selbst ist unmagnetisch).

**Vorbereitung an der Konsole**:
```
mag             Erkennung, Konfiguration, Feld, Selbsttest
cal show        mag_offset_gauss, mag_soft_iron, imu_axis_map, mag_axis_map
```

**Was gemessen wird**: `mag`: WHO_AM_I, 80 Hz / ±4 gauss / UHP, 250 ms Mittel, |B| nach aktueller
Kalibrierung, Selbsttest nach AN4602 (±12 gauss, Differenz mit und ohne Testsignal). `cal mag <s>`:
Proben während der Drehung (bis 1200, gleichmäßig ausgedünnt), Ellipsoid-Fit mit neun Parametern →
Offset, Soft-Iron-Matrix, Feldbetrag, Residuum, belegte Oktanten. `cal axes`: Teil 1 Spitze nach
oben (Chip-Achse mit +1 g = Körper +z), Teil 2 Körper +x nach oben, Teil 3 20 s Drehung: Magnetometer
gegen die Drehrate der zugeordneten IMU, 24 rechtshändige Kandidaten, Eindeutigkeit = Fehler des
zweitbesten durch Fehler des besten.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | Platine flach, ruhig | `--commands "mag"` |
| 2 | 60 s langsam drehen, alle Richtungen, auch über Kopf, Achten in die Luft | `--commands "cal mag 60,cal save"` |
| 3 | Spitze nach oben, dann +x nach oben, dann 20 s zügig drehen (eine Umdrehung je 2 s) | `--commands "cal axes,cal save"` |
| 4 | Gegenprobe: Spitze nach Norden, Platine waagerecht | `--commands "mag"` |
| 5 | optional Störung: 2S und ein Servo-Durchlauf während `mag` | `--commands "servo 1 sweep"` in einem zweiten Fenster, parallel `mag` |

„Spitze“ ist das Ende mit J_GPS und J_STACK, so wie die Platine in der Rakete sitzt. Welche Seite
**Körper +x** ist, legt Jan fest (offene Frage 1 in `Tischtest_revB1.md`); bis dahin ins Protokoll,
welche Seite genommen wurde.

**Auswertung**:

| Zeile | Soll |
|---|---|
| `mag_whoami` | 0x3D |
| `mag_read` | \|B\| 0,2–0,7 gauss unkalibriert (bis 1,5 hinnehmbar), nach Lauf 2 0,4–0,55 gauss |
| `mag_selftest` | Differenz X/Y 1,0–3,0 gauss, Z 0,1–1,0 gauss |
| `cal_mag` | Oktanten 8/8, Residuum < 5 % (bis 10 % übernommen), Achsenverhältnis < 1,5, Feld 0,2–0,7 gauss |
| `cal_axes_imu` | Zuordnung passt zur Lage des ICM auf der Platine (Datenblatt-Pfeil gegen Spitze) |
| `cal_axes_mag` | Eindeutigkeit > 2 (gut > 5) |
| Lauf 4 | kalibrierte Komponente in Richtung Spitze zeigt das horizontale Feld (ca. 0,2 gauss in Deutschland), die vertikale Komponente ca. 0,44 gauss nach unten (Inklination 65°) |

`cal_mag` `FEHL` mit Oktanten < 8: zu wenig über Kopf gedreht. Residuum > 10 %: Störfeld in der Nähe
oder Platine während der Drehung verbogen (USB-Stecker nicht als Griff nehmen).

**Protokoll**: Selbsttestdifferenzen, Offset, Feldbetrag, Residuum, Oktanten, beide Zuordnungen mit
Eindeutigkeit, welche Seite als +x genommen wurde, Umgebung (Tisch, Abstand zu Metall), Lauf 5: Abweichung
von |B| während des Servo-Durchlaufs.

**Grenzen**: Der Fit kennt den wahren Feldbetrag nicht (nur den mittleren Radius), für die Lage reicht
das. Soft-Iron ist in Chip-Achsen gespeichert und gilt für die Platine ohne Rumpf; im eingebauten Zustand
(Motor, Servos, Akku) muss `cal mag` wiederholt werden. Im Flug stören die Servo- und Motorströme, der
Sensor ist für den Boden und ruhige Phasen gedacht.

---

## V05 Barometer und SHT40

**Ziel**: BMP390 (und zweites, falls bestückt), Bodenreferenz und Rauschen, Höhenprobe; SHT40 gegen
Raumthermometer und Hygrometer.

**Material**: nur 1S, Raumthermometer, Hygrometer, Schale zum Abdecken, Regalbrett oder Treppe (1 m
Höhenunterschied), Maßband.

**Aufbau**: Platine auf dem Tisch, Fenster und Türen zu, Heizung und Ventilator aus, Platine nicht
anhauchen. Für Lauf 4 die Platine samt Kabel auf das Brett legen.

**Vorbereitung an der Konsole**:
```
baro            Chip-IDs, Druck, Temperatur
sht             Seriennummer, Temperatur, Feuchte
```

**Was gemessen wird**: `baro`: BMP390 ×8/×1, IIR 3, 50 Hz, erste Messung nach dem Reset; `cal baro <s>`:
Mittel und Standardabweichung des Drucks, Mitteltemperatur. `sht`: Messung hohe Genauigkeit mit CRC.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | Tisch | `--commands "baro,sht"` |
| 2 | Tisch, abgedeckt, 30 s | `--commands "cal baro 30"` (noch nicht speichern) |
| 3 | Tisch, offen, 30 s | `--commands "cal baro 30"`: Unterschied zu Lauf 2 = Luftzug |
| 4 | 1 m höher, 10 s | `--commands "cal baro 10"` |
| 5 | wieder Tisch, 30 s, Referenz | `--commands "cal baro 30,cal save"` |
| 6 | SHT40 neben dem Thermometer, 5 min gewartet | `--commands "sht"` |

**Auswertung**:

| Zeile | Soll |
|---|---|
| `baro1` | Chip-ID 0x60 (0x50 = BMP388 als Rückfall), 80–110 kPa, Temperatur ± 3 K zum Raum |
| `baro2` | `SKIP` (DNP) oder OK, wenn bestückt |
| `cal_baro` Rauschen | < 3 Pa (≈ 0,25 m); bis 6 Pa übernommen; Lauf 3 gegen 2 zeigt den Luftzug |
| Lauf 4 gegen 5 | Druckdifferenz 11–13 Pa je Meter |
| `sht_read` | Temperatur ± 2 K zum Thermometer, Feuchte ± 5 % zum Hygrometer |

**Protokoll**: Chip-IDs, Drücke der fünf Läufe, Rauschen, Höhenprobe (Meter gemessen, Pa gemessen),
Temperaturen (BMP390, SHT40, IMU, Raum), Feuchten.

**Grenzen**: Die Bodenreferenz gilt für den Tag; vor dem Flug wird sie auf der Rampe neu genommen
(`cal baro` oder die Flug-Firmware). Die Temperatur des BMP390 liegt wegen der Eigenerwärmung der
Platine über der Raumtemperatur, der SHT40 am Rand ist näher dran.

---

## V06 INA239 Strom und Spannung

**Ziel**: Erkennung, Busspannung gegen die Mux, Strom unter Last, Offset und Verstärkung gegen das Multimeter.

**Material**: 1S und 2S (1 A), Multimeter im Strombereich (2 A), Lastwiderstand 22 Ω / 5 W (0,34 A bei
7,4 V) an einem JST-XH-3-Stecker zwischen Pin 2 (VSERVO) und Pin 3 (GND_PWR), Multimeter in Reihe.

**Aufbau**: Widerstand an **J_SERVO3** (XH, freie Buchse), Multimeter in die Plusleitung des Widerstands.
Nichts anderes an VSERVO (keine Servos, kein Motor).

**Vorbereitung an der Konsole**:
```
status          2S da?
ina             IDs, Konfiguration, Busspannung gegen Mux
```

**Was gemessen wird**: INA239 mit 20-mΩ-Shunt, ±163,84 mV, 16-fach gemittelt (ca. 20 Hz); `ina` liest
VBUS (am Kelvin-Abgriff = VSERVO), Strom, Die-Temperatur; `ina load` wartet auf die Last und mittelt
5 Werte; `cal ina` mittelt 10 Werte ohne Last (Offset) und 10 mit Last gegen den eingegebenen
Multimeterstrom (Verstärkung).

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | 2S, ohne Last | `--commands "ina"` |
| 2 | Last nach Ansage stecken | `--commands "ina load"` |
| 3 | Offset ohne Last, dann Last mit Multimeter in Reihe, Wert in A eingeben | `--commands "cal ina,cal save"` |
| 4 | Kontrolle | `--commands "ina load"`: kalibrierter Strom gegen Multimeter |

**Auswertung**:

| Zeile | Soll |
|---|---|
| `ina_id` | 0x5449 / 0x239x |
| `ina_bus` | 2S ± 0,1 V, zur Mux ± 0,3 V |
| `ina_load` | 0,30–0,38 A bei 22 Ω und 7,4 V, Leistung plausibel |
| `cal_ina_offset` | \|Offset\| < 20 mA |
| `cal_ina_gain` | Faktor 0,97–1,03 |
| Lauf 4 | Abweichung zum Multimeter < 2 % |

**Protokoll**: IDs, Busspannung INA und Mux, Laststrom INA und Multimeter, Offset, Faktor, Widerstand,
Multimeter-Bereich. Das Multimeter danach aus dem Strombereich nehmen.

**Grenzen**: Verstärkung bei einem Strompunkt (0,34 A); Servo- und Motorströme liegen bei 1–3 A, die
Linearität des Shunts ist dort besser als 1 %, die Eigenerwärmung des 1-W-Shunts bei 3 A (0,18 W)
unkritisch. Die Mittelung über 50 ms macht den INA239 für den 100-Hz-Regler unbrauchbar, er dient Telemetrie und Log.

---

## V07 Servos

**Ziel**: alle vier Servoausgänge, Fenster aus `Config.h`, Mitte und Grenzen trimmen und speichern.

**Material**: 1S, 2S (1 A, bei vier Servos 2 A), Servos für 2S-Betrieb, Kardan montiert (Yaw, Pitch),
Fallschirm- und Beinmechanik oder freie Hörner.

**Aufbau**: J_SERVO1 Yaw, J_SERVO2 Pitch, J_SERVO3 Fallschirm, J_SERVO4 Beine (XH: Pin 1 Signal, 2 VSERVO,
3 GND_PWR). Beim ersten Einschalten des 2S auf den Netzteilstrom schauen (verpoltes Servo).

**Vorbereitung an der Konsole**:
```
status            2S da, nFAULT hoch
cal show          servo_us 1..4 (Standard 1500 / 1000 / 2000)
servo 1           Mitte Yaw, Rückfrage mit Enter beantworten
```

**Was gemessen wird**: `servo <n> center|min|max|sweep|us <wert>` mit der Servo-Bibliothek (50 Hz),
geklemmt auf das Fenster: Yaw 70–115°, Pitch 60–105° (Kardan, aus `Config.h`, umgerechnet in µs),
Chute und Beine 760–2300 µs; Mitte und Grenzen aus der Kalibrierung. `cal servo <n>`: interaktives
Fahren in µs, `c` Mitte, `a` min, `b` max.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | je Servo Mitte, min, max, Durchlauf | `--commands "servo 1,servo 1 min,servo 1 max,servo 1 sweep"`, dann 2, 3, 4 |
| 2 | Trimm Yaw: Kardan gerade (Lineal an der Düse), dann beide Grenzen mit 2–3° Luft | `--commands "cal servo 1"` |
| 3 | Trimm Pitch | `--commands "cal servo 2"` |
| 4 | Trimm Chute: verriegelt = min, offen = max | `--commands "cal servo 3"` |
| 5 | Trimm Beine: eingeklappt = min, ausgeklappt = max | `--commands "cal servo 4,cal save"` |
| 6 | Kontrolle mit den gespeicherten Werten | `--commands "servo all sweep"` |

Trimm-Befehle in der `WAIT Befehl`-Schleife: `+`/`-` 10 µs, `++`/`--` 50 µs, Zahl = µs, `c`, `a`, `b`,
`ok`, `q`.

**Auswertung**: alle `servoN_*` OK mit bestätigter Bewegung; Strom am 2S-Netzteil < 0,5 A je Servo im
Stillstand, kein Anschlaggeräusch; `cal_servoN` mit Mitte zwischen min und max. Mitte in µs gegen
`SERVO_*_OFFSET` aus `Config.h` vergleichen (92,5° ≈ 1552 µs, 82,5° ≈ 1466 µs bei 760–2300 µs); mehr als
50 µs Unterschied heißt, das Horn sitzt einen Zahn versetzt.

**Protokoll**: je Servo Mitte, min, max in µs, Stromaufnahme, Servotyp, Auffälligkeiten (Zittern, Summen,
Nachlaufen), Hornposition.

**Grenzen**: Nur die Stellung, keine Dynamik. Kennlinie, Sprungantwort und Frequenzgang der TVC-Servos
mit dem Kardan sind Versuch E02 (`docs/experiments/E02_TVC_Charakterisierung_revB1.md`, Konsole `tvc ...`,
Aufnahme `tools/capture_tvc.py`). Die Grenzen in `Config.h` stammen vom SG90; mit anderen Servos gilt
das Fenster neu.

---

## V08 Rollmotor

**Ziel**: DRV8833 mit beiden Brücken parallel, Drehrichtung je Eingang, nFAULT, Strom.

**Material**: 1S, 2S (3 A), Rollmotor an **J_MOT** (XH, MOT_A / MOT_B), Schwungrad abgenommen oder frei
drehbar und gesichert, Markierung am Motor (Klebeband) für die Drehrichtung.

**Aufbau**: Motor so einspannen, dass nichts in die Welle geraten kann; Finger weg.

**Vorbereitung an der Konsole**:
```
status            nFAULT „hoch“
ina               INA239 bereit (liefert den Motorstrom)
```

**Was gemessen wird**: `motor`: nSLEEP hoch, 300 ms PWM 30 % (20 kHz, 12 bit) auf IN1, Pause, 300 ms auf
IN2, nFAULT während der Pulse, Strom aus dem INA239 am Ende jedes Pulses, dann nSLEEP tief.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | Motor frei | `--commands "motor"` |
| 2 | Motor mit Schwungrad | `--commands "motor"` |
| 3 | Wiederholung nach 1 min | `--commands "motor"` (Erwärmung, nFAULT) |

**Auswertung**: `motor_nfault_idle` und `motor_nfault_run` OK, Drehung in beide Richtungen bestätigt,
Strom am Ende des Pulses < 1,5 A (Richtwert, vom Motor abhängig). nFAULT tief während der Pulse:
Blockierstrom (> 2 × 1,5 A) oder Übertemperatur; Motor leichter laufen lassen, Verdrahtung an U7 prüfen.

**Protokoll**: Drehrichtung bei Puls 1 (IN1) und Puls 2 (IN2) gegen die Markierung (Vorzeichen des
Rollreglers), Ströme, nFAULT, Spannungseinbruch an TP VSERVO (Multimeter Min/Max).

**Grenzen**: 30 % und 300 ms sagen nichts über das Verhalten bei `ROLL_PWM_MAX`; Dauerstrom und
Erwärmung des DRV8833 am 2S sind ein eigener Versuch mit Wärmebild oder Temperaturfühler.

---

## V09 Pyro mit Lämpchen

**Ziel**: Zündkreise 1 und 2, Durchgangsprüfung, Sense-Pegel während und nach dem Puls, Sicherheitslogik.

**Material**: 1S, 2S (3 A), Schlüsselschalter an **J_ARM**, Glühlampe 12 V / 5 W mit XH-2-Stecker an
**J_PYRO1** (Pin 1 VBAT_ARMED, Pin 2 PYRO1_NEG). **Keine Zünder, keine Ladung, kein Motor im Raum.**
Ersatzweise 2 Ω / 10 W, dann nur `pyro 1 100` (3,7 A bei 7,4 V; Polyfuse 3 A hält, Auslösung ab 6 A).

**Aufbau**: Lämpchen so, dass man es sieht; Schalter in Reichweite; Multimeter mit Min/Max an TP VBAT_PROT.

**Vorbereitung an der Konsole**:
```
mux               Schalter aus: mux_arm „sicher“, mux_pyro1 SKIP
mux               Schalter ein: mux_arm „SCHARF“, mux_pyro1 „Durchgang“
```

**Was gemessen wird**: `pyro <n> <ms>` prüft Kanal bestückt, 2S, ARM > 5 V, Durchgang (Sense > 80 % ARM),
fragt `CONFIRM` (nur `JA`), setzt die LEDs rot, Puls 20–1000 ms, liest Sense nach 30 ms im Puls und
100 ms danach, Ausgang tief.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | Schalter aus, Lämpchen gesteckt | `--commands "pyro 1 500"` → `SKIP` „ARM nicht scharf“ |
| 2 | Schalter ein, kein Lämpchen | `--commands "pyro 1 500"` → `SKIP` „kein Durchgang“ |
| 3 | Schalter ein, Lämpchen | `--commands "pyro 1 500"`, `JA` tippen |
| 4 | wie 3 an J_PYRO2 | `--commands "pyro 2 500"` |
| 5 | wie 3, kurzer Puls wie im Flug | `--commands "pyro 1 80"` |

**Auswertung**: Läufe 1 und 2 `SKIP` mit dem genannten Grund (Sicherheitslogik). Läufe 3–5 `pyroN_fire`
OK: Sense im Puls < 30 % ARM, danach > 80 %, Ausgang tief; Lämpchen hat geleuchtet; Spannungseinbruch
an VBAT_PROT < 0,5 V (Min/Max). Sense im Puls hoch: FET schaltet nicht (Gate-Widerstand, Pin).

**Protokoll**: Sense vor, im und nach dem Puls, Pulsdauer, Einbruch VBAT_PROT, Lämpchentyp, Schalterproben.

**Grenzen**: Das Lämpchen zieht 0,4 A, ein Zünder 1–3 A; der Einbruch im Flug ist größer. Keine Aussage
über die TVS und den Fall „Zünder bleibt kurzgeschlossen“ (Polyfuse-Probe nicht Teil des Versuchs).

---

## V10 LoRa

**Ziel**: E22-400T22S erreichen, Konfiguration lesen, Ping zur Bodenstation mit RSSI, Sendestrom.

**Material**: 1S (3V3_RF versorgt das Modul). **Antenne an der IPEX-Buchse vor dem ersten Befehl.**
Bodenstation mit E22 auf demselben Kanal und derselben Luftrate (`kartonaut-ground` oder ein zweiter
E22 am USB-UART-Adapter im Terminal), Netzteil mit Stromanzeige oder Multimeter in der 1S-Leitung.

**Aufbau**: Bodenstation 1 m entfernt, später 10 m mit Tür dazwischen.

**Vorbereitung an der Konsole**:
```
status            Bausteine
lora              AUX, Konfiguration, Ping
```

**Was gemessen wird**: Modus 2 (M1 hoch, 9600 Bd): Register 00–08 lesen; zurück in Modus 0 mit der
gelesenen UART-Baudrate; `KARTONAUT PING 1\n` senden, 3 s auf eine Zeile mit `PONG` warten; RSSI aus dem
angehängten Byte, wenn REG3 Bit 7 gesetzt ist.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | Bodenstation aus | `--commands "lora"` → `lora_config` OK, `lora_ping` `SKIP` |
| 2 | Bodenstation an, 1 m | `--commands "lora"` |
| 3 | Bodenstation 10 m, Tür zu | `--commands "lora"` |
| 4 | Sendestrom: Multimeter in der 1S-Leitung, Lauf 2 wiederholen | `--commands "lora"` |

Die Bodenstation muss auf `KARTONAUT PING <n>` mit einer Zeile antworten, die `PONG` enthält; im
Terminal reicht `PONG` von Hand innerhalb von 3 s.

**Auswertung**: `lora_aux` hoch; `lora_config` mit Adresse, Kanal (410,125 MHz + Kanal), UART-Baudrate,
Luftrate, Leistung, RSSI-Byte; Werte gleich der Bodenstation. `lora_ping` OK mit Antworttext; RSSI bei
1 m etwa −30 bis −50 dBm, bei 10 m 10–20 dB weniger; „RSSI nicht aktiviert“, wenn REG3 Bit 7 aus ist
(offene Frage 3). Sendepuls am 1S: bis 150 mA zusätzlich für die Dauer des Pakets.

**Protokoll**: Konfiguration, Antwortzeit, RSSI 1 m / 10 m, Sendestrom, Antennentyp.

**Grenzen**: Der Ping misst nur Erreichbarkeit und RSSI im Raum, keine Reichweite im Feld. Die Konsole
ändert nichts im Modul; RSSI-Byte und Kanal werden am Modul eingestellt.

---

## V11 GPS

**Ziel**: NMEA-Empfang, Baudrate, Fix, Satellitenzahl, Position.

**Material**: 1S, GPS-Modul an **J_GPS** (GH: 1 3V3_RF, 2 GND, 3 GPS_TX, 4 GPS_RX), Platz mit Himmelssicht,
Smartphone mit Karte für den Vergleich.

**Aufbau**: Antenne des Moduls nach oben, nichts aus Metall darüber. Draußen: Laptop mit Akku, Platine
am 1S-Akku.

**Vorbereitung an der Konsole**:
```
gps               drinnen: NMEA ja, Fix nein ist normal
```

**Was gemessen wird**: 5 s bei 38400 Bd, bei < 3 Sätzen 5 s bei 9600 Bd; GGA (Fix, Satelliten, HDOP,
Position, Höhe) und RMC (gültig) mit Prüfsumme.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | drinnen | `--commands "gps"` |
| 2 | draußen, Modul 5 min laufen gelassen | `--commands "gps"` |
| 3 | draußen, nach weiteren 5 min | `--commands "gps"` (Satelliten gestiegen?) |

**Auswertung**: `gps_nmea` OK, 0 Prüfsummenfehler (sonst Kabel oder Baudrate); Lauf 2/3 `gps_fix` OK mit
≥ 6 Satelliten, HDOP < 3, Position ± 20 m zur Karte, Höhe plausibel. Baudrate notieren; weicht sie
von 38400 ab, in der Flug-Firmware nachziehen.

**Protokoll**: Baudrate, Sätze je 5 s, Prüfsummenfehler, Zeit bis zum Fix, Satelliten, HDOP, Position, Höhe.

**Grenzen**: Keine Konfiguration des Moduls (Rate, Dynamikmodell „Airborne“); das gehört in die
Flug-Firmware. Kein Test der Datenrate im Flug (1 Hz Standard).

---

## V12 SD-Karte, Loop-Timing, Watchdog, Signalgeber

**Ziel**: Loggerpfad, Takt der Flugschleife mit allen Sensoren, Neustart durch den Watchdog, LEDs,
Summer, Kamera-Trigger.

**Material**: 1S, microSD (FAT32/exFAT), optional Kamera oder Multimeter an J_CAM Pin 2 (GH: 1 5V_SYS,
2 CAM_TRIG_OUT über 1 k, 3 GND), Netzteil mit Stromanzeige.

**Aufbau**: Karte im Teensy-Slot; LEDs im Blickfeld; Kamera per Kabel an J_CAM.

**Vorbereitung an der Konsole**:
```
status
```

**Was gemessen wird**: `sd`: 1 MiB in 4-KiB-Blöcken schreiben (Zeit je Block), lesen und vergleichen,
Datei löschen. `timing`: 300 Durchläufe mit 100 Hz, je Durchlauf IMU, Baro, drei Mux-Kanäle,
Magnetometer, INA239 alle 10 Durchläufe; Mittel, Maximum, Überläufe. `watchdog`: 2-s-Watchdog 3 s
bedient, dann abgeschaltet, 2,5 s unbedient. `watchdog fire`: 1 s, nicht bedient → Neustart, Banner
meldet die Ursache. `led`, `buzzer`, `cam` mit Rückfrage.

**Läufe und Aufnahme**:

| Lauf | Zustand | Befehl |
|---|---|---|
| 1 | Karte A | `--commands "sd"` |
| 2 | Karte B (zweites Fabrikat) | `--commands "sd"` |
| 3 | alle Sensoren erkannt | `--commands "timing"` |
| 4 | Watchdog | `--commands "watchdog,watchdog fire"` (verbindet nach dem Neustart neu) |
| 5 | Signalgeber | `--commands "led,buzzer,cam"` |

**Auswertung**: `sd_write` > 1 MB/s, längster Block < 50 ms (Karten mit längeren Aussetzern nicht für den
Flug), `sd_read` „Inhalt stimmt“; `timing_loop` Mittel < 2 ms, Maximum < 5 ms, 0 Überläufe;
`watchdog_feed` OK, nach `watchdog fire` `INFO reset_cause Watchdog` und `TEST watchdog_reset OK`;
LEDs in der genannten Farbe (beide gleich, sonst GRB-Reihenfolge oder Kette), drei Töne, Kamerapuls.
Netzteilstrom beim SD-Schreiben notieren (Spitze).

**Protokoll**: Kartentypen und Datenraten, längster Block, Timing-Werte, Neustartursache, LED-Farben,
Summer, Kamera, Strom beim Schreiben.

**Grenzen**: `timing` misst die Sensorlesezeit, nicht die Flugschleife mit Regler und Logger; der
SD-Test schreibt am Stück, im Flug schreibt der Logger in Lücken (`SDLogger`). Die Abschaltung des
Watchdogs (`wdEnd`) ist auf der Platine noch nicht bestätigt; schlägt `watchdog` mit einem Neustart
nach 2,5 s fehl, bleibt der Watchdog nach dem Test scharf und `watchdog fire` entfällt.

---

## Reihenfolge und Dauer

| Versuch | Versorgung | Dauer |
|---|---|---|
| V01 Versorgung | 1S, 2S ohne Teensy | 15 min |
| V02 Mux, ADC | 1S, 2S, ARM | 20 min |
| V03 IMU | 1S | 25 min |
| V04 Magnetometer, Achsen | 1S (Akku) | 25 min |
| V05 Baro, SHT40 | 1S | 15 min |
| V06 INA239 | 1S, 2S, Last | 15 min |
| V07 Servos | 1S, 2S | 30 min |
| V08 Rollmotor | 1S, 2S 3 A | 10 min |
| V09 Pyro | 1S, 2S 3 A, ARM, Lämpchen | 15 min |
| V10 LoRa | 1S, Antenne, Bodenstation | 15 min |
| V11 GPS | 1S, draußen | 20 min |
| V12 SD, Timing, Watchdog, Signal | 1S | 15 min |
| E02 TVC-Charakterisierung | 1S, 2S, Kardan, externe IMU | 90 min |

Am Ende `cal show`, dann 1S aus und ein und wieder `cal show`: die Werte müssen wiederkommen
(„Kalibrierung ok“ im Banner). Die Berichte aus `test_reports/` mit dem Protokoll ablegen.
