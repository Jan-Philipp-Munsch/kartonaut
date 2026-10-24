// test_calstore.cpp – Tests der Kalibrierbibliothek auf dem PC (ohne Hardware)
//
//   g++ -std=c++17 -Wall -I lib/calstore test/host/test_calstore.cpp -o /tmp/test_calstore && /tmp/test_calstore
//
// Geprüft: CRC und Versionsprüfung von CalData, Ellipsoid-Fit mit bekanntem
// Hard-/Soft-Iron, Achszuordnung aus einer synthetischen Drehung.
#include "CalData.h"
#include "EllipsoidFit.h"
#include "AxisFit.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FEHL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)
#define NEAR(a, b, tol) CHECK(std::fabs((a) - (b)) <= (tol))

static double rnd() { return std::rand() / double(RAND_MAX); }

static void testCrc() {
  CHECK(cal::crc32("123456789", 9) == 0xCBF43926u);   // Referenzwert CRC-32/IEEE
  cal::CalData d = cal::defaults();
  CHECK(cal::check(d) == cal::Check::OK);
  CHECK(d.size == sizeof(cal::CalData));
  d.gyro_bias_dps[0] = 1.5f;                            // Änderung ohne seal(): CRC falsch
  CHECK(cal::check(d) == cal::Check::BAD_CRC);
  cal::seal(d);
  CHECK(cal::check(d) == cal::Check::OK);
  d.version = 99; cal::seal(d); d.version = 99;
  CHECK(cal::check(d) == cal::Check::BAD_VERSION);
  cal::CalData e; memset(&e, 0xFF, sizeof e);
  CHECK(cal::check(e) == cal::Check::EMPTY);
  // Standardwerte neutral
  cal::CalData s = cal::defaults();
  float in[3] = {1, 2, 3}, out[3];
  cal::applyMag(s, in, out);
  NEAR(out[0], 1, 1e-6); NEAR(out[1], 2, 1e-6); NEAR(out[2], 3, 1e-6);
  cal::mapAxes(s.imu_axis_map, s.imu_axis_sign, in, out);
  NEAR(out[2], 3, 1e-6);
  std::printf("CRC/Struktur: %zu Byte\n", sizeof(cal::CalData));
}

static void testEllipsoid() {
  // wahres Feld 0,48 gauss, Hard-Iron (0,20 -0,10 0,05), Soft-Iron: Skalierung und leichte Scherung
  const double field = 0.48, off[3] = {0.20, -0.10, 0.05};
  const double S[9] = {1.15, 0.05, 0.00, 0.05, 0.95, 0.02, 0.00, 0.02, 1.05};   // symmetrisch, verzerrt Kugel -> Ellipsoid
  cal::EllipsoidFit fit;
  std::srand(7);
  for (int k = 0; k < 800; ++k) {
    const double u = 2 * rnd() - 1, phi = 2 * M_PI * rnd(), rr = std::sqrt(1 - u * u);
    const double t[3] = {field * rr * std::cos(phi), field * rr * std::sin(phi), field * u};
    double m[3];
    for (int i = 0; i < 3; ++i) m[i] = off[i] + S[3 * i] * t[0] + S[3 * i + 1] * t[1] + S[3 * i + 2] * t[2] + (rnd() - 0.5) * 0.004;
    fit.add(float(m[0]), float(m[1]), float(m[2]));
  }
  cal::EllipsoidResult r;
  CHECK(fit.solve(r));
  for (int i = 0; i < 3; ++i) NEAR(r.offset[i], off[i], 0.003);
  // Der Betrag nach der Korrektur ist der geometrische Mittelradius: field · det(S)^(1/3).
  // Das wahre Feld ist aus dem Magnetometer allein nicht bestimmbar.
  const double detS = S[0] * (S[4] * S[8] - S[5] * S[7]) - S[1] * (S[3] * S[8] - S[5] * S[6]) + S[2] * (S[3] * S[7] - S[4] * S[6]);
  const double field_fit = field * std::cbrt(detS);
  NEAR(r.field, field_fit, 0.01);
  CHECK(r.residual_pct < 1.0f);
  CHECK(r.octants == 8);
  // Korrektur bildet die Proben auf die Kugel ab
  const double t[3] = {field, 0, 0};
  double m[3], c[3] = {0, 0, 0};
  for (int i = 0; i < 3; ++i) m[i] = off[i] + S[3 * i] * t[0] + S[3 * i + 1] * t[1] + S[3 * i + 2] * t[2];
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) c[i] += r.soft_iron[3 * i + j] * (m[j] - r.offset[j]);
  NEAR(std::sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]), field_fit, 0.01);
  std::printf("Ellipsoid: offset %.3f %.3f %.3f, Feld %.3f, Residuum %.2f %%, Achsen %.3f\n",
              r.offset[0], r.offset[1], r.offset[2], r.field, r.residual_pct, r.axis_ratio);
  // zu wenig Proben
  cal::EllipsoidFit few;
  for (int k = 0; k < 10; ++k) few.add(k, k, k);
  CHECK(!few.solve(r));
}

