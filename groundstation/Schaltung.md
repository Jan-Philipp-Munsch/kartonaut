# Bodenstation – Schaltung und Verdrahtung

Stand 2026-10-22. Aufbau auf Lochrasterplatine, kein KiCad. Pins und Schwellen stehen auch in
`firmware/src/Config.h`; bei Abweichungen gilt die Firmware und diese Datei wird nachgezogen.
Schnittstelle zum Pad: S2 in `docs/Schnittstellen_Bodensystem_2026-10-22.md`.

## 1. Versorgung

```
3S-LiPo ──XT60──┬── F2 10 A ───────────────────────────────── K1 COM (Zündpfad, §3)
                │
                └── F1 2 A ── S1 Hauptschalter ──┬── U1 Buck 5 V ── ESP32-S3-DevKitC-1 "5V"
                                                  │                    └── 3V3 (DevKit-LDO) ── E22, Prüfquelle
                                                  ├── Teiler 100k/27k ── GPIO4 (Akkuspannung)
                                                  └── SK Schlüsselschalter ── S2 ARM ── K1 Spule (§3)
```

| Netz | Quelle | Verbraucher | Bemerkung |
|---|---|---|---|
| `VBAT` | 3S-LiPo 1300 mAh, 11,1 V (10,5 … 12,6 V) | F1, F2 | Akku bleibt im Gehäuse, Laden über das Balancerkabel |
| `VSW` | `VBAT` über F1 2 A und S1 | U1, Schlüsselschalter, Teiler GPIO4 | S1 trägt nur Elektronik und Relaisspule (< 300 mA) |
| `5V` | U1 (Pololu D24V10F5 oder MP1584-Modul) | DevKit-Pin `5V`, Summer | |
| `3V3` | LDO auf dem DevKit | ESP32-S3, E22 (110 mA Sendepuls), Prüfquelle R1, LEDs | DevKit-LDO liefert 500 mA |
| `VKEY` | `VSW` über Schlüsselschalter SK | ARM-Schalter S2, Teiler GPIO5 | Schlüssel nur in Stellung AUS abziehbar |
| `VARM` | `VKEY` über ARM-Schalter S2 | Relaisspule K1, Teiler GPIO6 | Kippschalter mit Schutzklappe |

Der Zündstrom läuft nie über Schalter: F2 → Relaiskontakt → Leitung → Anzünder → MOSFET → Masse.
Schlüssel und ARM schalten nur die Relaisspule (ca. 35 mA).

## 2. Pinbelegung ESP32-S3-DevKitC-1

ADC nur an GPIO 1 … 10 (ADC1), weil ADC2 bei aktivem WLAN nicht nutzbar ist. Nicht belegt:
Strapping-Pins 0, 3, 45, 46; USB 19/20; Flash/PSRAM 26 … 37; UART0 43/44 (Konsole).

| GPIO | Richtung | Signal | Beschaltung |
|---|---|---|---|
| 1 | ADC | `LINE_NEG` | Leitung minus über 22 k, 6,8 k nach GND, 100 nF am Pin |
| 2 | ADC | `LINE_POS` | Leitung plus über 22 k, 6,8 k nach GND, 100 nF am Pin |
| 4 | ADC | `VBAT_SENSE` | `VSW` über 100 k, 27 k nach GND, 100 nF (12,6 V → 2,68 V) |
| 5 | Eingang | `KEY_SENSE` | `VKEY` über 22 k, 7,5 k nach GND (12,6 V → 3,20 V; 10 V → 2,54 V) |
| 6 | Eingang | `ARM_SENSE` | `VARM` über 22 k, 7,5 k nach GND |
| 7 | Eingang | `START_BTN` | Taster gegen GND, interner Pull-up, 100 nF parallel |
| 9 | Ausgang | `FIRE_GATE` | 100 Ω zum Gate Q1, 100 k Gate–Source (hält Q1 aus, solange der ESP startet) |
| 10 | Ausgang | `BUZZER` | 1 k zur Basis Q2 (BC547), Summer 5 V aktiv zwischen `5V` und Kollektor |
| 11 | Ausgang | `LED_CONT` | grüne LED, 330 Ω (Durchgang) |
| 12 | Ausgang | `LED_ARMED` | rote LED, 330 Ω (scharf, blinkt im Countdown) |
| 13 | Ausgang | `LED_LINK` | blaue LED, 330 Ω (Telemetrie jünger als 1 s) |
| 14 | Eingang | `E22_AUX` | E22 AUX (hoch = bereit) |
| 15 | Ausgang | `E22_M0` | E22 M0 |
| 16 | Ausgang | `E22_M1` | E22 M1 |
| 17 | Ausgang (TX1) | `E22_RXD` | E22 RXD |
| 18 | Eingang (RX1) | `E22_TXD` | E22 TXD |

