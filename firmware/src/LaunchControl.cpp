#include "LaunchControl.h"
#include <math.h>

bool gapContinuity(float pre_V, float gap_V, float arm_V, float gap_us, float tau_us, float ratio) {
  const float expected = (arm_V - pre_V) * (1.0f - expf(-gap_us / tau_us));
  if (expected <= 0.05f) return false;      // ohne Arming-Spannung keine Aussage
  return gap_V - pre_V > ratio * expected;
}

PyroGates pyroGates(const FlightStateMachine& fsm, bool chute_mode, int launch_ch, int ch_chute, int ch_igniter) {
  PyroGates g;
  g.recovery[ch_chute] = fsm.pyroAllowed();
  g.recovery[ch_igniter] = chute_mode ? fsm.pyroAllowed() : fsm.igniterAllowed();
  if (fsm.onboardLaunch() || fsm.launchSequence()) g.recovery[launch_ch] = false;
  g.launch = fsm.launchAllowed();
  return g;
}

uint8_t LaunchPreconditions::update(const PrecondInputs& in) {
  uint8_t m = 0;
  if (in.armed) m |= tlm::PRE_ARM_V;
  if (in.armed && in.continuity) m |= tlm::PRE_CONT;
  if (in.vbat1_V >= p_.min_vbat1_V && in.vbat2_V >= p_.min_vbat2_V) m |= tlm::PRE_BATT;
  // ruhig: Drehraten still_hold_ms lang unter der Schwelle; aufrecht: Kippung im Rampenwinkel
  if (in.omega_max_dps < p_.still_dps) {
    if (still_since_ == 0) still_since_ = in.t_ms ? in.t_ms : 1;
  } else {
    still_since_ = 0;
  }
  const bool still = still_since_ != 0 && in.t_ms - still_since_ >= p_.still_hold_ms;
  if (still && in.tilt_deg <= p_.max_tilt_deg) m |= tlm::PRE_STILL;
  if (in.sensors_ok && in.calibrated && in.logging) m |= tlm::PRE_SENSORS;
  if (in.servo_test_ok) m |= tlm::PRE_SERVO;
  if (in.launch_enabled) m |= tlm::PRE_KEY;
  mask_ = m;
  return m;
}

ServoTestOutput ServoSelfTest::update(uint32_t t_ms, float current_A) {
  ServoTestOutput o;
  if (!running_) return o;
  if (current_A > peak_a_) peak_a_ = current_A;
  const uint32_t step = (t_ms - t0_) / step_ms_;
  static const int8_t YAW[6] = {1, -1, 0, 0, 0, 0}, PITCH[6] = {0, 0, 0, 1, -1, 0};
  if (step >= 6) {
    running_ = false; done_ = true;
    return o;                       // Mitte
  }
  o.active = true;
  o.yaw_off_deg = d_ * YAW[step];
  o.pitch_off_deg = d_ * PITCH[step];
  return o;
}

LaunchSignal launchSignal(FlightState s, uint32_t t, uint32_t left) {
  LaunchSignal o;
  switch (s) {
    case FlightState::ARMED:         // Summer im Sekundentakt, LED rot blinkend
      o.active = true;
      o.beep = (t % 1000) < 100;
      o.led_on = (t % 1000) < 500;
      break;
    case FlightState::COUNTDOWN:     // Summer schnell, letzte Sekunde Dauerton
      o.active = true;
      o.beep = left <= 1000 ? true : (t % 250) < 100;
      o.led_on = (t % 250) < 125;
      break;
    case FlightState::MISFIRE:       // Dreiertakt bis SAFE
      o.active = true;
      o.beep = (t % 1500) < 600 && (t % 200) < 100;
      o.led_on = o.beep;
      break;
    default:
      break;
  }
  return o;
}

void IgnitionRecorder::begin(uint32_t t0_ms, float arm_V) {
  *this = IgnitionRecorder();
  active_ = true;
  t0_ = t0_ms;
  arm_before_ = arm_V;
}

void IgnitionRecorder::armSample(float v) {
  if (v < arm_min_) arm_min_ = v;
  if (samples_ < 0xFFFF) ++samples_;
}

void IgnitionRecorder::vbat1Sample(float v) {
  if (v < vbat1_min_) vbat1_min_ = v;
}

uint16_t IgnitionRecorder::rel(uint32_t t, uint32_t t0) {
  if (t == 0) return tlm::IGN_NO_TIME;
  const uint32_t d = t - t0;
  return d >= tlm::IGN_NO_TIME ? tlm::IGN_NO_TIME - 1 : (uint16_t)d;
}

uint16_t IgnitionRecorder::mv(float v) {
  if (v >= 1e8f) return 0;           // nie gemessen
  if (v <= 0.f) return 0;
  const float m = v * 1000.f + 0.5f;
  return m >= 65535.f ? 65535 : (uint16_t)m;
}

tlm::IgnPayload IgnitionRecorder::payload() const {
  tlm::IgnPayload p{};
  p.t_pulse_on_ms = rel(t_on_, t0_);
  p.t_cont_lost_ms = rel(t_cont_, t0_);
  p.t_thrust_ms = rel(t_thrust_, t0_);
  p.t_pulse_off_ms = rel(t_off_, t0_);
  p.arm_before_mv = mv(arm_before_);
  p.arm_min_mv = mv(arm_min_);
  p.vbat1_min_mv = mv(vbat1_min_);
  p.arm_samples = samples_;
  p.end_reason = reason_;
  return p;
}
