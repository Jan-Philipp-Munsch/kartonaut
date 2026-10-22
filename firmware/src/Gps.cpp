#include "Gps.h"
#include "Board.h"
#include <stdlib.h>
#include <string.h>

void Gps::begin(long baud) {
  if (!HAS_GPS) return;
  GPS_SERIAL.begin(baud);
}

void Gps::poll() {
  if (!HAS_GPS) return;
  int guard = 128;
  while (GPS_SERIAL.available() && guard-- > 0) {
    const char c = char(GPS_SERIAL.read());
    if (c == '$') { pos_ = 0; line_[0] = 0; }
    if (c == '\n' || c == '\r') {
      if (pos_ > 6) { line_[pos_] = 0; parseLine(); }
      pos_ = 0;
      continue;
    }
    if (pos_ < sizeof line_ - 1) line_[pos_++] = c;
  }
}

// "ddmm.mmmm" bzw. "dddmm.mmmm" -> Grad; Süd/West negativ
float Gps::parseCoord(const char* s, const char* hemi) {
  if (!s || !*s) return 0.0f;
  const double v = atof(s);
  const int deg = int(v / 100.0);
  double d = deg + (v - deg * 100.0) / 60.0;
  if (hemi && (*hemi == 'S' || *hemi == 'W')) d = -d;
  return float(d);
}

void Gps::parseLine() {
  // $GPGGA / $GNGGA: Zeit, Breite, N/S, Länge, E/W, Fix, Sats, HDOP, Höhe, M, ...
  if (strncmp(line_ + 3, "GGA", 3) != 0) return;
  ++sentences_;
  char* f[16] = {nullptr};
  int n = 0;
  char* p = line_;
  while (n < 16 && p) {
    f[n++] = p;
    p = strchr(p, ',');
    if (p) *p++ = 0;
  }
  if (n < 10) return;
  char* star = strchr(f[n - 1], '*');
  if (star) *star = 0;
  fix_ = uint8_t(atoi(f[6]));
  data_.fix = fix_ ? 3 : 0;
  data_.sats = uint8_t(atoi(f[7]));
  const double hdop10 = atof(f[8]) * 10.0;
  data_.hdop_d10 = uint8_t(hdop10 > 255.0 ? 255.0 : hdop10);
  if (fix_) {
    data_.lat_1e7 = int32_t(parseCoord(f[2], f[3]) * 1e7f);
    data_.lon_1e7 = int32_t(parseCoord(f[4], f[5]) * 1e7f);
    data_.alt_m = int16_t(atof(f[9]));
    t_fix_ms_ = millis();
  }
}
