#pragma once
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "../Controller.h"
#include "../render/Display.h"
#include "../util/Settings.h"

class ApiServer {
public:
  ApiServer(Controller& ctl, Display& disp, Settings& settings, bool& dirty)
    : _ctl(ctl), _disp(disp), _settings(settings), _dirty(dirty) {}

  void begin() {
    _server.reset(new AsyncWebServer(80));

    // --- REST endpoints ---

    _server->on("/api/status", HTTP_GET, [&](AsyncWebServerRequest *req){
      JsonDocument doc;
      doc["mode"] = _ctl.modeId();
      doc["brightness"] = _disp.brightness();
      doc["gamma"] = _disp.gammaEnabled();
      doc["heapFree"] = ESP.getFreeHeap();
      doc["uptimeMs"] = (uint32_t)millis();
      doc["firmware"] = "2.0.0";
      String out; serializeJson(doc, out);
      req->send(200, "application/json", out);
    });

    _server->on("/api/brightness", HTTP_POST, [&](AsyncWebServerRequest *req){}, nullptr,
      [&](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t, size_t){
        JsonDocument doc;
        if (deserializeJson(doc, data, len)) { req->send(400, "application/json", "{\"error\":\"bad json\"}"); return; }
        int b = doc["value"] | DEFAULT_BRIGHTNESS;
        b = constrain(b, 0, 255);
        _disp.setBrightness((uint8_t)b);
        _dirty = true;
        req->send(200, "application/json", "{\"ok\":true}");
      });

    _server->on("/api/mode", HTTP_POST, [&](AsyncWebServerRequest *req){}, nullptr,
      [&](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t, size_t){
        JsonDocument doc;
        if (deserializeJson(doc, data, len)) { req->send(400, "application/json", "{\"error\":\"bad json\"}"); return; }
        const char* mode = doc["mode"] | "";
        JsonVariantConst params = doc["params"];
        bool ok = _ctl.setMode(String(mode), params);
        if (!ok) {
          req->send(404, "application/json", "{\"error\":\"unknown mode\"}");
        } else {
          _dirty = true;
          req->send(200, "application/json", "{\"ok\":true}");
        }
      });

    _server->on("/api/params", HTTP_POST, [&](AsyncWebServerRequest *req){}, nullptr,
      [&](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t, size_t){
        JsonDocument doc;
        if (deserializeJson(doc, data, len)) { req->send(400, "application/json", "{\"error\":\"bad json\"}"); return; }
        _ctl.handleParams(doc["params"]);
        _dirty = true;
        req->send(200, "application/json", "{\"ok\":true}");
      });

    _server->on("/api/gamma", HTTP_POST, [&](AsyncWebServerRequest *req){}, nullptr,
      [&](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t, size_t){
        JsonDocument doc;
        if (deserializeJson(doc, data, len)) { req->send(400, "application/json", "{\"error\":\"bad json\"}"); return; }
        if (doc["enabled"].is<bool>()) {
          _disp.setGamma(doc["enabled"].as<bool>());
          _dirty = true;
        }
        req->send(200, "application/json", "{\"ok\":true}");
      });

    _server->on("/api/save", HTTP_POST, [&](AsyncWebServerRequest *req){
      _settings.brightness = _disp.brightness();
      _settings.mode = _ctl.modeId();
      _settings.gamma = _disp.gammaEnabled();
      bool ok = _settings.save();
      _dirty = false;
      if (ok) req->send(200, "application/json", "{\"ok\":true}");
      else req->send(500, "application/json", "{\"error\":\"save failed\"}");
    });

    // --- WebSockets ---

    _wsFrame.reset(new AsyncWebSocket(FRAME_WS_PATH));
    _wsEvents.reset(new AsyncWebSocket(EVENTS_WS_PATH));

    _wsFrame->onEvent([&](AsyncWebSocket* server, AsyncWebSocketClient* client, AwsEventType type,
                          void* arg, uint8_t* data, size_t len){
      (void)server; (void)client;
      if (type == WS_EVT_DATA) {
        AwsFrameInfo* info = (AwsFrameInfo*)arg;
        if (!info->final || info->index != 0) return;
        if (info->opcode != WS_BINARY) return;
        _handleFrameBinary(data, len);
      }
    });

    _wsEvents->onEvent([&](AsyncWebSocket* server, AsyncWebSocketClient* client, AwsEventType type,
                          void* arg, uint8_t* data, size_t len){
      (void)server; (void)client; (void)arg; (void)data; (void)len;
      if (type == WS_EVT_CONNECT) {
        JsonDocument doc;
        doc["event"] = "connect";
        doc["mode"] = _ctl.modeId();
        doc["brightness"] = _disp.brightness();
        doc["gamma"] = _disp.gammaEnabled();
        String out; serializeJson(doc, out);
        client->text(out);
      }
    });

    _server->addHandler(_wsFrame.get());
    _server->addHandler(_wsEvents.get());

    _server->begin();
  }

  void tickEvents(uint32_t nowMs){
    if (nowMs - _lastTelemetry > 1000){
      _lastTelemetry = nowMs;
      if (_wsEvents) {
        JsonDocument doc;
        doc["event"] = "telemetry";
        doc["heapFree"] = ESP.getFreeHeap();
        doc["uptimeMs"] = nowMs;
        doc["mode"] = _ctl.modeId();
        doc["brightness"] = _disp.brightness();
        String out; serializeJson(doc, out);
        _wsEvents->textAll(out);
      }
    }
  }

private:
  Controller& _ctl;
  Display& _disp;
  Settings& _settings;
  bool& _dirty;
  std::unique_ptr<AsyncWebServer> _server;
  std::unique_ptr<AsyncWebSocket> _wsFrame;
  std::unique_ptr<AsyncWebSocket> _wsEvents;
  uint32_t _lastTelemetry = 0;

  void _handleFrameBinary(uint8_t* data, size_t len);
};
