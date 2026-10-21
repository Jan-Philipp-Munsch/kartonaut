# Tor-1-Prüfung: Netzliste `kicad/circuit.py` gegen die Spezifikation rev B

Datum 21.10.2026. Geprüft wurde der Stand von Commit `04ce52d` (KiCad-Projekt aus Code). Methode:
Ein Skript liest die Pin-Namen jedes Symbols aus den KiCad-Bibliotheken (Standard und `kicad/lib/`),
stellt sie der Netzzuordnung in `circuit.py` gegenüber und vergleicht die Teensy-Belegung mit der
Tabelle in `README.md` §4. Die Pin-Belegungen der Chips wurden gegen die Datenblätter gehalten
(TPS63070 SLVSC58B, DRV8833, BMP390 DS002-07, E22-400T22S Herstellerseite); das TDK-Datenblatt des
ICM-42688-P war nicht erreichbar, dort bleibt ein Punkt offen.

## Ergebnis

**Teensy-Belegung:** alle 31 belegten Pins und die 11 freien Pins auf `J_EXP` stimmen mit §4 überein.
Einzige Abweichung ist Pin 8, in der Spezifikation frei, im KiCad-Projekt `MOT_FAULT` (nFAULT des
DRV8833 mit 10 k nach 3V3). Das ist sinnvoll und jetzt in §4 nachgetragen.

**Richtig verdrahtet (gegen Datenblatt geprüft):** INA219 (SOIC-Pinbelegung A1/A0/SDA/SCL/VS/GND/IN−/IN+,
Adresse 0x40, IN+ an VBAT_PROT), DRV8833 (AIN1 = BIN1 = MOT_IN1, AIN2 = BIN2 = MOT_IN2, Brücken
parallel, Pin 9 ist laut Datenblatt BIN1), TPS563201, AP2112K (EN an VIN), AO3401A als Verpolschutz
(Drain am Akku), AO3400A low-side, SS14 (Anode 5V_SYS, Kathode Teensy-VIN), 74AHCT1G125 (OE an GND),
WS2812B-2020 (DOUT/VSS/DIN/VDD), BMP390 (8 und 9 VSS, 10 VDD; SDO an VDDIO = 0x77, CSB an VDDIO wie
vom Datenblatt empfohlen), E22-400T22S (TXD Pin 23 an RX8, RXD Pin 22 an TX8, M0 20, M1 21, AUX 24,
VCC 25; M0/M1 haben schwache interne Pull-ups), Freilaufdiode am Summer, Schalter J_SW (1-2 = 1S,
3-4 = 2S), Teiler und Sense-Pins.

## Abweichungen und Befunde

| Nr. | Bauteil | Befund | Schwere | Vorschlag |
|---|---|---|---|---|
| 1 | U2 TPS63070 | Die Pins 8 (VOUT) und 13 (VIN) fehlen im LCSC-Symbol und in `circuit.py`; laut Datenblatt sind VIN = 12 + 13 und VOUT = 7 + 8. Der LCSC-Footprint fasst die Doppelpins aber zusammen: Er hat 13 Pads, die Pads 8 und 13 sind als zweites Pad mit den Nummern 7 bzw. 12 gezeichnet (plus Brückenpad). Elektrisch sind damit beide Pins angeschlossen. | keine, Doku | So lassen; in `build_lib.py` einen Kommentar setzen, damit beim Tausch des Footprints (z. B. KiCad-Standard-VQFN) die Pins 8/13 nachgezogen werden. |
| 2 | U2 TPS63070 | FB2 (Pin 6) liegt an GND. Das Datenblatt sagt: offen lassen, wenn VSEL nicht benutzt wird; FB2 ist ein Open-Drain-Ausgang, der bei VSEL = high nach GND zieht. Direkt an GND ist elektrisch harmlos, aber gegen die Vorgabe. | niedrig | Pin 6 auf NC setzen. |
| 3 | U2 TPS63070 | PS/SYNC (Pin 1) an VSYS_IN = Stromsparbetrieb (PFM) bei Teillast erlaubt. Bei 0,4 A Last läuft er meist in PWM; PFM bringt bei Leerlauf mehr Ripple auf 5V_SYS. | Entscheidung | So lassen oder für minimalen Ripple an GND (forced PWM, mehr Ruhestrom). Im Design Guide festhalten. |
| 4 | U4 ICM-42688-P | Das Datenblatt, das LCSC zur Nummer C1850418 verlinkt, trägt die Marke Tokmas (`www.tokmas.com`), nicht TDK InvenSense. | mittel | Vor der Bestellung im JLC-Teileprogramm den Hersteller prüfen; nur TDK InvenSense ICM-42688-P nehmen, sonst Breakout oder anderer Anbieter. |
| 5 | U4 ICM-42688-P | RESV-Pins 2, 3, 7, 10, 11 und FSYNC (9) liegen an GND. Das TDK-Datenblatt (DS-000347, Tabelle 9) war nicht erreichbar; die Zuordnung konnte nicht unabhängig bestätigt werden. | prüfen | Beim Review mit dem Datenblatt abgleichen; insbesondere, ob Pin 7 „do not connect“ oder GND ist. |
| 6 | Spezifikation | README §4 kannte Pin 8 nicht (jetzt `MOT_FAULT`) und sah einen Reset-Taster SW_RST vor, der im KiCad-Projekt begründet entfallen ist (Teensy hat am Sockel keinen Reset). | Doku | §4 und Stückliste der Spezifikation angepasst. |
| 7 | U10 E22-400T22S | Die Pads 9, 10, 17, 18 sind beim Hersteller nicht definiert; `circuit.py` lässt sie offen. NRST (Pin 1) offen; der Hersteller nennt keinen internen Pull-up. | niedrig | NRST über 10 k an 3V3_RF legen oder an einen Teensy-Pin (Reset des Funkmoduls aus der Firmware), beim Review entscheiden. |

Alle anderen Netze entsprechen der Spezifikation (§3 Versorgung, §4 Pins, §5 Pyro, §6 Sensorik und
Funk). Die im KiCad-Projekt getroffenen Entscheidungen (GND_PWR mit Sternpunkt NT1, SMBJ12CA,
220 Ω in den Servoleitungen, Unterspannungsschutz über den EN-Teiler des TPS63070, stehende Stecker an
den Stirnseiten) sind in `kicad/README.md` §4 begründet und werden hier übernommen.

## Skript

Das Prüfskript liegt nicht im Repo; es liest `circuit.py` und die Bibliotheken ein und druckt je
Bauteil `Pin / Name / Netz`. Es soll als `check_design.py` ins KiCad-Projekt wandern (dort in
`circuit.py` schon angekündigt), damit Tor 1 bei jeder Änderung wiederholbar ist.
