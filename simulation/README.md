# tvcsim: 6DOF-Simulation der TVC-Rakete in Python

Port des MATLAB/Simulink-Projekts `6DOF_model` (`TVC6DOF_sim.slx`, `TVC6DOF.m`, `pid_tuner.m`)
nach Python, wie in `docs/Plan_2026-10-21.md` Abschnitt 3 festgelegt. Zusätzlich zum
Simulink-Regler gibt es einen zweiten Regler, der genau wie die Firmware
(`firmware/src/Control.cpp` + `main.cpp`) rechnet, damit die Reglergewinne der Firmware
gegen die der Simulation verglichen werden können.

## Starten

Voraussetzungen: Python 3.10+, numpy, scipy, matplotlib (pytest für die Tests). Alle Skripte
laufen ohne Installation aus dem Ordner `simulation/`; alternativ `pip install -e simulation`.

```bash
cd simulation
python -m pytest tests                      # 52 Tests
python scripts/fit_servo.py                 # Servo-Fit gegen die Messung -> out/servo_fit.png
python scripts/run_nominal.py               # Nominallauf -> out/nominal_*.png
python scripts/run_nominal.py --controller firmware --vehicle preload --static-error-y 1
python scripts/run_montecarlo.py            # 100 Läufe à 7 s -> out/montecarlo_*.png, .csv
python scripts/tune_pid.py --kp-values 2 3.1 5 --ki-values 0 5 --kd-values 0.01 0.1 0.385
python scripts/compare_gains.py --vehicle preload   # Firmware- gegen Tuner-Gewinne
python scripts/ident_servo.py messung.csv   # Experiment E01 auswerten -> out/ident_*.png, .json
python scripts/ident_servo.py --synthetic   # dasselbe mit einer künstlichen Messung
python scripts/export_firmware_vectors.py   # Testvektoren für firmware/test/data/ (SIL, Flugprofil)
python scripts/landing_study.py             # Landebrennen mit der E12 nach Masse -> out/landing_study.png
python scripts/export_landing_firmware.py   # E12-Kurve und Prüfvektoren des Landeplaners für die Firmware
python scripts/throttle_study.py            # Landebrennen mit Schubdrossel: Masse × f_min, Monte-Carlo
python scripts/rate_study.py                # 100 gegen 250 Hz, Kardan-Reaktionsmoment, D-Tiefpass, Slew
```

Alle Ausgaben landen in `simulation/out/` (per `.gitignore` ausgeschlossen). Ein Lauf über
12 s dauert etwa 3 s, Monte-Carlo mit 100 Läufen à 7 s etwa 4 Minuten.

Wichtige Schalter von `run_nominal.py` (gelten auch für Monte-Carlo und Tuning):

| Schalter | Bedeutung |
|---|---|
| `--controller simulink\|firmware` | Simulink-Regler oder Port von `Control.cpp` |
| `--vehicle nominal\|preload\|cad\|stand2b` | Fahrzeugparameter aus `TVC6DOF.m`, aus dem PreLoadFcn der `.slx`, aus `cad/mass_properties.json` (Konfiguration `voll`, 981 g) oder aus `cad/mass_stand2b.json` (Modulbauweise *Kartonaut 1*, 723 g; siehe unten) |
| `--gains nominal\|tuner\|preload`, `--kp --ki --kd` | Gewinne des Simulink-Reglers |
| `--fw-kp --fw-ki --fw-kd --fw-mass --fw-servo-gain` | Konstanten des Firmware-Reglers (`Config.h`) |
| `--servo-gain 6` | Gain-Block hinter `tf5` (Servo-Grad je TVC-Grad; 23 laut `Config.h`) |
| `--accel rdd\|specific_force` | was der Beschleunigungssensor misst (Simulink: `rdd`) |
| `--fuel signalbuilder\|impulse` | Treibstoffmodell |
| `--no-noise`, `--static-error-y`, `--static-error-z`, `--mis-y`, `--mis-z` | Störungen |
| `--rate-hz 250\|100` | Regeltakt (Vorgabe 250 Hz wie die Firmware ab 11/2026; 100 = Simulink und alte Firmware) |
| `--imu-average auto\|on\|off` | Gyro/Accel als Mittel über den Takt (auto: an ab 200 Hz) |
| `--gimbal-inertia 5e-4` | Reaktionsmoment des Kardans an (wirksames Trägheitsmoment, kg m²) |
| `--servo-model sg90\|w5652h`, `--servo-rate` | Servomodell (SG90-Fit oder W5652H-Annahme), Ratengrenze in Servo-Grad/s |
| `--fw-d-lpf`, `--fw-slew` | Firmware: Tiefpass im D-Anteil (Hz), Ratenbegrenzung des Servokommandos (Servo-Grad/s) |

## Aufbau

```
simulation/
  data/      E12_thrustcurve.csv, F35_thrustcurve.csv (aus dem MATLAB-Projekt, Semikolon, s;N)
             servo_step_response.csv (aus "system identification.txt": t_ms, Soll, Kardan)
             m_fuel_signalbuilder.csv (Treibstoffkurve aus dem Signal Builder der .slx)
  tvcsim/    params.py     alle Parameter, Namen wie in MATLAB
             motors.py     Schub-Lookup, zweiter Motor nach secondburn Schritten, Treibstoffmasse
             dynamics.py   Port des Blocks "Equations of Motion" (Quaternion, Euler, TVC-Drehung)
             actuator.py   ZOH, Sättigung ±5°, PT2+Totzeit statt tf5, Gain 6, statische Fehler; Fit
             sensors.py    Avionics-Block (Rauschen auf q, w, rdd)
             estimator.py  Estimator-Block (T_est = |rdd_n| m)
             controller.py SimulinkController (PID + Moments2Commands), FirmwareController (Control.cpp)
             sim.py        Lauf: Regelschleife alle 4 ms (250 Hz), dazwischen RK4 mit 1 ms, Quaternion normiert
             montecarlo.py Port von TVC6DOF.m
             tuning.py     Port von pid_tuner.m
             plots.py      Höhe/Lage/Servo, 3D-Trajektorien, Servo-Fit
  tests/     Quaternionnorm, Schwebe-Gleichgewicht, Momentenvorzeichen, Regler gegeneinander
  scripts/   run_nominal.py, run_montecarlo.py, tune_pid.py, fit_servo.py, compare_gains.py,
             ident_servo.py (Experiment E01, Modul tvcsim/ident.py),
             export_firmware_vectors.py (Software-in-the-Loop-Vektoren für die Firmware-Tests),
             landing_study.py, export_landing_firmware.py (Landebrennen, tvcsim/landing.py),
             throttle_study.py (Schubdrossel, tvcsim/throttle.py),
             rate_study.py (Regeltakt, Reaktionsmoment, D-Tiefpass, Slew)
```

## Regeltakt 250 Hz und Reaktionsmoment des Kardans (seit 05.11.2026)

Die Firmware rechnet ab November 2026 mit **250 Hz** (Servo-PWM 250 Hz, Gyro und Beschleunigung als Mittel der
FIFO-Werte über den 4-ms-Takt, Barometer 50 Hz). Die Simulation folgt:

