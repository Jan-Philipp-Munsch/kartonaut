# Kartonaut 1: Bauanleitung in Modulbauweise

<p class="subtitle">Erstflug (ein TSP E12, Fallschirm, keine Beine, kein Rollmotor) · Stand 2 vom 22.10.2026, nach dem gebauten
Kardan · Maße aus <code>cad/modular_params.py</code>, Zeichnungen aus <code>docs/bauanleitung/zeichnungen.py</code></p>

Stand 2 richtet sich nach dem, was schon gebaut ist: dem Schubstangen-Kardan mit zwei FrSky W5652H im 125-mm-Rohr A,
dem 176-mm-Rohr B und dem halben Kuppler (75 mm). Der Flugcomputer ist die Platine rev B1 auf einem gedruckten Schlitten
im Rohr B. Oben schließt ein gedruckter Spant mit sichtbarem Band ab; auf ihm sitzt die CO₂-Ausstoßung, darüber liegt
im neuen Rohr C der Schirm unter der Klima-Spitze. Alle Radialschrauben sind M3 auf 0°/90°/180°/270° wie am Kardan.

| Datei | Inhalt |
|---|---|
| `docs/bauanleitung/Zeichnungen_Kartonaut1.pdf` | Z1 Übersicht, Z2–Z4 Abwicklungen der Rohre A, B, C, Z5 Schlitten mit Spant, Z6 Kleinteile |
| `docs/bauanleitung/Bohrschablonen_1zu1.pdf` | S1–S4 zum Ausdrucken in Originalgröße und Umwickeln der Rohre |
| `cad/export/modular/*.stl` | die vier neuen Druckteile |
| `cad/modular.py` | Druckteile, Kollisionsprüfung, Masse, Bilder |

```bash
MS_CONFIG=erstflug python cad/modular.py          # Druckteile, Prüfung, Masse, Bilder
python docs/bauanleitung/zeichnungen.py           # Zeichnungen und Schablonen
python docs/bauanleitung/build_pdf.py             # diese Anleitung als PDF
```

[TOC]

<hr class="pb">

## 1. Entscheidungen und Prüfbefunde

### 1.1 Entschieden am 22.10.2026

| Thema | Entscheidung | Grund |
|---|---|---|
| Flugcomputer | Platine rev B1 auf einem gedruckten Schlitten, **keine Gewindestangen**, kein Ring-Stack | eine Platine braucht keinen Stapel; 30 g Stahl gespart, Luken frei |
| Kardan | bleibt wie gebaut (Schubstangen, W5652H, Rohr A 125 mm) | gebaut und eingepasst |
| Roll | **kein Rollmotor, kein Schwungrad** | Masse, Vibration auf der IMU; ohne Flossen kaum Rollmoment. Bedingung: Lage in der Firmware als Quaternion aus dem Gyro (Befund 3 in `PROJECT.md`) |
| Ausstoß | **CO₂-Kapsel** (Aufbau ca. 10 g, ca. 2 l Gas), ausgelöst über ein Servo | keine Pyrotechnik, kein Sprengstoffrecht, kaltes Gas, am Tisch beliebig testbar |
| Schirm | im Rohr C unter der Spitze, gepackt 100 × Ø 70 | passt nicht in die Klima-Spitze (Holzplatte 25 mm über der Schulterkante) |
| Arming | **Schraubschalter** statt Schlüsselschalter; für den Erstflug ohne Pyro nur eine Brücke | leicht, kein großes Loch, nichts steht über |
| Funk und GPS | GPS flach unter dem Spant, Patch nach oben; LoRa als 433-MHz-Wendel axial am unteren Ende | ca. 12 cm Abstand; GPS sieht zum Himmel (auch am Schirm, der Rumpf hängt mit dem Spant nach oben); Wendel strahlt rundum zur Seite |
| Spitze | gekaufte Klima 8539 mit ihrer Holzplatte und dem Haken | die eigene Spitze mit Gewindestange, Servo und Federn ist verworfen |

