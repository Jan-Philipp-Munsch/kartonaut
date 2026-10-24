#pragma once
// INA239.h – Strom- und Spannungsmonitor INA239 an SPI1 (2S-Pfad)
//
// TI SBOSA22: SPI Modus 1, Rahmen = Befehlsbyte (Adresse << 2 | R/W)
// plus 16 oder 24 Datenbits. VBUS hängt an VSERVO, der Shunt (20 mΩ,
// Kelvin) sitzt zwischen VBAT_PROT und VBAT_MEAS. ADC-Bereich ±163,84 mV,
// also bis 8,19 A. Nur für Telemetrie und Log gedacht, nicht für die
// 100-Hz-Regelschleife (Review B6): die Wandlung mittelt über 50 ms.
//
// Rückfall bei Lieferproblemen ist der INA238 (I²C); dann wird nur diese
// Klasse ersetzt, die Schnittstelle (PowerSample) bleibt.
#include "BusRevB.h"

struct PowerSample {
  float bus_V      = 0;   // VSERVO
  float shunt_mV   = 0;
  float current_A  = 0;   // positiv = Entladen
  float power_W    = 0;
  float die_temp_C = 0;
};

class INA239 {
public:
  static constexpr uint16_t MANUFACTURER_TI = 0x5449;   // "TI"
  static constexpr uint16_t DEVICE_ID_INA239 = 0x239;   // DEVICE_ID[15:4]

  INA239(BusRevB& bus, float shunt_ohm, float max_current_a);

  bool     begin();          // Reset, IDs prüfen, SHUNT_CAL, Dauerwandlung
  uint16_t manufacturerId();
  uint16_t deviceId();       // ganzes Register, [3:0] = Revision
  void     read(PowerSample& s);

private:
  uint32_t readReg(uint8_t reg, uint8_t bytes);
  void     writeReg16(uint8_t reg, uint16_t val);

  BusRevB& bus_;
  float shunt_ohm_;
  float current_lsb_;
  const SPISettings set_{4000000, MSBFIRST, SPI_MODE1};   // bis 10 MHz
};
