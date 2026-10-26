#include "ThrottleLaw.h"
#include <math.h>

static constexpr float G = 9.81f;

ThrottleLaw::ThrottleLaw(const ThrottleLawParams& tp, const LandingParams& lp, const float* t_curve,
                         const float* f_curve, size_t n)
    : tp_(tp), lp_(lp), planner_(LandingParams{lp.mass_kg, lp.fuel_kg, lp.cd_a, lp.rho, lp.igniter_delay_s,
                                                lp.dt_ctrl_s, lp.min_speed_ms, tp.thrust_scale_plan},
                                  t_curve, f_curve, n),
      t_(t_curve), f_(f_curve), n_(n > 128 ? 128 : n) {
  impulse_[0] = 0.0f;
  for (size_t i = 1; i < n_; ++i) impulse_[i] = impulse_[i - 1] + 0.5f * (f_[i] + f_[i - 1]) * (t_[i] - t_[i - 1]);
  total_impulse_ = impulse_[n_ - 1] > 0.0f ? impulse_[n_ - 1] : 1.0f;
  for (size_t i = 0; i < n_; ++i) if (f_[i] > 0.0f && i + 1 < n_) burn_time_ = t_[i + 1];
  scale_est_ = tp_.thrust_scale_plan;
}

float ThrottleLaw::thrustAt(float t, float scale) const {
  if (t <= t_[0] || t >= t_[n_ - 1]) return 0.0f;
  size_t i = 1;
  while (i < n_ - 1 && t_[i] < t) ++i;
  const float w = (t - t_[i - 1]) / (t_[i] - t_[i - 1]);
  return scale * (f_[i - 1] + w * (f_[i] - f_[i - 1]));
}

float ThrottleLaw::burntFraction(float t) const {
  if (t <= t_[0]) return 0.0f;
  if (t >= t_[n_ - 1]) return 1.0f;
  size_t i = 1;
  while (i < n_ - 1 && t_[i] < t) ++i;
  const float w = (t - t_[i - 1]) / (t_[i] - t_[i - 1]);
  return (impulse_[i - 1] + w * (impulse_[i] - impulse_[i - 1])) / total_impulse_;
}

float ThrottleLaw::stopHeight(float h, float v, float t0, float scale, float f_now, float act_tau) const {
  // Port von tvcsim.throttle.stop_height (dt 5 ms)
  const float dt = 0.005f;
  if (v >= 0.0f) return h;
  float t = t0 < 0.0f ? 0.0f : t0;
  const float t_start = t;
  while (t < burn_time_ + 0.05f) {
    float T = thrustAt(t, scale);
    if (act_tau > 0.0f && f_now < 1.0f) T *= 1.0f - (1.0f - f_now) * expf(-(t - t_start) / act_tau);
    const float mass = lp_.mass_kg - lp_.fuel_kg * burntFraction(t);
    const float D = 0.5f * lp_.rho * lp_.cd_a * v * v * (v < 0.0f ? 1.0f : -1.0f);
    v += ((T + D) / mass - G) * dt;
    h += v * dt;
    t += dt;
    if (v >= 0.0f) return h;
    if (h <= 0.0f) return h;
  }
  return -1e9f;
}

bool ThrottleLaw::shouldIgnite(float h, float v) {
  if (v > -lp_.min_speed_ms) return false;
  float hp, vp;
  LandingPlanner::predict(h, v, lp_.igniter_delay_s, hp, vp);
  const float hs = stopHeight(hp, vp, 0.0f, tp_.thrust_scale_plan, 1.0f, 0.0f);
  last_hs_ = hs;
  if (hs <= -1e8f) return planner_.shouldIgnite(h, v);   // Bremsvermögen reicht nie: bestes Minimum
  return hs <= tp_.h_reserve_m;
}

void ThrottleLaw::track(float u) {
  const float f_cmd = factor(u, tp_.f_min);
  const float a = lp_.dt_ctrl_s / (tp_.act_tau_s > lp_.dt_ctrl_s ? tp_.act_tau_s : lp_.dt_ctrl_s);
  f_est_ += (f_cmd - f_est_) * a;
  last_u_ = u;
}

float ThrottleLaw::command(float t_since_ignition, float h, float v, float a_meas) {
  const float t_burn = t_since_ignition - lp_.igniter_delay_s;
  // Maßstab der wahren Kurve: nur in der Spitze, Pads sicher draußen
  if (t_burn <= tp_.throttle_after_s) {
    const float T_nom = thrustAt(t_burn, 1.0f);
    if (T_nom > 5.0f) {
      const float D0 = v < 0.0f ? 0.5f * lp_.rho * lp_.cd_a * v * v : 0.0f;
      float ratio = (lp_.mass_kg * a_meas - D0) / T_nom;
      ratio = ratio < 0.7f ? 0.7f : (ratio > 1.3f ? 1.3f : ratio);
      const float a = lp_.dt_ctrl_s / 0.15f;
      scale_est_ += (ratio - scale_est_) * (a > 1.0f ? 1.0f : a);
    }
  }
  const float T_avail = thrustAt(t_burn, scale_est_);
  const float D = v < 0.0f ? 0.5f * lp_.rho * lp_.cd_a * v * v : 0.0f;
  float u = 0.0f;
  if (T_avail <= 0.1f || v >= 0.0f) {
    u = 0.0f;
  } else if (t_burn < tp_.throttle_after_s) {
    u = 0.0f;                                            // Spitze: Pads draußen
  } else if (h > tp_.h_final_m) {
    float t_go = burn_time_ - t_burn - tp_.t_go_margin_s;
    if (t_go < tp_.t_go_min_s) t_go = tp_.t_go_min_s;
    last_tgo_ = t_go;
    const float zem = -(h + v * t_go - 0.5f * G * t_go * t_go);
    const float zev = -tp_.v_final_ms - (v - G * t_go);
    const float a_T = 6.0f * zem / (t_go * t_go) - 2.0f * zev / t_go;
    float T_req = lp_.mass_kg * a_T - D;
    if (T_req < 0.0f) T_req = 0.0f;
    float f = T_req / T_avail;
    if (f > 1.0f) f = 1.0f;
    if (f < tp_.f_min) f = tp_.f_min;
    u = tp_.f_min < 1.0f ? (1.0f - f) / (1.0f - tp_.f_min) : 0.0f;
  } else if (h <= tp_.h_cut_m) {
    u = 1.0f;                                            // Aufsetzen: Schubabbruch
  } else {
    const float a_cmd = G + tp_.kv * (-tp_.v_final_ms - v);
    float T_req = lp_.mass_kg * a_cmd - D;
    if (T_req < 0.0f) T_req = 0.0f;
    float f = T_req / T_avail;
    if (f > 1.0f) f = 1.0f;
    if (f < tp_.f_min) f = tp_.f_min;
    u = tp_.f_min < 1.0f ? (1.0f - f) / (1.0f - tp_.f_min) : 0.0f;
  }
  track(u);
  return u;
}
