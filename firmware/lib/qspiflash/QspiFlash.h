#pragma once
// QspiFlash.h – roher, nicht blockierender Zugriff auf den QSPI-Flash unter dem Teensy 4.1
//
// Der Teensy 4.1 hat auf der Rückseite zwei SOIC-8-Lötfelder an FlexSPI2. Auf unserem Teensy:
// Feld 1 PSRAM (8 MB, vom Kern als EXTMEM eingerichtet), Feld 2 Flash W25Q128 (16 MB, Adresse
// 0x800000 im FlexSPI2-Adressraum). Dieser Treiber spricht den Flash mit IP-Befehlen an, wie
// LittleFS_QSPIFlash im Teensy-Kern (LUT-Plätze 8–13 dieselben), aber ohne Dateisystem und ohne
// zu warten: startProgram() und startErase64k() geben den Befehl ab (wenige µs) und kehren
// zurück; busy() fragt das Statusregister. So kann der Flug-Loop den Flash beschreiben, ohne je
// auf ihn zu warten (Seite programmieren typ. 0,4–0,7 ms, höchstens 3 ms; 64-KB-Block löschen
// typ. 150 ms, höchstens 2 s; Werte W25Q128JV-Datenblatt, Richtwerte).
//
// Nicht mit LittleFS_QSPIFlash im selben Programm mischen: dessen begin() formatiert den Flash,
// wenn kein LittleFS darauf ist, und löscht damit den Flugschreiber.
#include <Arduino.h>

class QspiFlash {
public:
  static constexpr uint32_t PAGE  = 256;
  static constexpr uint32_t BLOCK = 65536;

  // JEDEC-ID lesen, LUTs einrichten, Quad-Modus einschalten. false = kein bekannter Flash.
  bool begin();
  bool ok() const { return size_ > 0; }
  uint32_t size() const { return size_; }        // Bytes
  uint32_t jedec() const { return jedec_; }      // z.B. 0xEF4018 (W25Q128JV)

  bool busy();                                   // Statusregister, Bit 0 (WIP)
  // Eine Seite (höchstens 256 Byte, nicht über eine Seitengrenze) programmieren; kehrt sofort zurück
  void startProgram(uint32_t addr, const void* data, uint32_t n);
  // 64-KB-Block löschen (addr auf Blockgrenze); kehrt sofort zurück
  void startErase64k(uint32_t addr);
  // Lesen (blockierend, für das Auslesen am Boden)
  void read(uint32_t addr, void* data, uint32_t n);
  // Warten, bis der Flash frei ist; false bei Zeitüberschreitung
  bool waitIdle(uint32_t timeout_us);

private:
  uint32_t size_ = 0, jedec_ = 0;
};
