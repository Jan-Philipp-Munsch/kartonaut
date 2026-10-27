#pragma once
// LaunchAuth.h – Authentisierung von ARM und LAUNCH (Plan Bordzündung 27.10.2026, §3.3)
//
//   MAC = erste 8 Byte von HMAC-SHA256(Schlüssel, Typ | seq | nonce (4 Byte, little-endian) | Raketen-ID)
//
// Die nonce ist eine 32-Bit-Zufallszahl der Rakete (TRNG des Teensy 4.1, main.cpp). Jede gilt genau
// einmal: verify() verbraucht sie, ob der MAC stimmt oder nicht; danach setzt main.cpp mit renew() eine
// neue, die im ACK zurückgeht. Ein aufgezeichneter Befehl passt damit auf keine spätere nonce.
// Kein Arduino: läuft in den nativen Tests. Das Laptop-Werkzeug rechnet dasselbe in Python
// (tools/ground/kartonaut_radio.py).
#include <stdint.h>
#include <stddef.h>

namespace launch_auth {

constexpr size_t KEY_LEN = 16, MAC_LEN = 8;

void computeMac(const uint8_t key[KEY_LEN], uint8_t type, uint8_t seq, uint32_t nonce, uint8_t rocket_id,
                uint8_t mac[MAC_LEN]);

// Ein Schlüssel aus lauter Nullen (Vorlage nicht ausgefüllt) gilt als fehlend
bool keyUsable(const uint8_t key[KEY_LEN]);

}  // namespace launch_auth

class LaunchAuth {
public:
  LaunchAuth(const uint8_t key[launch_auth::KEY_LEN], uint8_t rocket_id);

  void renew(uint32_t random) { nonce_ = random; valid_ = true; }   // neue nonce (Zufallszahl)
  void discard() { valid_ = false; }
  bool hasNonce() const { return valid_; }
  uint32_t nonce() const { return valid_ ? nonce_ : 0; }

  // MAC über die aktuelle nonce prüfen; die nonce ist danach in jedem Fall verbraucht.
  // Ohne gültige nonce oder ohne brauchbaren Schlüssel immer false.
  bool verify(uint8_t type, uint8_t seq, const uint8_t mac[launch_auth::MAC_LEN]);

private:
  uint8_t  key_[launch_auth::KEY_LEN];
  uint8_t  rocket_id_;
  uint32_t nonce_ = 0;
  bool     valid_ = false;
};
