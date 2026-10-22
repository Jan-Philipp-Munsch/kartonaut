// test_flightcore – Tests des Flugkerns ohne Hardware (Plan 22.10.2026 §2 B6)
//
//   pio test -e native                 (PlatformIO, echtes Unity, so in der CI)
//   firmware/tools/run_native_tests.sh (g++ mit Unity-Shim, ohne PlatformIO)
//
// Geprüft werden CRC und Rahmen, die Gyro-Quaternion samt Oben-Vektor, der
// Flugzustandsautomat mit synthetischen Eingaben und mit einem simulierten
// Erstflug aus tvcsim (test/data/flight_e12.csv), die Pyro-Regeln und der
// TVC-Regler.
#include <unity.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>

#include "Attitude.h"
#include "Crc16.h"
#include "FlightState.h"
#include "KartonautProtocol.h"
#include "Pyro.h"
#include "Telemetry.h"
#include "TvcController.h"

#ifndef FLIGHTCORE_TEST_DATA_DIR
#define FLIGHTCORE_TEST_DATA_DIR "test/data"
#endif

void setUp() {}
void tearDown() {}

// ===================== CRC und Rahmen =====================

static void test_crc16_check_value() {
  const char* s = "123456789";
  TEST_ASSERT_EQUAL_HEX16(0x29B1, crc16_ccitt(reinterpret_cast<const uint8_t*>(s), 9));
}

static void test_frame_roundtrip() {
  KnTelemetry t{};
  t.t_ms = 123456; t.phase = KN_PHASE_BOOST; t.flags = KN_FLAG_ARMED | KN_FLAG_CTRL_ACTIVE;
  t.alt_dm = 123; t.vz_cms = -456; t.q[0] = 32767; t.q[1] = -100; t.q[2] = 7; t.q[3] = 0;
  t.tvc_yaw_d5 = -12; t.tvc_pitch_d5 = 30; t.vbat1_20mV = 205; t.vbat2_40mV = 190;
  TEST_ASSERT_EQUAL(22, (int)sizeof(KnTelemetry));
  TEST_ASSERT_EQUAL(13, (int)sizeof(KnGps));
  TEST_ASSERT_EQUAL(8,  (int)sizeof(KnEvent));
  TEST_ASSERT_EQUAL(4,  (int)sizeof(KnCommand));
  TEST_ASSERT_EQUAL(3,  (int)sizeof(KnAck));

  uint8_t buf[64];
  const size_t n = kn_encode(KN_MSG_TELEMETRY, &t, sizeof t, buf, sizeof buf);
  TEST_ASSERT_EQUAL(sizeof(KnTelemetry) + KN_FRAME_OVERHEAD, n);
  TEST_ASSERT_EQUAL_HEX16(0xA55A, (buf[0] << 8) | buf[1]);

  KnParser p;
  bool done = false;
  for (size_t i = 0; i < n; ++i) done = p.feed(buf[i]) || done;
  TEST_ASSERT_TRUE(done);
  TEST_ASSERT_EQUAL(KN_MSG_TELEMETRY, p.type());
  KnTelemetry r{};
  TEST_ASSERT_TRUE(p.get(r));
  TEST_ASSERT_EQUAL_MEMORY(&t, &r, sizeof t);
  TEST_ASSERT_EQUAL(1, (int)p.framesOk());
}

