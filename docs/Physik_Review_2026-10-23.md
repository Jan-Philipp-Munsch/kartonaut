# Physik-Durchsicht 23.10.2026 und Landebrennen mit dem zweiten Motor

Anlass: Jans Frage, ob die Physik stimmt und ob eine Landung mit dem zweiten Motor geht. Geprüft
wurden das Simulink-Portmodell in `simulation/tvcsim/` und die physikalischen Annahmen der
Firmware (`firmware/src/ControlLaw.cpp`, `Attitude.cpp`, `FlightState.cpp`). Die Landestudie
steht in Abschnitt 3, die Drossel in Abschnitt 4, die Umsetzung in Abschnitt 5.

## 1. Was stimmt

- **Starrkörper, Quaternion, Euler-Gleichungen** (`dynamics.py`): Kinematik `q̇ = ½ q ⊗ ω`,
  Drehung Körper → inertial, Momente `M = r × T` mit dem Kardanpunkt `l` unter dem Schwerpunkt.
  Die Tests prüfen das gegen `scipy.spatial.transform.Rotation` (Produkt, Drehrichtung,
  Integration mit konstanter Rate, Schwebe-Gleichgewicht). Vorzeichen der TVC-Winkel sind
  dokumentiert und getestet.
- **Schubkurve TSP E12** aus thrustcurve.org: 38,6 Ns, Spitze 28,3 N bei 0,54 s, dann 3 s lang
  11 N, Brennschluss 3,54 s. Masse mit Abbrand proportional zum Impuls (`fuel_model="impulse"`).
- **Firmware-Regelgesetz**: `M = l·m·|a|·sin δ` mit der spezifischen Kraft `|a|` ist die richtige
  Schätzung des Schubs (sie enthält schon den Luftwiderstand); die Momentenumrechnung ist
  identisch zur Simulation (Software-in-the-Loop-Test). Der Kippwinkel aus dem Oben-Vektor der
  Gyro-Quaternion gilt auch bei Rollen (Test `roll_does_not_leak_into_tilt`).
- **Kalman** rechnet mit der Beschleunigung im Navigationssystem minus g; mit der eigenen
  Quaternion ist das jetzt konsistent (vorher drehte die DMP-Quaternion).

## 2. Befunde und was geändert wurde

| # | Befund | Folge | Änderung |
|---|---|---|---|
| P1 | **Kein Luftwiderstand** im Simulink-Modell und im Port. Bei 30 m/s wirkt auf den Rumpf (Ø 75 mm, Cd ≈ 0,7, A = 0,0044 m²) etwa 1,9 N, ein Viertel des Gewichts. Für den Aufstieg ist das ein Höhenfehler von etwa 10 %, für die Landung bestimmt es die Fallgeschwindigkeit (Endgeschwindigkeit 59 m/s bei 0,76 kg). | Gipfelhöhen zu hoch, Fall zu schnell | `VehicleParams.cd_a` (Cd·A, Vorgabe 0 wie Simulink; `VehicleParams.light()` setzt 0,003 m²), `D = −½ ρ Cd A \|v\| v` angriffsfrei in `eom()`. Kein aerodynamisches Moment: die Rakete hat keine Flossen, der Druckpunkt liegt nahe am Schwerpunkt; das bleibt eine Annahme. |
| P2 | **Beschleunigungsmessung** im Simulink-Modell ist `rdd` (mit g), ein echter Sensor misst die spezifische Kraft (Abweichung 7 im Simulations-README). | Schubschätzung beim Abheben und nach Brennschluss falsch | Bleibt als Schalter `accel_model`; alle neuen Studien und die Firmware-Testvektoren laufen mit `specific_force`. |
| P3 | **Treibstoffmodell** `signalbuilder` (Vorgabe, 60 g nur für Motor 1) passt nicht zur E12 (28 g). | Masse im Aufstieg um 32 g zu hoch | Landestudie und Testvektoren mit `fuel_model="impulse"`, 28 g je Motor. |
| P4 | **Zündung des zweiten Motors nach Zeit** (7,3 s) im Simulink-Modell trifft die fallende Rakete oder kommt nach der Landung (Befund 14). | Keine Landung simulierbar | `MotorParams.second_mode = "landing"`: Zündung aus Höhe und Sinkrate (Abschnitt 3), Zündverzug, Schubtoleranz. |
| P5 | **Boden** nur als Stopp bei der ersten Berührung. Ein Feststoffmotor mit T/W > 1 im Schwanz der Kurve hebt die Rakete nach dem Aufsetzen wieder ab (Hüpfer). | Landung sah weicher aus, als sie ist | Bodenkontakt in `sim.py`: liegen bleiben, solange der Schub nicht trägt, sonst abheben; jedes Aufsetzen wird mit Geschwindigkeit protokolliert (`extra["contacts"]`). |
| P6 | **Servos ohne Schub**: der Firmware-Regler in der Simulation stellte im freien Fall die Servos an den Anschlag (`asin` mit kleinem \|a\|). Die Firmware stellt sie seit dem 22.10. außerhalb von BOOST/LANDING_BURN auf Mitte. | Transiente bei der Zündung | `FirmwareParams.coast_center` (Vorgabe an). |
| P7 | **Trägheitsmomente** sind Platzhalter 0,1 kg·m², solange nicht `--vehicle cad`; Izz ist hundertmal kleiner (Befund 15). | Rollregelung in der Simulation unrealistisch | Unverändert; `VehicleParams.light()` skaliert die Erstflug-Werte mit der Masse. |
| P8 | **Firmware-Masse** `MASS_KG` ist konstant, die Rakete verliert 28 g je Motor (4 %); der Hebelarm wandert mit dem Schwerpunkt um etwa 12 mm. | Stellmoment 4 % daneben | Unkritisch für den Regler (Verstärkungsfehler), Hinweis in `Config.h`. |

