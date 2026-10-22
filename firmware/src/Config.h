#pragma once
#include <Arduino.h>

// =====================================================================
//  Config.h – alle Zahlen, Pins und Schalter der Flug-Firmware
//
//  Die Module (Sensors, Control, KalmanZ, SDLogger, Timing, Indicators)
//  lesen ihre Parameter ausschließlich von hier. Wer die Rakete umbaut,
//  ändert diese Datei, nicht die Module.
// =====================================================================

// ===== Loop-Takt =====
constexpr float    LOOP_HZ        = 100.0f;
constexpr uint32_t LOOP_PERIOD_US = uint32_t(1e6f / LOOP_HZ);

// ===== Physik =====
constexpr float G_MS2        = 9.81f;
// TODO vor dem ersten geregelten Flug abgleichen: Gewicht.csv plant 0,902 kg,
// die 6DOF-Simulation rechnet mit 0,94 kg. Die Masse geht direkt in den
// TVC-Winkel ein (asin(M / (l·m·|a|))), siehe PROJECT.md §5.
constexpr float MASS_KG      = 0.70f;
constexpr float MOMENT_ARM_M = 0.30f;   // Abstand Gimbal–Schwerpunkt

// ===== IMU (ICM-20948, DMP-Rohwerte) =====
constexpr float ACC_LSB_PER_G    = 8192.0f;   // ±4 g. Reicht für die E12 (3,2 g), nicht für die F35 (6,2 g).
constexpr float GYRO_LSB_PER_DPS = 16.384f;   // ±2000 °/s
// Statische Gyro-Offsets in LSB, am Tisch bestimmt (Okt. 2025).
// TODO: durch eine Kalibrierung auf der Rampe ersetzen, wie Accel_calibrate_body().
constexpr float GYRO_BIAS_LSB_X  = +12.1f;
constexpr float GYRO_BIAS_LSB_Y  = -7.96f;
constexpr float GYRO_BIAS_LSB_Z  = +2.44f;
constexpr bool  GYRO_FILT        = false;     // IIR-Glättung der Drehrate ein/aus
constexpr float GYRO_FILT_ALPHA  = 0.25f;     // 0..1, höher = weniger Glättung
constexpr int   IMU_FIFO_READ_CAP = 24;       // max. Frames pro Loop aus der FIFO

// ===== I2C =====
constexpr uint32_t I2C_MAIN_SPEED_HZ = 400000;  // BMP280 und INA219
//#define USE_WIRE1_FOR_IMU                      // optional: IMU auf eigenem Bus
constexpr uint32_t I2C_IMU_SPEED_HZ  = 1000000; // nur mit USE_WIRE1_FOR_IMU

// ===== Pins (Teensy 4.1) =====
constexpr int PIN_BEEPER      = 13;
constexpr int PIN_LED1        = 5;    // WS2812B
constexpr int PIN_LED2        = 6;    // WS2812B
constexpr int PIN_MOT_IN1     = 2;    // Rollmotor, H-Brücke
constexpr int PIN_MOT_IN2     = 3;
constexpr int PIN_SERVO_YAW   = 28;   // TVC
constexpr int PIN_SERVO_PITCH = 29;   // TVC
constexpr int PIN_SERVO_CHUTE = 9;    // Fallschirm
constexpr int PIN_PYRO1       = 23;   // Low-Side-MOSFET, Mainboard rev A: PYRO1_FIRE
// HC-12 hängt an Serial8 (RX8 = 34, TX8 = 35)

// ===== Servos =====
constexpr int   SERVO_DEG_CENTER   = 90;     // Mittelstellung
constexpr int   SERVO_PULSE_MIN_US = 760;    // SG90, gemessen
constexpr int   SERVO_PULSE_MAX_US = 2300;
// Linearisierte Umsetzung TVC-Winkel -> Servowinkel (aus der Gimbal-Geometrie):
//   servo_deg = tvc_deg * GAIN + OFFSET
constexpr float SERVO_YAW_GAIN     = -23.0f;
constexpr float SERVO_YAW_OFFSET   =  92.5f;
constexpr float SERVO_PITCH_GAIN   =  23.0f;
constexpr float SERVO_PITCH_OFFSET =  82.5f;
// Mechanische Fenster des Kardans (Servo-Grad)
constexpr float SERVO_YAW_MIN_DEG   =  70.0f;
constexpr float SERVO_YAW_MAX_DEG   = 115.0f;
constexpr float SERVO_PITCH_MIN_DEG =  60.0f;
constexpr float SERVO_PITCH_MAX_DEG = 105.0f;

// ===== Regler Pitch/Yaw (TVC) =====
// Arbeitet auf dem integrierten Gyro-Winkel in Grad, skaliert mit 1/100.
// TODO: mit pid_tuner.m (Kp = 3,1, Ki = 5, Kd = 0,385) abgleichen, Einheiten prüfen.
constexpr float PY_KP = 5.0f;
constexpr float PY_KI = 0.0f;
constexpr float PY_KD = 1.0f;
constexpr float PY_ERROR_SCALE = -100.0f;   // Grad -> Reglereingang
constexpr float A_NORM_MIN   = 1.0f;        // Schutz gegen Division bei kleiner Beschleunigung [m/s²]
constexpr float A_NORM_ALPHA = 0.1f;        // Tiefpass für |a|

// ===== Regler Roll (Schwungrad / Rollmotor) =====
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
constexpr float KALMAN_INIT_Z_M      = 0.0f;
constexpr float KALMAN_INIT_VZ_MS    = 0.0f;
constexpr float KALMAN_INIT_PZ_VAR   = 10000.0f;
constexpr float KALMAN_INIT_PV_VAR   = 10000.0f;
constexpr bool  KALMAN_ZERO_AFTER_SETTLE = true;   // Höhe nach dem Einpendeln auf 0 setzen
constexpr float KALMAN_SETTLE_TIME_S     = 20.0f;

// ===== Funk =====
constexpr long HC12_BAUD = 9600;

// ===== Logging =====
constexpr bool     LOG_DATA = false;
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

// ===== Signalgeber =====
constexpr bool SILENT = false;   // Summer aus
constexpr bool DARK   = false;   // LEDs aus
