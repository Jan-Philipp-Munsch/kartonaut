// main.cpp – Flug-Firmware des Teensy-4.1-Flugcomputers (Kartonaut)
//
// Läuft auf beiden Hardwareständen (Board.h): Breakouts heute, Mainboard rev B
// morgen. Ablauf pro Loop (LOOP_HZ, Config.h):
//   1. Sensoren: IMU (spezifische Kraft, Drehrate), Barometer, alle 5 Takte Versorgung
//   2. Lage als Quaternion aus dem Gyro (Attitude), Beschleunigung ins Navigationssystem
//   3. Kalman für Höhe und Vertikalgeschwindigkeit
//   4. Kommandos (Funk, USB), Flugzustandsautomat, Pyro-Logik, Prüfstand-Gas
//   5. Regler Pitch/Yaw (TVC-Servos) und Roll (Rollmotor), nur im Zustand BOOST
//   6. Telemetrie 10 Hz, Status/GPS 1 Hz, Anzeigen, Zustandsspeicher, Teleplot, SD-Log
//
// Tischtest über USB-Serial (115200 Bd): 'h' zeigt die Tasten.
#include <Arduino.h>
#include "Config.h"
#include "Board.h"
#include "MathTypes.h"
#include "Attitude.h"
#include "FlightState.h"
#include "Pyro.h"
#include "TvcController.h"
#include "KartonautProtocol.h"
#include "Indicators.h"
#include "Sensors.h"
#include "KalmanZ.h"
#include "Control.h"
#include "Timing.h"
#include "SDLogger.h"
#include "Radio.h"
#include "Persist.h"
#include "Gps.h"
#include "Testrig.h"

// ======= Konfiguration des Automaten aus Config.h =======
static FlightStateConfig fsConfig() {
  FlightStateConfig c;
  c.g_ms2 = G_MS2;
  c.liftoff_g = FS_LIFTOFF_G; c.liftoff_hold_ms = FS_LIFTOFF_HOLD_MS;
  c.burnout_g = FS_BURNOUT_G; c.burn_max_ms = FS_BURN_MAX_MS;
  c.coast_max_ms = FS_COAST_MAX_MS;
  c.abort_tilt_deg = FS_ABORT_TILT_DEG; c.pad_max_tilt_deg = FS_PAD_MAX_TILT_DEG;
  c.require_arm = HAS_ARM_SENSE && !TESTRIG_MODE;
  c.require_continuity = HAS_PYRO_SENSE && !TESTRIG_MODE;
  return c;
}

// ======= Zustand =======
static LoopTimer     loopTimer;
static KalmanZ       kal;
static Attitude      att;
static FlightState   fs(fsConfig());
static PyroLogic     pyro(PyroLogic::Config(PYRO_PULSE_MS));
static TvcController tvc(Control_tvcParams());
static Radio         radio;
static Gps           gps;
static Testrig       rig;

static ImuData   imu;
static BaroData  baro;
static PowerData power;
static bool      calibrated = false;
static bool      sensors_ok = false;
static uint32_t  last_imu_ms = 0;
static float     alt_offset_m = 0.0f;     // Kalman-Höhe auf dem Pad
static TvcOutput tvc_out;
static RollOutput roll_out;
static uint32_t  loop_us_max = 0, loop_us_last = 0;
static uint8_t   event_seq = 0;
static KnEvent   event_pending{};
static uint8_t   event_repeats = 0;
static uint32_t  t_landed_ms = 0;
static uint32_t  log_frames = 0;
static bool      log_exported = false;
static uint8_t   loop_count = 0;
static bool      cmd_abort = false, cmd_safe = false, cmd_force_ready = false, cmd_force_liftoff = false;

// ======= Hilfen =======
static void safeOutputs() {
  for (int i = 0; i < 4; ++i)
    if (PIN_PYRO_FIRE[i] >= 0) { digitalWrite(PIN_PYRO_FIRE[i], LOW); pinMode(PIN_PYRO_FIRE[i], OUTPUT); }
  if (PIN_CAM_TRIG >= 0) { digitalWrite(PIN_CAM_TRIG, LOW); pinMode(PIN_CAM_TRIG, OUTPUT); }
}

