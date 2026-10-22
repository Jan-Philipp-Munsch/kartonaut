#pragma once
// Control.h – Lageregler für Pitch/Yaw (TVC-Kardan) und Roll (Rollmotor)
// sowie die Ansteuerung der Servos und der H-Brücke.
//
// Alle Winkel in Grad. Die Lage kommt als integrierter Gyro-Winkel aus
// main.cpp (rot_deg: x = Yaw, y = Pitch, z = Roll). Die Regler integrieren
// selbst nur ihre I-Anteile.
#include "Config.h"
#include "MathTypes.h"
#include <PWMServo.h>
#include <Servo.h>

// Ergebnis der Rollregelung, für Logging und Teleplot
struct RollOutput {
  float angle_deg    = 0.0f;   // Roll-Winkel (integriert)
  float rate_dps     = 0.0f;   // Roll-Rate
  float corr_deg     = 0.0f;   // Regelabweichung (Soll 0°)
  float cmd_norm     = 0.0f;   // Stellgröße -1..+1
  int   pwm          = 0;      // 0..ROLL_PWM_MAX
  int   dir          = 0;      // -1, 0, +1
};

// Servos (TVC + Fallschirm) anhängen und auf Mitte stellen
void Control_setup();
// H-Brücke des Rollmotors konfigurieren (PWM-Frequenz und -Auflösung)
void Motor_setup();

// PID auf Yaw (x) und Pitch (y). Rechnet das geforderte Moment über
// M = l * m * |a| * sin(delta) in einen TVC-Winkel um und daraus in
// Servo-Grad (0..180) innerhalb der mechanischen Fenster.
void Control_updatePY(const Vec3& rot_deg,
                      const Vec3& omega_dps,
                      float dt_s,
                      float a_norm_filt,
                      int& yaw_servo_deg,
                      int& pitch_servo_deg);

// PID auf Roll (z) mit Totband und Mindest-PWM, treibt die H-Brücke direkt.
void Control_updateRoll(const Vec3& rot_deg,
                        const Vec3& omega_dps,
                        float dt_s,
                        RollOutput& out);

// Rollmotor stromlos (beide Halbbrücken 0)
void Motor_coast();

// Servowinkel setzen (0..180, wird geklemmt)
void Apply_servos_deg(int yaw_deg, int pitch_deg);
void Chute_servo_deg(int deg);
