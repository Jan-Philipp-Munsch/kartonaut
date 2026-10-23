# E02: Charakterisierung Servos und TVC-Kardan auf dem Mainboard rev B1

Stand 2026-10-23. Durchführung von Anfang bis Ende: was auf dem Tisch liegt, wo die externe IMU
sitzt und wie sie an die Platine kommt, welche Folge gefahren und aufgezeichnet wird, wie die
Datei aussieht und wie sie ausgewertet wird. Der Versuch ist die Fortsetzung von E01
(Branch `experiments/servo-ident`, Breakout-Aufbau) auf der Platine: gleiche Anregungsfolge,
gleiches Dateiformat, dazu die Platinen-IMU als zweite Messung am Rumpf.

**Ziel**: Übertragungsfunktion Servo-Soll → Kardanwinkel je Achse: statische Kennlinie (Kardan-Grad je
Servo-Grad, Nullpunktfehler, Hysterese), Sprungantwort (Totzeit, Anstiegszeit, Überschwingen,
Maximalrate), Frequenzgang (Bandbreite, Phasenverlust) und daraus `ServoParams` für die Simulation
und `SERVO_*_GAIN/OFFSET` für `Config.h`.

## 1. Material

| Teil | Hinweis |
|---|---|
| Mainboard rev B1 mit Teensy, `revb_test` geflasht, Kalibrierung aus V02/V03/V07 gespeichert | `cal show` muss `valid` mit SERVO-Bit zeigen, sonst nimmt der Versuch die Mitten aus `Config.h` |
| 1S-Versorgung (Akku oder Netzteil 4,0 V, 500 mA) an J_BAT1 + JP1 | Teensy läuft nur so |
| 2S-Versorgung an J_BAT2 + JP2: erst Netzteil 7,4 V mit 2 A Begrenzung, für den Flugwert der 2S-Akku | VSERVO liegt direkt am 2S, Servos müssen bis 8,4 V freigegeben sein |
| Kardan mit beiden TVC-Servos, montiert im Rohrstück oder im Raketenrumpf, Düse nach unten | Servos an **J_SERVO1** (Yaw) und **J_SERVO2** (Pitch), XH: Pin 1 Signal, 2 VSERVO, 3 GND_PWR |
| Externe IMU: **SparkFun ICM-20948-Breakout** (das aus dem Breakout-Flugcomputer) | I²C-Adresse 0x68 oder 0x69 (ADR-Brücke), die Konsole probiert beide |
| **Qwiic-Kabel JST-SH 4-polig, 20–30 cm** vom Breakout zu **J_QWIIC** auf der Platine | Belegung J_QWIIC: 1 GND, 2 3V3, 3 SDA, 4 SCL (Qwiic-Standard, direkt steckbar) |
| Motor-Dummy mit der Masse des Flugmotors (E12: 64 g) im Motoradapter | sonst ist die Trägheit kleiner als im Flug |
| Halterung: Rohr senkrecht in Schraubstock mit Holzbacken oder Stativklemme, Tisch stabil | was wackelt, zählt der Kardan-Gyro als Kardanbewegung |
| Klebeband/Kabelbinder, Libelle, Multimeter (Servospannung), Maßband (Hebelarm Gimbal–IMU) | |
| PC mit `pio`, `pyserial`, Repo mit dem Branch `experiments/servo-ident` für die Auswertung | |

## 2. Aufbau

1. **Rohr senkrecht einspannen**, Düse nach unten, Kardan frei beweglich über den ganzen Weg. Mit
   der Libelle senkrecht stellen: die Auswertung verankert den Kardanwinkel an der Schwerkraft, dafür
   muss die Schwerkraft quer zur Kardanachse stehen. Nichts darf gegen Servohörner oder Gestänge laufen.
2. **Externe IMU auf das Motorrohr** kleben oder mit Kabelbinder binden: auf das Teil, das mit der
   Düse kippt, **nicht** auf den Außenrahmen. Lage und Ausrichtung sind egal, der Chip muss nur
   fest sitzen (doppelseitiges Klebeband plus Kabelbinder). Welche IMU-Achse die Kardanachse ist,
   findet die Auswertung aus den Daten.
3. **Qwiic-Kabel** vom Breakout zu J_QWIIC. Schlaufe lassen, das Kabel darf den Kardan nicht bremsen
   und nicht straff werden, wenn der Kardan an der Fenstergrenze steht. Das Breakout bekommt 3V3
   von der Platine (Qwiic Pin 2), kein eigenes Netzteil.
4. **Servos** an J_SERVO1 (Yaw) und J_SERVO2 (Pitch). Beim ersten Mal nur 1S einschalten, dann 2S
   mit 2 A Begrenzung: ein falsch gepoltes Servo zieht sofort Strom.
5. **Platine** am Rumpf befestigen, wenn der Rumpf vorhanden ist (so misst die Platinen-IMU die
   Rumpfbewegung während der Servoläufe); sonst neben dem Aufbau auf dem Tisch, nicht lose.
