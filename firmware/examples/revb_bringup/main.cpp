// revb_bringup – Inbetriebnahme des Mainboards rev B
//
// Erstes Programm auf der bestückten Platine. Es setzt zuerst alle
// Ausgänge in den sicheren Zustand (Pyro tief, Rollmotor schlafend,
// Servos ohne Puls, alle Chip-Selects hoch), prüft dann jeden Baustein
// einzeln und meldet das Ergebnis auf USB-Serial (115200 Bd):
//
//   1. Analogmux: GND-Kanal, beide Akkus, ARM, Durchgang Pyro 1–4
//   2. ICM-42688-P: WHO_AM_I, Konfiguration, Beschleunigung ≈ 1 g in Ruhe
//   3. BMP390 (und BMP390 #2, falls bestückt): Chip-ID, Druck plausibel
//   4. INA239: Hersteller- und Geräte-ID, Bus-Spannung ≈ 2S-Akku
//   5. LoRa E22: Konfigurationsmodus, Parameter lesen (Kanal, Adresse)
//   6. GPS an Serial1: kommen NMEA-Zeilen an (38400 oder 9600 Bd)?
//
// Danach laufen die Messwerte im Sekundentakt. Pyro-Kanäle werden nicht
// gezündet; dafür bleibt examples/pyro_mosfet_test mit Lämpchen als Last.
#include <Arduino.h>
#include <FastLED.h>
#include "BoardRevB.h"
#include "BusRevB.h"
#include "ICM42688.h"
#include "BMP390.h"
#include "INA239.h"

using namespace revb;

static BusRevB  bus;
static ICM42688 imu(bus);
static BMP390   baro(bus, Cs::BARO);
static BMP390   baro2(bus, Cs::BARO2);
static INA239   ina(bus, INA_SHUNT_OHM, INA_MAX_CURRENT_A);
static CRGB     leds[LED_COUNT_ONBOARD];

static bool ok_imu = false, ok_baro = false, ok_baro2 = false, ok_ina = false;

static void safeOutputs() {
  for (uint8_t p : PYRO_FIRE_PINS) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
  digitalWrite(PIN_MOT_NSLEEP, LOW);  pinMode(PIN_MOT_NSLEEP, OUTPUT);
  digitalWrite(PIN_MOT_IN1, LOW);     pinMode(PIN_MOT_IN1, OUTPUT);
  digitalWrite(PIN_MOT_IN2, LOW);     pinMode(PIN_MOT_IN2, OUTPUT);
  for (uint8_t p : {PIN_SERVO_YAW, PIN_SERVO_PITCH, PIN_SERVO_CHUTE, PIN_SERVO_LEGS}) {
    digitalWrite(p, LOW); pinMode(p, OUTPUT);
  }
  digitalWrite(PIN_BUZZER, LOW);      pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_CAM_TRIG, LOW);    pinMode(PIN_CAM_TRIG, OUTPUT);
  pinMode(PIN_MOT_FAULT, INPUT_PULLUP);
  pinMode(PIN_IMU_INT, INPUT);
  pinMode(PIN_LORA_NRST, INPUT);      // Open-Drain: loslassen = Pull-up hält hoch
  pinMode(PIN_LORA_AUX, INPUT);
}

static void report(const char* what, bool ok, const char* detail = "") {
  Serial.printf("  [%s] %-28s %s\n", ok ? " OK " : "FEHL", what, detail);
}

static void checkMux() {
  Serial.println("\n1. Analogmux 74HC4051");
  char buf[64];
  const float v_gnd = bus.readMuxV(Mux::GND);
  snprintf(buf, sizeof buf, "%.3f V am ADC", v_gnd);
  report("GND-Kanal (Y7)", v_gnd < 0.05f, buf);

  const float v1 = bus.readMuxInputV(Mux::VBAT1);
  snprintf(buf, sizeof buf, "%.2f V", v1);
  report("1S-Akku (3,0..4,2 V)", v1 > 3.0f && v1 < 4.35f, buf);

  const float v2 = bus.readMuxInputV(Mux::VBAT2);
  snprintf(buf, sizeof buf, "%.2f V", v2);
  report("2S-Akku (6,0..8,4 V)", v2 > 6.0f && v2 < 8.6f, buf);

  const float va = bus.readMuxInputV(Mux::ARM);
  snprintf(buf, sizeof buf, "%.2f V (%s)", va, va > 5.0f ? "SCHARF" : "sicher");
  report("ARM (Schlüsselschalter)", true, buf);

  // Durchgang ist nur bei scharfem Schalter sichtbar: Pyro-Sense ≈ ARM-Spannung
  const Mux ch[4] = {Mux::PYRO1, Mux::PYRO2, Mux::PYRO3, Mux::PYRO4};
  for (int i = 0; i < 4; ++i) {
    const float vp = bus.readMuxInputV(ch[i]);
    const bool cont = va > 5.0f && vp > 0.8f * va;
    snprintf(buf, sizeof buf, "%.2f V, %s%s", vp, cont ? "Durchgang" : "offen",
             PYRO_FITTED[i] ? "" : " (DNP)");
    char what[24];
    snprintf(what, sizeof what, "Pyro %d", i + 1);
    report(what, true, buf);
  }
}

