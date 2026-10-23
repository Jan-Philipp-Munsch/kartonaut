# Versuchsanleitungen Mainboard rev B1: Vermessung und Kalibrierung

Stand 2026-10-23. Zwölf Versuche, die am Tisch nacheinander laufen. Jeder Versuch nennt Geräte,
Aufbau mit Steckerbelegung, Schritte mit Befehl an die Testkonsole `revb_test`, Sollwerte und die
Felder fürs Protokoll. Die Konsole stellt ihre Rückfragen selbst (`WAIT`, `ASK`, `CONFIRM`), die
Anleitung sagt, was du dabei in der Hand hältst. Den Gesamtablauf und das Zeilenformat beschreibt
`Tischtest_revB1.md`; Steckerbelegungen stammen aus `circuit.py` (Branch `claude/rev-b1`).

**Bericht**: `python tools/bench_test.py` schreibt jeden Lauf nach `test_reports/bench_<datum>.md`
und `.json`. Was du mit dem Multimeter misst, gibst du bei `ASK` ein, es landet im Bericht. Die
Protokollfelder unten sind das, was zusätzlich von Hand notiert wird (Seriennummer der Platine,
Akku, Raumtemperatur, Auffälligkeiten).

## Grundausstattung

| Gerät / Material | Wofür |
|---|---|
| Labornetzteil, zwei Kanäle oder zwei Geräte, einstellbare Strombegrenzung | 1S-Zweig (3,7–4,2 V) und 2S-Zweig (7,4 V) |
| Multimeter (Spannung bis 20 V, Strom bis 2 A, Durchgang) | Testpunkte, ADC- und INA-Abgleich, Pyro-Durchgang |
| 1S-LiPo und 2S-LiPo (optional statt Netzteil) | Akkuspannungen wie im Flug |
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
| Nicht magnetische Unterlage, 1 m Abstand zu Netzteilen, Lautsprechern, Stahltisch | Magnetometer |

Allgemeine Regeln:

- **Beim Einschalten erst 1S** (Netzteil 4,0 V, Strombegrenzung 100 mA; nach dem ersten Versuch
  500 mA). Der Teensy läuft nur bei versorgtem 1S-Zweig, USB liefert nur Daten.
- **2S nur, wenn der Versuch es braucht** (V06 bis V09). Netzteil 7,4 V, Strombegrenzung 1 A, für
  Motor und Pyro 3 A. Ohne 2S melden die betroffenen Prüfungen `SKIP`.
- **Neustart des Teensy**: 1S aus und wieder ein. Über USB geht es nicht.
- Vor jedem Flashen: `python tools/check_board_pins.py <circuit.py von claude/rev-b1>`.
- `q` in der Konsole bricht eine laufende Messung ab. Nach jedem Befehl stehen Servos ohne Puls,
  der Motortreiber schläft, Pyro ist tief.

Protokollkopf für jeden Lauf: Datum, Platine (Nummer, Bestückungsstand), Firmware-Commit,
Versorgung (Akku oder Netzteil, eingestellte Spannung und Begrenzung), Raumtemperatur, Name.

---

## V01 Versorgung ohne Teensy

**Zweck**: Schienen prüfen, bevor der Teensy gesteckt wird.
**Geräte**: Netzteil, Multimeter. **Teensy ausgesteckt.**

Aufbau:
1. Netzteil Kanal 1: 4,0 V, Strombegrenzung 100 mA, an **J_BAT1** (JST-PH, Pin 1 = Plus, Pin 2 = GND).
2. **JP1** (Lötbrücke „SJ 1S“) brücken oder an **J_SW** Pin 1 und 2 verbinden (Schalter 1S).
3. Für den 2S-Teil: Netzteil Kanal 2: 7,4 V, 100 mA, an **J_BAT2** (XT30, Pin 1 = Plus), **JP2**
   brücken oder J_SW Pin 3 und 4 verbinden.

