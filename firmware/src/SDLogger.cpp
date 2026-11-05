// SDLogger.cpp – Flug-Log mit Ringpuffer im PSRAM, SD-Zugriffe nur außerhalb der Flugphase.
// Ablauf und Gründe: SDLogger.h. Datensatz: 4 Byte Zeitstempel (micros), 2 Byte Formatversion,
// 2 Byte Kanalzahl, 64 × int16 mit fester Skalierung je Kanal (Tabelle LOG_CH).
// Beim nächsten Start werden liegengebliebene .TMP repariert (Ende = erster Satz ohne
// steigenden Zeitstempel). Am Boden exportiert SDLogger_exportLatestCSVx() die Datei als CSV.
#include "SDLogger.h"
#include "LogRing.h"
#include <SdFat.h>
#include <ctype.h>
#include <string.h>

extern "C" uint8_t external_psram_size;   // Teensy-Kern (startup.c): 0, 8 oder 16 MB PSRAM

// ===========================
// SD-Setup (Teensy 4.1 SDIO)
// ===========================
static SdFs   sd;
static FsFile file;
static const SdioConfig sdConfig = SdioConfig(FIFO_SDIO);

// ===========================
// Datensatz
// ===========================
static const uint16_t FORMAT = 2;          // 1 = bis 04.11.2026 (88 Byte, 40 Kanäle)
static const size_t   NCH    = 64;

struct __attribute__((packed, aligned(4))) Record {
  uint32_t ts_us;          // micros() beim Ablegen im Puffer
  uint16_t format;
  uint16_t nch;            // belegte Kanäle (L_NUM)
  int16_t  v[NCH];
};
static const size_t REC_BYTES = sizeof(Record);            // 136 B
static_assert(sizeof(Record) == 136, "Satzgröße");

// Kanaltabelle: Name (CSV-Kopf) und Faktor (Wert × Faktor -> int16)
struct ChDef { const char* name; float scale; };
static const ChDef LOG_CH[L_NUM] = {
  {"kalman_alt_m", 100}, {"kalman_vz_ms", 100}, {"baro_alt_m", 100}, {"kalman_innov_m", 100},
  {"p_rel_pa", 1}, {"baro_temp_c", 100}, {"imu_temp_c", 100},
  {"acc_x_ms2", 100}, {"acc_y_ms2", 100}, {"acc_z_ms2", 100},
  {"a_nav_x_ms2", 100}, {"a_nav_y_ms2", 100}, {"a_nav_z_ms2", 100}, {"a_norm_ms2", 100},
  {"omega_x_dps", 100}, {"omega_y_dps", 100}, {"omega_z_dps", 100},
  {"omega_raw_x_dps", 10}, {"omega_raw_y_dps", 10}, {"omega_raw_z_dps", 10},
  {"mag_x_gauss", 5000}, {"mag_y_gauss", 5000}, {"mag_z_gauss", 5000},
  {"q_w", 10000}, {"q_x", 10000}, {"q_y", 10000}, {"q_z", 10000},
  {"tilt_x_deg", 100}, {"tilt_y_deg", 100}, {"roll_deg", 100},
  {"mahony_int_x_dps", 1000}, {"mahony_int_y_dps", 1000}, {"mahony_int_z_dps", 1000},
  {"servo_yaw_deg", 100}, {"servo_pitch_deg", 100}, {"tvc_yaw_deg", 100}, {"tvc_pitch_deg", 100},
  {"roll_pwm", 1}, {"roll_dir", 1}, {"throttle_u", 1000},
  {"vbat1_V", 100}, {"vbat2_V", 100}, {"arm_V", 100}, {"current_A", 1000},
  {"state", 1}, {"flags", 1}, {"pyro", 1}, {"reset_cause", 1}, {"t_flight_ds", 1}, {"sensor_bits", 1},
  {"imu_n", 1}, {"loop_us", 1}, {"dt_us", 1}, {"log_dropped", 1}, {"ring_pct", 1}, {"fifo_overruns", 1},
};

