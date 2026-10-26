#pragma once
// LandingBurn.h – Zündentscheidung für das Landebrennen mit dem zweiten Feststoffmotor
// (Port von simulation/tvcsim/landing.py, LandingPlanner; Jan, 23.10.2026)
//
// Ein Feststoffmotor lässt sich weder drosseln noch abschalten; die einzige Stellgröße der
// Landung ist der Zündzeitpunkt. Jeden Takt im freien Fall werden die *Aufsetzkosten* J für
// eine Zündung jetzt und eine Zündung einen Takt später berechnet: J ist die größte
// Aufsetzgeschwindigkeit einer 1D-Simulation des ganzen Brennens mit Bodenkontakt (am Boden
// bleibt die Rakete liegen, solange der Schub nicht trägt, sonst hebt sie wieder ab). Im
// freien Fall sinkt J zuerst und steigt dann; gezündet wird im Minimum (J_jetzt <= J_später).
// Beide Zustände sind um den Zündverzug des Anzünders vorausgesagt.
// Die Schubkurve kommt aus ThrustCurveE12.h (Export aus der Simulation). Rechenaufwand je
// Aufruf: zwei 1D-Läufe mit 5 ms Schritt über höchstens 8 s, also unter 4000 Schritte.
// Kein Arduino: läuft in den nativen Tests (test_landing.cpp gegen landing_cost_E12.csv).
#include <stddef.h>

struct LandingParams {
  float mass_kg;          // Masse bei der Landung mit vollem zweitem Motor
  float fuel_kg;          // Treibstoff des Landemotors (Abbrand proportional zum Impuls)
  float cd_a;             // Widerstandsfläche Cd·A [m²], 0 = ohne Luftwiderstand
  float rho;              // Luftdichte [kg/m³]
  float igniter_delay_s;  // Zündverzug Anzünder -> Schub
  float dt_ctrl_s;        // Regeltakt (Vorausschau für "einen Takt später")
  float min_speed_ms;     // unter dieser Sinkrate wird nicht gezündet
  float thrust_scale;     // angenommene Schubtoleranz der Planung (1 = Nennkurve)
};

class LandingPlanner {
public:
  static constexpr float G = 9.81f;

  LandingPlanner(const LandingParams& p, const float* t_curve, const float* f_curve, size_t n);

  // Aufsetzkosten für eine Zündung im Zustand (h, v): größte Aufsetzgeschwindigkeit [m/s]
  float cost(float h_m, float v_ms) const;

  // Jeden Takt im freien Fall aufrufen; true = jetzt zünden
  bool shouldIgnite(float h_m, float v_ms);

  float lastCost() const { return last_J_; }
  float lastCostNext() const { return last_J_next_; }

  // Zustand nach tau Sekunden freiem Fall (ohne Luftwiderstand)
  static void predict(float h, float v, float tau, float& h_out, float& v_out) {
    h_out = h + v * tau - 0.5f * G * tau * tau;
    v_out = v - G * tau;
  }

private:
  float thrustAt(float t) const;
  float burntFraction(float t) const;

  LandingParams p_;
  const float* t_;
  const float* f_;
  size_t n_;
  float impulse_[128];     // Impuls bis zu jedem Stützpunkt
  float total_impulse_ = 0;
  float burn_time_ = 0;
  float last_J_ = -1, last_J_next_ = -1;
};
