#pragma once
#include <Arduino.h>

// ========= öffentliches API =========
void SDLogger_setup();                   // SD initialisieren, TMP→BIN recovern
bool SDLogger_start();                   // neue LOGxxxxx.TMP anlegen (pre-allocate)
void SDLogger_stop();                    // flush + rename → .BIN
bool SDLogger_isRecording();             // Status

// Ein Frame mit deinen Größen. Werte als floats/ints, wir packen sie in int16.
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

  // Reserviert für später (z.B. GPS, Temps, Flags …)
  float rsv1, rsv2, rsv3, rsv4, rsv5;

  // Optional: eigene 8 int16-Kanäle direkt (werden unverändert übernommen)
  int16_t raw_i16[8];

  SDFrame() :
    kalman_alt_m(0), kalman_vz_ms(0), baro_alt_m(0),
    a_nav_x_ms2(0), a_nav_y_ms2(0), a_nav_z_ms2(0),
    omega_x_dps(0), omega_y_dps(0), omega_z_dps(0),
    roll_angle_deg(0), roll_rate_dps(0),
    yaw_deg(90), pitch_deg(90), roll_pwm(0), roll_dir(0),
    bus_V(0), load_V(0), current_mA(0), power_mW(0), ina_overflow(0),
    rsv1(0), rsv2(0), rsv3(0), rsv4(0), rsv5(0)
  { memset(raw_i16, 0, sizeof(raw_i16)); }
};

// Ein Frame schreiben (macht selbst Pufferung/Flush). Gibt true bei Erfolg.
bool SDLogger_logFrame(const SDFrame& f);

// CSV-Export (auf SD-Karte im Root). Gibt true bei Erfolg.
bool SDLogger_exportLatestCSV(bool scaled = true);
bool SDLogger_exportBINtoCSV(const char* binName, bool scaled = true);

// === Ergebnisstruktur für CSV-Export ===
struct SDExportResult {
  bool     ok = false;        // Erfolg?
  uint32_t rows = 0;          // Anzahl Datensätze (Zeilen)
  uint64_t bytes = 0;         // geschriebene Bytes (inkl. Header)
  char     csv_name[16] = {0};
};

// Neue API (liefert Detail-Rückmeldung)
SDExportResult SDLogger_exportBINtoCSVx(const char* binName, bool scaled = true);
SDExportResult SDLogger_exportLatestCSVx(bool scaled = true);

// (Bestehende bool-APIs bleiben – optional intern auf x-Variante mappen)
bool SDLogger_exportBINtoCSV(const char* binName, bool scaled = true);
bool SDLogger_exportLatestCSV(bool scaled = true);

