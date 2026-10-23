#include "Tvc.h"
#include "Board.h"
#include "Config.h"
#include <Wire.h>
#include "ICM_20948.h"
#include <math.h>

using namespace board;

// ===== Versuchsparameter (identisch zu servo_ident / tvcsim.ident) =====
namespace {
constexpr uint32_t SAMPLE_HZ    = 500;
constexpr uint32_t SAMPLE_US    = 1000000UL / SAMPLE_HZ;
constexpr uint32_t BIAS_SAMPLES = 1000;
constexpr float STAIR_HOLD_S = 0.8f;
constexpr int   STAIR_LEVELS = 5;
constexpr float STEP_HOLD_S  = 1.0f;
constexpr float ALT_HOLD_S   = 0.8f;
constexpr float CHIRP_F0_HZ  = 0.3f;
constexpr float CHIRP_F1_HZ  = 12.0f;
constexpr float CHIRP_T_S    = 20.0f;
constexpr float CHIRP_FADE_S = 0.5f;
constexpr float HOLD_START_S = 2.0f;
constexpr float HOLD_END_S   = 2.0f;
constexpr int   PWM_BITS     = 16;

enum Seg : uint8_t { SEG_IDLE = 0, SEG_HOLD0 = 1, SEG_STAIR = 2, SEG_STEPS = 3,
                     SEG_ALT = 4, SEG_CHIRP_S = 5, SEG_CHIRP_L = 6, SEG_HOLD1 = 7 };
const char* SEG_NAMES = "0=idle,1=hold_start,2=staircase,3=steps,4=alternate,5=chirp_small,6=chirp_large,7=hold_end";

enum Kind : uint8_t { K_HOLD, K_CHIRP };
struct Piece { uint8_t seg; uint8_t kind; float a; uint32_t dur_ms; };
constexpr int MAX_PIECES = 96;

struct Axis { const char* name; uint8_t pin; int cal_index; float center_deg, min_deg, max_deg; };

ICM_20948_I2C ext;                 // externe IMU auf dem Motorrohr (J_QWIIC)
bool  ext_ok = false;
float ext_bias[3] = {0, 0, 0};
float body_bias[3] = {0, 0, 0};

Axis axes[2] = {
  {"Y", rb::PIN_SERVO_YAW,   0, SERVO_YAW_OFFSET,   SERVO_YAW_MIN_DEG,   SERVO_YAW_MAX_DEG},
  {"P", rb::PIN_SERVO_PITCH, 1, SERVO_PITCH_OFFSET, SERVO_PITCH_MIN_DEG, SERVO_PITCH_MAX_DEG},
};
float    amplitude_deg = 0.0f;     // 0 = aus dem Fenster
uint32_t frame_hz = 50;
float    servo_volt = 0.0f;
char     note[96] = "";
bool     centers_from_cal = false;

Piece pieces[MAX_PIECES];
int   n_pieces = 0;

// ----- Servo als 16-Bit-PWM (feiner als die Servo-Bibliothek, wie in E01) -----
float pulseForDeg(float deg) {
  deg = constrain(deg, 0.0f, 180.0f);
  return SERVO_PULSE_MIN_US + (SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) * deg / 180.0f;
}
float degForPulse(float us) {
  return (us - SERVO_PULSE_MIN_US) * 180.0f / (SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US);
}
void writePulse(uint8_t pin, float us) {
  const float period_us = 1e6f / frame_hz;
  const uint32_t maxval = (1UL << PWM_BITS) - 1;
  uint32_t v = uint32_t(lroundf(us / period_us * maxval));
  if (v > maxval) v = maxval;
  analogWrite(pin, v);
}
float setServoDeg(int ax, float deg) {
  deg = constrain(deg, axes[ax].min_deg, axes[ax].max_deg);
  writePulse(axes[ax].pin, pulseForDeg(deg));
  return deg;
}
void pwmSetup() {
  for (auto& a : axes) {
    servoRelease(a.cal_index);              // Servo-Bibliothek loslassen, Pin als PWM
    analogWriteFrequency(a.pin, frame_hz);
  }
  analogWriteResolution(PWM_BITS);
  setServoDeg(0, axes[0].center_deg);
  setServoDeg(1, axes[1].center_deg);
}
void pwmRelease() {
  for (auto& a : axes) { analogWrite(a.pin, 0); servoRelease(a.cal_index); }
  analogWriteResolution(12);
}
float defaultAmplitude(int ax) {
  return floorf(min(axes[ax].center_deg - axes[ax].min_deg, axes[ax].max_deg - axes[ax].center_deg));
}
void centersFromCal() {
  if (!cal::has(calib, cal::SERVO)) return;
  for (auto& a : axes) a.center_deg = degForPulse(calib.servo_center_us[a.cal_index]);
  centers_from_cal = true;
}

// ----- externe IMU ICM-20948 an Wire (SparkFun-Bibliothek) -----
bool extSetup() {
  bool found = false;
  for (int ad0 = 0; ad0 < 2 && !found; ++ad0) {
    ext.begin(Wire, ad0);
    found = ext.status == ICM_20948_Stat_Ok;
  }
  if (!found) return false;
  ext.swReset(); delay(250);
  ext.sleep(false);
  ext.lowPower(false);
  ext.setSampleMode(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, ICM_20948_Sample_Mode_Continuous);
  ICM_20948_fss_t fss; fss.a = gpm4; fss.g = dps500;
  ext.setFullScale(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, fss);
  ICM_20948_dlpcfg_t dlp; dlp.a = acc_d111bw4_n136bw; dlp.g = gyr_d151bw8_n187bw6;
  ext.setDLPFcfg(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, dlp);
  ext.enableDLPF(ICM_20948_Internal_Acc, true);
  ext.enableDLPF(ICM_20948_Internal_Gyr, true);
  ICM_20948_smplrt_t sr; sr.a = 0; sr.g = 0;
  ext.setSampleRate(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, sr);
  delay(50);
  return ext.status == ICM_20948_Stat_Ok;
}
void readExt(float g[3], float a[3]) {
  ext.getAGMT();
  g[0] = ext.gyrX() - ext_bias[0]; g[1] = ext.gyrY() - ext_bias[1]; g[2] = ext.gyrZ() - ext_bias[2];
  a[0] = ext.accX() * 1e-3f; a[1] = ext.accY() * 1e-3f; a[2] = ext.accZ() * 1e-3f;
}
void readBody(float g[3], float a[3]) {
  ImuSample s;
  imu.read(s);
  for (int i = 0; i < 3; ++i) { g[i] = s.gyro_dps[i] - body_bias[i]; a[i] = s.acc_ms2[i] / 9.80665f; }
}

bool zeroGyros() {
  proto::info("Gyro-Nullpunkte: %lu Messungen (2 s), Aufbau ruhig halten", (unsigned long)BIAS_SAMPLES);
  double se[3] = {0, 0, 0}, sb[3] = {0, 0, 0};
  for (int k = 0; k < 3; ++k) { ext_bias[k] = 0; body_bias[k] = 0; }
  for (uint32_t i = 0; i < BIAS_SAMPLES; ++i) {
    float g[3], a[3];
    if (ext_ok) { readExt(g, a); for (int k = 0; k < 3; ++k) se[k] += g[k]; }
    if (st.imu) { readBody(g, a); for (int k = 0; k < 3; ++k) sb[k] += g[k]; }
    delayMicroseconds(SAMPLE_US);
  }
  for (int k = 0; k < 3; ++k) { ext_bias[k] = float(se[k] / BIAS_SAMPLES); body_bias[k] = float(sb[k] / BIAS_SAMPLES); }
  proto::cal("tvc_ext_gyro_bias_dps", "%.4f %.4f %.4f", ext_bias[0], ext_bias[1], ext_bias[2]);
  proto::cal("tvc_body_gyro_bias_dps", "%.4f %.4f %.4f", body_bias[0], body_bias[1], body_bias[2]);
  return true;
}

// ----- Anregungsfolge -----
void addHold(uint8_t seg, float a, float dur_s) { if (n_pieces < MAX_PIECES) pieces[n_pieces++] = {seg, K_HOLD, a, uint32_t(dur_s * 1000.0f)}; }
void addChirp(uint8_t seg, float a)            { if (n_pieces < MAX_PIECES) pieces[n_pieces++] = {seg, K_CHIRP, a, uint32_t(CHIRP_T_S * 1000.0f)}; }

void buildSequence(float A) {
  n_pieces = 0;
  addHold(SEG_HOLD0, 0, HOLD_START_S);
  for (int i = 1; i <= STAIR_LEVELS; ++i)                  addHold(SEG_STAIR, A * i / STAIR_LEVELS, STAIR_HOLD_S);
  for (int i = STAIR_LEVELS - 1; i >= -STAIR_LEVELS; --i)  addHold(SEG_STAIR, A * i / STAIR_LEVELS, STAIR_HOLD_S);
  for (int i = -STAIR_LEVELS + 1; i <= 0; ++i)             addHold(SEG_STAIR, A * i / STAIR_LEVELS, STAIR_HOLD_S);
  const float frac[3] = {0.25f, 0.5f, 1.0f};
  for (int s = 0; s < 2; ++s)
    for (int i = 0; i < 3; ++i) { addHold(SEG_STEPS, (s == 0 ? 1 : -1) * A * frac[i], STEP_HOLD_S); addHold(SEG_STEPS, 0, STEP_HOLD_S); }
  addHold(SEG_ALT, +A, ALT_HOLD_S); addHold(SEG_ALT, -A, ALT_HOLD_S);
  addHold(SEG_ALT, +A, ALT_HOLD_S); addHold(SEG_ALT, -A, ALT_HOLD_S);
  addHold(SEG_ALT, 0, ALT_HOLD_S);
  addChirp(SEG_CHIRP_S, A * 0.25f);
  addHold(SEG_HOLD0, 0, 1.0f);
  addChirp(SEG_CHIRP_L, A * 0.5f);
  addHold(SEG_HOLD1, 0, HOLD_END_S);
}

float chirpValue(float a, float t_s) {
  const float T = CHIRP_T_S;
  t_s = constrain(t_s, 0.0f, T);
  const float k = logf(CHIRP_F1_HZ / CHIRP_F0_HZ);
  const float phase = 2.0f * PI * CHIRP_F0_HZ * T / k * (expf(t_s * k / T) - 1.0f);
  float env = 1.0f;
  if (t_s < CHIRP_FADE_S) env = t_s / CHIRP_FADE_S;
  else if (t_s > T - CHIRP_FADE_S) env = (T - t_s) / CHIRP_FADE_S;
  return a * env * sinf(phase);
}

float sequenceTotalS() {
  uint32_t ms = 0;
  for (int i = 0; i < n_pieces; ++i) ms += pieces[i].dur_ms;
  return ms / 1000.0f;
}

void printHeader(int ax, float A) {
  Serial.println("# kartonaut servo_ident v1");
  Serial.println("# board: mainboard rev B1, revb_test tvc (E02)");
  Serial.printf("# axis: %s\n", axes[ax].name);
  Serial.printf("# servo_pin: %d\n", axes[ax].pin);
  Serial.printf("# center_deg: %.2f\n", axes[ax].center_deg);
  Serial.printf("# center_source: %s\n", centers_from_cal ? "calibration" : "Config.h");
  Serial.printf("# window_deg: %.1f %.1f\n", axes[ax].min_deg, axes[ax].max_deg);
  Serial.printf("# amplitude_deg: %.2f\n", A);
  Serial.printf("# pulse_us: %d %d\n", SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  Serial.printf("# frame_hz: %lu\n", (unsigned long)frame_hz);
  Serial.printf("# sample_hz: %lu\n", (unsigned long)SAMPLE_HZ);
  Serial.printf("# chirp: f0_hz=%.2f f1_hz=%.2f t_s=%.1f fade_s=%.2f log\n", CHIRP_F0_HZ, CHIRP_F1_HZ, CHIRP_T_S, CHIRP_FADE_S);
  Serial.printf("# stair: levels=%d hold_s=%.2f\n", STAIR_LEVELS, STAIR_HOLD_S);
  Serial.printf("# step_hold_s: %.2f\n", STEP_HOLD_S);
  Serial.printf("# segments: %s\n", SEG_NAMES);
  Serial.printf("# imu: %s gyro_fs_dps=500 acc_fs_g=4 gyro_dlpf_hz=152\n", ext_ok ? "ICM-20948" : "FEHLT");
  Serial.printf("# gyro_bias_dps: %.4f %.4f %.4f\n", ext_bias[0], ext_bias[1], ext_bias[2]);
  Serial.printf("# body_imu: %s gyro_fs_dps=2000 acc_fs_g=16 rows=#body,t_us,gx_dps,gy_dps,gz_dps,ax_g,ay_g,az_g\n", st.imu ? imu.name() : "FEHLT");
  Serial.printf("# body_gyro_bias_dps: %.4f %.4f %.4f\n", body_bias[0], body_bias[1], body_bias[2]);
  Serial.printf("# servo_volt: %.2f\n", servo_volt);
  Serial.printf("# vservo_ina_v: %.2f\n", vbat2());
  Serial.printf("# note: %s\n", note);
  Serial.printf("# duration_s: %.1f\n", sequenceTotalS());
  Serial.println("t_us,seg,axis,servo_deg,cmd_rel_deg,pulse_us,gx_dps,gy_dps,gz_dps,ax_g,ay_g,az_g");
}

// Lauf auf einer Achse; blockiert bis zum Ende oder Abbruch (S/q auf der Konsole)
Res runAxis(int ax) {
  const float A = amplitude_deg > 0 ? amplitude_deg : defaultAmplitude(ax);
  buildSequence(A);
  pwmSetup();
  delay(300);
  printHeader(ax, A);
  uint32_t rows = 0;
  int piece_idx = 0;
  const uint32_t run_t0 = micros();
  uint32_t piece_t0 = run_t0, next_sample = run_t0;
  bool aborted = false;
  while (piece_idx < n_pieces) {
    while (Serial.available()) { const int c = Serial.read(); if (c == 'S' || c == 's' || c == 'q' || c == 'Q') aborted = true; }
    if (aborted) break;
    const uint32_t now = micros();
    if (int32_t(now - next_sample) < 0) continue;
    next_sample += SAMPLE_US;
    while (piece_idx < n_pieces && (now - piece_t0) >= pieces[piece_idx].dur_ms * 1000UL) {
      piece_t0 += pieces[piece_idx].dur_ms * 1000UL;
      ++piece_idx;
    }
    if (piece_idx >= n_pieces) break;
    const Piece& p = pieces[piece_idx];
    const float t_piece = (now - piece_t0) * 1e-6f;
    const float rel = p.kind == K_HOLD ? p.a : chirpValue(p.a, t_piece);
    const float abs_deg = setServoDeg(ax, axes[ax].center_deg + rel);
    float g[3] = {0, 0, 0}, a[3] = {0, 0, 0};
    if (ext_ok) readExt(g, a);
    Serial.printf("%lu,%u,%s,%.3f,%.3f,%.1f,%.3f,%.3f,%.3f,%.4f,%.4f,%.4f\n",
                  (unsigned long)(now - run_t0), p.seg, axes[ax].name, abs_deg, abs_deg - axes[ax].center_deg,
                  pulseForDeg(abs_deg), g[0], g[1], g[2], a[0], a[1], a[2]);
    if (st.imu) {
      readBody(g, a);
      Serial.printf("#body,%lu,%.3f,%.3f,%.3f,%.4f,%.4f,%.4f\n", (unsigned long)(now - run_t0), g[0], g[1], g[2], a[0], a[1], a[2]);
    }
    ++rows;
  }
  setServoDeg(0, axes[0].center_deg);
  setServoDeg(1, axes[1].center_deg);
  delay(300);
  pwmRelease();
  Serial.printf("# END rows=%lu reason=%s\n", (unsigned long)rows, aborted ? "abort" : "done");
  char name[16];
  snprintf(name, sizeof name, "tvc_run_%s", axes[ax].name);
  proto::test(name, !aborted, "%lu Zeilen, A %.1f Grad, %lu Hz Puls, Mitte %.2f, externe IMU %s", (unsigned long)rows, A,
              (unsigned long)frame_hz, axes[ax].center_deg, ext_ok ? "ok" : "FEHLT");
  return aborted ? Res::SKIP : Res::OK;
}

int axisIndex(const char* s) {
  if (!s) return -1;
  if (*s == 'Y' || *s == 'y') return 0;
  if (*s == 'P' || *s == 'p') return 1;
  return -1;
}
}  // namespace

void tvcHelp() {
  proto::comment("  tvc status | tvc imu | tvc zero");
  proto::comment("  tvc run Y|P|B            Folge auf Yaw, Pitch oder beide fahren (S bricht ab)");
  proto::comment("  tvc amp <deg> | tvc frame <hz> | tvc center <y> <p> | tvc window Y|P <min> <max>");
  proto::comment("  tvc move Y|P <deg> | tvc volt <V> | tvc note <text>");
}

// a1 = Unterbefehl, a2 = erstes Wort danach, rest = alles hinter dem Unterbefehl (a2 eingeschlossen)
Res tvcCommand(const char* a1, const char* a2, const char* rest) {
  static bool initialised = false;
  if (!initialised) { centersFromCal(); initialised = true; }
  if (!a1 || !strcmp(a1, "status")) {
    proto::info("tvc: externe IMU %s, Platinen-IMU %s, Mitte %s", ext_ok ? "ICM-20948 ok" : "nicht gesucht/gefunden (tvc imu)",
                st.imu ? "ok" : "fehlt", centers_from_cal ? "aus der Kalibrierung" : "aus Config.h");
    for (int i = 0; i < 2; ++i)
      proto::info("Achse %s: Pin %d, Mitte %.2f Grad (%.0f us), Fenster %.1f..%.1f, Vorgabe-Amplitude %.1f", axes[i].name, axes[i].pin,
                  axes[i].center_deg, pulseForDeg(axes[i].center_deg), axes[i].min_deg, axes[i].max_deg, defaultAmplitude(i));
    buildSequence(amplitude_deg > 0 ? amplitude_deg : defaultAmplitude(0));
    proto::info("Amplitude %s%.1f, Pulsrate %lu Hz, Servospannung %.2f V, Dauer je Achse %.0f s, Notiz: %s",
                amplitude_deg > 0 ? "" : "auto ", amplitude_deg > 0 ? amplitude_deg : defaultAmplitude(0), (unsigned long)frame_hz,
                servo_volt, sequenceTotalS(), note);
    return Res::OK;
  }
  if (!strcmp(a1, "imu")) {
    ext_ok = extSetup();
    proto::test("tvc_ext_imu", ext_ok, ext_ok ? "ICM-20948 an J_QWIIC (0x68/0x69), +-500 dps, +-4 g, DLPF 152 Hz" : "kein ICM-20948 an Wire (J_QWIIC: GND, 3V3, SDA, SCL)");
    return ext_ok ? Res::OK : Res::FEHL;
  }
  if (!strcmp(a1, "zero")) { zeroGyros(); return Res::OK; }
  if (!strcmp(a1, "amp"))  { amplitude_deg = a2 ? strtof(a2, nullptr) : 0; proto::info("amplitude_deg %.2f", amplitude_deg); return Res::OK; }
  if (!strcmp(a1, "volt")) { servo_volt = a2 ? strtof(a2, nullptr) : 0; proto::info("servo_volt %.2f", servo_volt); return Res::OK; }
  if (!strcmp(a1, "note")) { strncpy(note, rest ? rest : "", sizeof note - 1); note[sizeof note - 1] = 0; proto::info("note %s", note); return Res::OK; }
  if (!strcmp(a1, "frame")) {
    const long f = a2 ? atol(a2) : 0;
    if (f < 40 || f > 400) { proto::info("frame: 40..400 Hz"); return Res::FEHL; }
    frame_hz = f; proto::info("frame_hz %lu", (unsigned long)frame_hz); return Res::OK;
  }
  if (!strcmp(a1, "center")) {
    float y = 0, p = 0;
    if (!rest || sscanf(rest, "%f %f", &y, &p) != 2) { proto::info("center <yaw> <pitch> in Servo-Grad"); return Res::FEHL; }
    axes[0].center_deg = y; axes[1].center_deg = p; centers_from_cal = false;
    proto::info("center_deg %.2f %.2f", y, p); return Res::OK;
  }
  if (!strcmp(a1, "window")) {
    const int ax = axisIndex(a2);
    float lo = 0, hi = 0;
    if (ax < 0 || !rest || sscanf(rest, " %*c %f %f", &lo, &hi) != 2 || lo >= hi || lo < 0 || hi > 180) { proto::info("window Y|P <min> <max>"); return Res::FEHL; }
    axes[ax].min_deg = lo; axes[ax].max_deg = hi;
    proto::info("window_deg %s %.1f %.1f (Anschlag von Hand prüfen)", axes[ax].name, lo, hi); return Res::OK;
  }
  if (!strcmp(a1, "move")) {
    const int ax = axisIndex(a2);
    float deg = 0;
    if (ax < 0 || !rest || sscanf(rest, " %*c %f", &deg) != 1) { proto::info("move Y|P <deg>"); return Res::FEHL; }
    if (!have2S()) { proto::test("tvc_move", Res::SKIP, "2S nicht versorgt"); return Res::SKIP; }
    pwmSetup();
    const float set = setServoDeg(ax, deg);
    proto::info("%s auf %.2f Grad (%.0f us), 3 s halten", axes[ax].name, set, pulseForDeg(set));
    delay(3000);
    pwmRelease();
    return Res::OK;
  }
  if (!strcmp(a1, "run")) {
    const char sel = a2 ? toupper(a2[0]) : 'Y';
    if (sel != 'Y' && sel != 'P' && sel != 'B') { proto::info("run Y|P|B"); return Res::FEHL; }
    if (!have2S()) { proto::test("tvc_run", Res::SKIP, "2S nicht versorgt, VSERVO fehlt"); return Res::SKIP; }
    if (!ext_ok) { ext_ok = extSetup(); if (!ext_ok) proto::info("WARNUNG: keine externe IMU, Lauf zeichnet nur Kommando und Rumpf auf"); }
    zeroGyros();
    Res r = Res::OK;
    if (sel == 'Y' || sel == 'B') r = runAxis(0);
    if (sel == 'B' && r == Res::OK) delay(500);
    if (sel == 'P' || (sel == 'B' && r == Res::OK)) r = proto::worst(r, runAxis(1));
    return r;
  }
  proto::info("unbekannt: tvc %s", a1);
  return Res::FEHL;
}
