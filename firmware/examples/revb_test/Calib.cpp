#include "Calib.h"
#include "Board.h"
#include "EllipsoidFit.h"
#include "AxisFit.h"
#include <math.h>

using namespace board;

static const char* AXIS[3] = {"x", "y", "z"};

// Mittelwert der IMU über ms Millisekunden; false bei Bewegung (> max_dps Spanne) oder Abbruch
static bool imuAverage(uint32_t ms, float acc[3], float gyr[3], float& temp, float max_dps, float* std_dps = nullptr) {
  double sa[3] = {0, 0, 0}, sg[3] = {0, 0, 0}, sg2[3] = {0, 0, 0}, st_ = 0;
  float gmin[3] = {1e9, 1e9, 1e9}, gmax[3] = {-1e9, -1e9, -1e9};
  int n = 0;
  ImuSample s;
  const uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    if (proto::abortRequested()) return false;
    if (!imu.dataReady()) continue;
    imu.read(s);
    for (int i = 0; i < 3; ++i) {
      sa[i] += s.acc_ms2[i]; sg[i] += s.gyro_dps[i]; sg2[i] += double(s.gyro_dps[i]) * s.gyro_dps[i];
      if (s.gyro_dps[i] < gmin[i]) gmin[i] = s.gyro_dps[i];
      if (s.gyro_dps[i] > gmax[i]) gmax[i] = s.gyro_dps[i];
    }
    st_ += s.temp_c;
    ++n;
  }
  if (n < 10) return false;
  for (int i = 0; i < 3; ++i) {
    acc[i] = float(sa[i] / n);
    gyr[i] = float(sg[i] / n);
    if (std_dps) std_dps[i] = float(sqrt(fmax(sg2[i] / n - double(gyr[i]) * gyr[i], 0.0)));
    if (gmax[i] - gmin[i] > max_dps) { proto::info("Bewegung auf Achse %s (%.1f dps Spanne)", AXIS[i], gmax[i] - gmin[i]); return false; }
  }
  temp = float(st_ / n);
  return true;
}

Res calGyro(float seconds) {
  if (!st.imu) { proto::test("cal_gyro", Res::FEHL, "IMU nicht bereit"); return Res::FEHL; }
  seconds = constrain(seconds, 2.0f, 120.0f);
  proto::info("Gyro-Nullpunkt: Platine %.0f s ruhig liegen lassen (q bricht ab)", seconds);
  float acc[3], gyr[3], std_[3], temp;
  for (int attempt = 0; attempt < 3; ++attempt) {
    if (imuAverage(uint32_t(seconds * 1000), acc, gyr, temp, 3.0f, std_)) {
      for (int i = 0; i < 3; ++i) { calib.gyro_bias_dps[i] = gyr[i]; calib.gyro_noise_dps[i] = std_[i]; }
      calib.gyro_bias_temp_c = temp;
      calib.valid |= cal::GYRO;
      proto::cal("gyro_bias_dps", "%.4f %.4f %.4f", gyr[0], gyr[1], gyr[2]);
      proto::cal("gyro_bias_temp_c", "%.2f", temp);
      proto::cal("gyro_noise_dps", "%.4f %.4f %.4f", std_[0], std_[1], std_[2]);
      const bool ok = fabsf(gyr[0]) < 5 && fabsf(gyr[1]) < 5 && fabsf(gyr[2]) < 5;
      proto::test("cal_gyro", ok, "Nullpunkt %.3f %.3f %.3f dps bei %.1f C%s", gyr[0], gyr[1], gyr[2], temp, ok ? "" : ", > 5 dps: Bauteil?");
      return ok ? Res::OK : Res::FEHL;
    }
    if (proto::abortRequested()) break;
    proto::info("von vorn (Bewegung erkannt)");
  }
  proto::test("cal_gyro", Res::FEHL, "keine Ruhephase von %.0f s", seconds);
  return Res::FEHL;
}

