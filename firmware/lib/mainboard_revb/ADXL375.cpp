#include "ADXL375.h"
#include "I2cRevB.h"

namespace {
constexpr uint8_t DEVID       = 0x00;
constexpr uint8_t BW_RATE     = 0x2C;   // 0x0A = 100 Hz
constexpr uint8_t POWER_CTL   = 0x2D;   // bit3 Measure
constexpr uint8_t DATA_FORMAT = 0x31;   // 0x0B: full res, ±200 g fest
constexpr uint8_t DATAX0      = 0x32;   // 6 Byte, little-endian
}  // namespace

using namespace revb_i2c;

bool    ADXL375::present() { return revb_i2c::present(addr_); }
uint8_t ADXL375::devId()   { return readReg(addr_, DEVID); }

bool ADXL375::begin() {
  if (!present() || devId() != DEVID_VALUE) return false;
  writeReg(addr_, DATA_FORMAT, 0x0B);
  writeReg(addr_, BW_RATE, 0x0A);
  writeReg(addr_, POWER_CTL, 0x08);
  delay(5);
  return readReg(addr_, POWER_CTL) == 0x08;
}

bool ADXL375::read(float acc_g[3]) {
  uint8_t b[6];
  if (!readRegs(addr_, DATAX0, b, sizeof b)) return false;
  for (int i = 0; i < 3; ++i) acc_g[i] = int16_t(b[2 * i] | (b[2 * i + 1] << 8)) * G_PER_LSB;
  return true;
}
