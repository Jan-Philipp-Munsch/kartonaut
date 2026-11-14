#include "minitest.h"
#include "Pyro.h"
#include "ChuteRelease.h"
#include "Config.h"

static PyroParams params() { return PyroParams{{PYRO_PULSE_MS, PYRO_PULSE_MS}, PYRO_MIN_FLIGHT_MS, PYRO_BACKUP_DELAY_MS, PYRO_RETRY_DELAY_MS, PYRO_MAX_FIRES, true}; }

static void fires_only_with_all_conditions() {
  PyroLogic p(params());
  PyroInputs in; bool fire[2];
  in.t_ms = 10000; in.t_launch_ms = 5000; in.allowed[0] = in.allowed[1] = true; in.armed = true; in.continuity[0] = true;
  // je eine Bedingung weglassen
  in.allowed[0] = false; p.update(in, fire); CHECK(!fire[0]); in.allowed[0] = in.allowed[1] = true;
  in.armed = false;   p.update(in, fire); CHECK(!fire[0]); in.armed = true;
  in.continuity[0] = false; p.update(in, fire); CHECK(!fire[0]); in.continuity[0] = true;
  in.t_launch_ms = 9000; p.update(in, fire); CHECK(!fire[0]); in.t_launch_ms = 5000;   // zu kurz nach dem Start
  in.t_launch_ms = 0;    p.update(in, fire); CHECK(!fire[0]); in.t_launch_ms = 5000;   // nie gestartet
  CHECK_EQ(p.fires(0), 0);
  p.update(in, fire); CHECK(fire[0]);
  CHECK_EQ(p.fires(0), 1);
}

static void pulse_has_full_length_also_without_continuity() {
  PyroLogic p(params());
  PyroInputs in; bool fire[2];
  in.t_launch_ms = 1000; in.allowed[0] = in.allowed[1] = true; in.armed = true; in.continuity[0] = true;
  uint32_t on_ms = 0;
  for (uint32_t t = 10000; t < 10500; t += 10) {
    in.t_ms = t; p.update(in, fire);
    if (fire[0]) on_ms += 10;
  }
  CHECK_NEAR(on_ms, PYRO_PULSE_MS, 10);
  CHECK(p.done());
  CHECK_EQ(p.fires(0), 1);     // der zweite Versuch kommt erst nach PYRO_RETRY_DELAY_MS
  // Durchgang weg nach 30 ms (Anzünder durchgebrannt oder Sense vom FET nach unten gezogen):
  // der Puls läuft trotzdem zu Ende, und ohne Durchgang danach gibt es keinen zweiten Versuch
  PyroLogic q(params());
  on_ms = 0;
  for (uint32_t t = 10000; t < 12000; t += 10) {
    in.t_ms = t; in.continuity[0] = (t < 10030);
    q.update(in, fire);
    if (fire[0]) on_ms += 10;
  }
  CHECK_NEAR(on_ms, PYRO_PULSE_MS, 10);
  CHECK(q.done());
  CHECK_EQ(q.fires(0), 1);
}

// rev B1: PYRO_SENSE liegt am Drain des FET. Solange der Ausgang zündet, liest die Messung
// "kein Durchgang"; danach wieder Durchgang, wenn der Anzünder ganz geblieben ist (Befund 25).
static void sense_pulled_low_while_firing_does_not_cut_the_pulse() {
  PyroLogic p(params());
  PyroInputs in; bool fire[2] = {false, false};
  in.t_launch_ms = 1000; in.allowed[0] = in.allowed[1] = true; in.armed = true;
  uint32_t on_ms = 0, longest = 0, run = 0;
  for (uint32_t t = 10000; t < 12000; t += 4) {
    in.t_ms = t;
    in.continuity[0] = !fire[0];           // Messung folgt dem Ausgang des vorigen Takts
    p.update(in, fire);
    if (fire[0]) { on_ms += 4; run += 4; if (run > longest) longest = run; } else run = 0;
  }
  CHECK_NEAR(longest, PYRO_PULSE_MS, 4);                     // kein Abbruch nach dem ersten Takt
  CHECK_EQ(p.fires(0), PYRO_MAX_FIRES);                      // Anzünder bleibt ganz: zweiter Versuch
  CHECK_NEAR(on_ms, PYRO_MAX_FIRES * PYRO_PULSE_MS, 8);
}

static void chute_servo_opens_in_apogee_and_stays_open() {
  ChuteRelease c(PYRO_MIN_FLIGHT_MS, false);
  ChuteReleaseInputs in;
  in.t_ms = 20000; in.t_launch_ms = 0; in.allowed = true;
  CHECK(!c.update(in));                                      // nie gestartet
  CHECK(strcmp(c.lastRefusal(), "Flugzeit") == 0);
  in.t_launch_ms = 19000;
  CHECK(!c.update(in));                                      // erst 1 s nach dem Start
  in.t_launch_ms = 10000; in.allowed = false;
  CHECK(!c.update(in));                                      // Zustand erlaubt es nicht (BOOST, COAST)
  CHECK(strcmp(c.lastRefusal(), "Zustand") == 0);
  in.allowed = true; in.armed = false;
  CHECK(c.update(in));                                       // ohne ARM, wenn needs_arm aus ist
  CHECK_EQ(c.releaseTime(), 20000);
  in.allowed = false; in.t_ms = 30000;
  CHECK(c.update(in));                                       // bleibt offen (LANDED)
  c.reset();
  CHECK(!c.update(in));                                      // zurück in SAFE: wieder zu
}

