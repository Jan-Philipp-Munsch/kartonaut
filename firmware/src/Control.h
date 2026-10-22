#pragma once
// Control.h – Regler Pitch/Yaw (TVC-Kardan) und Roll (Rollmotor) mit der Hardware:
// Servos als 16-Bit-PWM mit SERVO_FRAME_HZ (Grad-zu-Puls wie PWMServo), H-Brücke.
// Die Reglergleichungen selbst stehen in ControlLaw.h (ohne Hardware, native Tests).
#include "Config.h"
#include "ControlLaw.h"
#include "MathTypes.h"

// Servos (TVC + Fallschirm) einrichten und auf Mitte stellen
void Control_setup();
// H-Brücke des Rollmotors konfigurieren (PWM-Frequenz und -Auflösung)
void Motor_setup();

// Pitch/Yaw: Kippwinkel um x (Yaw-Servo) und y (Pitch-Servo) in Grad, Drehraten, |a| gefiltert.
// Liefert Servo-Grad und Kardanwinkel; stellt die Servos.
PyOutput Control_updatePY(float tilt_x_deg, float tilt_y_deg, const Vec3& omega_dps, float dt_s, float a_norm_filt);
void     Control_resetPY();

// Roll: treibt die H-Brücke
RollOutput Control_updateRoll(float roll_deg, float roll_rate_dps, float dt_s);
void       Control_resetRoll();

// Rollmotor stromlos (beide Halbbrücken 0)
void Motor_coast();

// Servowinkel direkt setzen (0..180 Grad, Fenster wird nicht angewendet)
void Apply_servos_deg(float yaw_deg, float pitch_deg);
void Servos_center();
void Chute_servo_deg(float deg);
// Schubdrossel: u in [0, 1] (0 = Pads draußen); ohne PIN_SERVO_THROTTLE wirkungslos
void Throttle_set(float u);
