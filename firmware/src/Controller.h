#pragma once
#include <ArduinoJson.h>
#include <memory>
#include <vector>
#include "effects/Effect.h"
#include "effects/ClockFun.h"
#include "effects/WeatherFun.h"
#include "effects/AnimPlayer.h"
#include "effects/Rainbow.h"
#include "effects/Starfield.h"
#include "effects/TextScroll.h"

class Controller {
public:
  void begin() {
    _current = nullptr; // prevent use-after-free during clear
    _effects.clear();
    _effects.push_back(std::unique_ptr<Effect>(new ClockFun()));
    _effects.push_back(std::unique_ptr<Effect>(new WeatherFun()));
    _effects.push_back(std::unique_ptr<Effect>(new AnimPlayer()));
    _effects.push_back(std::unique_ptr<Effect>(new Rainbow()));
    _effects.push_back(std::unique_ptr<Effect>(new Starfield()));
    _effects.push_back(std::unique_ptr<Effect>(new TextScroll()));
    setMode("clock_fun", JsonVariantConst());
  }

  Effect* current() { return _current; }

  bool setMode(const String& id, const JsonVariantConst& params) {
    Effect* found = nullptr;
    for (auto& e : _effects) {
      if (id == e->id()) { found = e.get(); break; }
    }
    if (!found) return false;

    if (_current) _current->end();
    _current = found;
    _current->begin();
    if (!params.isNull()) _current->handleCommand(params);
    _modeId = id;
    return true;
  }

  String modeId() const { return _modeId; }

  void tick(uint32_t dt_ms) { if (_current) _current->tick(dt_ms); }
  void render(Canvas565& c) { if (_current) _current->render(c); }

  void handleParams(const JsonVariantConst& params) { if (_current) _current->handleCommand(params); }

  bool wantsExternalFrames() const { return _current && _current->wantsExternalFrames(); }
  void pushFrameRGB565(const uint16_t* frame, size_t pixels) { if (_current) _current->pushFrameRGB565(frame, pixels); }

private:
  std::vector<std::unique_ptr<Effect>> _effects;
  Effect* _current = nullptr;
  String _modeId = "clock_fun";
};
