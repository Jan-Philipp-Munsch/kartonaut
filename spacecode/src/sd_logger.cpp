#include <Arduino.h>
#include <SdFat.h>

// ===========================
// SD-Setup (Teensy 4.1 SDIO)
// ===========================
SdFs   sd;
FsFile file;
static const SdioConfig sdConfig = SdioConfig(FIFO_SDIO);

// ===========================
// Logger-Parameter
// ===========================
static const uint32_t LOOP_HZ   = 250;
static const uint32_t LOOP_US   = 1000000UL / LOOP_HZ;  // 4000 µs
static const size_t   NUM_I16   = 20;

// Datensatz: 4 + 2 + 2 + 40 = 48 B
struct __attribute__((packed,aligned(4))) Record {
  uint32_t ts_us;          // absolute micros() beim Schreiben
  uint16_t write_us_prev;  // Dauer des vorigen Schreibvorgangs (µs)
  uint16_t _pad;
  int16_t  v[NUM_I16];     // 20 Werte
};
static const size_t REC_BYTES   = sizeof(Record);   // 48

// Schreibhappen (512 B ~= Sektorgröße)
static const size_t PAGE        = 512;

// Voralloziierte Loggröße
static const uint32_t LOG_BYTES = 4UL * 1024UL * 1024UL; // 4 MB

// Aktuelle Dateinamen der laufenden Session
char currentTmpName[16]  = "";   // z.B. LOG00023.TMP
char currentBinName[16]  = "";   // z.B. LOG00023.BIN

// ===========================
// Laufzeit-States
// ===========================
uint8_t  pageBuf[PAGE];
size_t   fill           = 0;        // Pufferfüllung
uint32_t t_next         = 0;        // nächster 4-ms-Tick
bool     logging        = false;
bool     paused         = false;
uint16_t last_write_us  = 0;        // im nächsten Datensatz gespeichert

// opportunistisches Syncing
uint32_t lastSyncUs = 0;
uint32_t startUs    = 0;
const uint32_t SYNC_INTERVAL_US_LATE  = 2000000UL; // 2 s
const uint32_t SYNC_INTERVAL_US_EARLY = 500000UL;  // 0.5 s in den ersten 10 s

// ===========================
// Auswahl-Liste (Dump-/Export-Ziel)
// ===========================
#define MAX_LOGS  64
char     logList[MAX_LOGS][16];   // Dateinamen (LOGxxxxx.BIN / .TMP)
uint32_t logSize[MAX_LOGS];       // Größen in Bytes (nur Anzeige)
int      logCount = 0;            // Einträge
int      selIdx   = -1;           // aktuell ausgewählte Datei-Index

// ===========================
// Hilfsfunktionen
// ===========================
void menu() {
  Serial.println("\nCommands:");
  Serial.println(" s = start logging (pre-allocate + begin, unique .TMP)");
  Serial.println(" p = pause logging");
  Serial.println(" x = stop logging (flush + truncate + close + rename .TMP→.BIN)");
  Serial.println(" L = list logs (0–9 to select)");
  Serial.println(" d = dump selected log to Serial (time since start)");
  Serial.println(" c = export selected log to CSV on SD (LOGxxxxx.CSV)");
  Serial.println(" A = export ALL BIN logs to CSV");
  Serial.println(" i = card/file info");
  Serial.println(" e = erase all LOG*.BIN/.TMP (format light)");
  Serial.println(" h = help");
}

bool ensureSdBegun() {
  static bool begun = false;
  if (begun) return true;
  if (sd.begin(sdConfig)) { begun = true; return true; }
  Serial.println("[E] sd.begin() failed");
  return false;
}

void makeSampleCore(int16_t* dst20) {
  for (size_t i = 0; i < NUM_I16; ++i) {
    dst20[i] = (int16_t)random(-32768, 32767);   // TODO: echte Sensorwerte eintragen
  }
}

void flushPage() {
  if (fill == 0) return;
  int wrote = file.write(pageBuf, fill);
  if (wrote != (int)fill) Serial.println("[E] file.write() short/fail");
  fill = 0;
}

