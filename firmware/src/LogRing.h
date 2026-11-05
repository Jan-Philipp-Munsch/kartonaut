#pragma once
// LogRing.h – Ringpuffer für Log-Datensätze fester Größe (ohne Arduino, läuft in den nativen Tests)
//
// Der Flug-Loop legt jeden Datensatz hier ab (eine Kopie, < 1 µs im PSRAM); auf die SD-Karte
// schreibt SDLogger.cpp nur, wenn der Flugabschnitt es erlaubt. Datensätze bleiben ganz: Schreiben
// und Verwerfen geschehen nur in ganzen Sätzen, die Datei auf der Karte bleibt satzweise lesbar.
//
// Zwei Betriebsarten, wenn der Puffer voll ist:
//   overwrite = true   ältesten Satz verwerfen (PAD_READY: Vorlauf, nur die letzten Minuten zählen)
//   overwrite = false  neuen Satz verwerfen (ab dem Start: der Flug von Anfang an ist wichtiger)
#include <stddef.h>
#include <stdint.h>
#include <string.h>

class LogRing {
public:
  // buf: Speicher mit mindestens cap_bytes; rec: Satzgröße
  void attach(uint8_t* buf, size_t cap_bytes, size_t rec) {
    buf_ = buf; rec_ = rec; n_ = (rec && buf) ? cap_bytes / rec : 0;
    head_ = tail_ = count_ = 0; dropped_ = overwritten_ = 0; max_count_ = 0;
  }
  bool   ready() const { return n_ > 0; }
  size_t capacityRecords() const { return n_; }
  size_t count() const { return count_; }
  size_t maxCount() const { return max_count_; }
  uint32_t dropped() const { return dropped_; }
  uint32_t overwritten() const { return overwritten_; }
  void   setOverwrite(bool on) { overwrite_ = on; }
  bool   overwrite() const { return overwrite_; }

  // Einen Satz ablegen; false = verworfen (voll und overwrite aus)
  bool push(const void* rec) {
    if (!n_) return false;
    if (count_ == n_) {
      if (!overwrite_) { dropped_++; return false; }
      tail_ = (tail_ + 1) % n_; count_--; overwritten_++;
    }
    memcpy(buf_ + head_ * rec_, rec, rec_);
    head_ = (head_ + 1) % n_;
    count_++;
    if (count_ > max_count_) max_count_ = count_;
    return true;
  }

  // Zusammenhängender Block der ältesten Sätze (höchstens max_recs), ohne ihn freizugeben
  size_t peek(const uint8_t** p, size_t max_recs) const {
    if (!count_) { *p = nullptr; return 0; }
    size_t k = n_ - tail_;              // bis zum Pufferende
    if (k > count_) k = count_;
    if (k > max_recs) k = max_recs;
    *p = buf_ + tail_ * rec_;
    return k;
  }
  // k Sätze als geschrieben freigeben
  void consume(size_t k) {
    if (k > count_) k = count_;
    tail_ = (tail_ + k) % n_;
    count_ -= k;
  }

private:
  uint8_t* buf_ = nullptr;
  size_t rec_ = 0, n_ = 0, head_ = 0, tail_ = 0, count_ = 0, max_count_ = 0;
  uint32_t dropped_ = 0, overwritten_ = 0;
  bool overwrite_ = false;
};
