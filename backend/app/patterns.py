"""Page background pattern generators for themed catalog output.

Each generator returns a full-page RGB image at ``PAGE_W`` x ``PAGE_H`` pixels
(72 DPI, one A4 page).  The same JPEG bytes are embedded in the PDF via
``fpdf`` and in the HTML via a ``data:`` URI, so both formats share an
identical background.  Results are cached per pattern id.
"""

import colorsys
import functools
import io
import math
import random
from typing import Callable

from PIL import Image, ImageDraw

PAGE_W = 595
PAGE_H = 842
_QUALITY = 80


def _palette_ramp(keys: list[tuple[int, int, int]], size: int = 256) -> list[tuple[int, int, int]]:
    """Interpolate a color ramp through ``keys`` into ``size`` entries."""
    ramp = []
    steps = len(keys) - 1
    for i in range(size):
        t = i / (size - 1) * steps
        idx = min(int(t), steps - 1)
        frac = t - idx
        a, b = keys[idx], keys[idx + 1]
        ramp.append(tuple(round(a[k] + (b[k] - a[k]) * frac) for k in range(3)))
    return ramp


def _rainbow() -> Image.Image:
    """Full-page diagonal pastel rainbow gradient."""
    ramp_w = PAGE_W + PAGE_H
    ramp = Image.new("RGB", (ramp_w, 1))
    rp = ramp.load()
    for i in range(ramp_w):
        rp[i, 0] = tuple(round(v * 255) for v in colorsys.hsv_to_rgb(i / ramp_w, 0.35, 0.98))
    img = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
    for y in range(PAGE_H):
        img.paste(ramp, (-y, y))
    return img


def _nebula() -> Image.Image:
    """Julia-set fractal in deep purple / magenta / cyan with a vignette."""
    gw, gh = 200, 283
    max_iter = 60
    cr, ci = -0.7269, 0.1889
    re_min, re_max = -1.7, 1.7
    im_min, im_max = -1.7, 1.7
    palette = _palette_ramp([(0, 229, 255), (255, 45, 140), (120, 20, 90), (20, 10, 40)])
    data = []
    for py in range(gh):
        zy0 = im_max - (im_max - im_min) * py / (gh - 1)
        for px in range(gw):
            zx, zy = re_min + (re_max - re_min) * px / (gw - 1), zy0
            it = 0
            while it < max_iter:
                x2, y2 = zx * zx - zy * zy, 2 * zx * zy
                zx, zy = x2 + cr, y2 + ci
                if zx * zx + zy * zy > 4.0:
                    break
                it += 1
            data.append(min(255, int(it / max_iter * 255)))
    img = Image.new("RGB", (gw, gh))
    img.putdata([palette[v] for v in data])
    img = img.resize((PAGE_W, PAGE_H), Image.LANCZOS)
    px = img.load()
    cx, cy = PAGE_W / 2, PAGE_H / 2
    max_d = math.hypot(cx, cy)
    for y in range(PAGE_H):
        dy = y - cy
        for x in range(PAGE_W):
            d = math.hypot(x - cx, dy) / max_d
            f = 1.0 - 0.25 * d * d
            r, g, b = px[x, y]
            px[x, y] = (int(r * f), int(g * f), int(b * f))
    return img


