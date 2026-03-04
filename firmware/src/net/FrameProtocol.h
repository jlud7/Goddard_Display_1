#pragma once
#include <stdint.h>
#include <stddef.h>

struct FrameHeader {
  uint32_t magic;      // 'PANL' 0x50414E4C
  uint16_t w;
  uint16_t h;
  uint16_t frameId;
  uint16_t format;     // 0=RGB565
  uint16_t payloadBytes;
  uint16_t reserved;
};

static const uint32_t FRAME_MAGIC = 0x50414E4C;

inline bool parseHeader(const uint8_t* data, size_t len, FrameHeader& out){
  if (len < sizeof(FrameHeader)) return false;
  memcpy(&out, data, sizeof(FrameHeader));
  if (out.magic != FRAME_MAGIC) return false;
  return true;
}
