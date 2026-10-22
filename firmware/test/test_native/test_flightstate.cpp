#include "minitest.h"
#include "FlightState.h"
#include "Config.h"
#include <stdio.h>
#include <stdlib.h>
#include <vector>

static FlightParams params() {
  return FlightParams{FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M,
                      FS_LANDED_VZ_MS, FS_LANDED_ALT_M, FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS,
                      FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS, FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS,
                      FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS};
}

// Synthetischer Flug: 2 s Pad, 3,5 s Brennen mit 12 m/s² netto, Gipfel, Schirm 8 m/s, Landung.
struct Sample { uint32_t t_ms; float a_norm, a_axial, alt, vz, baro; };

static std::vector<Sample> synthetic_flight() {
  std::vector<Sample> v;
  float alt = 0, vz = 0;
  const float g = 9.81f, dt = 0.01f;
  bool chute = false;
  for (int i = 0; i < 6000; ++i) {
    const float t = i * dt;
    float thrust_acc = 0;
    if (t >= 2.0f && t < 5.5f) thrust_acc = 12.0f + g;   // spezifische Kraft axial
    float a_axial, a_norm;
    if (t < 2.0f) { a_axial = g; a_norm = g; }
    else if (t < 5.5f) { a_axial = thrust_acc; a_norm = thrust_acc; vz += 12.0f * dt; alt += vz * dt; }
    else {
      if (!chute && vz < 0 && alt > 5) { chute = true; }
      if (chute) { vz = -8.0f; a_axial = 0.5f; a_norm = g; }
      else { vz -= g * dt; a_axial = 0.3f; a_norm = 0.3f; }
      alt += vz * dt;
      if (alt <= 0) { alt = 0; vz = 0; a_axial = g; a_norm = g; }
    }
    v.push_back({(uint32_t)(t * 1000) + 1000, a_norm, a_axial, alt, vz, alt + 0.2f * sinf(t * 7)});
  }
  return v;
}

static void run_profile(FlightStateMachine& fsm, const std::vector<Sample>& prof, bool ready_cmd = true) {
  FlightInputs in;
  in.calibrated = true; in.sensors_ok = true;
  for (size_t i = 0; i < prof.size(); ++i) {
    const Sample& s = prof[i];
    in.t_ms = s.t_ms; in.a_norm_ms2 = s.a_norm; in.a_axial_ms2 = s.a_axial; in.alt_m = s.alt; in.vz_ms = s.vz;
    in.baro_alt_m = s.baro;
    in.cmd = (i == 10 && ready_cmd) ? FlightCmd::PAD_READY : FlightCmd::NONE;
    in.pyro_done = fsm.state() == FlightState::APOGEE && (s.t_ms - fsm.apogeeTime() > 150);
    fsm.update(in);
  }
}

static void full_sequence_on_synthetic_flight() {
  FlightStateMachine fsm(params());
  CHECK_EQ((int)fsm.state(), (int)FlightState::SAFE);
  run_profile(fsm, synthetic_flight());
  CHECK_EQ((int)fsm.state(), (int)FlightState::LANDED);
  const FlightState expect[] = {FlightState::PAD_READY, FlightState::BOOST, FlightState::COAST, FlightState::APOGEE,
                                FlightState::DESCENT, FlightState::LANDED};
  CHECK_EQ(fsm.events(), 6);
  for (int i = 0; i < fsm.events() && i < 6; ++i) CHECK_EQ((int)fsm.event(i).to, (int)expect[i]);
  // Zeiten: Start bei 3,0 s (+1 s Offset), Brennschluss 6,5 s, Gipfel nach 42/9,81 = 4,3 s Steigflug
  CHECK_NEAR(fsm.launchTime(), 3000, 30);
  CHECK_NEAR(fsm.burnoutTime(), 6500, 150);
  CHECK(fsm.event(1).reason == FlightReason::ACCEL);
  CHECK(fsm.event(2).reason == FlightReason::BURNOUT_ACCEL);
  CHECK(fsm.event(3).reason == FlightReason::APOGEE_SENSORS);
  CHECK(fsm.apogeeTime() > fsm.burnoutTime() + 4000 && fsm.apogeeTime() < fsm.burnoutTime() + 5000);
  CHECK(fsm.event(5).reason == FlightReason::LANDED_SENSORS);
}