Nicht geprüft werden konnten: Schubvektor-Fehlstellung durch Spiel im Kardan (nur als statischer
Fehler modelliert), Wind, Motor-zu-Motor-Streuung der E12 (angenommen ±10 %).

## 3. Landestudie: Landebrennen mit der E12

Ein Feststoffmotor hat nur eine Stellgröße: den Zündzeitpunkt. Nettobremsvermögen
`∫(F − m g) dt / m` der E12 ohne Luft:

| Landemasse | 0,50 kg | 0,60 kg | 0,70 kg | 0,76 kg | 0,85 kg | 1,00 kg |
|---|---|---|---|---|---|---|
| Bremsvermögen | 35 m/s | 30 m/s | 20 m/s | 16 m/s | 11 m/s | 4 m/s |
| T/W im Schwanz (11 N) | 2,3 | 1,9 | 1,6 | 1,5 | 1,3 | 1,1 |

Das Problem ist nicht das Bremsvermögen, sondern die **Form der Kurve**: 28 N für 0,3 s, dann
11 N für 3 s. Mit T/W > 1 im Schwanz kann die Rakete nicht schweben. Setzt sie vor dem Brennschluss
auf, hebt der Schwanz sie wieder ab und sie fällt nach dem Brennschluss aus der Hüpfhöhe; stoppt
sie in der Luft, fällt sie von dort. Eine weiche Landung verlangt, dass Geschwindigkeit null
**und** Höhe null **und** Brennschluss zusammenfallen: zwei Bedingungen, eine Stellgröße. Das geht
nur, wenn die Fallgeschwindigkeit beim Zünden genau zum Bremsvermögen passt, also bei genau einem
Gipfel je Masse.

Zündentscheidung (`tvcsim/landing.py`, `LandingPlanner`): jeden Takt werden die *Aufsetzkosten*
J (größte Aufsetzgeschwindigkeit bis zur Ruhe, 1D mit Bodenkontakt und Hüpfer) für „jetzt zünden“
und „einen Takt später zünden“ gerechnet, beide um den Zündverzug vorausgesagt; gezündet wird im
Minimum. Das deckt alle Fälle ab (Stopp in der Luft, Hüpfer, zu schnell) und braucht keine
Tabelle. Die Firmware rechnet dasselbe (`LandingBurn.cpp`, Test gegen Python-Werte).

Ergebnis in 1D (Aufstieg mit derselben E12, Cd·A = 0,003 m², Zündverzug 100 ms), Zahlen aus
`scripts/landing_study.py` (`out/landing_study.png`):

| Landemasse | Gipfel E12 | Zündung | Aufsetzen nominal | bester Gipfel → Aufsetzen |
|---|---|---|---|---|
| 0,50 kg | 125 m | 47 m, −34 m/s | **18 m/s** | 128 m → 18 m/s (Bremsvermögen reicht nicht) |
| 0,60 kg | 88 m | 44 m, −28 m/s | **9 m/s** | 128 m → 4 m/s |
| 0,70 kg | 61 m | 38 m, −21 m/s | **4,8 m/s** | 78 m → 0,5 m/s |
| 0,75 kg | 50 m | 34 m, −18 m/s | **2,7 m/s** | 56 m → 0,4 m/s |
| 0,80 kg | 41 m | 30 m, −15 m/s | **2,7 m/s** | 48 m → 0,9 m/s |
| 0,90 kg | 27 m | 22 m, −10 m/s | **0,6 m/s** | 26 m → 0,4 m/s |

