// calib_servo – Servo-Mitte, Fenster, Servo-Grad je TVC-Grad und Sprungantwort
//
// Für den neuen Kardan mit den FrSky W5652H (Befund 13: 6 oder 23 Servo-Grad
// je TVC-Grad?). Die IMU misst dabei den Kardanwinkel: Breakout-IMU oder
// das Mainboard so am Innenrahmen bzw. am Motorträger befestigen, dass eine
// Achse mit der Kardanachse zusammenfällt; welche, sagt der Modus 'm'.
// USB-Serial 115200 Bd, Tasten:
//
//   y / Y   Yaw-Servo −1 / +1 Grad        p / P   Pitch-Servo −1 / +1 Grad
//   c       beide auf Config-Mitte         0       beide auf 90
//   w       aktuelle Werte als SERVO_*_OFFSET / Fensterkandidaten ausgeben
//   m       Servo-Grad je TVC-Grad: fährt ±10, ±20 Servo-Grad an, misst den
//           statischen Kardanwinkel aus dem Beschleunigungssensor (Rakete steht
//           senkrecht, der Kardan kippt den Motorträger samt IMU) und gibt
//           SERVO_*_GAIN mit Vorzeichen aus.
//   r       Sprungantwort: Sprünge ±10 und ±20 Servo-Grad um die Mitte, je 1 s,
//           500 Hz Gyro-Integration auf der Kardanachse. Ausgabe als CSV
//           t_ms,servo_soll_deg,kardan_ist_deg, das Format von
//           simulation/data/servo_step_response.csv (fit_servo.py).
//   a       Achse für 'm' und 'r' wählen (x/y/z der IMU), Vorgabe x für Yaw
//   s       Servo für 'm' und 'r' wählen (y = Yaw, p = Pitch)
//   h       Hilfe
#include <Arduino.h>
#include "Config.h"
#include "Board.h"
#include "Sensors.h"
#include "Control.h"

static float yaw_deg = SERVO_YAW_OFFSET, pitch_deg = SERVO_PITCH_OFFSET;
static char  axis = 'x';
static char  servo = 'y';

static void help() {
  Serial.println("\n=== Kartonaut calib_servo (" BOARD_NAME ") ===");
  Serial.println("y/Y p/P jog | c Mitte | 0 90/90 | w Werte | m Gain messen | r Sprungantwort | a Achse | s Servo | h Hilfe");
  Serial.printf("Servo %c, IMU-Achse %c, Yaw %.1f Pitch %.1f\n", servo, axis, yaw_deg, pitch_deg);
}

static void apply() {
  Apply_servos_deg(yaw_deg, pitch_deg);
  Serial.printf("Yaw %.1f  Pitch %.1f\n", yaw_deg, pitch_deg);
}

static void setServo(float deg) {
  if (servo == 'y') yaw_deg = deg; else pitch_deg = deg;
  Apply_servos_deg(yaw_deg, pitch_deg);
}

static float center() { return servo == 'y' ? SERVO_YAW_OFFSET : SERVO_PITCH_OFFSET; }

static float axisOf(const Vec3& v) { return axis == 'x' ? v.x : (axis == 'y' ? v.y : v.z); }

// Neigung um die gewählte Achse aus der Ruhe-Beschleunigung (Grad)
static float staticTilt(int samples) {
  Vec3 sum; int n = 0;
  while (n < samples) { Vec3 a, w; if (Read_IMU_raw(a, w)) { sum += a; ++n; } delay(10); }
  const Vec3 m = sum * (1.0f / n);
  // Kippen um x bewegt y gegen z, Kippen um y bewegt x gegen z
  if (axis == 'x') return atan2f(m.y, m.z) * 57.29578f;
  if (axis == 'y') return atan2f(-m.x, m.z) * 57.29578f;
  return atan2f(m.y, m.x) * 57.29578f;
}

