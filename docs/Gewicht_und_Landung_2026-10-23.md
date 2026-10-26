# Gewicht und Landung: Durchsicht vom 23.10.2026

Anlass: Jans Wunsch, die Druckteile vor dem Drucken leichter zu machen, das Gewicht der ganzen Rakete
durchzugehen und zu prüfen, ob *Kartonaut 1* gleich mit Landebeinen statt am Fallschirm landen soll.
Grundlagen: `cad/mass_stand2b.py` (Massenbudget mit Hebeltabelle), `simulation/scripts/check_stand2b_levers.py`
(Regelgüte), die Landestudie der Cloud-Session (Branch `landing-burn`, `docs/Physik_Review_2026-10-23.md` §3,
`simulation/scripts/landing_study.py`) und deren frühere Machbarkeitsrechnung (Branch `firmware-flightcore`,
`docs/Landung_Machbarkeit_2026-10-22.md`). Alle Zahlen sind Modellwerte; gewogen ist nichts.

## 1. Ergebnis in drei Sätzen

Die Druckteile sind umkonstruiert und sparen 16 g, die ganze Rakete lässt sich ohne Konzeptänderung von 705 auf
672 g bringen und mit Federausstoß, kleinerem Schirm und gedruckter Spitze bis auf 593 g. Leichter verlangt kleinere
Reglergewinne: Mit der echten Masse und dem echten Hebelarm stehen die alten Gewinne den Kardan zwei Drittel der
Brennzeit an den Anschlag, Kp 2 / Ki 1 / Kd 0,45 aus der Bayes-Optimierung regelt sauber. Eine Landung mit Beinen und
einem zweiten E12 gelingt mit realistischen Streuungen nur in 2 bis 5 von 100 Versuchen und wird umso härter, je
leichter die Rakete ist; *Kartonaut 1* sollte deshalb am Fallschirm fliegen.

## 2. Druckteile: Stand 2c

Die vier Druckteile sind in `cad/modular.py` und `cad/modular_params.py` umkonstruiert (Stand 2c), die STL in
`cad/export/modular/` sind neu, die Kollisionsprüfung ist frei, Zeichnungen, Bohrschablonen und Bilder sind neu erzeugt.

| Teil | Stand 2b | Stand 2c | Was geändert ist |
|---|---|---|---|
| Schlitten mit Spant | 77,9 cm³, 71 g | 53,0 cm³, 64 g | Spantplatte 3,5 statt 5 mm (außen bleibt ein 5-mm-Rand, der auf Rohr B liegt); Zapfen 2 statt 4,1/3,1 mm; U-Profil statt des vollen Klotzes zwischen Träger und Zapfen (allein 11,5 cm³); Fenster im Trägerboden unter den Akkus; Augen weiter innen, damit hinter jeder Mutter mindestens 2,9 mm Material bleiben |
| Untere Scheibe | 8,7 cm³, 10 g | 5,8 cm³, 7 g | 2 statt 3 mm |
| Schalterbrett | 2,1 cm³, 3 g | unverändert | |
| Schraubring J1 | 14,6 cm³, 12 g | 4,5 cm³, 6 g | Wand 2 statt 6 mm, 10 statt 12 mm hoch; die vier Augen tragen die Muttern |
| **Summe** | **96 g** | **80 g** | |

Die Massen rechnen jetzt mit einem Slicer-Modell: Oberfläche × 1 mm voll gedruckt (drei Perimeter, vier bis fünf
Lagen oben und unten), der Rest mit 25 % Gyroid. Die alte Regel „75 % des Volumens“ hätte 98 → 62 g versprochen.
Das Volumen sinkt um 36 %, die Masse nur um 17 %, weil dünne Wände voll gedruckt werden, dicke Wände dagegen schon
vorher innen überwiegend hohl waren. Der Schlitten besteht jetzt fast nur noch aus Hülle; weitere Fenster und zwei
statt drei Perimeter bringen nur noch wenige Gramm.

