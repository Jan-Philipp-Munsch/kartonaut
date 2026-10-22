#pragma once
// Pyro.h – Zündlogik (Plan §2 B3, Review A4, Spezifikation rev B §5)
//
// Regeln, jede für sich hinreichend, um eine Zündung zu verhindern:
//   1. nur wenn der Flugzustand es erlaubt (APOGEE oder DESCENT, bzw. ABORT
//      nach dem Start für die Bergung),
//   2. nur bei ARM-Spannung (Schlüsselschalter) und Durchgang des Zünders,
//   3. je Kanal höchstens einmal,
//   4. Puls höchstens pulse_ms, Abbruch sobald der Durchgang verloren geht
//      (die Brücke ist durch, weiter Strom hilft nicht und heizt den FET).
//
// Die Klasse schaltet nichts selbst; main.cpp liest fireOutput(ch) und setzt
// die Gate-Pins. Die Hardware verweigert ohne ARM ohnehin.
#include <stdint.h>

class PyroLogic {
public:
  static constexpr int CHANNELS = 4;

  struct Config {
    uint32_t pulse_ms;        // Review A4: 50–100 ms
    uint32_t pulse_max_ms;    // harte Obergrenze
    uint32_t cont_grace_ms;   // Durchgangsverlust erst nach dieser Zeit werten (Messrauschen)
    constexpr Config(uint32_t pulse = 80, uint32_t pulse_max = 100, uint32_t grace = 10)
        : pulse_ms(pulse), pulse_max_ms(pulse_max), cont_grace_ms(grace) {}
  };

  struct Channel {
    bool     fitted = false;
    bool     continuity = false;
    bool     firing = false;
    bool     fired = false;
    uint32_t t_fire_start = 0;
    uint32_t t_cont_lost = 0;
    uint8_t  fire_count = 0;
  };

  explicit PyroLogic(const Config& cfg = Config()) : cfg_(cfg) {}

  void setFitted(int ch, bool fitted) { if (valid(ch)) ch_[ch].fitted = fitted; }

  // Jeden Takt aufrufen, auch ohne Zündwunsch (beendet laufende Pulse).
  // continuity[] = gemessener Durchgang je Kanal in diesem Takt.
  void update(uint32_t t_ms, bool armed, const bool continuity[CHANNELS], bool phase_allows);

  // Zündung anfordern. true = Puls gestartet. Ablehnung, wenn eine Regel greift.
  bool fire(int ch, uint32_t t_ms);

  bool fireOutput(int ch) const { return valid(ch) && ch_[ch].firing; }
  bool fired(int ch)      const { return valid(ch) && ch_[ch].fired; }
  bool continuity(int ch) const { return valid(ch) && ch_[ch].continuity; }
  const Channel& channel(int ch) const { return ch_[valid(ch) ? ch : 0]; }

  uint8_t firedMask() const;
  void    restoreFiredMask(uint8_t mask);   // nach Neustart: keine zweite Zündung

  bool armed() const { return armed_; }
  bool phaseAllows() const { return phase_allows_; }

private:
  static bool valid(int ch) { return ch >= 0 && ch < CHANNELS; }
  Config  cfg_;
  Channel ch_[CHANNELS];
  bool    armed_ = false, phase_allows_ = false;
  uint32_t t_now_ = 0;
};
