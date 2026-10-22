# Bodenstation – Startgerät und Telemetrie mit Handy-Anbindung

Stand 2026-10-22. Die Bodenstation zündet den Motor (TSP E12, elektrischer Anzünder) über eine
15-m-Leitung zum Pad, empfängt die Telemetrie der Rakete über LoRa (E22, 433 MHz) und stellt beides
über einen eigenen WLAN-Zugangspunkt im Browser des Handys dar. Verbindlich sind die Schnittstellen
S2 bis S4 in `docs/Schnittstellen_Bodensystem_2026-10-22.md`; Abweichungen stehen in §6.

| Datei | Inhalt |
|---|---|
| `README.md` | Konzept, Sicherheit, Ablauf, Stückliste, Gehäuse (diese Datei) |
| `Schaltung.md` | Pinbelegung ESP32-S3, Versorgung, Zündkreis mit Dimensionierung, Funkmodul, Bedienfeld |
| `firmware/` | PlatformIO-Projekt (Arduino, ESP32-S3), Weboberfläche in `firmware/src/index.html` |

## 1. Konzept

- **Ein Gerät, ein Akku.** ESP32-S3-DevKitC-1, E22-400T22D, Zündrelais, MOSFET und Bedienfeld in
  einem Koffer, versorgt aus einem 3S-LiPo, der auch den Zündstrom liefert.
- **Die Station entscheidet, das Handy zeigt an.** Startsperre und Zündung laufen im ESP32; das Handy
  ist eine Webseite ohne Sonderrechte. Scharf schalten geht nur mit Schlüssel und ARM-Schalter am Gerät.
- **Ohne Handy bedienbar.** Start-Taster, LEDs und Summer an der Station reichen für einen Start.
- **Ohne Internet, ohne App.** Die Seite ist in die Firmware eingebettet (eine HTML-Datei, kein CDN).

## 2. Blockschaltbild

```
                     ┌──────────────────────────── Bodenstation ─────────────────────────────┐
                     │                                                                        │
 Handy ◄──WLAN──────►│ ESP32-S3 ── WebSocket /ws (JSON, 10 Hz)                                │
 192.168.4.1         │   │  │  │                                                               │
                     │   │  │  └─UART1─ E22-400T22D ──SMA── ½λ-Antenne ◄──LoRa 433 MHz──────────┼──► Rakete (E22 an Serial8)
                     │   │  │                                                                  │
                     │   │  ├─ADC── Leitung +/−, Akku          Schlüssel ── ARM ── Relaisspule  │
                     │   │  ├─GPIO── Schlüssel-/ARM-Rückmeldung ◄──┘          │                 │
                     │   │  └─GPIO── Start-Taster, LEDs, Summer               ▼                 │
                     │   └──GPIO9── MOSFET ───────────┐       3S ── F2 ── Relaiskontakt ─┐      │
                     │                                │                                   │      │
                     │                       Leitung −┴─── XT30 ───────────── Leitung + ──┘      │
                     └─────────────────────────────────┼────────────────────────────────────────┘
                                                       └── Zündleitung 2 × 0,75 mm², 15 m ── Zündkasten Pad ── Anzünder
```

Zündpfad: **3S → F2 → Relais (Schlüssel + ARM, reine Hardware) → Anzünder → MOSFET (Firmware) → Masse.**
Schaltung im Einzelnen: `Schaltung.md`.

## 3. Sicherheitskonzept

### 3.1 Schalter und ihre Wirkung

| Element | Wirkt auf | Unabhängig von der Firmware? |
|---|---|---|
| Hauptschalter | Elektronik und Relaisspule | ja |
| Schlüsselschalter | Relaisspule; Schlüssel nur in AUS abziehbar | ja |
| ARM-Schalter mit Schutzklappe | Relaisspule | ja |
| Relais K1 | Zündpfad plus | ja (Spule hängt nur an Schlüssel und ARM) |
| MOSFET Q1 | Zündpfad minus | nein, GPIO9 mit 100-k-Pull-down |
| Sicherung F2 10 A | Zündpfad | ja |

