#include "QspiFlash.h"
#include <string.h>

// FlexSPI2-LUT-Hilfen wie im Teensy-Kern (LittleFS.cpp)
#define LUT0(opcode, pads, operand) (FLEXSPI_LUT_INSTRUCTION((opcode), (pads), (operand)))
#define LUT1(opcode, pads, operand) (FLEXSPI_LUT_INSTRUCTION((opcode), (pads), (operand)) << 16)
#define CMD_SDR   FLEXSPI_LUT_OPCODE_CMD_SDR
#define ADDR_SDR  FLEXSPI_LUT_OPCODE_RADDR_SDR
#define READ_SDR  FLEXSPI_LUT_OPCODE_READ_SDR
#define WRITE_SDR FLEXSPI_LUT_OPCODE_WRITE_SDR
#define DUMMY_SDR FLEXSPI_LUT_OPCODE_DUMMY_SDR
#define PINS1     FLEXSPI_LUT_NUM_PADS_1
#define PINS4     FLEXSPI_LUT_NUM_PADS_4

namespace {
constexpr uint32_t BASE = 0x00800000;   // zweites Lötfeld (Chip-Select 2) im FlexSPI2-Adressraum
// LUT-Plätze (Sequenz-Index): 8 ID, 9 Lesen 1-1-4, 10 Write-Enable, 11 Seite 1-1-4, 12 Block 64 K, 13 Status
constexpr uint32_t SEQ_ID = 8, SEQ_READ = 9, SEQ_WREN = 10, SEQ_PROG = 11, SEQ_ERASE = 12, SEQ_STATUS = 13;

void ipCommand(uint32_t index, uint32_t addr) {
  uint32_t n;
  FLEXSPI2_IPCR0 = addr;
  FLEXSPI2_IPCR1 = FLEXSPI_IPCR1_ISEQID(index);
  FLEXSPI2_IPCMD = FLEXSPI_IPCMD_TRG;
  while (!((n = FLEXSPI2_INTR) & FLEXSPI_INTR_IPCMDDONE)) {}
  if (n & FLEXSPI_INTR_IPCMDERR) FLEXSPI2_INTR = FLEXSPI_INTR_IPCMDERR;
  FLEXSPI2_INTR = FLEXSPI_INTR_IPCMDDONE;
}

void ipRead(uint32_t index, uint32_t addr, void* data, uint32_t length) {
  uint8_t* p = (uint8_t*)data;
  FLEXSPI2_INTR = FLEXSPI_INTR_IPRXWA;
  FLEXSPI2_IPRXFCR = FLEXSPI_IPRXFCR_CLRIPRXF | FLEXSPI_IPRXFCR_RXWMRK(1);
  FLEXSPI2_IPCR0 = addr;
  FLEXSPI2_IPCR1 = FLEXSPI_IPCR1_ISEQID(index) | FLEXSPI_IPCR1_IDATSZ(length);
  FLEXSPI2_IPCMD = FLEXSPI_IPCMD_TRG;
  while (1) {
    if (length >= 16) {
      if (FLEXSPI2_INTR & FLEXSPI_INTR_IPRXWA) {
        volatile uint32_t* fifo = &FLEXSPI2_RFDR0;
        uint32_t w[4] = {fifo[0], fifo[1], fifo[2], fifo[3]};
        memcpy(p, w, 16);
        p += 16; length -= 16;
        FLEXSPI2_INTR = FLEXSPI_INTR_IPRXWA;
      }
    } else if (length > 0) {
      if ((FLEXSPI2_IPRXFSTS & 0xFF) >= ((length + 7) >> 3)) {
        volatile uint32_t* fifo = &FLEXSPI2_RFDR0;
        uint32_t w[4] = {fifo[0], fifo[1], fifo[2], fifo[3]};
        memcpy(p, w, length);
        length = 0;
      }
    } else if (FLEXSPI2_INTR & FLEXSPI_INTR_IPCMDDONE) {
      break;
    }
  }
  if (FLEXSPI2_INTR & FLEXSPI_INTR_IPCMDERR) FLEXSPI2_INTR = FLEXSPI_INTR_IPCMDERR;
  FLEXSPI2_INTR = FLEXSPI_INTR_IPCMDDONE;
}

void ipWrite(uint32_t index, uint32_t addr, const void* data, uint32_t length) {
  const uint8_t* src = (const uint8_t*)data;
  uint32_t n;
  FLEXSPI2_IPCR0 = addr;
  FLEXSPI2_IPCR1 = FLEXSPI_IPCR1_ISEQID(index) | FLEXSPI_IPCR1_IDATSZ(length);
  FLEXSPI2_IPCMD = FLEXSPI_IPCMD_TRG;
  while (!((n = FLEXSPI2_INTR) & FLEXSPI_INTR_IPCMDDONE)) {
    if (n & FLEXSPI_INTR_IPTXWE) {
      uint32_t k = length > 8 ? 8 : length;
      if (k > 0) {
        memcpy((void*)&FLEXSPI2_TFDR0, src, k);
        src += k; length -= k;
        FLEXSPI2_INTR = FLEXSPI_INTR_IPTXWE;
      }
    }
  }
  if (n & FLEXSPI_INTR_IPCMDERR) FLEXSPI2_INTR = FLEXSPI_INTR_IPCMDERR;
  FLEXSPI2_INTR = FLEXSPI_INTR_IPCMDDONE;
}
}  // namespace

