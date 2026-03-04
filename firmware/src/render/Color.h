#pragma once
#include <stdint.h>

namespace Color {
  inline uint16_t rgb888_to_565(uint8_t r, uint8_t g, uint8_t b) {
    return (uint16_t)(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3));
  }

  inline void rgb565_to_888(uint16_t c, uint8_t &r, uint8_t &g, uint8_t &b) {
    r = (uint8_t)((c >> 8) & 0xF8);
    g = (uint8_t)((c >> 3) & 0xFC);
    b = (uint8_t)((c << 3) & 0xF8);
  }

  constexpr uint16_t BLACK = 0x0000;
  constexpr uint16_t WHITE = 0xFFFF;
  constexpr uint16_t RED   = 0xF800;
  constexpr uint16_t GREEN = 0x07E0;
  constexpr uint16_t BLUE  = 0x001F;
  constexpr uint16_t YELLOW= 0xFFE0;
  constexpr uint16_t ORANGE= 0xFD20;
  constexpr uint16_t CYAN  = 0x07FF;
  constexpr uint16_t MAGENTA=0xF81F;
}
