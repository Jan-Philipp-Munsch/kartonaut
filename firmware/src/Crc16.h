#pragma once
// Crc16.h – CRC-16/CCITT-FALSE (Polynom 0x1021, Start 0xFFFF, kein Reflect, kein XOR-Out).
// Prüfwert für "123456789": 0x29B1. Gemeinsam für Telemetrie und Zustandsspeicher;
// die Bodenstation übernimmt dieselbe Funktion.
#include <stdint.h>
#include <stddef.h>

inline uint16_t crc16_ccitt(const uint8_t* data, size_t n, uint16_t crc = 0xFFFF) {
  for (size_t i = 0; i < n; ++i) {
    crc ^= (uint16_t)data[i] << 8;
    for (int b = 0; b < 8; ++b) crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
  }
  return crc;
}
