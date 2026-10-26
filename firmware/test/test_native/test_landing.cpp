#include "minitest.h"
#include "LandingBurn.h"
#include "ThrustCurveE12.h"
#include "FlightState.h"
#include "Config.h"
#include <stdio.h>
#include <vector>

static LandingParams params(float m, float cd_a = 0.003f) {
  return LandingParams{m, 0.028f, cd_a, 1.2f, 0.10f, 0.01f, 2.0f, 1.0f};
}

static LandingPlanner planner(float m, float cd_a = 0.003f) {
  return LandingPlanner(params(m, cd_a), thrustcurve::E12_T_S, thrustcurve::E12_F_N, thrustcurve::E12_N);
}

// Aufsetzkosten wie tvcsim.landing.impact_cost (simulation/scripts/export_landing_firmware.py)
static void cost_matches_python() {
  FILE* f = fopen("test/data/landing_cost_E12.csv", "r");
  if (!f) f = fopen("firmware/test/data/landing_cost_E12.csv", "r");
  CHECK_MSG(f != nullptr, "landing_cost_E12.csv fehlt");
  if (!f) return;
  char line[128];
  if (!fgets(line, sizeof line, f)) { fclose(f); return; }
  int rows = 0; double max_err = 0;
  while (fgets(line, sizeof line, f)) {
    float m, h, v, cda, J;
    if (sscanf(line, "%f,%f,%f,%f,%f", &m, &h, &v, &cda, &J) != 5) continue;
    LandingPlanner pl = planner(m, cda);
    const float Jc = pl.cost(h, v);
    const double e = fabs(Jc - J);
    if (e > max_err) max_err = e;
    CHECK_MSG(e < 0.15, "m=%.2f h=%.0f v=%.0f: J %.3f statt %.3f", m, h, v, Jc, J);
    rows++;
  }
  fclose(f);
  CHECK_EQ(rows, 60);
  CHECK_MSG(max_err < 0.15, "max. Abweichung %g m/s", max_err);
}

static void cost_shape_along_free_fall() {
  // Entlang eines freien Falls aus 61 m (0,7 kg): J fällt, hat ein Minimum und steigt wieder;
  // der Planer zündet nahe dem Minimum, das die Simulation bei 37,6 m / -20,7 m/s fand.
  LandingPlanner pl = planner(0.7f);
  float h = 60.8f, v = 0.0f;
  float J_prev = 1e9f, J_min = 1e9f, h_min = 0, h_ign = -1, v_ign = 0;
  bool rising_seen = false;
  for (int k = 0; k < 2000 && h > 0; ++k) {
    v += (-9.81f + 0.5f * 1.2f * 0.003f * v * v / 0.7f) * 0.01f;
    h += v * 0.01f;
    if (v > -2.0f) continue;
    float hp, vp; LandingPlanner::predict(h, v, 0.10f, hp, vp);
    const float J = pl.cost(hp, vp);
    if (J < J_min) { J_min = J; h_min = h; }
    if (J > J_prev + 0.05f && J_min < J_prev) rising_seen = true;
    J_prev = J;
    if (h_ign < 0 && pl.shouldIgnite(h, v)) { h_ign = h; v_ign = v; }
  }
  CHECK(rising_seen);
  CHECK(h_ign > 0);
  CHECK_NEAR(h_ign, h_min, 1.5);
  CHECK_NEAR(h_ign, 37.6, 2.0);
  CHECK_NEAR(v_ign, -20.7, 0.6);
  CHECK(J_min < 6.0 && J_min > 3.0);        // Studie: ~4,8 m/s bei 0,7 kg
}

static void ignition_only_when_falling() {
  LandingPlanner pl = planner(0.7f);
  CHECK(!pl.shouldIgnite(50.0f, 0.0f));
  CHECK(!pl.shouldIgnite(50.0f, 5.0f));
  CHECK(!pl.shouldIgnite(50.0f, -1.0f));    // unter min_speed
  CHECK(pl.shouldIgnite(0.5f, -10.0f));     // praktisch am Boden: lieber zünden
}

// Flugzustandsautomat mit Landebrennen auf dem simulierten Flug (landing_profile_tvcsim.csv)
struct LSample { uint32_t t_ms; float a_norm, a_axial, alt, vz, baro, thrust; };

