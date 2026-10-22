# Physik-Durchsicht 23.10.2026 und Landebrennen mit dem zweiten Motor

Anlass: Jans Frage, ob die Physik stimmt und ob eine Landung mit dem zweiten Motor geht. Geprüft
wurden das Simulink-Portmodell in `simulation/tvcsim/` und die physikalischen Annahmen der
Firmware (`firmware/src/ControlLaw.cpp`, `Attitude.cpp`, `FlightState.cpp`). Die Landestudie
steht in Abschnitt 3, die Umsetzung in Abschnitt 4.

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

## 4. Umsetzung

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
