// main.cpp – Flug-Firmware des Teensy-4.1-Flugcomputers (Kartonaut)
//
// Ablauf pro Takt (LOOP_HZ, siehe Config.h):
//   1. Sensoren lesen (Sensors.h, Rückende je Board), auf dem Pad kalibrieren
//   2. Lage als Gyro-Quaternion fortschreiben (Attitude.h), Kippwinkel in Servoachsen
//   3. Kalman-Filter für Höhe und Vertikalgeschwindigkeit
//   4. Flugzustandsautomat (FlightState.h) mit Kommandos vom Boden oder von USB
//   5. Regler Pitch/Yaw (nur in BOOST) und Roll, Servos und H-Brücke
//   6. Pyro (Pyro.h): nur in APOGEE/DESCENT mit ARM und Durchgang; Startpuls nur in IGNITION
//   7. Telemetrie 10 Hz (Telemetry.h) über Serial8, Ereignisse sofort
//   8. Log-Frame auf die SD-Karte, Zustandsspeicher, Watchdog füttern
//
// Motorstart an Bord (docs/Plan_Bordzuendung_2026-10-27.md): ARM und LAUNCH kommen per Funk mit MAC
// (LaunchAuth.h), die Vorbedingungen und Anzeigen stehen in LaunchControl.h, der Startpuls in Pyro.h.
// Während des Pulses misst loop() VBAT_ARMED außerhalb des Takts mit 1 kHz und den Durchgang je Takt
// in einer Messlücke; nach IGNITION geht einmal der IGN-Rahmen raus.
//
// Nach einem Watchdog-Neustart im Flug nimmt die Firmware den Zustand aus dem
// Zustandsspeicher wieder auf (StateStore.h), statt in SAFE auf dem Pad zu beginnen.
#include <Arduino.h>
#include "Config.h"
#include "MathTypes.h"
#include "Indicators.h"
#include "Sensors.h"
#include "Attitude.h"
#include "KalmanZ.h"
#include "Control.h"
#include "FlightState.h"
#include "Pyro.h"
#include "Telemetry.h"
#include "Timing.h"
#include "SDLogger.h"
#include "CalStore.h"     // Kalibrierwerte aus dem EEPROM-Emulat (revb_test: "cal save")
#include "Watchdog.h"
#include "StateStore.h"
#include "LandingBurn.h"
#include "ThrustCurveE12.h"
#include "ThrottleLaw.h"
#include "LaunchAuth.h"
#include "LaunchControl.h"
#include "Sha256.h"
#include "E22Config.h"

HardwareSerial& radio = Serial8;   // HC-12 heute, E22-400T22S auf rev B (transparenter Modus)

// ======= Zustand =======
static LoopTimer loopTimer;
static Attitude  attitude;
static KalmanZ   kal;
static FlightStateMachine fsm(FlightParams{
    FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M, FS_LANDED_VZ_MS, FS_LANDED_ALT_M,
    FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS, FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS,
    FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS, FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS,
    RECOVERY_MODE == RecoveryMode::LANDING_BURN, LANDING_BURN_MAX_MS,
    ARM_TIMEOUT_S * 1000, LAUNCH_COUNTDOWN_S * 1000, HEARTBEAT_TIMEOUT_MS, LAUNCH_THRUST_TIMEOUT_MS});
static PyroLogic pyro(PyroParams{{PYRO_PULSE_MS, RECOVERY_MODE == RecoveryMode::LANDING_BURN ? PYRO_IGNITER_PULSE_MS : PYRO_PULSE_MS},
                                 PYRO_MIN_FLIGHT_MS, PYRO_BACKUP_DELAY_MS, PYRO_RETRY_DELAY_MS, PYRO_MAX_FIRES,
                                 RECOVERY_MODE == RecoveryMode::CHUTE, LAUNCH_PULSE_MAX_MS});
static LandingPlanner landing(LandingParams{LANDING_MASS_KG, LANDING_FUEL_KG, LANDING_CD_A_M2, LANDING_RHO,
                                            LANDING_IGNITER_DELAY_S, 1.0f / LOOP_HZ, LANDING_MIN_SPEED_MS,
                                            LANDING_THRUST_SCALE},
                              thrustcurve::E12_T_S, thrustcurve::E12_F_N, thrustcurve::E12_N);
static ThrottleLaw throttle(ThrottleLawParams{THROTTLE_F_MIN, THROTTLE_H_RESERVE_M, THROTTLE_T_GO_MARGIN_S, THROTTLE_T_GO_MIN_S,
                                              THROTTLE_KV, THROTTLE_V_FINAL_MS, THROTTLE_H_FINAL_M, THROTTLE_H_CUT_M,
                                              THROTTLE_AFTER_S, THROTTLE_ACT_TAU_S, THROTTLE_SCALE_PLAN},
                            LandingParams{LANDING_MASS_KG, LANDING_FUEL_KG, LANDING_CD_A_M2, LANDING_RHO,
                                          LANDING_IGNITER_DELAY_S, 1.0f / LOOP_HZ, LANDING_MIN_SPEED_MS, THROTTLE_SCALE_PLAN},
                            thrustcurve::E12_T_S, thrustcurve::E12_F_N, thrustcurve::E12_N);
static float throttle_u = 0.0f;
static tlm::Parser radioParser;

// Motorstart an Bord
constexpr int PIN_LAUNCH = (LAUNCH_CH == 0) ? PIN_PYRO1 : PIN_PYRO2;
static LaunchAuth auth(LAUNCH_KEY, ROCKET_ID);
static LaunchPreconditions preconds(PrecondParams{LAUNCH_MIN_VBAT1_V, LAUNCH_MIN_VBAT2_V, LAUNCH_STILL_DPS,
                                                  LAUNCH_STILL_HOLD_MS, LAUNCH_MAX_TILT_DEG});
static ServoSelfTest servoTest(SERVO_TEST_DEG, SERVO_TEST_STEP_MS, SERVO_TEST_MIN_A);
static IgnitionRecorder ign;
static bool     launch_fire = false;          // Sollzustand des Startkanals
static bool     gap_cont = false;             // Durchgang aus der letzten Messlücke
static uint32_t last_cmd_ms = 0;              // letztes Kommando vom Boden (Heartbeat)
static uint32_t state_since_ms = 0;           // Eintritt in den aktuellen Zustand
static uint32_t last_arm_sample_us = 0;
static float    arm_loop_min_V = 1e9f;        // kleinste VBAT_ARMED der schnellen Messung in diesem Takt
static LaunchSignal last_signal;
static FlightState pending_before = FlightState::SAFE;

