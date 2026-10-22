#include "Testrig.h"
#include <PWMServo.h>

namespace {
PWMServo esc;

// TSP E12 (simulation/data/E12_thrustcurve.csv, 85 Punkte auf 23 gekürzt), s / N
struct Pt { float t, f; };
constexpr Pt E12[] = {
  {0.000f, 0.00f}, {0.028f, 0.22f}, {0.182f, 1.51f}, {0.329f, 5.28f}, {0.432f, 12.82f}, {0.480f, 19.83f},
  {0.519f, 25.97f}, {0.535f, 28.34f}, {0.559f, 25.65f}, {0.615f, 21.23f}, {0.710f, 15.95f}, {0.876f, 13.36f},
  {1.039f, 11.21f}, {1.312f, 11.10f}, {1.550f, 11.31f}, {1.891f, 11.21f}, {2.078f, 10.99f}, {2.276f, 11.10f},
  {2.526f, 11.53f}, {2.732f, 11.53f}, {2.994f, 11.85f}, {3.180f, 11.96f}, {3.414f, 6.57f}, {3.545f, 0.00f},
};
constexpr int E12_N = sizeof(E12) / sizeof(E12[0]);
}  // namespace

float Testrig::e12Thrust(float t) {
  if (t <= 0.0f || t >= E12[E12_N - 1].t) return 0.0f;
  for (int i = 1; i < E12_N; ++i) {
    if (t < E12[i].t) {
      const float u = (t - E12[i - 1].t) / (E12[i].t - E12[i - 1].t);
      return E12[i - 1].f + u * (E12[i].f - E12[i - 1].f);
    }
  }
  return 0.0f;
}

void Testrig::begin() {
  if (!TESTRIG_MODE || PIN_THROTTLE < 0) return;
  // ESC-Puls 1000..2000 µs auf 0..180° abbilden, dann ist 0° = Minimalpuls
  esc.attach(PIN_THROTTLE, TESTRIG_ESC_MIN_US, TESTRIG_ESC_MAX_US);
  esc.write(0);
  attached_ = true;
  delay(2000);   // ESC armen (Minimalpuls)
}

void Testrig::writeThrust(float n) {
  thrust_n_ = constrain(n, 0.0f, TESTRIG_THRUST_MAX_N);
  if (!attached_) return;
  esc.write(180.0f * thrust_n_ / TESTRIG_THRUST_MAX_N);
}

void Testrig::startCurve(uint32_t now_ms) {
  if (!attached_) return;
  curve_running_ = true;
  t_curve_start_ = now_ms;
}

void Testrig::setThrust(float n) {
  curve_running_ = false;
  writeThrust(n);
}

void Testrig::stop() {
  curve_running_ = false;
  writeThrust(0.0f);
}

void Testrig::update(uint32_t now_ms) {
  if (!curve_running_) return;
  const float t = (now_ms - t_curve_start_) * 1e-3f;
  const float f = e12Thrust(t);
  writeThrust(f);
  if (t > E12[E12_N - 1].t) curve_running_ = false;
}
