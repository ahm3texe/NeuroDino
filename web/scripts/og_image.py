# Draws public/og-image.png, the 1200x630 social preview, from the site's own
# sprite sheet, pixel font and the trained network's weights:
#
#   uv run --with pillow python scripts/og_image.py . public/og-image.png
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

WEB = Path(sys.argv[1])
OUT = Path(sys.argv[2])
W, H = 1200, 630
BG, INK, MUTED = (247, 247, 247), (83, 83, 83), (143, 143, 143)
POS, NEG = (37, 99, 235), (229, 72, 77)

sheet = Image.open(WEB / "src/assets/100-offline-sprite.png").convert("RGBA")
font = lambda size: ImageFont.truetype(str(WEB / "src/assets/PressStart2P-Regular.ttf"), size)
brain = json.loads((WEB / "src/assets/best-brain.json").read_text())


def sprite(x, y, w, h, scale, key_white=False):
    part = sheet.crop((x, y, x + w, y + h))
    if key_white:
        # The T-rex is drawn on a white outline; the game keys it out too.
        opaque = part.convert("L").point(lambda v: 0 if v > 240 else 255)
        part.putalpha(ImageChops.multiply(part.getchannel("A"), opaque))
    return part.resize((w * scale, h * scale), Image.NEAREST)


img = Image.new("RGBA", (W, H), BG + (255,))
draw = ImageDraw.Draw(img)

# Ground, dino and a cactus at the game's own proportions (x3).
S = 3
GROUND = 520                       # top of the horizon sprite
img.alpha_composite(sprite(2, 54, 600, 12, S), (0, GROUND))
img.alpha_composite(sprite(2, 54, 600, 12, S), (600 * S - 600, GROUND))
img.alpha_composite(sprite(848, 2, 44, 47, S, key_white=True), (72, GROUND - 34 * S))     # T-rex, y 93 vs horizon 127
img.alpha_composite(sprite(332, 2, 25, 50, S), (430, GROUND - 37 * S))    # large cactus, y 90
img.alpha_composite(sprite(86, 2, 46, 14, S), (500, 300))                 # cloud

# Title and tagline.
draw.text((72, 84), "NEURODINO", font=font(64), fill=INK)
draw.text((72, 186), "An evolved neural", font=font(24), fill=INK)
draw.text((72, 222), "network plays", font=font(24), fill=INK)
draw.text((72, 258), "Chrome Dino, live", font=font(24), fill=INK)
draw.text((W - 72, H - 32), "huggingface.co/spaces/ahm3texe/neurodino", font=font(16),
          fill=MUTED, anchor="rs")

# The network, drawn from its real weights on a 2x layer for smooth lines.
K = 2
net = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0))
nd = ImageDraw.Draw(net)
ih, ho = brain["weights_ih"], brain["weights_ho"]
xi, xh, xo = 690, 880, 1060
top, bottom = 96, 456
col = lambda n, pitch: [(top + bottom) / 2 + (k - (n - 1) / 2) * pitch for k in range(n)]
yi, yh, yo = col(12, 30), col(48, 7.5), col(3, 64)
mi = max(abs(w) for row in ih for w in row)
mo = max(abs(w) for row in ho for w in row)
edges = [(abs(ih[j][i]) / mi, ih[j][i], (xi, yi[i]), (xh, yh[j])) for j in range(48) for i in range(12)]
edges += [(abs(ho[k][j]) / mo, ho[k][j], (xh, yh[j]), (xo, yo[k])) for k in range(3) for j in range(48)]
for strength, w, a, b in sorted(edges):
    color = POS if w >= 0 else NEG
    nd.line([(a[0] * K, a[1] * K), (b[0] * K, b[1] * K)],
            fill=color + (int(20 + 150 * strength ** 1.5),), width=K)
img.alpha_composite(net.resize((W, H), Image.LANCZOS))

draw = ImageDraw.Draw(img)
for y in yi:
    draw.ellipse((xi - 6, y - 6, xi + 6, y + 6), fill=(255, 255, 255), outline=INK, width=2)
for y in yh:
    draw.rectangle((xh - 2, y - 2, xh + 2, y + 2), fill=INK)
for k, y in enumerate(yo):
    draw.ellipse((xo - 9, y - 9, xo + 9, y + 9), fill=(255, 255, 255), outline=INK, width=2)
    draw.text((xo + 20, y), ["JUMP", "DUCK", "RUN"][k], font=font(16), fill=INK, anchor="lm")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.convert("RGB").save(OUT, optimize=True)
print(OUT, img.size, OUT.stat().st_size, "bytes")
