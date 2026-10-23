#include "Tests.h"
#include "Board.h"
#include "Watchdog.h"
#include "Nmea.h"
#include <SD.h>
#include <math.h>

using namespace board;

// ---------------------------------------------------------------- Analogmux
Res testMux() {
  Res r = Res::OK;
  const float v_gnd = bus.readMuxV(rb::Mux::GND);
  const bool gnd_ok = v_gnd < 0.05f;
  proto::test("mux_gnd", gnd_ok, "%.3f V am ADC (Y7)", v_gnd);
  if (!gnd_ok) r = Res::FEHL;

  const float v1 = vbat1();
  const bool v1_ok = v1 > 3.0f && v1 < 4.35f;
  proto::test("mux_vbat1", v1_ok, "%.3f V (1S, 3,0..4,35 V)", v1);
  if (!v1_ok) r = Res::FEHL;

  const float v2 = vbat2();
  if (v2 < 1.0f) {
    proto::test("mux_vbat2", Res::SKIP, "%.2f V, 2S nicht versorgt", v2);
    proto::test("mux_arm", Res::SKIP, "ohne 2S");
    for (int i = 0; i < 4; ++i) {
      char n[16]; snprintf(n, sizeof n, "mux_pyro%d", i + 1);
      proto::test(n, Res::SKIP, "ohne 2S");
    }
    return proto::worst(r, Res::SKIP);
  }
  const bool v2_ok = v2 > 6.0f && v2 < 8.6f;
  proto::test("mux_vbat2", v2_ok, "%.3f V (2S, 6,0..8,6 V)", v2);
  if (!v2_ok) r = Res::FEHL;

  const float va = armV();
  proto::test("mux_arm", Res::OK, "%.2f V %s", va, va > 5.0f ? "SCHARF" : "sicher");
  // Durchgang nur bei scharfem Schalter sichtbar: Sense ≈ ARM-Spannung
  for (int i = 0; i < 4; ++i) {
    char n[16]; snprintf(n, sizeof n, "mux_pyro%d", i + 1);
    const float vp = pyroV(i);
    if (!rb::PYRO_FITTED[i]) { proto::test(n, Res::SKIP, "%.2f V, Kanal DNP", vp); continue; }
    if (va < 5.0f) { proto::test(n, Res::SKIP, "%.2f V, ARM nicht scharf", vp); continue; }
    proto::test(n, Res::OK, "%.2f V %s", vp, vp > 0.8f * va ? "Durchgang" : "offen");
  }
  return r;
}

