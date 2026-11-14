#include "minitest.h"
#include "LogRing.h"

static uint8_t mem[10 * 4];

static void fill_and_drain_in_order() {
  LogRing r; r.attach(mem, sizeof mem, 4);
  for (uint32_t i = 0; i < 7; ++i) CHECK(r.push(&i));
  CHECK_EQ(r.count(), 7);
  const uint8_t* p; uint32_t v;
  size_t k = r.peek(&p, 3);
  CHECK_EQ(k, 3);
  memcpy(&v, p, 4); CHECK_EQ(v, 0);
  r.consume(3);
  k = r.peek(&p, 100);
  CHECK_EQ(k, 4);
  memcpy(&v, p, 4); CHECK_EQ(v, 3);
}

static void full_keep_mode_drops_newest() {
  LogRing r; r.attach(mem, sizeof mem, 4);
  for (uint32_t i = 0; i < 12; ++i) r.push(&i);
  CHECK_EQ(r.count(), 10);
  CHECK_EQ(r.dropped(), 2);
  const uint8_t* p; uint32_t v;
  r.peek(&p, 1); memcpy(&v, p, 4);
  CHECK_EQ(v, 0);                      // Flugbeginn bleibt erhalten
}

static void full_overwrite_mode_drops_oldest() {
  LogRing r; r.attach(mem, sizeof mem, 4); r.setOverwrite(true);
  for (uint32_t i = 0; i < 13; ++i) r.push(&i);
  CHECK_EQ(r.count(), 10);
  CHECK_EQ(r.overwritten(), 3);
  const uint8_t* p; uint32_t v;
  r.peek(&p, 1); memcpy(&v, p, 4);
  CHECK_EQ(v, 3);
}

static void peek_stops_at_wrap() {
  LogRing r; r.attach(mem, sizeof mem, 4);
  for (uint32_t i = 0; i < 8; ++i) r.push(&i);
  r.consume(8);
  for (uint32_t i = 0; i < 5; ++i) r.push(&i);   // liegt über das Pufferende: 2 + 3
  const uint8_t* p;
  CHECK_EQ(r.peek(&p, 100), 2);
  r.consume(2);
  CHECK_EQ(r.peek(&p, 100), 3);
}

// Vorlauf an der Rampe: im Überschreib-Modus bleiben höchstens `limit` Sätze, der Rest ist frei.
// Nach dem Umschalten beim Start passt der ganze Flug hinein und der Vorlauf bleibt davor stehen.
static void preroll_limit_leaves_room_for_the_flight() {
  LogRing r; r.attach(mem, sizeof mem, 4);
  r.setOverwrite(true); r.setOverwriteLimit(3);
  for (uint32_t i = 0; i < 100; ++i) CHECK(r.push(&i));       // lange an der Rampe
  CHECK_EQ(r.count(), 3);
  CHECK_EQ(r.overwritten(), 97);
  r.setOverwrite(false);                                      // Start
  for (uint32_t i = 100; i < 107; ++i) CHECK(r.push(&i));     // sieben Sätze Flug: alle passen
  CHECK_EQ(r.count(), 10);
  CHECK_EQ(r.dropped(), 0);
  const uint8_t* p; uint32_t v;
  r.peek(&p, 1); memcpy(&v, p, 4);
  CHECK_EQ(v, 97);                                            // die letzten drei vor dem Start zuerst
}

static void preroll_limit_shrinks_a_backlog_and_ignores_bad_values() {
  LogRing r; r.attach(mem, sizeof mem, 4);
  for (uint32_t i = 0; i < 8; ++i) r.push(&i);                // Rückstand ohne Grenze
  r.setOverwrite(true); r.setOverwriteLimit(2);
  uint32_t x = 8; r.push(&x);
  CHECK_EQ(r.count(), 2);
  const uint8_t* p; uint32_t v;
  r.peek(&p, 1); memcpy(&v, p, 4);
  CHECK_EQ(v, 7);
  r.setOverwriteLimit(10);                                    // nicht kleiner als der Puffer: keine Grenze
  CHECK_EQ(r.overwriteLimit(), 0);
}

void run_tests_logring() {
  RUN_TEST(fill_and_drain_in_order);
  RUN_TEST(full_keep_mode_drops_newest);
  RUN_TEST(full_overwrite_mode_drops_oldest);
  RUN_TEST(peek_stops_at_wrap);
  RUN_TEST(preroll_limit_leaves_room_for_the_flight);
  RUN_TEST(preroll_limit_shrinks_a_backlog_and_ignores_bad_values);
}