// Log-Frames laufen in SAFE und PAD_READY durch einen Ringpuffer (Verzögerung LOG_PRE_ARM_MS): fällt ein
// Frame hinten heraus, wird er mit der Pad-Rate geschrieben oder verworfen. Ab ARMED (und im Flug) wird
// der Puffer mit LOG_RING_DRAIN_PER_LOOP Frames je Takt geleert; so stehen die 2 s vor ARMED mit voller
// Rate im Log und die Zeitmarken bleiben in Reihenfolge.
struct RingFrame { SDFrame f; uint32_t ts_us; uint32_t loop; };
static LogRing<RingFrame, size_t(LOG_PRE_ARM_MS * LOOP_HZ / 1000)> logRing;

static SensorSample sample;
static float a_norm_filt = G_MS2;
static float alt_m = 0.f, vz_ms = 0.f;
static float tilt_x_deg = 0.f, tilt_y_deg = 0.f, roll_deg = 0.f;
static PyOutput   py;
static RollOutput roll;
static bool  pyro_fire[2] = {false, false};
static bool  calibrating = false;
static bool  restored = false;
static ResetCause reset_cause = ResetCause::OTHER;
static uint32_t clock_offset_ms = 0;    // Fortsetzung der Zeitachse nach einem Neustart
static FlightCmd pending_cmd = FlightCmd::NONE;
static uint8_t  pending_cmd_type = 0, pending_cmd_seq = 0;
static bool     pending_ack = false;
static uint8_t  tlm_seq = 0;
static uint32_t last_tlm_ms = 0;
static uint32_t loops = 0, log_frames = 0;
static bool     log_exported = false, log_closed = false;
static uint8_t  flags = 0;

static inline uint32_t clock_ms() { return millis() + clock_offset_ms; }
static inline uint32_t flight_ms(uint32_t t) { return fsm.launchTime() ? t - fsm.launchTime() : t; }

// ======= Zufallszahlen (TRNG des i.MX RT1062) für die nonce =======
// Der TRNG liefert 512 bit je Lauf (ENT0..15); das Lesen von ENT15 startet den nächsten Lauf.
// trngPoll() holt fertige Worte ohne zu warten in einen Vorrat, trngNext() nimmt daraus.
static uint32_t trng_pool[16];
static int      trng_n = 0;

static void trngBegin() {
  CCM_CCGR6 |= CCM_CCGR6_TRNG(CCM_CCGR_ON);
  TRNG_MCTL = TRNG_MCTL_RST_DEF | TRNG_MCTL_PRGM;   // Programmiermodus, Standardwerte
  TRNG_MCTL = TRNG_MCTL_SAMP_MODE(2);               // Laufmodus, von-Neumann-Entzerrung
  (void)TRNG_ENT15;                                 // ersten Lauf starten
}

static void trngPoll() {
  if (trng_n > 0) return;
  if (TRNG_MCTL & TRNG_MCTL_ERR) { trngBegin(); return; }
  if (!(TRNG_MCTL & TRNG_MCTL_ENT_VAL)) return;
  volatile uint32_t* ent = &TRNG_ENT0;
  for (int i = 0; i < 16; ++i) trng_pool[i] = ent[i];   // ENT15 zuletzt: nächster Lauf
  trng_n = 16;
}

static uint32_t trngNext() {
  const uint32_t t0 = millis();
  while (trng_n == 0 && millis() - t0 < 20) trngPoll();
  if (trng_n > 0) return trng_pool[--trng_n];
  // Rückfall (TRNG nicht bereit): Zähler und Zeit mischen, nie zweimal derselbe Wert
  static uint32_t ctr = 0;
  uint8_t buf[12], h[32];
  const uint32_t a = ARM_DWT_CYCCNT, b = micros(), c = ++ctr;
  memcpy(buf, &a, 4); memcpy(buf + 4, &b, 4); memcpy(buf + 8, &c, 4);
  sha256(buf, sizeof buf, h);
  uint32_t r; memcpy(&r, h, 4);
  Serial.println("WARNUNG: TRNG nicht bereit, nonce aus Zeitgeber");
  return r;
}

// ======= E22 (rev B): Register beim Start prüfen, nur bei Abweichung schreiben =======
// Ab Werk steht das Modul auf 2,4 kbit/s; Rakete und Laptop (tools/ground/e22_config.py) müssen dieselben
// Werte aus Config.h haben. Konfiguration: M0 = 0, M1 = 1, 9600 Bd; Lesen C1 00 09, Schreiben C0 00 09.
#ifdef BOARD_REVB
static bool e22WaitAux(uint32_t timeout_ms) {
  const uint32_t t0 = millis();
  while (!digitalRead(PIN_RADIO_AUX)) {
    if (millis() - t0 > timeout_ms) return false;
    delay(1);
  }
  return true;
}

static void e22Mode(bool config) {
  digitalWrite(PIN_RADIO_M0, LOW);
  digitalWrite(PIN_RADIO_M1, config ? HIGH : LOW);
  delay(10);
  e22WaitAux(500);
  delay(10);
}

static bool e22Reply(uint8_t* buf, size_t n, uint32_t timeout_ms) {
  size_t got = 0;
  const uint32_t t0 = millis();
  while (got < n && millis() - t0 < timeout_ms) {
    if (radio.available()) buf[got++] = (uint8_t)radio.read();
  }
  return got == n;
}