Spannungsteiler an GPIO 5/6: Die Schaltschwelle des ESP32-S3 liegt bei 0,75 · 3,3 V = 2,48 V. Mit
22 k / 7,5 k erkennt der Eingang „ein“ ab 9,7 V Akkuspannung, bei 12,6 V liegen 3,20 V am Pin.
Unter 10,5 V sperrt die Firmware den Countdown ohnehin (`VBAT_MIN_FIRE_V`).

## 3. Zündkreis mit Durchgangsprüfung

```
 VBAT ── F2 10 A ── K1 (COM→NO) ────────┬───────────────────── LINE+ ──┐
                                        │                              │
 3V3 ── R1 1k ── D2 BAT54 (A→K) ────────┤                         XT30-Buchse ── Zündleitung 15 m ── Pad ── Anzünder
                                        ├── 22k ─┬─ GPIO2              │
                                        │       6k8                    │
                                        │        GND                   │
                               D3 SS54 (K an LINE+, A an LINE−)        │
                                        │                              │
                                        ├───────────────────── LINE− ──┘
                                        ├── 22k ─┬─ GPIO1
                                        │       6k8
                                        │        GND
                                        ├── R2 2k2 (0,25 W) ── GND
                                        ├── D4 SMBJ15A ── GND
                                        └── Q1 IRLB8721 Drain;  Source ── GND;  Gate ── 100 Ω ── GPIO9, 100k ── GND

 VARM ── K1 Spule ── GND,  D1 1N4007 parallel zur Spule (Kathode an VARM)
```

**Zwei unabhängige Schalter in Reihe (S2):** K1 schließt nur, wenn Schlüssel und ARM eingeschaltet
sind; das erledigt die Verdrahtung, keine Software. Q1 schaltet nur der ESP32. Ein Fehler der Firmware
allein kann ohne ARM nicht zünden, ein klebendes Relais allein nicht ohne Q1.

### Dimensionierung

| Zustand | Weg | Strom durch den Anzünder | Leitung plus | Leitung minus |
|---|---|---|---|---|
| SICHER, Anzünder dran | 3V3 → R1 → D2 → Anzünder → R2 ∥ Teiler (2,04 k) → GND | (3,3 − 0,25) V / 3,04 kΩ ≈ **1,0 mA** | ≈ 2,0 V | ≈ 2,0 V → Durchgang |
| SICHER, Leitung offen | 3V3 → R1 → D2 → Teiler plus | 0 | ≈ 2,9 V | 0 V → kein Durchgang |
| SICHER, Q1 durchlegiert oder Leitung an Masse | 3V3 → R1 → D2 → Anzünder → Q1 | ≈ 3 mA | ≈ 0 V | ≈ 0 V → **Fehler**, nicht scharf schalten |
| SCHARF (K1 zu), Q1 aus | VBAT → Anzünder → R2 ∥ Teiler | 12,6 V / 2,04 kΩ = **6,2 mA** (≤ 10 mA nach S2) | VBAT | ≈ VBAT → Durchgang |
| SCHARF, Leitung offen | – | 0 | VBAT | 0 V → kein Durchgang |
| ZÜNDUNG (Q1 an) | VBAT → F2 → K1 → Anzünder → Q1 | 12,6 V / (1,5 Ω + 0,05 Ω) ≈ **8 A**, mit Akkueinbruch ≥ 6 A | VBAT − Abfall | ≈ 0,1 V |

- **R1 1 kΩ, D2 BAT54:** Prüfquelle aus 3,3 V. D2 sperrt, sobald K1 die Leitung auf Akkuspannung legt,
  damit kein Strom in die 3,3-V-Schiene zurückfließt (BAT54: 30 V Sperrspannung).
