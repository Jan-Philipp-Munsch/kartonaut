# Bergung *Kartonaut 1*: Fallschirm, Schnüre, Packen, Passproben

Stand 2026-10-22. Gilt für die Erstflug-Konfiguration (`cad/params.py`, `config="erstflug"`):
Rohr 700 mm, Klima-Spitze 8539 lose aufgesteckt, Fallschirm in der Spitze bzw. im Fallschirmraum
darunter, Ausstoß über einen Kolben aus einem Kupplerstück (`cad/ejection.py`). Rechnungen:
`simulation/scripts/recovery.py`, Auslösezeitpunkt aus dem Software-in-the-Loop
(`simulation/scripts/run_sil.py`).

**Nicht in diesem Dokument:** alles zur Ausstoßladung selbst (Menge, Behälter, Druck, Bodentest der
Ladung). Schwarzpulver ist in Deutschland erlaubnispflichtig (Sprengstoffgesetz). Kläre Bezug, Umgang
und den Ausstoß-Bodentest vor dem nächsten Versuch, z. B. über einen Raketenmodellbau-Verein mit
berechtigten Mitgliedern oder nach den Angaben eines Herstellers fertiger Ausstoßsätze. Eine Variante
ohne Pyrotechnik steht in §8.

## 1. Ausgangsdaten

| Größe | Wert | Quelle |
|---|---|---|
| Masse am Schirm | 733 g (Rakete nach Brennschluss, Spitze hängt mit am Schirm) | `cad/mass_properties.json`, `erstflug_700`, `burnout` |
| Fallschirm | Klima 8594, Ø 125 cm Nenndurchmesser, Bauart `[?]` (flach rund oder sechseckig, Folie) | `docs/BUILD.md` §1.1 |
| Schockschnur | Kevlar geflochten 2,0 mm, 1 m; Elastik 1,5 mm, 1,8 m | `docs/BUILD.md` §1.1 |
| Gepackter Schirm im CAD | Ø 60 × 230 mm, 50 g mit Schnur (Annahme) | `cad/params.py` `CHUTE_*` |
| Schnurraum bis zur Öse der Spitze | 76 mm bei 700 mm Rohr | `cad/mass_properties.md` |
| Gipfel (SIL, ein Flug) | 57,7 m nach 5,5 s | `run_sil.py` |
| Auslösung (SIL) | 0,8 s nach dem Gipfel, 54,5 m, 8,0 m/s nach unten, 4,4 m seitlich (Monte-Carlo: 0,6–0,8 s, 6–8 m/s) | `run_sil.py`, Schwellen aus `Config.h` |

## 2. Sinkgeschwindigkeit

`v = √(2 m g / (ρ · Cd · A))`, A = Nennfläche π D²/4 = 1,23 m², ρ = 1,20 kg/m³.

| Cd (unbekannt, typische Spanne) | Sinkgeschwindigkeit | Aufprallenergie | entspricht einem Fall aus |
|---|---|---|---|
| 0,60 | 4,0 m/s | 6,0 J | 0,83 m |
| 0,75 | 3,6 m/s | 4,8 J | 0,66 m |
| 0,90 | 3,3 m/s | 4,0 J | 0,55 m |

Üblich sind 3,5 bis 5 m/s. **Der 125-cm-Schirm reicht mit Reserve.** Ein kleinerer Schirm würde
Masse und Packlänge sparen (der Erstflug liegt 11 g über dem 750-g-Ziel): Ø 1,0 m gäbe 4,5 m/s,
Ø 0,9 m 5,0 m/s (Cd 0,75). Das ist eine Entscheidung für dich; der vorhandene Schirm ist die sichere
Wahl, solange er in den Fallschirmraum passt (§5).

**Cd messen statt annehmen (Fallversuch):** Schirm mit einer bekannten Masse (z. B. 0,75 kg in einem
Beutel) aus mindestens 6 m Höhe fallen lassen (Treppenhaus, Balkon, windstill), offen ausgelegt
starten, die Zeit über die letzten 3 m stoppen, dreimal. Dann
`python simulation/scripts/recovery.py --drop-test 0.75 3.0 <Zeit>` → Cd und neue Tabellen.

## 3. Drift

Sinkzeit von 54 m bei 3,6 m/s: 15 s. Abstand vom Pad bei gleichmäßigem Wind:

