#include "TvcController.h"

namespace {
constexpr float RAD2DEG = 57.29577951f;
inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
}

void TvcController::reset() {
  i_yaw_ = i_pitch_ = 0.0f;
  a_norm_filt_ = 9.81f;
}

void TvcController::updateAccelNorm(float a_norm_ms2) {
  a_norm_filt_ += (a_norm_ms2 - a_norm_filt_) * p_.a_norm_alpha;
}

float TvcController::yawServoForTvc(float tvc_deg) const {
  return clampf(tvc_deg * p_.yaw_gain + p_.yaw_offset, p_.yaw_min, p_.yaw_max);
}

float TvcController::pitchServoForTvc(float tvc_deg) const {
  return clampf(tvc_deg * p_.pitch_gain + p_.pitch_offset, p_.pitch_min, p_.pitch_max);
}

TvcOutput TvcController::neutral() const {
  TvcOutput o;
  o.yaw_servo_deg   = yawServoForTvc(0.0f);
  o.pitch_servo_deg = pitchServoForTvc(0.0f);
  return o;
}

TvcOutput TvcController::update(float yaw_err_deg, float pitch_err_deg, const Vec3& omega_dps, float dt_s) {
  TvcOutput o;
  const float S = p_.error_scale;

  // Integratoren mit Begrenzung (Anti-Windup)
  i_yaw_   = clampf(i_yaw_   + yaw_err_deg   * dt_s, -p_.i_max_deg_s, p_.i_max_deg_s);
  i_pitch_ = clampf(i_pitch_ + pitch_err_deg * dt_s, -p_.i_max_deg_s, p_.i_max_deg_s);

  o.yaw_moment_nm   = p_.kp * (yaw_err_deg / S)   + p_.ki * (i_yaw_ / S)   + p_.kd * (omega_dps.x / S);
  o.pitch_moment_nm = p_.kp * (pitch_err_deg / S) + p_.ki * (i_pitch_ / S) + p_.kd * (omega_dps.y / S);

  // Moment -> Auslenkung des Schubvektors
  const float a = a_norm_filt_ > p_.a_norm_min ? a_norm_filt_ : p_.a_norm_min;
  const float denom = p_.moment_arm_m * p_.mass_kg * a;
  const float yaw_tvc   = asinf(clampf(o.yaw_moment_nm   / denom, -p_.asin_clamp, p_.asin_clamp)) * RAD2DEG;
  const float pitch_tvc = asinf(clampf(o.pitch_moment_nm / denom, -p_.asin_clamp, p_.asin_clamp)) * RAD2DEG;

  o.yaw_tvc_deg   = clampf(yaw_tvc,   -p_.tvc_max_deg, p_.tvc_max_deg);
  o.pitch_tvc_deg = clampf(pitch_tvc, -p_.tvc_max_deg, p_.tvc_max_deg);
  o.yaw_saturated   = o.yaw_tvc_deg   != yaw_tvc;
  o.pitch_saturated = o.pitch_tvc_deg != pitch_tvc;

  // Linearisierte Kardangeometrie und mechanisches Fenster
  const float ys = o.yaw_tvc_deg   * p_.yaw_gain   + p_.yaw_offset;
  const float ps = o.pitch_tvc_deg * p_.pitch_gain + p_.pitch_offset;
  o.yaw_servo_deg   = clampf(ys, p_.yaw_min,   p_.yaw_max);
  o.pitch_servo_deg = clampf(ps, p_.pitch_min, p_.pitch_max);
  if (o.yaw_servo_deg   != ys) o.yaw_saturated   = true;
  if (o.pitch_servo_deg != ps) o.pitch_saturated = true;

  // Wenn die Stellgröße am Anschlag ist, den Integrator nicht weiter aufladen
  if (o.yaw_saturated)   i_yaw_   -= yaw_err_deg   * dt_s;
  if (o.pitch_saturated) i_pitch_ -= pitch_err_deg * dt_s;
  return o;
}
