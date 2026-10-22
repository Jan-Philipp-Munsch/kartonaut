#include "minitest.h"
#include "Pyro.h"
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

static void pulse_length_and_continuity_cut() {
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
  // Durchgang verloren nach 30 ms: Puls endet sofort
  PyroLogic q(params());
  on_ms = 0;
  for (uint32_t t = 10000; t < 10500; t += 10) {
    in.t_ms = t; in.continuity[0] = (t < 10030);
    q.update(in, fire);
    if (fire[0]) on_ms += 10;
  }
  CHECK_NEAR(on_ms, 30, 10);
  CHECK(q.done());
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
    in.t_ms = t; in.continuity[1] = (t < 20400);   // Anzünder brennt nach 400 ms durch
    p.update(in, fire);
    if (fire[0]) on0 += 10;
    if (fire[1]) on1 += 10;
  }
  CHECK_EQ(on0, 0);
  CHECK_NEAR(on1, 400, 15);                        // Puls endet mit dem Durchgang, nicht erst nach 1 s
  CHECK(p.done(1));
  CHECK_EQ(p.fires(1), 1);
}

void run_tests_pyro() {
  RUN_TEST(igniter_channel_without_backup_pair);
  RUN_TEST(fires_only_with_all_conditions);
  RUN_TEST(pulse_length_and_continuity_cut);
  RUN_TEST(retries_limited_and_backup_channel_delayed);
  RUN_TEST(unarmed_board_marks_done_so_state_machine_moves_on);
  RUN_TEST(disarm_during_pulse_stops_it);
}