// Sechs Lagen: Offset = (max + min) / 2, Skalierung = 2 g / (max - min) je Chip-Achse.
// Die Lagen müssen nur jede Achse einmal nach oben und einmal nach unten bringen.
Res calAcc() {
  if (!st.imu) { proto::test("cal_acc", Res::FEHL, "IMU nicht bereit"); return Res::FEHL; }
  static const char* POS[6] = {
    "Platine flach, Bestückseite (Teensy) nach oben",
    "Platine flach, Bestückseite nach unten",
    "Platine hochkant auf die lange Kante mit dem Teensy-USB",
    "Platine hochkant auf die gegenüberliegende lange Kante",
    "Platine hochkant auf die kurze Kante mit der Spitze (GPS/J_STACK)",
    "Platine hochkant auf die gegenüberliegende kurze Kante",
  };
  constexpr float G = 9.80665f;
  float amin[3] = {1e9, 1e9, 1e9}, amax[3] = {-1e9, -1e9, -1e9};
  for (int p = 0; p < 6; ++p) {
    if (proto::wait("Lage %d/6: %s. Ruhig halten, dann Enter", p + 1, POS[p]) != 1) {
      proto::test("cal_acc", Res::SKIP, "abgebrochen"); return Res::SKIP;
    }
    float acc[3], gyr[3], temp;
    if (!imuAverage(1500, acc, gyr, temp, 8.0f)) { proto::info("Lage %d: bewegt, noch einmal", p + 1); --p; continue; }
    proto::info("Lage %d: a = [%.3f %.3f %.3f] m/s2", p + 1, acc[0], acc[1], acc[2]);
    for (int i = 0; i < 3; ++i) { if (acc[i] < amin[i]) amin[i] = acc[i]; if (acc[i] > amax[i]) amax[i] = acc[i]; }
  }
  bool ok = true;
  for (int i = 0; i < 3; ++i) {
    if (amax[i] < 0.8f * G || amin[i] > -0.8f * G) { proto::info("Achse %s nicht nach oben und unten gesehen (%.2f..%.2f)", AXIS[i], amin[i], amax[i]); ok = false; }
  }
  if (!ok) { proto::test("cal_acc", Res::FEHL, "Lagen unvollständig"); return Res::FEHL; }
  float off[3], sc[3];
  for (int i = 0; i < 3; ++i) {
    off[i] = 0.5f * (amax[i] + amin[i]);
    sc[i]  = 2.0f * G / (amax[i] - amin[i]);
    calib.acc_offset_ms2[i] = off[i];
    calib.acc_scale[i] = sc[i];
  }
  calib.valid |= cal::ACC;
  proto::cal("acc_offset_ms2", "%.4f %.4f %.4f", off[0], off[1], off[2]);
  proto::cal("acc_scale", "%.5f %.5f %.5f", sc[0], sc[1], sc[2]);
  const bool plaus = fabsf(off[0]) < 1.0f && fabsf(off[1]) < 1.0f && fabsf(off[2]) < 1.0f
                  && fabsf(sc[0] - 1) < 0.05f && fabsf(sc[1] - 1) < 0.05f && fabsf(sc[2] - 1) < 0.05f;
  proto::test("cal_acc", plaus, "Offset %.3f %.3f %.3f m/s2, Skalierung %.4f %.4f %.4f%s", off[0], off[1], off[2], sc[0], sc[1], sc[2],
              plaus ? "" : " (ungewöhnlich groß)");
  return plaus ? Res::OK : Res::FEHL;
}

static cal::EllipsoidFit ellipsoid;   // 14 KB, deshalb statisch