Festigkeit: Die Spantplatte sieht bei 2,6 bar (Spitze klemmt, die ganze Kapsel bleibt im Rohr C, Obergrenze) 21 bis
34 MPa, je nachdem wie stark der Rand einspannt; PETG hält in der Druckebene 45 bis 50 MPa. Geht die Spitze wie
vorgesehen bei unter 0,1 bar ab, sind es unter 2 MPa. Der Träger hängt mit Boden und Wänden an der Platte und mit dem
Boden als Sehne an der Zapfenwand; die Last dort ist die Avionik von rund 110 g, auch bei zehnfacher
Erdbeschleunigung nur 11 N.

## 3. Gewicht der ganzen Rakete

Ausgangslage ist Stand 2b mit den neuen Druckteilen: **705 g** beim Start (vorher 723 g), Schwerpunkt 259 mm über
der Düse, Hebelarm Kardan–Schwerpunkt 190 mm. Die Tabelle steht vollständig in `cad/mass_stand2b.md`
(`python cad/mass_stand2b.py`); die Massen mit [Annahme] sind Händler- oder Schätzwerte.

| Hebel | Δ Masse | Hebelarm danach | Bewertung |
|---|---|---|---|
| 2S 300 statt 450 mAh | −9 g | 190 mm | reicht für die Servos über Stunden; muss gekauft werden |
| Motoradapter 29→24 als drei Ringe statt Vollrohr | −8 g | 192 mm | neu drucken, kein Risiko |
| Mikroservo statt SG90 für die CO₂-Auslösung | −4 g | 189 mm | Stellkraft für den Anstecher prüfen |
| Spitzen-Kuppler 50 statt 75 mm, Rohr C 25 mm kürzer | −12 g | 182 mm | Schnurraum halbiert, reicht für 1 m Kevlar und 1,8 m Gummischnur |
| Fallschirm 100 statt 125 cm | −20 g | 182 mm | Sinkrate 3,4 → 4,3 m/s, Aufprallenergie +60 %; muss gekauft werden |
| Federausstoß mit Servoriegel statt CO₂ | −31 g | 186 mm | Konzeptänderung gegen deine Entscheidung vom 22.10.; am Tisch genauso testbar |
| Spitze dünnwandig gedruckt statt Klima | −38 g | 171 mm | größter Einzelhebel, nimmt aber Masse ganz oben weg |

| Paket | Inhalt | Start | Hebelarm | Ixx |
|---|---|---|---|---|
| Ausgangslage | Druckteile Stand 2c | 705 g | 190 mm | 0,0211 kg·m² |
| P1 | ohne Konzeptänderung: Akku, Adapter, Mikroservo, kurzer Kuppler | 672 g | 185 mm | 0,0187 kg·m² |
| P2 | P1 + Federausstoß + 100-cm-Schirm | 631 g | 176 mm | 0,0171 kg·m² |
| P3 | P2 + gedruckte Spitze | 593 g | 157 mm | 0,0136 kg·m² |

Was fest oder schon minimal ist: Motor 64 g, Platine mit Teensy 45 g, Rohre A und B 72 g und Kardan mit Servos 73 g
(beides gebaut, wiegen), GPS 6 g und LoRa 5 g (für die Suche im abgelegenen Gelände nötig), 1S 14 g.

## 4. Leichter heißt nicht einfach besser: Regelung

Eine leichtere Rakete hat einen kürzeren Hebelarm und ein kleineres Quer-Trägheitsmoment. Dasselbe Stellmoment
dreht sie schneller, die Reglergewinne aus `Config.h` (Kp 5, Ki 0, Kd 1) wirken also stärker. Die Gewinne waren für
0,7 bis 1,0 kg mit I = 0,045 bis 0,11 kg·m² gefunden; *Kartonaut 1* hat I = 0,021 kg·m², ein Fünftel.

