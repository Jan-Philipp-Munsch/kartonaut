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
  float kalman_alt_m;      // z-Estimate
  float kalman_vz_ms;      // vz-Estimate
  float baro_alt_m;

  float a_nav_x_ms2;
  float a_nav_y_ms2;
  float a_nav_z_ms2;

  float omega_x_dps;
  float omega_y_dps;
  float omega_z_dps;

  // Aktorik / Regler
  float roll_angle_deg;
  float roll_rate_dps;
  int   yaw_deg;           // 0..180
  int   pitch_deg;         // 0..180
  int   roll_pwm;          // 0..4095
  int   roll_dir;          // -1/0/+1

  // Energie / Versorgung (INA219)
  float bus_V;
  float load_V;
  float current_mA;
  float power_mW;
  int   ina_overflow;      // 0/1

  // Reserviert für später
  float rsv1, rsv2, rsv3, rsv4, rsv5;

  // Optional: 8 rohe i16-Kanäle (werden 1:1 geschrieben)
  int16_t raw_i16[8];

  SDFrame()
  : kalman_alt_m(0), kalman_vz_ms(0), baro_alt_m(0),
    a_nav_x_ms2(0), a_nav_y_ms2(0), a_nav_z_ms2(0),
    omega_x_dps(0), omega_y_dps(0), omega_z_dps(0),
    roll_angle_deg(0), roll_rate_dps(0),
    yaw_deg(90), pitch_deg(90), roll_pwm(0), roll_dir(0),
    bus_V(0), load_V(0), current_mA(0), power_mW(0), ina_overflow(0),
    rsv1(0), rsv2(0), rsv3(0), rsv4(0), rsv5(0)
  { memset(raw_i16, 0, sizeof(raw_i16)); }
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
