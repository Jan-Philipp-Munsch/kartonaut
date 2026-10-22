#pragma once
// Sensors_common.h – gemeinsamer Teil beider Sensor-Rückenden: Achsenabbildung,
// Gyro-Nullpunkt und Bodendruck-Kalibrierung, Höhenformel.
#include "Sensors.h"
#include <math.h>

namespace sensors_common {

inline Vec3 mapAxes(const float chip[3]) {
  float v[3];
  for (int i = 0; i < 3; ++i) v[i] = IMU_AXIS_SIGN[i] * chip[IMU_AXIS_MAP[i]];
  return Vec3(v[0], v[1], v[2]);
}

inline float altitudeFromPressure(float p_pa, float p0_pa) {
  if (p0_pa <= 0 || p_pa <= 0) return 0;
  return 44330.0f * (1.0f - powf(p_pa / p0_pa, 0.1903f));
}

struct Calibration {
  Vec3  gyro_bias_dps;
  float ground_p_pa = 101325.0f;
  bool  done = false;
  // laufende Kalibrierung
  bool  running = false;
  int   n = 0;
  Vec3  gyro_sum;
  double p_sum = 0;
  int   p_n = 0;
  Vec3  gyro_first;

  void start() { running = true; done = false; n = 0; p_n = 0; gyro_sum = Vec3(); p_sum = 0; }

  // raw_omega: unkorrigierte Drehrate. true = fertig
  bool step(const Vec3& raw_omega, bool imu_fresh, float p_pa, bool baro_fresh) {
    if (!running) return done;
    if (imu_fresh) {
      if (n == 0) gyro_first = raw_omega;
      // Bewegung während der Kalibrierung: von vorn
      const Vec3 d = raw_omega - gyro_first;
      if (fabsf(d.x) > GYRO_CAL_MAX_DPS || fabsf(d.y) > GYRO_CAL_MAX_DPS || fabsf(d.z) > GYRO_CAL_MAX_DPS) {
        n = 0; p_n = 0; gyro_sum = Vec3(); p_sum = 0; return false;
      }
      gyro_sum += raw_omega; n++;
    }
    if (baro_fresh && p_pa > 30000.f) { p_sum += p_pa; p_n++; }
    if (n >= GYRO_CAL_SAMPLES && p_n >= 10) {
      gyro_bias_dps = gyro_sum * (1.0f / n);
      ground_p_pa = (float)(p_sum / p_n);
      done = true; running = false;
    }
    return done;
  }
};

}  // namespace sensors_common