### 1.2 Befunde, die zu diesem Stand geführt haben

| Nr. | | Befund | Lösung |
|---|---|---|---|
| 1 | K | Der 80-mm-Stoßkuppler des alten CAD hätte den Kolben blockiert (innen 70,2 < Kolben 72,4). | Kein Kolben mehr, kein Stoß im Schirmraum. |
| 2 | K | Antenne und GPS waren in der abgesprengten Spitze vorgesehen. | Beide im Avionikraum (Tabelle oben). |
| 3 | K | Die Stecker J5/J6/J1 an der unteren Stirnseite der Platine ragen 12 mm über. | Untere Scheibe mit Steckerfenster, Lage geprüft. |
| 4 | K | Das CAD-Modell `cad/tvc.py` beschreibt einen Kardan mit der Servowelle direkt auf der Drehachse; gebaut ist ein Schubstangen-Kardan. | Für den Bau gilt der gebaute Kardan; das CAD-Modell ist nachzuziehen (O4). Die Servo-Umrechnung in `Config.h` (Befund 13) am gebauten Kardan messen. |
| 5 | W | Das alte Massenmodell setzte Druckteile zu leicht an. | Hier aus den CAD-Volumen gerechnet: ≈ 706 g (§2.5). |
| 6 | W | Die Rampenführungen (Entwurf bei 60/180/300°) liegen auf Schrauben. | Führungen bei **45/135/225/315°**, zwischen den Schrauben (Hinweis an die Startrampe). |
| 7 | W | Gewinde direkt im Druck reißen bei häufigem Lösen aus. | Einschmelzmuttern M3 in allen geschraubten Druckteilen. |
| 8 | W | Barometerraum war zum Kardan offen. | Untere Scheibe plus Schaum; die 4 alten Löcher in Rohr B sind der Druckausgleich. |
| 9 | H | Bei 2 l CO₂ im freien Raum unter der Spitze (ca. 780 ml) entstünden bis 2,6 bar, wenn die Spitze klemmt. | Spant 5 mm (ca. 17 MPa bei 2,6 bar), keine Abscherstifte, bis der Test zeigt, dass die Spitze bei kleinem Druck geht. |

<hr class="pb">

## 2. Aufbau

### 2.1 Module und Trennstellen

![Z1 Übersicht](img/bauanleitung/Z1_uebersicht.png)

| Modul | Teile | Trennstelle |
|---|---|---|
| **M1 Antrieb** | Rohr A 125 mit dem gebauten Kardan, 2 × W5652H, Motor E12 (bündig) | T1: 4 × M3 durch Rohr A und Kuppler in den Schraubring |
| **M2 Avionik** | Rohr B 176, Kuppler J1 (in B verklebt), Schlitten mit Spant, Platine, Akkus, GPS, LoRa, Schalterbrett | T2: 4 × M3 durch Rohr B in den Spant |
| **M3 Bergung** | Rohr C, CO₂-Modul auf dem Spant, Schirm, Schnur | T3: 4 × M3 (45° versetzt) durch Rohr C in den Spant |
| **M4 Spitze** | Klima 8539 | T4: Passung |

Lastpfade: Schub über den Kardanflansch ins Rohr A, über T1 weiter. Der Spant liegt mit dem Band auf der Oberkante
von Rohr B: Der CO₂-Druck drückt ihn dorthin. Schirmzug über die Ringschraube am Spant und T2 in Rohr B, über T1 in A.

### 2.2 Winkel

Längslinie 0° = eine Kardanschraube (markieren). Von außen gesehen, Spitze oben, wächst der Winkel nach rechts.