Wer zum Pad geht, trägt den Schlüssel bei sich. Ohne Schlüssel ist das Relais offen, egal was die
Firmware oder ein Handy tut.

### 3.2 Zustände der Firmware (`firmware/src/Launch.cpp`)

| Zustand | Bedeutung | Verlassen |
|---|---|---|
| `LOCKOUT` | ARM war beim Einschalten an | ARM aus → `SAFE` |
| `SAFE` | Schlüssel oder ARM aus | ARM an → `ARMED` |
| `ARMED` | Relais zu, Countdown möglich, wenn die Startsperre frei ist | Countdown → `COUNTDOWN`; ARM aus → `SAFE` |
| `COUNTDOWN` | 10 s, jede Bedingung wird in jedem Durchlauf (1 ms) geprüft | T-0 → `FIRING`; Abbruch → `ABORTED` |
| `FIRING` | MOSFET 1,0 s an | → `FIRED` |
| `FIRED` | Zündung beendet; ohne gemeldetes Abheben 60 s Hänger-Wartezeit | ARM aus → `SAFE` |
| `ABORTED` | abgebrochen, Grund wird angezeigt | ARM aus → `SAFE` (bewusstes Entschärfen) |

Nach `ABORTED` und `FIRED` muss ARM einmal aus und wieder an, bevor ein neuer Countdown möglich ist.

### 3.3 Startsperre (S3)

Der Countdown startet nur, wenn alles erfüllt ist, und bricht ab, sobald während des Countdowns ein
Punkt wegfällt. Unmittelbar vor dem Einschalten des MOSFET wird noch einmal geprüft.

1. Schlüssel gedreht, ARM ein **und** Relais tatsächlich geschlossen (Spannung an Leitung plus).
2. Anzünder hat Durchgang (Leitung minus > 0,8 V, `Schaltung.md` §3).
3. Telemetrie jünger als 1 s, Flugzustand `PAD_READY`, Flag „Rakete scharf“ gesetzt.
4. Countdown läuft ohne Abbruch bis null.

Zusätzlich (nicht in S3, aber in der Firmware): kein Fehler im Zündkreis, Zündakku ≥ 10,5 V.

### 3.4 Countdown starten und abbrechen

| Quelle | Starten | Abbrechen |
|---|---|---|
| Start-Taster | 1 s halten. Bis T-0 gehalten lassen: loslassen = Abbruch (Totmann) | loslassen, ARM aus, Schlüssel ziehen |
| Handy | Knopf „Countdown starten“ 1,5 s halten; gesperrt, solange die Startsperre nicht frei ist | ABBRUCH-Knopf (wirkt beim Berühren), jederzeit, von jedem verbundenen Handy |
| Station selbst | – | jede Bedingung 1 … 3 fällt weg, Zündkreisfehler, Akku zu leer |

Verbindungsverlust (S4): Das Handy sendet alle 250 ms einen Herzschlag. Hat das Handy den Countdown
gestartet und fehlt der Herzschlag 1,5 s, oder meldet der WebSocket die Trennung, bricht die Station
ab. Der Herzschlag ist nötig, weil TCP einen WLAN-Abriss erst nach Sekunden bemerkt. Ein am Taster
gestarteter Countdown hängt nicht am Handy.

Bei jedem Abbruch schickt die Station `ABORT` an die Rakete (bis zu zehnmal, bis zur Quittung).

### 3.5 Fehlerfälle