static void chute_servo_can_require_arm() {
  ChuteRelease c(PYRO_MIN_FLIGHT_MS, true);
  ChuteReleaseInputs in;
  in.t_ms = 20000; in.t_launch_ms = 10000; in.allowed = true; in.armed = false;
  CHECK(!c.update(in));
  CHECK(strcmp(c.lastRefusal(), "nicht scharf") == 0);
  in.armed = true;
  CHECK(c.update(in));
}

static void retries_limited_and_backup_channel_delayed() {
  PyroLogic p(params());
  PyroInputs in; bool fire[2];
  in.t_launch_ms = 1000; in.allowed[0] = in.allowed[1] = true; in.armed = true; in.continuity[0] = true; in.continuity[1] = true;
  in.fitted[1] = true;
  uint32_t first1 = 0, first2 = 0;
  for (uint32_t t = 10000; t < 14000; t += 10) {
    in.t_ms = t; p.update(in, fire);
    if (fire[0] && !first1) first1 = t;
    if (fire[1] && !first2) first2 = t;
  }
  CHECK_EQ(p.fires(0), PYRO_MAX_FIRES);   // Durchgang bleibt (Anzünder brennt nicht durch): Versuche begrenzt
  CHECK_EQ(p.fires(1), PYRO_MAX_FIRES);
  CHECK_NEAR(first2 - first1, PYRO_BACKUP_DELAY_MS, 20);
  CHECK(!fire[0] && !fire[1]);
}

static void unarmed_board_marks_done_so_state_machine_moves_on() {
  PyroLogic p(params());
  PyroInputs in; bool fire[2];
  in.t_ms = 20000; in.t_launch_ms = 1000; in.allowed[0] = in.allowed[1] = true; in.armed = false; in.continuity[0] = true;
  p.update(in, fire);
  CHECK(!fire[0]);
  CHECK(p.done());
  CHECK(strcmp(p.lastRefusal(), "nicht scharf") == 0);
}

static void disarm_during_pulse_stops_it() {
  PyroLogic p(params());
  PyroInputs in; bool fire[2];
  in.t_launch_ms = 1000; in.allowed[0] = in.allowed[1] = true; in.armed = true; in.continuity[0] = true;
  in.t_ms = 10000; p.update(in, fire); CHECK(fire[0]);
  in.t_ms = 10010; in.armed = false; p.update(in, fire); CHECK(!fire[0]);
}

static void igniter_channel_without_backup_pair() {
  PyroLogic p(PyroParams{{PYRO_PULSE_MS, PYRO_IGNITER_PULSE_MS}, PYRO_MIN_FLIGHT_MS, PYRO_BACKUP_DELAY_MS,
                         PYRO_RETRY_DELAY_MS, PYRO_MAX_FIRES, false});
  PyroInputs in; bool fire[2];
  in.t_launch_ms = 1000; in.armed = true; in.continuity[0] = in.continuity[1] = true; in.fitted[1] = true;
  in.allowed[0] = false; in.allowed[1] = true;     // LANDING_BURN: nur der Anzünder
  uint32_t on1 = 0, on0 = 0;
  for (uint32_t t = 20000; t < 22000; t += 10) {
    in.t_ms = t; in.continuity[1] = (t < 20400);   // Anzünder brennt nach 400 ms durch (Messung: kein Durchgang)
    p.update(in, fire);
    if (fire[0]) on0 += 10;
    if (fire[1]) on1 += 10;
  }
  CHECK_EQ(on0, 0);
  CHECK_NEAR(on1, PYRO_IGNITER_PULSE_MS, 15);      // voller Puls: die Messung gilt während der Zündung nicht
  CHECK(p.done(1));
  CHECK_EQ(p.fires(1), 1);
}

void run_tests_pyro() {
  RUN_TEST(igniter_channel_without_backup_pair);
  RUN_TEST(fires_only_with_all_conditions);
  RUN_TEST(pulse_has_full_length_also_without_continuity);
  RUN_TEST(sense_pulled_low_while_firing_does_not_cut_the_pulse);
  RUN_TEST(chute_servo_opens_in_apogee_and_stays_open);
  RUN_TEST(chute_servo_can_require_arm);
  RUN_TEST(retries_limited_and_backup_channel_delayed);
  RUN_TEST(unarmed_board_marks_done_so_state_machine_moves_on);
  RUN_TEST(disarm_during_pulse_stops_it);
}
