// Feste Bytefolgen des Funkprotokolls (Plan Bordzündung §6): test/data/radio_vectors.csv enthält je Zeile
// Name und Rahmen in Hex. Dieser Test baut die Rahmen mit der Firmware und vergleicht; das Laptop-Werkzeug
// prüft dieselbe Datei mit Python (tools/ground/test_kartonaut_radio.py), beide Seiten sprechen also
// nachweislich dasselbe Protokoll. Eingaben (hier und in Python gleich):
//   Schlüssel 00 01 .. 0f, Raketen-ID 1
#include "minitest.h"
#include "Telemetry.h"
#include "LaunchAuth.h"
#include "E22Config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t VKEY[16] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};

struct Vec { const char* name; uint8_t frame[80]; size_t n; };

static Vec make(const char* name, uint8_t type, const void* p, size_t n) {
  Vec v{name, {0}, 0};
  v.n = tlm::encode(type, (const uint8_t*)p, n, v.frame, sizeof v.frame);
  return v;
}

static Vec auth_cmd(const char* name, uint8_t type, uint8_t seq, uint32_t nonce) {
  tlm::CmdAuthPayload c{};
  c.seq = seq;
  launch_auth::computeMac(VKEY, type, seq, nonce, 1, c.mac);
  return make(name, type, &c, sizeof c);
}

static int build(Vec* out) {
  int n = 0;
  out[n++] = auth_cmd("cmd_arm", tlm::CMD_ARM, 7, 0x12345678);
  out[n++] = auth_cmd("cmd_launch", tlm::CMD_LAUNCH, 8, 0xCAFEBABE);
  { tlm::CmdPayload c{9};  out[n++] = make("cmd_heartbeat", tlm::CMD_HEARTBEAT, &c, 1); }
  { tlm::CmdPayload c{10}; out[n++] = make("cmd_abort", tlm::CMD_ABORT, &c, 1); }
  { tlm::CmdPayload c{11}; out[n++] = make("cmd_ping", tlm::CMD_PING, &c, 1); }
  { tlm::AckAuthPayload a{tlm::CMD_PING, 11, tlm::ACK_OK, 1, 0x12345678, 0x5F, 0};
    out[n++] = make("ack_ping", tlm::ACK, &a, sizeof a); }
  { tlm::AckAuthPayload a{tlm::CMD_ARM, 7, tlm::ACK_OK, 9, 0xCAFEBABE, 0x7F, 0};
    out[n++] = make("ack_arm", tlm::ACK, &a, sizeof a); }
  { tlm::AckAuthPayload a{tlm::CMD_LAUNCH, 8, tlm::ACK_OK, 10, 0, 0x7F, 5000};
    out[n++] = make("ack_launch", tlm::ACK, &a, sizeof a); }
  { tlm::AckPayload a{tlm::CMD_SAFE, 12, tlm::ACK_REFUSED, 12};
    out[n++] = make("ack_safe", tlm::ACK, &a, sizeof a); }
  { tlm::EvtPayload e{1234, 10, 11, 19};
    out[n++] = make("evt_ignition", tlm::EVT, &e, sizeof e); }
  { tlm::IgnPayload g{10, 50, 130, 50, 7800, 6912, 3900, 80, tlm::IGN_END_CONT_LOST};
    out[n++] = make("ign", tlm::IGN, &g, sizeof g); }
  { tlm::TlmPayload p{};
    p.state = 9; p.flags = tlm::FLAG_ARMED | tlm::FLAG_CONT1 | tlm::FLAG_LOGGING; p.t_ds = 4321; p.alt_dm = -12;
    p.vz_cms = 3; p.tilt_x_hd = -4; p.tilt_y_hd = 6; p.roll_2d = 90 / 2; p.tvc_y_dd = 0; p.tvc_p_dd = -1;
    p.vbat1_20mv = 200; p.vbat2_50mv = 160; p.seq = 33;
    out[n++] = make("tlm_armed", tlm::TLM, &p, sizeof p); }
  return n;
}

static void tohex(const uint8_t* d, size_t n, char* out) {
  for (size_t i = 0; i < n; ++i) snprintf(out + 2 * i, 3, "%02x", d[i]);
  out[2 * n] = 0;
}

static void radio_vectors_match_shared_file() {
  Vec v[16];
  const int n = build(v);
  if (getenv("KARTONAUT_PRINT_VECTORS")) {
    printf("# name,hex\n");
    for (int i = 0; i < n; ++i) { char h[200]; tohex(v[i].frame, v[i].n, h); printf("%s,%s\n", v[i].name, h); }
  }
  FILE* f = fopen("test/data/radio_vectors.csv", "r");
  if (!f) f = fopen("firmware/test/data/radio_vectors.csv", "r");
  CHECK_MSG(f != nullptr, "test/data/radio_vectors.csv fehlt");
  if (!f) return;
  char line[256];
  int found = 0;
  while (fgets(line, sizeof line, f)) {
    if (line[0] == '#' || line[0] == '\n') continue;
    char* comma = strchr(line, ',');
    if (!comma) continue;
    *comma = 0;
    char* h = comma + 1;
    h[strcspn(h, "\r\n")] = 0;
    for (int i = 0; i < n; ++i) {
      if (strcmp(v[i].name, line) != 0) continue;
      char mine[200]; tohex(v[i].frame, v[i].n, mine);
      if (strcmp(mine, h) != 0) printf("%s\n  Firmware %s\n  Datei    %s\n", line, mine, h);
      CHECK_MSG(strcmp(mine, h) == 0, "Vektor %.40s weicht ab", line);
      ++found;
    }
  }
  fclose(f);
  CHECK_EQ(found, n);
}

static void parser_reads_vectors_back() {
  Vec v[16];
  const int n = build(v);
  tlm::Parser rx;
  int got = 0;
  for (int i = 0; i < n; ++i)
    for (size_t k = 0; k < v[i].n; ++k)
      if (rx.feed(v[i].frame[k])) ++got;
  CHECK_EQ(got, n);
  CHECK_EQ(rx.badFrames(), 0);
}

// E22-Register aus Config.h; tools/ground/test_kartonaut_radio.py erwartet dieselben Bytes
static void e22_registers_from_config() {
  uint8_t r[e22::REG_COUNT];
  e22::wantedRegs(r, false);
  const uint8_t want[e22::REG_COUNT] = {0x00, 0x00, 0x00, 0x64, 0x03, 0x17, 0x03, 0x00, 0x00};
  CHECK(memcmp(r, want, sizeof want) == 0);
  e22::wantedRegs(r, true);
  CHECK_EQ(r[6], 0x83);
}

void run_tests_radio_vectors() {
  RUN_TEST(e22_registers_from_config);
  RUN_TEST(radio_vectors_match_shared_file);
  RUN_TEST(parser_reads_vectors_back);
}
