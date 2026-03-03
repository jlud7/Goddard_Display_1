#pragma once
#include "Effect.h"
#include "../render/Color.h"
#include "../config.h"
#include <math.h>

class Starfield : public Effect {
public:
  const char* id() const override { return "starfield"; }

  void begin() override {
    // Initialize stars with pseudo-random positions
    uint32_t seed = 42;
    for (int i = 0; i < MAX_STARS; i++) {
      seed = seed * 1103515245 + 12345;
      _stars[i].x = (float)(seed % (PANEL_RES_X * 256)) / 256.0f;
      seed = seed * 1103515245 + 12345;
      _stars[i].y = (float)(seed % (PANEL_RES_Y * 256)) / 256.0f;
      seed = seed * 1103515245 + 12345;
      _stars[i].z = (float)(seed % 1000) / 1000.0f;
      seed = seed * 1103515245 + 12345;
      _stars[i].speed = 0.3f + (float)(seed % 700) / 1000.0f;
    }
  }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["speed"].is<int>()) _speedMul = constrain(params["speed"].as<int>(), 1, 10);
    if (params["density"].is<int>()) _density = constrain(params["density"].as<int>(), 10, MAX_STARS);
    if (params["warp"].is<bool>()) _warp = params["warp"].as<bool>();
  }

  void tick(uint32_t dt_ms) override {
    float dt = (float)dt_ms / 1000.0f * (float)_speedMul;

    for (int i = 0; i < _density; i++) {
      Star& s = _stars[i];
      if (_warp) {
        // Warp: stars move outward from center
        float cx = PANEL_RES_X * 0.5f;
        float cy = PANEL_RES_Y * 0.5f;
        float dx = s.x - cx;
        float dy = s.y - cy;
        float dist = sqrtf(dx * dx + dy * dy);
        if (dist < 0.5f) dist = 0.5f;
        s.x += (dx / dist) * s.speed * dt * 12.0f;
        s.y += (dy / dist) * s.speed * dt * 12.0f;
        s.z += dt * s.speed * 0.5f;
        if (s.z > 1.0f) s.z = 1.0f;
      } else {
        // Classic: stars drift down
        s.y += s.speed * dt * 8.0f;
        // Gentle twinkle
        s.z += dt * 0.8f;
        if (s.z > 1.0f) s.z -= 1.0f;
      }

      // Wrap around
      if (s.x < -1.0f || s.x >= PANEL_RES_X + 1) _resetStar(s);
      if (s.y < -1.0f || s.y >= PANEL_RES_Y + 1) _resetStar(s);
    }
  }

  void render(Canvas565& c) override {
    // Fade background instead of clearing (creates trails)
    for (int i = 0; i < PANEL_RES_X * PANEL_RES_Y; i++) {
      uint16_t px = c.data()[i];
      if (px == 0) continue;
      uint8_t r, g, b;
      Color::rgb565_to_888(px, r, g, b);
      r = (uint8_t)(r * 0.7f);
      g = (uint8_t)(g * 0.7f);
      b = (uint8_t)(b * 0.7f);
      c.data()[i] = Color::rgb888_to_565(r, g, b);
    }

    for (int i = 0; i < _density; i++) {
      const Star& s = _stars[i];
      int px = (int)roundf(s.x);
      int py = (int)roundf(s.y);

      // Twinkle brightness
      float bright = 0.5f + 0.5f * sinf(s.z * 6.2831853f);
      uint8_t v = (uint8_t)(bright * 255.0f);

      // Color tint based on speed (slow = warm, fast = cool)
      uint8_t r, g, b;
      if (s.speed < 0.5f) {
        r = v; g = (uint8_t)(v * 0.85f); b = (uint8_t)(v * 0.6f); // warm
      } else if (s.speed < 0.7f) {
        r = v; g = v; b = v; // white
      } else {
        r = (uint8_t)(v * 0.7f); g = (uint8_t)(v * 0.8f); b = v; // cool blue
      }

      c.set(px, py, Color::rgb888_to_565(r, g, b));
    }
  }

private:
  static constexpr int MAX_STARS = 80;

  struct Star {
    float x, y, z, speed;
  };

  Star _stars[MAX_STARS];
  int _speedMul = 3;
  int _density = 60;
  bool _warp = false;

  void _resetStar(Star& s) {
    // Quick pseudo-random reset using micros()
    uint32_t r = (uint32_t)micros();
    if (_warp) {
      s.x = PANEL_RES_X * 0.5f + (float)((int)(r % 7) - 3);
      s.y = PANEL_RES_Y * 0.5f + (float)((int)((r >> 8) % 7) - 3);
      s.z = 0.0f;
    } else {
      s.x = (float)(r % PANEL_RES_X);
      s.y = -1.0f;
      s.z = (float)((r >> 16) % 100) / 100.0f;
    }
    r = r * 1103515245 + 12345;
    s.speed = 0.3f + (float)(r % 700) / 1000.0f;
  }
};
