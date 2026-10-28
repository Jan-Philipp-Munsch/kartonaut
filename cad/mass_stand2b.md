# Massenbudget Kartonaut 1, Modulbauweise Stand 2b mit Druckteilen Stand 2c

Erzeugt von `cad/mass_stand2b.py` am 22.10.2026 aus `modular_params.py` und `export/modular/masses.json`. Nicht von Hand ändern, Skript laufen lassen. Methode wie `mass_properties.md` (Stabmodell, Steiner), Koordinaten z ab der Rohrunterkante von Rohr A (Motor bündig, also Düsenebene).

Kardanpunkt der gebauten Druckdatei: **69.5 mm** (Grundfläche 38 + Servomitte 31.5). Gesamtlänge mit Spitze 731 mm.

## Ergebnis

| Zustand | Masse | Schwerpunkt ab Düse | Hebelarm Kardan–Schwerpunkt | Ixx = Iyy | Izz (Roll) |
|---|---|---|---|---|---|
| Start, voller Motor | **704 g** | 260 mm | 190 mm | 0.0211 kg·m² | 0.00047 kg·m² |
| Brennschluss, Treibstoff verbraucht | **676 g** | 269 mm | 199 mm | 0.0196 kg·m² | 0.00047 kg·m² |
| Ohne Motor (Adapter bleibt) | **640 g** | 281 mm | 212 mm | 0.0177 kg·m² | 0.00046 kg·m² |

Schub-Gewichts-Verhältnis mit 12 N mittlerem Schub des TSP E12: **1.74** (Spitzenschub 28,3 N: 4.1). Ziel unter 750 g: **erreicht**, Reserve 46 g. Seitlicher Schwerpunktversatz beim Start x = -0.1 mm, y = -1.4 mm.

## Nach Baugruppen

| Baugruppe | Masse | Anteil |
|---|---|---|
| Motor | 36 g | 5 % |
| Treibstoff | 28 g | 4 % |
| Kardan, Servos, Adapter | 88 g | 12 % |
| Rohre und Kuppler | 136 g | 19 % |
| neue Druckteile | 73 g | 10 % |
| Flugcomputer, Akkus, Antennen, Schalterbrett | 115 g | 16 % |
| CO₂-Ausstoß | 44 g | 6 % |
| Fallschirm | 50 g | 7 % |
| Spitze | 100 g | 14 % |
| Kleinteile | 34 g | 5 % |
| **Start gesamt** | **704 g** | |

## Was sich gegenüber den Vorgängern geändert hat

| Modell | Start | Hebelarm | Bemerkung |
|---|---|---|---|
| `voll` (21.10.), 1000 mm Rohr, Beine, Ring-Stack | 981 g | 372 mm | Simulation: 20 m Gipfel, Schub-Gewicht 1,1 |
| `erstflug` (22.10.), 700 mm Rohr, Kolben, Schlüsselschalter | 761 g | 242 mm | Ziel 750 g um 11 g verfehlt |
| Stand 2b, Schätzung in `modular.py` | 689 g | – | Differenz zu 761 g aus Listen MASS_REMOVED / MASS_ADDED_HW |
| Stand 2b, Stabmodell (22.10. nachts) | 723 g | 186 mm | mit LoRa-Wendel, CO₂-Servo, Schalterbrett-Bauteilen, Ringschraube, Hebeln; Druckteile 98 g (75-%-Regel) |
| **Stand 2d, dieses Modell** | **704 g** | 190 mm | Druckteile Leichtbau, 73 g nach dem Slicer-Modell (-19 g) |

Die großen Hebel gegenüber 761 g: keine Gewindestangen (−30 g), Rohr 496 statt 700 mm (−49 g), kein Kolben (−31 g), kein Schlüsselschalter mit Kragen (−28 g), halbe Kuppler (−34 g); dagegen CO₂-Modul mit Kapsel und Servo (+44 g) und der Schlitten mit Spant als ein großes Druckteil (+74 g gegen Endringe und Träger 40 g).

Der Hebelarm Kardan–Schwerpunkt ist kurz: die schwere Spitze (83 g) und der Schirm sitzen zwar oben, aber Motor, Kardan und Rohr A liegen dicht am Kardanpunkt. Für die Firmware (`MOMENT_ARM_M`, `MASS_KG`) gelten nach dem Wiegen die gemessenen Werte.

## Druckteile Stand 2c: was sich geändert hat

