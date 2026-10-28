#include "LSM6DSV16X.h"

using namespace lsm6dsv16x;

uint8_t LSM6DSV16X::readReg(uint8_t reg) {
  uint8_t v = 0;
  bus_.readRegs(revb::Cs::IMU, set_, reg, &v, 1);
  return v;
}

void LSM6DSV16X::writeReg(uint8_t reg, uint8_t val) {
  bus_.writeReg(revb::Cs::IMU, set_, reg, val);
}

uint8_t LSM6DSV16X::whoAmI() { return readReg(WHO_AM_I); }

bool LSM6DSV16X::begin() {
  writeReg(CTRL3, 0x01);                        // SW_RESET
  delay(2);                                     // Reset braucht ~0,5 ms, danach IF_INC wieder setzen
  for (int i = 0; i < 10 && (readReg(CTRL3) & 0x01); ++i) delay(1);
  if (whoAmI() != WHO_AM_I_VALUE) return false;

  writeReg(CTRL3, CTRL3_FLIGHT);                // BDU, Adress-Autoinkrement
  writeReg(CTRL6, CTRL6_FLIGHT);                // Gyro ±2000 °/s
  writeReg(CTRL8, CTRL8_FLIGHT);                // Accel ±16 g
  writeReg(CTRL4, 0x00);                        // INT1 Pegel (nicht gepulst), kein DRDY-Mask
  writeReg(INT1_CTRL, INT1_CTRL_FLIGHT);        // INT1 = Gyro-Daten bereit
  writeReg(CTRL1, CTRL1_FLIGHT);                // Accel 960 Hz, Hochleistung
  writeReg(CTRL2, CTRL2_FLIGHT);                // Gyro 960 Hz, Hochleistung
  delay(80);                                    // Gyro-Anlauf (Datenblatt: 70 ms typisch)

  return readReg(CTRL1) == CTRL1_FLIGHT && readReg(CTRL2) == CTRL2_FLIGHT && readReg(CTRL6) == CTRL6_FLIGHT
         && readReg(CTRL8) == CTRL8_FLIGHT && (readReg(CTRL3) & 0x44) == 0x44;
}

bool LSM6DSV16X::dataReady() { return readReg(STATUS_REG) & 0x02; }

void LSM6DSV16X::readRaw(int16_t raw[7]) {
  uint8_t b[BLOCK_LEN];
  bus_.readRegs(revb::Cs::IMU, set_, OUT_TEMP_L, b, sizeof b);
  decodeBlock(b, raw);
}

void LSM6DSV16X::read(ImuSample& s) {
  readRaw(s.raw);
  s.temp_c = tempC(s.raw[0]);
  for (int i = 0; i < 3; ++i) {
    s.acc_ms2[i]  = accMs2(s.raw[1 + i], FLIGHT_FS_XL);
    s.gyro_dps[i] = gyroDps(s.raw[4 + i], FLIGHT_FS_G);
  }
}

// Mittel über ST_SAMPLES neue Sätze (nach einem verworfenen), in g und °/s der angegebenen Bereiche
bool LSM6DSV16X::average(float acc_g[3], float gyro_dps[3], FsXl fs_xl, FsG fs_g, uint8_t ready_bit) {
  for (int i = 0; i < 3; ++i) acc_g[i] = gyro_dps[i] = 0.0f;
  int16_t raw[7];
  for (int k = -1; k < ST_SAMPLES; ++k) {
    const uint32_t t0 = millis();
    while (!(readReg(STATUS_REG) & ready_bit)) { if (millis() - t0 > 200) return false; }
    readRaw(raw);
    if (k < 0) continue;                        // ersten Satz verwerfen (AN5763)
    for (int i = 0; i < 3; ++i) {
      acc_g[i]    += accMs2(raw[1 + i], fs_xl) / G_MS2;
      gyro_dps[i] += gyroDps(raw[4 + i], fs_g);
    }
  }
  for (int i = 0; i < 3; ++i) { acc_g[i] /= ST_SAMPLES; gyro_dps[i] /= ST_SAMPLES; }
  return true;
}

bool LSM6DSV16X::selfTest(ImuSelfTest& r) {
  r = ImuSelfTest{};
  if (whoAmI() != WHO_AM_I_VALUE) return false;
  float acc_base[3], acc_st[3], g_base[3], g_st[3], dummy[3];

  // --- Accel: 60 Hz, ±4 g, Gyro aus
  writeReg(CTRL10, 0x00);
  writeReg(CTRL3, CTRL3_FLIGHT);
  writeReg(CTRL2, ODR_OFF);
  writeReg(CTRL8, ST_FS_XL);
  writeReg(CTRL1, ST_ODR_XL);
  delay(100);
  bool ok = average(acc_base, dummy, ST_FS_XL, ST_FS_G, 0x01);
  writeReg(CTRL10, ST_XL_POS);
  delay(100);
  ok = ok && average(acc_st, dummy, ST_FS_XL, ST_FS_G, 0x01);
  writeReg(CTRL10, 0x00);
  writeReg(CTRL1, ODR_OFF);

  // --- Gyro: 240 Hz, ±2000 °/s, Accel aus
  writeReg(CTRL6, ST_FS_G);
  writeReg(CTRL2, ST_ODR_G);
  delay(100);
  ok = ok && average(dummy, g_base, ST_FS_XL, ST_FS_G, 0x02);
  writeReg(CTRL10, ST_G_POS);
  delay(100);
  ok = ok && average(dummy, g_st, ST_FS_XL, ST_FS_G, 0x02);
  writeReg(CTRL10, 0x00);

  r.gyro_ok = r.acc_ok = ok;
  for (int i = 0; i < 3; ++i) {
    r.acc_resp_g[i]      = acc_st[i] - acc_base[i];
    r.gyro_resp_dps[i]   = g_st[i] - g_base[i];
    r.gyro_offset_dps[i] = g_base[i];
    // kein Werkswert im Chip: Verhältnis zur Mitte des erlaubten Bereichs, nur zur Anzeige
    r.acc_ratio[i]  = fabsf(r.acc_resp_g[i]) / (0.5f * (ST_ACC_MIN_G + ST_ACC_MAX_G));
    r.gyro_ratio[i] = fabsf(r.gyro_resp_dps[i]) / (0.5f * (ST_GYRO_MIN_DPS + ST_GYRO_MAX_DPS));
    if (!selfTestAxisOk(r.acc_resp_g[i], ST_ACC_MIN_G, ST_ACC_MAX_G)) r.acc_ok = false;
    if (!selfTestAxisOk(r.gyro_resp_dps[i], ST_GYRO_MIN_DPS, ST_GYRO_MAX_DPS)) r.gyro_ok = false;
    if (fabsf(r.gyro_offset_dps[i]) > 20.0f) r.gyro_ok = false;
  }
  r.ok = r.gyro_ok && r.acc_ok;

  if (!begin()) r.ok = false;                   // zurück in die Flugkonfiguration
  return r.ok;
}
