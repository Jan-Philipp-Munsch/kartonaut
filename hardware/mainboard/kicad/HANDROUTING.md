# Handrouting der letzten 21 Verbindungen (Mainboard rev B1)

Stand 23.10.2026, Platine `mainboard.kicad_pcb` auf `claude/rev-b1` (Commit `a7fc5f4`): 0 DRC-Fehler,
21 offene Verbindungen. Ab hier ist die Platinendatei die Quelle. **`./make.sh pcb` nicht mehr laufen
lassen**, es würde die Handarbeit überschreiben. `./make.sh sch`, `./make.sh drc`, `./make.sh img` und
`gen_pcb.py silk` bleiben nutzbar. Zurück auf diesen Stand: `git checkout -- hardware/mainboard/kicad/mainboard.kicad_pcb`.

## 1. Vorbereitung (5 Minuten)

1. KiCad 10 starten (`%LOCALAPPDATA%\Programs\KiCad\10.0\bin\kicad.exe`), Projekt
   `.claude\worktrees\rev-b1\hardware\mainboard\kicad\mainboard.kicad_pro` öffnen, Leiterplatteneditor.
2. **Inspektion → DRC** ausführen (ohne „Zonen vorher auffüllen“ abzuwählen). Reiter „Nicht verbundene
   Elemente“: 21 Zeilen, ein Doppelklick springt zur Stelle und markiert beide Enden. Dialog offen lassen,
   nach jeder Stelle „DRC ausführen“ erneut.
3. **Route → Einstellungen interaktiver Router**: Modus **Schieben**, „Verletzungen hervorheben“ an,
   „Umschalten auf Schieben beim Ziehen“ an. Das ist das Werkzeug, das den dichten Stellen fehlt: es
   drückt fremde Bahnen beiseite statt sie aufzureißen.
4. Oben in der Werkzeugleiste Bahnbreite und Via auf **„Breite aus Netzklasse“** stellen. Die Klassen sind
   im Projekt hinterlegt (Strom 1,0 mm, Versorgung 0,6, Rückstrom 0,8, Wandler 0,4, Standard 0,2; Via 0,6/0,3).
   An engen Pins mit **W** auf die nächste Breite der Liste schalten (angelegt: 0,2 / 0,3 / 0,6 / 1,2 / 2,0);
   für die Stromklasse an 0603-Pads 0,6 nehmen, auf freier Fläche 1,0 aus der Klasse oder 1,2.
5. Raster 0,05 mm, Lagen-Umschaltung mit **Bild hoch / Bild runter**, Via setzen mit **V** während des
   Routens, Routen mit **X**, Abbrechen mit **Esc**, Rückgängig mit **Strg+Z**, Bauteil bewegen mit **M**,
   Bahn ziehen mit **D**.

## 2. Regeln, die der DRC nicht alle prüft

- **Klasse Strom nur auf F.Cu** (VSERVO, VBAT2_*, VBAT_PROT, VBAT_ARMED, PYRO*_NEG): kein Via, keine
  In2-Bahn (Review A6). Das Prüfskript meldet Verstöße.
- **5 mm um die IMU U4** (x 127,0 / y 109,5): keine fremden Vias, keine In2-Bahnen (B16). Nur die
  fünf GND-Vias der IMU dürfen dort sein. Die Sperrfläche „IMU ruhige Masse“ hält In2 frei, Vias
  im 2,6-mm-Kreis sind verboten; den Ring 2,6 bis 5 mm musst du selbst frei lassen.
- **LoRa-Modul U10:** Sperrfläche auf F.Cu und In2 unter dem Modul, Bahnen außen herum.
- **Flächen auf B.Cu:** GND_PWR unter allem am 2S (TVC-Ende, Mitte, rechter Streifen, Spitze) und 5V_SYS
  auf der 1S-Seite (linker Streifen, unter dem Teensy). Ein GND_PWR- oder 5V_SYS-Via nur dort, wo die
  eigene Fläche liegt; B.Cu einblenden und nachsehen.
