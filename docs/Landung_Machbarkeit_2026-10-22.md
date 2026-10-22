# Landung mit dem zweiten Motor: Machbarkeit (TSP E12)

Stand 2026-10-22. Rechnung: `simulation/scripts/landing_feasibility.py` (senkrechte Bewegung, Luftwiderstand
des Rumpfs Cd 0,6, Schubkurve des TSP E12, Abbrand proportional zum Impuls, Zündverzug zwischen Kommando
und Schubbeginn). Eine Machbarkeitsrechnung, keine Flugsimulation: Lage, Regler und Wind fehlen.

## Ergebnis in einem Satz

**Mit dem TSP E12 ist eine Motorlandung der geplanten Landekonfiguration nicht machbar, und auch eine
deutlich leichtere Rakete braucht eine Zündgenauigkeit von etwa 10 ms und eine Höhengenauigkeit von
etwa 0,2 m, die mit Anzünder und Barometer nicht erreichbar sind.**

## 1. Landekonfiguration (Beine, zwei Motoren)

| Größe | Wert |
|---|---|
| Rakete ohne Motoren | 942 g (`cad/mass_properties.json` voll, ohne Motor, + 25 g Doppelmount geschätzt) |
| Start mit zwei E12 | 1070 g, Schub/Gewicht im Mittel **1,04** |
| Gipfel mit Motor 1 | **14 m** |
| Masse bei der Landezündung | 1042 g, Gewicht 10,2 N gegen 10,9 N mittleren Schub |
| Was der E12 an Sinkgeschwindigkeit abbauen kann | höchstens **2,8 m/s** über die ganze Brenndauer |

Der E12 schiebt im Mittel kaum mehr als das Gewicht. Er kann die Rakete nur abfangen, wenn sie fast
steht. Ballistisch vom Gipfel gibt es mit 0,2 s Zündverzug genau eine Kommandohöhe, die unter 2 m/s
landet; mit 0,5 s Verzug keine. Am Fallschirm (3,6 m/s, Schirm wird bei der Zündung abgeworfen) gibt
es keine: 3,6 m/s ist mehr, als der Motor abbauen kann.

## 2. Leichtere Rakete

| Rakete ohne Motoren | Gipfel mit Motor 1 | Abbaubar | Fenster für ≤ 2 m/s |
|---|---|---|---|
| 0,80 kg | 27 m | 10,5 m/s | einzelne Punkte |
| 0,70 kg | 41 m | 16,4 m/s | einzelne Punkte |
| 0,60 kg | 62 m | 24,2 m/s | einzelne Punkte |

Es gibt für jede Masse eine Kommandohöhe, die sanft landet, aber kein Fenster um sie herum.
Empfindlichkeit bei 0,70 kg (Hülse ausgestoßen, Kommando optimal für 300 ms Verzug):

| Abweichung | Aufsetzgeschwindigkeit |
|---|---|
| keine | 1,3 m/s |
| Zündverzug ±10 ms | 2,6 bis 4,4 m/s |
| Zündverzug ±50 ms | 5,0 bis 7,5 m/s |
| Höhenfehler ±0,2 m | 3,0 bis 4,9 m/s |
| Höhenfehler ±1 m | 6,0 bis 8,9 m/s |

Warum: Ein Feststoffmotor lässt sich nicht drosseln und nicht abschalten. Zündet er zu früh, steht die
Rakete über dem Boden und steigt mit dem Restschub wieder; zündet er zu spät, reicht der Weg nicht. Mit
einem Schub knapp über dem Gewicht ist die Bremsstrecke lang und jede Millisekunde zählt. Der Zündverzug
eines Anzünders streut typisch um Zehntelsekunden, das Barometer hat am Boden ±0,3 m Rauschen und mehr
Fehler durch Bodeneffekt und Abgasstrahl.

## 3. Was eine Landung bräuchte

1. **Einen Landemotor mit deutlich mehr Schub als Gewicht** (Schub im Mittel ≥ 2 × Gewicht) und kurzer
   Brenndauer. Das verkürzt die Bremsstrecke, macht das Timing aber nicht weniger kritisch: Die
   Toleranz bleibt im Bereich weniger Hundertstelsekunden. Die Rechnung läuft für jede Schubkurve
   (`load_thrust_curve`), sobald ein konkreter, beziehbarer Motor feststeht.
2. **Den Zündverzug messen**, mit genau dem Anzünder, der fliegen soll, viele Male, am Schubstand. Erst
   dessen Streuung sagt, ob überhaupt ein Fenster existiert.
3. **Eine bessere Höhe in den letzten Metern**: Laser- oder Ultraschall-Entfernungsmesser (ToF, z. B.
   VL53L1X oder TF-Luna an `J_QWIIC`, in `Komponenten_2026-10-22.md` schon als Erweiterung vorgesehen)
   statt Barometer.
4. **Zündung aus dem gemessenen Zustand** (Höhe und Sinkgeschwindigkeit, laufend vorausgerechnet) statt
   einer festen Kommandohöhe; das ist Firmware-Arbeit für später (Zustand `LANDING_BURN`).
5. **Lage beim Fall:** Ohne Schub hat der Regler keine Stellmöglichkeit. Ob die finnenlose Rakete nach
   dem Gipfel mit der Düse nach unten fällt, kann `tvcsim` nicht sagen (keine Aerodynamik). Am Schirm
   hängt sie definiert, aber dort reicht der Schub nicht (§1).

## 4. Folgen für den Doppelmotor-Mount

Der Mount (zwei Motoren in einem Kardan, leere Hülse wird nach Brennschluss per Feder ausgestoßen, der
zweite Motor rückt nach) ist mechanisch machbar, aber er wäre heute für einen Motor konstruiert, mit dem
die Landung nicht geht. Länge, Durchmesser, Schubring und Federweg hängen am Landemotor, und der Mount
verlängert den Kardanteil um eine Motorlänge (≈ 95 mm beim E12). Das schiebt bei ±7° die Oberkante des
Motorstapels in den Bereich des Schlüsselschalter-Kragens und des Flugcomputer-Kupplers
(`cad/params.py`: Kragen ab z = 107 mm, Kuppler ab 127 mm). Die Avionik müsste nach oben, der
Schwerpunkt wandert mit.
