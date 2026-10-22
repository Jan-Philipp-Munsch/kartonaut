#pragma once
// KartonautProtocol.h – Telemetrie- und Kommandoprotokoll Rakete <-> Bodenstation
//
// Diese Datei gehört der Flug-Firmware und wird 1:1 in die Bodenstation
// (kartonaut-ground, ESP32-S3) kopiert. Nur C, kein C++, damit beide Seiten
// sie nehmen können. Alle Zahlen little-endian, Strukturen gepackt.
//
// Rahmen auf der Funkstrecke (docs/Schnittstellen_Bodensystem_2026-10-22.md, S3):
//
//   0xA5 0x5A | Typ (1) | Länge (1) | Nutzlast (Länge Byte) | CRC-16 (2, big-endian)
//
// CRC-16/CCITT-FALSE (0x1021, Start 0xFFFF) über Typ, Länge und Nutzlast.
// Luftrate 2,4 kbit/s heißt rund 300 Byte/s; der Telemetrierahmen hat 22 Byte
// Nutzlast + 6 Byte Rahmen = 28 Byte, bei 10 Hz also 280 Byte/s. GPS und
// Ereignisse kommen seltener dazwischen. Mehr passt nicht; wer Felder ergänzt,
// senkt die Rate oder hebt die Luftrate (dann sinkt die Reichweite).
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KN_SYNC0            0xA5
#define KN_SYNC1            0x5A
#define KN_MAX_PAYLOAD      64
#define KN_FRAME_OVERHEAD   6      /* 2 Sync + Typ + Länge + CRC */
#define KN_PROTOCOL_VERSION 1

/* Nachrichtentypen */
enum KnMsgType {
  KN_MSG_TELEMETRY = 0x01,   /* Rakete -> Boden, 10 Hz          KnTelemetry */
  KN_MSG_GPS       = 0x02,   /* Rakete -> Boden, 1 Hz           KnGps       */
  KN_MSG_EVENT     = 0x03,   /* Rakete -> Boden, je Übergang    KnEvent     */
  KN_MSG_STATUS    = 0x04,   /* Rakete -> Boden, 1 Hz           KnStatus    */
  KN_MSG_CMD       = 0x10,   /* Boden -> Rakete                 KnCommand   */
  KN_MSG_ACK       = 0x11,   /* Rakete -> Boden, Antwort        KnAck       */
};

/* Flugzustände (FlightState.h hält dieselbe Reihenfolge) */
enum KnPhase {
  KN_PHASE_SAFE      = 0,
  KN_PHASE_PAD_READY = 1,
  KN_PHASE_BOOST     = 2,
  KN_PHASE_COAST     = 3,
  KN_PHASE_APOGEE    = 4,
  KN_PHASE_DESCENT   = 5,
  KN_PHASE_LANDED    = 6,
  KN_PHASE_ABORT     = 7,
};

/* Bits in KnTelemetry.flags */
#define KN_FLAG_ARMED        0x01   /* ARM_SENSE sieht die Pyro-Spannung */
#define KN_FLAG_PYRO1_CONT   0x02   /* Durchgang Kanal 1 */
#define KN_FLAG_PYRO2_CONT   0x04
#define KN_FLAG_PYRO1_FIRED  0x08
#define KN_FLAG_PYRO2_FIRED  0x10
#define KN_FLAG_CTRL_ACTIVE  0x20   /* Pitch/Yaw-Regler stellt */
#define KN_FLAG_GYRO_CAL     0x40   /* Gyro-Bias und Lage auf der Rampe gesetzt */
#define KN_FLAG_LOGGING      0x80   /* SD-Log läuft */

#pragma pack(push, 1)

/* 22 Byte, 10 Hz */
typedef struct {
  uint32_t t_ms;         /* Millisekunden seit Boot (Flugzeit = t_ms - t_liftoff aus KN_MSG_EVENT) */
  uint8_t  phase;        /* KnPhase */
  uint8_t  flags;        /* KN_FLAG_* */
  int16_t  alt_dm;       /* Kalman-Höhe über Pad in 0,1 m */
  int16_t  vz_cms;       /* Vertikalgeschwindigkeit in cm/s */
  int16_t  q[4];         /* Lage Körper -> Navigation (w, x, y, z) × 32767 */
  int8_t   tvc_yaw_d5;   /* kommandierter TVC-Winkel Yaw in 0,2° (−25,4 .. +25,4°) */
  int8_t   tvc_pitch_d5; /* dito Pitch */
  uint8_t  vbat1_20mV;   /* 1S-Akku: Wert × 0,02 V (0 .. 5,1 V) */
  uint8_t  vbat2_40mV;   /* 2S-Akku: Wert × 0,04 V (0 .. 10,2 V) */
} KnTelemetry;

