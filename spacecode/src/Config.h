#pragma once
#include <Arduino.h>

// ===== Loop timing =====
constexpr float LOOP_HZ            = 100.0f;
constexpr uint32_t LOOP_PERIOD_US  = uint32_t(1e6f / LOOP_HZ);

// ===== Physical parameters =====
constexpr float G_MS2        = 9.81f;
constexpr float MASS_KG      = 0.70f;
constexpr float MOMENT_ARM_M = 0.30f;

// ===== IMU scaling (ICM-20948 DMP raw ranges assumed) =====
constexpr float ACC_LSB_PER_G    = 8192.0f;    // ±4 g
constexpr float GYRO_LSB_PER_DPS = 16.384f;    // ±2000 dps

// ===== I2C speeds =====
constexpr uint32_t I2C_MAIN_SPEED_HZ = 400000; // safe for BMP280 & INA219
//#define USE_WIRE1_FOR_IMU                      // optional: IMU auf separatem Bus
constexpr uint32_t I2C_IMU_SPEED_HZ  = 1000000; // nur wenn separater Bus genutzt

// ===== Pins =====
constexpr int PIN_BEEPER = 13;
// LEDs
constexpr int PIN_LED1   = 5;
constexpr int PIN_LED2   = 6;
// Roll motor (H-bridge)
constexpr int PIN_MOT_IN1 = 2;
constexpr int PIN_MOT_IN2 = 3;
// Servos
constexpr int PIN_SERVO_YAW   = 28;
constexpr int PIN_SERVO_PITCH = 29;
constexpr int PIN_SERVO_CHUTE = 9;

// Servos steuern wir in Grad (0..180) via PWMServo.write()
constexpr int SERVO_DEG_CENTER = 90;  // Mittelstellung

// Schutz gegen Divisionen durch geringe Beschleunigung
constexpr float A_NORM_MIN   = 1.0f;
// Low-Pass für |a|
constexpr float A_NORM_ALPHA = 0.1f;

// ===== Kalman tuning (Standardwerte) =====
constexpr float KALMAN_MEAS_STD_M     = 30.0f;    // std(R) für Baro [m]
constexpr float KALMAN_SIGMA_ACC_MS2  = 10.0f;    // std Prozessrauschen (acc input) [m/s^2]

// Initialzustand/Unsicherheit
constexpr float KALMAN_INIT_Z_M       = 0.0f;
constexpr float KALMAN_INIT_VZ_MS     = 0.0f;
constexpr float KALMAN_INIT_PZ_VAR    = 10000.0f;
constexpr float KALMAN_INIT_PV_VAR    = 10000.0f;

// Einpendeln / Nullpunkt nach Settle
constexpr bool  KALMAN_ZERO_AFTER_SETTLE = true;
constexpr float KALMAN_SETTLE_TIME_S     = 20.0f;

// HC-12
constexpr long HC12_BAUD = 9600;

// Debug
constexpr bool VERBOSE = false;

// Teleplot

constexpr bool PLOT_KALMAN = false;
constexpr bool PLOT_ROLL = false;
constexpr bool PLOT_ELECTRICS = false;

// LOGGING

constexpr bool LOOP_WARNING = true;
constexpr bool LOG_DATA = false;