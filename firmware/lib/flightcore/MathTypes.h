#pragma once
// MathTypes.h – Vektor und Quaternion der Flug-Firmware.
//
// Ohne Arduino-Abhängigkeit, damit lib/flightcore auch in der nativen
// Testumgebung baut. Konvention: Quaternion (w, x, y, z), Hamilton-Produkt,
// rotateVector(q, v) = q v q* dreht einen Vektor vom Körper- ins Navigationssystem,
// wenn q die Lage Körper -> Navigation beschreibt.
#include <math.h>

struct Vec3 {
  float x, y, z;
  Vec3(float x_=0, float y_=0, float z_=0): x(x_),y(y_),z(z_) {}

  Vec3 operator+(const Vec3& o) const { return {x+o.x,y+o.y,z+o.z}; }
  Vec3 operator-(const Vec3& o) const { return {x-o.x,y-o.y,z-o.z}; }
  Vec3 operator*(float s) const { return {x*s,y*s,z*s}; }
  Vec3& operator+=(const Vec3& o) { x+=o.x; y+=o.y; z+=o.z; return *this; }
  Vec3& operator*=(float s) { x*=s; y*=s; z*=s; return *this; }
};

inline Vec3 operator*(float s, const Vec3& v) { return v*s; }
inline float dot(const Vec3& a, const Vec3& b){ return a.x*b.x + a.y*b.y + a.z*b.z; }
inline Vec3  cross(const Vec3& a, const Vec3& b){
  return {a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y - a.y*b.x};
}
inline float norm(const Vec3& v){ return sqrtf(dot(v,v)); }
inline Vec3  normalized(const Vec3& v){ const float n = norm(v); return n > 0.f ? v * (1.0f/n) : Vec3(0,0,1); }

struct Quaternion {
  float w,x,y,z;
  Quaternion(float w_=1,float x_=0,float y_=0,float z_=0): w(w_),x(x_),y(y_),z(z_) {}

  Quaternion conjugate() const { return {w,-x,-y,-z}; }

  Quaternion operator*(const Quaternion& b) const {
    return {
      w*b.w - x*b.x - y*b.y - z*b.z,
      w*b.x + x*b.w + y*b.z - z*b.y,
      w*b.y - x*b.z + y*b.w + z*b.x,
      w*b.z + x*b.y - y*b.x + z*b.w
    };
  }

  float normSq() const { return w*w + x*x + y*y + z*z; }

  void normalize() {
    const float m = sqrtf(normSq());
    if (m > 0.f) { w/=m; x/=m; y/=m; z/=m; }
    else { w=1; x=y=z=0; }
  }

  // Drehung um eine Einheitsachse (Körper) um angle_rad
  static Quaternion fromAxisAngle(const Vec3& axis, float angle_rad) {
    const float h = 0.5f * angle_rad, s = sinf(h);
    return {cosf(h), axis.x*s, axis.y*s, axis.z*s};
  }
};

inline Vec3 rotateVector(const Quaternion& q, const Vec3& v) {
  const Quaternion vq(0, v.x, v.y, v.z);
  const Quaternion qc = q.conjugate();
  const Quaternion rq = q * vq * qc;
  return Vec3(rq.x, rq.y, rq.z);
}

// Inverse Drehung: Navigation -> Körper
inline Vec3 rotateVectorInverse(const Quaternion& q, const Vec3& v) {
  return rotateVector(q.conjugate(), v);
}
