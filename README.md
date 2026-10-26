# Kartonaut

<img src="docs/brand/kartonaut_patch.svg" width="150" align="right" alt="Kartonaut mission patch">

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Firmware: PlatformIO / Teensy 4.1](https://img.shields.io/badge/firmware-PlatformIO%20%C2%B7%20Teensy%204.1-orange.svg)](firmware/)
[![Simulation: Python 6DOF](https://img.shields.io/badge/simulation-Python%206DOF-3776AB.svg)](simulation/)
[![CI](https://github.com/Jan-Philipp-Munsch/kartonaut/actions/workflows/ci.yml/badge.svg)](https://github.com/Jan-Philipp-Munsch/kartonaut/actions/workflows/ci.yml)

*Deutsche Fassung: [README.de.md](README.de.md). The detailed documents are in German.*

**Kartonaut** is German *Karton* (cardboard) plus astronaut: the airframe is a cardboard tube. Flights are numbered, the first one is *Kartonaut 1*. Patch and logo in [`docs/brand/`](docs/brand/).

A thrust-vector-controlled (TVC) model rocket with a home-built flight computer, modelled on the
"Scout F" by [BPS.space](https://bps.space). The motor sits in a two-servo gimbal; a Teensy 4.1 with
IMU, barometer, power monitor, SD logger and a 433 MHz LoRa link holds the attitude and talks to a
ground station operated from a phone. The whole system is simulated in a six-degree-of-freedom model
before it flies. *Kartonaut 1* flies on one TSP E12, holds its attitude during the burn and comes back
on a parachute pushed out by a CO₂ cartridge. Landing legs, a landing burn on a second motor, a roll
motor and pyro channels are kept for later flights and already provided for on the board.

*Last updated: 26 Oct 2026.*

<img src="docs/img/bauanleitung/Z1_uebersicht.png" width="260" align="right" alt="Kartonaut 1 in modular construction: overview drawing">

## At a glance: *Kartonaut 1*

| | |
|---|---|
| Airframe | Klima cardboard tube Ø 75 mm (ID 72.6 mm) in three modules: tube A 125 mm (gimbal), tube B 176 mm (avionics), tube C 195 mm (recovery); two half couplers, Klima plastic nose cone; 731 mm overall. All radial screws M3 |
| Motor | TSP E12-0, 24 mm, 39 Ns, 12 N average, 28 N peak, 3.5 s burn, no ejection charge; four on hand |
| Lift-off mass | **705 g** in the mass budget ([`cad/mass_stand2b.md`](cad/mass_stand2b.md), printed parts state 2c), centre of gravity 259 mm above the nozzle, lever arm gimbal–CG 190 mm, thrust-to-weight 1.7; target below 750 g met. Nothing weighed yet |
| Flight computer | Teensy 4.1 on mainboard **rev B1** (KiCad from code, fully routed, DRC 0 errors, order files ready, in review): LSM6DSV16X IMU, BMP390 barometer, INA239 power monitor, all on SPI1 behind a chip-select decoder; LIS3MDL magnetometer and SHT40 on I²C; LoRa E22-400T22S, microSD, four pyro channels (two populated), stacking connector |
| Power | two batteries: 1S LiPo for the electronics (buck-boost), 2S LemonRC 450 mAh for the servos; FET load switches behind a mechanical switch, both charged inside the rocket |
| Actuators | push-rod gimbal with 2 × FrSky Xact W5652H directly on 2S (built and fitted into tube A); one servo releases the CO₂ cartridge. No roll motor on the first flight |
| Recovery | 8 g CO₂ cartridge pushes the nose cone off; 125 cm parachute in tube C |
| Control | attitude as a quaternion from the gyro, PID on pitch/yaw → torque → gimbal angle via `M = l · T · sin δ`; 100 Hz; roll uncontrolled. Flight state machine `SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED` with watchdog and state memory |
| Simulation | Python 6DOF: at 705 g one E12 carries the rocket to about 74 m (no drag); Kp 2 / Ki 1 / Kd 0.45 from a Bayesian optimisation keep the tilt below 2.5° without hitting the gimbal stop |
| Ground system | ESP32-S3 ground station with a web UI for the phone, ignition over a 15 m line with key, ARM switch and relay; launch stand 600 × 600 mm on three adjustable legs |
| Status | gimbal, tube A and tube B built; board ready to order after review; flight and bench-test firmware written and tested without hardware; **no flight yet** |

## Project status

**Done**

- Concept, mass and power budget; airframe parts, parachute, motors, CO₂ cartridges and the test-rig drive bought; push-rod gimbal with the W5652H built.
- **Build manual for *Kartonaut 1*** in modular construction with drawings, 1:1 drilling templates, parts list, build steps, maintenance and cable plan; mass budget state 2c (705 g).
- **6DOF simulation**: MATLAB/Simulink model ported to Python with a 1:1 copy of the flight controller; physics review (drag, ground contact, propellant model), Bayesian gain tuning, landing-burn and throttle studies; 45 tests.
- **Flight firmware**: gyro quaternion, flight state machine, pyro logic, telemetry protocol with CRC, watchdog with state memory, sensor backends for breakouts and rev B, landing burn and throttle law (disabled for the first flight); 42 native tests including software-in-the-loop against the simulation.
- **Bench-test firmware for rev B1**: drivers for LIS3MDL, SHT40, ADXL375, IMU self-test, test console `revb_test`, guided calibration stored with CRC, `bench_test.py` on the PC, experiment procedures E01, E02, E05 and twelve bench procedures.
- **Mainboard rev B1**: review points and decisions E1–E12 worked in, fully routed (DRC 0 errors, 0 open), Gerber/BOM/CPL for JLCPCB, review guide and shopping list.
- **Ground station** (concept, safety concept, circuit, BOM, ESP32-S3 firmware with web UI) and **launch stand** (CAD checked against the rocket); interfaces rocket/pad/station/phone defined; budget plan to the first flight.
- CI on GitHub Actions: every PlatformIO environment, simulation tests, native and host tests, pin check against the board.

**Next**

1. Review rev B1 after [`REVIEW_ANLEITUNG_revB1.md`](hardware/mainboard/REVIEW_ANLEITUNG_revB1.md), paper test fit in tube B, repeat the JLCPCB quote with the files in `hardware/mainboard/kicad/fab/` and order after sign-off (a test quote with the older rev B files came to about $165 for two assembled boards); buy the rest after [`EINKAUFSLISTE_revB1.md`](hardware/mainboard/EINKAUFSLISTE_revB1.md).
2. Firmware: LSM6DSV16X driver behind `Imu.h`, CO₂ release from the state machine, calibration data into the rev B sensor path, shared telemetry header with the ground station.
3. Build the rocket after the manual: print and weigh the parts, weigh the rocket, balance the centre of gravity, put mass, lever arm and the new gains into `Config.h`.
4. Bench test of rev B1 with `revb_test`, then ground tests: servo-to-gimbal ratio (E01/E02), CO₂ ejection three times (also cold), TVC test rig with the propeller motor, radio range, launch interlock from the phone.
5. Build ground station and launch stand (about €80 and €86).
6. *Kartonaut 1*: controlled ascent on one motor, parachute recovery.

Work packages, findings and changelog are in [PROJECT.md](PROJECT.md), the build log in
[docs/BUILD.md](docs/BUILD.md), the plan to the first flight in [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md),
the budget in [docs/Budget_2026-10-22.md](docs/Budget_2026-10-22.md).

## Build manual: *Kartonaut 1* in modular construction

[docs/Bauanleitung_Kartonaut1.md](docs/Bauanleitung_Kartonaut1.md) (German, also as a
[PDF](docs/bauanleitung/Bauanleitung_Kartonaut1.pdf)) describes how the first flyer grows out of the
gimbal that already exists. Four modules, three joints with four M3 screws each into captive nuts:

| Module | Contents |
|---|---|
| M1 propulsion | tube A 125 mm with the push-rod gimbal, two W5652H, motor flush at the bottom |
| M2 avionics | tube B 176 mm, coupler with screw ring, printed sled with bulkhead, board, 2S and 1S, GPS under the bulkhead, LoRa helix at the bottom, switch panel behind hatch B |
| M3 recovery | tube C 195 mm, CO₂ module on the bulkhead, parachute, shock cord |
| M4 nose | Klima nose cone with its wooden plate and hook, fitted over the second half coupler |

<p>
<img src="docs/img/bauanleitung/modular_section.png" width="22%" alt="Section of the modular construction">
<img src="docs/img/bauanleitung/modular_avionik_rumpf.png" width="36%" alt="Avionics sled in tube B, component side">
<img src="docs/img/bauanleitung/Z5_schlitten.png" width="38%" alt="Drawing Z5: sled with bulkhead">
</p>

Decisions fixed by state 2b: no ring stack and no threaded rods (the board sits on a printed sled),
**no roll motor** (mass, vibration, hardly any roll torque without fins), **CO₂ instead of black powder**
(no explosives, testable on the bench as often as needed), screw switch instead of key switch, GPS and
LoRa antenna in the avionics bay. Drawings and templates come from
[`docs/bauanleitung/zeichnungen.py`](docs/bauanleitung/zeichnungen.py), the printed parts from
[`cad/modular.py`](cad/modular.py).

```bash
MS_CONFIG=erstflug python cad/modular.py       # printed parts, collision check, mass, renders
python docs/bauanleitung/zeichnungen.py        # drawings and 1:1 templates
python cad/mass_stand2b.py                     # mass budget, centre of gravity, inertia
```

## Mass budget

Four models in three days, each lighter than the last. Model values from
[`cad/mass_properties.md`](cad/mass_properties.md) and [`cad/mass_stand2b.md`](cad/mass_stand2b.md);
weighing follows the printing.

| Configuration | Lift-off | CG above nozzle | Lever arm gimbal–CG | Ixx = Iyy | Izz (roll) | E12 in the simulation |
|---|---|---|---|---|---|---|
| `voll` (21 Oct): 1000 mm, legs, ring stack, piston | 981 g | 449 mm | 372 mm | 0.110 kg·m² | 0.00105 kg·m² | 20 m, thrust-to-weight 1.1 |
| `erstflug` (22 Oct): 700 mm, no legs, piston | 761 g | 318 mm | 242 mm | 0.046 kg·m² | 0.00057 kg·m² | – |
| State 2b (22 Oct): 496 mm tube in three modules, CO₂, no roll motor | 723 g | 256 mm | 186 mm | 0.021 kg·m² | 0.00047 kg·m² | 63 m |
| **State 2c (23 Oct): lightweight printed parts** | **705 g** | 259 mm | 190 mm | 0.021 kg·m² | 0.00047 kg·m² | **74 m**, thrust-to-weight 1.7 |

The lever arm is half that of `voll`, the transverse inertia a fifth. With the true values the old gains
Kp 5 / Kd 1 sit at the gimbal stop for two thirds of the burn; Kp 2 / Ki 1 / Kd 0.45 from a Bayesian
optimisation (`simulation/scripts/tune_bayes.py`, robust against 30 and 50 ms servo dead time) control
cleanly. Further levers down to 593 g are in
[docs/Gewicht_und_Landung_2026-10-23.md](docs/Gewicht_und_Landung_2026-10-23.md). Peak thrust of the E12
on 705 g gives about 4 g on the accelerometer, well inside the ±16 g of the IMU.

## What the simulation says

The Simulink model (rigid body with quaternions, TSP E12 thrust curve, servo transfer function
identified from step responses, sensor noise, static misalignment, ground contact, optional drag) lives
in [`simulation/`](simulation/README.md) as the Python package `tvcsim`. It has two controllers, the
Simulink one and a line-by-line port of the firmware's control law, and vehicle sets from the mass
models. The [physics review](docs/Physik_Review_2026-10-23.md) of 23 Oct checked the model and added a
landing mode.

![Controller comparison](docs/img/sim/compare_gains_preload.png)

Findings that changed the project:

- **The 1 kg rocket was too heavy for an E12** (thrust-to-weight 1.1, apogee 20 m). Instead of a
  stronger motor the rocket got lighter: *Kartonaut 1* at 705 g reaches about 74 m (no drag, about 10 %
  less with it).
- **The light rocket needs smaller gains** (see the mass budget above). The gains of the earlier MATLAB
  grid search were wrong as well: D term 40 times too large, gimbal in its limit, oscillation at 3–4 Hz.
- **The servo-to-gimbal ratio decides the control authority.** To be measured on the built gimbal
  ([E01](docs/experiments/E01_servo_ident.md), [E02](docs/experiments/E02_TVC_Charakterisierung_revB1.md)).
- **Without roll control the attitude has to be a quaternion.** Component-wise angle integration puts a
  tilt error into the wrong servo axis as soon as the rocket rolls; the flight firmware now integrates a
  quaternion.
- **Landing on a second motor is a later step.** Without throttling only a 0.75–0.80 kg rocket lands
  softly on an E12; with a Scout-F-style throttle 0.5–0.65 kg land at 1.2–2 m/s nominally, 2–3 m/s in
  Monte Carlo. *Kartonaut 1* uses the parachute.

<p>
<img src="docs/img/sim/montecarlo_preload.png" width="48%" alt="Monte Carlo trajectories">
<img src="docs/img/sim/servo_fit.png" width="48%" alt="Servo step response and fit">
</p>

```bash
cd simulation
python -m pytest tests                 # 45 tests
python scripts/run_nominal.py --controller firmware --vehicle stand2b --single-motor --fuel impulse
python scripts/check_stand2b_levers.py # weight packages against controller gains
python scripts/tune_bayes.py           # Bayesian gain search
python scripts/landing_study.py        # landing burn over mass, Monte Carlo
```

## Hardware: mainboard rev B1

Today all sensors hang off the Teensy as breakout boards with jumper wires, which is the biggest
failure risk in flight. [hardware/mainboard/](hardware/mainboard/README.md) specifies the mainboard: a
54 × 120 mm sled with the Teensy socket, the IMU exactly on the roll axis and all connectors on the end
faces. In the modular construction it sits on the printed sled in tube B.

<img src="hardware/mainboard/kicad/img/render_top.png" width="100%" alt="Mainboard, routed, rendered from above">

The KiCad project in [hardware/mainboard/kicad/](hardware/mainboard/kicad/README.md) is generated from
a single Python description of the circuit (`circuit.py`): seven schematic sheets, ERC without errors,
a board generator with outline, four layers, net classes, keep-outs and Freerouting, finished with an
own grid router and by hand ([schematic PDF](hardware/mainboard/kicad/out/mainboard_schematic.pdf)).
`./make.sh fab` writes Gerber, BOM and CPL for JLCPCB to `kicad/fab/`. The
[review brief](hardware/mainboard/review_brief_2026-10-23.md) gives the board in numbers and the points
to look at; the [design guide](docs/DesignGuide_Mainboard_revB.md) ([PDF](docs/DesignGuide_Mainboard_revB.pdf))
and the [datasheet](hardware/mainboard/datasheet/) present the design.

A [second-opinion review](hardware/mainboard/review_kicad_2026-10-21.md) of rev B found eight points;
together with the decisions in [Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md)
they went into rev B1:

- **Mechanical main switch, current through FETs**; polyfuse per battery; Kelvin shunt with INA239.
- **Charging inside the rocket**: 1S over USB-C on the board, 2S through a balancer socket.
- **All flight sensors on SPI1** behind a 74HC138 chip-select decoder, analog channels through a 74HC4051
  mux; I²C for magnetometer, SHT40 and the Qwiic expansion.
- **LSM6DSV16X instead of ICM-42688-P** on the same land pattern (3.4 instead of 21.5 USD at JLCPCB, in stock).
- **All servos directly on 2S**, no 5 V buck.
- **Room for later flights**: four pyro channels, a fourth servo connector, ADXL375 (±200 g) as a
  footprint, stacking connector `J_STACK`.

The firmware matches it: [`firmware/lib/mainboard_revb/`](firmware/README.md) holds pins, decoder, mux
and drivers; `check_board_pins.py` compares the pins with `circuit.py`, also in CI. Rev A and the
reasoning behind the sled layout are kept in [`rev_a_2026-10-15.md`](hardware/mainboard/rev_a_2026-10-15.md).

## Ground station and launch stand

<img src="docs/img/cad/landingpad.png" width="300" align="right" alt="Launch stand with Kartonaut 1">

The **ground station** ([groundstation/](groundstation/README.md)) ignites the motor over a 15 m line,
receives the LoRa telemetry and shows both in the phone's browser through its own Wi-Fi access point.
The station decides, the phone displays: arming only works with the key and the ARM switch on the box,
the ignition path runs through a relay and a MOSFET, the launch interlock checks igniter continuity,
fresh telemetry and the flight state `PAD_READY`; a heartbeat from the phone aborts the countdown on
connection loss. Budget version from modules about €80 ([circuit](groundstation/Schaltung.md)).

The **launch stand** ([`cad/landingpad.py`](cad/README.md)) is a 600 × 600 mm plywood plate with a hole
for the jet, three individually adjustable M10 legs (up to 23° ground slope) and three removable guides;
the script checks it against the rocket. 6.5 kg, about €86 of hardware-store parts. Interfaces between
rocket, stand, station and phone are in
[docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md).

## Ground testing

Before anything flies, the attitude control gets tested on the ground with real thrust and without a
rocket motor: the rocket hangs in a rig that lets it pitch and yaw about its centre of gravity, and a
brushless motor (Racerstar BR2814, 1000 KV, 11-inch propeller, 4S LiPo) sits in the gimbal in place of
the rocket motor. The drive is bought, the rig is designed in [`cad/testrig.py`](cad/README.md). Added
to that: the CO₂ ejection test, radio range with two E22 modules and the interlock test from the phone
down to a lamp on the firing line. Experiments are prepared as ready-to-run procedures in
[`docs/experiments/`](docs/experiments/README.md), bench procedures for the board in
[`firmware/Versuche_revB1.md`](firmware/Versuche_revB1.md).

<p>
<img src="docs/img/cad/testrig.png" width="40%" alt="Test rig: rocket in the two-axis frame">
<img src="docs/img/cad/testrig_drive.png" width="52%" alt="Drive end: propeller motor in the gimbal with guard cage">
</p>

## Firmware

PlatformIO project for the Teensy 4.1 in [`firmware/`](firmware/README.md). The main loop runs at a
fixed 100 Hz: read the sensors, integrate the attitude quaternion from the gyro, estimate the altitude
with a two-state Kalman filter, step the flight state machine, control pitch and yaw through the gimbal,
send telemetry, log one frame per pass to SD. A watchdog with state memory resumes the flight after a
reset.

```bash
cd firmware
pio run                            # flight firmware, breakout setup
pio run -e teensy41_revb           # flight firmware for mainboard rev B1
pio test -e native                 # 42 tests without hardware
pio run -e revb_test -t upload     # bench-test console for rev B1
python tools/bench_test.py         # drive the console from the PC, report as Markdown + JSON
python tools/check_board_pins.py   # firmware pins against circuit.py
```

The bench test step by step is in [`firmware/Tischtest_revB1.md`](firmware/Tischtest_revB1.md). Pins,
gains, thresholds and switches live in [`firmware/src/Config.h`](firmware/src/Config.h); the controllers
stay off there until the test rig clears them, and the landing burn is disabled (`RECOVERY_MODE = CHUTE`).

## Repository layout

```
firmware/               flight firmware (PlatformIO, Teensy 4.1)              -> firmware/README.md
  src/                  Attitude, FlightState, Pyro, Telemetry, ControlLaw, KalmanZ, SDLogger, LandingBurn, ...
  lib/mainboard_revb/   pins, CS decoder, mux, drivers for the rev B1 sensors
  lib/calstore/         calibration data with CRC, ellipsoid fit, axis mapping
  examples/             revb_test, revb_bringup, servo_ident and small test sketches
  test/                 native tests (pio test -e native) and host tests
groundstation/          ground station: concept, circuit, ESP32-S3 firmware   -> groundstation/README.md
simulation/             6DOF simulation in Python, package tvcsim             -> simulation/README.md
hardware/mainboard/     mainboard: specification, decisions, KiCad from code, fab files, datasheet, reviews, order
cad/                    parametric CAD, modular construction, launch stand, test rig, mass models -> cad/README.md
docs/                   build manual, experiments, design guide, build log, plans, budget, reviews, images
.github/workflows/      CI: PlatformIO environments, simulation, native and host tests, pin check
PROJECT.md              project file: key data, work packages, findings, changelog
```

The old ground station (Arduino Nano with HC-12) is its own repository,
[kartonaut-ground](https://github.com/Jan-Philipp-Munsch/kartonaut-ground); its successor is
`groundstation/`. The MATLAB/Simulink original of the simulation and the Blender files stay outside this
repository; their content is ported here.

## Documentation

| Document | What it holds |
|---|---|
| [PROJECT.md](PROJECT.md) | key data, work packages with status, findings, next steps, changelog |
| [docs/Baustellen_2026-10-26.md](docs/Baustellen_2026-10-26.md) | open work by strand (board, repo, firmware, mechanics, simulation, ground systems) with a suggested order up to the first flight |
| [docs/Bauanleitung_Kartonaut1.md](docs/Bauanleitung_Kartonaut1.md) | build manual: modules, parts list, build steps, maintenance, cable plan ([PDF](docs/bauanleitung/Bauanleitung_Kartonaut1.pdf), [drawings](docs/bauanleitung/Zeichnungen_Kartonaut1.pdf), [1:1 templates](docs/bauanleitung/Bohrschablonen_1zu1.pdf)) |
| [cad/mass_stand2b.md](cad/mass_stand2b.md) | mass budget *Kartonaut 1*: mass, CG, lever arm, inertia, parts list |
| [docs/Gewicht_und_Landung_2026-10-23.md](docs/Gewicht_und_Landung_2026-10-23.md) | weight levers to 593 g, gains, landing study with our masses |
| [docs/Physik_Review_2026-10-23.md](docs/Physik_Review_2026-10-23.md) | physics review of the simulation, landing burn, throttle |
| [docs/experiments/README.md](docs/experiments/README.md) | ready-to-run experiments E01, E02, E05 |
| [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md) | plan to the first flight with milestones |
| [docs/Budget_2026-10-22.md](docs/Budget_2026-10-22.md) | budget to the first flight |
| [docs/BUILD.md](docs/BUILD.md) | as-built: parts, mechanics, wiring, tests, build log |
| [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md) | interfaces rocket/pad, firing line, radio, phone |
| [hardware/mainboard/README.md](hardware/mainboard/README.md) | mainboard specification |
| [hardware/mainboard/review_brief_2026-10-23.md](hardware/mainboard/review_brief_2026-10-23.md) | rev B1 for the reviewer, with [review guide](hardware/mainboard/REVIEW_ANLEITUNG_revB1.md) and [shopping list](hardware/mainboard/EINKAUFSLISTE_revB1.md); [review package of 2026-10-26](hardware/mainboard/REVIEW_PAKET_2026-10-26.md) with checks run, reading order and decisions before ordering; [JLCPCB test quote](hardware/mainboard/Angebot_JLCPCB_2026-10-23.md) |
| [hardware/mainboard/Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md) | decisions, parts by rail and interface, pin budget |
| [hardware/mainboard/ORDER.md](hardware/mainboard/ORDER.md) | order plan: gates, JLCPCB parameters, mating connectors, costs |
| [docs/DesignGuide_Mainboard_revB.md](docs/DesignGuide_Mainboard_revB.md) | design with figures ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) |
| [groundstation/README.md](groundstation/README.md) | ground station: concept, safety, launch-site procedure, firmware, BOM |
| [firmware/README.md](firmware/README.md) | firmware modules, flight sequence, telemetry, tests, rev B library |
| [firmware/Tischtest_revB1.md](firmware/Tischtest_revB1.md) | bench test of rev B1 |
| [simulation/README.md](simulation/README.md) | model, coordinates, assumptions, vehicle sets, results |
| [cad/README.md](cad/README.md) | parametric model, modular construction, test rig, launch stand |
| [cad/blender_inventory.md](cad/blender_inventory.md) | what the 16 Blender files contain |

## License

[MIT](LICENSE). The BPS.space Scout F files that served as reference are not part of this repository.