Res calMag(float seconds) {
  if (!st.mag) { proto::test("cal_mag", Res::FEHL, "Magnetometer nicht bereit"); return Res::FEHL; }
  seconds = constrain(seconds, 10.0f, 180.0f);
  if (proto::wait("Magnetometer: Platine %.0f s langsam um alle Achsen drehen (alle Richtungen, auch über Kopf). Enter zum Start", seconds) != 1) {
    proto::test("cal_mag", Res::SKIP, "abgebrochen"); return Res::SKIP;
  }
  ellipsoid.reset();
  // 80 Hz; so ausdünnen, dass MAX_SAMPLES über die Dauer reichen
  const int keep_every = max(1, int(seconds * 80.0f / cal::EllipsoidFit::MAX_SAMPLES) + 1);
  int k = 0;
  MagSample s;
  const uint32_t t0 = millis();
  uint32_t last_info = t0;
  while (millis() - t0 < uint32_t(seconds * 1000)) {
    if (proto::abortRequested()) { proto::test("cal_mag", Res::SKIP, "abgebrochen"); return Res::SKIP; }
    if (!mag.dataReady() || !mag.read(s)) continue;
    if (k++ % keep_every == 0) ellipsoid.add(s.mag_gauss[0], s.mag_gauss[1], s.mag_gauss[2]);
    if (millis() - last_info > 5000) { last_info = millis(); proto::info("%d Proben, noch %lu s", ellipsoid.count(), (unsigned long)((seconds * 1000 - (millis() - t0)) / 1000)); }
  }
  cal::EllipsoidResult r;
  if (!ellipsoid.solve(r)) { proto::test("cal_mag", Res::FEHL, "Fit nicht lösbar (%d Proben, zu wenig Drehung)", ellipsoid.count()); return Res::FEHL; }
  const bool ok = r.octants == 8 && r.residual_pct < 10.0f && r.field > 0.15f && r.field < 1.2f && r.axis_ratio < 2.0f;
  for (int i = 0; i < 3; ++i) calib.mag_offset_gauss[i] = r.offset[i];
  for (int i = 0; i < 9; ++i) calib.mag_soft_iron[i] = r.soft_iron[i];
  calib.mag_field_gauss = r.field;
  calib.mag_fit_residual_pct = r.residual_pct;
  if (ok) calib.valid |= cal::MAG;
  proto::cal("mag_offset_gauss", "%.5f %.5f %.5f", r.offset[0], r.offset[1], r.offset[2]);
  proto::cal("mag_soft_iron", "%.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f", r.soft_iron[0], r.soft_iron[1], r.soft_iron[2],
             r.soft_iron[3], r.soft_iron[4], r.soft_iron[5], r.soft_iron[6], r.soft_iron[7], r.soft_iron[8]);
  proto::cal("mag_field_gauss", "%.4f", r.field);
  proto::cal("mag_fit", "%d %.2f %d %.3f", r.n, r.residual_pct, r.octants, r.axis_ratio);
  proto::test("cal_mag", ok, "%d Proben, Feld %.3f gauss, Residuum %.1f %%, Oktanten %d/8, Achsen %.2f%s", r.n, r.field, r.residual_pct,
              r.octants, r.axis_ratio, ok ? "" : " (nicht übernommen: Abdeckung oder Residuum)");
  return ok ? Res::OK : Res::FEHL;
}

static cal::AxisFit axisfit;   // 21 KB

// Chip-Achse mit dem größten Betrag und ihr Vorzeichen
static bool dominantAxis(const float a[3], int8_t& axis, int8_t& sign) {
  int best = 0;
  for (int i = 1; i < 3; ++i) if (fabsf(a[i]) > fabsf(a[best])) best = i;
  const float mag = sqrtf(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]);
  if (fabsf(a[best]) < 0.9f * mag) return false;   // schief gehalten
  axis = int8_t(best);
  sign = a[best] > 0 ? 1 : -1;
  return true;
}

