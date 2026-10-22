#pragma once
// Indicators.h – zwei WS2812B und der Summer.
//
// Blockierende Muster für setup() und Tests (Indicate_*), dazu ein nicht
// blockierendes Muster je Flugzustand für die Schleife (Indicators_update):
//
//   SAFE        blau, atmend; Warnton alle 2 s, wenn ein Akku schwach ist
//   PAD_READY   grün; kurzer Piep jede Sekunde (Start-Freigabe hörbar)
//   BOOST/COAST weiß
//   APOGEE/DESCENT magenta
//   LANDED      gelb blinkend, Piep jede Sekunde (Ortung)
//   ABORT       rot schnell blinkend mit Summer
#include "Config.h"
#include "Board.h"
#include "FlightState.h"

void Indicators_setup();
void Indicate_success();   // blockiert ca. 0,4 s
void Indicate_waiting();   // orange, Summer an (bis zum nächsten Muster)
void Indicate_warn();      // blockiert 20 s (Pyro-Test)
void Indicators_off();

struct IndicatorInputs {
  FlightPhase phase = FlightPhase::SAFE;
  bool armed = false;
  bool continuity = false;
  bool battery_low = false;
  bool calibrated = false;
};
void Indicators_update(const IndicatorInputs& in, uint32_t now_ms);
