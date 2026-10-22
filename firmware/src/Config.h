#pragma once
#include <Arduino.h>
#include "MathTypes.h"

// =====================================================================
//  Config.h – alle Zahlen und Schalter der Flug-Firmware
//
//  Die Module lesen ihre Parameter ausschließlich von hier; Pins stehen in
//  Board.h (je Rückende). Wer die Rakete umbaut, ändert diese Datei, nicht
//  die Module. Stand: Erstflug-Konfiguration *Kartonaut 1* (22.10.2026):
//  Rohr 700 mm, ohne Beine, TSP E12, Fallschirm über Pyro-Kolben.
// =====================================================================

// ===== Loop-Takt =====
constexpr float    LOOP_HZ        = 100.0f;
constexpr uint32_t LOOP_PERIOD_US = uint32_t(1e6f / LOOP_HZ);

// ===== Physik (cad/mass_properties.json, Variante erstflug_700, Start) =====
constexpr float G_MS2        = 9.81f;
constexpr float MASS_KG      = 0.761f;   // beim Start, voller Motor (Brennschluss 0,733)
constexpr float MOMENT_ARM_M = 0.242f;   // Kardan-Drehpunkt bis Schwerpunkt
constexpr float INERTIA_XX   = 0.046f;   // kg m², quer
constexpr float INERTIA_ZZ   = 0.00057f; // kg m², Rollachse
// TODO nach dem Zusammenbau: wiegen, Schwerpunkt auswiegen, Bifilarpendel
// (docs/Testplan_Firmware_2026-10-22.md §4), dann hier und in cad/ nachziehen.

// ===== IMU =====
// Statischer Gyro-Bias in °/s als Rückfall, wenn keine Rampenkalibrierung lief
// (Breakout-ICM-20948, Tisch Okt. 2025: +12,1 / −7,96 / +2,44 LSB bei 16,384 LSB/°/s).
// Die Firmware misst den Bias auf der Rampe neu (CALIBRATE), das hier ist nur der Start.
constexpr float GYRO_BIAS_DPS_X  = +0.74f;
constexpr float GYRO_BIAS_DPS_Y  = -0.49f;
constexpr float GYRO_BIAS_DPS_Z  = +0.15f;
// Accel-Bias und -Skalierung aus examples/calib_imu (Sechs-Lagen-Kalibrierung).
// Körpersystem, m/s². Solange nicht gemessen: 0 und 1.
constexpr Vec3  ACCEL_BIAS_MS2   = Vec3(0.0f, 0.0f, 0.0f);
constexpr Vec3  ACCEL_SCALE      = Vec3(1.0f, 1.0f, 1.0f);
constexpr uint16_t GYRO_CAL_SAMPLES = 200;     // Rampenkalibrierung: Dauer = Samples / LOOP_HZ
constexpr float    GYRO_CAL_MAX_STD_DPS = 1.0f; // sonst „nicht ruhig“, Kalibrierung verworfen
constexpr bool  GYRO_FILT        = false;      // IIR-Glättung der Drehrate ein/aus
constexpr float GYRO_FILT_ALPHA  = 0.25f;      // 0..1, höher = weniger Glättung
constexpr int   IMU_FIFO_READ_CAP = 24;        // Breakout: max. DMP-Frames pro Loop aus der FIFO
constexpr uint32_t IMU_STALE_MS  = 50;         // länger ohne neue IMU-Daten = Sensorausfall

// ===== Barometer =====
constexpr uint16_t BARO_CAL_SAMPLES = 100;     // Bodendruck: Mittel über so viele Messungen

