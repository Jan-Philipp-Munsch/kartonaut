// Control.cpp – siehe Control.h
#include "Control.h"
#include <PWMServo.h>

// Alle drei Servos über PWMServo (hardwaregetaktet, kein Jitter durch Interrupts).
// Bisher lief der Fallschirm-Servo über die Servo-Bibliothek (Befund 7); eine
// Bibliothek reicht, PWMServo kann auf dem Teensy 4.1 jeden PWM-Pin.
static PWMServo yawServo;
static PWMServo pitchServo;
static PWMServo chuteServo;
static float roll_int = 0.0f;

TvcParams Control_tvcParams() {
  TvcParams p;
  p.kp = PY_KP; p.ki = PY_KI; p.kd = PY_KD; p.error_scale = PY_ERROR_SCALE;
  p.mass_kg = MASS_KG; p.moment_arm_m = MOMENT_ARM_M;
  p.a_norm_min = A_NORM_MIN; p.a_norm_alpha = A_NORM_ALPHA;
  p.tvc_max_deg = TVC_MAX_DEG; p.i_max_deg_s = PY_I_MAX_DEG_S;
  p.yaw_gain = SERVO_YAW_GAIN; p.yaw_offset = SERVO_YAW_OFFSET;
  p.yaw_min = SERVO_YAW_MIN_DEG; p.yaw_max = SERVO_YAW_MAX_DEG;
  p.pitch_gain = SERVO_PITCH_GAIN; p.pitch_offset = SERVO_PITCH_OFFSET;
  p.pitch_min = SERVO_PITCH_MIN_DEG; p.pitch_max = SERVO_PITCH_MAX_DEG;
  return p;
}

void Control_setup() {
  if (PIN_MOT_NSLEEP >= 0) { digitalWrite(PIN_MOT_NSLEEP, LOW); pinMode(PIN_MOT_NSLEEP, OUTPUT); }
  if (PIN_MOT_FAULT >= 0)  pinMode(PIN_MOT_FAULT, INPUT_PULLUP);
  pinMode(PIN_MOT_IN1, OUTPUT);
  pinMode(PIN_MOT_IN2, OUTPUT);
  analogWriteFrequency(PIN_MOT_IN1, ROLL_PWM_FREQ_HZ);
  analogWriteFrequency(PIN_MOT_IN2, ROLL_PWM_FREQ_HZ);
  analogWriteResolution(12);   // 0..4095, gilt global für analogWrite()
  Motor_coast();

  yawServo.attach(PIN_SERVO_YAW,     SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  pitchServo.attach(PIN_SERVO_PITCH, SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  chuteServo.attach(PIN_SERVO_CHUTE, SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  Apply_servos_deg(SERVO_YAW_OFFSET, SERVO_PITCH_OFFSET);
  Chute_servo_deg(CHUTE_SERVO_CLOSED_DEG);
}

// PWMServo::write() nimmt ganze Grad; runden statt abschneiden, sonst sitzt die
// Mitte im Mittel einen halben Servo-Grad (bei Gain 6: 0,08° TVC) daneben.
static inline int servoDeg(float d) { return int(lroundf(d < 0.0f ? 0.0f : (d > 180.0f ? 180.0f : d))); }

void Apply_servos_deg(float yaw_deg, float pitch_deg) {
  yawServo.write(servoDeg(yaw_deg));
  pitchServo.write(servoDeg(pitch_deg));
}

void Chute_servo_deg(int deg) {
  chuteServo.write(servoDeg(float(deg)));
}

void Motor_coast() {
  analogWrite(PIN_MOT_IN1, 0);
  analogWrite(PIN_MOT_IN2, 0);
  if (PIN_MOT_NSLEEP >= 0) digitalWrite(PIN_MOT_NSLEEP, LOW);
}

void Roll_motor(float cmd) {
  cmd = constrain(cmd, -1.0f, 1.0f);
  if (fabsf(cmd) < ROLL_CMD_DEADBAND) { Motor_coast(); return; }
  float duty = fabsf(cmd);
  const float duty_min = float(ROLL_PWM_MIN) / float(ROLL_PWM_MAX);
  if (duty < duty_min) duty = duty_min;
  const int pwm = int(lroundf(duty * ROLL_PWM_MAX));
  if (PIN_MOT_NSLEEP >= 0) digitalWrite(PIN_MOT_NSLEEP, HIGH);
  // Neutral = beide 0 (Freilauf). Bremsen wäre beide HIGH.
  analogWrite(PIN_MOT_IN1, cmd > 0 ? pwm : 0);
  analogWrite(PIN_MOT_IN2, cmd > 0 ? 0 : pwm);
}

void Control_resetRoll() { roll_int = 0.0f; }

// ===== Roll =====
void Control_updateRoll(float roll_deg, float roll_rate_dps, float dt_s, RollOutput& out) {
  out.rate_dps  = roll_rate_dps;
  out.angle_deg = roll_deg;
  out.corr_deg  = -roll_deg;        // Soll = 0°

  // PID, D-Anteil über die gemessene Rate
  const float u = ROLL_KP * out.corr_deg + ROLL_KI * roll_int + ROLL_KD * (-out.rate_dps);

  float cmd = constrain(u / ROLL_CMD_SCALE, -1.0f, 1.0f);
  if (fabsf(cmd) < ROLL_CMD_DEADBAND) cmd = 0.0f;

  // Integrator nur, wenn der Regler aktiv stellt (einfaches Anti-Windup)
  if (ROLL_KI != 0.0f && cmd != 0.0f) roll_int += out.corr_deg * dt_s;

  out.cmd_norm = cmd;
  out.dir = (cmd > 0.0f) ? +1 : (cmd < 0.0f ? -1 : 0);
  float duty = fabsf(cmd);
  const float duty_min = float(ROLL_PWM_MIN) / float(ROLL_PWM_MAX);
  if (duty > 0.0f && duty < duty_min) duty = duty_min;
  out.pwm = int(lroundf(duty * ROLL_PWM_MAX));

  Roll_motor(cmd);
}
