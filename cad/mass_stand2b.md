# Massenbudget Kartonaut 1, Modulbauweise Stand 2b

Erzeugt von `cad/mass_stand2b.py` am 22.10.2026 aus `modular_params.py` und `export/modular/masses.json`. Nicht von Hand ändern, Skript laufen lassen. Methode wie `mass_properties.md` (Stabmodell, Steiner), Koordinaten z ab der Rohrunterkante von Rohr A (Motor bündig, also Düsenebene).

Kardanpunkt der gebauten Druckdatei: **69.5 mm** (Grundfläche 38 + Servomitte 31.5). Gesamtlänge mit Spitze 731 mm.

## Ergebnis

| Zustand | Masse | Schwerpunkt ab Düse | Hebelarm Kardan–Schwerpunkt | Ixx = Iyy | Izz (Roll) |
|---|---|---|---|---|---|
| Start, voller Motor | **723 g** | 256 mm | 186 mm | 0.0213 kg·m² | 0.00047 kg·m² |
| Brennschluss, Treibstoff verbraucht | **695 g** | 265 mm | 195 mm | 0.0199 kg·m² | 0.00047 kg·m² |
| Ohne Motor (Adapter bleibt) | **659 g** | 277 mm | 207 mm | 0.0180 kg·m² | 0.00047 kg·m² |

Schub-Gewichts-Verhältnis mit 12 N mittlerem Schub des TSP E12: **1.69** (Spitzenschub 28,3 N: 4.0). Ziel unter 750 g: **erreicht**, Reserve 27 g. Seitlicher Schwerpunktversatz beim Start x = -0.1 mm, y = -1.6 mm.

## Nach Baugruppen

| Baugruppe | Masse | Anteil |
|---|---|---|
| Motor | 36 g | 5 % |
| Treibstoff | 28 g | 4 % |
| Kardan, Servos, Adapter | 88 g | 12 % |
| Rohre und Kuppler | 136 g | 19 % |
| neue Druckteile | 98 g | 14 % |
| Flugcomputer, Akkus, Antennen, Schalterbrett | 109 g | 15 % |
| CO₂-Ausstoß | 44 g | 6 % |
| Fallschirm | 50 g | 7 % |
| Spitze | 100 g | 14 % |
| Kleinteile | 34 g | 5 % |
| **Start gesamt** | **723 g** | |

## Was sich gegenüber den Vorgängern geändert hat

| Modell | Start | Hebelarm | Bemerkung |
|---|---|---|---|
| `voll` (21.10.), 1000 mm Rohr, Beine, Ring-Stack | 981 g | 372 mm | Simulation: 20 m Gipfel, Schub-Gewicht 1,1 |
| `erstflug` (22.10.), 700 mm Rohr, Kolben, Schlüsselschalter | 761 g | 242 mm | Ziel 750 g um 11 g verfehlt |
| Stand 2b, Schätzung in `modular.py` | 689 g | – | Differenz zu 761 g aus Listen MASS_REMOVED / MASS_ADDED_HW |
| **Stand 2b, dieses Modell** | **723 g** | 186 mm | mit LoRa-Wendel, CO₂-Servo, Schalterbrett-Bauteilen, Ringschraube, Hebeln (+34 g gegenüber `modular.py`) |

Die großen Hebel gegenüber 761 g: keine Gewindestangen (−30 g), Rohr 496 statt 700 mm (−49 g), kein Kolben (−31 g), kein Schlüsselschalter mit Kragen (−28 g), halbe Kuppler (−34 g); dagegen CO₂-Modul mit Kapsel und Servo (+44 g) und der Schlitten mit Spant als ein großes Druckteil (+74 g gegen Endringe und Träger 40 g).

Der Hebelarm Kardan–Schwerpunkt ist kurz: die schwere Spitze (83 g) und der Schirm sitzen zwar oben, aber Motor, Kardan und Rohr A liegen dicht am Kardanpunkt. Für die Firmware (`MOMENT_ARM_M`, `MASS_KG`) gelten nach dem Wiegen die gemessenen Werte.

## Teileliste (Startzustand)

