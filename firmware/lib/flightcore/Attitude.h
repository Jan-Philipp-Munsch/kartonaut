#pragma once
// Attitude.h – Lage rein aus dem Gyro als Quaternion (PROJECT.md §5, Befund 3)
//
// Körpersystem: x und y quer, z entlang der Rollachse zur Spitze. Navigations-
// system: z nach oben. q dreht Körper -> Navigation.
//
//   Initialisierung auf der Rampe: der ruhende Beschleunigungssensor misst die
//   spezifische Kraft, also +g entlang „oben“. Die kürzeste Drehung, die diesen
//   Vektor auf ẑ legt, ist die Startlage (ohne Drehung um die Hochachse).
//   Integration: q̇ = ½ q ⊗ (0, ω) mit ω im Körpersystem [rad/s]; nach jedem
//   Schritt normiert.
//   Regelfehler: Oben-Vektor im Körpersystem u = R(q)ᵀ ẑ. Daraus
//     yaw_deg   = atan2( u.y, u.z)   (Drehung um die Körper-x-Achse)
//     pitch_deg = atan2(-u.x, u.z)   (Drehung um die Körper-y-Achse)
//   Für kleine Winkel ohne Rollen sind das genau die bisher integrierten
//   rot_deg.x / rot_deg.y; mit Rollen landen sie in der richtigen Servoachse.
//   roll_deg ist die Drehung der Körper-x-Achse um die Hochachse seit der
//   Initialisierung (Kurs der x-Achse im Navigationssystem).
#include "MathTypes.h"

class Attitude {
public:
  // Startlage aus einer gemittelten Ruhemessung der spezifischen Kraft [m/s², Körper].
  // Liefert false, wenn der Vektor unbrauchbar ist (zu kurz); q bleibt dann unverändert.
  bool initFromAccel(const Vec3& a_body);

  // Einheitsquaternion direkt setzen (Zustandsspeicher nach Neustart)
  void set(const Quaternion& q) { q_ = q; q_.normalize(); }

  // Einen Schritt integrieren, Drehrate im Körpersystem in °/s
  void integrateDps(const Vec3& omega_dps, float dt_s);
  void integrateRad(const Vec3& omega_rad_s, float dt_s);

  const Quaternion& q() const { return q_; }

  Vec3  upBody() const;                      // u = R(q)ᵀ ẑ
  float tiltDeg() const;                     // Winkel Rollachse zur Lotrechten
  float yawErrDeg() const;                   // um Körper-x
  float pitchErrDeg() const;                 // um Körper-y
  float rollDeg() const;                     // Kurs der Körper-x-Achse, −180..180

  Vec3 toNav(const Vec3& v_body) const { return rotateVector(q_, v_body); }
  Vec3 toBody(const Vec3& v_nav) const { return rotateVectorInverse(q_, v_nav); }

  // Beschleunigung im Navigationssystem ohne Schwerkraft (Eingang des Höhen-Kalman)
  Vec3 accelNav(const Vec3& a_body_ms2, float g_ms2) const {
    Vec3 a = toNav(a_body_ms2); a.z -= g_ms2; return a;
  }

  static constexpr float DEG2RAD = 3.14159265358979f / 180.0f;
  static constexpr float RAD2DEG = 180.0f / 3.14159265358979f;

private:
  Quaternion q_;
};
