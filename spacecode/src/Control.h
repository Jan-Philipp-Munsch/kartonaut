#pragma once
#include "Config.h"
#include "MathTypes.h"
#include <PWMServo.h>
#include <Servo.h>


struct AttState {
  Vec3 rot_deg;      // integrierte Rotation (Yaw, Pitch, Roll) in deg
  Vec3 rot_int_deg;  // Integrator
};

void Control_setup();
void Motor_setup();

void Control_updateRoll(const Vec3& omega_dps,
                        const Vec3& rot_prev_deg,
                        float dt_meas,
                        // Outputs:
                        float& roll_angle_deg,
                        float& roll_rate_dps,
                        float& roll_corr_angle_deg,
                        float& roll_cmd_norm,  // -1..+1
                        int&   roll_pwm,       // 0..4095
                        int&   roll_dir);      // -1,0,+1

// Regler berechnet direkt Ziel-Servowinkel in Grad (0..180)
void Control_updatePY(const Vec3& omega_dps,
                      const Vec3& rot_prev_deg,
                      float dt_meas,
                      float a_norm_filt,
                      int& yaw_deg_out,     // 0..180°
                      int& pitch_deg_out,   // 0..180°
                      AttState& out_state);

// setzt die Servos (PWMServo.write expects degrees 0..180)
void Apply_servos_deg(int yaw_deg, int pitch_deg);