6. USB zum PC. `pio device monitor` oder gleich das Aufnahmeskript.

Hebelarm notieren: Abstand Kardan-Drehpunkt bis Mitte des IMU-Chips (für die Plausibilität der
Querbeschleunigung in der Auswertung, nicht zwingend).

## 3. Vorbereitung an der Konsole (einmal je Aufbau)

```
status                 1S/2S/ARM, Bausteine; 2S muss da sein
cal show               Servo-Mitten aus V07 vorhanden? (servo_us 1 ... und 2 ...)
tvc imu                externe IMU gefunden? TEST tvc_ext_imu OK
tvc status             Mitten (aus der Kalibrierung oder Config.h), Fenster, Vorgabe-Amplitude, Dauer
tvc move Y 70          Kardan an die untere Fenstergrenze Yaw stellen (3 s), hinschauen: Anschlag?
tvc move Y 115         obere Grenze
tvc move P 60 / 105    dasselbe für Pitch
```

Schlägt der Kardan vor der Fenstergrenze an: Fenster enger setzen, `tvc window Y 75 110`, bis zu
beiden Seiten 2–3° Luft bleiben. Das Fenster gilt nur für diesen Versuch; was in `Config.h` kommt,
entscheiden wir nach der Auswertung. Die Vorgabe-Amplitude A ist der kleinere Abstand der Mitte zu
den Fenstergrenzen (Yaw 92,5 im Fenster 70–115 → 22°); `tvc amp 18` setzt sie kleiner.

Dann `tvc zero`: 2 s Gyro-Nullpunkt beider IMUs, Aufbau nicht berühren. Das macht `tvc run` auch
selbst, aber so sieht man vorher, ob die Werte klein sind (< 1 °/s).

## 4. Die Folge, die gefahren wird

Je Achse etwa 77 s, Kommando in Servo-Grad relativ zur Mitte, A = Amplitude:

| Segment (`seg`) | Inhalt | Liefert |
|---|---|---|
| 1 `hold_start` | 2 s Mitte | Nullpunkt, Drift |
| 2 `staircase` | 5 Stufen bis +A, hinunter bis −A, zurück auf 0, je 0,8 s | statische Kennlinie, Nullpunktfehler, Hysterese |
| 3 `steps` | Sprünge A/4, A/2, A in beide Richtungen, dazwischen Mitte, je 1 s | Totzeit, Anstiegszeit, Überschwingen |
| 4 `alternate` | +A, −A, +A, −A, 0, je 0,8 s | Maximalrate |
| 5 `chirp_small` | Sinus 0,3 → 12 Hz logarithmisch in 20 s, Amplitude A/4 | Frequenzgang, Bandbreite |
| 1 `hold_start` | 1 s Mitte | |
| 6 `chirp_large` | dasselbe mit A/2 | Nichtlinearität, Ratenbegrenzung |
| 7 `hold_end` | 2 s Mitte | Drift |

Die andere Achse steht währenddessen auf ihrer Mitte. Aufgezeichnet wird mit 500 Hz je Zeile:
Zeit, Segment, Achse, Servo-Soll absolut und relativ, Pulsbreite, drei Drehraten und drei
Beschleunigungen der externen IMU (±500 °/s, ±4 g, Tiefpass 152 Hz); dazu je Zeile eine
`#body,`-Zeile mit Drehrate und Beschleunigung der Platinen-IMU (Rumpf). Die Servos werden als
16-Bit-PWM mit der Grad-zu-Puls-Abbildung aus `Config.h` angesteuert (feiner als die
Servo-Bibliothek), Pulsrate 50 Hz wie im Flug, einstellbar mit `tvc frame`.

`S` oder `q` während des Laufs bricht ab und stellt beide Servos auf Mitte.

## 5. Läufe und Aufnahme

Ein Befehl je Lauf, die Datei bekommt alles von `# kartonaut servo_ident v1` bis `# END`:

```bash
cd firmware
python tools/capture_tvc.py --out ../E02_w5652h_ps_7V4_yaw.csv --run Y --volt 7.4 \
    --note "W5652H, Kardan v2, Netzteil 7,4 V, Motor-Dummy 64 g, 2026-10-xx"
python tools/capture_tvc.py --out ../E02_w5652h_ps_7V4_pitch.csv --run P --volt 7.4 --note "..."
```

(`--run B` fährt beide Achsen in eine Datei, `--amplitude 18`, `--frame-hz 100`, `--cmd "tvc window Y 75 110"`
für Fenster; unter Linux heißt der Port `/dev/ttyACM0`, sonst `--port COM7`.)

Vor jedem Lauf die Servospannung am Multimeter an J_SERVO1 Pin 2 gegen Pin 3 messen und mit
`--volt` angeben; die Konsole schreibt zusätzlich den INA239-Wert (`# vservo_ina_v`) in den Kopf.

