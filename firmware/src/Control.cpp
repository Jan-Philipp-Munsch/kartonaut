// Control.cpp – siehe Control.h
#include "Control.h"
#include <Arduino.h>
#include <Servo.h>

static constexpr int PWM_BITS = 16;
static Servo chuteServo;                 // Fallschirm (Reserve), eigene Bibliothek, 50 Hz

static PyControlLaw pyLaw(PyGains{PY_KP, PY_KI, PY_KD, PY_ERROR_SCALE, PY_INT_LIMIT, MASS_KG, MOMENT_ARM_M, A_NORM_MIN,
                                  SERVO_YAW_GAIN, SERVO_YAW_OFFSET, SERVO_PITCH_GAIN, SERVO_PITCH_OFFSET,
                                  SERVO_YAW_MIN_DEG, SERVO_YAW_MAX_DEG, SERVO_PITCH_MIN_DEG, SERVO_PITCH_MAX_DEG});
static RollControlLaw rollLaw(RollGains{ROLL_KP, ROLL_KI, ROLL_KD, ROLL_CMD_SCALE, ROLL_CMD_DEADBAND, ROLL_PWM_MIN, ROLL_PWM_MAX});

static void writeServoPulse(int pin, float us) {
  const float period_us = 1e6f / SERVO_FRAME_HZ;
  const uint32_t maxval = (1UL << PWM_BITS) - 1;
  uint32_t v = (uint32_t)lroundf(us / period_us * maxval);
  if (v > maxval) v = maxval;
  analogWrite(pin, v);
}

void Motor_setup(){
  pinMode(PIN_MOT_IN1, OUTPUT);
  pinMode(PIN_MOT_IN2, OUTPUT);
  analogWriteFrequency(PIN_MOT_IN1, ROLL_PWM_FREQ_HZ);
  analogWriteFrequency(PIN_MOT_IN2, ROLL_PWM_FREQ_HZ);
#ifdef BOARD_REVB
  pinMode(PIN_MOT_NSLEEP, OUTPUT);
  digitalWrite(PIN_MOT_NSLEEP, LOW);     // DRV8833 schlafend, bis die Rollregelung läuft
#endif
  Motor_coast();
}

void Motor_coast(){
  // analogWrite mit 16 Bit: die Rollmotor-Werte sind 12 Bit (0..4095), hochskalieren
  analogWrite(PIN_MOT_IN1, 0);
  analogWrite(PIN_MOT_IN2, 0);
}

void Control_setup(){
  // Pins 28/29 liegen auf demselben FlexPWM-Submodul und teilen sich die Frequenz.
  analogWriteResolution(PWM_BITS);        // gilt global (auch Rollmotor, siehe Motor_coast)
  pinMode(PIN_SERVO_YAW, OUTPUT);
  pinMode(PIN_SERVO_PITCH, OUTPUT);
  analogWriteFrequency(PIN_SERVO_YAW, SERVO_FRAME_HZ);
  analogWriteFrequency(PIN_SERVO_PITCH, SERVO_FRAME_HZ);
  chuteServo.attach(PIN_SERVO_CHUTE);
  Chute_servo_deg(CHUTE_SERVO_CLOSED_DEG);
  Servos_center();
}

void Apply_servos_deg(float yaw_deg, float pitch_deg){
  writeServoPulse(PIN_SERVO_YAW,   servoPulseUs(yaw_deg,   SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US));
  writeServoPulse(PIN_SERVO_PITCH, servoPulseUs(pitch_deg, SERVO_PULSE_MIN_US, SERVO_PULSE_MAX_US));
}

void Servos_center(){ Apply_servos_deg(SERVO_YAW_OFFSET, SERVO_PITCH_OFFSET); }

void Chute_servo_deg(float deg){
  int d = (int)lroundf(deg);
  chuteServo.write(d < 0 ? 0 : (d > 180 ? 180 : d));
}

PyOutput Control_updatePY(float tilt_x_deg, float tilt_y_deg, const Vec3& omega_dps, float dt_s, float a_norm_filt){
  const PyOutput o = pyLaw.update(tilt_x_deg, tilt_y_deg, omega_dps.x, omega_dps.y, dt_s, a_norm_filt);
  Apply_servos_deg(o.yaw_servo_deg, o.pitch_servo_deg);
  return o;
}

void Control_resetPY(){ pyLaw.reset(); }
void Control_resetRoll(){ rollLaw.reset(); }

RollOutput Control_updateRoll(float roll_deg, float roll_rate_dps, float dt_s){
  const RollOutput o = rollLaw.update(roll_deg, roll_rate_dps, dt_s);
  // 12-Bit-Werte des Reglers auf die 16-Bit-Auflösung
  const uint32_t pwm16 = (uint32_t)o.pwm * ((1UL << PWM_BITS) - 1) / ROLL_PWM_MAX;
#ifdef BOARD_REVB
  digitalWrite(PIN_MOT_NSLEEP, o.dir != 0 ? HIGH : LOW);
#endif
  if (o.dir > 0)      { analogWrite(PIN_MOT_IN1, pwm16); analogWrite(PIN_MOT_IN2, 0); }
  else if (o.dir < 0) { analogWrite(PIN_MOT_IN1, 0);     analogWrite(PIN_MOT_IN2, pwm16); }
  else                { Motor_coast(); }
  return o;
}
