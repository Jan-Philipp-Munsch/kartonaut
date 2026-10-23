#include "LIS3MDL.h"
#include "I2cRevB.h"
#include <math.h>

namespace {
constexpr uint8_t WHO_AM_I   = 0x0F;
constexpr uint8_t CTRL_REG1  = 0x20;   // TEMP_EN, OM, DO, FAST_ODR, ST
constexpr uint8_t CTRL_REG2  = 0x21;   // FS, REBOOT, SOFT_RST
constexpr uint8_t CTRL_REG3  = 0x22;   // MD
constexpr uint8_t CTRL_REG4  = 0x23;   // OMZ, BLE
constexpr uint8_t CTRL_REG5  = 0x24;   // BDU
constexpr uint8_t STATUS_REG = 0x27;   // bit3 ZYXDA
constexpr uint8_t OUT_X_L    = 0x28;   // 6 Byte, little-endian
constexpr uint8_t TEMP_OUT_L = 0x2E;   // 2 Byte, 8 LSB/°C, 0 = 25 °C
constexpr uint8_t AUTO_INC   = 0x80;   // Adressbit 7: Auto-Inkrement
}  // namespace

using namespace revb_i2c;

uint8_t LIS3MDL::whoAmI() { return readReg(addr_, WHO_AM_I); }

void LIS3MDL::configure() {
  writeReg(addr_, CTRL_REG1, 0xFC);   // TEMP_EN, OM = UHP, 80 Hz
  writeReg(addr_, CTRL_REG2, 0x00);   // ±4 gauss
  writeReg(addr_, CTRL_REG4, 0x0C);   // OMZ = UHP
  writeReg(addr_, CTRL_REG5, 0x40);   // BDU
  writeReg(addr_, CTRL_REG3, 0x00);   // Dauermessung
}

bool LIS3MDL::begin() {
  if (!present(addr_)) return false;
  writeReg(addr_, CTRL_REG2, 0x04);   // SOFT_RST
  delay(10);
  if (whoAmI() != WHO_AM_I_VALUE) return false;
  configure();
  delay(20);
  return readReg(addr_, CTRL_REG1) == 0xFC;
}

bool LIS3MDL::dataReady() { return readReg(addr_, STATUS_REG) & 0x08; }

bool LIS3MDL::read(MagSample& s) {
  uint8_t b[8];
  if (!readRegs(addr_, OUT_X_L | AUTO_INC, b, sizeof b)) return false;
  for (int i = 0; i < 3; ++i) {
    s.raw[i] = int16_t(b[2 * i] | (b[2 * i + 1] << 8));
    s.mag_gauss[i] = s.raw[i] / LSB_PER_GAUSS_4G;
  }
  s.temp_c = int16_t(b[6] | (b[7] << 8)) / 8.0f + 25.0f;
  return true;
}

void LIS3MDL::average(float out[3], int n, float lsb_per_gauss) {
  int32_t sum[3] = {0, 0, 0};
  for (int k = 0; k < n; ++k) {
    const uint32_t t0 = millis();
    while (!dataReady() && millis() - t0 < 50) {}
    uint8_t b[6];
    readRegs(addr_, OUT_X_L | AUTO_INC, b, sizeof b);
    for (int i = 0; i < 3; ++i) sum[i] += int16_t(b[2 * i] | (b[2 * i + 1] << 8));
  }
  for (int i = 0; i < 3; ++i) out[i] = sum[i] / float(n) / lsb_per_gauss;
}

bool LIS3MDL::selfTest(MagSelfTest& r) {
  r = MagSelfTest{};
  if (whoAmI() != WHO_AM_I_VALUE) return false;
  // AN4602 §: 80 Hz, ±12 gauss, Dauermessung; 20 ms warten, erste Messung verwerfen
  writeReg(addr_, CTRL_REG1, 0x1C);
  writeReg(addr_, CTRL_REG2, 0x40);
  writeReg(addr_, CTRL_REG3, 0x00);
  delay(20);
  float base[3], st[3];
  average(base, 1, LSB_PER_GAUSS_12G);        // erste Messung verwerfen
  average(base, 5, LSB_PER_GAUSS_12G);
  writeReg(addr_, CTRL_REG1, 0x1D);   // ST = 1
  delay(60);
  average(st, 1, LSB_PER_GAUSS_12G);
  average(st, 5, LSB_PER_GAUSS_12G);
  writeReg(addr_, CTRL_REG1, 0x1C);
  r.ok = true;
  for (int i = 0; i < 3; ++i) {
    r.diff_gauss[i] = fabsf(st[i] - base[i]);
    const float lo = i < 2 ? 1.0f : 0.1f, hi = i < 2 ? 3.0f : 1.0f;
    if (r.diff_gauss[i] < lo || r.diff_gauss[i] > hi) r.ok = false;
  }
  if (!begin()) r.ok = false;
  return r.ok;
}
