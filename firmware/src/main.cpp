// main.cpp – Flug-Firmware des Teensy-4.1-Flugcomputers (Kartonaut)
//
// Ablauf pro Takt (LOOP_HZ, siehe Config.h):
//   1. Sensoren lesen (Sensors.h, Rückende je Board), auf dem Pad kalibrieren
//   2. Lage als Gyro-Quaternion fortschreiben (Attitude.h), Kippwinkel in Servoachsen
//   3. Kalman-Filter für Höhe und Vertikalgeschwindigkeit
//   4. Flugzustandsautomat (FlightState.h) mit Kommandos vom Boden oder von USB
//   5. Regler Pitch/Yaw (nur in BOOST) und Roll, Servos und H-Brücke
//   6. Pyro (Pyro.h): nur in APOGEE/DESCENT mit ARM und Durchgang
//   7. Telemetrie 10 Hz (Telemetry.h) über Serial8, Ereignisse sofort
//   8. Log-Frame auf die SD-Karte, Zustandsspeicher, Watchdog füttern
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
#include "Watchdog.h"
#include "StateStore.h"

HardwareSerial& radio = Serial8;   // HC-12 heute, E22-400T22S auf rev B (transparenter Modus)

// ======= Zustand =======
static LoopTimer loopTimer;
static Attitude  attitude;
static KalmanZ   kal;
static FlightStateMachine fsm(FlightParams{
    FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M, FS_LANDED_VZ_MS, FS_LANDED_ALT_M,
    FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS, FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS,
    FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS, FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS});
static PyroLogic pyro(PyroParams{PYRO_PULSE_MS, PYRO_MIN_FLIGHT_MS, PYRO_BACKUP_DELAY_MS, PYRO_RETRY_DELAY_MS, PYRO_MAX_FIRES});
static tlm::Parser radioParser;

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

static void handleCommand(uint8_t type, uint8_t seq) {
  switch (type) {
    case tlm::CMD_PING:
      sendAck(type, seq, tlm::ACK_OK);
      break;
    case tlm::CMD_CALIBRATE:
      if (fsm.state() == FlightState::SAFE || fsm.state() == FlightState::PAD_READY) {
        Sensors_calibrateStart(); calibrating = true;
        sendAck(type, seq, tlm::ACK_OK);
      } else sendAck(type, seq, tlm::ACK_REFUSED);
      break;
    case tlm::CMD_PAD_READY: pending_cmd = FlightCmd::PAD_READY; pending_cmd_type = type; pending_cmd_seq = seq; pending_ack = true; break;
    case tlm::CMD_ABORT:     pending_cmd = FlightCmd::ABORT;     pending_cmd_type = type; pending_cmd_seq = seq; pending_ack = true; break;
    case tlm::CMD_SAFE:      pending_cmd = FlightCmd::SAFE;      pending_cmd_type = type; pending_cmd_seq = seq; pending_ack = true; break;
    default:
      sendAck(type, seq, tlm::ACK_UNKNOWN);
  }
}

