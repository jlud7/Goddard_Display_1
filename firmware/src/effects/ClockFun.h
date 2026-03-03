#pragma once
#include "Effect.h"
#include "../render/Text.h"
#include "../render/Color.h"
#include <time.h>

class ClockFun : public Effect {
public:
  const char* id() const override { return "clock_fun"; }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["style"].is<int>()) _style = params["style"].as<int>();
    if (params["blink"].is<bool>()) _blink = params["blink"].as<bool>();
  }

  void tick(uint32_t dt_ms) override {
    _t += dt_ms;
    if (_t > 1000) { _t = 0; _blinkState = !_blinkState; }
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
    snprintf(buf, sizeof(buf), "%02d%c%02d", hour, showColon?':':' ', minute);

    // style 0: centered; style 1: bottom; style 2: diagonal glow
    if (_style == 0){
      int x = (c.w() - (5*5 + 4)) / 2; // 5 chars including colon + spacing
      int y = (c.h() - 7) / 2;
      drawText5x7(c, x, y, buf, Color::CYAN, 1);
    } else if (_style == 1){
      int x = 2;
      int y = c.h() - 9;
      drawText5x7(c, x, y, buf, Color::GREEN, 1);
      // add a simple scanline accent
      for (int i=0; i<c.w(); i++) c.set(i, y-2, Color::BLUE);
    } else {
      // diagonal "glow" by rendering offset shadows
      int x = 4, y = 4;
      drawText5x7(c, x+1, y+1, buf, Color::BLUE, 1);
      drawText5x7(c, x, y, buf, Color::WHITE, 1);
      for (int i=0; i<32; i++){
        int px = (i*2) % c.w();
        int py = i % c.h();
        c.set(px, py, Color::MAGENTA);
      }
    }
  }

private:
  uint32_t _t = 0;
  bool _blink = true;
  bool _blinkState = true;
  int _style = 0;
};