static uint8_t telemetryFlags() {
  uint8_t f = 0;
  if (pyro.armed())         f |= KN_FLAG_ARMED;
  if (pyro.continuity(0))   f |= KN_FLAG_PYRO1_CONT;
  if (pyro.continuity(1))   f |= KN_FLAG_PYRO2_CONT;
  if (pyro.fired(0))        f |= KN_FLAG_PYRO1_FIRED;
  if (pyro.fired(1))        f |= KN_FLAG_PYRO2_FIRED;
  if (PY_CONTROL_ACTIVE && fs.controlAllowed()) f |= KN_FLAG_CTRL_ACTIVE;
  if (calibrated)           f |= KN_FLAG_GYRO_CAL;
  if (SDLogger_isRecording()) f |= KN_FLAG_LOGGING;
  return f;
}

static bool batteriesOk() {
  if (!HAS_VBAT_SENSE) return true;
  return power.vbat1_V >= VBAT1_MIN_V && power.vbat2_V >= VBAT2_MIN_V;
}

static void startLog() {
  if (!LOG_DATA || SDLogger_isRecording()) return;
  if (SDLogger_start()) Serial.println("Log: gestartet");
  else Serial.println("Log: SD-Karte fehlt oder voll");
}

static void stopLog() {
  if (!SDLogger_isRecording()) return;
  SDLogger_stop();
  Serial.println("Log: gestoppt");
}

// Gyro-Bias, Startlage und Bodendruck auf der Rampe (blockiert ca. 2 s)
static bool calibrate() {
  if (fs.phase() != FlightPhase::SAFE) return false;
  Vec3 bias, sd;
  if (!Sensors_calibrateGyro(GYRO_CAL_SAMPLES, GYRO_CAL_MAX_STD_DPS, bias, sd)) {
    Serial.printf("Kalibrierung: nicht ruhig (Std %.2f %.2f %.2f °/s)\n", sd.x, sd.y, sd.z);
    return false;
  }
  Vec3 a_sum; int n = 0;
  const uint32_t t0 = millis();
  while (n < 100 && millis() - t0 < 3000) {
    Vec3 a, w;
    if (Read_IMU_raw(a, w)) {
      a_sum += Vec3((a.x - ACCEL_BIAS_MS2.x) * ACCEL_SCALE.x, (a.y - ACCEL_BIAS_MS2.y) * ACCEL_SCALE.y,
                    (a.z - ACCEL_BIAS_MS2.z) * ACCEL_SCALE.z);
      ++n;
    }
    delay(10);
  }
  if (n < 50 || !att.initFromAccel(a_sum * (1.0f / n))) {
    Serial.println("Kalibrierung: Beschleunigungssensor liefert nichts Brauchbares");
    return false;
  }
  Sensors_calibrateBaroGround(BARO_CAL_SAMPLES);
  kal.setState(0.0f, 0.0f);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);
  alt_offset_m = 0.0f;
  tvc.reset();
  Control_resetRoll();
  calibrated = true;
  Serial.printf("Kalibrierung: Bias %.3f %.3f %.3f °/s, Std %.2f %.2f %.2f, Neigung %.2f°, p0 %.0f Pa\n",
                bias.x, bias.y, bias.z, sd.x, sd.y, sd.z, att.tiltDeg(), Sensors_groundPressure());
  return true;
}

