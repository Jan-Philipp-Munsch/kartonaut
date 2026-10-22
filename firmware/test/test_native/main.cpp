// Native Tests der Flug-Firmware: pio test -e native  (oder: python firmware/tools/run_native_tests.py)
#include "minitest.h"

void run_tests_attitude();
void run_tests_flightstate();
void run_tests_pyro();
void run_tests_telemetry();
void run_tests_statememory();
void run_tests_controllaw();
void run_tests_landing();
void run_tests_throttle();

int main() {
  run_tests_attitude();
  run_tests_flightstate();
  run_tests_pyro();
  run_tests_telemetry();
  run_tests_statememory();
  run_tests_controllaw();
  run_tests_landing();
  run_tests_throttle();
  return minitest::summary();
}
