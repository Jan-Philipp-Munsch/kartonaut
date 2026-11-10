// main.cpp – Flug-Firmware des Teensy-4.1-Flugcomputers (Kartonaut)
//
// Ablauf pro Takt (LOOP_HZ = 250 Hz, siehe Config.h):
//   1. Sensoren lesen (Sensors.h, Rückende je Board; IMU als Mittel über den FIFO), auf dem Pad kalibrieren
//   2. Lage als Gyro-Quaternion fortschreiben (Attitude.h); am Boden mit Beschleunigung und
//      Magnetometer gestützt (MahonyAid), im Flug nur Gyro mit dem am Boden gelernten Nullpunkt
//   3. Kalman-Filter für Höhe und Vertikalgeschwindigkeit: Vorhersage jeden Takt, Barometer nur
//      bei neuem Wert (50 Hz), Ausreißer verworfen
//   4. Flugzustandsautomat (FlightState.h) mit Kommandos vom Boden oder von USB
//   5. Regler Pitch/Yaw (nur in BOOST) und Roll, Servos und H-Brücke
//   6. Pyro (Pyro.h): nur in APOGEE/DESCENT mit ARM und Durchgang
//   7. Telemetrie 10 Hz (Telemetry.h) über Serial8, Ereignisse sofort
//   8. Log-Satz in den Ringpuffer (PSRAM); auf die SD-Karte nur in SAFE und ab DESCENT, und nur
//      in der freien Zeit bis zur nächsten Deadline (SDLogger.h); dazu in den Flash-Flugschreiber
//      (FlashLog.h, ab PAD_READY, übersteht Stromausfall und verlorene SD-Karte); Zustandsspeicher, Watchdog
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
#include "Filters.h"
#include "FlashLog.h"

HardwareSerial& radio = Serial8;   // HC-12 heute, E22-400T22S auf rev B (transparenter Modus)

// ======= Zustand =======
static LoopTimer loopTimer;
static Attitude  attitude;
static MahonyAid mahony;
static KalmanZ   kal;
static FlightStateMachine fsm(FlightParams{
    FS_LAUNCH_ACCEL_MS2, FS_BURNOUT_AXIAL_MS2, FS_APOGEE_VZ_MS, FS_APOGEE_BARO_DROP_M, FS_LANDED_VZ_MS, FS_LANDED_ALT_M,
    FS_LAUNCH_HOLD_MS, FS_BURNOUT_HOLD_MS, FS_BURN_MAX_MS, FS_APOGEE_EARLIEST_MS, FS_APOGEE_HOLD_MS,
    FS_APOGEE_FALLBACK_MS, FS_DESCENT_AFTER_MS, FS_LANDED_HOLD_MS, FS_FLIGHT_MAX_MS,
    RECOVERY_MODE == RecoveryMode::LANDING_BURN, LANDING_BURN_MAX_MS});