- `ControlParams.dt` ist jetzt **0,004 s** (`tvcsim.params.DT_CONTROL`). `SimParams.at_rate(100)` stellt
  0,01 s und Momentanwerte ein und rechnet die alten Zahlen bitgenau nach (geprüft gegen den Stand vor der
  Änderung, mit `A_NORM_ALPHA = 0,1`); alle Skripte mit `run_nominal`-Schaltern haben `--rate-hz`, ebenso
  `export_firmware_vectors.py` und `export_landing_firmware.py` (Vorgabe 250 Hz). Die RK4-Schrittweite bleibt
  ~1 ms (`SimParams.substeps = None` → `dt / 1 ms` Teilschritte).
- `NoiseParams.imu_average` (Vorgabe an): ω und a sind das Mittel über `[t_k − dt, t_k]` (Trapez über die
  Teilschritte), also 2 ms Gruppenlaufzeit bei 250 Hz. Das Rauschen bleibt 0,4 °/s je Takt.
- Der zweite Motor (`MotorParams.secondburn`) und der I-Reset des Simulink-Reglers liegen fest bei 7,3 s
  (Schritte zu 10 ms), unabhängig vom Regeltakt.
- `FirmwareController` wie `main.cpp`/`ControlLaw.cpp` ab 11/2026: |a|-Tiefpass zeitbasiert
  (`A_NORM_TAU_S = 0,095 s`, `y += (x − y) dt/(τ + dt)`; `A_NORM_ALPHA` = alter fester Faktor je Takt),
  I-Anteil auf ±`PY_INT_LIMIT` = 500 Grad·s begrenzt. Neu und optional: `D_LPF_HZ` (PT1 auf ω nur im
  D-Anteil) und `SERVO_SLEW_DPS` (Ratenbegrenzung des Servokommandos hinter dem Fenster).
- **Reaktionsmoment** (`VehicleParams.gimbal_inertia`, Vorgabe 0 = aus wie Simulink): beschleunigt der Servo den
  Kardan, dreht der Rumpf mit `−I_g θ̈` um dieselbe Querachse dagegen, und der Gyro sieht das. Wirksames
  Trägheitsmoment für Stand 2b `GIMBAL_INERTIA_STAND2B = 5e-4 kg m²` (bewegt: Motor 64 g, Adapter, Motorrohr,
  Innenrahmen; I um den Kardanpunkt 1,0e-4 plus Kopplung m·d·l = 4,1e-4, weil der Kardanschwerpunkt 28 mm unter
  dem Drehpunkt liegt), 2,4 % des Quer-Trägheitsmoments. Der Rotor des Servos selbst ist mit < 5 % davon
  vernachlässigt. Test `test_gimbal_reaction_conserves_angular_momentum` prüft die Drehimpulsbilanz.
- **Servo**: `ServoParams.rate_limit_dps` (Servo-Grad/s, 0 = aus) und `ServoParams.w5652h()`: Annahme für die
  W5652H am 2S, bis E01 misst: Verzögerung 25 ms als aperiodisches PT2 (ζ = 1, ωn = 80 rad/s, gleiche mittlere
  Verzögerung wie ein PT1 25 ms, aber endliche Beschleunigung), Totzeit 4 ms, 0,06 s/60° = 1000 Servo-Grad/s.

**Ergebnis** (`scripts/rate_study.py`, Stand 2b aus `levers`, Firmware-Regler **Kp 2 / Ki 1 / Kd 0,45**, wahre
Masse und Hebelarm, Servo-Umrechnung 6, ein Motor, Rauschen, statischer Fehler 1°/0,6°, Brennphase 0,05…3,55 s;
Kommandorate = Servo-Grad/s des Kommandos, Kardanrate = wirkliche Kardanbewegung in TVC-Grad/s; je Zelle
100 Hz / 250 Hz):

| Fall (SG90-Fit, ohne Reaktionsmoment) | Kipp max | Anschlag | Kommandorate p99 | Kommandorate RMS | Kommando RMS (Servo-Grad) | Kardanrate max |
|---|---|---|---|---|---|---|
| 705 g, Seeds 0..3, Totzeit 30/50 ms | 2,35…2,48° / 2,37…2,52° | 0 / 0 % | 270…430 / 690…800 | 65…87 / 172…182 | 2,5…3,1 / 2,6…3,1 | 15…18 / 15…17 °/s |
| P1 672 g | 2,46° / 2,48° | 0 / 0 % | 304 / 721 | 69 / 190 | 2,7 / 2,7 | 17 / 18 °/s |
| P2 631 g | 2,38° / 2,39° | 0 / 0 % | 275 / 782 | 75 / 204 | 2,9 / 2,8 | 19 / 20 °/s |
| P3 593 g | 2,59° / 2,50° | **6** / 0 % | 472 / 880 | 214 / 283 | 9,3 / 6,4 | 78 / 40 °/s |
| statischer Fehler 2°/2° | 7,57° / 7,71° | 0 / 0 % | 312 / 692 | 110 / 226 | 5,8 / 5,8 | 34 / 34 °/s |
| Schwerpunkt 3 mm seitlich | 7,26° / 7,38° | 0 / 0 % | 347 / 690 | 103 / 216 | 4,2 / 4,2 | 37 / 36 °/s |

250 Hz regelt so gut wie 100 Hz (Kipp ±0,1°), beim leichtesten Paket P3 besser (kein Anschlag mehr). Die
Kommandorate steigt um das 2,5-Fache, weil das Gyro-Rauschen (0,4 °/s je Takt, im Modell unabhängig vom Takt)
2,5-mal so oft durch den D-Anteil geht; die wirkliche Kardanbewegung ändert sich nicht. **Die Gewinne müssen für
250 Hz nicht geändert werden.**

250 Hz, Mittel über die vier Robustheitsfälle (W5652H-Totzeit 4 bzw. 24 ms):

| Fall | Kipp max | Kommandorate p99 / RMS (Servo-Grad/s) | Kardanrate max |
|---|---|---|---|
| SG90, I_g 0 / 5e-4 / 1,5e-3 | 2,52 / 2,50 / 2,48° | 748…754 / 177 | 16 °/s |
| W5652H, I_g 0 / 5e-4 / 1,5e-3 | 2,50 / 2,49 / 2,49° | 755 / 176 | 27 °/s |
| W5652H, I_g 5e-3 (10-fach) | 2,52° | 799 / 223 | 36 °/s |
| W5652H, 0,10 s/60° (600 Servo-Grad/s) | 2,49° | 755 / 176 | 27 °/s |
| W5652H, Kd 0,30 / 0,60 | 3,14 / 2,12° | 506 / 994 | 27 °/s |
| W5652H, **D-Tiefpass 30 Hz** | 2,48° | **327 / 89** | 27 °/s |
| W5652H, D-Tiefpass 15 Hz | 2,45° | 189 / 65 | 27 °/s |
| W5652H, Slew 600 / 300 Servo-Grad/s | 2,49 / 2,49° | 600 / 300 | 27 °/s |

Linear (offener Kreis mit diskretem Regler, Halteglied, IMU-Mittelung, Totzeit, Servo, Rumpf; 705 g):

