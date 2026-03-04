#pragma once
#include "Canvas565.h"
#include "Font5x7.h"

inline void drawChar5x7(Canvas565& c, int x, int y, char ch, uint16_t color) {
  int idx = glyphIndex(ch);
  for (int col=0; col<5; col++){
    uint8_t bits = FONT5X7[idx][col];
    for (int row=0; row<7; row++){
      if (bits & (1<<row)) c.set(x+col, y+row, color);
    }
  }
}

inline void drawText5x7(Canvas565& c, int x, int y, const char* s, uint16_t color, int spacing=1) {
  int cx=x;
  for (const char* p=s; *p; p++){
    drawChar5x7(c, cx, y, *p, color);
    cx += 5 + spacing;
  }
}
