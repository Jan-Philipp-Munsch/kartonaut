# Gewicht sparen beim Erstflug (aus `cad/weight_levers.py`)

Ausgangslage: Erstflug-Konfiguration aus `mass_model.py`. Δ gegen die Ausgangslage. Schub/Gewicht mit 10,9 N mittlerem Schub des TSP E12. Werte mit [Schätzung] sind Annahmen, keine Wägung. SIL: ein Flug je Zeile, Firmware mit angepasster Masse und angepasstem Hebelarm, statischer Kardanfehler 1°/0,6°.

| Hebel | Rohr | Start | Δ | Schwerpunkt | Hebelarm | Ixx | Schub/Gewicht | Gipfel (SIL) | Kipp max Boost | Sättigung |
|---|---|---|---|---|---|---|---|---|---|---|
| Ausgangslage (Erstflug, Rohr 700 mm) | 700 mm | 761 g | +0 g | 318 mm | 242 mm | 0.0460 | 1.46 | 58 m | 3.1° | 0 % |
| rohr675: Rohr 675 statt 700 mm (kürzestes mit 125-cm-Schirm) | 675 mm | 755 g | -6 g | 312 mm | 235 mm | 0.0428 | 1.47 | 59 m | 2.8° | 0 % |
| kuppler50: Stoßkuppler 50 statt 80 mm | 700 mm | 754 g | -7 g | 317 mm | 240 mm | 0.0457 | 1.47 | 59 m | 2.8° | 0 % |
| stangen_alu: 8 Gewindestangen M2 aus Aluminium statt Stahl | 700 mm | 741 g | -20 g | 321 mm | 245 mm | 0.0457 | 1.50 | 63 m | 2.8° | 0 % |
| druck_leicht: Druckteile 20 % leichter (Wände/Füllung) [Schätzung] | 700 mm | 738 g | -23 g | 324 mm | 247 mm | 0.0450 | 1.51 | 64 m | 2.9° | 0 % |
| akku_300: 2S-Akku 300 statt 450 mAh, 20 statt 30 g [Schätzung] | 700 mm | 751 g | -10 g | 320 mm | 244 mm | 0.0458 | 1.48 | 60 m | 2.8° | 0 % |
| arm_stecker: Arming-Stecker statt Schlüsselschalter, 10 statt 28 g [Schätzung] | 700 mm | 743 g | -18 g | 323 mm | 247 mm | 0.0452 | 1.50 | 62 m | 2.9° | 0 % |
| schirm100: Fallschirm Ø 100 statt 125 cm, gepackt 150 statt 230 mm [Schätzung], Rohr kürzer | 625 mm | 731 g | -31 g | 295 mm | 218 mm | 0.0362 | 1.52 | 66 m | 2.8° | 0 % |
| spitze_druck: Spitze gedruckt, dünnwandig, Kegel 45 statt 80 g [Schätzung] | 700 mm | 726 g | -35 g | 295 mm | 219 mm | 0.0375 | 1.53 | 67 m | 2.8° | 0 % |
| A: Konstruktion: Rohr, Stoßkuppler, Alu-Stangen, leichtere Druckteile; kein Zukauf außer Stangen | 675 mm | 706 g | -55 g | 319 mm | 242 mm | 0.0413 | 1.57 | 74 m | 2.9° | 0 % |
| B: A + Zukauf: A + 300-mAh-Akku + Arming-Stecker + 100-cm-Schirm | 610 mm | 649 g | -112 g | 303 mm | 227 mm | 0.0325 | 1.71 | 94 m | 2.8° | 1 % |
| C: B + Spitze: B + gedruckte Spitze | 610 mm | 614 g | -147 g | 280 mm | 204 mm | 0.0263 | 1.81 | 108 m | 4.8° | 51 % |

## Lesart (22.10.2026)

- **Paket A** (Rohr 675 mm, Stoßkuppler 50 mm, Alu-Gewindestangen, leichtere Druckteile) bringt den
  Erstflug mit −55 g auf 706 g, also unter das 750-g-Ziel, ohne Zukauf außer den Stangen. Gipfel
  58 → 74 m, Regelgüte unverändert. Die Alu-Stangen sind der größte Einzelhebel (−20 g); M2 aus Alu
  ist weich, also nur handfest anziehen.
- **Paket B** (zusätzlich 300-mAh-Akku, Arming-Stecker statt Schlüsselschalter, 100-cm-Schirm) kommt
  auf 649 g und 94 m. Der kleinere Schirm sinkt mit dann 621 g mit ca. 4,2 m/s (Cd 0,75), noch im
  Zielbereich 3,5–5 m/s, und spart 80 mm Rohr. Der Arming-Stecker ändert die Entscheidung E1/A3
  (mechanischer Schlüsselschalter); das ist deine Entscheidung.
- **Paket C** (zusätzlich gedruckte Spitze) spart nochmals 35 g, nimmt aber Masse von oben weg:
  Schwerpunkt 280 statt 318 mm, Hebelarm 204 statt 242 mm, Querträgheit fast halbiert. Mit den
  heutigen Reglerwerten steht der Regler dann zur Hälfte der Brennzeit am Anschlag (51 % Sättigung,
  4,8° Kippwinkel). Nur mit neu abgestimmtem Regler (`run_sil.py --kp/--kd`) sinnvoll.
- Werte mit [Schätzung] erst übernehmen, wenn die Teile gewogen sind. Nach jeder Änderung:
  `python cad/mass_model.py` und `Config.h` (`MASS_KG`, `MOMENT_ARM_M`) nachziehen.
