# E01: Übertragungsfunktion Servo-Soll → Kardanwinkel

Stand 2026-10-22. Ziel: die Dynamik zwischen dem Servowinkel, den die Firmware kommandiert, und
dem Winkel, den der Kardan wirklich einnimmt. Daraus kommen die Zahlen für die Simulation
(`ServoParams` in `simulation/tvcsim/params.py`: statischer Gain, Eigenfrequenz, Dämpfung, Totzeit)
und für die Firmware (`SERVO_*_GAIN` in `Config.h`, offener Befund 13: 6 oder 23 Servo-Grad je
TVC-Grad). Die Messung von 2025 (`simulation/data/servo_step_response.csv`, SG90 im alten Kardan)
ist die Referenz; der Versuch wird zuerst am selben Aufbau wiederholt, um die Messkette zu prüfen,
und dann am neuen Kardan mit den FrSky W5652H bei 5 V und am 2S-Akku.

## Was der Versuch macht

Der Sketch `firmware/examples/servo_ident/` fährt je Achse eine feste Folge von etwa 77 s:

| Segment | Inhalt | Liefert |
|---|---|---|
| `hold_start` | 2 s Mitte | Nullpunkt, Drift |
| `staircase` | 5 Stufen bis +A, hinunter bis −A, zurück auf 0, je 0,8 s | statische Kennlinie, Nullpunktfehler, Hysterese |
| `steps` | Sprünge A/4, A/2, A in beide Richtungen, dazwischen Mitte, je 1 s | Totzeit, Anstiegszeit, Überschwingen |
| `alternate` | +A, −A, +A, −A, 0, je 0,8 s | Maximalrate (Ratenbegrenzung) |
| `chirp_small` | Sinus 0,3 → 12 Hz in 20 s, Amplitude A/4 | Frequenzgang, Bandbreite |
| `chirp_large` | dasselbe mit A/2 | Nichtlinearität (Ratenbegrenzung im Frequenzgang) |
| `hold_end` | 2 s Mitte | Drift |

A ist die Amplitude in Servo-Grad um die Mitte, Vorgabe: Abstand der Mitte zum mechanischen Fenster
aus `Config.h` (Yaw 92,5 im Fenster 70…115 → 22°, Pitch 82,5 im Fenster 60…105 → 22°). Die
Messung 2025 ging bis ±35° um 95; wer so weit will, setzt `A 35` und vorher das Fenster mit `W`,
nachdem er den Anschlag von Hand (`M`) geprüft hat.

Aufgezeichnet werden mit 500 Hz: Zeit, Segment, Servo-Soll (absolut und relativ), Pulsbreite,
drei Drehraten und drei Beschleunigungen der IMU. Der Kardanwinkel entsteht in der Auswertung aus
der Drehrate um die Kardanachse; der Schwerkraftvektor verankert ihn an jeder Haltephase gegen
Drift. Welche IMU-Achse die Kardanachse ist, findet die Auswertung selbst.

## Material

- Flugcomputer-Aufbau mit Teensy 4.1 (Breakouts) und USB-Kabel
- ICM-20948-Breakout (das des Flugcomputers), für den Versuch **vom Flugcomputer abgenommen**,
  an Wire (SDA 18, SCL 19, 3,3 V, GND) wie bisher; vier Litzen 20 bis 30 cm
- Kardan mit beiden Servos im Rohrstück oder im Außenrahmen, Servos an Pin 28 (Yaw) und 29 (Pitch)
  mit eigener Versorgung (5 V BEC oder Netzteil; W5652H später auch 2S), Masse mit dem Teensy verbunden
- Klebeband/Kabelbinder, Wasserwaage oder Libelle, Multimeter für die Servospannung
- PC mit PlatformIO und Python (`pip install pyserial`)

## Aufbau

1. **IMU auf das Motorrohr** kleben oder binden, so dass sie mit dem Motorrohr mitkippt (nicht auf
   den Außenrahmen). Lage und Ausrichtung sind egal, sie muss nur fest sitzen. Kabel so führen,
   dass sie den Kardan nicht bremsen (Schlaufe, nicht straff).
2. **Rakete oder Rohrstück senkrecht und fest** einspannen, Düse nach unten wie im Flug, Kardan
   frei. Der Aufbau darf während des Versuchs nicht wackeln; was wackelt, sieht der Gyro als
   Kardanbewegung. Senkrecht deshalb, weil die Schwerkraft quer zur Kardanachse stehen muss,
   sonst sieht der Beschleunigungssensor die Drehung nicht (die Auswertung meldet dann
   `Verankerung: holds` statt `accel`).
3. Servos versorgen, Spannung messen und notieren.
4. `pio run -e servo_ident -t upload` im Ordner `firmware/`. Der Teensy stellt beide Servos auf
   Mitte, misst 2 s den Gyro-Nullpunkt (ruhig halten) und meldet sich mit `# servo_ident bereit`.

