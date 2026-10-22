// calib_imu – Kalibrierung und Rauschmessung von IMU und Barometer
//
// Läuft auf beiden Rückenden (Umgebungen calib_imu und calib_imu_revb) über die
// Sensors-Schnittstelle. Ergebnisse kommen als fertige Zeilen für Config.h.
// USB-Serial 115200 Bd, Tasten:
//
//   g   Gyro-Bias und Rauschen: 30 s ruhig liegen lassen. Ausgabe: Bias (°/s),
//       Standardabweichung je Achse bei 100 Hz und über 1-s-Mittel (Bias-Drift),
//       dazu GYRO_BIAS_DPS_* für Config.h.
//   6   Sechs-Lagen-Kalibrierung des Beschleunigungssensors: nacheinander +z, −z,
//       +x, −x, +y, −y nach oben legen, je Lage Taste drücken. Ausgabe: Bias und
//       Skalierung je Achse (ACCEL_BIAS_MS2, ACCEL_SCALE).
//   b   Barometer-Rauschen: 30 s, Standardabweichung der Höhe (KALMAN_MEAS_STD_M)
//       und der Drift über die Messung.
//   s   Rohdaten-Strom als CSV bei 100 Hz (t_ms, ax, ay, az, gx, gy, gz, p_pa, alt_m),
//       bis eine Taste kommt. Für simulation/scripts/analyze_imu_noise.py
//       (Allan-Abweichung, Rauschdichten für tvcsim.NoiseParams).
//   l   Lage live: Neigung, Yaw/Pitch-Fehler, Roll aus der Gyro-Quaternion
//       (Attitude), initialisiert aus der Ruhelage. Prüft die Achsen und
//       chipToBody(): Spitze nach oben, nach +x kippen -> Pitch-Fehler negativ.
//   h   Hilfe
#include <Arduino.h>
#include "Config.h"
#include "Board.h"
#include "Sensors.h"
#include "Attitude.h"

static void help() {
  Serial.println("\n=== Kartonaut calib_imu (" BOARD_NAME ") ===");
  Serial.println("g Gyro-Bias/Rauschen 30 s | 6 Sechs-Lagen-Accel | b Baro-Rauschen 30 s | s CSV-Strom | l Lage live | h Hilfe");
}

static bool keyPressed() {
  if (!Serial.available()) return false;
  while (Serial.available()) Serial.read();
  return true;
}

static void waitKey() { while (!Serial.available()) {} while (Serial.available()) Serial.read(); }

static void gyroNoise() {
  Serial.println("Gyro: 30 s ruhig liegen lassen ...");
  const int N = 3000;
  Vec3 sum, sq;             // 100-Hz-Werte
  Vec3 sum1, sq1, acc1;     // 1-s-Mittel
  int n = 0, n1 = 0, k1 = 0;
  const uint32_t t0 = millis();
  uint32_t next = t0;
  while (n < N) {
    if ((int32_t)(millis() - next) < 0) continue;
    next += 10;
    Vec3 a, w;
    if (!Read_IMU_raw(a, w)) continue;
    sum += w; sq += Vec3(w.x * w.x, w.y * w.y, w.z * w.z); ++n;
    acc1 += w; ++k1;
    if (k1 == 100) {
      const Vec3 m = acc1 * 0.01f;
      sum1 += m; sq1 += Vec3(m.x * m.x, m.y * m.y, m.z * m.z); ++n1;
      acc1 = Vec3(); k1 = 0;
      Serial.printf("  %2d s  Mittel %+.3f %+.3f %+.3f °/s\n", n1, m.x, m.y, m.z);
    }
  }
  const Vec3 bias = sum * (1.0f / n);
  auto sd = [](float s2, float m, int k) { return sqrtf(fmaxf(0.0f, s2 / k - m * m)); };
  const Vec3 std100(sd(sq.x, bias.x, n), sd(sq.y, bias.y, n), sd(sq.z, bias.z, n));
  const Vec3 m1 = sum1 * (1.0f / n1);
  const Vec3 std1(sd(sq1.x, m1.x, n1), sd(sq1.y, m1.y, n1), sd(sq1.z, m1.z, n1));
  Serial.printf("Bias            %+.4f %+.4f %+.4f °/s\n", bias.x, bias.y, bias.z);
  Serial.printf("Std bei 100 Hz   %.4f  %.4f  %.4f °/s  (tvcsim NoiseParams.w_sigma)\n", std100.x, std100.y, std100.z);
  Serial.printf("Std der 1-s-Mittel %.4f  %.4f  %.4f °/s  (Bias-Instabilität; Drift in 10 s Boost: %.2f°)\n",
                std1.x, std1.y, std1.z, fmaxf(fmaxf(std1.x, std1.y), std1.z) * 10.0f);
  Serial.println("Für Config.h (Rückfall, die Rampenkalibrierung misst neu):");
  Serial.printf("constexpr float GYRO_BIAS_DPS_X  = %+.3ff;\nconstexpr float GYRO_BIAS_DPS_Y  = %+.3ff;\nconstexpr float GYRO_BIAS_DPS_Z  = %+.3ff;\n",
                bias.x, bias.y, bias.z);
}