static void e22Configure() {
  pinMode(PIN_RADIO_M0, OUTPUT); pinMode(PIN_RADIO_M1, OUTPUT); pinMode(PIN_RADIO_AUX, INPUT);
  e22Mode(true);
  while (radio.available()) radio.read();
  uint8_t want[e22::REG_COUNT];
  e22::wantedRegs(want, false);
  const uint8_t rd[3] = {0xC1, 0x00, e22::REG_COUNT};
  radio.write(rd, sizeof rd);
  uint8_t rep[3 + e22::REG_COUNT];
  bool ok = e22Reply(rep, sizeof rep, 300) && rep[0] == 0xC1;
  if (ok && memcmp(rep + 3, want, e22::REG_COUNT) != 0) {
    uint8_t wr[3 + e22::REG_COUNT] = {0xC0, 0x00, e22::REG_COUNT};
    memcpy(wr + 3, want, e22::REG_COUNT);
    while (radio.available()) radio.read();
    radio.write(wr, sizeof wr);
    ok = e22Reply(rep, sizeof rep, 500) && rep[0] == 0xC1 && memcmp(rep + 3, want, e22::REG_COUNT) == 0;
    Serial.printf("E22: Register %s\n", ok ? "neu geschrieben" : "FEHLER beim Schreiben");
  } else {
    Serial.printf("E22: %s\n", ok ? "Register stimmen" : "keine Antwort im Konfigurationsmodus");
  }
  e22Mode(false);                                   // transparent
}
#endif

// ======= Telemetrie =======
static void sendFrame(uint8_t type, const void* payload, size_t n) {
  uint8_t buf[tlm::MAX_PAYLOAD + tlm::OVERHEAD];
  const size_t len = tlm::encode(type, (const uint8_t*)payload, n, buf, sizeof buf);
  if (len) radio.write(buf, len);
}

static void sendEvent(const FlightEvent& e) {
  tlm::EvtPayload p{flight_ms(e.t_ms), (uint8_t)e.from, (uint8_t)e.to, (uint8_t)e.reason};
  sendFrame(tlm::EVT, &p, sizeof p);
  Serial.printf("[%lu ms] %s -> %s (Grund %u)\n", (unsigned long)e.t_ms, flightStateName(e.from),
                flightStateName(e.to), (unsigned)e.reason);
}

static void sendAck(uint8_t cmd, uint8_t seq, uint8_t result) {
  tlm::AckPayload p{cmd, seq, result, (uint8_t)fsm.state()};
  sendFrame(tlm::ACK, &p, sizeof p);
}

// ACK auf PING, ARM und LAUNCH: mit nonce, Vorbedingungen und Countdown
static void sendAckAuth(uint8_t cmd, uint8_t seq, uint8_t result) {
  const uint32_t left = fsm.countdownLeftMs(clock_ms());
  tlm::AckAuthPayload p{cmd, seq, result, (uint8_t)fsm.state(), auth.nonce(), preconds.mask(),
                        (uint16_t)(left > 65535 ? 65535 : left)};
  sendFrame(tlm::ACK, &p, sizeof p);
}

static void sendIgnition() {
  const tlm::IgnPayload p = ign.payload();
  sendFrame(tlm::IGN, &p, sizeof p);
  Serial.printf("IGN: an %u ms, Durchgang weg %u ms, Schub %u ms, aus %u ms, Grund %u; ARM %u -> %u mV "
                "(%u Messungen), 1S min %u mV\n", p.t_pulse_on_ms, p.t_cont_lost_ms, p.t_thrust_ms, p.t_pulse_off_ms,
                p.end_reason, p.arm_before_mv, p.arm_min_mv, p.arm_samples, p.vbat1_min_mv);
}

static void sendTelemetry(uint32_t t) {
  tlm::TlmPayload p{};
  p.state = (uint8_t)fsm.state();
  p.flags = flags;
  const uint32_t ds = flight_ms(t) / 100;
  p.t_ds = ds > 65535 ? 65535 : (uint16_t)ds;
  p.alt_dm = tlm::clamp_i16(alt_m * 10.f);
  p.vz_cms = tlm::clamp_i16(vz_ms * 100.f);
  p.tilt_x_hd = tlm::clamp_i8(tilt_x_deg * 2.f);
  p.tilt_y_hd = tlm::clamp_i8(tilt_y_deg * 2.f);
  p.roll_2d = tlm::clamp_i8(roll_deg / 2.f);
  p.tvc_y_dd = tlm::clamp_i8(py.yaw_tvc_deg * 10.f);
  p.tvc_p_dd = tlm::clamp_i8(py.pitch_tvc_deg * 10.f);
  p.vbat1_20mv = tlm::clamp_u8(sample.vbat1_V / 0.02f);
  p.vbat2_50mv = tlm::clamp_u8(sample.vbat2_V / 0.05f);
  p.seq = tlm_seq++;
  sendFrame(tlm::TLM, &p, sizeof p);
}

static void queueCommand(FlightCmd cmd, uint8_t type, uint8_t seq) {
  if (pending_cmd == FlightCmd::ABORT && cmd != FlightCmd::ABORT) {   // Abbruch hat Vorrang
    sendAck(type, seq, tlm::ACK_REFUSED);
    return;
  }
  pending_cmd = cmd; pending_cmd_type = type; pending_cmd_seq = seq; pending_ack = true;
}

static void handleCommand(uint8_t type, const uint8_t* payload, size_t len) {
  const uint8_t seq = len ? payload[0] : 0;
  switch (type) {
    case tlm::CMD_PING:
      // in PAD_READY trägt die Antwort die nonce A für ARM (in ARMED die nonce B für LAUNCH)
      if (fsm.state() == FlightState::PAD_READY && !auth.hasNonce()) auth.renew(trngNext());
      sendAckAuth(type, seq, tlm::ACK_OK);
      break;
    case tlm::CMD_HEARTBEAT:
      break;                                          // nur Lebenszeichen (last_cmd_ms), kein ACK
    case tlm::CMD_ARM:
    case tlm::CMD_LAUNCH: {
      const bool arm = type == tlm::CMD_ARM;
      if (len < sizeof(tlm::CmdAuthPayload)
          || fsm.state() != (arm ? FlightState::PAD_READY : FlightState::ARMED)) {
        sendAckAuth(type, seq, tlm::ACK_REFUSED);
        break;
      }
      const bool ok = auth.verify(type, seq, payload + 1);   // nonce ist jetzt verbraucht
      // neue nonce: nach ARM die nonce B für LAUNCH (bei Ablehnung die nächste A);
      // nach falschem LAUNCH eine neue B, nach gültigem LAUNCH keine mehr
      if (arm || !ok) auth.renew(trngNext());
      if (!ok) { sendAckAuth(type, seq, tlm::ACK_AUTH); break; }
      queueCommand(arm ? FlightCmd::ARM : FlightCmd::LAUNCH, type, seq);
      break;
    }
    case tlm::CMD_CALIBRATE:
      if (fsm.state() == FlightState::SAFE || fsm.state() == FlightState::PAD_READY) {
        Sensors_calibrateStart(); calibrating = true;
        sendAck(type, seq, tlm::ACK_OK);
      } else sendAck(type, seq, tlm::ACK_REFUSED);
      break;
    case tlm::CMD_PAD_READY: queueCommand(FlightCmd::PAD_READY, type, seq); break;
    case tlm::CMD_ABORT:     queueCommand(FlightCmd::ABORT, type, seq); break;
    case tlm::CMD_SAFE:      queueCommand(FlightCmd::SAFE, type, seq); break;
    default:
      sendAck(type, seq, tlm::ACK_UNKNOWN);
  }
}

