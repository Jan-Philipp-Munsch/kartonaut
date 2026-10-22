// kartonaut_sil.cpp – C-Schnittstelle des Flugkerns für Software-in-the-Loop
//
// Baut lib/flightcore (Attitude, KalmanZ, FlightState, PyroLogic, TvcController)
// zusammen mit diesem Wrapper zu einer gemeinsam ladbaren Bibliothek, die
// simulation/tvcsim/sil.py über ctypes in die 6DOF-Simulation einhängt. Ein
// Schritt hier entspricht einem Durchlauf von loop() in src/main.cpp, ohne
// Hardware: dieselbe Lage, derselbe Kalman, derselbe Automat, dieselbe
// Pyro-Logik, derselbe Regler, dieselbe Servo-Rundung.
//
// Bauen macht tvcsim.sil.build_library() selbst; von Hand:
//   g++ -std=c++17 -O2 -shared -fPIC -Ilib/flightcore lib/flightcore/*.cpp sil/kartonaut_sil.cpp -o libkartonaut_sil.so
#include <math.h>
#include <stdint.h>
#include <new>

#include "Attitude.h"
#include "FlightState.h"
#include "KalmanZ.h"
#include "Pyro.h"
#include "TvcController.h"

#if defined(_WIN32)
#define SIL_API extern "C" __declspec(dllexport)
#else
#define SIL_API extern "C" __attribute__((visibility("default")))
#endif

// Alle Felder 4 Byte, damit ctypes ohne Packungsangaben dieselbe Anordnung hat.
// Reihenfolge = tvcsim/sil.py, SilConfig._fields_.
struct SilConfig {
  float g_ms2;
  // TVC-Regler (TvcParams)
  float kp, ki, kd, error_scale, mass_kg, moment_arm_m, a_norm_min, a_norm_alpha, tvc_max_deg, i_max_deg_s;
  float yaw_gain, yaw_offset, yaw_min, yaw_max;
  float pitch_gain, pitch_offset, pitch_min, pitch_max;
  // Flugzustandsautomat (Abweichungen von FlightStateConfig)
  float liftoff_g; uint32_t liftoff_hold_ms;
  float burnout_g; uint32_t burn_max_ms, coast_max_ms;
  float abort_tilt_deg;
  float apogee_vz_ms; uint32_t apogee_hold_ms; float apogee_baro_drop_m;
  float min_flight_alt_m;
  // Kalman
  float kalman_meas_std_m, kalman_sigma_acc, kalman_init_var;
  // Pyro
  uint32_t pyro_pulse_ms, pyro_backup_delay_ms;
  int32_t chute_channel, backup_channel;
  // Schalter
  int32_t control_enabled;   // PY_CONTROL_ACTIVE
  int32_t quantize_servo;    // ganze Servo-Grad wie Control.cpp
};

struct SilOutput {
  int32_t phase;             // KnPhase
  int32_t event;             // 1, wenn in diesem Schritt ein Übergang stattfand
  int32_t event_reason;      // KnEventReason
  float   tilt_deg, yaw_err_deg, pitch_err_deg, roll_deg;
  float   q[4];
  float   alt_m, vz_ms;      // Kalman
  float   yaw_moment_nm, pitch_moment_nm;
  float   tvc_yaw_deg, tvc_pitch_deg;       // was der Kardan bei linearer Geometrie macht (nach Servo-Rundung)
  float   servo_yaw_deg, servo_pitch_deg;   // was an den Servo geht
  int32_t yaw_saturated, pitch_saturated;
  int32_t pyro_fire_mask;    // Gate-Ausgänge in diesem Schritt
  int32_t pyro_fired_mask;   // Kanäle, die schon gezündet haben
  float   accel_norm_filt;
};

namespace {

struct Sil {
  SilConfig   cfg;
  Attitude    att;
  KalmanZ     kal;
  FlightState fs;
  PyroLogic   pyro;
  TvcController tvc;
  bool        calibrated = false;
  bool        force_ready = false;
  float       last_baro = 0.0f;

