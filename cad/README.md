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
python cad/mass_model.py                    # mass_properties.md und .json neu schreiben (alle Varianten)
python cad/build.py --config erstflug       # Erstflug-Konfiguration (22.10.2026), Rohr 700 mm
python cad/build.py --config erstflug --tube-l 665   # kürzestes Rohr (Minimum steht in params.TUBE_MIN)
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
| `ejection.py` | Kolben (Kuppler-Stück mit Platte und Öse), Fallschirm als Platzhalter; Gasraum 11 mm (war 5, die Ladungsschale ragte in die Kolbenplatte) |
| `legs.py` | Hülse am Rohrende, Ring 70 mm darüber, vier Beine mit Haupt- und oberer Strebe, Fuß, Gelenke |
| `testrig.py` | TVC-Prüfstand: Gestell, Rahmen, Klemmkragen, Prop-Adapter mit BR2814 und Propeller, Schutzkäfig (siehe unten) |
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

## Konfigurationen (22.10.2026): `voll` und `erstflug`

`params.py` kennt zwei Konfigurationen, gewählt über die Umgebungsvariable `MS_CONFIG` (von `build.py --config`
gesetzt, Vorgabe `voll`) und optional `MS_TUBE_L`. Die abgeleiteten Längen (Rohrstoß, Kuppler, Platine, Kolben,
Schirm, Spitze, Gesamtlänge) liefert `params.layout(config, tube_total)`; `mass_model.py` nutzt diese Funktion
und rechnet alle Varianten in einem Lauf, ohne die Umgebungsvariable.

| | `voll` (Stand 21.10.) | `erstflug` (Entscheidung Jan 22.10.) |
|---|---|---|
| Rohr | 2 × 500 mm, Stoß bei z = 520 | 700 mm (Minimum 665): unteres Rohr 131 mm, oberes Rest, Stoß bei z = 151 |
| Kuppler | zentriert um den Stoß (75 / 75) | 25 mm im unteren Rohr, 125 mm im oberen |
| Landebeine | ja (200 g) | nein |
| 2S-Akku / Platine | 45 g / 40 g | 30 g (450 mAh) / 45 g (Mainboard mit Teensy) |
| Luken | eine USB-Luke (+y) | Luke A (+y) und Luke B (−y), Schlüsselschalter-Kragen |
| Start | 981 g | 719 g (700 mm), 711 g (665 mm) |

Der Prüfstand (`rig=True`) und die Bilder der Gesamtübersicht gehören zu `voll`; `build.py --config erstflug` schreibt
`export/erstflug/*` und `export/rocket_erstflug.step` und rendert `rocket_erstflug_*.png` und `hatches_*.png`.
Dazu prüft es, ob die Luken frei sind, die Steckerräume leer bleiben und die Kolbenbohrung frei ist.

### Luken im Flugcomputer-Kuppler (Erstflug)

| Luke A, +y, Bestückungsseite | Luke B, −y, Schalterbrett |
|---|---|
| ![](../docs/img/cad/hatches_a_iso.png) | ![](../docs/img/cad/hatches_b_iso.png) |

Die M2-Stangen stehen bei (±7, ±29,5) und (±29,5, ±7); zwischen zwei Stangen eines Paars bleiben 12 mm frei.
Beide Luken sind deshalb 12 mm breit und liegen bei ±y (u = 0). Sie liegen im oberen Rohr, der Rohrstoß (25 mm über der
Kupplerunterkante) kreuzt sie nicht. Lage der Schrauben: drei M2 bei 45°, 135°, 225° im oberen Rohr, damit der Kuppler nur in
einer Drehung passt und die Luken zu den Fenstern im Rohr stehen.

- **Luke A (Teensy):** v = 25 … 100 mm (z = Platinenanfang + 25 … 100), Micro-USB, Programmiertaste und SD-Slot des
  Teensy. 21 mm Luft von der Teensy-Oberseite bis zur Kupplerwand für Stecker und Karte; Steckerräume (USB-Stecker 11 mm,
  SD-Karte 11 mm breit) sind frei.
- **Luke B (Schalterbrett):** v = 24 … 90 mm. Ein 11 mm breites Brett (gedruckt oder Leiterplatte) sitzt zwischen den Stangen
  bei y = −33,1 … −31,1 auf zwei Stützen am Trägerboden; die Bauteile in einer Reihe von unten (TVC) nach oben: Schiebeschalter
  2-polig (v 28–40), USB-C-Buchse (44–53) mit LED (56–59), XT30-Buchse (61–71), XH-3-Buchse für den Balancer (76–83,5). Sie sind
  über Kabel mit der Platine verbunden (`J_SW`, USB-C-Lader, `J_BAT2`-Parallelanschluss). Sie liegen frei von Stangen, Akkus
  (die 2S/1S-Akkus liegen bei y > −10,8, Trägerboden bei −14,5), Träger und Platine, jeder Stecker hat 1,5 mm Luft ringsum.
