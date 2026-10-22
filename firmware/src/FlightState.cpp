#include "FlightState.h"

const char* flightStateName(FlightState s) {
  switch (s) {
    case FlightState::SAFE: return "SAFE";
    case FlightState::PAD_READY: return "PAD_READY";
    case FlightState::BOOST: return "BOOST";
    case FlightState::COAST: return "COAST";
    case FlightState::APOGEE: return "APOGEE";
    case FlightState::DESCENT: return "DESCENT";
    case FlightState::LANDED: return "LANDED";
    case FlightState::ABORT: return "ABORT";
  }
  return "?";
}

void FlightStateMachine::transition(FlightState to, FlightReason why, uint32_t t_ms) {
  if (n_events_ < MAX_EVENTS) {
    events_[n_events_++] = FlightEvent{t_ms, s_, to, why};
  } else {
    for (int i = 1; i < MAX_EVENTS; ++i) events_[i - 1] = events_[i];
    events_[MAX_EVENTS - 1] = FlightEvent{t_ms, s_, to, why};
  }
  s_ = to;
  launch_since_ = burnout_since_ = apogee_since_ = landed_since_ = 0;
}

// Bedingung muss hold_ms lang ununterbrochen gelten. since_ms = 0 heißt "nicht aktiv".
bool FlightStateMachine::held(uint32_t& since_ms, bool cond, uint32_t t_ms, uint32_t hold_ms) {
  if (!cond) { since_ms = 0; return false; }
  if (since_ms == 0) since_ms = (t_ms == 0) ? 1 : t_ms;
  return (t_ms - since_ms) >= hold_ms;
}

void FlightStateMachine::restore(FlightState s, uint32_t t_launch_ms, uint32_t t_burnout_ms, uint32_t t_apogee_ms,
                                 float baro_max_m, uint32_t now_ms) {
  t_launch_ms_ = t_launch_ms; t_burnout_ms_ = t_burnout_ms; t_apogee_ms_ = t_apogee_ms;
  baro_max_m_ = baro_max_m;
  transition(s, FlightReason::RESTORED, now_ms);
}

bool FlightStateMachine::update(const FlightInputs& in) {
  const uint32_t t = in.t_ms;
  const FlightState before = s_;

  // Abbruch vom Boden gilt überall außer LANDED
  if (in.cmd == FlightCmd::ABORT && s_ != FlightState::LANDED && s_ != FlightState::ABORT) {
    transition(FlightState::ABORT, FlightReason::CMD, t);
    return true;
  }

  switch (s_) {
    case FlightState::SAFE:
      if (in.cmd == FlightCmd::PAD_READY) {
        if (in.calibrated && in.sensors_ok) transition(FlightState::PAD_READY, FlightReason::CMD, t);
        else transition(FlightState::SAFE, FlightReason::NOT_READY, t);   // Ereignis zur Rückmeldung
      }
      break;

    case FlightState::PAD_READY:
      if (in.cmd == FlightCmd::SAFE) { transition(FlightState::SAFE, FlightReason::CMD, t); break; }
      if (held(launch_since_, in.a_norm_ms2 > p_.launch_accel_ms2, t, p_.launch_hold_ms)) {
        t_launch_ms_ = t - p_.launch_hold_ms;
        baro_max_m_ = in.baro_alt_m;
        transition(FlightState::BOOST, FlightReason::ACCEL, t);
      }
      break;

    case FlightState::BOOST:
      if (in.baro_alt_m > baro_max_m_) baro_max_m_ = in.baro_alt_m;
      if (held(burnout_since_, in.a_axial_ms2 < p_.burnout_axial_ms2, t, p_.burnout_hold_ms)) {
        t_burnout_ms_ = t;
        transition(FlightState::COAST, FlightReason::BURNOUT_ACCEL, t);
      } else if (t - t_launch_ms_ >= p_.burn_max_ms) {
        t_burnout_ms_ = t;
        transition(FlightState::COAST, FlightReason::BURN_TIMEOUT, t);
      }
      break;

    case FlightState::COAST:
    case FlightState::ABORT: {
      if (s_ == FlightState::ABORT) {
        if (t_launch_ms_ == 0) {                      // Abbruch auf dem Pad: zurück nach SAFE
          if (in.cmd == FlightCmd::SAFE) transition(FlightState::SAFE, FlightReason::CMD, t);
          break;
        }
        if (t_burnout_ms_ == 0) t_burnout_ms_ = t;    // Abbruch während BOOST: ab jetzt antriebslos
      }
      if (in.baro_alt_m > baro_max_m_) baro_max_m_ = in.baro_alt_m;
      const bool early = (t - t_burnout_ms_) < p_.apogee_earliest_ms;
      const bool sensors = in.vz_ms < p_.apogee_vz_ms && in.baro_alt_m < baro_max_m_ - p_.apogee_baro_drop_m;
      if (!early && held(apogee_since_, sensors, t, p_.apogee_hold_ms)) {
        t_apogee_ms_ = t;
        transition(FlightState::APOGEE, FlightReason::APOGEE_SENSORS, t);
      } else if (t - t_burnout_ms_ >= p_.apogee_fallback_ms) {
        t_apogee_ms_ = t;
        transition(FlightState::APOGEE, FlightReason::APOGEE_TIMEOUT, t);
      }
      break;
    }

    case FlightState::APOGEE:
      if (in.pyro_done || t - t_apogee_ms_ >= p_.descent_after_ms) {
        transition(FlightState::DESCENT, FlightReason::PYRO_DONE, t);
      }
      break;

    case FlightState::DESCENT: {
      const bool still = in.vz_ms > -p_.landed_vz_ms && in.vz_ms < p_.landed_vz_ms && in.alt_m < p_.landed_alt_m;
      if (held(landed_since_, still, t, p_.landed_hold_ms)) {
        transition(FlightState::LANDED, FlightReason::LANDED_SENSORS, t);
      } else if (t - t_launch_ms_ >= p_.flight_max_ms) {
        transition(FlightState::LANDED, FlightReason::FLIGHT_TIMEOUT, t);
      }
      break;
    }

    case FlightState::LANDED:
      break;
  }
  return s_ != before || (n_events_ > 0 && events_[n_events_ - 1].t_ms == t && events_[n_events_ - 1].to == s_
                          && events_[n_events_ - 1].reason == FlightReason::NOT_READY);
}
