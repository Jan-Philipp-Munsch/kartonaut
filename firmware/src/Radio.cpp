#include "Radio.h"
#include <string.h>

static uint8_t serial_tx_mem[512];   // Serial8 hat ab Werk nur 40 Byte Sendepuffer

void Radio::begin() {
  RADIO_SERIAL.addMemoryForWrite(serial_tx_mem, sizeof serial_tx_mem);
  RADIO_SERIAL.begin(RADIO_BAUD);
  if (PIN_LORA_M0 >= 0) { digitalWrite(PIN_LORA_M0, LOW); pinMode(PIN_LORA_M0, OUTPUT); }
  if (PIN_LORA_M1 >= 0) { digitalWrite(PIN_LORA_M1, LOW); pinMode(PIN_LORA_M1, OUTPUT); }
  if (PIN_LORA_AUX >= 0) pinMode(PIN_LORA_AUX, INPUT);
  if (PIN_LORA_NRST >= 0) pinMode(PIN_LORA_NRST, INPUT);   // Open-Drain, Pull-up hält hoch
}

bool Radio::auxReady() const {
  if (PIN_LORA_AUX < 0) return true;
  return digitalRead(PIN_LORA_AUX) == HIGH;
}

bool Radio::e22ReadParams(uint8_t out[9]) {
  while (RADIO_SERIAL.available()) RADIO_SERIAL.read();
  const uint8_t cmd[3] = {0xC1, 0x00, 0x09};
  RADIO_SERIAL.write(cmd, 3);
  uint8_t r[12];
  size_t n = 0;
  const uint32_t t0 = millis();
  while (n < sizeof r && millis() - t0 < 300) {
    if (RADIO_SERIAL.available()) r[n++] = uint8_t(RADIO_SERIAL.read());
  }
  if (n != sizeof r || r[0] != 0xC1) return false;
  for (int i = 0; i < 9; ++i) out[i] = r[3 + i];
  return true;
}

bool Radio::configure() {
  if (!RADIO_IS_E22) { configured_ = true; return true; }

  // Register 00H..08H (Ebyte E22-400T22S, Benutzerhandbuch §7):
  //   ADDH ADDL NETID REG0 REG1 REG2 REG3 CRYPT_H CRYPT_L
  //   REG0: UART-Baud [7:5] (011 = 9600), Parität [4:3] (00 = 8N1), Luftrate [2:0]
  //   REG1: Paketgröße [7:6] (00 = 240 B), RSSI-Rauschen [5], Leistung [1:0] (00 = 22 dBm)
  //   REG2: Kanal (410,125 MHz + Kanal MHz)
  //   REG3: RSSI-Byte [7], feste Adressierung [6] (0 = transparent), Relais [5], LBT [4], WOR [3], WOR-Zyklus [2:0]
  const uint8_t want[9] = {
    uint8_t(E22_ADDRESS >> 8), uint8_t(E22_ADDRESS & 0xFF), E22_NETID,
    uint8_t((0b011 << 5) | (0b00 << 3) | (E22_AIR_RATE & 0x07)),
    uint8_t((0b00 << 6) | (E22_POWER & 0x03)),
    E22_CHANNEL,
    uint8_t(0b011),      // WOR-Zyklus 2000 ms (Vorgabe), sonst alles aus
    0x00, 0x00,
  };

  // Modus 2 (Konfiguration): M1 = 1, M0 = 0; UART dort fest 9600 8N1
  digitalWrite(PIN_LORA_M0, LOW);
  digitalWrite(PIN_LORA_M1, HIGH);
  delay(50);
  uint32_t t0 = millis();
  while (!auxReady() && millis() - t0 < 1000) {}

  uint8_t have[9];
  bool ok = e22ReadParams(have);
  if (ok && memcmp(have, want, 9) != 0) {
    uint8_t cmd[12] = {0xC0, 0x00, 0x09};
    memcpy(cmd + 3, want, 9);
    RADIO_SERIAL.write(cmd, sizeof cmd);
    delay(100);
    while (RADIO_SERIAL.available()) RADIO_SERIAL.read();
    ok = e22ReadParams(have) && memcmp(have, want, 9) == 0;
  }

  // zurück in Modus 0 (transparent)
  digitalWrite(PIN_LORA_M1, LOW);
  t0 = millis();
  while (!auxReady() && millis() - t0 < 1000) {}
  delay(20);
  while (RADIO_SERIAL.available()) RADIO_SERIAL.read();
  configured_ = ok;
  return ok;
}

bool Radio::send(uint8_t type, const void* payload, uint8_t len) {
  const size_t n = kn_encode(type, payload, len, txbuf_, sizeof txbuf_);
  if (n == 0) { ++dropped_; return false; }
  if (!auxReady() || RADIO_SERIAL.availableForWrite() < int(n)) { ++dropped_; return false; }
  RADIO_SERIAL.write(txbuf_, n);
  ++sent_;
  return true;
}

bool Radio::poll(KnCommand& cmd) {
  bool got = false;
  int guard = 64;   // nie länger als nötig in der Schleife bleiben
  while (RADIO_SERIAL.available() && guard-- > 0) {
    if (parser_.feed(uint8_t(RADIO_SERIAL.read())) && parser_.type() == KN_MSG_CMD && parser_.get(cmd)) {
      got = true;
      break;
    }
  }
  return got;
}