static const uint32_t LOG_BYTES = 64UL * 1024UL * 1024UL;   // vorab belegt, ~8 min bei 250 Hz
static const size_t   CHUNK_RECS = 15;                      // ~2 KB je Schreibzugriff
static const uint32_t SYNC_INTERVAL_US = 500000UL;          // endgültig speichern alle 0,5 s

static char currentTmpName[16] = "";       // z.B. LOG00023.TMP
static char currentBinName[16] = "";       // z.B. LOG00023.BIN

// ===========================
// Laufzeit
// ===========================
static LogRing    ring;
static uint8_t*   ring_mem = nullptr;
static SDLogStats st;
static bool       logging = false;
static uint32_t   lastSyncUs = 0;
static uint32_t   write_est_us = 2000;     // Schätzung je Schreibzugriff: steigt sofort, fällt langsam
static uint32_t   sync_est_us  = 4000;

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

// Ringpuffer: PSRAM, wenn bestückt (6 MB, 2 MB bleiben frei), sonst Heap im RAM2
static void allocRing() {
  if (ring_mem) return;
  st.psram_mb = external_psram_size;
  if (external_psram_size >= 8) {
    const uint32_t want = 6UL * 1024UL * 1024UL;
    ring_mem = (uint8_t*)extmem_malloc(want);
    if (ring_mem) { st.ring_bytes = want; st.in_psram = ((uint32_t)ring_mem >> 28) == 7; }
  }
  static const uint32_t FALLBACK[] = {384UL * 1024UL, 192UL * 1024UL, 96UL * 1024UL};
  for (uint32_t sz : FALLBACK) {
    if (ring_mem) break;
    ring_mem = (uint8_t*)malloc(sz);
    if (ring_mem) { st.ring_bytes = sz; st.in_psram = false; }
  }
  ring.attach(ring_mem, st.ring_bytes, REC_BYTES);
  st.capacity = ring.capacityRecords();
}

// Bis zu max_recs der ältesten Sätze auf die Karte; false = Schreibfehler (Karte weg)
static bool writeChunk(size_t max_recs) {
  const uint8_t* p;
  const size_t k = ring.peek(&p, max_recs);
  if (!k) return true;
  const uint32_t t0 = micros();
  const size_t n = file.write(p, k * REC_BYTES);
  const uint32_t dt = micros() - t0;
  st.write_us_last = dt;
  if (dt > st.write_us_max) st.write_us_max = dt;
  write_est_us = dt > write_est_us ? dt : (write_est_us * 15 + dt) / 16;
  if (n != k * REC_BYTES) return false;
  ring.consume(k);
  st.written += k;
  return true;
}

static void doSync() {
  const uint32_t t0 = micros();
  file.sync();
  const uint32_t dt = micros() - t0;
  if (dt > st.sync_us_max) st.sync_us_max = dt;
  sync_est_us = dt > sync_est_us ? dt : (sync_est_us * 7 + dt) / 8;
  lastSyncUs = micros();
}

static inline int16_t q(float x, float s) {
  long v = lroundf(x * s);
  if (v >  32767) v =  32767;
  if (v < -32768) v = -32768;
  return (int16_t)v;
}

// ===========================
// Öffentliches API
// ===========================
void SDLogger_setup() {
  allocRing();
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
  logging    = true;
  lastSyncUs = micros();
  return true;
}

bool SDLogger_isRecording() { return logging; }
uint32_t SDLogger_queued() { return ring.count(); }

void SDLogger_setOverwrite(bool on) { ring.setOverwrite(on); }

bool SDLogger_logFrame(const SDFrame& f) {
  if (!ring.ready()) return false;
  Record r;
  r.ts_us  = micros();
  r.format = FORMAT;
  r.nch    = L_NUM;
  for (size_t i = 0; i < NCH; ++i) r.v[i] = i < L_NUM ? q(f.v[i], LOG_CH[i].scale) : 0;
  return ring.push(&r);
}

