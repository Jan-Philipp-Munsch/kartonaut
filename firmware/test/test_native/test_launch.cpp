// Motorstart an Bord (docs/Plan_Bordzuendung_2026-10-27.md §6): MAC, Zustandsautomat, Startpuls,
// Vorbedingungen, Anzeige, IGN-Rahmen, Negativtest über alle Zustände.
#include "minitest.h"
#include "Sha256.h"
#include "LaunchAuth.h"
#include "LaunchControl.h"
#include "FlightState.h"
#include "Pyro.h"
#include "Config.h"
#include <string.h>

static void hex(const uint8_t* d, size_t n, char* out) {
  for (size_t i = 0; i < n; ++i) snprintf(out + 2 * i, 3, "%02x", d[i]);
}

// ------------------------------------------------------------------ SHA-256 / HMAC
static bool digest_is(const char* msg, const char* want) {
  uint8_t d[32]; char h[65];
  sha256((const uint8_t*)msg, strlen(msg), d);
  hex(d, 32, h);
  return strcmp(h, want) == 0;
}

static void sha256_fips_vectors() {
  CHECK(digest_is("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));
  CHECK(digest_is("abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
  CHECK(digest_is("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
                  "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"));
  // stückweise wie am Stück
  Sha256 s; uint8_t d[32]; char h[65];
  s.update((const uint8_t*)"ab", 2); s.update((const uint8_t*)"c", 1); s.final(d);
  hex(d, 32, h);
  CHECK(strcmp(h, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);
}

static void hmac_rfc4231_vectors() {
  uint8_t key[20]; memset(key, 0x0b, sizeof key);
  uint8_t d[32]; char h[65];
  hmac_sha256(key, sizeof key, (const uint8_t*)"Hi There", 8, d);
  hex(d, 32, h);
  CHECK(strcmp(h, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7") == 0);
  const char* msg = "what do ya want for nothing?";
  hmac_sha256((const uint8_t*)"Jefe", 4, (const uint8_t*)msg, strlen(msg), d);
  hex(d, 32, h);
  CHECK(strcmp(h, "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843") == 0);
}

// ------------------------------------------------------------------ MAC und nonce
static const uint8_t KEY[16] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};

static void mac_accepts_right_nonce_only_once() {
  LaunchAuth a(KEY, 1);
  uint8_t mac[8];
  a.renew(0x12345678);
  launch_auth::computeMac(KEY, 0x25, 7, 0x12345678, 1, mac);
  CHECK(a.verify(0x25, 7, mac));
  CHECK(!a.hasNonce());                         // verbraucht
  CHECK(!a.verify(0x25, 7, mac));               // Wiederholung abgelehnt
  a.renew(0x12345678);                          // selbst dieselbe Zahl gilt nur einmal
  CHECK(a.verify(0x25, 7, mac));
  CHECK(!a.verify(0x25, 7, mac));
}

static void mac_rejects_wrong_nonce_key_type_seq_id() {
  uint8_t mac[8];
  launch_auth::computeMac(KEY, 0x25, 7, 0x12345678, 1, mac);
  { LaunchAuth a(KEY, 1); a.renew(0x12345679); CHECK(!a.verify(0x25, 7, mac)); CHECK(!a.hasNonce()); }   // falsche nonce
  { uint8_t k2[16]; memcpy(k2, KEY, 16); k2[15] ^= 1;
    LaunchAuth a(k2, 1); a.renew(0x12345678); CHECK(!a.verify(0x25, 7, mac)); }                         // falscher Schlüssel
  { LaunchAuth a(KEY, 1); a.renew(0x12345678); CHECK(!a.verify(0x26, 7, mac)); }                          // ARM-MAC als LAUNCH
  { LaunchAuth a(KEY, 1); a.renew(0x12345678); CHECK(!a.verify(0x25, 8, mac)); }                          // andere Folgenummer
  { LaunchAuth a(KEY, 2); a.renew(0x12345678); CHECK(!a.verify(0x25, 7, mac)); }                          // andere Rakete
  { LaunchAuth a(KEY, 1); CHECK(!a.verify(0x25, 7, mac)); }                                               // keine nonce
  { uint8_t bad[8]; memcpy(bad, mac, 8); bad[0] ^= 0x80;
    LaunchAuth a(KEY, 1); a.renew(0x12345678); CHECK(!a.verify(0x25, 7, bad)); }                          // Bitfehler
}

static void zero_key_never_authenticates() {
  const uint8_t zero[16] = {0};
  CHECK(!launch_auth::keyUsable(zero));
  CHECK(launch_auth::keyUsable(KEY));
  uint8_t mac[8];
  launch_auth::computeMac(zero, 0x25, 1, 42, 1, mac);
  LaunchAuth a(zero, 1);
  a.renew(42);
  CHECK(!a.verify(0x25, 1, mac));
}

// ------------------------------------------------------------------ Zustandsautomat
static FlightParams fparams() {
  return FlightParams{FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M,
                      FS_LANDED_VZ_MS, FS_LANDED_ALT_M, FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS,
                      FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS, FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS,
                      FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS, false, LANDING_BURN_MAX_MS,
                      ARM_TIMEOUT_S * 1000, LAUNCH_COUNTDOWN_S * 1000, HEARTBEAT_TIMEOUT_MS, LAUNCH_THRUST_TIMEOUT_MS};
}

static FlightInputs pad(uint32_t t) {
  FlightInputs in;
  in.t_ms = t; in.calibrated = true; in.sensors_ok = true;
  in.a_norm_ms2 = G_MS2; in.a_axial_ms2 = G_MS2;
  in.launch_ready = true; in.heartbeat_age_ms = 100;
  return in;
}

// Takte von t bis t_end (ausschließlich) im Abstand 10 ms mit in als Vorlage
static uint32_t run(FlightStateMachine& f, FlightInputs in, uint32_t t, uint32_t t_end) {
  for (; t < t_end; t += 10) { in.t_ms = t; f.update(in); }
  return t;
}

static uint32_t to_armed(FlightStateMachine& f) {
  FlightInputs in = pad(1000);
  in.cmd = FlightCmd::PAD_READY; f.update(in);
  in = pad(1010); in.cmd = FlightCmd::ARM; f.update(in);
  return 1020;
}

static void launch_sequence_states_and_numbers() {
  CHECK_EQ((int)FlightState::SAFE, 0); CHECK_EQ((int)FlightState::PAD_READY, 1); CHECK_EQ((int)FlightState::BOOST, 2);
  CHECK_EQ((int)FlightState::ABORT, 7); CHECK_EQ((int)FlightState::LANDING_BURN, 8);
  CHECK_EQ((int)FlightState::ARMED, 9); CHECK_EQ((int)FlightState::COUNTDOWN, 10);
  CHECK_EQ((int)FlightState::IGNITION, 11); CHECK_EQ((int)FlightState::MISFIRE, 12);

  FlightStateMachine f(fparams());
  uint32_t t = to_armed(f);
  CHECK(f.state() == FlightState::ARMED);
  CHECK(f.launchSequence() && !f.launchAllowed());
  FlightInputs in = pad(t); in.cmd = FlightCmd::LAUNCH; f.update(in); t += 10;
  CHECK(f.state() == FlightState::COUNTDOWN);
  CHECK_EQ(f.countdownLeftMs(t - 10), LAUNCH_COUNTDOWN_S * 1000);
  t = run(f, pad(t), t, 1030 + LAUNCH_COUNTDOWN_S * 1000 - 10);
  CHECK(f.state() == FlightState::COUNTDOWN);
  t = run(f, pad(t), t, t + 20);
  CHECK(f.state() == FlightState::IGNITION);
  CHECK(f.lastEvent().reason == FlightReason::COUNTDOWN_END);
  CHECK(f.launchAllowed());
  const uint32_t t_ign = f.ignitionStartTime();
  // Schub nach 100 ms: Start nach launch_hold_ms erkannt
  t = run(f, pad(t), t, t_ign + 100);
  FlightInputs th = pad(t); th.a_norm_ms2 = 3 * G_MS2; th.a_axial_ms2 = 3 * G_MS2;
  t = run(f, th, t, t + FS_LAUNCH_HOLD_MS + 20);
  CHECK(f.state() == FlightState::BOOST);
  CHECK(f.onboardLaunch());
  CHECK(!f.launchSequence() && f.inFlight());
  CHECK_NEAR(f.launchTime(), t_ign + 100, 20);
}

static void arm_refused_without_preconditions_and_only_from_pad_ready() {
  FlightStateMachine f(fparams());
  FlightInputs in = pad(1000); in.cmd = FlightCmd::ARM;
  f.update(in);
  CHECK(f.state() == FlightState::SAFE);                 // nicht aus SAFE
  in = pad(1010); in.cmd = FlightCmd::PAD_READY; f.update(in);
  in = pad(1020); in.cmd = FlightCmd::LAUNCH; f.update(in);
  CHECK(f.state() == FlightState::PAD_READY);            // LAUNCH ohne ARM wirkt nicht
  in = pad(1030); in.cmd = FlightCmd::ARM; in.launch_ready = false;
  CHECK(f.update(in));                                   // Rückmeldung als Ereignis
  CHECK(f.state() == FlightState::PAD_READY);
  CHECK(f.lastEvent().reason == FlightReason::NOT_READY);
}

static void arm_timeout_and_heartbeat_loss() {
  { FlightStateMachine f(fparams());
    uint32_t t = to_armed(f);
    t = run(f, pad(t), t, 1010 + ARM_TIMEOUT_S * 1000 - 10);
    CHECK(f.state() == FlightState::ARMED);
    run(f, pad(t), t, t + 20);
    CHECK(f.state() == FlightState::SAFE);
    CHECK(f.lastEvent().reason == FlightReason::ARM_TIMEOUT); }
  { FlightStateMachine f(fparams());
    uint32_t t = to_armed(f);
    FlightInputs in = pad(t); in.heartbeat_age_ms = HEARTBEAT_TIMEOUT_MS;
    f.update(in);
    CHECK(f.state() == FlightState::ARMED);              // genau 1 s ist noch erlaubt
    in.t_ms += 10; in.heartbeat_age_ms = HEARTBEAT_TIMEOUT_MS + 1; f.update(in);
    CHECK(f.state() == FlightState::SAFE);
    CHECK(f.lastEvent().reason == FlightReason::HEARTBEAT_LOST); }
  { FlightStateMachine f(fparams());
    uint32_t t = to_armed(f);
    FlightInputs in = pad(t); in.cmd = FlightCmd::LAUNCH; f.update(in);
    in = pad(t + 2000); in.heartbeat_age_ms = 1500; f.update(in);
    CHECK(f.state() == FlightState::SAFE);               // auch im Countdown
    CHECK(f.lastEvent().reason == FlightReason::HEARTBEAT_LOST); }
}

static void precondition_lost_in_countdown() {
  FlightStateMachine f(fparams());
  uint32_t t = to_armed(f);
  FlightInputs in = pad(t); in.cmd = FlightCmd::LAUNCH; f.update(in);
  t = run(f, pad(t + 10), t + 10, t + 3000);
  CHECK(f.state() == FlightState::COUNTDOWN);
  in = pad(t); in.launch_ready = false; f.update(in);
  CHECK(f.state() == FlightState::SAFE);
  CHECK(f.lastEvent().reason == FlightReason::PRECOND_LOST);
}

static void abort_in_armed_countdown_ignition() {
  { FlightStateMachine f(fparams());
    uint32_t t = to_armed(f);
    FlightInputs in = pad(t); in.cmd = FlightCmd::ABORT; f.update(in);
    CHECK(f.state() == FlightState::SAFE); }             // nicht ABORT: der Motor hat nicht gezündet
  { FlightStateMachine f(fparams());
    uint32_t t = to_armed(f);
    FlightInputs in = pad(t); in.cmd = FlightCmd::LAUNCH; f.update(in);
    in = pad(t + 2000); in.cmd = FlightCmd::ABORT; f.update(in);
    CHECK(f.state() == FlightState::SAFE); }
  { FlightStateMachine f(fparams());
    uint32_t t = to_armed(f);
    FlightInputs in = pad(t); in.cmd = FlightCmd::LAUNCH; f.update(in);
    t = run(f, pad(t + 10), t + 10, t + 10 + LAUNCH_COUNTDOWN_S * 1000 + 10);
    CHECK(f.state() == FlightState::IGNITION);
    in = pad(t); in.cmd = FlightCmd::ABORT; f.update(in);
    CHECK(f.state() == FlightState::MISFIRE);            // Puls aus, Spätzünder möglich
    CHECK(!f.launchAllowed()); }
  { FlightStateMachine f(fparams());                     // bisheriges Verhalten: ABORT aus PAD_READY
    FlightInputs in = pad(1000); in.cmd = FlightCmd::PAD_READY; f.update(in);
    in = pad(1010); in.cmd = FlightCmd::ABORT; f.update(in);
    CHECK(f.state() == FlightState::ABORT); }
}

static uint32_t to_ignition(FlightStateMachine& f) {
  uint32_t t = to_armed(f);
  FlightInputs in = pad(t); in.cmd = FlightCmd::LAUNCH; f.update(in);
  return run(f, pad(t + 10), t + 10, t + 10 + LAUNCH_COUNTDOWN_S * 1000 + 10);
}

static void no_thrust_misfire_until_safe() {
  FlightStateMachine f(fparams());
  uint32_t t = to_ignition(f);
  CHECK(f.state() == FlightState::IGNITION);
  const uint32_t t_ign = f.ignitionStartTime();
  t = run(f, pad(t), t, t_ign + LAUNCH_THRUST_TIMEOUT_MS - 10);
  CHECK(f.state() == FlightState::IGNITION);
  t = run(f, pad(t), t, t + 20);
  CHECK(f.state() == FlightState::MISFIRE);
  CHECK(f.lastEvent().reason == FlightReason::THRUST_TIMEOUT);
  // bleibt: ABORT, PAD_READY, ARM, LAUNCH, fehlender Heartbeat, Vorbedingungen
  const FlightCmd cmds[] = {FlightCmd::ABORT, FlightCmd::PAD_READY, FlightCmd::ARM, FlightCmd::LAUNCH, FlightCmd::NONE};
  for (FlightCmd c : cmds) {
    FlightInputs in = pad(t); in.cmd = c; in.heartbeat_age_ms = 0xFFFFFFFF; in.launch_ready = false;
    f.update(in); t += 10;
    CHECK(f.state() == FlightState::MISFIRE);
  }
  t = run(f, pad(t), t, t + 60000);
  CHECK(f.state() == FlightState::MISFIRE);
  FlightInputs in = pad(t); in.cmd = FlightCmd::SAFE; f.update(in);
  CHECK(f.state() == FlightState::SAFE);
}

static void late_ignition_in_misfire_flies() {
  FlightStateMachine f(fparams());
  uint32_t t = to_ignition(f);
  t = run(f, pad(t), t, t + LAUNCH_THRUST_TIMEOUT_MS + 20);
  CHECK(f.state() == FlightState::MISFIRE);
  FlightInputs th = pad(t); th.a_norm_ms2 = 3 * G_MS2; th.a_axial_ms2 = 3 * G_MS2;
  run(f, th, t, t + FS_LAUNCH_HOLD_MS + 20);
  CHECK(f.state() == FlightState::BOOST);
  CHECK(f.onboardLaunch());
}

// ------------------------------------------------------------------ Startpuls
static PyroParams pparams() {
  return PyroParams{{PYRO_PULSE_MS, PYRO_PULSE_MS}, PYRO_MIN_FLIGHT_MS, PYRO_BACKUP_DELAY_MS, PYRO_RETRY_DELAY_MS,
                    PYRO_MAX_FIRES, true, LAUNCH_PULSE_MAX_MS};
}

static LaunchPulseInputs ready(uint32_t t) {
  LaunchPulseInputs in;
  in.t_ms = t; in.allowed = true; in.armed = true; in.continuity = true; in.continuity_valid = true;
  return in;
}

// Puls simulieren; end_at(t) liefert die geänderten Eingänge. Rückgabe: Einschaltdauer in ms
template <typename F>
static uint32_t pulse(PyroLogic& p, F change) {
  uint32_t on = 0;
  for (uint32_t t = 10000; t < 11000; t += 10) {
    LaunchPulseInputs in = ready(t);
    change(in);
    if (p.updateLaunch(in)) on += 10;
  }
  return on;
}

static void launch_pulse_ends_on_thrust_continuity_or_300ms() {
  { PyroLogic p(pparams());
    const uint32_t on = pulse(p, [](LaunchPulseInputs& in) { in.thrust = in.t_ms >= 10080; });
    CHECK_EQ(on, 80);
    CHECK_EQ(p.launchEndReason(), tlm::IGN_END_THRUST); }
  { PyroLogic p(pparams());
    const uint32_t on = pulse(p, [](LaunchPulseInputs& in) { in.continuity = in.t_ms < 10040; });
    CHECK_EQ(on, 40);
    CHECK_EQ(p.launchEndReason(), tlm::IGN_END_CONT_LOST); }
  { PyroLogic p(pparams());                         // Anzünder bleibt niederohmig: spätestens 300 ms
    const uint32_t on = pulse(p, [](LaunchPulseInputs&) {});
    CHECK_EQ(on, LAUNCH_PULSE_MAX_MS);
    CHECK_EQ(p.launchEndReason(), tlm::IGN_END_TIMEOUT);
    CHECK(p.launchUsed()); }
  { PyroLogic p(pparams());                         // Takt ohne Messlücke: Durchgang nicht auswerten
    const uint32_t on = pulse(p, [](LaunchPulseInputs& in) { in.continuity = in.continuity_valid = in.t_ms == 10000; });
    CHECK_EQ(on, LAUNCH_PULSE_MAX_MS); }
  { PyroLogic p(pparams());
    const uint32_t on = pulse(p, [](LaunchPulseInputs& in) { in.allowed = in.t_ms < 10050; });
    CHECK_EQ(on, 50);
    CHECK_EQ(p.launchEndReason(), tlm::IGN_END_STOPPED); }
  { PyroLogic p(pparams());
    const uint32_t on = pulse(p, [](LaunchPulseInputs& in) { in.armed = in.t_ms < 10030; });
    CHECK_EQ(on, 30);
    CHECK_EQ(p.launchEndReason(), tlm::IGN_END_DISARMED); }
}

static void launch_pulse_once_and_refused_without_continuity() {
  PyroLogic p(pparams());
  pulse(p, [](LaunchPulseInputs& in) { in.thrust = in.t_ms >= 10100; });
  CHECK(!p.launchFiring());
  CHECK_EQ(pulse(p, [](LaunchPulseInputs&) {}), 0);   // kein zweiter Puls im selben Ablauf
  p.resetLaunch();
  CHECK_EQ(pulse(p, [](LaunchPulseInputs&) {}), LAUNCH_PULSE_MAX_MS);   // neuer Ablauf nach SAFE
  PyroLogic q(pparams());
  CHECK_EQ(pulse(q, [](LaunchPulseInputs& in) { in.continuity = false; }), 0);
  CHECK_EQ(q.launchEndReason(), tlm::IGN_END_REFUSED);
  PyroLogic r(pparams());
  CHECK_EQ(pulse(r, [](LaunchPulseInputs& in) { in.allowed = false; }), 0);
  CHECK(!r.launchUsed());
}

static void gap_continuity_measurement() {
  const float arm = 7.6f, g = (float)LAUNCH_GAP_US, tau = PYRO_SENSE_TAU_US;
  const float rise = arm * (1.0f - expf(-g / tau));          // heiler Anzünder
  CHECK(gapContinuity(0.02f, 0.02f + rise, arm, g, tau, PYRO_GAP_RATIO));
  CHECK(!gapContinuity(0.02f, 0.03f, arm, g, tau, PYRO_GAP_RATIO));   // offen: bleibt fast 0
  CHECK(!gapContinuity(0.0f, 0.5f, 0.0f, g, tau, PYRO_GAP_RATIO));    // ohne Arming-Spannung keine Aussage
  CHECK(rise > 0.5f);                                          // deutlich messbar (ADC-Schritt ~3 mV)
}

// ------------------------------------------------------------------ Negativtest: Pyro 1 nur in IGNITION
static void pyro1_fires_only_in_ignition_all_states() {
  // jeder Zustand: Startkanal nur in IGNITION freigegeben
  for (int s = 0; s <= (int)FlightState::MISFIRE; ++s) {
    FlightStateMachine f(fparams());
    f.restore((FlightState)s, 1000, 2000, 3000, 10.f, 5000);
    const PyroGates g = pyroGates(f, true, LAUNCH_CH, PYRO_CH_CHUTE, PYRO_CH_IGNITER);
    CHECK_MSG(g.launch == ((FlightState)s == FlightState::IGNITION), "Zustand %d", s);
    if (f.launchSequence()) CHECK_MSG(!g.recovery[LAUNCH_CH], "Zustand %d", s);
  }
  // ganzer Ablauf mit günstigsten Eingängen (scharf, Durchgang auf beiden Kanälen die ganze Zeit,
  // also auch ein kurzgeschlossener abgebrannter Anzünder): Pyro 1 nur in IGNITION an
  FlightStateMachine f(fparams());
  PyroLogic p(pparams());
  FlightInputs in = pad(1000);
  bool fired_outside = false, fired_inside = false, backup_fired = false;
  float alt = 0, vz = 0;
  for (uint32_t t = 1000; t < 40000; t += 10) {
    in = pad(t);
    in.cmd = t == 1000 ? FlightCmd::PAD_READY : t == 1100 ? FlightCmd::ARM : t == 1200 ? FlightCmd::LAUNCH : FlightCmd::NONE;
    const bool burning = f.state() != FlightState::SAFE && f.ignitionStartTime() && t >= f.ignitionStartTime() + 120
                         && t < f.ignitionStartTime() + 3600;
    if (burning) { vz += 12.f * 0.01f; in.a_norm_ms2 = in.a_axial_ms2 = 12.f + G_MS2; }
    else if (alt > 0 || vz > 0) { vz = (f.state() == FlightState::DESCENT) ? -8.f : vz - G_MS2 * 0.01f; in.a_norm_ms2 = in.a_axial_ms2 = 0.3f; }
    alt += vz * 0.01f;
    if (alt < 0) { alt = 0; vz = 0; }
    in.alt_m = alt; in.baro_alt_m = alt; in.vz_ms = vz;
    in.pyro_done = p.done();
    f.update(in);
    const PyroGates g = pyroGates(f, true, LAUNCH_CH, PYRO_CH_CHUTE, PYRO_CH_IGNITER);
    PyroInputs pi;
    pi.t_ms = t; pi.t_launch_ms = f.launchTime(); pi.allowed[0] = g.recovery[0]; pi.allowed[1] = g.recovery[1];
    pi.armed = true; pi.continuity[0] = pi.continuity[1] = true; pi.fitted[0] = pi.fitted[1] = true;
    bool fire[2];
    p.update(pi, fire);
    LaunchPulseInputs li = ready(t); li.allowed = g.launch; li.thrust = in.a_norm_ms2 > FS_LAUNCH_ACCEL_MS2;
    const bool launch = p.updateLaunch(li);
    const bool ch0 = fire[0] || launch;
    if (ch0 && f.state() != FlightState::IGNITION) fired_outside = true;
    if (ch0 && f.state() == FlightState::IGNITION) fired_inside = true;
    if (fire[1]) backup_fired = true;
  }
  CHECK(fired_inside);
  CHECK(!fired_outside);
  CHECK(backup_fired);                                 // Kanal 2 bleibt Reserve der Bergung
  CHECK(f.onboardLaunch());
  CHECK(f.state() == FlightState::LANDED);
}

// ------------------------------------------------------------------ Bausteine
static void preconditions_bits() {
  LaunchPreconditions pc(PrecondParams{LAUNCH_MIN_VBAT1_V, LAUNCH_MIN_VBAT2_V, LAUNCH_STILL_DPS, LAUNCH_STILL_HOLD_MS,
                                       LAUNCH_MAX_TILT_DEG});
  PrecondInputs in;
  in.armed = true; in.continuity = true; in.vbat1_V = 4.0f; in.vbat2_V = 8.0f; in.omega_max_dps = 0.5f;
  in.tilt_deg = 3.f; in.sensors_ok = in.calibrated = in.logging = true; in.servo_test_ok = true; in.launch_enabled = true;
  in.t_ms = 1000; pc.update(in);
  CHECK(!(pc.mask() & tlm::PRE_STILL));                // erst nach 2 s ruhig
  in.t_ms = 1000 + LAUNCH_STILL_HOLD_MS; pc.update(in);
  CHECK_EQ(pc.mask(), tlm::PRE_ALL);
  CHECK(pc.allOk());
  struct { void (*f)(PrecondInputs&); uint8_t bit; } cases[] = {
    {[](PrecondInputs& i) { i.armed = false; }, tlm::PRE_ARM_V},
    {[](PrecondInputs& i) { i.continuity = false; }, tlm::PRE_CONT},
    {[](PrecondInputs& i) { i.vbat2_V = 6.5f; }, tlm::PRE_BATT},
    {[](PrecondInputs& i) { i.vbat1_V = 3.3f; }, tlm::PRE_BATT},
    {[](PrecondInputs& i) { i.tilt_deg = LAUNCH_MAX_TILT_DEG + 1; }, tlm::PRE_STILL},
    {[](PrecondInputs& i) { i.logging = false; }, tlm::PRE_SENSORS},
    {[](PrecondInputs& i) { i.calibrated = false; }, tlm::PRE_SENSORS},
    {[](PrecondInputs& i) { i.servo_test_ok = false; }, tlm::PRE_SERVO},
    {[](PrecondInputs& i) { i.launch_enabled = false; }, tlm::PRE_KEY},
  };
  for (auto& c : cases) {
    PrecondInputs x = in; c.f(x);
    LaunchPreconditions q = pc;
    q.update(x);
    CHECK_MSG(!(q.mask() & c.bit) && !q.allOk(), "Bit 0x%02X", c.bit);
  }
  // Wackeln setzt die 2 s zurück
  in.t_ms += 10; in.omega_max_dps = 20.f; pc.update(in);
  CHECK(!(pc.mask() & tlm::PRE_STILL));
  in.t_ms += 10; in.omega_max_dps = 0.5f; pc.update(in);
  CHECK(!(pc.mask() & tlm::PRE_STILL));
  CHECK(pc.mask() & tlm::PRE_ARM_V);
}

static void servo_self_test_sequence() {
  ServoSelfTest st(SERVO_TEST_DEG, SERVO_TEST_STEP_MS, 0.0f);
  CHECK(!st.passed());
  st.start(1000);
  float yaw_max = 0, yaw_min = 0, pitch_max = 0, pitch_min = 0;
  for (uint32_t t = 1000; t < 1000 + 7 * SERVO_TEST_STEP_MS; t += 10) {
    const ServoTestOutput o = st.update(t, 0.f);
    if (o.yaw_off_deg > yaw_max) yaw_max = o.yaw_off_deg;
    if (o.yaw_off_deg < yaw_min) yaw_min = o.yaw_off_deg;
    if (o.pitch_off_deg > pitch_max) pitch_max = o.pitch_off_deg;
    if (o.pitch_off_deg < pitch_min) pitch_min = o.pitch_off_deg;
    if (o.yaw_off_deg != 0 && o.pitch_off_deg != 0) CHECK(false);   // nie beide zugleich
  }
  CHECK_NEAR(yaw_max, SERVO_TEST_DEG, 1e-6); CHECK_NEAR(yaw_min, -SERVO_TEST_DEG, 1e-6);
  CHECK_NEAR(pitch_max, SERVO_TEST_DEG, 1e-6); CHECK_NEAR(pitch_min, -SERVO_TEST_DEG, 1e-6);
  CHECK(st.passed());
  CHECK(!st.update(5000, 0.f).active);                 // danach Mitte
  ServoSelfTest needs_current(SERVO_TEST_DEG, SERVO_TEST_STEP_MS, 0.15f);
  needs_current.start(0);
  for (uint32_t t = 0; t < 2000; t += 10) needs_current.update(t, 0.05f);
  CHECK(needs_current.finished() && !needs_current.passed());
  needs_current.start(3000);
  for (uint32_t t = 3000; t < 5000; t += 10) needs_current.update(t, t == 3300 ? 0.4f : 0.05f);
  CHECK(needs_current.passed());
  needs_current.reset();
  CHECK(!needs_current.passed());
}

static void signal_patterns() {
  CHECK(!launchSignal(FlightState::PAD_READY, 0, 0).active);
  CHECK(launchSignal(FlightState::ARMED, 50, 0).beep);
  CHECK(!launchSignal(FlightState::ARMED, 500, 0).beep);
  CHECK(!launchSignal(FlightState::ARMED, 600, 0).led_on);
  CHECK(!launchSignal(FlightState::COUNTDOWN, 150, 3000).beep);  // schnell: 100 an, 150 aus
  CHECK(launchSignal(FlightState::COUNTDOWN, 4150, 900).beep);   // letzte Sekunde Dauerton
  int beeps = 0; bool last = false;
  for (uint32_t t = 0; t < 1500; t += 10) {
    const bool b = launchSignal(FlightState::MISFIRE, t, 0).beep;
    if (b && !last) ++beeps;
    last = b;
  }
  CHECK_EQ(beeps, 3);                                             // Dreiertakt
}

static void ignition_recorder_payload() {
  IgnitionRecorder r;
  r.begin(50000, 7.80f);
  r.pulseOn(50010);
  for (int i = 0; i < 80; ++i) r.armSample(i == 40 ? 6.912f : 7.5f);
  r.vbat1Sample(3.95f); r.vbat1Sample(3.90f);
  r.contLost(50050);
  r.pulseOff(50050, tlm::IGN_END_CONT_LOST);
  r.thrust(50130);
  const tlm::IgnPayload p = r.payload();
  CHECK_EQ(p.t_pulse_on_ms, 10); CHECK_EQ(p.t_cont_lost_ms, 50); CHECK_EQ(p.t_pulse_off_ms, 50);
  CHECK_EQ(p.t_thrust_ms, 130);
  CHECK_EQ(p.arm_before_mv, 7800); CHECK_EQ(p.arm_min_mv, 6912); CHECK_EQ(p.vbat1_min_mv, 3900);
  CHECK_EQ(p.arm_samples, 80); CHECK_EQ(p.end_reason, tlm::IGN_END_CONT_LOST);
  IgnitionRecorder none;
  none.begin(1000, 0.f);
  none.refused();
  const tlm::IgnPayload q = none.payload();
  CHECK_EQ(q.t_pulse_on_ms, tlm::IGN_NO_TIME); CHECK_EQ(q.t_thrust_ms, tlm::IGN_NO_TIME);
  CHECK_EQ(q.arm_min_mv, 0); CHECK_EQ(q.end_reason, tlm::IGN_END_REFUSED);
}

static void log_ring_fifo() {
  LogRing<int, 4> r;
  for (int i = 0; i < 6; ++i) r.push(i);       // 0 und 1 fallen heraus
  CHECK_EQ(r.size(), 4);
  int v, expect = 2;
  bool ordered = true;
  while (r.pop(v)) ordered = ordered && v == expect++;
  CHECK(ordered && expect == 6);
  CHECK(r.empty());
}

void run_tests_launch() {
  RUN_TEST(sha256_fips_vectors);
  RUN_TEST(hmac_rfc4231_vectors);
  RUN_TEST(mac_accepts_right_nonce_only_once);
  RUN_TEST(mac_rejects_wrong_nonce_key_type_seq_id);
  RUN_TEST(zero_key_never_authenticates);
  RUN_TEST(launch_sequence_states_and_numbers);
  RUN_TEST(arm_refused_without_preconditions_and_only_from_pad_ready);
  RUN_TEST(arm_timeout_and_heartbeat_loss);
  RUN_TEST(precondition_lost_in_countdown);
  RUN_TEST(abort_in_armed_countdown_ignition);
  RUN_TEST(no_thrust_misfire_until_safe);
  RUN_TEST(late_ignition_in_misfire_flies);
  RUN_TEST(launch_pulse_ends_on_thrust_continuity_or_300ms);
  RUN_TEST(launch_pulse_once_and_refused_without_continuity);
  RUN_TEST(gap_continuity_measurement);
  RUN_TEST(pyro1_fires_only_in_ignition_all_states);
  RUN_TEST(preconditions_bits);
  RUN_TEST(servo_self_test_sequence);
  RUN_TEST(signal_patterns);
  RUN_TEST(ignition_recorder_payload);
  RUN_TEST(log_ring_fifo);
}
