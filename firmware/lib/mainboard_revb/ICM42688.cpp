#include "ICM42688.h"

namespace {
// Bank 0 (DS-000347 §14)
constexpr uint8_t DEVICE_CONFIG  = 0x11;   // bit0 SOFT_RESET_CONFIG
constexpr uint8_t INT_CONFIG     = 0x14;   // INT1 Modus/Treiber/Polarität
constexpr uint8_t TEMP_DATA1     = 0x1D;   // Beginn des 14-Byte-Blocks
constexpr uint8_t INT_STATUS     = 0x2D;   // bit3 DATA_RDY_INT
constexpr uint8_t INTF_CONFIG0   = 0x4C;   // Endianness, UI_SIFS_CFG
constexpr uint8_t PWR_MGMT0      = 0x4E;
constexpr uint8_t GYRO_CONFIG0   = 0x4F;
constexpr uint8_t ACCEL_CONFIG0  = 0x50;
constexpr uint8_t INT_CONFIG1    = 0x64;   // bit4 INT_ASYNC_RESET muss 0 sein
constexpr uint8_t INT_SOURCE0    = 0x65;   // bit3 UI_DRDY_INT1_EN
constexpr uint8_t WHO_AM_I       = 0x75;
constexpr uint8_t REG_BANK_SEL   = 0x76;
}  // namespace

uint8_t ICM42688::readReg(uint8_t reg) {
  uint8_t v = 0;
  bus_.readRegs(revb::Cs::IMU, set_, reg, &v, 1);
  return v;
}

void ICM42688::writeReg(uint8_t reg, uint8_t val) {
  bus_.writeReg(revb::Cs::IMU, set_, reg, val);
}

uint8_t ICM42688::whoAmI() { return readReg(WHO_AM_I); }

bool ICM42688::begin() {
  writeReg(REG_BANK_SEL, 0);
  writeReg(DEVICE_CONFIG, 0x01);          // Soft-Reset
  delay(2);                                // ≥ 1 ms
  if (whoAmI() != WHO_AM_I_VALUE) return false;

  writeReg(INTF_CONFIG0, 0x33);           // Daten big-endian (Default), I²C-Schnittstelle aus
  writeReg(GYRO_CONFIG0, 0x06);           // FS ±2000 °/s (000), ODR 1 kHz (0110)
  writeReg(ACCEL_CONFIG0, 0x06);          // FS ±16 g (000), ODR 1 kHz (0110)
  writeReg(INT_CONFIG, 0x03);             // INT1 gepulst, push-pull, aktiv hoch
  writeReg(INT_CONFIG1, 0x00);            // INT_ASYNC_RESET = 0 (Datenblatt-Pflicht), 100-µs-Puls
  writeReg(INT_SOURCE0, 0x08);            // nur "Daten bereit" auf INT1
  writeReg(PWR_MGMT0, 0x0F);              // Gyro und Accel Low-Noise
  delayMicroseconds(300);                 // nach PWR_MGMT0 200 µs keine Zugriffe
  delay(50);                              // Gyro-Anlauf 45 ms

  // Kontrolle: Konfiguration zurücklesen
  return readReg(GYRO_CONFIG0) == 0x06 && readReg(ACCEL_CONFIG0) == 0x06 && readReg(PWR_MGMT0) == 0x0F;
}

bool ICM42688::dataReady() { return readReg(INT_STATUS) & 0x08; }

void ICM42688::read(ImuSample& s) {
  uint8_t b[14];
  bus_.readRegs(revb::Cs::IMU, set_, TEMP_DATA1, b, sizeof b);
  for (int i = 0; i < 7; ++i) s.raw[i] = int16_t((b[2 * i] << 8) | b[2 * i + 1]);

  constexpr float G = 9.80665f;
  s.temp_c = s.raw[0] / 132.48f + 25.0f;
  for (int i = 0; i < 3; ++i) {
    s.acc_ms2[i]  = s.raw[1 + i] * (G / ACC_LSB_PER_G);
    s.gyro_dps[i] = s.raw[4 + i] / GYRO_LSB_PER_DPS;
  }
}
