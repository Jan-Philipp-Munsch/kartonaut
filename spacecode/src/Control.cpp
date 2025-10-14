#include "Control.h"

// --- TVC-Servos ---
static PWMServo yawServo;
static PWMServo pitchServo;
static Servo    chuteServo;

void Motor_setup(){
  pinMode(PIN_MOT_IN1, OUTPUT);
  pinMode(PIN_MOT_IN2, OUTPUT);
  analogWriteFrequency(PIN_MOT_IN1, 20000);
  analogWriteFrequency(PIN_MOT_IN2, 20000);
  analogWriteResolution(12); // 0..4095
  analogWrite(PIN_MOT_IN1, 0);
  analogWrite(PIN_MOT_IN2, 0);
}

void Control_setup(){
  // PWMServo.write() erwartet Grad; Pulsbreiten hier beim attach setzen
  yawServo.attach(PIN_SERVO_YAW,    760, 2300);
  pitchServo.attach(PIN_SERVO_PITCH,760, 2300);
  chuteServo.attach(PIN_SERVO_CHUTE);

  yawServo.write(90);
  pitchServo.write(90);
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

// ===== Pitch/Yaw TVC =====
void Control_updatePY(const Vec3& omega_dps,
                      const Vec3& rot_prev_deg,
                      float dt_meas,
                      float a_norm_filt,
                      int& yaw_deg_out,
                      int& pitch_deg_out,
                      AttState& out_state)
{
  // Gains (Startwerte)
  const float Kp = 5.0f;
  const float Ki = 0.0f;
  const float Kd = 1.0f;

  static Vec3 rot_deg = {0,0,0};
  static Vec3 rot_int_deg = {0,0,0};

  rot_deg = rot_prev_deg + omega_dps * dt_meas;   // deg
  rot_int_deg += rot_deg * dt_meas;               // deg*s

  const float yaw_moment   = ( Kp * (rot_deg.x / -100.0f) + Ki * (rot_int_deg.x / -100.0f) + Kd * (omega_dps.x / -100.0f) );
  const float pitch_moment = ( Kp * (rot_deg.y / -100.0f) + Ki * (rot_int_deg.y / -100.0f) + Kd * (omega_dps.y / -100.0f) );

  const float denom = MOMENT_ARM_M * MASS_KG * max(a_norm_filt, A_NORM_MIN);

  float yaw_TVC_rad   = asinf( constrain(yaw_moment   / denom, -0.99f, 0.99f) );
  float pitch_TVC_rad = asinf( constrain(pitch_moment / denom, -0.99f, 0.99f) );

  // Linearisierte Servoumsetzung (aus deinem Code)
  const float yaw_deg   = (yaw_TVC_rad   * 180.0f / PI) * (-23.0f) + 92.5f;
  const float pitch_deg = (pitch_TVC_rad * 180.0f / PI) * ( 23.0f) + 82.5f;

  // Begrenzungen (mechanische Fenster)
  const float yaw_deg_clamp   = constrain(yaw_deg,   70.0f, 115.0f);
  const float pitch_deg_clamp = constrain(pitch_deg, 60.0f, 105.0f);

  yaw_deg_out   = clampDeg( (int)lroundf(yaw_deg_clamp) );
  pitch_deg_out = clampDeg( (int)lroundf(pitch_deg_clamp) );

  out_state.rot_deg = rot_deg;
  out_state.rot_int_deg = rot_int_deg;
}

// ===== Roll-Regelung + Motor-Drive =====
void Control_updateRoll(const Vec3& omega_dps,
                        const Vec3& rot_prev_deg,
                        float dt_meas,
                        float& roll_angle_deg,
                        float& roll_rate_dps,
                        float& roll_corr_angle_deg,
                        float& roll_cmd_norm,
                        int&   roll_pwm,
                        int&   roll_dir)
{
  // Gains (Startwerte; gern in RocketConfig auslagern)
  const float Kp = 1.2f;
  const float Ki = 0.0f;
  const float Kd = 1.0f;

  // Stellgrößenbegrenzung & Mindest-PWM
  const float CMD_MAX      = 1.0f;
  const float CMD_DEADBAND = 0.02f;  // 2 %
  const int   MIN_PWM      = 600;    // ca. 15 % von 4095 (tunen)

  static float roll_int = 0.0f;

  // Zustand
  roll_rate_dps  = omega_dps.z;
  roll_angle_deg = rot_prev_deg.z + roll_rate_dps * dt_meas;

  // Soll = 0°, Korrekturwinkel = -Roll-Winkel
  roll_corr_angle_deg = -roll_angle_deg;

  // PID (D-Anteil über Rate, passend zum Original)
  const float u = Kp * roll_corr_angle_deg + Ki * roll_int + Kd * (-roll_rate_dps);

  // Normierung [-1..+1]
  float cmd = u / 200.0f;                 // Skalierung wie im Prototyp
  cmd = constrain(cmd, -CMD_MAX, CMD_MAX);

  // Deadband
  if (fabsf(cmd) < CMD_DEADBAND) cmd = 0.0f;

  // Integrator (simpel, Anti-Windup: nur wenn aktiv)
  if (Ki != 0.0f && cmd != 0.0f) {
    roll_int += roll_corr_angle_deg * dt_meas;
  }

  roll_cmd_norm = cmd;

  // Richtung & PWM
  if (cmd > 0.0f)      roll_dir = +1;
  else if (cmd < 0.0f) roll_dir = -1;
  else                 roll_dir = 0;

  float duty = fabsf(cmd);
  if (duty > 0.0f && duty < (float)MIN_PWM/4095.0f) duty = (float)MIN_PWM/4095.0f;
  roll_pwm = (int)lroundf(duty * 4095.0f);

  // Neutral = beide 0 (Coast). (Wenn Brake gewünscht: beide HIGH.)
  if (roll_dir > 0) {
    analogWrite(PIN_MOT_IN1, roll_pwm);
    analogWrite(PIN_MOT_IN2, 0);
  } else if (roll_dir < 0) {
    analogWrite(PIN_MOT_IN1, 0);
    analogWrite(PIN_MOT_IN2, roll_pwm);
  } else {
    analogWrite(PIN_MOT_IN1, 0);
    analogWrite(PIN_MOT_IN2, 0);
  }
}

