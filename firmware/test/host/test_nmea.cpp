// test_nmea.cpp – NMEA-Parser der Testkonsole auf dem PC
//
//   g++ -std=c++17 -Wall -I examples/revb_test test/host/test_nmea.cpp -o /tmp/test_nmea && /tmp/test_nmea
#include "Nmea.h"
#include <cstdio>
#include <cmath>
#include <string>

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FEHL %s:%d: %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

int main() {
  NmeaState s;
  // Beispielsatz (u-blox, Prüfsumme stimmt)
  CHECK(nmea::parse(s, "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"));
  CHECK(s.sentences == 1);
  CHECK(s.fix_quality == 1);
  CHECK(s.satellites == 8);
  CHECK(std::fabs(s.lat - 48.1173) < 1e-3);
  CHECK(std::fabs(s.lon - 11.5167) < 1e-3);
  CHECK(std::fabs(s.alt_m - 545.4f) < 0.01f);
  CHECK(std::fabs(s.hdop - 0.9f) < 0.01f);
  CHECK(std::string(s.time_utc) == "123519");
  // falsche Prüfsumme wird gezählt und ignoriert
  CHECK(!nmea::parse(s, "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*48"));
  CHECK(s.bad_checksum == 1 && s.sentences == 1);
  // RMC gültig
  CHECK(nmea::parse(s, "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"));
  CHECK(s.rmc_valid);
  // GNGGA ohne Fix: leere Felder
  NmeaState t;
  CHECK(nmea::parse(t, "$GNGGA,,,,,,0,00,99.99,,,,,,*56"));
  CHECK(t.fix_quality == 0 && t.satellites == 0);
  CHECK(!nmea::parse(t, "kein NMEA"));
  if (failures) { std::printf("%d Fehler\n", failures); return 1; }
  std::printf("NMEA ok\n");
  return 0;
}
