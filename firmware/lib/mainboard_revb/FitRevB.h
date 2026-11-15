#pragma once
// FitRevB.h – welche Bausteine auf dieser Platine bestückt sind (Bestückungsliste)
//
// Ein Teil, das hier "aus" steht, wird von den Prüfprogrammen nicht als Fehler gewertet:
// revb_test meldet "TEST <name> NICHT_ERKANNT nicht bestückt ...", revb_bringup "[ -- ]".
// Ein Teil, das "an" steht und nicht antwortet, ist FEHL. Kein Teil bricht den Lauf ab.
//
// Standard (Stand 05.11.2026, Platine von JLCPCB): IMU LSM6DSV16X, BMP388, LIS3MDL, SHT40
// bestückt; INA239 (U6) nachbestellt, kommt ca. 11.11.; LoRa E22 (U10) noch nicht da; GPS an
// J11 nicht gesteckt; Baro 2 (U15) und ADXL375 (U17) DNP.
//
// Ändern:
//   - zur Laufzeit in revb_test:  fit ina on | fit lora off | fit | fit default  (nur RAM)
//   - beim Bauen, für revb_test und revb_bringup, z. B. in platformio.ini:
//       build_flags = ${env.build_flags} -DREVB_FIT_INA239=1 -DREVB_FIT_LORA=1
#include <Arduino.h>
#include "BoardRevB.h"

#ifndef REVB_FIT_IMU
#define REVB_FIT_IMU 1
#endif
#ifndef REVB_FIT_BARO
#define REVB_FIT_BARO 1          // U5, auf rev B1 ein BMP388 (Chip-ID 0x50)
#endif
#ifndef REVB_FIT_BARO2
#define REVB_FIT_BARO2 0         // U15 DNP (BoardRevB.h: BARO2_FITTED)
#endif
#ifndef REVB_FIT_INA239
#define REVB_FIT_INA239 0        // U6 nachbestellt
#endif
#ifndef REVB_FIT_MAG
#define REVB_FIT_MAG 1           // U16 LIS3MDL
#endif
#ifndef REVB_FIT_SHT
#define REVB_FIT_SHT 1           // U18 SHT40
#endif
#ifndef REVB_FIT_ADXL
#define REVB_FIT_ADXL 0          // U17 DNP (BoardRevB.h: ADXL375_FITTED)
#endif
#ifndef REVB_FIT_LORA
#define REVB_FIT_LORA 0          // U10 E22-400T22S noch nicht da
#endif
#ifndef REVB_FIT_GPS
#define REVB_FIT_GPS 0           // Modul an J11 noch nicht gesteckt
#endif

namespace revb {

struct Fit {
  bool imu   = REVB_FIT_IMU;
  bool baro  = REVB_FIT_BARO;
  bool baro2 = REVB_FIT_BARO2;
  bool ina   = REVB_FIT_INA239;
  bool mag   = REVB_FIT_MAG;
  bool sht   = REVB_FIT_SHT;
  bool adxl  = REVB_FIT_ADXL;
  bool lora  = REVB_FIT_LORA;
  bool gps   = REVB_FIT_GPS;

  // Name -> Eintrag ("imu", "baro", "baro2", "ina", "mag", "sht", "adxl", "lora", "gps"); nullptr = unbekannt
  bool* find(const char* n) {
    for (int i = 0; i < COUNT; ++i) if (!strcmp(n, name(i))) return &at(i);
    return nullptr;
  }
  bool& at(int i) {
    bool* f[COUNT] = {&imu, &baro, &baro2, &ina, &mag, &sht, &adxl, &lora, &gps};
    return *f[i];
  }
  static constexpr int COUNT = 9;
  static const char* name(int i) {
    static const char* const n[COUNT] = {"imu", "baro", "baro2", "ina", "mag", "sht", "adxl", "lora", "gps"};
    return n[i];
  }
};

// LoRa-Pins in Ruhe. M0/M1 haben auf der Platine keinen Widerstand, das E22 will sie fest
// beschaltet (M0 = M1 = 0: Normalbetrieb). Mit Modul: beide tief treiben. Ohne Modul: nichts
// treiben, der Pull-down im Teensy hält einen festen Pegel an den offenen Pads. AUX ohne Modul
// ebenfalls Pull-down (liest dann "nicht bereit"), mit Modul treibt das E22 selbst.
// NRST ist Open-Drain mit 10 k nach 3V3_RF: nur loslassen. Serial8 wird hier nicht gestartet.
inline void loraPinsIdle(bool fitted) {
  pinMode(PIN_LORA_NRST, INPUT);
  if (fitted) {
    digitalWrite(PIN_LORA_M0, LOW); pinMode(PIN_LORA_M0, OUTPUT);
    digitalWrite(PIN_LORA_M1, LOW); pinMode(PIN_LORA_M1, OUTPUT);
    pinMode(PIN_LORA_AUX, INPUT);
  } else {
    pinMode(PIN_LORA_M0, INPUT_PULLDOWN);
    pinMode(PIN_LORA_M1, INPUT_PULLDOWN);
    pinMode(PIN_LORA_AUX, INPUT_PULLDOWN);
  }
}

}  // namespace revb
