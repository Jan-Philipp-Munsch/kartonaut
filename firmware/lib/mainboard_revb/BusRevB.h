#pragma once
// BusRevB.h – SPI1 mit dem CS-Decoder 74HC138 und der Analogmux 74HC4051
//
// Beide Bausteine teilen sich die drei Select-Leitungen SEL0..2. Der
// Decoder ist nur bei CS_EN = tief aktiv; die Mux ist immer an. Daraus
// folgen zwei Regeln für die ganze Firmware:
//   1. SEL wird nur bei CS_EN = hoch umgeschaltet, sonst ist für einige
//      Nanosekunden ein falscher Chip ausgewählt.
//   2. Kein SPI-Zugriff aus einer ISR. Eine Analogmessung zwischen
//      select() und deselect() würde sonst den Chip wechseln. Der INT1
//      der IMU setzt nur ein Flag, gelesen wird in der Schleife.
#include <Arduino.h>
#include <SPI.h>
#include "BoardRevB.h"

class BusRevB {
public:
  // Pins setzen (CS_EN hoch, SEL = 7), SPI1 auf 26/27/39 starten, ADC 12 bit
  void begin();

  SPIClass& spi() { return SPI1; }

  // Ein Gerät auswählen bzw. alle abwählen. Ohne beginTransaction() davor
  // sind Takt und Modus die des letzten Geräts.
  void select(revb::Cs cs);
  void deselect();

  // Register-Hilfen für Geräte mit "Adresse | 0x80 = lesen" (ICM, BMP).
  // dummy = Anzahl Füllbytes zwischen Adresse und Daten (BMP390: 1).
  void readRegs(revb::Cs cs, const SPISettings& set, uint8_t reg, uint8_t* buf, size_t n, uint8_t dummy = 0);
  void writeReg(revb::Cs cs, const SPISettings& set, uint8_t reg, uint8_t val);

  // Spannung am ADC-Eingang (0..3,3 V) bzw. vor dem 100k/33k-Teiler.
  // Darf nicht zwischen select() und deselect() aufgerufen werden.
  float readMuxV(revb::Mux ch);
  float readMuxInputV(revb::Mux ch) { return readMuxV(ch) * revb::DIVIDER_RATIO; }

private:
  void setSel(uint8_t n);
  bool selected_ = false;
};