/* 13 Byte, 1 Hz */
typedef struct {
  int32_t  lat_1e7;      /* Breite in 1e-7 Grad */
  int32_t  lon_1e7;      /* Länge in 1e-7 Grad */
  int16_t  alt_m;        /* Höhe über Ellipsoid/MSL, wie das Modul liefert */
  uint8_t  sats;
  uint8_t  fix;          /* 0 = kein Fix, 2 = 2D, 3 = 3D */
  uint8_t  hdop_d10;     /* HDOP × 10 */
} KnGps;

/* 8 Byte, bei jedem Zustandsübergang, dreimal wiederholt */
typedef struct {
  uint32_t t_ms;
  uint8_t  phase_from;   /* KnPhase */
  uint8_t  phase_to;
  uint8_t  reason;       /* KnEventReason */
  uint8_t  seq;          /* laufende Nummer, für die Erkennung der Wiederholungen */
} KnEvent;

enum KnEventReason {
  KN_REASON_NONE          = 0,
  KN_REASON_COMMAND       = 1,   /* Kommando vom Boden oder USB */
  KN_REASON_READY         = 2,   /* Rampenbedingungen erfüllt */
  KN_REASON_ACCEL         = 3,   /* Beschleunigungsschwelle (Start, Brennschluss) */
  KN_REASON_VELOCITY      = 4,   /* Kalman-vz und Barometer (Apogäum) */
  KN_REASON_TIMEOUT       = 5,   /* Rückfall über die Zeit */
  KN_REASON_LANDED        = 6,   /* ruhig und tief */
  KN_REASON_TILT          = 7,   /* Kippwinkel zu groß */
  KN_REASON_RESTORED      = 8,   /* nach Neustart aus dem Zustandsspeicher */
  KN_REASON_SENSOR_FAIL   = 9,
  KN_REASON_NO_FLIGHT     = 10,  /* Start erkannt, aber kein Steigen gemessen: zurück nach SAFE, keine Zündung */
};

/* 14 Byte, 1 Hz */
typedef struct {
  uint16_t loop_us_max;   /* längste Schleife seit dem letzten Status */
  uint16_t current_mA;    /* 2S-Pfad (INA) */
  int16_t  baro_alt_dm;   /* Barometer-Höhe über Pad, 0,1 m */
  int16_t  tilt_cdeg;     /* Kippwinkel in 0,01° */
  int16_t  temp_c10;      /* IMU-Temperatur × 10 */
  uint8_t  boot_count;    /* Neustarts seit dem Einschalten (Watchdog) */
  uint8_t  log_pct;       /* Füllstand der Logdatei in % */
  uint8_t  rssi;          /* 0 = unbekannt (E22 liefert RSSI nur auf Anfrage) */
  uint8_t  version;       /* KN_PROTOCOL_VERSION */
} KnStatus;

/* 4 Byte, Boden -> Rakete */
typedef struct {
  uint8_t  cmd;          /* KnCommandId */
  uint8_t  seq;          /* wird im ACK zurückgegeben */
  uint16_t arg;
} KnCommand;

enum KnCommandId {
  KN_CMD_PING            = 1,   /* Antwort: ACK mit aktuellem Zustand          */
  KN_CMD_CALIBRATE       = 2,   /* Gyro-Bias, Lage, Bodendruck (nur SAFE)      */
  KN_CMD_PAD_READY_QUERY = 3,   /* Antwort: ACK, result = KnPhase              */
  KN_CMD_ABORT           = 4,   /* -> ABORT, Regler aus, Servos Mitte          */
  KN_CMD_SAFE            = 5,   /* PAD_READY -> SAFE (Abbruch vor dem Start)   */
  KN_CMD_LOG_START       = 6,
  KN_CMD_LOG_STOP        = 7,
  KN_CMD_TESTRIG_THRUST  = 8,   /* arg = Schub in 0,01 N für den Prüfstand     */
};

/* 3 Byte, Rakete -> Boden */
typedef struct {
  uint8_t cmd;
  uint8_t seq;
  uint8_t result;        /* KnAckResult oder bei PAD_READY_QUERY/PING die KnPhase */
} KnAck;

enum KnAckResult {
  KN_ACK_OK       = 0,
  KN_ACK_REJECTED = 1,   /* im aktuellen Zustand nicht erlaubt */
  KN_ACK_FAILED   = 2,
  KN_ACK_UNKNOWN  = 3,
};

#pragma pack(pop)

#ifdef __cplusplus
}  /* extern "C" */
#endif