// ---------------------------------------------------------------- IMU
Res testImu() {
  Res r = Res::OK;
  const uint8_t id = imu.whoAmI();
  proto::test("imu_whoami", id == imu.expectedWhoAmI(), "0x%02X soll 0x%02X (%s)", id, imu.expectedWhoAmI(), imu.name());
  if (id != imu.expectedWhoAmI()) return Res::FEHL;
  st.imu = imu.begin();
  proto::test("imu_config", st.imu, "Flugkonfiguration zurückgelesen");
  if (!st.imu) return Res::FEHL;

  // Datenrate: neue Sätze in 500 ms zählen
  uint32_t n = 0;
  const uint32_t t0 = millis();
  ImuSample s;
  while (millis() - t0 < 500) if (imu.dataReady()) { imu.read(s); ++n; }
  const float hz = n * 2.0f;
  const bool rate_ok = fabsf(hz - imu.sampleRateHz()) < 0.1f * imu.sampleRateHz();
  proto::test("imu_rate", rate_ok, "%.0f Hz soll %.0f", hz, imu.sampleRateHz());
  if (!rate_ok) r = Res::FEHL;

  // Ruhe: |a| ≈ 1 g, Drehrate klein
  float acc[3] = {0, 0, 0}, gyr[3] = {0, 0, 0};
  int k = 0;
  const uint32_t t1 = millis();
  while (millis() - t1 < 300) {
    if (!imu.dataReady()) continue;
    imu.read(s);
    for (int i = 0; i < 3; ++i) { acc[i] += s.acc_ms2[i]; gyr[i] += s.gyro_dps[i]; }
    ++k;
  }
  if (k == 0) { proto::test("imu_rest", Res::FEHL, "keine Daten"); return Res::FEHL; }
  for (int i = 0; i < 3; ++i) { acc[i] /= k; gyr[i] /= k; }
  const float a = sqrtf(acc[0] * acc[0] + acc[1] * acc[1] + acc[2] * acc[2]);
  const float w = sqrtf(gyr[0] * gyr[0] + gyr[1] * gyr[1] + gyr[2] * gyr[2]);
  const bool rest_ok = fabsf(a - 9.81f) < 0.8f && w < 5.0f;
  proto::test("imu_rest", rest_ok, "|a| %.2f m/s2 a=[%.2f %.2f %.2f] |w| %.2f dps T %.1f C", a, acc[0], acc[1], acc[2], w, s.temp_c);
  if (!rest_ok) r = Res::FEHL;

  ImuSelfTest stt;
  imu.selfTest(stt);
  proto::test("imu_selftest_gyro", stt.gyro_ok, "Antwort %.0f %.0f %.0f dps, Verhältnis %.2f %.2f %.2f, Offset %.1f %.1f %.1f",
              stt.gyro_resp_dps[0], stt.gyro_resp_dps[1], stt.gyro_resp_dps[2],
              stt.gyro_ratio[0], stt.gyro_ratio[1], stt.gyro_ratio[2],
              stt.gyro_offset_dps[0], stt.gyro_offset_dps[1], stt.gyro_offset_dps[2]);
  proto::test("imu_selftest_acc", stt.acc_ok, "Antwort %.3f %.3f %.3f g, Verhältnis %.2f %.2f %.2f",
              stt.acc_resp_g[0], stt.acc_resp_g[1], stt.acc_resp_g[2], stt.acc_ratio[0], stt.acc_ratio[1], stt.acc_ratio[2]);
  if (!stt.ok) r = Res::FEHL;
  st.imu = imu.begin();
  return r;
}

// ---------------------------------------------------------------- Barometer
static Res testOneBaro(BMP390& b, const char* name, bool fitted, bool& ok_flag) {
  ok_flag = b.begin();
  if (!ok_flag) {
    if (!fitted) { proto::test(name, Res::SKIP, "nicht bestückt (DNP), Chip-ID 0x%02X", b.chipId()); return Res::SKIP; }
    proto::test(name, Res::FEHL, "keine Antwort, Chip-ID 0x%02X", b.chipId());
    return Res::FEHL;
  }
  float p = 0, t = 0;
  const uint32_t t0 = millis();
  while (!b.read(p, t) && millis() - t0 < 300) delay(5);
  const bool pl = p > 80000.0f && p < 110000.0f && t > -20.0f && t < 70.0f;
  proto::test(name, pl, "Chip-ID 0x%02X%s, %.0f Pa, %.1f C", b.chipId(),
              b.chipId() == BMP390::CHIP_ID_BMP388 ? " (BMP388)" : "", p, t);
  return pl ? Res::OK : Res::FEHL;
}

Res testBaro() {
  const Res a = testOneBaro(baro, "baro1", true, st.baro);
  const Res b = testOneBaro(baro2, "baro2", rb::BARO2_FITTED, st.baro2);
  return proto::worst(a, b);
}

// ---------------------------------------------------------------- Magnetometer
Res testMag() {
  const uint8_t id = mag.whoAmI();
  proto::test("mag_whoami", id == LIS3MDL::WHO_AM_I_VALUE, "0x%02X soll 0x3D (LIS3MDL, 0x%02X)", id, rb::I2C_ADDR_LIS3MDL);
  if (id != LIS3MDL::WHO_AM_I_VALUE) return Res::FEHL;
  st.mag = mag.begin();
  proto::test("mag_config", st.mag, "80 Hz, +-4 gauss, UHP");
  if (!st.mag) return Res::FEHL;
  Res r = Res::OK;
  delay(30);
  MagSample s;
  float sum[3] = {0, 0, 0};
  int n = 0;
  const uint32_t t0 = millis();
  while (millis() - t0 < 250) {
    if (mag.dataReady() && mag.read(s)) { for (int i = 0; i < 3; ++i) sum[i] += s.mag_gauss[i]; ++n; }
  }
  if (n == 0) { proto::test("mag_read", Res::FEHL, "keine Daten"); return Res::FEHL; }
  for (int i = 0; i < 3; ++i) sum[i] /= n;
  float c[3];
  cal::applyMag(calib, sum, c);
  const float bmag = sqrtf(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]);
  // Erdfeld 0,25..0,65 gauss; unkalibriert und neben Strömen kann es abweichen, darum weites Fenster
  const bool pl = bmag > 0.1f && bmag < 1.5f;
  proto::test("mag_read", pl, "%d Werte, roh [%.3f %.3f %.3f] gauss, |B| %.3f %s, T %.1f C", n, sum[0], sum[1], sum[2], bmag,
              cal::has(calib, cal::MAG) ? "kalibriert" : "unkalibriert", s.temp_c);
  if (!pl) r = Res::FEHL;
  MagSelfTest stt;
  mag.selfTest(stt);
  proto::test("mag_selftest", stt.ok, "Differenz %.2f %.2f %.2f gauss (X/Y 1,0..3,0, Z 0,1..1,0)", stt.diff_gauss[0], stt.diff_gauss[1], stt.diff_gauss[2]);
  if (!stt.ok) r = Res::FEHL;
  return r;
}