static void checkImu() {
  Serial.println("\n2. IMU ICM-42688-P (CS Y0)");
  char buf[64];
  const uint8_t id = imu.whoAmI();
  snprintf(buf, sizeof buf, "0x%02X (soll 0x47)", id);
  report("WHO_AM_I", id == ICM42688::WHO_AM_I_VALUE, buf);
  ok_imu = imu.begin();
  report("Konfiguration", ok_imu);
  if (!ok_imu) return;
  ImuSample s;
  imu.read(s);
  const float a = sqrtf(s.acc_ms2[0] * s.acc_ms2[0] + s.acc_ms2[1] * s.acc_ms2[1] + s.acc_ms2[2] * s.acc_ms2[2]);
  snprintf(buf, sizeof buf, "|a| = %.2f m/s², %.1f °C", a, s.temp_c);
  report("Ruhe ≈ 1 g", fabsf(a - 9.81f) < 0.8f, buf);
}

static bool checkBaro(BMP390& b, const char* name, bool fitted) {
  char buf[64];
  const bool ok = b.begin();
  snprintf(buf, sizeof buf, "Chip-ID 0x%02X%s", b.chipId(),
           b.chipId() == BMP390::CHIP_ID_BMP388 ? " (BMP388)" : "");
  if (!ok && !fitted) { report(name, true, "nicht bestückt (DNP)"); return false; }
  report(name, ok, buf);
  if (!ok) return false;
  float p = 0, t = 0;
  const uint32_t t0 = millis();
  while (!b.read(p, t) && millis() - t0 < 200) delay(5);
  snprintf(buf, sizeof buf, "%.0f Pa, %.1f °C", p, t);
  report("  Druck 80..110 kPa", p > 80000.0f && p < 110000.0f, buf);
  return true;
}

static void checkIna() {
  Serial.println("\n4. Strommonitor INA239 (CS Y3)");
  char buf[64];
  const uint16_t man = ina.manufacturerId(), dev = ina.deviceId();
  snprintf(buf, sizeof buf, "0x%04X / 0x%04X", man, dev);
  report("Hersteller / Gerät", man == INA239::MANUFACTURER_TI && (dev >> 4) == INA239::DEVICE_ID_INA239, buf);
  ok_ina = ina.begin();
  report("Konfiguration", ok_ina);
  if (!ok_ina) return;
  delay(60);                                   // eine gemittelte Wandlung
  PowerSample s;
  ina.read(s);
  snprintf(buf, sizeof buf, "%.2f V, %.0f mA", s.bus_V, s.current_A * 1000.0f);
  report("VSERVO ≈ 2S-Akku", s.bus_V > 6.0f && s.bus_V < 8.6f, buf);
}

static bool waitAux(uint32_t timeout_ms) {
  const uint32_t t0 = millis();
  while (!digitalRead(PIN_LORA_AUX)) {
    if (millis() - t0 > timeout_ms) return false;
  }
  return true;
}