| Winkel | Was dort liegt |
|---|---|
| 0°, 90°, 180°, 270° | alle Schrauben von Kardan, T1, T2 und die alten Löcher in B |
| 90° | Bestückungsseite der Platine, Luken A1 (SD) und A2 (USB) |
| 270° | Luke B (Schalterbrett), daneben bei 282° das Loch für den Schraubschalter |
| 45°, 135°, 225°, 315° | Rampenführungen (bis 160 mm Höhe), Schrauben T3 in Rohr C, Abscherstifte bei 45/225° |
| Servofenster | wie gebaut; sie dürfen nicht unter einer Rampenführung liegen (prüfen, sonst Führungen drehen) |

Die Platine muss nach dem Kardan ausgerichtet werden (welche Servoachse Nicken ist); Rohr B hat dafür eine Marke über
den Stoß zu Rohr A. T1 passt in vier Lagen, also vor dem Schrauben die Marke prüfen.

### 2.3 Avionik-Schlitten mit Spant

| Bestückungsseite (Luke A) | Schalterbrett (Luke B) | Schlitten allein |
|---|---|---|
| ![](img/bauanleitung/modular_avionik_rumpf.png) | ![](img/bauanleitung/modular_luke_b.png) | ![](img/bauanleitung/modular_avionik.png) |

Ein Druckteil: oben das **Band** Ø 75 × 5 (liegt auf Rohr B, außen sichtbar) mit **Zapfen nach unten** in Rohr B
(4 Augen für T2) und **Zapfen nach oben** in Rohr C (4 Augen für T3); darunter der **Träger** mit vier Säulen für die
Platine und Fächern für den 2S-Akku (v = 6 … 62) und den 1S-Akku (v = 64 … 114). Unter dem Band zwei Leisten für das
**GPS-Modul** (20 × 20, Patch nach oben). Unten verschraubt die **untere Scheibe** mit Steckerfenster; durch ihr
Kabelloch ragt die **LoRa-Wendel** nach unten. Hinter Luke B das **Schalterbrett**. Im Band: Ringschraube M4 für die
Schnur und eine Kabeldurchführung Ø 6 für das CO₂-Servo (mit Epoxid abdichten).

### 2.4 Stapel (z ab Rohrunterkante = Düse)

| z | Was |
|---|---|
| 0 … 93 | Motor TSP E12-0, bündig |
| 0 … 125 | Rohr A, Kardanschrauben bei 44, Servofenster ab 60 |
| 87,5 … 162,5 | Kuppler J1 (in B verklebt), Schraubring bei 104 … 116, T1 bei 110 |
| 125 … 301 | Rohr B, alte Löcher bei 169 (Druckausgleich), T2 bei 293 |
| 155 … 158 | untere Scheibe, LoRa-Wendel 124 … 154 |
| 167 … 287 | Platine rev B1 |
| 301 … 306 | Band des Spants |
| 306 … 564 | Rohr C (258 mm), T3 bei 313,5 |
| 322 … 346 | CO₂-Modul, Kapsel quer |
| 349 … 449 | Schirm 100 × Ø 70 |
| 489 … 564 | Schulter der Spitze (Schulterlänge 75 angenommen, nach Klima-Zeichnung prüfen) |
| 564 … 794 | Spitze |

### 2.5 Masse (Schätzung)

| | g |
|---|---|
| Rohre A + B + C | 30 + 42 + 62 |
| neue Druckteile (Schlitten mit Spant 74, Scheibe 8, Schalterbrett 2, Schraubring 14) | 98 |
| CO₂-Aufbau 10 + Kapsel 25 [Annahme] | 35 |
| **Start, ein E12** | **≈ 706** |

Rechnung in `cad/modular.py` gegen das alte Massenmodell (761 g, `cad/mass_properties.md`). Die Waage entscheidet:
Kardan und Rohr A wiegen, neue Teile nach dem Druck wiegen, Hebelarm neu bestimmen (§5.6).

<hr class="pb">

## 3. Teileliste: was da ist, was fehlt, was gedruckt wird

Status: **✓ da** · **bestellen** · **drucken** (neu) · **neu drucken** (besser) · **prüfen**. Zum Abhaken ausdrucken.

### 3.1 Bestellen

