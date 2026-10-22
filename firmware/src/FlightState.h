#pragma once
// FlightState.h – Flugzustandsautomat (Plan 22.10.2026, B2)
//
//   SAFE -> PAD_READY -> BOOST -> COAST -> APOGEE -> DESCENT -> LANDED, dazu ABORT.
//
// SAFE       nach dem Einschalten; Regler aus, Pyro gesperrt. Kalibrierung läuft hier.
// PAD_READY  auf Kommando (Boden oder Taster), wenn kalibriert und Sensoren ok; wartet
//            auf den Start (|a| > 2 g für 50 ms).
// BOOST      Motor brennt, Regler aktiv. Ende: axiale spezifische Kraft klein für 100 ms
//            oder Rückfall nach FS_BURN_MAX_MS.
// COAST      antriebslos; Regler aus (kein Schub, keine Stellmöglichkeit). Apogäum:
//            Kalman-vz < 0 UND Barometer unter seinem Maximum, beides für 200 ms;
//            Rückfall nach FS_APOGEE_FALLBACK_MS.
// APOGEE     Pyro darf zünden (Pyro.h prüft ARM und Durchgang). Nach FS_DESCENT_AFTER_MS
//            weiter nach DESCENT.
// DESCENT    am Fallschirm; Landung: |vz| klein und Höhe klein für 2 s, Rückfall nach 2 min.
// LANDED     alles aus, Log schließen.
// ABORT      vom Boden: auf dem Pad zurück nach SAFE; im Flug Regler aus, Bergung läuft
//            weiter (Apogäumslogik wie COAST), damit die Rakete am Schirm kommt.
//
// Bergungsart (FlightParams::landing_mode, Config.h RECOVERY_MODE):
//   Fallschirm: wie oben, Pyro-Kanal 1 zündet die Ausstoßladung in APOGEE.
//   Landebrennen (zweiter Motor): APOGEE geht sofort in DESCENT (freier Fall), LandingBurn.h
//   entscheidet die Zündung (in.ignite_now) -> LANDING_BURN: Anzünder auf Pyro-Kanal 2, Regler
//   wieder aktiv; LANDED, wenn die Rakete nach dem Brennen ruhig am Boden liegt. Ist das
//   Landebrennen unmöglich (in.landing_possible = false: nicht scharf, kein Durchgang am
//   Anzünder, ABORT), fällt die Bergung auf den Fallschirm in APOGEE zurück.
//
// Jeder Übergang landet mit Zeitstempel und Grund im Ereignispuffer (Log, Telemetrie).
// Kein Arduino: läuft in den nativen Tests. Zeiten in ms (millis()).
#include <stdint.h>

enum class FlightState : uint8_t {
  SAFE = 0, PAD_READY = 1, BOOST = 2, COAST = 3, APOGEE = 4, DESCENT = 5, LANDED = 6, ABORT = 7,
  LANDING_BURN = 8
};

enum class FlightCmd : uint8_t { NONE = 0, PAD_READY = 1, ABORT = 2, SAFE = 3 };

enum class FlightReason : uint8_t {
  NONE = 0, CMD = 1, ACCEL = 2, BURNOUT_ACCEL = 3, BURN_TIMEOUT = 4, APOGEE_SENSORS = 5,
  APOGEE_TIMEOUT = 6, PYRO_DONE = 7, LANDED_SENSORS = 8, FLIGHT_TIMEOUT = 9, RESTORED = 10,
  NOT_READY = 11, LANDING_FREEFALL = 12, IGNITION = 13, LANDING_FALLBACK = 14, BURN_END = 15
};

const char* flightStateName(FlightState s);

struct FlightInputs {
  uint32_t t_ms = 0;
  float    a_norm_ms2 = 0;     // |spezifische Kraft|
  float    a_axial_ms2 = 0;    // spezifische Kraft entlang der Längsachse (+ = Schub)
  float    alt_m = 0;          // Kalman-Höhe über dem Pad
  float    vz_ms = 0;          // Kalman-Vertikalgeschwindigkeit
  float    baro_alt_m = 0;     // Barometerhöhe über dem Pad
  bool     calibrated = false; // Gyro-Nullpunkt, Bodendruck, Lage gesetzt
  bool     sensors_ok = false;
  bool     pyro_done = false;  // Pyro.h: Zündpuls beendet (oder nicht möglich)
  bool     landing_possible = true;   // Landemodus: Anzünder hat Durchgang, scharf, kein Abbruch
  bool     ignite_now = false;        // Landemodus: LandingPlanner sagt zünden
  FlightCmd cmd = FlightCmd::NONE;
};

