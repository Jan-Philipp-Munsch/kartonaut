# CAD-Modell der Rakete (parametrisch, CadQuery)

Angelegt am 21.10.2026. Das Modell ersetzt die Blender-Dateien als Konstruktionsquelle; was aus ihnen
übernommen wurde, steht in [`blender_inventory.md`](blender_inventory.md). Alle Maße stehen in
[`params.py`](params.py), jede Zahl mit Quelle (`[Klima]`, `[BUILD]`, `[Blender]`, `[HW]`, `[Annahme]`,
`[Vorgabe]`). Das Massenmodell in [`mass_properties.md`](mass_properties.md) /
[`mass_properties.json`](mass_properties.json) rechnet mit denselben Parametern.

| Gesamtansicht | Schnitt (Beine eingeklappt) | Kardan mit W5652H, 5°/4° ausgelenkt | Flugcomputer-Modul |
|---|---|---|---|
| ![](../docs/img/cad/rocket_overall.png) | ![](../docs/img/cad/rocket_section.png) | ![](../docs/img/cad/rocket_tvc.png) | ![](../docs/img/cad/rocket_avionics.png) |

## Bauen

```bash
python -m pip install --user cadquery      # einmalig (CadQuery 2.8, Python 3.13 funktioniert)
python cad/build.py                         # STEP/STL nach cad/export/, Bilder nach docs/img/cad/
python cad/build.py --no-render             # ohne Blender
python cad/mass_model.py                    # mass_properties.md und .json neu schreiben
```

`build.py` baut die Geometrie (54 Teile, 2 s), exportiert je Baugruppe `export/<gruppe>.step` und `.stl`
sowie `export/rocket.step` (Gesamtmodell mit Farben, das einzige Export-Artefakt im Repo), prüft dann
Durchdringungen des Kardans bei ±`GIMBAL_MAX_DEG` und ruft Blender headless auf
(`tools/render_parts.py`, Pfad in `build.py` oder Umgebungsvariable `BLENDER`). Ohne Blender entfallen
nur die Bilder.

## Struktur

| Datei | Inhalt |
|---|---|
| `params.py` | alle Maße und Massen, Koordinatenkonvention |
| `common.py` | Helfer (Rohr, Zylinder zwischen Punkten, Quader, Rotation, Radialbohrungen), Teileliste |
| `airframe.py` | zwei Klima-Rohre 75 × 500, Luke, Klima-Spitze 8539 mit Schulterkuppler und Spant |
| `tvc.py` | Außenrahmen, Innenrahmen, Motorrohr, Adapter 29→24, Motor E12, zwei W5652H mit Hebelscheiben |
| `avionics.py` | Flugcomputer-Kuppler: Endringe, 8 × M2-Stangen, Träger, Platine 54 × 120 mit Teensy, Akkus 2S/1S, obere Endplatte = Spant mit Ladungsschale |
| `ejection.py` | Kolben (Kuppler-Stück mit Platte und Öse), Fallschirm als Platzhalter |
| `legs.py` | Hülse am Rohrende, Ring 70 mm darüber, vier Beine mit Haupt- und oberer Strebe, Fuß, Gelenke |
| `build.py` | Zusammenbau, Export, Kollisionsprüfung, Render-Aufrufe |
| `mass_model.py` | Stabmodell für Schwerpunkt und Trägheitstensor |
| `tools/` | Blender-Skripte: Inventur (`blender_inspect.py`, `run_inventory.sh`), Ortho-Ansichten und Radialmaße (`blender_views.py`), Renderer für den Build (`render_parts.py`) |

Koordinaten wie in der Firmware: z ist die Längsachse, z = 0 die Düsenebene, +z zur Spitze. x zeigt zum
Servo des Innenrahmens (Motorrohr kippt um x), y zum Lagerohr des Außenrahmens (Innenrahmen kippt um y).
Welche davon Pitch und welche Yaw ist, muss mit `Config.h` abgeglichen werden.