| Fehler | Erkennung | Folge |
|---|---|---|
| MOSFET durchlegiert, Leitung minus an Masse | in `SAFE` mit angeschlossenem Anzünder: Leitung plus ≈ 0 V | Fehlermeldung, Summer, Countdown gesperrt. **Nicht scharf schalten**: das Relais würde sofort zünden. Ohne angeschlossenen Anzünder ist dieser Fehler nicht sichtbar, daher Prüfung im Ablauf (§4, Schritt 6). |
| Relais klebt / Fremdspannung | Leitung plus hoch ohne ARM | Fehler, Countdown gesperrt; Q1 trennt weiterhin |
| Relais zieht nicht an | ARM ein, Leitung plus niedrig | Fehler (Sicherung F2, Spule, Akku prüfen) |
| Anzünder fehlt oder Leitung offen | Leitung minus ≈ 0 V | Bedingung 2 fehlt |
| Kurzschluss auf der Leitung beim Zünden | – | F2 löst aus; Elektronik läuft an F1 weiter |
| Funkstrecke weg | Telemetrie älter als 1 s | Bedingung 3 fehlt, im Countdown Abbruch |
| Rakete verlässt `PAD_READY` oder wird entschärft | Telemetrie | Bedingung 3 fehlt, im Countdown Abbruch |
| WLAN/Handy weg | Herzschlag, WebSocket-Trennung | Abbruch, wenn das Handy den Countdown gestartet hat |
| ESP32 stürzt ab oder startet neu | – | Gate über 100 k auf Masse, MOSFET aus; Neustart mit ARM an → `LOCKOUT` |
| Fehlzündung (Hänger) | nach der Zündung kein `BOOST` in der Telemetrie | `FIRED` mit 60-s-Wartezeit in der Anzeige; erst danach ARM aus, Schlüssel ziehen, zum Pad |
| Zündakku leer | < 10,5 V | Countdown gesperrt; Warnung ab 11,1 V |
| Bedienfehler am Handy | – | kein Scharfschalten über das Handy, Start nur durch Halten |

## 4. Ablauf am Startplatz

Rollen: **Startleiter** an der Station (Handy, Station), **Pad-Person** baut auf und trägt den Schlüssel.
Die Station steht mindestens 10 m vom Pad (Zündleitung 15 m), Zuschauer hinter der Station.

1. Station aufstellen, Antenne senkrecht, Hauptschalter **aus**, ARM **aus**, Schlüssel abgezogen
   (bei der Pad-Person).
2. Handy: WLAN `MissionSpace-GS` wählen, „ohne Internet verbunden bleiben“ bestätigen, mobile Daten
   aus, `http://192.168.4.1` öffnen. Hauptschalter ein; die Seite zeigt **SICHER**.
3. Pad aufbauen und ausrichten (Libelle, < 1°). Rakete einsetzen, einschalten. Telemetrie erscheint
   (blaue LED). **Kalibrieren** am Handy, Rakete still stehen lassen, bis `PAD_READY` gemeldet wird.
4. Am Pad: Kurzschlussbrücke steckt im Zündkasten. Anzünder in den Motor, Krokoklemmen an den
   Zündkasten. Zündleitung an Pad und Station stecken.
5. Rakete am Schlüsselschalter scharf schalten; Telemetrie zeigt „Rakete scharf“.
6. Kurzschlussbrücke am Pad ziehen. Pad-Person geht zurück zur Station. Station zeigt **Durchgang**
   (grüne LED), kein Zündkreisfehler. Fehlt der Durchgang oder steht ein Fehler an: nicht scharf
   schalten, Hauptschalter aus, nachsehen.
7. Umfeld frei? Luftraum frei? Laut ansagen. Schlüssel stecken und drehen, Schutzklappe auf,
   **ARM ein** → **SCHARF**, Summer piept alle 2 s.
8. Startsperre am Handy vollständig grün → Countdown: am Handy „Countdown starten“ halten oder den
   Start-Taster 1 s drücken und bis T-0 halten. Abbruch jederzeit: ABBRUCH am Handy, Taster loslassen,
   ARM aus.
9. Nach dem Start: ARM aus, Schlüssel ziehen. Telemetrie bis zur Landung verfolgen.
   **Kein Abheben:** 60 s warten (Anzeige), dann ARM aus, Schlüssel ziehen, Leitung an der Station
   abziehen, erst dann zum Pad. Rakete über den Schlüsselschalter entschärfen, Anzünder tauschen.
10. Abbau: Hauptschalter aus, Zündakku auf Lagerspannung.

## 5. Firmware

PlatformIO-Projekt in `firmware/` (Arduino-Core 2.0.17 über `espressif32@6.9.0`, Board
`esp32-s3-devkitc-1`). Bibliotheken: ESPAsyncWebServer und AsyncTCP (ESP32Async), ArduinoJson 7.