bool QspiFlash::begin() {
  size_ = 0;
  FLEXSPI2_LUTKEY = FLEXSPI_LUTKEY_VALUE;
  FLEXSPI2_LUTCR = FLEXSPI_LUTCR_UNLOCK;
  FLEXSPI2_LUT32 = LUT0(CMD_SDR, PINS1, 0x9F) | LUT1(READ_SDR, PINS1, 1);   // ID
  FLEXSPI2_LUT33 = 0;
  uint8_t id[3] = {0, 0, 0};
  ipRead(SEQ_ID, BASE, id, 3);
  jedec_ = (uint32_t(id[0]) << 16) | (uint32_t(id[1]) << 8) | id[2];
  // Winbond (0xEF) W25Q-Familie, 24-Bit-Adressen bis 16 MB (Kapazitätscode 0x18 = 16 MB)
  if (id[0] != 0xEF || id[2] < 0x14 || id[2] > 0x18) return false;
  const uint32_t sz = 1UL << id[2];

  FLEXSPI2_FLSHA2CR0 = sz / 1024;                  // Größe des zweiten Chip-Selects in KB
  FLEXSPI2_LUTKEY = FLEXSPI_LUTKEY_VALUE;
  FLEXSPI2_LUTCR = FLEXSPI_LUTCR_UNLOCK;
  // Quad-Modus (QE-Bit in SR2, flüchtig): 0x50 "Volatile SR Write Enable", dann 0x31 0x02
  FLEXSPI2_LUT40 = LUT0(CMD_SDR, PINS1, 0x50);
  FLEXSPI2_LUT41 = 0;
  ipCommand(SEQ_WREN, BASE);
  FLEXSPI2_LUT40 = LUT0(CMD_SDR, PINS1, 0x31) | LUT1(CMD_SDR, PINS1, 0x02);
  ipCommand(SEQ_WREN, BASE);
  // Lesen 1-1-4 (0x6B, 8 Dummy-Takte), Seite programmieren 1-1-4 (0x32), Block 64 K (0xD8), Status (0x05)
  FLEXSPI2_LUT36 = LUT0(CMD_SDR, PINS1, 0x6B) | LUT1(ADDR_SDR, PINS1, 24);
  FLEXSPI2_LUT37 = LUT0(DUMMY_SDR, PINS4, 8) | LUT1(READ_SDR, PINS4, 1);
  FLEXSPI2_LUT38 = 0;
  FLEXSPI2_LUT40 = LUT0(CMD_SDR, PINS1, 0x06);       // Write-Enable
  FLEXSPI2_LUT41 = 0;
  FLEXSPI2_LUT44 = LUT0(CMD_SDR, PINS1, 0x32) | LUT1(ADDR_SDR, PINS1, 24);
  FLEXSPI2_LUT45 = LUT0(WRITE_SDR, PINS4, 1);
  FLEXSPI2_LUT46 = 0;
  FLEXSPI2_LUT48 = LUT0(CMD_SDR, PINS1, 0xD8) | LUT1(ADDR_SDR, PINS1, 24);
  FLEXSPI2_LUT49 = 0;
  FLEXSPI2_LUT52 = LUT0(CMD_SDR, PINS1, 0x05) | LUT1(READ_SDR, PINS1, 1);
  FLEXSPI2_LUT53 = 0;
  size_ = sz;
  return waitIdle(10000);
}

bool QspiFlash::busy() {
  uint8_t st = 0;
  ipRead(SEQ_STATUS, BASE, &st, 1);
  return st & 0x01;
}

void QspiFlash::startProgram(uint32_t addr, const void* data, uint32_t n) {
  ipCommand(SEQ_WREN, BASE);
  ipWrite(SEQ_PROG, BASE + addr, data, n);
}

void QspiFlash::startErase64k(uint32_t addr) {
  ipCommand(SEQ_WREN, BASE);
  ipCommand(SEQ_ERASE, BASE + addr);
}

void QspiFlash::read(uint32_t addr, void* data, uint32_t n) {
  uint8_t* p = (uint8_t*)data;
  while (n) {                                       // IP-Lesen in Häppchen (IDATSZ, RX-FIFO)
    const uint32_t k = n > 64 ? 64 : n;
    ipRead(SEQ_READ, BASE + addr, p, k);
    p += k; addr += k; n -= k;
  }
}

bool QspiFlash::waitIdle(uint32_t timeout_us) {
  const uint32_t t0 = micros();
  while (busy()) if (micros() - t0 > timeout_us) return false;
  return true;
}
