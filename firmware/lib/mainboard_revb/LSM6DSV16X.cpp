#include "LSM6DSV16X.h"
#include <math.h>

namespace {
// Registerkarte DS13510 §8 (nur die Hauptseite, FUNC_CFG_ACCESS = 0 nach dem Reset)
constexpr uint8_t INT1_CTRL   = 0x0D;   // bit0 INT1_DRDY_XL, bit1 INT1_DRDY_G
constexpr uint8_t WHO_AM_I    = 0x0F;   // 0x70
constexpr uint8_t CTRL1       = 0x10;   // Accel: bit6:4 OP_MODE_XL (000 = High-Performance), bit3:0 ODR_XL
constexpr uint8_t CTRL2       = 0x11;   // Gyro:  bit6:4 OP_MODE_G  (000 = High-Performance), bit3:0 ODR_G
constexpr uint8_t CTRL3       = 0x12;   // bit7 BOOT, bit6 BDU, bit2 IF_INC, bit0 SW_RESET
constexpr uint8_t CTRL6       = 0x15;   // bit6:4 LPF1_G_BW, bit3:0 FS_G
constexpr uint8_t CTRL8       = 0x17;   // bit7:5 HP_LPF2_XL_BW, bit3 XL_DualC_EN, bit1:0 FS_XL
constexpr uint8_t CTRL10      = 0x19;   // bit3:2 ST_G, bit1:0 ST_XL (00 aus, 01 positiv, 10 negativ)
constexpr uint8_t STATUS_REG  = 0x1E;   // bit0 XLDA, bit1 GDA, bit2 TDA
constexpr uint8_t OUT_TEMP_L  = 0x20;   // 0x20/21 Temperatur, 0x22..27 OUTX_L_G.., 0x28..2D OUTX_L_A..

constexpr uint8_t CTRL3_BDU_INC = 0x44;  // BDU = 1, IF_INC = 1 (auch der Reset-Wert)
constexpr uint8_t CTRL3_SW_RESET = 0x01;

// ODR-Codes (CTRL1/CTRL2 bit3:0, gilt für Accel und Gyro gleich, DS13510 Tab. 52/55):
// 0010 7,5 Hz · 0011 15 · 0100 30 · 0101 60 · 0110 120 · 0111 240 · 1000 480 · 1001 960 · 1010 1920 Hz
// (beim LSM6DSO sind die Codes anders: dort ist 0x8 = 1,66 kHz und das Feld liegt in bit7:4)
// PRUEFEN: 0x09 = 960 Hz High-Performance auf der Platine bestätigen (imu_rate muss ~960 Hz zeigen)
constexpr uint8_t ODR_960HZ = 0x09;
constexpr uint8_t ODR_60HZ  = 0x05;
// Messbereiche: FS_G 0100 = ±2000 °/s (0001 ±250, 0010 ±500, 0011 ±1000, 1100 ±4000),
// FS_XL 11 = ±16 g (00 ±2, 01 ±4, 10 ±8)
// PRUEFEN: Codes gegen DS13510 Tab. CTRL6/CTRL8; Kontrolle auf der Platine: imu_rest |a| ≈ 9,8 m/s²,
// eine Vierteldrehung von Hand zeigt in der Summe ≈ 90 ° (Fehler um Faktor 2/4/8 = falscher FS-Code)
constexpr uint8_t FS_G_2000DPS = 0x04;
constexpr uint8_t FS_XL_16G    = 0x03;
constexpr uint8_t FS_XL_4G     = 0x01;

// Selbsttest (AN5763 §"Self-test", DS13510 Tab. 3 "XL_ST"/"G_ST")
// PRUEFEN: ODR 60 Hz, 100 ms Wartezeit, 5 gemittelte Sätze und die Grenzen 50..1700 mg (±4 g) bzw.
// 150..700 °/s (±2000 °/s) sind aus dem Ablauf der LSM6DSx-Familie übernommen; am Datenblatt-Stand
// des bestückten Chips nachlesen und mit der ersten Platine bestätigen.
constexpr float ST_ACC_G_PER_LSB   = 0.122e-3f;   // ±4 g
constexpr float ST_ACC_MIN_G = 0.050f, ST_ACC_MAX_G = 1.700f;
constexpr float ST_GYRO_MIN_DPS = 150.0f, ST_GYRO_MAX_DPS = 700.0f;
constexpr int   ST_SAMPLES = 5;
}  // namespace

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
  if (whoAmI() != WHO_AM_I_VALUE) return false;

  // Erst beide Sensoren aus, dann Soft-Reset (setzt die Steuerregister auf die Reset-Werte)
  writeReg(CTRL1, 0x00);
  writeReg(CTRL2, 0x00);
  writeReg(CTRL3, CTRL3_BDU_INC | CTRL3_SW_RESET);
  const uint32_t t0 = millis();
  while ((readReg(CTRL3) & CTRL3_SW_RESET) && millis() - t0 < 10) delayMicroseconds(50);   // typ. 50 µs
  if (whoAmI() != WHO_AM_I_VALUE) return false;

  writeReg(CTRL3, CTRL3_BDU_INC);         // BDU, Adresse zählt im Burst weiter
  writeReg(CTRL6, FS_G_2000DPS);          // ±2000 °/s, LPF1-Bandbreite Default
  writeReg(CTRL8, FS_XL_16G);             // ±16 g, LPF2 aus
  writeReg(CTRL10, 0x00);                 // kein Testsignal
  writeReg(INT1_CTRL, 0x02);              // INT1 = Gyro-Daten bereit (IF_CFG: push-pull, aktiv hoch)
  // PRUEFEN: INT1 (Pin 4, PIN_IMU_INT) mit dem Oszilloskop; DRDY ist per Default gelatcht (CTRL4.DRDY_PULSED = 0).
  // Die Firmware fragt STATUS_REG ab, der Pin ist nur Zusatz.
  writeReg(CTRL1, ODR_960HZ);             // Accel 960 Hz, High-Performance (OP_MODE_XL = 000)
  writeReg(CTRL2, ODR_960HZ);             // Gyro  960 Hz, High-Performance (OP_MODE_G = 000)
  delay(80);                               // Gyro-Anlauf (Datenblatt: Einschaltzeit bis ca. 70 ms)

  // Kontrolle: Konfiguration zurücklesen
  return readReg(CTRL1) == ODR_960HZ && readReg(CTRL2) == ODR_960HZ &&
         (readReg(CTRL6) & 0x0F) == FS_G_2000DPS && (readReg(CTRL8) & 0x03) == FS_XL_16G &&
         (readReg(CTRL3) & CTRL3_BDU_INC) == CTRL3_BDU_INC && readReg(INT1_CTRL) == 0x02;
}