| Fall | Durchtritt | Phasenreserve | Amplitudenreserve (T = 10 N / 3 N) |
|---|---|---|---|
| 100 Hz, SG90-Fit 30 ms | 13 rad/s | 18° | 2,9 dB (bei 19 rad/s) |
| 250 Hz, SG90-Fit 30 ms | 13 rad/s | 19° | 3,2 dB |
| 250 Hz, SG90-Fit 50 ms, I_g 5e-4 | 12…13 rad/s | 6…10° | 1,1 / 2,3 dB |
| 250 Hz, W5652H, I_g 0 | 13 rad/s | 47° | 14,6 dB (bei 49 rad/s) |
| 250 Hz, W5652H, I_g 5e-4 | 11…12 rad/s | 47° | 23 / 13,4 dB (bei 267 rad/s) |
| 250 Hz, W5652H, I_g 1,5e-3 (3-fach) | 10…11 rad/s | 47° | 14,4 / **3,8 dB** (bei 267 rad/s) |
| … dazu D-Tiefpass 30 Hz | 10…11 rad/s | 45° | 16,2 / 5,6 dB |
| 250 Hz, W5652H, I_g 5e-4, Kd 0,60 | 14…15 rad/s | 49…51° | 21 / 11 dB |

**Lesart:**

- **Reaktionsmoment (Jans Frage):** Die Strecke wird `I s² φ = −(l T + I_g s²) δ`: ein Nullstellenpaar bei
  `ω_z = √(l T / I_g)`, 97 rad/s (15 Hz) bei 25 N, 62 rad/s bei 10 N, 34 rad/s (5 Hz) bei 3 N im Abbrand. Darüber
  dreht der Kardan den Rumpf stärker als der Schub, mit umgekehrtem Vorzeichen; der Gyro sieht das als direkte
  Kopplung `ω = −(I_g/I) θ̇_Kardan`. Mit 5e-4 kg m² bleibt die Schleife dort weit unter 1 (13 dB Reserve im
  Abbrand), im Flug ändert sich der Kippwinkel um < 0,05°, auch das Zehnfache bleibt stabil. Eng wird es erst mit
  dreifachem I_g bei wenig Schub (3,8 dB bei 42 Hz); ein D-Tiefpass um 30 Hz holt davon 2 dB zurück. Unter 0,5 N
  stellt die Firmware die Servos ohnehin auf Mitte. Eine Rückkopplungsschleife entsteht nicht, solange der
  D-Anteil oberhalb von ~40 Hz nicht weiter durchgreift.
- **Engpass ist der Servo, nicht der Takt:** Mit dem SG90-Fit (30 ms Totzeit, 5,8 Hz) hat Kp 2 / Ki 1 / Kd 0,45
  nur 18° Phasenreserve und 3 dB Amplitudenreserve, bei 50 ms fast keine; 100 → 250 Hz bringt 1°. Mit der
  W5652H-Annahme sind es 47° und 15 dB. E01 an den W5652H ist deshalb wichtiger als jede Gewinnänderung.
- **Ratenbegrenzung des Servos** greift nie: der Kardan bewegt sich in allen Fällen mit höchstens 15…40 TVC-Grad/s
  (90…240 Servo-Grad/s bei Gain 6), die W5652H können 600…1000 Servo-Grad/s.
- Kd 0,60 senkt den Kippwinkel um 0,4°, braucht aber 30 % mehr Stellaktivität und verliert Reserve bei wenig
  Schub; Kd 0,30 ist schlechter. Kein Grund, die Bayes-Gewinne für 250 Hz zu ändern.

**Empfehlung für die Firmware (250 Hz):** Gewinne bleiben **Kp 2 / Ki 1 / Kd 0,45**. **D-Tiefpass 30 Hz**
(PT1 auf ω nur im D-Anteil; bei 250 Hz Faktor `1 − exp(−2π·30·0,004)` = 0,53, gleichwertig `lowpassStep` mit
τ = 5,3 ms): halbiert die Kommandoaktivität und kostet 2° Phase. **Slew-Begrenzung 100 TVC-Grad/s** (bei Gain 6:
600 Servo-Grad/s, 2,4 Servo-Grad je 4-ms-Takt) als Schutz gegen Sprünge (Moduswechsel, Ausreißer im Gyro), nicht
für die Stabilität nötig: sie liegt beim Zwei- bis Sechsfachen dessen, was der Regler braucht, und unter der
Servo-Grenze. `A_NORM_TAU_S` 0,095 s wie umgesetzt. Nach E01 (W5652H-Totzeit und Bandbreite) die Tabellen mit
`--servo-model` bzw. neuen `ServoParams` neu rechnen.


## Landebrennen und Luftwiderstand (seit 23.10.2026)

`MotorParams.second_mode = "landing"` zündet den zweiten Motor nicht nach Zeit, sondern aus Höhe
und Sinkrate: `tvcsim/landing.py` rechnet jeden Takt die Aufsetzkosten J (größte
Aufsetzgeschwindigkeit einer 1D-Simulation des Brennens mit Bodenkontakt und Hüpfern) für „jetzt“
und „einen Takt später“ und zündet im Minimum; Zündverzug `igniter_delay`, Schubtoleranz
`thrust_scale2`, Rauschen der Zündentscheidung `landing_alt_sigma/vz_sigma`. Der Boden hält die
Rakete, solange der Schub nicht trägt, sonst hebt sie wieder ab; `extra["contacts"]` listet jedes
Aufsetzen, `extra["v_land"]` das härteste. `VehicleParams.cd_a` schaltet den Luftwiderstand ein
(`VehicleParams.light(m)` für die leichte Landekonfiguration). Ergebnis und Einordnung:
`docs/Physik_Review_2026-10-23.md` §3; Zahlen aus `scripts/landing_study.py`.

**Schubdrossel** (`ThrottleParams.enabled`, Scout-F-Pads): Axialschub = Motorschub · f(u) mit
f = 1 − (1 − f_min) u, Pads als PT2 wie der Kardan-Servo. Der Landeregler in `tvcsim/throttle.py`
zündet mit Reserve für einen schwachen Motor, lässt die Schubspitze ungedrosselt, schätzt dabei den
wahren Schub aus |a| und führt danach zeitbasiert (ZEM/ZEV) auf Höhe 0 und −0,5 m/s zum
Brennschluss; `simulate_landing_1d` ist die schnelle 1D-Fassung für Monte-Carlo
(`scripts/throttle_study.py`). Ergebnis: `docs/Physik_Review_2026-10-23.md` §4.

## Modell (wie in Simulink)

**Dynamik** (`chart_44`, `dynamics.py`): Starrkörper mit Quaternion `q` (Skalar zuerst, dreht
Körper nach inertial), Zustand `r, rd, w, q`. TVC-Drehung `gCb = Rz(th_z) Ry(th_y)` in Grad,
Schub im Körpersystem `Tb = gCb' [T 0 0]'`, Hebel `r = [-l, mis_y, mis_z]`, `Mb = r × Tb`,
`Ti = q ⊗ [0 Tb] ⊗ q*`, `rdd = [Ti_x/m - g, Ti_y/m, Ti_z/m]`, Euler-Gleichungen mit `Ix, Iy, Iz`,
`qd = ½ q ⊗ [0 w]`. Masse `m = m_dry + m_fuel/1000`. Anfang `q = [1 0 0 0]`, Rest 0.
Die `hamilton`-Funktion des Blocks ist mit `r` zuerst hingeschrieben, ergibt aber das übliche
Produkt `q ⊗ r`; die Tests prüfen das gegen `scipy.spatial.transform.Rotation`.