  static FlightStateConfig fsConfig(const SilConfig& c) {
    FlightStateConfig f;
    f.g_ms2 = c.g_ms2;
    f.liftoff_g = c.liftoff_g; f.liftoff_hold_ms = c.liftoff_hold_ms;
    f.burnout_g = c.burnout_g; f.burn_max_ms = c.burn_max_ms;
    f.coast_max_ms = c.coast_max_ms; f.abort_tilt_deg = c.abort_tilt_deg;
    f.apogee_vz_ms = c.apogee_vz_ms; f.apogee_hold_ms = c.apogee_hold_ms; f.apogee_baro_drop_m = c.apogee_baro_drop_m;
    f.min_flight_alt_m = c.min_flight_alt_m;
    return f;
  }

  static TvcParams tvcParams(const SilConfig& c) {
    TvcParams p;
    p.kp = c.kp; p.ki = c.ki; p.kd = c.kd; p.error_scale = c.error_scale;
    p.mass_kg = c.mass_kg; p.moment_arm_m = c.moment_arm_m;
    p.a_norm_min = c.a_norm_min; p.a_norm_alpha = c.a_norm_alpha;
    p.tvc_max_deg = c.tvc_max_deg; p.i_max_deg_s = c.i_max_deg_s;
    p.yaw_gain = c.yaw_gain; p.yaw_offset = c.yaw_offset; p.yaw_min = c.yaw_min; p.yaw_max = c.yaw_max;
    p.pitch_gain = c.pitch_gain; p.pitch_offset = c.pitch_offset; p.pitch_min = c.pitch_min; p.pitch_max = c.pitch_max;
    return p;
  }

  explicit Sil(const SilConfig& c)
      : cfg(c), fs(fsConfig(c)), pyro(PyroLogic::Config(c.pyro_pulse_ms)), tvc(tvcParams(c)) {
    pyro.setFitted(c.chute_channel, true);
    pyro.setFitted(c.backup_channel, true);
  }
};

inline float quantize(float servo_deg, int on) {
  if (!on) return servo_deg;
  const float d = servo_deg < 0.0f ? 0.0f : (servo_deg > 180.0f ? 180.0f : servo_deg);
  return float(lroundf(d));
}

}  // namespace

SIL_API void* sil_create(const SilConfig* cfg) {
  return new (std::nothrow) Sil(*cfg);
}

SIL_API void sil_destroy(void* h) {
  delete static_cast<Sil*>(h);
}

SIL_API int32_t sil_config_size() { return int32_t(sizeof(SilConfig)); }
SIL_API int32_t sil_output_size() { return int32_t(sizeof(SilOutput)); }

// Rampenkalibrierung wie calibrate() in main.cpp: Startlage aus der gemittelten
// spezifischen Kraft, Kalman auf null, Regler zurück; danach im nächsten Schritt
// PAD_READY erzwingen (ARM und Durchgang gelten in der Simulation als gegeben).
SIL_API int32_t sil_init_pad(void* h, const float f_body[3]) {
  Sil& s = *static_cast<Sil*>(h);
  if (!s.att.initFromAccel(Vec3(f_body[0], f_body[1], f_body[2]))) return 0;
  s.kal.setMeasStd(s.cfg.kalman_meas_std_m);
  s.kal.setState(0.0f, 0.0f);
  s.kal.setPDiag(s.cfg.kalman_init_var, s.cfg.kalman_init_var);
  s.tvc.reset();
  s.calibrated = true;
  s.force_ready = true;
  return 1;
}

