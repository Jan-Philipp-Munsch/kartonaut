#pragma once
// unity.h (Shim) – Ersatz für ThrowTheSwitch/Unity, wenn die Tests ohne PlatformIO
// direkt mit g++ laufen (tools/run_native_tests.sh). Nur die Makros, die
// test_flightcore benutzt. In der CI nimmt `pio test -e native` das echte Unity;
// dieser Ordner liegt dort nicht im Include-Pfad.
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int unity_tests = 0, unity_failures = 0, unity_test_failed = 0;
static const char* unity_current = "";

#define UNITY_BEGIN() (unity_tests = 0, unity_failures = 0, 0)
#define UNITY_END() (printf("\n%d Tests, %d Fehler\n", unity_tests, unity_failures), unity_failures ? 1 : 0)
#define RUN_TEST(fn) do { unity_current = #fn; unity_test_failed = 0; ++unity_tests; fn(); \
  printf("%s: %s\n", unity_test_failed ? "FAIL" : "ok  ", #fn); if (unity_test_failed) ++unity_failures; } while (0)

#define UNITY_FAIL_(msg) do { printf("  %s:%d: %s: %s\n", __FILE__, __LINE__, unity_current, msg); unity_test_failed = 1; } while (0)

#define TEST_ASSERT(c)              do { if (!(c)) UNITY_FAIL_("TEST_ASSERT(" #c ")"); } while (0)
#define TEST_ASSERT_TRUE(c)         TEST_ASSERT(c)
#define TEST_ASSERT_FALSE(c)        TEST_ASSERT(!(c))
#define TEST_ASSERT_EQUAL(a, b)     do { if (!((a) == (b))) { char m_[160]; snprintf(m_, sizeof m_, "erwartet %ld, ist %ld (" #a " == " #b ")", (long)(a), (long)(b)); UNITY_FAIL_(m_); } } while (0)
#define TEST_ASSERT_EQUAL_INT(a, b) TEST_ASSERT_EQUAL(a, b)
#define TEST_ASSERT_EQUAL_UINT8(a, b) TEST_ASSERT_EQUAL(a, b)
#define TEST_ASSERT_EQUAL_UINT16(a, b) TEST_ASSERT_EQUAL(a, b)
#define TEST_ASSERT_EQUAL_HEX16(a, b) do { if (!((a) == (b))) { char m_[160]; snprintf(m_, sizeof m_, "erwartet 0x%04X, ist 0x%04X", (unsigned)(a), (unsigned)(b)); UNITY_FAIL_(m_); } } while (0)
#define TEST_ASSERT_FLOAT_WITHIN(d, a, b) do { if (!(fabs((double)(a) - (double)(b)) <= (double)(d))) { char m_[160]; snprintf(m_, sizeof m_, "erwartet %g ± %g, ist %g (" #b ")", (double)(a), (double)(d), (double)(b)); UNITY_FAIL_(m_); } } while (0)
#define TEST_ASSERT_GREATER_THAN(a, b) TEST_ASSERT((b) > (a))
#define TEST_ASSERT_LESS_THAN(a, b)    TEST_ASSERT((b) < (a))
#define TEST_ASSERT_EQUAL_MEMORY(a, b, n) do { if (memcmp((a), (b), (n)) != 0) UNITY_FAIL_("Speicher verschieden"); } while (0)
#define TEST_ASSERT_EQUAL_STRING(a, b) do { if (strcmp((a), (b)) != 0) UNITY_FAIL_("Strings verschieden"); } while (0)
#define TEST_FAIL_MESSAGE(m) UNITY_FAIL_(m)
#define TEST_MESSAGE(m) printf("  %s\n", m)
