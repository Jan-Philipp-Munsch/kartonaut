#pragma once
// Telemetry.h – Funkprotokoll Rakete <-> Bodenstation (Schnittstelle S3, Plan 22.10.2026 B4)
//
// Diese Datei ist die Definition des Protokolls; die Bodenstation (kartonaut-ground,
// groundstation/) übernimmt sie unverändert. Kein Arduino.
//
// Rahmen (alle Mehrbyte-Werte little-endian):
//   0xA5 0x5A | Typ (1) | Länge der Nutzlast (1) | Nutzlast (0..64) | CRC-16/CCITT (2)
//   CRC über Typ, Länge und Nutzlast (Crc16.h, Start 0xFFFF).
//
// Rakete -> Boden
//   TLM  0x01  10 Hz, 16 Byte: Flugzustand, Zeit, Höhe, Steiggeschwindigkeit, Lage, Kardan,
//              beide Akkus, Flags (ARM, Durchgang, Log). Statt der Quaternion aus dem
//              Schnittstellen-Vorschlag gehen die beiden Kippwinkel und der Rollwinkel über
//              Funk (3 statt 8 Byte); damit passt der Rahmen bei 2,4 kbit/s Luftrate in
//              10 Hz (22 Byte Rahmen = 2200 bit/s).
//   EVT  0x02  bei jedem Zustandsübergang: Zeit, von, nach, Grund
//   ACK  0x10  Antwort auf jedes Kommando: Kommandotyp, Folgenummer, Ergebnis, Zustand
//   GPS  0x03  1 Hz, später (Breite, Länge, Höhe, Fix) – noch nicht gesendet
//
// Boden -> Rakete (Nutzlast: Folgenummer 1 Byte)
//   PING 0x20, CALIBRATE 0x21 (Gyro, Bodendruck, Lage; nur in SAFE/PAD_READY),
//   PAD_READY 0x22 (Freigabe zum Warten auf den Start), ABORT 0x23, SAFE 0x24 (zurück)
#include <stdint.h>
#include <stddef.h>

namespace tlm {

constexpr uint8_t SYNC0 = 0xA5, SYNC1 = 0x5A;
constexpr size_t  MAX_PAYLOAD = 64;
constexpr size_t  OVERHEAD = 6;                  // Sync 2, Typ 1, Länge 1, CRC 2

enum Type : uint8_t {
  TLM = 0x01, EVT = 0x02, GPS = 0x03, ACK = 0x10,
  CMD_PING = 0x20, CMD_CALIBRATE = 0x21, CMD_PAD_READY = 0x22, CMD_ABORT = 0x23, CMD_SAFE = 0x24
};

enum Flag : uint8_t {
  FLAG_ARMED = 1 << 0, FLAG_CONT1 = 1 << 1, FLAG_CONT2 = 1 << 2, FLAG_LOGGING = 1 << 3,
  FLAG_CALIBRATED = 1 << 4, FLAG_SENSORS_OK = 1 << 5, FLAG_PYRO_FIRED = 1 << 6, FLAG_RESTORED = 1 << 7
};

enum AckResult : uint8_t { ACK_OK = 0, ACK_REFUSED = 1, ACK_UNKNOWN = 2 };

// Nutzlast TLM, 16 Byte, gepackt
struct __attribute__((packed)) TlmPayload {
  uint8_t  state;        // FlightState
  uint8_t  flags;        // Flag-Bits
  uint16_t t_ds;         // Zeit seit Start in 0,1 s (vor dem Start: Betriebszeit)
  int16_t  alt_dm;       // Kalman-Höhe über dem Pad in 0,1 m
  int16_t  vz_cms;       // Steiggeschwindigkeit in cm/s
  int8_t   tilt_x_hd;    // Kippwinkel um x (Yaw-Servo) in 0,5 Grad
  int8_t   tilt_y_hd;    // um y (Pitch-Servo) in 0,5 Grad
  int8_t   roll_2d;      // Rollwinkel in 2 Grad
  int8_t   tvc_y_dd;     // Kardanwinkel Yaw in 0,1 Grad
  int8_t   tvc_p_dd;     // Pitch in 0,1 Grad
  uint8_t  vbat1_20mv;   // 1S in 0,02 V (bis 5,1 V)
  uint8_t  vbat2_50mv;   // 2S in 0,05 V (bis 12,75 V)
  uint8_t  seq;          // läuft um, für Paketverlust
};
static_assert(sizeof(TlmPayload) == 16, "TlmPayload muss 16 Byte haben");

struct __attribute__((packed)) EvtPayload {
  uint32_t t_ms;         // Zeit seit Start (vor dem Start: Betriebszeit)
  uint8_t  from, to, reason;
};
static_assert(sizeof(EvtPayload) == 7, "EvtPayload");

struct __attribute__((packed)) AckPayload {
  uint8_t cmd, seq, result, state;
};

struct __attribute__((packed)) CmdPayload {
  uint8_t seq;
};

// Rahmen bauen: liefert die Länge in out (mindestens payload_len + OVERHEAD groß)
size_t encode(uint8_t type, const uint8_t* payload, size_t payload_len, uint8_t* out, size_t out_cap);

// Hilfen zum Skalieren
int8_t  clamp_i8(float v);
int16_t clamp_i16(float v);
uint8_t clamp_u8(float v);

// Byteweiser Empfänger mit Resynchronisation auf 0xA5 0x5A
class Parser {
public:
  // Ein Byte einspeisen; true, wenn ein vollständiger, geprüfter Rahmen vorliegt
  bool feed(uint8_t b);
  uint8_t type() const { return type_; }
  const uint8_t* payload() const { return buf_; }
  size_t length() const { return len_; }
  uint32_t badFrames() const { return bad_; }

private:
  enum { S_SYNC0, S_SYNC1, S_TYPE, S_LEN, S_PAYLOAD, S_CRC0, S_CRC1 } st_ = S_SYNC0;
  uint8_t  type_ = 0, len_ = 0, idx_ = 0;
  uint8_t  buf_[MAX_PAYLOAD];
  uint16_t crc_rx_ = 0;
  uint32_t bad_ = 0;
};

}  // namespace tlm
