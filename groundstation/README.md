# Bodenstation – Startgerät und Telemetrie mit Handy-Anbindung

Stand 2026-10-22. Die Bodenstation zündet den Motor (TSP E12, elektrischer Anzünder) über eine
15-m-Leitung zum Pad, empfängt die Telemetrie der Rakete über LoRa (E22, 433 MHz) und stellt beides
über einen eigenen WLAN-Zugangspunkt im Browser des Handys dar. Verbindlich sind die Schnittstellen
S2 bis S4 in `docs/Schnittstellen_Bodensystem_2026-10-22.md`; Abweichungen stehen in §6.

> **Stand 27.10.2026: für *Kartonaut 1* nicht mehr gebraucht.** Jan hat entschieden, dass die Rakete ihren
> Motor selbst über Pyro 1 zündet (`docs/Plan_Bordzuendung_2026-10-27.md`). Das Minimum am Startplatz ist
> **Laptop + USB-Funkmodul E22-400T22U** mit `tools/ground/launch.py` (Telemetrie, ARM, LAUNCH mit MAC,
> Heartbeat, ABORT mit der Leertaste) und `tools/ground/e22_config.py`. Zündbox, 15-m-Zündleitung und diese
> ESP32-Station entfallen; sie bleiben als möglicher späterer Ausbau (z. B. Handy-Anzeige, Landeversuche mit
> Bodenzündung). Die Station-Firmware kennt die neuen Kommandos ARM/LAUNCH/HEARTBEAT, den längeren ACK auf
> PING und den IGN-Rahmen noch nicht und müsste vor einem Einsatz an `firmware/src/Telemetry.h` angepasst
> werden.

| Datei | Inhalt |
|---|---|
| `README.md` | Konzept, Sicherheit, Ablauf, Stückliste, Gehäuse (diese Datei) |
| `Schaltung.md` | Pinbelegung ESP32-S3, Versorgung, Zündkreis mit Dimensionierung, Funkmodul, Bedienfeld |
| `firmware/` | PlatformIO-Projekt (Arduino, ESP32-S3), Weboberfläche in `firmware/src/index.html` |

## 1. Konzept

- **Ein Gerät, ein Akku.** ESP32-S3-DevKitC-1, E22-400T22D, Zündrelais, MOSFET und Bedienfeld in
  einem Gehäuse (Sparvariante ca. 80 €, ein Abend Bauzeit, §7), versorgt aus einem 3S-LiPo, der auch den Zündstrom liefert.
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

**Telemetrieprotokoll.** Die Flug-Firmware (`firmware/`) hat am 22.10.2026 noch keine Definition (nur den HC-12-Beacon
`BEACON,<seq>,<millis>` in `examples/radio_beacon`, `main.cpp` nennt Serial8 „noch ohne Protokoll“).
`Protocol.h` setzt deshalb den Vorschlag aus S3 als Platzhalter um. Sobald die Flug-Firmware ihr
Protokoll hat (Plan 22.10. §2 B4), wird nur `Protocol.h/.cpp` ersetzt; am besten als gemeinsame Header-Datei, die beide
Projekte einbinden. Abzustimmen:

| Punkt | Vorschlag der Bodenstation |
|---|---|
| Rahmen | `A5 5A`, Typ, Länge, Nutzlast, CRC-16/CCITT-FALSE (0x1021, Start 0xFFFF) über Typ+Länge+Nutzlast, Little Endian |
| Typen | `0x01` Telemetrie (27 Byte), `0x02` GPS (12 Byte), `0x10` Kommando (cmd, seq), `0x11` Quittung (cmd, seq, Ergebnis) |
| Telemetrie | seq, Zustand, Flags, t_ms (u32), Höhe 0,1 m, v<sub>z</sub> cm/s, Quaternion 4 × i16/32767, Kardan Pitch/Yaw 0,01°, 1S/2S in mV |
| Flags | Bit 0 Rakete scharf (`VBAT_ARMED`), 1/2 Pyro-Durchgang 1/2, 3 GPS-Fix, 4 Log läuft, 5 kalibriert |
| Flugzustände | `BOOT, IDLE, CALIBRATING, PAD_READY, BOOST, COAST, APOGEE, DESCENT, LANDED, ABORT, FAULT` (0…10); der Automat in `firmware/` legt sie fest |
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

