#pragma once
// ControlLaw.h – die reinen Reglergleichungen (ohne Hardware), für Flug und native Tests.
//
// Pitch/Yaw: PID auf den Kippwinkeln (Grad) mit Skalierung 1/PY_ERROR_SCALE, Ausgang ein
// Moment [N m], Umrechnung in den TVC-Winkel über M = l·m·|a|·sin(delta), dann in Servo-Grad
// über die linearisierte Kardangeometrie und das mechanische Fenster. Rechnet exakt wie
// tvcsim.controller.FirmwareController (Test test_controllaw_sil gegen exportierte Vektoren).
// Roll: PID auf Rollwinkel und -rate mit Totband und Mindest-PWM.
#include <stdint.h>

struct PyGains {
  float kp, ki, kd, error_scale, int_limit;
  float mass_kg, arm_m, a_norm_min;
  float yaw_gain, yaw_offset, pitch_gain, pitch_offset;
  float yaw_min, yaw_max, pitch_min, pitch_max;
};

struct PyOutput {
  float yaw_moment_nm = 0, pitch_moment_nm = 0;
  float yaw_tvc_deg = 0, pitch_tvc_deg = 0;       // kommandierter Kardanwinkel (nach Fenster)
  float yaw_servo_deg = 90, pitch_servo_deg = 90; // Servo-Grad 0..180
};

class PyControlLaw {
public:
  explicit PyControlLaw(const PyGains& g) : g_(g) {}
  void reset() { int_x_ = int_y_ = 0; }
  // Winkel in Grad (x = Yaw-Achse, y = Pitch-Achse), Drehraten in Grad/s, |a| gefiltert in m/s²
  PyOutput update(float angle_x_deg, float angle_y_deg, float omega_x_dps, float omega_y_dps,
                  float dt_s, float a_norm_filt);
  float integralX() const { return int_x_; }
  float integralY() const { return int_y_; }
private:
  PyGains g_;
  float int_x_ = 0, int_y_ = 0;
};

struct RollGains {
  float kp, ki, kd, cmd_scale, deadband;
  int   pwm_min, pwm_max;
};

struct RollOutput {
  float angle_deg = 0, rate_dps = 0, corr_deg = 0, cmd_norm = 0;
  int   pwm = 0, dir = 0;
};

class RollControlLaw {
public:
  explicit RollControlLaw(const RollGains& g) : g_(g) {}
  void reset() { int_ = 0; }
  RollOutput update(float roll_deg, float roll_rate_dps, float dt_s);
private:
  RollGains g_;
  float int_ = 0;
};

// Servo-Grad -> Pulsbreite wie PWMServo: linear zwischen min_us (0°) und max_us (180°)
inline float servoPulseUs(float deg, int min_us, int max_us) {
  if (deg < 0) deg = 0; else if (deg > 180) deg = 180;
  return min_us + (max_us - min_us) * deg / 180.0f;
}
