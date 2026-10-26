#pragma once
#include <Arduino.h>

// =====================================================================
//  Protocol.h – Funkprotokoll Rakete <-> Bodenstation (S3)
//
//  PLATZHALTER. Das Protokoll gehört der Flug-Firmware (firmware/, E7).
//  Stand 22.10.2026 gibt es dort noch keine Definition (nur den
//  HC-12-Beacon "BEACON,<seq>,<millis>"). Diese Datei setzt den Vorschlag
//  aus docs/Schnittstellen_Bodensystem_2026-10-22.md §S3 um und ist so
//  geschnitten, dass sie gegen die Definition aus firmware/ ausgetauscht
//  werden kann: der Rest der Firmware kennt nur die Strukturen und
//  Funktionen unten.
//
//  Rahmen:  0xA5 0x5A | Typ (1) | Länge N (1) | Nutzlast (N) | CRC-16 (2)
//  CRC-16/CCITT-FALSE (Poly 0x1021, Start 0xFFFF) über Typ, Länge und
//  Nutzlast, Little Endian übertragen. Alle Mehrbyte-Felder Little Endian.
// =====================================================================

namespace proto {

constexpr uint8_t SYNC0 = 0xA5;
constexpr uint8_t SYNC1 = 0x5A;
constexpr uint8_t MAX_PAYLOAD = 64;

// ----- Rahmentypen -----
enum : uint8_t {
  T_TELEMETRY = 0x01,   // Rakete -> Boden, 10 Hz
  T_GPS       = 0x02,   // Rakete -> Boden, 1 Hz
  T_ACK       = 0x11,   // Rakete -> Boden, Quittung auf ein Kommando
  T_COMMAND   = 0x10,   // Boden -> Rakete
};

// ----- Kommandos Boden -> Rakete -----
enum Command : uint8_t {
  CMD_PING            = 0x01,
  CMD_CALIBRATE       = 0x02,
  CMD_PAD_READY_QUERY = 0x03,
  CMD_ABORT           = 0x04,
};

// ----- Quittungsergebnis -----
enum AckResult : uint8_t {
  ACK_OK       = 0x00,
  ACK_REFUSED  = 0x01,   // im aktuellen Flugzustand nicht erlaubt
  ACK_BUSY     = 0x02,   // z. B. Kalibrierung läuft schon
  ACK_UNKNOWN  = 0x03,
};

// ----- Flugzustände (Vorschlag; maßgeblich wird der Automat in firmware/) -----
enum FlightState : uint8_t {
  FS_BOOT        = 0,
  FS_IDLE        = 1,   // an, nicht kalibriert
  FS_CALIBRATING = 2,
  FS_PAD_READY   = 3,   // kalibriert, wartet auf Abheben
  FS_BOOST       = 4,
  FS_COAST       = 5,
  FS_APOGEE      = 6,
  FS_DESCENT     = 7,   // am Fallschirm
  FS_LANDED      = 8,
  FS_ABORT       = 9,
  FS_FAULT       = 10,
};

// ----- Telemetrie-Flags -----
enum : uint8_t {
  F_ARMED      = 1 << 0,  // Schlüsselschalter der Rakete scharf (VBAT_ARMED vorhanden)
  F_PYRO1_CONT = 1 << 1,  // Durchgang Pyro 1 (Fallschirm)
  F_PYRO2_CONT = 1 << 2,
  F_GPS_FIX    = 1 << 3,
  F_LOGGING    = 1 << 4,  // SD-Log läuft
  F_CALIBRATED = 1 << 5,
};

// Nutzlast T_TELEMETRY, 27 Byte
struct __attribute__((packed)) TelemetryRaw {
  uint8_t  seq;
  uint8_t  state;        // FlightState
  uint8_t  flags;
  uint32_t t_ms;         // Zeit seit Start der Flug-Firmware
  int16_t  alt_dm;       // Höhe über Pad, 0,1 m
  int16_t  vz_cms;       // Steiggeschwindigkeit, cm/s
  int16_t  q[4];         // Lage-Quaternion w,x,y,z, 1/32767
  int16_t  gimbal_cdeg[2]; // Kardan Pitch, Yaw, 0,01°
  uint16_t v1s_mv;       // 1S-Akku
  uint16_t v2s_mv;       // 2S-Akku
};
static_assert(sizeof(TelemetryRaw) == 27, "TelemetryRaw");

// Nutzlast T_GPS, 12 Byte
struct __attribute__((packed)) GpsRaw {
  int32_t  lat_e7;
  int32_t  lon_e7;
  int16_t  alt_m;        // über NN
  uint8_t  sats;
  uint8_t  fix;          // 0 kein, 2 2D, 3 3D
};
static_assert(sizeof(GpsRaw) == 12, "GpsRaw");

// Nutzlast T_COMMAND, 2 Byte
struct __attribute__((packed)) CommandRaw {
  uint8_t cmd;           // Command
  uint8_t seq;           // vom Boden hochgezählt, kommt in der Quittung zurück
};

// Nutzlast T_ACK, 3 Byte
struct __attribute__((packed)) AckRaw {
  uint8_t cmd;
  uint8_t seq;
  uint8_t result;        // AckResult
};

// ----- Aufbereitete Werte für den Rest der Firmware -----
struct Telemetry {
  uint8_t  seq = 0;
  uint8_t  state = FS_BOOT;
  uint8_t  flags = 0;
  uint32_t t_ms = 0;
  float    alt_m = 0, vz_ms = 0;
  float    q[4] = {1, 0, 0, 0};
  float    gimbal_deg[2] = {0, 0};
  float    v1s = 0, v2s = 0;
};

struct Gps {
  double  lat = 0, lon = 0;
  float   alt_m = 0;
  uint8_t sats = 0, fix = 0;
};

const char* stateName(uint8_t s);
const char* commandName(uint8_t c);

uint16_t crc16(const uint8_t* data, size_t len, uint16_t crc = 0xFFFF);

// Baut einen Rahmen in out (mindestens 6 + len Byte). Rückgabe: Länge.
size_t encode(uint8_t type, const void* payload, uint8_t len, uint8_t* out);

void decodeTelemetry(const TelemetryRaw& r, Telemetry& t);
void decodeGps(const GpsRaw& r, Gps& g);

// Zustandsautomat zum Byteweise-Empfang. Der transparente E22-Modus kann
// Rahmen auf mehrere Funkpakete verteilen oder zusammenlegen; der Parser
// synchronisiert sich deshalb nur an 0xA5 0x5A und der CRC.
class Parser {
public:
  // Liefert true, sobald ein vollständiger Rahmen mit gültiger CRC vorliegt.
  bool feed(uint8_t b);
  uint8_t type() const { return type_; }
  uint8_t length() const { return len_; }
  const uint8_t* payload() const { return buf_; }
  uint32_t crcErrors = 0;
  uint32_t frames = 0;

private:
  enum St : uint8_t { S0, S1, TYPE, LEN, DATA, CRC0, CRC1 } st_ = S0;
  uint8_t type_ = 0, len_ = 0, idx_ = 0;
  uint16_t crcRx_ = 0;
  uint8_t buf_[MAX_PAYLOAD];
};

} // namespace proto