| ✓ | Teil | Stück | Wofür | Quelle / Hinweis |
|---|---|---|---|---|
| ☐ | **Mainboard rev B1, bestückt** | 2 (eine Reserve) | Flugcomputer | JLCPCB, `hardware/mainboard/ORDER.md` Tor 3; erst nach dem Einarbeiten der Review-Punkte |
| ☐ | 1S-LiPo 450–600 mAh, JST-PH 2.0, ohne Schutzschaltung, max. 50 × 30 × 7 | 2 | Elektronik | ORDER.md 0.6 |
| ☐ | 1S-USB-Lader | 1 | Laden außerhalb der Rakete | ORDER.md 0.8 (auf der Platine ist auch einer) |
| ☐ | 2S-LiPo 450 mAh 50 C, XT30, max. 56 × 25,5 × 8 | 1–2 | Servos | nur falls der vorhandene Servo-Akku nicht passt (prüfen) |
| ☐ | GPS-Modul u-blox M10 mit SAW-Filter, ca. 20 × 20 mit Patch | 1 | GPS unter dem Spant | ORDER.md 0.20; Maße vor dem Kauf mit 20 × 20 × 7 vergleichen |
| ☐ | 433-MHz-Wendelantenne mit IPEX-Anschluss (oder IPEX-Pigtail + SMA-Wendel) | 2 | LoRa in der Rakete | ORDER.md 0.5 |
| ☐ | LoRa E22-400T22D + 433-MHz-Stabantenne | 2 | Bodenstation, Tisch | ORDER.md 0.3, 0.4 |
| ☐ | Schraubschalter (z. B. Featherweight Screw Switch) | 1 | Arming (später, für Pyro) | für den Erstflug reicht eine XH-2-Brücke |
| ☐ | CO₂-Kapseln mit Gewinde (8 g) | 5 | Ausstoß | Anzahl für Tests + Flüge |
| ☐ | Einschmelzmuttern M3 kurz (≈ 4 mm lang) | 25 | alle Druckteile | erst eine Probe, dann `INSERT_HOLE` anpassen |
| ☐ | Schrauben M3 × 6 ISO 7380 (Linsenkopf, Inbus 2) | 25 | T1, T2, T3, Platine, Schalterbrett | Kopf ≤ 1,7 mm hoch |
| ☐ | Schrauben M3 × 8 | 4 | untere Scheibe | |
| ☐ | Ringschraube M4 mit Mutter, 2 Scheiben | 1 | Schnur am Spant | |
| ☐ | Schiebeschalter 2-polig (DPDT) | 2 | Hauptschalter J_SW | ORDER.md 0.9 |
| ☐ | USB-C-Buchse auf kleiner Platine, LED 3 mm | 1 | Laden 1S am Schalterbrett | |
| ☐ | XT30-Buchse, Balancer-Verlängerung XH-3 | je 1 | Laden 2S am Schalterbrett | ORDER.md 0.13 |
| ☐ | JST-XH/PH-Sortiment mit Crimpkontakten | 1 | alle Kabel | ORDER.md 0.11 |
| ☐ | Crimpzange JST | 1 | | ORDER.md 0.12, falls nicht vorhanden |
| ☐ | Silikonlitze AWG 22/26 | je 2 m | Kabel | ORDER.md 0.21 |
| ☐ | Klettband 16 mm, Moosgummi 1 mm, offenporiger Schaum, Kapton/PE-Platte 1 mm | je 1 | Akkus, Dichtung, Isolierung | ORDER.md 0.23 |
| ☐ | Epoxid 30 min, dünner Sekundenkleber | je 1 | Kuppler, Ring, Bohrränder | |
| ☐ | Körperrohr 75/500 Klima, daraus Rohr C (258 mm) | 1 | Rohr C | nur falls kein passendes Stück übrig ist |
| ☐ | Wirbel/Schnellverbinder 3 mm | 3 | Schnur, Schirm | |

### 3.2 Drucken (neu)

