#include "LaunchAuth.h"
#include "Sha256.h"
#include <string.h>

namespace launch_auth {

void computeMac(const uint8_t key[KEY_LEN], uint8_t type, uint8_t seq, uint32_t nonce, uint8_t rocket_id,
                uint8_t mac[MAC_LEN]) {
  const uint8_t msg[7] = {type, seq, (uint8_t)nonce, (uint8_t)(nonce >> 8), (uint8_t)(nonce >> 16),
                          (uint8_t)(nonce >> 24), rocket_id};
  uint8_t full[Sha256::DIGEST];
  hmac_sha256(key, KEY_LEN, msg, sizeof msg, full);
  memcpy(mac, full, MAC_LEN);
}

bool keyUsable(const uint8_t key[KEY_LEN]) {
  uint8_t any = 0;
  for (size_t i = 0; i < KEY_LEN; ++i) any |= key[i];
  return any != 0;
}

}  // namespace launch_auth

LaunchAuth::LaunchAuth(const uint8_t key[launch_auth::KEY_LEN], uint8_t rocket_id) : rocket_id_(rocket_id) {
  memcpy(key_, key, sizeof key_);
}

bool LaunchAuth::verify(uint8_t type, uint8_t seq, const uint8_t mac[launch_auth::MAC_LEN]) {
  const bool had = valid_;
  valid_ = false;                       // verbraucht, auch bei falschem MAC
  if (!had || !launch_auth::keyUsable(key_)) return false;
  uint8_t want[launch_auth::MAC_LEN];
  launch_auth::computeMac(key_, type, seq, nonce_, rocket_id_, want);
  uint8_t diff = 0;                     // Vergleich ohne frühen Ausstieg
  for (size_t i = 0; i < launch_auth::MAC_LEN; ++i) diff |= (uint8_t)(want[i] ^ mac[i]);
  return diff == 0;
}