**Schub**: Lookup auf der E12-Kurve (TSP E12, 39 Ns), zweiter Motor um `secondburn = 730`
Schritte zu 0,01 s (`MotorParams.secondburn_dt`, unabhängig vom Regeltakt), also 7,3 s, verzögert (im Modell `Clock -> Delay -> Lookup`), Summe.
Die F35-Kurve liegt daneben und ist unbenutzt.

**Avionics** (`chart_76`, `chart_83`): ZOH mit `dt`; Quaternion mit zufälliger Kleinstdrehung
(Achse zufällig, Winkel ~ N(0, 0,01 rad)); Drehrate in Grad/s plus `randn * 0,4` (ein Skalar auf
alle drei Komponenten, so steht es im Block); Beschleunigung `rdd` plus Random Number
(Varianz 1, ein Skalar).

**Estimator** (`chart_32`): `w_est = w_n`, `q_est = q_n`, `T_est = |rdd_n| · m` mit der wahren Masse.

**Controller** (`system_83`, `chart_64`): `rot = ∫ w_est` in Grad (Integrator auf Root-Ebene,
wird nie zurückgesetzt), `e = -0,01 · rot`, je Achse `u = kp e + ki ∫e + kd (-w_est)` mit
`w_est` in Grad/s; die drei `∫e` werden bei `secondburn/100 = 7,3 s` auf 0 gesetzt. Die x-Achse
(Rollachse) wird mitgerechnet, `Mx` aber nicht benutzt. `Moments2Commands`:
`Tb = [0, Mz/l, -My/l]`, `th_y = asind(clamp(Tb_3/T_est))`,
`th_z = asind(clamp(Tb_2/(-T_est cos th_y)))` mit dem nominalen `l`.

**Aktuator** (Root): `th_com -> ZOH(dt) -> Sättigung ±5° -> tf5 -> Gain 6 -> ± statischer Fehler`.
Für y ist der statische Fehler `static_error_y · (1 für t<2, 0 für 2..7, 1 für 7..9, 0 ab 9 s)`
und wird abgezogen, für z konstant `+static_error_z`. Der Gain 6 kompensiert den DC-Gain von
`tf5` (Servo-Soll in Grad zu Kardan in Grad, etwa 1/6). ±5° Sättigung sind also ±5° TVC.

**Integration**: feste Regelschritte `dt = 0,01 s` (ZOH) im Simulink-Modell; die Vorgabe ist seit 05.11.2026
`dt = 0,004 s` (250 Hz, siehe oben), `SimParams.at_rate(100)` rechnet wie Simulink. Dazwischen RK4 mit ~1 ms
(`substeps` 10 bei 100 Hz, 4 bei 250 Hz), Quaternion nach jedem Teilschritt normiert. Simulink rechnet mit ode45
(variabler Schritt, RelTol 1e-3); Unterschiede daraus sind klein gegen die Modellannahmen.

**Monte-Carlo** (`TVC6DOF.m`): 100 Läufe à 7 s, `x_mc = x_n + randn * x_v` mit den
Streuungen `Ix_v = Iy_v = Iz_v = 1e-4, m_dry_v = 1e-4, servo_delay_v = 0,01, mis_y_v = mis_z_v =
0,001, static_error_y_v = static_error_z_v = 1, l_v = 0,01`. Plot wie in MATLAB:
Downrange (y) gegen Crossrange (z) gegen Höhe (x).

**Tuning** (`pid_tuner.m`): Raster über `kp, ki, kd`, Zielgröße `maxHeight` (laufendes Maximum
der Höhe) am Ende der 12 s (StopTime des Modells, also mit zweitem Motor).

## Koordinaten und Umrechnung zur Firmware

| | Simulink / tvcsim | Firmware (`main.cpp`, `Control.cpp`) |
|---|---|---|
| Längsachse (Roll) | Körper **x**; inertial x = Höhe | **z** (`rot_deg.z`, `omega_dps.z`) |
| Querachsen | y, z | x = Yaw, y = Pitch |
| Drehwinkel | `rot = ∫ w_est` in Grad, Regelfehler `-0,01 · rot` | `rot_deg += omega · dt`, Reglereingang `rot_deg / -100` |
| D-Anteil | `kd · (-w_est)` mit w in Grad/s | `Kd · omega_dps / -100` |
| Moment -> TVC | `th = asin(-M / (l T_est))`, `T_est = |a| m` | `delta = asin(M / (l m |a|))`, m = `MASS_KG` fest |
| TVC -> Servo | Gain 6 (Servo-Grad je TVC-Grad) | `servo = delta_deg · (±23) + Offset`, Fenster 70..115 / 60..105 |

`FirmwareController` ordnet zu: Firmware x (Yaw) = Simulink-Körperachse y, Firmware y (Pitch) =
Simulink z, Firmware z (Roll) = Simulink x. Mit `u = kp e + ki ∫e + kd(-w)` einerseits und
`M = Kp rot/(-100) + Ki ∫rot/(-100) + Kd w/(-100)` andererseits sind beide identisch für

```
kp = Kp,   ki = Ki,   kd = Kd / 100
```

(Test `test_simulink_and_firmware_same_moments`). Die Firmware-Gewinne `Kp=5, Ki=0, Kd=1`
entsprechen also `kp=5, ki=0, kd=0,01`; die Tuner-Gewinne `kp=3,1, ki=5, kd=0,385` entsprechen
`Kp=3,1, Ki=5, Kd=38,5`. Übrige Unterschiede der Firmware: sie addiert den aktuellen
Integrationsschritt vor dem Regler (Simulink integriert bis zum Takt), ihr I-Anteil wird nie
zurückgesetzt, `|a|` ist tiefpassgefiltert (`A_NORM_ALPHA = 0,1`, Untergrenze 1 m/s²), die
Masse ist `MASS_KG = 0,70` statt der wahren Masse, das asin-Argument wird auf ±0,99 geklemmt,
und der Servowinkel wird auf das mechanische Fenster begrenzt (bis 22.10.2026 zusätzlich auf ganze Grad gerundet, `quantize_servo=True`; die Firmware stellt die Servos seitdem als 16-Bit-PWM ohne Rundung).

**Vorzeichen**: die Firmware rechnet `delta = +asin(M/...)`, das Simulink-Modell braucht für
dasselbe Moment `th = asin(-M/...)`. In der Hardware steckt dieses Vorzeichen in
`SERVO_YAW_GAIN = -23` bzw. `SERVO_PITCH_GAIN = +23` (die beiden Achsen sind verschieden
gepolt). In der Simulation ist es der Parameter `FirmwareParams.axis_sign_yaw/pitch`
(Vorgabe -1/-1, damit die Schleife stabil ist). Welche Polung am Kardan richtig ist, muss der
Tischtest zeigen; die Simulation kann es nicht entscheiden.

## Annahmen und Abweichungen vom Simulink-Modell

