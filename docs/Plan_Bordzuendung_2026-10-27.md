# Plan: Motorzündung an Bord über ein gesichertes Funkprotokoll (27.10.2026)

**Entscheidung Jan, 27.10.2026:** Die Rakete zündet ihren Motor selbst über Pyro-Kanal 1. Gestartet wird per Funk vom
Laptop aus, nachdem die Rakete am Pad eingeschaltet und von Hand entsichert wurde. Die Bodenstation ist der Laptop mit
dem **zweiten Mainboard rev B1** (eigener Teensy 4.1, E22-400T22S) als Funkbrücke über USB, dazu die Startrampe.
Zündbox, 15-m-Zündleitung, ESP32-Station und das USB-Modul E22-400T22U entfallen für *Kartonaut 1* (Jan, 27.10. abends).
Antennen: 433-MHz-Wendeln aus den alten HC-12-Modulen, direkt an den ANT-Pad des E22 gelötet (IPEX bleibt frei).

**Gründe:** (1) Die eigenständige Zündung muss vor den Landeversuchen ohnehin erprobt werden (Landebrennen,
`LandingBurn`). (2) Die Zündung lässt sich auswerten: Verzögerung Befehl → Durchbrennen → Schub, Spannungseinbruch.
(3) Keine Zündbox, nichts zusätzlich zu koordinieren. (4) Die Rakete kennt den Startzeitpunkt exakt und zeichnet ab
dem Schärfen mit voller Rate auf.

Dieser Plan ist die Vorgabe für die Umsetzung (Cloud-Session). Er beschreibt, was gebaut wird, nicht wie der Code im
Einzelnen aussieht.

## 1. Was Platine und Firmware heute schon können

| Baustein | Stand | Quelle |
|---|---|---|
| Pyro-Kanäle 1 und 2 (J9, J10, JST-XH 2 liegend), Low-Side-FET AO3400A, Gate über 100 Ω | bestückt | `hardware/mainboard/README.md` §3, `kicad/circuit.py` |
| Hardware-Entsicherung: J_ARM (J4) mit Kippschalter ≥ 5 A, schaltet VBAT_PROT → VBAT_ARMED | vorhanden | README §3 Zeile „J_ARM“ |
| Durchgangsprüfung je Kanal (100 k / 33 k am Drain, über den Analogmux), Arming-Spannung auf Mux-Kanal 6 | vorhanden | README §5 |
| Elektronik am 1S (TPS63070), Pyro und Servos am 2S: ein Zündeinbruch zieht den Teensy nicht in den Neustart | vorhanden | README §3 |
| `PyroLogic` mit Pulsdauer je Kanal, Abbruch bei Durchgangsverlust, höchstens 2 Versuche | vorhanden | `firmware/src/Pyro.h/.cpp` |
| `PYRO_IGNITER_PULSE_MS = 1000`, `PYRO_CH_IGNITER = 1` (Index, also Kanal 2) für das Landebrennen | vorhanden | `firmware/src/Config.h` |
| Funkrahmen A5 5A, CRC-16, TLM 10 Hz, EVT, ACK, Kommandos PING/CALIBRATE/PAD_READY/ABORT/SAFE | vorhanden | `firmware/src/Telemetry.h` |
| Zustände SAFE, PAD_READY, BOOST … ; Startdetektion über Beschleunigung | vorhanden | `firmware/src/FlightState.h` |

**Kanalwahl:** Motorstart auf **Pyro 1 (J9, Index 0)**. Pyro 2 (J10) bleibt dem Anzünder des Landebrennens
vorbehalten (`PYRO_CH_IGNITER`). Bei *Kartonaut 1* sind beide frei, weil der Schirm per CO₂-Servo ausgeworfen wird.

## 2. Risiken, die vor dem ersten scharfen Versuch geklärt sein müssen

1. **Polyfuse F1 im Zündpfad.** Zündstrom und Servostrom laufen beide durch F1 (1812L300/24, 3 A halten, 6 A
   auslösen, laut Hersteller höchstens etwa 2 s bis zum Auslösen bei 8 A). Ein Anzünder, der in einigen 10 ms
   durchbrennt, ist unkritisch. Bleibt er nach dem Abbrennen niederohmig, fließt Strom bis zum Pulsende; löst F1 dann
   aus, sind die TVC-Servos beim Abheben stromlos. **Gegenmaßnahme in der Firmware:** Startpuls endet beim ersten von
   (a) Schub erkannt, (b) Durchgang weg, (c) `LAUNCH_PULSE_MAX_MS` = 300 ms. **Messung am Tisch:** Widerstand der
   TSP-Anzünder, Strom mit Ersatzlast (Leistungswiderstand passend zum gemessenen Anzünder) über 300 ms, VSERVO dabei
   beobachten.
