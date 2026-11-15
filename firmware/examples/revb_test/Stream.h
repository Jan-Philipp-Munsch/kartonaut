#pragma once
// Stream.h – Live-Messwerte für die PC-Oberfläche (tools/bench_gui)
//
// "stream [hz]" gibt bis zum Abbruch mit q fortlaufend Messwerte aus (Standard 50 Hz, 1..200):
//
//   HDR t_ms ax ay az gx gy gz ti mx my mz p tb v1 v2 varm py1 py2 py3 py4 ia vbus rh ts n
//   D <ein Wert je Spalte, Leerzeichen-getrennt, Punkt als Dezimalzeichen, "nan" = kein Wert>
//
//   t_ms          millis() beim Ablegen der Zeile
//   ax ay az      Beschleunigung in m/s², Chip-Achsen, UNKALIBRIERT (Mittel über den FIFO seit der letzten Zeile)
//   gx gy gz      Drehrate in °/s, Chip-Achsen, unkalibriert
//   ti            Temperatur der IMU in °C
//   mx my mz      Magnetfeld in gauss, Chip-Achsen, unkalibriert
//   p tb          Druck in Pa und Temperatur des Barometers 1 in °C
//   v1 v2 varm    1S, 2S und ARM in V (über die Mux, mit adc_gain), reihum je eine Messung pro Zeile
//   py1..py4      Sense-Spannung der Pyrokanäle in V
//   ia vbus       Strom in A (mit ina_offset/ina_gain) und VSERVO in V vom INA239
//   rh ts         relative Feuchte in % und Temperatur des SHT40 in °C (alle 2 s)
//   n             Zahl der gemittelten IMU-Sätze in dieser Zeile (0 = alter Wert wiederholt)
//
// Die IMU- und Magnetometerwerte sind absichtlich roh: die Oberfläche rechnet die Kalibrierung
// selbst (aus "cal show"), kann so "roh" und "kalibriert" nebeneinander zeigen und aus den rohen
// Werten neue Kalibrierwerte bestimmen ("cal set ...").
#include "Proto.h"

Res streamRun(float hz);