static void pollRadio() {
  while (radio.available()) {
    if (radioParser.feed((uint8_t)radio.read())) {
      const uint8_t seq = radioParser.length() ? radioParser.payload()[0] : 0;
      handleCommand(radioParser.type(), seq);
    }
  }
  // Tischtest ohne Bodenstation: Einzelbuchstaben auf USB-Serial
  while (Serial.available()) {
    const char c = (char)Serial.read();
    switch (c) {
      case 'c': handleCommand(tlm::CMD_CALIBRATE, 0); break;
      case 'r': handleCommand(tlm::CMD_PAD_READY, 0); break;
      case 'a': handleCommand(tlm::CMD_ABORT, 0); break;
      case 's': handleCommand(tlm::CMD_SAFE, 0); break;
      case '?':
        Serial.printf("Zustand %s, kalibriert %d, IMU %d Baro %d Power %d, Reset: %s%s, Watchdog %s\n",
                      flightStateName(fsm.state()), (int)Sensors_calibrated(), (int)Sensors_status().imu_ok,
                      (int)Sensors_status().baro_ok, (int)Sensors_status().power_ok, resetCauseName(reset_cause),
                      restored ? " (Flug wiederaufgenommen)" : "", WDT_ENABLED ? "an" : "aus");
        Serial.printf("Lage: Kipp x %.2f y %.2f gesamt %.2f Roll %.1f; Hoehe %.2f vz %.2f; |a| %.2f; "
                      "ARM %d Durchgang %d/%d, Akkus %.2f/%.2f V\n",
                      tilt_x_deg, tilt_y_deg, attitude.tiltTotalDeg(), roll_deg, alt_m, vz_ms, sample.a_norm,
                      (int)sample.armed, (int)sample.continuity[0], (int)sample.continuity[1], sample.vbat1_V, sample.vbat2_V);
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
  const FlightState st = (FlightState)s.state;
  const bool in_flight = st == FlightState::BOOST || st == FlightState::COAST || st == FlightState::APOGEE
                         || st == FlightState::DESCENT || (st == FlightState::ABORT && s.t_launch_ms != 0);
  if (!in_flight && st != FlightState::PAD_READY) return false;
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
    case FlightState::SAFE:      Indicate_color(0, 0, 40); break;
    case FlightState::PAD_READY: Indicate_color(0, 40, 0); break;
    case FlightState::BOOST:
    case FlightState::COAST:     Indicate_color(40, 40, 40); break;
    case FlightState::APOGEE:
    case FlightState::DESCENT:   Indicate_color(40, 0, 40); break;
    case FlightState::LANDED:    Indicate_color(0, 40, 20); break;
    case FlightState::ABORT:     Indicate_color(60, 0, 0); break;
  }
}

void setup(){
  Serial.begin(115200);
  StateStore_begin();
  reset_cause = Watchdog_resetCause();

  Indicators_setup();
  Indicate_success();
  Indicate_waiting();

  Motor_setup();
  Control_setup();
  Sensors_setup();

#ifdef BOARD_REVB
  pinMode(PIN_RADIO_M0, OUTPUT); digitalWrite(PIN_RADIO_M0, LOW);   // E22 transparent
  pinMode(PIN_RADIO_M1, OUTPUT); digitalWrite(PIN_RADIO_M1, LOW);
#endif
  radio.begin(RADIO_BAUD);

  pinMode(PIN_PYRO1, OUTPUT); digitalWrite(PIN_PYRO1, LOW);
  if (PIN_PYRO2 >= 0) { pinMode(PIN_PYRO2, OUTPUT); digitalWrite(PIN_PYRO2, LOW); }

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

void loop(){
  pollRadio();
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
  if (pending_ack) {
    const bool ok = (pending_cmd_type == tlm::CMD_PAD_READY) ? fsm.state() == FlightState::PAD_READY
                  : (pending_cmd_type == tlm::CMD_ABORT)     ? fsm.state() == FlightState::ABORT
                  :                                            fsm.state() == FlightState::SAFE;
    sendAck(pending_cmd_type, pending_cmd_seq, ok ? tlm::ACK_OK : tlm::ACK_REFUSED);
    pending_ack = false;
  }

  // --- 5. Regler ---
  if (PY_CONTROL_ACTIVE && fsm.controlActive()) {
    py = Control_updatePY(tilt_x_deg, tilt_y_deg, sample.omega_dps, dt, a_norm_filt);
  } else {
    py = PyOutput{};
    py.yaw_servo_deg = SERVO_YAW_OFFSET; py.pitch_servo_deg = SERVO_PITCH_OFFSET;
    Servos_center();
  }
  if (ROLL_CONTROL_ACTIVE && (fsm.state() == FlightState::BOOST || fsm.state() == FlightState::COAST)) {
    roll = Control_updateRoll(roll_deg, sample.omega_dps.z, dt);
  } else {
    roll = RollOutput{}; roll.angle_deg = roll_deg; roll.rate_dps = sample.omega_dps.z;
    Motor_coast();
  }

  // --- 6. Pyro ---
  PyroInputs pin;
  pin.t_ms = t; pin.allowed = fsm.pyroAllowed(); pin.t_launch_ms = fsm.launchTime();
  pin.armed = sample.armed;
  pin.continuity[0] = sample.continuity[0]; pin.continuity[1] = sample.continuity[1];
  pin.fitted[0] = sample.pyro_fitted[0] && PIN_PYRO1 >= 0;
  pin.fitted[1] = sample.pyro_fitted[1] && PIN_PYRO2 >= 0;
  pyro.update(pin, pyro_fire);
  digitalWrite(PIN_PYRO1, pyro_fire[0] ? HIGH : LOW);
  if (PIN_PYRO2 >= 0) digitalWrite(PIN_PYRO2, pyro_fire[1] ? HIGH : LOW);

  // --- 7. Telemetrie 10 Hz ---
  if (t - last_tlm_ms >= TLM_PERIOD_MS) { last_tlm_ms = t; sendTelemetry(t); }

  // --- 8. Log, Zustandsspeicher, Landung ---
  if (LOG_DATA && SDLogger_isRecording() && (loops % LOG_EVERY_N_LOOPS) == 0) {
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
    fr.raw_i16[2] = pyro.fires(0) | (pyro.fires(1) << 4) | (pyro_fire[0] << 8) | (pyro_fire[1] << 9);
    fr.raw_i16[3] = tlm::clamp_i16(sample.a_body.z * 100.f);
    fr.raw_i16[4] = tlm::clamp_i16(py.yaw_tvc_deg * 100.f);
    fr.raw_i16[5] = tlm::clamp_i16(py.pitch_tvc_deg * 100.f);
    fr.raw_i16[6] = (int16_t)reset_cause;
    SDLogger_logFrame(fr, LoopTimer_slack_us(loopTimer));
    log_frames++;
  }
  if ((fsm.inFlight() || fsm.state() == FlightState::PAD_READY) && (loops % STATE_SAVE_EVERY_N_LOOPS) == 0) {
    saveState(t);
  }
  if (fsm.state() == FlightState::LANDED && !log_closed) {
    log_closed = true;
    StateStore_clear();
    if (LOG_DATA && SDLogger_isRecording()) SDLogger_stop();
  }
  // Tischtest: nach N Frames stoppen und genau einmal als CSV exportieren
  if (LOG_DATA && LOG_STOP_AFTER_FRAMES > 0 && !log_exported && log_frames >= LOG_STOP_AFTER_FRAMES
      && !fsm.inFlight()) {
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
  }

  LoopTimer_overrunCheck(t0);
}
