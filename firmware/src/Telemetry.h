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
//   ACK  0x10  Antwort auf jedes Kommando: Kommandotyp, Folgenummer, Ergebnis, Zustand.
//              Auf PING, ARM und LAUNCH länger (AckAuthPayload): aktuelle nonce, Bitmaske der
//              Startvorbedingungen, verbleibende Countdownzeit
//   IGN  0x04  einmal nach der Zündung (beim Verlassen von IGNITION): Zeitmarken des Startpulses
//   GPS  0x03  1 Hz, später (Breite, Länge, Höhe, Fix) – noch nicht gesendet
//
// Boden -> Rakete (Nutzlast: Folgenummer 1 Byte)
//   PING 0x20, CALIBRATE 0x21 (Gyro, Bodendruck, Lage; nur in SAFE/PAD_READY),
//   PAD_READY 0x22 (Freigabe zum Warten auf den Start), ABORT 0x23, SAFE 0x24 (zurück)
// Motorstart an Bord (docs/Plan_Bordzuendung_2026-10-27.md §3):
//   ARM 0x25 und LAUNCH 0x26 mit Folgenummer und MAC (8 Byte, LaunchAuth.h) über die nonce,
//   HEARTBEAT 0x27 (nur Folgenummer, ohne ACK) während ARMED und COUNTDOWN mindestens 2 Hz.
//   ABORT bleibt ohne MAC, damit ein Abbruch nie an der Authentisierung scheitert.
//
// Laptop <-> Funkbrücke (tools/ground/bridge_pico), geht nie über Funk:
//   BRIDGE_CONFIG 0x70 (ohne Nutzlast): die Brücke stellt ihr E22 auf die Werte aus Config.h (E22Config.h)
//   BRIDGE_ACK    0x71: Ergebnis und die neun gelesenen Register
#include <stdint.h>
#include <stddef.h>

namespace tlm {

constexpr uint8_t SYNC0 = 0xA5, SYNC1 = 0x5A;
constexpr size_t  MAX_PAYLOAD = 64;
constexpr size_t  OVERHEAD = 6;                  // Sync 2, Typ 1, Länge 1, CRC 2

enum Type : uint8_t {
  TLM = 0x01, EVT = 0x02, GPS = 0x03, IGN = 0x04, ACK = 0x10,
  CMD_PING = 0x20, CMD_CALIBRATE = 0x21, CMD_PAD_READY = 0x22, CMD_ABORT = 0x23, CMD_SAFE = 0x24,
  CMD_ARM = 0x25, CMD_LAUNCH = 0x26, CMD_HEARTBEAT = 0x27,
  BRIDGE_CONFIG = 0x70, BRIDGE_ACK = 0x71
};

enum Flag : uint8_t {
  FLAG_ARMED = 1 << 0, FLAG_CONT1 = 1 << 1, FLAG_CONT2 = 1 << 2, FLAG_LOGGING = 1 << 3,
  FLAG_CALIBRATED = 1 << 4, FLAG_SENSORS_OK = 1 << 5, FLAG_PYRO_FIRED = 1 << 6, FLAG_RESTORED = 1 << 7
};

// ACK_AUTH: MAC falsch (falscher Schlüssel, alte nonce, wiederholter Befehl); die nonce ist trotzdem verbraucht
enum AckResult : uint8_t { ACK_OK = 0, ACK_REFUSED = 1, ACK_UNKNOWN = 2, ACK_AUTH = 3 };

// Startvorbedingungen (Plan Bordzündung §4), gesetztes Bit = erfüllt
enum Precond : uint8_t {
  PRE_ARM_V = 1 << 0,     // VBAT_ARMED vorhanden (Arming-Schalter ein)
  PRE_CONT = 1 << 1,      // Durchgang am Startkanal (Pyro 1)
  PRE_BATT = 1 << 2,      // 1S und 2S über ihrer Schwelle
  PRE_STILL = 1 << 3,     // ruhig (Gyro) und aufrecht (Kippung)
  PRE_SENSORS = 1 << 4,   // Sensoren ok, kalibriert, Logging läuft
  PRE_SERVO = 1 << 5,     // Servo-Selbsttest bestanden
  PRE_KEY = 1 << 6,       // LAUNCH_ENABLED (Schlüssel in Secrets.h)
  PRE_ALL = 0x7F
};

// Grund für das Ende des Startpulses (IgnPayload::end_reason)
enum IgnEnd : uint8_t {
  IGN_END_NONE = 0, IGN_END_THRUST = 1, IGN_END_CONT_LOST = 2, IGN_END_TIMEOUT = 3,
  IGN_END_STOPPED = 4,    // Zustand verlassen (ABORT)
  IGN_END_DISARMED = 5,   // Arming-Spannung weg
  IGN_END_REFUSED = 6     // Puls nie begonnen (nicht scharf, kein Durchgang)
};
constexpr uint16_t IGN_NO_TIME = 0xFFFF;   // Zeitmarke nicht eingetreten

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

constexpr size_t MAC_LEN = 8;

// ARM und LAUNCH
struct __attribute__((packed)) CmdAuthPayload {
  uint8_t seq;
  uint8_t mac[MAC_LEN];   // LaunchAuth.h: HMAC-SHA256(Schlüssel, Typ | seq | nonce | Raketen-ID), erste 8 Byte
};
static_assert(sizeof(CmdAuthPayload) == 9, "CmdAuthPayload");

// ACK auf PING, ARM und LAUNCH
struct __attribute__((packed)) AckAuthPayload {
  uint8_t  cmd, seq, result, state;
  uint32_t nonce;          // aktuelle nonce (0 und has_nonce-Bit aus, wenn keine gilt)
  uint8_t  precond;        // Precond-Bits
  uint16_t countdown_ms;   // verbleibende Countdownzeit (nur in COUNTDOWN, sonst 0)
};
static_assert(sizeof(AckAuthPayload) == 11, "AckAuthPayload");

// IGN: Zeiten in ms relativ zum Ende des Countdowns (Eintritt in IGNITION), IGN_NO_TIME = nicht eingetreten
struct __attribute__((packed)) IgnPayload {
  uint16_t t_pulse_on_ms, t_cont_lost_ms, t_thrust_ms, t_pulse_off_ms;
  uint16_t arm_before_mv;  // VBAT_ARMED vor dem Puls
  uint16_t arm_min_mv;     // kleinste VBAT_ARMED während des Pulses (Abtastung >= 1 kHz)
  uint16_t vbat1_min_mv;   // kleinste 1S-Spannung während des Pulses
  uint16_t arm_samples;    // Zahl der schnellen Messungen während des Pulses
  uint8_t  end_reason;     // IgnEnd
};
static_assert(sizeof(IgnPayload) == 17, "IgnPayload");

// BRIDGE_ACK: Ergebnis (BridgeResult) und die Register 00H..08H, wie sie das E22 der Brücke danach meldet
enum BridgeResult : uint8_t { BRIDGE_OK = 0, BRIDGE_NO_REPLY = 1, BRIDGE_WRITE_FAILED = 2 };
struct __attribute__((packed)) BridgeAckPayload {
  uint8_t result;
  uint8_t regs[9];
};
static_assert(sizeof(BridgeAckPayload) == 10, "BridgeAckPayload");

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