static void checkLora() {
  Serial.println("\n5. LoRa E22-400T22S (Serial8)");
  char buf[80];
  // Modus 2 (Konfiguration): M1 = 1, M0 = 0; UART dann fest 9600 8N1
  digitalWrite(PIN_LORA_M0, LOW);  pinMode(PIN_LORA_M0, OUTPUT);
  digitalWrite(PIN_LORA_M1, HIGH); pinMode(PIN_LORA_M1, OUTPUT);
  Serial8.begin(9600);
  delay(50);
  report("AUX hoch (bereit)", waitAux(1000));

  while (Serial8.available()) Serial8.read();
  const uint8_t cmd[3] = {0xC1, 0x00, 0x09};   // Register 00H..08H lesen
  Serial8.write(cmd, 3);
  uint8_t r[12];
  size_t n = 0;
  const uint32_t t0 = millis();
  while (n < sizeof r && millis() - t0 < 300) {
    if (Serial8.available()) r[n++] = Serial8.read();
  }
  const bool ok = n == sizeof r && r[0] == 0xC1;
  if (ok) {
    // r[3] ADDH, r[4] ADDL, r[5] NETID, r[6] REG0, r[7] REG1, r[8] REG2 = Kanal
    snprintf(buf, sizeof buf, "Adresse 0x%02X%02X, Kanal %u = %.3f MHz", r[3], r[4], r[8], 410.125f + r[8]);
  } else {
    snprintf(buf, sizeof buf, "%u Byte Antwort", unsigned(n));
  }
  report("Parameter lesen", ok, buf);

  digitalWrite(PIN_LORA_M1, LOW);              // zurück in Modus 0 (transparent)
  waitAux(1000);
}

static void checkGps() {
  Serial.println("\n6. GPS (Serial1, Modul in der Spitze, optional)");
  for (long baud : {38400L, 9600L}) {
    Serial1.begin(baud);
    while (Serial1.available()) Serial1.read();
    uint32_t dollars = 0;
    const uint32_t t0 = millis();
    while (millis() - t0 < 1500) {
      if (Serial1.available() && Serial1.read() == '$') ++dollars;
    }
    if (dollars > 2) {
      char buf[48];
      snprintf(buf, sizeof buf, "%lu NMEA-Zeilen bei %ld Bd", (unsigned long)dollars, baud);
      report("NMEA", true, buf);
      return;
    }
  }
  report("NMEA", false, "nichts empfangen (angesteckt?)");
}

void setup() {
  safeOutputs();
  bus.begin();
  FastLED.addLeds<WS2812B, PIN_LED_DATA, GRB>(leds, LED_COUNT_ONBOARD);
  fill_solid(leds, LED_COUNT_ONBOARD, CRGB(0, 0, 40));
  FastLED.show();

  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 4000) {}
  Serial.println("\n=== Kartonaut Mainboard rev B: Inbetriebnahme ===");
  Serial.printf("DRV8833 nFAULT: %s\n", digitalRead(PIN_MOT_FAULT) ? "ok (hoch)" : "FEHLER (tief)");

  checkMux();
  checkImu();
  Serial.println("\n3. Barometer BMP390 (CS Y1, Y2)");
  ok_baro  = checkBaro(baro,  "BMP390 #1", true);
  ok_baro2 = checkBaro(baro2, "BMP390 #2", false);
  checkIna();
  checkLora();
  checkGps();

  const bool all = ok_imu && ok_baro && ok_ina;
  fill_solid(leds, LED_COUNT_ONBOARD, all ? CRGB(0, 60, 0) : CRGB(60, 0, 0));
  FastLED.show();
  digitalWrite(PIN_BUZZER, HIGH); delay(all ? 80 : 600); digitalWrite(PIN_BUZZER, LOW);
  Serial.printf("\nErgebnis: %s. Ab jetzt Messwerte im Sekundentakt.\n\n", all ? "alles da" : "FEHLER, siehe oben");
}

void loop() {
  static uint32_t last = 0;
  if (millis() - last < 1000) return;
  last = millis();

  if (ok_imu) {
    ImuSample s;
    imu.read(s);
    Serial.printf("IMU a=[%6.2f %6.2f %6.2f] m/s²  w=[%7.2f %7.2f %7.2f] °/s  ",
                  s.acc_ms2[0], s.acc_ms2[1], s.acc_ms2[2], s.gyro_dps[0], s.gyro_dps[1], s.gyro_dps[2]);
  }
  if (ok_baro) {
    float p, t;
    if (baro.read(p, t)) Serial.printf("p=%.0f Pa  ", p);
  }
  if (ok_ina) {
    PowerSample s;
    ina.read(s);
    Serial.printf("2S %.2f V %.0f mA  ", s.bus_V, s.current_A * 1000.0f);
  }
  Serial.printf("1S %.2f V  ARM %.2f V\n", bus.readMuxInputV(Mux::VBAT1), bus.readMuxInputV(Mux::ARM));
}