void SDLogger_service(uint32_t deadline_us, bool sd_allowed) {
  if (!logging || !sd_allowed || !file.isOpen()) return;
  auto slack = [&]() { const int32_t s = (int32_t)(deadline_us - micros()); return s > 0 ? (uint32_t)s : 0u; };
  // nur schreiben, wenn auch ein Zugriff so lang wie der langsamste geschätzte noch Platz hat
  while (ring.count() > 0 && slack() > write_est_us + write_est_us / 2 + 300) {
    if (!writeChunk(CHUNK_RECS)) { logging = false; return; }   // Karte weg: der Puffer behält die Daten
  }
  if (micros() - lastSyncUs >= SYNC_INTERVAL_US && slack() > sync_est_us + sync_est_us / 2 + 300) doSync();
}

void SDLogger_drainAll() {
  if (!logging || !file.isOpen()) return;
  while (ring.count() > 0) {
    if (!writeChunk(64)) { logging = false; return; }
  }
  doSync();
}

void SDLogger_stop() {
  if (!logging) return;
  SDLogger_drainAll();
  logging = false;
  if (file.isOpen()) {
    file.truncate(file.curPosition());
    file.sync();
    file.close();
    if (currentTmpName[0]) {
      if (sd.exists(currentBinName)) {
        int num; if (nextFreeNumber(&num)) snprintf(currentBinName, sizeof(currentBinName), "LOG%05d.BIN", num);
      }
      sd.rename(currentTmpName, currentBinName);
    }
  }
}

void SDLogger_getStats(SDLogStats& out) {
  st.queued = ring.count(); st.max_queued = ring.maxCount();
  st.dropped = ring.dropped(); st.overwritten = ring.overwritten();
  out = st;
}

// ===========================
// CSV-Export (am Boden)
// ===========================
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

SDExportResult SDLogger_exportBINtoCSVx(const char* name, bool scaled) {
  SDExportResult res;
  if (!ensureSdBegun() || !name || !sd.exists(name)) return res;
  FsFile rf;
  if (!rf.open(name, O_RDONLY)) return res;
  bool isBin = false; int dummy = 0;
  isLogPattern(name, &isBin, &dummy);
  uint64_t used = usedLengthForFile(rf, !isBin);
  rf.rewind();

  char csvName[16];
  strncpy(csvName, name, sizeof(csvName));
  csvName[sizeof(csvName) - 1] = 0;
  const size_t L = strlen(csvName);
  if (L >= 4) { csvName[L - 3] = 'C'; csvName[L - 2] = 'S'; csvName[L - 1] = 'V'; }
  FsFile wf;
  if (!wf.open(csvName, O_RDWR | O_CREAT | O_TRUNC)) { rf.close(); return res; }

  wf.write("t_s", 3);
  for (size_t i = 0; i < L_NUM; ++i) { wf.write(",", 1); wf.write(LOG_CH[i].name, strlen(LOG_CH[i].name)); }
  wf.write("\n", 1);

  Record r;
  uint32_t t0 = 0, prev_ts = 0;
  bool first = true;
  char line[1024];
  while (used >= REC_BYTES) {
    if (rf.read(&r, REC_BYTES) != (int)REC_BYTES) break;
    used -= REC_BYTES;
    if (r.ts_us == 0 || (prev_ts && r.ts_us <= prev_ts) || r.format != FORMAT) break;
    if (first) { t0 = r.ts_us; first = false; }
    prev_ts = r.ts_us;
    int len = snprintf(line, sizeof line, "%.6f", (r.ts_us - t0) / 1.0e6);
    for (size_t i = 0; i < L_NUM && len < (int)sizeof(line) - 24; ++i) {
      const float s = LOG_CH[i].scale;
      len += scaled ? snprintf(line + len, sizeof(line) - len, ",%.*f", s >= 1000 ? 4 : (s >= 10 ? 2 : 0), r.v[i] / s)
                    : snprintf(line + len, sizeof(line) - len, ",%d", r.v[i]);
    }
    line[len++] = '\n';
    wf.write(line, len);
    res.rows++;
  }
  wf.sync();
  res.bytes = wf.curPosition();
  wf.close();
  rf.close();
  res.ok = true;
  memcpy(res.csv_name, csvName, sizeof(csvName));
  return res;
}

SDExportResult SDLogger_exportLatestCSVx(bool scaled) {
  SDExportResult res;
  char bin[16];
  if (!findLatestBIN(bin, sizeof(bin))) return res;
  return SDLogger_exportBINtoCSVx(bin, scaled);
}
