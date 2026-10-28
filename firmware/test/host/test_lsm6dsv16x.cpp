// Host-Test des reinen LSM6DSV16X-Kerns (Register, Codes, Umrechnungen, Selbsttest-Bewertung):
//   g++ -std=c++17 -Wall -Wextra -I firmware/lib/mainboard_revb firmware/test/host/test_lsm6dsv16x.cpp && ./a.out
#include "Lsm6dsv16xCore.h"
#include <stdio.h>
#include <math.h>

static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); ++fails; } } while (0)
#define NEAR(a, b, tol) CHECK(fabs((double)(a) - (double)(b)) <= (tol))

using namespace lsm6dsv16x;

int main() {
  // Kennung und Flugkonfiguration (Datenblatt DS14048)
  CHECK(WHO_AM_I == 0x0F && WHO_AM_I_VALUE == 0x70);
  CHECK(CTRL1_FLIGHT == 0x09 && CTRL2_FLIGHT == 0x09);        // 960 Hz, Hochleistung
  CHECK(CTRL6_FLIGHT == 0x04);                                // ±2000 °/s
  CHECK(CTRL8_FLIGHT == 0x03);                                // ±16 g
  CHECK((CTRL3_FLIGHT & 0x40) && (CTRL3_FLIGHT & 0x04));      // BDU, IF_INC
  NEAR(odrHz(ODR_960), 960.0f, 0.01);
  NEAR(odrHz(ODR_60), 60.0f, 0.01);
  NEAR(odrHz(ODR_240), 240.0f, 0.01);
  NEAR(odrHz(ODR_7680), 7680.0f, 0.01);
  CHECK(odrHz(ODR_OFF) == 0.0f);

  // Empfindlichkeiten (Tabelle 2)
  NEAR(accMgPerLsb(FS_XL_2G), 0.061f, 1e-6);
  NEAR(accMgPerLsb(FS_XL_16G), 0.488f, 1e-6);
  NEAR(gyroMdpsPerLsb(FS_G_250), 8.75f, 1e-6);
  NEAR(gyroMdpsPerLsb(FS_G_2000), 70.0f, 1e-6);
  NEAR(gyroMdpsPerLsb(FS_G_4000), 140.0f, 1e-6);

  // 1 g bei ±16 g sind 2049 LSB (1000 / 0,488); 1000 °/s bei ±2000 sind 14286 LSB
  NEAR(accMs2(2049, FS_XL_16G), G_MS2, 0.01);
  NEAR(gyroDps(14286, FS_G_2000), 1000.0f, 0.1);
  NEAR(gyroDps(-14286, FS_G_2000), -1000.0f, 0.1);
  NEAR(tempC(0), 25.0f, 1e-6);
  NEAR(tempC(256), 26.0f, 1e-6);
  NEAR(tempC(-512), 23.0f, 1e-6);

  // Block little-endian: T = 0x0100 (26 °C), Gyro x,y,z = 1, -1, 0x7FFF, Accel x,y,z = 2, 3, -2
  const uint8_t b[14] = {0x00, 0x01,  0x01, 0x00, 0xFF, 0xFF, 0xFF, 0x7F,  0x02, 0x00, 0x03, 0x00, 0xFE, 0xFF};
  int16_t raw[7];
  decodeBlock(b, raw);
  CHECK(raw[0] == 256);
  CHECK(raw[1] == 2 && raw[2] == 3 && raw[3] == -2);          // Accel in ImuSample-Reihenfolge
  CHECK(raw[4] == 1 && raw[5] == -1 && raw[6] == 32767);      // Gyro
  CHECK(le16(0x34, 0x12) == 0x1234 && le16(0x00, 0x80) == -32768);

  // Selbsttest-Bewertung: Betrag innerhalb der Grenzen, Vorzeichen egal
  CHECK(selfTestAxisOk(0.9f, ST_ACC_MIN_G, ST_ACC_MAX_G));
  CHECK(selfTestAxisOk(-0.9f, ST_ACC_MIN_G, ST_ACC_MAX_G));
  CHECK(!selfTestAxisOk(0.04f, ST_ACC_MIN_G, ST_ACC_MAX_G));
  CHECK(!selfTestAxisOk(1.8f, ST_ACC_MIN_G, ST_ACC_MAX_G));
  CHECK(selfTestAxisOk(50.0f, ST_GYRO_MIN_DPS, ST_GYRO_MAX_DPS));
  CHECK(!selfTestAxisOk(10.0f, ST_GYRO_MIN_DPS, ST_GYRO_MAX_DPS));
  CHECK(!selfTestAxisOk(90.0f, ST_GYRO_MIN_DPS, ST_GYRO_MAX_DPS));
  CHECK(ST_XL_POS == 0x01 && ST_G_POS == 0x04);               // CTRL10: ST_XL[1:0] = 01, ST_G[3:2] = 01

  printf("%s (%d Fehler)\n", fails ? "FAIL" : "OK", fails);
  return fails ? 1 : 0;
}
