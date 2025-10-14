#pragma once
#include <Arduino.h>
#include "Config.h"

// Exakter Loop-Scheduler mit gemessener Zeitbasis
struct LoopTimer {
  uint32_t next_us;   // nächste Deadline in µs
  float    dt_s;      // Soll-dt (1/LOOP_HZ)
  float    dt_meas_s; // gemessenes dt der letzten Iteration
};

// Initialisiert den Scheduler (setzt nächste Deadline)
void LoopTimer_init(LoopTimer& t);

// Gibt true genau zur Perioden-Deadline, sonst false (nicht blockierend)
bool LoopTimer_tick(LoopTimer& t);

// Optional: Overrun-Check (Debug-Prints bei Bedarf)
void LoopTimer_overrunCheck(uint32_t loop_start_us);


