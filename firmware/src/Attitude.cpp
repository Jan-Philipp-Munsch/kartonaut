#include "Attitude.h"

static constexpr float DEG2RAD = 3.14159265358979f / 180.0f;
static constexpr float RAD2DEG = 180.0f / 3.14159265358979f;

void Attitude::initFromAccel(const Vec3& a_body) {
  const Vec3 u = normalized(a_body);          // Oben-Vektor im Körpersystem
  const Vec3 ez(0, 0, 1);
  // Drehung, die u auf ez abbildet: Achse u × ez, Winkel acos(u·ez)
  const Vec3  axis = cross(u, ez);
  const float s = norm(axis);
  const float c = dot(u, ez);
  if (s < 1e-6f) {
    q = (c > 0.f) ? Quaternion(1, 0, 0, 0) : Quaternion(0, 1, 0, 0);   // genau oben / genau unten
  } else {
    q = Quaternion::fromAxisAngle(axis * (1.0f / s), atan2f(s, c));
  }
  q.normalize();
  initialized = true;
}

void Attitude::update(const Vec3& omega_dps, float dt_s) {
  const Vec3 w = omega_dps * DEG2RAD;
  const float wn = norm(w);
  Quaternion dq;
  if (wn * dt_s < 1e-6f) {
    // q_dot = 1/2 q ⊗ (0, w), erster Ordnung
    dq = Quaternion(1.0f, 0.5f * w.x * dt_s, 0.5f * w.y * dt_s, 0.5f * w.z * dt_s);
  } else {
    dq = Quaternion::fromAxisAngle(w * (1.0f / wn), wn * dt_s);
  }
  q = q * dq;          // Drehrate im Körpersystem: rechts multiplizieren
  q.normalize();
}

void Attitude::tiltDeg(float& about_x_deg, float& about_y_deg) const {
  const Vec3 u = upBody();
  about_x_deg = atan2f(u.y, u.z) * RAD2DEG;
  about_y_deg = atan2f(-u.x, u.z) * RAD2DEG;
}

float Attitude::tiltTotalDeg() const {
  const Vec3 u = upBody();
  const float c = u.z > 1.f ? 1.f : (u.z < -1.f ? -1.f : u.z);
  return acosf(c) * RAD2DEG;
}

float Attitude::rollDeg() const {
  // Heading: Richtung der Körper-x-Achse in der Navigationsebene
  const Vec3 xb = rotateVector(q, Vec3(1, 0, 0));
  return atan2f(xb.y, xb.x) * RAD2DEG;
}

Vec3 Attitude::accError(const Vec3& a_body) const {
  return cross(normalized(a_body), upBody());
}

Vec3 Attitude::magError(const Vec3& m_body) const {
  // Gemessene Nordrichtung im Navigationssystem; Bezug ist Navigations-x. Als Winkel statt als
  // Kreuzprodukt, damit die Stützung nicht mit cos²(Inklination) schwächer wird (bei uns ~0,2).
  const Vec3 h = rotateVector(q, m_body);
  if (h.x * h.x + h.y * h.y < 1e-12f) return Vec3();
  const float psi = atan2f(h.y, h.x);                      // Kursfehler [rad]
  return upBody() * (-psi);                                // Drehung um die Oben-Achse
}

Vec3 MahonyAid::apply(const Attitude& att, const Vec3& omega_dps, const Vec3& a_body, const Vec3* m_body,
                      bool aid, float dt_s) {
  if (!aid) return omega_dps + integral_dps;
  Vec3 e = att.accError(a_body) * kp_acc;
  Vec3 ei = att.accError(a_body);
  if (m_body) {
    const Vec3 em = att.magError(*m_body);
    e += em * kp_mag;
    ei += em;
  }
  integral_dps += ei * (ki * dt_s * RAD2DEG);
  auto clamp = [&](float& v) { v = v > max_int_dps ? max_int_dps : (v < -max_int_dps ? -max_int_dps : v); };
  clamp(integral_dps.x); clamp(integral_dps.y); clamp(integral_dps.z);
  return omega_dps + e * RAD2DEG + integral_dps;
}
