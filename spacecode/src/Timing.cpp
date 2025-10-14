#include "Timing.h"

void LoopTimer_init(LoopTimer& t){
  t.dt_s       = 1.0f / LOOP_HZ;         // Soll
  t.dt_meas_s  = t.dt_s;                 // initial
  t.next_us    = micros() + LOOP_PERIOD_US;
}

bool LoopTimer_tick(LoopTimer& t){
  const uint32_t now = micros();

  // Noch zu früh -> keine Iteration
  if ((int32_t)(now - t.next_us) < 0) return false;

  // Start dieser Iteration
  const uint32_t start = micros();

  // gemessenes dt: Zeit seit der letzten geplanten Deadline
  t.dt_meas_s = (start - (t.next_us - LOOP_PERIOD_US)) * 1e-6f;

  // neue Deadline
  t.next_us  += LOOP_PERIOD_US;

  return true;
}

void LoopTimer_overrunCheck(uint32_t loop_start_us){
  const uint32_t dur = micros() - loop_start_us;
  Serial.println(dur);
  if (dur > LOOP_PERIOD_US){
    if (VERBOSE){
      Serial.printf("\n⚠️  Loop overrun: %lu us (> %lu us)\n",
                    (unsigned long)dur, (unsigned long)LOOP_PERIOD_US);
    }
  }
}