1. **`tf5` neu gefittet.** Die identifizierte Übertragungsfunktion (`idtf`) ist ohne MATLAB
   nicht lesbar. `scripts/fit_servo.py` fittet aus `data/servo_step_response.csv` (SG90 im
   Kardan, Soll 95 = Mitte) ein PT2 mit Totzeit: `K = 0,166` Kardan-Grad je Servo-Grad (1/6,0),
   `wn = 36,7 rad/s` (5,8 Hz), `zeta = 0,60`, `tau = 30 ms`, RMS 0,57° über die ganze Messung.
   Die Sprungantworten zeigen eine Ratenbegrenzung (etwa 70°/s am Kardan) und etwas Hysterese
   (+35 Servo-Grad geben +5,5°, -35 geben -6,3°); das lineare Modell bildet das nicht ab.
   Der DC-Gain stimmt zum Simulink-Gain 6 (6 · K = 1,00). Der Parameter `servo_delay`
   (0,08 s in `TVC6DOF.m`) wird im Simulink-Modell gar nicht benutzt (nur ein Kommentar
   "ersetzen?" im PreLoadFcn); hier ist er die Totzeit des Servomodells, Vorgabe der Fit-Wert
   0,03 s, in Monte-Carlo mit `servo_delay_v = 0,01` gestreut. Die neuen Servos (FrSky W5652H)
   sind nicht vermessen; bis dahin gilt der SG90-Fit, alle Werte in `ServoParams`.
   **Nachtrag 22.10.2026:** `fit_servo_model` verschiebt den Eingang um ganze Abtastschritte,
   deshalb hat der Least-Squares-Fit die Totzeit nie bewegt (Startwert 10, 30 oder 60 ms kommt
   unverändert heraus, mit 25,7, 36,7 oder 147 rad/s als wn). Mit gebrochener Totzeit
   (`tvcsim.ident.fit_pt2_delay`, drei Startwerte) landet der Fit bei 30,3 ms und wn = 37,8 rad/s,
   die Werte in `ServoParams` bleiben also gültig. Neue Messungen laufen über Experiment E01
   (`docs/experiments/E01_servo_ident.md`, Sketch `servo_ident`, Auswertung `ident_servo.py`):
   Treppe für Gain und Hysterese, Sprünge für Totzeit und Rate, Chirps für den Frequenzgang.
2. **Servo-Grad je TVC-Grad: 6 oder 23.** `servo_deg_per_tvc_deg = 6` (Vorgabe, Simulink-Gain
   und Identifikation). `Config.h` sagt 23. Mit 23 und dem Fenster 70..115 Servo-Grad hat die
   Firmware nur ±0,98° TVC-Ausschlag, mit 6 wären es ±3,75°. Beides nur Parameter
   (`--servo-gain`, `--fw-servo-gain`).
3. **Treibstoffmasse.** Der Signal Builder der `.slx` ließ sich doch auslesen
   (`data/m_fuel_signalbuilder.csv`): 60 g bei t = 0, linear-stückweise auf 0 g bei 3,45 s,
   danach 0, auch für den zweiten Motor. Das ist die Vorgabe (`fuel_model = "signalbuilder"`),
   1:1 wie Simulink. Alternative `"impulse"`: 28 g je Motor (TSP E12), Abbrand proportional
   zum Impuls der Kurve, für beide Motoren.
4. **Schubkurve.** Die CSV beginnt bei (0,028 s, 0,216 N); die `.mat`-Tabellen des Modells
   haben stattdessen (0, 0) und enden bei (20 s, 0). Hier wird (0, 0) vorangestellt, nach dem
   letzten Punkt gilt 0.
5. **Zwei Nominalsätze.** `TVC6DOF.m` setzt `Ix = Iy = Iz = 0,1, m_dry = 0,94, l = 0,3,
   kp = 1, ki = 1, kd = 0,1`. Das PreLoadFcn der `.slx` setzt davon unabhängig
   `I = 3/800 + 1/24 = 0,0454, l = 0,5, m_dry_mc = 0,7 (m_dry_n = 1), static_error_y = 1,
   static_error_z = 0,6, kp = 2, ki = 1, kd = 0,004`. `pid_tuner.m` setzt nur `kp, ki, kd` und
   simuliert mit dem, was im Workspace steht. Ohne vorheriges `TVC6DOF.m` waren das die
   PreLoadFcn-Werte. Beides als `VehicleParams.nominal()` / `.preload()` verfügbar.
   Mit `m_dry = 0,94` (plus 60 g Treibstoff) hebt die E12 kaum ab (Gipfel 9..10 m, mittleres
   Schub-Gewichts-Verhältnis 1,2); das Bild `Images/Monte-Carlo (1).png` mit 45 m Gipfelhöhe
   passt zum PreLoadFcn-Satz mit 0,7 kg.
6. **Trägheitsmomente** 0,1 kg m² sind Platzhalter (Plan §3.3). Ein dritter Satz
   `VehicleParams.cad()` (`--vehicle cad`) liest das CAD-Massenmodell `cad/mass_properties.json`
   (Startzustand mit vollem Motor): 981 g, Hebelarm Drehpunkt–Schwerpunkt 0,372 m,
   quer `Ixx = Iyy = 0,110 kg m²`, längs `Izz = 0,00105 kg m²`. Achsentausch: CAD z (längs)
   wird Simulink x, also `Ix = Izz`, `Iy = Ixx`, `Iz = Iyy`; `m_dry` = 981 g minus 28 g
   Treibstoff = 953 g, die Treibstoffmasse kommt über `fuel_model` dazu (mit `signalbuilder`
   also 1,013 kg beim Start); die seitliche Schwerpunktlage (0,2 / −0,7 mm) geht als
   `mis_y/mis_z` ein.
7. **Beschleunigungssensor.** Das Simulink-Modell verrauscht `rdd`, die inertiale
   Beschleunigung samt g, und bildet daraus `T_est = |rdd| m`. Ein echter Sensor misst die
   spezifische Kraft `Tb/m`. Folge im Modell: bei T = 0 ist `T_est = m g` statt 0, und wenn der
   Schub durch `m g` läuft, wird `T_est ≈ 0` und `Moments2Commands` kommandiert ±90°
   (gesättigt auf ±5°), ein kurzer Stoß beim Abheben und bei der zweiten Zündung.
   Vorgabe bleibt `accel_model = "rdd"` (1:1), `"specific_force"` schaltet auf die physikalisch
   richtige Messung.
8. **`Moments2Commands`** setzt den cos-Faktor auf die andere Achse als die Dynamik
   (`My = -l T sin th_y cos th_z`, der Block rechnet mit `cos th_y` für `th_z`). Bis ±5° ist der
   Fehler unter 1 %; 1:1 übernommen.
9. **Nicht übernommen**: Random Number mit Varianz 0 auf `wd_x` (wirkungslos), die unbenutzten
   F35-Lookups und Thrust-Curve-Signal-Builder, Scopes und To-Workspace-Blöcke. **Anders als
   Simulink gibt es einen Boden** (`SimParams.ground`, Vorgabe an, seit 21.10.2026 abends): Auf der
   Rampe bewegt sich die Rakete nicht, bis der Schub das Gewicht übersteigt, und der Lauf endet bei
   der Landung (`extra["t_land"]`); die Plots laufen also nicht mehr bis 12 s ins Negative.
   `--no-ground` in `run_nominal.py` und `compare_gains.py` rechnet wie Simulink (der dort
   auskommentierte Hit-Crossing-Stop bei 0,01 m hätte dasselbe getan).
