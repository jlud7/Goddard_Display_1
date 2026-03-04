#include "ApiServer.h"
#include "FrameProtocol.h"
#include "../config.h"

void ApiServer::_handleFrameBinary(uint8_t* data, size_t len){
  if (!_ctl.wantsExternalFrames()) return;
  FrameHeader hdr;
  if (!parseHeader(data, len, hdr)) return;
  if (hdr.w != PANEL_RES_X || hdr.h != PANEL_RES_Y) return;
  if (hdr.format != 0) return; // only RGB565 in firmware
  size_t expected = sizeof(FrameHeader) + (size_t)hdr.w * hdr.h * 2;
  if (len < expected) return;

  const uint16_t* frame = (const uint16_t*)(data + sizeof(FrameHeader));
  _ctl.pushFrameRGB565(frame, (size_t)hdr.w * hdr.h);
}
