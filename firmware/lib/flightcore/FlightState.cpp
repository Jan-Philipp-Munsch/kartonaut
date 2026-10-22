#include "FlightState.h"
#include <math.h>

const char* flightPhaseName(FlightPhase p) {
  switch (p) {
    case FlightPhase::SAFE:      return "SAFE";
    case FlightPhase::PAD_READY: return "PAD_READY";
    case FlightPhase::BOOST:     return "BOOST";
    case FlightPhase::COAST:     return "COAST";
    case FlightPhase::APOGEE:    return "APOGEE";
    case FlightPhase::DESCENT:   return "DESCENT";
    case FlightPhase::LANDED:    return "LANDED";
    case FlightPhase::ABORT:     return "ABORT";
  }
  return "?";
}

void FlightState::transition(FlightPhase to, uint8_t reason, uint32_t t_ms) {
  last_ = FlightEvent{phase_, to, reason, t_ms};
  phase_ = to;
  t_phase_ = t_ms;
  t_cond_ = 0;
}

void FlightState::restore(FlightPhase p, uint32_t t_now_ms, uint32_t t_liftoff_ms, bool flight_confirmed) {
  flight_confirmed_ = flight_confirmed;
  last_ = FlightEvent{phase_, p, KN_REASON_RESTORED, t_now_ms};
  phase_ = p;
  t_phase_ = t_now_ms;
  t_liftoff_ = t_liftoff_ms;
  t_cond_ = 0;
}

bool FlightState::padConditions(const FlightInputs& in) const {
  if (!in.calibrated || !in.sensors_ok || !in.batteries_ok) return false;
  if (cfg_.require_arm && !in.armed) return false;
  if (cfg_.require_continuity && !in.continuity) return false;
  if (in.tilt_deg > cfg_.pad_max_tilt_deg) return false;
  if (in.gyro_mag_dps > cfg_.pad_max_rate_dps) return false;
  return true;
}

// Hilfe: Bedingung muss hold_ms lang ununterbrochen gelten
static bool held(uint32_t& t_cond, bool cond, uint32_t t_ms, uint32_t hold_ms) {
  if (!cond) { t_cond = 0; return false; }
  if (t_cond == 0) { t_cond = t_ms ? t_ms : 1; return hold_ms == 0; }
  return (t_ms - t_cond) >= hold_ms;
}

