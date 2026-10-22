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
| `landingpad.py` | Start- und Landepad: Deck, Strahlplatte, Startstützen, Zündkasten; Prüfung gegen die Rakete, eigener Export und Bilder (siehe unten) |
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
einer Drehung passt und die Luken zu den Fenstern im Rohr stehen. Drei weitere M2 auf halber Steckhöhe im unteren Rohr: ohne sie
hinge das untere Rohr (Kardan und Motor, ca. 150 g) nur mit 25 mm Reibung am Kuppler und fiele beim Öffnen des Schirms ab.

Wartung im Erstflug-Aufbau: die drei unteren M2 lösen, das Kabel zum Schlüsselschalter-Kragen am Stecker trennen, unteres Rohr mit
Kardan abziehen; das Modul bleibt mit dem Kuppler am oberen Rohr. Erst nach dem Lösen der oberen drei M2 kommt es nach unten heraus.

- **Luke A (Teensy):** v = 25 … 115 mm (z = Platinenanfang + 25 … 115), Micro-USB, Programmiertaste und SD-Slot des
  Teensy. Die Micro-USB-Buchse zeigt in Längsrichtung (+v) und endet bei v = 92,5; ein gerader Stecker mit Knickschutz reicht
  bis v ≈ 113, deshalb geht die Luke bis 115 (bis zur Prüfung am 22.10. nachmittags endete sie bei 100, dann ging nur ein
  Winkelstecker). 21 mm Luft von der Teensy-Oberseite bis zur Kupplerwand. Der SD-Slot des Teensy 4.1 sitzt **auf der Unterseite**
  am USB-fernen Ende (im Modell vereinfacht oben); die Karte wird bei v ≈ 28 längs herausgezogen, zwischen Teensy und Platine,
  mit Pinzette durch den Lukenanfang bei v = 25. Steckerräume (USB-Stecker und SD-Karte je 11 mm breit) sind frei.
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

## Start- und Landepad (`landingpad.py`, 22.10.2026)

| Start (Erstflug, Aufbauzustand: Shunt steckt) | Stützen und Zündkasten |
|---|---|
| ![](../docs/img/cad/landingpad.png) | ![](../docs/img/cad/landingpad_detail.png) |
| **Schnitt y = 0 durch die Stütze mit Zündkasten** | **Landung (voll, Beine ausgefahren), Stützen abgenommen** |
| ![](../docs/img/cad/landingpad_section.png) | ![](../docs/img/cad/landingpad_landing.png) |

Anforderungen: [`docs/Schnittstellen_Bodensystem_2026-10-22.md`](../docs/Schnittstellen_Bodensystem_2026-10-22.md), S1 und S2.
`python cad/landingpad.py` baut das Pad in den Koordinaten der Rakete (z = 0 Düse), prüft es gegen die Rakete aus
`build.build_all()` (Erstflug mit Kardan ±7°/±7°, Abheben bis 200 mm, voll mit ausgefahrenen Beinen auf dem Deck), schreibt
`export/landingpad.step` (Pad mit Erstflug-Rakete) und rendert die vier Bilder (`--no-render` ohne Blender). Laufzeit 1 min.
Das Modul schaltet `params` zur Laufzeit zwischen `erstflug` und `voll` um (`use_config`), ohne die Umgebungsvariable.

**Aufbau** (Maße oben in `landingpad.py`, jede Zahl mit Quelle):

- **Deck:** Achteck 1250 mm über die Flächen (Inkreis Ø 1250 ≥ 1200), Siebdruckplatte 18 mm in zwei Hälften 1250 × 625
  (Teilung y = 0), oben verzinktes Stahlblech 0,75 mm als nicht brennbare Fläche, verklebt, am Rand Senkschrauben. Darunter
  zwei Kanthölzer 45 × 70 (flach) bei x = ±250 quer zur Teilung, mit M8 von unten in Einschlagmuttern: sie verbinden die Hälften.
  Drei Fußklötze mit Stellfüßen M10 auf r = 540 bei 90°/210°/330°: drei Punkte kippeln nicht. Dosenlibelle Ø 40 bündig bei 135°.
  Deckoberkante 100 mm unter der Düse, 204 mm über dem Boden.
