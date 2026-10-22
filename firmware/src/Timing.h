#pragma once
// Timing.h – fester Loop-Takt (LOOP_HZ) auf Basis von micros(), nicht blockierend.
#include <Arduino.h>
#include "Config.h"

struct LoopTimer {
  uint32_t next_us;   // nächste Deadline in µs
  float    dt_s;      // Soll-dt (1/LOOP_HZ)
  float    dt_meas_s; // gemessenes dt der letzten Iteration
};

// Scheduler initialisieren (setzt die erste Deadline)
void LoopTimer_init(LoopTimer& t);

// true genau einmal pro Periode, sonst false (nicht blockierend)
bool LoopTimer_tick(LoopTimer& t);

// Verbleibende µs bis zur nächsten Deadline, 0 wenn schon überschritten.
// Der SD-Logger nutzt das, um Flush/Sync nur in freier Zeit zu machen.
uint32_t LoopTimer_slack_us(const LoopTimer& t);

// Overrun-Check am Ende der Iteration (meldet bei LOOP_WARNING auf Serial)
void LoopTimer_overrunCheck(uint32_t loop_start_us);
