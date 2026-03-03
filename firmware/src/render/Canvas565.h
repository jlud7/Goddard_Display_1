#pragma once
#include <stdint.h>
#include <stddef.h>

// Tiny RGB565 canvas for 64x32
class Canvas565 {
public:
  Canvas565(uint16_t w, uint16_t h, uint16_t* buf) : _w(w), _h(h), _buf(buf) {}

  inline uint16_t w() const { return _w; }
  inline uint16_t h() const { return _h; }
  inline uint16_t* data() { return _buf; }
  inline const uint16_t* data() const { return _buf; }
  inline size_t bytes() const { return (size_t)_w * _h * 2; }

  inline void clear(uint16_t c = 0) {
    for (size_t i = 0; i < (size_t)_w * _h; i++) _buf[i] = c;
  }

  inline void set(int x, int y, uint16_t c) {
    if (x < 0 || y < 0 || x >= _w || y >= _h) return;
    _buf[(size_t)y * _w + (size_t)x] = c;
  }

  inline uint16_t get(int x, int y) const {
    if (x < 0 || y < 0 || x >= _w || y >= _h) return 0;
    return _buf[(size_t)y * _w + (size_t)x];
  }

private:
  uint16_t _w, _h;
  uint16_t* _buf;
};
