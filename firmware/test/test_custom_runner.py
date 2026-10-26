"""Eigener Test-Runner für `pio test -e native`: wie Unity, aber ohne die Unity-Bibliothek aus
der Registry. Die Tests benutzen test/test_native/minitest.h und geben Zeilen im Unity-Format
aus (datei:zeile:name:PASS|FAIL[:meldung]) sowie die Schlusszeile "N Tests M Failures 0 Ignored".
"""
from platformio.test.runners.unity import UnityTestRunner


class CustomTestRunner(UnityTestRunner):
    EXTRA_LIB_DEPS = []

    def configure_build_env(self, env):
        # kein unity_config.h, keine Unity-Quellen
        return env