## Durchführung

Mit dem Aufnahmeskript (empfohlen, ein Befehl je Lauf):

```bash
pip install pyserial
python firmware/tools/capture_serial.py --port COM5 --out E01_sg90_5V_yaw.csv --run Y \
    --note "SG90, alter Kardan, Yaw, 23.10.2026" --volt 5.0
python firmware/tools/capture_serial.py --port COM5 --out E01_sg90_5V_pitch.csv --run P \
    --note "SG90, alter Kardan, Pitch, 23.10.2026" --volt 5.0
```

(`--run B` fährt beide Achsen nacheinander in eine Datei; `--amplitude 35` und
`--cmd "W Y 60 130"` setzen Amplitude und Fenster wie 2025; unter Linux heißt der Port
`/dev/ttyACM0`.)

Oder von Hand mit `pio device monitor -f log2file` (schreibt `platformio-device-monitor-*.log`
in den Ordner, den man danach in `.csv` umbenennt): `?` zeigt den Status, `N <Text>` und
`V <Spannung>` füllen den Dateikopf, `Y` startet den Lauf.

Vor dem ersten Lauf lohnt ein Blick auf das Fenster: `M Y 70`, `M Y 115` stellen den Yaw-Servo an
die Fenstergrenzen aus `Config.h`; schlägt der Kardan vorher an, Fenster mit `W Y <min> <max>`
enger setzen. Während des Laufs nichts anfassen; `S` bricht ab und stellt auf Mitte.

Läufe, die wir haben wollen:

| Lauf | Servo | Spannung | Pulsrate | Zweck |
|---|---|---|---|---|
| 1 | SG90, alter Kardan, Yaw und Pitch | 5 V | 50 Hz | Messkette prüfen, Vergleich mit 2025 |
| 2 | W5652H, neuer Kardan, beide Achsen | 5 V | 50 Hz | Zielmessung, Vergleich zum SG90 |
| 3 | W5652H, neuer Kardan, beide Achsen | 2S (7,4…8,4 V) | 50 Hz | Flugkonfiguration |
| 4 | wie 3 | 2S | 100 oder 200 Hz (`F`) | lohnt eine höhere Pulsrate? |

## Auswertung

```bash
cd simulation
python scripts/ident_servo.py ../E01_sg90_5V_yaw.csv
python scripts/ident_servo.py --synthetic        # Probelauf ohne Hardware
```

Ausgabe: Bericht auf der Konsole, `out/ident_<name>_<achse>.png` mit Zeitverlauf, Kennlinie,
normierten Sprungantworten und Frequenzgang, `out/ident_<name>_<achse>.json` mit allen Zahlen
und ein fertiger `ServoParams(...)`-Block. Kennwerte:

- **K** Kardan-Grad je Servo-Grad und sein Kehrwert (Servo-Grad je TVC-Grad, heute 6 gegen 23).
- **Nullpunktfehler** der Mitte (gehört in `SERVO_*_OFFSET`), **Hysterese** (Spiel im Kardan).
- **Totzeit, Anstiegszeit 10–90 %, Überschwingen, Maximalrate** aus den Sprüngen.
- **PT2 mit Totzeit** (K, ωn, ζ, τ), gefittet an Sprünge und Wechselsprünge, Güte als RMS über
  den ganzen Lauf.
- **Frequenzgang** aus beiden Chirps mit −3-dB-Bandbreite und den Frequenzen für −45° und −90°
  Phase. Unterscheiden sich kleiner und großer Chirp deutlich, begrenzt die Servorate.

Zum Weitergeben an Claude reichen die CSV-Dateien; was in `params.py` und `Config.h` eingetragen
wird, entscheiden wir danach gemeinsam.

## Grenzen

- Die IMU misst die Bewegung des Motorrohrs relativ zur Welt, nicht relativ zum Rumpf. Wackelt der
  Aufbau, steckt das im Ergebnis. Abhilfe: steifer Aufbau; später eine zweite IMU am Rumpf.
- Ohne Last am Servo (kein Motor im Rohr) ist die Trägheit kleiner als im Flug. Für den Flugwert
  einen E12-Dummy gleicher Masse (64 g) in den Adapter stecken.
- Der Sketch steuert die Servos als 16-Bit-PWM mit derselben Grad-zu-Puls-Abbildung wie
  `PWMServo` in der Flug-Firmware, aber ohne deren Rundung auf ganze Grad. Die Rundung (0,17°
  Kardan bei K = 1/6) kommt im Flug dazu und steht in der Simulation (`quantize_servo`).
- Die Pulsrate von 50 Hz bringt bis zu 20 ms Latenz, die in der gemessenen Totzeit enthalten ist,
  wie im Flug.
