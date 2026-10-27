#pragma once
// Sha256.h – SHA-256 (FIPS 180-4) und HMAC-SHA256 (RFC 2104) für die Authentisierung der
// Startkommandos (LaunchAuth.h). Klein, ohne Heap, kein Arduino: läuft in den nativen Tests.
#include <stdint.h>
#include <stddef.h>

class Sha256 {
public:
  static constexpr size_t BLOCK = 64, DIGEST = 32;

  Sha256() { reset(); }
  void reset();
  void update(const uint8_t* data, size_t n);
  void final(uint8_t out[DIGEST]);

private:
  void block(const uint8_t* p);
  uint32_t h_[8];
  uint8_t  buf_[BLOCK];
  size_t   fill_ = 0;
  uint64_t bits_ = 0;
};

void sha256(const uint8_t* data, size_t n, uint8_t out[Sha256::DIGEST]);
void hmac_sha256(const uint8_t* key, size_t key_len, const uint8_t* msg, size_t msg_len,
                 uint8_t out[Sha256::DIGEST]);
