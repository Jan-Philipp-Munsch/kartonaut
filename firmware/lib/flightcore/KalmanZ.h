#pragma once
// KalmanZ.h – 2-Zustands-Kalman für Höhe und Vertikalgeschwindigkeit
//
// Zustand s = [z, vz]ᵀ, Eingang a = Beschleunigung im Navigationssystem ohne g,
// Messung = Barometerhöhe. Modell mit konstanter Beschleunigung über dt:
//   F = [1 dt; 0 1], G = [dt²/2; dt], Q = G Gᵀ σa², H = [1 0], R = σb².
// Mit 2 × 2 von Hand ausgeschrieben, ohne Matrixbibliothek: dieselbe Mathematik
// wie vorher mit BasicLinearAlgebra, läuft aber auch nativ (Tests, SIL).
struct KalmanZ {
  float z_ = 0, vz_ = 0;                 // Zustand
  float p00_ = 0, p01_ = 0, p11_ = 0;    // Kovarianz (symmetrisch)
  float dt_ = 0.01f, q_sigma2_ = 0;      // Modell
  float r_ = 900.0f;                     // Messvarianz, setMeasStd() überschreibt

  // Modell mit gemessenem dt anpassen
  void setDt(float dt, float sigma_acc) { dt_ = dt; q_sigma2_ = sigma_acc * sigma_acc; }

  void setMeasStd(float std_m) { r_ = std_m * std_m; }       // R = std²
  void setState(float z0_m, float vz0_ms) { z_ = z0_m; vz_ = vz0_ms; }
  void setPDiag(float pz_var, float pv_var) { p00_ = pz_var; p01_ = 0; p11_ = pv_var; }

  // jeden Takt predict(), update() nur mit einer frischen Barometermessung
  void predict(float accel_z);
  void update(float z_meas);
  void step(float accel_z, float z_meas, float& z_est, float& vz_est) {
    predict(accel_z); update(z_meas); z_est = z_; vz_est = vz_;
  }

  float z()  const { return z_; }
  float vz() const { return vz_; }
};
