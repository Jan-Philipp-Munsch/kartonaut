#pragma once
// ChuteRelease.h – Auslösung des Fallschirms über den Servo (Kartonaut 1: der Servo an J_SERVO3
// sticht die CO₂-Kapsel an, das Gas drückt die Spitze ab)
//
// Der Servo öffnet, wenn gleichzeitig gilt:
//   1. der Zustandsautomat erlaubt die Bergung (APOGEE oder DESCENT; im Landemodus nur als Rückfall),
//   2. unabhängig davon ist seit dem Start mindestens min_flight_ms vergangen (wie bei Pyro.h),
//   3. nur wenn needs_arm gesetzt ist: der ARM-Schalter ist scharf.
// Einmal geöffnet bleibt er offen, bis reset() ihn am Boden (SAFE) wieder schließt. Nach einem
// Neustart im Flug öffnet er im ersten Takt wieder, weil die Bedingungen aus dem wiederhergestellten
// Zustand folgen; gespeichert werden muss dafür nichts.
//
// Anders als die Pyrokanäle hängt der Servo nicht hinter dem ARM-Schalter (er wird aus VSERVO
// versorgt). Am Boden schützt deshalb nur der Zustandsautomat: ohne PAD_READY und erkannten Start
// gibt es kein APOGEE. Die CO₂-Kapsel erst an der Rampe einsetzen.
// Kein Arduino: den Servo stellt main.cpp nach dem Ergebnis von update().
#include <stdint.h>

struct ChuteReleaseInputs {
  uint32_t t_ms = 0;
  uint32_t t_launch_ms = 0;     // 0 = nicht gestartet
  bool     allowed = false;     // FlightStateMachine::pyroAllowed()
  bool     armed = false;       // ARM_SENSE scharf (nur ausgewertet, wenn needs_arm)
};

class ChuteRelease {
public:
  ChuteRelease(uint32_t min_flight_ms, bool needs_arm) : min_flight_ms_(min_flight_ms), needs_arm_(needs_arm) {}

  // true = Servo offen (ausgelöst)
  bool update(const ChuteReleaseInputs& in) {
    if (released_) return true;
    if (!in.allowed)                                                   { refusal_ = "Zustand"; return false; }
    if (in.t_launch_ms == 0 || in.t_ms - in.t_launch_ms < min_flight_ms_) { refusal_ = "Flugzeit"; return false; }
    if (needs_arm_ && !in.armed)                                       { refusal_ = "nicht scharf"; return false; }
    released_ = true;
    t_release_ms_ = in.t_ms;
    refusal_ = "";
    return true;
  }

  bool released() const { return released_; }
  uint32_t releaseTime() const { return t_release_ms_; }
  const char* lastRefusal() const { return refusal_; }
  void reset() { released_ = false; t_release_ms_ = 0; refusal_ = ""; }

private:
  uint32_t min_flight_ms_;
  bool     needs_arm_;
  bool     released_ = false;
  uint32_t t_release_ms_ = 0;
  const char* refusal_ = "";
};
