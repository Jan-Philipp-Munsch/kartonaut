#include "SDLogger.h"
#include <SdFat.h>
#include <ctype.h>

// ===========================
// SD-Setup (Teensy 4.1 SDIO)
// ===========================
static SdFs   sd;
static FsFile file;
static const SdioConfig sdConfig = SdioConfig(FIFO_SDIO);

// ===========================
// Logger-Parameter
// ===========================
static const uint32_t LOOP_HZ_LOG   = 250;                 // nur fürs Housekeeping (Sync), Logging selbst: on-demand
static const uint32_t LOOP_US_LOG   = 1000000UL / LOOP_HZ_LOG;
static const size_t   NUM_I16       = 40;

// Datensatz: 4 + 2 + 2 + 40*2 = 88 B
struct __attribute__((packed,aligned(4))) Record {
  uint32_t ts_us;          // absolute micros() beim Schreiben
  uint16_t write_us_prev;  // Dauer des vorigen phys. Writes (µs)
  uint16_t _pad;
  int16_t  v[NUM_I16];     // 40 Werte (dein Mapping unten)
};
static const size_t REC_BYTES   = sizeof(Record);          // 88 B

// Schreibhappen (512 B ~= Sektorgröße)
static const size_t PAGE        = 512;

// Voralloziierte Loggröße
static const uint32_t LOG_BYTES = 8UL * 1024UL * 1024UL;   // 8 MB (anpassbar)

// Aktuelle Dateinamen der laufenden Session
static char currentTmpName[16]  = "";   // z.B. LOG00023.TMP
static char currentBinName[16]  = "";   // z.B. LOG00023.BIN

// ===========================
// Laufzeit-States
// ===========================
static uint8_t  pageBuf[PAGE];
static size_t   fill           = 0;        // Pufferfüllung
static bool     logging        = false;
static uint16_t last_write_us  = 0;        // im nächsten Datensatz gespeichert

// opportunistisches Syncing
static uint32_t lastSyncUs = 0;
static uint32_t startUs    = 0;
static const uint32_t SYNC_INTERVAL_US_LATE  = 2000000UL; // 2 s
static const uint32_t SYNC_INTERVAL_US_EARLY = 500000UL;  // 0.5 s in den ersten 10 s

// ===========================
// intern
// ===========================
static bool ensureSdBegun() {
  static bool begun = false;
  if (begun) return true;
  if (sd.begin(sdConfig)) { begun = true; return true; }
  return false;
}

static bool isLogPattern(const char* name, bool* isBinOut, int* numOut) {
  size_t L = strlen(name);
  if (L != 12) return false;               // "LOG" + 5 Ziffern + "." + 3
  if (!(name[0]=='L' && name[1]=='O' && name[2]=='G')) return false;
  if (!(isdigit(name[3]) && isdigit(name[4]) && isdigit(name[5]) && isdigit(name[6]) && isdigit(name[7]))) return false;
  if (name[8] != '.') return false;
  bool isBin = (strcasecmp(name+9, "BIN") == 0);
  bool isTmp = (strcasecmp(name+9, "TMP") == 0);
  if (!isBin && !isTmp) return false;
  if (isBinOut) *isBinOut = isBin;
  if (numOut) {
    *numOut = (name[3]-'0')*10000 + (name[4]-'0')*1000 + (name[5]-'0')*100 + (name[6]-'0')*10 + (name[7]-'0');
  }
  return true;
}

static bool nextFreeNumber(int* outNum) {
  if (!ensureSdBegun()) return false;
  for (int n = 1; n <= 99999; ++n) {
    char tmp[16], bin[16];
    snprintf(tmp, sizeof(tmp), "LOG%05d.TMP", n);
    snprintf(bin, sizeof(bin), "LOG%05d.BIN", n);
    if (!sd.exists(tmp) && !sd.exists(bin)) {
      *outNum = n;
      return true;
    }
  }
  return false;
}

static void flushPage() {
  if (fill == 0) return;
  int wrote = file.write(pageBuf, fill);
  if (wrote != (int)fill) {
    // nothing: in einem Flug wollen wir nicht spammen
  }
  fill = 0;
}