**Entscheidung 26.10.2026 (Jan):** Für den Erstflug läuft das absolute Minimum, die Station hier ist der spätere
Ausbau. Minimum = E22-400T22U (USB) am Laptop für Telemetrie und Kommandos plus verdrahtete Zündbox mit Schlüssel;
siehe `hardware/mainboard/Beschaffung_2026-10-26.md` §6c.

Preise sind Richtwerte (Stand Okt. 2026, nicht einzeln geprüft), keine Angebote. Zwei Varianten mit
**derselben Schaltung** (`Schaltung.md`) und derselben Firmware; sie unterscheiden sich nur in der
Bauform von Relais, MOSFET und Mikrocontroller-Träger.

**Schon anderswo eingeplant, hier nicht mitgezählt:** E22-400T22D und 433-MHz-Antenne kommen aus der
Vorab-Bestellung (`hardware/mainboard/ORDER.md` 0.3 und 0.4, je zwei Stück, eins für die Station),
Summer aus ORDER 0.16 (zweites Stück), Crimpzange aus ORDER 0.12. Der 3S-Akku lädt am vorhandenen
HTRC H4AC (2 … 4S, `docs/BUILD.md` §1.5).

### 7.1 Sparvariante (empfohlen): Module mit Schraubklemmen und Flachsteckern

Gelötet wird nur eine kleine **Messplatine** (Lochraster ca. 40 × 60 mm) mit den Bauteilen der
Durchgangsprüfung und den Teilern. Relais, MOSFET und Mikrocontroller sind fertige Module, die mit
Schraubklemmen und Kfz-Flachsteckern verdrahtet werden.

| Pos. | Teil | Menge | Bezug | ca. € |
|---|---|---|---|---|
| 1 | ESP32-S3-DevKitC-1 N16R8, Nachbau | 1 | AliExpress, Amazon | 7 |
| 2 | Schraubklemmen-Adapter für ESP32-S3-DevKitC (GPIO-Breakout) | 1 | AliExpress, Amazon | 5 |
| 3 | Buck 5 V: MP1584- oder LM2596-Modul | 1 | AliExpress, Eckstein | 1 … 2 |
| 4 | 3S-LiPo 1000 mAh, ≥ 20 C, XT60 | 1 | Modellbauhandel | 13 |
| 5 | Kfz-Relais 12 V, 30 A, Schließer, mit Freilaufdiode, plus Relaissockel mit Kabeln | 1 | Kfz-Bedarf, Reichelt, Amazon | 5 |
| 6 | MOSFET-Modul „D4184“ (2 × AOD4184A, 40 V, ab 3,3 V Logik), Schraubklemmen | 1 (+1 Reserve) | AliExpress, Amazon | 2 |
| 7 | Messplatine: Lochraster, R 1k, 2k2 (0,25 W), 3 × 22k, 2 × 6k8, 2 × 7k5, 100k, 27k, 3 × 330 Ω, 1k, BAT54 oder 1N5819, SS54, SMBJ15A, BC547, 6 × 100 nF, 100 µF | Satz | Reichelt | 5 |
| 8 | Schlüsselschalter, Schlüssel nur in AUS abziehbar | 1 | AliExpress, Reichelt | 3 |
| 9 | Kippschalter mit Schutzklappe (ARM), Start-Taster 16 … 22 mm, Wippschalter | je 1 | AliExpress, Reichelt | 5 |
| 10 | LED-Fassungen 5 mm mit LED grün/rot/blau | 3 | AliExpress, Reichelt | 2 |
| 11 | Flachsicherungshalter fliegend 2 ×, Sicherungen 2 A und 10 A | Satz | Kfz-Bedarf | 3 |
| 12 | XT60-Buchse (Akku), XT30-Buchse und 2 XT30-Stecker (Zündleitung) | Satz | Modellbauhandel | 4 |
| 13 | Zündleitung 2 × 0,75 mm², 15 m (Lautsprecherkabel) | 1 | Baumarkt | 9 |
| 14 | Gehäuse: Abzweigdose IP65 ca. 190 × 140 × 70, Deckel als Bedienfeld | 1 | Baumarkt | 8 |
| 15 | Kfz-Flachstecker 6,3 mm, Aderendhülsen, Litze 1,5 mm² und 0,25 mm² | Satz | Baumarkt, Reichelt | 5 |
| | **Summe** | | | **ca. 80** |

**Bauaufwand:** etwa ein Abend. Messplatine löten (ca. 30 min, 25 Lötstellen), Deckel bohren
(Schalter, Taster, LEDs, XT30, SMA), Module mit Klebepads oder Schrauben in die Dose, verdrahten
(Schraubklemmen, Flachstecker), Firmware über USB flashen, mit Lastwiderstand prüfen (§9).

