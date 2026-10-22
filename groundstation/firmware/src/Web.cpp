#include "Web.h"
#include "Config.h"
#include "Launch.h"
#include "Igniter.h"
#include "Radio.h"
#include "Protocol.h"

#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>

// Eingebettet über board_build.embed_txtfiles (platformio.ini)
extern const char index_html_start[] asm("_binary_src_index_html_start");

namespace web {

static AsyncWebServer server(80);
static AsyncWebSocket ws("/ws");

enum Action : uint8_t { A_HB, A_COUNTDOWN, A_ABORT, A_CALIBRATE, A_PING, A_PADQ, A_DISCONNECT };
struct Item { uint32_t client; Action a; };
static constexpr int QLEN = 16;
static Item q[QLEN];
static int qHead = 0, qTail = 0;
static portMUX_TYPE qMux = portMUX_INITIALIZER_UNLOCKED;

static void push(uint32_t client, Action a) {
  portENTER_CRITICAL(&qMux);
  int next = (qTail + 1) % QLEN;
  if (next != qHead) { q[qTail] = {client, a}; qTail = next; }
  else if (a == A_ABORT || a == A_DISCONNECT) { q[(qTail + QLEN - 1) % QLEN] = {client, a}; }  // nie verwerfen
  portEXIT_CRITICAL(&qMux);
}

static bool pop(Item& it) {
  bool ok = false;
  portENTER_CRITICAL(&qMux);
  if (qHead != qTail) { it = q[qHead]; qHead = (qHead + 1) % QLEN; ok = true; }
  portEXIT_CRITICAL(&qMux);
  return ok;
}

static void onWsMessage(AsyncWebSocketClient* c, uint8_t* data, size_t len) {
  JsonDocument doc;
  if (deserializeJson(doc, data, len)) return;
  const char* cmd = doc["cmd"] | "";
  uint32_t id = c->id();
  if      (!strcmp(cmd, "hb"))              push(id, A_HB);
  else if (!strcmp(cmd, "abort"))           push(id, A_ABORT);
  else if (!strcmp(cmd, "countdown"))       push(id, A_COUNTDOWN);
  else if (!strcmp(cmd, "calibrate"))       push(id, A_CALIBRATE);
  else if (!strcmp(cmd, "ping"))            push(id, A_PING);
  else if (!strcmp(cmd, "pad_ready_query")) push(id, A_PADQ);
}

static void onWsEvent(AsyncWebSocket*, AsyncWebSocketClient* c, AwsEventType type,
                      void* arg, uint8_t* data, size_t len) {
  switch (type) {
    case WS_EVT_CONNECT:
      Serial.printf("[WEB] Handy %u verbunden\n", c->id());
      break;
    case WS_EVT_DISCONNECT:
      push(c->id(), A_DISCONNECT);
      break;
    case WS_EVT_DATA: {
      auto* info = static_cast<AwsFrameInfo*>(arg);
      if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT)
        onWsMessage(c, data, len);
      break;
    }
    default:
      break;
  }
}

void begin() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_PASSWORD, WIFI_CHANNEL, 0, WIFI_MAX_CLIENTS);
  WiFi.setSleep(false);
  Serial.printf("[WEB] WLAN %s, http://%s\n", WIFI_SSID, WiFi.softAPIP().toString().c_str());

  ws.onEvent(onWsEvent);
  server.addHandler(&ws);
  server.on("/", HTTP_GET, [](AsyncWebServerRequest* r) {
    AsyncWebServerResponse* res = r->beginResponse(200, "text/html; charset=utf-8", index_html_start);
    res->addHeader("Cache-Control", "no-store");
    r->send(res);
  });
  server.onNotFound([](AsyncWebServerRequest* r) { r->redirect("/"); });
  server.begin();
}

void event(const char* msg) {
  if (!ws.count()) return;
  JsonDocument doc;
  doc["t"] = "ev";
  doc["ms"] = millis();
  doc["msg"] = msg;
  String s;
  serializeJson(doc, s);
  ws.textAll(s);
}

uint32_t clientCount() { return ws.count(); }

