// main.cpp – Flug-Firmware des Teensy-4.1-Flugcomputers (Kartonaut)
//
// Ablauf pro Loop (LOOP_HZ, siehe Config.h):
//   1. Sensoren lesen: Barometer, IMU (DMP-FIFO leeren), Strommonitor
//   2. Lage aus dem Gyro integrieren (rot_deg: x = Yaw, y = Pitch, z = Roll)
//   3. Kalman-Filter für Höhe und Vertikalgeschwindigkeit
//   4. Regler Pitch/Yaw (TVC-Servos) und Roll (Rollmotor), wenn freigegeben
//   5. Teleplot-Ausgaben und ein Log-Frame auf die SD-Karte
//
// Ein Flugzustandsautomat (Pad, Boost, Coast, Apogäum, Bergung) fehlt noch,
// siehe PROJECT.md §4. Die Regler sind in Config.h abgeschaltet, bis der
// erste Flugtest ansteht.
#include <Arduino.h>
#include <HardwareSerial.h>
#include "Config.h"
#include "MathTypes.h"
#include "Indicators.h"
#include "Sensors.h"
#include "KalmanZ.h"
#include "Control.h"
#include "Timing.h"
#include "SDLogger.h"
#include "CalStore.h"     // Kalibrierwerte aus dem EEPROM-Emulat (revb_test: "cal save")

HardwareSerial& hc12 = Serial8;   // Funkmodul HC-12 (Telemetrie, noch ohne Protokoll)

// ======= Zustand =======
static LoopTimer loopTimer;
static KalmanZ   kal;
static float a_norm_filt = G_MS2;      // Tiefpass von |a_body|
static Vec3  rot_deg = {0,0,0};        // integrierte Gyro-Winkel (Yaw, Pitch, Roll)
static float alt_kalman_m = 0.f, vz_kalman_ms = 0.f;

// Nullpunkt der Höhe nach dem Einpendeln des Filters
static float alt_offset_m   = 0.0f;
static bool  offset_applied = false;

// Logging
static uint32_t log_frames   = 0;
static bool     log_exported = false;

// Kalibrierung aus dem EEPROM-Emulat. Bei leerem oder beschädigtem Block
// (falsche CRC, fremde Version) stehen die Standardwerte drin. Die Werte
// gelten für das Mainboard rev B1; der Breakout-Aufbau hier nutzt noch die
// Konstanten aus Config.h, die Zuweisung folgt mit dem rev-B-Sensorpfad.
cal::CalData g_cal;

void setup(){
  Serial.begin(115200);

  const cal::Check cc = cal::load(g_cal);
  if (cc == cal::Check::OK) {
    Serial.printf("Kalibrierung geladen: Version %u, gueltig 0x%02lX, %lu. Speicherung\n",
                  g_cal.version, (unsigned long)g_cal.valid, (unsigned long)g_cal.saved_count);
  } else {
    Serial.printf("WARNUNG: Kalibrierung %s, Standardwerte\n", cal::checkName(cc));
  }

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

  kal.setDt(1.0f / LOOP_HZ, KALMAN_SIGMA_ACC_MS2);
  kal.setMeasStd(KALMAN_MEAS_STD_M);
  kal.setState(KALMAN_INIT_Z_M, KALMAN_INIT_VZ_MS);
  kal.setPDiag(KALMAN_INIT_PZ_VAR, KALMAN_INIT_PV_VAR);

  Indicate_success();
  LoopTimer_init(loopTimer);
}

