#pragma once
// Nmea.h – minimaler NMEA-0183-Parser für GGA und RMC (Fix, Satelliten,
// Position). Reines C++ ohne Arduino, zeilenweise; test/host/ prüft ihn.
#include <stdlib.h>
#include <string.h>

struct NmeaState {
  int  sentences = 0;        // gültige Sätze mit richtiger Prüfsumme
  int  bad_checksum = 0;
  int  fix_quality = 0;      // GGA Feld 6: 0 = kein Fix, 1 = GPS, 2 = DGPS
  int  satellites = 0;       // GGA Feld 7
  bool rmc_valid = false;    // RMC Feld 2 == 'A'
  double lat = 0, lon = 0;   // Grad, Vorzeichen nach N/S, E/W
  float hdop = 0;
  float alt_m = 0;
  char  time_utc[11] = {0};  // hhmmss.ss
};

namespace nmea {

inline bool checksumOk(const char* line) {
  if (line[0] != '$') return false;
  const char* star = strchr(line, '*');
  if (!star || strlen(star) < 3) return false;
  unsigned char cs = 0;
  for (const char* p = line + 1; p < star; ++p) cs ^= (unsigned char)*p;
  return (unsigned)strtoul(star + 1, nullptr, 16) == cs;
}

// Feld i (0 = Satzkennung) in out kopieren; false, wenn es fehlt
inline bool field(const char* line, int i, char* out, size_t n) {
  const char* p = line;
  for (int k = 0; k < i; ++k) {
    p = strchr(p, ',');
    if (!p) return false;
    ++p;
  }
  size_t len = 0;
  while (p[len] && p[len] != ',' && p[len] != '*') ++len;
  if (len + 1 > n) len = n - 1;
  memcpy(out, p, len);
  out[len] = 0;
  return true;
}

inline double toDegrees(const char* ddmm, const char* hemi) {
  if (!ddmm[0]) return 0;
  const double v = atof(ddmm);
  const int deg = int(v / 100);
  double d = deg + (v - deg * 100) / 60.0;
  if (hemi[0] == 'S' || hemi[0] == 'W') d = -d;
  return d;
}

// Eine Zeile ("$GxGGA,...*hh") einarbeiten; true, wenn sie ausgewertet wurde
inline bool parse(NmeaState& s, const char* line) {
  if (!checksumOk(line)) { if (line[0] == '$') ++s.bad_checksum; return false; }
  ++s.sentences;
  char f[24], g[24];
  if (strncmp(line + 3, "GGA", 3) == 0) {
    if (field(line, 1, f, sizeof f)) { memcpy(s.time_utc, f, sizeof s.time_utc - 1); s.time_utc[sizeof s.time_utc - 1] = 0; }
    if (field(line, 6, f, sizeof f)) s.fix_quality = atoi(f);
    if (field(line, 7, f, sizeof f)) s.satellites = atoi(f);
    if (field(line, 8, f, sizeof f)) s.hdop = float(atof(f));
    if (field(line, 9, f, sizeof f)) s.alt_m = float(atof(f));
    if (field(line, 2, f, sizeof f) && field(line, 3, g, sizeof g)) s.lat = toDegrees(f, g);
    if (field(line, 4, f, sizeof f) && field(line, 5, g, sizeof g)) s.lon = toDegrees(f, g);
    return true;
  }
  if (strncmp(line + 3, "RMC", 3) == 0) {
    if (field(line, 2, f, sizeof f)) s.rmc_valid = f[0] == 'A';
    return true;
  }
  return true;
}

}  // namespace nmea
