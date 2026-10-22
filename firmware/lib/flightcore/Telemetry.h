#pragma once
// Telemetry.h – Rahmen des Protokolls bauen und byteweise wieder zerlegen.
//
// Unabhängig vom Transport (HC-12, E22, USB). Der Parser ist eine kleine
// Zustandsmaschine, die nach Müll auf der Leitung von selbst wieder auf
// den nächsten 0xA5 0x5A synchronisiert.
#include <stddef.h>
#include <stdint.h>
#include "KartonautProtocol.h"

// Rahmen in buf schreiben; Rückgabe = Länge oder 0, wenn buf zu klein / Nutzlast zu lang.
size_t kn_encode(uint8_t type, const void* payload, uint8_t len, uint8_t* buf, size_t buf_size);

class KnParser {
public:
  // Ein Byte verarbeiten; true genau dann, wenn damit ein gültiger Rahmen
  // vollständig ist. Danach type(), payload(), length() lesen.
  bool feed(uint8_t b);

  uint8_t        type()    const { return type_; }
  uint8_t        length()  const { return len_; }
  const uint8_t* payload() const { return payload_; }

  uint32_t framesOk()  const { return ok_; }
  uint32_t crcErrors() const { return crc_err_; }
  void     reset()           { state_ = S_SYNC0; }

  // Nutzlast typisiert kopieren, false bei falscher Länge
  template <typename T> bool get(T& out) const {
    if (len_ != sizeof(T)) return false;
    const uint8_t* src = payload_;
    uint8_t* dst = reinterpret_cast<uint8_t*>(&out);
    for (size_t i = 0; i < sizeof(T); ++i) dst[i] = src[i];
    return true;
  }

private:
  enum State : uint8_t { S_SYNC0, S_SYNC1, S_TYPE, S_LEN, S_PAYLOAD, S_CRC_HI, S_CRC_LO };
  State    state_ = S_SYNC0;
  uint8_t  type_ = 0, len_ = 0, pos_ = 0;
  uint8_t  payload_[KN_MAX_PAYLOAD];
  uint16_t crc_rx_ = 0;
  uint32_t ok_ = 0, crc_err_ = 0;
};
