import math
import random
import re
from PIL import Image, ImageDraw
from .base import Provider


# ---------------------------------------------------------------------------
# Smart keyword extraction & routing
# ---------------------------------------------------------------------------
# Maps natural-language prompts to the best generator.  Each entry is
# (list-of-regex-patterns, generator-method-name, optional-extra-kwargs).
# First match wins — order matters (specific before general).

_ROUTE_TABLE: list[tuple[list[str], str, dict]] = [
    # ---------- Characters / creatures ----------
    (["charmander", "fire.?lizard"],                "_charmander",     {}),
    (["pikachu"],                                    "_pikachu",        {}),
    (["pokemon", "pok[eé]mon"],                      "_pikachu",        {}),
    (["mario", "plumber"],                           "_retro_plumber",  {}),
    (["metroid", "samus"],                           "_metroid",        {}),
    (["zelda", "link", "triforce"],                  "_zelda",          {}),
    (["dragon"],                                     "_dragon_frame",   {"t": 0.0}),
    (["cat", "kitten", "kitty"],                     "_cat",            {}),
    (["dog", "puppy", "pupper"],                     "_dog",            {}),
    (["fish", "goldfish", "aquarium"],               "_fish",           {}),
    (["owl", "bird"],                                "_owl",            {}),
    (["robot", "mech", "android"],                   "_robot",          {}),
    (["skull", "skeleton"],                          "_skull",          {}),
    (["ghost", "boo", "spooky"],                     "_ghost",          {}),
    (["alien", "ufo"],                               "_alien",          {}),
    (["mushroom", "toadstool", "1up", "1-up"],       "_mushroom",       {}),

    # ---------- Food ----------
    (["pizza"],                                      "_pizza",          {}),
    (["burger", "hamburger", "cheeseburger"],        "_burger",         {}),
    (["taco"],                                       "_taco",           {}),
    (["sushi"],                                      "_sushi",          {}),
    (["donut", "doughnut"],                          "_donut",          {}),
    (["cake", "birthday"],                           "_cake",           {}),
    (["ice.?cream", "sundae", "cone"],               "_ice_cream",      {}),
    (["coffee", "latte", "espresso", "cup"],         "_coffee",         {}),
    (["fruit", "apple", "watermelon"],               "_fruit",          {}),
    (["ramen", "noodle", "soup"],                    "_ramen",          {}),

    # ---------- Objects ----------
    (["heart", "love", "valentine"],                 "_heart",          {}),
    (["star(?!field)", "shooting.?star"],             "_star_object",    {}),
    (["moon", "crescent", "lunar"],                  "_moon_scene",     {}),
    (["sword", "blade", "weapon"],                   "_sword",          {}),
    (["crown", "king", "queen", "royal"],            "_crown",          {}),
    (["gem", "diamond", "crystal", "jewel"],         "_gem",            {}),
    (["tree", "forest", "woods"],                    "_tree",           {}),
    (["flower", "rose", "daisy", "tulip"],           "_flower",         {}),
    (["car", "auto", "vehicle"],                     "_car",            {}),
    (["rocket", "spaceship", "ship"],                "_rocket",         {}),
    (["house", "home", "cottage"],                   "_house",          {}),
    (["flag", "banner"],                             "_flag",           {}),

    # ---------- Scenes ----------
    (["neon"],                                       "_neon_grid",      {}),
    (["sunset", "sunrise"],                          "_sunset",         {}),
    (["space", "galaxy", "cosmos", "nebula"],        "_galaxy",         {}),
    (["fire", "flame", "blaze", "inferno"],          "_fire_frame",     {"t": 0.0}),
    (["mountain", "landscape", "cliff"],             "_mountain",       {}),
    (["ocean", "sea", "wave", "beach"],              "_ocean",          {}),
    (["city", "skyline", "building"],                "_cityscape",      {}),
    (["rainbow"],                                    "_rainbow_scene",  {}),
    (["snow", "winter", "christmas", "xmas"],        "_snow_scene",     {}),
    (["rain", "storm", "thunder"],                   "_rain_frame",     {"i": 0}),
]


def _match_prompt(prompt: str) -> tuple[str, dict] | None:
    """Return (method_name, kwargs) for the first matching route, or None."""
    lower = prompt.lower().strip()
    for patterns, method, kwargs in _ROUTE_TABLE:
        for pat in patterns:
            if re.search(pat, lower):
                return method, kwargs
    return None


