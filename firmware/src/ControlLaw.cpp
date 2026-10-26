#include "ControlLaw.h"
#include <math.h>

static inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

PyOutput PyControlLaw::update(float ax_deg, float ay_deg, float wx_dps, float wy_dps, float dt_s, float a_norm) {
  int_x_ = clampf(int_x_ + ax_deg * dt_s, -g_.int_limit, g_.int_limit);
  int_y_ = clampf(int_y_ + ay_deg * dt_s, -g_.int_limit, g_.int_limit);
  const float s = g_.error_scale;

  PyOutput o;
  o.yaw_moment_nm   = g_.kp * (ax_deg / s) + g_.ki * (int_x_ / s) + g_.kd * (wx_dps / s);
  o.pitch_moment_nm = g_.kp * (ay_deg / s) + g_.ki * (int_y_ / s) + g_.kd * (wy_dps / s);

  const float denom = g_.arm_m * g_.mass_kg * (a_norm > g_.a_norm_min ? a_norm : g_.a_norm_min);
  const float yaw_rad   = asinf(clampf(o.yaw_moment_nm / denom, -0.99f, 0.99f));
  const float pitch_rad = asinf(clampf(o.pitch_moment_nm / denom, -0.99f, 0.99f));
  constexpr float RAD2DEG = 180.0f / 3.14159265358979f;

  float yaw_servo   = yaw_rad * RAD2DEG * g_.yaw_gain + g_.yaw_offset;
  float pitch_servo = pitch_rad * RAD2DEG * g_.pitch_gain + g_.pitch_offset;
  yaw_servo   = clampf(yaw_servo, g_.yaw_min, g_.yaw_max);
  pitch_servo = clampf(pitch_servo, g_.pitch_min, g_.pitch_max);
  o.yaw_servo_deg   = clampf(yaw_servo, 0.f, 180.f);
  o.pitch_servo_deg = clampf(pitch_servo, 0.f, 180.f);
  o.yaw_tvc_deg   = (o.yaw_servo_deg - g_.yaw_offset) / g_.yaw_gain;
  o.pitch_tvc_deg = (o.pitch_servo_deg - g_.pitch_offset) / g_.pitch_gain;
  return o;
}

RollOutput RollControlLaw::update(float roll_deg, float roll_rate_dps, float dt_s) {
  RollOutput o;
  o.rate_dps  = roll_rate_dps;
  o.angle_deg = roll_deg;
  o.corr_deg  = -roll_deg;                 // Soll 0°
  const float u = g_.kp * o.corr_deg + g_.ki * int_ + g_.kd * (-o.rate_dps);
  float cmd = clampf(u / g_.cmd_scale, -1.0f, 1.0f);
  if (fabsf(cmd) < g_.deadband) cmd = 0.0f;
  if (g_.ki != 0.0f && cmd != 0.0f) int_ += o.corr_deg * dt_s;   // einfaches Anti-Windup
  o.cmd_norm = cmd;
  o.dir = (cmd > 0.0f) ? +1 : (cmd < 0.0f ? -1 : 0);
  float duty = fabsf(cmd);
  const float duty_min = (float)g_.pwm_min / (float)g_.pwm_max;
  if (duty > 0.0f && duty < duty_min) duty = duty_min;
  o.pwm = (int)(duty * g_.pwm_max + 0.5f);
  return o;
}
