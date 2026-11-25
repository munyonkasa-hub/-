from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'sources/Codex 图像 2026年9月11日 17_21_30.png'
OUTPUT = ROOT / 'production/working/P5-v1.png'
W, H = 1200, 1600
SAGE = (152, 164, 136)
INK = (48, 49, 47)
SOFT = (113, 118, 108)
REGULAR = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

source = Image.open(SOURCE).convert('RGB')
canvas = Image.new('RGB', (W, H), 'white')
draw = ImageDraw.Draw(canvas)
title = ImageFont.truetype(BOLD, 44, index=0)
label = ImageFont.truetype(BOLD, 30, index=0)
value = ImageFont.truetype(REGULAR, 25, index=0)
note = ImageFont.truetype(REGULAR, 18, index=0)

draw.text((62, 54), '設置前に確認できる外寸サイズ', fill=INK, font=title)
draw.rounded_rectangle((62, 133, 1138, 138), radius=2, fill=SAGE)
# Preserve source ratio; no crop or stretch.
product = source.resize((900, 1200), Image.Resampling.LANCZOS)
canvas.paste(product, (0, 170))
draw = ImageDraw.Draw(canvas)
# Height: line follows the full visible top-to-foot span.
draw.line([(835, 272), (835, 1336)], fill=SAGE, width=4)
draw.polygon([(835, 254), (824, 279), (846, 279)], fill=SAGE)
draw.polygon([(835, 1354), (824, 1329), (846, 1329)], fill=SAGE)
draw.line([(810, 272), (854, 272)], fill=SAGE, width=3)
draw.line([(810, 1336), (854, 1336)], fill=SAGE, width=3)
draw.text((866, 745), '高さ', font=label, fill=INK)
draw.text((866, 788), '78.5 cm', font=value, fill=INK)
draw.text((866, 824), '約30.91 in', font=value, fill=SOFT)
# Depth: diagonal leader follows the visible side edge of the top shelf.
draw.line([(540, 408), (682, 348)], fill=SAGE, width=4)
draw.polygon([(525, 414), (550, 421), (543, 397)], fill=SAGE)
draw.polygon([(697, 341), (672, 333), (679, 357)], fill=SAGE)
draw.text((858, 350), '奥行', font=label, fill=INK)
draw.text((858, 392), '26 cm', font=value, fill=INK)
draw.text((858, 428), '約10.24 in', font=value, fill=SOFT)
# Width: only the front-left and front-right feet; do not span toward the rear foot.
draw.line([(194, 1372), (548, 1372)], fill=SAGE, width=4)
draw.polygon([(176, 1372), (201, 1361), (201, 1383)], fill=SAGE)
draw.polygon([(566, 1372), (541, 1361), (541, 1383)], fill=SAGE)
draw.line([(194, 1334), (194, 1384)], fill=SAGE, width=3)
draw.line([(548, 1334), (548, 1384)], fill=SAGE, width=3)
draw.text((255, 1390), '幅 32 cm', font=label, fill=INK)
draw.text((271, 1432), '約12.60 in', font=value, fill=SOFT)
draw.text((62, 1534), '※サイズは採寸方法により、1–2cm程度の誤差が生じる場合がございます。', font=note, fill=(75, 76, 73))
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUTPUT, format='PNG', optimize=True)
print(OUTPUT)
