#pragma once
// Pyro.h – Zündlogik für die Bergung (Plan 22.10.2026, B3; Review A4)
//
// Ein Kanal zündet nur, wenn gleichzeitig gilt:
//   1. der Zustandsautomat erlaubt es (APOGEE oder DESCENT, aus vz und Barometer),
//   2. unabhängig davon ist seit dem Start mindestens PYRO_MIN_FLIGHT_MS vergangen,
//   3. der Schlüsselschalter ist scharf (ARM_SENSE über PYRO_ARM_MIN_V),
//   4. der Anzünder hat Durchgang.
// Der Puls dauert PYRO_PULSE_MS und endet früher, sobald der Durchgang verloren geht
// (Anzünder durchgebrannt). Je Kanal höchstens PYRO_MAX_FIRES Versuche; Kanal 2 ist die
// Reserve und zündet PYRO_BACKUP_DELAY_MS nach Kanal 1, falls bestückt. Bleibt der Durchgang nach
// einem Puls bestehen (Anzünder nicht durchgebrannt), folgt nach PYRO_RETRY_DELAY_MS ein zweiter.
// Auf dem Breakout-Aufbau gibt es weder ARM- noch Durchgangsmessung: das Backend meldet
// armed = false, damit ist Zünden unmöglich (Jan, 22.10.2026).
// Kein Arduino: die Pins schaltet main.cpp nach dem Ergebnis von update().
//
// Startpuls (Motorstart an Bord, Plan Bordzündung 27.10.2026 §2.1/§4): updateLaunch() schaltet den
// Startkanal (LAUNCH_CH) genau einmal, nur solange der Automat in IGNITION ist. Der Puls endet beim
// ersten von: Schub erkannt, Durchgang weg, launch_pulse_max_ms (300 ms, schont F1 und VSERVO),
// Zustand verlassen, Arming-Spannung weg. Den Durchgang misst main.cpp während des Pulses in einer
// kurzen Messlücke (FET kurz aus, Drain lesen), denn bei leitendem Low-Side-FET liegt der Drain auf
// 0 V und die Messung sähe immer "kein Durchgang" (Jan, 27.10.2026).
#include <stdint.h>

struct PyroInputs {
  uint32_t t_ms = 0;
  bool     allowed[2] = {false, false};   // Freigabe je Kanal (Fallschirm: pyroAllowed(); Anzünder: igniterAllowed())
  uint32_t t_launch_ms = 0;       // 0 = nicht gestartet
  bool     armed = false;
  bool     continuity[2] = {false, false};
  bool     fitted[2] = {true, false};
};

struct PyroParams {
  uint32_t pulse_ms[2];           // Pulslänge je Kanal (Ausstoßladung kurz, Anzünder länger)
  uint32_t min_flight_ms, backup_delay_ms, retry_delay_ms;
  uint8_t  max_fires;
  bool     backup_pair;           // true: Kanal 2 ist die Reserve von Kanal 1 (Fallschirm-Modus)
  uint32_t launch_pulse_max_ms = 300;   // Startpuls höchstens so lang
};

// Startpuls: Eingänge je Takt
struct LaunchPulseInputs {
  uint32_t t_ms = 0;
  bool     allowed = false;       // FlightStateMachine::launchAllowed() (nur IGNITION)
  bool     armed = false;
  bool     continuity = false;    // vor dem Puls: normale Messung; während des Pulses: Messlücke
  bool     continuity_valid = false;   // false: in diesem Takt keine Messung (Durchgang nicht auswerten)
  bool     thrust = false;        // |a| über der Startschwelle (erste Probe, ohne Haltezeit)
};

class PyroLogic {
public:
  explicit PyroLogic(const PyroParams& p) : p_(p) {}

  // Liefert in fire[] den Sollzustand der beiden Zündausgänge für diesen Takt.
  void update(const PyroInputs& in, bool fire[2]);

  bool firing(int ch) const { return firing_[ch]; }
  uint8_t fires(int ch) const { return fires_[ch]; }
  uint32_t firstFireTime() const { return t_first_fire_; }
  // true, sobald Kanal 1 seinen Puls beendet hat oder nicht zünden kann (ohne ARM/Durchgang)
  bool done() const { return done_; }
  bool done(int ch) const { return done_ch_[ch]; }
  const char* lastRefusal() const { return refusal_; }
  // Startpuls (Kanal LAUNCH_CH): Sollzustand des Ausgangs für diesen Takt
  bool updateLaunch(const LaunchPulseInputs& in);
  bool launchFiring() const { return launch_firing_; }
  bool launchUsed() const { return launch_used_; }       // Puls begonnen oder verweigert, kein zweiter
  uint32_t launchOnTime() const { return t_launch_on_; }  // 0 = nie an
  uint32_t launchOffTime() const { return t_launch_off_; }
  uint8_t  launchEndReason() const { return launch_end_; }   // tlm::IgnEnd
  // Neuer Startablauf (Eintritt in ARMED, z. B. nach MISFIRE -> SAFE mit neuem Anzünder)
  void resetLaunch() { if (!launch_firing_) { launch_used_ = false; t_launch_on_ = t_launch_off_ = 0; launch_end_ = 0; } }

  // Nach einem Neustart im Flug (StateMemory): Zählerstände übernehmen
  void restore(uint8_t fires0, uint8_t fires1) { fires_[0] = fires0; fires_[1] = fires1; done_ = fires0 > 0; done_ch_[0] = fires0 > 0; done_ch_[1] = fires1 > 0; }

private:
  bool conditions(const PyroInputs& in, int ch);

  PyroParams p_;
  bool     firing_[2] = {false, false};
  uint32_t t_start_[2] = {0, 0};
  uint32_t t_end_[2] = {0, 0};
  uint8_t  fires_[2] = {0, 0};
  uint32_t t_first_fire_ = 0;
  uint32_t t_allowed_since_ = 0;
  bool     done_ = false;
  bool     done_ch_[2] = {false, false};
  const char* refusal_ = "";
  bool     launch_firing_ = false, launch_used_ = false;
  uint32_t t_launch_on_ = 0, t_launch_off_ = 0;
  uint8_t  launch_end_ = 0;
};
