#pragma once
// Radio.h – Funkstrecke zur Bodenstation über Serial8.
//
//   Breakouts  HC-12, transparent, 9600 Bd, keine Konfiguration aus der Firmware.
//   rev B      E22-400T22S: einmalige Konfiguration über M0/M1 (Adresse, Kanal,
//              Luftrate, Leistung), danach transparenter Modus. AUX zeigt an,
//              ob das Modul einen weiteren Rahmen annimmt.
//
// Rahmen nach KartonautProtocol.h. send() blockiert nie: Passt der Rahmen
// nicht in den Sendepuffer oder ist das Modul beschäftigt, wird er verworfen
// und gezählt (Telemetrie kommt im nächsten Takt wieder).
#include "Config.h"
#include "Board.h"
#include "Telemetry.h"

class Radio {
public:
  void begin();
  bool configure();                  // rev B: E22-Parameter schreiben und prüfen; Breakout: true
  bool sendRaw(uint8_t type, const void* payload, uint8_t len);
  template <typename T> bool send(uint8_t type, const T& msg) { return sendRaw(type, &msg, uint8_t(sizeof(T))); }

  // Empfang verarbeiten; true, wenn ein Kommando vollständig angekommen ist
  bool poll(KnCommand& cmd);

  uint32_t sent() const { return sent_; }
  uint32_t dropped() const { return dropped_; }
  const KnParser& parser() const { return parser_; }
  bool configured() const { return configured_; }

private:
  bool auxReady() const;
  bool e22ReadParams(uint8_t out[9]);

  KnParser parser_;
  uint32_t sent_ = 0, dropped_ = 0;
  bool configured_ = false;
  uint8_t txbuf_[256];
};
