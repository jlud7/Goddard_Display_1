import math
import random
from PIL import Image, ImageDraw
from .base import Provider


class ProceduralProvider(Provider):
    def image(self, prompt: str, seed: int | None = None) -> Image.Image:
        rng = random.Random(seed)
        prompt_l = prompt.lower()
        if "dragon" in prompt_l:
            return self._dragon_frame(t=0.0, rng=rng)
        if "mario" in prompt_l:
            return self._retro_plumber(rng=rng)
        if "metroid" in prompt_l:
            return self._metroid(rng=rng)
        if "zelda" in prompt_l:
            return self._zelda(rng=rng)
        if "pikachu" in prompt_l or "pokemon" in prompt_l:
            return self._pikachu(rng=rng)
        if "neon" in prompt_l:
            return self._neon_grid(rng=rng)
        if "sunset" in prompt_l or "sunrise" in prompt_l:
            return self._sunset(rng=rng)
        if "space" in prompt_l or "galaxy" in prompt_l:
            return self._galaxy(rng=rng)
        if "fire" in prompt_l or "flame" in prompt_l:
            return self._fire_frame(0.0, rng=rng)
        if "mountain" in prompt_l or "landscape" in prompt_l:
            return self._mountain(rng=rng)
        return self._abstract(prompt, rng=rng)

    def animation(self, prompt: str, frames: int, seed: int | None = None) -> list[Image.Image]:
        rng = random.Random(seed)
        prompt_l = prompt.lower()
        frames = max(2, frames)  # prevent division by zero
        denom = frames - 1
        if "dragon" in prompt_l and ("fire" in prompt_l or "breath" in prompt_l):
            return [self._dragon_frame(t=i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "rain" in prompt_l:
            return [self._rain_frame(i, rng=random.Random(seed)) for i in range(frames)]
        if "time" in prompt_l or "orbit" in prompt_l:
            return [self._clock_orbit_frame(i, frames, rng=random.Random(seed)) for i in range(frames)]
        if "fire" in prompt_l or "flame" in prompt_l:
            return [self._fire_frame(i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "neon" in prompt_l or "pulse" in prompt_l:
            return [self._neon_pulse_frame(i, frames, rng=random.Random(seed)) for i in range(frames)]
        if "star" in prompt_l or "space" in prompt_l:
            return [self._starfield_frame(i, frames, rng=random.Random(seed)) for i in range(frames)]
        # fallback: animated abstract
        return [self._abstract(prompt, rng=random.Random(rng.randint(0, 10_000_000))) for _ in range(frames)]

    # ---- Image generators ----

    def _dragon_frame(self, t: float, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 6, 12))
        d = ImageDraw.Draw(img)

        # Stars in background
        for _ in range(40):
            sx, sy = rng.randint(0, W), rng.randint(0, 60)
            brightness = rng.randint(60, 200)
            d.point((sx, sy), fill=(brightness, brightness, brightness + 30))

        # Moon with glow
        d.ellipse((175, 5, 235, 65), fill=(30, 35, 50))  # glow
        d.ellipse((180, 10, 230, 60), fill=(200, 210, 255))

        # Dragon silhouette
        bx, by = 60, 80
        body = [(bx - 10, by), (bx + 30, by - 30), (bx + 70, by - 25),
                (bx + 95, by - 10), (bx + 70, by + 15), (bx + 25, by + 10)]
        d.polygon(body, fill=(20, 30, 35))

        # Head
        d.ellipse((bx + 75, by - 45, bx + 115, by - 15), fill=(22, 34, 40))
        # Eye
        d.ellipse((bx + 95, by - 40, bx + 103, by - 32), fill=(255, 160, 40))
        d.ellipse((bx + 97, by - 38, bx + 101, by - 34), fill=(200, 40, 20))
        # Horn
        d.polygon([(bx + 92, by - 48), (bx + 102, by - 65), (bx + 110, by - 45)], fill=(25, 40, 45))

        # Wings
        d.polygon([(bx + 15, by - 20), (bx - 10, by - 55), (bx + 20, by - 60), (bx + 55, by - 35)], fill=(15, 25, 30))
        d.polygon([(bx + 35, by - 22), (bx + 10, by - 65), (bx + 45, by - 70), (bx + 75, by - 40)], fill=(14, 22, 28))

        # Fire breath (animated)
        mouth = (bx + 115, by - 30)
        fire_len = 110 + int(30 * math.sin(t * math.tau))
        flame_points = []
        for i in range(7):
            px = mouth[0] + (fire_len * i / 6)
            jitter = int(8 * math.sin(t * math.tau * 2 + i) + rng.randint(-2, 2))
            py = mouth[1] + jitter + int(10 * math.sin(t * math.tau + i * 0.7))
            flame_points.append((px, py))
        for i in range(6):
            c = (255, max(0, 180 - i * 18), 40 + i * 10)
            d.line(flame_points[i:i + 2], fill=c, width=18 - i * 2)
        # Sparks
        for _ in range(40):
            sx = mouth[0] + rng.randint(20, fire_len + 20)
            sy = mouth[1] + rng.randint(-25, 25)
            if rng.random() < 0.6:
                sz = rng.randint(1, 3)
                d.ellipse((sx, sy, sx + sz, sy + sz), fill=(255, rng.randint(180, 255), rng.randint(80, 160)))

        # Ground with gradient
        for gy in range(100, H):
            shade = int((gy - 100) / (H - 100) * 12)
            d.line((0, gy, W, gy), fill=(8 + shade, 10 + shade, 14 + shade))
        return img

    def _retro_plumber(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (92, 148, 252))  # sky blue
        d = ImageDraw.Draw(img)

        # Ground blocks
        for bx in range(0, W, 16):
            d.rectangle((bx, 96, bx + 15, 112), fill=(200, 76, 12))
            d.rectangle((bx, 112, bx + 15, H), fill=(148, 52, 8))

        # Question block
        d.rectangle((112, 48, 144, 80), fill=(252, 188, 60))
        d.rectangle((114, 50, 142, 78), fill=(228, 168, 40))
        d.rectangle((124, 56, 132, 72), fill=(255, 255, 255))  # ?

        # Clouds
        for cx in [40, 170]:
            d.ellipse((cx, 20, cx + 40, 45), fill=(255, 255, 255))
            d.ellipse((cx + 15, 12, cx + 55, 42), fill=(255, 255, 255))
            d.ellipse((cx + 30, 20, cx + 70, 45), fill=(255, 255, 255))

        # Character sprite
        x, y = 90, 48
        d.rectangle((x + 20, y, x + 60, y + 16), fill=(255, 0, 0))  # hat
        d.rectangle((x + 16, y + 4, x + 24, y + 12), fill=(255, 0, 0))  # hat brim
        d.rectangle((x + 24, y + 16, x + 56, y + 36), fill=(255, 200, 150))  # face
        d.rectangle((x + 32, y + 20, x + 44, y + 28), fill=(180, 120, 80))  # mustache
        d.rectangle((x + 16, y + 36, x + 64, y + 64), fill=(0, 0, 255))  # overalls
        d.rectangle((x + 24, y + 40, x + 56, y + 56), fill=(255, 0, 0))  # shirt
        d.rectangle((x + 12, y + 64, x + 36, y + 84), fill=(80, 48, 16))  # boot
        d.rectangle((x + 44, y + 64, x + 68, y + 84), fill=(80, 48, 16))  # boot

        # Pipe
        d.rectangle((200, 64, 240, 96), fill=(0, 168, 0))
        d.rectangle((196, 64, 244, 76), fill=(0, 200, 0))
        return img

    def _metroid(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (3, 3, 8))
        d = ImageDraw.Draw(img)

        # Starfield background
        for _ in range(60):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            bright = rng.randint(30, 120)
            d.point((sx, sy), fill=(bright, bright, bright + 20))

        # Outer glow
        for r in range(50, 30, -2):
            alpha = int(20 * (50 - r) / 20)
            d.ellipse((128 - r, 60 - r, 128 + r, 60 + r), fill=(alpha, alpha * 2, alpha * 3))

        # Main body
        d.ellipse((90, 20, 170, 100), fill=(40, 80, 160))
        d.ellipse((100, 30, 160, 90), fill=(60, 120, 220))
        d.ellipse((108, 38, 152, 82), fill=(120, 200, 255))

        # Nucleus
        d.ellipse((118, 50, 142, 70), fill=(200, 255, 255))

        # Tentacles with curve
        for i in range(8):
            x0, y0 = 130, 85
            mid_x = 50 + i * 22 + rng.randint(-5, 5)
            mid_y = 105 + rng.randint(-3, 3)
            x1 = 40 + i * 20 + rng.randint(-8, 8)
            y1 = 120 + rng.randint(-5, 5)
            d.line((x0, y0, mid_x, mid_y), fill=(200, 80, 220), width=8)
            d.line((mid_x, mid_y, x1, y1), fill=(160, 50, 180), width=5)
        return img

    def _zelda(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (12, 18, 10))
        d = ImageDraw.Draw(img)

        # Background foliage pattern
        for _ in range(200):
            gx = rng.randint(0, W)
            gy = rng.randint(0, H)
            gc = (rng.randint(8, 20), rng.randint(14, 28), rng.randint(6, 14))
            d.point((gx, gy), fill=gc)

        # Triforce
        cx, cy = 128, 50
        size = 55
        d.polygon([(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)], fill=(240, 200, 40))
        # Inner triangle cutout
        d.polygon([(cx, cy + 10), (cx - 25, cy + size), (cx + 25, cy + size)], fill=(12, 18, 10))

        # Glow
        for r in range(3):
            offset = r * 2
            d.polygon(
                [(cx, cy - size - offset), (cx - size - offset, cy + size + offset), (cx + size + offset, cy + size + offset)],
                outline=(240, 200, 40)
            )

        # Master Sword
        sx = 40
        d.rectangle((sx + 3, 15, sx + 9, 100), fill=(180, 190, 210))  # blade
        d.rectangle((sx + 1, 15, sx + 11, 20), fill=(200, 210, 230))  # tip
        d.rectangle((sx - 5, 72, sx + 17, 80), fill=(90, 60, 160))    # crossguard
        d.rectangle((sx + 2, 80, sx + 10, 105), fill=(60, 40, 120))   # grip
        d.ellipse((sx, 105, sx + 12, 115), fill=(200, 180, 40))       # pommel

        return img

    def _pikachu(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (30, 140, 50))  # grass green
        d = ImageDraw.Draw(img)

        # Sky gradient
        for y in range(60):
            shade = int(100 + y * 2)
            d.line((0, y, W, y), fill=(shade, min(255, shade + 40), 255))

        # Grass
        d.rectangle((0, 60, W, H), fill=(30, 140, 50))
        for _ in range(80):
            gx = rng.randint(0, W)
            gy = rng.randint(60, H)
            d.line((gx, gy, gx + rng.randint(-3, 3), gy - rng.randint(3, 10)), fill=(40, 160, 60), width=2)

        # Body
        d.rounded_rectangle((90, 35, 165, 115), radius=20, fill=(250, 220, 60))

        # Eyes
        d.ellipse((105, 55, 122, 72), fill=(0, 0, 0))
        d.ellipse((108, 58, 116, 66), fill=(255, 255, 255))  # highlight
        d.ellipse((135, 55, 152, 72), fill=(0, 0, 0))
        d.ellipse((138, 58, 146, 66), fill=(255, 255, 255))

        # Cheeks
        d.ellipse((96, 74, 118, 94), fill=(240, 80, 80))
        d.ellipse((140, 74, 162, 94), fill=(240, 80, 80))

        # Mouth
        d.arc((118, 78, 140, 92), start=0, end=180, fill=(100, 60, 20), width=2)

        # Nose
        d.ellipse((124, 72, 132, 78), fill=(80, 50, 20))

        # Ears
        d.polygon([(95, 40), (85, 5), (110, 30)], fill=(250, 220, 60))
        d.polygon([(85, 5), (95, 18), (80, 15)], fill=(40, 40, 40))
        d.polygon([(160, 40), (170, 5), (145, 30)], fill=(250, 220, 60))
        d.polygon([(170, 5), (160, 18), (175, 15)], fill=(40, 40, 40))

        # Tail
        d.polygon([(165, 65), (210, 40), (230, 55), (215, 70), (235, 85), (200, 95), (170, 80)], fill=(250, 220, 60))
        return img

    def _neon_grid(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 8))
        d = ImageDraw.Draw(img)

        # Perspective grid
        vanish_y = 40
        for x in range(0, W + 1, 20):
            d.line((W // 2, vanish_y, x, H), fill=(0, 80, 200), width=1)
        for y_step in range(8):
            y = vanish_y + int((H - vanish_y) * (y_step / 8) ** 1.5)
            d.line((0, y, W, y), fill=(0, 80, 200), width=1)

        # Neon sun
        cx, cy = W // 2, vanish_y
        for r in range(30, 0, -1):
            shade = int(255 * (30 - r) / 30)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(shade, 0, min(255, shade + 60)))

        # Horizontal glow lines
        colors = [(255, 0, 100), (255, 60, 0), (255, 180, 0)]
        for i, c in enumerate(colors):
            y = cy + 5 + i * 4
            d.line((cx - 35, y, cx + 35, y), fill=c, width=2)

        # Side towers
        for tx in [30, W - 50]:
            d.rectangle((tx, 60, tx + 20, H), fill=(10, 10, 30))
            for wy in range(65, H, 8):
                if rng.random() > 0.3:
                    d.rectangle((tx + 4, wy, tx + 8, wy + 3), fill=(200, 200, 50))
                if rng.random() > 0.3:
                    d.rectangle((tx + 12, wy, tx + 16, wy + 3), fill=(200, 200, 50))
        return img

    def _sunset(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)

        # Sky gradient
        sky_colors = [
            (20, 0, 60),     # deep purple
            (60, 10, 80),    # purple
            (140, 30, 60),   # magenta
            (220, 80, 40),   # orange
            (250, 160, 60),  # golden
            (250, 200, 120), # light gold
        ]
        for y in range(80):
            idx = y / 80 * (len(sky_colors) - 1)
            i0 = int(idx)
            i1 = min(i0 + 1, len(sky_colors) - 1)
            frac = idx - i0
            r = int(sky_colors[i0][0] * (1 - frac) + sky_colors[i1][0] * frac)
            g = int(sky_colors[i0][1] * (1 - frac) + sky_colors[i1][1] * frac)
            b = int(sky_colors[i0][2] * (1 - frac) + sky_colors[i1][2] * frac)
            d.line((0, y, W, y), fill=(r, g, b))

        # Sun
        d.ellipse((100, 40, 160, 100), fill=(255, 200, 80))
        # Sun reflection lines (retrowave style)
        for sy in range(55, 95, 5):
            gap = (sy - 55) // 5
            d.line((105, sy, 155, sy), fill=sky_colors[min(gap, len(sky_colors) - 1)], width=2)

        # Water
        for y in range(80, H):
            shade = int((y - 80) / (H - 80) * 40)
            d.line((0, y, W, y), fill=(10 + shade, 20 + shade, 60 + shade))

        # Sun reflection on water
        for y in range(82, H, 3):
            rw = max(1, 30 - (y - 82))
            d.line((128 - rw, y, 128 + rw, y), fill=(200, 140, 60), width=1)

        return img

    def _galaxy(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 6))
        d = ImageDraw.Draw(img)

        # Dense starfield
        for _ in range(300):
            sx, sy = rng.randint(0, W - 1), rng.randint(0, H - 1)
            brightness = rng.randint(30, 255)
            tint = rng.choice([(1, 1, 1), (1, 0.9, 0.8), (0.8, 0.9, 1)])
            d.point((sx, sy), fill=(
                int(brightness * tint[0]),
                int(brightness * tint[1]),
                int(brightness * tint[2]),
            ))

        # Spiral galaxy arms
        cx, cy = 128, 64
        for arm in range(2):
            offset = arm * math.pi
            for i in range(200):
                angle = offset + i * 0.06
                radius = 5 + i * 0.35
                jitter_r = rng.gauss(0, 3)
                jitter_a = rng.gauss(0, 0.1)
                x = cx + int((radius + jitter_r) * math.cos(angle + jitter_a))
                y = cy + int((radius + jitter_r) * 0.5 * math.sin(angle + jitter_a))
                if 0 <= x < W and 0 <= y < H:
                    bright = max(40, 255 - i)
                    color = rng.choice([
                        (bright, bright // 2, bright // 3),
                        (bright // 2, bright // 2, bright),
                        (bright, bright, bright),
                    ])
                    d.point((x, y), fill=color)

        # Bright core
        for r in range(15, 0, -1):
            v = int(255 * (15 - r) / 15)
            d.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), fill=(v, v, min(255, v + 30)))

        return img

    def _fire_frame(self, t: float, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 2, 0))
        d = ImageDraw.Draw(img)

        # Fire columns
        for x in range(0, W, 4):
            height = rng.randint(30, 90) + int(20 * math.sin(t * math.tau + x * 0.05))
            for y in range(H - 1, H - height, -1):
                progress = (H - y) / height
                if progress < 0.3:
                    color = (255, 240, 180)
                elif progress < 0.6:
                    color = (255, max(0, int(180 - progress * 200)), 20)
                else:
                    color = (max(0, int(200 - progress * 150)), max(0, int(40 - progress * 40)), 0)
                d.rectangle((x, y, x + 3, y + 1), fill=color)

        # Embers
        for _ in range(30):
            ex = rng.randint(0, W)
            ey = rng.randint(10, H - 30) - int(20 * t)
            if 0 <= ey < H:
                d.point((ex, ey), fill=(255, rng.randint(150, 255), rng.randint(50, 100)))
        return img

    def _mountain(self, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)

        # Sky gradient
        for y in range(H):
            frac = y / H
            r = int(40 + frac * 30)
            g = int(60 + frac * 40)
            b = int(120 - frac * 40)
            d.line((0, y, W, y), fill=(r, g, b))

        # Mountain layers (back to front)
        layers = [
            (70, (30, 40, 60)),
            (85, (40, 55, 50)),
            (100, (25, 45, 35)),
        ]
        for base_y, color in layers:
            points = [(0, H)]
            for x in range(0, W + 1, 8):
                peak = base_y - rng.randint(10, 45)
                points.append((x, peak))
            points.append((W, H))
            d.polygon(points, fill=color)

        # Snow caps on first layer
        for i in range(1, len(layers)):
            pass  # simplified

        # Moon
        d.ellipse((190, 15, 220, 45), fill=(220, 225, 240))

        # Trees in foreground
        for _ in range(15):
            tx = rng.randint(0, W)
            ty = rng.randint(90, 110)
            th = rng.randint(10, 25)
            d.rectangle((tx, ty - th, tx + 3, ty), fill=(15, 30, 15))
            d.polygon([(tx - 5, ty - th + 5), (tx + 8, ty - th + 5), (tx + 2, ty - th - 8)], fill=(20, 60, 25))

        return img

    # ---- Animation generators ----

    def _rain_frame(self, i: int, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 8, 16))
        d = ImageDraw.Draw(img)

        # Darker sky gradient
        for y in range(40):
            d.line((0, y, W, y), fill=(5 + y // 5, 8 + y // 5, 16 + y // 4))

        # Clouds
        for cx, cw in [(70, 120), (150, 100)]:
            d.ellipse((cx, 10, cx + cw // 2, 55), fill=(100, 110, 130))
            d.ellipse((cx + cw // 4, 0, cx + cw * 3 // 4, 60), fill=(110, 120, 140))
            d.ellipse((cx + cw // 2, 10, cx + cw, 55), fill=(100, 110, 130))
            d.rectangle((cx, 30, cx + cw, 60), fill=(105, 115, 135))

        # Rain streaks
        for x in range(0, W, 10):
            y = (i * 18 + (x * 3)) % H
            length = rng.randint(12, 22)
            d.line((x, y, x - 4, y + length), fill=(80, 150, 255), width=2)

        # Puddle reflections
        for px in range(0, W, 16):
            py = H - 10 + rng.randint(-3, 3)
            pw = rng.randint(8, 20)
            d.ellipse((px, py, px + pw, py + 4), fill=(15, 25, 45))
        return img

    def _clock_orbit_frame(self, i: int, n: int, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 6))
        d = ImageDraw.Draw(img)

        cx, cy = 128, 64

        # Orbit ring with glow
        for r_off in range(3, 0, -1):
            shade = 40 + (3 - r_off) * 20
            d.ellipse((cx - 40 - r_off, cy - 40 - r_off, cx + 40 + r_off, cy + 40 + r_off),
                      outline=(shade, shade, shade + 40), width=1)

        # Orbiting body
        ang = (i / n) * math.tau
        px = cx + int(math.cos(ang) * 40)
        py = cy + int(math.sin(ang) * 40)

        # Trail
        for trail in range(8):
            tang = ang - trail * 0.08
            tx = cx + int(math.cos(tang) * 40)
            ty = cy + int(math.sin(tang) * 40)
            fade = max(0, 200 - trail * 25)
            d.ellipse((tx - 4, ty - 4, tx + 4, ty + 4), fill=(fade, fade // 2, 0))

        # Planet
        d.ellipse((px - 8, py - 8, px + 8, py + 8), fill=(255, 200, 60))
        d.ellipse((px - 5, py - 5, px + 2, py + 2), fill=(255, 230, 120))

        # Center star
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(200, 200, 255))
        d.line((cx, cy - 10, cx, cy + 10), fill=(160, 160, 220), width=1)
        d.line((cx - 10, cy, cx + 10, cy), fill=(160, 160, 220), width=1)
        return img

    def _neon_pulse_frame(self, i: int, n: int, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 8))
        d = ImageDraw.Draw(img)
        t = i / n

        # Pulsing concentric rings
        cx, cy = W // 2, H // 2
        colors = [(255, 0, 80), (0, 200, 255), (180, 0, 255), (0, 255, 120)]
        for ring in range(6):
            r = int((t * 60 + ring * 15) % 80)
            if r < 5:
                continue
            cidx = ring % len(colors)
            fade = max(0, 255 - r * 3)
            c = tuple(int(v * fade / 255) for v in colors[cidx])
            d.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), outline=c, width=2)

        # Center glow
        phase = math.sin(t * math.tau) * 0.5 + 0.5
        v = int(200 * phase)
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(v, 0, v))
        return img

    def _starfield_frame(self, i: int, n: int, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (0, 0, 2))
        d = ImageDraw.Draw(img)

        cx, cy = W // 2, H // 2
        t = i / n

        # Warp-speed stars
        for s in range(100):
            angle = rng.uniform(0, math.tau)
            base_r = rng.uniform(5, 80)
            speed = 0.5 + rng.uniform(0, 1.5)
            r = (base_r + t * speed * 60) % 90
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * 0.5 * math.sin(angle))

            # Stretch based on distance from center
            stretch = max(1, int(r / 20))
            x2 = cx + int((r + stretch) * math.cos(angle))
            y2 = cy + int((r + stretch) * 0.5 * math.sin(angle))

            brightness = min(255, int(r * 3))
            d.line((x, y, x2, y2), fill=(brightness, brightness, min(255, brightness + 30)), width=1)
        return img

    def _abstract(self, prompt: str, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)

        # Create interesting abstract art based on prompt hash
        style = sum(ord(c) for c in prompt) % 3

        if style == 0:
            # Flowing curves
            for _ in range(20):
                points = []
                x, y = rng.randint(0, W), rng.randint(0, H)
                for _ in range(6):
                    x += rng.randint(-60, 60)
                    y += rng.randint(-30, 30)
                    points.append((max(0, min(W, x)), max(0, min(H, y))))
                col = (rng.randint(80, 255), rng.randint(80, 255), rng.randint(80, 255))
                if len(points) >= 2:
                    d.line(points, fill=col, width=rng.randint(3, 12))
        elif style == 1:
            # Geometric shapes
            for _ in range(15):
                cx, cy = rng.randint(20, W - 20), rng.randint(10, H - 10)
                r = rng.randint(8, 40)
                col = (rng.randint(80, 255), rng.randint(80, 255), rng.randint(80, 255))
                shape = rng.choice(["circle", "rect", "tri"])
                if shape == "circle":
                    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
                elif shape == "rect":
                    d.rectangle((cx - r, cy - r // 2, cx + r, cy + r // 2), fill=col)
                else:
                    d.polygon([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)], fill=col)
        else:
            # Noise gradient with accents
            for y_band in range(0, H, 4):
                for x_band in range(0, W, 4):
                    v = rng.randint(20, 80)
                    d.rectangle((x_band, y_band, x_band + 3, y_band + 3),
                                fill=(v + rng.randint(0, 40), v, v + rng.randint(0, 60)))
            # Bright accent spots
            for _ in range(8):
                ax, ay = rng.randint(20, W - 20), rng.randint(10, H - 10)
                ar = rng.randint(5, 15)
                d.ellipse((ax - ar, ay - ar, ax + ar, ay + ar),
                          fill=(rng.randint(200, 255), rng.randint(100, 255), rng.randint(100, 255)))
        return img