Schritte (`python tools/bench_test.py` fragt die Werte in dieser Reihenfolge ab):

| Testpunkt | Soll | Hinweis |
|---|---|---|
| Strom am Netzteil 1S | < 60 mA | Mehr heißt Kurzschluss oder falsches Bauteil, sofort aus |
| TP VSYS_IN | Netzteilspannung minus < 0,1 V | hinter Verpolschutz Q2 und Lastschalter Q7 |
| TP 5V_SYS | 4,85–5,15 V | TPS63070, FB-Teiler 680 k / 130 k |
| TP 3V3_RF | 3,20–3,40 V | LDO U3 |
| TP 3V3_EXP | 3,20–3,40 V | LDO U14 |
| Strom am Netzteil 2S | < 10 mA | ohne Last nur der Teiler und die INA239 |
| TP VBAT_PROT | 2S-Spannung minus < 0,1 V | hinter Q1, F1, Q6 |
| TP VSERVO | wie VBAT_PROT minus < 0,05 V | hinter dem 20-mΩ-Shunt |

Zusatz: JP1 öffnen (bzw. J_SW 1-2 trennen): VSYS_IN muss auf 0 V fallen (Lastschalter aus). Gleiches
mit JP2 für VBAT_PROT. Dann wieder schließen.

Abbruch: ein Wert außerhalb → nicht weiter, Bauteil suchen (Lötbrücke, verdrehtes SOT-23, Polung).

Protokoll: alle acht Werte, Stromaufnahme 1S und 2S, Schalterprobe ok/nicht ok.

---

## V02 Analogmux und ADC-Teiler

**Zweck**: alle acht Mux-Kanäle, Akkuspannungen, ARM-Pegel, Durchgang Pyro 1–4, dann den
Teilerfaktor je Kanal gegen das Multimeter abgleichen.
**Geräte**: Netzteil 1S (jetzt 500 mA), optional 2S (1 A), Multimeter, J_ARM-Brücke, Lämpchen.

Aufbau: wie V01, Teensy gesteckt, USB verbunden, `pio run -e revb_test -t upload`.

Schritte:
1. `mux`. Soll: `mux_gnd` < 0,05 V, `mux_vbat1` = Netzteil ± 0,05 V. Ohne 2S: Rest `SKIP`.
2. 2S dazu, J_ARM mit Schlüsselschalter oder Brücke (XH, Pin 1 VBAT_PROT, Pin 2 VBAT_ARMED), an
   J_PYRO1 und J_PYRO2 je ein Lämpchen. `mux` erneut.
   Soll: `mux_vbat2` = 2S ± 0,05 V, `mux_arm` ≈ 2S und „SCHARF“, `mux_pyro1/2` „Durchgang“ (Sense
   > 80 % von ARM), `mux_pyro3/4` `SKIP` (DNP). Lämpchen abziehen: `mux_pyro1` „offen“.
3. Abgleich: `cal adc` (Kanäle 4, 5, 6). Die Konsole nennt den Teensy-Wert und fragt nach dem
   Multimeter:
   - Kanal 4 VBAT1_F: Multimeter an **J_BAT1 Pin 1** gegen GND (hinter Q2 liegen nur Millivolt).
   - Kanal 5 VBAT2_F: Multimeter an **J_BAT2 Pin 1** gegen GND.
   - Kanal 6 VBAT_ARMED: Multimeter an **J_ARM Pin 2** oder J_PYRO1 Pin 1 gegen GND.
   Soll: Faktor 0,98–1,02 (1-%-Widerstände). Außerhalb 0,9–1,1 übernimmt die Konsole nichts.
4. Optional Kanäle 0 und 1 (`cal adc 0`, `cal adc 1`) mit scharfem ARM und ohne Lämpchen:
   Multimeter an **J_PYRO1 Pin 2** (PYRO1_NEG, über den 100-k/33-k-Teiler bei ARM-Spannung).
5. `cal save`.

