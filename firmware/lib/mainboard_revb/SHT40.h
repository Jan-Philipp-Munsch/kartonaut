#pragma once
// SHT40.h – Feuchte und Temperatur SHT40-AD1B an Wire (rev B1, U18, 0x44)
//
// Sensirion-Datenblatt SHT4x: Befehl 0xFD = Messung hohe Genauigkeit
// (8,3 ms), Antwort 2 Byte T + CRC, 2 Byte RH + CRC (CRC-8, Polynom 0x31,
// Start 0xFF). 0x89 = Seriennummer, 0x94 = Soft-Reset.
#include <Arduino.h>

struct ShtSample {
  float temp_c;
  float rh_pct;        // 0..100, geklemmt
  bool  crc_ok;
};

class SHT40 {
public:
  explicit SHT40(uint8_t addr) : addr_(addr) {}

  bool     begin();                // Reset, Seriennummer lesen
  uint32_t serial() const { return serial_; }
  bool     read(ShtSample& s);     // blockiert ca. 10 ms
  static uint8_t crc8(const uint8_t* d, size_t n);

private:
  bool command(uint8_t cmd, uint8_t* buf, size_t n, uint32_t wait_ms);
  uint8_t  addr_;
  uint32_t serial_ = 0;
};
