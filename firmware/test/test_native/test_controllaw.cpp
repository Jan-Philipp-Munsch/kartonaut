#include "minitest.h"
#include "ControlLaw.h"
#include "Config.h"
#include <stdio.h>
#include <string.h>

static PyGains gains(float ki) {
  return PyGains{PY_KP, ki, PY_KD, PY_ERROR_SCALE, PY_INT_LIMIT, MASS_KG, MOMENT_ARM_M, A_NORM_MIN,
                 SERVO_YAW_GAIN, SERVO_YAW_OFFSET, SERVO_PITCH_GAIN, SERVO_PITCH_OFFSET,
                 SERVO_YAW_MIN_DEG, SERVO_YAW_MAX_DEG, SERVO_PITCH_MIN_DEG, SERVO_PITCH_MAX_DEG};
}

static void zero_error_gives_center() {
  PyControlLaw law(gains(0));
  PyOutput o = law.update(0, 0, 0, 0, 0.01f, 9.81f);
  CHECK_NEAR(o.yaw_servo_deg, SERVO_YAW_OFFSET, 1e-4);
  CHECK_NEAR(o.pitch_servo_deg, SERVO_PITCH_OFFSET, 1e-4);
  CHECK_NEAR(o.yaw_tvc_deg, 0, 1e-5);
}

static void sign_and_window() {
  PyControlLaw law(gains(0));
  // 0,3° Kippen um x: Moment = Kp * (0,3 / -100) = -0,015 N m -> delta = asin(-0,015 / (l m g)) < 0
  PyOutput o = law.update(0.3f, 0, 0, 0, 0.01f, 9.81f);
  CHECK(o.yaw_moment_nm < 0);
  const float delta = asinf(-0.015f / (MOMENT_ARM_M * MASS_KG * 9.81f)) * 180.0f / 3.14159265f;
  CHECK_NEAR(o.yaw_servo_deg, delta * SERVO_YAW_GAIN + SERVO_YAW_OFFSET, 1e-3);
  // großer Fehler: Fenster greift
  o = law.update(60.0f, -60.0f, 0, 0, 0.01f, 9.81f);
  CHECK(o.yaw_servo_deg >= SERVO_YAW_MIN_DEG - 1e-4 && o.yaw_servo_deg <= SERVO_YAW_MAX_DEG + 1e-4);
  CHECK(o.pitch_servo_deg >= SERVO_PITCH_MIN_DEG - 1e-4 && o.pitch_servo_deg <= SERVO_PITCH_MAX_DEG + 1e-4);
  CHECK(o.yaw_servo_deg == SERVO_YAW_MIN_DEG || o.yaw_servo_deg == SERVO_YAW_MAX_DEG);
}

static void integrator_limited() {
  PyControlLaw law(gains(1.0f));
  for (int i = 0; i < 100000; ++i) law.update(50.0f, 0, 0, 0, 0.01f, 9.81f);
  CHECK_NEAR(law.integralX(), PY_INT_LIMIT, 1e-3);
  law.reset();
  CHECK_EQ((int)law.integralX(), 0);
}

static void roll_law_deadband_and_min_pwm() {
  RollControlLaw law(RollGains{ROLL_KP, ROLL_KI, ROLL_KD, ROLL_CMD_SCALE, ROLL_CMD_DEADBAND, ROLL_PWM_MIN, ROLL_PWM_MAX});
  RollOutput o = law.update(0.5f, 0, 0.01f);          // u = -0,6 -> cmd -0,003: Totband
  CHECK_EQ(o.dir, 0); CHECK_EQ(o.pwm, 0);
  o = law.update(10.0f, 0, 0.01f);                     // u = -12 -> cmd -0,06 -> Mindest-PWM
  CHECK_EQ(o.dir, -1); CHECK_EQ(o.pwm, 246);
  o = law.update(-400.0f, 0, 0.01f);                   // Sättigung
  CHECK_EQ(o.dir, 1); CHECK_EQ(o.pwm, ROLL_PWM_MAX);
}

// Software-in-the-loop: dieselben Eingänge wie tvcsim.controller.FirmwareController,
// Vektoren aus simulation/scripts/export_firmware_vectors.py
static void sil_against_tvcsim(const char* name, float ki) {
  char path[128];
  snprintf(path, sizeof path, "test/data/%s", name);
  FILE* f = fopen(path, "r");
  if (!f) { snprintf(path, sizeof path, "firmware/test/data/%s", name); f = fopen(path, "r"); }
  CHECK_MSG(f != nullptr, "%s fehlt (export_firmware_vectors.py)", name);
  if (!f) return;
  PyControlLaw law(gains(ki));
  char line[512];
  if (!fgets(line, sizeof line, f)) { fclose(f); return; }
  int rows = 0; double max_err = 0;
  while (fgets(line, sizeof line, f)) {
    float t, ax, ay, wx, wy, an, dt, ey, ep, em_y, em_p;
    if (sscanf(line, "%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f", &t, &dt, &ax, &ay, &wx, &wy, &an, &em_y, &em_p, &ey, &ep) != 11) continue;
    PyOutput o = law.update(ax, ay, wx, wy, dt, an);
    const double e = fmax(fabs(o.yaw_servo_deg - ey), fabs(o.pitch_servo_deg - ep));
    if (e > max_err) max_err = e;
    CHECK_MSG(fabs(o.yaw_moment_nm - em_y) < 1e-4 && fabs(o.pitch_moment_nm - em_p) < 1e-4,
              "t=%.2f Moment %g/%g statt %g/%g", t, o.yaw_moment_nm, o.pitch_moment_nm, em_y, em_p);
    rows++;
  }
  fclose(f);
  CHECK(rows > 300);
  CHECK_MSG(max_err < 0.01, "max. Abweichung Servo-Grad %g", max_err);
}

static void sil_ki0()  { sil_against_tvcsim("sil_controller_ki0.csv", 0.0f); }
static void sil_ki1()  { sil_against_tvcsim("sil_controller_ki1.csv", 1.0f); }

void run_tests_controllaw() {
  RUN_TEST(zero_error_gives_center);
  RUN_TEST(sign_and_window);
  RUN_TEST(integrator_limited);
  RUN_TEST(roll_law_deadband_and_min_pwm);
  RUN_TEST(sil_ki0);
  RUN_TEST(sil_ki1);
}