static void test_frame_rejects_corruption_and_resyncs() {
  KnCommand c{KN_CMD_ABORT, 7, 0};
  uint8_t buf[32];
  const size_t n = kn_encode(KN_MSG_CMD, &c, sizeof c, buf, sizeof buf);
  KnParser p;
  // Müll davor, dann ein kaputtes Byte in der Nutzlast, dann der gute Rahmen
  const uint8_t junk[] = {0x00, 0xA5, 0x12, 0xA5, 0xA5};
  for (uint8_t b : junk) TEST_ASSERT_FALSE(p.feed(b));
  for (size_t i = 0; i < n; ++i) {
    const uint8_t b = (i == 5) ? uint8_t(buf[i] ^ 0x40) : buf[i];
    TEST_ASSERT_FALSE(p.feed(b));
  }
  TEST_ASSERT_EQUAL(1, (int)p.crcErrors());
  bool done = false;
  for (size_t i = 0; i < n; ++i) done = p.feed(buf[i]) || done;
  TEST_ASSERT_TRUE(done);
  KnCommand r{};
  TEST_ASSERT_TRUE(p.get(r));
  TEST_ASSERT_EQUAL(KN_CMD_ABORT, r.cmd);
  TEST_ASSERT_EQUAL(7, r.seq);
  // zu lange Nutzlast wird nicht gebaut
  uint8_t big[KN_MAX_PAYLOAD + 1] = {0};
  TEST_ASSERT_EQUAL(0, (int)kn_encode(KN_MSG_CMD, big, sizeof big, buf, sizeof buf));
}

// ===================== Quaternion =====================

static void test_attitude_init_from_accel() {
  Attitude a;
  const float th = 10.0f * Attitude::DEG2RAD;
  // Rakete um +10° um die Körper-x-Achse gekippt: der Sensor misst g·(0, sin, cos)
  TEST_ASSERT_TRUE(a.initFromAccel(Vec3(0, 9.81f * sinf(th), 9.81f * cosf(th))));
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 10.0f, a.tiltDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 10.0f, a.yawErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, a.pitchErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, a.rollDeg());
  // Beschleunigung im Navigationssystem ohne g ist in Ruhe null
  const Vec3 an = a.accelNav(Vec3(0, 9.81f * sinf(th), 9.81f * cosf(th)), 9.81f);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 0.0f, norm(an));
  // zu kleiner Vektor wird abgelehnt
  TEST_ASSERT_FALSE(a.initFromAccel(Vec3(0, 0, 0.1f)));
  // senkrecht: Einheitsquaternion
  Attitude b;
  TEST_ASSERT_TRUE(b.initFromAccel(Vec3(0, 0, 9.81f)));
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, 1.0f, b.q().w);
}

static void test_attitude_integrates_like_rot_deg_for_pure_axes() {
  Attitude a;
  a.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 100; ++i) a.integrateDps(Vec3(30.0f, 0, 0), 0.01f);   // 30°/s, 1 s
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 30.0f, a.yawErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 0.0f, a.pitchErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 30.0f, a.tiltDeg());

  Attitude b;
  b.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 100; ++i) b.integrateDps(Vec3(0, -20.0f, 0), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(0.05f, -20.0f, b.pitchErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 0.0f, b.yawErrDeg());

  Attitude c;
  c.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 100; ++i) c.integrateDps(Vec3(0, 0, 45.0f), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 45.0f, c.rollDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.05f, 0.0f, c.tiltDeg());
}

static void test_attitude_error_follows_body_axis_after_roll() {
  // Erst 15° um x kippen, dann 90° rollen: die Neigung liegt jetzt in der
  // Körper-y-Achse (Pitch-Servo), was rot_deg += ω·dt nie hergibt (Befund 3).
  Attitude a;
  a.initFromAccel(Vec3(0, 0, 9.81f));
  for (int i = 0; i < 100; ++i) a.integrateDps(Vec3(15.0f, 0, 0), 0.01f);
  for (int i = 0; i < 100; ++i) a.integrateDps(Vec3(0, 0, 90.0f), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 15.0f, a.tiltDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, a.yawErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 15.0f, fabsf(a.pitchErrDeg()));
  // und zurückrollen bringt den Fehler in die x-Achse zurück
  for (int i = 0; i < 100; ++i) a.integrateDps(Vec3(0, 0, -90.0f), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 15.0f, a.yawErrDeg());
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 0.0f, a.pitchErrDeg());
}

