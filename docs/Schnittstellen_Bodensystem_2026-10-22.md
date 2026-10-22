# Schnittstellen Bodensystem: Rakete, Start-/Landepad, Bodenstation, Handy

Stand 2026-10-22. Diese Datei legt fest, was die drei Teile voneinander erwarten, damit Pad und
Bodenstation getrennt konstruiert werden können. Zahlen der Rakete kommen aus `cad/params.py` und
`cad/mass_properties.md` (Konfiguration `erstflug`, Rohr 700 mm); bei Änderungen dort gilt das Modell.

```
 Handy (Browser)  ──WLAN──  Bodenstation  ──Zündleitung 15 m──  Pad (Zündkasten, Anzünder im Motor)
                              │
                              └──LoRa 433 MHz──────────────────  Rakete (E22-400T22S an Serial8)
```

## S1 Rakete → Pad (mechanisch)

| Größe | Erstflug | Voll (Landung, später) |
|---|---|---|
| Rumpf | Ø 75,0 außen, Papprohr, Unterkante 20 mm über der Düse | gleich |
| Motor | TSP E12-0, Ø 24, ragt 20 mm unter das Rohr | gleich |
| Gesamtlänge | 950 mm | 1250 mm |
| Masse / Schwerpunkt | ca. 760 g, 318 mm über der Düse | ca. 920 g ohne Treibstoff bei der Landung, 477 mm |
| Beine | keine | 4, Fuß 35 × 35 auf r ≈ 320 mm, Fußsohle ca. 70 mm unter der Düse |

Anforderungen an das Pad:

- **Start ohne Startschiene.** Die Rakete steht senkrecht auf drei Auflagen unter der Rohrunterkante
  (Ringfläche r = 36,3 … 37,5 mm). Seitlich halten sie drei Führungen mit 1 bis 2 mm Luft zum Rohr,
  mindestens 150 mm hoch, ohne Klemmung: die Rakete hebt frei ab.
- **Kardan frei:** unterhalb der Rohrunterkante kein Teil innerhalb r = 30 mm. Die Düse wandert bei 7°
  um 9,3 mm seitlich (Kardanpunkt 76,5 mm über der Düse).
- **Abgasstrahl:** Düse mindestens 80 mm über einer Strahlplatte (Stahl 2 mm auf nicht brennbarer Unterlage)
  mit seitlichem Abzug. Brenndauer des E12 ca. 3 s.
- **Ruhe vor dem Start:** die Firmware kalibriert Kreisel und Lage auf dem Pad. Das Pad steht steif,
  ist mit Libelle und Stellfüßen auf besser als 1° ausgerichtet und wackelt nicht im Wind.
- **Landung (Konfiguration voll):** ebene, nicht brennbare Fläche, mindestens Ø 1200 mm. Führungen und
  Auflagen sind abnehmbar und stehen nicht über die Fläche.
- **Zündkasten am Pad:** Klemmen für den Anzünder (30 cm Kabel mit Krokoklemmen) und eine Buchse für die
  Zündleitung von der Bodenstation (S2). Kurzschlussbrücke (Shunt-Stecker) für den Aufbau.

## S2 Bodenstation ↔ Pad (Zündleitung)

| Größe | Festlegung |
|---|---|
| Leitung | 2 × 0,75 mm², 15 m (Sicherheitsabstand mindestens 10 m, bei E-Motoren üblich) |
| Stecker | XT30: Buchse am Zündkasten des Pads, Stecker an der Leitung |
| Zündstrom | 3S-LiPo der Bodenstation (11,1 V), mindestens 5 A für 1 s; Leitung + Anzünder ca. 1,5 Ω |
| Durchgangsprüfung | höchstens 10 mA, ständig, solange nicht gezündet wird |
| Schaltung | zwei unabhängige Schalter in Reihe: Relais (nur bei steckendem Schlüssel und ARM) und MOSFET (vom Rechner) |

## S3 Bodenstation ↔ Rakete (Funk)

