// SensorsBreakout.cpp – Rückende für den heutigen Aufbau mit Breakouts:
// BMP280 (I²C 0x76), ICM-20948 über DMP/FIFO (nur rohe Accel- und Gyro-Pakete),
// INA219 (0x40). Siehe Sensors.h.
#ifndef BOARD_REVB
#include "Sensors.h"
#include <Wire.h>
#include <Adafruit_BMP280.h>
#include "ICM_20948.h"
#include <INA219_WE.h>

namespace {
constexpr float ACC_LSB_PER_G    = 8192.0f;   // DMP-Rohwerte ±4 g. Reicht für die E12 (3,8 g bei 0,761 kg), nicht für F35.
constexpr float GYRO_LSB_PER_DPS = 16.384f;   // ±2000 °/s

Adafruit_BMP280 bmp;
ICM_20948_I2C   imu;
INA219_WE       ina219(0x40);
SensorStatus    status;
void (*idle_hook)() = nullptr;
float ground_pa = 101325.0f;
Vec3  gyro_bias_dps(GYRO_BIAS_DPS_X, GYRO_BIAS_DPS_Y, GYRO_BIAS_DPS_Z);
Vec3  last_a, last_w;
Vec3  gyro_filt;

inline Vec3 correctAccel(const Vec3& raw) {
  return Vec3((raw.x - ACCEL_BIAS_MS2.x) * ACCEL_SCALE.x,
              (raw.y - ACCEL_BIAS_MS2.y) * ACCEL_SCALE.y,
              (raw.z - ACCEL_BIAS_MS2.z) * ACCEL_SCALE.z);
}

// Die FIFO bis leer (oder cap) lesen und Accel/Gyro mitteln. Liefert die Zahl der Pakete.
int drainFifo(Vec3& a_sum, Vec3& w_sum, int& n_a, int& n_w) {
  n_a = n_w = 0;
  int frames = 0;
  for (int i = 0; i < IMU_FIFO_READ_CAP; ++i) {
    icm_20948_DMP_data_t d;
    imu.readDMPdataFromFIFO(&d);
    if (!(imu.status == ICM_20948_Stat_Ok || imu.status == ICM_20948_Stat_FIFOMoreDataAvail)) break;
    ++frames;
    if (d.header & DMP_header_bitmap_Accel) {
      a_sum += Vec3(d.Raw_Accel.Data.X, d.Raw_Accel.Data.Y, d.Raw_Accel.Data.Z) * (G_MS2 / ACC_LSB_PER_G);
      ++n_a;
    }
    // Raw_Gyro wird nur beim Gyro-Paket (Bit 0x4000) gefüllt, nicht beim Calibr-Paket (Befund 9)
    if (d.header & DMP_header_bitmap_Gyro) {
      w_sum += Vec3(d.Raw_Gyro.Data.X, d.Raw_Gyro.Data.Y, d.Raw_Gyro.Data.Z) * (1.0f / GYRO_LSB_PER_DPS);
      ++n_w;
    }
    if (imu.status != ICM_20948_Stat_FIFOMoreDataAvail) break;
  }
  return frames;
}
}  // namespace

bool Sensors_setup() {
  status.backend = BOARD_NAME;
  Wire.begin();
  Wire.setClock(I2C_MAIN_SPEED_HZ);

  status.baro = bmp.begin(0x76);
  if (status.baro) {
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL, Adafruit_BMP280::SAMPLING_X1,
                    Adafruit_BMP280::SAMPLING_X4, Adafruit_BMP280::FILTER_X4,
                    Adafruit_BMP280::STANDBY_MS_1);
  }

  imu.begin(Wire, 0);
  status.imu = (imu.status == ICM_20948_Stat_Ok);
  if (status.imu) {
    bool ok = true;
    ok &= (imu.initializeDMP() == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMPSensor(INV_ICM20948_SENSOR_ACCELEROMETER) == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMPSensor(INV_ICM20948_SENSOR_GYROSCOPE) == ICM_20948_Stat_Ok);
    ok &= (imu.setDMPODRrate(DMP_ODR_Reg_Accel, 0) == ICM_20948_Stat_Ok);
    ok &= (imu.setDMPODRrate(DMP_ODR_Reg_Gyro, 0) == ICM_20948_Stat_Ok);
    ok &= (imu.enableFIFO() == ICM_20948_Stat_Ok);
    ok &= (imu.enableDMP() == ICM_20948_Stat_Ok);
    ok &= (imu.resetDMP() == ICM_20948_Stat_Ok);
    ok &= (imu.resetFIFO() == ICM_20948_Stat_Ok);
    status.imu = ok;
  }

  status.power = ina219.init();
  if (status.power) ina219.setShuntSizeInOhms(INA_SHUNT_OHM_BREAKOUT);

  if (status.baro) Sensors_calibrateBaroGround(BARO_CAL_SAMPLES);
  return status.imu && status.baro;
}