Rechnung mit `simulation/scripts/check_stand2b_levers.py`: Firmware-Regler mit der wahren Masse und dem wahren
Hebelarm (so wird `Config.h` nach dem Wiegen gesetzt), Servo-Umrechnung 6 Servo-Grad je Kardan-Grad (±3,75°), ein
Motor, Boden, Rauschen, statischer Fehler 1°/0,6°, Treibstoff 28 g, kein Luftwiderstand. „Anschlag“ ist der Anteil
der Brennzeit, in dem der Kardan am Fenster steht. Gemittelt über zwei bis drei Seeds, Kipp ist der größte Wert.

| Paket | Gewinne | Gipfel | Kipp max Brennphase | Kipp bei Brennschluss | seitlich bei Brennschluss | Anschlag |
|---|---|---|---|---|---|---|
| Ausgangslage 705 g | **alt: Kp 5, Kd 1** | 73 m | 4,3° | 3,3° | 1,2 m | **67 %** |
| Ausgangslage 705 g | Kp 1, Kd 0,5 | 74 m | 3,3° | 2,9° | 3,1 m | 0 % |
| Ausgangslage 705 g | **Kp 2, Kd 0,5** | 74 m | **2,4°** | 1,5° | 1,8 m | **0 %** |
| Ausgangslage 705 g | Kp 3,5, Kd 0,25 | 74 m | 5,1° | 4,0° | 1,2 m | 6 % |
| P1 672 g | alt: Kp 5, Kd 1 | 84 m | 5,1° | 3,8° | 1,6 m | 70 % |
| P1 672 g | **Kp 2, Kd 0,5** | 86 m | **2,5°** | 1,5° | 1,7 m | **0 %** |
| P2 631 g | alt: Kp 5, Kd 1 | 102 m | 6,4° | 3,7° | 2,1 m | 73 % |
| P2 631 g | **Kp 2, Kd 0,5** | 103 m | **2,3°** | 1,4° | 1,7 m | **0 %** |
| P3 593 g | alt: Kp 5, Kd 1 | 121 m | 8,5° | 4,2° | 3,0 m | 82 % |
| P3 593 g | Kp 2, Kd 0,5 | 123 m | 3,7° | 3,7° | 2,1 m | 36 % |
| P3 593 g | **Kp 2, Kd 0,25** | 124 m | **2,2°** | 1,3° | 2,0 m | **0 %** |

Drei Folgerungen:

- **Mit den alten Gewinnen steht der Kardan bei jeder Erstflug-Masse zwei Drittel der Brennzeit am Anschlag.** Die
  Brennphase bleibt geregelt (4 bis 6° Kipp), aber ohne Reserve für Wind oder einen größeren Fehler. Meine Zahl vom
  22.10. nachts (unter 2° Kipp) war zu gut, weil `Config.h` noch mit 0,30 m Hebelarm und 0,70 kg rechnete; der zu
  lange Hebelarm drückt die Verstärkung genau um den Faktor, um den die leichte Rakete empfindlicher ist. Wer
  `Config.h` auf die gewogenen Werte setzt, muss die Gewinne mitändern.
- **Im Raster sieht Kp 2, Kd 0,5 von 705 bis 631 g gut aus** (2,3 bis 2,5° Kipp, nie am Anschlag), aber nur mit der
  Servo-Totzeit des SG90-Fits (30 ms). Mit 50 ms kippt dieser Satz bei 631 g auf 19 % Anschlag (§4b). Unter etwa
  600 g muss Kd weiter herunter (P3: Kd 0,25). Faustregel: Kd mit dem Quer-Trägheitsmoment skalieren.
- **Gipfel:** 74 m (Ausgangslage), 86 m (P1), 103 m (P2), 124 m (P3), ohne Luftwiderstand; mit ihm etwa 10 % weniger
  (`docs/Physik_Review_2026-10-23.md`, P1). Die Zahlen vom 22.10. (63 m) rechneten mit dem Simulink-Treibstoffmodell
  (60 statt 28 g) und waren zu niedrig.

Alle Werte hängen an der Servo-Umrechnung (6 angenommen, `Config.h` sagt 23) und an der Servo-Dynamik vom SG90-Fit
2025. Experiment E01 (Branch `experiments/servo-ident`) misst beides am gebauten Kardan; danach die Gewinne neu suchen.