| Wind | 2 m/s | 4 m/s | 6 m/s | 8 m/s |
|---|---|---|---|---|
| Landung vom Pad | 35 m | 65 m | 95 m | 125 m |

Für den Erstflug: Wind unter 4 m/s, das Gelände in Windrichtung mindestens 100 m frei.

## 4. Auslösezeitpunkt und Öffnungsstoß

Der Zustandsautomat erkennt das Apogäum, wenn die Kalman-Steiggeschwindigkeit unter −0,5 m/s liegt
**und** das Barometer 1 m unter seinem Maximum ist, beides 300 ms lang (`FS_APOGEE_*` in `Config.h`).
Das schützt vor einer Zündung im Steigflug, kostet aber Zeit: Die Rakete fällt nach dem Gipfel frei,
1 m Höhenverlust allein dauert 0,45 s, dazu die Haltezeit. Im SIL (Rauschen an) kommt die Zündung
0,6 bis 0,8 s nach dem Gipfel bei 6 bis 8 m/s (Monte-Carlo in §4.3).

### 4.1 Öffnungsstoß

`F = Ck · ρ/2 · v² · Cd · A` mit Öffnungsstoßfaktor Ck = 1,8 (vorsichtig für flache Schirme bei
kleiner Last). Die Schnur und alle Ösen sollen das Vierfache aushalten.

| Geschwindigkeit beim Öffnen | F (Cd 0,9) | Beschleunigung der Rakete | nötige Bruchlast (× 4) |
|---|---|---|---|
| 4 m/s | 19 N | 2,6 g | 76 N |
| 8 m/s (SIL heute) | 76 N | 10,6 g | 305 N |
| 10 m/s | 119 N | 17 g | 477 N |
| 15 m/s | 268 N | 37 g | 1074 N |
| 20 m/s | 477 N | 66 g | 1909 N |

Heute liegt die Last im Bereich, den eine 2-mm-Kevlarschnur trägt (Bruchlast beim Händler nachsehen;
dein Knoten kostet ein Drittel davon). Kritisch wird es, wenn die Auslösung später kommt: Jede
Sekunde Verzug bringt ≈ 10 m/s mehr und den Öffnungsstoß ins Quadrat. Deshalb ist der Rückfall über
die Zeit (`FS_COAST_MAX_MS`, 6 s nach Brennschluss) zwar richtig als letzte Sicherung, aber im
Normalfall soll die Geschwindigkeitserkennung greifen.

**Zündsperre (seit 22.10.2026):** Die Bergung zündet nur nach mindestens 10 m gemessenem Steigen
(Kalman oder Barometer, `FS_MIN_FLIGHT_ALT_M`). Ein Flug, der unter 10 m bleibt, bekommt also keinen
Fallschirm; im SIL liegt der Erstflug bei 48–69 m.

### 4.2 Schwellen: früher auslösen?

`python simulation/scripts/run_sil.py --apogee-sweep` (je 5 Läufe mit Rauschen, vz-Schwelle −0,5 m/s):

| Barometer-Abfall | Haltezeit | Verzug nach dem Gipfel (Median / max) | Geschwindigkeit (Median / max) | vor dem Gipfel ausgelöst |
|---|---|---|---|---|
| 0,3 m | 100 ms | 0,17 / 0,33 s | 1,9 / 3,4 m/s | 0 von 5 |
| 0,3 m | 200 ms | 0,35 / 0,43 s | 3,6 / 4,3 m/s | 0 von 5 |
| 0,5 m | 100 ms | 0,35 / 0,43 s | 3,6 / 4,3 m/s | 0 von 5 |
| **0,5 m** | **200 ms** | **0,45 / 0,53 s** | **4,5 / 5,3 m/s** | 0 von 5 |
| 0,5 m | 300 ms | 0,55 / 0,63 s | 5,5 / 6,3 m/s | 0 von 5 |
| 1,0 m | 200 ms | 0,61 / 0,71 s | 6,1 / 7,1 m/s | 0 von 5 |
| **1,0 m (Config.h)** | **300 ms** | **0,71 / 0,81 s** | **7,1 / 8,0 m/s** | 0 von 5 |
| 1,5 m | 300 ms | 0,83 / 0,87 s | 8,2 / 8,6 m/s | 0 von 5 |

Von 1,0 m / 300 ms auf 0,5 m / 200 ms sinkt die Geschwindigkeit beim Öffnen von ca. 7 auf 4,5 m/s,
der Öffnungsstoß damit auf rund 40 %.