Protokoll: Teensy-Wert und Multimeterwert je Kanal, Faktoren, Durchgangsprobe mit und ohne Lämpchen.

---

## V03 IMU

**Zweck**: Erkennung, Datenrate, Werksselbsttest, Gyro-Nullpunkt, Beschleunigung in sechs Lagen.
**Geräte**: nur 1S. Ebene, feste Unterlage (Tischplatte, keine Pappe), Zimmertemperatur.

Schritte:
1. `imu`. Soll: `imu_whoami` 0x47, `imu_rate` 1000 ± 100 Hz, `imu_rest` |a| 9,0–10,6 m/s² und
   |ω| < 5 °/s, `imu_selftest_gyro` und `imu_selftest_acc` OK (Verhältnis 0,5–1,5 zum Werkswert,
   Gyro-Antwort > 60 °/s). Ein Selbsttest `FEHL` bei sonst guten Werten: Versuch wiederholen, die
   Platine darf während der 2 s nicht angestoßen werden; bleibt es, ist der Chip verdächtig.
2. `cal gyro 30`. Platine 30 s nicht berühren, kein Tritt gegen den Tisch. Soll: Nullpunkt je Achse
   < 2 °/s (typisch < 1), Rauschen < 0,2 °/s. Die Konsole startet bei Bewegung von vorn.
   Notiere die Temperatur aus der `CAL gyro_bias_temp_c`-Zeile.
3. Optional Temperaturgang: Platine 10 min mit dem Deckel einer Lampe oder in der Hand erwärmen,
   `cal gyro 20` wiederholen, Differenz der Nullpunkte je Grad notieren (nicht speichern, nur
   protokollieren; die Firmware hält bisher einen Nullpunkt bei einer Temperatur).
4. `cal acc`. Sechs Lagen, je 1,5 s ruhig halten; die Konsole sagt die Lage an:
   1 flach, Bestückseite oben · 2 flach, Bestückseite unten · 3 hochkant auf der langen Kante mit
   dem Teensy-USB · 4 gegenüberliegende lange Kante · 5 hochkant auf der kurzen Kante mit der Spitze
   (GPS/J_STACK) · 6 gegenüberliegende kurze Kante. Ein Winkel oder ein Buch als Anschlag hilft.
   Soll: Offset je Achse < 0,3 m/s², Skalierung 0,98–1,02. Meldet die Konsole „Achse nicht nach oben
   und unten gesehen“, war eine Lage schief oder zweimal dieselbe.
5. `cal save`.

Protokoll: WHO_AM_I, Datenrate, Selbsttestwerte, Nullpunkt mit Temperatur, sechs Lagenwerte
(aus den `INFO`-Zeilen), Offset und Skalierung.

---

## V04 Magnetometer und Achszuordnung

**Zweck**: LIS3MDL erkennen und selbsttesten, Hard- und Soft-Iron, Achsen von IMU und Magnetometer
zum Raketenkörper.
**Geräte**: nur 1S. Nicht magnetische Umgebung: Holztisch, 1 m zu Netzteil, Monitor, Lautsprecher,
Stahl. Keine Schraubendreher in der Nähe. Am besten mit 1S-Akku statt Netzteilkabel.

Schritte:
1. `mag`. Soll: `mag_whoami` 0x3D, `mag_read` |B| 0,2–0,7 gauss (unkalibriert und auf der Platine
   auch bis 1,5 gauss hinnehmbar), `mag_selftest` OK (Differenz X/Y 1,0–3,0, Z 0,1–1,0 gauss).
2. `cal mag 60`. Nach Enter die Platine 60 s langsam um alle Achsen drehen: wie beim Kompass
   kalibrieren, Achten in die Luft malen, auch über Kopf, jede Richtung etwa gleich lang. Das
   USB-Kabel darf mit, aber nicht zerren. Die Konsole zählt die Proben und meldet alle 5 s.
   Soll: Oktanten 8/8, Residuum < 5 % (bis 10 % wird übernommen), Achsenverhältnis < 1,5,
   Feld 0,2–0,7 gauss. Bei `FEHL` nochmal mit mehr Drehung über Kopf.
