// Pyro-/MOSFET-Test: schaltet den Low-Side-MOSFET an PIN_PYRO1 (Pin 23)
// einmalig für eine Sekunde durch, mit Warnblinken davor.
//
// Nur mit Glühlämpchen oder 2-Ohm-Widerstand als Last testen, nie mit einer
// echten Ladung auf dem Tisch (siehe hardware/mainboard/README.md §8).
//
//   pio run -e pyro_mosfet_test -t upload
#include <Arduino.h>
#include "Config.h"       // src/ liegt über build_flags = -Isrc im Include-Pfad
#include "Board.h"
#include "Indicators.h"

void setup(){
  Serial.begin(115200);
  pinMode(PIN_PYRO1, OUTPUT);
  digitalWrite(PIN_PYRO1, LOW);   // definierter Start
  Indicators_setup();
  Indicate_success();
}

void loop(){
  Indicate_warn();                // 20 s rotes Blinken mit Summer
  delay(2000);
  digitalWrite(PIN_PYRO1, HIGH);
  delay(1000);
  digitalWrite(PIN_PYRO1, LOW);
  Indicate_success();
  Serial.println("Puls gesetzt. Reset für einen weiteren Durchlauf.");
  while (true) delay(1000);
}
