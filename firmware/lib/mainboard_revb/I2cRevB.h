#pragma once
// I2cRevB.h – Register-Hilfen für die I²C-Bausteine an Wire (rev B1)
#include <Arduino.h>
#include <Wire.h>

namespace revb_i2c {

// Wire auf 400 kHz starten (einmal; mehrfacher Aufruf ist harmlos)
inline void begin(uint32_t hz = 400000) {
  Wire.begin();
  Wire.setClock(hz);
}

// true, wenn ein Baustein unter addr mit ACK antwortet
inline bool present(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

inline bool writeReg(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

// Registerblock lesen; false bei fehlendem ACK oder zu wenig Bytes
inline bool readRegs(uint8_t addr, uint8_t reg, uint8_t* buf, size_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;   // Repeated Start
  if (Wire.requestFrom(addr, uint8_t(n)) != n) return false;
  for (size_t i = 0; i < n; ++i) buf[i] = Wire.read();
  return true;
}

inline uint8_t readReg(uint8_t addr, uint8_t reg) {
  uint8_t v = 0;
  readRegs(addr, reg, &v, 1);
  return v;
}

}  // namespace revb_i2c
