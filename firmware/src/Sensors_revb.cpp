// Sensors_revb.cpp – Rückende für das Mainboard rev B (Umgebung teensy41_revb):
// IMU (LSM6DSV16X auf rev B1, ICM-42688-P auf älteren Platinen, Wahl nach WHO_AM_I), BMP390/388, INA239 an SPI1
// über den CS-Decoder, Magnetometer LIS3MDL an I²C, Akkus/ARM/Pyro-Durchgang über die Analogmux
// (lib/mainboard_revb/). Regeln aus BusRevB.h: kein SPI aus einer ISR, keine Analogmessung zwischen
// select() und deselect().
//
// Takt (Loop 250 Hz): IMU jeden Loop als Mittel aller FIFO-Sätze (960 Hz), Barometer mit 50 Hz
// (Chip: Druck ×8, Temperatur ×1, IIR 3), Magnetometer jeden 4. Loop (62,5 Hz, Chip 80 Hz UHP),
// INA239 mit 10 Hz, Mux mit 20 Hz. Magnetometer, INA und Mux laufen versetzt, damit kein Loop
// mehrere langsame Zugriffe sammelt.
//
// Kalibrierung aus dem EEPROM-Emulat (g_cal, revb_test "cal ..."): Achszuordnung IMU und
// Magnetometer, Accel-Offset/-Skala, Hard-/Soft-Iron. Ohne gültige Werte: Achsen aus Config.h,
// Magnetometer nur fürs Log (mag_cal = false).
#include "Sensors_common.h"
#include "BoardRevB.h"
#include "BusRevB.h"
#include "ImuAuto.h"
#include "BMP390.h"
#include "INA239.h"
#include "LIS3MDL.h"
#include "I2cRevB.h"
#include "CalData.h"
#include "Filters.h"

using namespace sensors_common;

extern cal::CalData g_cal;

static BusRevB  bus;
static ImuAuto  imu(bus);
static BMP390   baro(bus, revb::Cs::BARO);
static INA239   ina(bus, revb::INA_SHUNT_OHM, revb::INA_MAX_CURRENT_A);
static LIS3MDL  mag(0x1E);
static SensorStatus status;
static Calibration  padcal;   // Nullpunkte vom Pad (Name "cal" ist der Namespace aus CalData.h)
static Biquad   notch[3];
static uint32_t loop_n = 0;

// Chip -> Körper mit der Kalibrierung, sonst mit Config.h
static Vec3 imuToBody(const float chip[3]) {
  if (g_cal.valid & cal::AXES) {
    float v[3];
    for (int i = 0; i < 3; ++i) v[i] = g_cal.imu_axis_sign[i] * chip[g_cal.imu_axis_map[i]];
    return Vec3(v[0], v[1], v[2]);
  }
  return mapAxes(chip);
}

static Vec3 magToBody(const float chip_gauss[3], bool& calibrated) {
  float c[3] = {chip_gauss[0], chip_gauss[1], chip_gauss[2]};
  calibrated = (g_cal.valid & cal::MAG) && (g_cal.valid & cal::AXES);
  if (g_cal.valid & cal::MAG) {
    float d[3];
    for (int i = 0; i < 3; ++i) d[i] = c[i] - g_cal.mag_offset_gauss[i];
    for (int r = 0; r < 3; ++r)
      c[r] = g_cal.mag_soft_iron[3 * r] * d[0] + g_cal.mag_soft_iron[3 * r + 1] * d[1] + g_cal.mag_soft_iron[3 * r + 2] * d[2];
  }
  if (g_cal.valid & cal::AXES) {
    float v[3];
    for (int i = 0; i < 3; ++i) v[i] = g_cal.mag_axis_sign[i] * c[g_cal.mag_axis_map[i]];
    return Vec3(v[0], v[1], v[2]);
  }
  return Vec3(c[0], c[1], c[2]);
}

void Sensors_setup() {
  bus.begin();
  revb_i2c::begin();
  status.imu_ok   = imu.begin();
  status.baro_ok  = baro.begin();
  status.power_ok = ina.begin();
  status.mag_ok   = mag.begin();
  for (auto& n : notch) n.setNotch(GYRO_NOTCH_HZ, GYRO_NOTCH_Q, LOOP_HZ);
}

