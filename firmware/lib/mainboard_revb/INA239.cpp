#include "INA239.h"

namespace {
constexpr uint8_t CONFIG     = 0x00;   // bit15 RST, bit4 ADCRANGE
constexpr uint8_t ADC_CONFIG = 0x01;
constexpr uint8_t SHUNT_CAL  = 0x02;
constexpr uint8_t VSHUNT     = 0x04;   // 5 µV/LSB bei ADCRANGE = 0
constexpr uint8_t VBUS       = 0x05;   // 3,125 mV/LSB
constexpr uint8_t DIETEMP    = 0x06;   // [15:4], 125 m°C/LSB
constexpr uint8_t CURRENT    = 0x07;   // × CURRENT_LSB
constexpr uint8_t POWER      = 0x08;   // 24 bit, × 0,2 · CURRENT_LSB
constexpr uint8_t MANUFACTURER_ID = 0x3E;
constexpr uint8_t DEVICE_ID  = 0x3F;
}  // namespace

INA239::INA239(BusRevB& bus, float shunt_ohm, float max_current_a)
    : bus_(bus), shunt_ohm_(shunt_ohm), current_lsb_(max_current_a / 32768.0f) {}

uint32_t INA239::readReg(uint8_t reg, uint8_t bytes) {
  SPIClass& spi = bus_.spi();
  spi.beginTransaction(set_);
  bus_.select(revb::Cs::INA);
  spi.transfer(uint8_t((reg << 2) | 0x01));
  uint32_t v = 0;
  for (uint8_t i = 0; i < bytes; ++i) v = (v << 8) | spi.transfer(0x00);
  bus_.deselect();
  spi.endTransaction();
  return v;
}

void INA239::writeReg16(uint8_t reg, uint16_t val) {
  SPIClass& spi = bus_.spi();
  spi.beginTransaction(set_);
  bus_.select(revb::Cs::INA);
  spi.transfer(uint8_t(reg << 2));
  spi.transfer(uint8_t(val >> 8));
  spi.transfer(uint8_t(val));
  bus_.deselect();
  spi.endTransaction();
}

uint16_t INA239::manufacturerId() { return uint16_t(readReg(MANUFACTURER_ID, 2)); }
uint16_t INA239::deviceId()       { return uint16_t(readReg(DEVICE_ID, 2)); }

bool INA239::begin() {
  writeReg16(CONFIG, 0x8000);                 // Reset
  delay(2);
  if (manufacturerId() != MANUFACTURER_TI) return false;
  if ((deviceId() >> 4) != DEVICE_ID_INA239) return false;

  writeReg16(CONFIG, 0x0000);                 // ADCRANGE 0: ±163,84 mV
  // SHUNT_CAL = 819,2·10^6 · CURRENT_LSB · R_SHUNT (SBOSA22 Gl. 1), 15 bit
  const float cal = 819.2e6f * current_lsb_ * shunt_ohm_;
  writeReg16(SHUNT_CAL, uint16_t(constrain(cal, 1.0f, 32767.0f) + 0.5f));
  // Dauerwandlung Bus, Shunt, Temperatur (0xF), je 1052 µs, 16-fach gemittelt: ca. 20 Hz
  writeReg16(ADC_CONFIG, 0xFB6A);
  return readReg(ADC_CONFIG, 2) == 0xFB6A;
}

void INA239::read(PowerSample& s) {
  s.shunt_mV   = int16_t(readReg(VSHUNT, 2)) * 0.005f;
  s.bus_V      = int16_t(readReg(VBUS, 2)) * 0.003125f;
  s.current_A  = int16_t(readReg(CURRENT, 2)) * current_lsb_;
  s.power_W    = readReg(POWER, 3) * 0.2f * current_lsb_;
  s.die_temp_C = (int16_t(readReg(DIETEMP, 2)) >> 4) * 0.125f;
}
