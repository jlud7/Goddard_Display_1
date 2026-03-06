#pragma once

// -------- Panel / HUB75 config --------
// Set pins to match your adapter board.
// For ESP32-S3 DevKitC-1, these defaults are placeholders.
// Update to the exact wiring you are using.

#define PANEL_RES_X 64
#define PANEL_RES_Y 32

// DMA panel config: adjust if you have chained panels later.
// For single 64x32 panel: chain length = 1
#define PANEL_CHAIN 1

// HUB75 signal pins — RGB Matrix Adapter Board (E) pinout
#define PIN_R1  37
#define PIN_G1  6
#define PIN_B1  36
#define PIN_R2  35
#define PIN_G2  5
#define PIN_B2  0
#define PIN_A   45
#define PIN_B   1
#define PIN_C   48
#define PIN_D   2
#define PIN_E   4
#define PIN_LAT 38
#define PIN_OE  21
#define PIN_CLK 47

// -------- WiFi --------
// Option A: hardcode WiFi (fastest for initial bringup).
#define CONFIG_WIFI_SSID     "GL-AXT1800-bec"
#define CONFIG_WIFI_PASS     "26RMAARJFJ"

// Optional static IP (0.0.0.0 disables)
#define CONFIG_WIFI_STATIC_IP   "0.0.0.0"
#define CONFIG_WIFI_GATEWAY     "0.0.0.0"
#define CONFIG_WIFI_SUBNET      "255.255.255.0"
#define CONFIG_WIFI_DNS         "0.0.0.0"

// Device hostname for mDNS: http://led64x32.local (if supported by your network)
#define CONFIG_MDNS_HOSTNAME "led64x32"

// Local timezone for the panel clock. This default matches US Eastern time.
// Change it if the device will live elsewhere.
#define CONFIG_TZ_INFO "EST5EDT,M3.2.0,M11.1.0"

// -------- Render / streaming --------
#define FRAME_WS_PATH "/ws/frame"
#define EVENTS_WS_PATH "/ws/events"

#define FRAME_JITTER_BUFFER 3   // number of frames to buffer for smooth playback
#define FRAME_MAX_FPS 30

// -------- Defaults --------
#define DEFAULT_BRIGHTNESS 160   // 0..255
