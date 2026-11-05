#pragma once
// LSM6DSV16X.h – IMU LSM6DSV16X (ST) an SPI1 über den CS-Decoder (Y0), ohne FIFO und ohne
// eingebettete Funktionen (SFLP, MLC, FSM bleiben aus)
//
// Seit 23.10.2026 auf rev B1 bestückt (U4, statt ICM-42688-P, gleiches LGA-14-Landebild).
// Registerkarte: ST DS13510 (LSM6DSV16X) §8/§9, Selbsttest nach AN5763 (Application Note
// LSM6DSV16X). SPI 4-Draht, Modus 3 (CPOL = CPHA = 1), höchstens 10 MHz. Lesen = Adresse | 0x80,
// mit IF_INC zählt die Adresse in einem Burst weiter.
//
// Flugkonfiguration: Gyro ±2000 °/s, Accel ±16 g, beide 960 Hz im High-Performance-Modus,
// BDU an (Hi- und Lo-Byte aus demselben Satz), INT1 = "Gyro-Daten bereit" (push-pull, aktiv hoch,
// Default von IF_CFG). Gelesen wird ein 14-Byte-Block ab OUT_TEMP_L (0x20): Temperatur, Gyro xyz,
// Accel xyz, little-endian.
//
// Achsen: Chip-Achsen. Die Drehung Chip -> Körpersystem kommt aus der Kalibrierung ("cal axes").
//
// Der Chip hat keine Werkswerte für den Selbsttest: geprüft wird gegen die festen Grenzen aus
// dem Datenblatt (Accel 50..1700 mg bei ±4 g, Gyro 150..700 °/s bei ±2000 °/s).
#include "Imu.h"
#include "BusRevB.h"

class LSM6DSV16X : public ImuDriver {
public:
  static constexpr uint8_t WHO_AM_I_VALUE = 0x70;
  // Empfindlichkeit (DS13510 Tab. 3): ±16 g 0,488 mg/LSB, ±2000 °/s 70 mdps/LSB
  static constexpr float   ACC_G_PER_LSB    = 0.488e-3f;
  static constexpr float   GYRO_DPS_PER_LSB = 70.0e-3f;

  explicit LSM6DSV16X(BusRevB& bus) : bus_(bus) {}

  const char* name() const override { return "LSM6DSV16X"; }
  uint8_t expectedWhoAmI() const override { return WHO_AM_I_VALUE; }
  // ODR-Raster des LSM6DSV16X: 7,5 · 2^n Hz, die Stufe über 1 kHz-Nähe ist 960 Hz
  float   sampleRateHz() const override { return 960.0f; }

  // Soft-Reset, WHO_AM_I prüfen, konfigurieren, Sensoren einschalten, Konfiguration zurücklesen.
  bool    begin() override;
  uint8_t whoAmI() override;

  // true, wenn seit dem letzten Lesen ein neuer Gyro-Satz da ist (STATUS_REG.GDA)
  bool dataReady() override;
  void read(ImuSample& s) override;

  bool selfTest(ImuSelfTest& r) override;

private:
  uint8_t readReg(uint8_t reg);
  void    writeReg(uint8_t reg, uint8_t val);
  void    readRaw(int16_t raw[7]);                 // T, ax, ay, az, gx, gy, gz (wie ImuSample::raw)
  bool    averageSt(float out[3], bool gyro, int n);

  BusRevB& bus_;
  // bis 10 MHz erlaubt; 8 MHz wie beim ICM, 10 cm Leitung über den Decoder
  const SPISettings set_{8000000, MSBFIRST, SPI_MODE3};
};