Res calAxes() {
  if (!st.imu) { proto::test("cal_axes", Res::FEHL, "IMU nicht bereit"); return Res::FEHL; }
  int8_t map[3], sign[3];
  float acc[3], gyr[3], temp;
  // 1. Körper +z (Rollachse, Spitze) nach oben: die Chip-Achse mit +1 g ist +z
  if (proto::wait("Achsen 1/3: Rakete bzw. Platine mit der SPITZE nach oben halten (Rollachse senkrecht), Enter") != 1) { proto::test("cal_axes", Res::SKIP, "abgebrochen"); return Res::SKIP; }
  if (!imuAverage(1000, acc, gyr, temp, 8.0f) || !dominantAxis(acc, map[2], sign[2])) { proto::test("cal_axes", Res::FEHL, "Lage z unklar oder bewegt"); return Res::FEHL; }
  // 2. Körper +x nach oben
  if (proto::wait("Achsen 2/3: die Seite, die Körper +x sein soll, nach OBEN halten (Spitze waagerecht), Enter") != 1) { proto::test("cal_axes", Res::SKIP, "abgebrochen"); return Res::SKIP; }
  if (!imuAverage(1000, acc, gyr, temp, 8.0f) || !dominantAxis(acc, map[0], sign[0])) { proto::test("cal_axes", Res::FEHL, "Lage x unklar oder bewegt"); return Res::FEHL; }
  if (map[0] == map[2]) { proto::test("cal_axes", Res::FEHL, "x und z zeigen auf dieselbe Chip-Achse"); return Res::FEHL; }
  // 3. y = z × x (rechtshändig): die verbleibende Chip-Achse, Vorzeichen aus der Determinante
  map[1] = int8_t(3 - map[0] - map[2]);
  sign[1] = 1;
  if (!cal::AxisFit::rightHanded(map, sign)) sign[1] = -1;
  for (int i = 0; i < 3; ++i) { calib.imu_axis_map[i] = map[i]; calib.imu_axis_sign[i] = sign[i]; }
  calib.valid |= cal::AXES;
  proto::cal("imu_axis_map", "%d %d %d", map[0], map[1], map[2]);
  proto::cal("imu_axis_sign", "%d %d %d", sign[0], sign[1], sign[2]);
  proto::test("cal_axes_imu", true, "body x = %c%s, y = %c%s, z = %c%s (Chip-Achsen)",
              sign[0] > 0 ? '+' : '-', AXIS[map[0]], sign[1] > 0 ? '+' : '-', AXIS[map[1]], sign[2] > 0 ? '+' : '-', AXIS[map[2]]);

  // 4. Magnetometer gegen die zugeordnete Drehrate
  if (!st.mag) { proto::test("cal_axes_mag", Res::SKIP, "Magnetometer nicht bereit"); return Res::OK; }
  if (!cal::has(calib, cal::MAG)) proto::info("Hinweis: Magnetometer noch nicht kalibriert (cal mag), Hard-Iron verfälscht die Zuordnung");
  if (proto::wait("Achsen 3/3: Platine 20 s um alle Achsen drehen (zügig, alle Richtungen), Enter zum Start") != 1) { proto::test("cal_axes_mag", Res::SKIP, "abgebrochen"); return Res::OK; }
  axisfit.reset();
  const uint32_t t0 = millis();
  uint32_t t_last = micros();
  ImuSample is;
  MagSample ms;
  float w_body[3] = {0, 0, 0};
  while (millis() - t0 < 20000 && !axisfit.full()) {
    if (proto::abortRequested()) break;
    if (imu.dataReady()) {
      imu.read(is);
      float w_chip[3];
      for (int i = 0; i < 3; ++i) w_chip[i] = (is.gyro_dps[i] - calib.gyro_bias_dps[i]) * (float(M_PI) / 180.0f);
      cal::mapAxes(map, sign, w_chip, w_body);
    }
    if (mag.dataReady() && mag.read(ms)) {
      const uint32_t now = micros();
      float corr[3];
      cal::applyMag(calib, ms.mag_gauss, corr);
      axisfit.add(corr, w_body, (now - t_last) * 1e-6f);
      t_last = now;
    }
  }
  cal::AxisResult ar;
  if (!axisfit.solve(ar)) { proto::test("cal_axes_mag", Res::FEHL, "zu wenig Daten (%d)", axisfit.count()); return Res::FEHL; }
  const bool ok = ar.ratio > 2.0f;
  if (ok) for (int i = 0; i < 3; ++i) { calib.mag_axis_map[i] = ar.map[i]; calib.mag_axis_sign[i] = ar.sign[i]; }
  proto::cal("mag_axis_map", "%d %d %d", ar.map[0], ar.map[1], ar.map[2]);
  proto::cal("mag_axis_sign", "%d %d %d", ar.sign[0], ar.sign[1], ar.sign[2]);
  proto::cal("mag_axis_fit", "%d %.4g %.1f", ar.n, ar.best_err, ar.ratio);
  proto::test("cal_axes_mag", ok, "body x = %c%s, y = %c%s, z = %c%s (Mag-Chip), %d Proben, Eindeutigkeit %.1f%s",
              ar.sign[0] > 0 ? '+' : '-', AXIS[ar.map[0]], ar.sign[1] > 0 ? '+' : '-', AXIS[ar.map[1]], ar.sign[2] > 0 ? '+' : '-', AXIS[ar.map[2]],
              ar.n, ar.ratio, ok ? "" : " (< 2: mehr und schnellere Drehung)");
  return ok ? Res::OK : Res::FEHL;
}