| ✓ | Teil | Datei | Material | Masse |
|---|---|---|---|---|
| ☐ | Schlitten mit Spant | `Schlitten_mit_Spant.stl` | PETG | 74 g |
| ☐ | Untere Scheibe | `Untere_Scheibe.stl` | PETG | 8 g |
| ☐ | Schalterbrett | `Schalterbrett.stl` | PETG | 2 g |
| ☐ | Schraubring J1 | `Schraubring_J1.stl` | PETG | 14 g |
| ☐ | CO₂-Modul (deine Konstruktion) | – | PETG (PLA wird bei kaltem CO₂ spröde) | ca. 10 g |

### 3.3 Neu drucken (besser) oder prüfen

| ✓ | Teil | Warum | Was tun |
|---|---|---|---|
| ☐ | Motorrohr/Adapter am Kardan, falls PLA | Das Motorgehäuse wird nach dem Brand heiß; PLA wird ab ca. 55 °C weich. | in PETG oder ASA nachdrucken; sonst nach dem ersten Brand auf Verformung prüfen |
| ☐ | Kardanrahmen, falls PLA | wie oben, und Kriechen unter den Schrauben | prüfen; bei Spiel oder Verformung in PETG nachdrucken |
| ☐ | Servohebel am Gestänge | Spiel zwischen 2-mm-Draht und Hebelbohrung ist totes Band in der Regelung | Spiel prüfen; sonst Hebel mit passender Bohrung oder Messinghülse |
| ☐ | Ring-Stack, Batterie-Ring mit Radialschrauben, eigene Spitze | entfällt | nicht mehr drucken |

### 3.4 Vorhanden (laut `docs/BUILD.md` und deinen Bildern)

| ✓ | Teil |
|---|---|
| ☐ | Kardan, gebaut, in Rohr A 125 mit 4 Schrauben, 2 × FrSky W5652H mit Gestänge |
| ☐ | Rohr B 176, halber Kuppler 75, weitere Rohr- und Kupplerstücke |
| ☐ | Klima-Spitze 8539 mit Haken, Fallschirm 125 cm, Kevlar 2 mm und Gummischnur (Klima) |
| ☐ | 4 × TSP E12-0 |
| ☐ | Teensy 4.1, microSD |
| ☐ | Servo-Akku (Typ und Maße prüfen: passt er ins 2S-Fach 56 × 25,5 × 8 mit XT30?) |
| ☐ | SG90 als Auslöse-Servo für das CO₂-Modul |

## 4. Druckeinstellungen

| Teil | Lage | Wände / Füllung |
|---|---|---|
| Schlitten mit Spant | Band auf dem Bett (im Slicer um 180° drehen) | 3 Wände, 25 % Gyroid, keine Stützen |
| Untere Scheibe, Schraubring | flach | 3 Wände, 30 % |
| Schalterbrett | flach | 100 % |

Einschmelzmuttern bei 220 °C senkrecht eindrücken, 0,2 mm unter die Oberfläche. Jedes Teil nach dem Druck wiegen.

## 5. Bauschritte

### 5.1 Vorbereiten

1. Schablonen aus `Bohrschablonen_1zu1.pdf` in Originalgröße drucken, 100-mm-Balken nachmessen.
2. Längslinie 0° an Rohr A durch eine Kardanschraube ziehen (Winkelprofil), über den Stoß auf Rohr B verlängern.
3. Rohr C auf 258 mm ablängen (Schulterlänge der Spitze vorher messen: jeder Millimeter mehr oder weniger geht 1:1 in
   die Rohrlänge).

### 5.2 Stoß J1 (Rohr A ↔ Rohr B)

1. Kuppler J1 mit Epoxid 37,5 mm tief in Rohr B kleben, Marke über den Stoß ausrichten.
2. Rohr A auf den Kuppler stecken, Längslinien fluchten. **S1** an der Oberkante von A anlegen, 4 Löcher Ø 3,4 bei
   h = 110 durch Rohr A **und** Kuppler bohren.
