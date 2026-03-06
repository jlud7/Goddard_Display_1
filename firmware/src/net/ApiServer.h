#pragma once
#include <sys/time.h>
#include <vector>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "../Controller.h"
#include "../render/Display.h"
#include "../util/Settings.h"
#include "Net.h"

class ApiServer {
public:
  ApiServer(Controller& ctl, Display& disp, Settings& settings, bool& dirty)
    : _ctl(ctl), _disp(disp), _settings(settings), _dirty(dirty) {}

  void begin() {
    _server.reset(new AsyncWebServer(80));

    // --- REST endpoints ---

    _server->on("/api/status", HTTP_GET, [&](AsyncWebServerRequest *req){
      JsonDocument doc;
      const time_t now = time(nullptr);
      doc["mode"] = _ctl.modeId();
      doc["brightness"] = _disp.brightness();
      doc["gamma"] = _disp.gammaEnabled();
      doc["heapFree"] = ESP.getFreeHeap();
      doc["uptimeMs"] = (uint32_t)millis();
      doc["firmware"] = "2.0.0";
      doc["epoch"] = (uint32_t)now;
      doc["timeSynced"] = now >= 1700000000;
      doc["ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "";
      doc["wifiRssi"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
      doc["framePackets"] = _framePackets;
      doc["frameBytes"] = _lastFrameBytes;
      doc["frameId"] = _lastFrameId;
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

    _server->on("/api/time", HTTP_POST, [&](AsyncWebServerRequest *req){}, nullptr,
      [&](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t, size_t){
        JsonDocument doc;
        if (deserializeJson(doc, data, len)) { req->send(400, "application/json", "{\"error\":\"bad json\"}"); return; }
        if (doc["timeZone"].is<const char*>()) {
          Net::applyTimeZone(doc["timeZone"].as<const char*>());
        }
        const time_t epoch = doc["epoch"] | 0;
        if (epoch > 1700000000) {
          timeval tv = {};
          tv.tv_sec = epoch;
          settimeofday(&tv, nullptr);
        }
        req->send(200, "application/json", "{\"ok\":true}");
      });

    _server->on("/api/frame", HTTP_POST, [&](AsyncWebServerRequest *req){}, nullptr,
      [&](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t index, size_t total){
        if (index == 0) {
          _httpFrameRxExpected = total;
          _httpFrameRxBuffer.clear();
          _httpFrameRxBuffer.reserve(total);
        }
        _httpFrameRxBuffer.insert(_httpFrameRxBuffer.end(), data, data + len);
        if ((index + len) < total) {
          return;
        }
        const bool ok = _httpFrameRxExpected == total
          && _httpFrameRxBuffer.size() == total
          && _handleFrameBinary(_httpFrameRxBuffer.data(), _httpFrameRxBuffer.size());
        _httpFrameRxBuffer.clear();
        _httpFrameRxExpected = 0;
        if (ok) {
          req->send(200, "application/json", "{\"ok\":true}");
        } else {
          req->send(400, "application/json", "{\"error\":\"invalid frame payload\"}");
        }
      });

    // --- WebSockets ---

    _wsFrame.reset(new AsyncWebSocket(FRAME_WS_PATH));
    _wsEvents.reset(new AsyncWebSocket(EVENTS_WS_PATH));

    _wsFrame->onEvent([&](AsyncWebSocket* server, AsyncWebSocketClient* client, AwsEventType type,
                          void* arg, uint8_t* data, size_t len){
      (void)server; (void)client;
      if (type == WS_EVT_DATA) {
        AwsFrameInfo* info = (AwsFrameInfo*)arg;
        if (info->index == 0) {
          if (info->opcode != WS_BINARY) return;
          _frameRxExpected = info->len;
          _frameRxBuffer.clear();
          _frameRxBuffer.reserve(info->len);
        }
        _frameRxBuffer.insert(_frameRxBuffer.end(), data, data + len);
        if (!info->final) return;
        if (_frameRxExpected == 0 || _frameRxBuffer.size() != _frameRxExpected) {
          _frameRxBuffer.clear();
          _frameRxExpected = 0;
          return;
        }
        _handleFrameBinary(_frameRxBuffer.data(), _frameRxBuffer.size());
        _frameRxBuffer.clear();
        _frameRxExpected = 0;
      }
    });

    _wsEvents->onEvent([&](AsyncWebSocket* server, AsyncWebSocketClient* client, AwsEventType type,
                          void* arg, uint8_t* data, size_t len){
      (void)server; (void)client; (void)arg; (void)data; (void)len;
      if (type == WS_EVT_CONNECT) {
        JsonDocument doc;
        const time_t now = time(nullptr);
        doc["event"] = "connect";
        doc["mode"] = _ctl.modeId();
        doc["brightness"] = _disp.brightness();
        doc["gamma"] = _disp.gammaEnabled();
        doc["epoch"] = (uint32_t)now;
        doc["timeSynced"] = now >= 1700000000;
        doc["ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "";
        doc["wifiRssi"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
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
        const time_t now = time(nullptr);
        doc["event"] = "telemetry";
        doc["heapFree"] = ESP.getFreeHeap();
        doc["uptimeMs"] = nowMs;
        doc["mode"] = _ctl.modeId();
        doc["brightness"] = _disp.brightness();
        doc["epoch"] = (uint32_t)now;
        doc["timeSynced"] = now >= 1700000000;
        doc["wifiRssi"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
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
  std::vector<uint8_t> _frameRxBuffer;
  size_t _frameRxExpected = 0;
  std::vector<uint8_t> _httpFrameRxBuffer;
  size_t _httpFrameRxExpected = 0;
  uint32_t _framePackets = 0;
  uint32_t _lastFrameBytes = 0;
  uint16_t _lastFrameId = 0;

  bool _handleFrameBinary(uint8_t* data, size_t len);
};
