#pragma once
// Imu.h – schmale Schnittstelle der Flug-IMU
//
// rev B1 trägt seit 23.10.2026 den LSM6DSV16X (LSM6DSV16X.h); der Treiber für
// den ICM-42688-P (ICM42688.h, gleiches Gehäuse LGA-14) bleibt für ältere
// Platinen. Alles außerhalb des Treibers spricht nur diese Schnittstelle:
// begin, whoAmI, dataReady, read, selfTest. ImuAuto.h wählt den Treiber
// beim Start nach WHO_AM_I; Selbsttest, Kalibrierung und Flug bleiben gleich.
//
// Werte in Chip-Achsen. Die Zuordnung zum Raketenkörper kommt aus der
// Kalibrierung (CalData::imu_axis_map/sign), nicht aus dem Treiber.
#include <Arduino.h>

struct ImuSample {
  float acc_ms2[3];    // Beschleunigung (spezifische Kraft), Chip-Achsen
  float gyro_dps[3];   // Drehrate, Chip-Achsen
  float temp_c;
  int16_t raw[7];      // T, ax, ay, az, gx, gy, gz
};

struct ImuSelfTest {
  bool  ok = false;            // Gesamtergebnis
  bool  gyro_ok = false, acc_ok = false;
  float gyro_resp_dps[3] = {0, 0, 0};   // Antwort des Selbsttests je Achse
  float acc_resp_g[3]    = {0, 0, 0};
  float gyro_ratio[3]    = {0, 0, 0};   // Antwort / Werkswert (0 = kein Werkswert)
  float acc_ratio[3]     = {0, 0, 0};
  float gyro_offset_dps[3] = {0, 0, 0}; // Nullpunkt in Ruhe während des Tests
  // Feste Grenzen für |Antwort|, wenn der Chip keinen Werkswert hat (LSM6DSV16X); 0 = nicht benutzt
  float gyro_min_dps = 0, gyro_max_dps = 0;
  float acc_min_g = 0, acc_max_g = 0;
};

class ImuDriver {
public:
  virtual ~ImuDriver() = default;
  virtual const char* name() const = 0;
  virtual uint8_t     expectedWhoAmI() const = 0;
  virtual float       sampleRateHz() const = 0;

  // Reset, Kennung prüfen, Flugkonfiguration laden, Sensoren einschalten.
  virtual bool    begin() = 0;
  virtual uint8_t whoAmI() = 0;

  // true, wenn seit dem letzten Lesen ein neuer Satz da ist
  virtual bool dataReady() = 0;
  virtual void read(ImuSample& s) = 0;

  // Werksselbsttest (Chip in Ruhe). Konfiguriert den Chip um und ruft
  // danach begin(); die Flugkonfiguration steht anschließend wieder.
  virtual bool selfTest(ImuSelfTest& r) = 0;
};
