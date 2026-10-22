#pragma once
// TvcController.h – PID Pitch/Yaw und Umrechnung Moment -> TVC-Winkel -> Servo-Grad
//
// Reine Rechnung ohne Hardware, damit sie nativ getestet und gegen die
// Python-Simulation (simulation/tvcsim/controller.py, FirmwareController)
// gehalten werden kann. Dieselbe Formel wie bisher in Control.cpp:
//
//   M      = Kp·(e/S) + Ki·(∫e/S) + Kd·(ω/S)        S = PY_ERROR_SCALE (−100)
//   δ      = asin(M / (l·m·|a|))                      M = l·m·|a|·sin δ
//   servo  = δ_deg·GAIN + OFFSET, geklemmt auf das mechanische Fenster
//
// Neu: der Fehler e kommt aus dem Oben-Vektor der Quaternion (Attitude), nicht
// mehr aus rot_deg; der Integrator hat ein Anti-Windup, und die Servowerte
// werden als float gehalten (die Rundung auf ganze Grad macht der Aufrufer).
#include "MathTypes.h"

struct TvcParams {
  float kp = 5.0f, ki = 0.0f, kd = 1.0f;
  float error_scale = -100.0f;
  float mass_kg = 0.761f;
  float moment_arm_m = 0.242f;
  float a_norm_min = 1.0f;         // m/s², Schutz gegen Division durch 0
  float a_norm_alpha = 0.1f;       // Tiefpass auf |a|
  float asin_clamp = 0.99f;
  float tvc_max_deg = 7.0f;        // mechanischer Kardanbereich (CAD: ±7°)
  float i_max_deg_s = 500.0f;      // Anti-Windup für ∫e [°·s]
  // Servo-Linearisierung je Achse
  float yaw_gain = -23.0f,  yaw_offset = 92.5f,  yaw_min = 70.0f,  yaw_max = 115.0f;
  float pitch_gain = 23.0f, pitch_offset = 82.5f, pitch_min = 60.0f, pitch_max = 105.0f;
};

struct TvcOutput {
  float yaw_moment_nm = 0, pitch_moment_nm = 0;
  float yaw_tvc_deg = 0, pitch_tvc_deg = 0;      // nach Klemmung auf tvc_max_deg
  float yaw_servo_deg = 90, pitch_servo_deg = 90; // nach Fenster
  bool  yaw_saturated = false, pitch_saturated = false;
};

class TvcController {
public:
  explicit TvcController(const TvcParams& p = TvcParams()) : p_(p) {}

  void reset();                               // Integratoren und |a|-Filter auf Start
  void setParams(const TvcParams& p) { p_ = p; }
  const TvcParams& params() const { return p_; }

  // |a| in den Tiefpass geben (jeden Takt, auch wenn der Regler nicht stellt)
  void updateAccelNorm(float a_norm_ms2);
  float accelNormFilt() const { return a_norm_filt_; }

  // Ein Regelschritt. yaw_err/pitch_err in Grad (Attitude::yawErrDeg/pitchErrDeg),
  // omega in °/s im Körpersystem, dt in s.
  TvcOutput update(float yaw_err_deg, float pitch_err_deg, const Vec3& omega_dps, float dt_s);

  // Ruhelage (Servos auf Mitte des Fensters laut Offset)
  TvcOutput neutral() const;

  // Servo-Grad für einen gewünschten TVC-Winkel (Kalibrierung, Prüfstand)
  float yawServoForTvc(float tvc_deg) const;
  float pitchServoForTvc(float tvc_deg) const;

private:
  TvcParams p_;
  float i_yaw_ = 0, i_pitch_ = 0;    // ∫e [°·s]
  float a_norm_filt_ = 9.81f;
};