Monte-Carlo ohne Drossel (60 Läufe je Masse, Schub ±10 %, Zündverzug 50–200 ms, Masse ±20 g,
Höhe ±0,3 m, Sinkrate ±0,3 m/s): Median des härtesten Aufsetzens 24 m/s (0,5 kg), 16 m/s (0,6),
12 m/s (0,7), 10 m/s (0,75 und 0,8), 7,5 m/s (0,9); **kein einziger Lauf unter 2 m/s** bis 0,8 kg,
2 % bei 0,9 kg. Ohne Drossel ist die Landung mit der E12 also nur nominal, nicht robust.

Lesart: **Je leichter, desto härter.** Die leichte Rakete steigt mit der E12 höher und fällt
schneller, als dieselbe E12 bremsen kann; bei 0,5 kg reicht nicht einmal das Bremsvermögen. Unter
0,7 kg landet nichts weich. Bei 0,75 bis 0,80 kg passt der E12-Gipfel ungefähr zum Bremsvermögen,
nominal 2,7 m/s. Das ist die Grenze dessen, was Landebeine wegstecken (Vorgabe: 2 m/s). Die
Monte-Carlo-Streuung (Schub ±10 %, Zündverzug 50 bis 200 ms, Masse ±20 g, Höhe ±0,3 m, Sinkrate
±0,3 m/s) steht in der Tabelle des Skripts; sie ist groß, weil ±10 % Schub bei 0,76 kg schon ±4 m/s
Bremsvermögen sind.

Was helfen würde, in dieser Reihenfolge:

1. **Gipfel wählen statt Masse drücken**: Aufstieg mit einem schwächeren Motor (D-Klasse) oder mit
   Ballast, so dass der Gipfel zum Bremsvermögen passt (0,70 kg: 78 m statt 61 m ist falsch herum,
   0,80 kg: 48 m statt 41 m). Mit der E12 auf beiden Seiten bleibt die Masse 0,75 bis 0,80 kg.
2. **Motor mit flacher Kurve** (Estes F15: 15 N über 3,4 s, T/W ≈ 1,9 bei 0,8 kg) oder mit
   niedrigerem Schwanz; die Spitze der E12 ist für das Bremsen gut, der Schwanz für die Landung
   schlecht.
3. **Zündverzug und Schub messen** (Experiment am Prüfstand): die Streuung dominiert das Ergebnis.
4. **Beine mit Federweg** für 3 m/s statt 2 m/s.

Die F35 (67,5 Ns, 2,2 s, Spitze 55 N) kann bei jeder Masse bremsen, braucht aber ±16 g am
Beschleunigungssensor (rev B) und einen Gipfel über 100 m; sie ist in `landing_study.py` über
`CURVE` wählbar.

## 4. Mit Schubdrossel (Scout-F-Pads, Jan 23.10.2026)

Jan baut eine Drossel nach BPS Scout F: zwei Pads schwenken symmetrisch unter der Düse in den
Abgasstrahl und lenken ihn seitlich ab (die „Throttlepads“ in den Blender-Dateien). Modell:
Axialschub = Motorschub · f(u), u ∈ [0, 1], f linear von 1 auf f_min, Pads mit der Servodynamik
des Kardans (PT2, 30 ms Totzeit), Zusatzmasse 60 g. f_min ist unbekannt (Experiment E05); gerechnet
wurden 0,3 / 0,5 / 0,7.

Damit wird aus dem Zündzeitpunkt eine Regelung (`tvcsim/throttle.py`, `firmware/src/ThrottleLaw.*`):

1. **Zündung mit Reserve**, geplant für den schwächsten erwarteten Motor (−10 %): zünden, sobald
   ein Vollschub-Brennen höchstens 3 m über dem Boden stoppen würde. Reicht das Bremsvermögen des
   schwachen Motors nie, gilt die Zündung im Kostenminimum wie ohne Drossel.
2. **Schubspitze ohne Drossel** (erste 0,8 s): dort wird das meiste Bremsvermögen geholt, und aus
   dem Beschleunigungssensor wird der wahre Maßstab der Schubkurve geschätzt.
