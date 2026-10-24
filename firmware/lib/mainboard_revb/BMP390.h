#pragma once
// BMP390.h – Barometer BMP390 (oder pinkompatibel BMP388) an SPI1
//
// Registerkarte und Kompensation: Bosch BST-BMP390-DS002, §8.4 und §9
// (Gleitkommaformeln). SPI-Lesezugriffe haben nach der Adresse ein
// Füllbyte. Nach dem Einschalten ist der Chip im I²C-Modus, die erste
// fallende CSB-Flanke schaltet ihn auf SPI; begin() liest dafür einmal blind.
//
// Einstellung nach der Bosch-Empfehlung für Drohnen: Druck ×8, Temperatur
// ×1, IIR-Koeffizient 3, 50 Hz im Normal-Modus.
#include "BusRevB.h"

class BMP390 {
public:
  static constexpr uint8_t CHIP_ID_BMP390 = 0x60;
  static constexpr uint8_t CHIP_ID_BMP388 = 0x50;

  BMP390(BusRevB& bus, revb::Cs cs) : bus_(bus), cs_(cs) {}

  bool    begin();                 // erkennt BMP390 und BMP388
  uint8_t chipId() const { return chip_id_; }

  // Liest den letzten Messwert; false, wenn noch keine neue Messung vorliegt
  bool read(float& pressure_pa, float& temp_c);

  // Barometrische Höhe über dem Referenzdruck p0 (Normatmosphäre)
  static float altitude_m(float p_pa, float p0_pa);

private:
  uint8_t readReg(uint8_t reg);
  void    readRegs(uint8_t reg, uint8_t* buf, size_t n);
  void    writeReg(uint8_t reg, uint8_t val);
  bool    readCalibration();

  BusRevB& bus_;
  revb::Cs cs_;
  uint8_t  chip_id_ = 0;
  const SPISettings set_{8000000, MSBFIRST, SPI_MODE0};   // bis 10 MHz

  // Kalibrierwerte als Gleitkomma (Datenblatt §9.1)
  double t1_, t2_, t3_;
  double p1_, p2_, p3_, p4_, p5_, p6_, p7_, p8_, p9_, p10_, p11_;
};
