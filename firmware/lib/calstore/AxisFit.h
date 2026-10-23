#pragma once
// AxisFit.h – Achszuordnung des Magnetometers zum Raketenkörper aus einer
// Drehbewegung
//
// Während die Platine um alle Achsen gedreht wird, ist das Erdfeld in der
// Welt fest. Im Körpersystem gilt für seinen Vektor m: dm/dt = -ω × m, mit
// ω der Drehrate im Körpersystem (aus der schon zugeordneten IMU). Für jede
// der 24 rechtshändigen Permutationen mit Vorzeichen wird der Fehler
// Σ |Δm/Δt + ω × m|² gebildet; die kleinste gewinnt. Das Verhältnis zum
// zweitbesten Kandidaten ist das Maß für die Eindeutigkeit.
//
// Die Magnetometerwerte sollen Hard-/Soft-Iron-korrigiert sein (Chip-
// Achsen), die Drehrate in rad/s im Körpersystem. Reines C++ (test/host/).
#include <math.h>

namespace cal {

struct AxisResult {
  int8_t map[3];
  int8_t sign[3];
  float  best_err;
  float  second_err;     // Fehler des zweitbesten Kandidaten
  float  ratio;          // second / best; > 2 heißt eindeutig
  int    n;
};

class AxisFit {
public:
  static constexpr int MAX_SAMPLES = 1500;

  void reset() { n_ = 0; }
  int  count() const { return n_; }
  bool full() const { return n_ >= MAX_SAMPLES; }

  // mag: Chip-Achsen (korrigiert); gyro: Körpersystem, rad/s; dt zum vorigen Satz
  void add(const float mag[3], const float gyro_body_rads[3], float dt_s) {
    if (n_ >= MAX_SAMPLES) return;
    for (int i = 0; i < 3; ++i) { m_[n_][i] = mag[i]; w_[n_][i] = gyro_body_rads[i]; }
    dt_[n_] = dt_s;
    ++n_;
  }

  bool solve(AxisResult& r) const {
    if (n_ < 20) return false;
    static const int8_t perms[6][3] = {{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}};
    float best = INFINITY, second = INFINITY;
    for (int p = 0; p < 6; ++p) {
      for (int s = 0; s < 8; ++s) {
        const int8_t sign[3] = {int8_t(s & 1 ? -1 : 1), int8_t(s & 2 ? -1 : 1), int8_t(s & 4 ? -1 : 1)};
        if (!rightHanded(perms[p], sign)) continue;
        const float err = error(perms[p], sign);
        if (err < best) {
          second = best; best = err;
          for (int i = 0; i < 3; ++i) { r.map[i] = perms[p][i]; r.sign[i] = sign[i]; }
        } else if (err < second) {
          second = err;
        }
      }
    }
    r.best_err = best;
    r.second_err = second;
    r.ratio = best > 0 ? second / best : INFINITY;
    r.n = n_;
    return best < INFINITY;
  }

  // Determinante der Abbildungsmatrix = +1?
  static bool rightHanded(const int8_t map[3], const int8_t sign[3]) {
    float M[9] = {0};
    for (int i = 0; i < 3; ++i) M[3 * i + map[i]] = sign[i];
    const float det = M[0] * (M[4] * M[8] - M[5] * M[7]) - M[1] * (M[3] * M[8] - M[5] * M[6]) + M[2] * (M[3] * M[7] - M[4] * M[6]);
    return det > 0;
  }

private:
  float error(const int8_t map[3], const int8_t sign[3]) const {
    double sum = 0;
    for (int k = 1; k < n_; ++k) {
      const float dt = dt_[k];
      if (dt <= 0) continue;
      float a[3], b[3], w[3];
      for (int i = 0; i < 3; ++i) {
        a[i] = sign[i] * m_[k - 1][map[i]];
        b[i] = sign[i] * m_[k][map[i]];
        w[i] = 0.5f * (w_[k - 1][i] + w_[k][i]);
      }
      const float m[3] = {0.5f * (a[0] + b[0]), 0.5f * (a[1] + b[1]), 0.5f * (a[2] + b[2])};
      const float dm[3] = {(b[0] - a[0]) / dt, (b[1] - a[1]) / dt, (b[2] - a[2]) / dt};
      const float wxm[3] = {w[1] * m[2] - w[2] * m[1], w[2] * m[0] - w[0] * m[2], w[0] * m[1] - w[1] * m[0]};
      for (int i = 0; i < 3; ++i) { const float e = dm[i] + wxm[i]; sum += e * e; }
    }
    return float(sum / (n_ - 1));
  }

  float m_[MAX_SAMPLES][3];
  float w_[MAX_SAMPLES][3];
  float dt_[MAX_SAMPLES];
  int   n_ = 0;
};

}  // namespace cal