static void pollRadio() {
  while (radio.available()) {
    if (radioParser.feed((uint8_t)radio.read())) {
      if (radioParser.type() >= tlm::CMD_PING) last_cmd_ms = clock_ms();   // jedes Kommando ist ein Lebenszeichen
      handleCommand(radioParser.type(), radioParser.payload(), radioParser.length());
    }
  }
  // Tischtest ohne Bodenstation: Einzelbuchstaben auf USB-Serial
  while (Serial.available()) {
    const char c = (char)Serial.read();
    switch (c) {
      // ARM und LAUNCH gibt es hier bewusst nicht: nur per Funk mit MAC (tools/ground/launch.py)
      case 'c': handleCommand(tlm::CMD_CALIBRATE, nullptr, 0); break;
      case 'r': handleCommand(tlm::CMD_PAD_READY, nullptr, 0); break;
      case 'a': handleCommand(tlm::CMD_ABORT, nullptr, 0); break;
      case 's': handleCommand(tlm::CMD_SAFE, nullptr, 0); break;
      case '?':
        Serial.printf("Zustand %s, kalibriert %d, IMU %d Baro %d Power %d, Reset: %s%s, Watchdog %s\n",
                      flightStateName(fsm.state()), (int)Sensors_calibrated(), (int)Sensors_status().imu_ok,
                      (int)Sensors_status().baro_ok, (int)Sensors_status().power_ok, resetCauseName(reset_cause),
                      restored ? " (Flug wiederaufgenommen)" : "", WDT_ENABLED ? "an" : "aus");
        Serial.printf("Lage: Kipp x %.2f y %.2f gesamt %.2f Roll %.1f; Hoehe %.2f vz %.2f; |a| %.2f; "
                      "ARM %d Durchgang %d/%d, Akkus %.2f/%.2f V\n",
                      tilt_x_deg, tilt_y_deg, attitude.tiltTotalDeg(), roll_deg, alt_m, vz_ms, sample.a_norm,
                      (int)sample.armed, (int)sample.continuity[0], (int)sample.continuity[1], sample.vbat1_V, sample.vbat2_V);
        Serial.printf("Start: Vorbedingungen 0x%02X von 0x%02X, Schluessel %s, Servotest %s (Spitze %.2f A)\n",
                      preconds.mask(), tlm::PRE_ALL, LAUNCH_ENABLED ? "da" : "FEHLT",
                      servoTest.passed() ? "ok" : (servoTest.running() ? "laeuft" : "offen"), servoTest.peakCurrent());
        break;
      default: break;
    }
  }
}

// ======= Zustandsspeicher =======
static void saveState(uint32_t t) {
  SavedState s{};
  s.state = (uint8_t)fsm.state();
  s.calibrated = Sensors_calibrated();
  s.flags = flags;
  s.uptime_ms = t;
  s.t_launch_ms = fsm.launchTime(); s.t_burnout_ms = fsm.burnoutTime(); s.t_apogee_ms = fsm.apogeeTime();
  Vec3 gb; float p0 = 0; Sensors_getBias(gb, p0); s.ground_p_pa = p0;
  s.gyro_bias_dps[0] = gb.x; s.gyro_bias_dps[1] = gb.y; s.gyro_bias_dps[2] = gb.z;
  s.alt_offset_m = 0;
  s.baro_max_m = fsm.maxBaroAlt();
  s.q[0] = attitude.q.w; s.q[1] = attitude.q.x; s.q[2] = attitude.q.y; s.q[3] = attitude.q.z;
  s.alt_m = alt_m; s.vz_ms = vz_ms;
  s.pyro_fires[0] = pyro.fires(0); s.pyro_fires[1] = pyro.fires(1);
  s.restarts = restored ? 1 : 0;
  StateStore_save(s);
}

static bool tryRestore() {
  SavedState s;
  if (!StateStore_restore(s)) return false;
  FlightState st = (FlightState)s.state;
  // Neustart während IGNITION: der Puls ist aus, der Motor kann noch zünden -> MISFIRE (Starterkennung an).
  // ARMED/COUNTDOWN werden nicht fortgesetzt: frischer Start in SAFE, neues ARM nötig.
  if (st == FlightState::IGNITION) st = FlightState::MISFIRE;
  const bool in_flight = st == FlightState::BOOST || st == FlightState::COAST || st == FlightState::APOGEE
                         || st == FlightState::DESCENT || (st == FlightState::ABORT && s.t_launch_ms != 0);
  if (!in_flight && st != FlightState::PAD_READY && st != FlightState::MISFIRE) return false;
  // Zeitachse fortsetzen: der Neustart kostete etwa Watchdog-Zeit plus Bootzeit
  clock_offset_ms = s.uptime_ms + WDT_TIMEOUT_MS + 300;
  Sensors_setBias(Vec3(s.gyro_bias_dps[0], s.gyro_bias_dps[1], s.gyro_bias_dps[2]), s.ground_p_pa);
  attitude.q = Quaternion(s.q[0], s.q[1], s.q[2], s.q[3]); attitude.q.normalize(); attitude.initialized = true;
  kal.setState(s.alt_m, s.vz_ms);
  alt_m = s.alt_m; vz_ms = s.vz_ms;
  flags = s.flags | tlm::FLAG_RESTORED;
  pyro.restore(s.pyro_fires[0], s.pyro_fires[1]);
  fsm.restore(st, s.t_launch_ms, s.t_burnout_ms, s.t_apogee_ms, s.baro_max_m, clock_ms());
  restored = true;
  return true;
}

