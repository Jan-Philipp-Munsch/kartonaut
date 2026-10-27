#pragma once
// LaunchControl.h – Bausteine des Motorstarts an Bord (Plan Bordzündung 27.10.2026, §4), ohne Hardware:
//
//   LaunchPreconditions  die sieben Vorbedingungen für ARM als Bitmaske (tlm::Precond); main.cpp prüft
//                        sie vor ARM und laufend in ARMED/COUNTDOWN (FlightInputs::launch_ready)
//   ServoSelfTest        kurzer Ausschlag beider TVC-Servos beim Eintritt in PAD_READY, Rückkehr in die Mitte
//   launchSignal()       Summer- und LED-Takt für ARMED, COUNTDOWN und MISFIRE
//   IgnitionRecorder     Zeitmarken und Spannungen des Startpulses für den IGN-Rahmen
//   LogRing              Ringpuffer der Log-Frames vor ARMED (die letzten 2 s mit voller Rate)
//
// Kein Arduino: läuft in den nativen Tests.
#include <stdint.h>
#include <stddef.h>
#include "FlightState.h"
#include "Telemetry.h"

// ---------------------------------------------------------------- Vorbedingungen
struct PrecondInputs {
  uint32_t t_ms = 0;
  bool  armed = false;          // VBAT_ARMED über PYRO_ARM_MIN_V
  bool  continuity = false;     // Durchgang am Startkanal
  float vbat1_V = 0, vbat2_V = 0;
  float omega_max_dps = 0;      // größter Betrag der drei Drehraten
  float tilt_deg = 0;           // Kippung gegen die Senkrechte
  bool  sensors_ok = false, calibrated = false, logging = false;
  bool  servo_test_ok = false;
  bool  launch_enabled = false; // Schlüssel vorhanden und nicht leer
};

struct PrecondParams {
  float    min_vbat1_V, min_vbat2_V;
  float    still_dps;           // Rakete ruhig: alle Drehraten darunter ...
  uint32_t still_hold_ms;       // ... für so lange
  float    max_tilt_deg;
};

class LaunchPreconditions {
public:
  explicit LaunchPreconditions(const PrecondParams& p) : p_(p) {}
  uint8_t update(const PrecondInputs& in);   // jeden Takt; liefert die Bitmaske
  uint8_t mask() const { return mask_; }
  bool    allOk() const { return mask_ == tlm::PRE_ALL; }

private:
  PrecondParams p_;
  uint32_t still_since_ = 0;
  uint8_t  mask_ = 0;
};

// Durchgang in der Messlücke: pre_V = Drain-Messwert direkt vor dem Abschalten, gap_V = nach gap_us
// mit FET aus, arm_V = VBAT_ARMED (alles in Volt am Teilereingang). Mit heilem Anzünder lädt der
// Teilerkondensator gegen VBAT_ARMED: erwarteter Anstieg (arm_V - pre_V) · (1 - exp(-gap/tau)).
bool gapContinuity(float pre_V, float gap_V, float arm_V, float gap_us, float tau_us, float ratio);

// ---------------------------------------------------------------- Freigaben der Pyro-Kanäle
// Bergung (PyroLogic::update) und Startpuls (PyroLogic::updateLaunch) aus dem Flugzustand. Der Startkanal
// zündet nur in IGNITION. Nach einem Bordstart bleibt er für die Bergung gesperrt: dort hängt der
// abgebrannte Anzünder, dessen Drähte kurzgeschlossen sein können (Jan, 27.10.2026).
struct PyroGates {
  bool recovery[2] = {false, false};
  bool launch = false;
};
PyroGates pyroGates(const FlightStateMachine& fsm, bool chute_mode, int launch_ch, int ch_chute, int ch_igniter);

// ---------------------------------------------------------------- Servo-Selbsttest
// Ablauf je step_ms: Yaw +d, Yaw -d, Mitte, Pitch +d, Pitch -d, Mitte. Bestanden, wenn der Ablauf
// durch ist und – falls min_current_A > 0 – der Servostrom dabei mindestens einmal darüber lag.
struct ServoTestOutput {
  bool  active = false;
  float yaw_off_deg = 0, pitch_off_deg = 0;   // Servo-Grad relativ zur Mitte
};

