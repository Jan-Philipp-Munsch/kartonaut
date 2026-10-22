#pragma once
#include <Arduino.h>

// =====================================================================
//  Launch – Zünd-Zustandsautomat mit Startsperre (S3) und den Rechten
//  des Handys (S4).
//
//  SAFE ──Schlüssel+ARM──> ARMED ──Countdown──> COUNTDOWN ──T-0──> FIRING ──1 s──> FIRED
//    ^                       │                      │                                  │
//    └──────ARM aus──────────┴── ABORTED <──Abbruch─┘                                  │
//    └──────ARM aus─────────────────────────────────────────────────────────────────────┘
//  LOCKOUT: ARM war beim Einschalten an. Erst ARM aus, dann geht es in SAFE.
//  ABORTED und FIRED verlassen den Zustand nur über ARM aus (bewusstes Entschärfen).
// =====================================================================

namespace launch {

enum State : uint8_t { LOCKOUT, SAFE, ARMED, COUNTDOWN, FIRING, FIRED, ABORTED };

enum Source : uint8_t { SRC_BUTTON, SRC_PHONE };

// Die vier Bedingungen der Startsperre; 4 ist "Countdown läuft ohne Abbruch".
struct Interlock {
  bool keyArm = false;      // 1: Schlüssel, ARM, Relais geschlossen
  bool continuity = false;  // 2: Durchgang
  bool rocketReady = false; // 3: Telemetrie < 1 s, PAD_READY, Rakete scharf
  bool tlmFresh = false, padReady = false, rocketArmed = false;  // Einzelteile von 3
  bool battery = false;     // Zusatz: 3S nicht leer
  bool noFault = false;     // Zusatz: kein Fehler im Zündkreis
  bool all() const { return keyArm && continuity && rocketReady && battery && noFault; }
};

using LogFn = void (*)(const char* msg);

void begin(LogFn log);
void update();

// Countdown anfordern. Rückgabe nullptr = gestartet, sonst Ablehnungsgrund.
const char* requestCountdown(Source src, uint32_t phoneId = 0);
void abort(const char* reason);   // jederzeit, aus jeder Quelle

void phoneHeartbeat(uint32_t phoneId);
void phoneDisconnected(uint32_t phoneId);

State state();
const char* stateName(State s);
const Interlock& interlock();
int32_t countdownRemainingMs();   // -1 außerhalb des Countdowns
uint32_t hangfireRemainingMs();   // nach FIRED ohne Abheben: Wartezeit bis zum Annähern
const char* lastReason();         // letzter Abbruch- oder Sperrgrund

} // namespace launch
