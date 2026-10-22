#pragma once
// Gps.h – kleiner NMEA-Leser (GGA) für das u-blox-Modul an Serial1 (nur rev B).
//
// Mehr als Position, Höhe, Satelliten und Fix braucht die Telemetrie nicht;
// das Modul sendet ab Werk 1 Hz. TinyGPSPlus würde dasselbe tun, aber dieser
// Leser hat keine Abhängigkeit und läuft nicht blockierend in der Schleife.
#include <Arduino.h>
#include "KartonautProtocol.h"

class Gps {
public:
  void begin(long baud = 9600);
  void poll();                       // jeden Loop; verarbeitet, was im Puffer liegt
  bool hasFix() const { return fix_ > 0; }
  const KnGps& data() const { return data_; }
  uint32_t sentences() const { return sentences_; }
  uint32_t lastFix_ms() const { return t_fix_ms_; }

private:
  void parseLine();
  static float parseCoord(const char* s, const char* hemi);

  char     line_[100];
  uint8_t  pos_ = 0;
  KnGps    data_{};
  uint8_t  fix_ = 0;
  uint32_t sentences_ = 0, t_fix_ms_ = 0;
};
