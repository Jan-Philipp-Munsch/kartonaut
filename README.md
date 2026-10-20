# Mission Space

Eine Modellrakete mit Schubvektorsteuerung (TVC) und selbst entwickeltem Flugcomputer,
aufgebaut nach dem Vorbild der „Scout F“ von [BPS.space](https://bps.space).
Der Motor hängt in einem Kardan mit zwei Servos, ein Rollmotor hält die Rollachse,
ein Fallschirm bringt die Rakete zurück. An Bord sitzt ein Teensy 4.1 mit IMU,
Barometer, Strommonitor, SD-Logger und 433-MHz-Funk zur Bodenstation.

<img src="docs/img/model_rocket.png" width="220" align="right" alt="Gesamtmodell (Blender)">

| | |
|---|---|
| Rumpf | Ø 75 mm, 1 m lang, 3D-gedruckte Spitze und Landebeine |
| Motor | Estes E12 (24 mm) im Kardan, Schubkurve E12/F35 in der Simulation |
| Startmasse | ca. 0,9 kg geplant |
| Flugcomputer | Teensy 4.1, ICM-20948 (DMP), BMP280, INA219, HC-12, microSD |
| Aktoren | 2× SG90 (TVC), Rollmotor an H-Brücke, Fallschirm-Servo |
| Regelung | PID auf Pitch/Yaw mit Momenten-Umrechnung in den TVC-Winkel, PID auf Roll |
| Status | Firmware und Elektronik auf dem Tisch getestet, Mainboard rev A spezifiziert, noch kein Flug |

Der aktuelle Stand aller Arbeitspakete, die Befunde aus der Code-Durchsicht und die
nächsten Schritte stehen in [PROJECT.md](PROJECT.md).

## Aufbau des Repos

```
spacecode/            Flug-Firmware (PlatformIO, Teensy 4.1)        -> spacecode/README.md
  src/                Module: Sensors, KalmanZ, Control, SDLogger, Timing, Indicators
  examples/           eigenständige Test-Sketches (Funk, I2C-Scan, Pyro-MOSFET)
hardware/mainboard/   Spezifikation des Mainboards rev A, Umriss (DXF), Platzierungsplan
docs/                 Render-Skript für Blender und Bilder
PROJECT.md            Projektdatei: Eckdaten, Fortschritt, Befunde, Änderungsprotokoll
```

Die Bodenstation (Arduino Nano mit HC-12-Empfänger) ist ein eigenes Repo:
[groundcode](https://github.com/Jan-Philipp-Munsch/groundcode).
Die 6DOF-Simulation (MATLAB/Simulink, Monte-Carlo und PID-Suche) und die
Blender-CAD-Modelle liegen außerhalb dieses Repos.

## Firmware bauen und flashen

Voraussetzung ist [PlatformIO](https://platformio.org) (CLI oder VS-Code-Erweiterung).

```bash
cd spacecode
pio run                      # Flug-Firmware bauen
pio run -t upload            # auf den Teensy 4.1 flashen
pio device monitor           # serielle Konsole, 115200 Bd
pio run -e radio_beacon      # einen Test-Sketch aus examples/ bauen
```

Alle Pins, Reglerparameter, Filterkonstanten und Debug-Schalter liegen in
[`spacecode/src/Config.h`](spacecode/src/Config.h). Die Regler sind dort
abgeschaltet, bis der erste Flugtest ansteht.

## Wie die Firmware arbeitet

Die Hauptschleife läuft mit festem Takt (100 Hz) und erledigt pro Durchlauf:

1. **Sensoren lesen.** Die IMU liefert über den DMP Quaternion, Beschleunigung und
   Drehrate aus der FIFO, das Barometer die Höhe, der INA219 Spannung und Strom.
2. **Lage integrieren.** Die Drehrate des Gyros wird zu Yaw, Pitch und Roll aufsummiert.
   Im Flug sind Kompass und Beschleunigungsstützung unbrauchbar, deshalb rein inertial.
3. **Höhe schätzen.** Ein Kalman-Filter mit den Zuständen Höhe und Vertikalgeschwindigkeit
   fusioniert Barometer und Vertikalbeschleunigung.
4. **Regeln.** Ein PID auf Pitch und Yaw liefert ein Moment, das über
   `M = l · m · |a| · sin(δ)` in den TVC-Winkel und dann in Servo-Grad umgerechnet wird.
   Ein zweiter PID treibt den Rollmotor über die H-Brücke.
5. **Loggen.** Ein 88-Byte-Frame pro Durchlauf geht in einen Seitenpuffer; physische
   Schreibzugriffe und Syncs auf die SD-Karte passieren nur in freier Zeit vor der
   nächsten Deadline. Am Boden wird das Binärlog als CSV exportiert.

Details zu den Modulen, dem Log-Format und den Test-Sketches:
[spacecode/README.md](spacecode/README.md).

## Hardware

Heute hängen alle Sensoren als Breakouts mit Dupont-Kabeln am Teensy. Das ist im Flug
das größte Ausfallrisiko. [hardware/mainboard/](hardware/mainboard/README.md) spezifiziert
deshalb ein Mainboard rev A als Längs-Schlitten 54 × 120 mm mit Teensy-Sockel, IMU auf der
Rollachse, zwei Buck-Wandlern, zwei Pyro-Kanälen mit Arming und allen Steckern an den
Stirnseiten. Schaltplan und Layout in KiCad sind der nächste Schritt.

## Bekannte Baustellen

- Masse und Reglerparameter zwischen Firmware und Simulation abgleichen.
- Lage als Quaternion aus dem Gyro statt komponentenweiser Integration (gilt nur für
  kleine Winkel ohne Rollen).
- Gyro-Kalibrierung auf der Rampe statt fester Offsets.
- Flugzustandsautomat (Pad, Boost, Coast, Apogäum, Bergung) und Pyro-Logik mit Arming.
- Telemetrieprotokoll über HC-12.

Die vollständige Liste mit Begründungen steht in [PROJECT.md §5](PROJECT.md).
