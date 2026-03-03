#pragma once
#include <LittleFS.h>
#include <ArduinoJson.h>
#include "../util/Log.h"
#include "../config.h"

class Settings {
public:
  uint8_t brightness = DEFAULT_BRIGHTNESS;
  String mode = "clock_fun";
  bool gamma = true;
  int clockStyle = 0;
  bool clockBlink = true;
  String scrollText = "GODDARD DISPLAY";

  bool begin() {
    if (!LittleFS.begin(true)) {
      Log::err("Settings", "LittleFS mount failed");
      return false;
    }
    Log::info("Settings", "LittleFS mounted");
    return load();
  }

  bool load() {
    if (!LittleFS.exists(_path)) {
      Log::info("Settings", "No saved settings, using defaults");
      return true;
    }

    File f = LittleFS.open(_path, "r");
    if (!f) {
      Log::warn("Settings", "Could not open settings file");
      return false;
    }

    JsonDocument doc;
    if (deserializeJson(doc, f)) {
      Log::warn("Settings", "Settings file corrupt, using defaults");
      f.close();
      return false;
    }
    f.close();

    if (doc["brightness"].is<int>()) brightness = constrain(doc["brightness"].as<int>(), 0, 255);
    if (doc["mode"].is<const char*>()) mode = doc["mode"].as<const char*>();
    if (doc["gamma"].is<bool>()) gamma = doc["gamma"].as<bool>();
    if (doc["clockStyle"].is<int>()) clockStyle = doc["clockStyle"].as<int>();
    if (doc["clockBlink"].is<bool>()) clockBlink = doc["clockBlink"].as<bool>();
    if (doc["scrollText"].is<const char*>()) scrollText = doc["scrollText"].as<const char*>();

    Log::info("Settings", String("Loaded: mode=") + mode + " brightness=" + String(brightness));
    return true;
  }

  bool save() {
    File f = LittleFS.open(_path, "w");
    if (!f) {
      Log::err("Settings", "Could not write settings");
      return false;
    }

    JsonDocument doc;
    doc["brightness"] = brightness;
    doc["mode"] = mode;
    doc["gamma"] = gamma;
    doc["clockStyle"] = clockStyle;
    doc["clockBlink"] = clockBlink;
    doc["scrollText"] = scrollText;

    serializeJson(doc, f);
    f.close();
    Log::info("Settings", "Saved");
    return true;
  }

private:
  static constexpr const char* _path = "/settings.json";
};