- **R2 2,2 kΩ:** zieht Leitung minus bei offenem Q1 nach Masse und macht die Durchgangsprüfung im
  scharfen Zustand möglich. 6,2 mA bei vollem Akku liegen unter der Grenze von S2 (10 mA) und weit
  unter dem Nichtzündstrom üblicher Anzünder (einige 100 mA). Verlustleistung 72 mW.
- **Teiler 22 k / 6,8 k:** 12,6 V → 2,97 V am ADC (Messbereich bei 11 dB Dämpfung bis ca. 3,1 V).
- **Q1 IRLB8721:** 30 V, R<sub>DS(on)</sub> 8,7 mΩ bei 4,5 V, Schwelle 1,35 … 2,35 V; bei 3,3 V Gate
  ca. 15 … 25 mΩ. 8 A · 8 A · 25 mΩ = 1,6 W für 1 s, TO-220 ohne Kühlkörper genügt.
  Vor dem ersten Einsatz mit 1,5-Ω-Lastwiderstand (≥ 100 W kurzzeitig, oder ein Stück Heizdraht)
  den Strom messen.
- **D3 SS54 und D4 SMBJ15A:** Freilauf für die Induktivität der 15-m-Leitung beim Abschalten und
  Überspannungsschutz am Drain.
- **F2 10 A flink (Flachsicherung):** 8 A für 1 s hält sie, einen Kurzschluss (Shunt-Stecker am Pad
  vergessen) trennt sie. F1 2 A schützt die Elektronik getrennt, damit die Station bei ausgelöster F2
  weiterläuft und den Fehler anzeigt.
- **K1:** 12-V-Relais, Schließer ≥ 10 A (Finder 40.31 oder Song Chuan 833H). Spule ca. 400 Ω,
  Anzug bei 75 % = 9 V; am 3S-Akku sicher.

### Was die Durchgangsprüfung nicht unterscheiden kann

- Anzünder (1,5 Ω) und Kurzschlussbrücke am Pad (0 Ω) sehen gleich aus. Die Brücke wird deshalb im
  Ablauf (README §4) als letzter Schritt am Pad gezogen, und erst danach wird der Durchgang an der
  Station bewertet.
- Einen hochohmigen Anzünder (Wackelkontakt, > ca. 2 kΩ) meldet die Prüfung als offen, einen mit
  10 … 100 Ω als in Ordnung. Für Ja/Nein am Startplatz reicht das.

## 4. Funkmodul

| E22-400T22D | ESP32-S3 / Netz | Bemerkung |
|---|---|---|
| M0 | GPIO15 | |
| M1 | GPIO16 | |
| RXD | GPIO17 (TX1) | 3,3-V-Pegel |
| TXD | GPIO18 (RX1) | |
| AUX | GPIO14 | |
| VCC | 3V3 | 100 µF + 100 nF direkt am Modul |
| GND | GND | |
| Antenne | SMA-Buchse am Modul → ½λ-Antenne 433 MHz, außen am Gehäuse | nie ohne Antenne senden |

Die Firmware liest beim Start die Register (Modus M0 = 0, M1 = 1) und schreibt sie nur, wenn sie von
`Config.h` abweichen (Kanal 0x17, Adresse 0x0000, 9600 Bd, Luftrate, Sendeleistung). Das Modul
der Rakete muss dieselben Werte haben.

## 5. Bedienfeld

| Teil | Funktion | Verdrahtung |
|---|---|---|
| S1 Hauptschalter (Wippe) | Elektronik ein | in `VSW` |
| SK Schlüsselschalter | Freigabe; Schlüssel trägt, wer zum Pad geht | `VSW` → `VKEY` |
| S2 ARM (Kippschalter mit Schutzklappe) | scharf schalten (zieht K1 an) | `VKEY` → `VARM` |
| S3 Start-Taster (22 mm, grün) | Countdown starten: 1 s halten, während des Countdowns gehalten lassen | GPIO7 gegen GND |
| LED grün | Durchgang | GPIO11 |
| LED rot | scharf (Dauerlicht), Countdown/Abbruch (blinkt) | GPIO12 |
| LED blau | Telemetrie aktuell | GPIO13 |
| Summer | Countdown-Takt, Erinnerung „scharf“ alle 2 s, Fehler | GPIO10 über Q2 |
| XT30-Buchse (Panelhalter) | Zündleitung | LINE+ / LINE− |
| SMA-Durchführung | Antenne | |
| USB-C (DevKit) über Durchführung | Flashen, serielle Konsole | |