static PyroLogic pyro(PyroParams{{PYRO_PULSE_MS, RECOVERY_MODE == RecoveryMode::LANDING_BURN ? PYRO_IGNITER_PULSE_MS : PYRO_PULSE_MS},
                                 PYRO_MIN_FLIGHT_MS, PYRO_BACKUP_DELAY_MS, PYRO_RETRY_DELAY_MS, PYRO_MAX_FIRES,
                                 RECOVERY_MODE == RecoveryMode::CHUTE});
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
static uint32_t last_loop_us = 0;
static uint8_t  sensor_bits = 0;
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
      case 'f':                          // Flugschreiber aus dem Flash auf die SD-Karte kopieren (nur am Boden)
        if (!fsm.inFlight()) FlashLog_copyToSd();
        break;
      case 'x':                          // Tischtest: Log schließen und als CSV exportieren (nur am Boden)
        if (LOG_DATA && !fsm.inFlight()) {
          SDLogger_stop();
          const SDExportResult res = SDLogger_exportLatestCSVx(true);
          if (res.ok) Serial.printf("Export: %s  Zeilen=%lu\n", res.csv_name, (unsigned long)res.rows);
          else Serial.println("Export fehlgeschlagen.");
        }
        break;
      case '?':
        Serial.printf("Zustand %s, kalibriert %d, IMU %d Baro %d Power %d, Reset: %s%s, Watchdog %s\n",
                      flightStateName(fsm.state()), (int)Sensors_calibrated(), (int)Sensors_status().imu_ok,
                      (int)Sensors_status().baro_ok, (int)Sensors_status().power_ok, resetCauseName(reset_cause),
                      restored ? " (Flug wiederaufgenommen)" : "", WDT_ENABLED ? "an" : "aus");
        Serial.printf("Lage: Kipp x %.2f y %.2f gesamt %.2f Roll %.1f; Hoehe %.2f vz %.2f; |a| %.2f; "
                      "ARM %d Durchgang %d/%d, Akkus %.2f/%.2f V\n",
                      tilt_x_deg, tilt_y_deg, attitude.tiltTotalDeg(), roll_deg, alt_m, vz_ms, sample.a_norm,
                      (int)sample.armed, (int)sample.continuity[0], (int)sample.continuity[1], sample.vbat1_V, sample.vbat2_V);
        {
          SDLogStats ls; SDLogger_getStats(ls);
          Serial.printf("Log: %s, Puffer %lu/%lu Saetze (max %lu), verworfen %lu, ueberschrieben %lu, "
                        "geschrieben %lu, Schreiben max %lu us, Sync max %lu us; Loop %lu us, IMU-Saetze %u, "
                        "Mahony-Nullpunkt %.3f %.3f %.3f Grad/s\n",
                        SDLogger_isRecording() ? "laeuft" : "aus", (unsigned long)ls.queued, (unsigned long)ls.capacity,
                        (unsigned long)ls.max_queued, (unsigned long)ls.dropped, (unsigned long)ls.overwritten,
                        (unsigned long)ls.written, (unsigned long)ls.write_us_max, (unsigned long)ls.sync_us_max,
                        (unsigned long)last_loop_us, (unsigned)sample.imu_n,
                        mahony.integral_dps.x, mahony.integral_dps.y, mahony.integral_dps.z);
          FlashLogStats fs; FlashLog_getStats(fs);
          Serial.printf("Flugschreiber: %s (JEDEC %06lX, %lu MB), Sitzung %d, geschrieben %lu KB, geloescht bis %lu KB, "
                        "Warteschlange %lu (max %lu) Seiten, verloren %lu Saetze%s\n",
                        fs.present ? "Flash da" : "kein Flash", (unsigned long)fs.jedec, (unsigned long)(fs.size >> 20),
                        (int)fs.session, (unsigned long)(fs.write_pos >> 10), (unsigned long)(fs.erased_to >> 10),
                        (unsigned long)fs.queued_pages, (unsigned long)fs.max_queued, (unsigned long)fs.dropped_records,
                        fs.old_flight_pending ? ", ALTER FLUG NICHT KOPIERT ('f')" : "");
        }
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
    case FlightState::LANDING_BURN: Indicate_color(60, 30, 0); break;
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

#ifdef BOARD_REVB
  pinMode(PIN_RADIO_M0, OUTPUT); digitalWrite(PIN_RADIO_M0, LOW);   // E22 transparent
  pinMode(PIN_RADIO_M1, OUTPUT); digitalWrite(PIN_RADIO_M1, LOW);
