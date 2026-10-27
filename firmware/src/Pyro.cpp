#include "Pyro.h"
#include "Telemetry.h"

bool PyroLogic::conditions(const PyroInputs& in, int ch) {
  if (!in.fitted[ch])                       { refusal_ = "nicht bestueckt"; return false; }
  if (!in.allowed[ch])                      { refusal_ = "Zustand"; return false; }
  if (in.t_launch_ms == 0 || in.t_ms - in.t_launch_ms < p_.min_flight_ms) { refusal_ = "Flugzeit"; return false; }
  if (!in.armed)                            { refusal_ = "nicht scharf"; return false; }
  if (!in.continuity[ch])                   { refusal_ = "kein Durchgang"; return false; }
  if (fires_[ch] >= p_.max_fires)           { refusal_ = "Versuche verbraucht"; return false; }
  refusal_ = "";
  return true;
}

void PyroLogic::update(const PyroInputs& in, bool fire[2]) {
  // Bezug der Reservezeit: erste Freigabe eines Kanals (Kanal 1 kann nach einem Bordstart gesperrt sein)
  if (in.allowed[0] || in.allowed[1]) {
    if (t_allowed_since_ == 0) t_allowed_since_ = in.t_ms ? in.t_ms : 1;
  } else {
    t_allowed_since_ = 0;
  }

  for (int ch = 0; ch < 2; ++ch) {
    if (firing_[ch]) {
      // Puls läuft: Ende nach pulse_ms, oder sobald der Durchgang weg ist, oder ARM fällt
      const bool expired = in.t_ms - t_start_[ch] >= p_.pulse_ms[ch];
      if (expired || !in.continuity[ch] || !in.armed || !in.allowed[ch]) {
        firing_[ch] = false;
        t_end_[ch] = in.t_ms;
        done_ch_[ch] = true;
        if (ch == 0) done_ = true;
      }
      fire[ch] = firing_[ch];
      continue;
    }
    fire[ch] = false;
    // Reservepaar: Kanal 2 wartet nach der ersten Zündung von Kanal 1 die Reservezeit ab
    if (ch == 1 && p_.backup_pair) {
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
    } else if (in.allowed[ch] && (!in.armed || !in.fitted[ch] || fires_[ch] >= p_.max_fires)) {
      done_ch_[ch] = true;   // Zünden unmöglich: der Automat soll nicht ewig warten
      if (ch == 0) done_ = true;
    }
  }
}

bool PyroLogic::updateLaunch(const LaunchPulseInputs& in) {
  if (launch_firing_) {
    uint8_t end = tlm::IGN_END_NONE;
    if (in.thrust)                                    end = tlm::IGN_END_THRUST;
    else if (in.continuity_valid && !in.continuity)   end = tlm::IGN_END_CONT_LOST;
    else if (!in.allowed)                             end = tlm::IGN_END_STOPPED;
    else if (!in.armed)                               end = tlm::IGN_END_DISARMED;
    else if (in.t_ms - t_launch_on_ >= p_.launch_pulse_max_ms) end = tlm::IGN_END_TIMEOUT;
    if (end != tlm::IGN_END_NONE) {
      launch_firing_ = false;
      launch_end_ = end;
      t_launch_off_ = in.t_ms;
    }
    return launch_firing_;
  }
  if (launch_used_ || !in.allowed) return false;
  launch_used_ = true;                                // genau ein Versuch je Startablauf
  if (!in.armed || !in.continuity) {
    launch_end_ = tlm::IGN_END_REFUSED;
    refusal_ = !in.armed ? "nicht scharf" : "kein Durchgang";
    return false;
  }
  launch_firing_ = true;
  t_launch_on_ = in.t_ms ? in.t_ms : 1;
  return true;
}
