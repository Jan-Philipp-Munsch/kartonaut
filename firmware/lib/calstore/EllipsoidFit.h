#pragma once
// EllipsoidFit.h – Hard- und Soft-Iron des Magnetometers per Ellipsoid-Fit
//
// Algebraischer Kleinste-Quadrate-Fit mit neun Parametern:
//   a x² + b y² + c z² + 2h xy + 2g xz + 2f yz + 2p x + 2q y + 2r z = 1
// Daraus Mittelpunkt (Hard-Iron) und die symmetrische Matrix W (Soft-Iron),
// die das Ellipsoid auf eine Kugel mit dem Radius `field` abbildet:
//   korrigiert = W · (roh - offset)
// Die Proben bleiben im Speicher (bis MAX_SAMPLES), damit Residuum und
// Abdeckung (Oktanten) berechnet werden können. Reines C++ für test/host/.
#include "SmallMath.h"

namespace cal {

struct EllipsoidResult {
  float offset[3];
  float soft_iron[9];
  float field;            // mittlerer Radius
  float residual_pct;     // RMS-Abweichung des Radius in Prozent
  float axis_ratio;       // größte / kleinste Halbachse
  int   n;
  int   octants;          // belegte Oktanten um den Mittelpunkt (8 = gut)
};

class EllipsoidFit {
public:
  static constexpr int MAX_SAMPLES = 1200;

  void reset() { n_ = 0; }
  int  count() const { return n_; }
  bool full() const { return n_ >= MAX_SAMPLES; }

  void add(float x, float y, float z) {
    if (n_ >= MAX_SAMPLES) return;
    s_[n_][0] = x; s_[n_][1] = y; s_[n_][2] = z;
    ++n_;
  }

  bool solve(EllipsoidResult& r) const {
    if (n_ < 50) return false;
    double ATA[81] = {0}, ATb[9] = {0};
    for (int k = 0; k < n_; ++k) {
      const double x = s_[k][0], y = s_[k][1], z = s_[k][2];
      const double row[9] = {x * x, y * y, z * z, 2 * x * y, 2 * x * z, 2 * y * z, 2 * x, 2 * y, 2 * z};
      for (int i = 0; i < 9; ++i) {
        ATb[i] += row[i];
        for (int j = 0; j < 9; ++j) ATA[i * 9 + j] += row[i] * row[j];
      }
    }
    double v[9];
    if (!smallmath::solve(ATA, ATb, 9, v)) return false;
    // A = [[a h g],[h b f],[g f c]], b = (p q r)
    const double A[9] = {v[0], v[3], v[4], v[3], v[1], v[5], v[4], v[5], v[2]};
    const double bv[3] = {v[6], v[7], v[8]};
    double Ai[9];
    if (!smallmath::inv3(A, Ai)) return false;
    double c[3];
    for (int i = 0; i < 3; ++i) c[i] = -(Ai[3 * i] * bv[0] + Ai[3 * i + 1] * bv[1] + Ai[3 * i + 2] * bv[2]);
    // y^T A y = 1 + c^T A c  ->  M = A / (1 + c^T A c)
    double cAc = 0;
    for (int i = 0; i < 3; ++i)
      for (int j = 0; j < 3; ++j) cAc += c[i] * A[3 * i + j] * c[j];
    const double k = 1.0 + cAc;
    if (k <= 0) return false;
    double M[9];
    for (int i = 0; i < 9; ++i) M[i] = A[i] / k;
    // W = M^(1/2) über die Eigenzerlegung; Halbachsen r_i = 1/sqrt(w_i)
    double w[3], V[9];
    smallmath::eigen3(M, w, V);
    double radius[3];
    for (int i = 0; i < 3; ++i) {
      if (w[i] <= 0) return false;        // kein Ellipsoid (Hyperboloid): zu wenig Drehung
      radius[i] = 1.0 / sqrt(w[i]);
    }
    const double field = cbrt(radius[0] * radius[1] * radius[2]);
    double rmax = radius[0], rmin = radius[0];
    for (int i = 1; i < 3; ++i) { if (radius[i] > rmax) rmax = radius[i]; if (radius[i] < rmin) rmin = radius[i]; }
    // W = V diag(sqrt(w) * field) V^T
    double W[9] = {0};
    for (int i = 0; i < 3; ++i)
      for (int j = 0; j < 3; ++j)
        for (int kk = 0; kk < 3; ++kk) W[3 * i + j] += V[3 * i + kk] * sqrt(w[kk]) * field * V[3 * j + kk];

    for (int i = 0; i < 3; ++i) r.offset[i] = float(c[i]);
    for (int i = 0; i < 9; ++i) r.soft_iron[i] = float(W[i]);
    r.field = float(field);
    r.axis_ratio = float(rmax / rmin);
    r.n = n_;

    // Residuum und Abdeckung
    double sq = 0;
    bool oct[8] = {false, false, false, false, false, false, false, false};
    for (int kk = 0; kk < n_; ++kk) {
      double d[3], e[3] = {0, 0, 0};
      for (int i = 0; i < 3; ++i) d[i] = s_[kk][i] - c[i];
      for (int i = 0; i < 3; ++i)
        for (int j = 0; j < 3; ++j) e[i] += W[3 * i + j] * d[j];
      const double rad = sqrt(e[0] * e[0] + e[1] * e[1] + e[2] * e[2]);
      sq += (rad - field) * (rad - field);
      oct[(d[0] > 0 ? 1 : 0) | (d[1] > 0 ? 2 : 0) | (d[2] > 0 ? 4 : 0)] = true;
    }
    r.residual_pct = float(sqrt(sq / n_) / field * 100.0);
    r.octants = 0;
    for (bool o : oct) r.octants += o ? 1 : 0;
    return true;
  }

private:
  float s_[MAX_SAMPLES][3];
  int   n_ = 0;
};

}  // namespace cal