```
cd groundstation/firmware
pio run                 # bauen
pio run -t upload       # flashen über USB
pio device monitor      # Konsole 115200 Bd
```

| Datei | Aufgabe |
|---|---|
| `Config.h` | alle Pins, Schwellen, Zeiten, WLAN, E22-Register |
| `Protocol.h/.cpp` | **Funkprotokoll, austauschbar** (Rahmen, CRC, Strukturen, Flugzustände) |
| `Radio.h/.cpp` | E22 konfigurieren, Empfang, Kommandos mit Quittung und Wiederholung |
| `Igniter.h/.cpp` | Schlüssel/ARM lesen, Leitungsspannungen, Durchgang, Fehler, MOSFET |
| `Launch.h/.cpp` | Zustandsautomat, Startsperre, Countdown, Abbruch |
| `Web.h/.cpp` | WLAN-Zugangspunkt, Webserver, WebSocket, JSON |
| `index.html` | Weboberfläche (eine Datei, wird in die Firmware eingebettet) |
| `main.cpp` | Schleife, LEDs, Summer |

**WebSocket `/ws`** (JSON):

| Richtung | Nachricht |
|---|---|
| Handy → Station | `{"cmd":"hb"}` alle 250 ms; `countdown`, `abort`, `calibrate`, `ping`, `pad_ready_query` |
| Station → Handy, 10 Hz | `{"t":"st","gs":{Stationszustand, Schlüssel, ARM, Relais, Durchgang, Spannungen, Fehler, Countdown},"lk":{Startsperre},"rf":{Funkzähler},"rk":{Telemetrie, GPS}}` |
| Station → Handy, bei Bedarf | `{"t":"ev","msg":"…"}` Ereignis (Zustandswechsel, Quittungen, Ablehnungen) |

Kommandos an die Rakete gehen nach dem nächsten empfangenen Telemetrierahmen hinaus (dann hört die
Rakete zu, der transparente E22-Modus kennt kein Kollisionsvermeiden), spätestens nach 150 ms, und
werden alle 300 ms wiederholt, bis die Quittung kommt (4×, `ABORT` 10×).

## 6. Abweichungen von S2–S4 und Abstimmung mit der Flug-Firmware

**Telemetrieprotokoll.** `spacecode/` hat am 22.10.2026 noch keine Definition (nur den HC-12-Beacon
`BEACON,<seq>,<millis>` in `examples/radio_beacon`, `main.cpp` nennt Serial8 „noch ohne Protokoll“).
`Protocol.h` setzt deshalb den Vorschlag aus S3 als Platzhalter um. Sobald die Flug-Firmware ihr
Protokoll hat, wird nur `Protocol.h/.cpp` ersetzt; am besten als gemeinsame Header-Datei, die beide
Projekte einbinden. Abzustimmen:

| Punkt | Vorschlag der Bodenstation |
|---|---|
| Rahmen | `A5 5A`, Typ, Länge, Nutzlast, CRC-16/CCITT-FALSE (0x1021, Start 0xFFFF) über Typ+Länge+Nutzlast, Little Endian |
| Typen | `0x01` Telemetrie (27 Byte), `0x02` GPS (12 Byte), `0x10` Kommando (cmd, seq), `0x11` Quittung (cmd, seq, Ergebnis) |
| Telemetrie | seq, Zustand, Flags, t_ms (u32), Höhe 0,1 m, v<sub>z</sub> cm/s, Quaternion 4 × i16/32767, Kardan Pitch/Yaw 0,01°, 1S/2S in mV |
| Flags | Bit 0 Rakete scharf (`VBAT_ARMED`), 1/2 Pyro-Durchgang 1/2, 3 GPS-Fix, 4 Log läuft, 5 kalibriert |
| Flugzustände | `BOOT, IDLE, CALIBRATING, PAD_READY, BOOST, COAST, APOGEE, DESCENT, LANDED, ABORT, FAULT` (0…10); der Automat in `spacecode/` legt sie fest |
| Quaternion | Achsenkonvention; die Oberfläche nimmt die Rumpfachse als z an (Neigungsanzeige) |
| `ABORT` | Bedeutung auf dem Pad (zurück nach `IDLE`, Pyros sperren) und im Flug (Fallschirm?) legt die Flug-Firmware fest. Die Station sendet es bei jedem Abbruch. |
| `PAD_READY` | muss während des Countdowns stehen bleiben; die Rakete darf ihn nicht für eine Nachkalibrierung verlassen, sonst bricht die Station ab |
| Sendefenster | Rakete hört nach jedem Telemetrierahmen ca. 100 ms zu (E22 halbduplex), Station sendet in diesem Fenster |
| Quittung | Rakete antwortet auf jedes Kommando mit `0x11`, auch auf Wiederholungen (gleiche seq) |