## 4b. Bayes-Optimierung statt Raster

Das Raster oben rechnet 20 Punkte mit je drei Flügen und nur einer Servo-Totzeit. Mit dem Integralanteil als drittem
Parameter und einem robusten Ziel wird es teuer, deshalb sucht `scripts/tune_bayes.py` die Gewinne mit einem
Bayes-Optimierer (`tvcsim/bayesopt.py`: Gauß-Prozess mit Matérn-5/2-Kern, Expected Improvement, Kp und Kd auf
logarithmischen Achsen, nur numpy und scipy, Test in `tests/test_bayesopt.py`). Jeder Punkt ist ein kleines
Monte-Carlo aus vier Flügen: zwei Rausch-Seeds je Servo-Totzeit 30 und 50 ms, weil die W5652H am gebauten Kardan
noch nicht vermessen sind. Ziel (kleiner ist besser): mittlerer Kipp + halber schlechtester Kipp + 20 × Anteil am
Anschlag + halber seitlicher Versatz bei Brennschluss. 35 Punkte je Paket, alle vier Pakete parallel in 15 Minuten.

| Paket | gefunden Kp / Ki / Kd | Kipp mittel / schlechtester | Anschlag | seitlich bei Brennschluss |
|---|---|---|---|---|
| Ausgangslage 705 g | 2,42 / 1,50 / 0,44 | 2,1° / 2,3° | 0 % | 1,0 m |
| P1 672 g | 1,97 / 1,50 / 0,43 | 2,3° / 2,4° | 0 % | 1,2 m |
| P2 631 g | 1,82 / 1,13 / 0,40 | 2,4° / 2,5° | 0 % | 1,4 m |
| P3 593 g | 1,50 / 0,77 / 0,29 | 2,6° / 2,9° | 0 % | 1,9 m |

Ein gemeinsamer runder Satz, mit demselben robusten Ziel nachgerechnet (`tune_bayes.py --eval`):

| Satz Kp / Ki / Kd | 705 g | 672 g (P1) | 631 g (P2) | 593 g (P3) |
|---|---|---|---|---|
| **2 / 1 / 0,45** | 2,3/2,4°, 0 %, 1,3 m | 2,4/2,5°, 0 %, 1,3 m | 2,8/3,3°, 6 %, 1,4 m | 4,1/5,7°, 34 %, 2,0 m |
| 2 / 0 / 0,5 (Raster) | 2,5/2,6°, 0 %, 1,8 m | 3,7/5,3°, 7 %, 1,8 m | 3,8/6,1°, 19 %, 2,0 m | 5,1/6,5°, 48 %, 2,6 m |
| 5 / 0 / 1 (`Config.h`) | 5,7/7,8°, 69 %, 1,7 m | 7,2/9,5°, 75 %, 2,1 m | 7,7/10,2°, 77 %, 2,4 m | 8,9/11,5°, 82 %, 2,8 m |

Lesart: **Kp 2 / Ki 1 / Kd 0,45 ist der Satz für *Kartonaut 1*** in der Ausgangslage und mit P1. Für P2 und P3 gelten
die eigenen Werte aus der ersten Tabelle. Der Integralanteil gleicht die statische Fehlausrichtung des Kardans aus
und drückt den seitlichen Versatz um ein Drittel; Ki lag bei zwei Paketen am Rand des Suchraums (1,5). In der
Firmware den I-Anteil erst ab der Starterkennung laufen lassen und begrenzen, damit er auf der Rampe nicht aufläuft.
Gegen das Raster spricht nicht die Rechenzeit allein: Das Raster hatte nur eine Servo-Totzeit gerechnet und hätte
einen Satz empfohlen, der mit langsameren Servos ein Fünftel der Brennzeit am Anschlag steht. Nach Experiment E01
(Servo-Gain, Totzeit und Rate am gebauten Kardan gemessen) `tune_bayes.py` mit den gemessenen Werten neu laufen lassen.

## 5. Landung mit Beinen statt Fallschirm

