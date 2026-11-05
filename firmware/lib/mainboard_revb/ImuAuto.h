#pragma once
// ImuAuto.h – wählt beim Start den IMU-Treiber nach WHO_AM_I
//
// rev B1 trägt den LSM6DSV16X (WHO_AM_I 0x70 in Register 0x0F), ältere Platinen den
// ICM-42688-P (0x47 in Register 0x75). Beide Abfragen sind für den jeweils anderen Chip
// harmlos (reservierte bzw. Nur-Lese-Register). Antwortet keiner, bleibt der LSM6DSV16X
// gewählt, damit die Meldung "0x.. soll 0x70" auf das bestückte Teil zeigt.
//
// ImuAuto ist selbst ein ImuDriver und reicht alles an den gewählten Treiber weiter; die
// Programme halten wie bisher eine Referenz "ImuDriver& imu".
#include "Imu.h"
#include "LSM6DSV16X.h"
#include "ICM42688.h"

class ImuAuto : public ImuDriver {
public:
  explicit ImuAuto(BusRevB& bus) : lsm_(bus), icm_(bus) {}

  // Kennung lesen und Treiber wählen; true, wenn einer der beiden Chips antwortet
  bool detect() {
    if (lsm_.whoAmI() == LSM6DSV16X::WHO_AM_I_VALUE) { act_ = &lsm_; return true; }
    if (icm_.whoAmI() == ICM42688::WHO_AM_I_VALUE)   { act_ = &icm_; return true; }
    act_ = &lsm_;
    return false;
  }

  const char* name() const override { return act_->name(); }
  uint8_t expectedWhoAmI() const override { return act_->expectedWhoAmI(); }
  float   sampleRateHz() const override { return act_->sampleRateHz(); }

  bool    begin() override { detect(); return act_->begin(); }
  uint8_t whoAmI() override { detect(); return act_->whoAmI(); }
  bool    dataReady() override { return act_->dataReady(); }
  void    read(ImuSample& s) override { act_->read(s); }
  bool    selfTest(ImuSelfTest& r) override { return act_->selfTest(r); }

private:
  LSM6DSV16X lsm_;
  ICM42688   icm_;
  ImuDriver* act_ = &lsm_;
};
