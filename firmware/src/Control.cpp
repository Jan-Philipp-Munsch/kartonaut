// Control.cpp – siehe Control.h
#include "Control.h"

// --- Aktoren ---
static PWMServo yawServo;     // TVC, PWMServo: hardwaregetaktet, keine Jitter durch Interrupts
static PWMServo pitchServo;
static Servo    chuteServo;   // Fallschirm (eigene Bibliothek, teilt sich die Timer mit PWMServo)

void Motor_setup(){
  pinMode(PIN_MOT_IN1, OUTPUT);
  pinMode(PIN_MOT_IN2, OUTPUT);
  analogWriteFrequency(PIN_MOT_IN1, ROLL_PWM_FREQ_HZ);
  analogWriteFrequency(PIN_MOT_IN2, ROLL_PWM_FREQ_HZ);
  analogWriteResolution(12);   // 0..4095, gilt global für analogWrite()
  Motor_coast();
}

void Motor_coast(){
  analogWrite(PIN_MOT_IN1, 0);
  analogWrite(PIN_MOT_IN2, 0);
}

void Control_setup(){
  yawServo.attach(PIN_SERVO_YAW,     SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  pitchServo.attach(PIN_SERVO_PITCH, SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US);
  chuteServo.attach(PIN_SERVO_CHUTE);
  Apply_servos_deg(SERVO_DEG_CENTER, SERVO_DEG_CENTER);
}

static inline int clampDeg(int d){
  if (d < 0)   return 0;
  if (d > 180) return 180;
  return d;
}

void Apply_servos_deg(int yaw_deg, int pitch_deg){
  yawServo.write(clampDeg(yaw_deg));
  pitchServo.write(clampDeg(pitch_deg));
}

void Chute_servo_deg(int deg){
  chuteServo.write(clampDeg(deg));
}

// ===== Pitch/Yaw (TVC) =====
void Control_updatePY(const Vec3& rot_deg,
                      const Vec3& omega_dps,
                      float dt_s,
                      float a_norm_filt,
                      int& yaw_servo_deg,
                      int& pitch_servo_deg)
{
  static Vec3 rot_int_deg_s = {0,0,0};   // Integrator [deg*s]
  rot_int_deg_s += rot_deg * dt_s;

  // PID auf skaliertem Winkel; Ausgang ist ein gefordertes Moment [N m]
  const float yaw_moment   = PY_KP * (rot_deg.x       / PY_ERROR_SCALE)
                           + PY_KI * (rot_int_deg_s.x / PY_ERROR_SCALE)
                           + PY_KD * (omega_dps.x     / PY_ERROR_SCALE);
  const float pitch_moment = PY_KP * (rot_deg.y       / PY_ERROR_SCALE)
                           + PY_KI * (rot_int_deg_s.y / PY_ERROR_SCALE)
                           + PY_KD * (omega_dps.y     / PY_ERROR_SCALE);

  // Moment -> Auslenkwinkel des Schubvektors: M = l * m * |a| * sin(delta)
  const float denom = MOMENT_ARM_M * MASS_KG * max(a_norm_filt, A_NORM_MIN);
  const float yaw_tvc_rad   = asinf(constrain(yaw_moment   / denom, -0.99f, 0.99f));
  const float pitch_tvc_rad = asinf(constrain(pitch_moment / denom, -0.99f, 0.99f));

  // Linearisierte Gimbal-Geometrie -> Servo-Grad
  const float yaw_deg   = (yaw_tvc_rad   * 180.0f / PI) * SERVO_YAW_GAIN   + SERVO_YAW_OFFSET;
  const float pitch_deg = (pitch_tvc_rad * 180.0f / PI) * SERVO_PITCH_GAIN + SERVO_PITCH_OFFSET;

  // Mechanische Fenster des Kardans
  const float yaw_clamp   = constrain(yaw_deg,   SERVO_YAW_MIN_DEG,   SERVO_YAW_MAX_DEG);
  const float pitch_clamp = constrain(pitch_deg, SERVO_PITCH_MIN_DEG, SERVO_PITCH_MAX_DEG);

  yaw_servo_deg   = clampDeg((int)lroundf(yaw_clamp));
  pitch_servo_deg = clampDeg((int)lroundf(pitch_clamp));
}

// ===== Roll =====
void Control_updateRoll(const Vec3& rot_deg,
                        const Vec3& omega_dps,
                        float dt_s,
                        RollOutput& out)
{
  static float roll_int = 0.0f;

  out.rate_dps  = omega_dps.z;
  out.angle_deg = rot_deg.z;
  out.corr_deg  = -out.angle_deg;        // Soll = 0°

  // PID, D-Anteil über die gemessene Rate
  const float u = ROLL_KP * out.corr_deg + ROLL_KI * roll_int + ROLL_KD * (-out.rate_dps);

  float cmd = constrain(u / ROLL_CMD_SCALE, -1.0f, 1.0f);
  if (fabsf(cmd) < ROLL_CMD_DEADBAND) cmd = 0.0f;

  // Integrator nur, wenn der Regler aktiv stellt (einfaches Anti-Windup)
  if (ROLL_KI != 0.0f && cmd != 0.0f) roll_int += out.corr_deg * dt_s;

  out.cmd_norm = cmd;
  out.dir = (cmd > 0.0f) ? +1 : (cmd < 0.0f ? -1 : 0);

  float duty = fabsf(cmd);
  const float duty_min = (float)ROLL_PWM_MIN / (float)ROLL_PWM_MAX;
  if (duty > 0.0f && duty < duty_min) duty = duty_min;
  out.pwm = (int)lroundf(duty * ROLL_PWM_MAX);

  // Neutral = beide 0 (Freilauf). Bremsen wäre beide HIGH.
  if (out.dir > 0) {
    analogWrite(PIN_MOT_IN1, out.pwm);
    analogWrite(PIN_MOT_IN2, 0);
  } else if (out.dir < 0) {
    analogWrite(PIN_MOT_IN1, 0);
    analogWrite(PIN_MOT_IN2, out.pwm);
  } else {
    Motor_coast();
  }
}
