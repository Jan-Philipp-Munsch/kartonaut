// I2C-Scanner: listet alle Adressen auf Wire (Pins 18/19), alle 5 s.
// Erwartet am Flugcomputer: 0x40 (INA219), 0x68 oder 0x69 (ICM-20948), 0x76 (BMP280).
//
//   pio run -e i2c_scanner -t upload
#include <Arduino.h>
#include <Wire.h>
#include "Config.h"
#include "Board.h"

void setup(){
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(I2C_MAIN_SPEED_HZ);
}

void loop(){
  Serial.println("I2C-Scan ...");
  int found = 0;
  for (uint8_t addr = 1; addr < 127; ++addr){
    Wire.beginTransmission(addr);
    const uint8_t err = Wire.endTransmission();
    if (err == 0){
      Serial.printf("  Gerät bei 0x%02X\n", addr);
      ++found;
    } else if (err == 4){
      Serial.printf("  Fehler bei 0x%02X\n", addr);
    }
  }
  if (found == 0) Serial.println("  keine Geräte gefunden");
  delay(5000);
}
