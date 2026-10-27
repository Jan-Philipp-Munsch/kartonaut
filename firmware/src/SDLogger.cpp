// SDLogger.cpp – Binär-Logger auf die SD-Karte des Teensy 4.1 (SDIO).
//
// Pro Loop ein 88-Byte-Record (Zeitstempel + 40 × int16, feste Skalierung,
// siehe mapFrameToI16). Die Datei wird vorab alloziert (LOG_BYTES) und als
// LOGxxxxx.TMP geschrieben; SDLogger_stop() kürzt sie und benennt sie in
// .BIN um. Beim nächsten Start werden liegengebliebene .TMP repariert.
// Physische Writes und Syncs passieren nur, wenn die Loop dafür Slack hat.
// Am Boden exportiert SDLogger_exportLatestCSVx() die Datei als CSV.
#include "SDLogger.h"
#include <SdFat.h>
#include <ctype.h>
#include <string.h>

// ===========================
// SD-Setup (Teensy 4.1 SDIO)
// ===========================
static SdFs   sd;
static FsFile file;
static const SdioConfig sdConfig = SdioConfig(FIFO_SDIO);

// ===========================
// Logger-Parameter
// ===========================
static const size_t   NUM_I16       = 40;

// Datensatz: 4 + 2 + 2 + 40*2 = 88 B
struct __attribute__((packed,aligned(4))) Record {
  uint32_t ts_us;          // absolute micros() beim Schreiben
  uint16_t write_us_prev;  // Dauer des vorigen phys. Writes (µs)
  uint16_t _pad;
  int16_t  v[NUM_I16];     // 40 Werte
};
static const size_t REC_BYTES   = sizeof(Record);          // 88 B

// Schreibhappen (512 B ~= Sektor)
static const size_t PAGE        = 512;

// Voralloziierte Loggröße
static const uint32_t LOG_BYTES = 8UL * 1024UL * 1024UL;   // 8 MB

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
// Timing / Guards (Slack-aware)
// ===========================
static SDLogTiming g_tim{};
static float    g_safety_factor    = 1.5f; // Multiplikator auf Schätzung
static uint32_t g_min_slack_flush  = 2000; // µs
static uint32_t g_min_slack_sync   = 4000; // µs
static const float EMA_ALPHA       = 0.10f;

// ===========================
// intern: SD/File Helpers
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
  uint32_t t0 = micros();
  int wrote = file.write(pageBuf, fill);
  uint32_t dt = micros() - t0;

  g_tim.flush_us_last = dt;
  g_tim.flush_us_avg = (g_tim.flush_us_avg == 0) ? dt
                     : (uint32_t)((1.0f-EMA_ALPHA)*g_tim.flush_us_avg + EMA_ALPHA*dt);
  if (dt > g_tim.flush_us_max) g_tim.flush_us_max = dt;
  else                         g_tim.flush_us_max = (uint32_t)(0.999f * g_tim.flush_us_max);

  (void)wrote; // im Flug keine Serials
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
    if (fill == PAGE) flushPage();   // löst ggf. physischen Write aus (gemessen)
  }
}

static uint64_t usedLengthForFile(FsFile& rf, bool isTMP) {
  uint64_t size = rf.fileSize();
  if (!isTMP) return (size / REC_BYTES) * REC_BYTES;

  // .TMP: realen Schluss finden
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
// Öffentliches API
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
  if (!file.preAllocate(LOG_BYTES)) { file.close(); return false; }
  file.sync();
  file.rewind();

  fill          = 0;
  logging       = true;
  last_write_us = 0;
  startUs       = micros();
  lastSyncUs    = startUs;

  // reset timing stats
  g_tim = SDLogTiming{};
  return true;
}

void SDLogger_stop() {
  if (!logging) return;
  logging = false;

  flushPage();
  if (file.isOpen()) {
    file.truncate(file.curPosition());
    uint32_t t0 = micros();
    file.sync();
    uint32_t dt = micros() - t0;
    g_tim.sync_us_last = dt;
    if (dt > g_tim.sync_us_max) g_tim.sync_us_max = dt;

    file.close();

    if (currentTmpName[0]) {
      if (sd.exists(currentBinName)) {
        int num; if (nextFreeNumber(&num)) snprintf(currentBinName, sizeof(currentBinName), "LOG%05d.BIN", num);
      }
      sd.rename(currentTmpName, currentBinName);
    }
  }
}

bool SDLogger_isRecording(){ return logging; }

// ===========================
// Guards / Timing Getter
// ===========================
void SDLogger_getTiming(SDLogTiming& out){ out = g_tim; }

void SDLogger_setTimingGuard(float safety_factor,
                             uint32_t min_slack_flush_us,
                             uint32_t min_slack_sync_us)
{
  if (safety_factor < 1.0f) safety_factor = 1.0f;
  g_safety_factor   = safety_factor;
  g_min_slack_flush = min_slack_flush_us;
  g_min_slack_sync  = min_slack_sync_us;
}

