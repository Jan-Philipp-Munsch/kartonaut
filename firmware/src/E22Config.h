#pragma once
// E22Config.h – Registerwerte 00H..08H des E22-400T22 aus Config.h (Rakete und Laptop gleich).
//   ADDH, ADDL, NETID, REG0 (UART 9600 8N1 + Luftrate), REG1 (240-Byte-Teilpakete, Sendeleistung),
//   REG2 (Kanal), REG3 (RSSI-Byte, transparent, kein LBT, WOR 2000 ms), CRYPT_H, CRYPT_L.
// Bitlagen nach Ebyte-Handbuch E22-400T22S (wie groundstation/firmware/src/Radio.cpp). Das RSSI-Byte
// hängt das empfangende Modul an jedes Paket; an der Rakete aus, am Laptop an (tools/ground/e22_config.py
// rechnet dasselbe). Kein Arduino: läuft in den nativen Tests.
#include <stdint.h>
#include "Config.h"

namespace e22 {

constexpr uint8_t REG_COUNT = 9;

inline void wantedRegs(uint8_t r[REG_COUNT], bool rssi_byte) {
  r[0] = E22_ADDH;
  r[1] = E22_ADDL;
  r[2] = E22_NETID;
  r[3] = uint8_t((0b011 << 5) | (0b00 << 3) | (E22_AIR_RATE & 0x07));
  r[4] = uint8_t((0b00 << 6) | (E22_POWER & 0x03));
  r[5] = E22_CHANNEL;
  r[6] = uint8_t((rssi_byte ? 0x80 : 0x00) | 0x03);
  r[7] = 0x00;
  r[8] = 0x00;
}

}  // namespace e22
