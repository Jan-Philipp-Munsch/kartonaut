#pragma once
// ThrottleLaw.h – Landeregler mit Schubdrossel (Scout-F-Pads), Port von tvcsim/throttle.py
//
// Die Drossel: zwei Pads schwenken symmetrisch unter der Düse in den Abgasstrahl; Axialschub =
// Motorschub · f(u), u in [0, 1], f(u) = 1 − (1 − f_min) u (Kennlinie: Experiment E05).
//
// Ablauf im Landebrennen (LANDING_BURN):
//   1. Zündung mit Reserve: sobald ein Vollschub-Brennen mit dem schwächsten erwarteten Motor
//      (thrust_scale_plan, −10 %) höchstens h_reserve über dem Boden stoppen würde (shouldIgnite).
//   2. Schubspitze (t_burn < throttle_after_s): Pads draußen, dabei Schätzung des wahren
//      Kurvenmaßstabs aus |a| (T_mess = m |a| gegen die Nennkurve).
//   3. Schwanz der Kurve: zeitbasierte Führung. Die Restbrenndauer t_go ist die harte Grenze;
//      gefordert wird die Schubbeschleunigung, die Höhe und Sinkrate in t_go auf 0 bzw. −v_final
//      bringt (Zero-Effort-Miss/-Velocity): a_T = 6 ZEM / t_go² − 2 ZEV / t_go,
//      ZEM = −(h + v t_go − g t_go²/2), ZEV = −v_final − (v − g t_go); T_req = m a_T − D,
//      f = T_req / T_verfügbar in [f_min, 1]. Der Maßstab der Kurve ist der aus Schritt 2.
//   4. Unter h_final: Sinkrate auf −v_final halten; unter h_cut Pads ganz hinein (Schubabbruch),
//      sonst hebt der Schwanz der Kurve die aufgesetzte Rakete wieder ab.
// Kein Arduino: läuft in den nativen Tests (test_throttle.cpp gegen Python-Vektoren).
#include <stddef.h>
#include "LandingBurn.h"

struct ThrottleLawParams {
  float f_min;
  float h_reserve_m, t_go_margin_s, t_go_min_s, kv, v_final_ms, h_final_m, h_cut_m;
  float throttle_after_s, act_tau_s, thrust_scale_plan;
};

class ThrottleLaw {
public:
  ThrottleLaw(const ThrottleLawParams& tp, const LandingParams& lp, const float* t_curve, const float* f_curve, size_t n);

  static float factor(float u, float f_min) {
    u = u < 0.f ? 0.f : (u > 1.f ? 1.f : u);
    return 1.0f - (1.0f - f_min) * u;
  }

  // Höhe, in der ein Weiterbrennen mit vollem Schub zum Stehen käme (Kurve ab t0, Maßstab scale,
  // Pads kommen von f_now mit act_tau zurück). Negativ = Boden vorher; -1e9 = kein Stopp bis Brennschluss.
  float stopHeight(float h, float v, float t0, float scale, float f_now, float act_tau) const;

  // Zündentscheidung im freien Fall (jeden Takt): true = jetzt zünden
  bool shouldIgnite(float h, float v);

  // Drosselkommando u in [0, 1] im Landebrennen; a_meas = gemessene spezifische Kraft |a| (m/s²)
  float command(float t_since_ignition_s, float h, float v, float a_meas);

  void  reset() { f_est_ = 1.0f; scale_est_ = tp_.thrust_scale_plan; last_hs_ = 0; last_u_ = 0; last_tgo_ = 0; }
  float lastStopHeight() const { return last_hs_; }
  float lastTimeToGo() const { return last_tgo_; }
  float burnTime() const { return burn_time_; }
  float scaleEstimate() const { return scale_est_; }
  float lastCommand() const { return last_u_; }

private:
  float thrustAt(float t, float scale) const;
  float burntFraction(float t) const;
  void  track(float u);

  ThrottleLawParams tp_;
  LandingParams lp_;
  LandingPlanner planner_;     // Rückfall der Zündung, wenn das Bremsvermögen nie reicht
  const float* t_; const float* f_; size_t n_;
  float impulse_[128]; float total_impulse_ = 0; float burn_time_ = 0;
  float f_est_ = 1.0f, scale_est_ = 1.0f, last_hs_ = 0, last_u_ = 0, last_tgo_ = 0;
};
