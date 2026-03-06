#pragma once
#include <sys/time.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <time.h>
#include "../util/Log.h"
#include "../config.h"

namespace Net {
  static uint32_t _lastReconnectAttempt = 0;
  static bool _wasConnected = false;

  inline void applyTimeZone(const char* tz) {
    const char* value = (tz && tz[0]) ? tz : CONFIG_TZ_INFO;
    setenv("TZ", value, 1);
    tzset();
  }

  inline bool setupWifi() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);

    // Optional static IP
    IPAddress ip; ip.fromString(CONFIG_WIFI_STATIC_IP);
    if ((uint32_t)ip != 0) {
      IPAddress gw; gw.fromString(CONFIG_WIFI_GATEWAY);
      IPAddress sn; sn.fromString(CONFIG_WIFI_SUBNET);
      IPAddress dns; dns.fromString(CONFIG_WIFI_DNS);
      WiFi.config(ip, gw, sn, dns);
    }

    WiFi.begin(CONFIG_WIFI_SSID, CONFIG_WIFI_PASS);
    Log::info("WiFi", "Connecting...");
    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
      delay(200);
    }
    if (WiFi.status() != WL_CONNECTED) {
      Log::err("WiFi", "Failed to connect");
      return false;
    }
    Log::info("WiFi", String("Connected: ") + WiFi.localIP().toString());
    _wasConnected = true;
    return true;
  }

  inline void checkConnection() {
    uint32_t now = millis();
    if (WiFi.status() == WL_CONNECTED) {
      if (!_wasConnected) {
        Log::info("WiFi", String("Reconnected: ") + WiFi.localIP().toString());
        _wasConnected = true;
      }
      return;
    }

    // WiFi dropped — attempt reconnect every 10 seconds
    if (_wasConnected) {
      Log::warn("WiFi", "Connection lost");
      _wasConnected = false;
    }

    if (now - _lastReconnectAttempt > 10000) {
      _lastReconnectAttempt = now;
      Log::info("WiFi", "Attempting reconnect...");
      WiFi.disconnect();
      WiFi.begin(CONFIG_WIFI_SSID, CONFIG_WIFI_PASS);
    }
  }

  inline void setupMDNS() {
    if (MDNS.begin(CONFIG_MDNS_HOSTNAME)) {
      Log::info("mDNS", String("Started: ") + CONFIG_MDNS_HOSTNAME + ".local");
      MDNS.addService("http", "tcp", 80);
    } else {
      Log::warn("mDNS", "Failed to start");
    }
  }

  inline void setupTime() {
    applyTimeZone(CONFIG_TZ_INFO);
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    time_t now = time(nullptr);
    uint32_t start = millis();
    while (now < 1700000000 && millis() - start < 15000) {
      delay(250);
      now = time(nullptr);
    }
    if (now < 1700000000) {
      Log::warn("Time", "NTP sync failed, clock may be wrong");
    } else {
      Log::info("Time", String("Epoch: ") + (uint32_t)now);
    }
  }
}
