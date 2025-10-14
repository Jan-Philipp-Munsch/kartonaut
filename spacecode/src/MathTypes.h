#pragma once
#include <Arduino.h>
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
inline float norm(const Vec3& v){ return sqrtf(dot(v,v)); }

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

  void normalize() {
    const float m = sqrtf(w*w + x*x + y*y + z*z);
    if (m > 0.f) { w/=m; x/=m; y/=m; z/=m; }
    else { w=1; x=y=z=0; }
  }
};

inline Vec3 rotateVector(const Quaternion& q, const Vec3& v) {
  const Quaternion vq(0, v.x, v.y, v.z);
  const Quaternion qc = q.conjugate();
  const Quaternion rq = q * vq * qc;
  return Vec3(rq.x, rq.y, rq.z);
}