static void no_launch_without_pad_ready() {
  FlightStateMachine fsm(params());
  run_profile(fsm, synthetic_flight(), false);
  CHECK_EQ((int)fsm.state(), (int)FlightState::SAFE);
  CHECK_EQ(fsm.events(), 0);
}

static void pad_ready_refused_when_not_calibrated() {
  FlightStateMachine fsm(params());
  FlightInputs in; in.t_ms = 100; in.cmd = FlightCmd::PAD_READY; in.calibrated = false; in.sensors_ok = true;
  CHECK(fsm.update(in));
  CHECK_EQ((int)fsm.state(), (int)FlightState::SAFE);
  CHECK(fsm.lastEvent().reason == FlightReason::NOT_READY);
}

static void short_bump_does_not_launch() {
  FlightStateMachine fsm(params());
  FlightInputs in; in.calibrated = in.sensors_ok = true; in.t_ms = 100; in.cmd = FlightCmd::PAD_READY;
  fsm.update(in);
  in.cmd = FlightCmd::NONE;
  for (int i = 0; i < 4; ++i) { in.t_ms += 10; in.a_norm_ms2 = 30; fsm.update(in); }   // 40 ms Stoß
  in.t_ms += 10; in.a_norm_ms2 = 9.8f; fsm.update(in);
  CHECK_EQ((int)fsm.state(), (int)FlightState::PAD_READY);
  for (int i = 0; i < 6; ++i) { in.t_ms += 10; in.a_norm_ms2 = 30; fsm.update(in); }   // 60 ms
  CHECK_EQ((int)fsm.state(), (int)FlightState::BOOST);
}

static void timeouts_carry_the_flight_without_sensors() {
  // Beschleunigung bleibt hoch, Baro/Kalman liefern nichts: Rückfälle über die Zeit
  FlightStateMachine fsm(params());
  FlightInputs in; in.calibrated = in.sensors_ok = true; in.t_ms = 100; in.cmd = FlightCmd::PAD_READY;
  fsm.update(in); in.cmd = FlightCmd::NONE;
  in.a_norm_ms2 = 40; in.a_axial_ms2 = 40; in.alt_m = 100; in.vz_ms = 10;
  for (uint32_t t = 110; t < 130000; t += 10) {
    in.t_ms = t;
    in.pyro_done = false;
    fsm.update(in);
  }
  CHECK_EQ((int)fsm.state(), (int)FlightState::LANDED);
  CHECK(fsm.event(2).reason == FlightReason::BURN_TIMEOUT);
  CHECK(fsm.event(3).reason == FlightReason::APOGEE_TIMEOUT);
  CHECK_NEAR(fsm.event(3).t_ms, fsm.burnoutTime() + FS_APOGEE_FALLBACK_MS, 20);
  CHECK(fsm.event(5).reason == FlightReason::FLIGHT_TIMEOUT);
}

static void abort_on_pad_and_in_flight() {
  FlightStateMachine fsm(params());
  FlightInputs in; in.calibrated = in.sensors_ok = true; in.t_ms = 100; in.cmd = FlightCmd::PAD_READY;
  fsm.update(in);
  in.t_ms = 200; in.cmd = FlightCmd::ABORT; fsm.update(in);
  CHECK_EQ((int)fsm.state(), (int)FlightState::ABORT);
  CHECK(!fsm.inFlight());
  in.t_ms = 300; in.cmd = FlightCmd::SAFE; fsm.update(in);
  CHECK_EQ((int)fsm.state(), (int)FlightState::SAFE);

  // im Flug: Abbruch während BOOST -> Regler aus, Bergung über die Zeit
  FlightStateMachine f2(params());
  in = FlightInputs{}; in.calibrated = in.sensors_ok = true; in.t_ms = 100; in.cmd = FlightCmd::PAD_READY; f2.update(in);
  in.cmd = FlightCmd::NONE; in.a_norm_ms2 = 30; in.a_axial_ms2 = 30;
  for (uint32_t t = 110; t < 1000; t += 10) { in.t_ms = t; f2.update(in); }
  CHECK_EQ((int)f2.state(), (int)FlightState::BOOST);
  CHECK(f2.controlActive());
  in.t_ms = 1000; in.cmd = FlightCmd::ABORT; f2.update(in);
  CHECK_EQ((int)f2.state(), (int)FlightState::ABORT);
  CHECK(f2.inFlight());
  CHECK(!f2.controlActive());
  in.cmd = FlightCmd::NONE;
  for (uint32_t t = 1010; t < 7500; t += 10) { in.t_ms = t; f2.update(in); }
  CHECK_EQ((int)f2.state(), (int)FlightState::APOGEE);   // Rückfall nach apogee_fallback_ms ab Abbruch
  CHECK_NEAR(f2.apogeeTime(), 1010 + FS_APOGEE_FALLBACK_MS, 20);
  for (uint32_t t = 7500; t < 9000; t += 10) { in.t_ms = t; f2.update(in); }
  CHECK_EQ((int)f2.state(), (int)FlightState::DESCENT);  // ohne Pyro-Rückmeldung nach descent_after_ms
}

