#pragma once
// Crc16.h – CRC-16/CCITT-FALSE (Polynom 0x1021, Start 0xFFFF, ohne Reflexion)
// für die Telemetrierahmen. Prüfwert für "123456789": 0x29B1.
#include <stddef.h>
#include <stdint.h>

uint16_t crc16_ccitt(const uint8_t* data, size_t len, uint16_t crc = 0xFFFF);