// ===== Servos (TVC) =====
// FrSky Xact W5652H (bestellt 21.10.2026): Pulsbereich laut Datenblatt 900–2100 µs
// für 0..180°. TODO: am Servo messen (examples/calib_servo), SG90 war 760–2300.
constexpr int   SERVO_PULSE_MIN_US = 900;
constexpr int   SERVO_PULSE_MAX_US = 2100;
constexpr float SERVO_DEG_CENTER   = 90.0f;
// Linearisierte Umsetzung TVC-Winkel -> Servowinkel: servo_deg = tvc_deg * GAIN + OFFSET.
// Befund 13: Identifikation 2025 sagt 6 Servo-Grad je TVC-Grad, Config.h hatte 23.
// Mit dem neuen Kardan (cad/tvc.py, ±7°) und den W5652H neu messen (calib_servo, Modus 'm').
constexpr float SERVO_YAW_GAIN     = -6.0f;
constexpr float SERVO_YAW_OFFSET   =  90.0f;
constexpr float SERVO_PITCH_GAIN   =  6.0f;
constexpr float SERVO_PITCH_OFFSET =  90.0f;
// Mechanische Fenster des Kardans (Servo-Grad): ±7° TVC bei Gain 6 = ±42 Servo-Grad
constexpr float SERVO_YAW_MIN_DEG   =  48.0f;
constexpr float SERVO_YAW_MAX_DEG   = 132.0f;
constexpr float SERVO_PITCH_MIN_DEG =  48.0f;
constexpr float SERVO_PITCH_MAX_DEG = 132.0f;
constexpr float TVC_MAX_DEG         = 7.0f;    // Kardanbereich (cad/tvc.py)
constexpr int   CHUTE_SERVO_CLOSED_DEG = 90;   // Fallschirm-Servo (Reserve, Pin 9)
constexpr int   CHUTE_SERVO_OPEN_DEG   = 10;

// ===== Regler Pitch/Yaw (TVC) =====
// Fehler aus dem Oben-Vektor der Quaternion in Grad, skaliert mit 1/100.
// Befund 11: Kp 5, Ki 0, Kd 1 stabilisieren in der Simulation; ein kleines Ki
// (Simulink-ki ≈ 1 entspricht Ki = 1) nimmt den statischen Servofehler weg.
constexpr float PY_KP = 5.0f;
constexpr float PY_KI = 0.0f;
constexpr float PY_KD = 1.0f;
constexpr float PY_ERROR_SCALE = -100.0f;   // Grad -> Reglereingang
constexpr float PY_I_MAX_DEG_S = 500.0f;    // Anti-Windup
constexpr float A_NORM_MIN   = 1.0f;        // Schutz gegen Division bei kleiner Beschleunigung [m/s²]
constexpr float A_NORM_ALPHA = 0.1f;        // Tiefpass für |a|

// ===== Regler Roll (Schwungrad / Rollmotor) =====
// Achtung Befund 15: Izz ist 0,0006 kg m², hundertmal kleiner als der alte Platzhalter.
// Gewinne vor dem ersten Einsatz am Prüfstand neu einstellen.
constexpr float ROLL_KP = 1.2f;
constexpr float ROLL_KI = 0.0f;
constexpr float ROLL_KD = 1.0f;
constexpr float ROLL_CMD_SCALE    = 200.0f;  // Reglerausgang -> [-1, +1]
constexpr float ROLL_CMD_DEADBAND = 0.02f;
constexpr int   ROLL_PWM_MIN      = 100;     // kleinste Duty, bei der der Motor anläuft (von 4095)
#ifdef BOARD_REVB
constexpr int   ROLL_PWM_MAX      = 2450;    // E9: Motor direkt am 2S, 5 V / 8,4 V ≈ 60 % Tastverhältnis
#else
constexpr int   ROLL_PWM_MAX      = 4095;
#endif
constexpr uint32_t ROLL_PWM_FREQ_HZ = 20000;

// ===== Kalman (Höhe, Vertikalgeschwindigkeit) =====
constexpr float KALMAN_MEAS_STD_M    = 2.0f;    // Baro-Rauschen [m] (BMP390 ×8 IIR 3: ca. 0,3 m; Breakout BMP280 gröber)
constexpr float KALMAN_SIGMA_ACC_MS2 = 3.0f;    // Prozessrauschen [m/s²]
constexpr float KALMAN_INIT_PZ_VAR   = 100.0f;
constexpr float KALMAN_INIT_PV_VAR   = 100.0f;

// ===== Flugzustandsautomat (FlightState.h hält die Vorgaben, hier die Abweichungen) =====
constexpr float    FS_LIFTOFF_G       = 2.0f;     // E12: Spitze 28 N / 0,761 kg = 3,8 g
constexpr uint32_t FS_LIFTOFF_HOLD_MS = 50;
constexpr float    FS_BURNOUT_G       = 0.5f;
constexpr uint32_t FS_BURN_MAX_MS     = 4500;     // E12 brennt 3,55 s
constexpr uint32_t FS_COAST_MAX_MS    = 6000;     // Simulation: Gipfel 1,9 s nach Brennschluss
constexpr float    FS_ABORT_TILT_DEG  = 70.0f;
constexpr float    FS_PAD_MAX_TILT_DEG = 10.0f;

