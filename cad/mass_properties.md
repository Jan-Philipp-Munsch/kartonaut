# Massenmodell und Trägheitsmomente

Erzeugt von `cad/mass_model.py` aus `cad/params.py` am 21.10.2026. Nicht von Hand ändern, Skript laufen lassen.

## Methode

Stabmodell: jedes Teil ist eine Zylinderschale, ein Vollzylinder, eine Kegelmantelfläche, ein Quader, ein dünner Stab oder eine Punktmasse mit bekannter Masse und Lage. Für jedes Teil wird der Trägheitstensor um den eigenen Schwerpunkt gebildet und mit dem Satz von Steiner auf den Gesamtschwerpunkt umgerechnet. Koordinaten wie in der Firmware: z ist die Längsachse, z = 0 die Düsenebene, +z zur Spitze; x zeigt zum Servo des Innenrahmens, y zum Lagerohr des Außenrahmens. Die Blender-Dateien lieferten nur Längen und Lagen (siehe `blender_inventory.md`), keine Massen.

Kardanpunkt (Schnittpunkt der beiden Kipp-Achsen): **76.5 mm** über der Düsenebene (Rahmen-Grundfläche 45 mm + Servomitte 31.5 mm aus Blender). Rohrunterkante 20 mm, Stoß der Rohre 520 mm, Rohroberkante 1020 mm, Spitze 1250 mm. Landebeine eingeklappt (Flugzustand).

## Ergebnis

| Zustand | Masse | Schwerpunkt ab Düse | Hebelarm Kardan–Schwerpunkt | Ixx | Iyy | Izz |
|---|---|---|---|---|---|---|
| Start, voller Motor | 981 g | 448 mm | 372 mm | 0.1096 kg·m² | 0.1096 kg·m² | 0.00105 kg·m² |
| Brennschluss, Treibstoff verbraucht | 953 g | 460 mm | 384 mm | 0.1047 kg·m² | 0.1047 kg·m² | 0.00105 kg·m² |
| Ohne Motor (Adapter bleibt) | 917 g | 477 mm | 400 mm | 0.0983 kg·m² | 0.0983 kg·m² | 0.00105 kg·m² |

Seitlicher Schwerpunktversatz beim Start: x = 0.2 mm, y = -0.7 mm (Servos, Akkus unter der Platine, Teensy darüber). Die Deviationsmomente stehen in der JSON.

Zum Vergleich die bisherigen Platzhalter der Simulation: m = 0,94 kg, Ix = Iy = Iz = 0,1 kg·m², Hebelarm 0,30 m. Das Quer-Trägheitsmoment Ixx = Iyy trifft den Platzhalter nahezu, aber Izz (Rollachse) ist hundertmal kleiner, denn fast alle Masse liegt innerhalb von r = 37 mm. Der Hebelarm ist länger als 0,30 m, weil Flugcomputer, Akkus und Kuppler im Rohrstoß 500 mm über der Düse sitzen und die Spitze 100 g wiegt. Für die Rollregelung mit dem Platzhalter 0,1 kg·m² wäre die Dynamik also um zwei Größenordnungen falsch.

Mit ausgefahrenen Beinen (Landung, ohne Motor-Treibstoff wäre es entsprechend weniger): Schwerpunkt 414 mm, Ixx = 0.1357 kg·m², Izz = 0.0086 kg·m² (Startmasse).

## Teileliste (Startzustand)