// Ein Durchlauf von loop(). f_body: spezifische Kraft [m/s²], gyro: Drehrate [°/s],
// beides im Körpersystem der Firmware (x, y quer, z Rollachse). baro_alt_m: neue
// Barometermessung oder NaN, wenn in diesem Takt keine kam.
SIL_API void sil_step(void* h, uint32_t t_ms, float dt, const float f_body[3], const float gyro_dps[3],
                      float baro_alt_m, SilOutput* out) {
  Sil& s = *static_cast<Sil*>(h);
  const Vec3 f(f_body[0], f_body[1], f_body[2]);
  const Vec3 w(gyro_dps[0], gyro_dps[1], gyro_dps[2]);

  // Lage und Höhe
  if (s.calibrated) s.att.integrateDps(w, dt);
  const Vec3 a_nav = s.att.accelNav(f, s.cfg.g_ms2);
  s.tvc.updateAccelNorm(norm(f));
  s.kal.setDt(dt, s.cfg.kalman_sigma_acc);
  s.kal.predict(a_nav.z);
  if (!isnan(baro_alt_m)) { s.kal.update(baro_alt_m); s.last_baro = baro_alt_m; }

  // Zustandsautomat
  FlightInputs in;
  in.t_ms = t_ms;
  in.accel_z_g = f.z / s.cfg.g_ms2;
  in.accel_mag_g = norm(f) / s.cfg.g_ms2;
  in.gyro_mag_dps = norm(w);
  in.vz_ms = s.kal.vz();
  in.alt_m = s.kal.z();
  in.baro_alt_m = s.last_baro;
  in.tilt_deg = s.att.tiltDeg();
  in.armed = true;
  in.continuity = s.pyro.continuity(s.cfg.chute_channel);
  in.calibrated = s.calibrated;
  in.cmd_force_ready = s.force_ready;
  s.force_ready = false;
  out->event = s.fs.update(in) ? 1 : 0;
  out->event_reason = out->event ? s.fs.lastEvent().reason : 0;

  // Pyro wie main.cpp: Kanal 1 sofort, Reserve nach der Verzögerung
  bool cont[PyroLogic::CHANNELS] = {false, false, false, false};
  cont[s.cfg.chute_channel] = true;
  cont[s.cfg.backup_channel] = true;
  const bool allowed = s.fs.pyroAllowed();
  s.pyro.update(t_ms, true, cont, allowed);
  if (allowed) {
    s.pyro.fire(s.cfg.chute_channel, t_ms);
    const uint32_t t_ref = s.fs.apogee_ms() ? s.fs.apogee_ms() : s.fs.phaseEntered_ms();
    if (t_ms - t_ref >= s.cfg.pyro_backup_delay_ms) s.pyro.fire(s.cfg.backup_channel, t_ms);
  }
  int fire = 0;
  for (int i = 0; i < PyroLogic::CHANNELS; ++i) if (s.pyro.fireOutput(i)) fire |= 1 << i;

  // Regler nur im BOOST, sonst Mitte
  TvcOutput o = (s.cfg.control_enabled && s.calibrated && s.fs.controlAllowed())
                    ? s.tvc.update(s.att.yawErrDeg(), s.att.pitchErrDeg(), w, dt)
                    : s.tvc.neutral();
  const float ys = quantize(o.yaw_servo_deg, s.cfg.quantize_servo);
  const float ps = quantize(o.pitch_servo_deg, s.cfg.quantize_servo);

  out->phase = int32_t(s.fs.phase());
  out->tilt_deg = s.att.tiltDeg();
  out->yaw_err_deg = s.att.yawErrDeg();
  out->pitch_err_deg = s.att.pitchErrDeg();
  out->roll_deg = s.att.rollDeg();
  out->q[0] = s.att.q().w; out->q[1] = s.att.q().x; out->q[2] = s.att.q().y; out->q[3] = s.att.q().z;
  out->alt_m = s.kal.z();
  out->vz_ms = s.kal.vz();
  out->yaw_moment_nm = o.yaw_moment_nm;
  out->pitch_moment_nm = o.pitch_moment_nm;
  out->servo_yaw_deg = ys;
  out->servo_pitch_deg = ps;
  out->tvc_yaw_deg = (ys - s.cfg.yaw_offset) / s.cfg.yaw_gain;
  out->tvc_pitch_deg = (ps - s.cfg.pitch_offset) / s.cfg.pitch_gain;
  out->yaw_saturated = o.yaw_saturated;
  out->pitch_saturated = o.pitch_saturated;
  out->pyro_fire_mask = fire;
  out->pyro_fired_mask = s.pyro.firedMask();
  out->accel_norm_filt = s.tvc.accelNormFilt();
}
