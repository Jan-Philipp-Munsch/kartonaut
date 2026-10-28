# Funkbrücke: Raspberry Pi Pico mit E22-400T22S

Die Bodenstation für *Kartonaut 1* ist ein Laptop mit dieser Brücke am USB (`docs/Plan_Bordzuendung_2026-10-27.md` §5).
Ein drittes E22-400T22S hängt frei verdrahtet am Pico; Gehäuse mit senkrechtem Halbwellen-Dipol: `cad/groundbridge.py`.

## Verdrahtung

| E22-400T22S | Pico | Bemerkung |
|---|---|---|
| VCC | 3V3 OUT (Pin 36) | |
| GND | GND | |
| TXD | GP5 (UART1 RX) | |
| RXD | GP4 (UART1 TX) | |
| M0 | GP6 | |
| M1 | GP7 | |
| AUX | GP8 | Eingang, hoch = bereit |
| ANT-Pad | Dipol | IPEX bleibt frei |

## Verhalten

- **Laptop → Funk:** nur vollständige Rahmen mit gültiger CRC, unverändert. Bytes außerhalb eines Rahmens verwirft die Brücke.
- **Funk → Laptop:** jedes Byte unverändert, auch das RSSI-Byte, das das E22 an jedes Paket hängt (`launch.py` zeigt es an).
- **Konfiguration:** `python tools/ground/launch.py --port COM5 --config` schickt den Rahmen `BRIDGE_CONFIG` (0x70). Er geht
  nicht über Funk: Die Brücke setzt M1 hoch, liest die E22-Register und schreibt sie bei Abweichung dauerhaft (Kanal, Adresse,
  Luftrate, Sendeleistung aus `firmware/src/Config.h` über `E22Config.h`, dazu RSSI-Byte an). Danach antwortet sie mit
  `BRIDGE_ACK` (0x71) und den gelesenen Registern. Einmal nach dem ersten Flashen genügt; die Werte bleiben im E22.
- **LED:** Dauerlicht, wenn in den letzten 2 s ein gültiger Rahmen von der Rakete kam; Blinken, wenn nicht.
- UART zum E22 mit `RADIO_BAUD` (9600 Bd) wie die Rakete; der USB-Port hat keine feste Baudrate.

## Bauen und flashen

```bash
pio run -d tools/ground/bridge_pico                # bauen (läuft auch in der CI)
pio run -d tools/ground/bridge_pico -t upload      # flashen; beim ersten Mal BOOTSEL gedrückt halten und einstecken
```

Protokoll (`Telemetry.h`), Konfiguration (`Config.h`) und E22-Register (`E22Config.h`) kommen direkt aus `firmware/src/`.
Nicht am Gerät getestet; die Registerlage folgt dem Ebyte-Handbuch des E22-400T22S und ist vor dem ersten Einsatz mit dem
Datenblatt der gelieferten Version abzugleichen.
