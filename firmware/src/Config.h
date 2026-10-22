#pragma once
#include <stdint.h>

// =====================================================================
//  Config.h – alle Zahlen, Pins und Schalter der Flug-Firmware
//
//  Die Module lesen ihre Parameter ausschließlich von hier. Wer die
//  Rakete umbaut, ändert diese Datei, nicht die Module.
//
//  Zwei Boards: der Breakout-Aufbau (Umgebung teensy41) und das Mainboard
//  rev B (Umgebung teensy41_revb, Build-Flag BOARD_REVB). Die Pins des
//  Mainboards kommen aus lib/mainboard_revb/BoardRevB.h.
// =====================================================================

// ===== Loop-Takt =====
constexpr float    LOOP_HZ        = 100.0f;
constexpr uint32_t LOOP_PERIOD_US = uint32_t(1e6f / LOOP_HZ);

// ===== Physik (Erstflug-Konfiguration, cad/mass_properties.md, 22.10.2026) =====
constexpr float G_MS2        = 9.81f;
constexpr float MASS_KG      = 0.761f;  // Start, voller E12, Rohr 700 mm, ohne Beine; nach dem Wiegen eintragen
constexpr float MOMENT_ARM_M = 0.242f;  // Kardanpunkt–Schwerpunkt (voll: 0,372 m)

// ===== IMU =====
// Breakout: ICM-20948 roh (ohne DMP), ±4 g und ±2000 °/s. Rev B: ICM-42688-P an SPI1.
constexpr float ACC_RANGE_G      = 4.0f;    // E12: 3,2 g bei 0,9 kg; F35 bräuchte ±8 g
constexpr bool  GYRO_FILT        = false;   // IIR-Glättung der Drehrate ein/aus
constexpr float GYRO_FILT_ALPHA  = 0.25f;   // 0..1, höher = weniger Glättung
constexpr int   GYRO_CAL_SAMPLES = 400;     // Gyro-Nullpunkt auf dem Pad (bei 100 Hz: 4 s)
constexpr float GYRO_CAL_MAX_DPS = 2.0f;    // größer: Rakete wackelt, Kalibrierung ungültig
// Drehung Chip -> Körpersystem (x, y quer, z Rollachse): Vorzeichen und Achsenreihenfolge.
// Breakout: Chip-Achsen = Körperachsen (bisheriger Einbau). Rev B: wird mit der Platzierung
// eingetragen (Plan 22.10., A2).
#ifdef BOARD_REVB
constexpr int   IMU_AXIS_MAP[3]  = {0, 1, 2};     // Körper x,y,z = Chip-Achse Index
constexpr float IMU_AXIS_SIGN[3] = {1.f, 1.f, 1.f};
#else
constexpr int   IMU_AXIS_MAP[3]  = {0, 1, 2};
constexpr float IMU_AXIS_SIGN[3] = {1.f, 1.f, 1.f};
#endif

// ===== I2C (nur Breakout) =====
constexpr uint32_t I2C_MAIN_SPEED_HZ = 400000;

// ===== Pins (Teensy 4.1) =====
#ifdef BOARD_REVB
// Mainboard rev B: Pins aus BoardRevB.h; hier nur die Aliase, die die Module benutzen.
constexpr int PIN_BEEPER      = 37;
constexpr int PIN_LED_DATA    = 5;    // WS2812B-Kette LED1 -> LED2
constexpr int PIN_MOT_IN1     = 2;    // DRV8833
constexpr int PIN_MOT_IN2     = 3;
constexpr int PIN_MOT_NSLEEP  = 11;
constexpr int PIN_SERVO_YAW   = 28;
constexpr int PIN_SERVO_PITCH = 29;
constexpr int PIN_SERVO_CHUTE = 9;
constexpr int PIN_PYRO1       = 23;
constexpr int PIN_PYRO2       = 22;
constexpr int PIN_RADIO_M0    = 33;   // E22: M0 = M1 = 0 -> transparenter Modus
constexpr int PIN_RADIO_M1    = 32;
#else
constexpr int PIN_BEEPER      = 13;
constexpr int PIN_LED1        = 5;    // WS2812B
constexpr int PIN_LED2        = 6;    // WS2812B
constexpr int PIN_MOT_IN1     = 2;    // Rollmotor, H-Brücke
constexpr int PIN_MOT_IN2     = 3;
constexpr int PIN_SERVO_YAW   = 28;   // TVC
constexpr int PIN_SERVO_PITCH = 29;   // TVC
constexpr int PIN_SERVO_CHUTE = 9;    // Fallschirm
constexpr int PIN_PYRO1       = 23;   // Low-Side-MOSFET, Mainboard rev A: PYRO1_FIRE
constexpr int PIN_PYRO2       = -1;   // nicht vorhanden
#endif
// Funk hängt an Serial8 (RX8 = 34, TX8 = 35): HC-12 heute, E22 auf rev B

