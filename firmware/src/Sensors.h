#pragma once
#include "Config.h"
#include "MathTypes.h"
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include "ICM_20948.h"
#include <INA219_WE.h>

// --- Datentypen ---
struct BaroData { float alt_m = 0.0f; };

struct ImuData {
  Quaternion q;      // Orientierung (body->nav)
  Vec3 a_body;       // Accel (m/s^2, Body-Frame, bias-korrigiert)
  Vec3 a_nav;        // Accel im Nav-Frame (Gravity subtrahiert)
  Vec3 omega_dps;    // Gyro (°/s) (bereits leicht geglättet)

  // Frische-Flags (true = Wert stammt aus diesem Loop aus FIFO)
  bool hasQuat  = false;
  bool hasAccel = false;
  bool hasGyro  = false;

  // Zeitstempel (us) des zuletzt verarbeiteten FIFO-Frames
  uint32_t stamp_us = 0;
};

struct PowerData {
  float shunt_mV = 0, bus_V = 0, load_V = 0, current_mA = 0, power_mW = 0;
  bool  overflow = false;
};

// --- API ---
void Sensors_setup();
void BMP_calibrate_ground();
bool Read_Baro(BaroData& out);

// Liest die FIFO bis leer (oder cap) und liefert den *letzten* kompletten Satz.
// Entschärft Interleave/„0-Frames“ und glättet Gyro minimal.
bool Read_IMU(ImuData& out, float& a_norm_filt);

bool Read_Power(PowerData& out);

// Stationäre Accelerometer-Kalibrierung (Body-Frame, Rakete ruhig ablegen)
void Accel_calibrate_body(int samples = 200, uint16_t sample_delay_ms = 5);

// --- Exporte ---
extern float gndps_hPa;                 // Bodendruck für Höhenberechnung
extern Vec3  g_acc_bias_body_ms2;       // Accel-Bias im Body-Frame (m/s^2)
