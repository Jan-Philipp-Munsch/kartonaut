#!/usr/bin/env bash
# Native Tests des Flugkerns ohne PlatformIO: baut lib/flightcore und
# test/test_flightcore mit g++ gegen den Unity-Shim und führt sie aus.
#
#   firmware/tools/run_native_tests.sh
#
# Mit PlatformIO ist `pio test -e native` der normale Weg (so läuft es in der CI);
# dieses Skript ist für Rechner ohne PlatformIO oder ohne Zugang zur Registry.
set -euo pipefail
cd "$(dirname "$0")/.."
out=".pio/native_shim"
mkdir -p "$out"
g++ -std=c++17 -O1 -g -Wall -Wextra -DUNITY_SHIM -DFLIGHTCORE_TEST_DATA_DIR="\"$PWD/test/data\"" \
    -Ilib/flightcore -Itest/unity_shim \
    lib/flightcore/*.cpp test/test_flightcore/*.cpp -o "$out/test_flightcore"
"$out/test_flightcore"