static void onEvent(const FlightEvent& e) {
  if (PLOT_STATE)
    Serial.printf("[%lu ms] %s -> %s (Grund %u)\n", (unsigned long)e.t_ms,
                  flightPhaseName(e.from), flightPhaseName(e.to), e.reason);
  event_pending = KnEvent{e.t_ms, uint8_t(e.from), uint8_t(e.to), e.reason, ++event_seq};
  event_repeats = 3;

  switch (e.to) {
    case FlightPhase::PAD_READY:
      startLog();
      break;
    case FlightPhase::BOOST:
      tvc.reset();
      Control_resetRoll();
      startLog();
      if (PIN_CAM_TRIG >= 0) digitalWrite(PIN_CAM_TRIG, HIGH);
      if (TESTRIG_MODE && e.reason == KN_REASON_COMMAND) rig.startCurve(e.t_ms);
      break;
    case FlightPhase::SAFE:
      stopLog();
      break;
    case FlightPhase::LANDED:
      t_landed_ms = e.t_ms;
      rig.stop();
      break;
    case FlightPhase::ABORT:
      rig.stop();
      break;
    default:
      break;
  }
}

static void sendAck(uint8_t cmd, uint8_t seq, uint8_t result) {
  radio.send(KN_MSG_ACK, KnAck{cmd, seq, result});
}

static void handleCommand(const KnCommand& c) {
  switch (c.cmd) {
    case KN_CMD_PING:
    case KN_CMD_PAD_READY_QUERY:
      sendAck(c.cmd, c.seq, uint8_t(fs.phase()));
      break;
    case KN_CMD_CALIBRATE:
      sendAck(c.cmd, c.seq, fs.phase() == FlightPhase::SAFE ? (calibrate() ? KN_ACK_OK : KN_ACK_FAILED) : KN_ACK_REJECTED);
      break;
    case KN_CMD_ABORT:
      cmd_abort = true;
      sendAck(c.cmd, c.seq, KN_ACK_OK);
      break;
    case KN_CMD_SAFE:
      cmd_safe = true;
      sendAck(c.cmd, c.seq, fs.phase() == FlightPhase::PAD_READY ? KN_ACK_OK : KN_ACK_REJECTED);
      break;
    case KN_CMD_LOG_START:
      startLog();
      sendAck(c.cmd, c.seq, SDLogger_isRecording() ? KN_ACK_OK : KN_ACK_FAILED);
      break;
    case KN_CMD_LOG_STOP:
      stopLog();
      sendAck(c.cmd, c.seq, KN_ACK_OK);
      break;
    case KN_CMD_TESTRIG_THRUST:
      if (!TESTRIG_MODE) { sendAck(c.cmd, c.seq, KN_ACK_REJECTED); break; }
      if (c.arg == 0xFFFF) { cmd_force_ready = true; cmd_force_liftoff = true; }
      else rig.setThrust(c.arg * 0.01f);
      sendAck(c.cmd, c.seq, KN_ACK_OK);
      break;
    default:
      sendAck(c.cmd, c.seq, KN_ACK_UNKNOWN);
      break;
  }
}

static void printStatus() {
  const SensorStatus& st = Sensors_status();
  Serial.printf("%s | %s | IMU %d Baro %d Power %d | kal %d | q %.3f %.3f %.3f %.3f | Neigung %.2f° Yaw %.2f Pitch %.2f Roll %.1f\n",
                BOARD_NAME, flightPhaseName(fs.phase()), st.imu, st.baro, st.power, calibrated,
                att.q().w, att.q().x, att.q().y, att.q().z, att.tiltDeg(), att.yawErrDeg(), att.pitchErrDeg(), att.rollDeg());
  Serial.printf("  a_body %.2f %.2f %.2f  w %.2f %.2f %.2f  alt %.2f vz %.2f baro %.2f | 1S %.2f V 2S %.2f V ARM %.2f V (%s) cont %d%d | INA %.2f V %.2f A\n",
                imu.a_body.x, imu.a_body.y, imu.a_body.z, imu.omega_dps.x, imu.omega_dps.y, imu.omega_dps.z,
                kal.z() - alt_offset_m, kal.vz(), baro.alt_m, power.vbat1_V, power.vbat2_V, power.arm_V,
                power.armed ? "scharf" : "sicher", power.continuity[0], power.continuity[1], power.bus_V, power.current_A);
  Serial.printf("  Loop max %lu µs | Log %s | Funk gesendet %lu verworfen %lu, empfangen %lu CRC-Fehler %lu | GPS Sätze %lu Fix %d | Boot %lu%s\n",
                (unsigned long)loop_us_max, SDLogger_isRecording() ? "an" : "aus",
                (unsigned long)radio.sent(), (unsigned long)radio.dropped(),
                (unsigned long)radio.parser().framesOk(), (unsigned long)radio.parser().crcErrors(),
                (unsigned long)gps.sentences(), gps.hasFix(), (unsigned long)Persist_bootCount(),
                Persist_wasWatchdogReset() ? " (Watchdog)" : "");
  loop_us_max = 0;
}