static Vec3 averageAccel(int samples) {
  Vec3 sum; int n = 0;
  while (n < samples) {
    Vec3 a, w;
    if (Read_IMU_raw(a, w)) { sum += a; ++n; }
    delay(10);
  }
  return sum * (1.0f / n);
}

static void sixPosition() {
  const char* names[6] = {"+z nach oben (Spitze oben)", "-z nach oben (Spitze unten)", "+x nach oben", "-x nach oben", "+y nach oben", "-y nach oben"};
  Vec3 m[6];
  for (int i = 0; i < 6; ++i) {
    Serial.printf("Lage %d/6: %s, dann Taste\n", i + 1, names[i]);
    waitKey();
    m[i] = averageAccel(200);
    Serial.printf("  gemessen %+.3f %+.3f %+.3f m/s²\n", m[i].x, m[i].y, m[i].z);
  }
  // Bias = Mittel der beiden Gegenlagen, Skalierung = g / halber Abstand
  const float bz = 0.5f * (m[0].z + m[1].z), sz = 2.0f * G_MS2 / (m[0].z - m[1].z);
  const float bx = 0.5f * (m[2].x + m[3].x), sx = 2.0f * G_MS2 / (m[2].x - m[3].x);
  const float by = 0.5f * (m[4].y + m[5].y), sy = 2.0f * G_MS2 / (m[4].y - m[5].y);
  Serial.println("Für Config.h:");
  Serial.printf("constexpr Vec3  ACCEL_BIAS_MS2   = Vec3(%+.4ff, %+.4ff, %+.4ff);\n", bx, by, bz);
  Serial.printf("constexpr Vec3  ACCEL_SCALE      = Vec3(%.5ff, %.5ff, %.5ff);\n", sx, sy, sz);
  Serial.println("(Skalierung sollte zwischen 0,98 und 1,02 liegen; sonst Lage oder Achsen prüfen.)");
}

static void baroNoise() {
  Serial.println("Barometer: 30 s ruhig, Fenster zu, nicht anpusten ...");
  Sensors_calibrateBaroGround(BARO_CAL_SAMPLES);
  double sum = 0, sq = 0; int n = 0;
  float first = 0, last = 0;
  const uint32_t t0 = millis();
  while (millis() - t0 < 30000) {
    BaroData b;
    if (Read_Baro(b) && b.fresh) {
      if (n == 0) first = b.alt_m;
      last = b.alt_m;
      sum += b.alt_m; sq += double(b.alt_m) * b.alt_m; ++n;
    }
    delay(10);
  }
  const double mean = sum / n;
  const double std = sqrt(fmax(0.0, sq / n - mean * mean));
  Serial.printf("%d Messungen, Mittel %.2f m, Std %.3f m, Drift %.2f m über 30 s\n", n, mean, std, last - first);
  Serial.printf("constexpr float KALMAN_MEAS_STD_M    = %.2ff;   // gemessen %.3f m, mit Reserve\n", std * 2.0, std);
}

static void stream() {
  Serial.println("t_ms,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,p_pa,alt_m");
  uint32_t next = millis();
  while (!keyPressed()) {
    if ((int32_t)(millis() - next) < 0) continue;
    next += 10;
    Vec3 a, w; BaroData b;
    if (!Read_IMU_raw(a, w)) continue;
    Read_Baro(b);
    Serial.printf("%lu,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.1f,%.3f\n", (unsigned long)millis(),
                  a.x, a.y, a.z, w.x, w.y, w.z, b.pressure_pa, b.alt_m);
  }
}

static void liveAttitude() {
  Serial.println("Lage: 1 s ruhig für die Startlage ...");
  Vec3 bias, sd;
  Sensors_calibrateGyro(100, 2.0f, bias, sd);
  Attitude att;
  att.initFromAccel(averageAccel(50));
  Serial.println("Bewegen; Taste beendet. Spitze oben: Neigung ~0. Um +x gedreht -> Yaw-Fehler positiv, um +y -> Pitch-Fehler positiv.");
  uint32_t next = millis(), print = millis();
  while (!keyPressed()) {
    if ((int32_t)(millis() - next) < 0) continue;
    next += 10;
    ImuData d;
    if (Read_IMU(d) && d.fresh) att.integrateDps(d.omega_dps, 0.01f);
    if (millis() - print >= 200) {
      print = millis();
      Serial.printf("Neigung %6.2f°  Yaw %+7.2f  Pitch %+7.2f  Roll %+7.2f  | a %+.2f %+.2f %+.2f\n",
                    att.tiltDeg(), att.yawErrDeg(), att.pitchErrDeg(), att.rollDeg(), d.a_body.x, d.a_body.y, d.a_body.z);
    }
  }
}

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) {}
  Sensors_setup();
  const SensorStatus& st = Sensors_status();
  Serial.printf("IMU %s, Barometer %s\n", st.imu ? "ok" : "FEHLT", st.baro ? "ok" : "FEHLT");
  help();
}

void loop() {
  if (!Serial.available()) return;
  const int c = Serial.read();
  while (Serial.available()) Serial.read();
  switch (c) {
    case 'g': gyroNoise(); break;
    case '6': sixPosition(); break;
    case 'b': baroNoise(); break;
    case 's': stream(); break;
    case 'l': liveAttitude(); break;
    case 'h': help(); break;
    default: break;
  }
}