2. **Strom ist nicht direkt messbar.** Die Pyro-Kanäle liegen vor dem Shunt, der INA239 sieht den Zündstrom nicht.
   Messbar sind: Spannung VBAT_ARMED (Mux-Kanal 6) während des Pulses, daraus der Strom grob über den Innenwiderstand
   des 2S; Zeitpunkt Durchgang weg; Zeitpunkt Schub (Beschleunigung); VSERVO-Strom am INA239; 1S-Spannung.
3. **Kabelweg.** J9 sitzt auf der Platine in Rohr B, der Anzünder steckt unten in der Düse. Die Leitung (zwei Adern
   26 AWG Silikon, XHP-2 an J9) läuft durch den Schlitten und am Kardan vorbei nach unten, mit genug Spiel für den vollen
   Kardanausschlag; sie wird beim Zünden aus der Düse geblasen und hängt danach lose. Prüfung im CAD und am Kardan
   (Kardan per Hand voll ausschlagen, Leitung darf nicht klemmen). Gehört in die Bauanleitung.
4. **Sicherheit am Pad.** Zwischen Arming-Schalter und Weggehen ist die Rakete scharf. Deshalb zündet die Firmware
   nur bei allen Bedingungen aus §4, und das Funk-ARM ist zeitlich begrenzt.

## 3. Funkprotokoll (Erweiterung von `Telemetry.h`)

### 3.1 Neue Kommandos (Boden → Rakete)

| Typ | Name | Nutzlast | Wirkung |
|---|---|---|---|
| 0x25 | `CMD_ARM` | seq (1), MAC (8) | nur aus PAD_READY: Vorbedingungen prüfen, bei Erfolg Zustand ARMED, neue Zufallszahl erzeugen |
| 0x26 | `CMD_LAUNCH` | seq (1), MAC (8) | nur aus ARMED: Countdown starten |
| 0x27 | `CMD_HEARTBEAT` | seq (1) | während ARMED und COUNTDOWN mindestens 2 Hz; fehlt er länger als 1 s, bricht die Rakete ab |

`CMD_ABORT` (0x23) bleibt **ohne** MAC, damit ein Abbruch nie an der Authentisierung scheitert. Er ist in ARMED und
COUNTDOWN immer wirksam und führt nach SAFE (nicht ABORT, denn der Motor hat nicht gezündet).

### 3.2 Antworten (Rakete → Boden)

- `ACK` auf `CMD_ARM` trägt zusätzlich die **Zufallszahl** `nonce` (4 Byte) und eine Bitmaske der Vorbedingungen
  (1 Byte, gesetztes Bit = erfüllt). Bei ACK_REFUSED sieht der Laptop daran, was fehlt.
- `ACK` auf `CMD_LAUNCH` trägt die verbleibende Countdownzeit.
- `TLM` bleibt 16 Byte. Neue Zustände (§4) kommen über das bestehende Feld `state`.
- Neuer Rahmen `IGN` 0x04 einmal nach der Zündung: Zeitmarken (ms relativ zum LAUNCH-Ende des Countdowns) für
  Puls an, Durchgang weg, Schub erkannt, Puls aus; minimale Spannung VBAT_ARMED und 1S; Grund für Pulsende.

### 3.3 Authentisierung

- **Gemeinsamer Schlüssel** 16 Byte, in der Firmware aus `firmware/src/Secrets.h` und im Laptop-Skript aus einer
  Datei `secrets.json`. Beide Dateien stehen in `.gitignore`; im Repo liegen nur Vorlagen (`Secrets.example.h`,
  `secrets.example.json`). Ohne Schlüssel baut die Firmware mit `LAUNCH_ENABLED = false`.
- **MAC** = die ersten 8 Byte von HMAC-SHA256(Schlüssel, Kommandotyp ‖ seq ‖ nonce ‖ Raketen-ID).
- **Nonce:** 32 Bit aus dem Hardware-Zufallsgenerator des Teensy 4.1 (TRNG). Ablauf in zwei Schritten:
  1. Der Laptop sendet `CMD_PING`; das `ACK` darauf trägt in PAD_READY die aktuelle nonce A.
  2. `CMD_ARM` trägt den MAC über nonce A. Die Rakete verwirft A sofort (auch bei Ablehnung) und schickt im `ACK` auf
     ARM die neue nonce B.
  3. `CMD_LAUNCH` trägt den MAC über nonce B. B wird nach Gebrauch oder beim Verlassen von ARMED verworfen.
  Jede nonce gilt genau einmal; kein aufgezeichneter Befehl ist wiederholbar.