- **Schlüsselschalter passt nicht in Luke B** (Körper Ø 12 gegen 12 mm Stangenlücke, dazu 15 mm Einbautiefe). Er sitzt in einem
  gedruckten **Kragen** im unteren Rohr direkt unter dem Kuppler (z = 106 … 124, 3 mm über dem Kardan), radial nach +x, durch eine
  Bohrung Ø 12,4 im unteren Rohr. Das kostet 20 mm Rohrlänge (der Kuppler beginnt bei z = 126), das Modul wird weiter nach oben
  herausgezogen, der Kragen bleibt im Rohr; Kabel zur Platine über Steckverbinder.

## Prüfstand (`testrig.py`, 21.10.2026)

| Rakete im Gestell, 12° genickt, 8° gegiert | Antriebsende: Prop-Adapter, BR2814, Propeller, Schutzkäfig |
|---|---|
| ![](../docs/img/cad/testrig.png) | ![](../docs/img/cad/testrig_drive.png) |

Die Rakete hängt in einem zweiachsigen Gestell mit Drehpunkt im Schwerpunkt (`RIG_PIVOT_Z`, aus dem
Massenmodell, nach dem Auswiegen setzen) und bekommt ihren Schub von einem Propellermotor im Kardan:

- **Gestell:** Sperrholzplatte 820 × 500, zwei Alu-Stützen 40 × 40 bei x = ±350 mit je drei Streben,
  Kugellager 608 in Höhe des Drehpunkts (800 mm über dem Boden), zwei Achsstummel Ø 8.
- **Rahmen:** Rechteck aus Alu-Profil 20 × 20 (innen 116 × 135 mm), auf den Stummeln geklemmt, nickt
  um x. Auf den y-Stäben zwei gedruckte Lagerböcke mit 608-Lagern.
- **Klemmkragen:** gedruckt, zweiteilig (Teilung x = 0), Ø 95 × 40 um das Rohr, Ohren an ±y mit je
  zwei M4; der Zapfen Ø 8 liegt in der Teilung und wird mitgeklemmt. Die Rakete giert damit um y,
  Rollen ist gesperrt (das Reaktionsmoment des Propellers geht in den Kragen).
- **Antrieb:** Adapter mit Ø-29-Zapfen im Motorrohr (die Klemmschraube greift wie beim E12-Adapter)
  und Flansch Ø 44 mit M3-Kreuz 16/19 unter dem Motorrohr; daran der BR2814 mit Welle nach unten,
  Propeller 12 × 6 (oder 11 × 7) unter der Rohrunterkante. Der Schubvektor läuft durch den
  Kardanpunkt, der Kardan lenkt ihn wie im Flug; `build_all(rig=True)` tauscht Adapter und E12 gegen
  diese drei Teile (`tvc.build(..., motor_kind="prop")`).
- **Schutzkäfig:** zwei Ringe Ø 337 aus 8-mm-Rohr, zwölf Stäbe, vier Speichen zu einem zweiteiligen
  Klemmring am Rohr über dem Außenrahmen-Flansch. Sitzt an der Rakete, schwenkt mit; die
  Propellerspitze hat 12 mm radiales Spiel und steigt bei 10° Kardanneigung bis z = 24 mm, der obere
  Ring liegt bei z = 40.
- **Auslenkung:** ±20° je Rig-Achse (`RIG_TILT_MAX_DEG`), begrenzt per Gurt zwischen Rohr und Rahmen
  (nicht modelliert). `build.py` prüft bei ±20° Nicken und Gieren und ±7° Kardan, dass Propeller,
  Käfig, Rohr, Spitze und Kragen weder Gestell, Rahmen noch Achsstummel berühren, und dass der
  Propeller frei vom Käfig bleibt; der Propeller reicht bei 20° Gieren bis x = 304 (Stützen bei 350).

Export: `cad/export/testrig.step` (Gestell mit Rakete, im Repo) und `testrig.stl` (nur Gestell).
Nicht modelliert: Kabel (ESC und 4S-Akku sitzen als Klotz auf dem Rahmen), Gurt-Anschläge, Schrauben.
Maße des BR2814 (Ø 35 × 36, Lochkreuz 16/19, 75 g) sind Annahmen für einen 2814-Außenläufer und am
Teil nachzumessen; danach `PM_*` in `params.py` anpassen. Der Schwerpunkt verschiebt sich gegenüber
dem Flugzustand (kein E12, dafür Motor, Propeller und Käfig unten), deshalb vor dem Einbau auswiegen.

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
6. Prüfstand: Gurt-Anschläge, Kabelführung vom ESC zum Motor über den Kragen, Gas-Ausgang in der Firmware; BR2814 nachmessen.
