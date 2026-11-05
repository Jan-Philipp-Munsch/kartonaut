#pragma once
// SDLogger.h – Flug-Log: Ringpuffer im PSRAM, SD-Karte nur außerhalb der Flugphase
//
// Ablauf (seit 05.11.2026):
//   * Jeder Loop legt einen Datensatz (136 Byte, 64 Kanäle) in den Ringpuffer (LogRing.h). Der
//     Puffer liegt im PSRAM des Teensy (6 MB, ~3 min bei 250 Hz); ohne PSRAM 384 KB im RAM2 (~11 s).
//   * SDLogger_service() schreibt den Rückstand auf die Karte, aber nur, wenn main.cpp es erlaubt
//     (SAFE, DESCENT, LANDED) und der Loop genug Luft bis zur nächsten Deadline hat. Von PAD_READY
//     bis APOGEE fasst der Loop die Karte nie an: ein langsamer Schreibzugriff (SD-Karten brauchen
//     gelegentlich 10–100 ms) kann die Regelung nicht aufhalten.
//   * PAD_READY: Puffer im Überschreibmodus (älteste Sätze fallen weg, die letzten Minuten vor dem
//     Start bleiben). Ab dem Start: neue Sätze werden verworfen, falls er je voll wäre (Flugbeginn
//     zählt mehr).
//   * Ab DESCENT wird nachgeschrieben, alle 0,5 s endgültig gespeichert (sync); bei LANDED alles.
//     Fällt beim Aufprall der Strom weg, fehlen höchstens die letzten Zehntelsekunden.
//
// Datei LOGxxxxx.TMP, vorab belegt; SDLogger_stop() kürzt und benennt in .BIN um, beim nächsten
// Start werden liegengebliebene .TMP repariert. Am Boden: SDLogger_exportLatestCSVx() -> CSV.
#include <Arduino.h>

// ===========================
// Kanäle eines Datensatzes (Skalierung in SDLogger.cpp, Tabelle LOG_CH)
// ===========================
enum LogCh : uint8_t {
  L_KAL_ALT, L_KAL_VZ, L_BARO_ALT, L_KAL_INNOV, L_P_REL, L_BARO_T, L_IMU_T,
  L_ACC_X, L_ACC_Y, L_ACC_Z, L_ANAV_X, L_ANAV_Y, L_ANAV_Z, L_A_NORM,
  L_W_X, L_W_Y, L_W_Z, L_WRAW_X, L_WRAW_Y, L_WRAW_Z,
  L_MAG_X, L_MAG_Y, L_MAG_Z,
  L_Q_W, L_Q_X, L_Q_Y, L_Q_Z, L_TILT_X, L_TILT_Y, L_ROLL,
  L_MINT_X, L_MINT_Y, L_MINT_Z,
  L_SERVO_YAW, L_SERVO_PITCH, L_TVC_YAW, L_TVC_PITCH, L_ROLL_PWM, L_ROLL_DIR, L_THROTTLE,
  L_VBAT1, L_VBAT2, L_ARM_V, L_CURRENT,
  L_STATE, L_FLAGS, L_PYRO, L_RESET, L_T_FLIGHT, L_SENS_BITS,
  L_IMU_N, L_LOOP_US, L_DT_US, L_LOG_DROP, L_RING_PCT, L_FIFO_OVR,
  L_NUM
};
static_assert(L_NUM <= 64, "höchstens 64 Kanäle je Datensatz");

struct SDFrame {
  float v[64];
  SDFrame() { for (float& x : v) x = 0; }
};

// ===========================
// API
// ===========================
void SDLogger_setup();          // Ringpuffer anlegen (PSRAM?), SD starten, .TMP reparieren
bool SDLogger_start();          // neue LOGxxxxx.TMP (vorab belegt)
void SDLogger_stop();           // Rest schreiben, kürzen, .BIN
bool SDLogger_isRecording();
uint32_t SDLogger_queued();     // Sätze im Puffer, noch nicht auf der Karte

// Datensatz in den Ringpuffer (nie ein SD-Zugriff)
bool SDLogger_logFrame(const SDFrame& f);

// Rückstand auf die Karte schreiben, solange bis deadline_us Zeit ist (micros()-Basis) und
// sd_allowed gilt. Ohne Erlaubnis: nichts.
void SDLogger_service(uint32_t deadline_us, bool sd_allowed);
// Alles schreiben, ohne Zeitgrenze (Landung, Tischtest)
void SDLogger_drainAll();
// Puffer voll: true = ältesten Satz verwerfen (Vorlauf am Pad), false = neuen verwerfen (Flug)
void SDLogger_setOverwrite(bool on);

struct SDLogStats {
  uint32_t ring_bytes = 0;      // Größe des Ringpuffers
  bool     in_psram = false;
  uint8_t  psram_mb = 0;        // erkannter PSRAM (0, 8, 16)
  uint32_t queued = 0, max_queued = 0, capacity = 0;   // Sätze
  uint32_t dropped = 0, overwritten = 0, written = 0;
  uint32_t write_us_last = 0, write_us_max = 0, sync_us_max = 0;
};
void SDLogger_getStats(SDLogStats& out);

// ===========================
// CSV-Export (am Boden)
// ===========================
struct SDExportResult {
  bool     ok = false;
  uint32_t rows = 0;
  uint64_t bytes = 0;
  char     csv_name[16] = {0};
};

SDExportResult SDLogger_exportBINtoCSVx(const char* binName, bool scaled = true);
SDExportResult SDLogger_exportLatestCSVx(bool scaled = true);
