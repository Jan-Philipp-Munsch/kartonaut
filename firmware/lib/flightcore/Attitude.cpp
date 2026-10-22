#include "Attitude.h"

bool Attitude::initFromAccel(const Vec3& a_body) {
  const float n = norm(a_body);
  if (n < 1.0f) return false;
  const Vec3 a = a_body * (1.0f / n);          // „oben“ im Körpersystem
  const Vec3 z(0, 0, 1);
  // kürzeste Drehung a -> z: Achse a × z, Winkel acos(a · z)
  const float d = dot(a, z);
  if (d < -0.9999f) {                            // kopfüber: Drehung um x um 180°
    q_ = Quaternion(0, 1, 0, 0);
    return true;
  }
  // q = (1 + a·z, a × z) normiert, das ist die halbe Drehung ohne trig
  const Vec3 c = cross(a, z);
  q_ = Quaternion(1.0f + d, c.x, c.y, c.z);
  q_.normalize();
  return true;
}

void Attitude::integrateRad(const Vec3& w, float dt) {
  // q̇ = ½ q ⊗ (0, ω); Euler-Schritt reicht bei 100 Hz und < 500 °/s, der
  // Fehler ist zweiter Ordnung in ω·dt und wird durch die Normierung begrenzt.
  const Quaternion wq(0, w.x, w.y, w.z);
  const Quaternion dq = q_ * wq;
  const float h = 0.5f * dt;
  q_.w += dq.w * h; q_.x += dq.x * h; q_.y += dq.y * h; q_.z += dq.z * h;
  q_.normalize();
}

void Attitude::integrateDps(const Vec3& omega_dps, float dt) {
  integrateRad(omega_dps * DEG2RAD, dt);
}

Vec3 Attitude::upBody() const {
  // R(q)ᵀ ẑ ohne Quaternionprodukt: dritte Zeile der Drehmatrix
  const float w = q_.w, x = q_.x, y = q_.y, z = q_.z;
  return Vec3(2.0f * (x*z - w*y),
              2.0f * (y*z + w*x),
              1.0f - 2.0f * (x*x + y*y));
}

float Attitude::tiltDeg() const {
  const Vec3 u = upBody();
  float c = u.z;
  if (c > 1.0f) c = 1.0f; else if (c < -1.0f) c = -1.0f;
  return acosf(c) * RAD2DEG;
}

float Attitude::yawErrDeg() const {
  const Vec3 u = upBody();
  return atan2f(u.y, u.z) * RAD2DEG;
}

float Attitude::pitchErrDeg() const {
  const Vec3 u = upBody();
  return atan2f(-u.x, u.z) * RAD2DEG;
}

float Attitude::rollDeg() const {
  // Körper-x-Achse im Navigationssystem = erste Spalte von R(q)
  const float w = q_.w, x = q_.x, y = q_.y, z = q_.z;
  const float r00 = 1.0f - 2.0f * (y*y + z*z);
  const float r10 = 2.0f * (x*y + w*z);
  return atan2f(r10, r00) * RAD2DEG;
}