**Die Wahl ist deine.** Mein Vorschlag: Barometer-Abfall 0,5 m und Haltezeit 200 ms. Das senkt den
Verzug von 0,7 auf 0,45 s, und in der Simulation gab es keine einzige Auslösung vor dem Gipfel. Die
Einschränkung: Das Barometer-Rauschen ist dort weißes Rauschen mit 0,3 m. Echte Störungen wie Böen am
Druckloch, die Druckwelle beim Brennschluss oder Sonne auf der Spitze sind darin nicht enthalten. Bevor
die Schwellen gesenkt werden, gehört deshalb ein echter Barometer-Mitschnitt aus dem Prüfstand oder
einem Flug in die Simulation (`calib_imu`, Taste `s`). Bis dahin bleiben in `Config.h` die sicheren
Werte.

### 4.3 Monte-Carlo (Erstflug, Regler an, 50 Läufe)

`python simulation/scripts/run_sil.py --runs 50`: statischer Kardanfehler σ 1° / 0,6°, Masse ±3 %,
Trägheitsmomente ±10 %, Schwerpunkt ±1 mm seitlich, Servo-Totzeit 30 ± 10 ms, Rauschen an.

| Größe | Median | 95 % | Maximum |
|---|---|---|---|
| Kippwinkel im Boost | 2,7° | 5,3° | 15,2° |
| Gipfelhöhe | 58 m | 66 m | 69 m (Minimum 48 m) |
| Zündung nach dem Gipfel | 0,70 s | 0,77 s | 0,79 s |
| Geschwindigkeit bei der Zündung | 6,9 m/s | 7,6 m/s | 8,1 m/s |
| ABORT / Zündung vor dem Gipfel | 0 von 50 | | |

Der Ausreißer mit 15° hatte einen Kardan-Nullfehler von −3,8° (fast 4 σ): Die Rakete kippt in den
ersten 0,12 s nach dem Abheben, bevor der Automat BOOST erkennt und der Regler stellt; danach regelt
er sie bis zum Brennschluss auf 0,1° zurück. Daraus folgt: die Servo-Mitte genau einstellen
(Testplan 3.2). Außerdem ist die Starterkennung ein Hebel: mit 1,3 g / 20 ms statt 2 g / 50 ms stellt
der Regler 0,1 s früher, und derselbe Fall bleibt unter 6° (`run_sil.py`, Vergleich am 22.10.). Das
erhöht aber das Risiko einer falschen Starterkennung auf der Rampe, siehe `docs/Testplan_Firmware_2026-10-22.md` §8.

## 5. Schnüre und Anordnung

```
 Spitze (Öse am Spant) ──── 0,3 m Kevlar ──── Schirm (Schnurbündel am Wirbel/Schäkel)
                                                  │
                                         Rest Kevlar (0,7 m) ∥ Elastik 1,8 m (parallel, Kevlar mit Schlaufe)
                                                  │
                                    Kolben (Öse) ─┴─ Öse am Spant des Flugcomputer-Moduls
```

- **Gesamtlänge** 2 bis 3 × Raketenlänge (950 mm), also 2 bis 3 m. Vorhanden: 1 m Kevlar + 1,8 m
  Elastik, das passt.
- **Elastik parallel zur Kevlar-Schlaufe:** Die Elastikschnur nimmt den Ruck, die Kevlarschnur hängt
  daneben mit etwas Lose und hält die volle Last, falls das Elastik reißt. Elastik nie allein in
  Reihe als einziges Glied.
- **Schirm im oberen Drittel**, 0,3 m unter der Spitze: Spitze und Rohr hängen getrennt und schlagen
  beim Sinken nicht aneinander.
- **Wirbel (Swivel)** zwischen Schirm und Schnur, sonst verdrehen sich die Fangleinen.
- **Verbindungen:** Kevlar mit Achterschlaufe oder Palstek, Enden mit Sekundenkleber sichern; Schäkel
  oder Schraubglieder statt Knoten an Ösen, damit sich das System zerlegen lässt.
- **Ösen:** Öse am Spant der Spitze und Öse am Spant des Flugcomputers je ≥ 305 N (§4.1). Gedruckte
  Ösen nicht als einziges Glied: eine Kevlarschlaufe durch den Spant ziehen.
- **Der Kolben** bleibt über eine eigene kurze Schnur mit dem Rumpf verbunden; er darf nicht frei
  herausfallen.