// ===========================
// Quantisierung & Mapping
// ===========================
static inline int16_t q_s(float x, float s){
  long v = lroundf(x * s);
  if (v >  32767) v =  32767;
  if (v < -32768) v = -32768;
  return (int16_t)v;
}
static inline int16_t q_u(float x, float s){
  long v = lroundf(x * s);
  if (v < 0) v = 0;
  if (v >  32767) v = 32767;
  return (int16_t)v;
}

static void mapFrameToI16(const SDFrame& f, int16_t out[40]){
  out[0] = q_s(f.kalman_alt_m,   100.0f);
  out[1] = q_s(f.kalman_vz_ms,   100.0f);
  out[2] = q_s(f.baro_alt_m,     100.0f);
  out[3] = q_s(f.a_nav_x_ms2,    100.0f);
  out[4] = q_s(f.a_nav_y_ms2,    100.0f);
  out[5] = q_s(f.a_nav_z_ms2,    100.0f);

  out[6] = q_s(f.omega_x_dps,    100.0f);
  out[7] = q_s(f.omega_y_dps,    100.0f);
  out[8] = q_s(f.omega_z_dps,    100.0f);

  out[9]  = q_s(f.roll_angle_deg, 100.0f);
  out[10] = q_s(f.roll_rate_dps,  100.0f);
  out[11] = q_u(f.yaw_deg,   100.0f);
  out[12] = q_u(f.pitch_deg, 100.0f);
  out[13] = q_u((float)f.roll_pwm,    1.0f);
  out[14] = q_s((float)f.roll_dir, 1000.0f);

  out[15] = q_s(f.bus_V,        1000.0f);
  out[16] = q_s(f.load_V,       1000.0f);
  out[17] = q_s(f.current_mA,      1.0f);
  out[18] = q_s(f.power_mW,        1.0f);
  out[19] = q_s((float)f.ina_overflow, 1.0f);

  out[20] = q_s(f.state_id, 100.0f);
  out[21] = q_s(f.tilt_x_deg, 100.0f);
  out[22] = q_s(f.tilt_y_deg, 100.0f);
  out[23] = q_s(f.vbat1_V, 100.0f);
  out[24] = q_s(f.a_norm_ms2, 100.0f);

  for (int i=0;i<8;i++) out[25+i] = f.raw_i16[i];

  for (int i=33;i<40;i++) out[i] = 0;
}

// ===========================
// Slack-aware Logging
// ===========================
bool SDLogger_logFrame(const SDFrame& f, uint32_t slack_us){
  return SDLogger_logFrameAt(f, micros(), slack_us);
}

// Frame mit eigener Zeitmarke (Ringpuffer vor ARMED, main.cpp). ts_us muss gegenüber dem
// vorigen Record wachsen, sonst endet die Wiederherstellung und der Export dort.
bool SDLogger_logFrameAt(const SDFrame& f, uint32_t ts_us, uint32_t slack_us){
  if (!logging || !file.isOpen()) return false;

  // 1) Opportunistischer PRE-FLUSH, wenn Puffer Daten hat und Slack groß genug
  if (fill > 0 && slack_us > 0) {
    uint32_t est_flush = max(g_tim.flush_us_avg, g_tim.flush_us_max/2);
    est_flush = (uint32_t)(g_safety_factor * (float)max(est_flush, (uint32_t)500)); // ≥0.5 ms konservativ
    if (slack_us >= max(est_flush, g_min_slack_flush)) {
      flushPage();
    }
  }

  // 2) Record packen + in Page schreiben
  Record r;
  r.ts_us = ts_us;
  r.write_us_prev = last_write_us;
  r._pad = 0;
  mapFrameToI16(f, r.v);

  uint32_t w0 = micros();
  writeRec(r);
  uint32_t w1 = micros();
  uint32_t wdt = (w1 - w0);
  last_write_us = (wdt > 0xFFFF) ? 0xFFFF : (uint16_t)wdt;

  // 3) Periodisches SYNC nur bei genügend Slack & Intervall erfüllt
  const uint32_t now_us = micros();
  uint32_t sinceStart = now_us - startUs;
  uint32_t interval   = (sinceStart < 10000000UL) ? SYNC_INTERVAL_US_EARLY : SYNC_INTERVAL_US_LATE;

  if (slack_us > 0 && (now_us - lastSyncUs) >= interval) {
    uint32_t est_sync = max(g_tim.sync_us_avg, g_tim.sync_us_max/2);
    est_sync = (uint32_t)(g_safety_factor * (float)max(est_sync, (uint32_t)1500)); // ≥1.5 ms konservativ
    if (slack_us >= max(est_sync, g_min_slack_sync)) {
      uint32_t t0 = micros();
      file.sync();
      uint32_t dt = micros() - t0;

      g_tim.sync_us_last = dt;
      g_tim.sync_us_avg = (g_tim.sync_us_avg == 0) ? dt
                           : (uint32_t)((1.0f-EMA_ALPHA)*g_tim.sync_us_avg + EMA_ALPHA*dt);
      if (dt > g_tim.sync_us_max) g_tim.sync_us_max = dt;
      else                        g_tim.sync_us_max = (uint32_t)(0.999f * g_tim.sync_us_max);

      lastSyncUs = micros();
    }
  }

  return true;
}

