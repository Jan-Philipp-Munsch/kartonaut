#pragma once
// LIS3MDL.h – 3-Achsen-Magnetometer LIS3MDL an Wire (rev B1, U16, 0x1E)
//
// Registerkarte: ST DocID024204 rev 6. Betrieb: ±4 gauss (6842 LSB/gauss),
// 80 Hz, Ultra-High-Performance auf allen Achsen, Block Data Update,
// Temperatursensor an. Selbsttest nach AN4602 (±12 gauss, Differenz
// X/Y 1,0..3,0 gauss, Z 0,1..1,0 gauss).
//
// Das Feld auf der Platine wird von Servo- und Motorströmen verbogen;
// der Sensor ist für den Boden und ruhige Flugphasen gedacht. Hard- und
// Soft-Iron kommen aus der Kalibrierung (revb_test: "cal mag").
#include <Arduino.h>

struct MagSample {
  float mag_gauss[3];   // Chip-Achsen, unkorrigiert
  float temp_c;
  int16_t raw[3];
};

struct MagSelfTest {
  bool  ok = false;
  float diff_gauss[3] = {0, 0, 0};
};

class LIS3MDL {
public:
  static constexpr uint8_t WHO_AM_I_VALUE = 0x3D;
  static constexpr float   LSB_PER_GAUSS_4G  = 6842.0f;
  static constexpr float   LSB_PER_GAUSS_12G = 2281.0f;

  explicit LIS3MDL(uint8_t addr) : addr_(addr) {}

  bool    begin();                    // Reset, Kennung, Konfiguration
  uint8_t whoAmI();
  bool    dataReady();
  bool    read(MagSample& s);
  bool    selfTest(MagSelfTest& r);   // ruft danach begin()

private:
  void configure();
  void average(float out[3], int n, float lsb_per_gauss);
  uint8_t addr_;
};
