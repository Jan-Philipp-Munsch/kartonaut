#pragma once
// Filters.h – kleine digitale Filter für den Flug-Loop (ohne Arduino, läuft in den nativen Tests)
//
// Biquad nach R. Bristow-Johnson ("Audio EQ Cookbook"), Direktform I in float. Gebraucht als
// Kerbfilter (Notch) auf der Drehrate, wenn das Flug-Log eine schmale Vibrationslinie zeigt
// (Motor, Servo-Brummen, Rumpfmode). Ein Notch kostet außerhalb seiner Kerbe kaum Phase, anders
// als ein Tiefpass gleicher Dämpfung; der Regler bleibt also schnell. Ohne Linie im Log bleibt
// GYRO_NOTCH_HZ = 0 und das Filter aus.
#include <math.h>

class Biquad {
public:
  // Notch bei f0 (Hz), Güte q (Breite ≈ f0/q), Abtastrate fs (Hz). f0 <= 0 oder f0 >= fs/2: Durchgang.
  void setNotch(float f0, float q, float fs) {
    if (f0 <= 0.f || f0 >= 0.5f * fs || q <= 0.f) { setPass(); return; }
    const float w = 2.f * 3.14159265f * f0 / fs, c = cosf(w), alpha = sinf(w) / (2.f * q);
    set(1.f, -2.f * c, 1.f, 1.f + alpha, -2.f * c, 1.f - alpha);
  }
  // Tiefpass 2. Ordnung (Butterworth bei q = 0,7071)
  void setLowpass(float fc, float q, float fs) {
    if (fc <= 0.f || fc >= 0.5f * fs || q <= 0.f) { setPass(); return; }
    const float w = 2.f * 3.14159265f * fc / fs, c = cosf(w), alpha = sinf(w) / (2.f * q);
    set((1.f - c) / 2.f, 1.f - c, (1.f - c) / 2.f, 1.f + alpha, -2.f * c, 1.f - alpha);
  }
  void setPass() { set(1.f, 0.f, 0.f, 1.f, 0.f, 0.f); }

  float update(float x) {
    const float y = b0_ * x + b1_ * x1_ + b2_ * x2_ - a1_ * y1_ - a2_ * y2_;
    x2_ = x1_; x1_ = x; y2_ = y1_; y1_ = y;
    return y;
  }
  // Zustand auf einen Gleichwert setzen (kein Einschwingen beim Start)
  void reset(float v = 0.f) { x1_ = x2_ = y1_ = y2_ = v; }

private:
  void set(float b0, float b1, float b2, float a0, float a1, float a2) {
    b0_ = b0 / a0; b1_ = b1 / a0; b2_ = b2 / a0; a1_ = a1 / a0; a2_ = a2 / a0;
  }
  float b0_ = 1, b1_ = 0, b2_ = 0, a1_ = 0, a2_ = 0;
  float x1_ = 0, x2_ = 0, y1_ = 0, y2_ = 0;
};

// Tiefpass 1. Ordnung mit Zeitkonstante statt Faktor je Takt: bleibt bei einer anderen Loop-Rate gleich
inline float lowpassStep(float y, float x, float tau_s, float dt_s) {
  if (tau_s <= 0.f) return x;
  return y + (x - y) * (dt_s / (tau_s + dt_s));
}
