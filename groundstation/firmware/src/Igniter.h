#pragma once
#include <Arduino.h>

// =====================================================================
//  Igniter – Zündkreis der Bodenstation (S2): Schlüssel und ARM lesen,
//  Leitungsspannungen messen, Durchgang und Fehler erkennen, MOSFET
//  schalten. Das Relais schalten Schlüssel und ARM in Hardware; die
//  Firmware sieht es nur über die Spannung an Leitung plus.
// =====================================================================

namespace igniter {

struct Status {
  bool  key = false;          // Schlüssel steckt (gedreht)
  bool  arm = false;          // ARM-Schalter ein (setzt den Schlüssel voraus, Reihenschaltung)
  bool  relayClosed = false;  // Leitung plus führt Akkuspannung
  bool  continuity = false;   // Anzünder hat Durchgang
  bool  firing = false;       // MOSFET leitet
  float linePosV = 0, lineNegV = 0, vbatV = 0;
  const char* fault = nullptr;  // nullptr = kein Fehler, sonst Klartext
};

void begin();
void update();                // ADC und Eingänge lesen, Fehler bewerten
void setFire(bool on);        // MOSFET; die Ablaufsteuerung (Launch) entscheidet
const Status& status();

} // namespace igniter
