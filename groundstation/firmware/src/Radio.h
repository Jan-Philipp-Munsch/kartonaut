#pragma once
#include <Arduino.h>
#include "Protocol.h"

// =====================================================================
//  Radio – E22-400T22 an UART1: Konfiguration, Empfang, Kommandos mit
//  Quittung und Wiederholung.
// =====================================================================

namespace radio {

// Ergebnis eines Kommandos: Quittung erhalten (result) oder nach allen
// Wiederholungen ohne Antwort (timedOut).
using CommandCallback = void (*)(uint8_t cmd, bool timedOut, uint8_t result);

struct Status {
  bool     configured = false;   // Register gelesen und stimmen
  bool     haveTelemetry = false;
  uint32_t lastTelemetryMs = 0;  // millis() beim letzten gültigen Telemetrierahmen
  uint32_t lastGpsMs = 0;
  uint32_t frames = 0, crcErrors = 0, txFrames = 0;
  proto::Telemetry tlm;
  proto::Gps gps;
};

bool begin(CommandCallback cb);
void update();

// Reiht ein Kommando ein. ABORT verdrängt alle anderen und wird öfter wiederholt.
bool send(proto::Command cmd);

uint32_t telemetryAgeMs();   // UINT32_MAX, wenn noch nie empfangen
const Status& status();

} // namespace radio