static void writeRec(const Record& r) {
  const uint8_t* p = (const uint8_t*)&r;
  size_t n = REC_BYTES;
  while (n) {
    size_t space = PAGE - fill;
    size_t chunk = n < space ? n : space;
    memcpy(pageBuf + fill, p + (REC_BYTES - n), chunk);
    fill += chunk;
    n    -= chunk;
    if (fill == PAGE) flushPage();   // typ. << 1 ms
  }
}

static uint64_t usedLengthForFile(FsFile& rf, bool isTMP) {
  uint64_t size = rf.fileSize();
  if (!isTMP) return (size / REC_BYTES) * REC_BYTES;

  // .TMP: realen Schluss finden (einfacher Plausibilitäts-Check)
  uint64_t pos = 0;
  Record r;
  uint32_t prev_ts = 0;
  while (pos + REC_BYTES <= size) {
    int n = rf.read(&r, REC_BYTES);
    if (n != (int)REC_BYTES) break;
    if (r.ts_us == 0 || (prev_ts && r.ts_us <= prev_ts)) { size = pos; break; }
    prev_ts = r.ts_us;
    pos += REC_BYTES;
  }
  return (size / REC_BYTES) * REC_BYTES;
}

static void autoRecoverTMPtoBIN() {
  if (!ensureSdBegun()) return;
  FsFile dir;
  if (!dir.open("/")) return;

  FsFile e;
  char name[16];
  while (e.openNext(&dir, O_RDWR)) {
    int len = e.getName(name, sizeof(name));
    if (len > 0) {
      bool isBin; int num;
      if (isLogPattern(name, &isBin, &num) && !isBin) {
        uint64_t used = usedLengthForFile(e, true);
        e.truncate(used);
        e.sync();
        e.close();

        char tmpName[16], binName[16];
        snprintf(tmpName, sizeof(tmpName), "LOG%05d.TMP", num);
        snprintf(binName, sizeof(binName), "LOG%05d.BIN", num);
        if (sd.exists(binName)) {
          int newNum;
          if (!nextFreeNumber(&newNum)) continue;
          snprintf(binName, sizeof(binName), "LOG%05d.BIN", newNum);
        }
        sd.rename(tmpName, binName);
      } else {
        e.close();
      }
    } else {
      e.close();
    }
  }
  dir.close();
}

// ===========================
// öffentliches API
// ===========================
void SDLogger_setup() {
  ensureSdBegun();
  autoRecoverTMPtoBIN();
}

bool SDLogger_start() {
  if (!ensureSdBegun()) return false;
  if (logging) return true;

  int num;
  if (!nextFreeNumber(&num)) return false;

  snprintf(currentTmpName, sizeof(currentTmpName), "LOG%05d.TMP", num);
  snprintf(currentBinName, sizeof(currentBinName), "LOG%05d.BIN", num);

  if (!file.open(currentTmpName, O_RDWR | O_CREAT | O_TRUNC)) return false;
  if (!file.preAllocate(LOG_BYTES)) {
    file.close(); return false;
  }
  file.sync();
  file.rewind();

  fill          = 0;
  logging       = true;
  last_write_us = 0;
  startUs       = micros();
  lastSyncUs    = startUs;

  return true;
}

void SDLogger_stop() {
  if (!logging) return;
  logging = false;

  flushPage();
  if (file.isOpen()) {
    file.truncate(file.curPosition());
    file.sync();
    file.close();

    if (currentTmpName[0]) {
      // Kollision vermeiden
      if (sd.exists(currentBinName)) {
        int num; if (nextFreeNumber(&num)) snprintf(currentBinName, sizeof(currentBinName), "LOG%05d.BIN", num);
      }
      sd.rename(currentTmpName, currentBinName);
    }
  }
}

bool SDLogger_isRecording() { return logging; }

// ===========================
// Quantisierung & Mapping
// ===========================

// Hilfsfunktionen zum Packen
static inline int16_t q_s(float x, float s){ // skaliert & clamp
  long v = lroundf(x * s);
  if (v >  32767) v =  32767;
  if (v < -32768) v = -32768;
  return (int16_t)v;
}
static inline int16_t q_u(float x, float s){ // für positive Größen (z.B. PWM 0..4095)
  long v = lroundf(x * s);
  if (v < 0) v = 0;
  if (v >  32767) v = 32767;
  return (int16_t)v;
}

