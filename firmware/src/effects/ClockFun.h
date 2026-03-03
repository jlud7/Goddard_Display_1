#pragma once
#include "Effect.h"
#include "../render/Text.h"
#include "../render/Color.h"
#include <time.h>
#include <math.h>

class ClockFun : public Effect {
public:
  const char* id() const override { return "clock_fun"; }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["style"].is<int>()) _style = constrain(params["style"].as<int>(), 0, 2);
    if (params["blink"].is<bool>()) _blink = params["blink"].as<bool>();
  }

  void tick(uint32_t dt_ms) override {
    _t += dt_ms;
    if (_t > 1000) { _t = 0; _blinkState = !_blinkState; }
    _phase += dt_ms * 0.001f;
  }

  void render(Canvas565& c) override {
    c.clear(Color::BLACK);

    time_t now = time(nullptr);
    struct tm tmv;
    localtime_r(&now, &tmv);

    int hour = tmv.tm_hour;
    int minute = tmv.tm_min;

    char buf[6];
    bool showColon = !_blink || _blinkState;
    snprintf(buf, sizeof(buf), "%02d%c%02d", hour, showColon ? ':' : ' ', minute);

    if (_style == 0) {
      // Centered with accent line
      int x = (c.w() - (5 * 5 + 4)) / 2;
      int y = (c.h() - 7) / 2;
      drawText5x7(c, x, y, buf, Color::CYAN, 1);
    } else if (_style == 1) {
      // Bottom with scanline
      int x = 2;
      int y = c.h() - 9;
      drawText5x7(c, x, y, buf, Color::GREEN, 1);
      for (int i = 0; i < c.w(); i++) c.set(i, y - 2, Color::BLUE);
    } else {
      // Animated glow: soft radial gradient behind text
      int cx = c.w() / 2;
      int cy = c.h() / 2;
      for (int y = 0; y < c.h(); y++) {
        for (int x = 0; x < c.w(); x++) {
          float dx = (float)(x - cx);
          float dy = (float)(y - cy);
          float dist = sqrtf(dx * dx + dy * dy);
          float wave = sinf(_phase * 0.8f + dist * 0.15f) * 0.5f + 0.5f;
          uint8_t v = (uint8_t)(wave * 18.0f);
          if (v > 0) {
            c.set(x, y, Color::rgb888_to_565(v / 2, 0, v));
          }
        }
      }
      // Shadow + text
      int tx = (c.w() - (5 * 5 + 4)) / 2;
      int ty = (c.h() - 7) / 2;
      drawText5x7(c, tx + 1, ty + 1, buf, Color::rgb888_to_565(40, 20, 80), 1);
      drawText5x7(c, tx, ty, buf, Color::WHITE, 1);
    }
  }

private:
  uint32_t _t = 0;
  bool _blink = true;
  bool _blinkState = true;
  int _style = 0;
  float _phase = 0.0f;
};