10. Der `Delay`-Block läuft in Simulink mit geerbter Abtastzeit; mit `secondburn/100` im Step-Block
    des Reglers ist 7,3 s die einzige konsistente Lesart.

## Ergebnis: Firmware-Gewinne gegen Tuner-Gewinne

**Nachtrag 21.10.2026 abends, mit Boden** (`SimParams.ground`, siehe Abweichung 9): Die Tabellen
weiter unten sind ohne Boden gerechnet, wie Simulink. Mit Boden sitzt die Rakete auf der Rampe, bis
der Schub das Gewicht übersteigt, und das ändert bei Schub-Gewichts-Verhältnissen nahe 1 viel: Ohne
Boden sinkt die Rakete in den ersten 0,3 s des E12 um 0,4 m und nimmt 2,6 m/s Geschwindigkeitsdefizit
mit, das bei nur 2 m/s² Nettobeschleunigung die ganze Brennphase bleibt. `compare_gains.py --accel
specific_force` mit Boden (Rauschen an, statischer Fehler 1/0,6°, Landung = Zeitpunkt Höhe 0):

| Fahrzeug `cad` (1,013 kg Start) | maxHeight | Kipp max Brenn. | Kipp 3,55 s | seitlich 3,55 s | Landung |
|---|---|---|---|---|---|
| Simulink-Regler, Firmware-Gewinne | 20,2 m | 3,9° | 0,9° | 1,7 m | 6,3 s |
| Simulink-Regler, Tuner | 19,4 m | 6,7° | 6,4° | 2,6 m | 6,3 s |
| Firmware 1:1 (Gain 23) | 20,0 m | 6,8° | 0,6° | 3,2 m | 6,3 s |
| Firmware, Servo-Gain 6 | 20,2 m | 1,8° | 0,5° | 1,0 m | 6,3 s |

| Fahrzeug `preload` (0,76 kg Start) | maxHeight | Kipp max Brenn. | Kipp 3,55 s | seitlich 3,55 s | Landung |
|---|---|---|---|---|---|
| Simulink-Regler, Firmware-Gewinne | 62,2 m | 5,3° | 1,0° | 3,7 m | – (zweite Zündung bei 7,3 s hebt sie wieder) |
| Simulink-Regler, Tuner | 53,7 m | 23,0° | 19,5° | 16,6 m | 9,0 s |
| Firmware 1:1 (Gain 23) | 57,0 m | 25,1° | 3,3° | 14,5 m | 8,7 s |
| Firmware, Servo-Gain 6 | 61,5 m | 4,9° | 2,5° | 2,5 m | 9,6 s |

Mit Boden erreicht die 1,0-kg-Rakete am E12 also 20 m statt 9 m (ohne Boden), die 0,7-kg-Rakete
62 m statt 48 m. Die Rangfolge der Regler bleibt dieselbe. Ohne Boden (`--no-ground`) kommen die
alten Zahlen wieder heraus. Für den zweiten Motor gilt: Bei der `cad`-Rakete ist er mit 7,3 s zu
spät (Landung bei 6,3 s), ein Landebrennen braucht eine Zündung aus der Höhe statt nach Zeit.

**Nachtrag 22.10.2026 nachts, *Kartonaut 1* Stand 2b** (überholt durch den Nachtrag vom 23.10. unten: diese Läufe rechneten mit dem
Signal-Builder-Treibstoff von 60 statt 28 g und mit den alten `Config.h`-Werten 0,70 kg / 0,30 m) (`--vehicle stand2b`: m_dry 0,695 kg, 0,723 kg beim Start,
I quer 0,0213, längs 0,00047 kg m², Hebelarm 0,186 m aus `cad/mass_stand2b.json`; `--single-motor`, Boden, Rauschen,
statischer Fehler 1/0,6°, `--accel specific_force`). Die Modulbauweise ist ein Viertel leichter als `voll`, der
Hebelarm halb so lang, das Quer-Trägheitsmoment ein Fünftel: die Rakete reagiert viel schneller auf den Kardan.

| Fahrzeug `stand2b` (0,723 kg Start), ein Motor | maxHeight | Kipp max Brenn. | Kipp 3,55 s | seitlich 3,55 s | Landung |
|---|---|---|---|---|---|
| Simulink-Regler, Firmware-Gewinne (kp 5 / ki 0 / kd 0,01) | 62,5 m | 3,9° | 2,8° | 1,0 m | 9,2 s |
| Simulink-Regler, Tuner (3,1 / 5 / 0,385) | 59,8 m | 14,1° | 11,8° | 9,3 m | 9,1 s |
| Simulink-Regler, TVC6DOF.m (1 / 1 / 0,1) | 59,9 m | 14,7° | 11,7° | 8,3 m | 9,1 s |
| Firmware 1:1 (`MASS_KG` 0,70, `MOMENT_ARM_M` 0,30, Gain 23) | 63,7 m | 1,9° | 1,0° | 1,0 m | 9,3 s |
| Firmware, Servo-Gain 6 | 63,6 m | 1,9° | 1,1° | 0,9 m | 9,3 s |
| Firmware, Gain 6, Kd = 38,5 (Tuner-D) | 60,5 m | 15,6° | 13,6° | 8,6 m | 9,1 s |

Monte-Carlo (`run_montecarlo.py --controller firmware --vehicle stand2b --single-motor --accel specific_force
--fw-servo-gain 6 --fw-mass 0.723`, 100 Läufe): Gipfel 63,4 ± 0,4 m (61,3 … 63,8 m), seitlicher Versatz bei der
Landung im Median 6,9 m. Der Kippwinkel nach Brennschluss ist ohne Schub nicht mehr regelbar und deshalb kein Maß
für den Regler; in der Brennphase bleibt die Firmware mit beiden Servo-Umrechnungen unter 2°. Das Massenproblem aus
Befund 12 ist mit der Modulbauweise erledigt: 63 m statt 20 m am selben Motor. Nach dem Wiegen der Rakete
`cad/mass_stand2b.py` korrigieren und diese Tabelle neu rechnen; die Servo-Übertragungsfunktion stammt weiter vom
SG90-Fit von 2025 und ist am gebauten Schubstangen-Kardan mit den W5652H neu zu messen.

**Nachtrag 23.10.2026, Gewichtspakete und Gewinne** (`scripts/check_stand2b_levers.py`, Massen aus `cad/mass_stand2b.json`
Abschnitt `levers`: Ausgangslage 705 g mit den Leichtbau-Druckteilen, P1 672 g, P2 631 g, P3 593 g). Firmware-Regler mit
der wahren Masse und dem wahren Hebelarm, Servo-Umrechnung 6, ein Motor, Treibstoff 28 g (`fuel_model="impulse"`),
Boden, Rauschen, statischer Fehler 1°/0,6°, spezifische Kraft, kein Luftwiderstand. „Anschlag“ = Anteil der Brennzeit
am Kardanfenster.