Die Cloud-Session hat das Landebrennen mit einem zweiten TSP E12 gründlich gerechnet (Branch `landing-burn`,
`docs/Physik_Review_2026-10-23.md` §3): Luftwiderstand, Bodenkontakt mit Hüpfern, Zündentscheidung aus Höhe und
Sinkrate (`LandingPlanner`, auch in der Firmware als `LandingBurn.cpp`). Ich habe ihre Studie für die Massen
nachgerechnet, die eine Landeversion von *Kartonaut 1* hätte.

**Was die Landeversion wiegt.** Stand 2c ohne Motor wiegt 641 g. Ohne Fallschirm und CO₂-Modul (−94 g), dafür mit
dem zweiten Motor (64 g), der leeren Hülse des ersten (36 g), einem Doppelmotor-Halter (ca. 25 g) und einem Antrieb
für die Beine (ca. 10 g) sind es bei der Landezündung 682 g plus Beine:

| Beine | Masse bei der Landezündung | Start | mit Fallschirm als Reserve |
|---|---|---|---|
| 80 g (leicht, Carbonstäbe) | 762 g | 790 g | 856 g |
| 120 g | 802 g | 830 g | 896 g |
| 200 g (Vorgabe Modell `voll`) | 882 g | 910 g | 976 g |

**Was die Landung bei diesen Massen ergibt** (`landing_study.py`, Aufstieg und Landung mit je einem E12, Cd·A
0,003 m², Zündverzug 100 ms angenommen; Monte-Carlo mit Schub ±10 %, Zündverzug 50 bis 200 ms, Masse ±20 g,
Höhe ±0,3 m, Sinkrate ±0,3 m/s; 80 Läufe bei 0,70 und 0,75 kg, 40 Läufe darüber):

| Landemasse | Bremsvermögen | Gipfel | Aufsetzen nominal | Monte-Carlo: Median | 90 % der Läufe unter | Läufe unter 2 m/s |
|---|---|---|---|---|---|---|
| 0,70 kg | 20 m/s | 61 m | 4,8 m/s | 11,8 m/s | 14,6 m/s | 0 % |
| 0,75 kg | 17 m/s | 50 m | 2,7 m/s | 8,9 m/s | 12,8 m/s | 0 % |
| 0,80 kg | 14 m/s | 41 m | 2,7 m/s | 8,5 m/s | 11,0 m/s | 0 % |
| 0,85 kg | 11 m/s | 34 m | 1,5 m/s | 8,1 m/s | 9,9 m/s | 5 % |
| 0,90 kg | 8 m/s | 27 m | 0,6 m/s | 6,7 m/s | 10,9 m/s | 2 % |

Lesart:

- **Nominal geht es, real fast nie.** Bei 0,85 bis 0,90 kg passt der E12-Gipfel zum Bremsvermögen desselben Motors,
  und die Rakete setzt im Nominalfall mit 0,6 bis 1,5 m/s auf. Mit den Streuungen, die ein Feststoffmotor und ein
  Anzünder wirklich haben, landen nur 2 bis 5 von 100 Flügen unter 2 m/s; der typische Aufsetzer liegt bei 7 bis
  8 m/s, jeder zehnte über 10 m/s. Das entspricht einem Fall aus 3 bis 5 m Höhe.
- **Der Grund ist die Physik des Feststoffmotors.** Er hat nur eine Stellgröße, den Zündzeitpunkt. Für eine weiche
  Landung müssen Geschwindigkeit null, Höhe null und Brennschluss zusammenfallen: zwei Bedingungen, eine Stellgröße.
  Der E12 schiebt im Schwanz der Kurve mehr als das Gewicht; setzt die Rakete vor Brennschluss auf, hebt sie wieder
  ab. ±10 % Schub sind bei 0,8 kg schon ±4 m/s Bremsvermögen.
- **Leichter macht die Landung härter.** Die leichte Rakete steigt mit dem E12 höher und fällt schneller, als
  derselbe E12 bremsen kann. Das ist genau die Gegenrichtung zum Leichtbau aus §3: Für eine Landung müsste die Rakete
  bei 0,85 bis 0,90 kg liegen, nicht bei 0,6.