- **GND** immer per Via auf In1 (durchgehende Fläche); die F.Cu-Füllung ist nur Beiwerk.
- **Sense-Netze** ISENS_P/ISENS_N nur zwischen Shunt-Pads, Filter und INA239 (A5); nichts anhängen.
- Abstände: 0,15 mm Standard, 0,2 mm zu den Stromklassen; Randabstand 0,2 mm. Der DRC prüft das.

## 3. Reihenfolge

Erst die Flächenpunkte (einfach), dann Shunt-Bereich, dann J_STACK, zuletzt DRV8833. Nach jeder Gruppe DRC.
Wenn an einer Stelle auch Schieben nichts bringt: das nächste kleine Bauteil (C36, C37, C38, R26 am DRV8833
liegen nur notdürftig außerhalb ihrer Region, JP2 ebenso) mit **M** um 0,5 bis 1 mm versetzen, seine Bahnen
mit **D** nachziehen, dann erneut. Freerouting und die Skripte konnten das nicht; der Editor schon.

| Art | Netz | Was | KiCad x / y (mm) | So |
|---|---|---|---|---|
| Fläche | GND | Pad 7 von U6 ↔ Zone "GND F.Cu" | 133.5 / 148.7 | Via neben dem Pad auf In1 setzen (Masse-Via 0,6/0,3), kurzer Stummel 0,3 mm zum Pad; die zweite GND-Zeile ist dieselbe Insel |
| Fläche | GND | Zone "GND F.Cu" ↔ Zone "GND F.Cu" | 100.3 / 169.7 | Via neben dem Pad auf In1 setzen (Masse-Via 0,6/0,3), kurzer Stummel 0,3 mm zum Pad; die zweite GND-Zeile ist dieselbe Insel |
| Fläche | VBAT2_F | Zone "VBAT2_F" ↔ Pad 1 von R4 | 132.6 / 153.0 | Bahn 1,0 mm vom Pad R4 in die Fläche F1 → Q6 ziehen |
| Fläche | VBAT2_RAW | Pad 1 von J18 ↔ Zone "VBAT2_RAW" | 146.0 / 150.4 | Bahn 1,0 mm von J18 Pin 1 in die Fläche XT30 → Q1 |
| Fläche | VBAT_PROT | Zone "VBAT_PROT" ↔ Zone "VBAT_PROT" | 153.5 / 91.6 | die kleine Insel am Stich zu J4 Pin 1 mit einer Bahn 1,0 mm an die große anbinden |
| Fläche | VSERVO | Pad 1 von C36 ↔ Zone "VSERVO" | 143.6 / 107.8 | C36 Pin 1 mit Bahn 1,0 mm an die VSERVO-Fläche (Puffer-Elko, kurz halten) |
| Fläche | VSERVO | Zone "VSERVO" ↔ Pad 6 von J15 | 140.7 / 92.7 | J15 Pin 6 (Stapelstecker, VSERVO) von der inneren Schiene aus nach Westen anbinden, 1,0 mm, nur F.Cu |
| Versorgung | 5V_SYS | Pad 4 von J15 ↔ Bahn | 140.7 / 90.1 | 0,6 mm zur nächsten 5V_SYS-Bahn; Via auf die 5V_SYS-Fläche (B.Cu) nur dort, wo sie liegt (1S-Seite, linker Streifen und unter dem Teensy) |
| Versorgung | GND_PWR | Bahn ↔ Pad 2 von C6 | 126.3 / 147.7 | Via 0,6/0,3 direkt neben dem Pad auf die GND_PWR-Fläche (B.Cu, unter allem am 2S); Stummel 0,5 mm |
| Versorgung | GND_PWR | Via - B.Cu ↔ Pad 2 von C38 | 139.3 / 116.5 | Via 0,6/0,3 direkt neben dem Pad auf die GND_PWR-Fläche (B.Cu, unter allem am 2S); Stummel 0,5 mm |
| Versorgung | VSERVO | Bahn ↔ Bahn | 146.0 / 122.1 | zwei VSERVO-Bahnenden an der Schiene verbinden, 0,5 mm, nur F.Cu |
| Versorgung | VSERVO | Pad 12 von U7 ↔ Bahn | 146.4 / 115.8 | U7 Pin 12 (VM) vom Pad gerade heraus, dann 0,5 mm zur VSERVO-Bahn; nur F.Cu |
| Versorgung | VSERVO | Pad 6 von J15 ↔ Pad 5 von J15 | 140.7 / 92.7 | J15 Pin 5 und 6 sind beide VSERVO: kurze Bahn 1,0 mm zwischen den beiden Pins |
| Signal | CS_EXT0 | Pad 11 von U12 ↔ Pad 10 von J15 | 124.9 / 126.6 | 0,2 mm, In2 erlaubt: vom U12-Pin gerade heraus, Via, auf In2 zum J15-Pin |
| Signal | CS_EXT1 | Pad 10 von U12 ↔ Pad 11 von J15 | 125.5 / 126.6 | wie CS_EXT0 |
| Signal | LORA_M1 | Pad 21 von U10 ↔ Pad 24 von A1 | 101.4 / 113.5 | 0,2 mm; Modus-Pin, darf lang sein; Sperrfläche des LoRa-Moduls (F.Cu/In2) umgehen, Teensy Pin 24 |
| Signal | MOT_A | Bahn ↔ Pad 2 von U7 | 140.6 / 117.1 | Klasse Versorgung, 0,3 mm an den Pins, sonst 0,6; U7 Pin 2 zur Bahn |
| Signal | MOT_B | Pad 5 von U7 ↔ Pad 2 von J8 | 140.6 / 115.8 | wie MOT_A, U7 Pin 5 → J8 Pin 2 |
| Signal | PYRO3_NEG | Pad 3 von Q8 ↔ Bahn | 130.3 / 64.7 | Klasse Strom, nur F.Cu, 1,0 mm: Q8 Pin 3 (Drain) zur Bahn an D5 Pin 2 |
| Signal | SEL2 | Pad 9 von U13 ↔ Bahn | 132.4 / 126.6 | 0,2 mm, vom U13-Pin heraus zum vorhandenen Via |
| Signal | VBAT1_SENSE | Pad 1 von C7 ↔ Bahn | 122.2 / 124.4 | 0,2 mm; C7 Pin 1 über Via zur In2-Bahn |