const SensorStatus& Sensors_status() { return status; }

void Sensors_read(SensorSample& out) {
  static ImuSample s{};
  static Vec3 last_a(0, 0, G_MS2), last_w, last_m;
  static float last_p = 0, last_t = 0;
  static float vbat1 = 0, vbat2 = 0, arm = 0, pyro_v[2] = {0, 0};
  const uint32_t phase = loop_n++ % 25;   // 25 Loops = 100 ms bei 250 Hz

  out.imu_fresh = false;
  out.imu_n = 0;
  if (status.imu_ok) {
    const int n = imu.readAveraged(s);
    if (n > 0) {
      float acc[3] = {s.acc_ms2[0], s.acc_ms2[1], s.acc_ms2[2]};
      if (g_cal.valid & cal::ACC)
        for (int i = 0; i < 3; ++i) acc[i] = (acc[i] - g_cal.acc_offset_ms2[i]) * g_cal.acc_scale[i];
      last_a = imuToBody(acc);
      last_w = imuToBody(s.gyro_dps);
      out.temp_c = s.temp_c;
      out.imu_fresh = true;
      out.imu_n = n > 255 ? 255 : (uint8_t)n;
      out.imu_fifo_ovr = imu.fifoOverruns();
    }
  }
  out.a_body = last_a;
  Vec3 w = last_w - padcal.gyro_bias_dps;
  out.omega_raw_dps = w;
  if (GYRO_NOTCH_HZ > 0.f && out.imu_fresh) {
    w = Vec3(notch[0].update(w.x), notch[1].update(w.y), notch[2].update(w.z));
  }
  out.omega_dps = w;
  out.a_norm = norm(out.a_body);

  out.baro_fresh = false;
  if (status.baro_ok) {
    float p, t;
    if (baro.read(p, t)) { last_p = p; last_t = t; out.baro_fresh = true; }
  }
  out.p_pa = last_p;
  out.baro_temp_c = last_t;
  out.baro_alt_m = altitudeFromPressure(last_p, padcal.ground_p_pa);

  out.mag_fresh = false;
  if (status.mag_ok && (phase % 4) == 1) {        // 62,5 Hz, nie im selben Loop wie INA/Mux
    MagSample ms;
    if (mag.read(ms)) {
      bool calibrated = false;
      last_m = magToBody(ms.mag_gauss, calibrated);
      out.mag_cal = calibrated;
      out.mag_fresh = true;
    }
  }
  out.mag_body = last_m;

  if (status.power_ok && phase == 2) {            // 10 Hz, INA239 mittelt über 50 ms
    PowerSample ps;
    ina.read(ps);
    out.current_A = ps.current_A;
  }
  if (phase == 0 || phase == 12) {                // Mux-Kanäle mit 20 Hz
    vbat1 = bus.readMuxInputV(revb::Mux::VBAT1);
    vbat2 = bus.readMuxInputV(revb::Mux::VBAT2);
    arm   = bus.readMuxInputV(revb::Mux::ARM);
    pyro_v[0] = bus.readMuxInputV(revb::Mux::PYRO1);
    pyro_v[1] = bus.readMuxInputV(revb::Mux::PYRO2);
  }
  out.vbat1_V = vbat1; out.vbat2_V = vbat2; out.arm_V = arm;
  out.armed = arm > PYRO_ARM_MIN_V;
  for (int i = 0; i < 2; ++i) {
    out.pyro_fitted[i] = revb::PYRO_FITTED[i];
    out.continuity[i] = out.armed && pyro_v[i] > PYRO_CONT_MIN_RATIO * arm;
  }
}

void Sensors_calibrateStart() { padcal.start(); }
bool Sensors_calibrateStep(const SensorSample& s) {
  return padcal.step(s.omega_raw_dps + padcal.gyro_bias_dps, s.imu_fresh, s.p_pa, s.baro_fresh);
}
bool Sensors_calibrated() { return padcal.done; }
void Sensors_getBias(Vec3& g, float& p0) { g = padcal.gyro_bias_dps; p0 = padcal.ground_p_pa; }
void Sensors_setBias(const Vec3& g, float p0) { padcal.gyro_bias_dps = g; padcal.ground_p_pa = p0; padcal.done = true; padcal.running = false; }