static void handle(const Item& it) {
  switch (it.a) {
    case A_HB:
      launch::phoneHeartbeat(it.client);
      break;
    case A_DISCONNECT:
      Serial.printf("[WEB] Handy %u getrennt\n", it.client);
      launch::phoneDisconnected(it.client);
      break;
    case A_ABORT:
      launch::abort("Abbruch am Handy");
      break;
    case A_COUNTDOWN:
      if (const char* r = launch::requestCountdown(launch::SRC_PHONE, it.client)) {
        String m = String("Countdown abgelehnt: ") + r;
        event(m.c_str());
      }
      break;
    case A_CALIBRATE:
      // Nicht während Countdown oder Zündung: die Rakete muss dann PAD_READY bleiben.
      if (launch::state() == launch::COUNTDOWN || launch::state() == launch::FIRING)
        event("Kalibrieren im Countdown gesperrt");
      else
        radio::send(proto::CMD_CALIBRATE);
      break;
    case A_PING:
      radio::send(proto::CMD_PING);
      break;
    case A_PADQ:
      radio::send(proto::CMD_PAD_READY_QUERY);
      break;
  }
}

static void pushState() {
  const auto& ig = igniter::status();
  const auto& il = launch::interlock();
  const auto& rs = radio::status();
  uint32_t age = radio::telemetryAgeMs();

  JsonDocument doc;
  doc["t"] = "st";
  doc["up"] = millis();

  JsonObject gs = doc["gs"].to<JsonObject>();
  gs["state"]  = launch::stateName(launch::state());
  gs["key"]    = ig.key;
  gs["arm"]    = ig.arm;
  gs["relay"]  = ig.relayClosed;
  gs["cont"]   = ig.continuity;
  gs["fire"]   = ig.firing;
  gs["vbat"]   = serialized(String(ig.vbatV, 2));
  gs["vpos"]   = serialized(String(ig.linePosV, 2));
  gs["vneg"]   = serialized(String(ig.lineNegV, 2));
  gs["fault"]  = ig.fault ? ig.fault : "";
  gs["reason"] = launch::lastReason();
  gs["cd"]     = launch::countdownRemainingMs();
  gs["hang"]   = launch::hangfireRemainingMs();
  gs["phones"] = ws.count();

  JsonObject lk = doc["lk"].to<JsonObject>();
  lk["c1"] = il.keyArm;
  lk["c2"] = il.continuity;
  lk["c3"] = il.rocketReady;
  lk["fresh"] = il.tlmFresh;
  lk["pad"] = il.padReady;
  lk["rarm"] = il.rocketArmed;
  lk["bat"] = il.battery;
  lk["ok"] = il.noFault;
  lk["all"] = il.all();

  JsonObject rf = doc["rf"].to<JsonObject>();
  rf["cfg"] = rs.configured;
  rf["rx"] = rs.frames;
  rf["crc"] = rs.crcErrors;
  rf["tx"] = rs.txFrames;

  JsonObject rk = doc["rk"].to<JsonObject>();
  rk["age"] = age == UINT32_MAX ? -1 : int32_t(age);
  if (rs.haveTelemetry) {
    const auto& t = rs.tlm;
    rk["state"] = proto::stateName(t.state);
    rk["t"] = t.t_ms;
    rk["alt"] = serialized(String(t.alt_m, 1));
    rk["vz"] = serialized(String(t.vz_ms, 2));
    JsonArray qa = rk["q"].to<JsonArray>();
    for (float v : t.q) qa.add(serialized(String(v, 4)));
    JsonArray ga = rk["gim"].to<JsonArray>();
    for (float v : t.gimbal_deg) ga.add(serialized(String(v, 2)));
    rk["v1"] = serialized(String(t.v1s, 2));
    rk["v2"] = serialized(String(t.v2s, 2));
    rk["arm"] = bool(t.flags & proto::F_ARMED);
    rk["p1"] = bool(t.flags & proto::F_PYRO1_CONT);
    rk["p2"] = bool(t.flags & proto::F_PYRO2_CONT);
    rk["log"] = bool(t.flags & proto::F_LOGGING);
    rk["cal"] = bool(t.flags & proto::F_CALIBRATED);
  }
  if (rs.lastGpsMs) {
    JsonObject g = rk["gps"].to<JsonObject>();
    g["lat"] = serialized(String(rs.gps.lat, 7));
    g["lon"] = serialized(String(rs.gps.lon, 7));
    g["alt"] = rs.gps.alt_m;
    g["sats"] = rs.gps.sats;
    g["fix"] = rs.gps.fix;
    g["age"] = millis() - rs.lastGpsMs;
  }

  String s;
  serializeJson(doc, s);
  ws.textAll(s);
}

void update() {
  Item it;
  while (pop(it)) handle(it);

  static uint32_t lastPush = 0, lastCleanup = 0;
  uint32_t now = millis();
  if (now - lastPush >= WS_PUSH_PERIOD_MS) {
    lastPush = now;
    if (ws.count()) pushState();
  }
  if (now - lastCleanup >= 1000) {
    lastCleanup = now;
    ws.cleanupClients(WIFI_MAX_CLIENTS);
  }
}

} // namespace web