static void handleKey(int ch) {
  static char num[12]; static uint8_t numlen = 0; static bool in_num = false;
  if (in_num) {
    if (ch == '\n' || ch == '\r' || numlen >= sizeof(num) - 1) {
      num[numlen] = 0; in_num = false; numlen = 0;
      rig.setThrust(atof(num));
      Serial.printf("Prüfstand: Schub %.2f N\n", rig.thrust_N());
    } else num[numlen++] = char(ch);
    return;
  }
  switch (ch) {
    case 'h': Serial.println("c Kalibrieren | r PAD_READY erzwingen | l Start erzwingen | a Abbruch | s SAFE | "
                             "L Log an | S Log aus | x CSV-Export | p Status | t<N> Schub N (Prüfstand)"); break;
    case 'c': calibrate(); break;
    case 'r': cmd_force_ready = true; break;
    case 'l': cmd_force_liftoff = true; break;
    case 'a': cmd_abort = true; break;
    case 's': cmd_safe = true; break;
    case 'L': startLog(); break;
    case 'S': stopLog(); break;
    case 'p': printStatus(); break;
    case 't': in_num = true; numlen = 0; break;
    case 'x': {
      stopLog();
      const SDExportResult res = SDLogger_exportLatestCSVx(true);
      if (res.ok) Serial.printf("Export: %s  Zeilen=%lu  Bytes=%llu\n", res.csv_name, (unsigned long)res.rows, (unsigned long long)res.bytes);
      else Serial.println("Export fehlgeschlagen.");
      break;
    }
    default: break;
  }
}

static void restoreFromPersist(const PersistState& ps) {
  att.set(Quaternion(ps.q[0], ps.q[1], ps.q[2], ps.q[3]));
  Sensors_setGyroBias(Vec3(ps.gyro_bias_dps[0], ps.gyro_bias_dps[1], ps.gyro_bias_dps[2]));
  if (ps.ground_pressure_pa > 50000.0f) Sensors_setGroundPressure(ps.ground_pressure_pa);
  alt_offset_m = ps.alt_offset_m;
  calibrated = ps.calibrated != 0;
  pyro.restoreFiredMask(ps.pyro_fired);
  const uint32_t now = millis();
  fs.restore(FlightPhase(ps.phase), now, ps.t_since_liftoff_ms ? now - ps.t_since_liftoff_ms : 0);
  kal.setState(ps.max_alt_m, 0.0f);   // grobe Schätzung, das Barometer zieht es gerade
  Serial.printf("Zustandsspeicher: %s nach Watchdog-Neustart übernommen (Boot %lu)\n",
                flightPhaseName(fs.phase()), (unsigned long)Persist_bootCount());
  onEvent(fs.lastEvent());
}

static void savePersist(uint32_t now) {
  PersistState ps{};
  ps.phase = uint8_t(fs.phase());
  ps.pyro_fired = pyro.firedMask();
  ps.calibrated = calibrated;
  ps.t_since_liftoff_ms = fs.liftoff_ms() ? now - fs.liftoff_ms() : 0;
  ps.t_saved_ms = now;
  ps.q[0] = att.q().w; ps.q[1] = att.q().x; ps.q[2] = att.q().y; ps.q[3] = att.q().z;
  const Vec3 b = Sensors_gyroBias();
  ps.gyro_bias_dps[0] = b.x; ps.gyro_bias_dps[1] = b.y; ps.gyro_bias_dps[2] = b.z;
  ps.ground_pressure_pa = Sensors_groundPressure();
  ps.alt_offset_m = alt_offset_m;
  ps.max_alt_m = fs.maxAlt_m();
  Persist_save(ps);
}