#endif
  radio.begin(RADIO_BAUD);

  pinMode(PIN_PYRO1, OUTPUT); digitalWrite(PIN_PYRO1, LOW);
  if (PIN_PYRO2 >= 0) { pinMode(PIN_PYRO2, OUTPUT); digitalWrite(PIN_PYRO2, LOW); }

  mahony.kp_acc = MAHONY_KP_ACC; mahony.kp_mag = MAHONY_KP_MAG; mahony.ki = MAHONY_KI;
  kal.setDt(1.0f / LOOP_HZ, KALMAN_SIGMA_ACC_MS2);
  kal.setMeasStd(KALMAN_MEAS_STD_M);
  kal.setState(0.f, 0.f);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);

  if (LOG_DATA) {
    SDLogger_setup();
    SDLogger_start();
    SDLogStats ls; SDLogger_getStats(ls);
    Serial.printf("Log: PSRAM %u MB, Ringpuffer %lu KB im %s, SD %s\n", (unsigned)ls.psram_mb,
                  (unsigned long)(ls.ring_bytes / 1024), ls.in_psram ? "PSRAM" : "RAM2",
                  SDLogger_isRecording() ? "bereit" : "FEHLT");
  }

  if (reset_cause == ResetCause::WATCHDOG && tryRestore()) {
    Serial.println("Watchdog-Neustart: Flugzustand wiederaufgenommen");
    sendEvent(fsm.lastEvent());
  } else {
    StateStore_clear();
    Sensors_calibrateStart();           // Nullpunkte gleich nach dem Einschalten (Rakete ruhig)
    calibrating = true;
  }
  // Flugschreiber: nach einem Neustart im Flug weiterschreiben, sonst alten Flug zur SD kopieren und
  // den Bereich im Hintergrund löschen. Vor dem Watchdog: die Kopie darf einige Sekunden dauern.
  if (LOG_DATA) FlashLog_setup(restored);
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
    mahony.reset();
    kal.setState(0.f, 0.f);
    kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);
    Control_resetPY(); Control_resetRoll();
    Vec3 gb; float p0; Sensors_getBias(gb, p0);
    Serial.printf("Kalibriert: Gyro-Bias %.3f %.3f %.3f Grad/s, Bodendruck %.0f Pa, Kipp %.2f Grad\n",
                  gb.x, gb.y, gb.z, p0, attitude.tiltTotalDeg());
  }

  // --- 2. Lage: Gyro, am Boden gestützt ---
  // Stützung nur in SAFE/PAD_READY, nach der Kalibrierung und in Ruhe (|a| ≈ g, kaum Drehung). Ab dem
  // Start nur Gyro plus der am Boden gelernte Nullpunkt (mahony.integral_dps).
  const FlightState st_now = fsm.state();
  const bool at_rest = fabsf(sample.a_norm - G_MS2) < MAHONY_ACC_TOL * G_MS2 && norm(sample.omega_dps) < MAHONY_RATE_MAX_DPS;
  const bool aid = (st_now == FlightState::SAFE || st_now == FlightState::PAD_READY) && !calibrating
                   && Sensors_calibrated() && at_rest;
  const bool use_mag = aid && MAHONY_USE_MAG && Sensors_status().mag_ok && sample.mag_cal;
  const Vec3 omega_ctrl = sample.omega_dps + mahony.integral_dps;      // auch für den D-Anteil des Reglers
  if (attitude.initialized && sample.imu_fresh) {
    attitude.update(mahony.apply(attitude, sample.omega_dps, sample.a_body, use_mag ? &sample.mag_body : nullptr,
                                 aid, dt), dt);
  }
  attitude.tiltDeg(tilt_x_deg, tilt_y_deg);
  roll_deg = attitude.rollDeg();
  // D-Anteil: Drehrate durch einen Tiefpass 1. Ordnung (PY_D_LPF_HZ); die Lage nutzt die ungefilterte
  static Vec3 omega_d;
  // Faktor 1 − exp(−2π·f·dt) wie in tvcsim (D_LPF_HZ), bei 30 Hz und 4 ms: 0,53
  const float k_d = PY_D_LPF_HZ > 0.f ? 1.0f - expf(-2.0f * 3.14159265f * PY_D_LPF_HZ * dt) : 1.0f;
  omega_d += (omega_ctrl - omega_d) * k_d;
  a_norm_filt = lowpassStep(a_norm_filt, sample.a_norm, A_NORM_TAU_S, dt);

  // --- 3. Höhe und Vertikalgeschwindigkeit ---
  const Vec3 a_nav = attitude.initialized ? attitude.accelNav(sample.a_body, G_MS2) : Vec3();
  kal.setDt(dt, KALMAN_SIGMA_ACC_MS2);
  kal.predict(a_nav.z);
  const bool kal_upd = sample.baro_fresh && kal.update(sample.baro_alt_m, KALMAN_GATE_SIGMA, KALMAN_MAX_REJECTS);
  alt_m = kal.z(); vz_ms = kal.vz();
  sensor_bits = (sample.imu_fresh ? 1 : 0) | (sample.baro_fresh ? 2 : 0) | (sample.mag_fresh ? 4 : 0)
              | (sample.mag_cal ? 8 : 0) | (kal_upd ? 16 : 0) | (aid ? 32 : 0) | (use_mag ? 64 : 0);

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
      if (LOG_DATA) FlashLog_startSession();
    }
    if (fsm.state() == FlightState::SAFE && !fsm.launchTime()) FlashLog_abortSession();   // zurück ohne Start
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
    py = Control_updatePY(tilt_x_deg, tilt_y_deg, omega_d, dt, a_norm_filt);
  } else {
    py = PyOutput{};
    py.yaw_servo_deg = SERVO_YAW_OFFSET; py.pitch_servo_deg = SERVO_PITCH_OFFSET;
    Servos_center();
  }
  if (ROLL_CONTROL_ACTIVE && (fsm.state() == FlightState::BOOST || fsm.state() == FlightState::COAST)) {
    roll = Control_updateRoll(roll_deg, omega_ctrl.z, dt);
  } else {
    roll = RollOutput{}; roll.angle_deg = roll_deg; roll.rate_dps = omega_ctrl.z;
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
  PyroInputs pin;
  pin.t_ms = t; pin.t_launch_ms = fsm.launchTime();
  pin.allowed[PYRO_CH_CHUTE] = fsm.pyroAllowed();
  pin.allowed[PYRO_CH_IGNITER] = (RECOVERY_MODE == RecoveryMode::CHUTE) ? fsm.pyroAllowed() : fsm.igniterAllowed();
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
  // Rate und SD-Erlaubnis je Flugabschnitt (Config.h, SDLogger.h): von PAD_READY bis APOGEE nur in den
  // Ringpuffer, Vorlauf am Pad im Überschreibmodus, ab dem Start nichts mehr überschreiben.
  const FlightState fs_now = fsm.state();
  const bool descent = fs_now == FlightState::DESCENT || fs_now == FlightState::LANDED
                       || (fs_now == FlightState::ABORT && !fsm.launchTime());
  const bool ground = fs_now == FlightState::SAFE || (fs_now == FlightState::ABORT && !fsm.launchTime());
  const uint32_t log_div = ground ? LOG_DIV_GROUND : (descent ? LOG_DIV_DESCENT : LOG_DIV_FLIGHT);
  SDLogger_setOverwrite(fs_now == FlightState::PAD_READY || ground);
  if (LOG_DATA && (loops % log_div) == 0) {
    SDLogStats ls; SDLogger_getStats(ls);
    SDFrame fr;
    float* v = fr.v;
    v[L_KAL_ALT] = alt_m; v[L_KAL_VZ] = vz_ms; v[L_BARO_ALT] = sample.baro_alt_m; v[L_KAL_INNOV] = kal.last_innov;
    { Vec3 gb; float p0; Sensors_getBias(gb, p0); v[L_P_REL] = sample.p_pa - p0; }
    v[L_BARO_T] = sample.baro_temp_c; v[L_IMU_T] = sample.temp_c;
    v[L_ACC_X] = sample.a_body.x; v[L_ACC_Y] = sample.a_body.y; v[L_ACC_Z] = sample.a_body.z;
    v[L_ANAV_X] = a_nav.x; v[L_ANAV_Y] = a_nav.y; v[L_ANAV_Z] = a_nav.z; v[L_A_NORM] = sample.a_norm;
    v[L_W_X] = omega_ctrl.x; v[L_W_Y] = omega_ctrl.y; v[L_W_Z] = omega_ctrl.z;
    v[L_WRAW_X] = sample.omega_raw_dps.x; v[L_WRAW_Y] = sample.omega_raw_dps.y; v[L_WRAW_Z] = sample.omega_raw_dps.z;
    v[L_MAG_X] = sample.mag_body.x; v[L_MAG_Y] = sample.mag_body.y; v[L_MAG_Z] = sample.mag_body.z;
    v[L_Q_W] = attitude.q.w; v[L_Q_X] = attitude.q.x; v[L_Q_Y] = attitude.q.y; v[L_Q_Z] = attitude.q.z;
    v[L_TILT_X] = tilt_x_deg; v[L_TILT_Y] = tilt_y_deg; v[L_ROLL] = roll_deg;
    v[L_MINT_X] = mahony.integral_dps.x; v[L_MINT_Y] = mahony.integral_dps.y; v[L_MINT_Z] = mahony.integral_dps.z;
    v[L_SERVO_YAW] = py.yaw_servo_deg; v[L_SERVO_PITCH] = py.pitch_servo_deg;
    v[L_TVC_YAW] = py.yaw_tvc_deg; v[L_TVC_PITCH] = py.pitch_tvc_deg;
    v[L_ROLL_PWM] = roll.pwm; v[L_ROLL_DIR] = roll.dir; v[L_THROTTLE] = throttle_u;
    v[L_VBAT1] = sample.vbat1_V; v[L_VBAT2] = sample.vbat2_V; v[L_ARM_V] = sample.arm_V; v[L_CURRENT] = sample.current_A;
    v[L_STATE] = (float)fs_now; v[L_FLAGS] = flags;
    v[L_PYRO] = pyro.fires(0) | (pyro.fires(1) << 4) | (pyro_fire[0] << 8) | (pyro_fire[1] << 9);
    v[L_RESET] = (float)reset_cause;
    const uint32_t fds = flight_ms(t) / 100;
    v[L_T_FLIGHT] = fds > 32767 ? 32767 : fds;
    v[L_SENS_BITS] = sensor_bits; v[L_IMU_N] = sample.imu_n;
    v[L_LOOP_US] = last_loop_us; v[L_DT_US] = dt * 1e6f;
    v[L_LOG_DROP] = (ls.dropped + ls.overwritten) & 0x7FFF;
    v[L_RING_PCT] = ls.capacity ? 100.f * ls.queued / ls.capacity : 0.f;
    v[L_FIFO_OVR] = sample.imu_fifo_ovr & 0x7FFF;
    SDLogger_logFrame(fr);
    if (fs_now != FlightState::PAD_READY || (loops % 10) == 0) FlashLog_log(fr);   // am Pad 25 Hz, sonst wie das Log
    log_frames++;
  }
  if ((fsm.inFlight() || fsm.state() == FlightState::PAD_READY) && (loops % STATE_SAVE_EVERY_N_LOOPS) == 0) {
    saveState(t);
  }
  static bool flash_closed = false;
  if (fsm.state() == FlightState::LANDED && !flash_closed) { flash_closed = true; FlashLog_finish(); }
  if (fsm.state() == FlightState::LANDED && !log_closed) {
    // erst schließen, wenn der Puffer leer ist (das Nachschreiben läuft in der freien Zeit, unten)
    StateStore_clear();
    if (!LOG_DATA || !SDLogger_isRecording() || SDLogger_queued() == 0) {
      log_closed = true;
      if (LOG_DATA) SDLogger_stop();
    }
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
    if (RECOVERY_MODE == RecoveryMode::LANDING_BURN) { Serial.print(">Landing_J:"); Serial.println(landing.lastCost(), 2); }
    if (THROTTLE_ENABLED) { Serial.print(">Throttle_u:"); Serial.println(throttle_u, 3); }
  }

  // --- 9. SD-Karte: nur am Boden und ab DESCENT, nur in der freien Zeit bis zur nächsten Deadline ---
  // Flugschreiber jeden Loop: höchstens eine Seite programmieren (µs, wartet nie); löschen nur am Boden
  if (LOG_DATA) FlashLog_service(ground || fs_now == FlightState::PAD_READY || fs_now == FlightState::LANDED);
  if (LOG_DATA) SDLogger_service(loopTimer.next_us - 200, ground || descent);

  last_loop_us = micros() - t0;
  LoopTimer_overrunCheck(t0);
}
