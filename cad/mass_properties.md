# Massenmodell und Trägheitsmomente

Erzeugt von `cad/mass_model.py` aus `cad/params.py` am 21.10.2026. Nicht von Hand ändern, Skript laufen lassen.

## Methode

Stabmodell: jedes Teil ist eine Zylinderschale, ein Vollzylinder, eine Kegelmantelfläche, ein Quader, ein dünner Stab oder eine Punktmasse mit bekannter Masse und Lage. Für jedes Teil wird der Trägheitstensor um den eigenen Schwerpunkt gebildet und mit dem Satz von Steiner auf den Gesamtschwerpunkt umgerechnet. Koordinaten wie in der Firmware: z ist die Längsachse, z = 0 die Düsenebene, +z zur Spitze; x zeigt zum Servo des Innenrahmens, y zum Lagerohr des Außenrahmens. Die Blender-Dateien lieferten nur Längen und Lagen (siehe `blender_inventory.md`), keine Massen.

Kardanpunkt (Schnittpunkt der beiden Kipp-Achsen): **76.5 mm** über der Düsenebene (Rahmen-Grundfläche 45 mm + Servomitte 31.5 mm aus Blender). Rohrunterkante 20 mm, Stoß der Rohre 520 mm, Rohroberkante 1020 mm, Spitze 1250 mm. Landebeine eingeklappt (Flugzustand).

## Ergebnis

| Zustand | Masse | Schwerpunkt ab Düse | Hebelarm Kardan–Schwerpunkt | Ixx | Iyy | Izz |
|---|---|---|---|---|---|---|
| Start, voller Motor | 981 g | 449 mm | 372 mm | 0.1098 kg·m² | 0.1098 kg·m² | 0.00105 kg·m² |
| Brennschluss, Treibstoff verbraucht | 953 g | 461 mm | 384 mm | 0.1049 kg·m² | 0.1049 kg·m² | 0.00105 kg·m² |
| Ohne Motor (Adapter bleibt) | 917 g | 477 mm | 401 mm | 0.0985 kg·m² | 0.0985 kg·m² | 0.00105 kg·m² |

Seitlicher Schwerpunktversatz beim Start: x = 0.2 mm, y = -0.7 mm (Servos, Akkus unter der Platine, Teensy darüber). Die Deviationsmomente stehen in der JSON.

Zum Vergleich die bisherigen Platzhalter der Simulation: m = 0,94 kg, Ix = Iy = Iz = 0,1 kg·m², Hebelarm 0,30 m. Das Quer-Trägheitsmoment Ixx = Iyy trifft den Platzhalter nahezu, aber Izz (Rollachse) ist hundertmal kleiner, denn fast alle Masse liegt innerhalb von r = 37 mm. Der Hebelarm ist länger als 0,30 m, weil Flugcomputer, Akkus und Kuppler im Rohrstoß 500 mm über der Düse sitzen und die Spitze 100 g wiegt. Für die Rollregelung mit dem Platzhalter 0,1 kg·m² wäre die Dynamik also um zwei Größenordnungen falsch.

Mit ausgefahrenen Beinen (Landung, ohne Motor-Treibstoff wäre es entsprechend weniger): Schwerpunkt 414 mm, Ixx = 0.1359 kg·m², Izz = 0.0086 kg·m² (Startmasse).

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
| Rohr unten | 120.0 g | 270 mm | [Klima] 240 g/m |
| Rohr oben | 120.0 g | 770 mm | [Klima] 240 g/m |
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
| Kolben Kuppler-Stück | 9.0 g | 626 mm | [Annahme] 34 g/150 mm × 40 mm |
| Kolbenplatte | 10.0 g | 609 mm | [Annahme] |
| Ladungsschale + E-Match + Anker | 12.0 g | 599 mm | [Annahme] |
| Fallschirm 125 cm mit Schockschnur | 50.0 g | 766 mm | [Vorgabe] 50 g |
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

## Erstflug-Konfiguration (22.10.2026)

Entscheidung Jan 22.10.2026: Aufstieg mit einem Motor (TSP E12-0) und Fallschirm, kein Landesystem, Rohr aus Papier. Gegenüber der Konfiguration oben (`config="voll"`) gilt bei `config="erstflug"` (`MS_CONFIG=erstflug`, `layout()` in `params.py`):

- keine Beine, kein Beinring, kein Aktor (−200 g); der zweite Motor war im Modell schon nicht enthalten.
- 8 Gewindestangen mit 30 g statt 20 g: die Luken brauchen alle acht als Fensterbegrenzung.
- 2S-Akku 450 mAh mit 30 g statt 45 g (Abmessungen 56 × 25,5 × 8 der 850er zur Sicherheit beibehalten); Mainboard 54 × 120 mit Teensy 45 g statt 40 g.
- Hardware der Luken (Schalterbrett, Schlüsselschalter, Kragen) 34 g [Annahme], neu.
- Kolbenabstand 11 statt 5 mm (auch bei "voll"): die Ladungsschale (8 mm) und die Öse (8,5 mm) der Endplatte durchdrangen sonst die Kolbenplatte.
- Das Rohr beginnt wie bisher bei z = 20 mm. Über dem Kardan folgt der Schlüsselschalter-Kragen (z = 107 … 125), dann der Kuppler ganz im unteren Rohr (500 mm Klima-Länge, beide Luken darin). Das obere Rohr (200 mm) stößt bei z = 520 im Fallschirmraum an; ein 80-mm-Kupplerstück (18 g) überbrückt den Stoß. Rohrmasse 0,24 g/mm.