// Wrapper: kein Slack übergeben → kein Sync im Flug
bool SDLogger_logFrame(const SDFrame& f){
  return SDLogger_logFrame(f, 0);
}

// ===========================
// CSV-Export (am Boden nutzen)
// ===========================

// Decoder passend zum Mapping (q_s und q_u unterscheiden sich nur im Klemmen)
static inline float d_s(int16_t v, float s){ return float(v) / s; }
static inline float d_u(int16_t v, float s){ return d_s(v, s); }

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

SDExportResult SDLogger_exportBINtoCSVx(const char* name, bool scaled){
  SDExportResult res;
  if (!ensureSdBegun() || !name || !sd.exists(name)) return res;

  FsFile rf;
  if (!rf.open(name, O_RDONLY)) return res;

  bool isTMP=false; int dummy=0;
  isLogPattern(name, &isTMP, &dummy);
  uint64_t used = usedLengthForFile(rf, isTMP);
  rf.rewind();

  char csvName[16];
  strncpy(csvName, name, sizeof(csvName));
  csvName[sizeof(csvName)-1] = 0;
  size_t L = strlen(csvName);
  if (L >= 4) { csvName[L-3]='C'; csvName[L-2]='S'; csvName[L-1]='V'; }

  FsFile wf;
  if (!wf.open(csvName, O_RDWR | O_CREAT | O_TRUNC)) { rf.close(); return res; }

  const char* hdr =
    "t_s,write_us_prev,"
    "kalman_alt_m,kalman_vz_ms,baro_alt_m,"
    "a_nav_x_ms2,a_nav_y_ms2,a_nav_z_ms2,"
    "omega_x_dps,omega_y_dps,omega_z_dps,"
    "roll_angle_deg,roll_rate_dps,yaw_deg,pitch_deg,roll_pwm,roll_dir,"
    "bus_V,load_V,current_mA,power_mW,ina_overflow,"
    "state,tilt_x_deg,tilt_y_deg,vbat1_V,a_norm_ms2,"
    "t_flight_ds,flags,pyro_fires,a_axial_cms2,tvc_yaw_cdeg,tvc_pitch_cdeg,reset_cause,raw_7,"
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
      float kalman_alt_m   = d_s(r.v[0], 100.0f);
      float kalman_vz_ms   = d_s(r.v[1], 100.0f);
      float baro_alt_m     = d_s(r.v[2], 100.0f);
      float a_nav_x        = d_s(r.v[3], 100.0f);
      float a_nav_y        = d_s(r.v[4], 100.0f);
      float a_nav_z        = d_s(r.v[5], 100.0f);
      float gx             = d_s(r.v[6], 100.0f);
      float gy             = d_s(r.v[7], 100.0f);
      float gz             = d_s(r.v[8], 100.0f);
      float roll_ang       = d_s(r.v[9], 100.0f);
      float roll_rate      = d_s(r.v[10],100.0f);
      float yaw_deg        = d_u(r.v[11],100.0f);
      float pitch_deg      = d_u(r.v[12],100.0f);
      float roll_pwm       = d_u(r.v[13],1.0f);
      int   roll_dir       = (int)lroundf(d_s(r.v[14],1000.0f));
      float bus_V          = d_s(r.v[15],1000.0f);
      float load_V         = d_s(r.v[16],1000.0f);
      float current_mA     = d_s(r.v[17],1.0f);
      float power_mW       = d_s(r.v[18],1.0f);
      int   ina_overflow   = (int)r.v[19];
      float rsv1           = d_s(r.v[20],100.0f);
      float rsv2           = d_s(r.v[21],100.0f);
      float rsv3           = d_s(r.v[22],100.0f);
      float rsv4           = d_s(r.v[23],100.0f);
      float rsv5           = d_s(r.v[24],100.0f);

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
      // exakt 40 Daten (%d) + 2 Kopf (t_s, write_us_prev)
      len = snprintf(line, sizeof(line),
        "%.6f,%u,"
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,"
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,"
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,"
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
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
  res.bytes = wf.curPosition();
  wf.close();
  rf.close();

  res.ok = true;
  static_assert(sizeof(res.csv_name) >= sizeof(csvName), "csv_name zu klein");
  memcpy(res.csv_name, csvName, sizeof(csvName));
  return res;
}

SDExportResult SDLogger_exportLatestCSVx(bool scaled){
  SDExportResult res;
  char bin[16];
  if (!findLatestBIN(bin, sizeof(bin))) return res;
  return SDLogger_exportBINtoCSVx(bin, scaled);
}

bool SDLogger_exportBINtoCSV(const char* binName, bool scaled){
  SDExportResult r = SDLogger_exportBINtoCSVx(binName, scaled);
  return r.ok;
}
bool SDLogger_exportLatestCSV(bool scaled){
  SDExportResult r = SDLogger_exportLatestCSVx(scaled);
  return r.ok;
}
