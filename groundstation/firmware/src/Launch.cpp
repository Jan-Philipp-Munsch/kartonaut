#include "Launch.h"
#include "Config.h"
#include "Igniter.h"
#include "Radio.h"
#include "Protocol.h"

namespace launch {

static State st = SAFE;
static Interlock il;
static LogFn logFn = nullptr;
static const char* reason = "";

static uint32_t stateSinceMs = 0;
static Source cdSource = SRC_BUTTON;
static uint32_t cdPhoneId = 0;
static uint32_t lastHeartbeatMs = 0;

static bool btnPrev = false;
static uint32_t btnDownSinceMs = 0;
static bool btnConsumed = false;

static char logBuf[120];

static void log(const char* fmt, const char* arg = "") {
  snprintf(logBuf, sizeof(logBuf), fmt, arg);
  Serial.printf("[LAUNCH] %s\n", logBuf);
  if (logFn) logFn(logBuf);
}

static void enter(State s) {
  st = s;
  stateSinceMs = millis();
  log("Zustand %s", stateName(s));
}

const char* stateName(State s) {
  switch (s) {
    case LOCKOUT:   return "LOCKOUT";
    case SAFE:      return "SAFE";
    case ARMED:     return "ARMED";
    case COUNTDOWN: return "COUNTDOWN";
    case FIRING:    return "FIRING";
    case FIRED:     return "FIRED";
    case ABORTED:   return "ABORTED";
  }
  return "?";
}

static void evalInterlock() {
  const auto& ig = igniter::status();
  const auto& rs = radio::status();
  il.keyArm      = ig.key && ig.arm && ig.relayClosed;
  il.continuity  = ig.continuity;
  il.tlmFresh    = radio::telemetryAgeMs() < TLM_MAX_AGE_MS;
  il.padReady    = il.tlmFresh && rs.tlm.state == proto::FS_PAD_READY;
  il.rocketArmed = il.tlmFresh && (rs.tlm.flags & proto::F_ARMED);
  il.rocketReady = il.tlmFresh && il.padReady && il.rocketArmed;
  il.battery     = ig.vbatV >= VBAT_MIN_FIRE_V;
  il.noFault     = ig.fault == nullptr;
}

// Erster nicht erfüllter Punkt der Startsperre als Klartext
static const char* blocker() {
  const auto& ig = igniter::status();
  if (!il.noFault)     return ig.fault;
  if (!ig.key)         return "Schlüssel steckt nicht";
  if (!ig.arm)         return "ARM aus";
  if (!il.keyArm)      return "Relais nicht geschlossen";
  if (!il.continuity)  return "kein Durchgang am Anzünder";
  if (!il.tlmFresh)    return "Telemetrie älter als 1 s";
  if (!il.padReady)    return "Rakete nicht PAD_READY";
  if (!il.rocketArmed) return "Schlüsselschalter der Rakete nicht scharf";
  if (!il.battery)     return "Zündakku leer";
  return nullptr;
}

void begin(LogFn fn) {
  logFn = fn;
  pinMode(PIN_START_BTN, INPUT_PULLUP);
  igniter::setFire(false);
  evalInterlock();
  // Startet die Station mit eingeschaltetem ARM, wird nichts freigegeben,
  // bis ARM einmal aus war (kein Scharfschalten durch Einschalten).
  if (igniter::status().arm) {
    reason = "ARM war beim Einschalten an";
    st = LOCKOUT;
  } else {
    st = SAFE;
  }
  stateSinceMs = millis();
}

const char* requestCountdown(Source src, uint32_t phoneId) {
  if (st != ARMED) {
    reason = (st == SAFE || st == LOCKOUT) ? "nicht scharf (Schlüssel und ARM an der Station)"
                                           : "Countdown nur aus ARMED";
    return reason;
  }
  evalInterlock();
  if (const char* b = blocker()) { reason = b; return b; }
  cdSource = src;
  cdPhoneId = phoneId;
  lastHeartbeatMs = millis();
  reason = "";
  enter(COUNTDOWN);
  log("Countdown gestartet (%s)", src == SRC_PHONE ? "Handy" : "Start-Taster");
  return nullptr;
}

void abort(const char* why) {
  // Die Rakete bekommt das ABORT in jedem Fall; was sie im Flug daraus macht,
  // entscheidet die Flug-Firmware.
  radio::send(proto::CMD_ABORT);
  if (st == COUNTDOWN || st == FIRING) {
    igniter::setFire(false);
    reason = why;
    enter(ABORTED);
    log("ABBRUCH: %s", why);
  } else {
    log("Abbruch-Kommando an die Rakete (%s)", why);
  }
}

void phoneHeartbeat(uint32_t id) {
  if (st == COUNTDOWN && cdSource == SRC_PHONE && id == cdPhoneId) lastHeartbeatMs = millis();
}

void phoneDisconnected(uint32_t id) {
  if (st == COUNTDOWN && cdSource == SRC_PHONE && id == cdPhoneId)
    abort("Verbindung zum Handy verloren");
}

static void handleButton(uint32_t now) {
  bool down = !digitalRead(PIN_START_BTN);
  if (down && !btnPrev) { btnDownSinceMs = now; btnConsumed = false; }
  if (down && !btnConsumed && now - btnDownSinceMs >= START_BTN_HOLD_MS) {
    btnConsumed = true;
    if (const char* r = requestCountdown(SRC_BUTTON)) log("Start-Taster abgelehnt: %s", r);
  }
  if (!down && btnPrev && START_BTN_DEADMAN && st == COUNTDOWN && cdSource == SRC_BUTTON)
    abort("Start-Taster losgelassen");
  btnPrev = down;
}

void update() {
  uint32_t now = millis();
  evalInterlock();
  handleButton(now);
  const auto& ig = igniter::status();

  // ARM aus beendet jeden Zustand außer SAFE; während Countdown/Zündung ist es ein Abbruch.
  if (!ig.arm) {
    if (st == COUNTDOWN || st == FIRING) abort("ARM aus oder Schlüssel gezogen");
    if (st == LOCKOUT) reason = "";
    if (st != SAFE) enter(SAFE);
    return;
  }

  switch (st) {
    case LOCKOUT:
    case SAFE:
      // LOCKOUT bleibt, bis ARM aus war (oben). SAFE -> ARMED, wenn ARM an ist.
      if (st == SAFE) enter(ARMED);
      break;

    case ARMED:
      break;

    case COUNTDOWN: {
      if (const char* b = blocker()) { abort(b); break; }
      if (cdSource == SRC_PHONE && now - lastHeartbeatMs > PHONE_HEARTBEAT_TIMEOUT_MS) {
        abort("Handy antwortet nicht (Herzschlag)");
        break;
      }
      if (now - stateSinceMs >= COUNTDOWN_MS) {
        // Bedingung 4 erfüllt, 1-3 eben noch einmal geprüft
        igniter::setFire(true);
        enter(FIRING);
      }
      break;
    }

    case FIRING:
      if (now - stateSinceMs >= FIRE_PULSE_MS) {
        igniter::setFire(false);
        enter(FIRED);
      }
      break;

    case FIRED:
    case ABORTED:
      break;
  }
}

State state() { return st; }
const Interlock& interlock() { return il; }
const char* lastReason() { return reason; }

int32_t countdownRemainingMs() {
  if (st != COUNTDOWN) return -1;
  return int32_t(COUNTDOWN_MS) - int32_t(millis() - stateSinceMs);
}

uint32_t hangfireRemainingMs() {
  if (st != FIRED) return 0;
  // Hebt die Rakete ab, meldet sie BOOST oder später; dann gibt es keinen Hänger.
  const auto& t = radio::status().tlm;
  if (radio::status().lastTelemetryMs > stateSinceMs && t.state >= proto::FS_BOOST && t.state <= proto::FS_LANDED)
    return 0;
  uint32_t el = millis() - stateSinceMs;
  return el >= HANGFIRE_WAIT_MS ? 0 : HANGFIRE_WAIT_MS - el;
}

} // namespace launch
