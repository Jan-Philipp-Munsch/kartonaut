// Sensors_breakout.cpp – Rückende für den Breakout-Aufbau (Umgebung teensy41):
// ICM-20948 über die SparkFun-Bibliothek, aber roh ohne DMP (Register, 1,1 kHz intern,
// ±4 g, ±2000 °/s, DLPF 50 Hz), BMP280, INA219. Kein ARM, kein Durchgang.
#include "Sensors_common.h"
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include "ICM_20948.h"
#include <INA219_WE.h>

using namespace sensors_common;

static Adafruit_BMP280 bmp;
static ICM_20948_I2C   imu;
static INA219_WE       ina219(0x40);
static SensorStatus    status;
static Calibration     cal;
static uint32_t        last_baro_us = 0;
static uint32_t        last_power_us = 0;

static bool imuSetup() {
  bool found = false;
  for (int ad0 = 0; ad0 < 2 && !found; ++ad0) {
    imu.begin(Wire, ad0);
    found = (imu.status == ICM_20948_Stat_Ok);
  }
  if (!found) return false;
  imu.swReset(); delay(250);
  imu.sleep(false);
  imu.lowPower(false);
  imu.setSampleMode(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, ICM_20948_Sample_Mode_Continuous);
  ICM_20948_fss_t fss;
  fss.a = gpm4;            // ACC_RANGE_G = 4
  fss.g = dps2000;
  imu.setFullScale(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, fss);
  ICM_20948_dlpcfg_t dlp;
  dlp.a = acc_d50bw4_n68bw8;      // 50 Hz: Servos und Rollmotor regen bei 50..300 Hz an (Plan §2.6)
  dlp.g = gyr_d51bw2_n73bw3;
  imu.setDLPFcfg(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, dlp);
  imu.enableDLPF(ICM_20948_Internal_Acc, true);
  imu.enableDLPF(ICM_20948_Internal_Gyr, true);
  ICM_20948_smplrt_t sr;
  sr.a = 0; sr.g = 0;             // 1125 Hz intern; die Schleife liest mit 100 Hz den letzten Wert
  imu.setSampleRate(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, sr);
  delay(50);
  return imu.status == ICM_20948_Stat_Ok;
}

void Sensors_setup() {
  Wire.begin();
  Wire.setClock(I2C_MAIN_SPEED_HZ);

  status.baro_ok = bmp.begin(0x76);
  if (status.baro_ok) {
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL, Adafruit_BMP280::SAMPLING_X1, Adafruit_BMP280::SAMPLING_X4,
                    Adafruit_BMP280::FILTER_X4, Adafruit_BMP280::STANDBY_MS_1);
  }
  status.imu_ok = imuSetup();
  status.power_ok = ina219.init();
}

const SensorStatus& Sensors_status() { return status; }

void Sensors_read(SensorSample& out) {
  static Vec3 gyro_filt;
  static Vec3 last_a(0, 0, G_MS2), last_w;
  static float last_p = 0, last_t = 0;
  const uint32_t now = micros();

  out.imu_fresh = false;
  if (status.imu_ok && imu.dataReady()) {
    imu.getAGMT();
    const float acc_chip[3]  = {imu.accX() * 1e-3f * G_MS2, imu.accY() * 1e-3f * G_MS2, imu.accZ() * 1e-3f * G_MS2};
    const float gyro_chip[3] = {imu.gyrX(), imu.gyrY(), imu.gyrZ()};
    last_a = mapAxes(acc_chip);
    last_w = mapAxes(gyro_chip);
    out.imu_fresh = true;
  }
  out.a_body = last_a;
  Vec3 w = last_w - cal.gyro_bias_dps;
  if (GYRO_FILT) {
    gyro_filt += (w - gyro_filt) * GYRO_FILT_ALPHA;
    w = gyro_filt;
  }
  out.omega_dps = w;
  out.a_norm = norm(out.a_body);

  // Barometer: 50 Hz reichen (BMP280 ×4 braucht ~10 ms)
  out.baro_fresh = false;
  if (status.baro_ok && now - last_baro_us >= 20000) {
    last_baro_us = now;
    last_p = bmp.readPressure();
    last_t = bmp.readTemperature();
    out.baro_fresh = true;
  }
  out.p_pa = last_p; out.temp_c = last_t;
  out.baro_alt_m = altitudeFromPressure(last_p, cal.ground_p_pa);

  // Versorgung: 10 Hz
  if (status.power_ok && now - last_power_us >= 100000) {
    last_power_us = now;
    out.vbat2_V = ina219.getBusVoltage_V();
    out.current_A = ina219.getCurrent_mA() * 1e-3f;
  }
  out.vbat1_V = 0;
  out.arm_V = 0;
  out.armed = false;                       // keine Messung: Pyro gesperrt (Jan, 22.10.2026)
  out.continuity[0] = out.continuity[1] = false;
  out.pyro_fitted[0] = true; out.pyro_fitted[1] = false;
}

void Sensors_calibrateStart() { cal.start(); }
bool Sensors_calibrateStep(const SensorSample& s) {
  // s.omega_dps ist schon um den alten Bias korrigiert; zurückrechnen auf roh
  return cal.step(s.omega_dps + cal.gyro_bias_dps, s.imu_fresh, s.p_pa, s.baro_fresh);
}
bool Sensors_calibrated() { return cal.done; }
void Sensors_getBias(Vec3& g, float& p0) { g = cal.gyro_bias_dps; p0 = cal.ground_p_pa; }
void Sensors_setBias(const Vec3& g, float p0) { cal.gyro_bias_dps = g; cal.ground_p_pa = p0; cal.done = true; cal.running = false; }

float Sensors_readArmV() { return 0.f; }
float Sensors_readPyroSenseV(int) { return 0.f; }
