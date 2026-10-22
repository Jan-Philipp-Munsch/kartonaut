#include "minitest.h"
#include "Telemetry.h"
#include "Crc16.h"
#include <string.h>

static void crc16_check_value() {
  const char* s = "123456789";
  CHECK_EQ(crc16_ccitt((const uint8_t*)s, 9), 0x29B1);
  // stückweise identisch
  uint16_t c = crc16_ccitt((const uint8_t*)s, 4);
  CHECK_EQ(crc16_ccitt((const uint8_t*)s + 4, 5, c), 0x29B1);
}

static void encode_decode_roundtrip() {
  tlm::TlmPayload p{};
  p.state = 2; p.flags = tlm::FLAG_ARMED | tlm::FLAG_CONT1; p.t_ds = 123; p.alt_dm = -45; p.vz_cms = 1234;
  p.tilt_x_hd = -7; p.tilt_y_hd = 9; p.roll_2d = 45; p.tvc_y_dd = -30; p.tvc_p_dd = 12; p.vbat1_20mv = 205;
  p.vbat2_50mv = 160; p.seq = 77;
  uint8_t frame[64];
  const size_t n = tlm::encode(tlm::TLM, (const uint8_t*)&p, sizeof p, frame, sizeof frame);
  CHECK_EQ(n, sizeof(p) + tlm::OVERHEAD);
  CHECK_EQ(n, 22);
  CHECK_EQ(frame[0], 0xA5); CHECK_EQ(frame[1], 0x5A); CHECK_EQ(frame[2], tlm::TLM); CHECK_EQ(frame[3], 16);

  tlm::Parser rx;
  bool got = false;
  for (size_t i = 0; i < n; ++i) got = rx.feed(frame[i]) || got;
  CHECK(got);
  CHECK_EQ(rx.type(), tlm::TLM);
  CHECK_EQ(rx.length(), 16);
  tlm::TlmPayload q; memcpy(&q, rx.payload(), sizeof q);
  CHECK_EQ(q.alt_dm, -45); CHECK_EQ(q.vz_cms, 1234); CHECK_EQ(q.seq, 77); CHECK_EQ(q.flags, p.flags);
  CHECK_EQ(rx.badFrames(), 0);
}

static void parser_rejects_corruption_and_resyncs() {
  tlm::CmdPayload c{9};
  uint8_t frame[16];
  const size_t n = tlm::encode(tlm::CMD_ABORT, (const uint8_t*)&c, 1, frame, sizeof frame);
  CHECK_EQ(n, 7);
  tlm::Parser rx;
  // Müll, dann ein Rahmen mit Bitfehler, dann ein guter
  const uint8_t junk[] = {0x00, 0xA5, 0x13, 0xA5, 0xA5, 0x5A, 0x20, 0x01};
  for (uint8_t b : junk) CHECK(!rx.feed(b));
  uint8_t bad[16]; memcpy(bad, frame, n); bad[4] ^= 0x01;
  bool got = false;
  for (size_t i = 0; i < n; ++i) got = rx.feed(bad[i]) || got;
  CHECK(!got);
  CHECK(rx.badFrames() >= 1);
  for (size_t i = 0; i < n; ++i) got = rx.feed(frame[i]) || got;
  CHECK(got);
  CHECK_EQ(rx.type(), tlm::CMD_ABORT);
  CHECK_EQ(rx.payload()[0], 9);
}

static void length_limits() {
  uint8_t big[80] = {0};
  uint8_t out[128];
  CHECK_EQ(tlm::encode(tlm::GPS, big, 65, out, sizeof out), 0);
  CHECK_EQ(tlm::encode(tlm::GPS, big, 64, out, sizeof out), 70);
  CHECK_EQ(tlm::encode(tlm::GPS, big, 10, out, 12), 0);    // Ausgabepuffer zu klein
  CHECK_EQ(tlm::encode(tlm::ACK, nullptr, 0, out, sizeof out), 6);
  tlm::Parser rx;
  for (size_t i = 0; i < 6; ++i) rx.feed(out[i]);
  CHECK_EQ(rx.length(), 0);
}

static void scaling_helpers() {
  CHECK_EQ(tlm::clamp_i8(200.f), 127);
  CHECK_EQ(tlm::clamp_i8(-200.f), -128);
  CHECK_EQ(tlm::clamp_i8(-2.4f), -2);
  CHECK_EQ(tlm::clamp_i8(2.6f), 3);
  CHECK_EQ(tlm::clamp_i16(40000.f), 32767);
  CHECK_EQ(tlm::clamp_u8(-1.f), 0);
  CHECK_EQ(tlm::clamp_u8(4.1f / 0.02f), 205);
}

void run_tests_telemetry() {
  RUN_TEST(crc16_check_value);
  RUN_TEST(encode_decode_roundtrip);
  RUN_TEST(parser_rejects_corruption_and_resyncs);
  RUN_TEST(length_limits);
  RUN_TEST(scaling_helpers);
}