// ======= setup =======
void setup() {
  safeOutputs();
  Serial.begin(115200);
  Indicators_setup();
  Indicate_waiting();
  Control_setup();                       // Servos Mitte, Motor stromlos
  for (int i = 0; i < 4; ++i) pyro.setFitted(i, PYRO_FITTED[i]);

  PersistState ps{};
  const bool have_state = Persist_begin(ps);

  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 1500) {}
  Serial.printf("\n=== Kartonaut Flug-Firmware, %s ===\n", BOARD_NAME);

  sensors_ok = Sensors_setup();
  const SensorStatus& st = Sensors_status();
  Serial.printf("Sensoren: IMU %s, Barometer %s, Versorgung %s\n", st.imu ? "ok" : "FEHLT",
                st.baro ? "ok" : "FEHLT", st.power ? "ok" : "fehlt");

  radio.begin();
  Serial.printf("Funk: %s%s\n", RADIO_IS_E22 ? "E22 " : "HC-12", radio.configure() ? "" : " (Konfiguration FEHLGESCHLAGEN)");
  gps.begin();
  rig.begin();
  if (LOG_DATA) {
    SDLogger_setup();
    SDLogger_setTimingGuard(1.5f, 3000, 6000);
    if (LOG_FROM_BOOT) startLog();
  }

  kal.setDt(1.0f / LOOP_HZ, KALMAN_SIGMA_ACC_MS2);
  kal.setMeasStd(KALMAN_MEAS_STD_M);
  kal.setState(0.0f, 0.0f);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);

  Read_Power(power);

  // Neustart im Flug: dort weitermachen, wo der Watchdog zugeschlagen hat
  const bool in_flight = have_state && ps.phase >= KN_PHASE_BOOST && ps.phase <= KN_PHASE_DESCENT;
  if (in_flight && Persist_wasWatchdogReset()) {
    restoreFromPersist(ps);
  } else {
    if (have_state && Persist_wasWatchdogReset())
      Serial.printf("Watchdog-Neustart im Zustand %s, beginne in SAFE\n", flightPhaseName(FlightPhase(ps.phase)));
    Persist_clear();
    if (st.imu && st.baro) calibrate();   // Tisch/Rampe: erste Lage; auf der Rampe per CALIBRATE wiederholen
  }

  if (WATCHDOG_ENABLE) {
    Watchdog_begin(WATCHDOG_TIMEOUT_S);
    Sensors_setIdleHook(Watchdog_feed);
    SDLogger_setIdleHook(Watchdog_feed);
  }
  Indicators_off();
  if (st.imu && st.baro) Indicate_success();
  Serial.println("Bereit. 'h' für Tasten.");
  LoopTimer_init(loopTimer);
}

