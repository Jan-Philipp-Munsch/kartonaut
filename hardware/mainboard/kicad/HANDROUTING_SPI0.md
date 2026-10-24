# Handrouten der sieben SPI0-Lücken (Mainboard rev B1, 23.10.2026)

> **Erledigt 24.10.2026** in einer eigenen Sitzung (Opus 5.5): alle sieben geschlossen, DRC 0 Fehler, 0 offen,
> Prüfskript ohne Befund. Die Wege (Längen, Vias, B.Cu-Stücke) stehen in `README.md` §5.5. Die Regel „B.Cu nur
> Versorgung“ unten gilt seitdem mit der Ausnahme kurzer Signalstücke (Freigabe Jan, 24.10.).

Briefing für eine eigene Sitzung. Stand: `mainboard.kicad_pcb` im Worktree
`C:\Users\Janmu\Gitlab\mission_space\.claude\worktrees\rev-b1\hardware\mainboard\kicad`, Branch `claude/rev-b1`.
Die Platinendatei ist die Quelle: **niemals `./make.sh pcb` oder `gen_pcb.py place`** laufen lassen.
`./make.sh drc`, `gaps.py`, `review_check_layout.py` bleiben nutzbar. Regeln und Router-Einstellungen: `HANDROUTING.md` §1 und §2,
Klick-Anleitung `HANDROUTING_KLICKS.md`.

## Warum

Entscheidung E11 (23.10.): J_STACK (J15) Pin 7/8/9 an SPI0 (Teensy 13/11/12) statt SPI1, damit ein Fehler auf der
Zusatzplatine den Flugbus SPI1 nicht stören kann. Dafür verlegt: MOT_NSLEEP → Pin 40, PYRO3_FIRE → Pin 41,
PWM_EXT → Pin 33, LORA_M0 → Pin 16. Schaltplan, `circuit.py`, `check_design.py` und Doku sind fertig; auf der
Platine ist das alte Kupfer der vier Netze und die SPI1-Äste zu J15 Pin 7–9 entfernt, die Pad-Netze stimmen.
Vier automatische Versuche (Gitter-Router mit Rip-up, Freerouting fest, Freerouting über die aufgerissene Region,
Freerouting mit beweglicher Region) haben keine der sieben Verbindungen geschlossen.

## Die sieben Lücken (KiCad-Koordinaten mm)

A1 = Teensy 4.1, J15 = J_STACK 2×10, U7 = DRV8833, U10 = LoRa E22, R38 = Gate-Widerstand Pyro 3.

| # | Netz | Von | Nach | Luftlinie |
|---|---|---|---|---|
| 1 | SPI0_MOSI | A1-13 (119,38 / 110,77, linke Reihe) | J15-8 (140,74 / 95,22) | 26 mm |
| 2 | SPI0_MISO | A1-14 (119,38 / 113,31, linke Reihe) | J15-9 (138,20 / 97,76) | 24 mm |
| 3 | SPI0_SCK | A1-38 (134,62 / 113,31, rechte Reihe) | J15-7 (138,20 / 95,22) | 18 mm |
| 4 | LORA_M0 | U10-20 (101,40 / 112,20, SMD am Modulrand) | A1-35 (134,62 / 105,69, rechte Reihe) | 34 mm |
| 5 | PYRO3_FIRE | R38-1 (128,91 / 69,58, SMD an der Spitze) | A1-40 (134,62 / 118,39) | 49 mm |
| 6 | MOT_NSLEEP | A1-41 (134,62 / 120,93) | U7-1 (140,64 / 113,22, SMD 0,65-mm-Raster) | 10 mm |
| 7 | PWM_EXT | A1-48 (134,62 / 138,71) | J15-18 (140,74 / 107,92) | 31 mm |

Die Teensy-Pads sind durchkontaktiert (1,7 mm), erreichbar auf F.Cu und In2. Engpass: 1 und 2 müssen von der linken
Reihe quer unter dem Teensy zum J_STACK rechts, vorbei an der IMU U4 (x 127,0 / y 109,5) und dem SPI1-Bus; der Kanal
innen an der rechten Pin-Reihe (x 131–134) ist dicht belegt. Oberhalb (y < 100) oder unterhalb (y > 115) der IMU-Zone
über In2 ist der wahrscheinliche Weg. Fremde Bahnen mit dem Schiebe-Router beiseitedrücken; wenn das nicht reicht,
einzelne Signalbahnen (nicht Versorgung) umlegen oder kleine Bauteile um 0,5–1 mm versetzen und ihre Bahnen mit D
nachziehen. `out/mainboard_before_spi0.kicad_pcb` zeigt, wie die alten Routen liefen (LORA_M0 A1-48 → U10-20,
PWM_EXT A1-38 → J15-18, MOT_NSLEEP A1-13 → U7-1, PYRO3_FIRE A1-14 → R38-1); Teile davon taugen als Vorbild.

## Regeln, die der DRC nicht alle prüft

- Klasse Strom (VSERVO, VBAT2_*, VBAT_PROT, VBAT_ARMED, PYRO*_NEG) nur auf F.Cu: kein Via, keine In2-Bahn (A6).
- Um die IMU U4 im Radius 5 mm keine fremden Vias und keine In2-Bahnen (B16); nur die eigenen GND-Vias der IMU.
- Unter dem LoRa-Modul U10 Sperrflächen auf F.Cu und In2, außen herum routen.
- GND immer per Via auf In1. Auf B.Cu keine Signalbahnen (Versorgungsflächen GND_PWR, 5V_SYS).
- Abstände 0,15 mm Standard, 0,2 mm zu den Stromklassen; Signale 0,2 mm (0,15 an engen Pins), Via 0,6/0,3.
- Die F.Cu-Kupferflächen der Strompfade (Zonen „… Strompfad“) nicht zerschneiden.

## Werkzeuge und Prüfen

- KiCad 10: `%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad.exe`, Projekt `mainboard.kicad_pro` **im Worktree** öffnen
  (nicht im Hauptcheckout `C:\Users\Janmu\Gitlab\mission_space\hardware\mainboard\kicad`, dort liegen Lock-Dateien).
- Vor dem Start: `cp mainboard.kicad_pcb out/mainboard_before_hand_spi0.kicad_pcb`.
- Prüfen (Git Bash im Ordner `kicad/`): `./make.sh drc`;
  `"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" gaps.py` listet die offenen Verbindungen mit Koordinaten;
  `"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" review_check_layout.py` prüft A6/B16/A5.
- Bekannt und zu ignorieren: drei Paritäts-Hinweise zu U4 Pad 9/10/11 (GND statt unconnected; der IMU-Tausch auf
  LSM6DSV16X wird in der Hauptsitzung auf die Platine gebracht) und die Silk-Meldungen (14× silk_over_copper,
  2× silk_overlap, 1× silk_edge_clearance; Bestückungsdruck wird mit `gen_pcb.py silk` neu erzeugt).
  1× hole_to_hole und dangling-Meldungen prüfen; Reststummel des entfernten Kupfers löschen.

## Fertig heißt

`./make.sh drc` meldet 0 Fehler und 0 offene Verbindungen (nur die drei U4-Hinweise bleiben), `review_check_layout.py`
ohne Befund, `mainboard.kicad_pcb` gespeichert, KiCad geschlossen (keine Lock-Datei). Nichts committen, keine anderen
Dateien ändern (im Worktree liegen uncommittete Doku-Änderungen der Hauptsitzung). Zum Schluss kurz berichten: Wege
der sieben Verbindungen (Lagen, Vias), was verschoben wurde, DRC-Ergebnis.
