#pragma once
#include "Effect.h"
#include "../render/Color.h"
#include "../render/Text.h"

class WeatherFun : public Effect {
public:
  const char* id() const override { return "weather_fun"; }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["tempF"].is<float>()) _tempF = params["tempF"].as<float>();
    if (params["condition"].is<const char*>()) _condition = params["condition"].as<const char*>();
    if (params["variant"].is<int>()) _variant = params["variant"].as<int>();
  }

  void tick(uint32_t dt_ms) override {
    _t += dt_ms;
  }

  void render(Canvas565& c) override {
    c.clear(Color::BLACK);
    // Variant 0: simple icon + temp
    // Variant 1: "rain" or "snow" animation
    // Variant 2: heat shimmer / wind
    if (_variant == 0){
      drawIcon(c);
      char buf[16];
      snprintf(buf, sizeof(buf), "%dF", (int)roundf(_tempF));
      drawText5x7(c, 28, 12, buf, Color::YELLOW, 1);
    } else if (_variant == 1){
      drawIcon(c);
      renderParticles(c);
      char buf[16];
      snprintf(buf, sizeof(buf), "%dF", (int)roundf(_tempF));
      drawText5x7(c, 2, 2, buf, Color::CYAN, 1);
    } else {
      drawIcon(c);
      renderWind(c);
      char buf[16];
      snprintf(buf, sizeof(buf), "%dF", (int)roundf(_tempF));
      drawText5x7(c, 2, 22, buf, Color::WHITE, 1);
    }
  }

private:
  float _tempF = 72;
  String _condition = "clear";
  int _variant = 0;
  uint32_t _t = 0;

  void drawIcon(Canvas565& c){
    // Tiny 16x16 icons drawn procedurally.
    if (_condition.indexOf("rain") >= 0){
      // cloud
      fillCircle(c, 12, 10, 4, Color::WHITE);
      fillCircle(c, 16, 8, 5, Color::WHITE);
      fillCircle(c, 20, 10, 4, Color::WHITE);
      fillRect(c, 10, 10, 14, 6, Color::WHITE);
      // drops
      for (int i=0; i<6; i++){
        int x = 11 + (i*2);
        int y = 18 + (int)(((_t/80)+i)%6);
        c.set(x, y% c.h(), Color::CYAN);
      }
    } else if (_condition.indexOf("cloud") >= 0){
      fillCircle(c, 12, 10, 4, Color::WHITE);
      fillCircle(c, 16, 8, 5, Color::WHITE);
      fillCircle(c, 20, 10, 4, Color::WHITE);
      fillRect(c, 10, 10, 14, 6, Color::WHITE);
    } else if (_condition.indexOf("snow") >= 0){
      fillCircle(c, 12, 10, 4, Color::WHITE);
      fillCircle(c, 16, 8, 5, Color::WHITE);
      fillCircle(c, 20, 10, 4, Color::WHITE);
      fillRect(c, 10, 10, 14, 6, Color::WHITE);
      for (int i=0; i<10; i++){
        int x = 10 + (i*3)%16;
        int y = 18 + (int)(((_t/120)+i)%10);
        c.set(x, y% c.h(), Color::WHITE);
      }
    } else {
      // sun
      fillCircle(c, 16, 12, 6, Color::YELLOW);
      for (int i=0; i<8; i++){
        int dx = (int)roundf(cosf(i*0.785f)*10);
        int dy = (int)roundf(sinf(i*0.785f)*10);
        c.set(16+dx, 12+dy, Color::YELLOW);
      }
    }
  }

  void renderParticles(Canvas565& c){
    // extra rain/snow streaks in background
    for (int i=0; i<40; i++){
      int x = (i*7 + (_t/30)) % c.w();
      int y = (i*13 + (_t/50)) % c.h();
      uint16_t col = (_condition.indexOf("snow")>=0) ? Color::WHITE : Color::CYAN;
      c.set(x, y, col);
    }
  }

  void renderWind(Canvas565& c){
    // drifting bands
    for (int band=0; band<3; band++){
      int y = 6 + band*8;
      int phase = (_t/40 + band*10) % c.w();
      for (int x=0; x<c.w(); x++){
        if (((x+phase) % 12) < 8) c.set(x, y, Color::BLUE);
      }
    }
  }

  // tiny primitives
  void fillRect(Canvas565& c, int x, int y, int w, int h, uint16_t col){
    for (int yy=y; yy<y+h; yy++)
      for (int xx=x; xx<x+w; xx++)
        c.set(xx, yy, col);
  }
  void fillCircle(Canvas565& c, int cx, int cy, int r, uint16_t col){
    for (int y=-r; y<=r; y++){
      for (int x=-r; x<=r; x++){
        if (x*x+y*y <= r*r) c.set(cx+x, cy+y, col);
      }
    }
  }
};
