#include <Arduino.h>
#include "config.h"
#include "util/Log.h"
#include "util/Settings.h"
#include "render/Display.h"
#include "Controller.h"
#include "net/Net.h"
#include "net/ApiServer.h"

static Display display;
static Controller controller;
static Settings settings;
static ApiServer* api = nullptr;

static uint32_t lastTick = 0;
static uint32_t lastSave = 0;
static bool settingsDirty = false;
static bool wifiReady = false;

void setup() {
  Serial.begin(115200);
  delay(200);

  Log::info("Boot", "Goddard Display starting");

  settings.begin();

  if (!display.begin()) {
    Log::err("Boot", "Display init failed; check HUB75 pins in config.h");
    while(true) delay(1000);
  }

  display.playBootAnimation();
  Log::info("Boot", "Boot animation complete");

  // Restore saved settings
  display.setBrightness(settings.brightness);
  display.setGamma(settings.gamma);

  controller.begin();

  // Restore saved mode
  JsonDocument initDoc;
  if (settings.mode == "clock_fun") {
    initDoc["style"] = settings.clockStyle;
    initDoc["blink"] = settings.clockBlink;
  } else if (settings.mode == "text_scroll") {
    initDoc["text"] = settings.scrollText;
  }
  controller.setMode(settings.mode, initDoc.as<JsonVariantConst>());

  // WiFi is optional — effects run offline if WiFi fails
  wifiReady = Net::setupWifi();
  if (wifiReady) {
    Net::setupMDNS();
    Net::setupTime();

    api = new ApiServer(controller, display, settings, settingsDirty);
    api->begin();
  } else {
    Log::warn("Boot", "WiFi failed — running in offline mode. Will retry in loop.");
  }

  lastTick = millis();
  lastSave = millis();

  Log::info("Boot", "Ready");
}

void loop() {
  uint32_t now = millis();
  uint32_t dt = now - lastTick;
  lastTick = now;

  controller.tick(dt);
  controller.render(display.back());
  display.swapAndShow();

  if (api) api->tickEvents(now);

  // If WiFi wasn't ready at boot, retry periodically
  if (!wifiReady) {
    Net::checkConnection();
    if (WiFi.status() == WL_CONNECTED) {
      wifiReady = true;
      Log::info("Boot", "WiFi connected late — starting network services");
      Net::setupMDNS();
      Net::setupTime();
      api = new ApiServer(controller, display, settings, settingsDirty);
      api->begin();
    }
  } else {
    Net::checkConnection();
  }

  // Auto-save settings every 30s if dirty
  if (settingsDirty && (now - lastSave > 30000)) {
    settings.brightness = display.brightness();
    settings.mode = controller.modeId();
    settings.gamma = display.gammaEnabled();
    settings.save();
    settingsDirty = false;
    lastSave = now;
  }

  delay(1);
}