3. Rohr A wieder abziehen. Schraubring (mit Einschmelzmuttern) von unten in den Kuppler schieben, mit zwei M3 durch die
   Löcher ausrichten, dann mit Epoxid festkleben. Servokabel laufen innen durch den Ring.

### 5.3 Rohr B

1. **S2** an der Unterkante von B: Luken A1 und B ausschneiden (Stücke als Deckel aufheben), Schraubschalter-Loch Ø 3.
   Die alten Löcher bei h = 44 bleiben offen (Barometer).
2. **S3** an der Oberkante von B: Luke A2 ausschneiden, 4 Löcher T2 Ø 3,4 bei h = 168 (8 mm unter der Kante).
3. Schnittkanten und Bohrränder mit dünnem Sekundenkleber härten.

### 5.4 Rohr C und Spitze

1. **S4** an der Unterkante von C: 4 Löcher T3 Ø 3,4 bei 45/135/225/315°, h = 7,5.
2. Spitze aufsetzen, Passung einstellen (Klebeband auf der Schulter): sie soll leicht gehen, aber nicht von allein.

### 5.5 Avionik-Schlitten

1. Einschmelzmuttern in Schlitten (4 unten, 4 oben, 4 Säulen, 2 Stirn), Schalterbrett-Säulen (2), Schraubring (4).
2. Ringschraube M4 durch das Band; Kabel des CO₂-Servos durch die Ø-6-Durchführung, mit Epoxid abdichten.
3. GPS zwischen die Leisten unter dem Band (Patch nach oben), Kabel zu J_GPS.
4. Schalterbrett bestücken und anschrauben (siehe Z6), Akkus mit Klettband, Isolierplatte, Platine mit 4 × M3 × 6.
5. LoRa-Wendel an IPEX, axial durch das Kabelloch der unteren Scheibe; Scheibe mit 2 × M3 × 8.
6. Einbau: Servokabel aus Rohr A durch den Schraubring nach oben, an J5/J6 stecken, Schlitten von oben in Rohr B, bis das
   Band aufliegt; Augen auf die Löcher T2 drehen (Luke A über dem USB-Stecker); 4 × M3 × 6. Stecker- und Kabelfenster der
   Scheibe durch Luke B mit Schaum stopfen.

### 5.6 Bergung und Endkontrolle

1. CO₂-Modul auf den Spant (Kapsel quer, 0°–180°), Servo an J_SERVO3.
2. Schnur: Ringschraube Spant → Kevlar → Wirbel mit Schirm → Gummischnur → Haken der Spitze. Schirm 100 × Ø 70 packen,
   Schnur im Zickzack darüber, Spitze aufsetzen.
3. Rohr C aufstecken, 4 × M3 bei T3.
4. **Wiegen** (Ziel ≈ 706 g) und **Schwerpunkt** auswiegen; Hebelarm Kardanpunkt–Schwerpunkt und Masse in
   `firmware/src/Config.h` (`MOMENT_ARM_M`, `MASS_KG`) eintragen.
5. **Servo-Umrechnung messen:** Servo um 10° stellen, Kardanwinkel messen (Befund 13); `SERVO_*_GAIN` setzen.
6. **CO₂-Bodentest** (draußen, Rakete waagrecht): Spitze fliegt ab, Schirm und Schnur vollständig draußen, Spant und
   Rohr C unbeschädigt. Mindestens dreimal, auch kalt.
7. **Reichweite:** LoRa mit geschlossener Rakete; GPS-Signal ansehen, während LoRa sendet.
8. **Barometer:** an einem der alten Löcher saugen, Druck muss im Log springen.

## 6. Wartung