| Teil | Masse | z Schwerpunkt | Quelle / Annahme |
|---|---|---|---|
| Motorgehäuse E12 (ohne Treibstoff) | 36.0 g | 48 mm | [BUILD] 64 g gesamt, 28 g Treibstoff |
| Treibstoff E12 | 28.0 g | 35 mm | [Annahme] Treibsatz bei z = 10…60 mm |
| Adapter 29→24 | 15.0 g | 52 mm | [Annahme] 15 g PLA |
| Motorrohr | 12.0 g | 74 mm | [Vorgabe] Kardan 50 g, Aufteilung [Annahme] |
| Innenrahmen | 16.0 g | 69 mm | Anteil der 50 g |
| Außenrahmen | 22.0 g | 69 mm | Anteil der 50 g |
| Servo Außenrahmen (y-Achse) | 10.0 g | 76 mm | [BUILD] W5652H 10 g |
| Servo Innenrahmen (x-Achse) | 10.0 g | 76 mm | [BUILD] W5652H 10 g |
| Rohr unten | 120.0 g | 270 mm | [Klima] 120 g |
| Rohr oben | 120.0 g | 770 mm | [Klima] 120 g |
| Kuppler Flugcomputer | 34.0 g | 520 mm | [Klima] 34 g |
| Spitze Kegel (ABS) | 80.0 g | 1097 mm | [Klima] ca. 100 g gesamt; Aufteilung [Annahme] |
| Spitze Schulterkuppler | 17.0 g | 982 mm | [Annahme] |
| Spitze Spant + Öse | 3.0 g | 1016 mm | [Annahme] |
| Platine + Teensy + Bauteile | 40.0 g | 515 mm | [Annahme] Anteil der 100 g |
| Endring unten | 7.5 g | 448 mm | [Annahme] |
| Endplatte oben (Spant mit Ladungsschale) | 17.5 g | 592 mm | [Annahme] |
| 8 Gewindestangen M2 | 20.0 g | 520 mm | [Annahme] als Ring auf r = 30,3 |
| Träger (gedruckt) | 15.0 g | 515 mm | [Annahme] |
| Akku 2S | 45.0 g | 493 mm | [Vorgabe] 45 g, Maße [BUILD] |
| Akku 1S | 12.0 g | 544 mm | [Vorgabe] 12 g, Maße [Annahme] |
| Kolben Kuppler-Stück | 9.0 g | 620 mm | [Annahme] 34 g/150 mm × 40 mm |
| Kolbenplatte | 10.0 g | 603 mm | [Annahme] |
| Ladungsschale + E-Match + Anker | 12.0 g | 599 mm | [Annahme] |
| Fallschirm 125 cm mit Schockschnur | 50.0 g | 760 mm | [Vorgabe] 50 g |
| Beinring unten (Hülse) | 25.0 g | 21 mm | [Vorgabe] 200 g gesamt, Aufteilung [Annahme] |
| Beinring oben | 25.0 g | 94 mm | Anteil der 200 g |
| Bein 1 Hauptstrebe | 20.0 g | 163 mm | Anteil der 200 g |
| Bein 1 obere Strebe | 10.0 g | 196 mm | Anteil der 200 g |
| Bein 1 Fuß | 7.5 g | 306 mm | Anteil der 200 g |
| Bein 2 Hauptstrebe | 20.0 g | 163 mm | Anteil der 200 g |
| Bein 2 obere Strebe | 10.0 g | 196 mm | Anteil der 200 g |
| Bein 2 Fuß | 7.5 g | 306 mm | Anteil der 200 g |
| Bein 3 Hauptstrebe | 20.0 g | 163 mm | Anteil der 200 g |
| Bein 3 obere Strebe | 10.0 g | 196 mm | Anteil der 200 g |
| Bein 3 Fuß | 7.5 g | 306 mm | Anteil der 200 g |
| Bein 4 Hauptstrebe | 20.0 g | 163 mm | Anteil der 200 g |
| Bein 4 obere Strebe | 10.0 g | 196 mm | Anteil der 200 g |
| Bein 4 Fuß | 7.5 g | 306 mm | Anteil der 200 g |
| Kabel, Schrauben, Kleber | 20.0 g | 520 mm | [Annahme] 20 g |
| **Summe** | **981 g** | | |

## Abweichung vom Massenbudget `Gewicht.csv` (902 g)

Das Budget vom Juni 2025 rechnet mit zwei Motoren (128 g), aber ohne Servos, Adapter, Kolben-Ausstoß, zweiten Akku und Kleinteile. Mit einem Motor und den Teilen der Entscheidungen vom 21.10.2026 kommt das Stabmodell auf 981 g. Die größten Unsicherheiten: Landesystem (200 g Vorgabe, keine Konstruktion), Flugcomputer 100 g (Platine rev B existiert noch nicht), Kolben-Ausstoß und Kleinteile (Schätzung).

## Nachzumessen

- Masse von Spitze, Kuppler, Rohr auf der Küchenwaage (Shop-Angaben: 100 / 34 / 120 g).
- Motor E12 wiegen; Lage des Treibsatzes aus dem Datenblatt (hier z = 10 bis 60 mm angenommen).
- Gedruckte Kardanteile wiegen (hier 50 g gesamt).
- Nach dem Zusammenbau: Schwerpunkt per Auswiegen (Rakete auf einer Kante balancieren) und Quer-Trägheitsmoment per Pendelversuch (bifilar). Beides gegen diese Tabelle halten und `params.py` anpassen.