static void restore_after_reboot() {
  FlightStateMachine fsm(params());
  fsm.restore(FlightState::COAST, 5000, 8500, 0, 40.0f, 9000);
  CHECK_EQ((int)fsm.state(), (int)FlightState::COAST);
  CHECK(fsm.inFlight());
  CHECK(fsm.lastEvent().reason == FlightReason::RESTORED);
  FlightInputs in; in.t_ms = 9010; in.vz_ms = -3; in.baro_alt_m = 38; in.alt_m = 38;
  for (uint32_t t = 9010; t < 9400; t += 10) { in.t_ms = t; fsm.update(in); }
  CHECK_EQ((int)fsm.state(), (int)FlightState::APOGEE);
}

// Flugdaten aus der Python-Simulation (simulation/scripts/export_firmware_vectors.py)
static void sequence_on_tvcsim_flight() {
  FILE* f = fopen("test/data/flight_profile_tvcsim.csv", "r");
  if (!f) f = fopen("firmware/test/data/flight_profile_tvcsim.csv", "r");
  CHECK_MSG(f != nullptr, "test/data/flight_profile_tvcsim.csv fehlt (export_firmware_vectors.py)");
  if (!f) return;
  std::vector<Sample> prof;
  char line[256];
  if (!fgets(line, sizeof line, f)) { fclose(f); return; }   // Kopf
  while (fgets(line, sizeof line, f)) {
    Sample s; float t;
    if (sscanf(line, "%f,%f,%f,%f,%f,%f", &t, &s.a_norm, &s.a_axial, &s.alt, &s.vz, &s.baro) == 6) {
      s.t_ms = (uint32_t)(t * 1000.0f + 0.5f) + 1000;
      prof.push_back(s);
    }
  }
  fclose(f);
  CHECK(prof.size() > 500);
  FlightStateMachine fsm(params());
  run_profile(fsm, prof);
  CHECK_MSG(fsm.state() == FlightState::LANDED, "Endzustand %s", flightStateName(fsm.state()));
  const FlightState expect[] = {FlightState::PAD_READY, FlightState::BOOST, FlightState::COAST, FlightState::APOGEE,
                                FlightState::DESCENT, FlightState::LANDED};
  CHECK_EQ(fsm.events(), 6);
  for (int i = 0; i < fsm.events() && i < 6; ++i)
    CHECK_MSG(fsm.event(i).to == expect[i], "Ereignis %d: %s", i, flightStateName(fsm.event(i).to));
  // Brennschluss der E12 bei 3,55 s; die Schubkurve läuft ab 3,1 s unter 2,3 N (3 m/s²) aus
  CHECK_NEAR(fsm.burnoutTime() - fsm.launchTime(), 3300, 400);
  CHECK(fsm.event(3).reason == FlightReason::APOGEE_SENSORS);
}

void run_tests_flightstate() {
  RUN_TEST(full_sequence_on_synthetic_flight);
  RUN_TEST(no_launch_without_pad_ready);
  RUN_TEST(pad_ready_refused_when_not_calibrated);
  RUN_TEST(short_bump_does_not_launch);
  RUN_TEST(timeouts_carry_the_flight_without_sensors);
  RUN_TEST(abort_on_pad_and_in_flight);
  RUN_TEST(restore_after_reboot);
  RUN_TEST(sequence_on_tvcsim_flight);
}
