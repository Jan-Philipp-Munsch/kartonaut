#pragma once
// FlightState.h – Flugzustandsautomat (docs/Plan_2026-10-22.md §2 B2)
//
//   SAFE ──(Kalibrierung, ARM, Durchgang, Akkus, ruhig)──> PAD_READY
//   PAD_READY ──(> LIFTOFF_G für LIFTOFF_HOLD)──> BOOST
//   BOOST ──(spezifische Kraft < BURNOUT_G für BURNOUT_HOLD, oder Zeit)──> COAST
//   COAST ──(vz < 0 für APOGEE_HOLD und Baro unter Maximum, oder Zeit)──> APOGEE
//   APOGEE ──(APOGEE_DWELL abgelaufen)──> DESCENT
//   DESCENT ──(ruhig für LANDED_HOLD)──> LANDED
//   jeder Zustand ──(ABORT-Kommando, Sensorausfall)──> ABORT
//   PAD_READY ──(SAFE-Kommando oder Bedingung verloren)──> SAFE
//   COAST ──(Zeit-Rückfall ohne bestätigten Flug)──> SAFE  (Grund NO_FLIGHT)
//
// Sicherheitssperre (Jan, 22.10.2026): Die Bergung darf erst zünden, wenn Kalman ODER
// Barometer seit dem Start mindestens min_flight_alt_m Steigen gesehen haben. Eine falsche
// Starterkennung auf der Rampe läuft sonst über die Zeit-Rückfälle bis APOGEE und gibt die
// Zündung auf der Rampe frei. Für Tischtests hebt setBenchOverride(true) die Sperre auf.
//
// Zeitbasis ist t_ms des Aufrufers (millis()), damit der Automat in der
// nativen Testumgebung mit aufgezeichneten oder simulierten Flügen läuft.
// Der Automat kennt keine Hardware: Pyro, Servos und Logger reagieren in
// main.cpp auf phase() und auf die Ereignisse.
#include <stdint.h>
#include "KartonautProtocol.h"

enum class FlightPhase : uint8_t {
  SAFE      = KN_PHASE_SAFE,
  PAD_READY = KN_PHASE_PAD_READY,
  BOOST     = KN_PHASE_BOOST,
  COAST     = KN_PHASE_COAST,
  APOGEE    = KN_PHASE_APOGEE,
  DESCENT   = KN_PHASE_DESCENT,
  LANDED    = KN_PHASE_LANDED,
  ABORT     = KN_PHASE_ABORT,
};

const char* flightPhaseName(FlightPhase p);

struct FlightStateConfig {
  float    g_ms2            = 9.81f;
  // Start: spezifische Kraft entlang der Rollachse über der Schwelle, gehalten
  float    liftoff_g        = 2.0f;     // Plan: > 2 g
  uint32_t liftoff_hold_ms  = 50;
  // Brennschluss: spezifische Kraft entlang z unter der Schwelle (freier Flug ≈ 0 g minus Luftwiderstand)
  float    burnout_g        = 0.5f;
  uint32_t burnout_hold_ms  = 100;
  uint32_t burn_max_ms      = 5000;     // Rückfall: E12 brennt 3,55 s
  // Apogäum: Kalman-vz negativ, gehalten, und Barometer unter seinem Maximum
  float    apogee_vz_ms     = -0.5f;
  uint32_t apogee_hold_ms   = 300;
  float    apogee_baro_drop_m = 1.0f;
  uint32_t coast_max_ms     = 8000;     // Rückfall nach Brennschluss (Simulation: Gipfel ≈ 3–4 s nach Brennschluss)
  uint32_t apogee_dwell_ms  = 100;      // APOGEE -> DESCENT (Zeit für die Zündung, siehe Pyro)
  // Landung: ruhig (|a| ≈ g, |vz| klein) für einige Sekunden
  float    landed_vz_ms     = 0.5f;
  float    landed_accel_tol_g = 0.3f;
  uint32_t landed_hold_ms   = 3000;
  uint32_t descent_max_ms   = 120000;   // Rückfall: nach 2 min gilt gelandet
  // Rampenbedingungen
  float    pad_max_tilt_deg = 10.0f;
  float    pad_max_rate_dps = 2.0f;
  float    abort_tilt_deg   = 70.0f;    // im Boost: Regler aus, Fallschirm sobald möglich
  float    min_flight_alt_m = 10.0f;    // Sicherheitssperre: so viel Steigen muss gemessen sein
  bool     require_arm      = true;     // ohne ARM kein PAD_READY (Tischtest: false)
  bool     require_continuity = true;
};

