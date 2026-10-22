#include "Telemetry.h"
#include "Crc16.h"

size_t kn_encode(uint8_t type, const void* payload, uint8_t len, uint8_t* buf, size_t buf_size) {
  if (len > KN_MAX_PAYLOAD || buf_size < size_t(len) + KN_FRAME_OVERHEAD) return 0;
  buf[0] = KN_SYNC0;
  buf[1] = KN_SYNC1;
  buf[2] = type;
  buf[3] = len;
  const uint8_t* p = static_cast<const uint8_t*>(payload);
  for (uint8_t i = 0; i < len; ++i) buf[4 + i] = p[i];
  const uint16_t crc = crc16_ccitt(buf + 2, size_t(len) + 2);
  buf[4 + len]     = uint8_t(crc >> 8);
  buf[5 + len]     = uint8_t(crc & 0xFF);
  return size_t(len) + KN_FRAME_OVERHEAD;
}

bool KnParser::feed(uint8_t b) {
  switch (state_) {
    case S_SYNC0:
      if (b == KN_SYNC0) state_ = S_SYNC1;
      return false;
    case S_SYNC1:
      // 0xA5 0xA5 0x5A soll auch synchronisieren
      state_ = (b == KN_SYNC1) ? S_TYPE : (b == KN_SYNC0 ? S_SYNC1 : S_SYNC0);
      return false;
    case S_TYPE:
      type_ = b;
      state_ = S_LEN;
      return false;
    case S_LEN:
      if (b > KN_MAX_PAYLOAD) { state_ = S_SYNC0; return false; }
      len_ = b;
      pos_ = 0;
      state_ = (len_ == 0) ? S_CRC_HI : S_PAYLOAD;
      return false;
    case S_PAYLOAD:
      payload_[pos_++] = b;
      if (pos_ >= len_) state_ = S_CRC_HI;
      return false;
    case S_CRC_HI:
      crc_rx_ = uint16_t(b) << 8;
      state_ = S_CRC_LO;
      return false;
    case S_CRC_LO: {
      crc_rx_ |= b;
      state_ = S_SYNC0;
      uint16_t crc = crc16_ccitt(&type_, 1);
      crc = crc16_ccitt(&len_, 1, crc);
      crc = crc16_ccitt(payload_, len_, crc);
      if (crc == crc_rx_) { ++ok_; return true; }
      ++crc_err_;
      return false;
    }
  }
  return false;
}
