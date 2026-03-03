#pragma once
#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>
#include "../util/Log.h"
#include "../config.h"
#include "Canvas565.h"
#include "Color.h"

// Gamma 2.2 correction table for more natural LED colors
static const uint8_t GAMMA_LUT[256] PROGMEM = {
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    3,  3,  3,  3,  3,  4,  4,  4,  4,  5,  5,  5,  5,  6,  6,  6,
    6,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10, 10, 11, 11, 11, 12,
   12, 13, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18, 19, 19,
   20, 20, 21, 22, 22, 23, 23, 24, 25, 25, 26, 26, 27, 28, 28, 29,
   30, 30, 31, 32, 33, 33, 34, 35, 35, 36, 37, 38, 39, 39, 40, 41,
   42, 43, 43, 44, 45, 46, 47, 48, 49, 49, 50, 51, 52, 53, 54, 55,
   56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
   73, 74, 75, 76, 77, 78, 79, 81, 82, 83, 84, 85, 87, 88, 89, 90,
   91, 93, 94, 95, 97, 98, 99,100,102,103,105,106,107,109,110,111,
  113,114,116,117,119,120,121,123,124,126,127,129,130,132,133,135,
  137,138,140,141,143,145,146,148,149,151,153,154,156,158,159,161,
  163,165,166,168,170,172,173,175,177,179,181,182,184,186,188,190,
  192,194,196,197,199,201,203,205,207,209,211,213,215,217,219,221,
  223,225,227,229,231,234,236,238,240,242,244,246,248,251,253,255,
};

class Display {
public:
  bool begin() {
    HUB75_I2S_CFG mxconfig(
      PANEL_RES_X, PANEL_RES_Y, PANEL_CHAIN
    );

    mxconfig.gpio.r1 = PIN_R1;
    mxconfig.gpio.g1 = PIN_G1;
    mxconfig.gpio.b1 = PIN_B1;
    mxconfig.gpio.r2 = PIN_R2;
    mxconfig.gpio.g2 = PIN_G2;
    mxconfig.gpio.b2 = PIN_B2;
    mxconfig.gpio.a  = PIN_A;
    mxconfig.gpio.b  = PIN_B;
    mxconfig.gpio.c  = PIN_C;
    mxconfig.gpio.d  = PIN_D;
    mxconfig.gpio.e  = PIN_E;
    mxconfig.gpio.lat= PIN_LAT;
    mxconfig.gpio.oe = PIN_OE;
    mxconfig.gpio.clk= PIN_CLK;

    mxconfig.clkphase = false;
    mxconfig.driver = HUB75_I2S_CFG::SHIFTREG;
    mxconfig.i2sspeed = HUB75_I2S_CFG::HZ_20M;
    mxconfig.latch_blanking = 2;

    _matrix = new MatrixPanel_I2S_DMA(mxconfig);
    if (!_matrix->begin()) {
      Log::err("Display", "Matrix begin failed");
      return false;
    }

    _targetBrightness = DEFAULT_BRIGHTNESS;
    _currentBrightness = 0; // start dark for fade-in
    _matrix->setBrightness8(0);

    _front = new uint16_t[PANEL_RES_X * PANEL_RES_Y];
    _back  = new uint16_t[PANEL_RES_X * PANEL_RES_Y];
    memset(_front, 0, PANEL_RES_X * PANEL_RES_Y * 2);
    memset(_back, 0, PANEL_RES_X * PANEL_RES_Y * 2);

    _frontCanvas = new Canvas565(PANEL_RES_X, PANEL_RES_Y, _front);
    _backCanvas  = new Canvas565(PANEL_RES_X, PANEL_RES_Y, _back);
    return true;
  }

  void setBrightness(uint8_t b) {
    _targetBrightness = b;
  }

  uint8_t brightness() const { return _targetBrightness; }

  Canvas565& back() { return *_backCanvas; }