// ---------------------------------------------------------------- SHT40
Res testSht() {
  st.sht = sht.begin();
  proto::test("sht_serial", st.sht, "Seriennummer %08lX (0x%02X)", (unsigned long)sht.serial(), rb::I2C_ADDR_SHT40);
  if (!st.sht) return Res::FEHL;
  ShtSample s;
  const bool ok = sht.read(s);
  const bool pl = ok && s.temp_c > -10.0f && s.temp_c < 60.0f && s.rh_pct > 2.0f && s.rh_pct < 98.0f;
  proto::test("sht_read", pl, "%.2f C, %.1f %%rF, CRC %s", s.temp_c, s.rh_pct, ok ? "ok" : "falsch");
  return pl ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- ADXL375 (DNP)
Res testAdxl() {
  if (!adxl.present()) {
    proto::test("adxl_present", rb::ADXL375_FITTED ? Res::FEHL : Res::SKIP, "kein ACK auf 0x%02X%s", rb::I2C_ADDR_ADXL375,
                rb::ADXL375_FITTED ? "" : ", nicht bestückt (DNP)");
    return rb::ADXL375_FITTED ? Res::FEHL : Res::SKIP;
  }
  const uint8_t id = adxl.devId();
  proto::test("adxl_present", id == ADXL375::DEVID_VALUE, "DEVID 0x%02X soll 0xE5", id);
  st.adxl = adxl.begin();
  if (!st.adxl) return Res::FEHL;
  float a[3];
  if (!adxl.read(a)) { proto::test("adxl_read", Res::FEHL, "Lesen"); return Res::FEHL; }
  const float n = sqrtf(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
  const bool pl = fabsf(n - 1.0f) < 0.4f;    // 49 mg/LSB: grob
  proto::test("adxl_read", pl, "|a| %.2f g [%.2f %.2f %.2f]", n, a[0], a[1], a[2]);
  return pl ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- INA239
Res testIna() {
  const uint16_t man = ina.manufacturerId(), dev = ina.deviceId();
  const bool id_ok = man == INA239::MANUFACTURER_TI && (dev >> 4) == INA239::DEVICE_ID_INA239;
  proto::test("ina_id", id_ok, "Hersteller 0x%04X Gerät 0x%04X", man, dev);
  if (!id_ok) return Res::FEHL;
  st.ina = ina.begin();
  proto::test("ina_config", st.ina, "ADC_CONFIG zurückgelesen");
  if (!st.ina) return Res::FEHL;
  delay(120);
  PowerSample s;
  ina.read(s);
  if (!have2S()) {
    proto::test("ina_bus", Res::SKIP, "%.2f V, 2S nicht versorgt", s.bus_V);
    return Res::SKIP;
  }
  const float v2 = vbat2();
  const bool bus_ok = s.bus_V > 6.0f && s.bus_V < 8.6f && fabsf(s.bus_V - v2) < 0.3f;
  proto::test("ina_bus", bus_ok, "VSERVO %.3f V, Mux 2S %.3f V, Strom %.1f mA, Die %.1f C", s.bus_V, v2, s.current_A * 1000.0f, s.die_temp_C);
  return bus_ok ? Res::OK : Res::FEHL;
}

Res testInaLoad() {
  if (!st.ina && !(st.ina = ina.begin())) { proto::test("ina_load", Res::FEHL, "INA239 antwortet nicht"); return Res::FEHL; }
  if (!have2S()) { proto::test("ina_load", Res::SKIP, "2S nicht versorgt"); return Res::SKIP; }
  if (proto::wait("Last an VSERVO anschließen (z. B. 10 Ohm / 5 W zwischen + und - einer Servobuchse), dann Enter") != 1) {
    proto::test("ina_load", Res::SKIP, "abgebrochen"); return Res::SKIP;
  }
  delay(150);
  float i_sum = 0, v_sum = 0;
  for (int k = 0; k < 5; ++k) { PowerSample s; ina.read(s); i_sum += s.current_A; v_sum += s.bus_V; delay(60); }
  const float i = (i_sum / 5 - calib.ina_offset_a) * calib.ina_gain, v = v_sum / 5;
  const bool ok = i > 0.1f;
  proto::test("ina_load", ok, "%.3f A bei %.2f V (%.1f W)%s", i, v, i * v, ok ? "" : ", Strom < 0,1 A: Last angeschlossen?");
  proto::wait("Last wieder abnehmen, Enter");
  return ok ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- LEDs, Summer, Kamera
static Res askSeen(const char* name, const char* what) {
  const int a = proto::wait("%s? (Enter = ja, n = nein, q = abbrechen)", what);
  if (a < 0) { proto::test(name, Res::SKIP, "abgebrochen"); return Res::SKIP; }
  proto::test(name, a == 1, a == 1 ? "bestätigt" : "nicht gesehen");
  return a == 1 ? Res::OK : Res::FEHL;
}

Res testLeds() {
  struct { const char* name; const char* text; CRGB c; } steps[] = {
    {"led_rot", "Leuchten beide LEDs rot", CRGB(80, 0, 0)},
    {"led_gruen", "Leuchten beide LEDs grün", CRGB(0, 80, 0)},
    {"led_blau", "Leuchten beide LEDs blau", CRGB(0, 0, 80)},
    {"led_weiss", "Leuchten beide LEDs weiß", CRGB(60, 60, 60)},
  };
  Res r = Res::OK;
  for (auto& s : steps) {
    setLeds(s.c);
    const Res a = askSeen(s.name, s.text);
    r = proto::worst(r, a);
    if (a == Res::SKIP) break;
  }
  setLeds(CRGB::Black);
  return r;
}

Res testBuzzer() {
  for (int i = 0; i < 3; ++i) { beep(80); delay(120); }
  return askSeen("buzzer", "Hat der Summer dreimal gepiept");
}

Res testCam() {
  proto::info("CAM_TRIG 500 ms hoch (J_CAM Pin 2 über 1 k)");
  digitalWrite(rb::PIN_CAM_TRIG, HIGH);
  delay(500);
  digitalWrite(rb::PIN_CAM_TRIG, LOW);
  return askSeen("cam_trigger", "Hat die Kamera ausgelöst bzw. war der Pegel an J_CAM Pin 2 zu sehen");
}

// ---------------------------------------------------------------- Servos
static const char* SERVO_NAMES[4] = {"yaw", "pitch", "chute", "legs"};

Res testServo(int i, const char* mode) {
  if (i < 0 || i > 3) { proto::test("servo", Res::FEHL, "Kanal 1..4"); return Res::FEHL; }
  char name[24];
  snprintf(name, sizeof name, "servo%d_%s", i + 1, SERVO_NAMES[i]);
  if (!have2S()) { proto::test(name, Res::SKIP, "2S nicht versorgt, VSERVO fehlt"); return Res::SKIP; }
  int lo, hi;
  servoLimitsUs(i, lo, hi);
  const int c = constrain(int(calib.servo_center_us[i]), lo, hi);
  const int mn = constrain(int(calib.servo_min_us[i]), lo, hi), mx = constrain(int(calib.servo_max_us[i]), lo, hi);
  proto::info("%s: Fenster %d..%d us (Config.h), Mitte %d, Grenzen %d..%d us (Kalibrierung)", name, lo, hi, c, mn, mx);

  if (strncmp(mode, "us", 2) == 0) {
    const int us = atoi(mode + 2);
    servoWriteUs(i, us);
    delay(600);
    proto::test(name, Res::OK, "%d us (geklemmt auf %d..%d)", constrain(us, lo, hi), lo, hi);
  } else if (strcmp(mode, "min") == 0) {
    servoWriteUs(i, c); delay(500); servoWriteUs(i, mn); delay(800);
    proto::test(name, Res::OK, "Grenze min %d us", mn);
  } else if (strcmp(mode, "max") == 0) {
    servoWriteUs(i, c); delay(500); servoWriteUs(i, mx); delay(800);
    proto::test(name, Res::OK, "Grenze max %d us", mx);
  } else if (strcmp(mode, "sweep") == 0) {
    servoWriteUs(i, c); delay(500);
    for (int us = c; us <= mx; us += 5) { servoWriteUs(i, us); delay(10); }
    for (int us = mx; us >= mn; us -= 5) { servoWriteUs(i, us); delay(10); }
    for (int us = mn; us <= c; us += 5) { servoWriteUs(i, us); delay(10); }
    proto::test(name, Res::OK, "Durchlauf %d -> %d -> %d -> %d us", c, mx, mn, c);
  } else {
    servoWriteUs(i, c); delay(800);
    proto::test(name, Res::OK, "Mitte %d us", c);
  }
  const int a = proto::wait("Hat sich Servo %d (%s) wie gemeldet bewegt? (Enter = ja, n = nein)", i + 1, SERVO_NAMES[i]);
  servoWriteUs(i, c); delay(400);
  servoRelease(i);
  if (a < 0) return Res::SKIP;
  if (a == 0) { proto::test(name, Res::FEHL, "Bewegung nicht bestätigt"); return Res::FEHL; }
  return Res::OK;
}

// ---------------------------------------------------------------- Rollmotor
Res testMotor() {
  const bool fault_idle = !digitalRead(rb::PIN_MOT_FAULT);
  proto::test("motor_nfault_idle", !fault_idle, "nFAULT %s (schlafend)", fault_idle ? "TIEF" : "hoch");
  if (!have2S()) { proto::test("motor_pulse", Res::SKIP, "2S nicht versorgt"); return Res::SKIP; }
  if (proto::wait("Rollmotor: je ein 300-ms-Puls mit 30 %% in beide Richtungen. Motor frei drehbar? Enter") != 1) {
    proto::test("motor_pulse", Res::SKIP, "abgebrochen"); return Res::SKIP;
  }
  analogWriteFrequency(rb::PIN_MOT_IN1, 20000);
  analogWriteFrequency(rb::PIN_MOT_IN2, 20000);
  analogWriteResolution(12);
  digitalWrite(rb::PIN_MOT_NSLEEP, HIGH);
  delay(2);
  bool fault = false;
  float i_fwd = 0, i_rev = 0;
  for (int dir = 0; dir < 2; ++dir) {
    analogWrite(dir == 0 ? rb::PIN_MOT_IN1 : rb::PIN_MOT_IN2, 1230);   // 30 %
    analogWrite(dir == 0 ? rb::PIN_MOT_IN2 : rb::PIN_MOT_IN1, 0);
    const uint32_t t0 = millis();
    while (millis() - t0 < 300) { if (!digitalRead(rb::PIN_MOT_FAULT)) fault = true; }
    if (st.ina) { PowerSample s; ina.read(s); (dir == 0 ? i_fwd : i_rev) = s.current_A; }
    analogWrite(rb::PIN_MOT_IN1, 0);
    analogWrite(rb::PIN_MOT_IN2, 0);
    delay(400);
  }
  digitalWrite(rb::PIN_MOT_NSLEEP, LOW);
  digitalWrite(rb::PIN_MOT_IN1, LOW); pinMode(rb::PIN_MOT_IN1, OUTPUT);
  digitalWrite(rb::PIN_MOT_IN2, LOW); pinMode(rb::PIN_MOT_IN2, OUTPUT);
  proto::test("motor_nfault_run", !fault, "nFAULT während der Pulse %s", fault ? "TIEF (Überstrom/Temperatur?)" : "hoch");
  const int a = proto::wait("Hat der Motor kurz vor und zurück gedreht? (Strom %.0f / %.0f mA) Enter = ja, n = nein", i_fwd * 1000, i_rev * 1000);
  if (a < 0) { proto::test("motor_pulse", Res::SKIP, "abgebrochen"); return Res::SKIP; }
  proto::test("motor_pulse", a == 1 && !fault, a == 1 ? "bestätigt" : "nicht bestätigt");
  return (a == 1 && !fault) ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- Pyro (nur Lämpchen)
Res testPyro(int ch, int pulse_ms) {
  char name[24];
  snprintf(name, sizeof name, "pyro%d_fire", ch + 1);
  if (ch < 0 || ch > 3) { proto::test("pyro", Res::FEHL, "Kanal 1..4"); return Res::FEHL; }
  if (!rb::PYRO_FITTED[ch]) { proto::test(name, Res::SKIP, "Kanal DNP"); return Res::SKIP; }
  if (!have2S()) { proto::test(name, Res::SKIP, "2S nicht versorgt"); return Res::SKIP; }
  const float va = armV();
  if (va < 5.0f) { proto::test(name, Res::SKIP, "ARM nicht scharf (%.2f V), Schlüsselschalter", va); return Res::SKIP; }
  const float vp = pyroV(ch);
  if (vp < 0.8f * va) { proto::test(name, Res::SKIP, "kein Durchgang (%.2f V von %.2f V): Lämpchen angeschlossen?", vp, va); return Res::SKIP; }
  pulse_ms = constrain(pulse_ms, 20, 1000);
  if (!proto::confirm("Pyro %d zünden, %d ms. NUR Lämpchen oder 2-Ohm-Widerstand, KEINE LADUNG. Tippe JA", ch + 1, pulse_ms)) {
    proto::test(name, Res::SKIP, "nicht bestätigt"); return Res::SKIP;
  }
  setLeds(CRGB(80, 0, 0));
  const uint8_t pin = rb::PYRO_FIRE_PINS[ch];
  digitalWrite(pin, HIGH);
  const uint32_t t0 = millis();
  float v_on = NAN;
  while (millis() - t0 < uint32_t(pulse_ms)) {
    if (isnan(v_on) && millis() - t0 > 30) v_on = pyroV(ch);   // FET zieht PYRO_NEG nach GND_PWR
  }
  digitalWrite(pin, LOW);
  setLeds(CRGB::Black);
  delay(100);
  const float v_after = pyroV(ch);
  const bool ok = v_on < 0.3f * va && v_after > 0.8f * va && digitalRead(pin) == LOW;
  proto::test(name, ok, "Puls %d ms, Sense bei Zündung %.2f V (soll < %.2f), danach %.2f V, Ausgang tief", pulse_ms, v_on, 0.3f * va, v_after);
  return ok ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- LoRa E22
static bool loraWaitAux(uint32_t timeout_ms) {
  const uint32_t t0 = millis();
  while (!digitalRead(rb::PIN_LORA_AUX)) if (millis() - t0 > timeout_ms) return false;
  return true;
}

static long loraUartBaud(uint8_t reg0) {
  static const long b[8] = {1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200};
  return b[reg0 >> 5];
}

Res testLora() {
  Res r = Res::OK;
  // Modus 2 (Konfiguration): M1 = 1, M0 = 0; UART fest 9600 8N1
  digitalWrite(rb::PIN_LORA_M0, LOW);  pinMode(rb::PIN_LORA_M0, OUTPUT);
  digitalWrite(rb::PIN_LORA_M1, HIGH); pinMode(rb::PIN_LORA_M1, OUTPUT);
  Serial8.begin(9600);
  delay(50);
  const bool aux = loraWaitAux(1000);
  proto::test("lora_aux", aux, "AUX %s", aux ? "hoch (bereit)" : "bleibt tief");
  if (!aux) r = Res::FEHL;

  while (Serial8.available()) Serial8.read();
  const uint8_t cmd[3] = {0xC1, 0x00, 0x09};   // Register 00H..08H lesen
  Serial8.write(cmd, 3);
  uint8_t rg[12];
  size_t n = 0;
  const uint32_t t0 = millis();
  while (n < sizeof rg && millis() - t0 < 300) if (Serial8.available()) rg[n++] = Serial8.read();
  const bool cfg_ok = n == sizeof rg && rg[0] == 0xC1;
  long baud = 9600;
  bool rssi_byte = false;
  if (cfg_ok) {
    baud = loraUartBaud(rg[6]);
    rssi_byte = rg[9] & 0x80;
    proto::test("lora_config", true, "Adresse 0x%02X%02X NetID %u Kanal %u = %.3f MHz UART %ld Bd Luftrate %u Leistung %u RSSI-Byte %s",
                rg[3], rg[4], rg[5], rg[8], 410.125f + rg[8], baud, rg[6] & 7, rg[7] & 3, rssi_byte ? "an" : "aus");
  } else {
    proto::test("lora_config", false, "%u Byte Antwort", unsigned(n));
    r = Res::FEHL;
  }
  // zurück in Modus 0 (transparent), Ping
  digitalWrite(rb::PIN_LORA_M1, LOW);
  loraWaitAux(1000);
  if (!cfg_ok) { proto::test("lora_ping", Res::SKIP, "ohne Konfiguration"); return r; }
  Serial8.begin(baud);
  delay(20);
  while (Serial8.available()) Serial8.read();
  Serial8.print("KARTONAUT PING 1\n");
  Serial8.flush();
  char reply[96];
  size_t len = 0;
  int rssi_dbm = 0;
  bool got = false;
  const uint32_t t1 = millis();
  while (millis() - t1 < 3000 && !got) {
    if (!Serial8.available()) continue;
    const int c = Serial8.read();
    if (c == '\n') {
      reply[len] = 0;
      if (strstr(reply, "PONG")) {
        got = true;
        if (rssi_byte) {   // E22: letztes Byte des Pakets ist RSSI, Wert = -(256 - Byte) dBm
          delay(20);
          if (Serial8.available()) rssi_dbm = -(256 - Serial8.read());
        }
      }
      len = 0;
    } else if (len + 1 < sizeof reply) {
      reply[len++] = char(c);
    }
  }
  if (got) proto::test("lora_ping", true, "Antwort \"%s\"%s%d dBm", reply, rssi_byte ? ", RSSI " : ", RSSI nicht aktiviert ", rssi_dbm);
  else { proto::test("lora_ping", Res::SKIP, "keine Antwort in 3 s (Bodenstation an, gleicher Kanal?)"); r = proto::worst(r, Res::SKIP); }
  return r;
}

// ---------------------------------------------------------------- GPS
Res testGps() {
  NmeaState s;
  long found = 0;
  for (long baud : {38400L, 9600L}) {
    Serial1.begin(baud);
    while (Serial1.available()) Serial1.read();
    char line[120];
    size_t len = 0;
    const uint32_t t0 = millis();
    while (millis() - t0 < 5000) {
      if (!Serial1.available()) continue;
      const int c = Serial1.read();
      if (c == '\n' || c == '\r') {
        line[len] = 0;
        if (len > 6) nmea::parse(s, line);
        len = 0;
      } else if (len + 1 < sizeof line) {
        line[len++] = char(c);
      }
    }
    if (s.sentences > 2) { found = baud; break; }
  }
  if (!found) {
    proto::test("gps_nmea", Res::FEHL, "keine NMEA-Sätze bei 38400/9600 Bd (Modul angesteckt, 3V3_RF?)%s",
                s.bad_checksum ? ", Prüfsummenfehler" : "");
    proto::test("gps_fix", Res::SKIP, "ohne NMEA");
    return Res::FEHL;
  }
  proto::test("gps_nmea", true, "%d Sätze bei %ld Bd, %d Prüfsummenfehler, UTC %s", s.sentences, found, s.bad_checksum, s.time_utc);
  if (s.fix_quality > 0 || s.rmc_valid) {
    proto::test("gps_fix", true, "Fix %d, %d Satelliten, HDOP %.1f, %.5f %.5f, %.0f m", s.fix_quality, s.satellites, s.hdop, s.lat, s.lon, s.alt_m);
    return Res::OK;
  }
  proto::test("gps_fix", Res::SKIP, "kein Fix, %d Satelliten (freie Sicht zum Himmel?)", s.satellites);
  return Res::SKIP;
}

// ---------------------------------------------------------------- SD-Karte
Res testSd() {
  if (!SD.begin(BUILTIN_SDCARD)) { proto::test("sd_init", Res::FEHL, "keine Karte oder Dateisystem (FAT32/exFAT)"); return Res::FEHL; }
  proto::test("sd_init", true, "Karte erkannt");
  const char* fn = "REVBTEST.BIN";
  SD.remove(fn);
  File f = SD.open(fn, FILE_WRITE);
  if (!f) { proto::test("sd_write", Res::FEHL, "Datei anlegen"); return Res::FEHL; }
  static uint8_t block[4096];
  for (size_t i = 0; i < sizeof block; ++i) block[i] = uint8_t(i * 7 + 3);
  const int blocks = 256;   // 1 MiB
  uint32_t t_max = 0;
  const uint32_t t0 = micros();
  bool wok = true;
  for (int b = 0; b < blocks && wok; ++b) {
    const uint32_t tb = micros();
    wok = f.write(block, sizeof block) == sizeof block;
    const uint32_t d = micros() - tb;
    if (d > t_max) t_max = d;
  }
  f.close();
  const float secs = (micros() - t0) / 1e6f;
  const float mbs = blocks * sizeof block / 1048576.0f / secs;
  proto::test("sd_write", wok, "1 MiB in %.2f s = %.2f MB/s, längster 4-KiB-Block %lu us", secs, mbs, (unsigned long)t_max);
  if (!wok) return Res::FEHL;

  f = SD.open(fn, FILE_READ);
  if (!f) { proto::test("sd_read", Res::FEHL, "Datei öffnen"); return Res::FEHL; }
  static uint8_t rbuf[4096];
  bool rok = f.size() == uint64_t(blocks) * sizeof block;
  const uint32_t t1 = micros();
  for (int b = 0; b < blocks && rok; ++b) {
    rok = f.read(rbuf, sizeof rbuf) == int(sizeof rbuf) && memcmp(rbuf, block, sizeof block) == 0;
  }
  f.close();
  const float rs = (micros() - t1) / 1e6f;
  proto::test("sd_read", rok, "1 MiB in %.2f s = %.2f MB/s, Inhalt %s", rs, blocks * sizeof block / 1048576.0f / rs, rok ? "stimmt" : "FALSCH");
  SD.remove(fn);
  return rok ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- Loop-Timing
Res testTiming() {
  // 100-Hz-Schleife wie im Flug: IMU, Baro, Mux (3 Kanäle), Magnetometer, INA alle 100 ms
  constexpr uint32_t period_us = 10000;
  const int loops = 300;
  uint32_t t_max = 0, t_sum = 0, overruns = 0;
  uint32_t next = micros() + period_us;
  ImuSample s; float p, t; MagSample m;
  for (int k = 0; k < loops; ++k) {
    while (int32_t(micros() - next) < 0) {}
    const uint32_t t0 = micros();
    if (st.imu && imu.dataReady()) imu.read(s);
    if (st.baro) baro.read(p, t);
    (void)vbat1(); (void)vbat2(); (void)armV();
    if (st.mag) mag.read(m);
    if (st.ina && k % 10 == 0) { PowerSample ps; ina.read(ps); }
    const uint32_t d = micros() - t0;
    t_sum += d;
    if (d > t_max) t_max = d;
    if (d > period_us) ++overruns;
    next += period_us;
  }
  const bool ok = overruns == 0 && t_max < period_us / 2;
  proto::test("timing_loop", ok, "%d Durchläufe bei 100 Hz: Mittel %lu us, Maximum %lu us, Überläufe %lu",
              loops, (unsigned long)(t_sum / loops), (unsigned long)t_max, (unsigned long)overruns);
  return ok ? Res::OK : Res::FEHL;
}

// ---------------------------------------------------------------- Watchdog
Res testWatchdog(bool fire) {
  if (fire) {
    proto::info("Watchdog scharf (1 s), wird nicht mehr bedient: Neustart folgt, Konsole neu verbinden");
    proto::end("watchdog fire", Res::OK);
    Serial.flush();
    wdBegin(1000);
    for (;;) {}
  }
  wdBegin(2000);
  const uint32_t t0 = millis();
  while (millis() - t0 < 3000) { wdFeed(); delay(100); }
  wdEnd();
  delay(2500);   // wäre er noch scharf, käme hier der Neustart
  proto::test("watchdog_feed", true, "2-s-Watchdog 3 s lang bedient, kein Neustart; danach abgeschaltet und 2,5 s ohne Bedienung überstanden");
  return Res::OK;
}