| Paket | Kp / Kd | Gipfel | Kipp max Brenn. | Kipp 3,55 s | seitlich 3,55 s | Anschlag |
|---|---|---|---|---|---|---|
| 705 g, Hebelarm 190 mm | 5 / 1 (`Config.h`) | 73 m | 4,3° | 3,3° | 1,2 m | 67 % |
| 705 g | 1 / 0,5 | 74 m | 3,3° | 2,9° | 3,1 m | 0 % |
| 705 g | **2 / 0,5** | 74 m | **2,4°** | 1,5° | 1,8 m | **0 %** |
| 705 g | 2 / 1 | 73 m | 4,8° | 3,7° | 2,5 m | 60 % |
| 705 g | 3,5 / 0,1 | 68 m | 49° | 50° | 2,6 m | 56 % |
| P1 672 g, 185 mm | 5 / 1 | 84 m | 5,1° | 3,8° | 1,6 m | 70 % |
| P1 | **2 / 0,5** | 86 m | **2,5°** | 1,5° | 1,7 m | **0 %** |
| P2 631 g, 176 mm | 5 / 1 | 102 m | 6,4° | 3,7° | 2,1 m | 73 % |
| P2 | **2 / 0,5** | 103 m | **2,3°** | 1,4° | 1,7 m | **0 %** |
| P3 593 g, 157 mm | 5 / 1 | 121 m | 8,5° | 4,2° | 3,0 m | 82 % |
| P3 | 2 / 0,5 | 123 m | 3,7° | 3,7° | 2,1 m | 36 % |
| P3 | **2 / 0,25** | 124 m | **2,2°** | 1,3° | 2,0 m | **0 %** |

Kd = 1 setzt den Kardan bei jeder Erstflug-Masse an den Anschlag, auch mit Kp 0,5. Das Quer-Trägheitsmoment ist mit
0,014 bis 0,021 kg m² fünf- bis achtmal kleiner als bei den Fahrzeugen, für die die Gewinne gefunden wurden; der D-Anteil
muss mitgehen. Die Läufe vom 22.10. nachts sahen nur deshalb gut aus, weil die Firmware mit 0,30 m statt 0,19 m Hebelarm
rechnete und so die Verstärkung um etwa den Faktor 1,6 drückte. Ausführlich: `docs/Gewicht_und_Landung_2026-10-23.md` §4.

Das Raster rechnet nur eine Servo-Totzeit (30 ms). **Bayes-Optimierung** (`scripts/tune_bayes.py`, Optimierer
`tvcsim/bayesopt.py`: Gauß-Prozess mit Expected Improvement; je Punkt vier Flüge, Servo-Totzeit 30 und 50 ms; Kp, Ki, Kd):
705 g → Kp 2,42 / Ki 1,50 / Kd 0,44, P1 → 1,97 / 1,50 / 0,43, P2 → 1,82 / 1,13 / 0,40, P3 → 1,50 / 0,77 / 0,29, jeweils
2,1 bis 2,9° Kipp und nie am Anschlag. Gemeinsamer Satz **Kp 2 / Ki 1 / Kd 0,45** für 705 und 672 g (0 % Anschlag, seitlich
1,3 m); der Raster-Satz 2 / 0 / 0,5 steht mit 50 ms bei 631 g schon 19 % am Anschlag, `Config.h` (5 / 0 / 1) 69 bis 82 %.

```bash
python scripts/tune_bayes.py --config base --iters 35 --workers 4
python scripts/tune_bayes.py --eval 2 1 0.45 --configs base P1 P2 P3
```


`scripts/compare_gains.py` (Rauschen an, statischer Fehler 1°/0,6°, ein Seed). Maßgeblich
ist die erste Brennphase (0..3,55 s); danach gibt es keinen Schub und keine Stellmöglichkeit,
und die zweite Zündung bei 7,3 s trifft die fallende Rakete. Kippwinkel = Winkel der
Längsachse zur Lotrechten.

Fahrzeug `preload` (m_dry 0,7 kg, I 0,045, l 0,5 m), Beschleunigung wie Simulink (`rdd`):

| Fall | maxHeight | Kipp max Brennphase | Kipp bei 3,55 s | seitlich bei 3,55 s |
|---|---|---|---|---|
| Simulink-Regler, Firmware-Gewinne kp 5 / ki 0 / kd 0,01 | 46,7 m | 9,2° | 3,0° | 4,0 m |
| Simulink-Regler, Tuner kp 3,1 / ki 5 / kd 0,385 | 38,1 m | 26,3° | 19,8° | 22,0 m |
| Simulink-Regler, TVC6DOF.m kp 1 / ki 1 / kd 0,1 | 41,3 m | 22,4° | 19,0° | 16,5 m |
| Firmware 1:1 (MASS_KG 0,70, Servo-Gain 23) | 47,9 m | 10,8° | 2,1° | 6,9 m |
| Firmware, Servo-Gain 6 | 47,3 m | 9,5° | 3,6° | 4,9 m |
| Firmware, Servo-Gain 6, Kd = 38,5 (= Tuner-kd) | 40,6 m | 25,2° | 22,3° | 18,4 m |

Fahrzeug `nominal` (m_dry 0,94 kg, I 0,1, l 0,3 m), Beschleunigung `rdd`:

| Fall | maxHeight | Kipp max Brennphase | Kipp bei 3,55 s | seitlich bei 3,55 s |
|---|---|---|---|---|
| Simulink-Regler, Firmware-Gewinne | 9,9 m | 1,5° | 0,3° | 0,5 m |
| Simulink-Regler, Tuner | 9,3 m | 6,2° | 4,9° | 3,6 m |
| Simulink-Regler, TVC6DOF.m | 9,4 m | 6,4° | 5,1° | 3,7 m |
| Firmware 1:1 (Gain 23) | 10,1 m | 5,6° | 0,8° | 2,6 m |
| Firmware, Servo-Gain 6 | 10,0 m | 1,4° | 0,9° | 0,6 m |
| Firmware, Servo-Gain 6, Kd = 38,5 | 9,6 m | 6,5° | 6,0° | 3,5 m |

Mit `--accel specific_force` (physikalisch richtige Schubschätzung) bleibt das Bild gleich,
die Firmware-Gewinne werden eher noch besser (preload: Kipp max 5,3°, bei 3,55 s 1,0°).

Fahrzeug `cad` (CAD-Massenmodell: m_dry 0,953 kg, 1,013 kg beim Start, I quer 0,110, längs 0,00105,
l 0,372 m), Beschleunigung `specific_force`:

| Fall | maxHeight | Kipp max Brennphase | Kipp bei 3,55 s | seitlich bei 3,55 s |
|---|---|---|---|---|
| Simulink-Regler, Firmware-Gewinne | 9,0 m | 3,7° | 0,9° | 1,8 m |
| Simulink-Regler, Tuner | 8,1 m | 7,1° | 6,2° | 4,0 m |
| Simulink-Regler, TVC6DOF.m | 8,2 m | 6,8° | 6,4° | 3,9 m |
| Firmware 1:1 (Gain 23) | 8,9 m | 4,4° | 0,5° | 2,2 m |
| Firmware, Servo-Gain 6 | 9,0 m | 1,8° | 0,5° | 1,0 m |
| Firmware, Servo-Gain 6, Kd = 38,5 | 8,4 m | 7,4° | 7,1° | 3,6 m |

