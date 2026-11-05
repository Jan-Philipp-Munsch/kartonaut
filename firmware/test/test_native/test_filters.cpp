#include "minitest.h"
#include "Filters.h"

// Amplitude eines Sinus nach dem Filter (eingeschwungen)
static double gain(Biquad f, float hz, float fs) {
  double peak = 0;
  for (int i = 0; i < 4000; ++i) {
    const float y = f.update(sinf(2.f * 3.14159265f * hz * i / fs));
    if (i > 3000 && fabs(y) > peak) peak = fabs(y);
  }
  return peak;
}

static void notch_kills_its_line_and_passes_the_rest() {
  Biquad n; n.setNotch(80.f, 4.f, 250.f);
  CHECK(gain(n, 80.f, 250.f) < 0.02);
  CHECK_NEAR(gain(n, 5.f, 250.f), 1.0, 0.02);       // Regelband bleibt unberührt
}

static void lowpass_butterworth_minus3db() {
  Biquad l; l.setLowpass(50.f, 0.7071f, 250.f);
  CHECK_NEAR(gain(l, 50.f, 250.f), 0.7071, 0.02);
  CHECK_NEAR(gain(l, 2.f, 250.f), 1.0, 0.01);
}

static void off_means_passthrough() {
  Biquad p; p.setNotch(0.f, 4.f, 250.f);
  CHECK_NEAR(p.update(1.234f), 1.234, 1e-6);
}

static void lowpass_step_keeps_time_constant() {
  // Gleiche Zeitkonstante bei 100 und 250 Hz: nach 0,1 s fast gleicher Wert
  float a = 0, b = 0;
  for (int i = 0; i < 10; ++i) a = lowpassStep(a, 1.f, 0.1f, 0.01f);
  for (int i = 0; i < 25; ++i) b = lowpassStep(b, 1.f, 0.1f, 0.004f);
  CHECK_NEAR(a, b, 0.03);
}

void run_tests_filters() {
  RUN_TEST(notch_kills_its_line_and_passes_the_rest);
  RUN_TEST(lowpass_butterworth_minus3db);
  RUN_TEST(off_means_passthrough);
  RUN_TEST(lowpass_step_keeps_time_constant);
}