## Aufbau von unten nach oben (z in mm ab Düse)

| z | Was |
|---|---|
| 0 … 95 | Motor TSP E12-0 im Adapter 29→24 (Adapter 10 … 95), Motorrohr 45 … 103 |
| 20 | Unterkante des unteren Rohrs; Beinhülse 14,5 … 27 |
| 45 … 93 | Außenrahmen (Flansch 45 … 57 mit 4 × M3 durch das Rohr), Innenrahmen, Kardanpunkt bei **76,5** |
| 90 … 99 | oberer Beinring mit vier Gelenkböcken |
| 445 … 595 | Flugcomputer-Kuppler, symmetrisch um den Rohrstoß bei 520; Platine 455 … 575, Teensy 485 … 546 |
| 544 … 560 | Luke 16 mm breit auf +y über dem USB-Stecker (im oberen Rohr, 24 mm über dem Stoß) |
| 595 | obere Endplatte = fester Spant mit Ladungsschale, E-Match-Bohrungen und Öse |
| 600 … 640 | Kolben |
| 645 … 875 | Fallschirm |
| 945 … 1020 | Schulter der Spitze (lose), 1020 … 1250 Spitze |

## Wartung und Montage, wie das Modell es vorsieht

- **Flugcomputer als Modul:** vier M2-Schrauben oben lösen, oberes Rohr abziehen, Modul am oberen
  Ring aus dem unteren Rohr ziehen. Kuppler, Endringe, Stangen, Träger, Platine und beide Akkus bleiben
  eine Einheit. Die Akkus liegen in der Trägerwanne unter der Platine und sind nach dem Herausziehen
  von der Seite zugänglich (Aussparung in den Längswänden).
- **Luke:** nur über dem USB-Stecker (`HATCH_V`). Eine Luke für die SD-Karte läge 35 bis 41 mm unter
  dem Rohrstoß im unteren Rohr; `HATCH_SD = True` schneidet sie zusätzlich. Eine gemeinsame Luke für
  beide würde den Rohrstoß kreuzen, deshalb nicht vorgesehen. Alternative: Platine um 180° einbauen
  (USB zum TVC), dann liegt die USB-Luke im unteren Rohr; das legt `hardware/mainboard/` fest.
- **Kardan:** Servos von außen in die Taschen setzen, bevor der Außenrahmen ins Rohr kommt. Der
  Außenrahmen sitzt mit vier M3 radial im Rohr (Flansch 25 mm über der Rohrunterkante). Motor von unten
  in den Adapter, Adapter im Motorrohr geklemmt.
- **Bergung:** Ladung in der Schale auf der Endplatte, Kolben darüber, Schockschnur von der Öse der
  Endplatte über die Kolben-Öse zur Spitze. Die Spitze sitzt lose (Schulter 72,4 statt 72,6).

## Was gegenüber Blender geändert ist (alles Parameter in `params.py`)