- **Strahlplatte:** Einsatz in einer Aussparung 320 × 320 über der Teilung: Stahl 2 mm auf Zementfaserplatte 16 mm, darunter
  Trägerplatte Zementfaser 400 × 400 × 12, von unten mit 4 × M6 an beiden Hälften. Oberkante 0,75 mm unter dem Deckblech,
  **Düse 100,75 mm darüber** (bei 7° Kardan 99,8; gefordert ≥ 80). Der Strahl trifft senkrecht auf und läuft flach nach allen
  Seiten ab; zwischen den drei Stützen ist es offen (seitlicher Abzug 360° bis auf drei Fußplatten 50 mm breit).
- **Startstützen (drei, abnehmbar):** bei 60°, 180°, 300°, also nicht vor dem Schlüsselschalter (+x) und den Luken (±y).
  Je eine Fußplatte Alu 50 × 5 mit zwei Langlöchern für M6 in Einschlagmuttern (radial ±5 mm einstellbar), ein Vierkantrohr
  20 × 20 × 1,5 als **Führung, 160 mm über der Rohrunterkante, 1,5 mm Luft** zum Rohr, oben innen angefast, ein Knotenblech
  Alu 5 mm und ein **Auflage-Klotz** 20 × 5 × 10 innen am Rohr, Oberkante z = 20 unter der Ringfläche (r 34 … 39 deckt
  36,3 … 37,5). Die Rakete steht nur auf den Auflagen und hebt ohne Klemmung ab. Unter der Rohrunterkante liegt kein Teil
  innerhalb r = 30 (innerste Kante r = 34; Ausnahme: das biegsame Anzünderkabel). Einstellen mit einem gedruckten Ring Ø 78
  (Lehre = Rohr + 2 × 1,5) statt der Rakete: Stützen anlegen, M6 festziehen, Lehre nach oben abziehen.
- **Zündkasten** auf der verlängerten Fußplatte der Stütze bei 180°, geht mit ihr ab: Abzweigkasten 100 × 100 × 55, außen zwei
  XT30-Buchsen nebeneinander: **LEITUNG** (Stecker der 15-m-Zündleitung, S2) und **SHUNT** (gebrückter XT30-Stecker mit Fahne
  REMOVE BEFORE FLIGHT). Beide Buchsen liegen parallel am Anzünder; verwechselt man sie, passiert nichts. Oben zwei Polklemmen
  4 mm für das 30-cm-Kabel mit Krokoklemmen zum Anzünder, vorn zur Düse ein Hitzeschild Stahl 1 mm. Litze 1,5 mm² im Kasten.

**Prüfungen** (alle frei, Stand 22.10.): Rakete Erstflug bei Kardan 0° und allen vier Ecken ±7°/±7° gegen jedes Padteil;
Düsenabstand; Kardan-Freiraum (Zylinder r = 30 von der Strahlplatte bis z = 20); Auflagen auf z = 20 und über der Ringfläche,
Luft der Führungen (gemessen 1,50 mm, Grenze 1 … 2) und Höhe ≥ 150; Abheben in Schritten bis 200 mm gegen die Stützen;
Landung `voll` mit Fußsohle auf dem Deck (Düse dann 86 mm darüber, nicht 70 wie in S1 geschätzt) bei Versatz 0 und 150 mm;
nichts in der Landekonfiguration über dem Deckblech; Füße bis r = 337, also **263 mm Landeversatz** innerhalb Ø 1200
(288 mm bis zum Rand). Ein Gegentest (Rakete 5 mm tiefer bzw. 3 mm seitlich) meldet Auflagen und Führungen.

**Stückliste** (Massen aus dem Modell mit Dichten [Annahme], Preise grob, Baumarkt/Online Oktober 2026 [Annahme]):

