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

  // Fehlervektoren für die Stützung (Körpersystem, rad, Mahony 2008): e = gemessen × geschätzt.
  // accError: Oben-Richtung aus der spezifischen Kraft, gilt nur in Ruhe (|a| ≈ g).
  // magError: Kurs aus dem Magnetfeld, nur die Komponente um die Oben-Achse, damit das
  //           Magnetometer die Kippwinkel nicht verbiegt (Inklination, Störfelder).
  Vec3 accError(const Vec3& a_body) const;
  Vec3 magError(const Vec3& m_body) const;
};

// Mahony-Stützung der Gyro-Lage. Am Boden (SAFE/PAD_READY, Rakete in Ruhe) ziehen Beschleunigung
// und Magnetometer die Lage nach, der I-Anteil lernt den Rest-Nullpunkt des Gyros. Im Flug
// (aid = false) misst der Beschleunigungssensor Schub statt Schwere, und das Magnetometer sitzt
// zwischen Servo- und Motorströmen: dann nur Gyro, mit dem am Boden gelernten Nullpunkt.
struct MahonyAid {
  float kp_acc = 1.0f;    // 1/s: Lagefehler halbiert sich in ~0,7 s
  float kp_mag = 0.5f;    // 1/s
  float ki     = 0.05f;   // 1/s²
  float max_int_dps = 2.0f;   // Grenze des gelernten Nullpunkts
  Vec3  integral_dps;     // wird zur Drehrate addiert

  void reset() { integral_dps = Vec3(); }
  // Korrigierte Drehrate für Attitude::update. m_body = nullptr: ohne Magnetometer.
  Vec3 apply(const Attitude& att, const Vec3& omega_dps, const Vec3& a_body, const Vec3* m_body,
             bool aid, float dt_s);
};
