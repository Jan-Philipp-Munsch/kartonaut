// =====================================================================
//  Bodenstation Kartonaut – Startgerät und Telemetrie (ESP32-S3)
//
//  Ablauf je Schleifendurchlauf:
//    igniter::update()  Schlüssel, ARM, Leitungsspannungen, Fehler
//    radio::update()    E22 lesen, Kommandos senden/wiederholen
//    launch::update()   Startsperre und Zünd-Zustandsautomat
//    web::update()      Handy-Kommandos abarbeiten, Zustand 10 Hz senden
//    indicators()       LEDs und Summer
//
//  Schnittstellen: docs/Schnittstellen_Bodensystem_2026-10-22.md (S2-S4)
//  Schaltung und Pins: groundstation/Schaltung.md
// =====================================================================
#include <Arduino.h>
#include "Config.h"
#include "Igniter.h"
#include "Radio.h"
#include "Launch.h"
#include "Web.h"

static void onCommandResult(uint8_t cmd, bool timedOut, uint8_t result) {
  char buf[80];
  if (timedOut)
    snprintf(buf, sizeof(buf), "%s: keine Quittung von der Rakete", proto::commandName(cmd));
  else
    snprintf(buf, sizeof(buf), "%s: Quittung %s", proto::commandName(cmd),
             result == proto::ACK_OK ? "OK" : result == proto::ACK_REFUSED ? "abgelehnt"
             : result == proto::ACK_BUSY ? "beschäftigt" : "unbekannt");
  Serial.printf("[RADIO] %s\n", buf);
  web::event(buf);
}

static void onLaunchLog(const char* msg) { web::event(msg); }

static void beep(bool on) { digitalWrite(PIN_BUZZER, on ? HIGH : LOW); }

static void indicators() {
  uint32_t now = millis();
  const auto& ig = igniter::status();
  bool fresh = radio::telemetryAgeMs() < TLM_MAX_AGE_MS;
  bool blink = (now / 250) % 2;

  digitalWrite(PIN_LED_CONT, ig.continuity);
  digitalWrite(PIN_LED_LINK, fresh);

  switch (launch::state()) {
    case launch::LOCKOUT:
      digitalWrite(PIN_LED_ARMED, blink);
      beep((now % 1000) < 50);
      break;
    case launch::SAFE:
      digitalWrite(PIN_LED_ARMED, LOW);
      beep(ig.fault && (now % 2000) < 100);
      break;
    case launch::ARMED:
      digitalWrite(PIN_LED_ARMED, HIGH);
      beep((now % 2000) < 30);   // Erinnerung: scharf
      break;
    case launch::COUNTDOWN: {
      int32_t rem = launch::countdownRemainingMs();
      digitalWrite(PIN_LED_ARMED, blink);
      uint32_t period = rem > 3000 ? 1000 : 250;
      beep((uint32_t(rem) % period) > period - 80);
      break;
    }
    case launch::FIRING:
      digitalWrite(PIN_LED_ARMED, HIGH);
      beep(true);
      break;
    case launch::FIRED:
    case launch::ABORTED:
      digitalWrite(PIN_LED_ARMED, blink);
      beep(false);
      break;
  }
}

void setup() {
  // Zündausgang vor allem anderen auf LOW
  digitalWrite(PIN_FIRE_GATE, LOW);
  pinMode(PIN_FIRE_GATE, OUTPUT);

  Serial.begin(115200);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_CONT, OUTPUT);
  pinMode(PIN_LED_ARMED, OUTPUT);
  pinMode(PIN_LED_LINK, OUTPUT);

  igniter::begin();
  if (!radio::begin(onCommandResult)) Serial.println("[RADIO] E22 antwortet nicht oder Register falsch");
  web::begin();
  launch::begin(onLaunchLog);
  Serial.println("[GS] bereit");
}

void loop() {
  igniter::update();
  radio::update();
  launch::update();
  web::update();
  indicators();
  delay(1);
}
