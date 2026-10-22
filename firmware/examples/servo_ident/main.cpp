// servo_ident – Experiment E01: Übertragungsfunktion Servo-Soll -> Kardanwinkel
//
// Fährt je TVC-Achse eine feste Anregungsfolge (Treppe, Sprünge, Wechselsprünge,
// zwei Chirps) auf den Servo und zeichnet dabei mit 500 Hz das Kommando und die
// Drehrate/Beschleunigung einer IMU auf, die für den Versuch auf dem Motorrohr
// sitzt. Die Ausgabe ist eine CSV auf USB-Serial, die
// simulation/scripts/ident_servo.py auswertet. Anleitung: docs/experiments/E01_servo_ident.md
//
//   pio run -e servo_ident -t upload
//   python firmware/tools/capture_serial.py --port COM5 --out messung.csv --run Y
//   (oder pio device monitor -f log2file und von Hand "Y" senden)
//
// Befehle (eine Zeile, Enter):
//   ?            Status und Hilfe
//   Y | P | B    Folge auf Yaw, Pitch oder beide Achsen fahren (B = Y, dann P)
//   S            Abbruch, Servos auf Mitte
//   A <deg>      Amplitude in Servo-Grad um die Mitte (Vorgabe: Abstand zum Fenster)
//   C <y> <p>    Mittelstellung Yaw/Pitch in Servo-Grad (Vorgabe Config.h: 92,5 / 82,5)
//   W <achse> <min> <max>   mechanisches Fenster ändern (achse Y|P), Vorsicht
//   F <hz>       Pulsrate der Servos (50 wie im Flug; Digitalservos auch 100..333)
//   M <achse> <deg>         Servo von Hand auf einen Winkel stellen (Fenster suchen)
//   Z            Gyro-Nullpunkt neu messen (Aufbau ruhig halten)
//   V <volt>     Servospannung für den Dateikopf notieren
//   N <text>     Notiz (Servo-Typ, Kardan, Datum) für den Dateikopf
//
// Die Pins, Pulsbreiten und Fenster kommen aus Config.h (gleiche Werte wie der Flug).
// Die Servos werden nicht über PWMServo (ganze Grad) angesteuert, sondern direkt als
// 16-Bit-PWM, damit die Chirps nicht in 1-Grad-Stufen zerfallen. Die Umrechnung
// Grad -> Puls ist dieselbe lineare Abbildung wie in PWMServo.
#include <Arduino.h>
#include <Wire.h>
#include "ICM_20948.h"
#include "Config.h"

// ===== Versuchsparameter =====
constexpr uint32_t SAMPLE_HZ        = 500;
constexpr uint32_t SAMPLE_US        = 1000000UL / SAMPLE_HZ;
constexpr uint32_t BIAS_SAMPLES     = 1000;      // 2 s Gyro-Nullpunkt
constexpr float    STAIR_HOLD_S     = 0.8f;
constexpr int      STAIR_LEVELS     = 5;         // Stufen von 0 bis A
constexpr float    STEP_HOLD_S      = 1.0f;
constexpr float    ALT_HOLD_S       = 0.8f;
constexpr float    CHIRP_F0_HZ      = 0.3f;
constexpr float    CHIRP_F1_HZ      = 12.0f;
constexpr float    CHIRP_T_S        = 20.0f;
constexpr float    CHIRP_FADE_S     = 0.5f;
constexpr float    HOLD_START_S     = 2.0f;
constexpr float    HOLD_END_S       = 2.0f;
constexpr int      PWM_BITS         = 16;

// Segment-Kennungen in der Spalte "seg"
enum Seg : uint8_t { SEG_IDLE = 0, SEG_HOLD0 = 1, SEG_STAIR = 2, SEG_STEPS = 3,
                     SEG_ALT = 4, SEG_CHIRP_S = 5, SEG_CHIRP_L = 6, SEG_HOLD1 = 7 };
static const char* SEG_NAMES = "0=idle,1=hold_start,2=staircase,3=steps,4=alternate,5=chirp_small,6=chirp_large,7=hold_end";

enum Kind : uint8_t { K_HOLD, K_CHIRP };
struct Piece { uint8_t seg; uint8_t kind; float a; uint32_t dur_ms; };
constexpr int MAX_PIECES = 96;

struct Axis {
  const char* name;
  int   pin;
  float center_deg;
  float min_deg, max_deg;
};

// ===== Zustand =====
static ICM_20948_I2C imu;
static bool imu_ok = false;
static float gyro_bias_dps[3] = {0, 0, 0};

