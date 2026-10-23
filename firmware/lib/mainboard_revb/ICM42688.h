#pragma once
// ICM42688.h – IMU ICM-42688-P an SPI1, ohne DMP und ohne FIFO
//
// Registerkarte: TDK DS-000347 rev 1.8, Bank 0. Konfiguration für den Flug:
// Gyro ±2000 °/s, Accel ±16 g, beide 1 kHz im Low-Noise-Modus, INT1
// push-pull aktiv hoch bei "Daten bereit". Gelesen wird ein 14-Byte-Block
// ab TEMP_DATA1 (Temperatur, Accel xyz, Gyro xyz, big-endian).
//
// Achsen: Chip-Achsen. Die Drehung Chip -> Körpersystem (x, y quer, z
// Rollachse) kommt aus der Kalibrierung (revb_test: "cal axes").
//
// Selbsttest nach dem TDK-Referenzablauf (icm426xx_selftest.c): Gyro
// ±250 °/s und Accel ±2 g bei 1 kHz, Antwort = Mittel mit minus Mittel
// ohne Testsignal, Vergleich mit dem Werkswert aus Bank 1/2.
#include "Imu.h"
#include "BusRevB.h"

class ICM42688 : public ImuDriver {
public:
  static constexpr uint8_t WHO_AM_I_VALUE = 0x47;
  static constexpr float   ACC_LSB_PER_G    = 2048.0f;   // ±16 g
  static constexpr float   GYRO_LSB_PER_DPS = 16.4f;     // ±2000 °/s

  explicit ICM42688(BusRevB& bus) : bus_(bus) {}

  const char* name() const override { return "ICM-42688-P"; }
  uint8_t expectedWhoAmI() const override { return WHO_AM_I_VALUE; }
  float   sampleRateHz() const override { return 1000.0f; }

  // Soft-Reset, WHO_AM_I prüfen, konfigurieren, Sensoren einschalten.
  // Danach braucht der Gyro ca. 45 ms, bis die Werte gelten.
  bool begin() override;
  uint8_t whoAmI() override;

  // true, wenn seit dem letzten Lesen ein neuer Satz da ist (INT_STATUS)
  bool dataReady() override;
  void read(ImuSample& s) override;

  bool selfTest(ImuSelfTest& r) override;

private:
  uint8_t readReg(uint8_t reg);
  void    writeReg(uint8_t reg, uint8_t val);
  void    bank(uint8_t b);
  void    readRaw(int16_t raw[7]);
  void    average(int32_t sum[6], int n);

  BusRevB& bus_;
  // bis 24 MHz erlaubt; 8 MHz ist auf 10 cm Leitung über den Decoder sicher
  const SPISettings set_{8000000, MSBFIRST, SPI_MODE0};
};