| Teil | Masse | z Schwerpunkt | Quelle / Annahme |
|---|---|---|---|
| Motorgehäuse E12 (ohne Treibstoff) | 36.0 g | 46 mm | [BUILD] 64 g gesamt, 28 g Treibstoff; bündig mit Rohr A [Jan] |
| Treibstoff E12 | 28.0 g | 35 mm | [Annahme] Treibsatz bei z = 10…60 mm |
| Adapter 29→24 | 15.0 g | 50 mm | [Annahme] 15 g PLA |
| Motorrohr (gedruckt, Blender 12.06.2025) | 12.0 g | 66 mm | [Vorgabe] Kardan 50 g, Aufteilung [Annahme] |
| Innenrahmen | 16.0 g | 62 mm | Anteil der 50 g |
| Außenrahmen mit Flansch | 22.0 g | 62 mm | Anteil der 50 g |
| Servo W5652H Außenrahmen (treibt Innenrahmen) | 10.0 g | 70 mm | [BUILD] W5652H 10 g, Lage aus der Druckdatei |
| Hebel + Drahtbügel (Außenrahmen) | 1.5 g | 69 mm | [Annahme] 1,5 g je Servo |
| Servo W5652H Innenrahmen (treibt Motorrohr) | 10.0 g | 70 mm | [BUILD] W5652H 10 g, Lage aus der Druckdatei |
| Hebel + Drahtbügel (Innenrahmen) | 1.5 g | 69 mm | [Annahme] 1,5 g je Servo |
| Rohr A 125 (Kardan) | 30.0 g | 62 mm | [Klima] 0,24 g/mm, Länge [Jan] |
| Kuppler J1 75 mm (in B verklebt) | 17.0 g | 125 mm | [Klima] halber Kuppler 17 g |
| Schraubring J1 (gedruckt) | 13.9 g | 110 mm | masses.json, 75 % Volumen PETG |
| Rohr B 176 (Avionik) | 42.2 g | 213 mm | [Klima] 0,24 g/mm, Länge [Jan] |
| Untere Scheibe (gedruckt) | 8.2 g | 156 mm | masses.json |
| Schlitten: Band mit beiden Zapfen | 30.0 g | 302 mm | [Annahme] Aufteilung der 74 g aus masses.json: Band + Zapfen ca. 32 cm³ |
| Schlitten: Träger, Säulen, Fächer, GPS-Leisten | 44.2 g | 220 mm | Rest der Schlittenmasse, unter der Platine |
| Platine rev B1 + Teensy + Bauteile | 45.0 g | 227 mm | [Vorgabe] 45 g |
| Akku 2S LemonRC 450 mAh | 29.0 g | 200 mm | [reichelt] 29 g |
| Akku 1S 600 mAh | 14.0 g | 256 mm | [Annahme] 14 g, vorhanden (BUILD §1.3) |
| GPS-Modul 20 × 20 (Patch nach oben) | 6.0 g | 297 mm | [Annahme] 6 g |
| LoRa-Wendel + Pigtail | 5.0 g | 149 mm | [Annahme] 5 g |
| Schalterbrett (gedruckt) | 2.0 g | 211 mm | masses.json |
| Schalterbrett: Schalter, USB-C, XT30, XH-3, LED, Kabel | 8.0 g | 212 mm | [Annahme] 8 g |
| ARM-Brücke / Schraubschalter | 2.0 g | 237 mm | [Annahme] 2 g |
| Ringschraube M4 mit Mutter | 4.0 g | 304 mm | [Annahme] 4 g |
| Rohr C 195 (Bergung) | 46.8 g | 404 mm | [Klima] 0,24 g/mm |
| CO₂-Modul: Aufbau (gedruckt, Anstecher) | 10.0 g | 334 mm | [Jan] ca. 10 g |
| CO₂-Kapsel 8 g, gefüllt (quer) | 25.0 g | 334 mm | [Annahme] 25 g, Stahl 18 × 65 |
| Servo CO₂-Auslösung (SG90) | 9.0 g | 334 mm | [Annahme] 9 g, Auslösung über Servo (Bauanleitung §1.1) |
| Fallschirm 125 cm mit Schockschnur, gepackt | 50.0 g | 399 mm | [Vorgabe] 50 g |
| Kuppler Spitze 75 mm (in der Spitze verklebt) | 17.0 g | 488 mm | [Klima] halber Kuppler 17 g |
| Spitze Klima 8539 mit Holzplatte und Haken | 83.0 g | 578 mm | [Klima] ca. 100 g inkl. Schulter; hier ohne Schulter |
| M3-Schrauben und Muttern (ca. 20) | 8.0 g | 200 mm | [Annahme] 8 g |
| Kabel, Kleber, Moosgummi, Schaum | 22.0 g | 230 mm | [Annahme] 22 g |
| **Summe** | **723 g** | | |

## Nachzumessen

- Jedes Druckteil nach dem Druck wiegen (hier 75 % des CAD-Volumens; mit 3 Wänden und 25 % Füllung ist der Schlitten eher bei 60 g).
- Spitze mit Holzplatte, beide halben Kuppler, Rohre A/B/C, Kardan mit Servos und Gestänge auf die Waage.
- CO₂-Modul mit gefüllter Kapsel und Servo; 1S-Akku; LoRa-Wendel mit Pigtail.
- Nach dem Zusammenbau: Schwerpunkt auswiegen, Quer-Trägheitsmoment per Bifilarpendel; `Config.h` und die Simulation (`--vehicle stand2b`) damit korrigieren.