3. `cal axes`, drei Teile:
   - Teil 1: Platine mit der **Spitze nach oben** halten (Rollachse senkrecht; „Spitze“ = das Ende
     mit J_GPS/J_STACK, wie sie in der Rakete sitzt). 1 s ruhig.
   - Teil 2: die Seite, die **Körper +x** ist, nach oben, Spitze waagerecht. Welche Seite das ist,
     legt Jan fest (offene Frage 1 in `Tischtest_revB1.md`); bis dahin eintragen, welche Seite
     genommen wurde.
   - Teil 3: 20 s zügig um alle Achsen drehen (schneller als bei `cal mag`, etwa eine Umdrehung
     pro 2 s), damit die Drehrate deutlich ist.
   Soll: `cal_axes_imu` OK mit einer Zuordnung, die zur Lage des ICM auf der Platine passt;
   `cal_axes_mag` Eindeutigkeit > 2 (gut: > 5). Unter 2 nochmal mit schnellerer Drehung.
4. Gegenprobe: `imu` und `mag` nochmal, Platine mit der Spitze nach Norden halten; die
   kalibrierte Magnetometer-x- oder -z-Komponente sollte das Feld zeigen (Ortsfeld in Deutschland
   ca. 0,48 gauss, Inklination 65°, also mehr vertikal als horizontal).
5. `cal save`.

Protokoll: Selbsttestdifferenzen, Offset, Feldbetrag, Residuum, Oktanten, beide Achszuordnungen
mit Eindeutigkeit, welche Seite als +x genommen wurde, Umgebung (Tisch, Abstand zu Metall).

---

## V05 Barometer und SHT40

**Zweck**: BMP390 (und zweites, falls bestückt), Bodenreferenz und Rauschen; SHT40.
**Geräte**: nur 1S. Fenster und Türen zu, kein Ventilator, Platine nicht anhauchen.

Schritte:
1. `baro`. Soll: `baro1` Chip-ID 0x60 (0x50 = BMP388 als Rückfall), 80–110 kPa, Temperatur
   plausibel; `baro2` `SKIP` (DNP) oder OK, wenn bestückt.
2. `sht`. Soll: Seriennummer ungleich 0, Temperatur ± 2 °C zum Raumthermometer, Feuchte
   ± 5 % zu einem Vergleichshygrometer (falls vorhanden).
3. `cal baro 30`. Soll: Rauschen < 3 Pa (≈ 0,25 m), bis 6 Pa wird übernommen. Höher: Luftzug oder
   Heizung; Platine mit einer Schale abdecken und wiederholen.
4. Plausibilität der Höhe: Platine 1 m anheben (Regalbrett), `cal baro 10` erneut, der Druck muss
   um etwa 12 Pa fallen. Danach wieder auf den Tisch und `cal baro 30` für die Referenz.
5. `cal save`.

Protokoll: Chip-IDs, Druck, Temperaturen (BMP390, SHT40, IMU, Raum), Feuchte, Rauschen, 1-m-Probe.

---

## V06 INA239 Strom und Spannung

**Zweck**: Erkennung, Busspannung gegen die Mux, Strom unter Last, Offset und Verstärkung.
**Geräte**: 1S und 2S (1 A), Multimeter im Strombereich, Lastwiderstand 22 Ω / 5 W (0,34 A bei
7,4 V) an einem JST-XH-3-Stecker zwischen Pin 2 (VSERVO) und Pin 3 (GND_PWR); Multimeter in
Reihe zum Widerstand.

Schritte:
1. `ina`. Soll: Hersteller 0x5449, Gerät 0x239x, `ina_bus` = 2S ± 0,1 V und ± 0,3 V zur Mux.
2. `ina load`: Konsole fragt nach der Last; Widerstand an **J_SERVO3** (Pin 2/3) stecken, Enter.
   Soll: Strom 0,30–0,38 A bei 22 Ω, Leistung plausibel.