**Luftrate 9,6 statt 2,4 kbit/s (Abweichung von S3).** 10 Hz × 33 Byte (27 Nutzlast + 6 Rahmen)
= 2,64 kbit/s Nutzdaten, also mehr als die 2,4 kbit/s Luftrate, ohne LoRa-Präambel, GPS und
Kommandos. Mit 9,6 kbit/s ist der Kanal zu rund 30 % belegt. Die Reichweite sinkt gegenüber 2,4 kbit/s,
bleibt aber im Kilometerbereich, und der Erstflug am Fallschirm bleibt in wenigen hundert Metern.
Alternative ohne Änderung der Luftrate: Telemetrie 4 Hz. Die Werte stehen in `Config.h`
(`E22_AIR_RATE`) und müssen auf der Rakete gleich eingestellt sein.

**Sendeleistung und Zulassung.** 433,05 … 434,79 MHz ist in Deutschland ein SRD-Band: höchstens
10 mW ERP und ein Tastgrad von höchstens 10 % (ohne Amateurfunkgenehmigung). Die E22 senden bis
22 dBm (160 mW). Die Station ist auf 10 dBm eingestellt und sendet nur Kommandos. Auf der Rakete
sind Leistung und Tastgrad bei 10 Hz zu prüfen; 10 Hz Telemetrie überschreitet die 10 % auch bei
9,6 kbit/s. Lösungen: Amateurfunk (70-cm-Band, Rufzeichen), weniger Telemetrie (z. B. 2 Hz und
volle Rate nur im Flug) oder 868 MHz (E22-900T22, eigene Bandregeln). Jan entscheidet.

**E22-400T22D statt -T22S an der Station.** Gleiches Funkteil und gleiche Register, aber mit
Stiftleiste und SMA-Buchse statt Lötpads; passt auf Lochraster. Auf der Rakete bleibt das -T22S.

**XT30 an der Station.** S2 legt nur die Pad-Seite fest. Die Station hat ebenfalls eine XT30-Buchse
(spannungsführende Seite mit Buchsenkontakten); die Leitung trägt an beiden Enden einen XT30-Stecker.

## 7. Stückliste

Preise sind Richtwerte (Stand Okt. 2026, nicht einzeln geprüft), Bezugsquellen Beispiele.

