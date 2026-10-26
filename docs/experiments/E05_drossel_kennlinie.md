# E05: Kennlinie der Schubdrossel (Scout-F-Pads)

Stand 2026-10-23. Ziel: die Kennlinie Pad-Stellung → Axialschub (`f(u)` in `tvcsim.params.ThrottleParams`,
`THROTTLE_F_MIN` und `THROTTLE_SERVO_*_DEG` in `Config.h`), die Stellzeit der Pads und ihre
Standfestigkeit im Abgasstrahl. Ohne diese Zahlen rechnen Simulation und Firmware mit einer
linearen Kennlinie und einem geratenen Mindestschub `f_min = 0,5`.

## Was gemessen wird

| Größe | Methode | Landet in |
|---|---|---|
| Axialschub über der Pad-Stellung | E12 auf dem TVC-Prüfstand (`cad/testrig.py`) mit Kraftmessung in Achsrichtung (Wägezelle 5 kg unter dem Rahmen oder Rakete kopfüber auf einer Waage mit Datenlogger), Pads in fünf festen Stellungen 0 / 25 / 50 / 75 / 100 %, je ein Motor | `f(u)`, `f_min`; falls nicht linear: Tabelle statt Gerade |
| Querkraft und Moment bei asymmetrischer Stellung | wie oben, ein Pad 50 %, das andere 0 % | Entscheidung, ob die Pads auch steuern dürfen |
| Stellzeit der Pads | Servo-Sprung 0 → 100 % ohne Strahl, Kamera 240 fps oder Winkelsensor wie in E01 | `act_tau_s`, Servodynamik |
| Standfestigkeit | Pads nach jedem Brennen wiegen und fotografieren; Material (Edelstahl 1 mm, Graphit, Keramikfaserplatte) | Werkstoffwahl, Lebensdauer |
| Zündverzug des Anzünders | Zeit von Zündkommando bis Schubanstieg (Pyro-Kanal 2 schaltet, Wägezelle) | `LANDING_IGNITER_DELAY_S`, `MotorParams.igniter_delay` |

## Aufbau

- Prüfstand nach `cad/testrig.py`, Rakete oder Motorrohr mit Kardan und Drosselmechanik, Kardan
  auf Mitte fixiert.
- Wägezelle in der Schubachse (5 kg, HX711 oder ADC am Teensy, 80 Hz), vorher mit Gewichten
  kalibriert. Alternativ die Rakete kopfüber auf eine Küchenwaage mit Datenlogger stellen.
- Pads über die Firmware auf feste Stellungen fahren: Umgebung `servo_ident` mit `M T <deg>`,
  sobald der Drosselkanal dort eingetragen ist, oder ein kleiner Sketch, der `Throttle_set(u)` auf
  USB-Kommando setzt.
- Je Stellung ein Motor; die E12 streut selbst um ±10 %, deshalb den Vollschub (Pads draußen) als
  Bezug am selben Tag mitmessen. Mindestens 6 Motoren: 0, 50, 100 % je zweimal.
- Sicherheit: 10 m Abstand, Zündung über die Bodenstation oder Zündkasten, Strahlplatte, Brandschutz.

## Auswertung

Kraftverlauf je Motor, Impuls und mittlerer Schub im Plateau (1 bis 3 s) im Verhältnis zum
Vollschub-Motor desselben Tages → `f(u)` als Punkte, lineare Regression, `f_min` = Wert bei 100 %.
Zündverzug = Zeit zwischen Pyro-Kommando und 2 N Schub. Stellzeit aus Video oder Winkelsensor.
Danach `THROTTLE_F_MIN`, `THROTTLE_SERVO_OUT_DEG/IN_DEG`, `THROTTLE_ACT_TAU_S`,
`LANDING_IGNITER_DELAY_S` eintragen und `scripts/throttle_study.py` neu laufen lassen.

## Grenzen

- Die Pads sehen am Prüfstand denselben Strahl wie im Flug, aber keinen Fahrtwind; der Einfluss auf
  die Ablenkung ist klein.
- Die Querkraft ist nur grob messbar; für den Flug zählt, dass sie bei symmetrischer Stellung null
  ist (Pads gleich tief, gleiche Servos, gleiche Hebel).