| Ziel | Handgriffe |
|---|---|
| Akkus laden | USB-C und XT30 an Luke B |
| Firmware, SD-Karte | Lukendeckel A2/A1 ab |
| Kapsel wechseln, Schirm packen | Spitze ab, 4 × M3 an T3, Rohr C ab |
| Schlitten heraus | Rohr C ab, 4 × M3 an T2, Schlitten am Band herausziehen, J5/J6 abziehen |
| Kardan, Servo | 4 × M3 an T1, Rohr A nach unten abziehen (Servokabel vorher am Schlitten abziehen) |
| Motor | von unten, wie gebaut |

### 6.1 Flugvorbereitung am Startplatz

| ✓ | Schritt |
|---|---|
| ☐ | Akkus voll (1S ≥ 4,1 V, 2S ≥ 8,2 V), Hauptschalter AUS |
| ☐ | CO₂-Kapsel eingesetzt, Auslöser gesichert, Schirm gepackt, Rohr C und Spitze drauf |
| ☐ | Motor einsetzen, Anzünder noch nicht |
| ☐ | Rakete auf die Rampe, Schrauben zwischen den Führungen |
| ☐ | Hauptschalter EIN: Bootton, Telemetrie, GPS-Fix, Kardan-Selbsttest |
| ☐ | Lukendeckel mit Klebeband schließen |
| ☐ | Anzünder einsetzen, alle auf Abstand |

## 7. Kabelplan

| Stecker | Gegenstelle | Lösen beim |
|---|---|---|
| J5, J6 (XH-3) | Servos im Rohr A (durch den Schraubring) | Schlitten heraus |
| J_SERVO3 | Servo des CO₂-Moduls (durch das Band) | Rohr C ab (Stecker unter dem Band) |
| J1 XT30, J_BAT1 PH | Akkus im Träger | Akkutausch |
| J_SW, J_CHG1, J_CHG2, Balancer | Schalterbrett | bleibt am Schlitten |
| J_ARM (XH-2) | Brücke (Erstflug) bzw. Schraubschalter | bleibt am Schlitten |
| IPEX | LoRa-Wendel | bleibt am Schlitten |
| J_GPS | GPS unter dem Band | bleibt am Schlitten |

## 8. Offen

| Nr. | Punkt |
|---|---|
| O1 | Winkel der beiden Servofenster in Rohr A ab der Längslinie messen, dann gegen die Rampenführungen (45/135/225/315°) prüfen. |
| O2 | Schulterlänge und Innenmaß der Klima-Spitze aus der Klima-Zeichnung; ändert Rohr C. |
| O3 | Einschmelzmuttern: Muster kaufen, `INSERT_HOLE` anpassen, Druckteile neu erzeugen. |
| O4 | `cad/tvc.py` auf den gebauten Schubstangen-Kardan umstellen (Hebel 15 mm, Stangen 29/30 mm); Servo-Umrechnung messen. |
| O5 | Firmware: Lage als Quaternion aus dem Gyro (Voraussetzung für den Verzicht auf den Rollmotor). |
| O6 | CO₂-Modul: Kapselgröße und Anstechmechanismus festlegen, Bodentests. |
| O7 | Platine rev B1: Antennenlage (GPS, LoRa-Wendel) in die Spezifikation übernehmen; Pyro-Kanäle bleiben für später. |
| O8 | Startrampe (Branch `landepad`): Führungen auf 45/135/225/315°. |

<hr class="pb">

## 9. Zeichnungen

Verkleinert zum Nachschlagen. Maßstäblich: `docs/bauanleitung/Zeichnungen_Kartonaut1.pdf`. Schablonen nur aus
`docs/bauanleitung/Bohrschablonen_1zu1.pdf` drucken.

![Z2 Rohr A](img/bauanleitung/Z2_rohr_a.png)

![Z3 Rohr B](img/bauanleitung/Z3_rohr_b.png)

![Z4 Rohr C](img/bauanleitung/Z4_rohr_c.png)

![Z5 Schlitten mit Spant](img/bauanleitung/Z5_schlitten.png)

![Z6 Kleinteile](img/bauanleitung/Z6_kleinteile.png)

![Längsschnitt (CAD)](img/bauanleitung/modular_section.png){ width=28% }
