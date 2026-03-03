#pragma once
#include "Effect.h"
#include "../render/Text.h"
#include "../render/Color.h"
#include <Arduino.h>

class TextScroll : public Effect {
public:
  const char* id() const override { return "text_scroll"; }

  void begin() override {
    _offset = PANEL_RES_X; // start offscreen right
  }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["text"].is<const char*>()) {
      _text = params["text"].as<const char*>();
      _offset = PANEL_RES_X; // restart scroll
    }
    if (params["speed"].is<int>()) _speed = constrain(params["speed"].as<int>(), 1, 20);
    if (params["color"].is<const char*>()) _setColor(params["color"].as<const char*>());
    if (params["y"].is<int>()) _yPos = constrain(params["y"].as<int>(), 0, PANEL_RES_Y - 7);
    if (params["rainbow"].is<bool>()) _rainbow = params["rainbow"].as<bool>();
  }

  void tick(uint32_t dt_ms) override {
    _accum += dt_ms;
    uint32_t step = 1000 / (20 + _speed * 8); // ms per pixel
    while (_accum >= step) {
      _accum -= step;
      _offset--;
    }

    int textWidth = (int)_text.length() * 6; // 5px char + 1px spacing
    if (_offset < -textWidth) {
      _offset = PANEL_RES_X; // loop
    }

    _huePhase += dt_ms * 0.002f;
    if (_huePhase > 6.2831853f) _huePhase -= 6.2831853f;
  }

  void render(Canvas565& c) override {
    c.clear(Color::BLACK);

    if (_rainbow) {
      // Render each character in a rainbow color
      int cx = _offset;
      for (size_t i = 0; i < _text.length(); i++) {
        float hue = _huePhase + (float)i * 0.12f;
        hue = hue - floorf(hue);
        uint16_t col = _hueToRgb565(hue);
        drawChar5x7(c, cx, _yPos, _text[i], col);
        cx += 6;
      }
    } else {
      drawText5x7(c, _offset, _yPos, _text.c_str(), _color, 1);
    }
  }

private:
  String _text = "GODDARD DISPLAY";
  int _offset = PANEL_RES_X;
  int _speed = 5;
  int _yPos = 12; // vertically centered for 5x7 font on 32px
  uint16_t _color = Color::CYAN;
  bool _rainbow = true;
  uint32_t _accum = 0;
  float _huePhase = 0.0f;

  void _setColor(const char* name) {
    String n(name);
    n.toLowerCase();
    if (n == "red")     _color = Color::RED;
    else if (n == "green")  _color = Color::GREEN;
    else if (n == "blue")   _color = Color::BLUE;
    else if (n == "yellow") _color = Color::YELLOW;
    else if (n == "cyan")   _color = Color::CYAN;
    else if (n == "white")  _color = Color::WHITE;
    else if (n == "orange") _color = Color::ORANGE;
    else if (n == "magenta") _color = Color::MAGENTA;
  }

  static uint16_t _hueToRgb565(float h) {
    float c = 1.0f;
    float x = 1.0f - fabsf(fmodf(h * 6.0f, 2.0f) - 1.0f);
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
    return Color::rgb888_to_565((uint8_t)(rf * 255), (uint8_t)(gf * 255), (uint8_t)(bf * 255));
  }
};
