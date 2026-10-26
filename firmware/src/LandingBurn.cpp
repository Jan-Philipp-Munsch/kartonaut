#include "LandingBurn.h"
#include <math.h>

LandingPlanner::LandingPlanner(const LandingParams& p, const float* t_curve, const float* f_curve, size_t n)
    : p_(p), t_(t_curve), f_(f_curve), n_(n > 128 ? 128 : n) {
  impulse_[0] = 0.0f;
  for (size_t i = 1; i < n_; ++i)
    impulse_[i] = impulse_[i - 1] + 0.5f * (f_[i] + f_[i - 1]) * (t_[i] - t_[i - 1]);
  total_impulse_ = impulse_[n_ - 1] > 0.0f ? impulse_[n_ - 1] : 1.0f;
  burn_time_ = 0.0f;
  for (size_t i = 0; i < n_; ++i)
    if (f_[i] > 0.0f && i + 1 < n_) burn_time_ = t_[i + 1];
}

float LandingPlanner::thrustAt(float t) const {
  if (t <= t_[0] || t >= t_[n_ - 1]) return 0.0f;
  size_t i = 1;
  while (i < n_ - 1 && t_[i] < t) ++i;
  const float w = (t - t_[i - 1]) / (t_[i] - t_[i - 1]);
  return p_.thrust_scale * (f_[i - 1] + w * (f_[i] - f_[i - 1]));
}

float LandingPlanner::burntFraction(float t) const {
  if (t <= t_[0]) return 0.0f;
  if (t >= t_[n_ - 1]) return 1.0f;
  size_t i = 1;
  while (i < n_ - 1 && t_[i] < t) ++i;
  const float w = (t - t_[i - 1]) / (t_[i] - t_[i - 1]);
  return (impulse_[i - 1] + w * (impulse_[i] - impulse_[i - 1])) / total_impulse_;
}

float LandingPlanner::cost(float h, float v) const {
  // Port von tvcsim.landing.impact_cost (dt 5 ms, t_max 8 s), gleiche Reihenfolge der Schritte
  const float dt = 0.005f, t_max = 8.0f;
  float t = 0.0f, worst = 0.0f;
  bool on_ground = h <= 0.0f;
  while (t < t_max) {
    const float T = thrustAt(t);
    const float mass = p_.mass_kg - p_.fuel_kg * burntFraction(t);
    if (on_ground) {
      if (T / mass - G > 0.0f) { on_ground = false; v = 0.0f; }
      else if (t > burn_time_) break;
      else { t += dt; continue; }
    }
    const float D = 0.5f * p_.rho * p_.cd_a * v * v * (v < 0.0f ? 1.0f : -1.0f);
    v += ((T + D) / mass - G) * dt;
    h += v * dt;
    t += dt;
    if (h <= 0.0f) {
      if (-v > worst) worst = -v;
      h = 0.0f; v = 0.0f; on_ground = true;
      if (t > burn_time_) break;
    }
  }
  if (!on_ground) {
    // noch in der Luft: freier Fall bis zum Boden
    if (p_.cd_a <= 0.0f) {
      const float v_td = -sqrtf(fmaxf(0.0f, v * v + 2.0f * G * h));
      if (-v_td > worst) worst = -v_td;
    } else {
      while (h > 0.0f) {
        v += (-G + 0.5f * p_.rho * p_.cd_a * v * v / p_.mass_kg * (v < 0.0f ? 1.0f : -1.0f)) * dt;
        h += v * dt;
      }
      if (-v > worst) worst = -v;
    }
  }
  return worst;
}

bool LandingPlanner::shouldIgnite(float h, float v) {
  if (v > -p_.min_speed_ms) return false;
  float h_now, v_now, h_next, v_next;
  predict(h, v, p_.igniter_delay_s, h_now, v_now);
  predict(h, v, p_.igniter_delay_s + p_.dt_ctrl_s, h_next, v_next);
  if (h_now <= 0.0f) return true;
  last_J_ = cost(h_now, v_now);
  last_J_next_ = cost(h_next, v_next);
  return last_J_ <= last_J_next_;
}