Res calBaro(float seconds) {
  if (!st.baro) { proto::test("cal_baro", Res::FEHL, "Barometer nicht bereit"); return Res::FEHL; }
  seconds = constrain(seconds, 5.0f, 120.0f);
  proto::info("Bodenreferenz: %.0f s, kein Luftzug", seconds);
  double sp = 0, sp2 = 0, stt = 0;
  int n = 0;
  float p, t;
  const uint32_t t0 = millis();
  while (millis() - t0 < uint32_t(seconds * 1000)) {
    if (proto::abortRequested()) { proto::test("cal_baro", Res::SKIP, "abgebrochen"); return Res::SKIP; }
    if (baro.read(p, t)) { sp += p; sp2 += double(p) * p; stt += t; ++n; }
    delay(5);
  }
  if (n < 10) { proto::test("cal_baro", Res::FEHL, "nur %d Messungen", n); return Res::FEHL; }
  const float mean = float(sp / n), sd = float(sqrt(fmax(sp2 / n - (sp / n) * (sp / n), 0.0))), tm = float(stt / n);
  calib.baro_ground_pa = mean;
  calib.baro_noise_pa = sd;
  calib.baro_ground_temp_c = tm;
  calib.valid |= cal::BARO;
  proto::cal("baro_ground_pa", "%.1f", mean);
  proto::cal("baro_noise_pa", "%.2f", sd);
  proto::cal("baro_ground_temp_c", "%.2f", tm);
  const bool ok = sd < 6.0f;   // ca. 0,5 m
  proto::test("cal_baro", ok, "%d Messungen, %.1f Pa, Rauschen %.2f Pa = %.2f m, %.1f C", n, mean, sd, sd / 12.0f, tm);
  return ok ? Res::OK : Res::FEHL;
}

static const char* MUX_NET[8] = {"PYRO1_NEG", "PYRO2_NEG", "PYRO3_NEG", "PYRO4_NEG", "VBAT1_F", "VBAT2_F", "VBAT_ARMED", "GND"};

static Res calAdcOne(int ch) {
  char name[16];
  snprintf(name, sizeof name, "cal_adc%d", ch);
  float sum = 0;
  for (int k = 0; k < 16; ++k) sum += bus.readMuxInputV(rb::Mux(ch));
  const float meas = sum / 16;   // mit Nennteiler, ohne adc_gain
  if (meas < 0.5f) { proto::test(name, Res::SKIP, "%s: nur %.3f V, nicht versorgt", MUX_NET[ch], meas); return Res::SKIP; }
  float user;
  if (!proto::ask(user, "Kanal %d %s: Teensy misst %.3f V. Multimeter an %s gegen GND, Wert in V", ch, MUX_NET[ch], meas, MUX_NET[ch])) {
    proto::test(name, Res::SKIP, "übersprungen"); return Res::SKIP;
  }
  const float gain = user / meas;
  const bool ok = gain > 0.9f && gain < 1.1f;
  if (ok) { calib.adc_gain[ch] = gain; calib.valid |= cal::ADC; }
  proto::cal("adc_gain", "%d %.5f", ch, gain);
  proto::test(name, ok, "gemessen %.3f V, Multimeter %.3f V, Faktor %.4f%s", meas, user, gain, ok ? "" : " (> 10 %%: Teiler oder Eingabe prüfen, nicht übernommen)");
  return ok ? Res::OK : Res::FEHL;
}

Res calAdc(int channel) {
  if (channel >= 0) return channel < 8 ? calAdcOne(channel) : Res::FEHL;
  Res r = Res::OK;
  for (int ch : {4, 5, 6}) r = proto::worst(r, calAdcOne(ch));
  return r;
}

