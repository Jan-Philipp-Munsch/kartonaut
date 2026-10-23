#include "Proto.h"
#include <stdarg.h>
#include <string.h>
#include <ctype.h>

namespace proto {

const char* name(Res r) { return r == Res::OK ? "OK" : r == Res::FEHL ? "FEHL" : "SKIP"; }

Res worst(Res a, Res b) {
  if (a == Res::FEHL || b == Res::FEHL) return Res::FEHL;
  if (a == Res::SKIP || b == Res::SKIP) return Res::SKIP;
  return Res::OK;
}

static void vline(const char* prefix, const char* fmt, va_list ap) {
  char buf[200];
  vsnprintf(buf, sizeof buf, fmt, ap);
  Serial.print(prefix);
  Serial.println(buf);
}

void ready() { Serial.println("READY"); }

void comment(const char* fmt, ...) { va_list ap; va_start(ap, fmt); vline("# ", fmt, ap); va_end(ap); }
void info(const char* fmt, ...)    { va_list ap; va_start(ap, fmt); vline("INFO ", fmt, ap); va_end(ap); }

void test(const char* n, Res r, const char* fmt, ...) {
  char buf[200];
  va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
  Serial.printf("TEST %s %s %s\n", n, name(r), buf);
}

void test(const char* n, bool ok, const char* fmt, ...) {
  char buf[200];
  va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
  Serial.printf("TEST %s %s %s\n", n, ok ? "OK" : "FEHL", buf);
}

void cal(const char* n, const char* fmt, ...) {
  char buf[240];
  va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
  Serial.printf("CAL %s %s\n", n, buf);
}

void end(const char* cmd, Res r) { Serial.printf("END %s %s\n", cmd, name(r)); }

void flushInput() { while (Serial.available()) Serial.read(); }

bool readLine(char* buf, size_t n, uint32_t timeout_ms) {
  size_t len = 0;
  const uint32_t t0 = millis();
  for (;;) {
    if (timeout_ms && millis() - t0 > timeout_ms) return false;
    if (!Serial.available()) continue;
    const int c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') break;
    if (len + 1 < n) buf[len++] = char(c);
  }
  buf[len] = 0;
  // trimmen
  char* s = buf;
  while (*s && isspace(uint8_t(*s))) ++s;
  if (s != buf) memmove(buf, s, strlen(s) + 1);
  for (char* e = buf + strlen(buf); e > buf && isspace(uint8_t(e[-1])); --e) e[-1] = 0;
  return true;
}

int wait(const char* fmt, ...) {
  va_list ap; va_start(ap, fmt); vline("WAIT ", fmt, ap); va_end(ap);
  flushInput();
  char line[32];
  readLine(line, sizeof line);
  if (line[0] == 0 || line[0] == 'j' || line[0] == 'J' || line[0] == 'y') return 1;
  if (line[0] == 'n' || line[0] == 'N') return 0;
  return -1;
}

bool ask(float& value, const char* fmt, ...) {
  va_list ap; va_start(ap, fmt); vline("ASK ", fmt, ap); va_end(ap);
  flushInput();
  char line[32];
  readLine(line, sizeof line);
  if (line[0] == 0 || line[0] == 'q') return false;
  for (char* c = line; *c; ++c) if (*c == ',') *c = '.';
  char* endp = nullptr;
  value = strtof(line, &endp);
  return endp != line;
}

bool confirm(const char* fmt, ...) {
  va_list ap; va_start(ap, fmt); vline("CONFIRM ", fmt, ap); va_end(ap);
  flushInput();
  char line[32];
  readLine(line, sizeof line, 60000);
  return strcmp(line, "JA") == 0;
}

bool abortRequested() {
  while (Serial.available()) {
    const int c = Serial.read();
    if (c == 'q' || c == 'Q') { flushInput(); return true; }
  }
  return false;
}

}  // namespace proto