// ======= Anzeige je Zustand =======
static void indicateState(FlightState s) {
  switch (s) {
    case FlightState::LANDING_BURN: Indicate_color(60, 30, 0); break;
    case FlightState::SAFE:      Indicate_color(0, 0, 40); break;
    case FlightState::PAD_READY: Indicate_color(0, 40, 0); break;
    case FlightState::BOOST:
    case FlightState::COAST:     Indicate_color(40, 40, 40); break;
    case FlightState::APOGEE:
    case FlightState::DESCENT:   Indicate_color(40, 0, 40); break;
    case FlightState::LANDED:    Indicate_color(0, 40, 20); break;
    case FlightState::ABORT:     Indicate_color(60, 0, 0); break;
    case FlightState::ARMED:
    case FlightState::COUNTDOWN: Indicate_color(60, 0, 0); break;   // blinkt über launchSignal()
    case FlightState::IGNITION:  Indicate_color(60, 60, 60); break;
    case FlightState::MISFIRE:   Indicate_color(60, 20, 0); break;
  }
}

// Kalibrierung aus dem EEPROM-Emulat. Bei leerem oder beschädigtem Block
// (falsche CRC, fremde Version) stehen die Standardwerte drin. Die Werte
// gelten für das Mainboard rev B1; der Breakout-Aufbau hier nutzt noch die
// Konstanten aus Config.h, die Zuweisung folgt mit dem rev-B-Sensorpfad.
cal::CalData g_cal;

void setup(){
  Serial.begin(115200);
  StateStore_begin();
  reset_cause = Watchdog_resetCause();

  const cal::Check cc = cal::load(g_cal);
  if (cc == cal::Check::OK) {
    Serial.printf("Kalibrierung geladen: Version %u, gueltig 0x%02lX, %lu. Speicherung\n",
                  g_cal.version, (unsigned long)g_cal.valid, (unsigned long)g_cal.saved_count);
  } else {
    Serial.printf("WARNUNG: Kalibrierung %s, Standardwerte\n", cal::checkName(cc));
  }

  Indicators_setup();
  Indicate_success();
  Indicate_waiting();

  Motor_setup();
  Control_setup();
  Sensors_setup();

  radio.begin(RADIO_BAUD);
#ifdef BOARD_REVB
  e22Configure();                                   // danach M0 = M1 = 0, transparent
#endif

  pinMode(PIN_PYRO1, OUTPUT); digitalWrite(PIN_PYRO1, LOW);
  if (PIN_PYRO2 >= 0) { pinMode(PIN_PYRO2, OUTPUT); digitalWrite(PIN_PYRO2, LOW); }
  trngBegin();
  if (LAUNCH_ENABLED && !launch_auth::keyUsable(LAUNCH_KEY))
    Serial.println("WARNUNG: Secrets.h enthaelt nur Nullen, ARM wird verweigert");

  kal.setDt(1.0f / LOOP_HZ, KALMAN_SIGMA_ACC_MS2);
  kal.setMeasStd(KALMAN_MEAS_STD_M);
  kal.setState(0.f, 0.f);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);

  if (LOG_DATA) {
    SDLogger_setup();
    SDLogger_start();
    SDLogger_setTimingGuard(1.5f, 3000, 6000);
  }

  if (reset_cause == ResetCause::WATCHDOG && tryRestore()) {
    Serial.println("Watchdog-Neustart: Flugzustand wiederaufgenommen");
    sendEvent(fsm.lastEvent());
  } else {
    StateStore_clear();
    Sensors_calibrateStart();           // Nullpunkte gleich nach dem Einschalten (Rakete ruhig)
    calibrating = true;
  }
  Serial.printf("Kartonaut Flug-Firmware, Board %s, Reset: %s, IMU %s, Baro %s\n",
#ifdef BOARD_REVB
                "rev B",
#else
                "Breakouts",
#endif
                resetCauseName(reset_cause), Sensors_status().imu_ok ? "ok" : "FEHLT",
                Sensors_status().baro_ok ? "ok" : "FEHLT");

  if (WDT_ENABLED) Watchdog_begin(WDT_TIMEOUT_MS);
  indicateState(fsm.state());
  Indicate_success();
  LoopTimer_init(loopTimer);
}

// Zustandswechsel: Startablauf vorbereiten und aufräumen
static void onStateChange(FlightState from, FlightState to, uint32_t t) {
  state_since_ms = t;
  if (to == FlightState::PAD_READY) {
    servoTest.start(t);                       // Vorbedingung 6
    auth.renew(trngNext());                   // nonce A für ARM
  }
  if (to == FlightState::SAFE) {
    servoTest.reset();
    auth.discard();
  }
  if (to == FlightState::ARMED) {
    pyro.resetLaunch();                       // neuer Startablauf (z. B. nach MISFIRE mit neuem Anzünder)
    if (LOG_DATA && !SDLogger_isRecording()) SDLogger_start();
  }
  if (from == FlightState::ARMED && to != FlightState::ARMED) auth.discard();   // nonce B gilt nur in ARMED
  if (to == FlightState::IGNITION) {
    ign.begin(t, Sensors_readArmV());
    last_arm_sample_us = 0;
  }
}

// Log-Frame durch den Ringpuffer (siehe logRing)
static void logRouted(const SDFrame& fr) {
  const RingFrame rf{fr, micros(), loops};
  const bool rec = SDLogger_isRecording();
  if (fsm.state() == FlightState::SAFE || fsm.state() == FlightState::PAD_READY) {
    RingFrame old;
    if (logRing.size() == logRing.capacity() && logRing.pop(old) && rec && old.loop % LOG_PAD_EVERY_N_LOOPS == 0) {
      SDLogger_logFrameAt(old.f, old.ts_us, LoopTimer_slack_us(loopTimer));
      log_frames++;
    }
    logRing.push(rf);
    return;
  }
  if (logRing.empty()) {
    if (rec && (loops % LOG_EVERY_N_LOOPS) == 0) {
      SDLogger_logFrameAt(fr, rf.ts_us, LoopTimer_slack_us(loopTimer));
      log_frames++;
    }
    return;
  }
  logRing.push(rf);                           // hinten anstellen, damit die Zeitmarken steigen
  RingFrame old;
  for (uint32_t k = 0; k < LOG_RING_DRAIN_PER_LOOP && logRing.pop(old); ++k) {
    if (!rec) continue;
    SDLogger_logFrameAt(old.f, old.ts_us, LoopTimer_slack_us(loopTimer));
    log_frames++;
  }
}

