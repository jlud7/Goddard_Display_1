#pragma once
#include "../config.h"
#include "Effect.h"
#include "../render/Color.h"
#include "../util/Log.h"
#include <Arduino.h>

// External RGB565 frames streamed over WS/UDP are queued into a jitter buffer.
class AnimPlayer : public Effect {
public:
  const char* id() const override { return "anim_player"; }
  bool wantsExternalFrames() const override { return true; }

  void begin() override {
    _playing = true;
    _fps = 12;
    _loop = true;
    _frameCount = 0;
    _readIdx = 0;
    _writeIdx = 0;
    _queued = 0;
    _everReceived = false;
    memset(_frames, 0, sizeof(_frames));
  }

  void handleCommand(const JsonVariantConst& params) override {
    if (params["fps"].is<int>()) _fps = constrain(params["fps"].as<int>(), 1, 30);
    if (params["loop"].is<bool>()) _loop = params["loop"].as<bool>();
    if (params["playing"].is<bool>()) _playing = params["playing"].as<bool>();
  }

  void tick(uint32_t dt_ms) override {
    _accum += dt_ms;
    uint32_t frameMs = 1000 / (uint32_t)_fps;
    while (_accum >= frameMs) {
      _accum -= frameMs;
      // Hold on the last received frame until a newer one is available.
      if (_playing && _queued > 1) {
        _readIdx = (_readIdx + 1) % FRAME_JITTER_BUFFER;
        _queued--;
        _frameCount++;
      }
    }
  }

  void render(Canvas565& c) override {
    // If we have any frames at all, show the current read frame.
    if (_hasAny()){
      const uint16_t* src = _frames[_readIdx];
      memcpy(c.data(), src, c.bytes());
      // subtle overlay diagnostics line (disabled by default)
      if (_showOverlay){
        for (int x=0; x<c.w(); x+=2) c.set(x, 0, Color::MAGENTA);
      }
    } else {
      // idle placeholder
      c.clear(Color::BLACK);
      for (int x=0; x<c.w(); x++) c.set(x, c.h()/2, Color::BLUE);
      for (int y=0; y<c.h(); y++) c.set(c.w()/2, y, Color::BLUE);
    }
  }

  void pushFrameRGB565(const uint16_t* frame, size_t pixels) override {
    if (pixels != (size_t)PANEL_RES_X * PANEL_RES_Y) return;

    if (_queued == 0) {
      memcpy(_frames[_writeIdx], frame, (size_t)PANEL_RES_X * PANEL_RES_Y * 2);
      _readIdx = _writeIdx;
      _queued = 1;
      _everReceived = true;
      Log::info("Anim", String("First frame accepted, pixels=") + pixels);
      return;
    }

    // Don't overwrite the slot currently being displayed.
    int next = (_writeIdx + 1) % FRAME_JITTER_BUFFER;
    if (next == _readIdx) {
      return;
    }

    memcpy(_frames[next], frame, (size_t)PANEL_RES_X * PANEL_RES_Y * 2);
    _writeIdx = next;
    _everReceived = true;
    if (_queued < FRAME_JITTER_BUFFER) _queued++;
    Log::info("Anim", String("Frame queued, queued=") + _queued + " read=" + _readIdx + " write=" + _writeIdx);
  }

private:
  bool _playing = true;
  bool _loop = true;
  bool _showOverlay = false;
  int _fps = 12;
  uint32_t _accum = 0;
  uint32_t _frameCount = 0;
  bool _everReceived = false;

  // ring buffer
  uint16_t _frames[FRAME_JITTER_BUFFER][PANEL_RES_X * PANEL_RES_Y];
  int _readIdx = 0;
  int _writeIdx = 0;
  int _queued = 0;

  inline bool _hasAny() const { return _queued > 0 || _everReceived; }
};
