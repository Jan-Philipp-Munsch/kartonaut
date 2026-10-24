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

*Last updated: 24 Oct 2026.*

<img src="docs/img/cad/rocket_overall.png" width="200" align="right" alt="Parametric CAD model (CadQuery)">

## At a glance: *Kartonaut 1*

| | |
|---|---|
| Airframe | Klima cardboard tube Ø 75 mm (ID 72.6 mm) in three modules (gimbal, avionics, recovery) joined by half couplers with M3 screws, Klima plastic nose cone; 731 mm overall |
| Motor | TSP E12-0, 24 mm, 39 Ns, 12 N average, 3.5 s burn, no ejection charge; four on hand |
| Lift-off mass | **705 g** in the mass budget (state 2c), centre of gravity 259 mm above the nozzle, lever arm gimbal–CG 190 mm, thrust-to-weight 1.7; target below 750 g met. Nothing weighed yet |
| Flight computer | Teensy 4.1 on mainboard **rev B1** (KiCad from code, fully routed, DRC clean, in review before the order): ICM-42688-P IMU, BMP390 barometer, INA239 power monitor, all on SPI1; LIS3MDL magnetometer and SHT40 on I²C; LoRa E22-400T22S, microSD, four pyro channels (two populated), stacking connector |
| Power | two batteries: 1S LiPo for the electronics (buck-boost), 2S LiPo for the servos; FET load switches behind a mechanical switch, both charged inside the rocket |
| Actuators | push-rod gimbal with 2 × FrSky Xact W5652H directly on 2S (built); one servo releases the CO₂ cartridge. No roll motor on the first flight |
| Recovery | 8 g CO₂ cartridge pushes the nose cone off, 125 cm parachute |
| Control | attitude from the gyro (quaternion), PID on pitch/yaw → torque → gimbal angle via `M = l · T · sin δ`; 100 Hz. Roll stays uncontrolled |
| Simulation | Python 6DOF: at 705 g one E12 carries the rocket to about 74 m (no drag); gains Kp 2 / Ki 1 / Kd 0.45 keep the tilt below 2.5° without hitting the gimbal stop |
| Ground system | ESP32-S3 ground station with a web UI for the phone, ignition over a 15 m line with key and ARM switch; launch stand 600 × 600 mm on three adjustable legs |
| Status | gimbal and two tube modules built, board rev B1 ready for the order, bench-test console for rev B1 merged; **no flight yet** |

## Project status

**Done**