### Kürzestes Rohr

Rohrlänge = Rohrunterkante (z = 20 mm) bis Spitzenbasis. Die Stapelhöhe über dem Kardan bestimmt das Minimum:

| Abschnitt | Länge | z von … bis |
|---|---|---|
| Kardan (Motorrohr endet bei 103, mit 7° bis 105) | | 20 … 107 |
| Schlüsselschalter-Kragen + 2 mm Luft | 20 mm | 107 … 127 |
| Flugcomputer-Kuppler | 150 mm | 127 … 277 |
| Gasraum + Kolben | 11 + 40 mm | 277 … 328 |
| Fallschirm 125 cm (Ø 60 × 230) mit 5 mm Luft | 235 mm | 333 … 563 |
| Schockschnur | 50 mm | 563 … 613 |
| Schulter der Spitze bis Unterkante der Öse am Spant | 81.5 mm | … 695 (Rohrende) |
| **Rohr gesamt (Minimum)** | **675 mm** | |

Das Minimum hängt an Annahmen: gepackter Fallschirm 230 mm (`CHUTE_L`), 50 mm Raum für die Schockschnur (`CORD_BAY_MIN`) bis zur Öse der Spitze, Kolben 40 mm. Jede 10 mm weniger Schirm oder Schnurraum kürzen das Rohr um 10 mm (2,4 g). Beim Packen nachmessen. Bei 700 mm bleiben 76 mm Raum über dem Schirm.

### Ergebnis

| Konfiguration | Rohr | Start | Schwerpunkt ab Düse | Hebelarm Kardan–CG | Ixx = Iyy | Izz | Brennschluss | Hebelarm BS |
|---|---|---|---|---|---|---|---|---|
| voll, Beine, 850-mAh-2S | 1000 mm | **981 g** | 449 mm | 372 mm | 0.1098 kg·m² | 0.00105 kg·m² | 953 g | 384 mm |
| Erstflug | 700 mm | **761 g** | 318 mm | 242 mm | 0.0460 kg·m² | 0.00057 kg·m² | 733 g | 253 mm |
| Erstflug, kürzestes Rohr | 675 mm | **755 g** | 312 mm | 235 mm | 0.0428 kg·m² | 0.00056 kg·m² | 727 g | 246 mm |

Ziel unter 750 g: verfehlt (761 g bei 700 mm, 755 g bei 675 mm). Schub-Gewicht mit 12 N mittlerem Schub bei 700 mm: 1.61.

Hebel, um unter 750 g zu kommen (je einzeln, Modellwerte): Rohr 675 statt 700 mm −6 g; Stoßkuppler 50 statt 80 mm −7 g; 2S-Akku 450 mAh wiegen (30 g angenommen); Kleinteile 20 g (`MISC_M`) nachwiegen; Endringe 25 g und Träger 15 g als Leichtbau-Druckteile; Spitze wiegen (100 g Shop-Angabe). Die Teile des Erstflugs auf der Waage ersetzen die Schätzung.

### Teileliste Erstflug, Rohr 700 mm (Start)

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
| Rohr unten | 120.0 g | 270 mm | [Klima] 240 g/m |
| Rohr oben | 48.0 g | 620 mm | [Klima] 240 g/m |
| Kuppler Flugcomputer | 34.0 g | 202 mm | [Klima] 34 g |
| Spitze Kegel (ABS) | 80.0 g | 797 mm | [Klima] ca. 100 g gesamt; Aufteilung [Annahme] |
| Spitze Schulterkuppler | 17.0 g | 682 mm | [Annahme] |
| Spitze Spant + Öse | 3.0 g | 716 mm | [Annahme] |
| Platine + Teensy + Bauteile | 45.0 g | 197 mm | [Annahme] Anteil der 100 g |
| Endring unten | 7.5 g | 130 mm | [Annahme] |
| Endplatte oben (Spant mit Ladungsschale) | 17.5 g | 274 mm | [Annahme] |
| 8 Gewindestangen M2 | 30.0 g | 202 mm | [Annahme] als Ring auf r = 30,3 |
| Träger (gedruckt) | 15.0 g | 197 mm | [Annahme] |
| Akku 2S | 30.0 g | 175 mm | [Vorgabe] 45 g, Maße [BUILD] |
| Akku 1S | 12.0 g | 226 mm | [Vorgabe] 12 g, Maße [Annahme] |
| Kolben Kuppler-Stück | 9.0 g | 308 mm | [Annahme] 34 g/150 mm × 40 mm |
| Kolbenplatte | 10.0 g | 291 mm | [Annahme] |
| Ladungsschale + E-Match + Anker | 12.0 g | 281 mm | [Annahme] |
| Fallschirm 125 cm mit Schockschnur | 50.0 g | 448 mm | [Vorgabe] 50 g |
| Schlüsselschalter-Kragen + Schlüsselschalter | 28.0 g | 116 mm | [Annahme] Kragen 8 g, Schalter mit Schlüssel 20 g |
| Stoßkuppler im Fallschirmraum | 18.1 g | 520 mm | [Klima] 34 g/150 mm × 80 mm; Rohr 500 + 200 |
| Schalterbrett (Schalter, USB-C, XT30, XH-3, LED) | 6.0 g | 194 mm | [Annahme] Anteil von ERSTFLUG_HATCH_HW_M |
| Kabel, Schrauben, Kleber | 20.0 g | 520 mm | [Annahme] 20 g |
| **Summe** | **761 g** | | |
