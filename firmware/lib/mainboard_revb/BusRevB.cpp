#include "BusRevB.h"

using namespace revb;

void BusRevB::begin() {
  // Zuerst abwählen: der Pull-up hält CS_EN beim Boot hoch, das bleibt so.
  digitalWrite(PIN_CS_EN, HIGH);
  pinMode(PIN_CS_EN, OUTPUT);
  pinMode(PIN_SEL0, OUTPUT);
  pinMode(PIN_SEL1, OUTPUT);
  pinMode(PIN_SEL2, OUTPUT);
  setSel(uint8_t(Cs::NONE));

  // SPI1-MISO liegt ab Werk auf Pin 1 (dort hängt das GPS). Vor begin() umlegen.
  SPI1.setMISO(PIN_SPI1_MISO);
  SPI1.setMOSI(PIN_SPI1_MOSI);
  SPI1.setSCK(PIN_SPI1_SCK);
  SPI1.begin();

  analogReadResolution(12);
  analogReadAveraging(4);
}

void BusRevB::setSel(uint8_t n) {
  digitalWriteFast(PIN_SEL0, (n >> 0) & 1);
  digitalWriteFast(PIN_SEL1, (n >> 1) & 1);
  digitalWriteFast(PIN_SEL2, (n >> 2) & 1);
}

void BusRevB::select(Cs cs) {
  digitalWriteFast(PIN_CS_EN, HIGH);   // Regel 1: erst abwählen, dann umschalten
  setSel(uint8_t(cs));
  delayNanoseconds(50);                // 74HC138 bei 3,3 V: tpd < 40 ns
  digitalWriteFast(PIN_CS_EN, LOW);
  selected_ = true;
}

void BusRevB::deselect() {
  digitalWriteFast(PIN_CS_EN, HIGH);
  selected_ = false;
}

void BusRevB::readRegs(Cs cs, const SPISettings& set, uint8_t reg, uint8_t* buf, size_t n, uint8_t dummy) {
  SPI1.beginTransaction(set);
  select(cs);
  SPI1.transfer(uint8_t(reg | 0x80));
  for (uint8_t i = 0; i < dummy; ++i) SPI1.transfer(0x00);
  for (size_t i = 0; i < n; ++i) buf[i] = SPI1.transfer(0x00);
  deselect();
  SPI1.endTransaction();
}

void BusRevB::writeReg(Cs cs, const SPISettings& set, uint8_t reg, uint8_t val) {
  SPI1.beginTransaction(set);
  select(cs);
  SPI1.transfer(uint8_t(reg & 0x7F));
  SPI1.transfer(val);
  deselect();
  SPI1.endTransaction();
}

float BusRevB::readMuxV(Mux ch) {
  if (selected_) return NAN;           // Regel 2
  setSel(uint8_t(ch));
  // Der 100-nF-Kondensator am Teiler liefert die Ladung, die Mux hat ca. 100 Ω.
  // Kurz warten und die erste Wandlung verwerfen, sie sieht noch den alten Kanal.
  delayMicroseconds(5);
  (void)analogRead(PIN_MUX_OUT);
  const int raw = analogRead(PIN_MUX_OUT);
  return raw * (ADC_VREF_V / 4095.0f);
}
