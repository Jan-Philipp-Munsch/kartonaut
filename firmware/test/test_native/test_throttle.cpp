#include "minitest.h"
#include "ThrottleLaw.h"
#include "ThrustCurveE12.h"
#include "Config.h"
#include <stdio.h>
#include <string.h>

static ThrottleLawParams tparams(float f_min) {
  return ThrottleLawParams{f_min, 3.0f, 0.15f, 0.3f, 3.0f, 0.5f, 0.8f, 0.25f, 0.8f, 0.12f, 0.9f};
}
static LandingParams lparams(float m) { return LandingParams{m, 0.028f, 0.003f, 1.2f, 0.10f, 0.01f, 2.0f, 0.9f}; }
static ThrottleLaw law(float m, float f_min) {
  return ThrottleLaw(tparams(f_min), lparams(m), thrustcurve::E12_T_S, thrustcurve::E12_F_N, thrustcurve::E12_N);
}

static void factor_linear() {
  CHECK_NEAR(ThrottleLaw::factor(0.0f, 0.5f), 1.0, 1e-6);
  CHECK_NEAR(ThrottleLaw::factor(1.0f, 0.5f), 0.5, 1e-6);
  CHECK_NEAR(ThrottleLaw::factor(0.5f, 0.3f), 0.65, 1e-6);
  CHECK_NEAR(ThrottleLaw::factor(2.0f, 0.5f), 0.5, 1e-6);
}

// Stopphöhen und Kommandofolge gegen tvcsim.throttle (export_landing_firmware.py)
static void matches_python_vectors() {
  FILE* f = fopen("test/data/throttle_vectors.csv", "r");
  if (!f) f = fopen("firmware/test/data/throttle_vectors.csv", "r");
  CHECK_MSG(f != nullptr, "throttle_vectors.csv fehlt");
  if (!f) return;
  char line[256];
  if (!fgets(line, sizeof line, f)) { fclose(f); return; }
  ThrottleLaw cmd_law = law(0.6f, 0.5f);
  int n_stop = 0, n_cmd = 0, n_bad = 0; double err_stop = 0, err_cmd = 0, err_scale = 0;
  while (fgets(line, sizeof line, f)) {
    char kind[8]; float m, h, v, t0, x, u, val;
    if (sscanf(line, "%7[^,],%f,%f,%f,%f,%f,%f,%f", kind, &m, &h, &v, &t0, &x, &u, &val) != 8) continue;
    if (strcmp(kind, "stop") == 0) {
      ThrottleLaw l = law(m, 0.5f);
      const float hs = l.stopHeight(h, v, t0, 0.9f, x, 0.12f);
      if (val < -1e8f) {                      // Python: -inf = kein Stopp bis Brennschluss
        CHECK_MSG(hs <= -1e8f, "stop m=%.1f h=%.0f v=%.0f: Stopp %.3f, Python keiner", m, h, v, hs);
      } else {
        const double e = fabs(hs - val);
        if (e > err_stop) err_stop = e;
        CHECK_MSG(e < 0.15, "stop m=%.1f h=%.0f v=%.0f t0=%.1f f=%.1f: %.3f statt %.3f", m, h, v, t0, x, hs, val);
      }
      n_stop++;
    } else {
      const float uc = cmd_law.command(t0, h, v, x);
      const double e = fabs(uc - u);
      if (e > 0.05) n_bad++;
      if (e > err_cmd) err_cmd = e;
      const double es = fabs(cmd_law.scaleEstimate() - val);
      if (es > err_scale) err_scale = es;
      n_cmd++;
    }
  }
  fclose(f);
  CHECK_EQ(n_stop, 8);
  CHECK(n_cmd > 200);
  // Einzelne Takte an der Phasengrenze (t_burn = 0,8 s, float gegen double) dürfen abweichen
  CHECK_MSG(n_bad <= 2, "%d Takte mit Abweichung > 0,05 im Drosselkommando (max %g)", n_bad, err_cmd);
  CHECK_MSG(err_scale < 0.01, "max. Abweichung Schubschaetzung %g", err_scale);
}

static void ignition_reserve_at_06kg() {
  // 0,6 kg aus dem E12-Gipfel (88 m): Zündung mit Reserve höher als das Kostenminimum (44 m)
  ThrottleLaw l = law(0.6f, 0.5f);
  float h = 88.3f, v = 0.0f, h_ign = -1;
  for (int k = 0; k < 3000 && h > 0; ++k) {
    v += (-9.81f + 0.5f * 1.2f * 0.003f * v * v / 0.6f) * 0.01f;
    h += v * 0.01f;
    if (l.shouldIgnite(h, v)) { h_ign = h; break; }
  }
  CHECK(h_ign > 48 && h_ign < 54);
}

static void command_phases() {
  ThrottleLaw l = law(0.6f, 0.5f);
  CHECK_NEAR(l.command(0.05f, 40.0f, -25.0f, 9.0f), 0.0, 1e-6);          // vor dem Schub
  CHECK_NEAR(l.command(0.6f, 30.0f, -20.0f, 40.0f), 0.0, 1e-6);          // Spitze: Pads draußen
  CHECK(l.scaleEstimate() > 0.9f);                                         // |a| 40 m/s² bei 0,6 kg > Nennkurve
  const float u_high = l.command(1.6f, 30.0f, -3.0f, 15.0f);              // hoch und langsam: drosseln
  CHECK(u_high > 0.5f);
  CHECK_NEAR(l.command(1.6f, 4.0f, -15.0f, 15.0f), 0.0, 1e-6);           // tief und schnell: voller Schub
  CHECK_NEAR(l.command(2.0f, 0.1f, -0.6f, 15.0f), 1.0, 1e-6);            // Aufsetzen: Schubabbruch
  l.reset();
  CHECK_NEAR(l.scaleEstimate(), 0.9, 1e-6);
}

void run_tests_throttle() {
  RUN_TEST(factor_linear);
  RUN_TEST(matches_python_vectors);
  RUN_TEST(ignition_reserve_at_06kg);
  RUN_TEST(command_phases);
}