3. `cal ina`: erst ohne Last (Offset, Soll |Offset| < 20 mA), dann Last mit Multimeter in Reihe
   stecken, Multimeterwert in A eingeben. Soll: Faktor 0,97–1,03 (20-mΩ-Shunt 1 %).
   Das Multimeter nach der Messung aus dem Strombereich nehmen.
4. `cal save`.

Protokoll: IDs, Busspannung INA und Mux, Laststrom INA und Multimeter, Offset, Faktor, Widerstandswert.

---

## V07 Servos

**Zweck**: alle vier Servoausgänge, Fenster aus `Config.h`, Mitte und Grenzen trimmen.
**Geräte**: 1S, 2S (1 A, bei vier Servos 2 A). Servos für 2S-Betrieb, nach Plan gesteckt: J_SERVO1
Yaw, J_SERVO2 Pitch, J_SERVO3 Fallschirm, J_SERVO4 Beine (XH: Pin 1 Signal, 2 VSERVO, 3 GND_PWR).
Bei den TVC-Servos den Kardan montiert, sonst das Horn frei.

Schritte:
1. `servo 1` (Mitte), dann `servo 1 min`, `servo 1 max`, `servo 1 sweep`. Die Konsole fragt nach
   jeder Bewegung, ob sie zu sehen war. Für Yaw und Pitch klemmt die Firmware auf das Kardanfenster
   aus `Config.h` (70–115° bzw. 60–105°, umgerechnet in µs), für Chute und Beine auf 760–2300 µs.
   Soll: Bewegung ohne Anschlaggeräusch, Strom am 2S-Netzteil unter 0,5 A je Servo, nFAULT bleibt
   unberührt (der Motortreiber ist nicht beteiligt).
2. Dasselbe für `servo 2`, `servo 3`, `servo 4`. Oder `servo all sweep`.
3. Trimm: `cal servo 1`. Mit `+`/`-` (10 µs), `++`/`--` (50 µs) oder einer Zahl in µs fahren, bis der
   Kardan gerade steht, `c` setzt die Mitte; dann an die mechanische Grenze fahren (nicht gegen den
   Anschlag drücken, 2–3° Luft lassen), `a` setzt min, andere Seite `b` setzt max, `ok`. Für Pitch
   wiederholen; bei Chute und Beinen die Stellungen „verriegelt“ und „offen“ als min/max.
4. `cal save`.

Protokoll: je Servo Mitte, min, max in µs, Stromaufnahme, Typ des Servos, Auffälligkeiten (Zittern,
Summen, Nachlaufen).

---

## V08 Rollmotor

**Zweck**: DRV8833 mit beiden Brücken parallel, kurze Pulse in beide Richtungen, nFAULT, Strom.
**Geräte**: 1S, 2S (3 A), Rollmotor an **J_MOT** (XH, MOT_A / MOT_B), Schwungrad abgenommen oder
frei drehbar und gesichert; Finger weg.

Schritte:
1. `status`: nFAULT muss „hoch“ sein.
2. `motor`. Konsole fragt, ob der Motor frei ist; dann 300 ms 30 % vorwärts, Pause, 300 ms rückwärts.
   Soll: `motor_nfault_idle` und `motor_nfault_run` OK, sichtbare Drehung in beide Richtungen,
   Strom (aus der INA239, in der `WAIT`-Zeile) plausibel für den Motor (Richtwert < 1,5 A bei 30 %).
3. Wenn nFAULT während der Pulse tief geht: Blockierstrom oder Übertemperatur. Motor leichter
   laufen lassen, Versuch nach 1 min wiederholen; bleibt es, Verdrahtung an U7 prüfen.

Protokoll: Drehrichtung bei IN1 (Puls 1) und IN2 (Puls 2) notieren (wichtig für das Vorzeichen des
Rollreglers), Ströme, nFAULT.

---

