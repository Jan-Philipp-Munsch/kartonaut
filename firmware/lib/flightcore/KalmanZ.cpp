#include "KalmanZ.h"

void KalmanZ::predict(float a) {
  const float dt = dt_, h = 0.5f * dt * dt;
  // s = F s + G a
  z_  += vz_ * dt + h * a;
  vz_ += dt * a;
  // P = F P Fᵀ + G Gᵀ σ²
  const float p00 = p00_ + 2.0f * dt * p01_ + dt * dt * p11_;
  const float p01 = p01_ + dt * p11_;
  p00_ = p00 + h * h * q_sigma2_;
  p01_ = p01 + h * dt * q_sigma2_;
  p11_ = p11_ + dt * dt * q_sigma2_;
}

void KalmanZ::update(float zm) {
  // K = P Hᵀ / (H P Hᵀ + R), H = [1 0]
  const float s = p00_ + r_;
  if (s <= 0.0f) return;
  const float k0 = p00_ / s, k1 = p01_ / s;
  const float y = zm - z_;
  z_  += k0 * y;
  vz_ += k1 * y;
  // P = (I − K H) P
  const float p00 = (1.0f - k0) * p00_;
  const float p01 = (1.0f - k0) * p01_;
  const float p11 = p11_ - k1 * p01_;
  p00_ = p00; p01_ = p01; p11_ = p11;
}
