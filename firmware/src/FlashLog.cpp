// FlashLog.cpp – Flugschreiber im QSPI-Flash, siehe FlashLog.h
#include "FlashLog.h"
#include "QspiFlash.h"
#include <Arduino.h>
#include <string.h>

namespace {
constexpr uint32_t MAGIC = 0x314C464Bu;    // "KFL1"
constexpr uint32_t DATA0 = QspiFlash::PAGE;  // Datensätze ab Seite 1
constexpr uint32_t OFF_COPIED = 64, OFF_END = 68;

struct __attribute__((packed)) FlashHeader {
  uint32_t magic;
  uint16_t format;           // Satzformat (SDLogger, 2)
  uint16_t rec_bytes;        // 136
  uint32_t session_ms;       // millis() beim Start der Sitzung
  uint8_t  reserved[52];
  uint8_t  copied;           // Byte 64: 0xFF = noch nicht auf der SD-Karte, 0x00 = kopiert
  uint8_t  reserved2[3];
  uint32_t end;              // Byte 68: Ende der Daten, 0xFFFFFFFF = nicht abgeschlossen (Stromausfall)
};
static_assert(sizeof(FlashHeader) == 72, "Kopf");

// Warteschlange der zu programmierenden Stücke (je höchstens eine Seite, nicht über Seitengrenzen)
struct Op { uint32_t addr; uint16_t len; uint8_t data[QspiFlash::PAGE]; };
constexpr int QN = 64;                       // 16 KB, ~0,5 s Vorrat bei 250 Hz
DMAMEM Op q[QN];
int q_head = 0, q_tail = 0, q_count = 0, q_max = 0;

QspiFlash fl;
bool     present = false, session = false, session_pending = false, old_pending = false;
uint32_t write_pos = DATA0, erased_to = 0, erase_limit = 0, dropped = 0;
uint8_t  page[QspiFlash::PAGE];
uint32_t page_fill = 0;

bool push(uint32_t addr, const void* data, uint32_t len) {
  if (q_count == QN) return false;
  Op& o = q[q_head];
  o.addr = addr; o.len = (uint16_t)len;
  memcpy(o.data, data, len);
  q_head = (q_head + 1) % QN; q_count++;
  if (q_count > q_max) q_max = q_count;
  return true;
}

bool readHeader(FlashHeader& h) {
  fl.read(0, &h, sizeof h);
  return h.magic == MAGIC;
}

// Erste ungeschriebene Seite ab DATA0 (Binärsuche; Seite gilt als leer, wenn ihre ersten 16 Byte 0xFF sind)
bool pageBlank(uint32_t addr) {
  uint8_t b[16];
  fl.read(addr, b, sizeof b);
  for (uint8_t x : b) if (x != 0xFF) return false;
  return true;
}
uint32_t findEnd() {
  uint32_t lo = DATA0 / QspiFlash::PAGE, hi = fl.size() / QspiFlash::PAGE;   // Seiten [lo, hi)
  while (lo < hi) {
    const uint32_t mid = (lo + hi) / 2;
    if (pageBlank(mid * QspiFlash::PAGE)) hi = mid; else lo = mid + 1;
  }
  return lo * QspiFlash::PAGE;
}

uint32_t roundUpBlock(uint32_t a) { return (a + QspiFlash::BLOCK - 1) / QspiFlash::BLOCK * QspiFlash::BLOCK; }

// ---- Kopie zur SD-Karte: Datensätze prüfen und glätten ----
// Nach einem Neustart im Flug fehlt ein angefangener Satz (Seitenpuffer im RAM verloren), und micros()
// beginnt von vorn. Die Kopie sucht deshalb jeden Satz an Format und Kanalzahl, überspringt Bruchstücke
// und macht die Zeitstempel monoton, damit der CSV-Export die ganze Datei liest.
uint32_t c_pos, c_end, c_prev_ts, c_ts_off;
uint8_t  c_win[512];
uint32_t c_win_addr = 0xFFFFFFFF;

uint8_t byteAt(uint32_t a) {
  if (a < c_win_addr || a >= c_win_addr + sizeof c_win) {
    c_win_addr = a;
    fl.read(a, c_win, sizeof c_win);
  }
  return c_win[a - c_win_addr];
}

size_t nextRecords(void* buf, size_t max) {
  const size_t rec = SDLogger_recordBytes();
  uint8_t* out = (uint8_t*)buf;
  size_t n = 0;
  while (n + rec <= max && c_pos + rec <= c_end) {
    uint8_t r[160];
    for (size_t i = 0; i < rec; ++i) r[i] = byteAt(c_pos + i);
    uint32_t ts; uint16_t format, nch;
    memcpy(&ts, r, 4); memcpy(&format, r + 4, 2); memcpy(&nch, r + 6, 2);
    if (format != 2 || nch != L_NUM || ts == 0xFFFFFFFF) { c_pos++; continue; }   // Bruchstück: weitersuchen
    ts += c_ts_off;
    if (c_prev_ts && ts <= c_prev_ts) { c_ts_off += c_prev_ts - ts + 4000; ts = c_prev_ts + 4000; }
    c_prev_ts = ts;
    memcpy(r, &ts, 4);
    memcpy(out + n, r, rec);
    n += rec;
    c_pos += rec;
  }
  return n;
}
}  // namespace