3. **Zeitbasierte Führung** danach: die Restbrenndauer ist die harte Grenze; gefordert wird die
   Schubbeschleunigung, die Höhe und Sinkrate zum Brennschluss auf 0 bzw. −0,5 m/s bringt
   (Zero-Effort-Miss/-Velocity); die Drossel stellt f = T_bedarf / T_verfügbar in [f_min, 1].
4. **Endphase**: unter 0,8 m Sinkrate halten, unter 0,25 m Pads ganz hinein (Schubabbruch), sonst
   hebt der Schwanz der Kurve die aufgesetzte Rakete wieder ab. Liegen bleiben kann die Rakete nur,
   wenn f_min · 11 N unter dem Gewicht liegt: f_min < 0,53 bei 0,6 kg, < 0,45 bei 0,5 kg.

Drei Sackgassen auf dem Weg, als Warnung für spätere Änderungen: eine feste Sollkurve v(h)
verschenkt die Schubspitze; eine Regelung der Vollschub-Stopphöhe reagiert auf jeden Schätzfehler
mit unwiederbringlichem Bremsverlust; ohne Schätzung des wahren Schubs ist ein nominaler Motor für
den auf −10 % geplanten Regler „zu stark“ und die Rakete stoppt in der Luft.

Ergebnis (1D, Aufstieg mit derselben E12, `scripts/throttle_study.py`, `out/throttle_study.png`):

| Landemasse | f_min | Gipfel E12 | Zündung | Aufsetzen nominal | Monte-Carlo Median / 90 % | Anteil ≤ 2 m/s | Hüpfer |
|---|---|---|---|---|---|---|---|
| 0.50 kg | 0.3 | 125 m | 54 m, -33 m/s | **1.6 m/s** | 2.0 / 2.9 m/s | 40 % | 38 % |
| 0.50 kg | 0.5 | 125 m | 54 m, -33 m/s | **1.2 m/s** | 1.8 / 5.9 m/s | 57 % | 65 % |
| 0.50 kg | 0.7 | 125 m | 54 m, -33 m/s | **2.5 m/s** | 5.4 / 12.6 m/s | 0 % | 10 % |
| 0.55 kg | 0.3 | 106 m | 53 m, -30 m/s | **1.8 m/s** | 2.6 / 3.4 m/s | 12 % | 62 % |
| 0.55 kg | 0.5 | 106 m | 53 m, -30 m/s | **1.6 m/s** | 2.6 / 9.8 m/s | 20 % | 98 % |
| 0.55 kg | 0.7 | 106 m | 53 m, -30 m/s | **1.2 m/s** | 1.8 / 4.9 m/s | 60 % | 28 % |
| 0.60 kg | 0.3 | 88 m | 50 m, -26 m/s | **2.0 m/s** | 3.0 / 3.7 m/s | 0 % | 55 % |
| 0.60 kg | 0.5 | 88 m | 50 m, -26 m/s | **1.8 m/s** | 2.8 / 3.6 m/s | 18 % | 100 % |
| 0.60 kg | 0.7 | 88 m | 50 m, -26 m/s | **1.6 m/s** | 3.3 / 7.1 m/s | 25 % | 78 % |
| 0.65 kg | 0.3 | 74 m | 45 m, -23 m/s | **1.9 m/s** | 3.4 / 4.2 m/s | 2 % | 62 % |
| 0.65 kg | 0.5 | 74 m | 45 m, -23 m/s | **1.7 m/s** | 3.0 / 3.9 m/s | 2 % | 98 % |
| 0.65 kg | 0.7 | 74 m | 45 m, -23 m/s | **1.5 m/s** | 4.0 / 7.7 m/s | 5 % | 88 % |
| 0.70 kg | 0.3 | 61 m | 41 m, -19 m/s | **2.1 m/s** | 4.0 / 5.1 m/s | 0 % | 75 % |
| 0.70 kg | 0.5 | 61 m | 41 m, -19 m/s | **1.9 m/s** | 3.8 / 5.1 m/s | 0 % | 95 % |
| 0.70 kg | 0.7 | 61 m | 41 m, -19 m/s | **1.8 m/s** | 4.6 / 6.6 m/s | 0 % | 95 % |
| 0.80 kg | 0.3 | 41 m | 32 m, -13 m/s | **3.4 m/s** | 4.5 / 5.7 m/s | 0 % | 75 % |
| 0.80 kg | 0.5 | 41 m | 32 m, -13 m/s | **3.3 m/s** | 5.1 / 6.5 m/s | 0 % | 82 % |
| 0.80 kg | 0.7 | 41 m | 32 m, -13 m/s | **3.6 m/s** | 4.9 / 8.5 m/s | 0 % | 82 % |

