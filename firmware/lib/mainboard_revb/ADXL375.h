#pragma once
// ADXL375.h – Hochbeschleunigung ±200 g an Wire (rev B1, U17, 0x53), DNP
//
// Auf rev B1 ist nur der Footprint vorgesehen. Der Treiber erkennt den
// Baustein (DEVID 0xE5) und liest die Rohwerte (49 mg/LSB, Datenblatt
// Rev. E), mehr nicht: im Flug wird er erst mit stärkeren Motoren gebraucht.
#include <Arduino.h>

class ADXL375 {
public:
  static constexpr uint8_t DEVID_VALUE = 0xE5;
  static constexpr float   G_PER_LSB   = 0.049f;

  explicit ADXL375(uint8_t addr) : addr_(addr) {}

  bool    present();              // ACK auf der Adresse
  uint8_t devId();
  bool    begin();                // Messbetrieb, 100 Hz
  bool    read(float acc_g[3]);

private:
  uint8_t addr_;
};