| Pos. | Teil | Menge | Bezug | ca. € |
|---|---|---|---|---|
| 1 | ESP32-S3-DevKitC-1-N8R8 (Espressif) | 1 | BerryBase, Reichelt, Mouser | 15 |
| 2 | Ebyte E22-400T22D (SX1268, 433 MHz, SMA) | 1 | Ebyte-Shop AliExpress, Amazon | 12 |
| 3 | Antenne 433 MHz ½λ, SMA, ggf. SMA-Durchführung | 1 | AliExpress, Funk24 | 8 |
| 4 | 3S-LiPo 1300 mAh, ≥ 25 C, XT60 | 1 | Modellbauhandel | 20 |
| 5 | Buck 5 V, 1 A (Pololu D24V10F5 oder MP1584-Modul) | 1 | Eckstein, BerryBase | 2 … 8 |
| 6 | Relais 12 V, 1 Schließer 10 A (Finder 40.31.9.012 oder Song Chuan 833H-1C-C 12V) | 1 | Reichelt, Conrad | 3 |
| 7 | MOSFET IRLB8721PbF (TO-220) | 1 (+1 Reserve) | Reichelt, Mouser | 2 |
| 8 | Dioden: 1N4007, BAT54, SS54, TVS SMBJ15A | je 1 | Reichelt | 2 |
| 9 | Widerstände 1/4 W: 1k, 2k2, 3 × 22k, 2 × 6k8, 2 × 7k5, 100k ×2, 27k, 100 Ω, 3 × 330 Ω, 1k (Basis) | Satz | Reichelt | 3 |
| 10 | Kondensatoren: 6 × 100 nF, 100 µF/10 V | Satz | Reichelt | 2 |
| 11 | BC547, Summer 5 V aktiv | je 1 | Reichelt | 2 |
| 12 | Schlüsselschalter 2 Stellungen, Schlüssel nur in AUS abziehbar, ≥ 1 A | 1 | Reichelt, Conrad | 8 |
| 13 | Kippschalter 1-polig mit Schutzklappe (ARM) | 1 | Reichelt, AliExpress | 6 |
| 14 | Drucktaster 22 mm, Schließer (Start) | 1 | Reichelt | 5 |
| 15 | Wippschalter (Hauptschalter) | 1 | Reichelt | 2 |
| 16 | LEDs 5 mm grün/rot/blau mit Einbaufassung | je 1 | Reichelt | 3 |
| 17 | Flachsicherungshalter + Sicherungen 2 A und 10 A | 2 | Reichelt, Kfz-Bedarf | 5 |
| 18 | XT60-Buchse (Akku), XT30-Buchse mit Panelhalter (Zündleitung) | je 1 | Modellbauhandel, AliExpress | 4 |
| 19 | Zündleitung 2 × 0,75 mm², 15 m (H03VV-F oder Lautsprecherkabel), 2 × XT30-Stecker | 1 | Baumarkt | 15 |
| 20 | Lochrasterplatine 100 × 80, Stiftleisten, Litze, Schrumpfschlauch | Satz | Reichelt | 6 |
| 21 | Gehäuse (§8) | 1 | Reichelt, Baumarkt | 20 |
| | **Summe** | | | **ca. 150** |

Für den Abgleich: ein 1,5-Ω-Lastwiderstand (≥ 50 W, kurzzeitig) oder ein Stück Heizdraht als
Anzünder-Ersatz, und ein Multimeter mit 10-A-Bereich.

## 8. Gehäuse

- Kunststoffkoffer oder ABS-Gehäuse ca. 200 × 150 × 90 mm (z. B. Hammond 1554, Fibox, Spelsberg),
  spritzwassergeschützt, Deckel als Bedienfeld oder Bedienfeld schräg auf der Oberseite.
- Bedienfeld von links nach rechts in der Reihenfolge des Ablaufs: Hauptschalter – Schlüssel – ARM
  (Schutzklappe) – Start-Taster; LEDs darüber. Der Start-Taster liegt so, dass er mit dem ARM-Schalter
  nicht in einem Griff erreichbar ist.
- XT30-Buchse und SMA-Durchführung an der Seite, Antenne senkrecht. USB-C des DevKit über eine
  Durchführung oder einen Deckel zugänglich.
- Akku in einem Fach mit Klett, Balancerkabel zugänglich zum Laden ohne Ausbau; F1/F2 von außen
  oder hinter einer Klappe zugänglich.
- Abstand der 433-MHz-Antenne zum ESP32 (WLAN 2,4 GHz) und zur Zündleitung > 10 cm.

## 9. Offen

- Protokoll mit der Flug-Firmware festlegen (§6), danach `Protocol.h/.cpp` ersetzen.
- Luftrate, Telemetrierate, Sendeleistung und Tastgrad entscheiden (§6).
- Zündkreis mit Lastwiderstand abgleichen: Strom ≥ 5 A für 1 s, Leckstrom scharf ≤ 10 mA messen,
  Durchgangsschwellen mit echtem Anzünder und 15-m-Leitung prüfen.
- E22-Registerbelegung gegen das Datenblatt der gelieferten Modulversion prüfen (`Radio.cpp`).
- Firmware-Test ohne Rakete: ein zweites E22 an einem USB-UART mit einem Skript, das Telemetrie
  (`PAD_READY`, scharf) sendet und Kommandos quittiert.
