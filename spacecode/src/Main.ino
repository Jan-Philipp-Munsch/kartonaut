/*
#include <Arduino.h>
#include "Config.h"
#include "MathTypes.h"
#include "Indicators.h"
#include "Sensors.h"
#include "KalmanZ.h"
#include "Control.h"
#include "Timing.h"
#include <HardwareSerial.h>
#include "SDLogger.h"

HardwareSerial& hc12 = Serial8;

// ======= State =======
static LoopTimer loopTimer;
static KalmanZ kal;
static float a_norm_filt = G_MS2;   // LPF(|a|)
static Vec3 rot_deg = {0,0,0};      // integrierte Demo-Rotation
static float AltitudeKalman = 0.f, VelocityVerticalKalman = 0.f;

// Offset/Zeroing nach Einpendeln
static float alt_offset = 0.0f;
static bool  offset_applied = false;

// --- Logging Steuerung ---
static uint32_t log_iter = 0;
static bool     log_exported = false;

// Slack-Deadline (für SDLogger)
static uint32_t t_next = 0;

void setup(){
  Serial.begin(115200);

  // SD-Logger init
  if (LOG_DATA) {
    SDLogger_setup();
    SDLogger_start();
    SDLogger_setTimingGuard(1.5f, 3000, 6000);
  }

  Indicators_setup();
  Indicate_success();
  Indicate_waiting();

  Motor_setup();
  Control_setup();
  Sensors_setup();

  hc12.begin(HC12_BAUD);

  // Kalman initial parametrieren
  kal.setDt(1.0f/LOOP_HZ, KALMAN_SIGMA_ACC_MS2);
  kal.setMeasStd(KALMAN_MEAS_STD_M);
  kal.setState(KALMAN_INIT_Z_M, KALMAN_INIT_VZ_MS);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);

  Indicate_success();

  LoopTimer_init(loopTimer);

  // Slack-Deadline initialisieren (für feste Loop-Periode)
  t_next = micros() + LOOP_PERIOD_US;
}


void loop(){

  if (!LoopTimer_tick(loopTimer)) return; // exakte Periodik nach Timing.h
  const uint32_t t0 = micros();

  // --- Sensors ---
  BaroData baro;
  Read_Baro(baro);

  // Integration, wenn kein neuer Wert fehlt!
  ImuData imu;
  Read_IMU(imu, a_norm_filt);
  rot_deg += imu.omega_dps * loopTimer.dt_meas_s;

  // --- Kalman (mit aktuellem dt) ---
  kal.setDt(loopTimer.dt_meas_s, KALMAN_SIGMA_ACC_MS2);
  kal.step(imu.a_nav.z, baro.alt_m, AltitudeKalman, VelocityVerticalKalman);

  // Einpendeln & Nullpunkt setzen (optional)
  if (KALMAN_ZERO_AFTER_SETTLE && !offset_applied) {
    static uint32_t t_start_ms = millis();
    if ((millis() - t_start_ms) > (uint32_t)(KALMAN_SETTLE_TIME_S * 1000.0f)) {
      alt_offset = AltitudeKalman;  // Boden als 0 setzen
      offset_applied = true;
    }
  }

  // --- Control: Servos (Grad) ---
  int yaw_deg_cmd = SERVO_DEG_CENTER, pitch_deg_cmd = SERVO_DEG_CENTER;
  AttState attOut;
  if (PY_CONTROL_ACTIVE) {
    Control_updatePY(imu.omega_dps, rot_deg, loopTimer.dt_meas_s, a_norm_filt,
                     yaw_deg_cmd, pitch_deg_cmd, attOut);
    Apply_servos_deg(yaw_deg_cmd, pitch_deg_cmd);
  }

  // --- Control: Roll (Default-Werte, falls Feature aus) ---
  float roll_angle_deg = 0.0f;
  float roll_rate_dps  = 0.0f;
  float roll_corr_angle_deg = 0.0f;
  float roll_cmd_norm  = 0.0f;
  int   roll_pwm = 0;
  int   roll_dir = 0;
  if (ROLL_CONTROL_ACTIVE) {
    Control_updateRoll(imu.omega_dps, rot_deg, loopTimer.dt_meas_s,
                       roll_angle_deg, roll_rate_dps, roll_corr_angle_deg,
                       roll_cmd_norm, roll_pwm, roll_dir);
  }

  // --- INA219 Daten (einmal pro Loop einlesen) ---
 
  PowerData p{};
  (void)Read_Power(p); // liefert true, wenn neue Messung — wir nutzen die Felder so oder so

  // --- Teleplot-Ausgaben (Konsole) ---
  if (PLOT_KALMAN)  {
    Serial.print(">Kalman_Alt:");  Serial.println(AltitudeKalman - alt_offset, 3);
    Serial.print(">Kalman_Vz:");   Serial.println(VelocityVerticalKalman, 3);
  }
  if (PLOT_ROLL)  {
    Serial.print(">Roll_Angle:");  Serial.println(roll_angle_deg, 3);
    Serial.print(">Roll_Rate:");   Serial.println(roll_rate_dps, 3);
    Serial.print(">Roll_PWM:");    Serial.println(roll_pwm);
    Serial.print(">Roll_Dir:");    Serial.println(roll_dir);
  }
  if (PLOT_PY)  {
    Serial.print(">Pitch_Angle:"); Serial.println(rot_deg.y, 3);
    Serial.print(">Yaw_Angle:");   Serial.println(rot_deg.x, 3);
    Serial.print(">Yaw_Servo_Out:");   Serial.println(yaw_deg_cmd);
    Serial.print(">Pitch_Servo_Out:"); Serial.println(pitch_deg_cmd);
  }
  if (PLOT_ELECTRICS)  {
    // leichte Glättung für nicer plots
    static float i_filt = 0.0f;
    const float ALPHA = 0.2f; // 0..1 (höher = glatter)
    i_filt   += (p.current_mA - i_filt) * ALPHA;

    Serial.print(">INA_Bus_V:");       Serial.println(p.bus_V,      3);
    Serial.print(">INA_Current_mA_f:");Serial.println(i_filt,       3);

  }


  // --- Logging: ein Frame pro Loop ---
  if (LOG_DATA && SDLogger_isRecording()) {
    SDFrame fr;
    fr.kalman_alt_m   = AltitudeKalman;
    fr.kalman_vz_ms   = VelocityVerticalKalman;
    fr.baro_alt_m     = baro.alt_m;

    fr.a_nav_x_ms2    = imu.a_nav.x;
    fr.a_nav_y_ms2    = imu.a_nav.y;
    fr.a_nav_z_ms2    = imu.a_nav.z;

    fr.omega_x_dps    = imu.omega_dps.x;
    fr.omega_y_dps    = imu.omega_dps.y;
    fr.omega_z_dps    = imu.omega_dps.z;

    fr.roll_angle_deg = roll_angle_deg;
    fr.roll_rate_dps  = roll_rate_dps;
    fr.yaw_deg        = yaw_deg_cmd;
    fr.pitch_deg      = pitch_deg_cmd;
    fr.roll_pwm       = roll_pwm;
    fr.roll_dir       = roll_dir;

    fr.bus_V          = p.bus_V;
    fr.current_mA     = p.current_mA;

    // Slack-aware schreiben
    SDLogger_logFrame(fr);

    // Iterationen zählen (für Test)
    log_iter++;
  }

  // --- Test: nach N Loops stoppen & genau 1× CSV exportieren ---
  if (LOG_DATA && !log_exported && log_iter > 1000) {
    SDLogger_stop();  // schließt .TMP → .BIN
    auto res = SDLogger_exportLatestCSVx(true);  // true = physikalische Einheiten

    if (res.ok) {
      Serial.printf("Export erfolgreich: %s  Zeilen=%lu  Bytes=%llu\n",
                    res.csv_name, (unsigned long)res.rows, (unsigned long long)res.bytes);
    } else {
      Serial.println("Export fehlgeschlagen.");
    }
    log_exported = true;  // verhindert mehrfachen Export
  }

  // Overrun-Check (bestehende Helper)
  LoopTimer_overrunCheck(t0);
}
*/