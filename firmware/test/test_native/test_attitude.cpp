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

// Mahony am Boden: Schätzung steht aufrecht, die Rakete aber 8° schief -> die Stützung zieht nach
static void mahony_pulls_tilt_to_accel() {
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  MahonyAid aid;
  const float t = 8.0f * 3.14159265f / 180.0f;
  const Vec3 acc(0, sinf(t) * 9.81f, cosf(t) * 9.81f);
  // 100 s: der I-Anteil hält einen Teil des Anfangssprungs zunächst für einen Gyro-Fehler und baut ihn
  // mit der langsamen Polstelle (~20 s) ab; nach 10 s stünden noch 8,28°.
  for (int i = 0; i < 25000; ++i) a.update(aid.apply(a, Vec3(), acc, nullptr, true, 0.004f), 0.004f);
  CHECK_NEAR(a.tiltTotalDeg(), 8.0, 0.05);
}

// Ein Gyro-Restfehler von 0,5 °/s um x wird am Boden gelernt und im Flug (ohne Stützung) abgezogen
static void mahony_learns_gyro_bias() {
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  MahonyAid aid;
  const Vec3 up(0, 0, 9.81f), bias(0.5f, 0, 0);
  for (int i = 0; i < 25000; ++i) a.update(aid.apply(a, bias, up, nullptr, true, 0.004f), 0.004f);   // 100 s
  CHECK_NEAR(aid.integral_dps.x, -0.5, 0.02);
  Attitude f = a;
  for (int i = 0; i < 2500; ++i) f.update(aid.apply(f, bias, Vec3(0, 0, 30.f), nullptr, false, 0.004f), 0.004f);
  CHECK(f.tiltTotalDeg() < 0.2);            // 10 s Flug ohne Stützung: kaum Drift
}

// Das Magnetometer dreht nur den Kurs, nicht die Kippwinkel
static void mahony_mag_only_turns_heading() {
  Attitude a; a.initFromAccel(Vec3(0, 0, 9.81f));
  MahonyAid aid;
  // Feld mit Inklination 65°, Nord liegt 40° neben der Körper-x-Achse
  const float inc = 65.0f * 3.14159265f / 180.0f, hd = 40.0f * 3.14159265f / 180.0f;
  const Vec3 m(cosf(inc) * cosf(hd), -cosf(inc) * sinf(hd), -sinf(inc));
  for (int i = 0; i < 25000; ++i) a.update(aid.apply(a, Vec3(), Vec3(0, 0, 9.81f), &m, true, 0.004f), 0.004f);   // 100 s, s. o.
  CHECK(a.tiltTotalDeg() < 0.05);
  CHECK_NEAR(fabs(a.rollDeg()), 40.0, 0.5);
}

void run_tests_attitude() {
  RUN_TEST(mahony_pulls_tilt_to_accel);
  RUN_TEST(mahony_learns_gyro_bias);
  RUN_TEST(mahony_mag_only_turns_heading);
  RUN_TEST(rotation_about_x_matches_integration);
  RUN_TEST(rotation_about_y_matches_integration);
  RUN_TEST(roll_does_not_leak_into_tilt);
  RUN_TEST(init_from_tilted_accel);
  RUN_TEST(quaternion_stays_normalized);
  RUN_TEST(small_rate_first_order_branch);
}
