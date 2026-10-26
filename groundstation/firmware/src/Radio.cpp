#include "Radio.h"
#include "Config.h"

namespace radio {

static HardwareSerial& E22 = Serial1;
static Status st;
static proto::Parser parser;
static CommandCallback callback = nullptr;

struct Pending {
  uint8_t  cmd;
  uint8_t  seq;
  uint8_t  retriesLeft;
  bool     sentOnce;
  uint32_t nextTxMs;
};
static constexpr int QUEUE_LEN = 4;
static Pending queue[QUEUE_LEN];
static int queueCount = 0;
static uint8_t cmdSeq = 0;

// ----- E22-Konfiguration -----
// Register 00H..08H: ADDH, ADDL, NETID, REG0, REG1, REG2 (Kanal), REG3, CRYPT_H, CRYPT_L.
// REG0: UART 9600 (011 << 5), 8N1 (00 << 3), Luftrate (Bits 2..0)
// REG1: Teilpaket 240 Byte (00 << 6), Störpegel-RSSI aus, Sendeleistung (Bits 1..0)
// REG3: kein RSSI-Byte, transparent, kein Relais, kein LBT, WOR 2000 ms (Vorgabe)
// Bitlagen nach Ebyte-Handbuch E22-400T22S; vor dem ersten Einsatz gegen das
// Datenblatt der gelieferten Version prüfen.
static void wantedRegs(uint8_t r[9]) {
  r[0] = E22_ADDH;
  r[1] = E22_ADDL;
  r[2] = E22_NETID;
  r[3] = uint8_t((0b011 << 5) | (0b00 << 3) | (E22_AIR_RATE & 0x07));
  r[4] = uint8_t((0b00 << 6) | (E22_POWER & 0x03));
  r[5] = E22_CHANNEL;
  r[6] = 0x03;
  r[7] = 0x00;
  r[8] = 0x00;
}

static bool waitAux(uint32_t timeoutMs) {
  uint32_t t0 = millis();
  while (!digitalRead(PIN_E22_AUX)) {
    if (millis() - t0 > timeoutMs) return false;
    delay(1);
  }
  return true;
}

static void setMode(bool config) {
  // Normalbetrieb M0 = 0, M1 = 0; Konfiguration M0 = 0, M1 = 1
  digitalWrite(PIN_E22_M0, LOW);
  digitalWrite(PIN_E22_M1, config ? HIGH : LOW);
  delay(10);
  waitAux(500);
  delay(10);   // Ebyte: nach AUX high noch ~2 ms bis zum Moduswechsel
}

static bool readReply(uint8_t* buf, size_t n, uint32_t timeoutMs) {
  size_t got = 0;
  uint32_t t0 = millis();
  while (got < n && millis() - t0 < timeoutMs) {
    if (E22.available()) buf[got++] = uint8_t(E22.read());
  }
  return got == n;
}

static bool configure() {
  setMode(true);
  while (E22.available()) E22.read();

  uint8_t want[9];
  wantedRegs(want);

  // Lesen: C1 00 09 -> Antwort C1 00 09 + 9 Register
  const uint8_t rd[3] = {0xC1, 0x00, 0x09};
  E22.write(rd, 3);
  uint8_t rep[12];
  bool ok = readReply(rep, 12, 300) && rep[0] == 0xC1;
  bool same = ok && memcmp(rep + 3, want, 9) == 0;

  if (!same) {
    // Schreiben (dauerhaft): C0 00 09 + 9 Register -> Antwort C1 00 09 + Register
    uint8_t wr[12] = {0xC0, 0x00, 0x09};
    memcpy(wr + 3, want, 9);
    while (E22.available()) E22.read();
    E22.write(wr, 12);
    ok = readReply(rep, 12, 500) && rep[0] == 0xC1 && memcmp(rep + 3, want, 9) == 0;
    Serial.printf("[E22] Register %s\n", ok ? "neu geschrieben" : "FEHLER beim Schreiben");
  } else {
    Serial.println("[E22] Register stimmen");
  }

  setMode(false);
  return ok;
}

bool begin(CommandCallback cb) {
  callback = cb;
  pinMode(PIN_E22_M0, OUTPUT);
  pinMode(PIN_E22_M1, OUTPUT);
  pinMode(PIN_E22_AUX, INPUT);
  E22.begin(E22_UART_BAUD, SERIAL_8N1, PIN_E22_TXD, PIN_E22_RXD);
  st.configured = configure();
  return st.configured;
}

// ----- Kommandos -----
bool send(proto::Command cmd) {
  uint8_t retries = CMD_RETRIES;
  if (cmd == proto::CMD_ABORT) {
    queueCount = 0;               // Abbruch hat Vorrang vor allem anderen
    retries = ABORT_RETRIES;
  } else {
    for (int i = 0; i < queueCount; i++)
      if (queue[i].cmd == cmd) return true;   // schon unterwegs
  }
  if (queueCount >= QUEUE_LEN) return false;
  queue[queueCount++] = {uint8_t(cmd), ++cmdSeq, retries, false, 0};
  return true;
}

static void popFront() {
  for (int i = 1; i < queueCount; i++) queue[i - 1] = queue[i];
  if (queueCount) queueCount--;
}

static void transmitHead(uint32_t now) {
  Pending& p = queue[0];
  if (!digitalRead(PIN_E22_AUX)) return;   // Sendepuffer des Moduls noch belegt
  proto::CommandRaw c{p.cmd, p.seq};
  uint8_t frame[6 + sizeof(c)];
  size_t n = proto::encode(proto::T_COMMAND, &c, sizeof(c), frame);
  E22.write(frame, n);
  st.txFrames++;
  p.sentOnce = true;
  p.retriesLeft--;
  p.nextTxMs = now + CMD_RETRY_MS;
}

static void serviceQueue(uint32_t now, bool slotOpen) {
  if (!queueCount) return;
  Pending& p = queue[0];
  if (!p.sentOnce) {
    // Erste Sendung direkt nach einem Telemetrierahmen (die Rakete hört dann
    // zu), oder spätestens nach CMD_SLOT_WAIT_MS, falls keine Telemetrie kommt.
    if (p.nextTxMs == 0) p.nextTxMs = now + CMD_SLOT_WAIT_MS;
    if (slotOpen || int32_t(now - p.nextTxMs) >= 0) transmitHead(now);
    return;
  }
  if (int32_t(now - p.nextTxMs) < 0) return;
  if (p.retriesLeft == 0) {
    uint8_t cmd = p.cmd;
    popFront();
    if (callback) callback(cmd, true, 0);
    return;
  }
  transmitHead(now);
}

// ----- Empfang -----
static bool handleFrame(uint32_t now) {
  const uint8_t* pl = parser.payload();
  switch (parser.type()) {
    case proto::T_TELEMETRY: {
      if (parser.length() != sizeof(proto::TelemetryRaw)) return false;
      proto::TelemetryRaw tr;
      memcpy(&tr, pl, sizeof(tr));
      proto::decodeTelemetry(tr, st.tlm);
      st.lastTelemetryMs = now;
      st.haveTelemetry = true;
      return true;   // Sendefenster für Kommandos
    }
    case proto::T_GPS: {
      if (parser.length() != sizeof(proto::GpsRaw)) return false;
      proto::GpsRaw gr;
      memcpy(&gr, pl, sizeof(gr));
      proto::decodeGps(gr, st.gps);
      st.lastGpsMs = now;
      return false;
    }
    case proto::T_ACK: {
      if (parser.length() != sizeof(proto::AckRaw)) return false;
      proto::AckRaw a;
      memcpy(&a, pl, sizeof(a));
      if (queueCount && queue[0].seq == a.seq && queue[0].cmd == a.cmd) {
        popFront();
        if (callback) callback(a.cmd, false, a.result);
      }
      return false;
    }
    default:
      return false;
  }
}

void update() {
  uint32_t now = millis();
  bool slot = false;
  while (E22.available()) {
    if (parser.feed(uint8_t(E22.read()))) slot |= handleFrame(now);
  }
  st.frames = parser.frames;
  st.crcErrors = parser.crcErrors;
  serviceQueue(now, slot);
}

uint32_t telemetryAgeMs() {
  return st.haveTelemetry ? millis() - st.lastTelemetryMs : UINT32_MAX;
}

const Status& status() { return st; }

} // namespace radio