// ======= loop =======
void loop() {
  if (!LoopTimer_tick(loopTimer)) return;
  const uint32_t t0 = micros();
  const uint32_t now = millis();
  const float dt = loopTimer.dt_meas_s;
  Watchdog_feed();
  ++loop_count;

  // --- 1. Sensoren ---
  if (Read_IMU(imu)) last_imu_ms = now;
  const SensorStatus& st = Sensors_status();
  sensors_ok = st.imu && st.baro && (now - last_imu_ms) < IMU_STALE_MS;
  Read_Baro(baro);
  if (loop_count % 5 == 0) Read_Power(power);
  gps.poll();

  // --- 2. Lage ---
  if (calibrated && imu.fresh) att.integrateDps(imu.omega_dps, dt);
  const Vec3 a_nav = att.accelNav(imu.a_body, G_MS2);
  tvc.updateAccelNorm(norm(imu.a_body));

  // --- 3. Höhe ---
  kal.setDt(dt, KALMAN_SIGMA_ACC_MS2);
  kal.predict(a_nav.z);
  if (baro.fresh) kal.update(baro.alt_m);
  const float alt_m = kal.z() - alt_offset_m;
  const float vz_ms = kal.vz();

  // --- 4. Kommandos, Zustandsautomat, Pyro, Prüfstand ---
  KnCommand cmd;
  if (radio.poll(cmd)) handleCommand(cmd);
  while (Serial.available()) handleKey(Serial.read());

  FlightInputs in;
  in.t_ms = now;
  in.accel_z_g = imu.a_body.z / G_MS2;
  in.accel_mag_g = norm(imu.a_body) / G_MS2;
  in.gyro_mag_dps = norm(imu.omega_dps);
  in.vz_ms = vz_ms; in.alt_m = alt_m; in.baro_alt_m = baro.alt_m;
  in.tilt_deg = att.tiltDeg();
  // Ohne Messleitungen (Breakouts) entscheidet PYRO_NO_SENSE_ASSUME_OK, ob die Pyro-Logik
  // „scharf und Durchgang“ annimmt (Tischtest) oder nie zündet
  const bool armed = HAS_ARM_SENSE ? power.armed : PYRO_NO_SENSE_ASSUME_OK;
  bool continuity[4];
  for (int i = 0; i < 4; ++i) continuity[i] = HAS_PYRO_SENSE ? power.continuity[i] : (PYRO_NO_SENSE_ASSUME_OK && PYRO_FITTED[i]);
  in.armed = armed;
  in.continuity = pyro.continuity(PYRO_CHUTE_CHANNEL);
  in.calibrated = calibrated;
  in.batteries_ok = batteriesOk();
  in.sensors_ok = sensors_ok;
  in.cmd_abort = cmd_abort; in.cmd_safe = cmd_safe;
  in.cmd_force_ready = cmd_force_ready; in.cmd_force_liftoff = cmd_force_liftoff;
  cmd_abort = cmd_safe = cmd_force_ready = cmd_force_liftoff = false;
  if (fs.update(in)) onEvent(fs.lastEvent());
  rig.update(now);

  const bool pyro_allowed = fs.pyroAllowed() || (fs.phase() == FlightPhase::ABORT && fs.liftoff_ms() > 0);
  pyro.update(now, armed, continuity, pyro_allowed);
  if (pyro_allowed) {
    pyro.fire(PYRO_CHUTE_CHANNEL, now);                       // lehnt ab, wenn schon gezündet
    const uint32_t t_ref = fs.apogee_ms() ? fs.apogee_ms() : fs.phaseEntered_ms();
    if (now - t_ref >= PYRO_BACKUP_DELAY_MS) pyro.fire(PYRO_BACKUP_CHANNEL, now);
    Chute_servo_deg(CHUTE_SERVO_OPEN_DEG);
  }
  int pyro_state = 0;
  for (int i = 0; i < 4; ++i) {
    if (PIN_PYRO_FIRE[i] >= 0) digitalWrite(PIN_PYRO_FIRE[i], pyro.fireOutput(i) ? HIGH : LOW);
    if (pyro.continuity(i)) pyro_state |= 1 << i;
    if (pyro.fireOutput(i)) pyro_state |= 1 << (4 + i);
  }

  // --- 5. Regler ---
  if (PY_CONTROL_ACTIVE && calibrated && fs.controlAllowed()) {
    tvc_out = tvc.update(att.yawErrDeg(), att.pitchErrDeg(), imu.omega_dps, dt);
  } else {
    tvc_out = tvc.neutral();
  }
  Apply_servos_deg(tvc_out.yaw_servo_deg, tvc_out.pitch_servo_deg);
  if (ROLL_CONTROL_ACTIVE && calibrated && fs.controlAllowed()) {
    Control_updateRoll(att.rollDeg(), imu.omega_dps.z, dt, roll_out);
  } else {
    roll_out = RollOutput{};
    roll_out.angle_deg = att.rollDeg(); roll_out.rate_dps = imu.omega_dps.z;
    Motor_coast();
  }

  // --- 6a. Telemetrie ---
  static uint32_t t_tele = 0, t_status = 0;
  if (now - t_tele >= 1000 / TELEMETRY_HZ) {
    t_tele = now;
    if (event_repeats > 0) { radio.send(KN_MSG_EVENT, event_pending); --event_repeats; }
    KnTelemetry t{};
    t.t_ms = now; t.phase = uint8_t(fs.phase()); t.flags = telemetryFlags();
    t.alt_dm = int16_t(constrain(alt_m * 10.0f, -32768.0f, 32767.0f));
    t.vz_cms = int16_t(constrain(vz_ms * 100.0f, -32768.0f, 32767.0f));
    t.q[0] = int16_t(att.q().w * 32767.0f); t.q[1] = int16_t(att.q().x * 32767.0f);
    t.q[2] = int16_t(att.q().y * 32767.0f); t.q[3] = int16_t(att.q().z * 32767.0f);
    t.tvc_yaw_d5 = int8_t(constrain(tvc_out.yaw_tvc_deg * 5.0f, -127.0f, 127.0f));
    t.tvc_pitch_d5 = int8_t(constrain(tvc_out.pitch_tvc_deg * 5.0f, -127.0f, 127.0f));
    t.vbat1_20mV = uint8_t(constrain(power.vbat1_V / 0.02f, 0.0f, 255.0f));
    t.vbat2_40mV = uint8_t(constrain(power.vbat2_V / 0.04f, 0.0f, 255.0f));
    radio.send(KN_MSG_TELEMETRY, t);
  }
  if (now - t_status >= 1000 / STATUS_HZ) {
    t_status = now;
    KnStatus s{};
    s.loop_us_max = uint16_t(loop_us_max > 65535 ? 65535 : loop_us_max);
    s.current_mA = uint16_t(constrain(power.current_A * 1000.0f, 0.0f, 65535.0f));
    s.baro_alt_dm = int16_t(constrain(baro.alt_m * 10.0f, -32768.0f, 32767.0f));
    s.tilt_cdeg = int16_t(constrain(att.tiltDeg() * 100.0f, -32768.0f, 32767.0f));
    s.temp_c10 = int16_t(imu.temp_c * 10.0f);
    s.boot_count = uint8_t(Persist_bootCount());
    s.log_pct = uint8_t((log_frames * 88ULL * 100ULL) / (8ULL * 1024ULL * 1024ULL));
    s.version = KN_PROTOCOL_VERSION;
    radio.send(KN_MSG_STATUS, s);
    if (HAS_GPS && gps.sentences() > 0) radio.send(KN_MSG_GPS, gps.data());
    loop_us_max = 0;
  }

  // --- 6b. Anzeigen, Zustandsspeicher ---
  IndicatorInputs ii;
  ii.phase = fs.phase(); ii.armed = armed; ii.continuity = pyro.continuity(PYRO_CHUTE_CHANNEL);
  ii.battery_low = !batteriesOk(); ii.calibrated = calibrated;
  Indicators_update(ii, now);
  if (loop_count % (uint8_t)(LOOP_HZ / PERSIST_SAVE_HZ) == 0) savePersist(now);

  // --- 6c. Teleplot (USB-Serial) ---
  if (PLOT_KALMAN) {
    Serial.printf(">Kalman_Alt:%.3f\n>Kalman_Vz:%.3f\n>Baro_Alt:%.3f\n", alt_m, vz_ms, baro.alt_m);
  }
  if (PLOT_ATTITUDE) {
    Serial.printf(">Tilt:%.3f\n>YawErr:%.3f\n>PitchErr:%.3f\n>Roll:%.3f\n", att.tiltDeg(), att.yawErrDeg(), att.pitchErrDeg(), att.rollDeg());
  }
  if (PLOT_ROLL) {
    Serial.printf(">Roll_Angle:%.3f\n>Roll_Rate:%.3f\n>Roll_PWM:%d\n>Roll_Dir:%d\n", roll_out.angle_deg, roll_out.rate_dps, roll_out.pwm, roll_out.dir);
  }
  if (PLOT_PY) {
    Serial.printf(">TVC_Yaw:%.3f\n>TVC_Pitch:%.3f\n>Yaw_Servo:%.1f\n>Pitch_Servo:%.1f\n",
                  tvc_out.yaw_tvc_deg, tvc_out.pitch_tvc_deg, tvc_out.yaw_servo_deg, tvc_out.pitch_servo_deg);
  }
  if (PLOT_ELECTRICS) {
    Serial.printf(">VBAT1:%.3f\n>VBAT2:%.3f\n>ARM:%.3f\n>INA_Bus_V:%.3f\n>INA_Current_A:%.3f\n",
                  power.vbat1_V, power.vbat2_V, power.arm_V, power.bus_V, power.current_A);
  }

  // --- 6d. SD-Log: ein Frame pro Loop, Flush/Sync nur in freier Zeit ---
  if (LOG_DATA && SDLogger_isRecording()) {
    SDFrame fr;
    fr.kalman_alt_m = alt_m; fr.kalman_vz_ms = vz_ms; fr.baro_alt_m = baro.alt_m;
    fr.a_nav_x_ms2 = a_nav.x; fr.a_nav_y_ms2 = a_nav.y; fr.a_nav_z_ms2 = a_nav.z;
    fr.omega_x_dps = imu.omega_dps.x; fr.omega_y_dps = imu.omega_dps.y; fr.omega_z_dps = imu.omega_dps.z;
    fr.a_body_x_ms2 = imu.a_body.x; fr.a_body_y_ms2 = imu.a_body.y; fr.a_body_z_ms2 = imu.a_body.z;
    fr.q_w = att.q().w; fr.q_x = att.q().x; fr.q_y = att.q().y; fr.q_z = att.q().z;
    fr.tilt_deg = att.tiltDeg(); fr.yaw_err_deg = att.yawErrDeg(); fr.pitch_err_deg = att.pitchErrDeg(); fr.roll_deg = att.rollDeg();
    fr.yaw_moment_nm = tvc_out.yaw_moment_nm; fr.pitch_moment_nm = tvc_out.pitch_moment_nm;
    fr.tvc_yaw_deg = tvc_out.yaw_tvc_deg; fr.tvc_pitch_deg = tvc_out.pitch_tvc_deg;
    fr.yaw_servo_deg = tvc_out.yaw_servo_deg; fr.pitch_servo_deg = tvc_out.pitch_servo_deg;
    fr.roll_cmd = roll_out.cmd_norm; fr.roll_pwm = roll_out.pwm; fr.roll_dir = roll_out.dir;
    fr.phase = int(fs.phase()); fr.flags = telemetryFlags(); fr.pyro_state = pyro_state;
    fr.loop_us = int(loop_us_last); fr.boot_count = int(Persist_bootCount());
    fr.vbat1_V = power.vbat1_V; fr.vbat2_V = power.vbat2_V; fr.arm_V = power.arm_V;
    fr.bus_V = power.bus_V; fr.current_A = power.current_A; fr.imu_temp_c = imu.temp_c;
    fr.thrust_cmd_n = rig.thrust_N();
    SDLogger_logFrame(fr, LoopTimer_slack_us(loopTimer));
    log_frames++;
  }

  // Log-Ende: nach der Landung, oder am Tisch nach N Frames mit CSV-Export
  if (t_landed_ms && SDLogger_isRecording() && now - t_landed_ms >= LOG_STOP_AFTER_LANDING_MS) stopLog();
  if (LOG_DATA && LOG_STOP_AFTER_FRAMES > 0 && !log_exported && log_frames >= LOG_STOP_AFTER_FRAMES) {
    log_exported = true;
    handleKey('x');
  }

  loop_us_last = micros() - t0;
  if (loop_us_last > loop_us_max) loop_us_max = loop_us_last;
  LoopTimer_overrunCheck(t0);
}
