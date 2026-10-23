#include "ICM42688.h"
#include <math.h>

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
constexpr uint8_t GYRO_ACCEL_CONFIG0 = 0x52;   // UI-Filterbandbreiten
constexpr uint8_t INT_CONFIG1    = 0x64;   // bit4 INT_ASYNC_RESET muss 0 sein
constexpr uint8_t INT_SOURCE0    = 0x65;   // bit3 UI_DRDY_INT1_EN
constexpr uint8_t SELF_TEST_CONFIG = 0x70; // bit6 ACCEL_ST_POWER, 5:3 EN_A, 2:0 EN_G
constexpr uint8_t WHO_AM_I       = 0x75;
constexpr uint8_t REG_BANK_SEL   = 0x76;
// Bank 1 / Bank 2: Werkswerte des Selbsttests
constexpr uint8_t XG_ST_DATA     = 0x5F;   // Bank 1, 3 Byte
constexpr uint8_t XA_ST_DATA     = 0x3B;   // Bank 2, 3 Byte

// Selbsttest: ±250 °/s (131 LSB/°/s) und ±2 g (16384 LSB/g), 1 kHz
constexpr uint8_t ST_GYRO_CONFIG0  = 0x66;
constexpr uint8_t ST_ACCEL_CONFIG0 = 0x66;
constexpr float   ST_GYRO_LSB_PER_DPS = 131.0f;
constexpr float   ST_ACC_LSB_PER_G    = 16384.0f;
constexpr int     ST_SAMPLES = 200;

// Werkswert aus dem OTP-Code: ST_OTP = 2620 / 2^(3-FS) · 1,01^(code-1), hier FS-Index 3
float stOtp(uint8_t code) { return code == 0 ? 0.0f : 2620.0f * powf(1.01f, float(code) - 1.0f); }
}  // namespace

uint8_t ICM42688::readReg(uint8_t reg) {
  uint8_t v = 0;
  bus_.readRegs(revb::Cs::IMU, set_, reg, &v, 1);
  return v;
}

void ICM42688::writeReg(uint8_t reg, uint8_t val) {
  bus_.writeReg(revb::Cs::IMU, set_, reg, val);
}

void ICM42688::bank(uint8_t b) { writeReg(REG_BANK_SEL, b); }

uint8_t ICM42688::whoAmI() { return readReg(WHO_AM_I); }

bool ICM42688::begin() {
  bank(0);
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

void ICM42688::readRaw(int16_t raw[7]) {
  uint8_t b[14];
  bus_.readRegs(revb::Cs::IMU, set_, TEMP_DATA1, b, sizeof b);
  for (int i = 0; i < 7; ++i) raw[i] = int16_t((b[2 * i] << 8) | b[2 * i + 1]);
}

void ICM42688::read(ImuSample& s) {
  readRaw(s.raw);
  constexpr float G = 9.80665f;
  s.temp_c = s.raw[0] / 132.48f + 25.0f;
  for (int i = 0; i < 3; ++i) {
    s.acc_ms2[i]  = s.raw[1 + i] * (G / ACC_LSB_PER_G);
    s.gyro_dps[i] = s.raw[4 + i] / GYRO_LSB_PER_DPS;
  }
}

// Mittel über n neue Sätze (ax ay az gx gy gz), wartet jeweils auf "Daten bereit"
void ICM42688::average(int32_t sum[6], int n) {
  for (int i = 0; i < 6; ++i) sum[i] = 0;
  int16_t raw[7];
  for (int k = 0; k < n; ++k) {
    const uint32_t t0 = micros();
    while (!dataReady() && micros() - t0 < 5000) {}
    readRaw(raw);
    for (int i = 0; i < 6; ++i) sum[i] += raw[1 + i];
  }
  for (int i = 0; i < 6; ++i) sum[i] /= n;
}

bool ICM42688::selfTest(ImuSelfTest& r) {
  r = ImuSelfTest{};
  bank(0);
  if (whoAmI() != WHO_AM_I_VALUE) return false;

  // Testkonfiguration: kleine Messbereiche, Filter ODR/10, Low-Noise
  writeReg(GYRO_CONFIG0, ST_GYRO_CONFIG0);
  writeReg(ACCEL_CONFIG0, ST_ACCEL_CONFIG0);
  writeReg(GYRO_ACCEL_CONFIG0, 0x44);
  writeReg(PWR_MGMT0, 0x0F);
  delayMicroseconds(300);
  delay(100);                                       // Gyro-Anlauf, Filter einschwingen

  int32_t base[6], st[6];
  average(base, ST_SAMPLES);

  // Gyro-Testsignal
  writeReg(SELF_TEST_CONFIG, 0x07);
  delay(200);
  average(st, ST_SAMPLES);
  int32_t gyro_resp[3];
  for (int i = 0; i < 3; ++i) gyro_resp[i] = st[3 + i] - base[3 + i];

  // Accel-Testsignal
  writeReg(SELF_TEST_CONFIG, 0x78);
  delay(200);
  average(st, ST_SAMPLES);
  int32_t acc_resp[3];
  for (int i = 0; i < 3; ++i) acc_resp[i] = st[i] - base[i];
  writeReg(SELF_TEST_CONFIG, 0x00);

  // Werkswerte
  uint8_t otp_g[3], otp_a[3];
  bank(1);
  bus_.readRegs(revb::Cs::IMU, set_, XG_ST_DATA, otp_g, 3);
  bank(2);
  bus_.readRegs(revb::Cs::IMU, set_, XA_ST_DATA, otp_a, 3);
  bank(0);

  r.gyro_ok = r.acc_ok = true;
  for (int i = 0; i < 3; ++i) {
    r.gyro_resp_dps[i]   = gyro_resp[i] / ST_GYRO_LSB_PER_DPS;
    r.gyro_offset_dps[i] = base[3 + i] / ST_GYRO_LSB_PER_DPS;
    r.acc_resp_g[i]      = acc_resp[i] / ST_ACC_LSB_PER_G;
    const float og = stOtp(otp_g[i]), oa = stOtp(otp_a[i]);
    r.gyro_ratio[i] = og > 0 ? gyro_resp[i] / og : 0.0f;
    r.acc_ratio[i]  = oa > 0 ? acc_resp[i] / oa : 0.0f;
    // TDK: mit Werkswert 50..150 %, ohne Werkswert Gyro ≥ 60 °/s, Accel 50..1200 mg
    if (og > 0 ? (r.gyro_ratio[i] < 0.5f || r.gyro_ratio[i] > 1.5f) : fabsf(r.gyro_resp_dps[i]) < 60.0f)
      r.gyro_ok = false;
    if (fabsf(r.gyro_offset_dps[i]) > 20.0f) r.gyro_ok = false;
    if (oa > 0 ? (r.acc_ratio[i] < 0.5f || r.acc_ratio[i] > 1.5f)
               : (fabsf(r.acc_resp_g[i]) < 0.05f || fabsf(r.acc_resp_g[i]) > 1.2f))
      r.acc_ok = false;
  }
  r.ok = r.gyro_ok && r.acc_ok;

  // zurück in die Flugkonfiguration
  if (!begin()) r.ok = false;
  return r.ok;
}
