#include "Pyro.h"

void PyroLogic::update(uint32_t t_ms, bool armed, const bool continuity[CHANNELS], bool phase_allows) {
  t_now_ = t_ms;
  armed_ = armed;
  phase_allows_ = phase_allows;
  for (int i = 0; i < CHANNELS; ++i) {
    Channel& c = ch_[i];
    c.continuity = continuity[i];
    if (!c.firing) continue;

    const uint32_t dur = t_ms - c.t_fire_start;
    bool stop = dur >= cfg_.pulse_ms || dur >= cfg_.pulse_max_ms;

    // Durchgang weg: Brücke durch. Kurze Aussetzer (Messrauschen) überbrücken.
    if (!c.continuity) {
      if (c.t_cont_lost == 0) c.t_cont_lost = t_ms ? t_ms : 1;
      else if (t_ms - c.t_cont_lost >= cfg_.cont_grace_ms) stop = true;
    } else {
      c.t_cont_lost = 0;
    }
    // Scharfschaltung weg: Hardware ist ohnehin stromlos, Logik beendet den Puls
    if (!armed) stop = true;

    if (stop) {
      c.firing = false;
      c.fired = true;
    }
  }
}

bool PyroLogic::fire(int ch, uint32_t t_ms) {
  if (!valid(ch)) return false;
  Channel& c = ch_[ch];
  if (!c.fitted || c.fired || c.firing) return false;    // Regel 3
  if (!phase_allows_) return false;                      // Regel 1
  if (!armed_ || !c.continuity) return false;            // Regel 2
  c.firing = true;
  c.t_fire_start = t_ms;
  c.t_cont_lost = 0;
  ++c.fire_count;
  return true;
}

uint8_t PyroLogic::firedMask() const {
  uint8_t m = 0;
  for (int i = 0; i < CHANNELS; ++i) if (ch_[i].fired) m |= uint8_t(1u << i);
  return m;
}

void PyroLogic::restoreFiredMask(uint8_t mask) {
  for (int i = 0; i < CHANNELS; ++i) if (mask & (1u << i)) ch_[i].fired = true;
}