bool FlashLog_copyToSd() {
  if (!present) return false;
  FlashHeader h;
  if (!readHeader(h)) return false;
  c_pos = DATA0;
  c_end = h.end != 0xFFFFFFFFu ? h.end : findEnd();
  c_prev_ts = 0; c_ts_off = 0; c_win_addr = 0xFFFFFFFF;
  char name[16];
  const bool ok = SDLogger_writeBlobFile(nextRecords, name);
  if (ok) {
    const uint8_t zero = 0;
    fl.waitIdle(5000);
    fl.startProgram(OFF_COPIED, &zero, 1);    // 0xFF -> 0x00 geht ohne Löschen
    fl.waitIdle(5000);
    Serial.printf("Flugschreiber: %lu Byte aus dem Flash nach %s kopiert\n", (unsigned long)(c_end - DATA0), name);
    old_pending = false;
    if (!session && !session_pending) {         // kopiert: benutzten Bereich für den nächsten Flug löschen
      erase_limit = roundUpBlock(c_end) + QspiFlash::BLOCK;
      if (erase_limit > fl.size()) erase_limit = fl.size();
      erased_to = 0;
    }
  }
  return ok;
}

void FlashLog_setup(bool resume) {
  present = fl.begin();
  if (!present) return;
  FlashHeader h;
  const bool valid = readHeader(h);
  if (resume && valid) {                       // Neustart im Flug: hinten anhängen
    write_pos = findEnd();
    erased_to = erase_limit = fl.size();
    session = true;
    return;
  }
  if (valid && h.copied == 0xFF) {
    old_pending = true;
    if (!FlashLog_copyToSd()) {
      Serial.println("Flugschreiber: alter Flug im Flash, keine SD-Karte -> nicht geloescht, Flugschreiber aus (USB 'f')");
      return;
    }
  }
  // zu löschen: der zuletzt benutzte Bereich; ohne gültigen Kopf (erster Einsatz) der ganze Chip
  const uint32_t used = valid ? (h.end != 0xFFFFFFFFu ? h.end : findEnd()) : fl.size();
  erase_limit = roundUpBlock(used) + (valid ? QspiFlash::BLOCK : 0);
  if (erase_limit > fl.size()) erase_limit = fl.size();
  erased_to = 0;
}

void FlashLog_startSession() {
  if (!present || old_pending || session) return;
  session_pending = true;
}

void FlashLog_abortSession() {
  if (!present || (!session && !session_pending)) return;
  session = session_pending = false;
  q_head = q_tail = q_count = 0;
  page_fill = 0;
  erase_limit = roundUpBlock(write_pos);
  erased_to = 0;
  write_pos = DATA0;
}

void FlashLog_finish() {
  if (!present || !session) return;
  if (page_fill > 0) { if (!push(write_pos, page, page_fill)) dropped++; write_pos += page_fill; page_fill = 0; }
  const uint32_t end = write_pos;
  push(OFF_END, &end, 4);
  session = false;
}

void FlashLog_log(const SDFrame& f) {
  if (!present || !session) return;
  uint8_t rec[160];
  const size_t n = SDLogger_recordBytes();
  SDLogger_pack(f, rec);
  if (write_pos + page_fill + n > fl.size()) { dropped++; return; }     // voll
  size_t done = 0;
  while (done < n) {
    const size_t k = (QspiFlash::PAGE - page_fill) < (n - done) ? (QspiFlash::PAGE - page_fill) : (n - done);
    memcpy(page + page_fill, rec + done, k);
    page_fill += k; done += k;
    if (page_fill == QspiFlash::PAGE) {
      if (!push(write_pos, page, QspiFlash::PAGE)) dropped++;   // Warteschlange voll: Seite fehlt
      write_pos += QspiFlash::PAGE;
      page_fill = 0;
    }
  }
}

void FlashLog_service(bool erase_ok) {
  if (!present) return;
  if (fl.busy()) return;                      // Chip arbeitet noch: nächster Loop
  if (q_count > 0) {
    Op& o = q[q_tail];
    q_tail = (q_tail + 1) % QN; q_count--;
    if (o.addr < DATA0 || o.addr + o.len <= erased_to) fl.startProgram(o.addr, o.data, o.len);
    else dropped++;                           // Bereich (noch) nicht gelöscht
    return;
  }
  if (session_pending && erased_to >= QspiFlash::BLOCK) {
    FlashHeader h;
    memset(&h, 0xFF, sizeof h);
    h.magic = MAGIC; h.format = 2; h.rec_bytes = (uint16_t)SDLogger_recordBytes(); h.session_ms = millis();
    push(0, &h, sizeof h);
    write_pos = DATA0; page_fill = 0;
    session = true; session_pending = false;
    return;
  }
  if (erase_ok && erased_to < erase_limit) {
    fl.startErase64k(erased_to);
    erased_to += QspiFlash::BLOCK;
  }
}

void FlashLog_getStats(FlashLogStats& s) {
  s.present = present; s.jedec = fl.jedec(); s.size = fl.size();
  s.session = session; s.write_pos = write_pos + page_fill; s.erased_to = erased_to;
  s.queued_pages = q_count; s.max_queued = q_max; s.dropped_records = dropped;
  s.old_flight_pending = old_pending;
}