  void playBootAnimation() {
    if (!_matrix) return;

    // Sweep a blue line across, then fade in the G logo
    for (int phase = 0; phase < 64; phase++) {
      for (int y = 0; y < PANEL_RES_Y; y++) {
        for (int x = 0; x < PANEL_RES_X; x++) {
          if (x == phase) {
            _matrix->drawPixel(x, y, Color::rgb888_to_565(40, 80, 255));
          } else if (x < phase) {
            // Gradient fade behind sweep line
            uint8_t fade = (uint8_t)((float)(phase - x) / 64.0f * 10.0f);
            _matrix->drawPixel(x, y, Color::rgb888_to_565(fade, fade, fade + 5));
          } else {
            _matrix->drawPixel(x, y, 0);
          }
        }
      }
      _matrix->flipDMABuffer();
      _matrix->setBrightness8(constrain(phase * 4, 0, _targetBrightness));
      delay(12);
    }

    // Flash center "G" briefly
    _matrix->fillScreenRGB888(0, 0, 0);
    int gx = (PANEL_RES_X - 5) / 2;
    int gy = (PANEL_RES_Y - 7) / 2;
    // Draw 'G' manually with pixel art
    const uint8_t G_GLYPH[5] = {0x3E, 0x41, 0x49, 0x49, 0x3A};
    for (int col = 0; col < 5; col++) {
      uint8_t bits = G_GLYPH[col];
      for (int row = 0; row < 7; row++) {
        if (bits & (1 << row)) {
          _matrix->drawPixel(gx + col, gy + row, Color::rgb888_to_565(59, 125, 255));
        }
      }
    }
    _matrix->flipDMABuffer();
    delay(600);

    // Fade out
    for (int b = _targetBrightness; b >= 0; b -= 8) {
      _matrix->setBrightness8(constrain(b, 0, 255));
      delay(20);
    }
    _matrix->fillScreenRGB888(0, 0, 0);
    _matrix->flipDMABuffer();
    _currentBrightness = 0;
  }

  void swapAndShow() {
    // Smooth brightness transitions
    if (_currentBrightness != _targetBrightness) {
      if (_currentBrightness < _targetBrightness) {
        _currentBrightness = min((int)_currentBrightness + BRIGHTNESS_STEP, (int)_targetBrightness);
      } else {
        _currentBrightness = max((int)_currentBrightness - BRIGHTNESS_STEP, (int)_targetBrightness);
      }
      if (_matrix) _matrix->setBrightness8(_currentBrightness);
    }

    // Swap pointers
    uint16_t* tmp = _front; _front = _back; _back = tmp;
    Canvas565* tc = _frontCanvas; _frontCanvas = _backCanvas; _backCanvas = tc;

    // Blit with gamma correction
    for (int y = 0; y < PANEL_RES_Y; y++) {
      for (int x = 0; x < PANEL_RES_X; x++) {
        uint16_t c = _front[(size_t)y * PANEL_RES_X + x];
        if (_gammaEnabled && c != 0) {
          uint8_t r, g, b;
          Color::rgb565_to_888(c, r, g, b);
          r = pgm_read_byte(&GAMMA_LUT[r]);
          g = pgm_read_byte(&GAMMA_LUT[g]);
          b = pgm_read_byte(&GAMMA_LUT[b]);
          c = Color::rgb888_to_565(r, g, b);
        }
        _matrix->drawPixel(x, y, c);
      }
    }
    _matrix->flipDMABuffer();
  }

  void setGamma(bool enabled) { _gammaEnabled = enabled; }
  bool gammaEnabled() const { return _gammaEnabled; }

private:
  static constexpr int BRIGHTNESS_STEP = 4;

  MatrixPanel_I2S_DMA* _matrix = nullptr;
  uint8_t _targetBrightness = DEFAULT_BRIGHTNESS;
  uint8_t _currentBrightness = 0;
  bool _gammaEnabled = true;

  uint16_t* _front = nullptr;
  uint16_t* _back = nullptr;
  Canvas565* _frontCanvas = nullptr;
  Canvas565* _backCanvas = nullptr;
};
