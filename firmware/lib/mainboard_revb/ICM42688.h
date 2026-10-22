#pragma once
// ICM42688.h – IMU ICM-42688-P an SPI1, ohne DMP und ohne FIFO
//
// Registerkarte: TDK DS-000347 rev 1.8, Bank 0. Konfiguration für den Flug:
// Gyro ±2000 °/s, Accel ±16 g, beide 1 kHz im Low-Noise-Modus, INT1
// push-pull aktiv hoch bei "Daten bereit". Gelesen wird ein 14-Byte-Block
// ab TEMP_DATA1 (Temperatur, Accel xyz, Gyro xyz, big-endian).
//
// Achsen: Chip-Achsen. Die Drehung Chip -> Körpersystem (x, y quer, z
// Rollachse) hängt von der Lage von U4 auf der Platine und der Platine im
// Kuppler ab und kommt erst mit der fertigen Platzierung.
#include "BusRevB.h"

struct ImuSample {
  float acc_ms2[3];    // Beschleunigung (spezifische Kraft), Chip-Achsen
  float gyro_dps[3];   // Drehrate, Chip-Achsen
  float temp_c;
  int16_t raw[7];      // T, ax, ay, az, gx, gy, gz
};

class ICM42688 {
public:
  static constexpr uint8_t WHO_AM_I_VALUE = 0x47;
  static constexpr float   ACC_LSB_PER_G    = 2048.0f;   // ±16 g
  static constexpr float   GYRO_LSB_PER_DPS = 16.4f;     // ±2000 °/s

  explicit ICM42688(BusRevB& bus) : bus_(bus) {}

  // Soft-Reset, WHO_AM_I prüfen, konfigurieren, Sensoren einschalten.
  // Danach braucht der Gyro ca. 45 ms, bis die Werte gelten.
  bool begin();
  uint8_t whoAmI();

  // true, wenn seit dem letzten Lesen ein neuer Satz da ist (INT_STATUS)
  bool dataReady();
  void read(ImuSample& s);

private:
  uint8_t readReg(uint8_t reg);
  void    writeReg(uint8_t reg, uint8_t val);

  BusRevB& bus_;
  // bis 24 MHz erlaubt; 8 MHz ist auf 10 cm Leitung über den Decoder sicher
  const SPISettings set_{8000000, MSBFIRST, SPI_MODE0};
};