static Axis axes[2] = {
  {"Y", PIN_SERVO_YAW,   SERVO_YAW_OFFSET,   SERVO_YAW_MIN_DEG,   SERVO_YAW_MAX_DEG},
  {"P", PIN_SERVO_PITCH, SERVO_PITCH_OFFSET, SERVO_PITCH_MIN_DEG, SERVO_PITCH_MAX_DEG},
};
static float    amplitude_deg = 0.0f;    // 0 = aus dem Fenster ableiten
static uint32_t frame_hz      = 50;
static float    servo_volt    = 0.0f;
static char     note[96]      = "";

static Piece    pieces[MAX_PIECES];
static int      n_pieces = 0;

static bool     running    = false;
static int      run_axis   = 0;         // 0 = Y, 1 = P
static bool     then_pitch = false;     // B: nach Y noch P
static int      piece_idx  = 0;
static uint32_t piece_t0_us = 0, run_t0_us = 0, next_sample_us = 0;
static uint32_t rows = 0;
static float    last_rel_deg[2] = {0, 0};

// ===== Servo-PWM =====
static float pulseForDeg(float deg) {
  deg = constrain(deg, 0.0f, 180.0f);
  return SERVO_PULSE_MIN_US + (SERVO_PULSE_MAX_US - SERVO_PULSE_MIN_US) * deg / 180.0f;
}

static void writePulse(int pin, float us) {
  const float period_us = 1e6f / frame_hz;
  const uint32_t maxval = (1UL << PWM_BITS) - 1;
  uint32_t v = (uint32_t)lroundf(us / period_us * maxval);
  if (v > maxval) v = maxval;
  analogWrite(pin, v);
}

// Servo auf absoluten Winkel, innerhalb des Fensters; liefert tatsächlich gesetzten Winkel
static float setServoDeg(int ax, float deg) {
  deg = constrain(deg, axes[ax].min_deg, axes[ax].max_deg);
  writePulse(axes[ax].pin, pulseForDeg(deg));
  last_rel_deg[ax] = deg - axes[ax].center_deg;
  return deg;
}

static void servosSetup() {
  for (int i = 0; i < 2; ++i) {
    pinMode(axes[i].pin, OUTPUT);
    analogWriteFrequency(axes[i].pin, frame_hz);
  }
  analogWriteResolution(PWM_BITS);
  setServoDeg(0, axes[0].center_deg);
  setServoDeg(1, axes[1].center_deg);
}

static float defaultAmplitude(int ax) {
  const float lo = axes[ax].center_deg - axes[ax].min_deg;
  const float hi = axes[ax].max_deg - axes[ax].center_deg;
  return floorf(min(lo, hi));
}

// ===== IMU =====
static bool imuSetup() {
  Wire.begin();
  Wire.setClock(I2C_MAIN_SPEED_HZ);
  bool found = false;
  for (int ad0 = 0; ad0 < 2 && !found; ++ad0) {
    imu.begin(Wire, ad0);
    found = (imu.status == ICM_20948_Stat_Ok);
  }
  if (!found) return false;

  imu.swReset(); delay(250);
  imu.sleep(false);
  imu.lowPower(false);
  imu.setSampleMode(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, ICM_20948_Sample_Mode_Continuous);

  ICM_20948_fss_t fss;
  fss.a = gpm4;        // ±4 g: der Kardan bewegt nur die Lage im Schwerefeld
  fss.g = dps500;      // ±500 °/s: W5652H am Kardan erreichen etwa 200 °/s
  imu.setFullScale(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, fss);

  ICM_20948_dlpcfg_t dlp;
  dlp.a = acc_d111bw4_n136bw;
  dlp.g = gyr_d151bw8_n187bw6;    // 3-dB-Bandbreite 152 Hz, weit über der Servodynamik
  imu.setDLPFcfg(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, dlp);
  imu.enableDLPF(ICM_20948_Internal_Acc, true);
  imu.enableDLPF(ICM_20948_Internal_Gyr, true);

  ICM_20948_smplrt_t sr;
  sr.a = 0; sr.g = 0;             // 1125 Hz intern, wir lesen mit 500 Hz den jeweils letzten Wert
  imu.setSampleRate(ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr, sr);
  delay(50);
  return imu.status == ICM_20948_Stat_Ok;
}

static void readImu(float g[3], float a[3]) {
  imu.getAGMT();
  g[0] = imu.gyrX() - gyro_bias_dps[0];
  g[1] = imu.gyrY() - gyro_bias_dps[1];
  g[2] = imu.gyrZ() - gyro_bias_dps[2];
  a[0] = imu.accX() * 1e-3f;      // g
  a[1] = imu.accY() * 1e-3f;
  a[2] = imu.accZ() * 1e-3f;
}