class ServoSelfTest {
public:
  ServoSelfTest(float deflect_deg, uint32_t step_ms, float min_current_A)
    : d_(deflect_deg), step_ms_(step_ms), min_a_(min_current_A) {}
  void start(uint32_t t_ms) { t0_ = t_ms; running_ = true; done_ = false; peak_a_ = 0; }
  void reset() { running_ = false; done_ = false; peak_a_ = 0; }
  ServoTestOutput update(uint32_t t_ms, float current_A);
  bool running() const { return running_; }
  bool passed() const { return done_ && (min_a_ <= 0.f || peak_a_ >= min_a_); }
  bool finished() const { return done_; }
  float peakCurrent() const { return peak_a_; }

private:
  float d_; uint32_t step_ms_; float min_a_;
  uint32_t t0_ = 0;
  bool running_ = false, done_ = false;
  float peak_a_ = 0;
};

// ---------------------------------------------------------------- Summer und LED
struct LaunchSignal {
  bool active = false;   // false: Zustand ohne eigenes Muster (normale Zustandsfarbe)
  bool beep = false;
  bool led_on = false;   // rot an
};
// t_in_state_ms: Zeit seit Eintritt in den Zustand; countdown_left_ms nur für COUNTDOWN
LaunchSignal launchSignal(FlightState s, uint32_t t_in_state_ms, uint32_t countdown_left_ms);

// ---------------------------------------------------------------- IGN-Rahmen
class IgnitionRecorder {
public:
  // Eintritt in IGNITION; arm_V = VBAT_ARMED kurz vor dem Puls
  void begin(uint32_t t0_ms, float arm_V);
  void pulseOn(uint32_t t_ms) { if (t_on_ == 0) t_on_ = t_ms ? t_ms : 1; }
  void pulseOff(uint32_t t_ms, uint8_t reason) { if (t_off_ == 0) { t_off_ = t_ms ? t_ms : 1; reason_ = reason; } }
  void contLost(uint32_t t_ms) { if (t_cont_ == 0) t_cont_ = t_ms ? t_ms : 1; }
  void thrust(uint32_t t_ms) { if (t_thrust_ == 0) t_thrust_ = t_ms ? t_ms : 1; }
  void refused() { reason_ = tlm::IGN_END_REFUSED; }
  void armSample(float arm_V);     // schnelle Messung während des Pulses (>= 1 kHz)
  void vbat1Sample(float vbat1_V); // 1S während des Pulses
  bool active() const { return active_; }
  tlm::IgnPayload payload() const;
  void end() { active_ = false; }

private:
  static uint16_t rel(uint32_t t, uint32_t t0);
  static uint16_t mv(float v);
  bool active_ = false;
  uint32_t t0_ = 0, t_on_ = 0, t_off_ = 0, t_cont_ = 0, t_thrust_ = 0;
  float arm_before_ = 0, arm_min_ = 1e9f, vbat1_min_ = 1e9f;
  uint16_t samples_ = 0;
  uint8_t reason_ = tlm::IGN_END_NONE;
};

// ---------------------------------------------------------------- Ringpuffer
// FIFO fester Größe; voll: das älteste Element fällt heraus.
template <typename T, size_t N>
class LogRing {
public:
  void push(const T& v) {
    buf_[(head_ + n_) % N] = v;
    if (n_ < N) ++n_; else head_ = (head_ + 1) % N;
  }
  bool pop(T& out) {
    if (n_ == 0) return false;
    out = buf_[head_]; head_ = (head_ + 1) % N; --n_;
    return true;
  }
  size_t size() const { return n_; }
  bool empty() const { return n_ == 0; }
  void clear() { head_ = n_ = 0; }
  static constexpr size_t capacity() { return N; }

private:
  T buf_[N];
  size_t head_ = 0, n_ = 0;
};