void loop(){
  if (!LoopTimer_tick(loopTimer)) return;
  const uint32_t t0 = micros();
  const float dt = loopTimer.dt_meas_s;

  // --- 1. Sensoren ---
  BaroData baro;
  Read_Baro(baro);

  ImuData imu;
  Read_IMU(imu, a_norm_filt);   // ohne neuen Frame bleiben die letzten Werte stehen

  PowerData power{};
  Read_Power(power);

  // --- 2. Lage: rein inertial aus dem Gyro ---
  // Komponentenweise Integration gilt nur für kleine Winkel ohne Rollen,
  // siehe PROJECT.md §5 Punkt 3 (Quaternion aus dem Gyro ist der nächste Schritt).
  rot_deg += imu.omega_dps * dt;

  // --- 3. Höhe und Vertikalgeschwindigkeit ---
  kal.setDt(dt, KALMAN_SIGMA_ACC_MS2);
  kal.step(imu.a_nav.z, baro.alt_m, alt_kalman_m, vz_kalman_ms);

  if (KALMAN_ZERO_AFTER_SETTLE && !offset_applied) {
    static const uint32_t t_start_ms = millis();
    if ((millis() - t_start_ms) > (uint32_t)(KALMAN_SETTLE_TIME_S * 1000.0f)) {
      alt_offset_m   = alt_kalman_m;
      offset_applied = true;
    }
  }

  // --- 4. Regler ---
  int yaw_servo_deg = SERVO_DEG_CENTER, pitch_servo_deg = SERVO_DEG_CENTER;
  if (PY_CONTROL_ACTIVE) {
    Control_updatePY(rot_deg, imu.omega_dps, dt, a_norm_filt, yaw_servo_deg, pitch_servo_deg);
    Apply_servos_deg(yaw_servo_deg, pitch_servo_deg);
  }

  RollOutput roll;
  if (ROLL_CONTROL_ACTIVE) {
    Control_updateRoll(rot_deg, imu.omega_dps, dt, roll);
  }

  // --- 5a. Teleplot (USB-Serial) ---
  if (PLOT_KALMAN) {
    Serial.print(">Kalman_Alt:"); Serial.println(alt_kalman_m - alt_offset_m, 3);
    Serial.print(">Kalman_Vz:");  Serial.println(vz_kalman_ms, 3);
  }
  if (PLOT_ROLL) {
    Serial.print(">Roll_Angle:"); Serial.println(roll.angle_deg, 3);
    Serial.print(">Roll_Rate:");  Serial.println(roll.rate_dps, 3);
    Serial.print(">Roll_PWM:");   Serial.println(roll.pwm);
    Serial.print(">Roll_Dir:");   Serial.println(roll.dir);
  }
  if (PLOT_PY) {
    Serial.print(">Pitch_Angle:");     Serial.println(rot_deg.y, 3);
    Serial.print(">Yaw_Angle:");       Serial.println(rot_deg.x, 3);
    Serial.print(">Yaw_Servo_Out:");   Serial.println(yaw_servo_deg);
    Serial.print(">Pitch_Servo_Out:"); Serial.println(pitch_servo_deg);
  }
  if (PLOT_ELECTRICS) {
    static float i_filt = 0.0f;
    i_filt += (power.current_mA - i_filt) * 0.2f;
    Serial.print(">INA_Bus_V:");        Serial.println(power.bus_V, 3);
    Serial.print(">INA_Current_mA_f:"); Serial.println(i_filt, 3);
  }

  // --- 5b. SD-Log: ein Frame pro Loop, Flush/Sync nur in freier Zeit ---
  if (LOG_DATA && SDLogger_isRecording()) {
    SDFrame fr;
    fr.kalman_alt_m   = alt_kalman_m;
    fr.kalman_vz_ms   = vz_kalman_ms;
    fr.baro_alt_m     = baro.alt_m;
    fr.a_nav_x_ms2    = imu.a_nav.x;
    fr.a_nav_y_ms2    = imu.a_nav.y;
    fr.a_nav_z_ms2    = imu.a_nav.z;
    fr.omega_x_dps    = imu.omega_dps.x;
    fr.omega_y_dps    = imu.omega_dps.y;
    fr.omega_z_dps    = imu.omega_dps.z;
    fr.roll_angle_deg = roll.angle_deg;
    fr.roll_rate_dps  = roll.rate_dps;
    fr.yaw_deg        = yaw_servo_deg;
    fr.pitch_deg      = pitch_servo_deg;
    fr.roll_pwm       = roll.pwm;
    fr.roll_dir       = roll.dir;
    fr.bus_V          = power.bus_V;
    fr.current_mA     = power.current_mA;

    SDLogger_logFrame(fr, LoopTimer_slack_us(loopTimer));
    log_frames++;
  }

  // Tischtest: nach N Frames stoppen und genau einmal als CSV exportieren
  if (LOG_DATA && LOG_STOP_AFTER_FRAMES > 0 && !log_exported && log_frames >= LOG_STOP_AFTER_FRAMES) {
    SDLogger_stop();
    const SDExportResult res = SDLogger_exportLatestCSVx(true);
    if (res.ok) {
      Serial.printf("Export: %s  Zeilen=%lu  Bytes=%llu\n",
                    res.csv_name, (unsigned long)res.rows, (unsigned long long)res.bytes);
    } else {
      Serial.println("Export fehlgeschlagen.");
    }
    log_exported = true;
  }

  LoopTimer_overrunCheck(t0);
}