static void state_machine_lands_with_second_motor() {
  FILE* f = fopen("test/data/landing_profile_tvcsim.csv", "r");
  if (!f) f = fopen("firmware/test/data/landing_profile_tvcsim.csv", "r");
  CHECK_MSG(f != nullptr, "landing_profile_tvcsim.csv fehlt");
  if (!f) return;
  std::vector<LSample> prof;
  char line[256];
  if (!fgets(line, sizeof line, f)) { fclose(f); return; }
  while (fgets(line, sizeof line, f)) {
    LSample s; float t;
    if (sscanf(line, "%f,%f,%f,%f,%f,%f,%f", &t, &s.a_norm, &s.a_axial, &s.alt, &s.vz, &s.baro, &s.thrust) == 7) {
      s.t_ms = (uint32_t)(t * 1000.0f + 0.5f) + 1000;
      prof.push_back(s);
    }
  }
  fclose(f);
  CHECK(prof.size() > 1000);

  FlightParams fp{FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M,
                  FS_LANDED_VZ_MS, FS_LANDED_ALT_M, FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS,
                  FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS, FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS,
                  FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS, true, LANDING_BURN_MAX_MS};
  FlightStateMachine fsm(fp);
  LandingPlanner pl = planner(0.7f);
  FlightInputs in; in.calibrated = in.sensors_ok = true; in.landing_possible = true;
  uint32_t t_ign = 0; float h_ign = 0, v_ign = 0; uint32_t t_thrust2 = 0;
  for (size_t i = 0; i < prof.size(); ++i) {
    const LSample& s = prof[i];
    in.t_ms = s.t_ms; in.a_norm_ms2 = s.a_norm; in.a_axial_ms2 = s.a_axial; in.alt_m = s.alt; in.vz_ms = s.vz;
    in.baro_alt_m = s.baro;
    in.cmd = (i == 10) ? FlightCmd::PAD_READY : FlightCmd::NONE;
    in.ignite_now = fsm.state() == FlightState::DESCENT && pl.shouldIgnite(s.alt, s.vz);
    if (fsm.update(in) && fsm.state() == FlightState::LANDING_BURN) { t_ign = s.t_ms; h_ign = s.alt; v_ign = s.vz; }
    if (!t_thrust2 && t_ign && s.thrust > 0.5f) t_thrust2 = s.t_ms;
  }
  CHECK_MSG(fsm.state() == FlightState::LANDED, "Endzustand %s", flightStateName(fsm.state()));
  const FlightState expect[] = {FlightState::PAD_READY, FlightState::BOOST, FlightState::COAST, FlightState::APOGEE,
                                FlightState::DESCENT, FlightState::LANDING_BURN, FlightState::LANDED};
  CHECK_EQ(fsm.events(), 7);
  for (int i = 0; i < fsm.events() && i < 7; ++i)
    CHECK_MSG(fsm.event(i).to == expect[i], "Ereignis %d: %s", i, flightStateName(fsm.event(i).to));
  CHECK(fsm.event(4).reason == FlightReason::LANDING_FREEFALL);
  CHECK(fsm.event(5).reason == FlightReason::IGNITION);
  // Die Firmware zündet dort, wo auch die Simulation gezündet hat (37,6 m, -20,7 m/s)
  CHECK_NEAR(h_ign, 37.6, 1.5);
  CHECK_NEAR(v_ign, -20.7, 0.6);
  // Die Simulation (double, eigener Planer) zündete 100 ms vor ihrem Schub; die Firmware trifft
  // das flache Minimum von J bis auf wenige Takte (float): Schub 100..300 ms nach ihrer Zündung
  CHECK((double)t_thrust2 - (double)t_ign >= 90 && (double)t_thrust2 - (double)t_ign <= 300);
}

static void landing_falls_back_to_chute_without_igniter() {
  FlightParams fp{FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M,
                  FS_LANDED_VZ_MS, FS_LANDED_ALT_M, FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS,
                  FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS, FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS,
                  FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS, true, LANDING_BURN_MAX_MS};
  FlightStateMachine fsm(fp);
  FlightInputs in; in.calibrated = in.sensors_ok = true; in.landing_possible = false;
  in.t_ms = 100; in.cmd = FlightCmd::PAD_READY; fsm.update(in); in.cmd = FlightCmd::NONE;
  in.a_norm_ms2 = 30; in.a_axial_ms2 = 30;
  for (uint32_t t = 110; t < 6000; t += 10) { in.t_ms = t; fsm.update(in); }   // Brennschluss per Zeit
  in.a_norm_ms2 = 1; in.a_axial_ms2 = 0.2f; in.vz_ms = -3; in.baro_alt_m = 50; in.alt_m = 50;
  for (uint32_t t = 6000; t < 7000; t += 10) { in.t_ms = t; in.baro_alt_m -= 0.03f; fsm.update(in); }
  CHECK_EQ((int)fsm.state(), (int)FlightState::APOGEE);
  CHECK(fsm.landingFallback());
  CHECK(fsm.pyroAllowed());                  // Fallschirm-Kanal frei
  CHECK(!fsm.igniterAllowed());
  in.pyro_done = true; in.t_ms = 7010; fsm.update(in);
  CHECK_EQ((int)fsm.state(), (int)FlightState::DESCENT);
  in.ignite_now = true; in.t_ms = 7020; fsm.update(in);
  CHECK_EQ((int)fsm.state(), (int)FlightState::DESCENT);   // kein Landebrennen mehr nach dem Rückfall
}

void run_tests_landing() {
  RUN_TEST(cost_matches_python);
  RUN_TEST(cost_shape_along_free_fall);
  RUN_TEST(ignition_only_when_falling);
  RUN_TEST(state_machine_lands_with_second_motor);
  RUN_TEST(landing_falls_back_to_chute_without_igniter);
}