- **Reibstellen:** Lukenkanten, M2-Stangen und Schraubenköpfe im Fallschirmraum abkleben; Kevlar
  scheuert an scharfen Kanten durch.

## 6. Fallschirm packen

1. Schirm flach ausbreiten, Kappe glattziehen, die Fangleinen gerade nebeneinander legen und am Ende
   zusammenfassen (Wirbel).
2. Kappe entlang der Bahnen wie einen Fächer auf eine Breite von ca. 55 mm zusammenlegen (schmaler
   als der Innendurchmesser 72,6 mm, damit Luft und Schnur danebenpassen).
3. Die Leinen locker in Längsrichtung auf den Fächer legen, nicht um die Kappe wickeln.
4. Den Streifen in Z-Faltung auf die Länge des Fallschirmraums falten (Ziel ≤ 230 mm, `CHUTE_L`) und
   die Leinen einmal lose um das Paket legen. Kein Gummiband, nichts verkleben.
5. Folie bei Kälte (< 10 °C) leicht mit Talkum bestäuben, sonst klebt sie und öffnet spät.
6. Reihenfolge ins Rohr von unten: Kolben (anliegend), Schirmpaket, Schockschnur in Z-Falten (nicht
   gerollt) oben drauf, dann die Spitze.
7. Das Paket muss **locker** sitzen: umgedreht und leicht geschüttelt rutscht es von selbst heraus.
8. Gepackte Länge und Durchmesser messen und in `cad/params.py` (`CHUTE_L`, `CHUTE_D`) eintragen; mit
   dem Schnurbündel prüfen, ob die 76 mm über dem Schirm reichen (`CORD_BAY_MIN`).

## 7. Passproben (ohne Ladung)

| # | Probe | Erwartung | Ergebnis → |
|---|---|---|---|
| 7.1 | Kolben ohne Schirm von Hand durch das ganze obere Rohr schieben | gleitet ohne Klemmen, auch über den Stoßkuppler bei z = 520 mm | `BUILD.md` §5; sonst Kolben abschleifen |
| 7.2 | Rohr umdrehen, Kolben mit Schirmpaket | rutscht unter Eigengewicht heraus | Paket schmaler packen |
| 7.3 | Spitze aufstecken, Rakete kopfüber schütteln | Spitze bleibt sitzen | sonst eine Lage Klebeband auf die Schulter |
| 7.4 | Spitze mit Kofferwaage abziehen | gleichmäßig, ohne Ruck; Kraft notieren | `BUILD.md` §5 |
| 7.5 | Schnüre mit Kofferwaage oder Gewicht ziehen, jede Verbindung einzeln, langsam bis 150 N | nichts rutscht, nichts reißt | `BUILD.md` §5 |
| 7.6 | Kompletter Ausstoß von Hand: Spitze abziehen, Kolben mit einem Stab herausdrücken | Schirm kommt frei, Leinen verheddern nicht, Schnur hängt nirgends | – |
| 7.7 | Schirm-Fallversuch (§2) | Cd | `recovery.py --drop-test` |

## 8. Variante ohne Pyrotechnik (zur Entscheidung)

Die Firmware hat einen Servo-Ausgang für den Fallschirm (Pin 9, `CHUTE_SERVO_OPEN_DEG`), der heute
im Zustand APOGEE mit aufmacht. Damit ginge ein **Federausstoß**: Eine Druckfeder unter dem Kolben,
ein Servo-Riegel hält den Kolben, der Servo gibt beim Apogäum frei. Vorteile: keine Erlaubnis, beliebig
oft am Tisch testbar, keine heißen Gase am Schirm. Nachteile: Feder, Riegel und Servo wiegen
ca. 15 bis 25 g, und der Riegel muss den Startstoß halten. Wenn du das willst, rechne und konstruiere
ich es im CAD (`cad/ejection.py`).

## 9. Checkliste Bergung am Starttag

1. Schnüre und Ösen sichtgeprüft, Schäkel zugeschraubt, Wirbel dreht.
2. Schirm frisch gepackt (§6), Passprobe 7.2 bestanden.
3. Spitze sitzt (7.3), Schnurbündel liegt oben im Raum, nichts zwischen Spitze und Rohr eingeklemmt.
4. Wind gemessen < 4 m/s, Landezone in Windrichtung frei.
5. Nach der Landung: erst Schlüssel ziehen, dann Rakete anfassen.