static void test_attitude_norm_stays_one() {
  Attitude a;
  a.initFromAccel(Vec3(0.3f, -0.2f, 9.7f));
  uint32_t s = 12345;
  for (int i = 0; i < 100000; ++i) {
    s = s * 1664525u + 1013904223u;
    const float wx = float(int(s >> 16) % 400 - 200);
    s = s * 1664525u + 1013904223u;
    const float wy = float(int(s >> 16) % 400 - 200);
    s = s * 1664525u + 1013904223u;
    const float wz = float(int(s >> 16) % 400 - 200);
    a.integrateDps(Vec3(wx, wy, wz), 0.01f);
  }
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, sqrtf(a.q().normSq()));
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, 1.0f, norm(a.upBody()));
}

// ===================== Flugzustandsautomat =====================

static FlightInputs padInputs(uint32_t t) {
  FlightInputs in;
  in.t_ms = t; in.accel_z_g = 1.0f; in.accel_mag_g = 1.0f; in.gyro_mag_dps = 0.1f;
  in.armed = true; in.continuity = true; in.calibrated = true;
  return in;
}

static void test_flightstate_synthetic_sequence() {
  FlightStateConfig cfg;
  FlightState fs(cfg);
  TEST_ASSERT_EQUAL((int)FlightPhase::SAFE, (int)fs.phase());

  // ohne ARM kein PAD_READY
  uint32_t t = 0;
  for (; t < 3000; t += 10) { FlightInputs in = padInputs(t); in.armed = false; fs.update(in); }
  TEST_ASSERT_EQUAL((int)FlightPhase::SAFE, (int)fs.phase());
  // mit allem: nach 1 s gehalten
  bool ev = false;
  for (; t < 6000 && !ev; t += 10) ev = fs.update(padInputs(t));
  TEST_ASSERT_TRUE(ev);
  TEST_ASSERT_EQUAL((int)FlightPhase::PAD_READY, (int)fs.phase());
  TEST_ASSERT_EQUAL(KN_REASON_READY, fs.lastEvent().reason);

  // kurzer Stoß von 3 g für 20 ms darf nicht starten
  for (int i = 0; i < 2; ++i, t += 10) { FlightInputs in = padInputs(t); in.accel_z_g = 3.0f; fs.update(in); }
  for (int i = 0; i < 20; ++i, t += 10) fs.update(padInputs(t));
  TEST_ASSERT_EQUAL((int)FlightPhase::PAD_READY, (int)fs.phase());

  // 3 g für 60 ms: Start
  ev = false;
  for (int i = 0; i < 8 && !ev; ++i, t += 10) { FlightInputs in = padInputs(t); in.accel_z_g = 3.0f; ev = fs.update(in); }
  TEST_ASSERT_TRUE(ev);
  TEST_ASSERT_EQUAL((int)FlightPhase::BOOST, (int)fs.phase());
  TEST_ASSERT_TRUE(fs.controlAllowed());
  TEST_ASSERT_FALSE(fs.pyroAllowed());
  const uint32_t t_lift = fs.liftoff_ms();
  TEST_ASSERT_TRUE(t_lift > 0 && t_lift < t);

  // Brennschluss: 0,1 g für 100 ms
  ev = false;
  for (int i = 0; i < 20 && !ev; ++i, t += 10) {
    FlightInputs in = padInputs(t); in.accel_z_g = 0.1f; in.accel_mag_g = 0.1f; in.vz_ms = 30; in.alt_m = 40; in.baro_alt_m = 40;
    ev = fs.update(in);
  }
  TEST_ASSERT_TRUE(ev);
  TEST_ASSERT_EQUAL((int)FlightPhase::COAST, (int)fs.phase());
  TEST_ASSERT_FALSE(fs.controlAllowed());

  // Steigen, dann fallen: Apogäum nach 300 ms negativem vz und 1 m Baro-Abfall
  for (int i = 0; i < 50; ++i, t += 10) {
    FlightInputs in = padInputs(t); in.accel_z_g = 0; in.accel_mag_g = 0; in.vz_ms = 5; in.alt_m = 60; in.baro_alt_m = 60; fs.update(in);
  }
  ev = false;
  for (int i = 0; i < 60 && !ev; ++i, t += 10) {
    FlightInputs in = padInputs(t); in.accel_z_g = 0; in.accel_mag_g = 0; in.vz_ms = -2; in.alt_m = 58; in.baro_alt_m = 58.5f; ev = fs.update(in);
  }
  TEST_ASSERT_TRUE(ev);
  TEST_ASSERT_EQUAL((int)FlightPhase::APOGEE, (int)fs.phase());
  TEST_ASSERT_EQUAL(KN_REASON_VELOCITY, fs.lastEvent().reason);
  TEST_ASSERT_TRUE(fs.pyroAllowed());
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 60.0f, fs.maxAlt_m());

  // APOGEE -> DESCENT nach der Verweilzeit
  ev = false;
  for (int i = 0; i < 20 && !ev; ++i, t += 10) {
    FlightInputs in = padInputs(t); in.accel_z_g = 0; in.accel_mag_g = 0; in.vz_ms = -5; in.alt_m = 50; in.baro_alt_m = 50; ev = fs.update(in);
  }
  TEST_ASSERT_EQUAL((int)FlightPhase::DESCENT, (int)fs.phase());
  TEST_ASSERT_TRUE(fs.pyroAllowed());

  // Landung: ruhig für 3 s
  ev = false;
  for (int i = 0; i < 400 && !ev; ++i, t += 10) ev = fs.update(padInputs(t));
  TEST_ASSERT_TRUE(ev);
  TEST_ASSERT_EQUAL((int)FlightPhase::LANDED, (int)fs.phase());
  // LANDED ist endgültig
  FlightInputs in = padInputs(t); in.accel_z_g = 5.0f; fs.update(in);
  TEST_ASSERT_EQUAL((int)FlightPhase::LANDED, (int)fs.phase());
}

