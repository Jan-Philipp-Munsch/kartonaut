#pragma once
// Testrig.h – Gas-Ausgang für den TVC-Prüfstand (PROJECT.md Paket 15, Plan §2 C2)
//
// Am Prüfstand sitzt statt des Raketenmotors ein Brushless-Motor mit Propeller
// (BR2814, ESC 60 A) im Kardan. Der ESC bekommt einen Servopuls auf
// PIN_THROTTLE. Mit TESTRIG_MODE in Config.h fährt die Firmware nach dem
// Kommando „Start“ (USB 'l' oder KN_CMD_TESTRIG_THRUST) die Schubkurve des TSP E12
// nach, skaliert auf TESTRIG_THRUST_MAX_N; danach fällt der Schub auf 0 und der
// Zustandsautomat erkennt den Brennschluss über die Zeit (die Beschleunigung
// bleibt im Gestell bei 1 g). Alternativ setzt KN_CMD_TESTRIG_THRUST einen
// konstanten Schub.
//
// Schub -> Puls ist hier linear; das stimmt für einen Propeller nur grob
// (Schub ~ Drehzahl²). Die Kurve wird mit einer Waage am Prüfstand kalibriert
// (docs/Testplan_Firmware_2026-10-22.md §5), bis dahin ist der Wert ein Platzhalter.
#include "Config.h"
#include "Board.h"

class Testrig {
public:
  void begin();                        // ESC armen: Minimalpuls für 2 s
  void startCurve(uint32_t now_ms);    // E12-Kurve ab jetzt
  void setThrust(float n);             // konstanter Schub, hebt die Kurve auf
  void stop();                         // Puls auf Minimum
  void update(uint32_t now_ms);        // jeden Loop

  float thrust_N() const { return thrust_n_; }
  bool  running() const { return curve_running_; }

  // Schub des TSP E12 zur Brennzeit t (Lookup in der eingebauten Kurve)
  static float e12Thrust(float t_s);

private:
  void writeThrust(float n);
  float    thrust_n_ = 0;
  bool     curve_running_ = false;
  uint32_t t_curve_start_ = 0;
  bool     attached_ = false;
};
