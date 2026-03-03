export const W = 64;
export const H = 32;

export function rgb565ToRgb888(c: number): [number, number, number] {
  // Extract and scale to full 0-255 range by replicating high bits into low bits
  const r5 = (c >> 11) & 0x1F;
  const g6 = (c >> 5)  & 0x3F;
  const b5 = c & 0x1F;
  const r = (r5 << 3) | (r5 >> 2); // 5-bit -> 8-bit: 31 -> 255
  const g = (g6 << 2) | (g6 >> 4); // 6-bit -> 8-bit: 63 -> 255
  const b = (b5 << 3) | (b5 >> 2); // 5-bit -> 8-bit: 31 -> 255
  return [r, g, b];
}

export function decodeB64ToU16LE(b64: string): Uint16Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i=0; i<bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Uint16Array(bytes.buffer);
}

export function makeFramePacketRGB565(frame: Uint16Array, frameId: number): ArrayBuffer {
  // matches firmware FrameHeader (little-endian)
  const headerBytes = 16; // sizeof(FrameHeader)
  const payloadBytes = W*H*2;
  const buf = new ArrayBuffer(headerBytes + payloadBytes);
  const dv = new DataView(buf);

  dv.setUint32(0, 0x50414E4C, true); // 'PANL'
  dv.setUint16(4, W, true);
  dv.setUint16(6, H, true);
  dv.setUint16(8, frameId & 0xffff, true);
  dv.setUint16(10, 0, true); // format 0 RGB565
  dv.setUint16(12, payloadBytes, true);
  dv.setUint16(14, 0, true);

  const out = new Uint8Array(buf, headerBytes);
  out.set(new Uint8Array(frame.buffer));
  return buf;
}
