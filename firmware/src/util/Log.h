#pragma once
#include <Arduino.h>

namespace Log {
  inline void info(const char* tag, const String& msg) {
    Serial.printf("[I][%s] %s\n", tag, msg.c_str());
  }
  inline void warn(const char* tag, const String& msg) {
    Serial.printf("[W][%s] %s\n", tag, msg.c_str());
  }
  inline void err(const char* tag, const String& msg) {
    Serial.printf("[E][%s] %s\n", tag, msg.c_str());
  }
}
