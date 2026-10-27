// Sensors_revb.cpp – Rückende für das Mainboard rev B (Umgebung teensy41_revb):
// ICM-42688-P, BMP390, INA239 an SPI1 über den CS-Decoder, Akkus/ARM/Pyro-Durchgang über
// die Analogmux (lib/mainboard_revb/). Regeln aus BusRevB.h: kein SPI aus einer ISR, keine
// Analogmessung zwischen select() und deselect().
#include "Sensors_common.h"
#include "BoardRevB.h"
#include "BusRevB.h"
#include "ICM42688.h"
#include "BMP390.h"
#include "INA239.h"

using namespace sensors_common;

static BusRevB  bus;
static ICM42688 imu(bus);
static BMP390   baro(bus, revb::Cs::BARO);
static INA239   ina(bus, revb::INA_SHUNT_OHM, revb::INA_MAX_CURRENT_A);
static SensorStatus status;
static Calibration  cal;
static uint32_t last_power_us = 0, last_mux_us = 0;

void Sensors_setup() {
  bus.begin();
  status.imu_ok   = imu.begin();
  status.baro_ok  = baro.begin();
  status.power_ok = ina.begin();
}

const SensorStatus& Sensors_status() { return status; }

void Sensors_read(SensorSample& out) {
  static Vec3 gyro_filt;
  static Vec3 last_a(0, 0, G_MS2), last_w;
  static float last_p = 0, last_t = 0;
  static float vbat1 = 0, vbat2 = 0, arm = 0, pyro_v[2] = {0, 0};
  const uint32_t now = micros();

  out.imu_fresh = false;
  if (status.imu_ok && imu.dataReady()) {
    ImuSample s;
    imu.read(s);
    last_a = mapAxes(s.acc_ms2);
    last_w = mapAxes(s.gyro_dps);
    out.temp_c = s.temp_c;
    out.imu_fresh = true;
  }
  out.a_body = last_a;
  Vec3 w = last_w - cal.gyro_bias_dps;
  if (GYRO_FILT) { gyro_filt += (w - gyro_filt) * GYRO_FILT_ALPHA; w = gyro_filt; }
  out.omega_dps = w;
  out.a_norm = norm(out.a_body);

  out.baro_fresh = false;
  if (status.baro_ok) {
    float p, t;
    if (baro.read(p, t)) { last_p = p; last_t = t; out.baro_fresh = true; }
  }
  out.p_pa = last_p;
  if (!out.imu_fresh) out.temp_c = last_t;
  out.baro_alt_m = altitudeFromPressure(last_p, cal.ground_p_pa);

  if (status.power_ok && now - last_power_us >= 100000) {   // INA239 mittelt über 50 ms
    last_power_us = now;
    PowerSample ps;
    ina.read(ps);
    out.current_A = ps.current_A;
  }
  if (now - last_mux_us >= 50000) {                          // Mux-Kanäle mit 20 Hz
    last_mux_us = now;
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

void Sensors_calibrateStart() { cal.start(); }
bool Sensors_calibrateStep(const SensorSample& s) {
  return cal.step(s.omega_dps + cal.gyro_bias_dps, s.imu_fresh, s.p_pa, s.baro_fresh);
}
bool Sensors_calibrated() { return cal.done; }
void Sensors_getBias(Vec3& g, float& p0) { g = cal.gyro_bias_dps; p0 = cal.ground_p_pa; }
void Sensors_setBias(const Vec3& g, float p0) { cal.gyro_bias_dps = g; cal.ground_p_pa = p0; cal.done = true; cal.running = false; }

float Sensors_readArmV() { return bus.readMuxInputV(revb::Mux::ARM); }
float Sensors_readPyroSenseV(int ch) { return bus.readMuxInputV(ch == 0 ? revb::Mux::PYRO1 : revb::Mux::PYRO2); }
