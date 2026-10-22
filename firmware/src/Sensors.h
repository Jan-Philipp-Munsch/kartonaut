#pragma once
// Sensors.h – Schnittstelle zu den Flugsensoren (Plan 22.10.2026, B7)
//
// Zwei Rückenden, ausgewählt über die PlatformIO-Umgebung:
//   Sensors_breakout.cpp  Breakout-Aufbau: ICM-20948 roh (ohne DMP), BMP280, INA219 an I2C.
//                         Kein ARM, kein Durchgang: armed = false, Pyro damit gesperrt.
//   Sensors_revb.cpp      Mainboard rev B: ICM-42688-P, BMP390, INA239 an SPI1, ARM, Pyro-
//                         Durchgang und beide Akkuspannungen über die Mux (lib/mainboard_revb/).
// Beide liefern je Takt dieselbe Struktur: spezifische Kraft und Drehrate im Körpersystem
// (x, y quer, z Rollachse; Chip->Körper über IMU_AXIS_MAP/SIGN in Config.h), Druck und
// Barometerhöhe, Versorgung, Zündkreis. Die Lage rechnet Attitude.h aus der Drehrate.
#include "Config.h"
#include "MathTypes.h"

struct SensorSample {
  Vec3  a_body;             // spezifische Kraft [m/s²], Körpersystem, nullpunktkorrigiert
  Vec3  omega_dps;          // Drehrate [°/s], Körpersystem, nullpunktkorrigiert
  float a_norm = G_MS2;     // |a_body|
  bool  imu_fresh = false;  // neuer IMU-Satz in diesem Takt
  float p_pa = 0;           // Druck
  float baro_alt_m = 0;     // Höhe über dem Bodendruck
  bool  baro_fresh = false;
  float temp_c = 0;
  float vbat1_V = 0;        // 1S (rev B), sonst 0
  float vbat2_V = 0;        // 2S (rev B: Mux; Breakout: INA219-Bus)
  float current_A = 0;      // 2S-Pfad
  float arm_V = 0;          // hinter dem Schlüsselschalter (rev B)
  bool  armed = false;
  bool  continuity[2] = {false, false};
  bool  pyro_fitted[2] = {true, false};
};

struct SensorStatus {
  bool imu_ok = false, baro_ok = false, power_ok = false;
  bool ok() const { return imu_ok && baro_ok; }
};

void Sensors_setup();
const SensorStatus& Sensors_status();

// Einen Takt lesen (nicht blockierend; ohne neue Daten bleiben die letzten Werte)
void Sensors_read(SensorSample& out);

// Nullpunkte auf dem Pad: Gyro-Bias (Mittel über GYRO_CAL_SAMPLES Takte, Abbruch bei Bewegung)
// und Bodendruck. Nicht blockierend: jeden Takt aufrufen, bis true zurückkommt.
void Sensors_calibrateStart();
bool Sensors_calibrateStep(const SensorSample& s);   // true = fertig
bool Sensors_calibrated();
void Sensors_getBias(Vec3& gyro_bias_dps, float& ground_p_pa);
void Sensors_setBias(const Vec3& gyro_bias_dps, float ground_p_pa);   // aus dem Zustandsspeicher