struct FlightInputs {
  uint32_t t_ms = 0;
  float    accel_z_g = 1.0f;     // spezifische Kraft entlang der Rollachse, in g (Rampe: +1)
  float    accel_mag_g = 1.0f;   // Betrag der spezifischen Kraft in g
  float    gyro_mag_dps = 0.0f;  // Betrag der Drehrate
  float    vz_ms = 0.0f;         // Kalman
  float    alt_m = 0.0f;         // Kalman, über Pad
  float    baro_alt_m = 0.0f;    // Barometer, über Pad
  float    tilt_deg = 0.0f;
  bool     armed = false;
  bool     continuity = false;   // Zündkanal für die Bergung hat Durchgang
  bool     calibrated = false;   // Gyro-Bias und Lage gesetzt
  bool     batteries_ok = true;
  bool     sensors_ok = true;
  // Kommandos (Flanken, vom Aufrufer nach dem Aufruf zurückgesetzt)
  bool     cmd_abort = false;
  bool     cmd_safe = false;
  bool     cmd_force_ready = false;   // Tischtest / Prüfstand: PAD_READY ohne ARM und Durchgang
  bool     cmd_force_liftoff = false; // Prüfstand: Start ohne Beschleunigung
};

struct FlightEvent {
  FlightPhase from, to;
  uint8_t     reason;   // KnEventReason
  uint32_t    t_ms;
};

class FlightState {
public:
  explicit FlightState(const FlightStateConfig& cfg = FlightStateConfig()) : cfg_(cfg) {}

  // Einen Schritt rechnen. true, wenn ein Übergang stattfand (dann steht er in lastEvent()).
  bool update(const FlightInputs& in);

  FlightPhase phase() const { return phase_; }
  const FlightEvent& lastEvent() const { return last_; }
  uint32_t phaseEntered_ms() const { return t_phase_; }
  uint32_t liftoff_ms() const { return t_liftoff_; }       // 0 = noch nicht gestartet
  uint32_t burnout_ms() const { return t_burnout_; }
  uint32_t apogee_ms()  const { return t_apogee_; }
  float    maxAlt_m()   const { return alt_max_; }
  float    maxBaroAlt_m() const { return baro_max_; }

  bool inFlight() const { return phase_ >= FlightPhase::BOOST && phase_ <= FlightPhase::DESCENT; }
  bool controlAllowed() const { return phase_ == FlightPhase::BOOST; }
  // Bergungszündung erlaubt: APOGEE/DESCENT, oder ABORT nach einem Start; immer nur mit
  // bestätigtem Flug (Sicherheitssperre) oder aufgehobener Sperre am Tisch
  bool pyroAllowed() const {
    const bool phase_ok = phase_ == FlightPhase::APOGEE || phase_ == FlightPhase::DESCENT ||
                          (phase_ == FlightPhase::ABORT && t_liftoff_ != 0);
    return phase_ok && (flight_confirmed_ || bench_override_);
  }
  bool flightConfirmed() const { return flight_confirmed_; }

  // Tischtest: Sperre aufheben (USB-Taste 'B' in main.cpp). Nie im Flug benutzen.
  void setBenchOverride(bool on) { bench_override_ = on; }
  bool benchOverride() const { return bench_override_; }

  // Nach einem Neustart im Flug: Zustand aus dem Zustandsspeicher übernehmen
  void restore(FlightPhase p, uint32_t t_now_ms, uint32_t t_liftoff_ms, bool flight_confirmed);

  const FlightStateConfig& config() const { return cfg_; }

private:
  void transition(FlightPhase to, uint8_t reason, uint32_t t_ms);
  bool padConditions(const FlightInputs& in) const;

  FlightStateConfig cfg_;
  FlightPhase phase_ = FlightPhase::SAFE;
  FlightEvent last_{FlightPhase::SAFE, FlightPhase::SAFE, KN_REASON_NONE, 0};
  uint32_t t_phase_ = 0, t_liftoff_ = 0, t_burnout_ = 0, t_apogee_ = 0;
  uint32_t t_cond_ = 0;        // Beginn der aktuell gehaltenen Bedingung, 0 = nicht erfüllt
  float    alt_max_ = 0.0f, baro_max_ = 0.0f;
  float    alt0_ = 0.0f, baro0_ = 0.0f;   // Höhen beim Start
  bool     flight_confirmed_ = false;
  bool     bench_override_ = false;
};
