#pragma once
// Lsm6dsv16xCore.h – Register, Codes und Umrechnungen des LSM6DSV16X ohne Arduino
//
// Quelle: ST Datenblatt DS14048 (LSM6DSV16X) und AN5763 (Selbsttest). Alles hier ist reine Arithmetik,
// damit es in test/host/test_lsm6dsv16x.cpp auf dem PC geprüft werden kann; die SPI-Zugriffe stehen in
// LSM6DSV16X.cpp. Die Grenzwerte des Selbsttests sind aus dem Datenblatt, an der Platine noch nicht bestätigt.
#include <stdint.h>
#include <math.h>

namespace lsm6dsv16x {

// ---- Register (Bank 0 des Benutzerbereichs)
constexpr uint8_t FUNC_CFG_ACCESS = 0x01;
constexpr uint8_t IF_CFG          = 0x03;
constexpr uint8_t INT1_CTRL       = 0x0D;   // bit0 INT1_DRDY_XL, bit1 INT1_DRDY_G
constexpr uint8_t WHO_AM_I        = 0x0F;
constexpr uint8_t CTRL1           = 0x10;   // OP_MODE_XL[6:4], ODR_XL[3:0]
constexpr uint8_t CTRL2           = 0x11;   // OP_MODE_G[6:4], ODR_G[3:0]
constexpr uint8_t CTRL3           = 0x12;   // bit7 BOOT, bit6 BDU, bit2 IF_INC, bit0 SW_RESET
constexpr uint8_t CTRL4           = 0x13;   // bit3 DRDY_MASK, bit1 DRDY_PULSED
constexpr uint8_t CTRL6           = 0x15;   // LPF1_G_BW[6:4], FS_G[3:0]
constexpr uint8_t CTRL7           = 0x16;   // bit0 LPF1_G_EN
constexpr uint8_t CTRL8           = 0x17;   // HP_LPF2_XL_BW[7:5], FS_XL[1:0]
constexpr uint8_t CTRL9           = 0x18;   // bit3 LPF2_XL_EN
constexpr uint8_t CTRL10          = 0x19;   // ST_G[3:2], ST_XL[1:0]
constexpr uint8_t STATUS_REG      = 0x1E;   // bit0 XLDA, bit1 GDA, bit2 TDA
constexpr uint8_t OUT_TEMP_L      = 0x20;   // 14-Byte-Block: T, Gyro xyz, Accel xyz, little-endian
constexpr uint8_t OUTX_L_G        = 0x22;
constexpr uint8_t OUTX_L_A        = 0x28;

constexpr uint8_t WHO_AM_I_VALUE  = 0x70;
constexpr size_t  BLOCK_LEN       = 14;

// ---- Datenraten (ODR[3:0] in CTRL1/CTRL2), Hochleistungsmodus OP_MODE = 000
enum Odr : uint8_t {
  ODR_OFF = 0x0, ODR_1_875 = 0x1, ODR_7_5 = 0x2, ODR_15 = 0x3, ODR_30 = 0x4, ODR_60 = 0x5, ODR_120 = 0x6,
  ODR_240 = 0x7, ODR_480 = 0x8, ODR_960 = 0x9, ODR_1920 = 0xA, ODR_3840 = 0xB, ODR_7680 = 0xC
};
// 1,875 Hz, dann 7,5 Hz · 2^(Code − 2): 15, 30, 60, 120, 240, 480, 960, 1920, 3840, 7680 Hz
inline float odrHz(Odr o) { return o == ODR_OFF ? 0.0f : o == ODR_1_875 ? 1.875f : 7.5f * (float)(1u << (o - 2)); }

// ---- Messbereiche
enum FsXl : uint8_t { FS_XL_2G = 0x0, FS_XL_4G = 0x1, FS_XL_8G = 0x2, FS_XL_16G = 0x3 };
enum FsG  : uint8_t { FS_G_125 = 0x0, FS_G_250 = 0x1, FS_G_500 = 0x2, FS_G_1000 = 0x3, FS_G_2000 = 0x4, FS_G_4000 = 0xC };

// Empfindlichkeit (Datenblatt Tabelle 2): Accel 0,061 mg/LSB bei ±2 g, verdoppelt je Stufe; Gyro 4,375 mdps/LSB bei ±125
inline float accMgPerLsb(FsXl fs) { return 0.061f * (float)(1u << fs); }
inline float gyroMdpsPerLsb(FsG fs) { return fs == FS_G_4000 ? 140.0f : 4.375f * (float)(1u << fs); }
constexpr float TEMP_LSB_PER_C = 256.0f;    // 25 °C bei 0
constexpr float G_MS2 = 9.80665f;

// ---- Flugkonfiguration: Gyro ±2000 °/s, Accel ±16 g, beide 960 Hz
constexpr Odr  FLIGHT_ODR = ODR_960;
constexpr FsXl FLIGHT_FS_XL = FS_XL_16G;
constexpr FsG  FLIGHT_FS_G = FS_G_2000;
constexpr uint8_t CTRL1_FLIGHT = FLIGHT_ODR;                 // OP_MODE 000 (high performance)
constexpr uint8_t CTRL2_FLIGHT = FLIGHT_ODR;
constexpr uint8_t CTRL3_FLIGHT = 0x44;                       // BDU, IF_INC
constexpr uint8_t CTRL6_FLIGHT = FLIGHT_FS_G;                // LPF1-Bandbreite 000
constexpr uint8_t CTRL8_FLIGHT = FLIGHT_FS_XL;
constexpr uint8_t INT1_CTRL_FLIGHT = 0x02;                   // INT1 = Gyro-Daten bereit

inline int16_t le16(uint8_t lo, uint8_t hi) { return (int16_t)((uint16_t)lo | ((uint16_t)hi << 8)); }

// 14-Byte-Block ab OUT_TEMP_L nach raw[7] in der Reihenfolge von ImuSample: T, ax, ay, az, gx, gy, gz
inline void decodeBlock(const uint8_t b[BLOCK_LEN], int16_t raw[7]) {
  raw[0] = le16(b[0], b[1]);
  for (int i = 0; i < 3; ++i) {
    raw[4 + i] = le16(b[2 + 2 * i], b[3 + 2 * i]);    // Gyro steht vor Accel
    raw[1 + i] = le16(b[8 + 2 * i], b[9 + 2 * i]);
  }
}

inline float tempC(int16_t raw) { return raw / TEMP_LSB_PER_C + 25.0f; }
inline float accMs2(int16_t raw, FsXl fs) { return raw * accMgPerLsb(fs) * 1e-3f * G_MS2; }
inline float gyroDps(int16_t raw, FsG fs) { return raw * gyroMdpsPerLsb(fs) * 1e-3f; }

// ---- Selbsttest (AN5763 §?: Mittel mit minus Mittel ohne Testsignal, Betrag innerhalb der Grenzen)
// Accel: ODR 60 Hz, FS ±4 g, Antwort 50 … 1700 mg. Gyro: ODR 240 Hz, FS ±2000 °/s, Antwort 20 … 80 °/s.
constexpr uint8_t ST_XL_POS = 0x01, ST_G_POS = 0x04;         // CTRL10: ST_XL = 01, ST_G = 01
constexpr Odr  ST_ODR_XL = ODR_60;
constexpr Odr  ST_ODR_G = ODR_240;
constexpr FsXl ST_FS_XL = FS_XL_4G;
constexpr FsG  ST_FS_G = FS_G_2000;
constexpr float ST_ACC_MIN_G = 0.05f, ST_ACC_MAX_G = 1.7f;
constexpr float ST_GYRO_MIN_DPS = 20.0f, ST_GYRO_MAX_DPS = 80.0f;
constexpr int   ST_SAMPLES = 5;                               // nach einem verworfenen Satz

inline bool selfTestAxisOk(float response, float lo, float hi) {
  const float a = fabsf(response);
  return a >= lo && a <= hi;
}

}  // namespace lsm6dsv16x