| Teil | Stand 2b | Stand 2c | Änderung |
|---|---|---|---|
| Schlitten mit Spant | 77,9 cm³, 71 g | 53,0 cm³, 64 g | Spantplatte 3,5 statt 5 mm (außen 5-mm-Rand), Zapfen 2 statt 4,1/3,1 mm, U-Profil statt Klotz zwischen Träger und Zapfen (11,5 cm³), Fenster im Boden unter den Akkus, Augen weiter innen (≥ 2,9 mm hinter der Mutter) |
| Untere Scheibe | 8,7 cm³, 10 g | 5,8 cm³, 7 g | 2 statt 3 mm |
| Schalterbrett | 2,1 cm³, 3 g | unverändert | |
| Schraubring J1 | 14,6 cm³, 12 g | 4,5 cm³, 6 g | Wand 2 statt 6 mm, 10 statt 12 mm hoch, vier Augen mit Muttern |
| **Summe** | **96 g** | **80 g** | Massen nach dem Slicer-Modell (Oberfläche × 1 mm voll, Rest 25 %); nach der alten 75-%-Regel 98 → 62 g |

Das Volumen sinkt um 36 %, die Druckmasse nur um 17 %: dünne Wände druckt der Slicer mit drei Perimetern voll, dicke Wände waren innen schon zu 75 % hohl. Mehr spart nur Material, das ganz wegfällt. Weitere Fenster lohnen kaum (der Schlitten besteht jetzt fast nur aus Hülle, Masse ∝ Oberfläche); zwei statt drei Perimeter ändern an 2-mm-Wänden nichts. Festigkeit: Spantplatte bei 2,6 bar (Spitze klemmt, Obergrenze) 21 bis 34 MPa, PETG 45 bis 50 MPa; bei < 0,1 bar (Spitze geht ab) unter 2 MPa. Der Träger hängt mit Boden und Wänden an der Platte und mit dem Boden als Sehne an der Zapfenwand.

## Gewichtshebel über die ganze Rakete

Jeder Hebel einzeln gegen die Ausgangslage, dann drei Pakete. Masse, Schwerpunkt, Hebelarm und Trägheit aus dem Stabmodell; Schub-Gewicht mit 12 N. Regelgüte und Gipfel der Pakete: `simulation/README.md` (Nachtrag 23.10.).

| Hebel | Start | Δ | Schwerpunkt | Hebelarm | Ixx | Schub/Gewicht | Bewertung |
|---|---|---|---|---|---|---|---|
| Stand 2d (Druckteile Leichtbau, GPS NEO-6M), Ausgangslage | 704 g | +0 g | 260 mm | 190 mm | 0.0211 | 1.74 |  |
| 2S-Akku 300 statt 450 mAh (ca. 20 statt 29 g) [Annahme] | 695 g | -9 g | 260 mm | 191 mm | 0.0211 | 1.76 | reicht für 2 Servos und das CO₂-Servo über Stunden; 35C × 0,3 Ah = 10 A Spitze |
| Motoradapter 29→24 als drei Ringe statt Vollrohr (7 statt 15 g) [Annahme] | 696 g | -8 g | 262 mm | 193 mm | 0.0207 | 1.76 | neu drucken; der Motor sitzt weiter im gebauten Motorrohr |
| Mikroservo 4,5 g statt SG90 (9 g) für die CO₂-Auslösung [Annahme] | 700 g | -4 g | 259 mm | 190 mm | 0.0211 | 1.75 | Stellkraft für den Anstecher prüfen |
| Spitzen-Kuppler 50 statt 75 mm (25 in der Spitze, 25 in Rohr C), Rohr C 170 statt 195 mm | 692 g | -12 g | 252 mm | 183 mm | 0.0190 | 1.77 | Schnurraum 97 statt 194 cm³; 1 m Kevlar und 1,8 m Gummischnur brauchen ca. 30 cm³ |
| Fallschirm 100 statt 125 cm (ca. 35 statt 50 g, gepackt 80 statt 100 mm) [Annahme] | 684 g | -20 g | 252 mm | 183 mm | 0.0193 | 1.79 | Sinkrate 3,4 → 4,3 m/s (Cd 0,75), Aufprallenergie +60 %; muss gekauft werden |
| Federausstoß mit Servoriegel statt CO₂ (Feder 5 g + Riegel 3 g + Mikroservo 4,5 g statt 44 g) [Konzept] | 673 g | -31 g | 256 mm | 187 mm | 0.0209 | 1.82 | Konzeptänderung (Jan 22.10.: CO₂); Feder muss Spitze und Schirm 100 mm weit schieben, am Tisch beliebig testbar |
| Spitze gedruckt, dünnwandig (45 statt 83 g) [Annahme] | 666 g | -38 g | 241 mm | 172 mm | 0.0169 | 1.84 | nimmt Masse ganz oben weg: Schwerpunkt und Hebelarm sinken deutlich |
| **P1** ohne Konzeptänderung: Akku, Adapter, Mikroservo, kurzer Spitzen-Kuppler | 671 g | -33 g | 255 mm | 185 mm | 0.0186 | 1.82 | akku300+adapter+mikroservo+kuppler50 |
| **P2** P1 + Federausstoß + 100-cm-Schirm | 630 g | -74 g | 246 mm | 176 mm | 0.0171 | 1.94 | akku300+adapter+kuppler50+feder+schirm100 |
| **P3** P2 + gedruckte Spitze | 592 g | -112 g | 227 mm | 158 mm | 0.0136 | 2.07 | akku300+adapter+kuppler50+feder+schirm100+spitze_druck |

