# Mission Space

*Deutsche Fassung: [README.de.md](README.de.md). The detailed documents
([PROJECT.md](PROJECT.md), [spacecode/README.md](spacecode/README.md),
[hardware/mainboard/README.md](hardware/mainboard/README.md)) are in German.*

A thrust-vector-controlled (TVC) model rocket with a home-built flight computer,
modelled on the "Scout F" by [BPS.space](https://bps.space). The motor sits in a
two-servo gimbal, a roll motor holds the roll axis, and a parachute brings the rocket
back. On board is a Teensy 4.1 with IMU, barometer, power monitor, SD logger and a
433 MHz radio link to the ground station.

<img src="docs/img/model_rocket.png" width="220" align="right" alt="Full model (Blender)">

| | |
|---|---|
| Airframe | Ø 75 mm, 1 m long, 3D-printed nose cone and landing legs |
| Motor | Estes E12 (24 mm) in the gimbal; E12 and F35 thrust curves in the simulation |
| Lift-off mass | about 0.9 kg planned |
| Flight computer | Teensy 4.1, ICM-20948 (DMP), BMP280, INA219, HC-12, microSD |
| Actuators | 2× SG90 (TVC), roll motor on an H-bridge, parachute servo |
| Control | PID on pitch/yaw with torque-to-gimbal-angle conversion, PID on roll |
| Status | Firmware and electronics bench-tested, mainboard rev A specified, no flight yet |

The state of every work package, the findings from the code review and the next steps
are tracked in [PROJECT.md](PROJECT.md) (German).

## Repository layout

```
spacecode/            flight firmware (PlatformIO, Teensy 4.1)     -> spacecode/README.md
  src/                modules: Sensors, KalmanZ, Control, SDLogger, Timing, Indicators
  examples/           stand-alone test sketches (radio, I2C scan, pyro MOSFET)
hardware/mainboard/   mainboard rev A specification, outline (DXF), placement plan
docs/                 Blender render script and images
PROJECT.md            project file: key data, progress, findings, changelog
```

The ground station (Arduino Nano with HC-12 receiver) lives in its own repository,
[groundcode](https://github.com/Jan-Philipp-Munsch/groundcode). The 6-DOF simulation
(MATLAB/Simulink, Monte Carlo and PID search) and the Blender CAD models are kept
outside this repository.

## Building and flashing the firmware

You need [PlatformIO](https://platformio.org) (CLI or the VS Code extension).

```bash
cd spacecode
pio run                      # build the flight firmware
pio run -t upload            # flash the Teensy 4.1
pio device monitor           # serial console, 115200 baud
pio run -e radio_beacon      # build one of the test sketches in examples/
```

All pins, controller gains, filter constants and debug switches live in
[`spacecode/src/Config.h`](spacecode/src/Config.h). The controllers are switched off
there until the first flight test.

## How the firmware works

The main loop runs at a fixed 100 Hz and does the following on every pass:

1. **Read the sensors.** The IMU's DMP delivers quaternion, acceleration and angular
   rate from its FIFO, the barometer the altitude, the INA219 voltage and current.
2. **Integrate attitude.** The gyro rate is summed into yaw, pitch and roll. In flight
   the magnetometer and accelerometer aiding are useless, so attitude is purely inertial.
3. **Estimate altitude.** A Kalman filter with the states altitude and vertical velocity
   fuses the barometer with vertical acceleration.
4. **Control.** A PID on pitch and yaw outputs a torque that is converted via
   `M = l · m · |a| · sin(δ)` into a gimbal angle and then into servo degrees. A second
   PID drives the roll motor through the H-bridge.
5. **Log.** One 88-byte frame per pass goes into a page buffer; physical writes and syncs
   to the SD card only happen in the spare time before the next deadline. On the ground
   the binary log is exported as CSV.

Module details, the log format and the test sketches are described in
[spacecode/README.md](spacecode/README.md) (German).

## Hardware

Today all sensors hang off the Teensy as breakout boards with Dupont wires, which is the
biggest failure risk in flight. [hardware/mainboard/](hardware/mainboard/README.md)
therefore specifies a mainboard rev A: a 54 × 120 mm sled with a Teensy socket, the IMU on
the roll axis, two buck converters, two pyro channels with arming, and all connectors on
the end faces. Schematic and layout in KiCad are the next step.

## Known open points

- Align mass and controller gains between firmware and simulation.
- Attitude as a quaternion from the gyro instead of component-wise integration (only
  valid for small angles without roll).
- Gyro calibration on the pad instead of fixed offsets.
- Flight state machine (pad, boost, coast, apogee, recovery) and pyro logic with arming.
- Telemetry protocol over the HC-12.

The full list with reasoning is in [PROJECT.md §5](PROJECT.md).

## License

[MIT](LICENSE). The BPS.space Scout F files that served as reference are not part of
this repository.
