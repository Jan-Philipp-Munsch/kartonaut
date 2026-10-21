# Inventur der Blender-Dateien (Stand 21.10.2026)

Die 16 Blender-Dateien unter `D:\Krams_aktuell_2026-08-16\Krams\Blender\Dateien\` sind die bisherige
CAD-Quelle des Projekts. Sie liegen nicht im Repo. Jede Datei wurde am 21.10.2026 headless mit
Blender 5.2 geöffnet (`cad/tools/blender_inspect.py`, Aufruf in `cad/tools/run_inventory.sh`);
daraus stammen Änderungsdatum, Objektliste, Abmessungen und die Renderbilder `docs/img/cad/blender_<name>.png`.
Alle Dateien sind mit Blender 3.4.6 gespeichert, die Szene steht auf „Metric / Meters“ mit Skala 1,0;
die Zahlen sind trotzdem Millimeter. Keine Datei hat Dichten oder Massen; Materialien gibt es nur als
Fusion-Farbnamen (`color_a0a0a0` usw.) in den importierten BPS-Teilen und als „PLA“ in `Inner_gimbal_V2`.

Das parametrische Modell in `cad/` ersetzt diese Dateien als Quelle. Was daraus übernommen wurde, steht
in `cad/README.md`; die Maße stehen in `cad/params.py` mit dem Hinweis, aus welcher Datei sie stammen.

## 1. Übersicht

Sortiert nach Änderungsdatum. „Stand“ heißt: aktuellster Entwurf dieser Baugruppe (✔), überholt (✘) oder Zwischenstand/unklar (?).

| Datei | Geändert | Baugruppe | Inhalt | Stand | Bild |
|---|---|---|---|---|---|
| `TVC.blend` | 08.03.2025 | Kardan, Gen. 1 | BPS-Import „K-9 TVC Gimbal V7“ (Inner/Outer Gimbal), „BPS Rocket Cradle to K-9 TVC adapter“, 29→24-mm-Adapter (35 × 35 × 100 mm, deutlich größer als nötig). Teile liegen lose nebeneinander. | ✘ durch `dual_tvc` | [Bild](../docs/img/cad/blender_TVC.png) |
| `Inner_gimbal.blend` | 14.03.2025 | Kardan, eigener Innenrahmen | Eigener Innenrahmen (`Circle.002`, 45,7 × 67,5 × 54 mm) neben dem K-9-V7-Innenrahmen als Vorlage; Schraubenloch-Hilfsobjekt. | ✘ | [Bild](../docs/img/cad/blender_Inner_gimbal.png) |
| `flywheel.blend` | 24.03.2025 16:50 | Rollregelung | Schwungrad Ø 60 × 18 mm mit 6 Mutterntaschen (Massen), Nabe Ø 14, Welle Ø 5. | ✘ durch V2 | [Bild](../docs/img/cad/blender_flywheel.png) |
| `flywheelV2.blend` | 24.03.2025 16:58 | Rollregelung | Schwungrad Ø 60 × 14,5 mm, Welle Ø 1,7 mm (Motorwelle), Nabe Ø 14 × 10. Dieses Mesh (1600 Vertices) ist auch das `flywheel` in `flight_computer.blend`. | ✔ Schwungrad | [Bild](../docs/img/cad/blender_flywheelV2.png) |
| `rocket nose.blend` | 26.03.2025 | Spitze (gedruckt) | Spitze Ø 80,3 × 98,9 mm (Hülse über das 75-mm-Rohr, Wand 2,5 mm), federgelagert: Gewindestange M2,5 × 117 mm, Muttern, Scheiben, 4 Federhalter auf r = 28,4 mm, Federn Ø 10 (44 mm entspannt / 20 mm gespannt), Servo 23 × 12 × 24 als Auslöser, Spitze `tip` Ø 12,7 × 25. 26 Objekte, viele ausgeblendet. | ✘ durch Klima-Spitze 8539 (Kunststoff, 230 mm, ca. 100 g, Schulter 72,6 mm) | [Bild](../docs/img/cad/blender_rocket_nose.png) |
| `flight_computer_obj.blend` | 27.04.2025 | Flugcomputer, Ring-Stack | Vier Ringe Ø 69 mm: `battery ring` (6 mm), `teensy ring` (7,5), `sensor ring` (13), `roll ring` (22,9); Bauteile Teensy 4.1, SparkFun ICM-20948 (27 × 27), BMP280, LiPo 56 × 25,5 × 8, DC-Motor Ø 15,8–20,6 × 32, Schwungrad, Summer, LED; `stage bolts` = 8 Stangen Ø 2 auf r ≈ 30,3 mm, `airframe bolts` = 4 Querschrauben. **Alle Ringe liegen bei z ≈ 0 übereinander**, der Stack ist nicht gestapelt modelliert. | ✘ durch `flight_computer` | [Bild](../docs/img/cad/blender_flight_computer_obj.png) |
| `TVC_V2.blend` | 14.05.2025 10:03 | Kardan, Gen. 2 | BPS-Import „K-9 TVC Gimbal Gen 2“: Inner Gimbal 58 × 50 × 44, Motor Tube 32 × 58 (Ø 32, 29-mm-Motor), Outer Gimbal Ø 76 × 50. | ✘ durch `dual_tvc` | [Bild](../docs/img/cad/blender_TVC_V2.png) |
| `Inner_gimbal_V2.blend` | 14.05.2025 14:38 | Kardan, eigener Entwurf V2 | Eigene Teile mit Material „PLA“ und Geometry-Nodes: `inner gimbal` 45,7 × 67,5 × 54, `outer gimbal` 75,5 × 61 × 48,5 (Ring mit 4 Radialbohrungen), `motor mount` Ø 37,7 × 115 (Motorrohr mit zwei Lagerbolzen). Einzige Datei mit Kamera und Lichtern (Präsentationsrender, goldener Hintergrund-Cube). Servos als Klötze mit Hebeln angedeutet. | ✘ durch `dual_tvc` | [Bild](../docs/img/cad/blender_Inner_gimbal_V2.png) |
| `test123.blend` | 11.06.2025 00:27 | Kardan, Zwischenstand | Klotz 39 × 37 × 15 mit zwei Taschen für die BPS-„Throttlepads“, dazu `Throttle housing.002` ausgeblendet. Probestück für das Servogehäuse. | ? | [Bild](../docs/img/cad/blender_test123.png) |
| `dual_tvc.blend` | 11.06.2025 18:17 | Kardan, Gen. 3 (BPS Scout F) | BPS-Scout-F-Import (27 MB): `Outer Gimbal` 63,7 × 66,9 × 47,35, `Inner Gimbal` 46,5 × 55,3 × 48,4, `MotorTube` Ø 33,5 × 52,5 (Innen Ø 28,6), dazu „original“-Kopien. **Servos SG90 (12 × 32 × 24) sitzen unterhalb des Kardans** (z −39 … −7) in `Throttle housing` (54 × 34 × 49, BPS-Teil als Servohalter), darunter Throttle-Pads und ein zweites Motorrohr `FusionComponent.001` 48 × 41 × 91 bei z −193 … −102 für den zweiten Motor (daher „dual“). `Circle` = Rohr Ø 73,2 × 140 (angenommener Rohr-Innendurchmesser 73 mm). | ✔ Kardan-Mechanik (BPS-Prinzip), Servoanordnung ✘ | [Bild](../docs/img/cad/blender_dual_tvc.png) |
| `untitled.blend` | 11.06.2025 18:18 | Kardan, Zwischenstand | Kopie des Innenrahmens mit einem Servo `5600` (22,4 × 8 × 29,5 mm, FrSky-Xact-5600-Reihe) als Tasche. Vorstufe zu `inner_gimbal_dual_TVC`. | ? (überholt durch die beiden folgenden) | [Bild](../docs/img/cad/blender_untitled.png) |
| `outer_gimbal_dual_TVC.blend` | 12.06.2025 22:40 | Kardan, Außenrahmen mit Servotasche | `Outer Gimbal (1).001`: Grundring **Ø 73,0 außen** / Ø 51,3 innen, Flansch 12 mm hoch mit 4 Radialbohrungen; Servotasche bei y = −29 mm, Servo `5600.001` (mit 59 mm langem Hebelklotz) Mitte z = 31,5 mm, Abtriebswelle radial. **Gegenlager gegenüber der Servotasche fehlt** (oberhalb z = 12 mm gibt es nur die Tasche). Boolean-Modifier noch aktiv. Enthält auch `MotorTube.003` (58,6 mm lang) und den Innenrahmen. | ✔ Außenrahmen (unfertig) | [Bild](../docs/img/cad/blender_outer_gimbal_dual_TVC.png) |
| `inner_gimbal_dual_TVC.blend` | 12.06.2025 22:48 | Kardan, Innenrahmen mit Servotasche | `Inner Gimbal.002` (aktuell, dazu `_OLD`, `.001`): Grundring Ø 49,5 außen / Ø 37,2 innen, 12 mm hoch, Gesamthöhe 48,4; Servotasche bei x = +25 mm (Servo `5600`, Mitte z = 31,5, Welle radial), Lagerohr bei x = −24,75 mit Bohrung. | ✔ Innenrahmen | [Bild](../docs/img/cad/blender_inner_gimbal_dual_TVC.png) |
| `model_rocket.blend` | 14.06.2025 11:42 | Gesamtmodell | Siehe §2. | ✔ Gesamtanordnung und Landebeine, Kardan darin ✘ (alte Kopie) | [Bild](../docs/img/cad/blender_model_rocket.png) |
| `LegConnectors.blend` | 14.06.2025 12:15 | Landebeine, Anbindung | Ein Teil: `TopStrut Mount.001` 7 × 21,5 × 16,1 mm, der rumpfseitige Gelenkbock der oberen Strebe (identisch mit den vier in `model_rocket`). Jüngste Datei überhaupt. | ✔ Gelenkbock | [Bild](../docs/img/cad/blender_LegConnectors.png) |
| `flight_computer.blend` | 13.10.2025 | Flugcomputer, Ring-Stack + Akkuplatte | Inhalt von `flight_computer_obj` (alles ausgeblendet) plus Sammlung „Battery 7.4V“: `Battery plate obj` **Ø 73 × 8 mm** (einziges sichtbares Objekt, Boolean-Schnitte, Beschriftung „GND“ / „7.4V“). Render des ganzen Stacks: [blender_flight_computer_stack.png](../docs/img/cad/blender_flight_computer_stack.png). | ✘ durch Schlitten-Platine 54 × 120 (`hardware/mainboard/`) und Einbau im Kuppler | [Bild](../docs/img/cad/blender_flight_computer.png) |

## 2. `model_rocket.blend` im Einzelnen

Sammlungen `body` (16 Objekte) und `landing legs` (32 Objekte), 57 MB. Koordinaten: Rumpfrohr `airframe` Ø 75 × 1000 mm von z = 0 bis 1000, keine Wandstärke (Zylinder ohne Innenfläche).

| Baugruppe | Objekte | Lage (z ab Rohrunterkante) | Vergleich mit den Einzeldateien |
|---|---|---|---|
| Spitze | `rocket cone.001` Ø 80,3 × 98,9 | 990 … 1089 | identisch mit `rocket nose.blend` (5376 Vertices), nur die Außenhülle ohne Federmechanik |
| Kardan | `Outer Gimbal` (22 888 V.), `Inner Gimbal` (40 766 V.), `MotorTube.003` (4670 V.) | 69 … 124 | **Outer/Inner Gimbal sind die Kopien aus `dual_tvc.blend` vom 11.06. (BPS-Original ohne Servotaschen)**, nicht die Fassungen vom 12.06. mit Servotaschen (23 087 bzw. 40 147 V.). Das Motorrohr dagegen ist die neuere 58,6-mm-Fassung vom 12.06. |
| Servos | `SG90.002/.003` | 30 … 62, x = ±21 | ausgeblendet; Anordnung wie in `dual_tvc` unterhalb des Kardans |
| Throttle | `Throttle housing.002`, `Throttlepad l/r` | 15 … 69 | BPS-Teile als Servohalter; `Lower MotorTube` (ausgeblendet) |
| Motoren | `Second stage motor` Ø 29 × 95 bei 26,6 … 121,6; `First stage motor` Ø 29 × 95 bei −95 … −0,4 | | zwei Motoren, der untere ragt ganz aus dem Rohr |
| Landebeine | 4 × `FusionComponent001` (Hauptstrebe 285,6 mm), 4 × `FusionComponent002` (obere Strebe Ø 5 × 323 mm), 4 × `FusionComponent` (Fuß 35 × 35 × 18), 8 × `LegEnd` (Gelenk am Ring), 4 × `TopStrut Mount` | Grundring `Base Extension 1` Ø 82,5 / 77 × 12,5 bei −5,5 … 7; oberer Ring `Airframe Mount.002` r 37,5 … 53 bei 70 … 79; Füße auf r ≈ 320 mm bei z −95 … −77 | ausgefahrener Zustand; `TopStrut Mount` identisch mit `LegConnectors.blend` |
| Ausgeblendet, unklar | `Sphere`/`Sphere.001` (61 × 104 × 72, 65 k Vertices), `Cube` 10 × 120 × 100, `untitled`/`.001` 130 × 56 × 46 (gespiegelt), `damper?` Ø 16 × 100 | 37 … 174 | vermutlich Versuche für Beindämpfer und eine Verkleidung; nicht weiterverfolgt |

Nicht enthalten: Flugcomputer, Akkus, Fallschirm, Kolben-Ausstoß, Kuppler, Rohr-Wandstärke.

## 3. Befunde

1. **Jüngster Stand je Baugruppe:** Kardan-Mechanik aus `dual_tvc` (BPS-Scout-F-Geometrie), Rahmen mit Servotaschen aus `inner_gimbal_dual_TVC` / `outer_gimbal_dual_TVC` (12.06.2025), Landebeine aus `model_rocket` + `LegConnectors` (14.06.2025), Schwungrad `flywheelV2`, Flugcomputer `flight_computer` (13.10.2025, Akkuplatte).
2. **`model_rocket.blend` ist kein zusammengeführter Stand.** Der Kardan darin ist die Kopie vom 11.06. ohne Servotaschen, das Motorrohr die vom 12.06.; Servos liegen ausgeblendet unterhalb des Kardans. Spitze und Beine sind aktuell. Flugcomputer fehlt ganz.
3. **Überholt durch die Entscheidungen vom 21.10.2026:** `rocket nose` (Klima-Spitze 8539 ersetzt die federgelagerte Druckspitze), `TVC`, `TVC_V2`, `Inner_gimbal`, `Inner_gimbal_V2` (drei frühere Kardan-Generationen), die SG90-Anordnung in `dual_tvc`/`model_rocket` (Servos werden FrSky W5652H in den Rahmenwänden), der Ring-Stack mit vier Ringen und die Ø-73-Akkuplatte in `flight_computer` (Schlitten-Platine 54 × 120 im Kuppler), die Throttle-Teile (kein Mechanismus der Entscheidungsliste), das zweite Motorrohr (Erstflug mit einem Motor).
4. **Maßkonflikte mit den gekauften Teilen:** Das Blender-Rohr hat keine Wandstärke, der angenommene Innendurchmesser war 73,0–73,2 mm (Außenrahmen Ø 73,0, Hilfsrohr Ø 73,2, Akkuplatte Ø 73). Real: Rohr innen 72,6 mm, Kuppler innen 70,2 mm. Außenrahmen und Akkuplatte passen so nicht; im parametrischen Modell ist der Außenrahmen auf 72,2 mm gesetzt, die Flugcomputer-Ringe auf 69 mm (im Kuppler). Der Beinring `Base Extension 1` hat 77 mm Innendurchmesser (2 mm Luft um das Rohr); im Modell 75,2 mm.
5. **Unfertig:** Der Außenrahmen vom 12.06. hat nur die Servotasche, kein Gegenlager auf der Gegenseite. Das parametrische Modell ergänzt das Lagerohr spiegelbildlich zum Innenrahmen.
6. **Das Servo `5600` in den Juni-Dateien ist die FrSky-Xact-5600-Reihe** (22,4 × 8 × 29,5 mm mit Laschen). Die Taschen sind also schon für ein 8 mm dünnes Flächenservo mit radialer Abtriebswelle ausgelegt; der W5652H (19 × 8 × 23 mm) ist etwas kleiner. Die Taschenmaße sind in `cad/params.py` Parameter.
7. **Landebeine:** Hauptstrebe (285 mm) am Grundring, obere Strebe (323 mm) am Ring 70 mm darüber, beide treffen sich am Fuß. Mit festen Längen lässt sich das nicht einklappen (eingeklappt bräuchte die obere Strebe ≈ 218 mm). Wie das Einklappen gedacht war (Teleskop, Feder, `damper?`), ist aus den Dateien nicht ersichtlich.
8. **Was fehlt in Blender komplett:** Kuppler, Kolben-Ausstoß, Fallschirmraum, Kabelführung, Luke, Akku-Zugang. Das parametrische Modell legt diese Teile nach den Entscheidungen vom 21.10.2026 neu an und kennzeichnet sie als Annahmen.

## 4. Was am Gerät nachzumessen ist

- Rohr-Innendurchmesser (72,6 laut Klima) und Kuppler-Außendurchmesser: Shop 72,6 mm, `docs/BUILD.md` 72,4 mm.
- Schulterlänge der Klima-Spitze 8539 (im Modell 75 mm angenommen) und ihre tatsächliche Masse (Shop: ca. 100 g).
- Ob die gedruckten Kardanteile aus `dual_tvc` existieren und welche Fassung (mit/ohne Servotaschen).
- Lage und Länge der Abtriebswelle am W5652H (Datenblatt), davon hängt die Pivot-Höhe im Rahmen ab.
- Beinlängen und Gelenkabstände, falls Beine gedruckt wurden.
