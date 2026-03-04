#pragma once
#include <ArduinoJson.h>
#include "../render/Canvas565.h"

class Effect {
public:
  virtual ~Effect() = default;

  virtual const char* id() const = 0;
  virtual void begin() {}
  virtual void end() {}
  virtual void tick(uint32_t dt_ms) { (void)dt_ms; }
  virtual void render(Canvas565& c) = 0;
  virtual void handleCommand(const JsonVariantConst& params) { (void)params; }

  // For effects that want an external frame stream (animation/sprite players)
  virtual bool wantsExternalFrames() const { return false; }
  virtual void pushFrameRGB565(const uint16_t* frame, size_t pixels) { (void)frame; (void)pixels; }
};