Mit `--accel rdd` (wie Simulink) dieselbe Reihenfolge (Firmware-Gewinne: Kipp max 1,9°, bei
3,55 s 0,6°). Einordnung: mit 1,0 kg Startmasse liegt das mittlere Schub-Gewichts-Verhältnis
der E12 bei 1,1 (11 N gegen 9,9 N), die Rakete steigt in 3,5 s nur auf 9 m und erreicht beim
Brennschluss etwa 2 m/s; die Brennphase ist mit den Firmware-Gewinnen trotzdem geregelt
(Kippwinkel unter 4°, seitlich unter 2 m), weil der Schub von 11 N mit dem Hebelarm 0,37 m
gegen die Querträgheit 0,11 kg m² genug Stellmoment liefert. Ein Flug ist das nicht: der
Gipfel liegt bei 9 m, und jede Störung über die 1° statischen Fehler hinaus zehrt am
knappen Überschuss. Die schwere Rakete braucht einen stärkeren Motor (F35) oder weniger Masse.

Monte-Carlo (`run_montecarlo.py`, 100 Läufe à 7 s, Streuungen aus `TVC6DOF.m`, Seed 0):

| Fahrzeug, Gewinne | maxHeight (Mittel ± Std) | Kipp bei 7 s (Median) | seitlich bei 7 s (Median) | Anteil Kipp < 30° |
|---|---|---|---|---|
| preload, kp 2 / ki 1 / kd 0,004 (PreLoadFcn) | 48,4 ± 1,2 m | 19° | 5,4 m | 80 % |
| preload, kp 3,1 / ki 5 / kd 0,385 (Tuner) | 36,4 ± 8,6 m | 67° | 72 m | 12 % |
| nominal, kp 1 / ki 1 / kd 0,1 (TVC6DOF.m) | 9,2 ± 0,5 m | 20° | 14 m | 83 % |

Der Kippwinkel bei 7 s ist der des antriebslosen Falls nach dem Gipfel (kein Boden im Modell);
für die Regelgüte zählt die Brennphase. Das Bild `out/montecarlo_simulink_preload_preload.png`
entspricht in Gipfelhöhe (48 m gegen 45 m) und Streuung dem MATLAB-Bild `Images/Monte-Carlo (1).png`.

**Lesart:**

- **Die Firmware-Gewinne (Kp 5, Ki 0, Kd 1, Skala -100) stabilisieren die Rakete in diesem
  Modell**, sowohl im Simulink-Regler (als kp 5, ki 0, kd 0,01) als auch im 1:1-Firmware-Port,
  mit beiden Fahrzeugsätzen. Der Kippwinkel bleibt in der Brennphase unter 10°, mit dem
  nominalen Fahrzeug unter 2°.
- **Die Tuner-Gewinne (kp 3,1, ki 5, kd 0,385) sind in diesem Modell schlechter.** Der
  D-Anteil ist 40-mal so groß wie der der Firmware: 1°/s Drehrate fordert 0,385 N m, das sind
  bei 11 N Schub etwa 7° TVC, also sofort die ±5°-Sättigung. Mit der Servo-Totzeit (30 ms),
  dem ZOH (10 ms) und dem PT2 (5,8 Hz) ergibt das einen Grenzzyklus von 3..4 Hz an der
  Sättigung (`out/compare_gains_*.png`, unterstes Feld), und die statischen Fehler werden
  nicht ausgeregelt, weil der Stellbereich im Grenzzyklus verbraucht wird. Dasselbe gilt für
  `kd = 0,1` aus `TVC6DOF.m`. Das Raster `tune_pid.py` (preload, kp 2..5, ki 0..5,
  kd 0,004..0,385) findet den Gipfel bei kleinem kd (siehe `out/tune_pid_preload.csv`).
  Dass `pid_tuner.m` trotzdem 0,385 gefunden hat, spricht für ein anderes `tf5` in MATLAB
  (langsamer oder stärker gedämpft) oder dafür, dass dort noch ohne `tf5` und Sättigung
  getunt wurde. Das lässt sich nur mit MATLAB klären: `tf5` als Zähler, Nenner und
  `IODelay` exportieren und hier gegen `ServoParams` legen.
- **Servo-Gain 23 gegen 6**: Mit 23 (`Config.h`) hat die Firmware nur ±0,98° TVC. Das reicht
  im Modell knapp für die Brennphase, aber ein statischer Fehler von 1° ist damit nicht
  ausgleichbar (das Fenster wird dauerhaft angeschlagen, siehe `Firmware 1:1` im Plot ab 7 s).
  Mit 6 verhält sich die Firmware wie der Simulink-Regler. Welcher Wert stimmt, ist die
  offene Frage an die Kardangeometrie (Plan §6).
- `Ki = 0` in der Firmware heißt: ein statischer Fehler der Servo-Nullstellung bleibt als
  bleibende Neigung stehen (im Modell etwa 1° bei 1° Fehler). Ein kleines Ki (Simulink-ki um 1)
  nimmt das weg, ohne den Grenzzyklus auszulösen.

**Offen:**

- `tf5` aus MATLAB exportieren und mit dem Fit vergleichen; erst dann ist der Widerspruch
  zum Tuner-Ergebnis entschieden.
- Neue Servos (W5652H) vermessen und `ServoParams` aktualisieren (bis dahin `ServoParams.w5652h()` als
  Annahme); die Ratenbegrenzung ist seit 05.11.2026 im Modell (`rate_limit_dps`), der Wert kommt aus E01.
- Gyro-Rauschen des LSM6DSV16X einsetzen (Modell: 0,4 °/s je Takt aus Simulink); die Kommandoraten der
  250-Hz-Tabellen sind damit eher zu hoch.
- Servo-Grad je TVC-Grad (6 oder 23) und die Polung beider Achsen am Tisch messen.
- Das CAD-Massenmodell (981 g) bestätigt: mit 0,9..1,0 kg trägt die E12 die Rakete nur knapp
  (Gipfel 9..10 m). Masse senken oder F35 rechnen (`--vehicle cad`, Schubkurve `MotorParams(curve="F35")`;
  dann aber Beschleunigungsbereich ±4 g der IMU prüfen, PROJECT.md §5 Punkt 4). [Erledigt 22.10.2026 über die
  Masse: die Modulbauweise *Kartonaut 1* wiegt 723 g (`--vehicle stand2b`) und erreicht 63 m am E12, siehe Nachtrag oben.]
- Die zweite Zündung bei 7,3 s trifft im Modell die fallende Rakete (ohne Boden) oder kommt nach
  der Landung (mit Boden); für eine Flugvorhersage gehört ein Flugzustandsautomat hinein.
- Der Vergleich mit dem Simulink-Nominallauf ist nur über das Bild
  `Images/Monte-Carlo (1).png` möglich (45 m Gipfel, Streuung ±20 m seitlich bei 7 s);
  `run_montecarlo.py --vehicle preload --gains preload` liegt in dieser Größenordnung.
  Ein MATLAB-Export des Nominallaufs würde den Vergleich quantitativ machen.
