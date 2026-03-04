#pragma once
#include "Effect.h"
#include "../render/Color.h"
#include <math.h>

class Rainbow : public Effect {
public:
  const char* id() const override { return "rainbow"; }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["speed"].is<int>())  _speed = constrain(params["speed"].as<int>(), 1, 20);
    if (params["scale"].is<int>())  _scale = constrain(params["scale"].as<int>(), 1, 32);
    if (params["style"].is<int>())  _style = constrain(params["style"].as<int>(), 0, 2);
  }

  void tick(uint32_t dt_ms) override {
    _phase += dt_ms * _speed * 0.001f;
    _phase = fmodf(_phase, 6.2831853f);
  }

  void render(Canvas565& c) override {
    c.clear(Color::BLACK);

    for (int y = 0; y < c.h(); y++) {
      for (int x = 0; x < c.w(); x++) {
        float hue = 0.0f;

        if (_style == 0) {
          // Diagonal sweep
          hue = _phase + (float)(x + y) / (float)_scale * 0.5f;
        } else if (_style == 1) {
          // Radial from center
          float dx = (float)x - c.w() * 0.5f;
          float dy = (float)y - c.h() * 0.5f;
          float dist = sqrtf(dx * dx + dy * dy);
          hue = _phase + dist / (float)_scale * 0.8f;
        } else {
          // Horizontal wave
          hue = _phase + (float)x / (float)_scale + sinf((float)y * 0.3f + _phase) * 0.5f;
        }

        // Wrap hue to 0..1
        hue = hue - floorf(hue);
        if (hue < 0.0f) hue += 1.0f;

        uint8_t r, g, b;
        _hsvToRgb(hue, 1.0f, 1.0f, r, g, b);
        c.set(x, y, Color::rgb888_to_565(r, g, b));
      }
    }
  }

private:
  float _phase = 0.0f;
  int _speed = 3;
  int _scale = 8;
  int _style = 0;

  static void _hsvToRgb(float h, float s, float v, uint8_t& r, uint8_t& g, uint8_t& b) {
    float c = v * s;
    float x = c * (1.0f - fabsf(fmodf(h * 6.0f, 2.0f) - 1.0f));
    float m = v - c;
    float rf, gf, bf;
    int hi = (int)(h * 6.0f) % 6;
    switch (hi) {
      case 0: rf = c; gf = x; bf = 0; break;
      case 1: rf = x; gf = c; bf = 0; break;
      case 2: rf = 0; gf = c; bf = x; break;
      case 3: rf = 0; gf = x; bf = c; break;
      case 4: rf = x; gf = 0; bf = c; break;
      default: rf = c; gf = 0; bf = x; break;
    }
    r = (uint8_t)((rf + m) * 255.0f);
    g = (uint8_t)((gf + m) * 255.0f);
    b = (uint8_t)((bf + m) * 255.0f);
  }
};
