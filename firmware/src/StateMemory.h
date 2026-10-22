#pragma once
// StateMemory.h – Zustandsspeicher für den Neustart im Flug (Plan 22.10.2026, B5)
//
// Der Watchdog startet einen hängenden Teensy nach WDT_TIMEOUT_MS neu. Damit der Automat
// danach nicht wieder in SAFE auf dem Pad beginnt, liegt der Flugzustand in einem Block,
// den der Start nicht löscht (DMAMEM, Abschnitt .dmabuffers in OCRAM, wird von startup.c
// nicht genullt). Magic und CRC-16 schützen gegen Zufallsinhalt nach dem Einschalten.
// Die reinen Teile (Packen, Prüfen) sind hier, das Ablegen im RAM in StateMemory.cpp.
#include <stdint.h>
#include "MathTypes.h"

struct __attribute__((packed)) SavedState {
  uint32_t magic;            // SAVED_MAGIC
  uint8_t  version;          // Layout-Version
  uint8_t  state;            // FlightState
  uint8_t  calibrated;
  uint8_t  flags;            // tlm-Flags, u. a. Pyro gezündet
  uint32_t uptime_ms;        // millis() beim Speichern
  uint32_t t_launch_ms, t_burnout_ms, t_apogee_ms;
  float    ground_p_pa;      // Bodendruck
  float    alt_offset_m;     // Nullpunkt der Kalman-Höhe
  float    baro_max_m;
  float    gyro_bias_dps[3];
  float    q[4];             // Lage
  float    alt_m, vz_ms;     // Kalman-Zustand
  uint8_t  pyro_fires[2];
  uint8_t  restarts;         // Zahl der Wiederaufnahmen
  uint8_t  _pad;
  uint16_t crc;              // über alles davor
};

constexpr uint32_t SAVED_MAGIC   = 0x4B415254;   // "KART"
constexpr uint8_t  SAVED_VERSION = 1;

// CRC setzen bzw. prüfen (reine Funktionen, native Tests)
void     savedStateSeal(SavedState& s);
bool     savedStateValid(const SavedState& s);
