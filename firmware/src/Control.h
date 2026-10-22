#pragma once
// Control.h – Aktoren: TVC-Servos, Fallschirm-Servo, Rollmotor (H-Brücke), Rollregler.
//
// Die Pitch/Yaw-Regelung selbst rechnet TvcController (lib/flightcore); hier
// steht nur, was Hardware anfasst. Alle Winkel in Grad.
#include "Config.h"
#include "Board.h"
#include "MathTypes.h"
#include "TvcController.h"

// Ergebnis der Rollregelung, für Logging und Teleplot
struct RollOutput {
  float angle_deg    = 0.0f;   // Roll-Winkel
  float rate_dps     = 0.0f;   // Roll-Rate
  float corr_deg     = 0.0f;   // Regelabweichung (Soll 0°)
  float cmd_norm     = 0.0f;   // Stellgröße -1..+1
  int   pwm          = 0;      // 0..ROLL_PWM_MAX
  int   dir          = 0;      // -1, 0, +1
};

// Servos anhängen und auf Mitte stellen; H-Brücke konfigurieren (Motor stromlos)
void Control_setup();

// TvcParams aus Config.h
TvcParams Control_tvcParams();

// Servowinkel setzen (Grad, werden auf 0..180 geklemmt)
void Apply_servos_deg(float yaw_deg, float pitch_deg);
void Chute_servo_deg(int deg);

// PID auf Roll mit Totband und Mindest-PWM, treibt die H-Brücke direkt.
void Control_updateRoll(float roll_deg, float roll_rate_dps, float dt_s, RollOutput& out);
void Control_resetRoll();

// Rollmotor direkt (-1..+1), für Prüfstand und Kalibrierung
void Roll_motor(float cmd_norm);
// Rollmotor stromlos (beide Halbbrücken 0, rev B: nSLEEP tief)
void Motor_coast();