- **Es fehlt außerdem Hardware.** Der gebaute Kardan hält einen Motor; ein Doppelhalter (leere Hülse wird
  ausgestoßen, der zweite Motor rückt nach) verlängert ihn um eine Motorlänge (95 mm) und ist nicht konstruiert.
  Die Beine und ihr Ausklappen sind offen. Ob die finnenlose Rakete nach dem Gipfel mit der Düse nach unten fällt,
  kann die Simulation nicht sagen: ohne Schub hat der Kardan keine Wirkung, und Aerodynamik ist nicht modelliert.
- **Ein Fehlversuch kostet die ganze Rakete.** Ohne Fallschirm trifft sie bei einer Fehlzündung mit 15 bis 30 m/s
  auf, mit Platine (der teuerste Posten im Budget) und Kardan. Einen Fallschirm als Reserve mitzunehmen kostet 94 g
  und hilft nur, wenn er vor der Landezündung entschieden wird; nach einer Fehlzündung in 25 m Höhe bleibt keine Zeit
  zum Öffnen.

Was eine Landung realistisch machen würde, in dieser Reihenfolge: den Zündverzug des Anzünders am Boden messen
(zwanzig Stück, er dominiert die Streuung); die Schubstreuung des E12 aus dem Erstflug-Log ablesen; die Höhe in den
letzten Metern mit einem Laser-Entfernungsmesser statt dem Barometer (VL53L1X oder TF-Luna an `J_QWIIC`, auf der
Platine vorgesehen); einen Landemotor mit flacherer Kurve oder niedrigerem Schwanz; die Lage im freien Fall aus dem
Erstflug-Log kennen. Erst wenn die Monte-Carlo-Rechnung mit gemessenen Streuungen ein Fenster zeigt, lohnt die
Mechanik.

## 6. Empfehlung

1. ***Kartonaut 1* fliegt am Fallschirm.** Die Landung mit dem E12 gelingt mit den heute realistischen
   Streuungen in 2 bis 5 von 100 Versuchen, und ein Fehlversuch zerstört Platine und Kardan. Der Erstflug liefert
   dafür genau die Daten, die eine Landung später braucht: Schubkurve und Streuung aus dem Beschleunigungssensor,
   Lage nach Brennschluss (Auslösung des Schirms 1 bis 2 s nach dem Gipfel, dann sieht man den freien Fall),
   Barometer am Boden. Die Landung wird *Kartonaut 2* oder später, mit gemessenem Zündverzug und Laser-Höhe.
2. **Druckteile Stand 2c drucken** (in diesem Branch, STL in `cad/export/modular/`). Sie sparen 16 g und sind
   geprüft.
3. **Paket P1 umsetzen**, wenn es ohne Konzeptänderung gehen soll: 2S 300 mAh, Ringadapter, Mikroservo,
   Spitzen-Kuppler 50 mm. Zusammen 705 → 672 g.
4. **Federausstoß und 100-cm-Schirm (P2, 631 g) nur, wenn du die Entscheidung für CO₂ ändern willst.** Der Gewinn
   ist echt (−41 g), aber die Sinkrate steigt auf 4,3 m/s, und das landet ohne Beine auf Kardan und Servos.
5. **Gedruckte Spitze (P3) nicht für den Erstflug.** Sie bringt am meisten, verkürzt aber den Hebelarm auf 157 mm
   und verlangt neu abgestimmte Gewinne; das lohnt erst, wenn die Servos vermessen sind.
6. **`Config.h` mit kleineren Gewinnen**, sobald Masse und Hebelarm gewogen eingetragen werden: Kp 2, Ki 1, Kd 0,45
   statt 5, 0 und 1 (Bayes-Optimierung in §4b); I-Anteil erst ab der Starterkennung und begrenzt. Nach Experiment E01 (Servo am gebauten Kardan) die Gewinne mit
   `scripts/tune_bayes.py` neu suchen.