void writeRec(const Record& r) {
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

// prüft, ob Name LOGxxxxx.EXT ist (EXT ".BIN" oder ".TMP")
bool isLogPattern(const char* name, bool* isBinOut, int* numOut) {
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

// nächste freie Nummer finden, die weder .TMP noch .BIN belegt
bool nextFreeNumber(int* outNum) {
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

// Root scannen → Liste füllen (neueste zuerst), selIdx auf 0 setzen
void refreshLogList() {
  logCount = 0;
  selIdx = -1;
  if (!ensureSdBegun()) return;

  FsFile dir;
  if (!dir.open("/")) { Serial.println("[E] open root failed"); return; }

  char name[64];
  FsFile e;
  struct Entry { char nm[16]; uint32_t sz; int num; bool bin; } tmp[MAX_LOGS];
  int cnt = 0;

  while (e.openNext(&dir, O_RDONLY)) {
    int len = e.getName(name, sizeof(name));
    if (len > 0) {
      bool isBin; int num;
      if (isLogPattern(name, &isBin, &num)) {
        if (cnt < MAX_LOGS) {
          strncpy(tmp[cnt].nm, name, sizeof(tmp[cnt].nm));
          tmp[cnt].nm[sizeof(tmp[cnt].nm)-1] = 0;
          tmp[cnt].sz = e.fileSize();
          tmp[cnt].num = num;
          tmp[cnt].bin = isBin;
          cnt++;
        }
      }
    }
    e.close();
  }
  dir.close();

  // sortieren: Nummer absteigend, BIN vor TMP bei gleicher Nummer
  for (int i = 0; i < cnt; ++i) {
    for (int j = i+1; j < cnt; ++j) {
      bool prior = (tmp[j].num > tmp[i].num) || (tmp[j].num == tmp[i].num && tmp[j].bin && !tmp[i].bin);
      if (prior) { auto t = tmp[i]; tmp[i] = tmp[j]; tmp[j] = t; }
    }
  }

  for (int i = 0; i < cnt && i < MAX_LOGS; ++i) {
    strncpy(logList[i], tmp[i].nm, sizeof(logList[i]));
    logList[i][sizeof(logList[i]) - 1] = 0;
    logSize[i] = tmp[i].sz;
  }
  logCount = (cnt < MAX_LOGS) ? cnt : MAX_LOGS;
  if (logCount > 0) selIdx = 0;

  Serial.println("\nLogs in root (newest first):");
  int show = (logCount > 10) ? 10 : logCount;
  for (int i = 0; i < show; ++i) {
    Serial.printf(" %d: %s  (%lu B)%s\n", i, logList[i], (unsigned long)logSize[i], (i==selIdx?"  <selected>":""));
  }
  if (logCount == 0) Serial.println(" (none)");
  else if (logCount > show) Serial.printf(" ... and %d more\n", logCount - show);
}

// ===== Plausibilitätscheck & Nutzlängen-Ermittlung =====
bool validRec(const Record& r, uint32_t prev_ts) {
  if (r.ts_us == 0) return false;
  if (prev_ts && (r.ts_us <= prev_ts)) return false;     // monoton steigend
  if (r.write_us_prev > 50000) return false;             // >50 ms unrealistisch
  int crlf = 0;
  for (int i = 0; i < (int)NUM_I16; i++) if (r.v[i] == 2573) crlf++;
  if (crlf > 8) return false;                            // zu viel ASCII-"Rauschen"
  return true;
}

// ermittelt die "benutzte" Länge einer LOG-Datei
// - für .BIN: fileSize() abgerundet auf Record-Grenze
// - für .TMP: bis zum ersten ungültigen Record vorgehen
uint64_t usedLengthForFile(FsFile& rf, bool isTMP) {
  uint64_t size = rf.fileSize();
  if (!isTMP) return (size / REC_BYTES) * REC_BYTES;

  // .TMP: realen Schluss finden
  uint64_t pos = 0;
  Record r;
  uint32_t prev_ts = 0;
  while (pos + REC_BYTES <= size) {
    int n = rf.read(&r, REC_BYTES);
    if (n != (int)REC_BYTES) break;
    if (!validRec(r, prev_ts)) {
      size = pos; break;
    }
    prev_ts = r.ts_us;
    pos += REC_BYTES;
  }
  return (size / REC_BYTES) * REC_BYTES;
}

// ===== Start/Stop/Erase =====
bool startLog() {
  if (!ensureSdBegun()) return false;

  int num;
  if (!nextFreeNumber(&num)) { Serial.println("[E] no free LOGxxxxx numbers"); return false; }

  snprintf(currentTmpName, sizeof(currentTmpName), "LOG%05d.TMP", num);
  snprintf(currentBinName, sizeof(currentBinName), "LOG%05d.BIN", num);

  if (!file.open(currentTmpName, O_RDWR | O_CREAT | O_TRUNC)) {
    Serial.println("[E] open failed");
    return false;
  }
  if (!file.preAllocate(LOG_BYTES)) {
    Serial.println("[E] preAllocate(LOG_BYTES) failed");
    file.close();
    return false;
  }

  // WICHTIG: Dir/FAT sofort sichern
  file.sync();

  file.rewind();
  fill           = 0;
  logging        = true;
  paused         = false;
  last_write_us  = 0;
  startUs        = micros();
  lastSyncUs     = startUs;

  // Liste aktualisieren + Auswahl auf aktuelle TMP setzen
  refreshLogList();
  for (int i = 0; i < logCount; ++i) {
    if (strcmp(logList[i], currentTmpName) == 0) { selIdx = i; break; }
  }

  Serial.printf("Logging started: %s (pre-allocated %lu bytes)\n",
                currentTmpName, (unsigned long)LOG_BYTES);
  return true;
}

void stopLog() {
  logging = false;
  paused  = false;

  flushPage();

  if (file.isOpen()) {
    if (!file.truncate(file.curPosition())) Serial.println("[W] truncate failed (ignored)");
    file.sync();
    file.close();

    if (currentTmpName[0]) {
      // Falls Wunsch-BIN existiert, nächste freie Nummer wählen
      if (sd.exists(currentBinName)) {
        int num;
        if (!nextFreeNumber(&num)) {
          Serial.printf("[W] rename failed: no free number; keeping as %s\n", currentTmpName);
          return;
        }
        snprintf(currentBinName, sizeof(currentBinName), "LOG%05d.BIN", num);
      }
      if (sd.rename(currentTmpName, currentBinName)) {
        Serial.printf("Stopped. Saved as %s\n", currentBinName);
      } else {
        Serial.printf("[W] rename failed, kept as %s\n", currentTmpName);
      }
      // Liste neu aufbauen, Auswahl auf eben gespeicherte BIN setzen
      refreshLogList();
      for (int i = 0; i < logCount; ++i) {
        if (strcmp(logList[i], currentBinName) == 0) { selIdx = i; break; }
      }
    } else {
      Serial.println("Stopped (no current name).");
    }
  } else {
    Serial.println("Stopped (file not open).");
  }
}

void eraseAllLogs() {
  if (!ensureSdBegun()) return;
  if (file.isOpen()) { Serial.println("[W] file open; stop first."); return; }

  FsFile dir;
  if (!dir.open("/")) { Serial.println("[E] open root failed"); return; }
  FsFile e;
  char name[64];
  uint32_t removed = 0;

  while (e.openNext(&dir, O_RDONLY)) {
    int len = e.getName(name, sizeof(name));
    e.close();
    if (len <= 0) continue;
    bool isBin; int num;
    if (isLogPattern(name, &isBin, &num)) {
      if (sd.remove(name)) { removed++; Serial.printf("removed %s\n", name); }
      else                 { Serial.printf("[W] remove failed: %s\n", name); }
    }
  }
  dir.close();
  Serial.printf("Erase done. Removed %lu files.\n", (unsigned long)removed);

  // Liste leeren
  logCount = 0; selIdx = -1;
}

// ===== List & Select =====
void refreshLogListAndPrint() { refreshLogList(); } // alias für Menü ‘L’

// ===== Dump to Serial (Zeit seit Start) =====
void dumpCSV_Selected_Serial() {
  if (!ensureSdBegun()) return;

  // aktive Datei bestimmen
  const char* name = nullptr;
  if (file.isOpen()) name = currentTmpName;
  else if (selIdx >= 0 && selIdx < logCount) name = logList[selIdx];
  else { refreshLogList(); if (selIdx >= 0 && selIdx < logCount) name = logList[selIdx]; }

  if (!name) { Serial.println("(no selection)"); return; }
  if (!sd.exists(name)) { Serial.printf("[E] file not found: %s\n", name); return; }

  FsFile rf;
  if (!rf.open(name, O_RDONLY)) {
    Serial.printf("[E] open for read failed: %s\n", name);
    return;
  }

  bool isTMP = false; int dummy;
  isLogPattern(name, &isTMP, &dummy);
  uint64_t used = usedLengthForFile(rf, isTMP);
  rf.rewind();

  Serial.printf("\nDumping %s as CSV (used=%llu bytes)\n", name, (unsigned long long)used);
  Serial.println("t_s,write_us_prev,int0,int1,int2,int3,int4,int5,int6,int7,int8,int9,int10,int11,int12,int13,int14,int15,int16,int17,int18,int19");

  Record r;
  uint64_t left = used;
  uint32_t t0 = 0;
  uint32_t prev_ts = 0;
  bool first = true;

  while (left >= REC_BYTES) {
    int n = rf.read(&r, REC_BYTES);
    if (n != (int)REC_BYTES) break;
    left -= REC_BYTES;

    if (!validRec(r, prev_ts)) break;
    if (first) { t0 = r.ts_us; first = false; }
    prev_ts = r.ts_us;

    float t_s = (r.ts_us - t0) / 1e6f;  // Zeit seit Start (s)

    Serial.print(t_s, 6);
    Serial.print(','); Serial.print(r.write_us_prev);
    for (size_t i = 0; i < NUM_I16; ++i) { Serial.print(','); Serial.print(r.v[i]); }
    Serial.println();
  }

  rf.close();
  Serial.println("<end>");
}

// ===== CSV-Dateiname zu einer Logdatei bilden =====
void makeCsvName(const char* logName, char* out, size_t outSz) {
  // LOGxxxxx.BIN/.TMP -> LOGxxxxx.CSV
  strncpy(out, logName, outSz);
  out[outSz-1] = 0;
  size_t L = strlen(out);
  if (L >= 4) { out[L-3]='C'; out[L-2]='S'; out[L-1]='V'; }
}

// ===== Export ausgewählte Datei zu CSV auf SD =====
bool exportCSV_For(const char* name) {
  if (!ensureSdBegun()) return false;
  if (!name || !sd.exists(name)) { Serial.println("[E] export: source not found"); return false; }

  FsFile rf;
  if (!rf.open(name, O_RDONLY)) { Serial.printf("[E] open src failed: %s\n", name); return false; }

  bool isTMP = false; int dummy;
  isLogPattern(name, &isTMP, &dummy);
  uint64_t used = usedLengthForFile(rf, isTMP);
  rf.rewind();

  char csvName[16];
  makeCsvName(name, csvName, sizeof(csvName));

  // Zieldatei anlegen (überschreiben erlaubt)
  FsFile wf;
  if (!wf.open(csvName, O_RDWR | O_CREAT | O_TRUNC)) {
    Serial.printf("[E] open dst failed: %s\n", csvName);
    rf.close();
    return false;
  }

  // Header
  wf.println(F("t_s,write_us_prev,int0,int1,int2,int3,int4,int5,int6,int7,int8,int9,int10,int11,int12,int13,int14,int15,int16,int17,int18,int19"));

  // Zeilen schreiben
  Record r;
  uint64_t left = used;
  uint32_t t0 = 0;
  uint32_t prev_ts = 0;
  bool first = true;

  char line[256];

  while (left >= REC_BYTES) {
    int n = rf.read(&r, REC_BYTES);
    if (n != (int)REC_BYTES) break;
    left -= REC_BYTES;

    if (!validRec(r, prev_ts)) break;
    if (first) { t0 = r.ts_us; first = false; }
    prev_ts = r.ts_us;

    float t_s = (r.ts_us - t0) / 1e6f;

    // Zeile in Buffer formatieren (schneller als viele prints)
    // t_s mit 6 Nachkommastellen
    int len = snprintf(line, sizeof(line),
                       "%.6f,%u,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
                       t_s, r.write_us_prev,
                       r.v[0], r.v[1], r.v[2], r.v[3], r.v[4], r.v[5], r.v[6], r.v[7], r.v[8], r.v[9],
                       r.v[10], r.v[11], r.v[12], r.v[13], r.v[14], r.v[15], r.v[16], r.v[17], r.v[18], r.v[19]);
    if (wf.write(line, len) != len) { Serial.println("[E] CSV write failed"); break; }
  }

  wf.sync();
  wf.close();
  rf.close();

  Serial.printf("CSV written: %s  (from %s, used=%llu bytes)\n", csvName, name, (unsigned long long)used);
  return true;
}

void exportCSV_Selected() {
  const char* name = nullptr;
  if (file.isOpen()) {
    Serial.println("[W] stop logging first (x) before exporting.");
    return;
  }
  if (selIdx >= 0 && selIdx < logCount) name = logList[selIdx];
  else { refreshLogList(); if (selIdx >= 0 && selIdx < logCount) name = logList[selIdx]; }

  if (!name) { Serial.println("(no selection)"); return; }
  exportCSV_For(name);
}

void exportCSV_AllBIN() {
  if (!ensureSdBegun()) return;
  if (file.isOpen()) { Serial.println("[W] stop logging first."); return; }

  int exported = 0;
  for (int i = 0; i < logCount; ++i) {
    bool isBin; int num;
    if (isLogPattern(logList[i], &isBin, &num) && isBin) {
      exportCSV_For(logList[i]);
      exported++;
    }
  }
  Serial.printf("Exported %d BIN logs to CSV.\n", exported);
}

// ===== Auto-Recovery: alle TMP → BIN (mit benutzter Länge) =====
void autoRecoverTMPtoBIN() {
  if (!ensureSdBegun()) return;
  FsFile dir;
  if (!dir.open("/")) { Serial.println("[E] open root failed"); return; }

  FsFile e;
  char name[16];
  int recovered = 0;

  while (e.openNext(&dir, O_RDWR)) {
    int len = e.getName(name, sizeof(name));
    if (len > 0) {
      bool isBin; int num;
      if (isLogPattern(name, &isBin, &num) && !isBin) {
        // .TMP → benutzte Länge ermitteln
        uint64_t used = usedLengthForFile(e, true);
        e.truncate(used);
        e.sync();
        e.close();

        char tmpName[16], binName[16];
        snprintf(tmpName, sizeof(tmpName), "LOG%05d.TMP", num);
        snprintf(binName, sizeof(binName), "LOG%05d.BIN", num);

        // Falls BIN schon existiert, hole dir nächste freie Nummer
        if (sd.exists(binName)) {
          int newNum;
          if (!nextFreeNumber(&newNum)) {
            Serial.printf("[W] no free number to recover %s\n", tmpName);
            continue;
          }
          snprintf(binName, sizeof(binName), "LOG%05d.BIN", newNum);
        }

        if (sd.rename(tmpName, binName)) {
          Serial.printf("Recovered %s → %s (used=%llu)\n", tmpName, binName, (unsigned long long)used);
          recovered++;
        } else {
          Serial.printf("[W] rename failed: %s\n", tmpName);
        }
      } else {
        e.close();
      }
    } else {
      e.close();
    }
  }
  dir.close();
  if (recovered) {
    refreshLogList();
  }
}

// ===========================
// Setup / Loop
// ===========================
void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {}
  Serial.println("\nTeensy 4.1 — 250Hz SD Logger (robust: unique names, list+select, .TMP→.BIN, periodic sync, CSV export)");

  randomSeed(analogRead(A0) ^ micros());
  t_next  = micros() + LOOP_US;

  // SD initialisieren, alte TMP-Dateien automatisch recovern, Liste füllen
  if (ensureSdBegun()) {
    autoRecoverTMPtoBIN();
    refreshLogList();
  }

  menu();
}

void loop() {
  // Konsole
  if (Serial.available()) {
    char c = Serial.read();
    switch (c) {
      case 's': startLog(); break;
      case 'p': paused = true;  Serial.println("Paused."); break;
      case 'x': stopLog(); break;
      case 'L': refreshLogListAndPrint(); break;
      case 'd': dumpCSV_Selected_Serial(); break;
      case 'c': exportCSV_Selected(); break;
      case 'A': exportCSV_AllBIN(); break;
      case 'i': {
        if (!ensureSdBegun()) break;
        cid_t cid; csd_t csd;
        if (sd.card()->readCID(&cid) && sd.card()->readCSD(&csd)) {
          uint32_t sectors = sd.card()->sectorCount();
          uint64_t cap     = (uint64_t)sectors * 512ULL;
          Serial.printf("Card: %lu MiB  Sectors: %lu  FS: %s\n",
                        (unsigned long)(cap >> 20),
                        (unsigned long)sectors,
                        sd.fatType() == 16 ? "FAT16" : (sd.fatType() == 32 ? "FAT32" : "exFAT"));
        } else {
          Serial.println("Card info unavailable.");
        }
        if (file.isOpen()) {
          Serial.printf("Recording: %s  curPosition=%llu B  buffer fill=%u  last_write_us=%u\n",
                        currentTmpName[0] ? currentTmpName : "(unnamed)",
                        (unsigned long long)file.curPosition(),
                        (unsigned)fill, (unsigned)last_write_us);
        } else {
          if (selIdx >= 0 && selIdx < logCount) {
            Serial.printf("Selected: %s  size=%lu B\n", logList[selIdx], (unsigned long)logSize[selIdx]);
          } else {
            Serial.println("No selection. Press 'L' to list and select.");
          }
        }
      } break;
      case 'e': eraseAllLogs(); break;

      // Ziffern 0..9 → Auswahl setzen (nur wenn gelistet)
      case '0': case '1': case '2': case '3': case '4':
      case '5': case '6': case '7': case '8': case '9': {
        int idx = c - '0';
        if (logCount > 0 && idx < logCount) {
          selIdx = idx;
          Serial.printf("Selected #%d: %s  size=%lu B\n", selIdx, logList[selIdx], (unsigned long)logSize[selIdx]);
        } else {
          Serial.println("[W] index out of range (list first with 'L').");
        }
      } break;

      case 'h':
      case '\r':
      case '\n': menu(); break;
    }
    while (Serial.read() != -1) {}
  }

  // 250-Hz-Loop
  uint32_t now = micros();
  if ((int32_t)(now - t_next) >= 0) {
    uint32_t t0 = micros();

    if (logging && !paused) {
      Record rec;
      rec.ts_us = micros();
      rec.write_us_prev = last_write_us;
      rec._pad = 0;
      makeSampleCore(rec.v);

      uint32_t w0 = micros();
      writeRec(rec);                 // packt in 512B-Puffer, flush bei Voll
      uint32_t w1 = micros();
      uint32_t wdt = w1 - w0;
      last_write_us = (wdt > 0xFFFF) ? 0xFFFF : (uint16_t)wdt;

      // opportunistisches Syncing:
      // - erst 10 s alle 0.5 s, danach alle 2 s – nur wenn Zeitpuffer > ~1.2 ms
      uint32_t sinceStart = rec.ts_us - startUs;
      uint32_t interval   = (sinceStart < 10000000UL) ? SYNC_INTERVAL_US_EARLY : SYNC_INTERVAL_US_LATE;
      uint32_t now2 = micros();
      if ((now2 - lastSyncUs) >= interval
          && (t_next > now2) && ((t_next - now2) > 1200)) {
        file.sync();
        lastSyncUs = now2;
      }
    }

    // Deadline-Wächter
    uint32_t dt = micros() - t0;
    if (dt > LOOP_US) {
      Serial.printf("\n⚠️  Loop overrun: %lu us (> %lu us). fill=%u pos=%llu\n",
                    (unsigned long)dt, (unsigned long)LOOP_US,
                    (unsigned)fill,
                    file.isOpen() ? (unsigned long long)file.curPosition() : 0ULL);
    }

    // nächsten Tick planen
    t_next += LOOP_US;
    if ((int32_t)(micros() - t_next) > 10 * (int32_t)LOOP_US) {
      t_next = micros() + LOOP_US;
    }
  }
}