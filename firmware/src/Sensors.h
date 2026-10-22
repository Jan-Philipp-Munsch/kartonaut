#pragma once
// Sensors.h – gemeinsame Schnittstelle der beiden Sensor-Rückenden
//
//   SensorsBreakout.cpp   ICM-20948 (DMP-FIFO, rohe Accel/Gyro), BMP280, INA219
//   SensorsRevB.cpp       ICM-42688-P, BMP390, INA239 an SPI1, Akkus/ARM/Pyro an der Mux
//
// Beide liefern dasselbe: spezifische Kraft und Drehrate im Körpersystem
// (x, y quer, z Rollachse), bias-korrigiert, dazu Barometerhöhe über dem
// Bodendruck und die Versorgungswerte. Die Lage (Quaternion) rechnet main.cpp
// mit Attitude aus lib/flightcore; die DMP-Quaternion des ICM-20948 wird nicht
// mehr benutzt (Befund 3).
#include "Config.h"
#include "Board.h"
#include "MathTypes.h"

struct ImuData {
  Vec3  a_body;          // spezifische Kraft [m/s²], Körpersystem, bias-korrigiert
  Vec3  omega_dps;       // Drehrate [°/s], Körpersystem, bias-korrigiert
  float temp_c = 0;
  bool  fresh = false;   // mindestens ein neuer Messwert in diesem Loop
  uint8_t samples = 0;   // wie viele Messwerte gemittelt wurden
  uint32_t stamp_us = 0; // micros() des letzten Lesens
};

struct BaroData {
  float alt_m = 0;         // über dem Bodendruck
  float pressure_pa = 0;
  float temp_c = 0;
  bool  fresh = false;
};

struct PowerData {
  float vbat1_V = 0;       // 1S Elektronik (nur rev B)
  float vbat2_V = 0;       // 2S Servos/Pyro (rev B: Teiler; Breakout: INA219-Bus)
  float arm_V = 0;         // VBAT_ARMED hinter dem Schlüsselschalter (nur rev B)
  float bus_V = 0;         // INA: Bus-Spannung
  float current_A = 0;     // INA: Strom 2S-Pfad
  float pyro_V[4] = {0, 0, 0, 0};
  bool  armed = false;
  bool  continuity[4] = {false, false, false, false};
  bool  fresh = false;
};

struct SensorStatus {
  bool imu = false, baro = false, power = false;
  const char* backend = "";
};

// Hardware starten; true, wenn IMU und Barometer da sind
bool Sensors_setup();
const SensorStatus& Sensors_status();

bool Read_IMU(ImuData& out);     // jeden Loop; ohne neue Daten bleiben die letzten Werte, fresh = false
bool Read_Baro(BaroData& out);   // jeden Loop; fresh, wenn eine neue Messung vorlag
bool Read_Power(PowerData& out); // langsam (20 Hz reicht)

// Gyro-Bias auf der Rampe: samples Messwerte mitteln (blockiert samples/ODR, ca. 1–2 s).
// false, wenn die Rakete nicht ruhig war (Standardabweichung über max_std_dps).
bool Sensors_calibrateGyro(uint16_t samples, float max_std_dps, Vec3& bias_dps, Vec3& std_dps);
void Sensors_setGyroBias(const Vec3& bias_dps);
Vec3 Sensors_gyroBias();

// Bodendruck neu mitteln (blockiert ca. 0,5 s bei 50 Hz)
void  Sensors_calibrateBaroGround(uint16_t samples);
void  Sensors_setGroundPressure(float p0_pa);
float Sensors_groundPressure();

// Rohwerte ohne Bias-Korrektur (Kalibrier-Sketches)
bool Read_IMU_raw(Vec3& a_body_ms2, Vec3& omega_dps);