struct FlightEvent {
  uint32_t t_ms = 0;
  FlightState from = FlightState::SAFE, to = FlightState::SAFE;
  FlightReason reason = FlightReason::NONE;
};

struct FlightParams {
  float    launch_accel_ms2, burnout_axial_ms2, apogee_vz_ms, apogee_baro_drop_m, landed_vz_ms, landed_alt_m;
  uint32_t launch_hold_ms, burnout_hold_ms, burn_max_ms, apogee_earliest_ms, apogee_hold_ms,
           apogee_fallback_ms, descent_after_ms, landed_hold_ms, flight_max_ms;
  bool     landing_mode = false;       // true = Landebrennen statt Fallschirm
  uint32_t landing_burn_max_ms = 6000; // LANDING_BURN -> LANDED spätestens danach
};

class FlightStateMachine {
public:
  static constexpr int MAX_EVENTS = 16;

  explicit FlightStateMachine(const FlightParams& p) : p_(p) {}

  FlightState state() const { return s_; }
  bool inFlight() const { return s_ == FlightState::BOOST || s_ == FlightState::COAST || s_ == FlightState::APOGEE
                                 || s_ == FlightState::DESCENT || s_ == FlightState::LANDING_BURN
                                 || (s_ == FlightState::ABORT && t_launch_ms_ != 0); }
  bool controlActive() const { return s_ == FlightState::BOOST || s_ == FlightState::LANDING_BURN; }
  // Fallschirm-Kanal: in APOGEE/DESCENT; im Landemodus nur als Rückfall (landing_fallback_)
  bool pyroAllowed() const {
    return (s_ == FlightState::APOGEE || s_ == FlightState::DESCENT) && (!p_.landing_mode || landing_fallback_);
  }
  // Anzünder des Landemotors: nur in LANDING_BURN
  bool igniterAllowed() const { return s_ == FlightState::LANDING_BURN; }
  bool landingFallback() const { return landing_fallback_; }
  uint32_t ignitionTime() const { return t_ignite_ms_; }
  uint32_t launchTime() const { return t_launch_ms_; }
  uint32_t burnoutTime() const { return t_burnout_ms_; }
  uint32_t apogeeTime() const { return t_apogee_ms_; }
  float    maxBaroAlt() const { return baro_max_m_; }

  // Einen Takt rechnen; true, wenn ein Übergang stattfand (dann steht er in lastEvent()).
  bool update(const FlightInputs& in);

  // Nach einem Neustart im Flug (StateMemory): Zustand und Zeiten wiederherstellen
  void restore(FlightState s, uint32_t t_launch_ms, uint32_t t_burnout_ms, uint32_t t_apogee_ms,
               float baro_max_m, uint32_t now_ms);

  int events() const { return n_events_; }
  const FlightEvent& event(int i) const { return events_[i]; }
  const FlightEvent& lastEvent() const { return events_[n_events_ > 0 ? n_events_ - 1 : 0]; }

private:
  void transition(FlightState to, FlightReason why, uint32_t t_ms);
  bool held(uint32_t& since_ms, bool cond, uint32_t t_ms, uint32_t hold_ms);

  FlightParams p_;
  FlightState s_ = FlightState::SAFE;
  uint32_t t_launch_ms_ = 0, t_burnout_ms_ = 0, t_apogee_ms_ = 0, t_ignite_ms_ = 0;
  bool     landing_fallback_ = false;
  uint32_t launch_since_ = 0, burnout_since_ = 0, apogee_since_ = 0, landed_since_ = 0;
  float    baro_max_m_ = -1e9f;
  FlightEvent events_[MAX_EVENTS];
  int n_events_ = 0;
};