- Concept, mass and power budget; airframe parts, parachute, motors, CO₂ cartridges and the test-rig drive bought; push-rod gimbal with the W5652H built.
- 6DOF simulation: MATLAB/Simulink model ported to Python with a 1:1 copy of the flight controller; vehicle sets from the CAD mass models.
- Firmware base: sensors, altitude Kalman filter, SD logger with CSV export, controllers, timing, indicators; SPI drivers and pin map for rev B.
- **Firmware for the rev B1 bench test** ([PR #6](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/6), merged 23 Oct): drivers for LIS3MDL, SHT40 and ADXL375, IMU self-test, test console `revb_test` with one command per function, guided calibration (gyro, six positions, magnetometer ellipsoid, axis mapping, ADC, INA239, servo trim) stored with CRC in the EEPROM emulation, `bench_test.py` to drive it from the PC, twelve experiment procedures.
- CI on GitHub Actions: every PlatformIO environment, simulation tests, host tests, pin check against the board.
- Mainboard rev B: specification, design guide, datasheet, KiCad project from code, second-opinion review, manufacturer decision (JLCPCB), order plan, decisions E1–E10.
- Parametric CAD (CadQuery) with mass model, test rig, first-flight configuration; the 16 Blender files inventoried and superseded.

**Waiting for review and merge** (work is finished on a branch, not yet in `main`)

| What | Where |
|---|---|
| **Mainboard rev B1**: all review points worked in, extra sensors, fully routed (DRC 0 errors, 0 open), Gerber/BOM/CPL for JLCPCB, review brief for a second pair of eyes | [PR #5](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/5) |
| **Flight firmware** B1–B8: gyro quaternion, flight state machine `SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED`, pyro logic, telemetry protocol, watchdog with state memory, sensor backends for breakouts and rev B, 32 native tests incl. software-in-the-loop against the simulation | [PR #3](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/3) |
| **Physics review and landing burn**: drag, ground contact, landing burn on a second E12, thrust throttle after Scout F, in simulation and firmware (disabled for the first flight) | [PR #4](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/4) |
| **Experiment E01**: servo → gimbal transfer function as a ready-to-run experiment with analysis script | [PR #2](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/2) |
| **Consolidation of 22 Oct**: build manual for *Kartonaut 1* in modular construction (drawings, 1:1 drilling templates, parts list), mass budget state 2b/2c (705 g), Bayesian gain tuning, ground station (concept, circuit, ESP32-S3 firmware), launch stand, budget plan | branch [`claude/konsolidierung`](https://github.com/Jan-Philipp-Munsch/kartonaut/tree/claude/konsolidierung) |

**Next**

1. Review and order the board: second opinion on rev B1, settle the IMU range (the ICM-42688-P saturates at ±16 g, LSM6DSO32 with ±32 g as the alternative), repeat the JLCPCB quote with the rev B1 files and order. A test quote with the older rev B files came to about $165 for two assembled boards.
2. Merge the open PRs and the consolidation into `main`.
3. Build the rocket after the manual, weigh it, balance the centre of gravity, put the measured values into `Config.h`.
4. Bench test of rev B1 with `revb_test`, then ground tests: CO₂ ejection, TVC test rig with the propeller motor, radio range, launch interlock from the phone.
5. Build ground station and launch stand.
6. *Kartonaut 1*: controlled ascent on one motor, parachute recovery.

Work packages, findings and changelog are in [PROJECT.md](PROJECT.md), the build log in
[docs/BUILD.md](docs/BUILD.md), the plan to the first flight in [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md).

## What the simulation says

The Simulink model (rigid body with quaternions, TSP E12 thrust curve, servo transfer function
identified from step responses, sensor noise, static misalignment) lives in
[`simulation/`](simulation/README.md) as the Python package `tvcsim`. It has two controllers, the
Simulink one and a line-by-line port of the firmware's `Control.cpp`, so both can be compared in the
same model.

![Controller comparison](docs/img/sim/compare_gains_preload.png)

Findings that changed the project:

- **The 1 kg rocket was too heavy for an E12** (thrust-to-weight 1.1, apogee 20 m). Instead of a
  stronger motor the rocket got lighter: from 981 g (21 Oct) through 761 g to **705 g** for
  *Kartonaut 1*, which reaches about 74 m in the model.
- **The light rocket needs smaller gains.** Lever arm and transverse inertia shrank to half and a fifth.
  With the true values the old firmware gains Kp 5 / Kd 1 drive the gimbal to its stop for two thirds
  of the burn; Kp 2 / Ki 1 / Kd 0.45 from a Bayesian optimisation control the rocket cleanly.
- **The gains of the MATLAB grid search were wrong** (D term 40 times too large, gimbal in its limit,
  oscillation at 3 to 4 Hz).
- **The servo-to-gimbal ratio decides the control authority.** To be measured on the built gimbal
  (experiment E01).
- **Without roll control the attitude has to be a quaternion.** Integrating angles component by
  component puts a tilt error into the wrong servo axis as soon as the rocket rolls. That is the
  condition for dropping the roll motor, and the flight firmware in PR #3 does it.

<p>
<img src="docs/img/sim/montecarlo_preload.png" width="48%" alt="Monte Carlo trajectories">
<img src="docs/img/sim/servo_fit.png" width="48%" alt="Servo step response and fit">
</p>

```bash
cd simulation
python -m pytest tests                 # tests, also in CI
python scripts/run_nominal.py          # nominal flight -> out/
python scripts/run_montecarlo.py       # 100 runs
python scripts/compare_gains.py --vehicle preload
```

## Hardware: mainboard rev B / B1

Today all sensors hang off the Teensy as breakout boards with jumper wires, which is the biggest
failure risk in flight. [hardware/mainboard/](hardware/mainboard/README.md) specifies the mainboard: a
54 × 120 mm sled with the Teensy socket, the IMU exactly on the roll axis and all connectors on the end
faces.

<img src="hardware/mainboard/kicad/img/render_top.png" width="100%" alt="Mainboard rev B, routed, rendered from above">

The KiCad project in [hardware/mainboard/kicad/](hardware/mainboard/kicad/README.md) is generated from
a single Python description of the circuit (`circuit.py`): seven schematic sheets, ERC without errors,
a board generator with outline, four layers, net classes, keep-outs and Freerouting
([schematic PDF](hardware/mainboard/kicad/out/mainboard_schematic.pdf)). The
[design guide](docs/DesignGuide_Mainboard_revB.md) ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) presents
the design with figures, the [order plan](hardware/mainboard/ORDER.md) lists parts, gates and costs.

A [second-opinion review](hardware/mainboard/review_kicad_2026-10-21.md) of rev B found eight points
(buck-boost output capacitance, 1S undervoltage threshold, main switch in the current path, fuse per
battery, Kelvin shunt, 2S currents on the inner layer). Together with ten decisions
([Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md)) they went into **rev B1**
([PR #5](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/5)):

- **Mechanical main switch, current through FETs**; polyfuse per battery; Kelvin shunt with INA239.
- **Charging inside the rocket**: 1S over USB-C on the board, 2S through a balancer socket.
- **All flight sensors on SPI1** behind a 74HC138 chip-select decoder, analog channels through a
  74HC4051 mux; I²C only for the magnetometer, SHT40 and the Qwiic expansion.
- **All servos directly on 2S**, no 5 V buck.
- **Room for later flights**: four pyro channels, a fourth servo connector, ADXL375 (±200 g) as a
  footprint, stacking connector `J_STACK`.
- Power paths as copper pours on the outer layer, 5 mm keep-out around the IMU; routed by Freerouting,
  an own grid router and by hand.

The firmware matches it: [`firmware/lib/mainboard_revb/`](firmware/README.md) holds pins, decoder, mux
and the drivers; `check_board_pins.py` compares the pins with `circuit.py`, also in CI. Rev A and the
reasoning behind the sled layout are kept in [`rev_a_2026-10-15.md`](hardware/mainboard/rev_a_2026-10-15.md).

## CAD model

The Blender files are inventoried in [`cad/blender_inventory.md`](cad/blender_inventory.md) and replaced
by a parametric model in CadQuery ([`cad/`](cad/README.md)): every dimension in `cad/params.py` with its
source, STEP and STL per assembly, a collision check of the gimbal at ±7°, renders through Blender
headless. The same parameters feed a mass model ([`cad/mass_properties.md`](cad/mass_properties.md)).
The modular construction of *Kartonaut 1* with its mass budget is on the consolidation branch.

<p>
<img src="docs/img/cad/rocket_section.png" width="24%" alt="Section: motor, gimbal, flight computer, parachute, nose cone">
<img src="docs/img/cad/rocket_tvc.png" width="37%" alt="Gimbal with the two W5652H servos, deflected 5° and 4°">
<img src="docs/img/cad/rocket_avionics.png" width="37%" alt="Flight computer module">
</p>

```bash
python -m pip install --user cadquery
python cad/build.py              # STEP/STL to cad/export/, renders to docs/img/cad/
python cad/mass_model.py         # mass_properties.md and .json
```

## Ground testing

Before anything flies, the attitude control gets tested on the ground with real thrust and without a
rocket motor: the rocket hangs in a rig that lets it pitch and yaw about its centre of gravity, and a
brushless motor (Racerstar BR2814, 1000 KV, 11-inch propeller, 4S LiPo) sits in the gimbal in place of
the rocket motor. At part throttle it delivers the 12 N of the E12. The drive is bought, the rig is
designed in [`cad/testrig.py`](cad/README.md) and checked for collisions. Added to that: the CO₂ ejection
test, radio range with two E22 modules and the interlock test from the phone down to a lamp on the firing
line. The procedures for the board are in [`firmware/Versuche_revB1.md`](firmware/Versuche_revB1.md).

<p>
<img src="docs/img/cad/testrig.png" width="40%" alt="Test rig: rocket in the two-axis frame">
<img src="docs/img/cad/testrig_drive.png" width="52%" alt="Drive end: propeller motor in the gimbal with guard cage">
</p>

## Firmware

PlatformIO project for the Teensy 4.1 in [`firmware/`](firmware/README.md). The main loop runs at a
fixed 100 Hz: read the sensors, integrate the attitude from the gyro, estimate the altitude with a
two-state Kalman filter (barometer and vertical acceleration), control pitch and yaw through the gimbal,
log one frame per pass to SD.

```bash
cd firmware
pio run                            # build the flight firmware
pio run -t upload                  # flash the Teensy 4.1
pio device monitor                 # serial console, 115200 baud, Teleplot-compatible
pio run -e revb_test -t upload     # bench-test console for mainboard rev B1
python tools/bench_test.py         # drive the console from the PC, report as Markdown + JSON
python tools/check_board_pins.py   # firmware pins against circuit.py
```

The bench test step by step is in [`firmware/Tischtest_revB1.md`](firmware/Tischtest_revB1.md). All
pins, gains, filter constants and debug switches live in [`firmware/src/Config.h`](firmware/src/Config.h);
the controllers stay off there until the first flight test. Quaternion attitude, state machine, pyro
logic, telemetry and watchdog are in [PR #3](https://github.com/Jan-Philipp-Munsch/kartonaut/pull/3).

## Repository layout

```
firmware/               flight firmware (PlatformIO, Teensy 4.1)              -> firmware/README.md
  src/                  modules: Sensors, KalmanZ, Control, SDLogger, Timing, Indicators
  lib/mainboard_revb/   pins, CS decoder, mux, drivers ICM-42688-P, BMP390, INA239, LIS3MDL, SHT40, ADXL375
  lib/calstore/         calibration data with CRC, ellipsoid fit, axis mapping
  examples/             test sketches (revb_test, revb_bringup, radio beacon, I2C scan, pyro MOSFET)
  tools/                bench_test.py, capture_tvc.py, check_board_pins.py
  test/host/            host tests (g++), run in CI
simulation/             6DOF simulation in Python, package tvcsim             -> simulation/README.md
hardware/mainboard/     mainboard: specification, decisions, KiCad from code, datasheet, reviews, order plan
cad/                    parametric CAD, test rig, mass model                  -> cad/README.md
docs/                   design guide, build log, plans, research, images, brand
.github/workflows/      CI: PlatformIO environments, simulation tests, host tests, pin check
PROJECT.md              project file: key data, work packages, findings, changelog
```

The old ground station (Arduino Nano with HC-12) is its own repository,
[kartonaut-ground](https://github.com/Jan-Philipp-Munsch/kartonaut-ground); its successor on the ESP32-S3
is on the consolidation branch. The MATLAB/Simulink original of the simulation and the Blender files stay
outside this repository; their content is ported here.

## Documentation

| Document | What it holds |
|---|---|
| [PROJECT.md](PROJECT.md) | key data, work packages with status, findings, next steps, changelog |
| [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md) | plan to the first flight: work streams board, firmware, mechanics, ground systems, milestones |
| [docs/BUILD.md](docs/BUILD.md) | as-built: bought and printed parts, mechanics, wiring, tests, build log |
| [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md) | interfaces rocket/pad, firing line, radio, phone |
| [docs/Rohrmaterial_2026-10-22.md](docs/Rohrmaterial_2026-10-22.md) | composite tubes versus cardboard: cardboard stays |
| [docs/Plan_2026-10-21.md](docs/Plan_2026-10-21.md) | planning round of 21 Oct: board review, power architecture, port plan |
| [hardware/mainboard/README.md](hardware/mainboard/README.md) | mainboard specification |
| [hardware/mainboard/Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md) | decisions E1–E10, parts by rail and interface, pin budget |
| [docs/DesignGuide_Mainboard_revB.md](docs/DesignGuide_Mainboard_revB.md) | the rev B design with figures ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) |
| [hardware/mainboard/datasheet/](hardware/mainboard/datasheet/) | datasheet MS-MB-B (LaTeX, BOM from `circuit.py`) |
| [hardware/mainboard/ORDER.md](hardware/mainboard/ORDER.md) | order plan: parts to buy now, gates, JLCPCB parameters, costs |
| [hardware/mainboard/review_kicad_2026-10-21.md](hardware/mainboard/review_kicad_2026-10-21.md) | second-opinion review of rev B |
| [hardware/mainboard/Fertiger_2026-10-21.md](hardware/mainboard/Fertiger_2026-10-21.md) | manufacturer comparison and decision |
| [firmware/README.md](firmware/README.md) | firmware modules, log format, test sketches, rev B library |
| [firmware/Tischtest_revB1.md](firmware/Tischtest_revB1.md) | bench test of rev B1: procedure, commands, open questions |
| [firmware/Versuche_revB1.md](firmware/Versuche_revB1.md) | twelve experiment procedures with equipment, setup, targets |
| [simulation/README.md](simulation/README.md) | model, coordinates, assumptions, results |
| [cad/README.md](cad/README.md) | parametric model, test rig, maintenance concept |
| [cad/mass_properties.md](cad/mass_properties.md) | mass model of the earlier configurations |
| [cad/blender_inventory.md](cad/blender_inventory.md) | what the 16 Blender files contain |

## License

[MIT](LICENSE). The BPS.space Scout F files that served as reference are not part of this repository.