// Mapping der 40 Kanäle (kommentiert). Skalen so gewählt, dass typische Werte gut auflösen.
static void mapFrameToI16(const SDFrame& f, int16_t out[40]){
  // 0..5: Höhen/Vertikal/Accel
  out[0] = q_s(f.kalman_alt_m,   100.0f);   // cm
  out[1] = q_s(f.kalman_vz_ms,   100.0f);   // cm/s
  out[2] = q_s(f.baro_alt_m,     100.0f);   // cm
  out[3] = q_s(f.a_nav_x_ms2,    100.0f);   // mgal
  out[4] = q_s(f.a_nav_y_ms2,    100.0f);
  out[5] = q_s(f.a_nav_z_ms2,    100.0f);

  // 6..8: Gyro
  out[6] = q_s(f.omega_x_dps,    100.0f);   // 0.01 °/s
  out[7] = q_s(f.omega_y_dps,    100.0f);
  out[8] = q_s(f.omega_z_dps,    100.0f);

  // 9..14: Roll/Pitch/Yaw/Aktoren
  out[9]  = q_s(f.roll_angle_deg,  100.0f); // 0.01 °
  out[10] = q_s(f.roll_rate_dps,   100.0f); // 0.01 °/s
  out[11] = q_u((float)f.yaw_deg,    100.0f); // 0..18000
  out[12] = q_u((float)f.pitch_deg,  100.0f);
  out[13] = q_u((float)f.roll_pwm,      1.0f); // 0..4095 → clamp auf 32767 ok
  out[14] = q_s((float)f.roll_dir,   1000.0f); // -1000/0/+1000

  // 15..19: Energie
  out[15] = q_s(f.bus_V,        1000.0f);  // mV
  out[16] = q_s(f.load_V,       1000.0f);  // mV
  out[17] = q_s(f.current_mA,      1.0f);  // mA
  out[18] = q_s(f.power_mW,        1.0f);  // mW
  out[19] = q_s((float)f.ina_overflow, 1.0f); // 0/1

  // 20..24: Reserven
  out[20] = q_s(f.rsv1, 100.0f);
  out[21] = q_s(f.rsv2, 100.0f);
  out[22] = q_s(f.rsv3, 100.0f);
  out[23] = q_s(f.rsv4, 100.0f);
  out[24] = q_s(f.rsv5, 100.0f);

  // 25..32: User-int16 roh
  for (int i=0;i<8;i++) out[25+i] = f.raw_i16[i];

  // 33..39: frei (aktuell 0)
  for (int i=33;i<40;i++) out[i] = 0;
}

bool SDLogger_logFrame(const SDFrame& f){
  if (!logging || !file.isOpen()) return false;

  Record r;
  r.ts_us = micros();
  r.write_us_prev = last_write_us;
  r._pad = 0;

  mapFrameToI16(f, r.v);

  uint32_t w0 = micros();
  writeRec(r);
  uint32_t w1 = micros();
  uint32_t wdt = w1 - w0;
  last_write_us = (wdt > 0xFFFF) ? 0xFFFF : (uint16_t)wdt;

  // opportunistisches Syncing (wie im Original)
  uint32_t sinceStart = r.ts_us - startUs;
  uint32_t interval   = (sinceStart < 10000000UL) ? SYNC_INTERVAL_US_EARLY : SYNC_INTERVAL_US_LATE;
  uint32_t now        = micros();
  // „Luft“ lassen (wir hängen uns nicht an ein 250Hz-Tick, sondern schauen nur auf die Zeit)
  if ((now - lastSyncUs) >= interval) {
    file.sync();
    lastSyncUs = now;
  }
  return true;
}

// --- kleine Decoder passend zum Mapping ---
static inline float d_s(int16_t v, float s){ return float(v) / s; }   // signed
static inline float d_u(int16_t v, float s){ return float(v) / s; }   // unsigned gespeichert, aber int16