bool LSM6DSV16X::dataReady() { return readReg(STATUS_REG) & 0x02; }

void LSM6DSV16X::readRaw(int16_t raw[7]) {
  uint8_t b[14];
  bus_.readRegs(revb::Cs::IMU, set_, OUT_TEMP_L, b, sizeof b);
  auto le = [&](int i) { return int16_t(uint16_t(b[2 * i]) | (uint16_t(b[2 * i + 1]) << 8)); };
  raw[0] = le(0);                                   // Temperatur
  for (int i = 0; i < 3; ++i) raw[1 + i] = le(4 + i);   // Accel ab 0x28
  for (int i = 0; i < 3; ++i) raw[4 + i] = le(1 + i);   // Gyro  ab 0x22
}

void LSM6DSV16X::read(ImuSample& s) {
  readRaw(s.raw);
  constexpr float G = 9.80665f;
  s.temp_c = s.raw[0] / 256.0f + 25.0f;            // 256 LSB/°C, 0 = 25 °C (DS13510 Tab. 4)  PRUEFEN: gegen Raumthermometer
  for (int i = 0; i < 3; ++i) {
    s.acc_ms2[i]  = s.raw[1 + i] * (ACC_G_PER_LSB * G);
    s.gyro_dps[i] = s.raw[4 + i] * GYRO_DPS_PER_LSB;
  }
}