Res calIna() {
  if (!st.ina) { proto::test("cal_ina", Res::FEHL, "INA239 nicht bereit"); return Res::FEHL; }
  if (!have2S()) { proto::test("cal_ina", Res::SKIP, "2S nicht versorgt"); return Res::SKIP; }
  if (proto::wait("INA239 Offset: keine Last an VSERVO (Servos, Motor abgesteckt), Enter") != 1) { proto::test("cal_ina", Res::SKIP, "abgebrochen"); return Res::SKIP; }
  float sum = 0;
  for (int k = 0; k < 10; ++k) { PowerSample s; ina.read(s); sum += s.current_A; delay(60); }
  const float offset = sum / 10;
  calib.ina_offset_a = offset;
  proto::cal("ina_offset_a", "%.5f", offset);
  const bool off_ok = fabsf(offset) < 0.05f;
  proto::test("cal_ina_offset", off_ok, "%.1f mA ohne Last", offset * 1000);
  // Verstärkung
  float user;
  if (!proto::ask(user, "Bekannte Last an VSERVO anschließen, Strom laut Multimeter in A (leer = nur Offset)")) {
    calib.ina_gain = 1.0f;
    calib.valid |= cal::INA;
    return off_ok ? Res::OK : Res::FEHL;
  }
  sum = 0;
  for (int k = 0; k < 10; ++k) { PowerSample s; ina.read(s); sum += s.current_A; delay(60); }
  const float meas = sum / 10 - offset;
  if (meas < 0.05f) { proto::test("cal_ina_gain", Res::FEHL, "gemessen nur %.1f mA", meas * 1000); return Res::FEHL; }
  const float gain = user / meas;
  const bool ok = gain > 0.9f && gain < 1.1f;
  if (ok) { calib.ina_gain = gain; calib.valid |= cal::INA; }
  proto::cal("ina_gain", "%.5f", gain);
  proto::test("cal_ina_gain", ok, "gemessen %.3f A, Multimeter %.3f A, Faktor %.4f%s", meas, user, gain, ok ? "" : " (nicht übernommen)");
  proto::wait("Last wieder abnehmen, Enter");
  return ok && off_ok ? Res::OK : Res::FEHL;
}

Res calServo(int i) {
  if (i < 0 || i > 3) { proto::test("cal_servo", Res::FEHL, "Kanal 1..4"); return Res::FEHL; }
  char name[20];
  snprintf(name, sizeof name, "cal_servo%d", i + 1);
  if (!have2S()) { proto::test(name, Res::SKIP, "2S nicht versorgt"); return Res::SKIP; }
  int lo, hi;
  servoLimitsUs(i, lo, hi);
  int us = constrain(int(calib.servo_center_us[i]), lo, hi);
  int c = us, mn = constrain(int(calib.servo_min_us[i]), lo, hi), mx = constrain(int(calib.servo_max_us[i]), lo, hi);
  proto::info("Servo %d trimmen, Fenster %d..%d us. Befehle: + - (10 us), ++ -- (50 us), <zahl> us, c = Mitte, a = min, b = max, ok, q", i + 1, lo, hi);
  servoWriteUs(i, us);
  char line[24];
  for (;;) {
    proto::info("servo%d %d us (Mitte %d, min %d, max %d)", i + 1, us, c, mn, mx);
    Serial.println("WAIT Befehl");
    if (!proto::readLine(line, sizeof line, 120000) || line[0] == 'q') { servoRelease(i); proto::test(name, Res::SKIP, "abgebrochen"); return Res::SKIP; }
    if (strcmp(line, "++") == 0) us += 50;
    else if (strcmp(line, "--") == 0) us -= 50;
    else if (line[0] == '+') us += 10;
    else if (line[0] == '-') us -= 10;
    else if (line[0] == 'c') c = us;
    else if (line[0] == 'a') mn = us;
    else if (line[0] == 'b') mx = us;
    else if (strcmp(line, "ok") == 0 || line[0] == 0) break;
    else if (isdigit(uint8_t(line[0]))) us = atoi(line);
    us = constrain(us, lo, hi);
    servoWriteUs(i, us);
    delay(200);
  }
  if (mn > mx) { const int t = mn; mn = mx; mx = t; }
  c = constrain(c, mn, mx);
  calib.servo_center_us[i] = uint16_t(c);
  calib.servo_min_us[i] = uint16_t(mn);
  calib.servo_max_us[i] = uint16_t(mx);
  calib.valid |= cal::SERVO;
  servoWriteUs(i, c); delay(400); servoRelease(i);
  proto::cal("servo_us", "%d %d %d %d", i + 1, c, mn, mx);
  proto::test(name, true, "Mitte %d, min %d, max %d us", c, mn, mx);
  return Res::OK;
}