const SensorStatus& Sensors_status() { return status; }
void Sensors_setIdleHook(void (*fn)()) { idle_hook = fn; }
void Sensors_idle() { if (idle_hook) idle_hook(); }

bool Read_IMU_raw(Vec3& a, Vec3& w) {
  if (!status.imu) return false;
  Vec3 a_sum, w_sum; int na, nw;
  drainFifo(a_sum, w_sum, na, nw);
  if (na == 0 || nw == 0) return false;
  a = chipToBody(a_sum * (1.0f / na));
  w = chipToBody(w_sum * (1.0f / nw));
  return true;
}

bool Read_IMU(ImuData& out) {
  out.a_body = last_a;
  out.omega_dps = last_w;
  out.fresh = false;
  out.samples = 0;
  if (!status.imu) return false;

  Vec3 a_sum, w_sum; int na, nw;
  drainFifo(a_sum, w_sum, na, nw);
  if (na > 0) {
    last_a = correctAccel(chipToBody(a_sum * (1.0f / na)));
    out.a_body = last_a;
  }
  if (nw > 0) {
    Vec3 w = chipToBody(w_sum * (1.0f / nw)) - gyro_bias_dps;
    gyro_filt += (w - gyro_filt) * GYRO_FILT_ALPHA;
    last_w = GYRO_FILT ? gyro_filt : w;
    out.omega_dps = last_w;
  }
  out.fresh = (na > 0 && nw > 0);
  out.samples = uint8_t(min(na, nw));
  if (out.fresh) out.stamp_us = micros();
  return out.fresh;
}

bool Read_Baro(BaroData& out) {
  out.fresh = false;
  if (!status.baro) return false;
  out.pressure_pa = bmp.readPressure();
  out.temp_c = bmp.readTemperature();
  out.alt_m = 44330.0f * (1.0f - powf(out.pressure_pa / ground_pa, 0.190295f));
  out.fresh = true;
  return true;
}

bool Read_Power(PowerData& out) {
  out.fresh = false;
  if (!status.power) return false;
  out.bus_V = ina219.getBusVoltage_V();
  out.current_A = ina219.getCurrent_mA() * 0.001f;
  out.vbat2_V = out.bus_V;      // der INA219 hängt im Akkupfad
  out.fresh = true;
  return true;
}

bool Sensors_calibrateGyro(uint16_t samples, float max_std_dps, Vec3& bias, Vec3& std_dps) {
  if (!status.imu) return false;
  Vec3 sum, sq;
  uint16_t n = 0;
  const uint32_t t0 = millis();
  while (n < samples && millis() - t0 < 10000) {
    Sensors_idle();
    Vec3 a_sum, w_sum; int na, nw;
    drainFifo(a_sum, w_sum, na, nw);
    if (nw == 0) { delay(2); continue; }
    const Vec3 w = chipToBody(w_sum * (1.0f / nw));
    sum += w; sq += Vec3(w.x * w.x, w.y * w.y, w.z * w.z);
    ++n;
    delay(5);
  }
  if (n < samples / 2) return false;
  bias = sum * (1.0f / n);
  std_dps = Vec3(sqrtf(max(0.0f, sq.x / n - bias.x * bias.x)),
                 sqrtf(max(0.0f, sq.y / n - bias.y * bias.y)),
                 sqrtf(max(0.0f, sq.z / n - bias.z * bias.z)));
  if (std_dps.x > max_std_dps || std_dps.y > max_std_dps || std_dps.z > max_std_dps) return false;
  gyro_bias_dps = bias;
  return true;
}

void Sensors_setGyroBias(const Vec3& b) { gyro_bias_dps = b; }
Vec3 Sensors_gyroBias() { return gyro_bias_dps; }

void Sensors_calibrateBaroGround(uint16_t samples) {
  if (!status.baro) return;
  double sum = 0;
  for (uint16_t i = 0; i < samples; ++i) { Sensors_idle(); sum += bmp.readPressure(); delay(5); }
  ground_pa = float(sum / samples);
}

void  Sensors_setGroundPressure(float p0) { ground_pa = p0; }
float Sensors_groundPressure() { return ground_pa; }

#endif  // !BOARD_REVB