static void calibrateGyro() {
  if (!imu_ok) return;
  Serial.printf("# Gyro-Nullpunkt: %lu Messungen, bitte ruhig halten\n", (unsigned long)BIAS_SAMPLES);
  double s[3] = {0, 0, 0};
  gyro_bias_dps[0] = gyro_bias_dps[1] = gyro_bias_dps[2] = 0;
  for (uint32_t i = 0; i < BIAS_SAMPLES; ++i) {
    float g[3], a[3];
    readImu(g, a);
    for (int k = 0; k < 3; ++k) s[k] += g[k];
    delayMicroseconds(SAMPLE_US);
  }
  for (int k = 0; k < 3; ++k) gyro_bias_dps[k] = (float)(s[k] / BIAS_SAMPLES);
  Serial.printf("# gyro_bias_dps: %.4f %.4f %.4f\n", gyro_bias_dps[0], gyro_bias_dps[1], gyro_bias_dps[2]);
}

// ===== Anregungsfolge =====
static void addHold(uint8_t seg, float a, float dur_s) {
  if (n_pieces >= MAX_PIECES) return;
  pieces[n_pieces++] = {seg, K_HOLD, a, (uint32_t)(dur_s * 1000.0f)};
}
static void addChirp(uint8_t seg, float a) {
  if (n_pieces >= MAX_PIECES) return;
  pieces[n_pieces++] = {seg, K_CHIRP, a, (uint32_t)(CHIRP_T_S * 1000.0f)};
}

static void buildSequence(float A) {
  n_pieces = 0;
  addHold(SEG_HOLD0, 0, HOLD_START_S);
  // Treppe: 0 -> +A -> -A -> 0 in STAIR_LEVELS Stufen je Richtung (statischer Gain, Hysterese)
  for (int i = 1; i <= STAIR_LEVELS; ++i)          addHold(SEG_STAIR,  A * i / STAIR_LEVELS, STAIR_HOLD_S);
  for (int i = STAIR_LEVELS - 1; i >= -STAIR_LEVELS; --i) addHold(SEG_STAIR, A * i / STAIR_LEVELS, STAIR_HOLD_S);
  for (int i = -STAIR_LEVELS + 1; i <= 0; ++i)     addHold(SEG_STAIR,  A * i / STAIR_LEVELS, STAIR_HOLD_S);
  // Sprünge aus der Mitte: A/4, A/2, A je Richtung, zurück zur Mitte (Totzeit, Anstieg, Überschwingen)
  const float frac[3] = {0.25f, 0.5f, 1.0f};
  for (int s = 0; s < 2; ++s)
    for (int i = 0; i < 3; ++i) {
      addHold(SEG_STEPS, (s == 0 ? 1 : -1) * A * frac[i], STEP_HOLD_S);
      addHold(SEG_STEPS, 0, STEP_HOLD_S);
    }
  // Wechselsprünge +A/-A (Ratenbegrenzung, wie die Messung 2025)
  addHold(SEG_ALT, +A, ALT_HOLD_S); addHold(SEG_ALT, -A, ALT_HOLD_S);
  addHold(SEG_ALT, +A, ALT_HOLD_S); addHold(SEG_ALT, -A, ALT_HOLD_S);
  addHold(SEG_ALT, 0, ALT_HOLD_S);
  // Chirps 0,3..12 Hz, klein und groß (Frequenzgang, Nichtlinearität)
  addChirp(SEG_CHIRP_S, A * 0.25f);
  addHold(SEG_HOLD0, 0, 1.0f);
  addChirp(SEG_CHIRP_L, A * 0.5f);
  addHold(SEG_HOLD1, 0, HOLD_END_S);
}

static float chirpValue(float a, float t_s) {
  const float T = CHIRP_T_S;
  if (t_s < 0) t_s = 0;
  if (t_s > T) t_s = T;
  const float k = logf(CHIRP_F1_HZ / CHIRP_F0_HZ);
  const float phase = 2.0f * PI * CHIRP_F0_HZ * T / k * (expf(t_s * k / T) - 1.0f);
  float env = 1.0f;
  if (t_s < CHIRP_FADE_S)      env = t_s / CHIRP_FADE_S;
  else if (t_s > T - CHIRP_FADE_S) env = (T - t_s) / CHIRP_FADE_S;
  return a * env * sinf(phase);
}

static float sequenceTotalS() {
  uint32_t ms = 0;
  for (int i = 0; i < n_pieces; ++i) ms += pieces[i].dur_ms;
  return ms / 1000.0f;
}

