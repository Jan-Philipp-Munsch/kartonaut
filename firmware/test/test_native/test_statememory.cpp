#include "minitest.h"
#include "StateMemory.h"
#include <string.h>

static void seal_and_validate() {
  SavedState s; memset(&s, 0, sizeof s);
  s.state = 3; s.t_launch_ms = 12345; s.q[0] = 1.0f; s.ground_p_pa = 101325.f;
  CHECK(!savedStateValid(s));
  savedStateSeal(s);
  CHECK(savedStateValid(s));
  CHECK_EQ(s.magic, SAVED_MAGIC);
  s.t_launch_ms++;
  CHECK(!savedStateValid(s));
  savedStateSeal(s);
  s.version = 99;
  CHECK(!savedStateValid(s));
}

static void random_memory_is_rejected() {
  SavedState s;
  uint8_t* p = reinterpret_cast<uint8_t*>(&s);
  uint32_t x = 0x12345678;
  for (size_t i = 0; i < sizeof s; ++i) { x = x * 1664525u + 1013904223u; p[i] = (uint8_t)(x >> 24); }
  CHECK(!savedStateValid(s));
  memset(&s, 0xFF, sizeof s);
  CHECK(!savedStateValid(s));
  memset(&s, 0x00, sizeof s);
  CHECK(!savedStateValid(s));
}

void run_tests_statememory() {
  RUN_TEST(seal_and_validate);
  RUN_TEST(random_memory_is_rejected);
}