// ===== Servos =====
constexpr float SERVO_DEG_CENTER   = 90.0f;
constexpr int   SERVO_PULSE_MIN_US = 760;    // SG90, gemessen. W5652H: nach E01 eintragen.
constexpr int   SERVO_PULSE_MAX_US = 2300;
// Pulsrate der TVC-Servos. SG90 (analog): 50 Hz. FrSky W5652H (digital): bis 333 Hz,
// Ziel 250 Hz (Jan, 22.10.2026); vorher mit E01 bei 50 und 250 Hz vermessen.
#ifdef BOARD_REVB
constexpr uint32_t SERVO_FRAME_HZ  = 250;
#else
constexpr uint32_t SERVO_FRAME_HZ  = 50;
#endif
// Linearisierte Umsetzung TVC-Winkel -> Servowinkel (aus der Gimbal-Geometrie):
//   servo_deg = tvc_deg * GAIN + OFFSET
// TODO Befund 13: 23 (hier) gegen 6 (Identifikation 2025). Experiment E01 entscheidet,
// dann auch die W5652H-Werte und das Fenster des neuen Kardans eintragen.
constexpr float SERVO_YAW_GAIN     = -23.0f;
constexpr float SERVO_YAW_OFFSET   =  92.5f;
constexpr float SERVO_PITCH_GAIN   =  23.0f;
constexpr float SERVO_PITCH_OFFSET =  82.5f;
// Mechanische Fenster des Kardans (Servo-Grad)
constexpr float SERVO_YAW_MIN_DEG   =  70.0f;
constexpr float SERVO_YAW_MAX_DEG   = 115.0f;
constexpr float SERVO_PITCH_MIN_DEG =  60.0f;
constexpr float SERVO_PITCH_MAX_DEG = 105.0f;
constexpr float CHUTE_SERVO_CLOSED_DEG = 10.0f;   // Reserve, falls der Fallschirm doch per Servo kommt
constexpr float CHUTE_SERVO_OPEN_DEG   = 120.0f;

// ===== Regler Pitch/Yaw (TVC) =====
// Arbeitet auf den Kippwinkeln aus der Gyro-Quaternion (Grad), skaliert mit 1/100.
// Gewinne: in der Simulation bestätigt (Befund 11), Kd/100 entspricht dem Simulink-kd.
constexpr float PY_KP = 5.0f;
constexpr float PY_KI = 0.0f;
constexpr float PY_KD = 1.0f;
constexpr float PY_ERROR_SCALE = -100.0f;   // Grad -> Reglereingang
constexpr float PY_INT_LIMIT   = 500.0f;    // Anti-Windup des I-Anteils [Grad·s]
constexpr float A_NORM_MIN   = 1.0f;        // Schutz gegen Division bei kleiner Beschleunigung [m/s²]
constexpr float A_NORM_ALPHA = 0.1f;        // Tiefpass für |a|

// ===== Regler Roll (Schwungrad / Rollmotor) =====
// TODO Befund 15: Izz ist 0,0006 kg·m² (Erstflug), nicht 0,1; Gewinne vor dem Einsatz prüfen.
constexpr float ROLL_KP = 1.2f;
constexpr float ROLL_KI = 0.0f;
constexpr float ROLL_KD = 1.0f;
constexpr float ROLL_CMD_SCALE    = 200.0f;  // Reglerausgang -> [-1, +1]
constexpr float ROLL_CMD_DEADBAND = 0.02f;
constexpr int   ROLL_PWM_MIN      = 100;     // kleinste Duty, bei der der Motor anläuft (von 4095)
constexpr int   ROLL_PWM_MAX      = 4095;
constexpr uint32_t ROLL_PWM_FREQ_HZ = 20000;

// ===== Kalman (Höhe, Vertikalgeschwindigkeit) =====
constexpr float KALMAN_MEAS_STD_M    = 30.0f;   // Baro-Rauschen [m]
constexpr float KALMAN_SIGMA_ACC_MS2 = 10.0f;   // Prozessrauschen [m/s²]
constexpr float KALMAN_INIT_PZ_VAR   = 10000.0f;
constexpr float KALMAN_INIT_PV_VAR   = 10000.0f;

