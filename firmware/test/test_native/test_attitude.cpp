#include "minitest.h"
#include "Attitude.h"

static void rotation_about_x_matches_integration() {
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  const float dt = 0.01f;
  for (int i = 0; i < 100; ++i) a.update(Vec3(20.0f, 0, 0), dt);      // 1 s mit 20 °/s um x
  float tx, ty; a.tiltDeg(tx, ty);
  CHECK_NEAR(tx, 20.0, 0.05);
  CHECK_NEAR(ty, 0.0, 0.05);
  CHECK_NEAR(a.tiltTotalDeg(), 20.0, 0.05);
}

static void rotation_about_y_matches_integration() {
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 100; ++i) a.update(Vec3(0, -15.0f, 0), 0.01f);
  float tx, ty; a.tiltDeg(tx, ty);
  CHECK_NEAR(tx, 0.0, 0.05);
  CHECK_NEAR(ty, -15.0, 0.05);
}

static void roll_does_not_leak_into_tilt() {
  // Erst 5° um x kippen, dann 90° rollen: der Kippwinkel wandert in die andere Servoachse,
  // genau das, was Befund 3 an rot_deg += w*dt bemängelt (dort bliebe er auf x).
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 100; ++i) a.update(Vec3(5.0f, 0, 0), 0.01f);
  for (int i = 0; i < 100; ++i) a.update(Vec3(0, 0, 90.0f), 0.01f);
  float tx, ty; a.tiltDeg(tx, ty);
  CHECK_NEAR(a.tiltTotalDeg(), 5.0, 0.05);
  CHECK_NEAR(fabs(tx) + fabs(ty), 5.0, 0.1);
  CHECK_NEAR(fabs(ty), 5.0, 0.1);
  CHECK_NEAR(fabs(a.rollDeg()), 90.0, 0.1);
}

static void init_from_tilted_accel() {
  // Rakete steht 10° schief (Oben-Vektor im Körpersystem gekippt): Init liefert genau das
  Attitude a;
  const float t = 10.0f * 3.14159265f / 180.0f;
  a.initFromAccel(Vec3(0, sinf(t) * 9.81f, cosf(t) * 9.81f));
  float tx, ty; a.tiltDeg(tx, ty);
  CHECK_NEAR(tx, 10.0, 0.01);
  CHECK_NEAR(ty, 0.0, 0.01);
  CHECK(a.initialized);
  Vec3 an = a.accelNav(Vec3(0, sinf(t) * 9.81f, cosf(t) * 9.81f), 9.81f);
  CHECK_NEAR(norm(an), 0.0, 1e-4);
}

static void quaternion_stays_normalized() {
  Attitude a; a.initFromAccel(Vec3(0.3f, -0.2f, 9.7f));
  for (int i = 0; i < 100000; ++i) a.update(Vec3(300.0f, -200.0f, 50.0f), 0.001f);
  const float n = sqrtf(a.q.w * a.q.w + a.q.x * a.q.x + a.q.y * a.q.y + a.q.z * a.q.z);
  CHECK_NEAR(n, 1.0, 1e-5);
}

static void small_rate_first_order_branch() {
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 1000; ++i) a.update(Vec3(1e-4f, 0, 0), 0.001f);
  float tx, ty; a.tiltDeg(tx, ty);
  CHECK_NEAR(tx, 1e-4, 1e-5);
}

void run_tests_attitude() {
  RUN_TEST(rotation_about_x_matches_integration);
  RUN_TEST(rotation_about_y_matches_integration);
  RUN_TEST(roll_does_not_leak_into_tilt);
  RUN_TEST(init_from_tilted_accel);
  RUN_TEST(quaternion_stays_normalized);
  RUN_TEST(small_rate_first_order_branch);
}