static void test_flightstate_abort_and_timeouts() {
  FlightStateConfig cfg;
  FlightState fs(cfg);
  uint32_t t = 0;
  FlightInputs in = padInputs(t);
  in.cmd_force_ready = true;
  TEST_ASSERT_TRUE(fs.update(in));
  TEST_ASSERT_EQUAL((int)FlightPhase::PAD_READY, (int)fs.phase());
  in = padInputs(t += 10); in.cmd_force_liftoff = true;
  TEST_ASSERT_TRUE(fs.update(in));
  TEST_ASSERT_EQUAL((int)FlightPhase::BOOST, (int)fs.phase());
  // Prüfstand: Beschleunigung bleibt 1 g, Brennschluss kommt über die Zeit
  bool ev = false;
  for (int i = 0; i < 600 && !ev; ++i) ev = fs.update(padInputs(t += 10));
  TEST_ASSERT_TRUE(ev);
  TEST_ASSERT_EQUAL((int)FlightPhase::COAST, (int)fs.phase());
  TEST_ASSERT_EQUAL(KN_REASON_TIMEOUT, fs.lastEvent().reason);
  // Abbruch aus COAST
  in = padInputs(t += 10); in.cmd_abort = true;
  TEST_ASSERT_TRUE(fs.update(in));
  TEST_ASSERT_EQUAL((int)FlightPhase::ABORT, (int)fs.phase());
  TEST_ASSERT_FALSE(fs.controlAllowed());
  // nach dem Start führt ABORT in LANDED, wenn es ruhig ist
  ev = false;
  for (int i = 0; i < 400 && !ev; ++i) ev = fs.update(padInputs(t += 10));
  TEST_ASSERT_EQUAL((int)FlightPhase::LANDED, (int)fs.phase());

  // Kippen im Boost -> ABORT
  FlightState g(cfg);
  t = 0;
  in = padInputs(t); in.cmd_force_ready = true; g.update(in);
  in = padInputs(t += 10); in.cmd_force_liftoff = true; g.update(in);
  in = padInputs(t += 10); in.tilt_deg = 80.0f;
  TEST_ASSERT_TRUE(g.update(in));
  TEST_ASSERT_EQUAL((int)FlightPhase::ABORT, (int)g.phase());
  TEST_ASSERT_EQUAL(KN_REASON_TILT, g.lastEvent().reason);

  // Zustandsspeicher: Neustart im Coast
  FlightState h(cfg);
  h.restore(FlightPhase::COAST, 5000, 1000);
  TEST_ASSERT_EQUAL((int)FlightPhase::COAST, (int)h.phase());
  TEST_ASSERT_EQUAL(1000, (int)h.liftoff_ms());
  TEST_ASSERT_EQUAL(KN_REASON_RESTORED, h.lastEvent().reason);
}