void loop(){
  pollRadio();
  trngPoll();
  // Startpuls: VBAT_ARMED mit LAUNCH_ARM_SAMPLE_US abtasten, auch zwischen den Takten
  if (launch_fire) {
    const uint32_t now = micros();
    if (now - last_arm_sample_us >= LAUNCH_ARM_SAMPLE_US) {
      last_arm_sample_us = now;
      const float v = Sensors_readArmV();
      ign.armSample(v);
      if (v < arm_loop_min_V) arm_loop_min_V = v;
    }
  }
  if (!LoopTimer_tick(loopTimer)) return;
  if (WDT_ENABLED) Watchdog_feed();
  const uint32_t t0 = micros();
  const float dt = loopTimer.dt_meas_s;
  const uint32_t t = clock_ms();
  loops++;

  // --- 1. Sensoren, Kalibrierung auf dem Pad ---
  Sensors_read(sample);
  if (calibrating && Sensors_calibrateStep(sample)) {
    calibrating = false;
    attitude.initFromAccel(sample.a_body);
    kal.setState(0.f, 0.f);
    kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);
    Control_resetPY(); Control_resetRoll();
    Vec3 gb; float p0; Sensors_getBias(gb, p0);
    Serial.printf("Kalibriert: Gyro-Bias %.3f %.3f %.3f Grad/s, Bodendruck %.0f Pa, Kipp %.2f Grad\n",
                  gb.x, gb.y, gb.z, p0, attitude.tiltTotalDeg());
  }

  // --- 2. Lage aus dem Gyro ---
  if (attitude.initialized && sample.imu_fresh) attitude.update(sample.omega_dps, dt);
  attitude.tiltDeg(tilt_x_deg, tilt_y_deg);
  roll_deg = attitude.rollDeg();
  a_norm_filt += (sample.a_norm - a_norm_filt) * A_NORM_ALPHA;

  // --- 3. Höhe und Vertikalgeschwindigkeit ---
  const Vec3 a_nav = attitude.initialized ? attitude.accelNav(sample.a_body, G_MS2) : Vec3();
  kal.setDt(dt, KALMAN_SIGMA_ACC_MS2);
  kal.step(a_nav.z, sample.baro_alt_m, alt_m, vz_ms);

  // --- 4. Flugzustand ---
  flags = (sample.armed ? tlm::FLAG_ARMED : 0) | (sample.continuity[0] ? tlm::FLAG_CONT1 : 0)
        | (sample.continuity[1] ? tlm::FLAG_CONT2 : 0) | (SDLogger_isRecording() ? tlm::FLAG_LOGGING : 0)
        | (Sensors_calibrated() ? tlm::FLAG_CALIBRATED : 0) | (Sensors_status().ok() ? tlm::FLAG_SENSORS_OK : 0)
        | (pyro.fires(0) ? tlm::FLAG_PYRO_FIRED : 0) | (restored ? tlm::FLAG_RESTORED : 0);
  FlightInputs in;
  in.t_ms = t;
  in.a_norm_ms2 = sample.a_norm;
  in.a_axial_ms2 = sample.a_body.z;          // z = Rollachse, + zur Spitze
  in.alt_m = alt_m; in.vz_ms = vz_ms; in.baro_alt_m = sample.baro_alt_m;
  in.calibrated = Sensors_calibrated() && attitude.initialized && !calibrating;
  in.sensors_ok = Sensors_status().ok();
  in.pyro_done = pyro.done();
  // Landemodus: Anzünder muss scharf und mit Durchgang sein, sonst Fallschirm; Zündung vom Planer
  in.landing_possible = sample.armed && sample.continuity[PYRO_CH_IGNITER] && sample.pyro_fitted[PYRO_CH_IGNITER]
                        && PIN_PYRO2 >= 0 && pyro.fires(PYRO_CH_IGNITER) == 0;
  // Zündentscheidung: mit Drossel früher (Reserve, schwacher Motor geplant), sonst im Kostenminimum
  in.ignite_now = (fsm.state() == FlightState::DESCENT && RECOVERY_MODE == RecoveryMode::LANDING_BURN
                   && !fsm.landingFallback())
                  ? (THROTTLE_ENABLED ? throttle.shouldIgnite(alt_m, vz_ms) : landing.shouldIgnite(alt_m, vz_ms)) : false;
  // Motorstart: Vorbedingungen (ARM und laufend in ARMED/COUNTDOWN), Lebenszeichen vom Boden
  PrecondInputs pi;
  pi.t_ms = t;
  pi.armed = sample.armed;
  pi.continuity = sample.continuity[LAUNCH_CH] && sample.pyro_fitted[LAUNCH_CH] && PIN_LAUNCH >= 0;
  pi.vbat1_V = sample.vbat1_V; pi.vbat2_V = sample.vbat2_V;
  pi.omega_max_dps = fmaxf(fabsf(sample.omega_dps.x), fmaxf(fabsf(sample.omega_dps.y), fabsf(sample.omega_dps.z)));
  pi.tilt_deg = attitude.tiltTotalDeg();
  pi.sensors_ok = Sensors_status().ok(); pi.calibrated = in.calibrated; pi.logging = SDLogger_isRecording();
  pi.servo_test_ok = servoTest.passed();
  pi.launch_enabled = LAUNCH_ENABLED && launch_auth::keyUsable(LAUNCH_KEY);
  preconds.update(pi);
  in.launch_ready = preconds.allOk();
  in.heartbeat_age_ms = last_cmd_ms == 0 ? 0xFFFFFFFF : (t >= last_cmd_ms ? t - last_cmd_ms : 0);
  in.cmd = pending_cmd;
  pending_cmd = FlightCmd::NONE;
  const FlightState before = fsm.state();
  if (fsm.update(in)) {
    sendEvent(fsm.lastEvent());
    indicateState(fsm.state());
    if (fsm.state() == FlightState::PAD_READY && before == FlightState::SAFE) {
      StateStore_clear();
      Control_resetPY(); Control_resetRoll();
      if (LOG_DATA && !SDLogger_isRecording()) SDLogger_start();
    }
  }
  if (fsm.state() != before) onStateChange(before, fsm.state(), t);
  if (pending_ack) {
    const FlightState st = fsm.state();
    bool ok;
    switch (pending_cmd_type) {
      case tlm::CMD_PAD_READY: ok = st == FlightState::PAD_READY; break;
      case tlm::CMD_ARM:       ok = st == FlightState::ARMED; break;
      case tlm::CMD_LAUNCH:    ok = st == FlightState::COUNTDOWN; break;
      case tlm::CMD_ABORT:     // im Startablauf heißt Abbruch SAFE (vor der Zündung) bzw. MISFIRE
        ok = st == FlightState::ABORT || st == FlightState::MISFIRE
             || (st == FlightState::SAFE && (before == FlightState::ARMED || before == FlightState::COUNTDOWN));
        break;
      default:                 ok = st == FlightState::SAFE; break;
    }
    const uint8_t res = ok ? tlm::ACK_OK : tlm::ACK_REFUSED;
    if (pending_cmd_type == tlm::CMD_ARM || pending_cmd_type == tlm::CMD_LAUNCH) sendAckAuth(pending_cmd_type, pending_cmd_seq, res);
    else sendAck(pending_cmd_type, pending_cmd_seq, res);
    pending_ack = false;
  }

  // --- 5. Regler ---
  if (PY_CONTROL_ACTIVE && fsm.controlActive()) {
    py = Control_updatePY(tilt_x_deg, tilt_y_deg, sample.omega_dps, dt, a_norm_filt);
  } else {
    py = PyOutput{};
    py.yaw_servo_deg = SERVO_YAW_OFFSET; py.pitch_servo_deg = SERVO_PITCH_OFFSET;
    const ServoTestOutput so = servoTest.update(t, sample.current_A);   // Selbsttest in PAD_READY
    if (so.active) {
      py.yaw_servo_deg += so.yaw_off_deg; py.pitch_servo_deg += so.pitch_off_deg;
      Apply_servos_deg(py.yaw_servo_deg, py.pitch_servo_deg);
    } else {
      Servos_center();
    }
  }
  if (ROLL_CONTROL_ACTIVE && (fsm.state() == FlightState::BOOST || fsm.state() == FlightState::COAST)) {
    roll = Control_updateRoll(roll_deg, sample.omega_dps.z, dt);
  } else {
    roll = RollOutput{}; roll.angle_deg = roll_deg; roll.rate_dps = sample.omega_dps.z;
    Motor_coast();
  }

  // --- 5b. Schubdrossel im Landebrennen ---
  if (THROTTLE_ENABLED && fsm.state() == FlightState::LANDING_BURN) {
    throttle_u = throttle.command((t - fsm.ignitionTime()) * 1e-3f, alt_m, vz_ms, sample.a_norm);
  } else {
    throttle_u = 0.0f;
    if (fsm.state() == FlightState::DESCENT) throttle.reset();
  }
  Throttle_set(throttle_u);

  // --- 6. Pyro ---
  const PyroGates gates = pyroGates(fsm, RECOVERY_MODE == RecoveryMode::CHUTE, LAUNCH_CH, PYRO_CH_CHUTE, PYRO_CH_IGNITER);
  PyroInputs pin;
  pin.t_ms = t; pin.t_launch_ms = fsm.launchTime();
  pin.allowed[0] = gates.recovery[0]; pin.allowed[1] = gates.recovery[1];
  pin.armed = sample.armed;
  pin.continuity[0] = sample.continuity[0]; pin.continuity[1] = sample.continuity[1];
  pin.fitted[0] = sample.pyro_fitted[0] && PIN_PYRO1 >= 0;
  pin.fitted[1] = sample.pyro_fitted[1] && PIN_PYRO2 >= 0;
  pyro.update(pin, pyro_fire);

  // Startpuls: während er läuft, je Takt eine Messlücke (FET aus, Drain lesen, FET an)
  bool gap_valid = false;
  if (launch_fire && PIN_LAUNCH >= 0) {
    const float pre = Sensors_readPyroSenseV(LAUNCH_CH);
    digitalWrite(PIN_LAUNCH, LOW);
    delayMicroseconds(LAUNCH_GAP_US);
    const float gap = Sensors_readPyroSenseV(LAUNCH_CH);
    digitalWrite(PIN_LAUNCH, HIGH);
    const float arm = Sensors_readArmV();
    ign.armSample(arm);
    if (arm < arm_loop_min_V) arm_loop_min_V = arm;
    gap_cont = gapContinuity(pre, gap, arm, (float)LAUNCH_GAP_US, PYRO_SENSE_TAU_US, PYRO_GAP_RATIO);
    gap_valid = true;
    if (!gap_cont) ign.contLost(t);
  }
  LaunchPulseInputs li;
  li.t_ms = t;
  li.allowed = gates.launch;
  li.armed = sample.armed;
  li.continuity = gap_valid ? gap_cont : (sample.continuity[LAUNCH_CH] && sample.pyro_fitted[LAUNCH_CH] && PIN_LAUNCH >= 0);
  li.continuity_valid = gap_valid || !launch_fire;
  li.thrust = sample.a_norm > FS_LAUNCH_ACCEL_MS2;
  const bool was_firing = launch_fire;
  launch_fire = pyro.updateLaunch(li);
  if (ign.active()) {
    if (launch_fire && !was_firing) { ign.pulseOn(t); last_arm_sample_us = 0; }
    if (!launch_fire && was_firing) ign.pulseOff(t, pyro.launchEndReason());
    if (pyro.launchEndReason() == tlm::IGN_END_REFUSED) ign.refused();
    if (launch_fire) ign.vbat1Sample(sample.vbat1_V);
    if (li.thrust) ign.thrust(t);
  }
  const bool out0 = pyro_fire[0] || (LAUNCH_CH == 0 && launch_fire);
  const bool out1 = pyro_fire[1] || (LAUNCH_CH == 1 && launch_fire);
  digitalWrite(PIN_PYRO1, out0 ? HIGH : LOW);
  if (PIN_PYRO2 >= 0) digitalWrite(PIN_PYRO2, out1 ? HIGH : LOW);
  // IGN-Rahmen einmal, sobald IGNITION verlassen und der Puls aus ist
  if (ign.active() && !fsm.launchAllowed() && !launch_fire) { sendIgnition(); ign.end(); }

  // Summer und LED im Startablauf (ARMED, COUNTDOWN, MISFIRE)
  const LaunchSignal sig = launchSignal(fsm.state(), t - state_since_ms, fsm.countdownLeftMs(t));
  if (sig.active) {
    digitalWrite(PIN_BEEPER, (sig.beep && !SILENT) ? HIGH : LOW);
    if (!last_signal.active || sig.led_on != last_signal.led_on) {
      if (!sig.led_on) Indicate_color(0, 0, 0);
      else if (fsm.state() == FlightState::MISFIRE) Indicate_color(60, 20, 0);
      else Indicate_color(60, 0, 0);
    }
  } else if (last_signal.active) {
    digitalWrite(PIN_BEEPER, LOW);
    indicateState(fsm.state());
  }
  last_signal = sig;

  // --- 7. Telemetrie 10 Hz ---
  if (t - last_tlm_ms >= TLM_PERIOD_MS) { last_tlm_ms = t; sendTelemetry(t); }

  // --- 8. Log, Zustandsspeicher, Landung ---
  if (LOG_DATA) {
    SDFrame fr;
    fr.kalman_alt_m = alt_m; fr.kalman_vz_ms = vz_ms; fr.baro_alt_m = sample.baro_alt_m;
    fr.a_nav_x_ms2 = a_nav.x; fr.a_nav_y_ms2 = a_nav.y; fr.a_nav_z_ms2 = a_nav.z;
    fr.omega_x_dps = sample.omega_dps.x; fr.omega_y_dps = sample.omega_dps.y; fr.omega_z_dps = sample.omega_dps.z;
    fr.roll_angle_deg = roll_deg; fr.roll_rate_dps = sample.omega_dps.z;
    fr.yaw_deg = py.yaw_servo_deg; fr.pitch_deg = py.pitch_servo_deg;
    fr.roll_pwm = roll.pwm; fr.roll_dir = roll.dir;
    fr.bus_V = sample.vbat2_V; fr.current_mA = sample.current_A * 1000.f;
    fr.state_id = (float)fsm.state(); fr.tilt_x_deg = tilt_x_deg; fr.tilt_y_deg = tilt_y_deg;
    fr.vbat1_V = sample.vbat1_V; fr.a_norm_ms2 = sample.a_norm;
    const uint32_t fds = flight_ms(t) / 100;
    fr.raw_i16[0] = (int16_t)(fds > 32767 ? 32767 : fds);
    fr.raw_i16[1] = flags;
    fr.raw_i16[2] = pyro.fires(0) | (pyro.fires(1) << 4) | (pyro_fire[0] << 8) | (pyro_fire[1] << 9)
                  | (launch_fire << 10) | (gap_cont << 11) | (li.thrust << 12);
    fr.load_V = arm_loop_min_V < 1e8f ? arm_loop_min_V : sample.arm_V;   // VBAT_ARMED
    fr.raw_i16[3] = tlm::clamp_i16(sample.a_body.z * 100.f);
    fr.raw_i16[4] = tlm::clamp_i16(py.yaw_tvc_deg * 100.f);
    fr.raw_i16[5] = tlm::clamp_i16(py.pitch_tvc_deg * 100.f);
    fr.raw_i16[6] = (int16_t)reset_cause;
    fr.raw_i16[7] = (int16_t)(throttle_u * 1000.0f);
    logRouted(fr);
  }
  arm_loop_min_V = 1e9f;
  if ((fsm.inFlight() || fsm.state() == FlightState::PAD_READY || fsm.launchSequence())
      && (loops % STATE_SAVE_EVERY_N_LOOPS) == 0) {
    saveState(t);
  }
  if (fsm.state() == FlightState::LANDED && !log_closed) {
    log_closed = true;
    StateStore_clear();
    if (LOG_DATA && SDLogger_isRecording()) SDLogger_stop();
  }
  // Tischtest: nach N Frames stoppen und genau einmal als CSV exportieren (nie auf dem Pad oder im Startablauf,
  // Logging ist dort Vorbedingung für ARM)
  if (LOG_DATA && LOG_STOP_AFTER_FRAMES > 0 && !log_exported && log_frames >= LOG_STOP_AFTER_FRAMES
      && !fsm.inFlight() && !fsm.launchSequence() && fsm.state() != FlightState::PAD_READY) {
    SDLogger_stop();
    const SDExportResult res = SDLogger_exportLatestCSVx(true);
    if (res.ok) Serial.printf("Export: %s  Zeilen=%lu  Bytes=%llu\n", res.csv_name, (unsigned long)res.rows,
                              (unsigned long long)res.bytes);
    else Serial.println("Export fehlgeschlagen.");
    log_exported = true;
  }

  // --- Teleplot (USB-Serial) ---
  if (PLOT_KALMAN) {
    Serial.print(">Kalman_Alt:"); Serial.println(alt_m, 3);
    Serial.print(">Kalman_Vz:");  Serial.println(vz_ms, 3);
  }
  if (PLOT_ROLL) {
    Serial.print(">Roll_Angle:"); Serial.println(roll.angle_deg, 3);
    Serial.print(">Roll_Rate:");  Serial.println(roll.rate_dps, 3);
    Serial.print(">Roll_PWM:");   Serial.println(roll.pwm);
    Serial.print(">Roll_Dir:");   Serial.println(roll.dir);
  }
  if (PLOT_PY) {
    Serial.print(">Tilt_X:");          Serial.println(tilt_x_deg, 3);
    Serial.print(">Tilt_Y:");          Serial.println(tilt_y_deg, 3);
    Serial.print(">Yaw_Servo_Out:");   Serial.println(py.yaw_servo_deg, 2);
    Serial.print(">Pitch_Servo_Out:"); Serial.println(py.pitch_servo_deg, 2);
  }
  if (PLOT_ELECTRICS) {
    Serial.print(">VBAT1:"); Serial.println(sample.vbat1_V, 3);
    Serial.print(">VBAT2:"); Serial.println(sample.vbat2_V, 3);
    Serial.print(">I_A:");   Serial.println(sample.current_A, 3);
  }
  if (PLOT_STATE) {
    Serial.print(">State:"); Serial.println((int)fsm.state());
    Serial.print(">A_norm:"); Serial.println(sample.a_norm, 3);
    if (RECOVERY_MODE == RecoveryMode::LANDING_BURN) { Serial.print(">Landing_J:"); Serial.println(landing.lastCost(), 2); }
    if (THROTTLE_ENABLED) { Serial.print(">Throttle_u:"); Serial.println(throttle_u, 3); }
  }

  LoopTimer_overrunCheck(t0);
}
