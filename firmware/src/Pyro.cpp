#include "Pyro.h"

bool PyroLogic::conditions(const PyroInputs& in, int ch) {
  if (!in.fitted[ch])                       { refusal_ = "nicht bestueckt"; return false; }
  if (!in.allowed)                          { refusal_ = "Zustand"; return false; }
  if (in.t_launch_ms == 0 || in.t_ms - in.t_launch_ms < p_.min_flight_ms) { refusal_ = "Flugzeit"; return false; }
  if (!in.armed)                            { refusal_ = "nicht scharf"; return false; }
  if (!in.continuity[ch])                   { refusal_ = "kein Durchgang"; return false; }
  if (fires_[ch] >= p_.max_fires)           { refusal_ = "Versuche verbraucht"; return false; }
  refusal_ = "";
  return true;
}

void PyroLogic::update(const PyroInputs& in, bool fire[2]) {
  if (in.allowed) {
    if (t_allowed_since_ == 0) t_allowed_since_ = in.t_ms ? in.t_ms : 1;
  } else {
    t_allowed_since_ = 0;
  }

  for (int ch = 0; ch < 2; ++ch) {
    if (firing_[ch]) {
      // Puls läuft: Ende nach pulse_ms, oder sobald der Durchgang weg ist, oder ARM fällt
      const bool expired = in.t_ms - t_start_[ch] >= p_.pulse_ms;
      if (expired || !in.continuity[ch] || !in.armed || !in.allowed) {
        firing_[ch] = false;
        t_end_[ch] = in.t_ms;
        if (ch == 0) done_ = true;
      }
      fire[ch] = firing_[ch];
      continue;
    }
    fire[ch] = false;
    // Kanal 2 wartet nach der ersten Zündung von Kanal 1 die Reservezeit ab
    if (ch == 1) {
      const uint32_t ref = t_first_fire_ ? t_first_fire_ : t_allowed_since_;
      if (ref == 0 || in.t_ms - ref < p_.backup_delay_ms) continue;
    }
    if (fires_[ch] > 0 && in.t_ms - t_end_[ch] < p_.retry_delay_ms) continue;   // Wartezeit vor dem 2. Versuch
    if (conditions(in, ch)) {
      firing_[ch] = true;
      t_start_[ch] = in.t_ms;
      fires_[ch]++;
      if (t_first_fire_ == 0) t_first_fire_ = in.t_ms;
      fire[ch] = true;
    } else if (ch == 0 && in.allowed && (!in.armed || !in.fitted[0] || fires_[0] >= p_.max_fires)) {
      done_ = true;   // Zünden unmöglich: der Automat soll nicht ewig in APOGEE warten
    }
  }
}