// ===== Pyro =====
constexpr int      PYRO_CHUTE_CHANNEL = 0;      // Kanal 1 = Kolben-Ausstoß
constexpr int      PYRO_BACKUP_CHANNEL = 1;     // Kanal 2 = zweiter Zünder im selben Kolben, 1 s später
constexpr uint32_t PYRO_BACKUP_DELAY_MS = 1000;
constexpr uint32_t PYRO_PULSE_MS      = 80;     // Review A4: 50–100 ms
constexpr float    ARM_MIN_V          = 5.0f;   // ARM_SENSE über diesem Wert = scharf (2S ≥ 6 V)
constexpr float    PYRO_CONT_FRACTION = 0.5f;   // Durchgang, wenn PYRO_SENSE > Anteil von ARM

// ===== Akkus =====
constexpr float VBAT1_MIN_V = 3.5f;   // 1S Elektronik, darunter Warnton und kein PAD_READY
constexpr float VBAT2_MIN_V = 6.6f;   // 2S Servos/Pyro
constexpr float INA_SHUNT_OHM_BREAKOUT = 0.1f;   // INA219-Breakout

// ===== Funk =====
constexpr long     RADIO_BAUD        = 9600;    // HC-12 und E22 (UART-Seite)
constexpr uint32_t TELEMETRY_HZ      = 10;
constexpr uint32_t STATUS_HZ         = 1;
constexpr uint8_t  E22_CHANNEL       = 0x17;    // 433,125 MHz (S3)
constexpr uint16_t E22_ADDRESS       = 0x0000;
constexpr uint8_t  E22_NETID         = 0x00;
constexpr uint8_t  E22_AIR_RATE      = 0x02;    // 2,4 kbit/s
constexpr uint8_t  E22_POWER         = 0x00;    // 22 dBm

// ===== Logging =====
constexpr bool     LOG_DATA = true;             // SD-Log ab PAD_READY (und mit 'L' am Tisch)
constexpr bool     LOG_FROM_BOOT = false;       // true: ab Einschalten loggen (Tischtest)
constexpr uint32_t LOG_STOP_AFTER_FRAMES = 0;   // Tischtest: nach N Frames stoppen und CSV exportieren, 0 = nie
constexpr uint32_t LOG_STOP_AFTER_LANDING_MS = 10000;
constexpr bool     LOOP_WARNING = true;         // Overrun auf Serial melden

// ===== Watchdog und Zustandsspeicher =====
constexpr bool     WATCHDOG_ENABLE   = true;
constexpr float    WATCHDOG_TIMEOUT_S = 1.0f;   // WDOG1 in 0,5-s-Stufen
constexpr uint32_t PERSIST_SAVE_HZ   = 10;

// ===== Regler-Freigaben =====
constexpr bool ROLL_CONTROL_ACTIVE = false;
constexpr bool PY_CONTROL_ACTIVE   = false;     // erst nach dem Prüfstand (Meilenstein M4) auf true

// ===== Prüfstand (cad/testrig.py): ESC statt Raketenmotor =====
constexpr bool  TESTRIG_MODE        = false;    // true: Gas-Ausgang, Start per Kommando, Brennschluss nach Zeit
constexpr float TESTRIG_THRUST_MAX_N = 15.0f;   // Schub bei Vollgas (BR2814, 12×6, 4S; nachmessen)
constexpr int   TESTRIG_ESC_MIN_US  = 1000;
constexpr int   TESTRIG_ESC_MAX_US  = 2000;

// ===== Debug (Teleplot über USB-Serial) =====
constexpr bool VERBOSE        = false;
constexpr bool PLOT_KALMAN    = false;
constexpr bool PLOT_ROLL      = false;
constexpr bool PLOT_PY        = false;
constexpr bool PLOT_ATTITUDE  = false;
constexpr bool PLOT_ELECTRICS = false;
constexpr bool PLOT_STATE     = true;           // Zustandsübergänge auf Serial

// ===== Signalgeber =====
constexpr bool SILENT = false;   // Summer aus
constexpr bool DARK   = false;   // LEDs aus
