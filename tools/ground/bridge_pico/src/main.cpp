// main.cpp – Funkbrücke der Bodenstation: Raspberry Pi Pico mit E22-400T22S (Plan Bordzündung §5)
//
//   USB (Laptop, tools/ground/launch.py) -> Funk: nur vollständige, geprüfte Rahmen, unverändert. Bytes außerhalb
//              eines Rahmens werden verworfen. BRIDGE_CONFIG (0x70) geht nicht über Funk: die Brücke stellt
//              dann ihr E22 auf die Werte aus firmware/src/Config.h (E22Config.h) und antwortet mit BRIDGE_ACK.
//   Funk -> USB: jedes Byte unverändert, auch das RSSI-Byte, das das E22 an jedes Paket hängt.
//   LED:  Dauerlicht, wenn in den letzten 2 s ein gültiger Rahmen von der Rakete kam; sonst Blinken.
//
// Verdrahtung (README.md): E22 TXD -> GP5 (UART1 RX), E22 RXD -> GP4 (UART1 TX), M0 -> GP6, M1 -> GP7,
// AUX -> GP8, VCC -> 3V3 OUT, GND -> GND.
#include <Arduino.h>
#include "Config.h"
#include "E22Config.h"
#include "Telemetry.h"

constexpr pin_size_t PIN_E22_RXD = 4;   // Pico TX (UART1) -> E22 RXD
constexpr pin_size_t PIN_E22_TXD = 5;   // E22 TXD -> Pico RX (UART1)
constexpr pin_size_t PIN_E22_M0  = 6;
constexpr pin_size_t PIN_E22_M1  = 7;
constexpr pin_size_t PIN_E22_AUX = 8;   // hoch = bereit
constexpr uint32_t   LINK_FRESH_MS = 2000;
constexpr uint32_t   CONFIG_BAUD = 9600; // Konfigurationsmodus des E22 spricht immer 9600 Bd

static SerialUART& E22 = Serial2;       // UART1
static tlm::Parser fromUsb, fromRadio;
static uint32_t last_frame_ms = 0;      // 0 = noch nie

static bool waitAux(uint32_t timeout_ms) {
  const uint32_t t0 = millis();
  while (!digitalRead(PIN_E22_AUX)) {
    if (millis() - t0 > timeout_ms) return false;
    delay(1);
  }
  return true;
}

static void setMode(bool config) {
  digitalWrite(PIN_E22_M0, LOW);
  digitalWrite(PIN_E22_M1, config ? HIGH : LOW);
  delay(10);
  waitAux(500);
  delay(10);                            // Ebyte: nach AUX hoch noch ~2 ms bis zum Moduswechsel
}

static bool readReply(uint8_t* buf, size_t n, uint32_t timeout_ms) {
  size_t got = 0;
  const uint32_t t0 = millis();
  while (got < n && millis() - t0 < timeout_ms) {
    if (E22.available()) buf[got++] = (uint8_t)E22.read();
  }
  return got == n;
}

static void sendToUsb(uint8_t type, const void* payload, size_t n) {
  uint8_t buf[tlm::MAX_PAYLOAD + tlm::OVERHEAD];
  const size_t len = tlm::encode(type, (const uint8_t*)payload, n, buf, sizeof buf);
  if (len) Serial.write(buf, len);
}

// Register lesen, bei Abweichung dauerhaft schreiben (C0), Ergebnis an den Laptop
static void configure() {
  tlm::BridgeAckPayload ack{};
  uint8_t want[e22::REG_COUNT];
  e22::wantedRegs(want, true);          // RSSI-Byte an: launch.py zeigt die Empfangsstärke
  if (RADIO_BAUD != (long)CONFIG_BAUD) E22.begin(CONFIG_BAUD);
  setMode(true);
  while (E22.available()) E22.read();
  const uint8_t rd[3] = {0xC1, 0x00, e22::REG_COUNT};
  E22.write(rd, sizeof rd);
  uint8_t rep[3 + e22::REG_COUNT];
  bool ok = readReply(rep, sizeof rep, 300) && rep[0] == 0xC1;
  ack.result = ok ? tlm::BRIDGE_OK : tlm::BRIDGE_NO_REPLY;
  if (ok && memcmp(rep + 3, want, e22::REG_COUNT) != 0) {
    uint8_t wr[3 + e22::REG_COUNT] = {0xC0, 0x00, e22::REG_COUNT};
    memcpy(wr + 3, want, e22::REG_COUNT);
    while (E22.available()) E22.read();
    E22.write(wr, sizeof wr);
    ok = readReply(rep, sizeof rep, 500) && rep[0] == 0xC1 && memcmp(rep + 3, want, e22::REG_COUNT) == 0;
    ack.result = ok ? tlm::BRIDGE_OK : tlm::BRIDGE_WRITE_FAILED;
  }
  if (ack.result != tlm::BRIDGE_NO_REPLY) memcpy(ack.regs, rep + 3, e22::REG_COUNT);
  setMode(false);
  if (RADIO_BAUD != (long)CONFIG_BAUD) E22.begin(RADIO_BAUD);
  while (E22.available()) E22.read();
  sendToUsb(tlm::BRIDGE_ACK, &ack, sizeof ack);
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_E22_M0, OUTPUT);
  pinMode(PIN_E22_M1, OUTPUT);
  pinMode(PIN_E22_AUX, INPUT);
  Serial.begin(115200);                 // USB-CDC, Baudrate ohne Bedeutung
  E22.setTX(PIN_E22_RXD);
  E22.setRX(PIN_E22_TXD);
  E22.begin(RADIO_BAUD);
  setMode(false);                       // M0 = M1 = 0: transparent
}

void loop() {
  // Laptop -> Funk: nur ganze Rahmen
  while (Serial.available()) {
    if (!fromUsb.feed((uint8_t)Serial.read())) continue;
    if (fromUsb.type() == tlm::BRIDGE_CONFIG) {
      configure();
      continue;
    }
    uint8_t buf[tlm::MAX_PAYLOAD + tlm::OVERHEAD];
    const size_t len = tlm::encode(fromUsb.type(), fromUsb.payload(), fromUsb.length(), buf, sizeof buf);
    if (len) E22.write(buf, len);
  }

  // Funk -> Laptop: unverändert
  uint8_t rx[64];
  size_t n = 0;
  while (E22.available() && n < sizeof rx) {
    const uint8_t b = (uint8_t)E22.read();
    rx[n++] = b;
    if (fromRadio.feed(b)) last_frame_ms = millis() ? millis() : 1;
  }
  if (n) Serial.write(rx, n);

  const bool fresh = last_frame_ms != 0 && millis() - last_frame_ms < LINK_FRESH_MS;
  digitalWrite(LED_BUILTIN, fresh ? HIGH : ((millis() / 250) % 2 ? HIGH : LOW));
}
