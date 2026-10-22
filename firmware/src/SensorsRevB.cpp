// SensorsRevB.cpp – Rückende für das Mainboard rev B: ICM-42688-P, BMP390 und
// INA239 an SPI1 (lib/mainboard_revb), Akkus, ARM und Pyro-Durchgang über die
// Analogmux 74HC4051. Siehe Sensors.h und BusRevB.h (Regeln: kein SPI aus einer
// ISR, keine Analogmessung zwischen select() und deselect()).
#ifdef BOARD_REVB
#include "Sensors.h"
#include "BusRevB.h"
#include "ICM42688.h"
#include "BMP390.h"
#include "INA239.h"

namespace {
BusRevB  bus;
ICM42688 imu(bus);
BMP390   baro(bus, revb::Cs::BARO);
INA239   ina(bus, revb::INA_SHUNT_OHM, revb::INA_MAX_CURRENT_A);
SensorStatus status;
void (*idle_hook)() = nullptr;
float ground_pa = 101325.0f;
Vec3  gyro_bias_dps(GYRO_BIAS_DPS_X, GYRO_BIAS_DPS_Y, GYRO_BIAS_DPS_Z);
Vec3  last_a, last_w;
Vec3  gyro_filt;
float last_p = 0, last_t = 0;

inline Vec3 correctAccel(const Vec3& raw) {
  return Vec3((raw.x - ACCEL_BIAS_MS2.x) * ACCEL_SCALE.x,
              (raw.y - ACCEL_BIAS_MS2.y) * ACCEL_SCALE.y,
              (raw.z - ACCEL_BIAS_MS2.z) * ACCEL_SCALE.z);
}

inline void toBody(const ImuSample& s, Vec3& a, Vec3& w) {
  a = chipToBody(Vec3(s.acc_ms2[0], s.acc_ms2[1], s.acc_ms2[2]));
  w = chipToBody(Vec3(s.gyro_dps[0], s.gyro_dps[1], s.gyro_dps[2]));
}
}  // namespace

BusRevB& Sensors_bus() { return bus; }

bool Sensors_setup() {
  status.backend = BOARD_NAME;
  bus.begin();
  status.imu  = imu.begin();
  status.baro = baro.begin();
  status.power = ina.begin();
  if (status.baro) Sensors_calibrateBaroGround(BARO_CAL_SAMPLES);
  return status.imu && status.baro;
}

const SensorStatus& Sensors_status() { return status; }
void Sensors_setIdleHook(void (*fn)()) { idle_hook = fn; }
void Sensors_idle() { if (idle_hook) idle_hook(); }

bool Read_IMU_raw(Vec3& a, Vec3& w) {
  if (!status.imu) return false;
  ImuSample s;
  imu.read(s);
  toBody(s, a, w);
  return true;
}

bool Read_IMU(ImuData& out) {
  out.a_body = last_a;
  out.omega_dps = last_w;
  out.fresh = false;
  out.samples = 0;
  if (!status.imu) return false;
  // 1 kHz ODR, UI-Filter 50 Hz (ICM42688::begin): der letzte Wert je Loop reicht.
  if (!imu.dataReady()) return false;
  ImuSample s;
  imu.read(s);
  Vec3 a, w;
  toBody(s, a, w);
  last_a = correctAccel(a);
  w = w - gyro_bias_dps;
  gyro_filt += (w - gyro_filt) * GYRO_FILT_ALPHA;
  last_w = GYRO_FILT ? gyro_filt : w;
  out.a_body = last_a;
  out.omega_dps = last_w;
  out.temp_c = s.temp_c;
  out.fresh = true;
  out.samples = 1;
  out.stamp_us = micros();
  return true;
}

bool Read_Baro(BaroData& out) {
  out.fresh = false;
  if (!status.baro) return false;
  float p, t;
  if (baro.read(p, t)) { last_p = p; last_t = t; out.fresh = true; }
  out.pressure_pa = last_p;
  out.temp_c = last_t;
  out.alt_m = BMP390::altitude_m(last_p, ground_pa);
  return out.fresh;
}

bool Read_Power(PowerData& out) {
  out.vbat1_V = bus.readMuxInputV(revb::Mux::VBAT1);
  out.vbat2_V = bus.readMuxInputV(revb::Mux::VBAT2);
  out.arm_V   = bus.readMuxInputV(revb::Mux::ARM);
  out.armed   = out.arm_V > ARM_MIN_V;
  const revb::Mux ch[4] = {revb::Mux::PYRO1, revb::Mux::PYRO2, revb::Mux::PYRO3, revb::Mux::PYRO4};
  for (int i = 0; i < 4; ++i) {
    out.pyro_V[i] = PYRO_FITTED[i] ? bus.readMuxInputV(ch[i]) : 0.0f;
    // Der Zünder zieht den Drain auf VBAT_ARMED: Durchgang nur bei scharfem Schalter sichtbar
    out.continuity[i] = PYRO_FITTED[i] && out.armed && out.pyro_V[i] > PYRO_CONT_FRACTION * out.arm_V;
  }
  if (status.power) {
    PowerSample s;
    ina.read(s);
    out.bus_V = s.bus_V;
    out.current_A = s.current_A;
  }
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
    if (!imu.dataReady()) { delayMicroseconds(200); continue; }
    ImuSample s;
    imu.read(s);
    Vec3 a, w;
    toBody(s, a, w);
    sum += w; sq += Vec3(w.x * w.x, w.y * w.y, w.z * w.z);
    ++n;
    delay(5);   // 200 Hz statt 1 kHz: unabhängigere Werte für die Standardabweichung
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
  uint16_t n = 0;
  const uint32_t t0 = millis();
  while (n < samples && millis() - t0 < 5000) {
    Sensors_idle();
    float p, t;
    if (baro.read(p, t)) { sum += p; ++n; }
    delay(2);
  }
  if (n > 0) ground_pa = float(sum / n);
}

void  Sensors_setGroundPressure(float p0) { ground_pa = p0; }
float Sensors_groundPressure() { return ground_pa; }

#endif  // BOARD_REVB
