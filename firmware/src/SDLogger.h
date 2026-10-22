#pragma once
#include <Arduino.h>

// ===========================
// Öffentliche API
// ===========================
void SDLogger_setup();      // SD initialisieren, TMP→BIN Auto-Recovery
bool SDLogger_start();      // neue LOGxxxxx.TMP (pre-allocate) anlegen
void SDLogger_stop();       // flush + truncate + rename → .BIN
bool SDLogger_isRecording();

// ===========================
// Frame-Typ (ein Call pro Loop)
// ===========================
struct SDFrame {
  // Navigation / Sensorik
  float kalman_alt_m = 0;    // über Pad
  float kalman_vz_ms = 0;
  float baro_alt_m = 0;
  float a_nav_x_ms2 = 0, a_nav_y_ms2 = 0, a_nav_z_ms2 = 0;   // ohne g
  float omega_x_dps = 0, omega_y_dps = 0, omega_z_dps = 0;   // Körper, bias-korrigiert
  float a_body_x_ms2 = 0, a_body_y_ms2 = 0, a_body_z_ms2 = 0; // spezifische Kraft, Körper

  // Lage (Attitude)
  float q_w = 1, q_x = 0, q_y = 0, q_z = 0;
  float tilt_deg = 0, yaw_err_deg = 0, pitch_err_deg = 0, roll_deg = 0;

  // Regler / Aktoren
  float yaw_moment_nm = 0, pitch_moment_nm = 0;
  float tvc_yaw_deg = 0, tvc_pitch_deg = 0;
  float yaw_servo_deg = 90, pitch_servo_deg = 90;
  float roll_cmd = 0;          // -1..+1
  int   roll_pwm = 0;          // 0..4095
  int   roll_dir = 0;          // -1/0/+1

  // Flugzustand
  int   phase = 0;             // KnPhase
  int   flags = 0;             // KN_FLAG_*
  int   pyro_state = 0;        // Bit 0..3 Durchgang, Bit 4..7 Puls aktiv
  int   loop_us = 0;           // Dauer des Durchlaufs
  int   boot_count = 0;

  // Energie / Versorgung
  float vbat1_V = 0, vbat2_V = 0, arm_V = 0;
  float bus_V = 0, current_A = 0;
  float imu_temp_c = 0;
  float thrust_cmd_n = 0;      // Prüfstand
};

// Log-Frame schreiben (RAM-seitig packen & page-buffern).
// slack_us = verbleibende µs bis zur Loop-Deadline (0 ⇒ kein Sync im Flug).
bool SDLogger_logFrame(const SDFrame& f, uint32_t slack_us);

// Wrapper für alte Aufrufe ohne Slack (übernimmt slack_us=0)
bool SDLogger_logFrame(const SDFrame& f);

// ===========================
// Timing/Guards (Debug/Tuning)
// ===========================
struct SDLogTiming {
  uint32_t flush_us_last = 0;
  uint32_t flush_us_avg  = 0;
  uint32_t flush_us_max  = 0;

  uint32_t sync_us_last  = 0;
  uint32_t sync_us_avg   = 0;
  uint32_t sync_us_max   = 0;
};

void SDLogger_getTiming(SDLogTiming& out);
void SDLogger_setTimingGuard(float safety_factor,
                             uint32_t min_slack_flush_us,
                             uint32_t min_slack_sync_us);

// ===========================
// CSV-Export (optional, am Boden)
// ===========================
struct SDExportResult {
  bool     ok = false;        // Erfolg?
  uint32_t rows = 0;          // Datensätze (Zeilen)
  uint64_t bytes = 0;         // geschriebene Bytes inkl. Header
  char     csv_name[16] = {0};
};

SDExportResult SDLogger_exportBINtoCSVx(const char* binName, bool scaled = true);
SDExportResult SDLogger_exportLatestCSVx(bool scaled = true);
bool SDLogger_exportBINtoCSV(const char* binName, bool scaled = true);
bool SDLogger_exportLatestCSV(bool scaled = true);
