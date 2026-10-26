#include "Protocol.h"

namespace proto {

const char* stateName(uint8_t s) {
  switch (s) {
    case FS_BOOT:        return "BOOT";
    case FS_IDLE:        return "IDLE";
    case FS_CALIBRATING: return "CALIBRATING";
    case FS_PAD_READY:   return "PAD_READY";
    case FS_BOOST:       return "BOOST";
    case FS_COAST:       return "COAST";
    case FS_APOGEE:      return "APOGEE";
    case FS_DESCENT:     return "DESCENT";
    case FS_LANDED:      return "LANDED";
    case FS_ABORT:       return "ABORT";
    case FS_FAULT:       return "FAULT";
    default:             return "?";
  }
}

const char* commandName(uint8_t c) {
  switch (c) {
    case CMD_PING:            return "PING";
    case CMD_CALIBRATE:       return "CALIBRATE";
    case CMD_PAD_READY_QUERY: return "PAD_READY_QUERY";
    case CMD_ABORT:           return "ABORT";
    default:                  return "?";
  }
}

uint16_t crc16(const uint8_t* data, size_t len, uint16_t crc) {
  while (len--) {
    crc ^= uint16_t(*data++) << 8;
    for (int i = 0; i < 8; i++)
      crc = (crc & 0x8000) ? uint16_t((crc << 1) ^ 0x1021) : uint16_t(crc << 1);
  }
  return crc;
}

size_t encode(uint8_t type, const void* payload, uint8_t len, uint8_t* out) {
  out[0] = SYNC0;
  out[1] = SYNC1;
  out[2] = type;
  out[3] = len;
  memcpy(out + 4, payload, len);
  uint16_t c = crc16(out + 2, 2 + len);
  out[4 + len] = uint8_t(c);
  out[5 + len] = uint8_t(c >> 8);
  return 6 + len;
}

void decodeTelemetry(const TelemetryRaw& r, Telemetry& t) {
  t.seq   = r.seq;
  t.state = r.state;
  t.flags = r.flags;
  t.t_ms  = r.t_ms;
  t.alt_m = r.alt_dm * 0.1f;
  t.vz_ms = r.vz_cms * 0.01f;
  for (int i = 0; i < 4; i++) t.q[i] = r.q[i] / 32767.0f;
  for (int i = 0; i < 2; i++) t.gimbal_deg[i] = r.gimbal_cdeg[i] * 0.01f;
  t.v1s = r.v1s_mv * 0.001f;
  t.v2s = r.v2s_mv * 0.001f;
}

void decodeGps(const GpsRaw& r, Gps& g) {
  g.lat   = r.lat_e7 * 1e-7;
  g.lon   = r.lon_e7 * 1e-7;
  g.alt_m = r.alt_m;
  g.sats  = r.sats;
  g.fix   = r.fix;
}

bool Parser::feed(uint8_t b) {
  switch (st_) {
    case S0:
      if (b == SYNC0) st_ = S1;
      break;
    case S1:
      st_ = (b == SYNC1) ? TYPE : (b == SYNC0 ? S1 : S0);
      break;
    case TYPE:
      type_ = b;
      st_ = LEN;
      break;
    case LEN:
      if (b > MAX_PAYLOAD) { st_ = S0; break; }
      len_ = b;
      idx_ = 0;
      st_ = len_ ? DATA : CRC0;
      break;
    case DATA:
      buf_[idx_++] = b;
      if (idx_ >= len_) st_ = CRC0;
      break;
    case CRC0:
      crcRx_ = b;
      st_ = CRC1;
      break;
    case CRC1: {
      crcRx_ |= uint16_t(b) << 8;
      st_ = S0;
      uint8_t hdr[2] = {type_, len_};
      uint16_t c = crc16(hdr, 2);
      c = crc16(buf_, len_, c);
      if (c == crcRx_) { frames++; return true; }
      crcErrors++;
      break;
    }
  }
  return false;
}

} // namespace proto