- Wirkung: Ein anderes 433-MHz-Gerät, ein Bitfehler, den die CRC nicht erkennt, oder ein aufgezeichneter alter Befehl
  kann nicht schärfen und nicht zünden.

## 4. Zustandsautomat

Neue Zustände, hinten an `FlightState` angehängt (bestehende Nummern bleiben, wegen Zustandsspeicher und Telemetrie):
`ARMED = 9`, `COUNTDOWN = 10`, `IGNITION = 11`, `MISFIRE = 12`.

```
SAFE --PAD_READY--> PAD_READY --ARM (MAC ok, Vorbedingungen ok)--> ARMED
ARMED --LAUNCH (MAC ok)--> COUNTDOWN --nach LAUNCH_COUNTDOWN_S--> IGNITION
IGNITION --Schub erkannt--> BOOST (bestehender Flugablauf)
IGNITION --kein Schub nach LAUNCH_THRUST_TIMEOUT_MS--> MISFIRE (Pyro gesperrt, bleibt bis SAFE per Funk)
ARMED/COUNTDOWN --ABORT | Heartbeat fehlt > 1 s | Vorbedingung verletzt | ARM_TIMEOUT--> SAFE
```

**Vorbedingungen** für ARM (alle gleichzeitig, im ACK als Bitmaske):

1. Arming-Spannung VBAT_ARMED vorhanden (Hardware-Schalter ein).
2. Durchgang an Pyro 1.
3. 1S und 2S über ihrer Schwelle (`Config.h`).
4. Rakete ruhig (Gyro unter Schwelle für 2 s) und aufrecht innerhalb des Rampenwinkels (Kippung ≤ `LAUNCH_MAX_TILT_DEG`).
5. Sensoren ok, kalibriert, Logging läuft.
6. Servo-Selbsttest bestanden (kurzer Ausschlag beider TVC-Servos in PAD_READY, Rückkehr in die Mitte).
7. `LAUNCH_ENABLED` in der Firmware (Schlüssel vorhanden).

Diese Bedingungen werden in ARMED und COUNTDOWN laufend geprüft; fällt eine weg, geht es nach SAFE.

**Parameter** (neu in `Config.h`): `ARM_TIMEOUT_S = 30`, `LAUNCH_COUNTDOWN_S = 5`, `HEARTBEAT_TIMEOUT_MS = 1000`,
`LAUNCH_PULSE_MAX_MS = 300`, `LAUNCH_THRUST_TIMEOUT_MS = 2000`, `LAUNCH_MAX_TILT_DEG = 25`, `LAUNCH_CH = 0`.

**Anzeige an der Rakete:** ARMED: Summer im Sekundentakt, LED rot blinkend. COUNTDOWN: Summer schnell, letzte Sekunde
Dauerton. MISFIRE: Summer Dreiertakt bis SAFE.

**Zündpuls:** `PyroLogic` bekommt einen Startpuls-Modus für Kanal 1 mit den Abbruchgründen aus §2.1. Während des
Pulses wird VBAT_ARMED mit mindestens 1 kHz abgetastet (Mux fest auf Kanal 6), die Minimalspannung geht in den `IGN`-Rahmen.

**Aufzeichnung:** Ab ARMED schreibt der Logger mit voller Rate; ein Ringpuffer hält die letzten 2 s vor dem
Zündbefehl, damit der Countdown vollständig im Log steht.

## 5. Bodenstation: Funkbrücke auf Board 2 und Laptop-Werkzeug

**Funkbrücke (`firmware/`, neue PlatformIO-Umgebung `ground_bridge`):** läuft auf dem Teensy 4.1 des zweiten Mainboards.
- Transparent: Bytes von USB-Seriell nach `Serial8` (E22) und zurück, ohne die Rahmen zu verändern; dadurch braucht
  `launch.py` keinen eigenen Treiber.
- Setzt M0/M1 für den Normalbetrieb auf LOW, NRST hoch. Ein Konfigurationsmodus (z. B. Escape-Sequenz oder eigener
  USB-Befehl, Umsetzung frei) setzt M0/M1 auf Konfiguration und schreibt Kanal, Adresse und Luftrate passend zur Rakete
  (Werte aus `firmware/src/Config.h`, gemeinsamer Header). Liest RSSI aus, wenn das E22 es anhängt.
- Status über die WS2812 (grün: Funk empfängt, rot: kein Rahmen seit 2 s) und den Summer bei Verbindungsverlust.
- Keine Pyro-, Servo- oder Sensorfunktionen; Pyro-Pins bleiben LOW. Board 2 bekommt keinen Anzünder und keinen
  Arming-Schalter.