struct FlightRow { float t, fx, fy, fz, wx, wy, wz, alt, vz, baro, tilt; };

static bool loadFlight(std::vector<FlightRow>& rows) {
  char path[512];
  snprintf(path, sizeof path, "%s/flight_e12.csv", FLIGHTCORE_TEST_DATA_DIR);
  FILE* f = fopen(path, "r");
  if (!f) { printf("  %s nicht gefunden\n", path); return false; }
  char line[512];
  while (fgets(line, sizeof line, f)) {
    if (line[0] == '#' || line[0] == 't') continue;
    FlightRow r;
    if (sscanf(line, "%f,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f", &r.t, &r.fx, &r.fy, &r.fz, &r.wx, &r.wy, &r.wz,
               &r.alt, &r.vz, &r.baro, &r.tilt) == 11)
      rows.push_back(r);
  }
  fclose(f);
  return !rows.empty();
}

static void test_flightstate_on_simulated_flight() {
  std::vector<FlightRow> rows;
  if (!loadFlight(rows)) { TEST_FAIL_MESSAGE("flight_e12.csv fehlt (simulation/scripts/export_flight_csv.py)"); return; }

  FlightStateConfig cfg;
  FlightState fs(cfg);
  Attitude att;
  float t_boost = -1, t_coast = -1, t_apogee = -1, t_descent = -1, t_landed = -1;
  float max_tilt_err = 0;
  bool init = false;
  for (const FlightRow& r : rows) {
    FlightInputs in;
    in.t_ms = uint32_t(r.t * 1000.0f + 0.5f) + 20000;   // Boot 20 s vor dem Start
    const float amag = sqrtf(r.fx * r.fx + r.fy * r.fy + r.fz * r.fz);
    in.accel_z_g = r.fz / 9.81f;
    in.accel_mag_g = amag / 9.81f;
    in.gyro_mag_dps = sqrtf(r.wx * r.wx + r.wy * r.wy + r.wz * r.wz);
    in.vz_ms = r.vz; in.alt_m = r.alt; in.baro_alt_m = r.baro;
    in.armed = true; in.continuity = true; in.calibrated = true;
    if (!init) { att.initFromAccel(Vec3(r.fx, r.fy, r.fz)); init = true; }
    att.integrateDps(Vec3(r.wx, r.wy, r.wz), 0.01f);
    in.tilt_deg = att.tiltDeg();
    const float e = fabsf(att.tiltDeg() - r.tilt);
    if (e > max_tilt_err) max_tilt_err = e;
    // PAD_READY zu Beginn erzwingen (die Datei beginnt 0,4 s vor dem Start)
    if (fs.phase() == FlightPhase::SAFE) in.cmd_force_ready = true;
    if (fs.update(in)) {
      switch (fs.phase()) {
        case FlightPhase::BOOST:   t_boost = r.t; break;
        case FlightPhase::COAST:   t_coast = r.t; break;
        case FlightPhase::APOGEE:  t_apogee = r.t; break;
        case FlightPhase::DESCENT: t_descent = r.t; break;
        case FlightPhase::LANDED:  t_landed = r.t; break;
        default: break;
      }
    }
  }
  char msg[160];
  snprintf(msg, sizeof msg, "Boost %.2f  Coast %.2f  Apogee %.2f  Descent %.2f  Landed %.2f  Lagefehler max %.2f°",
           t_boost, t_coast, t_apogee, t_descent, t_landed, max_tilt_err);
  TEST_MESSAGE(msg);
  // Simulation: Start 0,40 s, Brennschluss 3,55 s, Gipfel 5,44 s, Landung 8,76 s
  TEST_ASSERT_FLOAT_WITHIN(0.15f, 0.45f, t_boost);
  TEST_ASSERT_FLOAT_WITHIN(0.5f, 3.6f, t_coast);
  TEST_ASSERT_FLOAT_WITHIN(0.8f, 5.9f, t_apogee);
  TEST_ASSERT_TRUE(t_descent > t_apogee);
  TEST_ASSERT_FLOAT_WITHIN(1.0f, 11.8f, t_landed);
  TEST_ASSERT_EQUAL((int)FlightPhase::LANDED, (int)fs.phase());
  TEST_ASSERT_FLOAT_WITHIN(5.0f, 54.0f, fs.maxAlt_m());
  // Quaternion aus dem Gyro gegen die wahre Lage der Simulation (verrauschtes Gyro, 0,1 °/s)
  TEST_ASSERT_LESS_THAN(1.0f, max_tilt_err);
}