// Mittel über n neue Sätze eines Sensors in LSB; der erste Satz nach dem Umschalten wird verworfen
bool LSM6DSV16X::averageSt(float out[3], bool gyro, int n) {
  const uint8_t flag = gyro ? 0x02 : 0x01;
  int16_t raw[7];
  for (int i = 0; i < 3; ++i) out[i] = 0;
  for (int k = -1; k < n; ++k) {
    const uint32_t t0 = millis();
    while (!(readReg(STATUS_REG) & flag)) if (millis() - t0 > 100) return false;
    readRaw(raw);
    if (k < 0) continue;
    for (int i = 0; i < 3; ++i) out[i] += raw[(gyro ? 4 : 1) + i];
  }
  for (int i = 0; i < 3; ++i) out[i] /= n;
  return true;
}

bool LSM6DSV16X::selfTest(ImuSelfTest& r) {
  r = ImuSelfTest{};
  r.acc_min_g = ST_ACC_MIN_G;     r.acc_max_g = ST_ACC_MAX_G;
  r.gyro_min_dps = ST_GYRO_MIN_DPS; r.gyro_max_dps = ST_GYRO_MAX_DPS;
  if (whoAmI() != WHO_AM_I_VALUE) return false;

  // ---- Accel (AN5763): ±4 g, 60 Hz, ohne / mit positivem Testsignal (CTRL10.ST_XL = 01)
  writeReg(CTRL1, 0x00);
  writeReg(CTRL2, 0x00);
  writeReg(CTRL3, CTRL3_BDU_INC);
  writeReg(CTRL10, 0x00);
  writeReg(CTRL8, FS_XL_4G);
  writeReg(CTRL1, ODR_60HZ);
  delay(100);
  float a0[3], a1[3];
  bool ok_a = averageSt(a0, false, ST_SAMPLES);
  writeReg(CTRL10, 0x01);
  delay(100);
  ok_a = averageSt(a1, false, ST_SAMPLES) && ok_a;
  writeReg(CTRL10, 0x00);
  writeReg(CTRL1, 0x00);

  // ---- Gyro: ±2000 °/s, 60 Hz, ohne / mit positivem Testsignal (CTRL10.ST_G = 01)
  writeReg(CTRL6, FS_G_2000DPS);
  writeReg(CTRL2, ODR_60HZ);
  delay(100);
  float g0[3], g1[3];
  bool ok_g = averageSt(g0, true, ST_SAMPLES);
  writeReg(CTRL10, 0x04);
  delay(100);
  ok_g = averageSt(g1, true, ST_SAMPLES) && ok_g;
  writeReg(CTRL10, 0x00);
  writeReg(CTRL2, 0x00);

  r.acc_ok = ok_a;
  r.gyro_ok = ok_g;
  for (int i = 0; i < 3; ++i) {
    r.acc_resp_g[i]      = (a1[i] - a0[i]) * ST_ACC_G_PER_LSB;
    r.gyro_resp_dps[i]   = (g1[i] - g0[i]) * GYRO_DPS_PER_LSB;
    r.gyro_offset_dps[i] = g0[i] * GYRO_DPS_PER_LSB;
    // Kein Werkswert: Verhältnis bleibt 0, die Grenzen stehen in acc_min_g.. / gyro_min_dps..
    const float ar = fabsf(r.acc_resp_g[i]), gr = fabsf(r.gyro_resp_dps[i]);
    if (!ok_a || ar < ST_ACC_MIN_G || ar > ST_ACC_MAX_G) r.acc_ok = false;
    if (!ok_g || gr < ST_GYRO_MIN_DPS || gr > ST_GYRO_MAX_DPS) r.gyro_ok = false;
    if (fabsf(r.gyro_offset_dps[i]) > 20.0f) r.gyro_ok = false;   // wie beim ICM: Platine bewegt?
  }
  r.ok = r.gyro_ok && r.acc_ok;

  // zurück in die Flugkonfiguration
  if (!begin()) r.ok = false;
  return r.ok;
}