def _triangles() -> Image.Image:
    """Isometric-ish triangle tiling in teal / coral / sand."""
    bg = (247, 243, 239)
    palette = [(27, 154, 170), (255, 107, 94), (236, 200, 140)]
    tw, th = 49, 42
    img = Image.new("RGB", (PAGE_W, PAGE_H), bg)
    d = ImageDraw.Draw(img)
    for r in range(PAGE_H // th + 2):
        for c in range(PAGE_W // tw + 2):
            x0, y0 = c * tw, r * th
            p_top = (x0, y0)
            p_right = (x0 + tw, y0)
            p_bot = (x0 + tw, y0 + th)
            p_left = (x0, y0 + th)
            d.polygon([p_top, p_right, p_bot], fill=palette[(r + c) % 3], outline=bg)
            d.polygon([p_top, p_bot, p_left], fill=palette[(r + c + 1) % 3], outline=bg)
    return img


def _waves() -> Image.Image:
    """Layered semi-transparent sine-wave bands over a pale blue page."""
    base = Image.new("RGBA", (PAGE_W, PAGE_H), (242, 248, 250, 255))
    overlay = Image.new("RGBA", (PAGE_W, PAGE_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    def band(base_y, amp, freq, phase, thickness, color, alpha):
        pts = []
        step = 12
        for x in range(-step, PAGE_W + step, step):
            pts.append((x, base_y + amp * math.sin(freq * x + phase)))
        for x in range(PAGE_W + step, -step, -step):
            pts.append((x, base_y + amp * math.sin(freq * x + phase) + thickness))
        d.polygon(pts, fill=(*color, alpha))

    colors = [(14, 124, 134), (50, 160, 170), (150, 200, 215)]
    for k in range(4):
        band(120 + k * 190, 22, 0.008, k * 1.4, 70 - k * 6, colors[k % 3], 60)
    return Image.alpha_composite(base, overlay).convert("RGB")


def _mandala() -> Image.Image:
    """Concentric-ring mandala in plum and ochre on cream."""
    img = Image.new("RGB", (PAGE_W, PAGE_H), (255, 249, 236))
    d = ImageDraw.Draw(img)
    plum, ochre = (86, 66, 140), (198, 160, 70)
    for cx, cy in [(170, 180), (470, 420), (300, 690)]:
        for r in range(14, 400, 26):
            color = plum if (r // 26) % 2 == 0 else ochre
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=3)
        d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=plum)
    return img


def _aurora() -> Image.Image:
    """Northern-lights ribbons concentrated at the top and bottom margins."""
    base = Image.new("RGBA", (PAGE_W, PAGE_H), (10, 14, 28, 255))
    overlay = Image.new("RGBA", (PAGE_W, PAGE_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    colors = [(64, 220, 160), (0, 200, 220), (150, 80, 220), (60, 160, 255)]

    def glow(x, y, r, color, alpha):
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, alpha))

    for i in range(8):
        glow(40 + i * 70, 6 + i * 3, 55 + i * 4, colors[i % 4], 100)
    for i in range(8):
        glow(30 + i * 72, PAGE_H - 8 - i * 3, 50 + i * 4, colors[(i + 2) % 4], 95)
    for i in range(6):
        glow(18, 90 + i * 120, 34, colors[i % 4], 45)
        glow(PAGE_W - 18, 90 + i * 120, 34, colors[(i + 1) % 4], 45)
    return Image.alpha_composite(base, overlay).convert("RGB")


def _confeti() -> Image.Image:
    """Multicolor confetti dots packed into a border strip around all margins."""
    img = Image.new("RGB", (PAGE_W, PAGE_H), (252, 250, 244))
    d = ImageDraw.Draw(img)
    palette = [(255, 90, 90), (250, 180, 40), (60, 190, 120), (70, 140, 255), (180, 90, 220), (30, 190, 200)]
    rng = random.Random(7)

    def dot(cx, cy, r, color):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    for _ in range(260):
        side = rng.randint(0, 3)
        if side == 0:
            cx, cy = rng.uniform(0, PAGE_W), rng.uniform(0, 60)
        elif side == 1:
            cx, cy = rng.uniform(0, PAGE_W), rng.uniform(PAGE_H - 62, PAGE_H)
        elif side == 2:
            cx, cy = rng.uniform(0, 40), rng.uniform(0, PAGE_H)
        else:
            cx, cy = rng.uniform(PAGE_W - 40, PAGE_W), rng.uniform(0, PAGE_H)
        dot(cx, cy, rng.uniform(3, 9), rng.choice(palette))
    for _ in range(70):
        dot(rng.uniform(50, PAGE_W - 50), rng.uniform(70, PAGE_H - 70), rng.uniform(3, 7), rng.choice(palette))
    return img


def _galaxia() -> Image.Image:
    """Star field with a nebula frame concentrated around the page edges."""
    base = Image.new("RGBA", (PAGE_W, PAGE_H), (8, 6, 16, 255))
    overlay = Image.new("RGBA", (PAGE_W, PAGE_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    colors = [(150, 60, 220), (255, 45, 140), (0, 200, 255)]

    def glow(x, y, r, color, alpha):
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, alpha))

    for i in range(6):
        glow(24 + i * 40, 40, 90, colors[i % 3], 55)
        glow(24 + i * 40, PAGE_H - 40, 90, colors[(i + 1) % 3], 55)
    for i in range(6):
        glow(40, 120 + i * 120, 80, colors[i % 3], 45)
        glow(PAGE_W - 40, 120 + i * 120, 80, colors[(i + 1) % 3], 45)
    img = Image.alpha_composite(base, overlay).convert("RGB")
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    star_colors = [(255, 255, 255), (200, 210, 255), (255, 235, 200)]
    for _ in range(600):
        if rng.random() < 0.6:
            side = rng.randint(0, 3)
            if side == 0:
                x, y = rng.uniform(0, PAGE_W), rng.uniform(0, 70)
            elif side == 1:
                x, y = rng.uniform(0, PAGE_W), rng.uniform(PAGE_H - 70, PAGE_H)
            elif side == 2:
                x, y = rng.uniform(0, 45), rng.uniform(0, PAGE_H)
            else:
                x, y = rng.uniform(PAGE_W - 45, PAGE_W), rng.uniform(0, PAGE_H)
        else:
            x, y = rng.uniform(0, PAGE_W), rng.uniform(0, PAGE_H)
        r = rng.choice([1, 1, 1, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=rng.choice(star_colors))
    for sx, sy in [(30, 30), (PAGE_W - 30, 30), (30, PAGE_H - 30), (PAGE_W - 30, PAGE_H - 30)]:
        d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 255, 255))
    return img


def _marco() -> Image.Image:
    """Bold multicolor sawtooth/chevron frame outlining all four margins."""
    img = Image.new("RGB", (PAGE_W, PAGE_H), (250, 247, 242))
    d = ImageDraw.Draw(img)
    palette = [(14, 154, 167), (240, 130, 20), (210, 60, 120), (200, 160, 70)]
    t_top, t_bot, t_side, step = 57, 31, 37, 42
    for i in range(0, PAGE_W + step, step):
        x = i
        d.polygon([(x, 0), (x + step, 0), (x + step // 2, t_top)], fill=palette[(i // step) % 4])
    for i in range(0, PAGE_W + step, step):
        x = i
        d.polygon([(x, PAGE_H), (x + step, PAGE_H), (x + step // 2, PAGE_H - t_bot)], fill=palette[(i // step + 2) % 4])
    for i in range(0, PAGE_H + step, step):
        y = i
        d.polygon([(0, y), (0, y + step), (t_side, y + step // 2)], fill=palette[(i // step + 1) % 4])
    for i in range(0, PAGE_H + step, step):
        y = i
        d.polygon([(PAGE_W, y), (PAGE_W, y + step), (PAGE_W - t_side, y + step // 2)], fill=palette[(i // step + 3) % 4])
    return img


def _flores() -> Image.Image:
    """Botanical rosettes and leaves clustered in the corners and along the edges."""
    img = Image.new("RGB", (PAGE_W, PAGE_H), (252, 247, 238))
    d = ImageDraw.Draw(img)
    green, terra, gold = (46, 96, 60), (200, 110, 70), (190, 150, 60)

    def rosette(cx, cy, r, petal, center):
        for k in range(8):
            ang = 2 * math.pi * k / 8
            px = cx + r * 0.75 * math.cos(ang)
            py = cy + r * 0.75 * math.sin(ang)
            d.ellipse([px - r * 0.42, py - r * 0.48, px + r * 0.42, py + r * 0.48], fill=petal)
        d.ellipse([cx - r * 0.32, cy - r * 0.32, cx + r * 0.32, cy + r * 0.32], fill=center)

    for cx, cy in [(28, 28), (PAGE_W - 28, 28), (28, PAGE_H - 28), (PAGE_W - 28, PAGE_H - 28)]:
        rosette(cx, cy, 22, green, gold)
    for x in range(70, PAGE_W, 120):
        rosette(x, 34, 16, terra, green)
        rosette(x + 60, PAGE_H - 34, 16, green, terra)
    for y in range(70, PAGE_H, 130):
        d.ellipse([6, y, 26, y + 34], fill=green)
        d.ellipse([PAGE_W - 26, y, PAGE_W - 6, y + 34], fill=gold)
    d.rectangle([37, 57, PAGE_W - 37, PAGE_H - 31], outline=green, width=2)
    return img


_PATTERNS: dict[str, Callable[[], Image.Image]] = {
    "rainbow": _rainbow,
    "nebula": _nebula,
    "triangles": _triangles,
    "waves": _waves,
    "mandala": _mandala,
    "aurora": _aurora,
    "confeti": _confeti,
    "galaxia": _galaxia,
    "marco": _marco,
    "flores": _flores,
}


@functools.lru_cache(maxsize=None)
def pattern_jpeg(pattern_id: str) -> bytes:
    """Return the full-page background pattern as cached JPEG bytes."""
    if pattern_id not in _PATTERNS:
        raise KeyError(f"unknown pattern: {pattern_id}")
    buf = io.BytesIO()
    _PATTERNS[pattern_id]().convert("RGB").save(buf, format="JPEG", quality=_QUALITY)
    return buf.getvalue()
