# Kartonaut

<img src="docs/brand/kartonaut_patch.svg" width="150" align="right" alt="Kartonaut mission patch">

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Firmware: PlatformIO / Teensy 4.1](https://img.shields.io/badge/firmware-PlatformIO%20%C2%B7%20Teensy%204.1-orange.svg)](firmware/)
[![Simulation: Python 6DOF](https://img.shields.io/badge/simulation-Python%206DOF-3776AB.svg)](simulation/)
[![CI](https://github.com/Jan-Philipp-Munsch/kartonaut/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

*Deutsche Fassung: [README.de.md](README.de.md). The detailed documents are in German.*

**Kartonaut** is German *Karton* (cardboard) plus astronaut: the airframe is a cardboard tube. Flights are numbered, the first one is *Kartonaut 1*. Patch and logo in [`docs/brand/`](docs/brand/).

A thrust-vector-controlled (TVC) model rocket with a home-built flight computer, modelled on the
"Scout F" by [BPS.space](https://bps.space). The motor sits in a two-servo gimbal; a Teensy 4.1 with
IMU, barometer, power monitor, SD logger and a 433 MHz LoRa link controls the attitude and talks to a
ground station operated from a phone. The whole system is simulated in a six-degree-of-freedom model
before it flies. *Kartonaut 1* flies on one TSP E12, holds its attitude during the burn and returns on
a parachute pushed out by a CO₂ cartridge. Landing legs, a second motor for a landing burn, a roll
motor and pyro channels are reserved for later flights and already provided for on the board.

<img src="docs/img/bauanleitung/Z1_uebersicht.png" width="260" align="right" alt="Kartonaut 1 in modular construction: overview drawing">

## At a glance: *Kartonaut 1* (build state 2b, 22 Oct 2026)

| | |
|---|---|
| Airframe | Klima cardboard tube Ø 75 mm (ID 72.6 mm) in three modules: tube A 125 mm (gimbal), tube B 176 mm (avionics), tube C 195 mm (recovery); two half couplers 75 mm, Klima plastic nose cone. Overall length 731 mm. All radial screws M3 at 0°/90°/180°/270° |
| Motor | TSP E12-0, 24 mm, 39 Ns, 12 N average, 3.5 s burn, no ejection charge; four on hand |
| Lift-off mass | **723 g** in the state-2b mass budget ([`cad/mass_stand2b.md`](cad/mass_stand2b.md)), centre of gravity 256 mm above the nozzle, lever arm gimbal–CG 186 mm, thrust-to-weight 1.7; the 750 g target is met with 27 g to spare. Nothing weighed yet |
| Flight computer | Teensy 4.1 on mainboard rev B (KiCad from code, routed; review points and decisions E1–E10 being worked in): ICM-42688-P IMU, BMP390 barometer, INA239 power monitor, all on SPI1; LoRa E22-400T22S, microSD, four pyro channels (two populated), stacking connector for add-on boards |
| Power | two batteries: 1S LiPo for the electronics (buck-boost), 2S LemonRC 450 mAh for the servos; FET load switches behind a mechanical switch, both batteries charged inside the rocket |
| Actuators | push-rod gimbal with 2 × FrSky Xact W5652H directly on 2S (built and fitted into tube A); one servo releases the CO₂ cartridge. No roll motor on the first flight |
| Recovery | 8 g CO₂ cartridge (about 2 l) pushes the nose cone off; 125 cm parachute (packed 100 × Ø 70) sits in tube C, shock cord in the nose coupler |
| Control | attitude from the gyro only, PID on pitch/yaw → torque → gimbal angle via `M = l · T · sin δ`; 100 Hz. Roll stays uncontrolled, which requires a quaternion attitude (TODO before the first flight) |
| Simulation | Python 6DOF (port of the Simulink model): at 723 g the E12 carries the rocket to about 63 m, tilt during the burn below 2° with the firmware gains |
| Ground system | ESP32-S3 ground station with a web UI for the phone, ignition over a 15 m line with key, ARM switch and relay; launch stand 600 × 600 mm on three adjustable legs, 6.5 kg, about €86 |
| Status | gimbal, tube A and tube B built; board in progress; printed parts and order list of the build manual ready; no flight yet |

## Project status

**Done**

- Concept, mass and power budget; airframe parts, parachute, motors, CO₂ cartridges and test-rig drive bought; gimbal with the W5652H built.
- 6DOF simulation: MATLAB/Simulink model ported to Python with a 1:1 copy of the flight controller, 25 tests; vehicle sets from both CAD mass models.
- Firmware modules: sensors, altitude Kalman filter, SD logger with CSV export, pitch/yaw and roll controllers, timing, indicators; SPI drivers, pin map and bring-up program for rev B; CI builds every environment.
- Mainboard rev B: specification, design guide, datasheet (17 pages), KiCad project from code (ERC and DRC clean, routed), second-opinion review, manufacturer decision, order plan; the decisions of 22 Oct (E1–E10) documented.
- Parametric CAD (CadQuery) with a mass model for the configurations `voll` and `erstflug`; modular construction state 2b with printed parts, full assembly (STEP/GLB) and mass budget.
- **Build manual for *Kartonaut 1*** in modular construction with drawings, 1:1 drilling templates, parts checklist, build steps, maintenance and cable plan.
- **Ground station** (concept, safety concept, circuit, BOM, ESP32-S3 firmware with web UI) and **launch stand** (CAD checked against the rocket, BOM) as sub-projects of their own; interfaces rocket/pad/station/phone defined; budget plan up to the first flight.

**In progress**

- Board rev B1: review points A1–A8 and decisions E1–E10 (FET load switches, charging inside the rocket, BMP390 and INA239 on SPI, all servos on 2S, four pyro channels, no 5 V buck, stacking connector, CS decoder and analog mux), re-route, fabrication files.
- Build manual: print and weigh the parts, place the orders (Reichelt, Berrybase, Ebyte, screws), design the CO₂ module, measure the servo-to-gimbal ratio on the built gimbal.
- Firmware: gyro quaternion with up-vector, flight state machine, telemetry protocol (shared header with the ground station), watchdog.

**Next**

1. Finish the board, paper test fit in the coupler, order at JLCPCB after sign-off; order the bench parts in parallel.
2. Build the rocket after the manual, weigh it, balance the centre of gravity, set `Config.h` to the measured values.
3. Ground tests: CO₂ ejection (three times, also cold), TVC test rig with the propeller motor in the gimbal, radio range with two E22, launch interlock end to end from the phone.
4. Build ground station and launch stand (about €80 and €86, an evening to a weekend each).
5. *Kartonaut 1*: controlled ascent on one motor, parachute recovery. Clarify launch site, permission and insurance first.

The full list of work packages, the findings and the changelog are in [PROJECT.md](PROJECT.md); the
build log in [docs/BUILD.md](docs/BUILD.md); the plan to the first flight with milestones in
[docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md); the budget in [docs/Budget_2026-10-22.md](docs/Budget_2026-10-22.md).

## Build manual: *Kartonaut 1* in modular construction

[docs/Bauanleitung_Kartonaut1.md](docs/Bauanleitung_Kartonaut1.md) (German, also as a
[PDF](docs/bauanleitung/Bauanleitung_Kartonaut1.pdf)) describes how the first flyer grows out of the
gimbal that already exists. Four modules, three joints with four M3 screws each into captive nuts:

| Module | Contents |
|---|---|
| M1 propulsion | tube A 125 mm with the push-rod gimbal, two W5652H, motor flush at the bottom |
| M2 avionics | tube B 176 mm, coupler J1 with screw ring, printed sled with bulkhead (band between B and C), board, 2S and 1S, GPS under the bulkhead, LoRa helix at the bottom, switch panel behind hatch B |
| M3 recovery | tube C 195 mm, CO₂ module on the bulkhead, parachute, shock cord |
| M4 nose | Klima 8539 with its wooden plate and hook, fitted over the second half coupler |

<p>
<img src="docs/img/bauanleitung/modular_section.png" width="22%" alt="Section of the modular construction">
<img src="docs/img/bauanleitung/modular_avionik_rumpf.png" width="36%" alt="Avionics sled in tube B, component side">
<img src="docs/img/bauanleitung/Z5_schlitten.png" width="38%" alt="Drawing Z5: sled with bulkhead">
</p>

Decisions fixed by state 2b: no ring stack and no threaded rods (the board sits on a printed sled),
**no roll motor** (mass, vibration, hardly any roll torque without fins), **CO₂ instead of black powder**
(no explosives law, testable on the bench as often as you like), screw switch instead of key switch, GPS
and LoRa antenna in the avionics bay instead of the jettisoned nose. Drawings Z1–Z6 and drilling templates
S1–S4 come from [`docs/bauanleitung/zeichnungen.py`](docs/bauanleitung/zeichnungen.py), the four printed
parts from [`cad/modular.py`](cad/modular.py).

```bash
MS_CONFIG=erstflug python cad/modular.py       # printed parts, collision check, mass, renders
python docs/bauanleitung/zeichnungen.py        # drawings and 1:1 templates
python cad/mass_stand2b.py                     # mass budget, centre of gravity, inertia
```

## Mass budget

Three models in three days, each lighter than the last. The numbers are model values from
[`cad/mass_properties.md`](cad/mass_properties.md) and [`cad/mass_stand2b.md`](cad/mass_stand2b.md);
weighing follows the printing.

| Configuration | Lift-off | CG above nozzle | Lever arm gimbal–CG | Ixx = Iyy | Izz (roll) | E12: apogee in the simulation |
|---|---|---|---|---|---|---|
| `voll` (21 Oct): 1000 mm, legs, ring stack, piston | 981 g | 449 mm | 372 mm | 0.110 kg·m² | 0.00105 kg·m² | 20 m, thrust-to-weight 1.1 |
| `erstflug` (22 Oct): 700 mm, no legs, piston, key switch | 761 g | 318 mm | 242 mm | 0.046 kg·m² | 0.00057 kg·m² | – (750 g target missed by 11 g) |
| **State 2b (22 Oct evening): 496 mm in three modules, CO₂, no roll motor** | **723 g** | 256 mm | 186 mm | 0.021 kg·m² | 0.00047 kg·m² | **63 m**, thrust-to-weight 1.7 |

Where the 258 g against `voll` went: landing system (−200 g), tube 496 instead of 1000 mm (−121 g), no
threaded rods and end rings, no piston, no key switch; against that the sled with bulkhead as one large
printed part (74 g), the CO₂ module with cartridge and servo (44 g) and one more half coupler. The
estimate in `modular.py` (689 g) forgot the LoRa helix, the CO₂ servo, the switch-panel parts, the eye
bolt and the servo horns; the budget includes them (+34 g). By group: tubes and couplers 19 %, flight
computer with batteries 15 %, nose 14 %, printed parts 14 %, gimbal 12 %.

The lever arm of 186 mm is half that of `voll`; the firmware (`MOMENT_ARM_M`, `MASS_KG`) and the
simulation (`--vehicle stand2b`) use it. The roll inertia remains two orders of magnitude below the old
placeholder of 0.1 kg·m².

## What the simulation says

The Simulink model (rigid body with quaternions, TSP E12 thrust curve, servo transfer function
identified from step responses, sensor noise, static misalignment, ground) lives in
[`simulation/`](simulation/README.md) as the Python package `tvcsim`. It has two controllers, the
Simulink one and a line-by-line port of the firmware's `Control.cpp`, and four vehicle sets, among
them `cad` (981 g) and `stand2b` (723 g) from the mass models.

![Controller comparison](docs/img/sim/compare_gains_preload.png)

Four findings that changed the project:

- **The firmware gains are the right ones.** Kp 5, Ki 0, Kd 1 (on the firmware's −100 scale) keep
  the tilt small during the burn. The gains found earlier by the MATLAB grid search (kp 3.1, ki 5,
  kd 0.385) have a 40 times larger D term, drive the gimbal straight into its ±5° limit and
  oscillate at 3 to 4 Hz.
- **The 1 kg rocket was too heavy for an E12** (thrust-to-weight 1.1, apogee 20 m). Instead of a
  stronger motor the rocket got lighter: *Kartonaut 1* at 723 g reaches **63 m** in the model
  (100 runs: 63.4 ± 0.4 m), lands after a good 9 s, tilts at most 1.9° during the burn with the
  firmware gains and drifts 0.9 m sideways by burnout.
- **The servo-to-gimbal ratio decides the control authority.** With the 23 servo degrees per gimbal
  degree in `Config.h` the gimbal only reaches ±1°, with the measured 6 it reaches ±3.75°. To be
  measured on the built push-rod gimbal.
- **Without roll control the attitude has to be a quaternion.** Component-wise integration
  `rot_deg += ω·dt` puts a tilt error into the wrong servo axis as soon as the rocket rolls
  (finding 3 in `PROJECT.md`). That is the condition for dropping the roll motor.

<p>
<img src="docs/img/sim/montecarlo_preload.png" width="48%" alt="Monte Carlo trajectories">
<img src="docs/img/sim/servo_fit.png" width="48%" alt="Servo step response and fit">
</p>

```bash
cd simulation
python -m pytest tests                 # 25 tests
python scripts/run_nominal.py --controller firmware --vehicle stand2b --single-motor
python scripts/run_montecarlo.py --controller firmware --vehicle stand2b --single-motor
python scripts/compare_gains.py --vehicle stand2b --single-motor --accel specific_force
```

## Hardware: mainboard rev B

Today all sensors hang off the Teensy as breakout boards with jumper wires, which is the biggest
failure risk in flight. [hardware/mainboard/](hardware/mainboard/README.md) specifies **mainboard
rev B**: a 54 × 120 mm sled with the Teensy socket, the IMU exactly on the roll axis and all connectors
on the end faces. In the modular construction it sits on four posts of the printed sled in tube B; the
hatches for USB, SD and the switch panel are cut into the tube wall.

<img src="hardware/mainboard/kicad/img/render_top.png" width="100%" alt="Mainboard rev B, routed, rendered from above">

The KiCad project in [hardware/mainboard/kicad/](hardware/mainboard/kicad/README.md) is generated from
a single Python description of the circuit (`circuit.py`): seven schematic sheets, ERC without errors,
a board generator with outline, four layers, net classes, keep-outs and Freerouting, all 134 parts
placed and routed, DRC without errors, silkscreen with the mission patch, blue solder mask. The
[design guide](docs/DesignGuide_Mainboard_revB.md) ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) presents
the design with figures, the [datasheet](hardware/mainboard/datasheet/) in industry format covers limits,
pin map, function and bill of materials.

A [second-opinion review](hardware/mainboard/review_kicad_2026-10-21.md) found eight A points (buck-boost
output capacitance, 1S undervoltage threshold, main switch in the current path, fuse per battery, Kelvin
shunt, 2S currents on the inner layer). The Q&A round of 22 Oct settled them together with ten decisions
([Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md)):

- **Mechanical main switch, current through FETs.** The switch on the airframe only drives the gates of
  two P-FET load switches; the battery current stays on the board.
- **Charging inside the rocket.** 1S through an MCP73831 with USB-C on the board, 2S through a charge
  socket with balancer on the switch panel; both ahead of the load switch.
- **All flight sensors on SPI1.** BMP390 with its own chip select, INA239 instead of INA219; I²C only
  for the Qwiic expansion. A hung I²C slave can no longer block the control loop.
- **All servos and the roll motor directly on 2S**, no 5 V buck any more; the PWM duty cycle limits the
  motor voltage.
- **Future built in:** four pyro channels, a fourth servo connector, a second barometer as a footprint,
  stacking connector `J_STACK` for add-on boards with current reserve. Because the Teensy ran out of
  pins, a 74HC138 supplies the chip selects and a 74HC4051 the analog channels (40 → 31 pins used).
- **Two batteries**, **IMU without DMP** (ICM-42688-P), **LoRa instead of HC-12** (E22-400T22S, antenna
  as a 433 MHz helix at the lower end of the sled) remain from rev B.

The firmware is prepared for it: [`firmware/lib/mainboard_revb/`](firmware/README.md) holds the pin
map, decoder and mux, SPI drivers for ICM-42688-P, BMP390 and INA239 and the bring-up program
`revb_bringup`; `check_board_pins.py` compares the pins with `circuit.py`, also in CI. Rev A and the
reasoning behind the sled layout are kept in [`rev_a_2026-10-15.md`](hardware/mainboard/rev_a_2026-10-15.md).

## Ground station and launch stand

<img src="docs/img/cad/landingpad.png" width="300" align="right" alt="Launch stand with Kartonaut 1 (first-flight CAD)">

The **ground station** ([groundstation/](groundstation/README.md)) ignites the motor over a 15 m line,
receives the LoRa telemetry and shows both in the phone's browser through its own Wi-Fi access point.
The station decides, the phone displays: arming only works with the key and the ARM switch on the box,
the ignition path runs through a relay (hardware) and a MOSFET (firmware), the launch interlock checks
igniter continuity, telemetry younger than one second and the flight state `PAD_READY`; a heartbeat from
the phone aborts the countdown on connection loss. The ESP32-S3 firmware with state machine, WebSocket
and embedded web page is in `groundstation/firmware/` ([circuit](groundstation/Schaltung.md)). Budget
version from modules about €80, one evening of work.

The **launch stand** ([`cad/landingpad.py`](cad/README.md)) is a 600 × 600 mm plywood plate with a
Ø 130 hole for the jet, sheet steel around it, three individually adjustable M10 legs (up to 23° ground
slope) and three removable guides with 1.5 mm clearance to the tube; plus an ignition box with XT30
sockets for the firing line and a shunt plug. The script checks the stand against the rocket (gimbal ±7°,
lift-off, jet cone, tip-over margin in wind). 6.5 kg, about €86 of hardware-store parts. The landing
surface for the configuration with legs becomes a part of its own.

The interfaces between rocket, stand, station and phone (guides, firing line, radio protocol, WebSocket)
are in [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md).
Open: the telemetry protocol belongs to the flight firmware and will be adopted as a shared header; the
stand's guides have to match the screws and servo windows of the modular construction (0/90/180/270° and
207/336°, guides at 45/135/250°); transmit power and duty cycle in the 433 MHz band are to be settled.

## CAD model

The Blender files are inventoried in [`cad/blender_inventory.md`](cad/blender_inventory.md) and replaced
by a parametric model in CadQuery ([`cad/`](cad/README.md)): every dimension in `cad/params.py` with its
source, STEP and STL export per assembly, a collision check of the gimbal at ±7°, renders through Blender
headless, configurations `voll` (with legs) and `erstflug`. The same parameters feed the mass model. The
modular construction lives next to it in `cad/modular.py` with its own dimensions (`modular_params.py`),
because it starts from the gimbal as built; the printed gimbal from the Blender files of June 2025 is
included as a mesh in the full assembly `cad/export/modular/Kartonaut1_Stand2b.step`.

<p>
<img src="docs/img/cad/rocket_section.png" width="24%" alt="Section of configuration voll: motor, gimbal, flight computer in the coupler, piston, parachute, nose cone">
<img src="docs/img/cad/rocket_tvc.png" width="37%" alt="Gimbal with the two W5652H servos, deflected 5° and 4° (direct-drive draft)">
<img src="docs/img/cad/rocket_avionics.png" width="37%" alt="Flight computer module of configuration voll: coupler, rods, sled, batteries">
</p>

```bash
python -m pip install --user cadquery
python cad/build.py                      # configuration voll: STEP/STL to cad/export/, renders to docs/img/cad/
python cad/build.py --config erstflug    # first-flight CAD of 22 Oct (hatches, piston, 700 mm)
python cad/mass_model.py                 # mass_properties.md and .json (voll and erstflug)
python cad/landingpad.py                 # launch stand checked against the rocket
```

## Ground testing

Before anything flies, the attitude control gets tested on the ground with real thrust and without a
rocket motor: the rocket hangs in a rig that lets it pitch and yaw about its centre of gravity, and a
brushless motor (Racerstar BR2814, 1000 KV, 11-inch propeller, 4S LiPo) sits in the gimbal in place of
the rocket motor. At part throttle it delivers the 12 N of the E12, and the Teensy can even drive the
ESC along the E12 thrust curve. Motor, ESC, propellers, battery and chargers are bought, the rig is
designed in [`cad/testrig.py`](cad/README.md) and checked for collisions. Added to that: the CO₂ ejection
test (rocket horizontal, nose flies off, parachute fully clear, three times, also cold), radio range
with two E22 modules and the interlock test from the phone down to a lamp on the firing line.

<p>
<img src="docs/img/cad/testrig.png" width="40%" alt="Test rig: rocket in the two-axis frame">
<img src="docs/img/cad/testrig_drive.png" width="52%" alt="Drive end: propeller motor in the gimbal with guard cage">
</p>

## Firmware

PlatformIO project for the Teensy 4.1 in [`firmware/`](firmware/README.md). The main loop runs at a
fixed 100 Hz:

1. **Read the sensors.** IMU (angular rate, acceleration), barometer, power monitor.
2. **Integrate attitude.** Gyro only: in flight, magnetometer and accelerometer aiding are useless.
3. **Estimate altitude.** A two-state Kalman filter fuses barometer and vertical acceleration.
4. **Control.** PID on pitch and yaw outputs a torque that is converted via `M = l · m · |a| · sin δ`
   into a gimbal angle and then into servo degrees; the roll controller stays off for *Kartonaut 1*.
5. **Log.** One 88-byte frame per pass into a page buffer; SD writes only in the spare time before the
   next deadline. On the ground the binary log is exported as CSV.

```bash
cd firmware
pio run                      # build the flight firmware
pio run -t upload            # flash the Teensy 4.1
pio device monitor           # serial console, 115200 baud, Teleplot-compatible
pio run -e revb_bringup      # bring-up program for mainboard rev B
python tools/check_board_pins.py   # firmware pins against circuit.py
```

All pins, gains, filter constants and debug switches live in
[`firmware/src/Config.h`](firmware/src/Config.h). The controllers are switched off there until the
first flight test. Open before the first flight: quaternion attitude with up-vector, gyro calibration on
the pad, flight state machine (`SAFE → PAD_READY → BOOST → COAST → APOGEE → DESCENT → LANDED`), CO₂
release from the state machine, telemetry protocol, watchdog with state memory, sensors behind an
interface for breakouts and rev B.

## Repository layout

```
firmware/               flight firmware (PlatformIO, Teensy 4.1)              -> firmware/README.md
  src/                  modules: Sensors, KalmanZ, Control, SDLogger, Timing, Indicators
  lib/mainboard_revb/   pins, CS decoder, mux, SPI drivers ICM-42688-P / BMP390 / INA239
  examples/             test sketches (radio beacon, I2C scan, pyro MOSFET, revb_bringup)
  tools/                check_board_pins.py
groundstation/          ground station: concept, circuit, ESP32-S3 firmware   -> groundstation/README.md
simulation/             6DOF simulation in Python, package tvcsim             -> simulation/README.md
hardware/mainboard/     mainboard rev B: specification, decisions, KiCad from code, datasheet, reviews, order plan
cad/                    parametric CAD, modular construction, launch stand, test rig, mass models -> cad/README.md
docs/                   build manual (+ drawings, templates, PDF), design guide, build log, plans, budget, images
.github/workflows/      CI: PlatformIO environments, simulation tests, pin check
PROJECT.md              project file: key data, work packages, findings, changelog
```

The old ground station (Arduino Nano with HC-12) is its own repository,
[kartonaut-ground](https://github.com/Jan-Philipp-Munsch/kartonaut-ground); its successor is
`groundstation/`. The MATLAB/Simulink original of the simulation and the Blender files stay outside this
repository; their content is ported here.

## Documentation

| Document | What it holds |
|---|---|
| [PROJECT.md](PROJECT.md) | key data, work packages with status, findings from the reviews, next steps, changelog |
| [docs/Bauanleitung_Kartonaut1.md](docs/Bauanleitung_Kartonaut1.md) | build manual state 2b: decisions, modules, stack, parts list with order and print status, build steps, maintenance, cable plan, drawings ([PDF](docs/bauanleitung/Bauanleitung_Kartonaut1.pdf), [drawings](docs/bauanleitung/Zeichnungen_Kartonaut1.pdf), [1:1 templates](docs/bauanleitung/Bohrschablonen_1zu1.pdf)) |
| [cad/mass_stand2b.md](cad/mass_stand2b.md) | mass budget *Kartonaut 1* state 2b: mass, CG, lever arm, inertia, parts list, comparison with the predecessors |
| [cad/mass_properties.md](cad/mass_properties.md) | mass model of the configurations `voll` and `erstflug` |
| [docs/BUILD.md](docs/BUILD.md) | as-built: inventory of bought and printed parts, mechanics, wiring, software on the device, tests, build log |
| [docs/Plan_2026-10-22.md](docs/Plan_2026-10-22.md) | plan to the first flight: work streams board, firmware, mechanics, ground systems, milestones M1–M7 |
| [docs/Budget_2026-10-22.md](docs/Budget_2026-10-22.md) | budget plan to the first flight: open costs by block, inventory, schedule, savings, uncertainties |
| [docs/Schnittstellen_Bodensystem_2026-10-22.md](docs/Schnittstellen_Bodensystem_2026-10-22.md) | interfaces S1–S4: rocket/pad, firing line, radio, phone |
| [docs/Plan_2026-10-21.md](docs/Plan_2026-10-21.md) | planning round of 21 Oct: board review, power architecture, layout checklist, port plan |
| [docs/Rohrmaterial_2026-10-22.md](docs/Rohrmaterial_2026-10-22.md) | research on composite tubes versus cardboard: cardboard stays |
| [hardware/mainboard/README.md](hardware/mainboard/README.md) | mainboard rev B specification |
| [hardware/mainboard/Komponenten_2026-10-22.md](hardware/mainboard/Komponenten_2026-10-22.md) | decisions E1–E10, parts by rail and interface, pin map, stacking connector, pin budget |
| [docs/DesignGuide_Mainboard_revB.md](docs/DesignGuide_Mainboard_revB.md) | the rev B design presented with figures ([PDF](docs/DesignGuide_Mainboard_revB.pdf)) |
| [hardware/mainboard/datasheet/](hardware/mainboard/datasheet/) | datasheet MS-MB-B rev B (LaTeX, BOM from `circuit.py`) |
| [hardware/mainboard/ORDER.md](hardware/mainboard/ORDER.md) | order plan: parts to buy now, gates, JLCPCB parameters, costs, order list by shop |
| [hardware/mainboard/review_kicad_2026-10-21.md](hardware/mainboard/review_kicad_2026-10-21.md) | second-opinion review of the KiCad project |
| [hardware/mainboard/Fertiger_2026-10-21.md](hardware/mainboard/Fertiger_2026-10-21.md) | manufacturer comparison and decision |
| [groundstation/README.md](groundstation/README.md) | ground station: concept, safety, launch-site procedure, firmware, BOM ([circuit](groundstation/Schaltung.md)) |
| [simulation/README.md](simulation/README.md) | model, coordinates, assumptions, vehicle sets, results |
| [firmware/README.md](firmware/README.md) | firmware modules, log format, test sketches, rev B library |
| [cad/README.md](cad/README.md) | parametric model, configurations, modular construction, test rig, launch stand |
| [cad/blender_inventory.md](cad/blender_inventory.md) | what the 16 Blender files contain, which is current, which is superseded |

## License

[MIT](LICENSE). The BPS.space Scout F files that served as reference are not part of this repository.