// ===== Ausgabe =====
static void printHeader(int ax, float A) {
  Serial.println("# kartonaut servo_ident v1");
  Serial.printf("# axis: %s\n", axes[ax].name);
  Serial.printf("# servo_pin: %d\n", axes[ax].pin);
  Serial.printf("# center_deg: %.2f\n", axes[ax].center_deg);
  Serial.printf("# window_deg: %.1f %.1f\n", axes[ax].min_deg, axes[ax].max_deg);
  Serial.printf("# amplitude_deg: %.2f\n", A);
  Serial.printf("# pulse_us: %d %d\n", SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  Serial.printf("# frame_hz: %lu\n", (unsigned long)frame_hz);
  Serial.printf("# sample_hz: %lu\n", (unsigned long)SAMPLE_HZ);
  Serial.printf("# chirp: f0_hz=%.2f f1_hz=%.2f t_s=%.1f fade_s=%.2f log\n", CHIRP_F0_HZ, CHIRP_F1_HZ, CHIRP_T_S, CHIRP_FADE_S);
  Serial.printf("# stair: levels=%d hold_s=%.2f\n", STAIR_LEVELS, STAIR_HOLD_S);
  Serial.printf("# step_hold_s: %.2f\n", STEP_HOLD_S);
  Serial.printf("# segments: %s\n", SEG_NAMES);
  Serial.printf("# imu: %s gyro_fs_dps=500 acc_fs_g=4 gyro_dlpf_hz=152\n", imu_ok ? "ICM-20948" : "FEHLT");
  Serial.printf("# gyro_bias_dps: %.4f %.4f %.4f\n", gyro_bias_dps[0], gyro_bias_dps[1], gyro_bias_dps[2]);
  Serial.printf("# servo_volt: %.2f\n", servo_volt);
  Serial.printf("# note: %s\n", note);
  Serial.printf("# duration_s: %.1f\n", sequenceTotalS());
  Serial.println("t_us,seg,axis,servo_deg,cmd_rel_deg,pulse_us,gx_dps,gy_dps,gz_dps,ax_g,ay_g,az_g");
}

static void startRun(int ax) {
  run_axis = ax;
  const float A = (amplitude_deg > 0) ? amplitude_deg : defaultAmplitude(ax);
  buildSequence(A);
  setServoDeg(0, axes[0].center_deg);
  setServoDeg(1, axes[1].center_deg);
  delay(300);
  printHeader(ax, A);
  rows = 0;
  piece_idx = 0;
  running = true;
  run_t0_us = piece_t0_us = next_sample_us = micros();
}

static void stopRun(const char* why) {
  running = false;
  then_pitch = false;
  setServoDeg(0, axes[0].center_deg);
  setServoDeg(1, axes[1].center_deg);
  Serial.printf("# END rows=%lu reason=%s\n", (unsigned long)rows, why);
}

static void runTick() {
  const uint32_t now = micros();
  if ((int32_t)(now - next_sample_us) < 0) return;
  next_sample_us += SAMPLE_US;

  // Stück fortschalten
  while (piece_idx < n_pieces && (now - piece_t0_us) >= pieces[piece_idx].dur_ms * 1000UL) {
    piece_t0_us += pieces[piece_idx].dur_ms * 1000UL;
    ++piece_idx;
  }
  if (piece_idx >= n_pieces) {
    stopRun("done");
    if (then_pitch) { then_pitch = false; delay(500); startRun(1); }
    return;
  }

  const Piece& p = pieces[piece_idx];
  const float t_piece = (now - piece_t0_us) * 1e-6f;
  const float rel = (p.kind == K_HOLD) ? p.a : chirpValue(p.a, t_piece);
  const float abs_deg = setServoDeg(run_axis, axes[run_axis].center_deg + rel);

  float g[3] = {0, 0, 0}, a[3] = {0, 0, 0};
  if (imu_ok) readImu(g, a);

  Serial.printf("%lu,%u,%s,%.3f,%.3f,%.1f,%.3f,%.3f,%.3f,%.4f,%.4f,%.4f\n",
                (unsigned long)(now - run_t0_us), p.seg, axes[run_axis].name,
                abs_deg, abs_deg - axes[run_axis].center_deg, pulseForDeg(abs_deg),
                g[0], g[1], g[2], a[0], a[1], a[2]);
  ++rows;
}

// ===== Befehle =====
static void printStatus() {
  Serial.println("# servo_ident bereit. Befehle: ? Y P B S A C W F M Z V N (siehe Quelltext)");
  Serial.printf("# IMU: %s\n", imu_ok ? "ICM-20948 ok" : "nicht gefunden (Lauf zeichnet nur das Kommando auf)");
  for (int i = 0; i < 2; ++i)
    Serial.printf("# Achse %s: Pin %d, Mitte %.2f, Fenster %.1f..%.1f, Vorgabe-Amplitude %.1f\n",
                  axes[i].name, axes[i].pin, axes[i].center_deg, axes[i].min_deg, axes[i].max_deg, defaultAmplitude(i));
  Serial.printf("# Amplitude: %s%.1f, Pulsrate %lu Hz, Servospannung %.2f V, Notiz: %s\n",
                amplitude_deg > 0 ? "" : "auto ", amplitude_deg > 0 ? amplitude_deg : 0.0f,
                (unsigned long)frame_hz, servo_volt, note);
  buildSequence(amplitude_deg > 0 ? amplitude_deg : defaultAmplitude(0));
  Serial.printf("# Dauer je Achse: %.0f s\n", sequenceTotalS());
}

static int axisIndex(char c) {
  if (c == 'Y' || c == 'y') return 0;
  if (c == 'P' || c == 'p') return 1;
  return -1;
}

static void handleLine(char* line) {
  while (*line == ' ') ++line;
  if (!*line) return;
  const char c = toupper(line[0]);
  char* rest = line + 1;
  switch (c) {
    case '?': printStatus(); break;
    case 'Y': if (!running) startRun(0); break;
    case 'P': if (!running) startRun(1); break;
    case 'B': if (!running) { then_pitch = true; startRun(0); } break;
    case 'S': stopRun("abort"); break;
    case 'Z': if (!running) calibrateGyro(); break;
    case 'A': amplitude_deg = atof(rest); Serial.printf("# amplitude_deg: %.2f\n", amplitude_deg); break;
    case 'F': {
      long f = atol(rest);
      if (f >= 40 && f <= 400) { frame_hz = f; servosSetup(); Serial.printf("# frame_hz: %lu\n", (unsigned long)frame_hz); }
      else Serial.println("# F: 40..400 Hz");
      break;
    }
    case 'V': servo_volt = atof(rest); Serial.printf("# servo_volt: %.2f\n", servo_volt); break;
    case 'N': {
      while (*rest == ' ') ++rest;
      strncpy(note, rest, sizeof(note) - 1); note[sizeof(note) - 1] = 0;
      Serial.printf("# note: %s\n", note);
      break;
    }
    case 'C': {
      float y = 0, p = 0;
      if (sscanf(rest, "%f %f", &y, &p) == 2) {
        axes[0].center_deg = y; axes[1].center_deg = p;
        setServoDeg(0, y); setServoDeg(1, p);
        Serial.printf("# center_deg: %.2f %.2f\n", y, p);
      } else Serial.println("# C <yaw> <pitch>");
      break;
    }
    case 'W': {
      char a = 0; float lo = 0, hi = 0;
      if (sscanf(rest, " %c %f %f", &a, &lo, &hi) == 3 && axisIndex(a) >= 0 && lo < hi && lo >= 0 && hi <= 180) {
        const int ax = axisIndex(a);
        axes[ax].min_deg = lo; axes[ax].max_deg = hi;
        Serial.printf("# window_deg %s: %.1f %.1f (Vorsicht: Kardan-Anschlag von Hand prüfen)\n", axes[ax].name, lo, hi);
      } else Serial.println("# W <Y|P> <min> <max>");
      break;
    }
    case 'M': {
      char a = 0; float d = 0;
      if (!running && sscanf(rest, " %c %f", &a, &d) == 2 && axisIndex(a) >= 0) {
        const int ax = axisIndex(a);
        const float set = setServoDeg(ax, d);
        Serial.printf("# %s auf %.2f Grad (%.0f us)\n", axes[ax].name, set, pulseForDeg(set));
      } else Serial.println("# M <Y|P> <deg>");
      break;
    }
    default: Serial.printf("# unbekannt: %s\n", line);
  }
}

static void pollSerial() {
  static char buf[128];
  static size_t n = 0;
  while (Serial.available()) {
    const char ch = (char)Serial.read();
    if (ch == '\n' || ch == '\r') {
      buf[n] = 0;
      if (n) handleLine(buf);
      n = 0;
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = ch;
    }
  }
}

// ===== Arduino =====
void setup() {
  Serial.begin(115200);
  servosSetup();
  while (!Serial && millis() < 3000) {}
  imu_ok = imuSetup();
  if (imu_ok) calibrateGyro();
  else Serial.println("# WARNUNG: ICM-20948 nicht gefunden (Wire, 0x68/0x69)");
  printStatus();
}

void loop() {
  pollSerial();
  if (running) runTick();
}