// suche neueste LOGxxxxx.BIN
static bool findLatestBIN(char* out, size_t outSz){
  if (!ensureSdBegun()) return false;
  FsFile dir;
  if (!dir.open("/")) return false;
  FsFile e;
  char name[32];
  int bestNum = -1;
  while (e.openNext(&dir, O_RDONLY)) {
    int len = e.getName(name, sizeof(name));
    e.close();
    if (len > 0) {
      bool isBin; int num;
      if (isLogPattern(name, &isBin, &num) && isBin) {
        if (num > bestNum) { bestNum = num; strncpy(out, name, outSz); out[outSz-1]=0; }
      }
    }
  }
  dir.close();
  return bestNum >= 0;
}

// --- Helfer bleibt gleich ---
// static inline float d_s(...), d_u(...)
// static bool findLatestBIN(...)

SDExportResult SDLogger_exportBINtoCSVx(const char* name, bool scaled){
  SDExportResult res;
  if (!ensureSdBegun() || !name || !sd.exists(name)) {
    Serial.println("[E] export: source not found");
    return res;
  }

  FsFile rf;
  if (!rf.open(name, O_RDONLY)) {
    Serial.printf("[E] open src failed: %s\n", name);
    return res;
  }

  bool isTMP=false; int dummy=0;
  isLogPattern(name, &isTMP, &dummy);
  uint64_t used = usedLengthForFile(rf, isTMP);
  rf.rewind();

  // LOGxxxxx.BIN → LOGxxxxx.CSV
  char csvName[16];
  strncpy(csvName, name, sizeof(csvName));
  csvName[sizeof(csvName)-1] = 0;
  size_t L = strlen(csvName);
  if (L >= 4) { csvName[L-3]='C'; csvName[L-2]='S'; csvName[L-1]='V'; }

  FsFile wf;
  if (!wf.open(csvName, O_RDWR | O_CREAT | O_TRUNC)) {
    rf.close();
    Serial.printf("[E] open dst failed: %s\n", csvName);
    return res;
  }

  // Header
  const char* hdr =
    "t_s,write_us_prev,"
    "kalman_alt_m,kalman_vz_ms,baro_alt_m,"
    "a_nav_x_ms2,a_nav_y_ms2,a_nav_z_ms2,"
    "omega_x_dps,omega_y_dps,omega_z_dps,"
    "roll_angle_deg,roll_rate_dps,yaw_deg,pitch_deg,roll_pwm,roll_dir,"
    "bus_V,load_V,current_mA,power_mW,ina_overflow,"
    "rsv1,rsv2,rsv3,rsv4,rsv5,"
    "raw_i16_0,raw_i16_1,raw_i16_2,raw_i16_3,raw_i16_4,raw_i16_5,raw_i16_6,raw_i16_7,"
    "ch33,ch34,ch35,ch36,ch37,ch38,ch39\n";
  wf.write(hdr, strlen(hdr));

  Record r;
  uint64_t left = used;
  uint32_t t0 = 0, prev_ts=0;
  bool first = true;

  char line[512];
  while (left >= REC_BYTES) {
    int n = rf.read(&r, REC_BYTES);
    if (n != (int)REC_BYTES) break;
    left -= REC_BYTES;
    if (r.ts_us == 0 || (prev_ts && r.ts_us <= prev_ts)) break;
    if (first){ t0 = r.ts_us; first=false; }
    prev_ts = r.ts_us;

    float t_s = (r.ts_us - t0) / 1.0e6f;

    int len = 0;
    if (scaled){
      // Entpacken gemäß mapFrameToI16(...)
      float kalman_alt_m   = (float)r.v[0] / 100.0f;
      float kalman_vz_ms   = (float)r.v[1] / 100.0f;
      float baro_alt_m     = (float)r.v[2] / 100.0f;
      float a_nav_x        = (float)r.v[3] / 100.0f;
      float a_nav_y        = (float)r.v[4] / 100.0f;
      float a_nav_z        = (float)r.v[5] / 100.0f;
      float gx             = (float)r.v[6] / 100.0f;
      float gy             = (float)r.v[7] / 100.0f;
      float gz             = (float)r.v[8] / 100.0f;
      float roll_ang       = (float)r.v[9]  / 100.0f;
      float roll_rate      = (float)r.v[10] / 100.0f;
      float yaw_deg        = (float)r.v[11] / 100.0f;
      float pitch_deg      = (float)r.v[12] / 100.0f;
      float roll_pwm       = (float)r.v[13] / 1.0f;
      int   roll_dir       = (int)lroundf((float)r.v[14] / 1000.0f);
      float bus_V          = (float)r.v[15] / 1000.0f;
      float load_V         = (float)r.v[16] / 1000.0f;
      float current_mA     = (float)r.v[17] / 1.0f;
      float power_mW       = (float)r.v[18] / 1.0f;
      int   ina_overflow   = (int)r.v[19];
      float rsv1           = (float)r.v[20] / 100.0f;
      float rsv2           = (float)r.v[21] / 100.0f;
      float rsv3           = (float)r.v[22] / 100.0f;
      float rsv4           = (float)r.v[23] / 100.0f;
      float rsv5           = (float)r.v[24] / 100.0f;

      len = snprintf(line, sizeof(line),
        "%.6f,%u,"
        "%.3f,%.3f,%.3f,"
        "%.3f,%.3f,%.3f,"
        "%.2f,%.2f,%.2f,"
        "%.2f,%.2f,%.0f,%.0f,%.0f,%d,"
        "%.3f,%.3f,%.0f,%.0f,%d,"
        "%.2f,%.2f,%.2f,%.2f,%.2f,"
        "%d,%d,%d,%d,%d,%d,%d,%d,"
        "%d,%d,%d,%d,%d,%d,%d\n",
        t_s, r.write_us_prev,
        kalman_alt_m, kalman_vz_ms, baro_alt_m,
        a_nav_x, a_nav_y, a_nav_z,
        gx, gy, gz,
        roll_ang, roll_rate, yaw_deg, pitch_deg, roll_pwm, roll_dir,
        bus_V, load_V, current_mA, power_mW, ina_overflow,
        rsv1, rsv2, rsv3, rsv4, rsv5,
        r.v[25], r.v[26], r.v[27], r.v[28], r.v[29], r.v[30], r.v[31], r.v[32],
        r.v[33], r.v[34], r.v[35], r.v[36], r.v[37], r.v[38], r.v[39]);
    } else {
      len = snprintf(line, sizeof(line),
        "%.6f,%u,"
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,"
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
        t_s, r.write_us_prev,
        r.v[0], r.v[1], r.v[2], r.v[3], r.v[4], r.v[5], r.v[6], r.v[7], r.v[8], r.v[9],
        r.v[10], r.v[11], r.v[12], r.v[13], r.v[14], r.v[15], r.v[16], r.v[17], r.v[18], r.v[19],
        r.v[20], r.v[21], r.v[22], r.v[23], r.v[24], r.v[25], r.v[26], r.v[27], r.v[28], r.v[29],
        r.v[30], r.v[31], r.v[32], r.v[33], r.v[34], r.v[35], r.v[36], r.v[37], r.v[38], r.v[39]);
    }
    if (len > 0) {
      wf.write(line, len);
      res.rows++;
    }
  }

  wf.sync();
  res.bytes = wf.curPosition();   // inkl. Header
  wf.close();
  rf.close();

  res.ok = true;
  strncpy(res.csv_name, csvName, sizeof(res.csv_name));
  res.csv_name[sizeof(res.csv_name)-1] = 0;

  // Kompakte Rückmeldung
  Serial.printf("CSV export OK: %s  rows=%lu  bytes=%llu\n",
                res.csv_name, (unsigned long)res.rows, (unsigned long long)res.bytes);
  return res;
}

SDExportResult SDLogger_exportLatestCSVx(bool scaled){
  SDExportResult res;
  char bin[16];
  if (!findLatestBIN(bin, sizeof(bin))) {
    Serial.println("[E] no BIN found");
    return res;
  }
  return SDLogger_exportBINtoCSVx(bin, scaled);
}

// === bool-Wrapper (falls du die alte Signatur weiter nutzt) ===
bool SDLogger_exportBINtoCSV(const char* binName, bool scaled){
  SDExportResult r = SDLogger_exportBINtoCSVx(binName, scaled);
  return r.ok;
}

bool SDLogger_exportLatestCSV(bool scaled){
  SDExportResult r = SDLogger_exportLatestCSVx(scaled);
  return r.ok;
}
