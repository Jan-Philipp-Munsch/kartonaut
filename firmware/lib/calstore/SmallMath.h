#pragma once
// SmallMath.h – kleine lineare Algebra ohne Bibliothek (double, feste Größen)
#include <math.h>
#include <stddef.h>

namespace smallmath {

// Löst A x = b (n ≤ 10) mit Gauß-Elimination und Spaltenpivot; A, b werden überschrieben.
inline bool solve(double* A, double* b, int n, double* x) {
  for (int col = 0; col < n; ++col) {
    int piv = col;
    for (int r = col + 1; r < n; ++r)
      if (fabs(A[r * n + col]) > fabs(A[piv * n + col])) piv = r;
    if (fabs(A[piv * n + col]) < 1e-12) return false;
    if (piv != col) {
      for (int c = 0; c < n; ++c) { const double t = A[col * n + c]; A[col * n + c] = A[piv * n + c]; A[piv * n + c] = t; }
      const double t = b[col]; b[col] = b[piv]; b[piv] = t;
    }
    for (int r = col + 1; r < n; ++r) {
      const double f = A[r * n + col] / A[col * n + col];
      if (f == 0.0) continue;
      for (int c = col; c < n; ++c) A[r * n + c] -= f * A[col * n + c];
      b[r] -= f * b[col];
    }
  }
  for (int r = n - 1; r >= 0; --r) {
    double s = b[r];
    for (int c = r + 1; c < n; ++c) s -= A[r * n + c] * x[c];
    x[r] = s / A[r * n + r];
  }
  return true;
}

// Eigenwerte und -vektoren einer symmetrischen 3x3-Matrix (Jacobi-Rotationen).
// V spaltenweise: Spalte k gehört zu w[k].
inline void eigen3(const double A[9], double w[3], double V[9]) {
  double a[9];
  for (int i = 0; i < 9; ++i) { a[i] = A[i]; V[i] = (i % 4 == 0) ? 1.0 : 0.0; }
  for (int sweep = 0; sweep < 50; ++sweep) {
    double off = fabs(a[1]) + fabs(a[2]) + fabs(a[5]);
    if (off < 1e-15) break;
    for (int p = 0; p < 3; ++p) {
      for (int q = p + 1; q < 3; ++q) {
        const double apq = a[p * 3 + q];
        if (fabs(apq) < 1e-18) continue;
        const double theta = (a[q * 3 + q] - a[p * 3 + p]) / (2.0 * apq);
        const double t = (theta >= 0 ? 1.0 : -1.0) / (fabs(theta) + sqrt(theta * theta + 1.0));
        const double c = 1.0 / sqrt(t * t + 1.0), s = t * c;
        for (int k = 0; k < 3; ++k) {   // Zeilen/Spalten p und q drehen
          const double akp = a[k * 3 + p], akq = a[k * 3 + q];
          a[k * 3 + p] = c * akp - s * akq;
          a[k * 3 + q] = s * akp + c * akq;
        }
        for (int k = 0; k < 3; ++k) {
          const double apk = a[p * 3 + k], aqk = a[q * 3 + k];
          a[p * 3 + k] = c * apk - s * aqk;
          a[q * 3 + k] = s * apk + c * aqk;
        }
        for (int k = 0; k < 3; ++k) {
          const double vkp = V[k * 3 + p], vkq = V[k * 3 + q];
          V[k * 3 + p] = c * vkp - s * vkq;
          V[k * 3 + q] = s * vkp + c * vkq;
        }
      }
    }
  }
  for (int i = 0; i < 3; ++i) w[i] = a[4 * i];
}

// Inverse einer 3x3-Matrix; false, wenn singulär
inline bool inv3(const double m[9], double out[9]) {
  const double det = m[0] * (m[4] * m[8] - m[5] * m[7]) - m[1] * (m[3] * m[8] - m[5] * m[6]) + m[2] * (m[3] * m[7] - m[4] * m[6]);
  if (fabs(det) < 1e-18) return false;
  const double id = 1.0 / det;
  out[0] =  (m[4] * m[8] - m[5] * m[7]) * id;
  out[1] = -(m[1] * m[8] - m[2] * m[7]) * id;
  out[2] =  (m[1] * m[5] - m[2] * m[4]) * id;
  out[3] = -(m[3] * m[8] - m[5] * m[6]) * id;
  out[4] =  (m[0] * m[8] - m[2] * m[6]) * id;
  out[5] = -(m[0] * m[5] - m[2] * m[3]) * id;
  out[6] =  (m[3] * m[7] - m[4] * m[6]) * id;
  out[7] = -(m[0] * m[7] - m[1] * m[6]) * id;
  out[8] =  (m[0] * m[4] - m[1] * m[3]) * id;
  return true;
}

}  // namespace smallmath
