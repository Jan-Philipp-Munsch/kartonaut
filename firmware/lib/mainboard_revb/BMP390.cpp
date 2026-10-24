#include "BMP390.h"
#include <math.h>

namespace {
constexpr uint8_t CHIP_ID   = 0x00;
constexpr uint8_t ERR_REG   = 0x02;   // bit2 conf_err
constexpr uint8_t STATUS    = 0x03;   // bit5 drdy_press, bit6 drdy_temp
constexpr uint8_t DATA_0    = 0x04;   // Druck xlsb..msb, Temperatur xlsb..msb
constexpr uint8_t PWR_CTRL  = 0x1B;
constexpr uint8_t OSR       = 0x1C;
constexpr uint8_t ODR       = 0x1D;
constexpr uint8_t CONFIG    = 0x1F;
constexpr uint8_t NVM_PAR   = 0x31;   // 21 Byte Kalibrierung
constexpr uint8_t CMD       = 0x7E;
}  // namespace

uint8_t BMP390::readReg(uint8_t reg) {
  uint8_t v = 0;
  readRegs(reg, &v, 1);
  return v;
}

void BMP390::readRegs(uint8_t reg, uint8_t* buf, size_t n) {
  bus_.readRegs(cs_, set_, reg, buf, n, 1);   // ein Füllbyte
}

void BMP390::writeReg(uint8_t reg, uint8_t val) {
  bus_.writeReg(cs_, set_, reg, val);
}

bool BMP390::begin() {
  (void)readReg(CHIP_ID);                      // CSB-Flanke: I²C -> SPI
  writeReg(CMD, 0xB6);                         // Soft-Reset
  delay(10);
  (void)readReg(CHIP_ID);                      // nach dem Reset wieder I²C -> SPI
  chip_id_ = readReg(CHIP_ID);
  if (chip_id_ != CHIP_ID_BMP390 && chip_id_ != CHIP_ID_BMP388) return false;
  if (!readCalibration()) return false;

  writeReg(OSR, (0b000 << 3) | 0b011);         // osr_t ×1, osr_p ×8
  writeReg(ODR, 0x02);                         // 200 Hz / 2^2 = 50 Hz
  writeReg(CONFIG, 0b010 << 1);                // IIR-Koeffizient 3
  writeReg(PWR_CTRL, 0x33);                    // Druck und Temperatur an, Normal-Modus
  delay(5);
  return (readReg(ERR_REG) & 0x04) == 0;       // conf_err: ODR zu schnell für die OSR
}

bool BMP390::readCalibration() {
  uint8_t c[21];
  readRegs(NVM_PAR, c, sizeof c);
  auto u16 = [&](int i) { return double(uint16_t(c[i] | (c[i + 1] << 8))); };
  auto s16 = [&](int i) { return double(int16_t(c[i] | (c[i + 1] << 8))); };
  auto s8  = [&](int i) { return double(int8_t(c[i])); };

  t1_  = u16(0)  * 256.0;                       // / 2^-8
  t2_  = u16(2)  / 1073741824.0;                // / 2^30
  t3_  = s8(4)   / 281474976710656.0;           // / 2^48
  p1_  = (s16(5) - 16384.0) / 1048576.0;        // (P1 - 2^14) / 2^20
  p2_  = (s16(7) - 16384.0) / 536870912.0;      // (P2 - 2^14) / 2^29
  p3_  = s8(9)   / 4294967296.0;                // / 2^32
  p4_  = s8(10)  / 137438953472.0;              // / 2^37
  p5_  = u16(11) * 8.0;                         // / 2^-3
  p6_  = u16(13) / 64.0;                        // / 2^6
  p7_  = s8(15)  / 256.0;                       // / 2^8
  p8_  = s8(16)  / 32768.0;                     // / 2^15
  p9_  = s16(17) / 281474976710656.0;           // / 2^48
  p10_ = s8(19)  / 281474976710656.0;           // / 2^48
  p11_ = s8(20)  / 36893488147419103232.0;      // / 2^65
  return t1_ != 0.0;                            // lauter Nullen = kein Chip
}

bool BMP390::read(float& pressure_pa, float& temp_c) {
  if ((readReg(STATUS) & 0x60) != 0x60) return false;
  uint8_t d[6];
  readRegs(DATA_0, d, sizeof d);
  const double up = double(uint32_t(d[0]) | (uint32_t(d[1]) << 8) | (uint32_t(d[2]) << 16));
  const double ut = double(uint32_t(d[3]) | (uint32_t(d[4]) << 8) | (uint32_t(d[5]) << 16));

  // Temperatur (§9.2)
  const double pd1 = ut - t1_;
  const double t   = pd1 * t2_ + pd1 * pd1 * t3_;

  // Druck (§9.3)
  const double t2 = t * t, t3 = t2 * t;
  const double out1 = p5_ + p6_ * t + p7_ * t2 + p8_ * t3;
  const double out2 = up * (p1_ + p2_ * t + p3_ * t2 + p4_ * t3);
  const double up2 = up * up;
  const double out3 = up2 * (p9_ + p10_ * t) + up2 * up * p11_;

  pressure_pa = float(out1 + out2 + out3);
  temp_c      = float(t);
  return true;
}

float BMP390::altitude_m(float p_pa, float p0_pa) {
  return 44330.0f * (1.0f - powf(p_pa / p0_pa, 0.190295f));
}