| Größe | Festlegung |
|---|---|
| Funkmodul | Ebyte E22-400T22S auf beiden Seiten, 433 MHz, transparenter UART-Modus, 9600 Bd am UART |
| Luftrate / Kanal | 2,4 kbit/s, Kanal 0x17 (433,125 MHz), Adresse 0x0000; feste Werte in beiden Firmwares |
| Rakete → Boden | Telemetrie 10 Hz: Flugzustand, Zeit, Höhe, Steiggeschwindigkeit, Lage (Quaternion), Kardanwinkel, Spannung 1S und 2S, ARM, Pyro-Durchgang, GPS 1 Hz |
| Boden → Rakete | Kommandos mit Quittung: PING, CALIBRATE, PAD_READY_QUERY, ABORT |
| Rahmen | Vorschlag: `0xA5 0x5A`, Typ (1 Byte), Länge (1 Byte), Nutzlast, CRC-16/CCITT |

Das Telemetrieprotokoll gehört der Flug-Firmware und liegt seit dem 22.10.2026 abends in
`firmware/lib/flightcore/KartonautProtocol.h` (reines C, gepackte Strukturen, little-endian): Rahmen wie
oben, `KnTelemetry` 22 Byte bei 10 Hz (Zeit, Zustand, Flags mit ARM/Durchgang/gezündet, Höhe, vz,
Quaternion, TVC-Winkel, 1S/2S), `KnStatus` und `KnGps` 1 Hz, `KnEvent` je Zustandsübergang (dreimal),
`KnCommand` (`PING`, `CALIBRATE`, `PAD_READY_QUERY`, `ABORT`, `SAFE`, `LOG_START/STOP`, `TESTRIG_THRUST`)
mit `KnAck`. Die Bodenstation kopiert die Datei unverändert; Parser-Referenz ist `Telemetry.cpp`
(`KnParser`), Prüfwerte in `firmware/test/test_flightcore`.

**Startsperre:** die Bodenstation zündet nur, wenn alle Bedingungen gleichzeitig erfüllt sind:
1. Der Schlüssel steckt in der Bodenstation und ARM ist eingeschaltet.
2. Der Anzünder hat Durchgang.
3. Die Telemetrie der Rakete ist jünger als 1 s, meldet den Zustand PAD_READY und meldet den Schlüsselschalter der Rakete scharf.
4. Der Countdown läuft bis null ohne Abbruch.

## S4 Handy ↔ Bodenstation

| Größe | Festlegung |
|---|---|
| Verbindung | WLAN-Zugangspunkt der Bodenstation (ESP32-S3), SSID `MissionSpace-GS`, WPA2; geht mit Android und iOS ohne App |
| Oberfläche | Webseite unter `http://192.168.4.1`, vom ESP32 ausgeliefert, funktioniert ohne Internet |
| Daten | WebSocket `/ws`, JSON: Telemetrie 10 Hz von der Station zum Handy, Kommandos vom Handy zur Station |
| Rechte des Handys | anzeigen, Kalibrieren anstoßen, Countdown starten, **Abbruch jederzeit**. Scharf schalten geht nur mit Schlüssel und ARM-Schalter an der Station; ohne beides ist der Start-Knopf am Handy gesperrt. |
| Verbindungsabbruch | verliert die Station das Handy während des Countdowns, bricht sie ab |
| Taster an der Station | ein Start-Taster funktioniert auch ohne Handy |

## Wer was baut

| Teil | Ordner | Darf nicht anfassen |
|---|---|---|
| Start-/Landepad | `cad/landingpad.py`, `docs/img/cad/landingpad*.png`, eigener Abschnitt in `cad/README.md` | `cad/params.py`, `build.py` und die übrigen Module (nur importieren) |
| Bodenstation | `groundstation/` (Konzept, Schaltung, Stückliste, Firmware ESP32-S3, Weboberfläche) | `firmware/`, `hardware/`, `simulation/`, `cad/` |