Was nicht in der Tabelle steht, weil es fest oder schon minimal ist: Motor 64 g, Platine mit Teensy 45 g (Schätzung), Rohre A/B 72 g (gebaut), Kardan mit Servos 73 g (gebaut, wiegen), GPS 6 g und LoRa 5 g (für die Suche in abgelegenem Gelände nötig), 1S 14 g.

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
| Hebel + Drahtbügel (Außenrahmen) | 1.5 g | 70 mm | [Annahme] 1,5 g je Servo, Hebel nach oben (Jans Fotos) |
| Servo W5652H Innenrahmen (treibt Motorrohr) | 10.0 g | 70 mm | [BUILD] W5652H 10 g, Lage aus der Druckdatei |
| Hebel + Drahtbügel (Innenrahmen) | 1.5 g | 70 mm | [Annahme] 1,5 g je Servo, Hebel nach oben (Jans Fotos) |
| Rohr A 125 (Kardan) | 30.0 g | 62 mm | [Klima] 0,24 g/mm, Länge [Jan] |
| Kuppler J1 75 mm (in B verklebt) | 17.0 g | 125 mm | [Klima] halber Kuppler 17 g |
| Schraubring J1 (gedruckt) | 5.5 g | 110 mm | masses.json, 75 % Volumen PETG |
| Rohr B 176 (Avionik) | 42.2 g | 213 mm | [Klima] 0,24 g/mm, Länge [Jan] |
| Untere Scheibe (gedruckt) | 7.3 g | 156 mm | masses.json |
| Schlitten: Band, Spantplatte, beide Zapfen | 35.7 g | 302 mm | [CAD] 62 % der 58 g (Volumenanteil Stand 2d, Slicer-Modell) |
| Schlitten: Träger, Säulen, Fächer, GPS-Leisten | 21.9 g | 220 mm | Rest der Schlittenmasse, unter der Platine |
| Platine rev B1 + Teensy + Bauteile | 45.0 g | 227 mm | [Vorgabe] 45 g |
| Akku 2S LemonRC 450 mAh | 29.0 g | 200 mm | [reichelt] 29 g |
| Akku 1S 600 mAh | 14.0 g | 256 mm | [Annahme] 14 g, vorhanden (BUILD §1.3) |
| GPS NEO-6M (GY-GPS6MV2) mit Patch 25 × 25 | 12.0 g | 295 mm | [Annahme] 12 g, wiegen |
| LoRa-Wendel + Pigtail | 5.0 g | 149 mm | [Annahme] 5 g |
| Schalterbrett (gedruckt) | 2.7 g | 211 mm | masses.json |
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
| **Summe** | **704 g** | | |

## Nachzumessen

- Jedes Druckteil nach dem Druck wiegen (hier Slicer-Modell: Oberfläche × 1 mm voll, Rest 25 % Gyroid; die Slicer-Vorschau nennt die Masse genauer).
- Spitze mit Holzplatte, beide halben Kuppler, Rohre A/B/C, Kardan mit Servos und Gestänge auf die Waage.
- CO₂-Modul mit gefüllter Kapsel und Servo; 1S-Akku; LoRa-Wendel mit Pigtail.
- Nach dem Zusammenbau: Schwerpunkt auswiegen, Quer-Trägheitsmoment per Bifilarpendel; `Config.h` und die Simulation (`--vehicle stand2b`) damit korrigieren.