Hinweise zu den Modulen:
- **D4184-Modul:** Ausgang `OUT−` ist der Drain, `VIN−` die Masse; `OUT+` bleibt frei. Ob das Modul
  einen Pull-down am Gate hat, am Modul messen; sonst 100 k zwischen Gate-Eingang und Masse ergänzen.
  Der AOD4184A hat bei 4,5 V Gate etwa 10 mΩ, bei 3,3 V mehr; die Strommessung in §9 zeigt, ob 3,3 V reichen.
- **Kfz-Relais:** Spule ca. 80 … 100 mA, Anzug ab ca. 7 V; Schlüssel- und ARM-Schalter müssen
  ≥ 0,5 A schalten können. Ein Typ mit eingebauter Diode ersetzt D1.
- **ESP32-S3-Nachbau:** auf GPIO 1 … 18 und den USB-Anschluss achten (manche Nachbauten führen
  GPIO 19/20 statt USB-UART heraus); die Pinbelegung bleibt wie in `Schaltung.md` §2.

### 7.2 Lochraster-Variante (Referenz)

Alles auf einer Lochrasterplatine 100 × 80 mit Original-DevKit, Printrelais und TO-220-MOSFET wie in
`Schaltung.md` §3. Robuster und kompakter, aber zwei bis drei Abende Lötarbeit.

| Pos. | Teil | Menge | Bezug | ca. € |
|---|---|---|---|---|
| 1 | ESP32-S3-DevKitC-1-N8R8 (Espressif) | 1 | BerryBase, Reichelt, Mouser | 15 |
| 2 | Buck 5 V, 1 A (Pololu D24V10F5) | 1 | Eckstein, BerryBase | 8 |
| 3 | 3S-LiPo 1300 mAh, ≥ 25 C, XT60 | 1 | Modellbauhandel | 20 |
| 4 | Relais 12 V, 10 A (Finder 40.31.9.012) | 1 | Reichelt | 4 |
| 5 | IRLB8721PbF, Dioden, Widerstände, Kondensatoren, BC547 | Satz | Reichelt | 8 |
| 6 | Schlüsselschalter, ARM mit Schutzklappe, Taster 22 mm, Wippschalter, LEDs (Reichelt) | Satz | Reichelt | 24 |
| 7 | Sicherungshalter, XT60, XT30 mit Panelhalter, Zündleitung 15 m | Satz | Reichelt, Baumarkt | 22 |
| 8 | Lochraster 100 × 80, Stiftleisten, Litze | Satz | Reichelt | 6 |
| 9 | Gehäuse Hammond 1554 oder Fibox | 1 | Reichelt | 20 |
| | **Summe** (ohne E22 und Antenne, die aus ORDER kommen) | | | **ca. 130** |

### 7.3 Was die Sparvariante spart

| | Lochraster | Sparvariante | Ersparnis |
|---|---|---|---|
| Kosten | ca. 130 € | ca. 80 € | ca. 50 € |
| Lötstellen | ca. 150 | ca. 25 | |
| Bauzeit | 2 … 3 Abende | 1 Abend | |
| Schaltung, Firmware, Sicherheit | gleich | gleich | |

Weiter drücken lässt sich der Preis kaum ohne Abstriche an der Sicherheit: Schlüssel, ARM, Relais,
zwei Sicherungen und die Durchgangsprüfung bleiben. Verzichtbar wären LEDs und Summer (das Handy zeigt
alles an), dann geht der Start ohne Handy aber nur noch blind; das spart 3 €. Eine eigene Trägerplatine
im JLC-Auftrag des Mainboards (ESP32-S3-Modul und E22-400T22S bestückt) würde den Bauaufwand weiter
senken, kostet aber Entwurfs- und Prüfzeit und hängt am Zeitplan der Hauptplatine; erst sinnvoll für
eine zweite Version der Station.

## 8. Gehäuse

- **Sparvariante:** Abzweigdose IP65 aus dem Baumarkt (ca. 190 × 140 × 70), der Deckel ist das
  Bedienfeld. Alternativ eine Kunststoff-Werkzeugbox mit gedruckter Frontplatte (PETG).
- **Lochraster-Variante:** Kunststoffkoffer oder ABS-Gehäuse ca. 200 × 150 × 90 mm (z. B. Hammond 1554,
  Fibox, Spelsberg), spritzwassergeschützt.
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
