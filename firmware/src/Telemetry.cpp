#include "Telemetry.h"
#include "Crc16.h"
#include <string.h>

namespace tlm {

size_t encode(uint8_t type, const uint8_t* payload, size_t payload_len, uint8_t* out, size_t out_cap) {
  if (payload_len > MAX_PAYLOAD || out_cap < payload_len + OVERHEAD) return 0;
  out[0] = SYNC0; out[1] = SYNC1; out[2] = type; out[3] = (uint8_t)payload_len;
  if (payload_len) memcpy(out + 4, payload, payload_len);
  const uint16_t crc = crc16_ccitt(out + 2, payload_len + 2);
  out[4 + payload_len] = (uint8_t)(crc & 0xFF);
  out[5 + payload_len] = (uint8_t)(crc >> 8);
  return payload_len + OVERHEAD;
}

int8_t clamp_i8(float v)  { return (int8_t)(v > 127.f ? 127 : (v < -128.f ? -128 : (v >= 0 ? (int)(v + 0.5f) : (int)(v - 0.5f)))); }
int16_t clamp_i16(float v){ return (int16_t)(v > 32767.f ? 32767 : (v < -32768.f ? -32768 : (v >= 0 ? (int)(v + 0.5f) : (int)(v - 0.5f)))); }
uint8_t clamp_u8(float v) { return (uint8_t)(v > 255.f ? 255 : (v < 0.f ? 0 : (int)(v + 0.5f))); }

bool Parser::feed(uint8_t b) {
  switch (st_) {
    case S_SYNC0:
      if (b == SYNC0) st_ = S_SYNC1;
      return false;
    case S_SYNC1:
      if (b == SYNC1) st_ = S_TYPE;
      else st_ = (b == SYNC0) ? S_SYNC1 : S_SYNC0;
      return false;
    case S_TYPE:
      type_ = b; st_ = S_LEN;
      return false;
    case S_LEN:
      if (b > MAX_PAYLOAD) { bad_++; st_ = S_SYNC0; return false; }
      len_ = b; idx_ = 0;
      st_ = len_ ? S_PAYLOAD : S_CRC0;
      return false;
    case S_PAYLOAD:
      buf_[idx_++] = b;
      if (idx_ >= len_) st_ = S_CRC0;
      return false;
    case S_CRC0:
      crc_rx_ = b; st_ = S_CRC1;
      return false;
    case S_CRC1: {
      crc_rx_ |= (uint16_t)b << 8;
      st_ = S_SYNC0;
      uint8_t hdr[2] = {type_, len_};
      uint16_t crc = crc16_ccitt(hdr, 2);
      crc = crc16_ccitt(buf_, len_, crc);
      if (crc != crc_rx_) { bad_++; return false; }
      return true;
    }
  }
  return false;
}

}  // namespace tlm