| Parameter | Blender | Modell | Grund |
|---|---|---|---|
| `OUTER_RING_OD` | 73,0 | 72,2 | Rohr innen 72,6 |
| `OUTER_RING_ID` | 51,3 | 58,3 | aus `GIMBAL_MAX_DEG` = 7°: bei 31,5 mm Hebel zur Ring-Unterkante braucht jeder Ring 4,4 mm radiales Spiel; Blender hatte 0,9 mm (1,6°) |
| `INNER_RING_ID` | 37,2 | 42,3 | dito, Blender 1,85 mm (3,4°) |
| `MOTOR_TUBE_ID` | 28,6 | 29,2 | 29-mm-Adapter |
| `SERVO_*` | „5600“ 22,4 × 8 × 29,5 | W5652H 23 × 19 × 8 | neues Servo; Welle liegt auf der Rahmenachse, Gehäuse um `SERVO_SHAFT_OFFSET` versetzt |
| `SERVO_OUTER_R`, `SERVO_INNER_R` | 29 / 25 | 30,9 / 23,5 | aus Ringmaßen und Wandstärken abgeleitet |
| Lagerohr am Außenrahmen | fehlt | ergänzt | Gegenlager zur Servowelle, spiegelbildlich zum Innenrahmen |
| `INNER_HOUSING_Z0`, `INNER_ENVELOPE_R` | – | 17 mm, 33,5 mm | Servogehäuse des Innenrahmens darf beim Kippen weder Außenflansch noch Rohr berühren |
| `ADAPTER_*` | Ø 35 × 100 | Ø 29 × 85 | wie ein 29-mm-Motor |
| `LEG_SLEEVE_ID`, `LEG_UPPER_RING_ID` | 77 / 75 | 75,2 | Spiel zum Rohr |
| Spitze | gedruckt, Ø 80, federgelagert | Klima 8539, Ogive als Spline geschätzt | Kaufteil |
| Servos SG90 unter dem Kardan, Throttle-Teile, zweites Motorrohr | vorhanden | nicht übernommen | Entscheidungen 21.10.2026 |
| Flugcomputer | Ring-Stack, Ø-73-Akkuplatte | Schlitten im Kuppler, Ringe Ø 69 | `hardware/mainboard/` |

Die Landebeine sind geometrisch wie in Blender (ausgefahren: Fuß auf r ≈ 320 mm). Eingeklappt wird nur
die Hauptstrebe senkrecht gestellt; die obere Strebe passt mit fester Länge nicht (eingeklappt bräuchte
sie 218 statt 320 mm). Der Einklappmechanismus ist offen, siehe Inventur §3.7.

## Annahmen, am Gerät nachzumessen

- Rohrunterkante 20 mm über der Düse (`TUBE_BOTTOM_Z`), Außenrahmen 25 mm darüber: beides frei gewählt,
  ergibt den Kardanpunkt bei 76,5 mm und den Hebelarm 0,37 m. Verschiebt sich der Rahmen, ändert sich
  der Hebelarm direkt.
- Kardanpunkt 31,5 mm über der Rahmen-Grundfläche (Servomitte in Blender). Lage der Abtriebswelle am
  W5652H (`SERVO_SHAFT_OFFSET`, 5 mm aus der Mitte) und welche Seite 19 bzw. 23 mm ist: Datenblatt.
- Kuppler außen 72,4 (BUILD.md) oder 72,6 (Klima-Shop); Schulterlänge und Masse der Spitze.
- Treibsatzlage im E12 (z = 10 … 60 mm), Masse der gedruckten Teile, Landesystem 200 g ohne Konstruktion.
- Flugcomputer 100 g gesamt, hier als 40 g Platine, 25 g Endringe/Platte, 20 g Stangen, 15 g Träger.
- Fallschirm gepackt Ø 60 × 230 mm; Kolbenlänge 40 mm; Ladungsschale Ø 12 × 8.
- Rohr-Innendurchmesser 72,6 (Klima): davon hängen Außenrahmen, Beinringe und Kolben ab.

## Offen

1. Pitch/Yaw-Zuordnung der beiden Servos zu `Config.h` und zur Platinenlage (`chipToBody`).
2. Einklappmechanismus der Beine und ihre Verriegelung im Flug.
3. Servo-Datenblatt W5652H: Wellenlage, Laschenabstand, Schraubenmaß; dann `tvc.py` Taschen prüfen.
4. Ob die Ringe mit 4,4 mm Spiel noch genug Führung haben, oder ob der Innenrahmen tiefer hängen soll
   (kleinerer Hebel zur Ring-Unterkante, weniger Spiel nötig).
5. Druckausgleichsbohrungen für das Barometer (3 bis 4 × Ø 2 auf Höhe v ≈ 80, `hardware/mainboard/README.md`) fehlen im Modell.