| Lauf | Servo / Kardan | Versorgung | Pulsrate | Zweck |
|---|---|---|---|---|
| 1 | W5652H, Kardan v2, ohne Motor-Dummy | Netzteil 7,4 V | 50 Hz | Messkette prüfen, Vergleich zu E01 (gleiche Servos am Breakout) |
| 2 | wie 1, mit Motor-Dummy 64 g | Netzteil 7,4 V | 50 Hz | Einfluss der Last |
| 3 | wie 2 | 2S-Akku voll (8,2 V) | 50 Hz | Flugkonfiguration, Start |
| 4 | wie 2 | 2S-Akku bei 7,0 V | 50 Hz | Flugkonfiguration, Ende des Flugs |
| 5 | wie 3 | 2S-Akku | 100 Hz, dann 200 Hz (`--frame-hz`) | lohnt eine höhere Pulsrate? |
| 6 | wie 3, Amplitude 10° | 2S-Akku | 50 Hz | Kleinsignal, Linearität |

Jeder Lauf auf beiden Achsen. Zwischen den Läufen die Servos 1 min ruhen lassen (Erwärmung),
nach Lauf 3 die Befestigung der IMU prüfen (nachgeben = Hysterese im Ergebnis).

Während des Laufs: Aufbau nicht berühren, Tisch nicht anstoßen, nicht am Kabel ziehen. Hört sich
ein Servo an der Fenstergrenze an wie blockiert: `S`, Fenster enger, Lauf wiederholen.

## 6. Auswertung

Das Auswerteskript liegt auf dem Branch `experiments/servo-ident`:

```bash
git checkout experiments/servo-ident -- simulation/tvcsim/ident.py simulation/scripts/ident_servo.py
cd simulation
python scripts/ident_servo.py ../E02_w5652h_ps_7V4_yaw.csv
python scripts/ident_servo.py --synthetic        # Probelauf ohne Hardware
```

Ausgabe: Bericht auf der Konsole, `out/ident_<name>_<achse>.png` (Zeitverlauf, Kennlinie,
normierte Sprungantworten, Frequenzgang), `out/ident_<name>_<achse>.json` mit allen Zahlen und ein
fertiger `ServoParams(...)`-Block. Die `#body,`-Zeilen überliest das Skript; sie sind für den
nächsten Schritt (Rumpfbewegung herausrechnen) da.

Was wir aus den Läufen eintragen wollen:

- **K** Kardan-Grad je Servo-Grad und sein Kehrwert → `SERVO_*_GAIN` (heute 23 in `Config.h`, E01-Befund: 6?).
- **Nullpunktfehler** → `SERVO_*_OFFSET` bzw. die Servo-Mitte in der Kalibrierung (`cal servo`).
- **Totzeit, Anstiegszeit, Überschwingen, Maximalrate** → `ServoParams` in `simulation/tvcsim/params.py`.
- **Bandbreite** und Unterschied kleiner/großer Chirp → Reglerauslegung, Entscheidung zur Pulsrate.
- **Spannungsabhängigkeit** (Lauf 3 gegen 4) → ob die Reglergewinne über den Flug angepasst werden müssen.

Zum Weitergeben reichen die CSV-Dateien und die Notizen aus Abschnitt 7.

## 7. Protokoll

Je Lauf: Dateiname, Servo-Typ und Kardan, Versorgung mit gemessener Spannung, Motor-Dummy ja/nein,
Pulsrate, Amplitude, Fenster, Hebelarm Drehpunkt–IMU, Raumtemperatur, Auffälligkeiten (Anschlag,
Summen, Zittern, Kabel), `TEST tvc_run_Y/P OK` mit Zeilenzahl (Soll ca. 38 500 je Achse bei 500 Hz),
Gyro-Nullpunkte beider IMUs aus den `CAL tvc_*_gyro_bias_dps`-Zeilen.

## 8. Grenzen

- Die externe IMU misst die Bewegung des Motorrohrs gegen die Welt. Rumpfbewegung steckt mit drin;
  mit der Platinen-IMU am Rumpf lässt sie sich später abziehen (noch nicht im Skript).
- Die 16-Bit-PWM bei 50 Hz löst 0,3 µs auf, die Servo-Elektronik selbst typisch 1–2 µs; die Chirps
  sind damit glatt, die Rundung auf ganze Grad der Flug-Firmware (`PWMServo`) kommt im Flug dazu.
- 50 Hz Pulsrate bringen bis zu 20 ms Latenz; sie steckt in der gemessenen Totzeit wie im Flug.
- Das I²C-Lesen der ICM-20948 (12 Byte bei 400 kHz) und das SPI-Lesen der Platinen-IMU brauchen
  zusammen unter 1 ms je 2-ms-Takt; bei 500 Hz bleibt die Zeitbasis sauber, die Zeitspalte ist die
  Messzeit des Kommandos.
