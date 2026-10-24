#pragma once
// CalData.h – Kalibrierwerte des Flugrechners, Ablageformat mit Version und CRC
//
// Reines C++ ohne Arduino, damit die Struktur, die CRC und die Prüfung auf
// dem PC getestet werden können (test/host/). Die Ablage im EEPROM-Emulat
// des Teensy macht CalStore.*. Die Flug-Firmware lädt den Block beim Start
// und fällt bei falscher CRC oder fremder Version auf die Standardwerte
// zurück (calDefaults), mit Warnung im Log.
//
// Jeder Kalibrierschritt setzt sein Bit in `valid`; was nicht kalibriert
// ist, steht auf dem Standardwert und zählt nicht als Fehler.
//
// Achsen: imu_axis_map/sign bilden Chip-Achsen auf den Raketenkörper ab:
//   body[i] = sign[i] * chip[map[i]]      (x, y quer, z Rollachse)
// Magnetometer: erst Hard-/Soft-Iron in Chip-Achsen, dann dieselbe Abbildung.
#include <stdint.h>
#include <stddef.h>
#include <string.h>

namespace cal {

constexpr uint32_t MAGIC   = 0x4C41434Bu;   // "KCAL"
constexpr uint16_t VERSION = 1;

enum Valid : uint32_t {
  GYRO  = 1u << 0,
  ACC   = 1u << 1,
  MAG   = 1u << 2,
  AXES  = 1u << 3,
  BARO  = 1u << 4,
  ADC   = 1u << 5,
  INA   = 1u << 6,
  SERVO = 1u << 7,
};

struct CalData {
  uint32_t magic;
  uint16_t version;
  uint16_t size;              // sizeof(CalData), Schutz gegen Layoutwechsel
  uint32_t valid;             // Bits aus Valid
  uint32_t saved_count;       // wie oft gespeichert (Diagnose)

  // Gyro: Nullpunkt in Ruhe, Temperatur dabei, Rauschen (Standardabweichung)
  float gyro_bias_dps[3];
  float gyro_bias_temp_c;
  float gyro_noise_dps[3];

  // Beschleunigung: korrigiert = (roh - offset) * scale, je Chip-Achse
  float acc_offset_ms2[3];
  float acc_scale[3];

  // Magnetometer: korrigiert = soft_iron * (roh - offset), Chip-Achsen, gauss
  float mag_offset_gauss[3];
  float mag_soft_iron[9];     // zeilenweise 3x3
  float mag_field_gauss;      // Betrag nach der Korrektur
  float mag_fit_residual_pct; // Güte des Fits

  // Achszuordnung Chip -> Körper
  int8_t imu_axis_map[3];
  int8_t imu_axis_sign[3];
  int8_t mag_axis_map[3];
  int8_t mag_axis_sign[3];

  // Barometer
  float baro_ground_pa;
  float baro_ground_temp_c;
  float baro_noise_pa;

  // Analogmux: Spannung = ADC * DIVIDER_RATIO * adc_gain[kanal]
  float adc_gain[8];

  // INA239: Strom = (roh - ina_offset_a) * ina_gain
  float ina_offset_a;
  float ina_gain;

  // Servos (Yaw, Pitch, Chute, Legs): Mitte und Grenzen in µs
  uint16_t servo_center_us[4];
  uint16_t servo_min_us[4];
  uint16_t servo_max_us[4];

  uint32_t crc;               // CRC-32 (IEEE) über alles davor
};

// CRC-32 (IEEE 802.3, reflektiert, Startwert 0xFFFFFFFF, Ergebnis invertiert)
inline uint32_t crc32(const void* data, size_t n, uint32_t crc = 0xFFFFFFFFu) {
  const uint8_t* p = static_cast<const uint8_t*>(data);
  for (size_t i = 0; i < n; ++i) {
    crc ^= p[i];
    for (int b = 0; b < 8; ++b) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
  }
  return crc ^ 0xFFFFFFFFu;
}

inline uint32_t computeCrc(const CalData& d) {
  return crc32(&d, offsetof(CalData, crc));
}

inline void seal(CalData& d) {
  d.magic   = MAGIC;
  d.version = VERSION;
  d.size    = uint16_t(sizeof(CalData));
  d.crc     = computeCrc(d);
}

enum class Check { OK, EMPTY, BAD_VERSION, BAD_SIZE, BAD_CRC };

inline Check check(const CalData& d) {
  if (d.magic != MAGIC) return Check::EMPTY;
  if (d.version != VERSION) return Check::BAD_VERSION;
  if (d.size != sizeof(CalData)) return Check::BAD_SIZE;
  if (d.crc != computeCrc(d)) return Check::BAD_CRC;
  return Check::OK;
}

inline const char* checkName(Check c) {
  switch (c) {
    case Check::OK:          return "ok";
    case Check::EMPTY:       return "leer";
    case Check::BAD_VERSION: return "fremde Version";
    case Check::BAD_SIZE:    return "fremdes Layout";
    default:                 return "CRC falsch";
  }
}

// Standardwerte: neutrale Kalibrierung, Servo 1500 µs Mitte, 1000..2000 µs
inline CalData defaults() {
  CalData d;
  memset(&d, 0, sizeof d);
  for (int i = 0; i < 3; ++i) {
    d.acc_scale[i] = 1.0f;
    d.mag_soft_iron[4 * i] = 1.0f;
    d.imu_axis_map[i] = d.mag_axis_map[i] = int8_t(i);
    d.imu_axis_sign[i] = d.mag_axis_sign[i] = 1;
  }
  d.mag_field_gauss = 0.5f;
  d.baro_ground_pa  = 101325.0f;
  d.baro_ground_temp_c = 15.0f;
  for (int i = 0; i < 8; ++i) d.adc_gain[i] = 1.0f;
  d.ina_gain = 1.0f;
  for (int i = 0; i < 4; ++i) {
    d.servo_center_us[i] = 1500;
    d.servo_min_us[i] = 1000;
    d.servo_max_us[i] = 2000;
  }
  seal(d);
  return d;
}

inline bool has(const CalData& d, Valid bit) { return (d.valid & bit) != 0; }

// Hilfen zum Anwenden
inline void mapAxes(const int8_t map[3], const int8_t sign[3], const float chip[3], float body[3]) {
  for (int i = 0; i < 3; ++i) body[i] = sign[i] * chip[map[i]];
}

inline void applyMag(const CalData& d, const float raw[3], float out_chip[3]) {
  float c[3];
  for (int i = 0; i < 3; ++i) c[i] = raw[i] - d.mag_offset_gauss[i];
  for (int i = 0; i < 3; ++i)
    out_chip[i] = d.mag_soft_iron[3 * i] * c[0] + d.mag_soft_iron[3 * i + 1] * c[1] + d.mag_soft_iron[3 * i + 2] * c[2];
}

inline void applyAcc(const CalData& d, const float raw[3], float out_chip[3]) {
  for (int i = 0; i < 3; ++i) out_chip[i] = (raw[i] - d.acc_offset_ms2[i]) * d.acc_scale[i];
}

}  // namespace cal
