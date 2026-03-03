#pragma once
#include <WiFi.h>
#include <ESPmDNS.h>
#include <time.h>
#include "../util/Log.h"
#include "../config.h"

namespace Net {
  inline bool setupWifi() {
    WiFi.mode(WIFI_STA);

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
    return true;
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
    // Use pool.ntp.org by default; adjust TZ env via setenv("TZ", "...", 1)
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    time_t now = time(nullptr);
    uint32_t start = millis();
    while (now < 1700000000 && millis() - start < 15000) { // wait for plausible epoch
      delay(250);
      now = time(nullptr);
    }
    Log::info("Time", String("Epoch: ") + (uint32_t)now);
  }
}