| Teil | Masse | Preis |
|---|---|---|
| Siebdruckplatte 18 mm, Zuschnitt 1250 × 1250, als zwei Achteck-Hälften | 2 × 7,3 kg | 45 € |
| Stahlblech verzinkt 0,75 mm, 2 × 1250 × 625 (Metallhandel) | 2 × 3,5 kg | 50 € |
| Kantholz 45 × 70, 3 m: zwei Latten 1160, drei Fußklötze 120 × 120; drei Stellfüße M10 mit Gelenkteller | 4,5 kg | 21 € |
| Einschlagmuttern M10/M8/M6, M8 × 70, M6 × 30 mit Rändelkopf, Senkschrauben | – | 15 € |
| Strahlplatten-Einsatz: Stahl 2 mm 316², Zementfaser 16 mm 316², Träger Zementfaser 12 mm 400² | 6,3 kg | 35 € |
| drei Stützen: Alu-Vierkantrohr 20 × 20 × 1,5 (1 m), Alu-Flach 50 × 5 (1 m), Alu 20 × 10 (Auflagen) | 0,86 kg | 26 € |
| Zündkasten: Abzweigkasten IP54, 2 × XT30-Buchse, 2 × XT30-Stecker (einer als Shunt), Polklemmen, Krokokabel, Fahne, Hitzeschild | 0,3 kg | 27 € |
| Dosenlibelle Ø 40; Druckteile PETG (Lehre Ø 78, XT30-Halter, Libellenfassung), ca. 60 g | – | 8 € |
| **gesamt** | **33,6 kg** | **ca. 230 €** |

**Transport:** zwei Deckhälften 1250 × 625 × 23 mm mit Fußklötzen (je ca. 11 kg), zwei Latten 1160 mm, Strahlplatten-Einsatz
400 × 400 (6 kg), drei Stützen, Stellfüße abgeschraubt. Passt in einen Kombi oder Kompaktwagen mit umgelegter Rückbank.
Aufbau: Hälften umgedreht auf den Boden, Latten und Einsatz anschrauben, umdrehen, Stellfüße nach der Libelle einstellen, Stützen
mit der Lehre setzen, Zündkasten an der Stütze 180° prüfen.

**Sicherheit:**
- Shunt-Stecker steckt, solange jemand am Pad ist. Reihenfolge: Bodenstation ohne Schlüssel, Zündleitung an LEITUNG,
  Anzünder einsetzen und an die Polklemmen, Rakete scharf schalten, **zuletzt Shunt ziehen** und mit der Fahne mitnehmen, dann
  zur Station (≥ 10 m, Leitung 15 m). Bei Abbruch: Schlüssel ziehen, 60 s warten, Shunt wieder stecken, erst dann Anzünder lösen.
- Der Shunt schließt den Anzünder kurz; die Durchgangsprüfung der Station (≤ 10 mA, S2) sieht dann ebenfalls Durchgang. Die
  Station kann Shunt und Anzünder nur am Widerstand unterscheiden (Anzünder etwa 1 Ω, Shunt ≈ 0): Hinweis an `groundstation/`.
- Pad auf festem, ebenem, nicht brennbarem Untergrund (kein trockenes Gras im Umkreis von 2 m), Feuerlöscher oder Wasser bereit.
  Deckrand nicht betreten: drei Füße auf r = 540, außerhalb davon kippt die Platte.
- Verzinktes Blech nicht über 200 °C bringen (Zinkdampf); die Strahlplatte im Strahl ist deshalb unverzinkter Stahl.

**Offen:** Schraubbild der Stützen und Einschlagmuttern im Deck sind nur als Langlöcher in den Fußplatten modelliert, Schrauben
und Muttern fehlen. Steifigkeit der Stütze mit 2 × M6 in 18 mm Sperrholz am Muster prüfen (Wind auf die Rakete ca. 5 N bei 10 m/s
[Annahme]). Hitzefestigkeit der Zementfaserplatte unter 3 s Strahl und die Temperatur der Alu-Auflagen (10 mm über der Düse,
seitlich vom Strahl) beim ersten Abbrand prüfen. Bei der Landung mit brennendem Motor trifft der Strahl auch das verzinkte
Deckblech, wenn die Rakete außerhalb der Strahlplatte aufsetzt. `export/landingpad.step` ist in `.gitignore` nicht freigegeben.

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
