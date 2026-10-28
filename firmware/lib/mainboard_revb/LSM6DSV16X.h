#pragma once
// LSM6DSV16X.h – Flug-IMU LSM6DSV16X an SPI1 (Mainboard rev B1, U4, CS Y0), ohne FIFO
//
// Entscheidung E12 (23.10.2026): LSM6DSV16X statt ICM-42688-P, gleiches Gehäuse LGA-14. Flugkonfiguration:
// Gyro ±2000 °/s, Accel ±16 g, beide 960 Hz im Hochleistungsmodus, BDU, INT1 = Gyro-Daten bereit (push-pull,
// aktiv hoch). Gelesen wird ein 14-Byte-Block ab OUT_TEMP_L (Temperatur, Gyro xyz, Accel xyz, little-endian).
// Register, Codes und Umrechnungen: Lsm6dsv16xCore.h (ohne Arduino, native Tests).
//
// Achsen: Chip-Achsen. Die Drehung Chip -> Körpersystem kommt aus der Kalibrierung (revb_test: "cal axes").
//
// Selbsttest nach AN5763: Accel bei 60 Hz / ±4 g (Antwort 50 … 1700 mg), Gyro bei 240 Hz / ±2000 °/s
// (20 … 80 °/s), je 5 Sätze mit und ohne Testsignal nach einem verworfenen Satz. Die Grenzen sind aus dem
// Datenblatt, an der Platine noch nicht bestätigt (Versuche_revB1.md V03).
#include "Imu.h"
#include "BusRevB.h"
#include "Lsm6dsv16xCore.h"

class LSM6DSV16X : public ImuDriver {
public:
  explicit LSM6DSV16X(BusRevB& bus) : bus_(bus) {}

  const char* name() const override { return "LSM6DSV16X"; }
  uint8_t expectedWhoAmI() const override { return lsm6dsv16x::WHO_AM_I_VALUE; }
  float   sampleRateHz() const override { return lsm6dsv16x::odrHz(lsm6dsv16x::FLIGHT_ODR); }

  // Soft-Reset, WHO_AM_I prüfen, Flugkonfiguration schreiben und zurücklesen, Sensoren einschalten.
  bool begin() override;
  uint8_t whoAmI() override;

  // true, wenn ein neuer Gyro-Satz vorliegt (STATUS_REG GDA)
  bool dataReady() override;
  void read(ImuSample& s) override;

  bool selfTest(ImuSelfTest& r) override;

private:
  uint8_t readReg(uint8_t reg);
  void    writeReg(uint8_t reg, uint8_t val);
  void    readRaw(int16_t raw[7]);
  bool    average(float acc_g[3], float gyro_dps[3], lsm6dsv16x::FsXl fs_xl, lsm6dsv16x::FsG fs_g, uint8_t ready_bit);

  BusRevB& bus_;
  // Datenblatt: SPI bis 10 MHz, CPOL = CPHA = 1; 8 MHz ist auf 10 cm Leitung über den Decoder sicher
  const SPISettings set_{8000000, MSBFIRST, SPI_MODE3};
};
