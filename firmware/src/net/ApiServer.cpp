#include "ApiServer.h"
#include "FrameProtocol.h"
#include "../config.h"
#include "../util/Log.h"

bool ApiServer::_handleFrameBinary(uint8_t* data, size_t len){
  if (!_ctl.wantsExternalFrames()) {
    Log::warn("WS", "Frame ignored: current mode does not accept external frames");
    return false;
  }
  FrameHeader hdr;
  if (!parseHeader(data, len, hdr)) {
    Log::warn("WS", String("Frame header parse failed, len=") + len);
    return false;
  }
  if (hdr.w != PANEL_RES_X || hdr.h != PANEL_RES_Y) {
    Log::warn("WS", String("Frame size mismatch: ") + hdr.w + "x" + hdr.h);
    return false;
  }
  if (hdr.format != 0) {
    Log::warn("WS", String("Frame format unsupported: ") + hdr.format);
    return false; // only RGB565 in firmware
  }
  size_t expected = sizeof(FrameHeader) + (size_t)hdr.w * hdr.h * 2;
  if (len < expected) {
    Log::warn("WS", String("Frame payload short: got=") + len + " expected=" + expected);
    return false;
  }

  const uint16_t* frame = (const uint16_t*)(data + sizeof(FrameHeader));
  _framePackets++;
  _lastFrameBytes = (uint32_t)len;
  _lastFrameId = hdr.frameId;
  Log::info("WS", String("Frame received: id=") + hdr.frameId + " bytes=" + len);
  _ctl.pushFrameRGB565(frame, (size_t)hdr.w * hdr.h);
  return true;
}
