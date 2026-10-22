#pragma once
// minitest.h – winziges Testgerüst mit Ausgabe im Unity-Format, damit `pio test -e native`
// die Ergebnisse versteht (test/test_custom_runner.py). Kein Arduino.
#include <stdio.h>
#include <math.h>
#include <string.h>

namespace minitest {
inline int& passed() { static int n = 0; return n; }
inline int& failed() { static int n = 0; return n; }
inline const char*& current() { static const char* c = ""; return c; }
inline bool& current_failed() { static bool f = false; return f; }

inline void begin(const char* name) { current() = name; current_failed() = false; }
inline void end(const char* file, int line) {
  if (current_failed()) failed()++; else { passed()++; printf("%s:%d:%s:PASS\n", file, line, current()); }
}
inline void fail(const char* file, int line, const char* msg) {
  if (!current_failed()) printf("%s:%d:%s:FAIL: %s\n", file, line, current(), msg);
  current_failed() = true;
}
inline int summary() {
  printf("\n-----------------------\n%d Tests %d Failures 0 Ignored\n%s\n", passed() + failed(), failed(),
         failed() ? "FAIL" : "OK");
  return failed() ? 1 : 0;
}
}  // namespace minitest

#define TEST(name) \
  static void name(); \
  struct name##_reg { name##_reg() { minitest::begin(#name); name(); minitest::end(__FILE__, __LINE__); } }; \
  static void name()
#define RUN_TEST(name) do { minitest::begin(#name); name(); minitest::end(__FILE__, __LINE__); } while (0)

#define CHECK(cond) do { if (!(cond)) { char _m[256]; snprintf(_m, sizeof _m, "%s", #cond); minitest::fail(__FILE__, __LINE__, _m); } } while (0)
#define CHECK_MSG(cond, ...) do { if (!(cond)) { char _m[256]; snprintf(_m, sizeof _m, __VA_ARGS__); minitest::fail(__FILE__, __LINE__, _m); } } while (0)
#define CHECK_EQ(a, b) do { auto _a = (a); auto _b = (b); if (!((long)_a == (long)_b)) { char _m[256]; snprintf(_m, sizeof _m, "%s == %s: %ld != %ld", #a, #b, (long)_a, (long)_b); minitest::fail(__FILE__, __LINE__, _m); } } while (0)
#define CHECK_NEAR(a, b, tol) do { double _a = (a), _b = (b); if (!(fabs(_a - _b) <= (tol))) { char _m[256]; snprintf(_m, sizeof _m, "%s ~ %s: %g != %g (tol %g)", #a, #b, _a, _b, (double)(tol)); minitest::fail(__FILE__, __LINE__, _m); } } while (0)