// ===================== Pyro =====================

static void test_pyro_rules() {
  PyroLogic py;
  py.setFitted(0, true); py.setFitted(1, true);
  bool cont[4] = {true, true, false, false};
  uint32_t t = 1000;

  // Zustand erlaubt nicht
  py.update(t, true, cont, false);
  TEST_ASSERT_FALSE(py.fire(0, t));
  // nicht scharf
  py.update(t, false, cont, true);
  TEST_ASSERT_FALSE(py.fire(0, t));
  // kein Durchgang
  cont[0] = false; py.update(t, true, cont, true);
  TEST_ASSERT_FALSE(py.fire(0, t));
  cont[0] = true;
  // nicht bestückt
  py.update(t, true, cont, true);
  TEST_ASSERT_FALSE(py.fire(2, t));
  TEST_ASSERT_FALSE(py.fire(4, t));

  // alles erfüllt: Puls 80 ms
  TEST_ASSERT_TRUE(py.fire(0, t));
  TEST_ASSERT_TRUE(py.fireOutput(0));
  for (int i = 0; i < 7; ++i) { t += 10; py.update(t, true, cont, true); TEST_ASSERT_TRUE(py.fireOutput(0)); }
  t += 10; py.update(t, true, cont, true);
  TEST_ASSERT_FALSE(py.fireOutput(0));
  TEST_ASSERT_TRUE(py.fired(0));
  // kein zweites Mal
  TEST_ASSERT_FALSE(py.fire(0, t));
  TEST_ASSERT_EQUAL(0x01, py.firedMask());

  // Kanal 2: Durchgang bricht nach 20 ms weg -> Puls endet nach der Karenz
  TEST_ASSERT_TRUE(py.fire(1, t));
  t += 20; py.update(t, true, cont, true); TEST_ASSERT_TRUE(py.fireOutput(1));
  cont[1] = false;
  t += 5;  py.update(t, true, cont, true); TEST_ASSERT_TRUE(py.fireOutput(1));    // Karenz 10 ms
  t += 10; py.update(t, true, cont, true); TEST_ASSERT_FALSE(py.fireOutput(1));
  TEST_ASSERT_TRUE(py.fired(1));
  TEST_ASSERT_EQUAL(0x03, py.firedMask());

  // Zustandsspeicher: nach Neustart gelten gezündete Kanäle als verbraucht
  PyroLogic q;
  q.setFitted(0, true);
  q.restoreFiredMask(0x01);
  bool c2[4] = {true, true, true, true};
  q.update(0, true, c2, true);
  TEST_ASSERT_FALSE(q.fire(0, 0));

  // Scharfschaltung geht während des Pulses weg: Puls endet
  PyroLogic r;
  r.setFitted(0, true);
  r.update(0, true, c2, true);
  TEST_ASSERT_TRUE(r.fire(0, 0));
  r.update(10, false, c2, true);
  TEST_ASSERT_FALSE(r.fireOutput(0));
}