- Versorgung über USB (Teensy-VIN → 5V_SYS laut Schaltplan prüfen; falls nicht, 1S-Akku an J2).

**Laptop-Werkzeug `tools/ground/launch.py`:**

- Python 3, `pyserial`, keine weiteren Abhängigkeiten außer `hmac`/`hashlib` aus der Standardbibliothek.
- Öffnet den USB-Port der Funkbrücke, dekodiert TLM/EVT/ACK/IGN, zeigt Zustand, Akkus, Flags, Lage, RSSI; schreibt
  alles als CSV mit Zeitstempel.
- Befehle per Taste: PING, CALIBRATE, PAD_READY, SAFE, ABORT (Leertaste, jederzeit), ARM, LAUNCH.
- **LAUNCH nur mit Bestätigung:** Eingabe des Wortes `START`, danach sendet das Skript LAUNCH und hält den Heartbeat.
  Leertaste bricht ab.
- Zeigt bei verweigertem ARM die fehlenden Vorbedingungen im Klartext.
- `launch.py --config` löst den Konfigurationsmodus der Funkbrücke aus (Kanal, Adresse, Luftrate wie die Rakete).

## 6. Tests

**Nativ (`firmware/test/`, laufen in der CI):**
- MAC: richtige nonce → angenommen; falsche nonce, wiederholter Befehl, falscher Schlüssel → abgelehnt.
- Zustandsautomat: jeder Übergang aus §4, ARM-Zeitüberschreitung, Heartbeat-Verlust, Vorbedingung fällt im Countdown
  weg, ABORT in ARMED und COUNTDOWN, kein Schub → MISFIRE, MISFIRE bleibt bis SAFE.
- Startpuls endet bei Schub, bei Durchgangsverlust und spätestens nach 300 ms.
- Kein Pfad zündet Pyro 1 außerhalb von IGNITION (Negativtest über alle Zustände).

**Python:** Rahmen kodieren/dekodieren gegen feste Bytefolgen aus den nativen Tests (gleiche Testvektoren).

**Am Tisch (Hardware, nach Lieferung der Platine):**
1. Ersatzlast statt Anzünder (Glühlampe 12 V oder Leistungswiderstand), kompletter Ablauf ARM → LAUNCH → Puls.
2. Funk-Abbruch: USB-Kabel der Funkbrücke im Countdown abziehen → SAFE.
3. Anzünder ohne Motor (im Freien, Abstand): Durchbrennzeit, Spannungseinbruch, VSERVO, F1 löst nicht aus.
4. Erst dann mit Motor auf der Rampe.

## 7. Dokumentation, die mitgezogen wird

- `docs/Schnittstellen_Bodensystem_2026-10-22.md`: S2 (Zündleitung) entfällt, S3 um ARM/LAUNCH/HEARTBEAT/IGN.
- `groundstation/README.md`: Minimum = Laptop + Board 2 als Funkbrücke; ESP32-Station als möglicher späterer Ausbau.
- `docs/Bauanleitung_Kartonaut1.md`: Kabelweg Anzünder (§2), Startcheckliste (§6.1) mit Reihenfolge Hauptschalter →
  Anzünder → Arming-Schalter → Weggehen → PAD_READY → ARM → LAUNCH; Vorgehen bei MISFIRE (60 s warten, dann SAFE, erst
  dann hingehen, Arming-Schalter aus).
- `PROJECT.md` (Entscheidung, Befunde), beide READMEs.

## 8. Abnahme

- Native Tests grün, Python-Tests grün, CI grün.
- Ein Probelauf mit Ersatzlast am Tisch zeichnet im Log und im `IGN`-Rahmen alle Zeitmarken auf.
- Ohne `Secrets.h` baut die Firmware und verweigert ARM.
- Kein bestehender Test bricht; Zustandsnummern 0–8 unverändert.

## 9. Offen

- **Zweiter Teensy 4.1** für Board 2 (Funkbrücke) beschaffen, oder für Tischtests den einen Teensy umstecken.
- Antenne am ANT-Pad statt unten durch die Scheibe: Reichweite am Boden mit RSSI prüfen (Ziel: sicherer Empfang über
  300 m).

- Widerstand und Zündstrom der TSP-Anzünder (messen).
- F1 bei Ersatzlast: löst sie in 300 ms aus? Falls ja, Pulsgrenze weiter senken oder F1 für rev C überdenken.
- Kabelweg am Kardan im CAD.
- Ob die Rampe die Rakete beim Abheben sauber führt, wenn die Anzünderleitung von innen kommt (keine Leitung zwischen
  Rakete und Rampe).
