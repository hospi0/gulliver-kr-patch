# -*- coding: utf-8 -*-
r"""«空想科学世界» 화면 → «공상과학세계» (2026-09-27)
  원본: STARTUP 레코드 10(셀 75, [u16 개수][4bpp]) + 레코드 8(맵 32×32, 팔레트 0), 바탕 14(0 = 투명 칸)
  글자 1 = 가장 밝은 색, 가장자리 5·6·3·7·4·2 (원본 글자 크기 151×27px, 가운데 x129 y109)
  시안: 나눔명조 ExtraBold 안티에일리어스 → 밝기 문턱으로 1/5/3/4 번호
  python tools/kuusou.py → my files/그래픽/공상과학세계_시안.png (원본과 나란히 ×3), work/mem/kuusou_new.pkl
"""
import os, pickle, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf'
TEXT = '공상과학세계'
CX, CY, H = 129, 109, 27
SHOW = {0: (0, 0, 0), 14: (0, 0, 0), 1: (240, 224, 224), 5: (184, 170, 170), 6: (150, 138, 138), 3: (116, 106, 106),
        7: (90, 82, 82), 4: (64, 58, 58), 2: (40, 36, 36)}


def render():
    px = H
    while True:
        F = ImageFont.truetype(FONT, px)
        l, t, r, b = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), TEXT, font=F)
        if b - t <= H or px < 10:
            break
        px -= 1
    im = Image.new('L', (r - l + 4, b - t + 4), 0)
    ImageDraw.Draw(im).text((2 - l, 2 - t), TEXT, font=F, fill=255)
    return im, px


def compose():
    orig = pickle.load(open(os.path.join(ROOT, 'work', 'mem', 'kuusou_idx.pkl'), 'rb'))
    img = [[(14 if c not in (0,) else 0) if c in (0, 14) else 14 for c in row] for row in orig]
    im, px = render()
    ox = CX - im.width // 2; oy = CY - im.height // 2
    for y in range(im.height):
        for x in range(im.width):
            a = im.getpixel((x, y))
            c = 1 if a >= 192 else 5 if a >= 128 else 3 if a >= 72 else 4 if a >= 32 else None
            if c:
                img[oy + y][ox + x] = c
    print('글꼴 %dpx · %d×%d · x %d‥%d' % (px, im.width, im.height, ox, ox + im.width))
    return orig, img


def to_png(img, box=(24, 88, 210, 44)):
    x0, y0, w, h = box
    out = Image.new('RGB', (w, h))
    for y in range(h):
        for x in range(w):
            out.putpixel((x, y), SHOW.get(img[y0 + y][x0 + x], (255, 0, 255)))
    return out


def main():
    orig, new = compose()
    a, b = to_png(orig), to_png(new)
    out = Image.new('RGB', (a.width, a.height * 2 + 4), (60, 60, 60))
    out.paste(a, (0, 0)); out.paste(b, (0, a.height + 4))
    p = os.path.join(ROOT, 'my files', '그래픽', '공상과학세계_시안.png')
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(p)
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'mem', 'kuusou_new.pkl'), 'wb'))
    print(p)


if __name__ == '__main__':
    main()
