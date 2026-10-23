#include "SHT40.h"
#include "I2cRevB.h"

namespace {
constexpr uint8_t CMD_MEASURE_HIGH = 0xFD;
constexpr uint8_t CMD_SERIAL       = 0x89;
constexpr uint8_t CMD_RESET        = 0x94;
}  // namespace

uint8_t SHT40::crc8(const uint8_t* d, size_t n) {
  uint8_t crc = 0xFF;
  for (size_t i = 0; i < n; ++i) {
    crc ^= d[i];
    for (int b = 0; b < 8; ++b) crc = (crc & 0x80) ? uint8_t((crc << 1) ^ 0x31) : uint8_t(crc << 1);
  }
  return crc;
}

bool SHT40::command(uint8_t cmd, uint8_t* buf, size_t n, uint32_t wait_ms) {
  Wire.beginTransmission(addr_);
  Wire.write(cmd);
  if (Wire.endTransmission() != 0) return false;
  delay(wait_ms);
  if (n == 0) return true;
  if (Wire.requestFrom(addr_, uint8_t(n)) != n) return false;
  for (size_t i = 0; i < n; ++i) buf[i] = Wire.read();
  return true;
}

bool SHT40::begin() {
  if (!revb_i2c::present(addr_)) return false;
  command(CMD_RESET, nullptr, 0, 2);
  uint8_t b[6];
  if (!command(CMD_SERIAL, b, sizeof b, 2)) return false;
  if (crc8(b, 2) != b[2] || crc8(b + 3, 2) != b[5]) return false;
  serial_ = (uint32_t(b[0]) << 24) | (uint32_t(b[1]) << 16) | (uint32_t(b[3]) << 8) | b[4];
  return true;
}

bool SHT40::read(ShtSample& s) {
  uint8_t b[6];
  if (!command(CMD_MEASURE_HIGH, b, sizeof b, 10)) return false;
  s.crc_ok = crc8(b, 2) == b[2] && crc8(b + 3, 2) == b[5];
  const uint16_t t = uint16_t((b[0] << 8) | b[1]), h = uint16_t((b[3] << 8) | b[4]);
  s.temp_c = -45.0f + 175.0f * t / 65535.0f;
  s.rh_pct = constrain(-6.0f + 125.0f * h / 65535.0f, 0.0f, 100.0f);
  return s.crc_ok;
}