// ===================== TVC-Regler =====================

static void test_tvc_controller() {
  TvcParams p;
  p.kp = 5; p.ki = 0; p.kd = 1; p.mass_kg = 0.761f; p.moment_arm_m = 0.242f;
  p.yaw_gain = -6; p.yaw_offset = 90; p.yaw_min = 60; p.yaw_max = 120;
  p.pitch_gain = 6; p.pitch_offset = 90; p.pitch_min = 60; p.pitch_max = 120;
  TvcController c(p);
  c.reset();
  for (int i = 0; i < 100; ++i) c.updateAccelNorm(15.0f);   // 1,5 g Schub
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 15.0f, c.accelNormFilt());

  // ohne Fehler: Mitte
  TvcOutput o = c.update(0, 0, Vec3(0, 0, 0), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 90.0f, o.yaw_servo_deg);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 90.0f, o.pitch_servo_deg);

  // 2° Fehler um x: M = 5·(2/−100) = −0,1 N m; δ = asin(−0,1/(0,242·0,761·15)) = −2,07°
  o = c.update(2.0f, 0, Vec3(0, 0, 0), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, -0.1f, o.yaw_moment_nm);
  const float delta = asinf(-0.1f / (0.242f * 0.761f * 15.0f)) * 57.29578f;
  TEST_ASSERT_FLOAT_WITHIN(0.01f, delta, o.yaw_tvc_deg);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, delta * -6 + 90, o.yaw_servo_deg);
  TEST_ASSERT_FALSE(o.yaw_saturated);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.0f, o.pitch_moment_nm);

  // D-Anteil: 10 °/s um y -> M = 1·(10/−100) = −0,1 N m
  o = c.update(0, 0, Vec3(0, 10.0f, 0), 0.01f);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, -0.1f, o.pitch_moment_nm);

  // Sättigung auf tvc_max_deg (7°) und Fenster
  o = c.update(30.0f, -30.0f, Vec3(0, 0, 0), 0.01f);
  TEST_ASSERT_TRUE(o.yaw_saturated);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, -7.0f, o.yaw_tvc_deg);
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 7.0f, o.pitch_tvc_deg);
  TEST_ASSERT_TRUE(o.yaw_servo_deg >= 60 && o.yaw_servo_deg <= 120);

  // I-Anteil mit Anti-Windup: begrenzt
  TvcParams pi = p; pi.ki = 2.0f; pi.i_max_deg_s = 1.0f;
  TvcController ci(pi);
  for (int i = 0; i < 1000; ++i) ci.updateAccelNorm(15.0f);
  TvcOutput last;
  for (int i = 0; i < 2000; ++i) last = ci.update(1.0f, 0, Vec3(0, 0, 0), 0.01f);
  // M = 5·(1/−100) + 2·(∫e/−100), ∫e ≤ 1 -> M ≥ −0,07
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, -0.07f, last.yaw_moment_nm);

  // Kalibrierhilfe
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 84.0f, c.yawServoForTvc(1.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 96.0f, c.pitchServoForTvc(1.0f));
}

// ===================== main =====================

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_crc16_check_value);
  RUN_TEST(test_frame_roundtrip);
  RUN_TEST(test_frame_rejects_corruption_and_resyncs);
  RUN_TEST(test_attitude_init_from_accel);
  RUN_TEST(test_attitude_integrates_like_rot_deg_for_pure_axes);
  RUN_TEST(test_attitude_error_follows_body_axis_after_roll);
  RUN_TEST(test_attitude_norm_stays_one);
  RUN_TEST(test_flightstate_synthetic_sequence);
  RUN_TEST(test_flightstate_abort_and_timeouts);
  RUN_TEST(test_flightstate_on_simulated_flight);
  RUN_TEST(test_pyro_rules);
  RUN_TEST(test_tvc_controller);
  return UNITY_END();
}