void calShow() {
  const cal::CalData& d = calib;
  proto::info("Kalibrierung: %s, Version %u, gespeichert %lu mal, gültig 0x%02lX (GYRO 1 ACC 2 MAG 4 AXES 8 BARO 10 ADC 20 INA 40 SERVO 80)",
              cal::checkName(calib_check), d.version, (unsigned long)d.saved_count, (unsigned long)d.valid);
  proto::cal("valid", "%lu", (unsigned long)d.valid);
  proto::cal("gyro_bias_dps", "%.4f %.4f %.4f", d.gyro_bias_dps[0], d.gyro_bias_dps[1], d.gyro_bias_dps[2]);
  proto::cal("gyro_bias_temp_c", "%.2f", d.gyro_bias_temp_c);
  proto::cal("gyro_noise_dps", "%.4f %.4f %.4f", d.gyro_noise_dps[0], d.gyro_noise_dps[1], d.gyro_noise_dps[2]);
  proto::cal("acc_offset_ms2", "%.4f %.4f %.4f", d.acc_offset_ms2[0], d.acc_offset_ms2[1], d.acc_offset_ms2[2]);
  proto::cal("acc_scale", "%.5f %.5f %.5f", d.acc_scale[0], d.acc_scale[1], d.acc_scale[2]);
  proto::cal("mag_offset_gauss", "%.5f %.5f %.5f", d.mag_offset_gauss[0], d.mag_offset_gauss[1], d.mag_offset_gauss[2]);
  proto::cal("mag_soft_iron", "%.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f %.5f", d.mag_soft_iron[0], d.mag_soft_iron[1], d.mag_soft_iron[2],
             d.mag_soft_iron[3], d.mag_soft_iron[4], d.mag_soft_iron[5], d.mag_soft_iron[6], d.mag_soft_iron[7], d.mag_soft_iron[8]);
  proto::cal("mag_field_gauss", "%.4f", d.mag_field_gauss);
  proto::cal("imu_axis_map", "%d %d %d", d.imu_axis_map[0], d.imu_axis_map[1], d.imu_axis_map[2]);
  proto::cal("imu_axis_sign", "%d %d %d", d.imu_axis_sign[0], d.imu_axis_sign[1], d.imu_axis_sign[2]);
  proto::cal("mag_axis_map", "%d %d %d", d.mag_axis_map[0], d.mag_axis_map[1], d.mag_axis_map[2]);
  proto::cal("mag_axis_sign", "%d %d %d", d.mag_axis_sign[0], d.mag_axis_sign[1], d.mag_axis_sign[2]);
  proto::cal("baro_ground_pa", "%.1f", d.baro_ground_pa);
  proto::cal("baro_noise_pa", "%.2f", d.baro_noise_pa);
  proto::cal("baro_ground_temp_c", "%.2f", d.baro_ground_temp_c);
  for (int i = 0; i < 8; ++i) proto::cal("adc_gain", "%d %.5f", i, d.adc_gain[i]);
  proto::cal("ina_offset_a", "%.5f", d.ina_offset_a);
  proto::cal("ina_gain", "%.5f", d.ina_gain);
  for (int i = 0; i < 4; ++i) proto::cal("servo_us", "%d %u %u %u", i + 1, d.servo_center_us[i], d.servo_min_us[i], d.servo_max_us[i]);
}

Res calSave() {
  const bool ok = cal::save(calib);
  calib_check = cal::Check::OK;
  proto::test("cal_save", ok, "EEPROM %d Byte, Version %u, CRC 0x%08lX, %lu. Speicherung", int(sizeof calib), calib.version,
              (unsigned long)calib.crc, (unsigned long)calib.saved_count);
  return ok ? Res::OK : Res::FEHL;
}

Res calLoad() {
  calib_check = cal::load(calib);
  const bool ok = calib_check == cal::Check::OK;
  proto::test("cal_load", ok ? Res::OK : Res::SKIP, "%s%s", cal::checkName(calib_check), ok ? "" : ", Standardwerte geladen");
  return ok ? Res::OK : Res::SKIP;
}

Res calDefaults() {
  calib = cal::defaults();
  proto::test("cal_defaults", true, "Standardwerte im RAM (nicht gespeichert)");
  return Res::OK;
}

Res calErase() {
  if (!proto::confirm("Kalibrierung im EEPROM löschen? Tippe JA")) { proto::test("cal_erase", Res::SKIP, "nicht bestätigt"); return Res::SKIP; }
  cal::erase();
  calib = cal::defaults();
  calib_check = cal::Check::EMPTY;
  proto::test("cal_erase", true, "gelöscht, Standardwerte");
  return Res::OK;
}
