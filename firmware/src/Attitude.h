#pragma once
// Attitude.h – Lage aus dem Gyro als Quaternion (Plan 22.10.2026, B1; Befund 3)
//
// q dreht Körper -> Navigation (z der Navigation zeigt nach oben). Fortschreibung mit
// q_dot = 1/2 q ⊗ (0, ω), hier als exakte Drehung um den Drehvektor ω·dt je Schritt.
// Auf dem Pad wird q aus der gemessenen spezifischen Kraft initialisiert (sie zeigt in
// Ruhe nach oben), Gieren = 0. Der Regelfehler kommt aus dem Oben-Vektor im Körpersystem
// u = R(q)^T e_z: Kippwinkel um die Körper-x-Achse (Yaw-Servo) = atan2(u_y, u_z), um die
// Körper-y-Achse (Pitch-Servo) = atan2(-u_x, u_z). Für kleine Winkel entspricht das der
// bisherigen Integration rot_deg += ω·dt (Test test_attitude).
// Kein Arduino: läuft in den nativen Tests.
#include "MathTypes.h"

struct Attitude {
  Quaternion q;        // Körper -> Navigation
  bool initialized = false;

  // q so wählen, dass die gemessene spezifische Kraft a_body (in Ruhe = +g nach oben)
  // auf die Navigations-z-Achse fällt. Gieren bleibt 0.
  void initFromAccel(const Vec3& a_body);

  // Drehrate in Grad/s (Körpersystem), Schritt dt in s
  void update(const Vec3& omega_dps, float dt_s);

  // Oben-Vektor im Körpersystem (Einheitsvektor)
  Vec3 upBody() const { return rotateVector(q.conjugate(), Vec3(0, 0, 1)); }

  // Kippwinkel in Grad in Servoachsen: x = Yaw-Achse, y = Pitch-Achse
  void tiltDeg(float& about_x_deg, float& about_y_deg) const;

  // Winkel der Längsachse zur Lotrechten in Grad
  float tiltTotalDeg() const;

  // Drehung um die Längsachse (Heading) in Grad, -180..180
  float rollDeg() const;

  // Beschleunigung ins Navigationssystem drehen und g abziehen (für den Kalman)
  Vec3 accelNav(const Vec3& a_body, float g_ms2) const {
    return rotateVector(q, a_body) - Vec3(0, 0, g_ms2);
  }
};