## V09 Pyro mit Lämpchen

**Zweck**: Zündkreis 1 und 2, Durchgangsprüfung, Sense-Pegel während des Pulses.
**Geräte**: 1S, 2S (3 A), Schlüsselschalter an **J_ARM**, Glühlampe 12 V / 5 W mit XH-2-Stecker an
**J_PYRO1** (Pin 1 VBAT_ARMED, Pin 2 PYRO1_NEG). **Keine Zünder, keine Ladung, kein Motor im Raum.**
Ersatzweise 2 Ω / 10 W, dann nur `pyro 1 100` (bei 7,4 V fließen 3,7 A, die Polyfuse hält 3 A,
Auslösung ab 6 A, 100 ms sind unkritisch, 1 s nicht).

Schritte:
1. Schalter aus. `mux`: `mux_arm` „sicher“, `mux_pyro1` `SKIP` „ARM nicht scharf“.
2. Schalter ein. `mux`: `mux_arm` „SCHARF“, `mux_pyro1` „Durchgang“.
3. `pyro 1 500`. Die Konsole prüft 2S, ARM und Durchgang, dann `CONFIRM`: nur mit dem Wort `JA`
   geht es weiter. Die LEDs werden rot, das Lämpchen leuchtet 0,5 s.
   Soll: `pyro1_fire` OK: Sense während des Pulses < 30 % der ARM-Spannung (FET zieht nach
   GND_PWR), danach wieder > 80 %, Ausgang tief.
4. Dasselbe mit `pyro 2 500` an J_PYRO2.
5. Schalter aus, Lämpchen ab. `pyro 1` ohne Lämpchen muss `SKIP` „kein Durchgang“ melden,
   `pyro 1` mit Schalter aus `SKIP` „ARM nicht scharf“.

Protokoll: Sense-Spannungen vor, während, nach dem Puls, Pulsdauer, Spannungseinbruch an TP
VBAT_PROT (Multimeter mit Min/Max-Funktion, falls vorhanden), Schalterproben.

---

## V10 LoRa

**Zweck**: E22-400T22S erreichen, Konfiguration lesen, Ping zur Bodenstation mit RSSI.
**Geräte**: 1S (3V3_RF speist das Modul). **Antenne an der IPEX-Buchse vor dem ersten Befehl.**
Bodenstation mit E22 auf demselben Kanal und derselben Luftrate, Empfänger aus `kartonaut-ground`
oder ein zweiter E22 am USB-UART-Adapter in einem Terminal.

Schritte:
1. `lora`. Soll: `lora_aux` hoch, `lora_config` mit Adresse, Kanal (Frequenz = 410,125 MHz +
   Kanal), UART-Baudrate, Luftrate, Leistung, RSSI-Byte an/aus. Werte mit der Bodenstation vergleichen.
2. Ping: die Konsole sendet `KARTONAUT PING 1` im Transparentmodus und wartet 3 s auf eine Zeile
   mit `PONG`. Die Bodenstation muss darauf antworten (`PONG 1`); am Terminal von Hand `PONG` tippen
   reicht. Soll: `lora_ping` OK mit Antworttext; RSSI nur, wenn das RSSI-Byte im Modul aktiv ist,
   sonst steht „RSSI nicht aktiviert“ (offene Frage 3).
3. Reichweite grob: Bodenstation 10 m weg, Tür dazwischen, `lora` wiederholen, RSSI vergleichen.

Protokoll: Konfiguration (Adresse, NetID, Kanal, Luftrate, Leistung), Antwortzeit, RSSI bei 1 m
und 10 m, Stromaufnahme 1S beim Senden (Netzteil zeigt kurz einen Puls).

---

## V11 GPS

**Zweck**: NMEA-Empfang, Fix, Satellitenzahl.
**Geräte**: 1S, GPS-Modul an **J_GPS** (GH: 1 3V3_RF, 2 GND, 3 GPS_TX, 4 GPS_RX). Draußen oder am
Fenster mit Himmelssicht; Kaltstart dauert bis 5 min, Modul vorher 5 min laufen lassen.

