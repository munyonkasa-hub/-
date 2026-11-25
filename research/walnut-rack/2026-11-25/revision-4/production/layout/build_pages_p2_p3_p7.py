from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'production/raw'
WORK = ROOT / 'production/working'
WORK.mkdir(parents=True, exist_ok=True)
REGULAR = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
INK = (48, 49, 47)
SOFT = (72, 75, 71)
SAGE = (152, 164, 136)

with (ROOT / 'SKILL3_批量制作清单.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = {r['page_id']: r for r in csv.DictReader(f)}

def fit_copy(page_id):
    lines = rows[page_id]['日文全文'].splitlines()
    if len(lines) < 2:
        raise ValueError(f'{page_id}: missing title/body copy')
    return lines[0], '\n'.join(lines[1:])

def wrap(draw, text, font, max_width):
    output=[]
    for paragraph in text.splitlines():
        current=''
        for ch in paragraph:
            candidate=current+ch
            if current and draw.textlength(candidate,font=font)>max_width:
                output.append(current); current=ch
            else:
                current=candidate
        output.append(current)
    return output

def draw_lines(draw, xy, lines, font, fill, leading):
    x,y=xy
    for line in lines:
        draw.text((x,y),line,font=font,fill=fill)
        y+=leading
    return y

# P2: photo above, full-width white copy panel below.
canvas=Image.new('RGB',(1200,1600),'white')
photo=Image.open(RAW/'P2-v1.1.png').convert('RGB').resize((885,1180),Image.Resampling.LANCZOS)
canvas.paste(photo,((1200-885)//2,0))
d=ImageDraw.Draw(canvas)
d.rectangle((0,1180,1200,1184),fill=SAGE)
title,body=fit_copy('P2')
tf=ImageFont.truetype(BOLD,42,index=0); bf=ImageFont.truetype(REGULAR,22,index=0)
d.text((64,1224),title,font=tf,fill=INK)
body_lines=wrap(d,body,bf,1070)
draw_lines(d,(64,1294),body_lines,bf,SOFT,34)
canvas.save(WORK/'P2-v1.1.png',format='PNG',optimize=True)

# P3: full-scene background with a white right-side panel outside the product silhouette.
canvas=Image.open(RAW/'P3-v1.png').convert('RGB').resize((1200,1600),Image.Resampling.LANCZOS)
d=ImageDraw.Draw(canvas)
px,py,pw,ph=920,500,280,590
d.rectangle((px,py,px+pw,py+ph),fill='white')
d.rectangle((px,py,px+5,py+ph),fill=SAGE)
title,body=fit_copy('P3')
title='3段に分けて、\n見渡しやすく整理'
tf=ImageFont.truetype(BOLD,25,index=0); bf=ImageFont.truetype(REGULAR,18,index=0)
x=px+24; maxw=pw-48
y=py+34
y=draw_lines(d,(x,y),wrap(d,title,tf,maxw),tf,INK,42)+22
draw_lines(d,(x,y),wrap(d,body,bf,maxw),bf,SOFT,29)
canvas.save(WORK/'P3-v1.1.png',format='PNG',optimize=True)

# P7: full-scene background with an upper-left card on the empty wall/curtain area.
photo=Image.open(RAW/'P7-v1.1.png').convert('RGB').resize((1200,1600),Image.Resampling.LANCZOS)
canvas=Image.new('RGB',(1200,1600),'white')
# Shift toward the right to reserve the blank upper-left wall for copy; the cropped right edge is background only, not product.
canvas.paste(photo,(110,0))
d=ImageDraw.Draw(canvas)
px,py,pw,ph=48,46,450,390
d.rectangle((px,py,px+pw,py+ph),fill='white')
d.rectangle((px,py,px+pw,py+5),fill=SAGE)
title,body=fit_copy('P7')
title='音楽の小物を、\n段ごとにまとめて置ける'
tf=ImageFont.truetype(BOLD,31,index=0); bf=ImageFont.truetype(REGULAR,19,index=0)
x=px+24; maxw=pw-48
y=py+28
y=draw_lines(d,(x,y),wrap(d,title,tf,maxw),tf,INK,44)+18
draw_lines(d,(x,y),wrap(d,body,bf,maxw),bf,SOFT,30)
canvas.save(WORK/'P7-v1.1.png',format='PNG',optimize=True)
print('Rendered P2/P3/P7 1200x1600 PNG layouts from the exact approved Japanese text.')