Die Koordinaten sind die des ersten genannten Pads oder Bahnendes. „Fläche ↔ Pad“ heißt: die Kupferfläche
des Strompfads erreicht das Pad nicht, eine Bahn in Netzbreite dazwischen genügt. Zwei gleiche Zonen in
einer Zeile sind zwei Inseln derselben Fläche.

## 4. Abschluss

In der Git-Bash im KiCad-Ordner:

```bash
./make.sh drc
```

Ziel: 0 Fehler, 0 nicht verbunden. Dann das Prüfskript (KiCad-Python, nicht die Store-Python):

```bash
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" ../review_check_layout.py mainboard.kicad_pcb
```

Erwartet: „2S-Netze auf In2: keine“, im IMU-Umfeld nur die fünf GND-Vias, Sense-Netze nur am Shunt.
Danach den Bestückungsdruck neu setzen (er weicht Pads und Bahnen aus), Bilder, Commit:

```bash
"$LOCALAPPDATA/Programs/KiCad/10.0/bin/python.exe" gen_pcb.py silk
```

```bash
./make.sh drc && ./make.sh img
```

```bash
git add -A hardware/mainboard/kicad && git commit -m "Platine rev B1: alle Verbindungen von Hand geschlossen, DRC 0/0"
```

Dann weiter mit README §8: Review mit dem Kollegen, Papierausdruck, Gerber/BOM/CPL.

## 5. Wenn sich die Schaltung noch ändert

`circuit.py` ändern, `./make.sh sch` laufen lassen (Schaltplan, ERC, Netzlistenprüfung), dann in KiCad
**Werkzeuge → Leiterplatte aus Schaltplan aktualisieren**. Nicht `./make.sh pcb`, nicht `gen_pcb.py place`.
