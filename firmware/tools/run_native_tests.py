"""Native Tests ohne PlatformIO bauen und laufen lassen (g++ reicht).

    python firmware/tools/run_native_tests.py

Entspricht `pio test -e native`, nur ohne Registry und Plattform-Download.
"""
import glob
import os
import subprocess
import sys
import tempfile

FW = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PURE = ["Attitude.cpp", "FlightState.cpp", "Pyro.cpp", "Telemetry.cpp", "ControlLaw.cpp", "StateMemory.cpp", "LandingBurn.cpp", "ThrottleLaw.cpp",
        "Sha256.cpp", "LaunchAuth.cpp", "LaunchControl.cpp"]


def main():
    src = [os.path.join(FW, "src", f) for f in PURE] + sorted(glob.glob(os.path.join(FW, "test", "test_native", "*.cpp")))
    exe = os.path.join(tempfile.mkdtemp(), "native_tests")
    cmd = ["g++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-DNATIVE_TEST", "-I", os.path.join(FW, "src"),
           "-I", os.path.join(FW, "test", "test_native"), *src, "-o", exe, "-lm"]
    subprocess.run(cmd, check=True)
    return subprocess.run([exe], cwd=FW).returncode


if __name__ == "__main__":
    sys.exit(main())