Schritte:
1. `gps` drinnen. Soll: `gps_nmea` OK (Sätze bei 38400 oder 9600 Bd, 0 Prüfsummenfehler), `gps_fix`
   `SKIP` „kein Fix“ ist drinnen normal.
2. `gps` draußen nach 5 min. Soll: `gps_fix` OK, ≥ 6 Satelliten, HDOP < 3, Position stimmt mit der
   Karte auf ± 20 m, Höhe plausibel.
3. Baudrate notieren; weicht sie von 38400 ab, in `BoardRevB.h`/Flug-Firmware nachziehen.

Protokoll: Baudrate, Sätze pro 5 s, Prüfsummenfehler, Zeit bis zum Fix, Satelliten, HDOP, Position.

---

## V12 SD-Karte, Loop-Timing, Watchdog, Signalgeber

**Zweck**: Datenlogger-Pfad, Takt der Flugschleife, Neustart durch den Watchdog, LEDs, Summer, Kamera.
**Geräte**: 1S, microSD im Teensy-Slot, optional Kamera oder Oszilloskop/Multimeter an J_CAM Pin 2.

Schritte:
1. `sd`. Soll: `sd_init` OK, `sd_write` > 1 MB/s, längster 4-KiB-Block < 50 ms (Karten mit langen
   Aussetzern sind für den Flug ungeeignet), `sd_read` „Inhalt stimmt“.
2. `timing`. Soll: Mittel < 2 ms, Maximum < 5 ms, 0 Überläufe bei 100 Hz mit IMU, Baro, drei
   Mux-Kanälen, Magnetometer, INA239.
3. `watchdog`. Soll: OK, kein Neustart (Watchdog 3 s bedient, dann abgeschaltet).
   `watchdog fire`: Konsole meldet den Neustart an, nach ca. 1 s startet der Teensy neu, im Banner
   steht `INFO reset_cause Watchdog` und `TEST watchdog_reset OK`. `bench_test.py --commands
   "watchdog,watchdog fire"` verbindet selbst neu; am Monitor von Hand neu verbinden.
4. `led`: rot, grün, blau, weiß nacheinander, je mit Rückfrage. Beide LEDs müssen dieselbe Farbe
   zeigen (Kette LED1 → LED2 → J_LED). `buzzer`: drei Töne. `cam`: 500-ms-Puls an J_CAM Pin 2
   (3,3 V über 1 k), Kamera löst aus oder Multimeter zeigt den Puls.

Protokoll: Kartentyp und Datenraten, längster Block, Timing-Werte, Neustartursache, LED-Farben
richtig (GRB-Reihenfolge), Summer, Kamera.

---

## Reihenfolge und Dauer

| Versuch | Versorgung | Dauer |
|---|---|---|
| V01 Versorgung | 1S, 2S ohne Teensy | 15 min |
| V02 Mux, ADC | 1S, 2S, ARM | 15 min |
| V03 IMU | 1S | 20 min |
| V04 Magnetometer, Achsen | 1S (Akku) | 20 min |
| V05 Baro, SHT40 | 1S | 10 min |
| V06 INA239 | 1S, 2S, Last | 10 min |
| V07 Servos | 1S, 2S | 20 min |
| V08 Rollmotor | 1S, 2S 3 A | 10 min |
| V09 Pyro | 1S, 2S 3 A, ARM, Lämpchen | 10 min |
| V10 LoRa | 1S, Antenne, Bodenstation | 15 min |
| V11 GPS | 1S, draußen | 15 min |
| V12 SD, Timing, Watchdog, Signal | 1S | 10 min |

Am Ende `cal show` und `cal save`, dann einmal 1S aus und ein und `cal show`: die Werte müssen
wiederkommen („Kalibrierung ok“ im Banner). Den Bericht aus `test_reports/` mit dem Protokoll
ablegen.