static void measureGain() {
  Serial.println("Gain: Rakete senkrecht, IMU am Kardan. Mitte ...");
  setServo(center()); delay(800);
  const float t0 = staticTilt(100);
  const float steps[4] = {-20, -10, 10, 20};
  float sum_xy = 0, sum_xx = 0;
  for (float s : steps) {
    setServo(center() + s); delay(800);
    const float t = staticTilt(100) - t0;
    Serial.printf("  Servo %+5.1f -> Kardan %+6.2f°  (%.2f Servo-Grad je TVC-Grad)\n", s, t, t != 0 ? s / t : 0);
    sum_xy += s * t; sum_xx += t * t;
  }
  setServo(center());
  const float gain = sum_xx > 0 ? sum_xy / sum_xx : 0;   // Servo-Grad je TVC-Grad, mit Vorzeichen
  Serial.printf("Ausgleichsgerade: %.2f Servo-Grad je TVC-Grad\n", gain);
  Serial.printf("constexpr float SERVO_%s_GAIN     = %.2ff;\n", servo == 'y' ? "YAW" : "PITCH", gain);
  Serial.printf("Fenster für ±%.0f° TVC: %.0f .. %.0f Servo-Grad\n", TVC_MAX_DEG,
                center() - fabsf(gain) * TVC_MAX_DEG, center() + fabsf(gain) * TVC_MAX_DEG);
}

static void stepResponse() {
  Serial.println("Sprungantwort: 500 Hz, Gyro auf der Kardanachse integriert. CSV folgt.");
  Vec3 bias, sd;
  setServo(center()); delay(800);
  Sensors_calibrateGyro(100, 2.0f, bias, sd);
  Serial.println("t_ms,servo_soll_deg,kardan_ist_deg");
  const float seq[8] = {0, 10, 0, -10, 0, 20, 0, -20};
  float angle = 0;
  uint32_t t_start = millis(), next_us = micros(), last_us = micros();
  int k = 0;
  uint32_t t_step = millis();
  setServo(center());
  while (k < 8) {
    if ((int32_t)(micros() - next_us) < 0) continue;
    next_us += 2000;
    Vec3 a, w;
    if (Read_IMU_raw(a, w)) {
      const uint32_t now_us = micros();
      angle += (axisOf(w) - axisOf(bias)) * (now_us - last_us) * 1e-6f;
      last_us = now_us;
    }
    if (millis() - t_step >= 1000) { t_step = millis(); ++k; if (k < 8) setServo(center() + seq[k]); }
    Serial.printf("%lu,%.2f,%.2f\n", (unsigned long)(millis() - t_start), center() + (k < 8 ? seq[k] : 0), angle);
  }
  setServo(center());
  Serial.println("Ende. Zeilen ab 't_ms' in simulation/data/servo_step_response_w5652h.csv speichern, fit_servo.py darauf laufen lassen.");
}

void setup() {
  Serial.begin(115200);
  const uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) {}
  Control_setup();
  Sensors_setup();
  help();
}

void loop() {
  if (!Serial.available()) return;
  const int c = Serial.read();
  switch (c) {
    case 'y': yaw_deg -= 1; apply(); break;
    case 'Y': yaw_deg += 1; apply(); break;
    case 'p': pitch_deg -= 1; apply(); break;
    case 'P': pitch_deg += 1; apply(); break;
    case 'c': yaw_deg = SERVO_YAW_OFFSET; pitch_deg = SERVO_PITCH_OFFSET; apply(); break;
    case '0': yaw_deg = 90; pitch_deg = 90; apply(); break;
    case 'w':
      Serial.printf("constexpr float SERVO_YAW_OFFSET   = %.1ff;\nconstexpr float SERVO_PITCH_OFFSET = %.1ff;\n", yaw_deg, pitch_deg);
      break;
    case 'm': measureGain(); break;
    case 'r': stepResponse(); break;
    case 'a': while (!Serial.available()) {} axis = char(Serial.read()); Serial.printf("IMU-Achse %c\n", axis); break;
    case 's': while (!Serial.available()) {} servo = char(Serial.read()); Serial.printf("Servo %c\n", servo); break;
    case 'h': help(); break;
    default: break;
  }
}