// ===== Flugzustandsautomat (FlightState.h) =====
constexpr float    FS_LAUNCH_ACCEL_MS2    = 2.0f * G_MS2;  // Start erkannt: |a| über dieser Schwelle ...
constexpr uint32_t FS_LAUNCH_HOLD_MS      = 50;            // ... für so lange
constexpr float    FS_BURNOUT_AXIAL_MS2   = 3.0f;          // Brennschluss: axiale spezifische Kraft darunter ...
constexpr uint32_t FS_BURNOUT_HOLD_MS     = 100;           // ... für so lange
constexpr uint32_t FS_BURN_MAX_MS         = 4500;          // Rückfall: E12 brennt 3,55 s
constexpr uint32_t FS_APOGEE_EARLIEST_MS  = 500;           // nach Brennschluss frühestens
constexpr float    FS_APOGEE_VZ_MS        = -0.5f;         // Kalman-vz darunter ...
constexpr float    FS_APOGEE_BARO_DROP_M  = 1.0f;          // ... und Barometer so weit unter dem Maximum ...
constexpr uint32_t FS_APOGEE_HOLD_MS      = 200;           // ... für so lange
constexpr uint32_t FS_APOGEE_FALLBACK_MS  = 6000;          // Rückfall nach Brennschluss (Simulation: Gipfel nach ~2,5 s)
constexpr uint32_t FS_DESCENT_AFTER_MS    = 1000;          // APOGEE -> DESCENT nach der Zündung
constexpr float    FS_LANDED_VZ_MS        = 0.5f;          // Landung: |vz| darunter ...
constexpr float    FS_LANDED_ALT_M        = 5.0f;          // ... und Höhe darunter ...
constexpr uint32_t FS_LANDED_HOLD_MS      = 2000;          // ... für so lange
constexpr uint32_t FS_FLIGHT_MAX_MS       = 120000;        // Rückfall: nach 2 min gilt gelandet

// ===== Pyro (Pyro.h) =====
constexpr uint32_t PYRO_PULSE_MS        = 80;      // 50..100 ms, Abbruch bei Durchgangsverlust
constexpr uint32_t PYRO_MIN_FLIGHT_MS   = 2000;    // zweite Bedingung: mindestens so lange seit dem Start
constexpr uint32_t PYRO_BACKUP_DELAY_MS = 1500;    // Kanal 2 zündet so viel später, falls bestückt
constexpr uint32_t PYRO_RETRY_DELAY_MS  = 500;     // zweiter Versuch, wenn der Durchgang nach dem Puls bleibt
constexpr uint8_t  PYRO_MAX_FIRES       = 2;       // Versuche je Kanal
constexpr float    PYRO_ARM_MIN_V       = 5.0f;    // ARM_SENSE darüber = scharf (2S hinter dem Schlüssel)
constexpr float    PYRO_CONT_MIN_RATIO  = 0.8f;    // Durchgang: PYRO_SENSE > Ratio · ARM

// ===== Telemetrie (Telemetry.h) =====
constexpr long     RADIO_BAUD        = 9600;
constexpr uint32_t TLM_PERIOD_MS     = 100;     // 10 Hz
constexpr uint32_t TLM_CMD_TIMEOUT_MS = 1000;   // Kommando-Rahmen älter als das wird verworfen

// ===== Watchdog und Zustandsspeicher =====
constexpr bool     WDT_ENABLED    = true;
constexpr uint32_t WDT_TIMEOUT_MS = 250;        // Loop 10 ms; SD-Flush bleibt mit dem Slack darunter
constexpr uint32_t STATE_SAVE_EVERY_N_LOOPS = 1;

// ===== Logging =====
constexpr bool     LOG_DATA = false;
constexpr uint32_t LOG_EVERY_N_LOOPS = 1;       // 1 = 100 Hz, 10 = 10 Hz
// Nach so vielen Frames stoppen und die CSV exportieren (Tischtest). 0 = nie.
constexpr uint32_t LOG_STOP_AFTER_FRAMES = 1000;
constexpr bool     LOOP_WARNING = true;         // Overrun auf Serial melden

// ===== Regler-Freigaben =====
constexpr bool ROLL_CONTROL_ACTIVE = false;
constexpr bool PY_CONTROL_ACTIVE   = false;

// ===== Debug (Teleplot über USB-Serial) =====
constexpr bool VERBOSE        = false;
constexpr bool PLOT_KALMAN    = false;
constexpr bool PLOT_ROLL      = false;
constexpr bool PLOT_PY        = false;
constexpr bool PLOT_ELECTRICS = false;
constexpr bool PLOT_STATE     = false;

// ===== Signalgeber =====
constexpr bool SILENT = false;   // Summer aus
constexpr bool DARK   = false;   // LEDs aus