class ProceduralProvider(Provider):
    def image(self, prompt: str, seed: int | None = None) -> Image.Image:
        rng = random.Random(seed)
        match = _match_prompt(prompt)
        if match:
            method_name, kwargs = match
            method = getattr(self, method_name)
            return method(rng=rng, **kwargs)
        return self._abstract(prompt, rng=rng)

    def animation(self, prompt: str, frames: int, seed: int | None = None) -> list[Image.Image]:
        rng = random.Random(seed)
        prompt_l = prompt.lower()
        frames = max(2, frames)
        denom = frames - 1

        # Animated versions for specific prompts
        if "dragon" in prompt_l and ("fire" in prompt_l or "breath" in prompt_l):
            return [self._dragon_frame(t=i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "charmander" in prompt_l:
            return [self._charmander_anim(t=i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "rain" in prompt_l or "storm" in prompt_l:
            return [self._rain_frame(i=i, rng=random.Random(seed)) for i in range(frames)]
        if "time" in prompt_l or "orbit" in prompt_l:
            return [self._clock_orbit_frame(i, frames, rng=random.Random(seed)) for i in range(frames)]
        if "fire" in prompt_l or "flame" in prompt_l:
            return [self._fire_frame(t=i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "neon" in prompt_l or "pulse" in prompt_l:
            return [self._neon_pulse_frame(i, frames, rng=random.Random(seed)) for i in range(frames)]
        if "star" in prompt_l or "space" in prompt_l or "warp" in prompt_l:
            return [self._starfield_frame(i, frames, rng=random.Random(seed)) for i in range(frames)]
        if "ocean" in prompt_l or "wave" in prompt_l or "sea" in prompt_l:
            return [self._ocean_anim(t=i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "snow" in prompt_l or "winter" in prompt_l:
            return [self._snow_anim(i=i, rng=random.Random(seed)) for i in range(frames)]
        if "heart" in prompt_l or "love" in prompt_l:
            return [self._heart_anim(t=i / denom, rng=random.Random(seed)) for i in range(frames)]
        if "rainbow" in prompt_l:
            return [self._rainbow_anim(t=i / denom, rng=random.Random(seed)) for i in range(frames)]

        # Fallback: try to generate a static match and do a gentle bob/glow animation
        match = _match_prompt(prompt)
        if match:
            method_name, kwargs = match
            method = getattr(self, method_name)
            return [method(rng=random.Random((seed or 0) + i), **kwargs) for i in range(frames)]

        return [self._abstract(prompt, rng=random.Random(rng.randint(0, 10_000_000))) for _ in range(frames)]


    # ====================================================================
    # CHARACTER / CREATURE GENERATORS
    # ====================================================================

    def _charmander(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (40, 120, 180))  # sky blue
        d = ImageDraw.Draw(img)

        # Ground
        d.rectangle((0, 95, W, H), fill=(80, 160, 60))
        for _ in range(60):
            gx, gy = rng.randint(0, W), rng.randint(95, H)
            d.line((gx, gy, gx + rng.randint(-2, 2), gy - rng.randint(2, 6)), fill=(60, 140, 45), width=1)

        # Body - orange lizard
        cx, cy = 128, 60
        # Belly
        d.rounded_rectangle((cx - 25, cy - 15, cx + 25, cy + 30), radius=14, fill=(255, 160, 50))
        # Lighter belly center
        d.rounded_rectangle((cx - 14, cy - 5, cx + 14, cy + 22), radius=10, fill=(255, 210, 120))
        # Head
        d.ellipse((cx - 22, cy - 40, cx + 22, cy - 8), fill=(255, 160, 50))
        # Eyes
        d.ellipse((cx - 16, cy - 32, cx - 6, cy - 20), fill=(255, 255, 255))
        d.ellipse((cx - 14, cy - 30, cx - 8, cy - 22), fill=(20, 20, 20))
        d.ellipse((cx + 6, cy - 32, cx + 16, cy - 20), fill=(255, 255, 255))
        d.ellipse((cx + 8, cy - 30, cx + 14, cy - 22), fill=(20, 20, 20))
        # Mouth - happy
        d.arc((cx - 8, cy - 18, cx + 8, cy - 10), start=0, end=180, fill=(80, 40, 20), width=2)
        # Arms
        d.rounded_rectangle((cx - 38, cy + 2, cx - 22, cy + 20), radius=4, fill=(255, 145, 40))
        d.rounded_rectangle((cx + 22, cy + 2, cx + 38, cy + 20), radius=4, fill=(255, 145, 40))
        # Legs
        d.rounded_rectangle((cx - 18, cy + 25, cx - 6, cy + 42), radius=4, fill=(255, 145, 40))
        d.rounded_rectangle((cx + 6, cy + 25, cx + 18, cy + 42), radius=4, fill=(255, 145, 40))
        # Feet
        d.ellipse((cx - 22, cy + 36, cx - 4, cy + 46), fill=(255, 145, 40))
        d.ellipse((cx + 4, cy + 36, cx + 22, cy + 46), fill=(255, 145, 40))
        # Tail with flame
        tail = [(cx + 25, cy + 15), (cx + 45, cy + 5), (cx + 55, cy - 5), (cx + 50, cy + 10)]
        d.line(tail, fill=(255, 145, 40), width=8)
        # Flame on tail tip
        fx, fy = cx + 55, cy - 8
        d.ellipse((fx - 6, fy - 10, fx + 6, fy + 2), fill=(255, 60, 20))
        d.ellipse((fx - 4, fy - 14, fx + 4, fy - 2), fill=(255, 180, 40))
        d.ellipse((fx - 2, fy - 12, fx + 2, fy - 4), fill=(255, 255, 100))
        return img

    def _charmander_anim(self, t: float, rng: random.Random) -> Image.Image:
        img = self._charmander(rng=rng)
        d = ImageDraw.Draw(img)
        cx, cy = 128, 60
        # Animated fire breath from mouth
        mouth_x, mouth_y = cx + 10, cy - 14
        fire_len = 60 + int(30 * math.sin(t * math.tau))
        for i in range(8):
            px = mouth_x + (fire_len * i / 7)
            jitter = int(6 * math.sin(t * math.tau * 2 + i) + rng.randint(-2, 2))
            py = mouth_y + jitter
            c = (255, max(0, 200 - i * 20), max(0, 60 - i * 8))
            sz = max(2, 14 - i * 2)
            d.ellipse((int(px - sz), int(py - sz), int(px + sz), int(py + sz)), fill=c)
        # Sparks
        for _ in range(20):
            sx = mouth_x + rng.randint(10, fire_len + 10)
            sy = mouth_y + rng.randint(-15, 15)
            d.point((int(sx), int(sy)), fill=(255, rng.randint(180, 255), rng.randint(50, 120)))
        return img

    def _cat(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        bg = rng.choice([(180, 200, 220), (220, 180, 180), (200, 220, 180)])
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        # Floor
        d.rectangle((0, 90, W, H), fill=(160, 140, 120))
        cx, cy = 128, 55
        fur = rng.choice([(255, 160, 50), (80, 80, 80), (255, 255, 255), (200, 120, 60)])
        # Body
        d.ellipse((cx - 28, cy - 10, cx + 28, cy + 30), fill=fur)
        # Head
        d.ellipse((cx - 20, cy - 35, cx + 20, cy - 2), fill=fur)
        # Ears
        d.polygon([(cx - 18, cy - 30), (cx - 24, cy - 50), (cx - 6, cy - 35)], fill=fur)
        d.polygon([(cx + 18, cy - 30), (cx + 24, cy - 50), (cx + 6, cy - 35)], fill=fur)
        inner = tuple(min(255, c + 60) for c in fur)
        d.polygon([(cx - 16, cy - 30), (cx - 20, cy - 44), (cx - 8, cy - 33)], fill=inner)
        d.polygon([(cx + 16, cy - 30), (cx + 20, cy - 44), (cx + 8, cy - 33)], fill=inner)
        # Eyes
        d.ellipse((cx - 14, cy - 24, cx - 4, cy - 14), fill=(100, 200, 100))
        d.ellipse((cx - 11, cy - 21, cx - 7, cy - 17), fill=(20, 20, 20))
        d.ellipse((cx + 4, cy - 24, cx + 14, cy - 14), fill=(100, 200, 100))
        d.ellipse((cx + 7, cy - 21, cx + 11, cy - 17), fill=(20, 20, 20))
        # Nose & mouth
        d.polygon([(cx - 3, cy - 12), (cx + 3, cy - 12), (cx, cy - 8)], fill=(255, 150, 150))
        d.line((cx, cy - 8, cx - 4, cy - 4), fill=(60, 40, 40), width=1)
        d.line((cx, cy - 8, cx + 4, cy - 4), fill=(60, 40, 40), width=1)
        # Whiskers
        for side in [-1, 1]:
            for angle in [-10, 0, 10]:
                wx = cx + side * 18
                wy = cy - 10 + angle
                d.line((cx + side * 6, cy - 10, wx, wy), fill=(60, 40, 40), width=1)
        # Tail
        pts = [(cx + 28, cy + 15)]
        for i in range(5):
            pts.append((cx + 35 + i * 6, cy + 10 - int(8 * math.sin(i * 0.8))))
        d.line(pts, fill=fur, width=6)
        # Paws
        for px in [cx - 16, cx + 10]:
            d.ellipse((px, cy + 26, px + 12, cy + 34), fill=fur)
        return img

    def _dog(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (140, 200, 240))
        d = ImageDraw.Draw(img)
        d.rectangle((0, 90, W, H), fill=(120, 180, 80))
        cx, cy = 128, 52
        fur = rng.choice([(200, 150, 80), (180, 120, 60), (255, 255, 240), (100, 70, 40)])
        # Body
        d.ellipse((cx - 32, cy - 5, cx + 32, cy + 35), fill=fur)
        # Head
        d.ellipse((cx - 22, cy - 38, cx + 22, cy), fill=fur)
        # Snout
        d.ellipse((cx - 12, cy - 18, cx + 12, cy), fill=tuple(min(255, c + 40) for c in fur))
        # Nose
        d.ellipse((cx - 5, cy - 16, cx + 5, cy - 8), fill=(30, 20, 20))
        # Eyes
        d.ellipse((cx - 16, cy - 30, cx - 6, cy - 20), fill=(40, 30, 20))
        d.ellipse((cx - 14, cy - 28, cx - 8, cy - 22), fill=(255, 255, 255))
        d.ellipse((cx + 6, cy - 30, cx + 16, cy - 20), fill=(40, 30, 20))
        d.ellipse((cx + 8, cy - 28, cx + 14, cy - 22), fill=(255, 255, 255))
        # Ears (floppy)
        d.ellipse((cx - 30, cy - 32, cx - 14, cy - 6), fill=tuple(max(0, c - 30) for c in fur))
        d.ellipse((cx + 14, cy - 32, cx + 30, cy - 6), fill=tuple(max(0, c - 30) for c in fur))
        # Mouth
        d.arc((cx - 6, cy - 10, cx + 6, cy - 2), start=0, end=180, fill=(80, 40, 20), width=2)
        # Tongue
        d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(255, 120, 120))
        # Legs
        for lx in [cx - 20, cx - 8, cx + 8, cx + 16]:
            d.rectangle((lx, cy + 30, lx + 8, cy + 44), fill=fur)
            d.ellipse((lx - 1, cy + 40, lx + 9, cy + 46), fill=fur)
        # Tail
        d.arc((cx + 25, cy - 10, cx + 55, cy + 20), start=180, end=340, fill=fur, width=6)
        return img

    def _fish(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (20, 60, 120))
        d = ImageDraw.Draw(img)
        # Water gradient
        for y in range(H):
            shade = int(20 + y * 0.3)
            d.line((0, y, W, y), fill=(shade, 60 + shade // 2, 120 + shade // 3))
        # Bubbles
        for _ in range(15):
            bx, by = rng.randint(10, W - 10), rng.randint(5, H - 20)
            br = rng.randint(3, 8)
            d.ellipse((bx - br, by - br, bx + br, by + br), outline=(100, 180, 255), width=1)
        # Fish body
        cx, cy = 128, 64
        body_col = rng.choice([(255, 140, 30), (255, 60, 60), (60, 180, 255), (255, 200, 40)])
        d.ellipse((cx - 40, cy - 18, cx + 30, cy + 18), fill=body_col)
        # Tail
        d.polygon([(cx + 25, cy), (cx + 50, cy - 20), (cx + 50, cy + 20)], fill=body_col)
        # Fin
        d.polygon([(cx - 5, cy - 18), (cx + 5, cy - 35), (cx + 15, cy - 15)], fill=tuple(max(0, c - 40) for c in body_col))
        # Eye
        d.ellipse((cx - 28, cy - 10, cx - 14, cy + 4), fill=(255, 255, 255))
        d.ellipse((cx - 24, cy - 6, cx - 18, cy), fill=(20, 20, 20))
        # Mouth
        d.arc((cx - 38, cy - 4, cx - 28, cy + 6), start=30, end=150, fill=(40, 20, 20), width=2)
        # Scales pattern
        for sx in range(cx - 20, cx + 20, 8):
            for sy in range(cy - 10, cy + 10, 8):
                d.arc((sx, sy, sx + 8, sy + 8), start=0, end=180,
                      outline=tuple(min(255, c + 30) for c in body_col), width=1)
        # Seaweed
        for sx in [30, 80, 180, 220]:
            for seg in range(8):
                y0 = H - seg * 12
                y1 = H - (seg + 1) * 12
                sway = int(6 * math.sin(seg * 0.5 + sx * 0.01))
                d.line((sx + sway, max(0, y0), sx + sway + 3, max(0, y1)), fill=(30, 120, 40), width=4)
        return img

    def _owl(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (15, 15, 40))
        d = ImageDraw.Draw(img)
        # Stars
        for _ in range(50):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            d.point((sx, sy), fill=(rng.randint(100, 255),) * 3)
        # Moon
        d.ellipse((180, 10, 220, 50), fill=(220, 225, 240))
        # Branch
        d.rectangle((60, 85, 200, 92), fill=(80, 50, 30))
        # Owl body
        cx, cy = 130, 55
        d.ellipse((cx - 22, cy - 8, cx + 22, cy + 30), fill=(140, 100, 60))
        # Head
        d.ellipse((cx - 20, cy - 32, cx + 20, cy), fill=(140, 100, 60))
        # Ear tufts
        d.polygon([(cx - 16, cy - 30), (cx - 22, cy - 48), (cx - 8, cy - 28)], fill=(120, 85, 50))
        d.polygon([(cx + 16, cy - 30), (cx + 22, cy - 48), (cx + 8, cy - 28)], fill=(120, 85, 50))
        # Face disk
        d.ellipse((cx - 16, cy - 26, cx + 16, cy - 2), fill=(170, 140, 90))
        # Eyes - big round
        for ex in [cx - 10, cx + 4]:
            d.ellipse((ex, cy - 22, ex + 12, cy - 10), fill=(255, 200, 40))
            d.ellipse((ex + 3, cy - 19, ex + 9, cy - 13), fill=(20, 20, 20))
        # Beak
        d.polygon([(cx - 3, cy - 10), (cx + 3, cy - 10), (cx, cy - 4)], fill=(200, 160, 60))
        # Wings
        d.ellipse((cx - 35, cy - 5, cx - 15, cy + 25), fill=(120, 85, 50))
        d.ellipse((cx + 15, cy - 5, cx + 35, cy + 25), fill=(120, 85, 50))
        # Feet
        for fx in [cx - 10, cx + 4]:
            d.ellipse((fx, cy + 28, fx + 12, cy + 34), fill=(200, 160, 60))
        return img

    def _robot(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (30, 30, 45))
        d = ImageDraw.Draw(img)
        # Grid bg
        for x in range(0, W, 16):
            d.line((x, 0, x, H), fill=(40, 40, 55), width=1)
        for y in range(0, H, 16):
            d.line((0, y, W, y), fill=(40, 40, 55), width=1)
        cx, cy = 128, 50
        # Body
        d.rounded_rectangle((cx - 25, cy + 5, cx + 25, cy + 45), radius=5, fill=(150, 160, 180))
        d.rounded_rectangle((cx - 20, cy + 10, cx + 20, cy + 40), radius=3, fill=(100, 110, 130))
        # Chest lights
        for i, c in enumerate([(255, 60, 60), (255, 200, 40), (60, 255, 60)]):
            d.ellipse((cx - 12 + i * 10, cy + 15, cx - 6 + i * 10, cy + 21), fill=c)
        # Head
        d.rounded_rectangle((cx - 20, cy - 25, cx + 20, cy + 8), radius=6, fill=(170, 180, 200))
        # Eyes - LED style
        d.rectangle((cx - 14, cy - 18, cx - 4, cy - 8), fill=(0, 200, 255))
        d.rectangle((cx + 4, cy - 18, cx + 14, cy - 8), fill=(0, 200, 255))
        # Antenna
        d.line((cx, cy - 25, cx, cy - 40), fill=(150, 160, 180), width=3)
        d.ellipse((cx - 4, cy - 44, cx + 4, cy - 36), fill=(255, 60, 60))
        # Arms
        d.rectangle((cx - 35, cy + 10, cx - 25, cy + 35), fill=(140, 150, 170))
        d.rectangle((cx + 25, cy + 10, cx + 35, cy + 35), fill=(140, 150, 170))
        # Claws
        d.rectangle((cx - 38, cy + 32, cx - 25, cy + 40), fill=(120, 130, 150))
        d.rectangle((cx + 25, cy + 32, cx + 38, cy + 40), fill=(120, 130, 150))
        # Legs
        d.rectangle((cx - 16, cy + 45, cx - 6, cy + 62), fill=(140, 150, 170))
        d.rectangle((cx + 6, cy + 45, cx + 16, cy + 62), fill=(140, 150, 170))
        # Feet
        d.rectangle((cx - 20, cy + 60, cx - 4, cy + 66), fill=(120, 130, 150))
        d.rectangle((cx + 4, cy + 60, cx + 20, cy + 66), fill=(120, 130, 150))
        return img

    def _skull(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (15, 10, 20))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 50
        # Glow
        for r in range(50, 30, -2):
            v = int(15 * (50 - r) / 20)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(v, v // 2, v))
        # Skull shape
        d.ellipse((cx - 30, cy - 35, cx + 30, cy + 10), fill=(230, 225, 210))
        d.rectangle((cx - 20, cy + 5, cx + 20, cy + 25), fill=(230, 225, 210))
        # Eye sockets
        d.ellipse((cx - 20, cy - 20, cx - 4, cy - 4), fill=(15, 10, 20))
        d.ellipse((cx + 4, cy - 20, cx + 20, cy - 4), fill=(15, 10, 20))
        # Eye glow
        d.ellipse((cx - 16, cy - 16, cx - 8, cy - 8), fill=(255, 40, 40))
        d.ellipse((cx + 8, cy - 16, cx + 16, cy - 8), fill=(255, 40, 40))
        # Nose
        d.polygon([(cx - 4, cy), (cx + 4, cy), (cx, cy + 8)], fill=(15, 10, 20))
        # Teeth
        for tx in range(cx - 16, cx + 16, 8):
            d.rectangle((tx, cy + 20, tx + 6, cy + 30), fill=(230, 225, 210))
            d.line((tx + 3, cy + 20, tx + 3, cy + 30), fill=(180, 175, 160), width=1)
        # Jaw line
        d.arc((cx - 22, cy + 10, cx + 22, cy + 35), start=0, end=180, fill=(200, 195, 180), width=2)
        return img

    def _ghost(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (20, 15, 40))
        d = ImageDraw.Draw(img)
        # Spooky background
        for _ in range(30):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            d.point((sx, sy), fill=(rng.randint(40, 80),) * 3)
        cx, cy = 128, 45
        # Ghost body
        d.ellipse((cx - 28, cy - 30, cx + 28, cy + 10), fill=(220, 220, 240))
        d.rectangle((cx - 28, cy - 5, cx + 28, cy + 35), fill=(220, 220, 240))
        # Wavy bottom
        for i in range(8):
            x0 = cx - 28 + i * 8
            peak = cy + 35 + (8 if i % 2 == 0 else 0)
            d.ellipse((x0 - 1, cy + 28, x0 + 8, peak), fill=(220, 220, 240))
        # Eyes
        d.ellipse((cx - 16, cy - 14, cx - 4, cy + 2), fill=(20, 15, 40))
        d.ellipse((cx + 4, cy - 14, cx + 16, cy + 2), fill=(20, 15, 40))
        # Mouth
        d.ellipse((cx - 6, cy + 6, cx + 6, cy + 16), fill=(20, 15, 40))
        # Glow around ghost
        for r in range(40, 28, -1):
            v = int(20 * (40 - r) / 12)
            d.ellipse((cx - r, cy - r + 5, cx + r, cy + r + 5), outline=(v, v, v + 10), width=1)
        return img

    def _alien(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 5, 15))
        d = ImageDraw.Draw(img)
        # Stars
        for _ in range(80):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            d.point((sx, sy), fill=(rng.randint(60, 200),) * 3)
        cx, cy = 128, 50
        # Alien body - classic grey
        skin = (140, 180, 140)
        d.ellipse((cx - 18, cy + 5, cx + 18, cy + 40), fill=skin)
        # Head - big
        d.ellipse((cx - 28, cy - 38, cx + 28, cy + 10), fill=skin)
        # Eyes - huge almond shape
        d.ellipse((cx - 24, cy - 20, cx - 2, cy + 2), fill=(20, 20, 20))
        d.ellipse((cx - 22, cy - 18, cx - 6, cy - 2), fill=(30, 60, 30))
        d.ellipse((cx + 2, cy - 20, cx + 24, cy + 2), fill=(20, 20, 20))
        d.ellipse((cx + 6, cy - 18, cx + 22, cy - 2), fill=(30, 60, 30))
        # Mouth - tiny
        d.line((cx - 3, cy + 5, cx + 3, cy + 5), fill=(100, 120, 100), width=1)
        # Arms
        d.line((cx - 18, cy + 15, cx - 35, cy + 30), fill=skin, width=5)
        d.line((cx + 18, cy + 15, cx + 35, cy + 30), fill=skin, width=5)
        # Legs
        d.line((cx - 8, cy + 38, cx - 14, cy + 55), fill=skin, width=4)
        d.line((cx + 8, cy + 38, cx + 14, cy + 55), fill=skin, width=4)
        return img

    def _mushroom(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (92, 148, 252))
        d = ImageDraw.Draw(img)
        # Ground
        d.rectangle((0, 90, W, H), fill=(80, 160, 60))
        cx, cy = 128, 50
        # Stem
        d.rounded_rectangle((cx - 14, cy + 5, cx + 14, cy + 40), radius=6, fill=(240, 230, 200))
        # Eyes on stem
        d.ellipse((cx - 10, cy + 12, cx - 2, cy + 22), fill=(20, 20, 20))
        d.ellipse((cx + 2, cy + 12, cx + 10, cy + 22), fill=(20, 20, 20))
        # Cap
        d.ellipse((cx - 30, cy - 20, cx + 30, cy + 12), fill=(255, 30, 30))
        # White spots
        spots = [(-15, -10, 8), (10, -8, 6), (0, -18, 7), (-8, 0, 5), (14, 2, 5)]
        for sx, sy, sr in spots:
            d.ellipse((cx + sx - sr, cy + sy - sr, cx + sx + sr, cy + sy + sr), fill=(255, 255, 255))
        return img

    # ====================================================================
    # FOOD GENERATORS
    # ====================================================================

    def _pizza(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (60, 30, 15))
        d = ImageDraw.Draw(img)
        # Checkered tablecloth bg
        for x in range(0, W, 16):
            for y in range(0, H, 16):
                if (x // 16 + y // 16) % 2 == 0:
                    d.rectangle((x, y, x + 15, y + 15), fill=(200, 40, 40))
                else:
                    d.rectangle((x, y, x + 15, y + 15), fill=(255, 255, 255))
        cx, cy = 128, 64
        # Pizza base - circular
        d.ellipse((cx - 50, cy - 40, cx + 50, cy + 40), fill=(200, 160, 80))  # crust
        d.ellipse((cx - 42, cy - 34, cx + 42, cy + 34), fill=(220, 60, 30))   # sauce
        d.ellipse((cx - 40, cy - 32, cx + 40, cy + 32), fill=(255, 210, 80))  # cheese
        # Pepperoni
        pepperoni_spots = [(-20, -15), (10, -10), (-5, 10), (18, 8), (-15, 5), (5, -22), (20, -5)]
        for px, py in pepperoni_spots:
            d.ellipse((cx + px - 6, cy + py - 5, cx + px + 6, cy + py + 5), fill=(180, 30, 20))
            d.ellipse((cx + px - 4, cy + py - 3, cx + px + 4, cy + py + 3), fill=(200, 50, 30))
        # Cheese stretches
        for _ in range(5):
            sx = cx + rng.randint(-30, 30)
            sy = cy + rng.randint(-20, 20)
            d.line((sx, sy, sx + rng.randint(-4, 4), sy + rng.randint(3, 8)), fill=(255, 230, 120), width=2)
        return img

    def _burger(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (240, 220, 180))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 64
        # Top bun
        d.ellipse((cx - 40, cy - 40, cx + 40, cy - 10), fill=(200, 140, 50))
        d.ellipse((cx - 38, cy - 38, cx + 38, cy - 14), fill=(220, 160, 60))
        # Sesame seeds
        for _ in range(8):
            sx = cx + rng.randint(-28, 28)
            sy = cy + rng.randint(-36, -18)
            d.ellipse((sx - 2, sy - 1, sx + 2, sy + 1), fill=(255, 240, 200))
        # Lettuce
        for lx in range(cx - 42, cx + 42, 6):
            ly = cy - 10
            d.arc((lx, ly - 4, lx + 10, ly + 6), start=0, end=180, fill=(60, 180, 40), width=3)
        # Tomato
        d.rectangle((cx - 38, cy - 6, cx + 38, cy + 2), fill=(220, 50, 30))
        # Cheese (draped)
        pts = [(cx - 40, cy + 2)]
        for i in range(9):
            x = cx - 40 + i * 10
            y = cy + 4 + (6 if i % 2 == 0 else 0)
            pts.append((x, y))
        pts.append((cx + 40, cy + 2))
        d.polygon(pts + [(cx + 40, cy + 2), (cx - 40, cy + 2)], fill=(255, 200, 40))
        # Patty
        d.rounded_rectangle((cx - 38, cy + 4, cx + 38, cy + 20), radius=4, fill=(120, 60, 30))
        # Char marks
        for i in range(cx - 30, cx + 30, 12):
            d.line((i, cy + 8, i + 8, cy + 8), fill=(80, 40, 15), width=2)
        # Bottom bun
        d.rounded_rectangle((cx - 40, cy + 18, cx + 40, cy + 38), radius=8, fill=(200, 140, 50))
        return img

    def _taco(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (255, 230, 180))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 64
        # Shell
        d.ellipse((cx - 50, cy - 30, cx + 50, cy + 40), fill=(220, 180, 80))
        d.ellipse((cx - 46, cy - 20, cx + 46, cy + 50), fill=(255, 230, 180))  # cutout
        # Meat
        d.ellipse((cx - 35, cy - 18, cx + 35, cy + 5), fill=(160, 80, 30))
        # Lettuce
        for i in range(-3, 4):
            lx = cx + i * 10
            d.ellipse((lx - 8, cy - 25, lx + 8, cy - 12), fill=(80, 200, 60))
        # Cheese shreds
        for _ in range(10):
            sx = cx + rng.randint(-25, 25)
            sy = cy + rng.randint(-20, -5)
            d.line((sx, sy, sx + rng.randint(-3, 3), sy + rng.randint(4, 10)), fill=(255, 210, 40), width=2)
        # Tomato chunks
        for _ in range(5):
            tx = cx + rng.randint(-20, 20)
            ty = cy + rng.randint(-22, -8)
            d.rectangle((tx - 3, ty - 3, tx + 3, ty + 3), fill=(220, 50, 30))
        return img

    def _sushi(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (40, 30, 25))
        d = ImageDraw.Draw(img)
        # Wooden board
        for y in range(30, 100, 2):
            shade = 60 + (y - 30) // 4
            d.line((40, y, 216, y), fill=(shade + 40, shade + 20, shade))
        pieces = [(80, 65), (128, 65), (176, 65)]
        for px, py in pieces:
            style = rng.choice(["nigiri", "maki", "nigiri"])
            if style == "nigiri":
                # Rice
                d.rounded_rectangle((px - 16, py - 6, px + 16, py + 10), radius=4, fill=(255, 250, 240))
                # Fish on top
                fish_col = rng.choice([(255, 120, 80), (255, 80, 60), (255, 160, 100)])
                d.rounded_rectangle((px - 18, py - 14, px + 18, py - 2), radius=6, fill=fish_col)
                # Shine
                d.line((px - 10, py - 12, px + 5, py - 10), fill=tuple(min(255, c + 50) for c in fish_col), width=1)
            else:
                # Nori wrap
                d.ellipse((px - 14, py - 14, px + 14, py + 14), fill=(20, 40, 20))
                # Rice ring
                d.ellipse((px - 10, py - 10, px + 10, py + 10), fill=(255, 250, 240))
                # Filling
                d.ellipse((px - 5, py - 5, px + 5, py + 5), fill=rng.choice([(255, 100, 60), (200, 60, 60), (80, 200, 80)]))
        # Chopsticks
        d.line((50, 100, 220, 30), fill=(160, 120, 60), width=3)
        d.line((54, 102, 224, 32), fill=(140, 100, 50), width=3)
        return img

    def _donut(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (255, 230, 240))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 64
        # Donut body
        d.ellipse((cx - 40, cy - 35, cx + 40, cy + 35), fill=(220, 160, 80))
        d.ellipse((cx - 14, cy - 12, cx + 14, cy + 12), fill=(255, 230, 240))  # hole
        # Frosting
        frosting = rng.choice([(255, 120, 160), (160, 80, 200), (100, 200, 255), (255, 255, 255)])
        d.ellipse((cx - 38, cy - 33, cx + 38, cy + 5), fill=frosting)
        d.ellipse((cx - 12, cy - 10, cx + 12, cy + 5), fill=(255, 230, 240))  # hole cutout
        # Sprinkles
        sprinkle_colors = [(255, 60, 60), (60, 200, 60), (60, 60, 255), (255, 255, 60), (255, 140, 0)]
        for _ in range(25):
            sx = cx + rng.randint(-30, 30)
            sy = cy + rng.randint(-28, -2)
            dist = math.sqrt((sx - cx) ** 2 + (sy - cy) ** 2)
            if 14 < dist < 36:
                col = rng.choice(sprinkle_colors)
                angle = rng.random() * math.pi
                dx = int(3 * math.cos(angle))
                dy = int(3 * math.sin(angle))
                d.line((sx - dx, sy - dy, sx + dx, sy + dy), fill=col, width=2)
        return img

    def _cake(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (240, 220, 230))
        d = ImageDraw.Draw(img)
        cx = 128
        # Plate
        d.ellipse((cx - 55, 90, cx + 55, 105), fill=(220, 220, 230))
        # Bottom layer
        d.rounded_rectangle((cx - 40, 55, cx + 40, 95), radius=5, fill=(255, 200, 180))
        # Middle layer
        d.rounded_rectangle((cx - 34, 30, cx + 34, 58), radius=5, fill=(255, 180, 200))
        # Top layer
        d.rounded_rectangle((cx - 28, 10, cx + 28, 33), radius=5, fill=(255, 160, 180))
        # Frosting drips
        for x in range(cx - 38, cx + 38, 8):
            drip_h = rng.randint(4, 12)
            d.rectangle((x, 55, x + 4, 55 + drip_h), fill=(255, 255, 255))
        for x in range(cx - 32, cx + 32, 8):
            drip_h = rng.randint(3, 8)
            d.rectangle((x, 30, x + 4, 30 + drip_h), fill=(255, 255, 255))
        # Candles
        candle_colors = [(255, 60, 60), (60, 120, 255), (255, 200, 40), (60, 200, 60), (200, 60, 200)]
        for i, cx_off in enumerate([-16, -6, 4, 14]):
            cc = candle_colors[i % len(candle_colors)]
            d.rectangle((cx + cx_off, 0, cx + cx_off + 4, 12), fill=cc)
            # Flame
            d.ellipse((cx + cx_off - 1, -8, cx + cx_off + 5, 2), fill=(255, 200, 60))
            d.ellipse((cx + cx_off, -6, cx + cx_off + 4, 0), fill=(255, 255, 180))
        return img

    def _ice_cream(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (180, 220, 255))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 50
        # Cone
        d.polygon([(cx - 20, cy + 15), (cx + 20, cy + 15), (cx, cy + 65)], fill=(220, 180, 100))
        # Waffle pattern
        for i in range(4):
            y = cy + 20 + i * 10
            d.line((cx - 16 + i * 3, y, cx + 16 - i * 3, y), fill=(200, 160, 80), width=1)
        # Scoops
        flavors = [(255, 180, 200), (200, 140, 80), (255, 255, 200)]  # strawberry, chocolate, vanilla
        scoops = [(cx, cy), (cx - 14, cy + 8), (cx + 14, cy + 8)]
        for (sx, sy), color in zip(scoops, flavors):
            d.ellipse((sx - 16, sy - 16, sx + 16, sy + 12), fill=color)
        # Cherry on top
        d.ellipse((cx - 5, cy - 22, cx + 5, cy - 12), fill=(220, 30, 30))
        d.line((cx, cy - 22, cx + 3, cy - 28), fill=(60, 120, 40), width=2)
        # Drips
        for _ in range(3):
            dx = cx + rng.randint(-14, 14)
            d.line((dx, cy + 10, dx + rng.randint(-2, 2), cy + 18), fill=(200, 140, 80), width=2)
        return img

    def _coffee(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (60, 40, 30))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 55
        # Saucer
        d.ellipse((cx - 45, 80, cx + 45, 100), fill=(220, 210, 200))
        # Cup body
        d.rounded_rectangle((cx - 28, cy - 10, cx + 28, cy + 30), radius=6, fill=(255, 255, 250))
        # Cup rim
        d.ellipse((cx - 30, cy - 16, cx + 30, cy - 2), fill=(255, 255, 255))
        # Coffee
        d.ellipse((cx - 26, cy - 12, cx + 26, cy - 2), fill=(120, 70, 30))
        # Latte art - simple heart
        d.ellipse((cx - 8, cy - 10, cx, cy - 4), fill=(200, 170, 130))
        d.ellipse((cx, cy - 10, cx + 8, cy - 4), fill=(200, 170, 130))
        d.polygon([(cx - 8, cy - 6), (cx + 8, cy - 6), (cx, cy - 1)], fill=(200, 170, 130))
        # Handle
        d.arc((cx + 26, cy, cx + 42, cy + 22), start=280, end=80, fill=(255, 255, 250), width=4)
        # Steam
        for i in range(3):
            sx = cx - 10 + i * 10
            for seg in range(4):
                y0 = cy - 20 - seg * 8
                sway = int(4 * math.sin(seg * 1.2 + i * 0.8))
                d.arc((sx + sway - 3, y0 - 6, sx + sway + 3, y0 + 2), start=180, end=0,
                      fill=(180, 180, 180), width=1)
        return img

    def _fruit(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (200, 230, 200))
        d = ImageDraw.Draw(img)
        # Apple
        d.ellipse((50, 35, 110, 95), fill=(220, 40, 40))
        d.ellipse((55, 40, 105, 90), fill=(240, 60, 50))
        d.rectangle((76, 22, 80, 38), fill=(100, 70, 30))
        d.ellipse((80, 22, 96, 36), fill=(80, 180, 60))
        # Watermelon slice
        d.pieslice((130, 30, 220, 100), start=200, end=340, fill=(30, 140, 30))
        d.pieslice((134, 34, 216, 96), start=200, end=340, fill=(255, 60, 60))
        # Seeds
        for _ in range(6):
            sx = 160 + rng.randint(-15, 25)
            sy = 55 + rng.randint(-5, 20)
            d.ellipse((sx - 2, sy - 1, sx + 2, sy + 2), fill=(30, 20, 10))
        return img

    def _ramen(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (40, 30, 25))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 60
        # Bowl
        d.ellipse((cx - 50, cy - 15, cx + 50, cy + 40), fill=(240, 235, 225))
        d.ellipse((cx - 46, cy - 11, cx + 46, cy + 36), fill=(200, 150, 80))  # broth
        # Noodles
        for _ in range(15):
            nx = cx + rng.randint(-30, 30)
            ny = cy + rng.randint(-5, 20)
            pts = [(nx, ny)]
            for _ in range(3):
                nx += rng.randint(-8, 8)
                ny += rng.randint(-4, 4)
                pts.append((nx, ny))
            d.line(pts, fill=(255, 230, 160), width=2)
        # Egg half
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 6), fill=(255, 255, 240))
        d.ellipse((cx - 4, cy - 4, cx + 4, cy + 2), fill=(255, 180, 40))
        # Nori
        d.rectangle((cx + 15, cy - 10, cx + 28, cy + 8), fill=(20, 40, 20))
        # Green onion
        for _ in range(6):
            gx = cx + rng.randint(-25, 25)
            gy = cy + rng.randint(-8, 15)
            d.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=(60, 180, 60))
        # Chopsticks
        d.line((cx + 30, cy - 20, cx + 55, cy + 35), fill=(180, 140, 80), width=3)
        d.line((cx + 34, cy - 18, cx + 58, cy + 37), fill=(160, 120, 70), width=3)
        # Steam
        for i in range(4):
            sx = cx - 15 + i * 10
            for seg in range(3):
                y0 = cy - 20 - seg * 8
                sway = int(3 * math.sin(seg + i * 0.7))
                d.arc((sx + sway - 3, y0 - 5, sx + sway + 3, y0 + 3), start=180, end=0,
                      fill=(200, 200, 200), width=1)
        return img

    # ====================================================================
    # OBJECT GENERATORS
    # ====================================================================

    def _heart(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (40, 10, 20))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 55
        # Glow
        for r in range(60, 0, -2):
            v = int(40 * (60 - r) / 60)
            d.ellipse((cx - r, cy - r + 10, cx + r, cy + r - 10), fill=(v, 0, v // 3))
        # Heart shape
        d.ellipse((cx - 30, cy - 30, cx, cy), fill=(220, 30, 60))
        d.ellipse((cx, cy - 30, cx + 30, cy), fill=(220, 30, 60))
        d.polygon([(cx - 30, cy - 8), (cx + 30, cy - 8), (cx, cy + 30)], fill=(220, 30, 60))
        # Highlight
        d.ellipse((cx - 20, cy - 24, cx - 8, cy - 12), fill=(255, 100, 120))
        return img

    def _heart_anim(self, t: float, rng: random.Random) -> Image.Image:
        img = self._heart(rng=rng)
        d = ImageDraw.Draw(img)
        # Pulsing particles
        cx, cy = 128, 55
        pulse = 0.8 + 0.2 * math.sin(t * math.tau * 2)
        for _ in range(int(15 * pulse)):
            angle = rng.uniform(0, math.tau)
            dist = 35 + rng.uniform(0, 25) * pulse
            px = cx + int(dist * math.cos(angle))
            py = cy + int(dist * 0.7 * math.sin(angle))
            sz = rng.randint(1, 3)
            d.ellipse((px - sz, py - sz, px + sz, py + sz), fill=(255, rng.randint(60, 150), rng.randint(80, 160)))
        return img

    def _star_object(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (10, 10, 30))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 60
        # Background stars
        for _ in range(60):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            d.point((sx, sy), fill=(rng.randint(40, 120),) * 3)
        # Main star - 5 pointed
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.tau / 10
            r = 40 if i % 2 == 0 else 18
            points.append((cx + int(r * math.cos(angle)), cy + int(r * math.sin(angle))))
        # Glow
        for g in range(3, 0, -1):
            glow_pts = [(cx + int((40 + g * 4) * math.cos(-math.pi / 2 + i * math.tau / 10) if i % 2 == 0 else (18 + g * 2) * math.cos(-math.pi / 2 + i * math.tau / 10)),
                         cy + int((40 + g * 4) * math.sin(-math.pi / 2 + i * math.tau / 10) if i % 2 == 0 else (18 + g * 2) * math.sin(-math.pi / 2 + i * math.tau / 10)))
                        for i in range(10)]
            v = 30 + g * 15
            d.polygon(glow_pts, fill=(v, v, 0))
        d.polygon(points, fill=(255, 230, 60))
        d.polygon(points, outline=(255, 255, 180))
        return img

    def _moon_scene(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (8, 8, 25))
        d = ImageDraw.Draw(img)
        # Stars
        for _ in range(80):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            d.point((sx, sy), fill=(rng.randint(60, 200),) * 3)
        cx, cy = 128, 55
        # Moon glow
        for r in range(55, 35, -1):
            v = int(30 * (55 - r) / 20)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(v, v, v + 10))
        # Full moon
        d.ellipse((cx - 35, cy - 35, cx + 35, cy + 35), fill=(220, 225, 240))
        # Craters
        craters = [(-12, -10, 8), (10, 5, 6), (-5, 15, 5), (15, -15, 7), (-15, 8, 4)]
        for dx, dy, r in craters:
            d.ellipse((cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r), fill=(190, 195, 210))
        return img

    def _sword(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (20, 15, 30))
        d = ImageDraw.Draw(img)
        cx = 128
        # Blade
        d.polygon([(cx - 4, 8), (cx + 4, 8), (cx + 6, 80), (cx - 6, 80)], fill=(200, 210, 230))
        # Edge highlight
        d.line((cx - 2, 10, cx - 4, 78), fill=(240, 245, 255), width=1)
        # Tip
        d.polygon([(cx, 2), (cx - 4, 8), (cx + 4, 8)], fill=(220, 230, 250))
        # Fuller (groove)
        d.rectangle((cx - 1, 14, cx + 1, 70), fill=(170, 180, 200))
        # Crossguard
        d.rounded_rectangle((cx - 24, 78, cx + 24, 86), radius=3, fill=(180, 150, 50))
        d.rounded_rectangle((cx - 22, 79, cx + 22, 85), radius=2, fill=(220, 190, 70))
        # Grip
        d.rectangle((cx - 5, 86, cx + 5, 110), fill=(100, 60, 30))
        # Grip wrap
        for y in range(88, 108, 4):
            d.line((cx - 5, y, cx + 5, y + 2), fill=(120, 80, 40), width=1)
        # Pommel
        d.ellipse((cx - 8, 108, cx + 8, 120), fill=(180, 150, 50))
        d.ellipse((cx - 4, 112, cx + 4, 118), fill=(200, 60, 60))
        return img

    def _crown(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (30, 10, 40))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 60
        # Velvet cushion
        d.rounded_rectangle((cx - 50, cy + 10, cx + 50, cy + 30), radius=8, fill=(120, 20, 40))
        # Crown base
        d.rounded_rectangle((cx - 38, cy - 5, cx + 38, cy + 12), radius=4, fill=(220, 180, 40))
        # Crown points
        points = [(cx - 35, cy - 5), (cx - 24, cy - 30), (cx - 12, cy - 10),
                  (cx, cy - 35), (cx + 12, cy - 10), (cx + 24, cy - 30), (cx + 35, cy - 5)]
        d.polygon(points, fill=(220, 180, 40))
        # Rim
        d.rounded_rectangle((cx - 40, cy + 2, cx + 40, cy + 10), radius=3, fill=(240, 200, 60))
        # Gems
        gem_colors = [(255, 40, 40), (40, 100, 255), (40, 200, 40), (255, 40, 40), (40, 100, 255)]
        gem_x = [cx - 24, cx - 12, cx, cx + 12, cx + 24]
        for gx, gc in zip(gem_x, gem_colors):
            d.ellipse((gx - 4, cy - 28, gx + 4, cy - 20), fill=gc)
        # Jewels on band
        for gx in [cx - 20, cx, cx + 20]:
            d.ellipse((gx - 3, cy + 4, gx + 3, cy + 8), fill=(255, 255, 255))
        return img

    def _gem(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (10, 5, 20))
        d = ImageDraw.Draw(img)
        cx, cy = 128, 60
        gem_col = rng.choice([(60, 120, 255), (220, 40, 60), (40, 200, 100), (200, 60, 255)])
        # Glow
        for r in range(50, 20, -2):
            v = int(30 * (50 - r) / 30)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(v * gem_col[0] // 255, v * gem_col[1] // 255, v * gem_col[2] // 255))
        # Gem shape - octagon cut
        top = cy - 25
        bot = cy + 25
        mid = cy
        d.polygon([(cx - 15, top), (cx + 15, top), (cx + 30, mid), (cx + 15, bot),
                   (cx - 15, bot), (cx - 30, mid)], fill=gem_col)
        # Facets
        lighter = tuple(min(255, c + 60) for c in gem_col)
        darker = tuple(max(0, c - 40) for c in gem_col)
        d.polygon([(cx - 15, top), (cx + 15, top), (cx, mid)], fill=lighter)
        d.polygon([(cx + 15, top), (cx + 30, mid), (cx, mid)], fill=gem_col)
        d.polygon([(cx - 15, top), (cx - 30, mid), (cx, mid)], fill=darker)
        d.polygon([(cx - 15, bot), (cx + 15, bot), (cx, mid)], fill=darker)
        # Sparkle
        for _ in range(5):
            sx = cx + rng.randint(-25, 25)
            sy = cy + rng.randint(-20, 20)
            d.line((sx - 3, sy, sx + 3, sy), fill=(255, 255, 255), width=1)
            d.line((sx, sy - 3, sx, sy + 3), fill=(255, 255, 255), width=1)
        return img

    def _tree(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (100, 180, 240))
        d = ImageDraw.Draw(img)
        # Ground
        d.rectangle((0, 95, W, H), fill=(80, 140, 50))
        cx = 128
        # Trunk
        d.rectangle((cx - 8, 50, cx + 8, 96), fill=(120, 80, 40))
        d.rectangle((cx - 6, 55, cx + 6, 96), fill=(140, 95, 50))
        # Foliage layers
        greens = [(40, 130, 40), (50, 150, 50), (60, 170, 55)]
        for i, (y_off, size) in enumerate([(10, 40), (25, 50), (42, 55)]):
            g = greens[i % len(greens)]
            d.ellipse((cx - size // 2, y_off, cx + size // 2, y_off + 30), fill=g)
        # Apples
        for _ in range(4):
            ax = cx + rng.randint(-20, 20)
            ay = rng.randint(15, 55)
            d.ellipse((ax - 3, ay - 3, ax + 3, ay + 3), fill=(220, 40, 30))
        return img

    def _flower(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (180, 220, 255))
        d = ImageDraw.Draw(img)
        # Ground
        d.rectangle((0, 90, W, H), fill=(80, 160, 60))
        cx, cy = 128, 50
        # Stem
        d.line((cx, cy + 15, cx, 95), fill=(40, 140, 40), width=4)
        # Leaves
        d.ellipse((cx + 3, 65, cx + 18, 78), fill=(50, 160, 50))
        d.ellipse((cx - 18, 72, cx - 3, 85), fill=(50, 160, 50))
        # Petals
        petal_col = rng.choice([(255, 80, 120), (255, 200, 60), (200, 80, 255), (255, 100, 60), (255, 255, 255)])
        for i in range(6):
            angle = i * math.tau / 6
            px = cx + int(18 * math.cos(angle))
            py = cy + int(18 * math.sin(angle))
            d.ellipse((px - 10, py - 8, px + 10, py + 8), fill=petal_col)
        # Center
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(255, 200, 40))
        d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(220, 160, 30))
        return img

    def _car(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (140, 200, 240))
        d = ImageDraw.Draw(img)
        # Road
        d.rectangle((0, 80, W, H), fill=(60, 60, 60))
        d.line((0, 90, W, 90), fill=(255, 255, 255), width=2)
        d.rectangle((0, 80, W, 82), fill=(180, 180, 180))
        cx, cy = 128, 58
        car_col = rng.choice([(220, 40, 40), (40, 80, 220), (40, 180, 60), (255, 200, 40)])
        # Body
        d.rounded_rectangle((cx - 45, cy, cx + 45, cy + 24), radius=5, fill=car_col)
        # Cabin
        d.polygon([(cx - 20, cy), (cx - 12, cy - 18), (cx + 16, cy - 18), (cx + 24, cy)], fill=(120, 180, 240))
        # Windows
        d.polygon([(cx - 16, cy - 2), (cx - 10, cy - 14), (cx, cy - 14), (cx, cy - 2)], fill=(160, 210, 255))
        d.polygon([(cx + 2, cy - 2), (cx + 2, cy - 14), (cx + 14, cy - 14), (cx + 20, cy - 2)], fill=(160, 210, 255))
        # Wheels
        for wx in [cx - 28, cx + 28]:
            d.ellipse((wx - 10, cy + 16, wx + 10, cy + 30), fill=(30, 30, 30))
            d.ellipse((wx - 6, cy + 20, wx + 6, cy + 26), fill=(120, 120, 120))
        # Headlights
        d.rectangle((cx + 42, cy + 4, cx + 46, cy + 12), fill=(255, 255, 200))
        d.rectangle((cx - 46, cy + 4, cx - 42, cy + 12), fill=(255, 60, 60))
        return img

    def _rocket(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 5, 20))
        d = ImageDraw.Draw(img)
        # Stars
        for _ in range(80):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            d.point((sx, sy), fill=(rng.randint(60, 200),) * 3)
        cx, cy = 128, 55
        # Rocket body
        d.rounded_rectangle((cx - 12, cy - 20, cx + 12, cy + 30), radius=6, fill=(230, 230, 240))
        # Nose cone
        d.polygon([(cx, cy - 40), (cx - 12, cy - 18), (cx + 12, cy - 18)], fill=(220, 40, 40))
        # Window
        d.ellipse((cx - 6, cy - 10, cx + 6, cy + 2), fill=(60, 140, 255))
        d.ellipse((cx - 4, cy - 8, cx + 4, cy), fill=(120, 200, 255))
        # Fins
        d.polygon([(cx - 12, cy + 20), (cx - 24, cy + 38), (cx - 12, cy + 30)], fill=(220, 40, 40))
        d.polygon([(cx + 12, cy + 20), (cx + 24, cy + 38), (cx + 12, cy + 30)], fill=(220, 40, 40))
        # Exhaust flame
        d.polygon([(cx - 8, cy + 30), (cx + 8, cy + 30), (cx, cy + 55)], fill=(255, 200, 40))
        d.polygon([(cx - 5, cy + 30), (cx + 5, cy + 30), (cx, cy + 48)], fill=(255, 255, 180))
        # Exhaust particles
        for _ in range(10):
            ex = cx + rng.randint(-12, 12)
            ey = cy + 40 + rng.randint(0, 20)
            d.point((ex, ey), fill=(255, rng.randint(150, 255), rng.randint(50, 100)))
        return img

    def _house(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (140, 200, 240))
        d = ImageDraw.Draw(img)
        # Ground
        d.rectangle((0, 90, W, H), fill=(80, 160, 60))
        # Path
        d.polygon([(118, 90), (138, 90), (145, H), (111, H)], fill=(180, 160, 140))
        cx = 128
        # Walls
        wall_col = rng.choice([(220, 200, 170), (180, 80, 60), (240, 240, 230)])
        d.rectangle((cx - 35, 45, cx + 35, 90), fill=wall_col)
        # Roof
        d.polygon([(cx - 42, 45), (cx, 15), (cx + 42, 45)], fill=(160, 60, 40))
        # Door
        d.rounded_rectangle((cx - 8, 60, cx + 8, 90), radius=4, fill=(120, 70, 30))
        d.ellipse((cx + 3, 73, cx + 6, 76), fill=(220, 200, 60))
        # Windows
        for wx in [cx - 25, cx + 15]:
            d.rectangle((wx, 55, wx + 14, 70), fill=(160, 210, 255))
            d.line((wx + 7, 55, wx + 7, 70), fill=wall_col, width=1)
            d.line((wx, 62, wx + 14, 62), fill=wall_col, width=1)
        # Chimney
        d.rectangle((cx + 15, 18, cx + 25, 40), fill=(140, 50, 35))
        # Smoke
        for i in range(3):
            d.ellipse((cx + 18 + i * 4, 8 - i * 4, cx + 26 + i * 4, 18 - i * 4), fill=(200, 200, 200))
        return img

    def _flag(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (140, 200, 240))
        d = ImageDraw.Draw(img)
        # Ground
        d.rectangle((0, 100, W, H), fill=(80, 160, 60))
        # Pole
        d.rectangle((70, 10, 74, 100), fill=(180, 180, 190))
        d.ellipse((68, 6, 76, 14), fill=(220, 200, 60))
        # Flag with wave
        colors = rng.choice([
            [(220, 40, 40), (255, 255, 255), (40, 60, 200)],
            [(40, 140, 40), (255, 255, 255), (255, 140, 0)],
            [(0, 60, 120), (255, 255, 255), (220, 40, 40)],
        ])
        flag_h = 40
        stripe_h = flag_h // 3
        for i, c in enumerate(colors):
            for x in range(76, 200):
                wave = int(4 * math.sin((x - 76) * 0.05))
                y0 = 20 + i * stripe_h + wave
                y1 = 20 + (i + 1) * stripe_h + wave
                d.line((x, y0, x, y1), fill=c, width=1)
        return img

    # ====================================================================
    # SCENE GENERATORS (original + new)
    # ====================================================================

    def _ocean(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        # Sky gradient
        for y in range(60):
            frac = y / 60
            r = int(100 + frac * 80)
            g = int(160 + frac * 60)
            b = int(240 - frac * 20)
            d.line((0, y, W, y), fill=(r, g, b))
        # Sun
        d.ellipse((180, 10, 220, 50), fill=(255, 220, 100))
        # Ocean
        for y in range(60, H):
            depth = (y - 60) / (H - 60)
            r = int(20 + depth * 10)
            g = int(80 + depth * 30)
            b = int(180 - depth * 40)
            d.line((0, y, W, y), fill=(r, g, b))
        # Waves
        for wave_y in range(60, H, 8):
            for x in range(0, W, 2):
                wy = wave_y + int(3 * math.sin(x * 0.04 + wave_y * 0.1))
                if 0 <= wy < H:
                    d.point((x, wy), fill=(100, 180, 240))
        # Sun reflection
        for y in range(62, H, 3):
            rw = max(1, 25 - (y - 62) // 2)
            d.line((200 - rw, y, 200 + rw, y), fill=(200, 180, 100), width=1)
        return img

    def _ocean_anim(self, t: float, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(60):
            frac = y / 60
            d.line((0, y, W, y), fill=(int(100 + frac * 80), int(160 + frac * 60), int(240 - frac * 20)))
        d.ellipse((180, 10, 220, 50), fill=(255, 220, 100))
        for y in range(60, H):
            depth = (y - 60) / (H - 60)
            d.line((0, y, W, y), fill=(int(20 + depth * 10), int(80 + depth * 30), int(180 - depth * 40)))
        phase = t * math.tau
        for wave_y in range(60, H, 6):
            for x in range(0, W, 2):
                wy = wave_y + int(4 * math.sin(x * 0.04 + wave_y * 0.08 + phase))
                if 0 <= wy < H:
                    d.point((x, wy), fill=(120, 200, 255))
        return img

    def _cityscape(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        # Night sky gradient
        for y in range(H):
            d.line((0, y, W, y), fill=(int(10 + y * 0.1), int(10 + y * 0.15), int(30 + y * 0.2)))
        # Stars
        for _ in range(40):
            sx, sy = rng.randint(0, W), rng.randint(0, 40)
            d.point((sx, sy), fill=(rng.randint(100, 220),) * 3)
        # Moon
        d.ellipse((200, 8, 228, 36), fill=(220, 225, 240))
        # Buildings
        for _ in range(12):
            bw = rng.randint(16, 35)
            bh = rng.randint(30, 80)
            bx = rng.randint(0, W - bw)
            by = H - bh
            shade = rng.randint(20, 50)
            d.rectangle((bx, by, bx + bw, H), fill=(shade, shade, shade + 10))
            # Windows
            for wx in range(bx + 3, bx + bw - 3, 6):
                for wy in range(by + 4, H - 4, 8):
                    if rng.random() > 0.3:
                        wc = rng.choice([(255, 220, 100), (200, 180, 80), (100, 150, 200)])
                        d.rectangle((wx, wy, wx + 3, wy + 4), fill=wc)
        # Ground
        d.rectangle((0, H - 5, W, H), fill=(30, 30, 35))
        return img

    def _rainbow_scene(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (140, 200, 240))
        d = ImageDraw.Draw(img)
        # Clouds
        for cx in [40, 130, 200]:
            d.ellipse((cx, 15, cx + 40, 40), fill=(255, 255, 255))
            d.ellipse((cx + 10, 8, cx + 50, 38), fill=(255, 255, 255))
            d.ellipse((cx + 20, 15, cx + 60, 40), fill=(255, 255, 255))
        # Rainbow arc
        colors = [(255, 0, 0), (255, 127, 0), (255, 255, 0), (0, 200, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)]
        cx_r, cy_r = 128, 100
        for i, c in enumerate(colors):
            r = 80 - i * 5
            d.arc((cx_r - r, cy_r - r, cx_r + r, cy_r + r), start=180, end=360, fill=c, width=4)
        # Ground
        d.rectangle((0, 95, W, H), fill=(80, 160, 60))
        return img

    def _rainbow_anim(self, t: float, rng: random.Random) -> Image.Image:
        img = self._rainbow_scene(rng=rng)
        d = ImageDraw.Draw(img)
        # Shimmer effect
        cx_r, cy_r = 128, 100
        colors = [(255, 0, 0), (255, 127, 0), (255, 255, 0), (0, 200, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)]
        phase = t * math.tau
        for i, c in enumerate(colors):
            r = 80 - i * 5
            bright = 0.6 + 0.4 * math.sin(phase + i * 0.5)
            bc = tuple(int(v * bright) for v in c)
            d.arc((cx_r - r, cy_r - r, cx_r + r, cy_r + r), start=180, end=360, fill=bc, width=5)
        return img

    def _snow_scene(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        # Sky
        for y in range(H):
            shade = int(40 + y * 0.3)
            d.line((0, y, W, y), fill=(shade, shade + 10, shade + 30))
        # Snowy ground
        d.rectangle((0, 80, W, H), fill=(230, 235, 240))
        # Snow hills
        for hx in [60, 140, 200]:
            d.ellipse((hx - 30, 72, hx + 30, 95), fill=(235, 240, 245))
        # Pine trees
        for tx in [40, 90, 170, 220]:
            ty = 80 - rng.randint(0, 10)
            d.rectangle((tx - 2, ty, tx + 2, ty + 18), fill=(80, 50, 30))
            for i in range(3):
                w = 12 - i * 3
                y = ty - 5 - i * 10
                d.polygon([(tx - w, y + 12), (tx, y), (tx + w, y + 12)], fill=(30, 80, 40))
            # Snow on tree
            d.polygon([(tx - 8, ty + 2), (tx, ty - 8), (tx + 8, ty + 2)], fill=(230, 235, 240))
        # Snowflakes
        for _ in range(40):
            sx, sy = rng.randint(0, W), rng.randint(0, 85)
            sz = rng.randint(1, 3)
            d.ellipse((sx - sz, sy - sz, sx + sz, sy + sz), fill=(240, 245, 255))
        # Snowman
        cx = 128
        d.ellipse((cx - 14, 56, cx + 14, 82), fill=(240, 245, 250))  # body
        d.ellipse((cx - 10, 40, cx + 10, 60), fill=(240, 245, 250))  # head
        d.ellipse((cx - 6, 47, cx - 2, 51), fill=(20, 20, 20))  # eye
        d.ellipse((cx + 2, 47, cx + 6, 51), fill=(20, 20, 20))  # eye
        d.polygon([(cx - 1, 51), (cx + 1, 51), (cx + 6, 54), (cx, 55)], fill=(255, 120, 30))  # nose
        return img

    def _snow_anim(self, i: int, rng: random.Random) -> Image.Image:
        img = self._snow_scene(rng=rng)
        d = ImageDraw.Draw(img)
        # Animated falling snow
        for _ in range(30):
            sx = rng.randint(0, 256)
            sy = (rng.randint(0, 128) + i * 4) % 90
            sz = rng.randint(1, 3)
            d.ellipse((sx - sz, sy - sz, sx + sz, sy + sz), fill=(245, 248, 255))
        return img

    # ====================================================================
    # ORIGINAL GENERATORS (preserved)
    # ====================================================================

    def _dragon_frame(self, t: float = 0.0, rng: random.Random = None, **_kw) -> Image.Image:
        if rng is None:
            rng = random.Random()
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 6, 12))
        d = ImageDraw.Draw(img)
        for _ in range(40):
            sx, sy = rng.randint(0, W), rng.randint(0, 60)
            brightness = rng.randint(60, 200)
            d.point((sx, sy), fill=(brightness, brightness, brightness + 30))
        d.ellipse((175, 5, 235, 65), fill=(30, 35, 50))
        d.ellipse((180, 10, 230, 60), fill=(200, 210, 255))
        bx, by = 60, 80
        body = [(bx - 10, by), (bx + 30, by - 30), (bx + 70, by - 25),
                (bx + 95, by - 10), (bx + 70, by + 15), (bx + 25, by + 10)]
        d.polygon(body, fill=(20, 30, 35))
        d.ellipse((bx + 75, by - 45, bx + 115, by - 15), fill=(22, 34, 40))
        d.ellipse((bx + 95, by - 40, bx + 103, by - 32), fill=(255, 160, 40))
        d.ellipse((bx + 97, by - 38, bx + 101, by - 34), fill=(200, 40, 20))
        d.polygon([(bx + 92, by - 48), (bx + 102, by - 65), (bx + 110, by - 45)], fill=(25, 40, 45))
        d.polygon([(bx + 15, by - 20), (bx - 10, by - 55), (bx + 20, by - 60), (bx + 55, by - 35)], fill=(15, 25, 30))
        d.polygon([(bx + 35, by - 22), (bx + 10, by - 65), (bx + 45, by - 70), (bx + 75, by - 40)], fill=(14, 22, 28))
        mouth = (bx + 115, by - 30)
        fire_len = 110 + int(30 * math.sin(t * math.tau))
        flame_points = []
        for i in range(7):
            px = mouth[0] + (fire_len * i / 6)
            jitter = int(8 * math.sin(t * math.tau * 2 + i) + rng.randint(-2, 2))
            py = mouth[1] + jitter + int(10 * math.sin(t * math.tau + i * 0.7))
            flame_points.append((int(px), int(py)))
        for i in range(6):
            c = (255, max(0, 180 - i * 18), 40 + i * 10)
            d.line(flame_points[i:i + 2], fill=c, width=18 - i * 2)
        for _ in range(40):
            sx = mouth[0] + rng.randint(20, fire_len + 20)
            sy = mouth[1] + rng.randint(-25, 25)
            if rng.random() < 0.6:
                sz = rng.randint(1, 3)
                d.ellipse((sx, sy, sx + sz, sy + sz), fill=(255, rng.randint(180, 255), rng.randint(80, 160)))
        for gy in range(100, H):
            shade = int((gy - 100) / max(1, H - 100) * 12)
            d.line((0, gy, W, gy), fill=(8 + shade, 10 + shade, 14 + shade))
        return img

    def _retro_plumber(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (92, 148, 252))
        d = ImageDraw.Draw(img)
        for bx in range(0, W, 16):
            d.rectangle((bx, 96, bx + 15, 112), fill=(200, 76, 12))
            d.rectangle((bx, 112, bx + 15, H), fill=(148, 52, 8))
        d.rectangle((112, 48, 144, 80), fill=(252, 188, 60))
        d.rectangle((114, 50, 142, 78), fill=(228, 168, 40))
        d.rectangle((124, 56, 132, 72), fill=(255, 255, 255))
        for cx in [40, 170]:
            d.ellipse((cx, 20, cx + 40, 45), fill=(255, 255, 255))
            d.ellipse((cx + 15, 12, cx + 55, 42), fill=(255, 255, 255))
            d.ellipse((cx + 30, 20, cx + 70, 45), fill=(255, 255, 255))
        x, y = 90, 48
        d.rectangle((x + 20, y, x + 60, y + 16), fill=(255, 0, 0))
        d.rectangle((x + 16, y + 4, x + 24, y + 12), fill=(255, 0, 0))
        d.rectangle((x + 24, y + 16, x + 56, y + 36), fill=(255, 200, 150))
        d.rectangle((x + 32, y + 20, x + 44, y + 28), fill=(180, 120, 80))
        d.rectangle((x + 16, y + 36, x + 64, y + 64), fill=(0, 0, 255))
        d.rectangle((x + 24, y + 40, x + 56, y + 56), fill=(255, 0, 0))
        d.rectangle((x + 12, y + 64, x + 36, y + 84), fill=(80, 48, 16))
        d.rectangle((x + 44, y + 64, x + 68, y + 84), fill=(80, 48, 16))
        d.rectangle((200, 64, 240, 96), fill=(0, 168, 0))
        d.rectangle((196, 64, 244, 76), fill=(0, 200, 0))
        return img

    def _metroid(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (3, 3, 8))
        d = ImageDraw.Draw(img)
        for _ in range(60):
            sx, sy = rng.randint(0, W), rng.randint(0, H)
            bright = rng.randint(30, 120)
            d.point((sx, sy), fill=(bright, bright, bright + 20))
        for r in range(50, 30, -2):
            alpha = int(20 * (50 - r) / 20)
            d.ellipse((128 - r, 60 - r, 128 + r, 60 + r), fill=(alpha, alpha * 2, alpha * 3))
        d.ellipse((90, 20, 170, 100), fill=(40, 80, 160))
        d.ellipse((100, 30, 160, 90), fill=(60, 120, 220))
        d.ellipse((108, 38, 152, 82), fill=(120, 200, 255))
        d.ellipse((118, 50, 142, 70), fill=(200, 255, 255))
        for i in range(8):
            x0, y0 = 130, 85
            mid_x = 50 + i * 22 + rng.randint(-5, 5)
            mid_y = 105 + rng.randint(-3, 3)
            x1 = 40 + i * 20 + rng.randint(-8, 8)
            y1 = 120 + rng.randint(-5, 5)
            d.line((x0, y0, mid_x, mid_y), fill=(200, 80, 220), width=8)
            d.line((mid_x, mid_y, x1, y1), fill=(160, 50, 180), width=5)
        return img

    def _zelda(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (12, 18, 10))
        d = ImageDraw.Draw(img)
        for _ in range(200):
            gx, gy = rng.randint(0, W), rng.randint(0, H)
            d.point((gx, gy), fill=(rng.randint(8, 20), rng.randint(14, 28), rng.randint(6, 14)))
        cx, cy = 128, 50
        size = 55
        d.polygon([(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)], fill=(240, 200, 40))
        d.polygon([(cx, cy + 10), (cx - 25, cy + size), (cx + 25, cy + size)], fill=(12, 18, 10))
        for r in range(3):
            offset = r * 2
            d.polygon([(cx, cy - size - offset), (cx - size - offset, cy + size + offset), (cx + size + offset, cy + size + offset)], outline=(240, 200, 40))
        sx = 40
        d.rectangle((sx + 3, 15, sx + 9, 100), fill=(180, 190, 210))
        d.rectangle((sx + 1, 15, sx + 11, 20), fill=(200, 210, 230))
        d.rectangle((sx - 5, 72, sx + 17, 80), fill=(90, 60, 160))
        d.rectangle((sx + 2, 80, sx + 10, 105), fill=(60, 40, 120))
        d.ellipse((sx, 105, sx + 12, 115), fill=(200, 180, 40))
        return img

    def _pikachu(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (30, 140, 50))
        d = ImageDraw.Draw(img)
        for y in range(60):
            shade = int(100 + y * 2)
            d.line((0, y, W, y), fill=(shade, min(255, shade + 40), 255))
        d.rectangle((0, 60, W, H), fill=(30, 140, 50))
        for _ in range(80):
            gx, gy = rng.randint(0, W), rng.randint(60, H)
            d.line((gx, gy, gx + rng.randint(-3, 3), gy - rng.randint(3, 10)), fill=(40, 160, 60), width=2)
        d.rounded_rectangle((90, 35, 165, 115), radius=20, fill=(250, 220, 60))
        d.ellipse((105, 55, 122, 72), fill=(0, 0, 0))
        d.ellipse((108, 58, 116, 66), fill=(255, 255, 255))
        d.ellipse((135, 55, 152, 72), fill=(0, 0, 0))
        d.ellipse((138, 58, 146, 66), fill=(255, 255, 255))
        d.ellipse((96, 74, 118, 94), fill=(240, 80, 80))
        d.ellipse((140, 74, 162, 94), fill=(240, 80, 80))
        d.arc((118, 78, 140, 92), start=0, end=180, fill=(100, 60, 20), width=2)
        d.ellipse((124, 72, 132, 78), fill=(80, 50, 20))
        d.polygon([(95, 40), (85, 5), (110, 30)], fill=(250, 220, 60))
        d.polygon([(85, 5), (95, 18), (80, 15)], fill=(40, 40, 40))
        d.polygon([(160, 40), (170, 5), (145, 30)], fill=(250, 220, 60))
        d.polygon([(170, 5), (160, 18), (175, 15)], fill=(40, 40, 40))
        d.polygon([(165, 65), (210, 40), (230, 55), (215, 70), (235, 85), (200, 95), (170, 80)], fill=(250, 220, 60))
        return img

    def _neon_grid(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 8))
        d = ImageDraw.Draw(img)
        vanish_y = 40
        for x in range(0, W + 1, 20):
            d.line((W // 2, vanish_y, x, H), fill=(0, 80, 200), width=1)
        for y_step in range(8):
            y = vanish_y + int((H - vanish_y) * (y_step / 8) ** 1.5)
            d.line((0, y, W, y), fill=(0, 80, 200), width=1)
        cx, cy = W // 2, vanish_y
        for r in range(30, 0, -1):
            shade = int(255 * (30 - r) / 30)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(shade, 0, min(255, shade + 60)))
        colors = [(255, 0, 100), (255, 60, 0), (255, 180, 0)]
        for i, c in enumerate(colors):
            y = cy + 5 + i * 4
            d.line((cx - 35, y, cx + 35, y), fill=c, width=2)
        for tx in [30, W - 50]:
            d.rectangle((tx, 60, tx + 20, H), fill=(10, 10, 30))
            for wy in range(65, H, 8):
                if rng.random() > 0.3:
                    d.rectangle((tx + 4, wy, tx + 8, wy + 3), fill=(200, 200, 50))
                if rng.random() > 0.3:
                    d.rectangle((tx + 12, wy, tx + 16, wy + 3), fill=(200, 200, 50))
        return img

    def _sunset(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        sky_colors = [(20, 0, 60), (60, 10, 80), (140, 30, 60), (220, 80, 40), (250, 160, 60), (250, 200, 120)]
        for y in range(80):
            idx = y / 80 * (len(sky_colors) - 1)
            i0 = int(idx)
            i1 = min(i0 + 1, len(sky_colors) - 1)
            frac = idx - i0
            r = int(sky_colors[i0][0] * (1 - frac) + sky_colors[i1][0] * frac)
            g = int(sky_colors[i0][1] * (1 - frac) + sky_colors[i1][1] * frac)
            b = int(sky_colors[i0][2] * (1 - frac) + sky_colors[i1][2] * frac)
            d.line((0, y, W, y), fill=(r, g, b))
        d.ellipse((100, 40, 160, 100), fill=(255, 200, 80))
        for sy in range(55, 95, 5):
            gap = (sy - 55) // 5
            d.line((105, sy, 155, sy), fill=sky_colors[min(gap, len(sky_colors) - 1)], width=2)
        for y in range(80, H):
            shade = int((y - 80) / max(1, H - 80) * 40)
            d.line((0, y, W, y), fill=(10 + shade, 20 + shade, 60 + shade))
        for y in range(82, H, 3):
            rw = max(1, 30 - (y - 82))
            d.line((128 - rw, y, 128 + rw, y), fill=(200, 140, 60), width=1)
        return img

    def _galaxy(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 6))
        d = ImageDraw.Draw(img)
        for _ in range(300):
            sx, sy = rng.randint(0, W - 1), rng.randint(0, H - 1)
            brightness = rng.randint(30, 255)
            tint = rng.choice([(1, 1, 1), (1, 0.9, 0.8), (0.8, 0.9, 1)])
            d.point((sx, sy), fill=(int(brightness * tint[0]), int(brightness * tint[1]), int(brightness * tint[2])))
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
                    color = rng.choice([(bright, bright // 2, bright // 3), (bright // 2, bright // 2, bright), (bright, bright, bright)])
                    d.point((x, y), fill=color)
        for r in range(15, 0, -1):
            v = int(255 * (15 - r) / 15)
            d.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), fill=(v, v, min(255, v + 30)))
        return img

    def _fire_frame(self, t: float = 0.0, rng: random.Random = None, **_kw) -> Image.Image:
        if rng is None:
            rng = random.Random()
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 2, 0))
        d = ImageDraw.Draw(img)
        for x in range(0, W, 4):
            height = rng.randint(30, 90) + int(20 * math.sin(t * math.tau + x * 0.05))
            for y in range(H - 1, H - height, -1):
                progress = (H - y) / max(1, height)
                if progress < 0.3:
                    color = (255, 240, 180)
                elif progress < 0.6:
                    color = (255, max(0, int(180 - progress * 200)), 20)
                else:
                    color = (max(0, int(200 - progress * 150)), max(0, int(40 - progress * 40)), 0)
                d.rectangle((x, y, x + 3, y + 1), fill=color)
        for _ in range(30):
            ex = rng.randint(0, W)
            ey = rng.randint(10, H - 30) - int(20 * t)
            if 0 <= ey < H:
                d.point((ex, ey), fill=(255, rng.randint(150, 255), rng.randint(50, 100)))
        return img

    def _mountain(self, rng: random.Random, **_kw) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        for y in range(H):
            frac = y / H
            d.line((0, y, W, y), fill=(int(40 + frac * 30), int(60 + frac * 40), int(120 - frac * 40)))
        layers = [(70, (30, 40, 60)), (85, (40, 55, 50)), (100, (25, 45, 35))]
        for base_y, color in layers:
            points = [(0, H)]
            for x in range(0, W + 1, 8):
                peak = base_y - rng.randint(10, 45)
                points.append((x, peak))
            points.append((W, H))
            d.polygon(points, fill=color)
        d.ellipse((190, 15, 220, 45), fill=(220, 225, 240))
        for _ in range(15):
            tx = rng.randint(0, W)
            ty = rng.randint(90, 110)
            th = rng.randint(10, 25)
            d.rectangle((tx, ty - th, tx + 3, ty), fill=(15, 30, 15))
            d.polygon([(tx - 5, ty - th + 5), (tx + 8, ty - th + 5), (tx + 2, ty - th - 8)], fill=(20, 60, 25))
        return img

    # ---- Animation generators (original) ----

    def _rain_frame(self, i: int = 0, rng: random.Random = None, **_kw) -> Image.Image:
        if rng is None:
            rng = random.Random()
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (5, 8, 16))
        d = ImageDraw.Draw(img)
        for y in range(40):
            d.line((0, y, W, y), fill=(5 + y // 5, 8 + y // 5, 16 + y // 4))
        for cx, cw in [(70, 120), (150, 100)]:
            d.ellipse((cx, 10, cx + cw // 2, 55), fill=(100, 110, 130))
            d.ellipse((cx + cw // 4, 0, cx + cw * 3 // 4, 60), fill=(110, 120, 140))
            d.ellipse((cx + cw // 2, 10, cx + cw, 55), fill=(100, 110, 130))
            d.rectangle((cx, 30, cx + cw, 60), fill=(105, 115, 135))
        for x in range(0, W, 10):
            y = (i * 18 + (x * 3)) % H
            length = rng.randint(12, 22)
            d.line((x, y, x - 4, y + length), fill=(80, 150, 255), width=2)
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
        for r_off in range(3, 0, -1):
            shade = 40 + (3 - r_off) * 20
            d.ellipse((cx - 40 - r_off, cy - 40 - r_off, cx + 40 + r_off, cy + 40 + r_off),
                      outline=(shade, shade, shade + 40), width=1)
        ang = (i / max(1, n)) * math.tau
        px = cx + int(math.cos(ang) * 40)
        py = cy + int(math.sin(ang) * 40)
        for trail in range(8):
            tang = ang - trail * 0.08
            tx = cx + int(math.cos(tang) * 40)
            ty = cy + int(math.sin(tang) * 40)
            fade = max(0, 200 - trail * 25)
            d.ellipse((tx - 4, ty - 4, tx + 4, ty + 4), fill=(fade, fade // 2, 0))
        d.ellipse((px - 8, py - 8, px + 8, py + 8), fill=(255, 200, 60))
        d.ellipse((px - 5, py - 5, px + 2, py + 2), fill=(255, 230, 120))
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(200, 200, 255))
        d.line((cx, cy - 10, cx, cy + 10), fill=(160, 160, 220), width=1)
        d.line((cx - 10, cy, cx + 10, cy), fill=(160, 160, 220), width=1)
        return img

    def _neon_pulse_frame(self, i: int, n: int, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (2, 2, 8))
        d = ImageDraw.Draw(img)
        t = i / max(1, n)
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
        phase = math.sin(t * math.tau) * 0.5 + 0.5
        v = int(200 * phase)
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=(v, 0, v))
        return img

    def _starfield_frame(self, i: int, n: int, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (0, 0, 2))
        d = ImageDraw.Draw(img)
        cx, cy = W // 2, H // 2
        t = i / max(1, n)
        for s in range(100):
            angle = rng.uniform(0, math.tau)
            base_r = rng.uniform(5, 80)
            speed = 0.5 + rng.uniform(0, 1.5)
            r = (base_r + t * speed * 60) % 90
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * 0.5 * math.sin(angle))
            stretch = max(1, int(r / 20))
            x2 = cx + int((r + stretch) * math.cos(angle))
            y2 = cy + int((r + stretch) * 0.5 * math.sin(angle))
            brightness = min(255, int(r * 3))
            d.line((x, y, x2, y2), fill=(brightness, brightness, min(255, brightness + 30)), width=1)
        return img

    # ---- Fallback ----

    def _abstract(self, prompt: str, rng: random.Random) -> Image.Image:
        W, H = 256, 128
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)
        style = sum(ord(c) for c in prompt) % 3
        if style == 0:
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
            for y_band in range(0, H, 4):
                for x_band in range(0, W, 4):
                    v = rng.randint(20, 80)
                    d.rectangle((x_band, y_band, x_band + 3, y_band + 3),
                                fill=(v + rng.randint(0, 40), v, v + rng.randint(0, 60)))
            for _ in range(8):
                ax, ay = rng.randint(20, W - 20), rng.randint(10, H - 10)
                ar = rng.randint(5, 15)
                d.ellipse((ax - ar, ay - ar, ax + ar, ay + ar),
                          fill=(rng.randint(200, 255), rng.randint(100, 255), rng.randint(100, 255)))
        return img