// Drehung einer Welt-festen Richtung ins Körpersystem bei gegebener Drehrate (Integration)
static void testAxes() {
  // wahre Zuordnung: body x = -chip y, body y = chip x, body z = chip z  (Drehung um z um 90°)
  const int8_t map[3] = {1, 0, 2}, sign[3] = {-1, 1, 1};
  CHECK(cal::AxisFit::rightHanded(map, sign));
  cal::AxisFit fit;
  // Körperfeld-Vektor m_b wird mit dm/dt = -w x m integriert; der Chip sieht m_c = P^-1 m_b
  double mb[3] = {0.2, 0.1, 0.4};
  const double dt = 0.0125;   // 80 Hz
  std::srand(3);
  for (int k = 0; k < 1200; ++k) {
    const double tt = k * dt;
    const double w[3] = {1.5 * std::sin(0.7 * tt), 1.2 * std::cos(0.5 * tt), 0.9 * std::sin(0.3 * tt + 1)};
    // Chip-Werte aus Körper: body[i] = sign[i] * chip[map[i]]  ->  chip[map[i]] = sign[i] * body[i]
    float mc[3], wb[3];
    for (int i = 0; i < 3; ++i) { mc[map[i]] = float(sign[i] * mb[i] + (rnd() - 0.5) * 0.002); wb[i] = float(w[i]); }
    fit.add(mc, wb, float(dt));
    // Integration (RK2) von dm/dt = -w x m
    auto f = [&](const double m[3], double out[3]) {
      out[0] = -(w[1] * m[2] - w[2] * m[1]); out[1] = -(w[2] * m[0] - w[0] * m[2]); out[2] = -(w[0] * m[1] - w[1] * m[0]);
    };
    double k1[3], mid[3], k2[3];
    f(mb, k1);
    for (int i = 0; i < 3; ++i) mid[i] = mb[i] + 0.5 * dt * k1[i];
    f(mid, k2);
    for (int i = 0; i < 3; ++i) mb[i] += dt * k2[i];
  }
  cal::AxisResult r;
  CHECK(fit.solve(r));
  for (int i = 0; i < 3; ++i) { CHECK(r.map[i] == map[i]); CHECK(r.sign[i] == sign[i]); }
  CHECK(r.ratio > 2.0f);
  std::printf("Achsen: map %d %d %d, sign %d %d %d, Fehler %.4g, Verhältnis %.1f\n",
              r.map[0], r.map[1], r.map[2], r.sign[0], r.sign[1], r.sign[2], r.best_err, r.ratio);
  // linkshändige Zuordnung wird nicht angeboten
  const int8_t bad[3] = {-1, 1, 1}, id[3] = {0, 1, 2};
  CHECK(!cal::AxisFit::rightHanded(id, bad));
}

int main() {
  testCrc();
  testEllipsoid();
  testAxes();
  if (failures) { std::printf("%d Fehler\n", failures); return 1; }
  std::printf("alle Tests ok\n");
  return 0;
}
