#include "Timing.h"

void LoopTimer_init(LoopTimer& t){
  t.dt_s       = 1.0f / LOOP_HZ;
  t.dt_meas_s  = t.dt_s;
  t.next_us    = micros() + LOOP_PERIOD_US;
}

bool LoopTimer_tick(LoopTimer& t){
  const uint32_t now = micros();

  // Noch zu früh -> keine Iteration (Differenz als int32 ist überlaufsicher)
  if ((int32_t)(now - t.next_us) < 0) return false;

  const uint32_t start = micros();

  // gemessenes dt: Zeit seit der letzten geplanten Deadline
  t.dt_meas_s = (start - (t.next_us - LOOP_PERIOD_US)) * 1e-6f;

  t.next_us += LOOP_PERIOD_US;
  return true;
}

uint32_t LoopTimer_slack_us(const LoopTimer& t){
  const int32_t slack = (int32_t)(t.next_us - micros());
  return slack > 0 ? (uint32_t)slack : 0u;
}

void LoopTimer_overrunCheck(uint32_t loop_start_us){
  const uint32_t dur = micros() - loop_start_us;
  if (dur > LOOP_PERIOD_US && LOOP_WARNING){
    Serial.printf("\nLoop overrun: %lu us (> %lu us)\n",
                  (unsigned long)dur, (unsigned long)LOOP_PERIOD_US);
  }
}