Monte-Carlo wie oben (40 Läufe: Schub ±10 %, Zündverzug 50–200 ms, Masse ±20 g, Höhe ±0,3 m,
Sinkrate ±0,3 m/s); Hüpfer = zweites Aufsetzen mit mindestens 1 m/s. Ein 6DOF-Lauf mit Regler
(0,6 kg, f_min 0,5, Rauschen an) bestätigt die 1D-Zahlen: Zündung 49,7 m / −26 m/s, Aufsetzen
2,5 m/s, Kippwinkel 0,3° (`out/throttle_6dof_0.60.png`).

Lesart: **Mit Drossel dreht sich das Bild.** Die leichte Rakete, die ohne Drossel am härtesten
landete, wird landbar, weil ihr Bremsvermögen die Fallgeschwindigkeit übersteigt und die Drossel
den Überschuss wegnimmt: 0,5 bis 0,65 kg landen nominal mit 1,2 bis 2 m/s, im Monte-Carlo mit
2 bis 3 m/s im Median (ohne Drossel 16 bis 24 m/s). Bei 0,7 kg und mehr gibt es mit einem schwachen
Motor keinen Überschuss, dort hilft die Drossel nichts (0,8 kg: 3,4 m/s nominal, 4,5 bis 5 m/s im
Median). Die Beine müssen also 3 m/s wegstecken. Der zweite Befund ist der **Hüpfer**: in den
meisten Läufen setzt die Rakete nach dem ersten Kontakt noch einmal mit über 1 m/s auf, weil der
Schwanz der Kurve sie wieder anhebt, bevor die Pads ganz eingeschwenkt sind. Liegen bleiben
verlangt f_min · 11 N < Gewicht (0,5 kg: f_min < 0,45; 0,6 kg: < 0,53) und schnelle Pads; mit
f_min 0,3 bei 0,5 kg sinkt die Hüpferquote auf 38 %, mit f_min 0,7 ist die Drossel zu schwach, um
einen starken Motor wegzunehmen (90 %-Wert 5 bis 13 m/s). Was die Landung noch weicher
machen würde: schnellere Pads (die Servoverzögerung kostet in der Endphase am meisten), eine
gemessene Kennlinie statt der Geraden, und f_min deutlich unter dem Schwebewert, damit die Rakete
nach dem Aufsetzen sicher liegen bleibt.

## 5. Umsetzung

- `simulation/tvcsim/landing.py`: `impact_cost`, `LandingPlanner`, `IgnitionTable` (Zündhöhe für
  |v| ≤ v_tol, Anschauung), `net_braking_dv`; `sim.py` mit Landemodus, Bodenkontakt, Hüpfern;
  `scripts/landing_study.py`; 6 Tests.
- `firmware/src/LandingBurn.*`: derselbe Planer in C++ mit der E12-Kurve aus `ThrustCurveE12.h`
  (erzeugt von `scripts/export_landing_firmware.py`); `FlightState.*` mit `RECOVERY_MODE`
  (Fallschirm oder Landebrennen), Zustand `LANDING_BURN`, Rückfall auf den Fallschirm, wenn der
  Anzünder keinen Durchgang hat oder ABORT kommt; `Pyro.*` mit Freigabe je Kanal (Kanal 1
  Ausstoßladung, Kanal 2 Anzünder des Landemotors, 1 s Puls); 5 native Tests, darunter der
  Zustandsautomat auf dem simulierten Landeflug und die Aufsetzkosten gegen 60 Python-Werte.
- `Config.h`: `RECOVERY_MODE = CHUTE` für den Erstflug; `LANDING_*`-Parameter.
- Drossel: `tvcsim/throttle.py` (Modell, Regler, 1D-Landesimulation für Monte-Carlo), `ThrottleParams`,
  Aktuatorzustand und Schubfaktor in `sim.py`, `scripts/throttle_study.py`, 5 Tests;
  `firmware/src/ThrottleLaw.*` (Port, Test gegen Python-Vektoren), dritter Servokanal
  `PIN_SERVO_THROTTLE` (rev B: J_SERVO4), `THROTTLE_*` in `Config.h`, `THROTTLE_ENABLED = false`
  bis zur Mechanik; Experiment E05 (`docs/experiments/E05_drossel_kennlinie.md`).