bool FlightState::update(const FlightInputs& in) {
  const uint32_t t = in.t_ms;

  // Übergeordnet: Abbruch jederzeit, Sensorausfall im Flug
  if (in.cmd_abort && phase_ != FlightPhase::ABORT && phase_ != FlightPhase::LANDED) {
    transition(FlightPhase::ABORT, KN_REASON_COMMAND, t);
    return true;
  }
  if (!in.sensors_ok && inFlight()) {
    transition(FlightPhase::ABORT, KN_REASON_SENSOR_FAIL, t);
    return true;
  }

  if (inFlight() || phase_ == FlightPhase::ABORT) {
    if (in.alt_m > alt_max_) alt_max_ = in.alt_m;
    if (in.baro_alt_m > baro_max_) baro_max_ = in.baro_alt_m;
    if (t_liftoff_ != 0 && (alt_max_ - alt0_ >= cfg_.min_flight_alt_m || baro_max_ - baro0_ >= cfg_.min_flight_alt_m))
      flight_confirmed_ = true;
  }

  switch (phase_) {
    case FlightPhase::SAFE:
      if (in.cmd_force_ready && in.calibrated) {
        transition(FlightPhase::PAD_READY, KN_REASON_COMMAND, t);
        return true;
      }
      if (held(t_cond_, padConditions(in), t, 1000)) {
        transition(FlightPhase::PAD_READY, KN_REASON_READY, t);
        return true;
      }
      return false;

    case FlightPhase::PAD_READY:
      if (in.cmd_safe) { transition(FlightPhase::SAFE, KN_REASON_COMMAND, t); return true; }
      if (in.cmd_force_liftoff) {
        t_liftoff_ = t; alt_max_ = alt0_ = in.alt_m; baro_max_ = baro0_ = in.baro_alt_m;
        transition(FlightPhase::BOOST, KN_REASON_COMMAND, t);
        return true;
      }
      if (held(t_cond_, in.accel_z_g > cfg_.liftoff_g, t, cfg_.liftoff_hold_ms)) {
        t_liftoff_ = t - cfg_.liftoff_hold_ms;
        alt_max_ = alt0_ = in.alt_m; baro_max_ = baro0_ = in.baro_alt_m;
        transition(FlightPhase::BOOST, KN_REASON_ACCEL, t);
        return true;
      }
      // Bedingung verloren (Schlüssel gezogen, Akku leer): zurück, aber nicht
      // bei kleinen Wacklern, deshalb ohne Haltezeit nur für harte Kriterien
      if ((cfg_.require_arm && !in.armed) || !in.batteries_ok || !in.sensors_ok) {
        transition(FlightPhase::SAFE, KN_REASON_READY, t);
        return true;
      }
      return false;

    case FlightPhase::BOOST:
      if (in.tilt_deg > cfg_.abort_tilt_deg) {
        transition(FlightPhase::ABORT, KN_REASON_TILT, t);
        return true;
      }
      if (held(t_cond_, in.accel_z_g < cfg_.burnout_g, t, cfg_.burnout_hold_ms)) {
        t_burnout_ = t;
        transition(FlightPhase::COAST, KN_REASON_ACCEL, t);
        return true;
      }
      if (t - t_phase_ >= cfg_.burn_max_ms) {
        t_burnout_ = t;
        transition(FlightPhase::COAST, KN_REASON_TIMEOUT, t);
        return true;
      }
      return false;

    case FlightPhase::COAST: {
      const bool falling = in.vz_ms < cfg_.apogee_vz_ms
                        && in.baro_alt_m < baro_max_ - cfg_.apogee_baro_drop_m;
      if (held(t_cond_, falling, t, cfg_.apogee_hold_ms)) {
        t_apogee_ = t;
        transition(FlightPhase::APOGEE, KN_REASON_VELOCITY, t);
        return true;
      }
      if (t - t_phase_ >= cfg_.coast_max_ms) {
        if (!flight_confirmed_ && !bench_override_) {
          // Start war falsch erkannt (Stoß auf der Rampe): nichts zünden, zurück in den sicheren Zustand
          t_liftoff_ = t_burnout_ = 0;
          transition(FlightPhase::SAFE, KN_REASON_NO_FLIGHT, t);
          return true;
        }
        t_apogee_ = t;
        transition(FlightPhase::APOGEE, KN_REASON_TIMEOUT, t);
        return true;
      }
      return false;
    }

    case FlightPhase::APOGEE:
      if (t - t_phase_ >= cfg_.apogee_dwell_ms) {
        transition(FlightPhase::DESCENT, KN_REASON_TIMEOUT, t);
        return true;
      }
      return false;

    case FlightPhase::DESCENT:
    case FlightPhase::ABORT: {
      const bool still = fabsf(in.vz_ms) < cfg_.landed_vz_ms
                      && fabsf(in.accel_mag_g - 1.0f) < cfg_.landed_accel_tol_g;
      // ABORT auf der Rampe (vor dem Start) bleibt ABORT; erst nach einem Start
      // gibt es eine Landung
      if (t_liftoff_ == 0) return false;
      if (held(t_cond_, still, t, cfg_.landed_hold_ms)) {
        transition(FlightPhase::LANDED, KN_REASON_LANDED, t);
        return true;
      }
      if (t - t_phase_ >= cfg_.descent_max_ms) {
        transition(FlightPhase::LANDED, KN_REASON_TIMEOUT, t);
        return true;
      }
      return false;
    }

    case FlightPhase::LANDED:
      return false;
  }
  return false;
}
